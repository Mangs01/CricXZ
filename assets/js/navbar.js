// =========================================================
// CRICXZ MOBILE NAVBAR
// =========================================================

document.addEventListener("DOMContentLoaded", function () {

    const menuToggle = document.getElementById("menuToggle");
    const mainMenu = document.getElementById("mainMenu");

    if (!menuToggle || !mainMenu) {
        return;
    }


    // -----------------------------------------------------
    // OPEN / CLOSE MOBILE MENU
    // -----------------------------------------------------

    menuToggle.addEventListener("click", function () {

        mainMenu.classList.toggle("active");

        const isOpen = mainMenu.classList.contains("active");

        menuToggle.setAttribute(
            "aria-expanded",
            isOpen ? "true" : "false"
        );

    });


    // -----------------------------------------------------
    // CLOSE MENU AFTER CLICKING A LINK
    // -----------------------------------------------------

    const menuLinks = mainMenu.querySelectorAll("a");

    menuLinks.forEach(function (link) {

        link.addEventListener("click", function () {

            mainMenu.classList.remove("active");

            menuToggle.setAttribute(
                "aria-expanded",
                "false"
            );

        });

    });


    // -----------------------------------------------------
    // CLOSE MENU WHEN WINDOW RETURNS TO DESKTOP
    // -----------------------------------------------------

    window.addEventListener("resize", function () {

        if (window.innerWidth > 768) {

            mainMenu.classList.remove("active");

            menuToggle.setAttribute(
                "aria-expanded",
                "false"
            );

        }

    });

});