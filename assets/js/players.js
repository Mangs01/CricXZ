// =========================================
// CRICXZ - PLAYERS PAGE SEARCH
// =========================================

document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("playerSearch");
    const searchButton = document.getElementById("playerSearchBtn");
    const playersGrid = document.querySelector(".players-grid");
    const players = document.querySelectorAll(".player-card");

    // Required elements check
    if (!searchInput || !playersGrid || !players.length) {
        return;
    }

    // =========================================
    // FILTER PLAYERS
    // =========================================

    function filterPlayers() {

        const searchValue = searchInput.value
            .toLowerCase()
            .trim();

        let visiblePlayers = 0;

        players.forEach(function (player) {

            const playerName =
                player.querySelector("h3")?.textContent
                .toLowerCase()
                .trim() || "";

            const isMatch =
                searchValue === "" ||
                playerName.includes(searchValue);

            if (isMatch) {

                player.style.display = "";

                visiblePlayers++;

            } else {

                player.style.display = "none";

            }

        });

        // Center card when only one player is found
        playersGrid.classList.toggle(
            "single-result",
            visiblePlayers === 1
        );
    }

    // =========================================
    // LIVE SEARCH
    // =========================================

    searchInput.addEventListener("input", filterPlayers);

    // =========================================
    // SEARCH BUTTON
    // =========================================

    if (searchButton) {

        searchButton.addEventListener("click", filterPlayers);

    }

    // =========================================
    // ENTER KEY SEARCH
    // =========================================

    searchInput.addEventListener("keydown", function (event) {

        if (event.key === "Enter") {

            event.preventDefault();

            filterPlayers();

        }

    });

});