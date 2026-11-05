// Psalm fórmulas (book.yaml psalm_tags / formula_tag; only in books that use them).
// A psalm's "Choose fórmula" button picks a semitono or tono recto from a list
// with search; that song's staff, tab and chords are copied above the psalm and
// follow the psalm's transposition. Remembered per psalm on this device
// (songState "formula") and carried in shared session links (session.js).
// Loads before session.js and transpose.js, so it checks their names exist.

// The fórmulas' staff and chords as built: copied now, before transpose.js
// rewrites any of them for their own saved transposition.
const formulaHtml = new Map(BOOK.formulas.flatMap(([, items]) => items).map(([id]) => {
    const song = document.getElementById(id);
    return [id, (song.querySelector(".melody")?.outerHTML ?? "") + song.querySelector(".lyrics").outerHTML];
}));

// Chords written over the psalm itself, for semitonos only (tonos rectos: later).
// Keys are the fórmula subtags of the liturgia book's tags.yaml; value = bars.
const SEMITONO_BARS = { semitonos_2: 2, semitonos_3: 3, semitonos_4: 4 };

// A semitono's bars as built: "Em Bm | A D Em" + "Flexa: Em D" ->
// { size: 2, bars: [["Em", "Bm"], ["A", "D", "Em"]], flexa: ["Em", "D"] }
const formulaBars = new Map(BOOK.formulas.flatMap(([, items, tag]) => (SEMITONO_BARS[tag] ? items : []).map(([id]) => {
    const lyrics = document.getElementById(id).querySelector(".lyrics");
    const bars = lyrics.querySelector(".chord-line")?.textContent.split("|").map((bar) => bar.trim().split(/\s+/)) ?? [];
    const flexa = lyrics.querySelector(".chord-inline")?.textContent.replace(/^[^:]*:/, "").trim().split(/\s+/);
    return [id, { size: SEMITONO_BARS[tag], bars, flexa }];
})).filter(([, f]) => f.bars.length === f.size));

// How strongly a line ends: 2 = . ; : ? ! (also before » or a quote), 1 = comma, 0 = none.
function linePause(text) {
    const end = lineEnd(text);
    return end && ".;:?!".includes(end) ? 2 : end === "," ? 1 : 0;
}

