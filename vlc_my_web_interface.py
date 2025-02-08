from flask import Flask, request, render_template, jsonify, Response, send_from_directory
import requests
import subprocess
import shlex
import time
import threading
import queue
import os
import xmltodict
import json

app = Flask(__name__, static_folder="static", template_folder="templates")
    
# Configuration variables at the top
VLC_HOST = "http://localhost:8090"  # Adjust this to your VLC's address
VLC_PASSWORD = "password"  # Replace with your VLC password
FLASK_HOST = '0.0.0.0'  # Host for the Flask app
FLASK_PORT = 5000  # Port for the Flask app


vlc_clients = set()  # Set to store connected VLC clients
vlc_status_cache = None # cache the last status

def fetch_vlc_status(): # function that fetches VLC data
    try:
        response = requests.get(f"{VLC_HOST}/requests/status.xml", auth=('', VLC_PASSWORD))
        response.raise_for_status()
        xml_data = response.text
        json_data = xmltodict.parse(xml_data)["root"]  # Parse and extract
        return json_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching VLC status: {e}")
        return None

def update_vlc_status_periodically():
    global vlc_status_cache
    while True:
        vlc_status = fetch_vlc_status()

        # print(vlc_status)

        if vlc_status != vlc_status_cache: # check if it has changed
#            print(vlc_status)
            vlc_status_cache = vlc_status
            if vlc_status:
                broadcast_vlc_status(vlc_status)
        time.sleep(1)  # Adjust polling interval as needed

def broadcast_vlc_status(status):
    """Send VLC status updates to all connected clients."""
    json_status = json.dumps(status)  # Use json.dumps() to create JSON string
#    print(f"Broadcasting to {len(clients)} clients: VLC status {json_status}")
    print(f"Broadcasting to {len(clients)} clients: VLC status")
    for client in list(vlc_clients):
        try:
            client.put(json_status)
        except Exception:
            vlc_clients.remove(client)

def fetch_system_volume():
    try:
        result = subprocess.run(
            ['amixer', 'get', 'Master'],
            stdout=subprocess.PIPE,  # Capture stdout
            stderr=subprocess.PIPE,  # Capture stderr
            text=True,
            check=True
        )

        # Print only stderr, if any
        if result.stderr:
            print("Error from amixer:", result.stderr)

        # Process stdout to extract volume
        for line in result.stdout.splitlines():
            if 'Front Left:' in line:  # Adjust if necessary
                system_volume_str = line.split('[')[1].split('%')[0]
                return int(system_volume_str)

        return None  # Return None if volume not found

    except (subprocess.CalledProcessError, ValueError) as e:
        print("Exception occurred:", e)
        return None


current_system_volume = fetch_system_volume()

clients = set()  # Set of connected clients

def update_system_volume_periodically():
    global current_system_volume
    while True:
        system_volume = fetch_system_volume()
        #print("update_system_volume_periodically:", volume)
        if system_volume is not None and system_volume != current_system_volume:
            current_system_volume = system_volume
            print(f"Broadcasting system volume update: {system_volume}")
            broadcast_system_volume(system_volume)  # Send update to all clients
        time.sleep(1)

@app.route('/system_volume')
def system_volume():
    global current_system_volume
    try:
        system_volume = int(request.args.get('volume', 0))
        if 0 <= system_volume <= 100:
            result = subprocess.run(
                ['amixer', 'set', 'Master', f'{system_volume}%'],
                stdout=subprocess.PIPE,  # Capture stdout (but don't print it)
                stderr=subprocess.PIPE,  # Capture stderr (print if there's an error)
                text=True,
                check=True
            )

            # Print only stderr if it exists
            if result.stderr:
                print("Error from amixer:", result.stderr)

            current_system_volume = system_volume
            broadcast_system_volume(system_volume)  # 🔹 Ensure all clients receive updates (including sender)
            return jsonify({'status': 'success', 'system_volume': system_volume})

    except subprocess.CalledProcessError as e:
        print("Subprocess error:", e.stderr)  # Print only stderr from exception
        return jsonify({'status': 'error', 'message': e.stderr}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def broadcast_system_volume(system_volume):
    """Send volume updates to all connected clients."""
    print(f"Broadcasting to {len(clients)} clients: System Volume {system_volume}")
    for client in list(clients):  # Iterate over a copy of the set
        try:
            client.put(system_volume)  # Send the volume to each client
        except Exception:
            clients.remove(client)  # Remove disconnected clients


@app.route('/system_volume_updates')
def system_volume_updates():
    """Server-Sent Events (SSE) endpoint to notify clients of volume changes."""
    def event_stream(q):
        clients.add(q)  # Register the client
        try:
            while True:
                system_volume = q.get()
                yield f"data: {system_volume}\n\n"
        except GeneratorExit:
            clients.remove(q)  # Remove client when it disconnects

    q = queue.Queue()  # Each client gets its own queue
    return Response(event_stream(q), mimetype="text/event-stream")

@app.route('/vlc_status_updates')
def vlc_status_updates():
    """SSE endpoint for VLC status updates."""
    def event_stream(q):
        vlc_clients.add(q)
        try:
            while True:
                status = q.get()
                yield f"data: {status}\n\n"  # Send the JSON string as an event
                # yield f"data: {jsonify(status).data.decode('utf-8')}\n\n" # JSON stringify
        except GeneratorExit:
            vlc_clients.remove(q)

    q = queue.Queue()
    return Response(event_stream(q), mimetype="text/event-stream")



@app.route('/current_system_volume')  # Restored route
def get_current_volume():
    global current_system_volume
    return jsonify({'system_volume': current_system_volume})

# # polling -> moved to SSE notifications
# @app.route('/vlc_status')
# def vlc_status():
#     try:
#         response = requests.get(f"{VLC_HOST}/requests/status.xml", auth=('', VLC_PASSWORD))
#         response.raise_for_status()
#         xml_data = response.text
        
#         # Convert XML to JSON (using xmltodict)
#         json_data = xmltodict.parse(xml_data)
#         return jsonify(json_data["root"])  # Return relevant part
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@app.route('/vlc_command')
def vlc_command():
    command = request.args.get('cmd', '')
    value = request.args.get('val', '')

    try:
        requests.get(f"{VLC_HOST}/requests/status.xml", 
                     params={"command": command, "val": value},
                     auth=('', VLC_PASSWORD))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/')
def index():
    return render_template("index.html")       

if __name__ == '__main__':
    # Ensure volume_queue is initialized before starting the thread
    volume_queue = queue.Queue()

    # Start the background thread to monitor system volume changes

    system_volume_thread = threading.Thread(target=update_system_volume_periodically, daemon=True)
    system_volume_thread.start()

    vlc_status_thread = threading.Thread(target=update_vlc_status_periodically, daemon=True)
    vlc_status_thread.start()
    
    print("Flask app is starting...")  # Debug log to confirm startup
    app.run(host=FLASK_HOST, port=FLASK_PORT)  # Start Flask server

