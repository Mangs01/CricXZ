// ===============================
// Search Suggestions
// ===============================

// ===============================
// CricXZ Base Path
// ===============================

const isInsidePages = window.location.pathname.includes("/pages/");
const isInsideArticles = window.location.pathname.includes("/articles/");

function getSearchUrl(url) {

    if (isInsidePages || isInsideArticles) {
        return "../" + url;
    }

    return url;
}

const searchInput = document.getElementById("searchInput");
const suggestions = document.getElementById("searchSuggestions");

let selectedIndex = -1;
let currentResults = [];

if(searchInput){

searchInput.addEventListener("input", function(){

const value = this.value.toLowerCase().trim();

suggestions.innerHTML = "";

if(value === ""){

suggestions.style.display = "none";
return;

}

const results = searchData.filter(item =>
    item.title && item.title.toLowerCase().includes(value)
);

currentResults = results;
selectedIndex = -1;

if(results.length===0){

suggestions.style.display="none";
return;

}

results.forEach(item=>{

const div=document.createElement("div");

div.className="search-item";

div.textContent = item.title;

div.onclick=()=>{

window.location.href = getSearchUrl(item.url);

};

suggestions.appendChild(div);

});

suggestions.style.display="block";

});

document.addEventListener("click",function(e){

if(!e.target.closest(".search-box")){

suggestions.style.display="none";

}

});

}

// Search Button

const searchBtn = document.getElementById("searchBtn");

if (searchBtn) {

    searchBtn.addEventListener("click", searchPage);

}

function searchPage() {

    const value = searchInput.value.trim().toLowerCase();

    if (value === "") return;

    const match = searchData.find(item =>
        item.title.toLowerCase().includes(value)
    );

    if (match) {

        window.location.href = getSearchUrl(match.url);

    } else {

        alert("No results found!");

    }

}

if (searchInput) {

    searchInput.addEventListener("keydown", function(e) {

        const items = document.querySelectorAll(".search-item");

        if (items.length === 0) return;

        if (e.key === "ArrowDown") {

            e.preventDefault();

            selectedIndex++;

            if (selectedIndex >= items.length) {
                selectedIndex = 0;
            }

            items.forEach(item =>
                item.classList.remove("active")
            );

            items[selectedIndex].classList.add("active");
        }

        if (e.key === "ArrowUp") {

            e.preventDefault();

            selectedIndex--;

            if (selectedIndex < 0) {
                selectedIndex = items.length - 1;
            }

            items.forEach(item => {
                item.classList.remove("active");
            });

            items[selectedIndex].classList.add("active");

        }

        if (e.key === "Enter" && selectedIndex >= 0) {

            e.preventDefault();

            items[selectedIndex].click();

        }

    });

}

if(searchInput){

searchInput.addEventListener("keypress",function(e){

if(e.key==="Enter"){

searchPage();

}

});

}

// ===============================
// Breaking News Slider
// ===============================

const slides = document.querySelectorAll(".slide");
const nextBtn = document.querySelector(".next");
const prevBtn = document.querySelector(".prev");

if (slides.length > 0) {

    let current = 0;

    function showSlide(index) {

        slides.forEach(slide => slide.classList.remove("active"));

        slides[index].classList.add("active");

    }

    function nextSlide() {

        current++;

        if (current >= slides.length) {

            current = 0;

        }

        showSlide(current);

    }

    function prevSlide() {

        current--;

        if (current < 0) {

            current = slides.length - 1;

        }

        showSlide(current);

    }

    if (nextBtn) {

        nextBtn.addEventListener("click", nextSlide);

    }

    if (prevBtn) {

        prevBtn.addEventListener("click", prevSlide);

    }

    setInterval(nextSlide, 5000);

}

// ===============================
// Live Score Data
// ===============================

const liveMatches = [

    {
        title: "India vs Australia",
        score: "India: 245/4 (42.5)",
        status: "Australia yet to bat"
    },

    {
        title: "England vs Pakistan",
        score: "England: 156/2 (27.0)",
        status: "Pakistan bowling"
    },

    {
        title: "South Africa vs New Zealand",
        score: "South Africa: 198/5 (31.4)",
        status: "New Zealand bowling"
    }

];

// ===============================
// Live Score Display
// ===============================

const matchTitle = document.getElementById("matchTitle");
const matchScore = document.getElementById("matchScore");
const matchStatus = document.getElementById("matchStatus");
const matchUpdate = document.getElementById("matchUpdate");

if (
    matchTitle &&
    matchScore &&
    matchStatus &&
    matchUpdate &&
    liveMatches.length > 0
) {

    let currentMatch = 0;

    function showLiveMatch(index) {

        matchTitle.textContent = liveMatches[index].title;

        matchScore.textContent = liveMatches[index].score;

        matchStatus.textContent = liveMatches[index].status;

        matchUpdate.textContent = "Live Update";

    }

    showLiveMatch(currentMatch);

    setInterval(function () {

        currentMatch++;

        if (currentMatch >= liveMatches.length) {
            currentMatch = 0;
        }

        showLiveMatch(currentMatch);

    }, 5000);

}
