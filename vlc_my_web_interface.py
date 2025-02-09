#!/usr/bin/python

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
import sys
from urllib.parse import quote, unquote, urlencode

app = Flask(__name__, static_folder="static", template_folder="templates")

# @app.before_request
# def log_request():
#     print(f"Request: {request.method} {request.path} from {request.remote_addr}")

def str_to_bool(value, default=True):
    if value is None:
        return default
    return str(value).strip().lower() == "true"

# Load config.json
CONFIG_FILE = "static/config.json"

try:
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    print("Config loaded successfully.")
except FileNotFoundError:
    print(f"ERROR: Config file {CONFIG_FILE} not found.", file=sys.stderr)
    sys.exit(1)  # Exit with error code 1
except json.JSONDecodeError:
    print(f"ERROR: Config file {CONFIG_FILE} is not a valid JSON file.", file=sys.stderr)
    sys.exit(1)  # Exit with error code 1
except Exception as e:
    print(f"ERROR: Unexpected error loading config: {e}", file=sys.stderr)
    sys.exit(1)  # Exit with error code 1

# List of required keys
REQUIRED_KEYS = [
    "FLASK_PORT", "MEDIA_DIR", "VLC_PORT", "VLC_PWD"
]

# Validate presence and non-emptiness
for key in REQUIRED_KEYS:
    if key not in config or config[key] == "":
        sys.exit(f"Error: Missing or empty required configuration key: {key}")

# Define default values for optional keys
DEFAULTS = {
    "FLASK_HOST": "0.0.0.0",
    "MAX_VLC_VOLUME": 512,
    "REFRESH_RATE": 1,
    "VLC_BIN": "/usr/bin/vlc",
    "DISPLAY": ":0",
    "VLC_HOST": "127.0.0.1",
    "VLC_ADDR": "localhost",
    "VLC_USER": "",
    "VLC_XML": "/requests/status.xml",
    "LAST_OPENED": "true"
}

# Apply defaults for optional keys
for key, default_value in DEFAULTS.items():
    config[key] = config.get(key, default_value) or default_value  # Use default if missing or empty

# Convert necessary values to the correct type
try:
    FLASK_HOST = config["FLASK_HOST"]
    FLASK_PORT = int(config["FLASK_PORT"])
    MAX_VLC_VOLUME = int(config["MAX_VLC_VOLUME"])
    REFRESH_RATE = int(config["REFRESH_RATE"])
    MEDIA_DIR = config["MEDIA_DIR"]
    VLC_BIN = config["VLC_BIN"]
    DISPLAY = config["DISPLAY"]
    VLC_HOST = config["VLC_HOST"]
    VLC_PORT = int(config["VLC_PORT"])
    VLC_ADDR = config["VLC_ADDR"]
    VLC_USER = config["VLC_USER"]
    VLC_PASSWORD = config["VLC_PWD"]
    VLC_XML = config["VLC_XML"]
    LAST_OPENED = str_to_bool(config.get("LAST_OPENED"), default=True)
except ValueError as e:
    sys.exit(f"Error: Invalid numeric value in configuration: {e}")

# Print out the final config values (optional)
print(f"Final Config Values:\n{json.dumps(config, indent=2)}")

VLC_URL = f"http://{VLC_ADDR}:{VLC_PORT}"

VLC_STATUS_URL = f"{VLC_URL}{VLC_XML}"

# In-memory storage for the last opened folder
last_opened_folder = None

def fetch_vlc_status(): # function that fetches VLC data
    try:
        response = requests.get(VLC_STATUS_URL, auth=(VLC_USER, VLC_PASSWORD))
        response.raise_for_status()
        xml_data = response.text
        json_data = xmltodict.parse(xml_data)["root"]  # Parse and extract
        return json_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching VLC status: {e}")
        return None     

vlc_clients = set()  # Set to store connected VLC clients
vlc_status_cache = None # cache the last status

# Define the set of ignored keys that should only be updated every 60 seconds
IGNORED_KEYS = {'time', 'position', 'stats'}

