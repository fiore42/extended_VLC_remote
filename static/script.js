function isMobileDevice() {
    return /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

function checkScreenSize() {
    const width = window.innerWidth;
    console.log("Screen width:", width);
    console.log("User Agent:", navigator.userAgent);
    
    if (isMobileDevice() || width < 768) {
        console.log("Mobile detected - applying styles");
        document.body.classList.add('mobile');
    } else {
        console.log("Desktop detected - normal styles applied");
    }
}

function applyTheme() {
    const isDarkMode = window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.body.classList.toggle("dark-mode", isDarkMode);
}

applyTheme(); // Apply on load
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme); // Listen for changes

let CONFIG = {}; // Global variable to store config

async function loadConfig() {
    try {
        const response = await fetch("/config"); // Fetch from Flask
        if (!response.ok) throw new Error("Failed to load config");
        CONFIG = await response.json();

        console.log("✅ Config Loaded:", CONFIG);

        // Example usage
        const vlcHost = CONFIG.VLC_HOST;
        console.log("VLC Host:", vlcHost);
    } catch (error) {
        console.error("⚠️ Error loading config:", error);
    }
}

// Call function on page load
loadConfig();


checkScreenSize();
window.addEventListener('resize', checkScreenSize);

const systemVolumeEventSource = new EventSource('/system_volume_updates');

systemVolumeEventSource.onmessage = (event) => {
    const system_volume = parseInt(event.data);
    if (system_volume !== document.getElementById('systemVolume').value) {
        document.getElementById('systemVolume').value = system_volume;
        document.getElementById('systemValue').textContent = `${system_volume}%`;
    }
};

systemVolumeEventSource.onerror = (error) => {
    console.error("systemVolumeEventSource failed:", error);
    if (error.target.readyState === systemVolumeEventSource.CLOSED) {
        console.log("systemVolumeEventSource connection closed.");
    }
    systemVolumeEventSource.close();
};

let currentVLCStatus = null; // Initialize to null

const vlcEventSource = new EventSource('/vlc_status_updates');

vlcEventSource.onmessage = (event) => {
    try {
        const vlcStatus = JSON.parse(event.data);
        currentVLCStatus = vlcStatus; // Update the global variable
        processVLCStatus(vlcStatus); 
    } catch (error) {
        console.error("Error parsing VLC status:", error, event.data);
    }
};

vlcEventSource.onerror = (error) => {
    console.error("vlcEventSource failed:", error);
    if (error.target.readyState === vlcEventSource.CLOSED) {
        console.log("vlcEventSource connection closed.");
    }
    vlcEventSource.close();
};

// Initialize slider value
fetch('/current_system_volume')
    .then(response => response.json())
    .then(data => {
        document.getElementById('systemVolume').value = data.system_volume;
        document.getElementById('systemValue').textContent = `${data.system_volume}%`;
    });

let isDragging = false;  // Track whether user is dragging the slider

function getSystemVolume(value) {
    isDragging = true;  // 🔹 Prevent blocking broadcast updates while dragging

    fetch(`/system_volume?volume=${value}`)
        .then(response => response.json())
        .then(data => {
            console.log("Server confirmed volume:", data.system_volume);
            setTimeout(() => { isDragging = false; }, 500); // 🔹 Allow updates after delay
        })
        .catch(error => {
            console.error('Error:', error);
            isDragging = false;
        });
}


