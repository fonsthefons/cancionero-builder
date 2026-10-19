// Search songs by number, title, author or lyrics. Wires up every `.search` box:
//   - default (top bar): results are links that jump to the song;
//   - data-search="<action>" (e.g. the session box): results are buttons that
//     run that action with data-song="<song id>", and the box stays ready for
//     the next search.
// The index is built from the page itself, so song text is not duplicated.
//
// Matching ignores accents, capitals and punctuation, and finds songs that
// contain every word typed, in any order ("padre abba" finds Abba Padre).
// Words may be cut short ("alab" finds alabaré). Best matches come first:
// song number, then title, author, the exact phrase in the lyrics, and last
// the words scattered through the lyrics. A lyric match shows the line it
// was found in under the title.

const MAX_SEARCH_RESULTS = 50;

// Lower case, no accents, punctuation as spaces, single spaces.
function searchText(text) {
    return normalizeText(text).replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

const searchIndex = [...document.querySelectorAll(".song")].map((song) => {
    // Lyric lines only: chord lines would add noise ("am", "do"...). A lyric
    // under a chord line is its .line-pair's own text.
    const lines = [...song.querySelectorAll(".lyric-line, .line-pair")]
        .map((line) => (line.matches(".lyric-line")
            ? line.textContent
            : [...line.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE).map((node) => node.data).join("")
        ).trim())
        .filter(Boolean);
    const lineText = lines.map(searchText);
    return {
        id: song.id,
        label: song.querySelector("h3").textContent,
        number: song.querySelector("h3").textContent.match(/^\d+/)?.[0],
        title: searchText(song.dataset.title),
        autor: searchText(song.dataset.autor || ""),
        lyrics: " " + lineText.join(" ") + " ",
        lines,
        lineText,
    };
});

function hasAll(text, words) {
    return words.every((word) => text.includes(word));
}

// Rank of a song for the query (lower is better), or null if it doesn't match.
function searchRank(song, phrase, words) {
    if (/^\d+$/.test(phrase)) return song.number === phrase ? 0 : null;
    if (song.title.startsWith(phrase)) return 1;
    if (hasAll(song.title, words)) return 2;
    if (hasAll(song.autor, words)) return 3;
    if (song.lyrics.includes(" " + phrase)) return 4;
    if (hasAll(song.title + " " + song.autor + song.lyrics, words)) return 5;
    return null;
}

// The lyric line to show under a result: the phrase, else the first word.
function searchSnippet(song, phrase, words) {
    const i = song.lineText.findIndex((line) => (" " + line).includes(" " + phrase));
    const j = i >= 0 ? i : song.lineText.findIndex((line) => line.includes(words[0]));
    return j >= 0 ? song.lines[j] : "";
}

function searchSongs(query) {
    const phrase = searchText(query);
    if (!phrase) return [];
    const words = phrase.split(" ");
    return searchIndex
        .map((song, order) => ({ song, order, rank: searchRank(song, phrase, words) }))
        .filter((hit) => hit.rank !== null)
        .sort((a, b) => a.rank - b.rank || a.order - b.order)
        .map(({ song, rank }) => ({ song, snippet: rank >= 4 ? searchSnippet(song, phrase, words) : "" }));
}

function searchResultElement({ song, snippet }, action) {
    const item = document.createElement(action ? "button" : "a");
    item.className = "search-result";
    item.textContent = song.label;
    if (snippet) {
        const line = document.createElement("span");
        line.className = "search-snippet";
        line.textContent = snippet;
        item.append(line);
    }
    if (action) {
        item.dataset.action = action;
        item.dataset.song = song.id;
    } else {
        item.href = "#" + song.id;
    }
    return item;
}

document.querySelectorAll(".search").forEach((box) => {
    const input = box.querySelector("input");
    const results = box.querySelector(".search-results");
    const action = box.dataset.search; // undefined for plain "jump to song"

    function close() {
        results.hidden = true;
    }

    function update() {
        const query = input.value.trim();
        if (!query) return close();
        const found = searchSongs(query).slice(0, MAX_SEARCH_RESULTS);
        results.replaceChildren(...(found.length
            ? found.map((hit) => searchResultElement(hit, action))
            : [Object.assign(document.createElement("div"), {
                className: "search-empty",
                textContent: "No songs found",
            })]));
        results.scrollTop = 0;
        results.hidden = false;
    }

    input.addEventListener("input", update);
    input.addEventListener("focus", update);
    input.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            event.stopPropagation(); // clear the search, don't close the menu
            input.value = "";
            close();
            input.blur();
        }
    });

    // Picking a result: clear the box. Jumping also puts the keyboard away;
    // adding keeps focus so the next song can be typed straight away.
    results.addEventListener("click", (event) => {
        if (!event.target.closest(".search-result")) return;
        input.value = "";
        close();
        if (action) input.focus();
        else input.blur();
    });

    document.addEventListener("click", (event) => {
        if (!box.contains(event.target)) close();
    });
});