// The line's last punctuation mark (after » or a quote), or "".
function lineEnd(text) {
    return text.replace(/[\s»”"’')\]]+$/u, "").slice(-1);
}

// Semitono de 2: bars 1, 2 alternate line by line. An odd verse has one flexa
// (flexa, 1, 2) on line 1, 3, 5…, never in the last two lines: placed where the
// lines ending each group (every bar-2 line) end most strongly. Ties -> more group
// ends on . ! ? (the sentence ends), then more on :, then the earliest.
function semitono2Plan(texts, hasFlexa) {
    const alternate = (count) => Array.from({ length: count }, (_, i) => i % 2);
    if (texts.length % 2 === 0) return alternate(texts.length);
    if (texts.length < 3 || !hasFlexa) return null;
    let best = null;
    let bestScore = null;
    for (let k = 0; k <= texts.length - 3; k += 2) {
        const plan = [...alternate(k), "flexa", ...alternate(texts.length - k - 1)];
        const ends = texts.filter((_, i) => plan[i] === 1);
        const count = (marks) => ends.filter((t) => marks.includes(lineEnd(t) || "-")).length;
        const score = [ends.reduce((sum, t) => sum + linePause(t), 0), count(".!?"), count(":")];
        const i = bestScore && score.findIndex((v, j) => v !== bestScore[j]);
        if (!bestScore || (i >= 0 && score[i] > bestScore[i])) [best, bestScore] = [plan, score];
    }
    return best;
}

// The bar of each line ("flexa" or an index into bars), or null if the verse doesn't fit.
// De 3 / de 4: one bar per line, so exactly 3 / 4 lines.
function versePlan(texts, f) {
    if (f.size === 2) return semitono2Plan(texts, Boolean(f.flexa));
    return texts.length === f.size ? texts.map((_, i) => i) : null;
}

// First chord over the first letter; the others over the last words, one word
// each (the last chord on the last word), moved right if they would touch.
// An optional chord "(B7)" stays right after the one before it.
function chordLineText(text, bar) {
    const starts = [...text.matchAll(/\S+/g)].map((m) => m.index + Math.max(0, m[0].search(/\p{L}/u)));
    const chords = bar.join(" ").split(/ (?!\()/);
    let line = "";
    chords.forEach((chord, i) => {
        const word = i === 0 ? 0 : starts.length - chords.length + i;
        const col = Math.max(starts[word] ?? 0, line ? line.length + 1 : 0);
        line = line.padEnd(col) + chord;
    });
    return line;
}

function chordedLine({ text, bold }, chords, flexa) {
    const pair = Object.assign(document.createElement("div"), { className: bold ? "line-pair bold" : "line-pair" });
    const line = Object.assign(document.createElement("div"), { className: flexa ? "chord-line flexa" : "chord-line" });
    // separators in .sep spans, as lyrics.py chord_line_html writes them (transpose.js relies on it)
    line.innerHTML = chordLineText(text, chords).replace(/[()|]/g, '<span class="sep">$&</span>');
    pair.append(line, text);
    return pair;
}

// The psalm's lyrics as built, put back before each fórmula's chords.
const psalmLyrics = new WeakMap();

function setPsalmChords(psalm, id) {
    const lyrics = psalm.querySelector(":scope > .lyrics");
    if (!psalmLyrics.has(psalm)) psalmLyrics.set(psalm, lyrics.innerHTML);
    lyrics.innerHTML = psalmLyrics.get(psalm);
    const f = formulaBars.get(id);
    if (!f || lyrics.querySelector(".chord-line, .chord-inline")) return; // a psalm with its own chords keeps them
    const verses = [...lyrics.querySelectorAll(".verse")].map((verse) => {
        const lines = [...verse.children].map((line) => ({ text: line.textContent, bold: line.classList.contains("bold") }));
        // Semitono de 4's Gloria: "Gloria al Padre, y al Hijo" / "y al Espíritu Santo." / …
        // or, in hymns, "Gloria al Padre," / "gloria al Hijo," / "gloria al Espíritu Santo," / …
        if (f.size === 4 && lines.length === 3 && normalizeText(lines[0].text).startsWith("gloria al padre")) {
            const t = lines[0].text;
            const [, first, second] = t.match(/^(.*?),?\s+(y al Esp.*)$/) || t.match(/^(.*?,)\s+(.+)$/) || [];
            if (second) lines.splice(0, 1, { ...lines[0], text: first }, { ...lines[0], text: second });
        }
        return { verse, lines, plan: versePlan(lines.map((line) => line.text), f) };
    });
    if (f.size !== 2 && verses.some(({ plan }) => !plan)) return; // de 3 / de 4: every verse must fit
    verses.forEach(({ verse, lines, plan }) => {
        if (plan) verse.replaceChildren(...lines.map((line, i) => (plan[i] === "flexa"
            ? chordedLine(line, f.flexa, true) : chordedLine(line, f.bars[plan[i]], false))));
    });
}

function setFormula(psalm, id) {
    if (!formulaHtml.has(id)) id = null;
    songState.set(psalm, "formula", id);
    psalm.querySelector(".formula-pick").textContent =
        id ? `Fórmula: ${document.getElementById(id).dataset.title}` : "Choose fórmula…";
    const box = psalm.querySelector(".psalm-formula");
    if (typeof playing !== "undefined" && playing?.song === psalm) stopMelody(); // melody.js
    box.innerHTML = id ? formulaHtml.get(id) : "";
    setPsalmChords(psalm, id);
    // Not yet defined while the page loads; melody.js and transpose.js then do this themselves.
    if (typeof melodyObserver !== "undefined") melodyObserver.observe(psalm);
    if (typeof renderChords === "function") renderChords(psalm);
    if (typeof renderSession === "function") renderSession();
}

songState.each("formula", (psalm, id) => {
    if (psalm.querySelector(".formula-pick")) setFormula(psalm, id);
});

// One list for every psalm: search box, the fórmulas by group, no fórmula / cancel.
const formulaDialog = Object.assign(document.createElement("dialog"), { className: "print-dialog formula-dialog" });
formulaDialog.innerHTML = `<input type="search" placeholder="Search fórmulas" aria-label="Search fórmulas">
<div class="formula-options"></div>
<div class="dialog-buttons"><button data-formula="">No fórmula</button><button>Cancel</button></div>`;
const formulaSearch = formulaDialog.querySelector("input");
const formulaOptions = formulaDialog.querySelector(".formula-options");
BOOK.formulas.forEach(([label, items]) => {
    const group = document.createElement("section");
    group.append(Object.assign(document.createElement("h4"), { textContent: label }));
    items.forEach(([id, title]) => {
        // "Semitonos de 2: (1) Suplicante 1" shows as "(1) Suplicante 1" under its group heading
        const option = Object.assign(document.createElement("button"), { textContent: title.replace(/^[^:]*: (?=\(\d+\))/, "") });
        Object.assign(option.dataset, { formula: id, search: normalizeText(`${label} ${title}`) });
        group.append(option);
    });
    formulaOptions.append(group);
});
document.body.append(formulaDialog);

let formulaPsalm = null;

// Every typed word must appear in the group or title: "4 glor" finds "Semitonos de 4 … Glorioso".
formulaSearch.addEventListener("input", () => {
    const words = normalizeText(formulaSearch.value).split(/\s+/).filter(Boolean);
    formulaOptions.querySelectorAll("section").forEach((group) => {
        const options = [...group.querySelectorAll("button")];
        options.forEach((option) => { option.hidden = !words.every((word) => option.dataset.search.includes(word)); });
        group.hidden = options.every((option) => option.hidden);
    });
});
formulaSearch.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault(); // else the same Enter clicks the picker button, focused again on close
    formulaOptions.querySelector("button:not([hidden])")?.click();
});

formulaDialog.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if ("formula" in button.dataset) setFormula(formulaPsalm, button.dataset.formula);
    formulaDialog.close();
});

onAction("formula-pick", (button, psalm) => {
    formulaPsalm = psalm;
    formulaSearch.value = "";
    formulaSearch.dispatchEvent(new Event("input"));
    const current = songState.get(psalm, "formula");
    formulaOptions.querySelectorAll("button").forEach((option) => {
        option.setAttribute("aria-pressed", option.dataset.formula === current);
    });
    formulaDialog.showModal();
    // Start at the current choice (and keep phones from opening the keyboard).
    const start = formulaOptions.querySelector('[aria-pressed="true"]') ?? formulaOptions.querySelector("button");
    start.focus();
    start.scrollIntoView({ block: "center" });
});
