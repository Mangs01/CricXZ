document.addEventListener("DOMContentLoaded", function () {

    "use strict";

    const filterButtons = document.querySelectorAll(".score-tab");
    const matchesContainer = document.querySelector(".live-matches .container");
    const refreshButton = document.querySelector("#refreshScores");
    const updatedElement = document.querySelector("#scoresUpdatedAt");
    const checkedElement = document.querySelector("#scoresCheckedAt");
    let isLoading = false;

    if (!matchesContainer) {
        return;
    }

    // =========================================================
    // CRICXZ LIVE SCORE CONFIG
    // =========================================================

    const USE_MOCK_DATA = false;
    const API_URL = "https://pgrwcoj8f3.execute-api.ap-south-1.amazonaws.com/scores";
    const REQUEST_TIMEOUT_MS = 10000;
    
    // REFRESH TIME UPDATED: 60000 ms (1 Minute) pehle ye 300000 (5 Min) tha
    const AUTO_REFRESH_MS = 60000;


    // =========================================================
    // MOCK API DATA
    // =========================================================

    const mockMatches = [
        {
            id: "india-pakistan-women-asia-cup-2026",
            name: "India Women vs Pakistan Women, Women's Asia Cup 2026",
            matchType: "t20",
            status: "India Women need 57 runs to win",
            matchStarted: true,
            matchEnded: false,
            teams: ["Pakistan Women", "India Women"],
            score: [
                { r: 56, w: 10, o: 19.1, inning: "Pakistan Women Inning 1" }
            ]
        },
        {
            id: "england-australia-test-demo",
            name: "England vs Australia",
            matchType: "test",
            status: "Match starts tomorrow",
            matchStarted: false,
            matchEnded: false,
            teams: ["England", "Australia"],
            score: []
        },
        {
            id: "south-africa-new-zealand-demo",
            name: "South Africa vs New Zealand",
            matchType: "t20",
            status: "South Africa won by 5 wickets",
            matchStarted: true,
            matchEnded: true,
            teams: ["South Africa", "New Zealand"],
            score: [
                { r: 168, w: 6, o: 20, inning: "New Zealand Inning 1" },
                { r: 169, w: 5, o: 18.4, inning: "South Africa Inning 1" }
            ]
        }
    ];


    // =========================================================
    // LOAD MATCHES
    // =========================================================

    async function loadMatches() {
        if (isLoading) { return; }
        isLoading = true;

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
                        headers: { "Accept": "application/json" },
                        signal: controller.signal,
                        cache: "no-store"
                    });
                } finally {
                    window.clearTimeout(timeout);
                }

                if (!response.ok) {
                    throw new Error(`Live score request failed: ${response.status}`);
                }

                const rawResult = await response.json();
                const result = rawResult && typeof rawResult.body === "string"
                    ? JSON.parse(rawResult.body)
                    : rawResult;
                if (!result || typeof result !== "object" || Array.isArray(result)
                    || (result.status !== undefined && result.status !== "success")
                    || !Array.isArray(result.data)) {
                    throw new Error("Invalid live-score response.");
                }
                if (!result.data.every(function (match) {
                    return match && typeof match === "object" && !Array.isArray(match)
                        && Array.isArray(match.teams) && match.teams.length >= 2
                        && match.teams.slice(0, 2).every(function (team) {
                            return typeof team === "string" && team.trim().length > 0;
                        });
                })) {
                    throw new Error("Invalid match data.");
                }
                matches = result.data;
                cachedAt = result.meta && result.meta.cachedAt ? result.meta.cachedAt : null;
            }

            renderMatches(prepareMatches(matches));
            updateTimestamp(cachedAt);

        } catch (error) {
            console.error("CRICXZ Live Score Error:", error);
            showError();
        } finally {
            updateCheckedTime();
            isLoading = false;
            if (refreshButton) {
                refreshButton.disabled = false;
                refreshButton.textContent = "Refresh Scores";
            }
        }

    }


    // Cache creation and browser checks are different from scoring events.
    function formatTimestamp(date) {
        return new Intl.DateTimeFormat("en-IN", {
            day: "2-digit", month: "short", year: "numeric",
            hour: "numeric", minute: "2-digit", second: "2-digit",
            timeZoneName: "short"
        }).format(date);
    }

    function updateTimestamp(cachedAt) {
        if (!updatedElement) { return; }
        const date = typeof cachedAt === "string" && /^\d{4}-\d{2}-\d{2}T/.test(cachedAt)
            ? new Date(cachedAt) : null;
        if (date && Number.isFinite(date.getTime()) && date.getTime() <= Date.now() + 60000) {
            updatedElement.textContent = `Data cached: ${formatTimestamp(date)}`;
        } else {
            updatedElement.textContent = "Data cache time unavailable";
        }
    }

    function updateCheckedTime() {
        if (checkedElement) {
            checkedElement.textContent = `Last checked: ${formatTimestamp(new Date())}`;
        }
    }

    // =========================================================
    // CLASSIFY MATCH
    // =========================================================

    function getMatchStatus(match) {
        if (match.matchEnded === true) { return "result"; }
        if (match.matchStarted === true) { return "live"; }
        return "upcoming";
    }


    // =========================================================
    // FORMAT MATCH TYPE
    // =========================================================

    function formatMatchType(matchType) {
        if (!matchType) { return "CRICKET"; }
        const type = String(matchType).toLowerCase();
        const formats = { t10: "T10", t20: "T20", t20i: "T20I", odi: "ODI", test: "TEST" };
        return formats[type] || String(matchType).toUpperCase();
    }


    // =========================================================
    // FIND SCORE FOR TEAM
    // =========================================================

    function getTeamScore(match, teamName) {
        if (!Array.isArray(match.score)) { return null; }
        const normalizedTeam = normalizeText(teamName);
        const innings = match.score.filter(function (score) {
            if (!score || typeof score !== "object") { return false; }
            // Require a single exact team label; combined labels are ambiguous.
            const label = normalizeText(score.inning).replace(/\s+innings?\s*\d*\s*$/i, "").trim();
            return label === normalizedTeam;
        });
        return innings.length ? innings[innings.length - 1] : null;
    }

    function prepareMatches(matches) {
        const seen = new Set();
        return matches.filter(function (match) {
            const id = typeof match.id === "string" ? match.id.trim() : "";
            if (!id) { return true; }
            if (seen.has(id)) { return false; }
            seen.add(id);
            return true;
        }).sort(function (a, b) {
            const first = getMatchTime(a);
            const second = getMatchTime(b);
            if (first === null) { return second === null ? 0 : 1; }
            if (second === null) { return -1; }
            return getMatchStatus(a) === "upcoming" && getMatchStatus(b) === "upcoming"
                ? first - second : second - first;
        });
    }

    function getMatchTime(match) {
        const value = match.dateTimeGMT || match.date;
        if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}(?:T|$)/.test(value)) { return null; }
        const timestamp = Date.parse(/T/.test(value) && !/(Z|[+-]\d{2}:?\d{2})$/i.test(value)
            ? value + "Z" : value);
        return Number.isFinite(timestamp) ? timestamp : null;
    }

    function getMatchDateLabel(match) {
        const timestamp = getMatchTime(match);
        if (timestamp === null) { return "Match date unavailable"; }
        const options = { day: "2-digit", month: "short", year: "numeric" };
        if (match.dateTimeGMT) {
            options.hour = "numeric";
            options.minute = "2-digit";
            options.timeZoneName = "short";
        } else {
            options.timeZone = "UTC";
        }
        return new Intl.DateTimeFormat("en-IN", options).format(new Date(timestamp));
    }

    // =========================================================
    // NORMALIZE TEXT
    // =========================================================

    function normalizeText(value) {
        return String(value || "").toLowerCase().replace(/\s+/g, " ").trim();
    }


    // =========================================================
    // SCORE TEXT
    // =========================================================

    function formatScore(score) {
        if (!score) { return "—"; }
        const runs = score.r ?? 0;
        const wickets = score.w ?? 0;
        return `${runs}/${wickets}`;
    }

    function formatOvers(score) {
        if (!score || score.o === undefined || score.o === null) { return ""; }
        return `${score.o} Overs`;
    }


    // =========================================================
    // TEAM FLAG
    // =========================================================

    function getTeamFlag(teamName) {
        const name = normalizeText(teamName);
        const flags = {
            "india": "🇮🇳", "india women": "🇮🇳",
            "pakistan": "🇵🇰", "pakistan women": "🇵🇰",
            "australia": "🇦🇺", "australia women": "🇦🇺",
            "england": "🏴", "england women": "🏴",
            "south africa": "🇿🇦", "south africa women": "🇿🇦",
            "new zealand": "🇳🇿", "new zealand women": "🇳🇿",
            "sri lanka": "🇱🇰", "sri lanka women": "🇱🇰",
            "bangladesh": "🇧🇩", "bangladesh women": "🇧🇩",
            "afghanistan": "🇦🇫",
            "west indies": "🌴",
            "ireland": "🇮🇪",
            "zimbabwe": "🇿🇼",
            "japan": "🇯🇵", "japan women": "🇯🇵"
        };
        return flags[name] || "🏏";
    }


    // =========================================================
    // STATUS LABEL
    // =========================================================

    function getStatusLabel(status) {
        if (status === "live") { return "● LIVE"; }
        if (status === "result") { return "RESULT"; }
        return "UPCOMING";
    }


    // =========================================================
    // CREATE TEAM HTML
    // =========================================================

    function createTeamHtml(teamName, score, hasScores) {
        const safeTeamName = escapeHtml(teamName);
        const flag = getTeamFlag(teamName);
        const overs = formatOvers(score);

        return `
            <div class="team">
                <div class="team-name">${flag} ${safeTeamName}</div>
                <div class="team-score">${score ? escapeHtml(formatScore(score)) : (hasScores ? "Score unavailable" : "—")}</div>
                ${overs ? `<div class="overs">${escapeHtml(overs)}</div>` : ""}
            </div>
        `;
    }


    // =========================================================
    // CREATE MATCH CARD
    // =========================================================

    function createMatchCard(match) {
        const status = getMatchStatus(match);
        const teams = Array.isArray(match.teams) ? match.teams.slice(0, 2) : [];
        const teamOne = teams[0] || "Team 1";
        const teamTwo = teams[1] || "Team 2";
        const teamOneScore = getTeamScore(match, teamOne);
        const teamTwoScore = getTeamScore(match, teamTwo);
        const matchMessage = match.status || "Match information unavailable";

        return `
            <div class="score-card ${status}-card" data-status="${status}" data-match-id="${escapeHtml(match.id || "")}">
                <div class="score-card-top">
                    <span class="match-status ${status}">${getStatusLabel(status)}</span>
                    <span class="match-format">${escapeHtml(formatMatchType(match.matchType))}</span>
                </div>
                <p class="match-message"><strong>${escapeHtml(match.name || teams.join(" vs "))}</strong><br>${escapeHtml(getMatchDateLabel(match))}</p>
                <div class="teams">
                    ${createTeamHtml(teamOne, teamOneScore, Array.isArray(match.score) && match.score.length > 0)}
                    <div class="vs">VS</div>
                    ${createTeamHtml(teamTwo, teamTwoScore, Array.isArray(match.score) && match.score.length > 0)}
                </div>
                <div class="match-message">${escapeHtml(matchMessage)}</div>
                ${Array.isArray(match.score) && match.score.length > 0 && (!teamOneScore || !teamTwoScore) ? `<p class="match-message">Some innings could not be assigned reliably to a team. Unavailable scores are not assumed to be zero.</p>` : ""}
            </div>
        `;
    }


    // =========================================================
    // CREATE MATCH GROUP
    // =========================================================

    function createMatchGroup(status, matches) {
        if (matches.length === 0) { return ""; }
        const headings = {
            live: "🔴 Live Matches",
            upcoming: "📅 Upcoming Matches",
            result: "🏆 Latest Results"
        };
        const cards = matches.map(createMatchCard).join("");
        return `
            <div class="match-group" data-status="${status}">
                <h2 class="section-title">${headings[status]}</h2>
                ${cards}
            </div>
        `;
    }


    // =========================================================
    // RENDER MATCHES
    // =========================================================

    function renderMatches(matches) {
        setBusy(false);
        if (!Array.isArray(matches) || matches.length === 0) {
            matchesContainer.innerHTML = `
                <div class="score-state-message">No cricket matches are available right now.</div>
            `;
            return;
        }

        const groupedMatches = { live: [], upcoming: [], result: [] };

        matches.forEach(function (match) {
            const status = getMatchStatus(match);
            groupedMatches[status].push(match);
        });

        matchesContainer.innerHTML =
            createMatchGroup("live", groupedMatches.live) +
            createMatchGroup("upcoming", groupedMatches.upcoming) +
            createMatchGroup("result", groupedMatches.result) +
            `<div class="score-state-message" id="scoreFilterEmpty" role="status" hidden></div>`;

        applyCurrentFilter();
    }


    // =========================================================
    // LOADING / ERROR STATES
    // =========================================================

    function showLoading() {
        setBusy(true);
        matchesContainer.innerHTML = `
            <div class="score-state-message">Loading cricket scores...</div>
        `;
    }

    function showError() {
        setBusy(false);
        if (updatedElement) {
            updatedElement.textContent = "Score data temporarily unavailable";
        }
        matchesContainer.innerHTML = `
            <div class="score-state-message">Score data could not be loaded or verified. Please retry, or read our match reports below.</div>
        `;
    }

    function setBusy(isBusy) {
        matchesContainer.setAttribute("aria-busy", isBusy ? "true" : "false");
    }


    // =========================================================
    // FILTERING
    // =========================================================

    function getActiveFilter() {
        const activeButton = document.querySelector(".score-tab.active");
        return activeButton ? activeButton.dataset.filter : "all";
    }

    function applyCurrentFilter() {
        const filter = getActiveFilter();
        const matchGroups = document.querySelectorAll(".match-group");
        let visibleCount = 0;
        matchGroups.forEach(function (group) {
            const status = group.dataset.status;
            group.hidden = filter !== "all" && status !== filter;
            if (!group.hidden) { visibleCount += 1; }
        });
        const empty = document.querySelector("#scoreFilterEmpty");
        if (empty) {
            const labels = { live: "live matches", upcoming: "upcoming fixtures", result: "completed results", all: "matches" };
            empty.textContent = `No ${labels[filter] || "matches"} available in the current feed.`;
            empty.hidden = visibleCount > 0;
        }
    }

    filterButtons.forEach(function (button) {
        button.setAttribute("aria-pressed", button.classList.contains("active") ? "true" : "false");
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
