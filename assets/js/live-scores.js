document.addEventListener("DOMContentLoaded", function () {

    const filterButtons = document.querySelectorAll(".score-tab");
    const matchGroups = document.querySelectorAll(".match-group");


    filterButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            const filter = button.dataset.filter;


            // =========================
            // ACTIVE FILTER BUTTON
            // =========================

            filterButtons.forEach(function (btn) {
                btn.classList.remove("active");
            });

            button.classList.add("active");


            // =========================
            // FILTER SCORE CARDS
            // =========================

            matchGroups.forEach(function (group) {

                const status = group.dataset.status;


                if (filter === "all" || status === filter) {

                    group.hidden = false;

                } else {

                    group.hidden = true;

                }

            });

        });

    });

});
