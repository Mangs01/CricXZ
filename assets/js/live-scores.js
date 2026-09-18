document.addEventListener("DOMContentLoaded", function () {

    "use strict";

    const filterButtons = document.querySelectorAll(".score-tab");
    const matchesContainer = document.querySelector(".live-matches .container");
    const refreshButton = document.querySelector("#refreshScores");
    const updatedElement = document.querySelector("#scoresUpdatedAt");

    if (!matchesContainer) {
        return;
    }

    // =========================================================
    // CRICXZ LIVE SCORE CONFIG
    // =========================================================

    // The public API Gateway endpoint is inserted locally during deployment.
    // The CricketData API key remains private inside AWS Lambda.
    const USE_MOCK_DATA = false;
    const API_URL = "https://pgrwcoj8f3.execute-api.ap-south-1.amazonaws.com/scores";
    const REQUEST_TIMEOUT_MS = 10000;
    const AUTO_REFRESH_MS = 300000;


    // =========================================================
    // MOCK API DATA
    // Mirrors the useful structure returned by CricketData API.
    // No real API key is used here.
    // =========================================================

    const mockMatches = [
        {
            id: "india-pakistan-women-asia-cup-2026",
            name: "India Women vs Pakistan Women, Women's Asia Cup 2026",
            matchType: "t20",
            status: "India Women need 57 runs to win",
            matchStarted: true,
            matchEnded: false,
            teams: [
                "Pakistan Women",
                "India Women"
            ],
            score: [
                {
                    r: 56,
                    w: 10,
                    o: 19.1,
                    inning: "Pakistan Women Inning 1"
                }
            ]
        },

        {
            id: "england-australia-test-demo",
            name: "England vs Australia",
            matchType: "test",
            status: "Match starts tomorrow",
            matchStarted: false,
            matchEnded: false,
            teams: [
                "England",
                "Australia"
            ],
            score: []
        },

        {
            id: "south-africa-new-zealand-demo",
            name: "South Africa vs New Zealand",
            matchType: "t20",
            status: "South Africa won by 5 wickets",
            matchStarted: true,
            matchEnded: true,
            teams: [
                "South Africa",
                "New Zealand"
            ],
            score: [
                {
                    r: 168,
                    w: 6,
                    o: 20,
                    inning: "New Zealand Inning 1"
                },
                {
                    r: 169,
                    w: 5,
                    o: 18.4,
                    inning: "South Africa Inning 1"
                }
            ]
        }
    ];


    // =========================================================
    // LOAD MATCHES
    // =========================================================

    async function loadMatches() {

        if (refreshButton) {
            refreshButton.disabled = true;
            refreshButton.textContent = "Refreshing...";
        }

        try {

            showLoading();

            let matches;
            let cachedAt = null;

            if (USE_MOCK_DATA) {

                matches = mockMatches;

            } else {

                if (!/^https:\/\//i.test(API_URL)) {
                    throw new Error("A valid HTTPS live-score API URL is not configured.");
                }

                const controller = new AbortController();
                const timeout = window.setTimeout(function () {
                    controller.abort();
                }, REQUEST_TIMEOUT_MS);

                let response;

                try {
                    response = await fetch(API_URL, {
                        method: "GET",
                        headers: {
                            "Accept": "application/json"
                        },
                        signal: controller.signal,
                        cache: "no-store"
                    });
                } finally {
                    window.clearTimeout(timeout);
                }

                if (!response.ok) {
                    throw new Error(
                        `Live score request failed: ${response.status}`
                    );
                }

                const rawResult = await response.json();
                const result = typeof rawResult.body === "string"
                    ? JSON.parse(rawResult.body)
                    : rawResult;

                // Our future Lambda endpoint should return:
                // { data: [...] }
                matches = Array.isArray(result.data)
                    ? result.data
                    : [];

                cachedAt = result.meta && result.meta.cachedAt
                    ? result.meta.cachedAt
                    : null;

            }

            renderMatches(matches);
            updateTimestamp(cachedAt);

        } catch (error) {

            console.error("CRICXZ Live Score Error:", error);

            showError();

        } finally {

            if (refreshButton) {
                refreshButton.disabled = false;
                refreshButton.textContent = "Refresh Scores";
            }

        }

    }


    // =========================================================
    // LAST UPDATED TIME
    // =========================================================

    function updateTimestamp(cachedAt) {

        if (!updatedElement) {
            return;
        }

        const cachedDate = cachedAt ? new Date(cachedAt) : new Date();
        const displayDate = Number.isNaN(cachedDate.getTime())
            ? new Date()
            : cachedDate;

        const time = new Intl.DateTimeFormat("en-IN", {
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit"
        }).format(displayDate);

        updatedElement.textContent = USE_MOCK_DATA
            ? `Recent result data - Checked ${time}`
            : `Scores cached ${time}`;

    }


    // =========================================================
    // CLASSIFY MATCH
    // =========================================================

    function getMatchStatus(match) {

        if (match.matchEnded === true) {
            return "result";
        }

        if (match.matchStarted === true) {
            return "live";
        }

        return "upcoming";

    }


    // =========================================================
    // FORMAT MATCH TYPE
    // =========================================================

    function formatMatchType(matchType) {

        if (!matchType) {
            return "CRICKET";
        }

        const type = String(matchType).toLowerCase();

        const formats = {
            t20: "T20",
            t20i: "T20I",
            odi: "ODI",
            test: "TEST"
        };

        return formats[type] || String(matchType).toUpperCase();

    }


    // =========================================================
    // FIND SCORE FOR TEAM
    // =========================================================

    function getTeamScore(match, teamName) {

        if (!Array.isArray(match.score)) {
            return null;
        }

        const normalizedTeam = normalizeText(teamName);

        const innings = match.score.filter(function (score) {

            const inningName = normalizeText(score.inning);

            return inningName.includes(normalizedTeam);

        });

        if (innings.length === 0) {
            return null;
        }

        // For the prototype show the latest innings belonging to
        // this team.
        return innings[innings.length - 1];

    }


    // =========================================================
    // NORMALIZE TEXT
    // =========================================================

    function normalizeText(value) {

        return String(value || "")
            .toLowerCase()
            .replace(/\s+/g, " ")
            .trim();

    }


    // =========================================================
    // SCORE TEXT
    // =========================================================

    function formatScore(score) {

        if (!score) {
            return "—";
        }

        const runs = score.r ?? 0;
        const wickets = score.w ?? 0;

        return `${runs}/${wickets}`;

    }


    function formatOvers(score) {

        if (!score || score.o === undefined || score.o === null) {
            return "";
        }

        return `${score.o} Overs`;

    }


    // =========================================================
    // TEAM FLAG
    // =========================================================

    function getTeamFlag(teamName) {

        const name = normalizeText(teamName);

        const flags = {
            "india": "🇮🇳",
            "india women": "🇮🇳",
            "pakistan": "🇵🇰",
            "pakistan women": "🇵🇰",
            "australia": "🇦🇺",
            "australia women": "🇦🇺",
            "england": "🏴",
            "england women": "🏴",
            "south africa": "🇿🇦",
            "south africa women": "🇿🇦",
            "new zealand": "🇳🇿",
            "new zealand women": "🇳🇿",
            "sri lanka": "🇱🇰",
            "sri lanka women": "🇱🇰",
            "bangladesh": "🇧🇩",
            "bangladesh women": "🇧🇩",
            "afghanistan": "🇦🇫",
            "west indies": "🌴",
            "ireland": "🇮🇪",
            "zimbabwe": "🇿🇼",
            "japan": "🇯🇵",
            "japan women": "🇯🇵"
        };

        return flags[name] || "🏏";

    }


    // =========================================================
    // STATUS LABEL
    // =========================================================

    function getStatusLabel(status) {

        if (status === "live") {
            return "● LIVE";
        }

        if (status === "result") {
            return "RESULT";
        }

        return "UPCOMING";

    }


    // =========================================================
    // CREATE TEAM HTML
    // =========================================================

    function createTeamHtml(teamName, score) {

        const safeTeamName = escapeHtml(teamName);
        const flag = getTeamFlag(teamName);

        const overs = formatOvers(score);

        return `
            <div class="team">

                <div class="team-name">
                    ${flag} ${safeTeamName}
                </div>

                <div class="team-score">
                    ${formatScore(score)}
                </div>

                ${
                    overs
                        ? `<div class="overs">${escapeHtml(overs)}</div>`
                        : ""
                }

            </div>
        `;

    }


    // =========================================================
    // CREATE MATCH CARD
    // =========================================================

    function createMatchCard(match) {

        const status = getMatchStatus(match);

        const teams = Array.isArray(match.teams)
            ? match.teams.slice(0, 2)
            : [];

        const teamOne = teams[0] || "Team 1";
        const teamTwo = teams[1] || "Team 2";

        const teamOneScore = getTeamScore(match, teamOne);
        const teamTwoScore = getTeamScore(match, teamTwo);

        const matchMessage =
            match.status || "Match information unavailable";

        return `
            <div
                class="score-card ${status}-card"
                data-status="${status}"
                data-match-id="${escapeHtml(match.id || "")}"
            >

                <div class="score-card-top">

                    <span class="match-status ${status}">
                        ${getStatusLabel(status)}
                    </span>

                    <span class="match-format">
                        ${escapeHtml(formatMatchType(match.matchType))}
                    </span>

                </div>

                <div class="teams">

                    ${createTeamHtml(teamOne, teamOneScore)}

                    <div class="vs">
                        VS
                    </div>

                    ${createTeamHtml(teamTwo, teamTwoScore)}

                </div>

                <div class="match-message">
                    ${escapeHtml(matchMessage)}
                </div>

            </div>
        `;

    }


    // =========================================================
    // CREATE MATCH GROUP
    // =========================================================

    function createMatchGroup(status, matches) {

        if (matches.length === 0) {
            return "";
        }

        const headings = {
            live: "🔴 Live Matches",
            upcoming: "📅 Upcoming Matches",
            result: "🏆 Latest Results"
        };

        const cards = matches
            .map(createMatchCard)
            .join("");

        return `
            <div class="match-group" data-status="${status}">

                <h2 class="section-title">
                    ${headings[status]}
                </h2>

                ${cards}

            </div>
        `;

    }


    // =========================================================
    // RENDER MATCHES
    // =========================================================

    function renderMatches(matches) {

        if (!Array.isArray(matches) || matches.length === 0) {

            matchesContainer.innerHTML = `
                <div class="score-state-message">
                    No cricket matches are available right now.
                </div>
            `;

            return;

        }

        const groupedMatches = {
            live: [],
            upcoming: [],
            result: []
        };

        matches.forEach(function (match) {

            const status = getMatchStatus(match);

            groupedMatches[status].push(match);

        });

        matchesContainer.innerHTML =
            createMatchGroup("live", groupedMatches.live) +
            createMatchGroup("upcoming", groupedMatches.upcoming) +
            createMatchGroup("result", groupedMatches.result);

        applyCurrentFilter();

    }


    // =========================================================
    // LOADING / ERROR STATES
    // =========================================================

    function showLoading() {

        matchesContainer.innerHTML = `
            <div class="score-state-message">
                Loading cricket scores...
            </div>
        `;

    }


    function showError() {

        matchesContainer.innerHTML = `
            <div class="score-state-message">
                Live scores are temporarily unavailable.
                Please try again shortly.
            </div>
        `;

    }


    // =========================================================
    // FILTERING
    // =========================================================

    function getActiveFilter() {

        const activeButton =
            document.querySelector(".score-tab.active");

        return activeButton
            ? activeButton.dataset.filter
            : "all";

    }


    function applyCurrentFilter() {

        const filter = getActiveFilter();

        const matchGroups =
            document.querySelectorAll(".match-group");

        matchGroups.forEach(function (group) {

            const status = group.dataset.status;

            group.hidden =
                filter !== "all" &&
                status !== filter;

        });

    }


    filterButtons.forEach(function (button) {

        button.setAttribute(
            "aria-pressed",
            button.classList.contains("active") ? "true" : "false"
        );

        button.addEventListener("click", function () {

            filterButtons.forEach(function (btn) {
                btn.classList.remove("active");
                btn.setAttribute("aria-pressed", "false");
            });

            button.classList.add("active");
            button.setAttribute("aria-pressed", "true");

            applyCurrentFilter();

        });

    });


    // =========================================================
    // SECURITY
    // =========================================================

    function escapeHtml(value) {

        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");

    }


    // =========================================================
    // START
    // =========================================================

    if (refreshButton) {
        refreshButton.addEventListener("click", loadMatches);
    }

    loadMatches();

    if (!USE_MOCK_DATA) {
        window.setInterval(loadMatches, AUTO_REFRESH_MS);
    }

});
