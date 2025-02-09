document.addEventListener("DOMContentLoaded", function () {
    const menuButton = document.getElementById("menuButton");
    const sidebar = document.getElementById("sidebar");
    const closeMenu = document.getElementById("closeMenu");

    // ✅ Ensure overlay is created only once and reused
    let overlay = document.querySelector(".overlay");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.classList.add("overlay");
        document.body.appendChild(overlay);
    }

    function openMenu() {
        console.log("🔵 Menu Opened");
        sidebar.classList.add("open");
        document.body.classList.add("menu-active");
        overlay.classList.add("visible");
    }

    function closeMenuFunc() {
        console.log("🔴 Menu Closed");

        sidebar.classList.remove("open");
        document.body.classList.remove("menu-active");

        // Ensure sidebar is hidden by setting styles
        // this is ugly and shouldn't be needed, but I had a persistent bug 
        // that I couldn't find: closing the menu from the X works, 
        // but clicking overlay didn't hide the menu 
        sidebar.style.left = "-250px";
        sidebar.style.display = "none";

        overlay.classList.remove("visible");
    }

    menuButton.addEventListener("click", function (event) {
        console.log("📌 Clicked menu button");
        event.stopPropagation();
        openMenu();
    });

    closeMenu.addEventListener("click", function (event) {
        console.log("📌 Clicked close button");
        event.stopPropagation();
        closeMenuFunc();
    });

    overlay.addEventListener("click", function (event) {
        console.log("📌 Clicked overlay");
        event.stopPropagation();
        closeMenuFunc();
    });

    // Close menu when clicking a sidebar link
    const sidebarLinks = sidebar.querySelectorAll("a");
    sidebarLinks.forEach(link => {
        link.addEventListener("click", function () {
            console.log(`📌 Clicked sidebar link: ${this.textContent}`);
            closeMenuFunc();
        });
    });

    // Expose `closeMenuFunc()` globally so other scripts can call it
    window.closeMenuFunc = closeMenuFunc;
});
