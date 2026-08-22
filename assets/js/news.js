// =========================================================
// CRICXZ NEWS FILTER
// =========================================================

document.addEventListener("DOMContentLoaded", function () {

    const filterButtons =
        document.querySelectorAll(".news-filter-btn");

    const newsCards =
        document.querySelectorAll(".news-card");


    if (!filterButtons.length || !newsCards.length) {
        return;
    }


    filterButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            const selectedFilter =
                button.dataset.filter;


            // Remove active class from all buttons

            filterButtons.forEach(function (btn) {
                btn.classList.remove("active");
            });


            // Active clicked button

            button.classList.add("active");


            // Filter news cards

            newsCards.forEach(function (card) {

                const categories =
                    card.dataset.category
                        ?.toLowerCase()
                        .split(" ") || [];


                if (
                    selectedFilter === "all" ||
                    categories.includes(selectedFilter)
                ) {

                    card.style.display = "block";

                } else {

                    card.style.display = "none";

                }

            });

        });

    });

});