function processVLCStatus(data) {
    console.log("Received VLC Data:", data);  // Debugging output

    // Extract filename from VLC status XML
    let filename = "Unknown Title";
    if (data.information && data.information.category) {
        let metaCategory = data.information.category.find(cat => cat["@name"] === "meta");
        if (metaCategory && metaCategory.info) {
            let filenameInfo = metaCategory.info.find(info => info["@name"] === "filename");
            if (filenameInfo) {
                filename = filenameInfo["#text"];
            }
        }
    }

    // Update UI elements
    document.getElementById('mediaTitle').textContent = filename;
    document.getElementById('seekSlider').value = data.position * 100;
    document.getElementById('seekValue').textContent = `${Math.round(data.position * 100)}%`;
    // Scale VLC volume (0-512) to slider range (0-100)

    const scaledVolume = Math.round((data.volume / CONFIG.MAX_VLC_VOLUME) * 100);
    document.getElementById('vlcVolume').value = scaledVolume;
    document.getElementById('vlcValue').textContent = `${scaledVolume}%`;
    document.getElementById('playPause').textContent = data.state === "playing" ? "⏸️ Pause" : "▶️ Play";
    document.getElementById('fullscreenToggle').textContent = data.fullscreen === "true" ? "🔲 Exit Fullscreen" : "🖥️ Fullscreen";

    // Debugging output for all elements
    console.log("Filename:", filename);
    console.log("Seek Position:", document.getElementById('seekSlider').value);
    console.log("Seek Display:", document.getElementById('seekValue').textContent);
    console.log("VLC Volume:", document.getElementById('vlcVolume').value);
    console.log("VLC Volume Display:", document.getElementById('vlcValue').textContent);
    console.log("Playback State:", document.getElementById('playPause').textContent);
    console.log("Fullscreen State:", document.getElementById('fullscreenToggle').textContent);
}

function sendVLCCommand(command, value = "") {
    fetch(`/vlc_command?cmd=${command}&val=${value}`)
        .then(response => {
            if (!response.ok) { // Check for HTTP errors
                return response.text().then(err => { throw new Error(err) }); // Re-throw error
            }
            return response.json();
        })
        .then(data => {
            console.log("VLC command response:", data); // Log the response (optional)
            // No need to call processVLCStatus() here!  SSE will update the UI.
        })
        .catch(error => {
            console.error("Error sending VLC command:", error);
        });
}

document.getElementById("menuButton").addEventListener("click", function() {
    document.getElementById("sidebar").style.left = "0";
});

document.getElementById("closeMenu").addEventListener("click", function() {
    document.getElementById("sidebar").style.left = "-250px";
});


// Seek Back/Fwd
document.getElementById('seekBack10').addEventListener('click', () => sendVLCCommand("seek", "-10S"));
// Play/Pause Toggle
document.getElementById('playPause').addEventListener('click', () => sendVLCCommand("pl_pause"));
document.getElementById('seekFwd10').addEventListener('click', () => sendVLCCommand("seek", "+10S"));

document.getElementById('seekBack60').addEventListener('click', () => sendVLCCommand("seek", "-60S"));
// Fullscreen Toggle
document.getElementById('fullscreenToggle').addEventListener('click', () => sendVLCCommand("fullscreen"));
document.getElementById('seekFwd60').addEventListener('click', () => sendVLCCommand("seek", "+60S"));

// Seek Slider

document.getElementById('seekSlider').addEventListener('change', (e) => {
    const seekPercentage = e.target.value / 100;

    if (currentVLCStatus && currentVLCStatus.length) { // Check if initialized AND has length
        const seekSeconds = Math.round(currentVLCStatus.length * seekPercentage);
        sendVLCCommand("seek", seekSeconds);
    } else {
        console.error("VLC status not yet available or missing length.  Cannot seek.");
        // **Important:** Provide user feedback!
        document.getElementById('seekSlider').value = 0; // Or keep the old value
        document.getElementById('seekValue').textContent = "N/A"; // Or some other message
        // Optionally, you could disable the seek slider until currentVLCStatus is valid:
        // document.getElementById('seekSlider').disabled = true;
    }
});


document.getElementById('vlcVolume').addEventListener('input', (e) => {
    const volumePercentage = e.target.value / 100; // Convert slider value (0-100) to 0.0-1.0 range
    const vlcVolume = Math.round(CONFIG.MAX_VLC_VOLUME * volumePercentage); // Scale to 0-512 and round to nearest integer
    sendVLCCommand("volume", vlcVolume); // Send the scaled volume to VLC
});


document.getElementById('systemVolume').addEventListener('input', (e) => {
    getSystemVolume(e.target.value);
});