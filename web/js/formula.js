// Psalm fórmulas (book.yaml psalm_tags / formula_tag; only in books that use them).
// A psalm's "Choose fórmula" button picks a semitono or tono recto from a list
// with search; that song's staff, tab and chords are copied above the psalm and
// follow the psalm's transposition. Remembered per psalm on this device
// (songState "formula") and carried in shared session links (session.js).
// Loads before session.js and transpose.js, so it checks their names exist.
// The semitono rules (chordSpots, versePlan, chordLineText, …) are in formula-core.js.

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
// { size: 2, bars: [["Em", "Bm"], ["A", "D", "Em"]], flexa: ["Em", "D"], spots: chordSpots(its melody) }
const formulaBars = new Map(BOOK.formulas.flatMap(([, items, tag]) => (SEMITONO_BARS[tag] ? items : []).map(([id]) => {
    const song = document.getElementById(id);
    const lyrics = song.querySelector(".lyrics");
    const bars = lyrics.querySelector(".chord-line")?.textContent.split("|").map((bar) => bar.trim().split(/\s+/)) ?? [];
    const flexa = lyrics.querySelector(".chord-inline")?.textContent.replace(/^[^:]*:/, "").trim().split(/\s+/);
    const abc = song.querySelector(".melody")?.dataset.abc;
    return [id, { size: SEMITONO_BARS[tag], bars, flexa, spots: abc ? chordSpots(abc) : null }];
})).filter(([, f]) => f.bars.length === f.size));

// A psalm's exceptions to the semitono rules (song field `semitono`, docs/semitonos.md).
const semitonoExceptions = (psalm) => JSON.parse(psalm.dataset.semitono || "{}");

// The lyric text with each marked syllable in a span (underlined when "Sílabas" is on).
function markedText(text, marks) {
    const out = document.createDocumentFragment();
    let at = 0;
    for (const [start, end, notes] of marks.sort((a, b) => a[0] - b[0])) {
        out.append(text.slice(at, start),
            Object.assign(document.createElement("span"), { className: notes > 1 ? "syl syl2" : "syl", textContent: text.slice(start, end) }));
        at = end;
    }
    out.append(text.slice(at));
    return out;
}