def update_vlc_status_periodically():
    global vlc_status_cache
    last_update_time = 0  # Store last update timestamp for ignored keys
    last_rounded_position = None  # Track last rounded position

    while True:
        vlc_status = fetch_vlc_status()
        
        if not vlc_status:
            time.sleep(REFRESH_RATE)
            print("Invalid vlc_status")
            continue

        current_time = time.time()  # Get current timestamp

        # Convert nested dictionaries to JSON strings for accurate comparison
        def normalize_dict(d):
            return {k: json.dumps(v, sort_keys=True) if isinstance(v, dict) else v for k, v in d.items()}

        normalized_vlc_status = normalize_dict(vlc_status)
        normalized_cache = normalize_dict(vlc_status_cache) if vlc_status_cache else {}

        # Identify changed keys
        changed_keys = [
            k for k in normalized_vlc_status.keys()
            if normalized_vlc_status.get(k) != normalized_cache.get(k)
        ]

        # Separate ignored keys from immediate update keys
        ignored_keys_changed = [k for k in changed_keys if k in IGNORED_KEYS]
        immediate_keys_changed = [k for k in changed_keys if k not in IGNORED_KEYS]

        # Handle position movement > 2% logic
        current_position = float(vlc_status.get("position", 0))
        rounded_position = round(current_position * 100)

        position_moved = (
            last_rounded_position is not None and 
            abs(rounded_position - last_rounded_position) > 2
        )

        # Determine if an update should be broadcast
        should_broadcast_ignored = bool(ignored_keys_changed) and (current_time - last_update_time) > 60
        should_broadcast_immediate = bool(immediate_keys_changed)

        # print("should_broadcast_ignored:", should_broadcast_ignored)
        # print("should_broadcast_immediate:", should_broadcast_immediate)

        if should_broadcast_immediate:
            print(f"Immediate VLC Status Changed: {immediate_keys_changed}")
            vlc_status_cache = vlc_status
            broadcast_vlc_status(vlc_status)

        elif position_moved:
            # normally we disregard position change, unless it's more than 2%
            print(f"Position Moved > 2% (Rounded {last_rounded_position} -> {rounded_position})")
            last_rounded_position = rounded_position
            vlc_status_cache = vlc_status
            broadcast_vlc_status(vlc_status)

        elif should_broadcast_ignored:
            print(f"Ignored VLC Status Changed (delayed): {ignored_keys_changed}")
            last_update_time = current_time
            vlc_status_cache = vlc_status
            broadcast_vlc_status(vlc_status)

        # Update last known position
        last_rounded_position = rounded_position

        time.sleep(REFRESH_RATE)

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
        time.sleep(REFRESH_RATE)

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

        # Send the last known VLC status immediately when a client connects
        if vlc_status_cache:
            q.put(json.dumps(vlc_status_cache))  # Convert to JSON string and send

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

@app.route('/vlc_command')
def vlc_command():
    command = request.args.get('cmd', '')
    value = request.args.get('val', '')

    try:
        requests.get(VLC_STATUS_URL, params={"command": command, "val": value}, auth=(VLC_USER, VLC_PASSWORD))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/vlc_play')
def vlc_play():
    """Plays a media file in VLC."""
    file_path = request.args.get('file', '')

    if not file_path:
        return jsonify({"error": "No file path provided"}), 400

    # ✅ Decode first to ensure proper encoding flow
    file_path = unquote(file_path)

    # ✅ Encode only spaces (not slashes)
    encoded_path = quote(file_path, safe='/:')  # Spaces -> %20, slashes preserved

    # ✅ Construct the URL manually to prevent double encoding
    full_url = f"{VLC_STATUS_URL}?command=in_play&input={encoded_path}"

    print(f"Sending VLC play request: {full_url}")  # Debugging output

    try:
        response = requests.get(full_url, auth=(VLC_USER, VLC_PASSWORD))
        response.raise_for_status()
        return jsonify({"status": "success", "file": file_path})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/config')
def get_config():
    """Serve config.json to the frontend."""
    return config, 200, {"Content-Type": "application/json"}

ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}

