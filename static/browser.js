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

            // Playable Subfolders
            data.playable_folders.forEach(playable_folders => {
                const folderItem = document.createElement("li");
                folderItem.textContent = `📁 ${playable_folders}`;
                folderItem.style.cursor = "pointer";
                folderItem.onclick = () => playInVLC(`${data.current_path}/${playable_folders}`);
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

// function fetchMedia(directory = "") {
//     fetch(`/list_media?path=${encodeURIComponent(directory)}`)
//         .then(response => response.json())
//         .then(data => {
//             const fileList = document.getElementById('fileList');
//             fileList.innerHTML = ""; // Clear previous entries

//             if (data.error) {
//                 fileList.innerHTML = `<li style="color:red;">${data.error}</li>`;
//                 return;
//             }

//             // If a folder contains only ONE valid file, play it immediately
//             if (data.files.length === 1 && data.subfolders.length === 0) {
//                 playInVLC(data.files[0]); // ✅ Auto-play single file
//                 return;
//             }

//             // Add << parent folder >> option (if applicable)
//             if (data.parent) {
//                 const parentItem = document.createElement("li");
//                 parentItem.textContent = "📁 .. (Parent Folder)";
//                 parentItem.style.fontWeight = "bold";
//                 parentItem.style.cursor = "pointer";
//                 parentItem.onclick = () => fetchMedia(data.parent);
//                 fileList.appendChild(parentItem);
//             }

//             // Add subfolders
//             data.subfolders.forEach(folder => {
//                 const listItem = document.createElement("li");
//                 listItem.textContent = `📁 ${folder}`;
//                 listItem.style.fontWeight = "bold";
//                 listItem.style.cursor = "pointer";
//                 listItem.onclick = () => fetchMedia(directory + "/" + folder); // Navigate into folder
//                 fileList.appendChild(listItem);
//             });

//             // Add valid media files
//             data.files.forEach(file => {
//                 const listItem = document.createElement("li");
//                 listItem.textContent = `🎬 ${file}`;
//                 listItem.style.cursor = "pointer";
//                 listItem.onclick = () => playInVLC(file);
//                 fileList.appendChild(listItem);
//             });
//         })
//         .catch(error => {
//             console.error("Error fetching media:", error);
//             fileList.innerHTML = `<li style="color:red;">Failed to load media files.</li>`;
//         });
// }


/* Function to show a temporary notification */
function showNotification(message, isError = false) {
    const notification = document.createElement("div");
    notification.textContent = message;
    notification.className = "notification";
    if (isError) {
        notification.classList.add("error");  // Add an error class if it's an error
    }
    document.body.appendChild(notification);

    // Automatically remove after 1 second
    setTimeout(() => {
        notification.remove();
    }, 1000);
}

function playInVLC(filePath) {
    fetch(`/vlc_play?file=${encodeURIComponent(filePath)}`)
        .then(response => {
            if (!response.ok) throw new Error("Server returned an error");
            return response.json();
        })
        .then(data => {
            if (data.status === "success") {
                showNotification(`Now playing: ${filePath}`);

                // ✅ Switch back to VLC Controls
                document.getElementById("vlcSection").style.display = "block";
                document.getElementById("browserSection").style.display = "none";

                // ✅ Close menu if open
                closeMenuFunc();
                return;
            }
            throw new Error("Failed to play in VLC.");
        })
        .catch(error => {
            console.error("Error sending file to VLC:", error);
            showNotification("Error sending file to VLC.", true);
        });
}

// function playInVLC(filePath) {
//     fetch(`/vlc_play?file=${encodeURIComponent(filePath)}`)
//         .then(response => {
//             if (!response.ok) {
//                 throw new Error("Server returned an error"); // Force the catch block to handle this
//             }
//             return response.json();
//         })
//         .then(data => {
//             if (data.status === "success") {
//                 showNotification(`Now playing: ${filePath}`);

//                 // Automatically switch back to VLC Controls
//                 document.getElementById("vlcSection").style.display = "block";
//                 document.getElementById("browserSection").style.display = "none";

//                 // Close the menu if it's open
//                 closeMenuFunc();

//                 return; // ✅ Prevents the error message from appearing
//             }
//             throw new Error("Failed to play in VLC."); // ✅ Ensures error handling works properly
//         })
//         .catch(error => {
//             console.error("Error sending file to VLC:", error);
//             showNotification("Error sending file to VLC.", true);
//         });
// }


// Load initial media list
document.addEventListener("DOMContentLoaded", () => fetchMedia());