function chordedLine({ text, bold }, chords, flexa, spots, marks = [], ex = null) {
    if (!chords.length) {
        const plain = Object.assign(document.createElement("div"), { className: bold ? "lyric-line bold" : "lyric-line" });
        plain.append(markedText(text, marks));
        return plain;
    }
    const pair = Object.assign(document.createElement("div"), { className: bold ? "line-pair bold" : "line-pair" });
    const line = Object.assign(document.createElement("div"), { className: flexa ? "chord-line flexa" : "chord-line" });
    // separators in .sep spans, as lyrics.py chord_line_html writes them (transpose.js relies on it)
    line.innerHTML = chordLineText(text, chords, spots, ex).replace(/[()|]/g, '<span class="sep">$&</span>');
    pair.append(line, markedText(text, marks));
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
    const ex = semitonoExceptions(psalm);
    const verses = [...lyrics.querySelectorAll(".verse")].map((verse, v) => {
        const lines = [...verse.children].map((line) => ({ text: line.textContent, bold: line.classList.contains("bold") }));
        const texts = gloriaSplit(lines.map((line) => line.text), f.size);
        if (texts.length > lines.length) lines.splice(0, 1, { ...lines[0], text: texts[0] }, { ...lines[0], text: texts[1] });
        return { verse, lines, plan: versePlan(lines.map((line) => line.text), f, ex, v + 1) };
    });
    if (f.size !== 2 && verses.some(({ plan }) => !plan)) return; // de 3 / de 4: every verse must fit
    verses.forEach(({ verse, lines, plan }) => {
        if (plan) verse.replaceChildren(...lines.map((line, i) => {
            if (plan[i] === "flexa") {
                return chordedLine(line, f.flexa, true, f.spots?.flexa, syllableMarks(line.text, f.spots?.flexa, true, ex), ex);
            }
            const [bar, spots] = [f.bars[plan[i]], f.spots?.bars[plan[i]]];
            const shared = plan[i + 1] === plan[i] ? 0 : plan[i - 1] === plan[i] ? 1 : -1; // de 4: two lines, one bar
            if (shared < 0) return chordedLine(line, bar, false, spots, syllableMarks(line.text, spots, true, ex), ex);
            const [chords, part] = splitBar(bar, spots)[shared];
            // two lines, one bar: the notes after the reciting one all fall on the second line
            const el = chordedLine(line, chords, false, part, shared ? syllableMarks(line.text, spots, false, ex) : [], ex);
            el.classList.add("bar-shared"); // red bracket: these two lines are one bar
            return el;
        }));
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
    // "Sílabas": underline where the melody changes note; only with a semitono that has a melody.
    let toggle = psalm.querySelector(".syllables-toggle");
    if (!toggle) {
        toggle = Object.assign(document.createElement("button"), { className: "syllables-toggle", textContent: "Sílabas" });
        toggle.dataset.action = "syllables-toggle";
        psalm.querySelector(".formula-pick").after(toggle);
    }
    toggle.hidden = !psalm.querySelector(":scope > .lyrics .syl");
    showSyllables(psalm, songState.get(psalm, "syllables") === true);
    // Not yet defined while the page loads; melody.js and transpose.js then do this themselves.
    if (typeof melodyObserver !== "undefined") melodyObserver.observe(psalm);
    if (typeof renderChords === "function") renderChords(psalm);
    if (typeof renderSession === "function") renderSession();
}

function showSyllables(psalm, on) {
    psalm.classList.toggle("show-syllables", on);
    psalm.querySelector(".syllables-toggle")?.setAttribute("aria-pressed", on);
}

onAction("syllables-toggle", (button, psalm) => {
    const on = !psalm.classList.contains("show-syllables");
    songState.set(psalm, "syllables", on || null); // remembered on this device
    showSyllables(psalm, on);
});

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
BOOK.formulas.forEach(([label, items, tag]) => {
    const group = document.createElement("section");
    group.dataset.tag = tag;
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
const formulaGroups = [...formulaOptions.children];

// The standard closing Gloria, as letters only: the one verse that doesn't make de 4 red.
const STANDARD_GLORIA = "gloria al padre y al hijo y al espiritu santo como era en el principio " +
    "ahora y siempre por los siglos de los siglos amen";
const letters = (text) => normalizeText(text).replace(/[^a-zñ]+/g, " ").trim();

// Which fórmula groups suit a psalm (user, 2026-11-27): good = shown first, green; bad = red.
// Cánticos: tonos rectos good. De 3: good if every verse has 3 lines, else bad.
// De 4: bad if a verse other than the standard Gloria has 3 lines. Nothing is hidden.
// A verse with the psalm's own bars for that size (ex.bars) counts as fitting.
function formulaFit(psalm) {
    const box = document.createElement("div");
    box.innerHTML = psalmLyrics.get(psalm) ?? psalm.querySelector(":scope > .lyrics").innerHTML;
    const verses = [...box.querySelectorAll(".verse")].map((verse) => [...verse.children].map((line) => line.textContent));
    const ex = semitonoExceptions(psalm);
    const own = (lines, v, size) => ownBars(lines, size, ex, v + 1);
    const good = new Set(), bad = new Set();
    if (normalizeText(psalm.dataset.title).startsWith("cantico")) good.add("tonos_rectos");
    (verses.length && verses.every((lines, v) => lines.length === 3 || own(lines, v, 3)) ? good : bad).add("semitonos_3");
    if (verses.some((lines, v) => lines.length === 3 && letters(lines.join(" ")) !== STANDARD_GLORIA
        && !own(gloriaSplit(lines, 4), v, 4))) {
        bad.add("semitonos_4");
    }
    return { good, bad };
}

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
    const { good, bad } = formulaFit(psalm);
    formulaOptions.append(...formulaGroups.filter((g) => good.has(g.dataset.tag)),
        ...formulaGroups.filter((g) => !good.has(g.dataset.tag)));
    formulaGroups.forEach((group) => group.querySelectorAll("button").forEach((option) => {
        option.classList.toggle("formula-good", good.has(group.dataset.tag));
        option.classList.toggle("formula-bad", bad.has(group.dataset.tag));
    }));
    formulaOptions.querySelectorAll("button").forEach((option) => {
        option.setAttribute("aria-pressed", option.dataset.formula === current);
    });
    formulaDialog.showModal();
    // Start at the current choice (and keep phones from opening the keyboard).
    const start = formulaOptions.querySelector('[aria-pressed="true"]') ?? formulaOptions.querySelector("button");
    start.focus();
    start.scrollIntoView({ block: "center" });
});
