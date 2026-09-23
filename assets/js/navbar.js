// =========================================================
// CRICXZ MOBILE NAVBAR
// =========================================================

document.addEventListener("DOMContentLoaded", function () {

    const menuToggle = document.getElementById("menuToggle");
    const mainMenu = document.getElementById("mainMenu");

    // Keep the legal and editorial pages reachable from every published page.
    // Existing pages share this script, so one accessible footer block avoids
    // duplicating navigation maintenance across the static site.
    const footerBottom = document.querySelector(".footer-bottom");

    if (
        footerBottom &&
        !document.body.classList.contains("legal-page") &&
        !footerBottom.querySelector(".footer-legal-links")
    ) {
        const isNestedPage = /\/(pages|articles)\//.test(window.location.pathname);
        const pagesPath = isNestedPage ? "../pages/" : "pages/";
        const legalLinks = document.createElement("nav");

        legalLinks.className = "footer-legal-links";
        legalLinks.setAttribute("aria-label", "Legal and editorial information");
        legalLinks.innerHTML =
            '<a href="' + pagesPath + 'privacy-policy.html">Privacy Policy</a>' +
            '<a href="' + pagesPath + 'terms.html">Terms &amp; Conditions</a>' +
            '<a href="' + pagesPath + 'editorial-policy.html">Editorial Policy</a>' +
            '<a href="' + pagesPath + 'disclaimer.html">Disclaimer</a>';

        footerBottom.prepend(legalLinks);
    }

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
