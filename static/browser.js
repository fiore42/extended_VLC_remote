function fetchMedia(path = "") {
    const url = path ? `/list_media?path=${encodeURIComponent(path)}` : "/list_media";

    fetch(url)
        .then(response => response.json())
        .then(data => {
            const fileList = document.getElementById("fileList");
            fileList.innerHTML = ""; // Clear previous entries

            if (data.error) {
                fileList.innerHTML = `<li style="color:red;">${data.error}</li>`;
                return;
            }

            // Parent folder link (if applicable)
            if (data.parent) {
                const parentItem = document.createElement("li");
                parentItem.textContent = "📁 << Parent Folder >>";
                parentItem.style.cursor = "pointer";
                parentItem.style.fontWeight = "bold";
                parentItem.onclick = () => fetchMedia(data.parent);
                fileList.appendChild(parentItem);
            }

            // Subfolders
            data.folders.forEach(folder => {
                const folderItem = document.createElement("li");
                folderItem.textContent = `📁 ${folder}`;
                folderItem.style.cursor = "pointer";
                folderItem.onclick = () => fetchMedia(`${data.current_path}/${folder}`);
                fileList.appendChild(folderItem);
            });

            // Video files
            data.files.forEach(file => {
                const fileItem = document.createElement("li");
                fileItem.textContent = `🎬 ${file}`;
                fileItem.style.cursor = "pointer";
                fileItem.onclick = () => playInVLC(`${data.current_path}/${file}`);
                fileList.appendChild(fileItem);
            });
        })
        .catch(error => {
            console.error("Error fetching media:", error);
            fileList.innerHTML = `<li style="color:red;">Failed to load media files.</li>`;
        });
}

function playInVLC(filePath) {
    fetch(`/vlc_command?cmd=in_play&val=${encodeURIComponent(filePath)}`)
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

// Load initial media list
document.addEventListener("DOMContentLoaded", () => fetchMedia());
