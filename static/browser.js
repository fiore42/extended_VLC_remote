document.addEventListener("DOMContentLoaded", () => {
    fetchMedia();
});

function fetchMedia() {
    fetch('/list_media')
        .then(response => response.json())
        .then(data => {
            const fileList = document.getElementById('fileList');
            fileList.innerHTML = ""; // Clear previous entries

            if (data.error) {
                fileList.innerHTML = `<li style="color:red;">${data.error}</li>`;
                return;
            }

            data.files.forEach(file => {
                const listItem = document.createElement("li");
                listItem.textContent = file;
                listItem.style.cursor = "pointer";
                listItem.onclick = () => playInVLC(file);
                fileList.appendChild(listItem);
            });
        })
        .catch(error => {
            console.error("Error fetching media:", error);
            fileList.innerHTML = `<li style="color:red;">Failed to load media files.</li>`;
        });
}

function playInVLC(filePath) {
    fetch('/play_media', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ "file": filePath })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            alert(`Now playing: ${filePath}`);
        } else {
            alert("Failed to play in VLC.");
        }
    })
    .catch(error => {
        console.error("Error sending file to VLC:", error);
        alert("Error sending file to VLC.");
    });
}