@app.route('/list_media')
def list_media():

    """Lists video files in the requested path & classifies folders as playable or normal."""
    global last_opened_folder

    requested_path = request.args.get("path")

    print(f"LAST_OPENED: {LAST_OPENED}")  # Debugging output
    print(f"requested_path: {requested_path}")  # Debugging output

    # If LAST_OPENED is enabled and no specific path is requested, use the last folder browsed
    if LAST_OPENED and not requested_path:
        requested_path = last_opened_folder or MEDIA_DIR  # Default to MEDIA_DIR if never set

    requested_path = os.path.abspath(os.path.join(MEDIA_DIR, unquote(requested_path)))

    # Ensure security: restrict to MEDIA_DIR and prevent path traversal
    if not requested_path.startswith(MEDIA_DIR):
        requested_path = MEDIA_DIR

    media_files = []
    folders = set()  # Regular folders (contain multiple playable files)
    playable_folders = set()  # ✅ Folders with exactly ONE playable file

    def get_valid_files(folder_path):
        """Recursively collect all valid media files inside a folder."""
        valid_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if os.path.splitext(file)[1].lower() in ALLOWED_EXTENSIONS:
                    valid_files.append(os.path.join(root, file))  # Store full path
        return valid_files

    try:
        # Scan the **requested_path only** for files
        for entry in os.scandir(requested_path):
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in ALLOWED_EXTENSIONS:
                media_files.append(entry.name)  # Store only file names

        # Scan **only direct subfolders** of requested_path
        for entry in os.scandir(requested_path):
            if entry.is_dir():
                sub_path = os.path.join(requested_path, entry.name)
                valid_files = get_valid_files(sub_path)  # Get all playable files inside

                if valid_files:
                    if len(valid_files) == 1:  # ✅ Exactly ONE playable file
                        playable_folders.add(entry.name)
                    else:  # ✅ More than one playable file
                        folders.add(entry.name)

        response = {
            "current_path": requested_path,
            "folders": sorted(folders),  # ✅ Regular folders (contain multiple playable files)
            "playable_folders": sorted(playable_folders),  # ✅ Folders with ONE playable file
            "files": sorted(media_files)  # ✅ Files only in `requested_path`
        }

        # Add parent folder navigation if not in MEDIA_DIR
        if requested_path != MEDIA_DIR:
            response["parent"] = os.path.dirname(requested_path)

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# @app.route('/list_media')
# def list_media():
#     """List only files in the requested path & only subfolders containing valid files at any level."""
#     requested_path = request.args.get("path", MEDIA_DIR)  # Default to MEDIA_DIR

#     # Ensure security: restrict to MEDIA_DIR and prevent path traversal
#     if not requested_path.startswith(MEDIA_DIR):
#         requested_path = MEDIA_DIR

#     media_files = []
#     valid_subfolders = set()  # To store only subfolders that contain valid files

#     try:
#         # Scan the **requested_path only** for files
#         for entry in os.scandir(requested_path):
#             if entry.is_file() and os.path.splitext(entry.name)[1].lower() in ALLOWED_EXTENSIONS:
#                 media_files.append(entry.name)  # Store file names (not full path)

        # # Recursively check subfolders to see if they contain valid files
        # for root, dirs, files in os.walk(requested_path):
        #     for file in files:
        #         if os.path.splitext(file)[1].lower() in ALLOWED_EXTENSIONS:
        #             rel_path = os.path.relpath(root, requested_path)  # Get relative path from requested_path
        #             if rel_path != ".":
        #                 valid_subfolders.add(rel_path.split(os.sep)[0])  # Store only first-level subfolder
        #             break  # Stop scanning this subfolder once a valid file is found

#         response = {
#             "current_path": requested_path,
#             "folders": sorted(valid_subfolders),  # Show only first-level folders
#             "files": sorted(media_files)  # Show only files in requested_path
#         }

#         # Add parent folder navigation if not in MEDIA_DIR
#         if requested_path != MEDIA_DIR:
#             response["parent"] = os.path.dirname(requested_path)

#         return jsonify(response)

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@app.route('/browser')
def browser():
    return render_template("browser.html")

@app.route('/')
def index():
    return render_template("index.html")

def start_vlc():
    """Starts VLC in a new thread if it's not running."""
    print("Checking if VLC is running...")
    try:
        response = requests.get(VLC_STATUS_URL, auth=(VLC_USER, VLC_PASSWORD), timeout=2)
        if response.status_code == 200:
            print("VLC is already running.")
            return  # VLC is already running
    except requests.exceptions.RequestException:
        print("VLC is not running. Starting VLC...")

    def run_vlc():
        os.environ["DISPLAY"] = config["DISPLAY"]  # Ensure DISPLAY is set
        cmd = f'{VLC_BIN} --http-password {VLC_PASSWORD} --http-host={VLC_HOST} --http-port={VLC_PORT}'
        subprocess.Popen(shlex.split(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("VLC started.")

    # Start VLC in a separate thread
    threading.Thread(target=run_vlc, daemon=True).start()


if __name__ == '__main__':

    start_vlc() # Ensure VLC starts if not already running

    # Ensure volume_queue is initialized before starting the thread
    volume_queue = queue.Queue()

    # Start the background thread to monitor system volume changes

    system_volume_thread = threading.Thread(target=update_system_volume_periodically, daemon=True)
    system_volume_thread.start()

    vlc_status_thread = threading.Thread(target=update_vlc_status_periodically, daemon=True)
    vlc_status_thread.start()
    
    print("Flask app is starting...")  # Debug log to confirm startup
    app.run(host=FLASK_HOST, port=FLASK_PORT)  # Start Flask server
    #app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)