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
// { size: 2, bars: [["Em", "Bm"], ["A", "D", "Em"]], flexa: ["Em", "D"], spots: chordSpots(its melody) }
const formulaBars = new Map(BOOK.formulas.flatMap(([, items, tag]) => (SEMITONO_BARS[tag] ? items : []).map(([id]) => {
    const song = document.getElementById(id);
    const lyrics = song.querySelector(".lyrics");
    const bars = lyrics.querySelector(".chord-line")?.textContent.split("|").map((bar) => bar.trim().split(/\s+/)) ?? [];
    const flexa = lyrics.querySelector(".chord-inline")?.textContent.replace(/^[^:]*:/, "").trim().split(/\s+/);
    const abc = song.querySelector(".melody")?.dataset.abc;
    return [id, { size: SEMITONO_BARS[tag], bars, flexa, spots: abc ? chordSpots(abc) : null }];
})).filter(([, f]) => f.bars.length === f.size));

// Where each chord of a semitono's melody falls on a psalm line (rules found with the user,
// docs/semitonos.md): notes up to the long reciting note (len >= 4) take the line's first
// syllables, one each; the notes after it end on the line's last stressed syllable, one per
// syllable before it. A tuplet "(3abc" is one syllable. Per bar: [{from: "start"|"accent", k}].
// "Am"A4 "Em"E G "Am"A2 -> [{from: "start", k: 0}, {from: "accent", k: 2}, {from: "accent", k: 0}]
function chordSpots(abc) {
    const length = (s) => (s.split("/")[0] ? Number(s.split("/")[0]) : 1) / (s.includes("/") ? Number(s.split("/")[1] || 2) : 1);
    const bar = (text) => {
        const notes = [];
        let tuple = 0;
        for (const [, start, chord, len] of text.matchAll(/(\(\d)?(?:"([^"]+)")?[=^_]?[A-Ga-g][,']*([\d/]*)/g)) {
            if (tuple > 0) {
                tuple--;
                notes.at(-1).chord ||= chord;
                continue;
            }
            if (start) tuple = Number(start[1]) - 1;
            notes.push({ chord, len: length(len) });
        }
        const recto = Math.max(0, notes.findIndex((n) => n.len >= 4));
        // recto: notes before the reciting note; after: notes after it (for the syllable marks)
        return Object.assign(notes.flatMap((n, j) => (!n.chord ? [] : j <= recto
            ? [{ from: "start", k: j }] : [{ from: "accent", k: notes.length - 1 - j }])),
            { recto, after: notes.length - 1 - recto });
    };
    const [main, flexa = ""] = abc.replace(/^[A-Za-z]:.*$/gm, "").split("||");
    return { bars: main.split("|").filter((b) => b.trim()).map(bar), flexa: flexa.trim() ? bar(flexa) : null };
}

// Spanish sung syllables of a line: [{col, stress}], col = index of the syllable's first
// letter. Spelling rules (diphthongs, hiatus, consonant clusters), stress from the accent mark
// or the word's ending, atonic little words, and sinalefa across words unless one of the two
// vowels is stressed. Port of docs/experiments/semitono-marks/marks.py.
// Hiatus that spelling hides: HIATUS gives those words' syllable starts (add words as found).
const VOWELS = "aeiouáéíóúü";
const STRONG = "aeoáéóíú"; // accented í/ú break a diphthong like a, e, o do
const ONSETS = new Set("bl br cl cr dr fl fr gl gr kl kr pl pr tr ch ll rr qu gu".split(" "));
const ATONIC = new Set(("el la los las lo le les de del a al y e o u ni en con por para sin que se me te nos os " +
    "mi mis tu tus su sus un una unos unas pero si cuando como donde mientras hacia desde entre hasta según tan es").split(" "));

const HIATUS = { "sión": [0, 2], "santuario": [0, 3, 5, 6], "santuarios": [0, 3, 5, 6] }; // Si-ón, san-tu-a-rio

function syllableStarts(word) {
    const w = word.toLowerCase();
    if (HIATUS[w]) return HIATUS[w];
    const vowel = [...w].map((c, i) => (c === "y" ? !VOWELS.includes(w[i + 1] || "x")
        : c === "u" && "qg".includes(w[i - 1] || "x") && "eiéí".includes(w[i + 1] || "x") ? false // que, guerra
            : VOWELS.includes(c)));
    const nuclei = [];
    for (let i = 0; i < w.length; i++) {
        if (!vowel[i]) continue;
        const start = i;
        while (vowel[i + 1] && !(STRONG.includes(w[i]) && STRONG.includes(w[i + 1]))) i++;
        nuclei.push([start, i + 1]);
    }
    return [0, ...nuclei.slice(1).map(([next], n) => {
        const end = nuclei[n][1];
        const cons = w.slice(end, next);
        return cons.length <= 1 ? end : ONSETS.has(cons.slice(-2)) ? next - 2 : next - 1;
    })];
}

function stressedSyllable(word, starts) {
    const w = word.toLowerCase();
    if (ATONIC.has(w)) return -1;
    const mark = w.search(/[áéíóú]/);
    if (mark >= 0) return starts.findLastIndex((s) => s <= mark);
    if (starts.length === 1) return 0;
    return "aeiouns".includes(w.at(-1)) ? starts.length - 2 : starts.length - 1;
}

function lineSyllables(text) {
    const units = [];
    let prev = null;
    for (const m of text.matchAll(/\p{L}+/gu)) {
        const starts = syllableStarts(m[0]);
        const stress = stressedSyllable(m[0], starts);
        const sylls = starts.map((s, i) => ({ col: m.index + s, stress: i === stress }));
        const gap = prev ? text.slice(prev.end, m.index) : "";
        const next = m[0].toLowerCase().replace(/^h/, "");
        if (prev && /\s/.test(gap) && !/[.;:?!«»"“”()]/.test(gap) && (VOWELS + "y").includes(prev.last)
            && !units.at(-1).stress && stress !== 0 && (VOWELS.includes(next[0]) || next === "y")) sylls.shift();
        units.push(...sylls);
        prev = { end: m.index + m[0].length, last: m[0].at(-1).toLowerCase() };
    }
    return units;
}

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
// A quote isn't split: a line inside an open « or “, or a ":" line just before one,
// counts as no pause (user's flexa marks, round 1).
function semitono2Plan(texts, hasFlexa) {
    const alternate = (count) => Array.from({ length: count }, (_, i) => i % 2);
    if (texts.length % 2 === 0) return alternate(texts.length);
    if (texts.length < 3 || !hasFlexa) return null;
    const tally = (s, ch) => s.split(ch).length - 1;
    const pauses = texts.map((t, i) => {
        const upTo = texts.slice(0, i + 1).join("");
        const inQuote = tally(upTo, "«") > tally(upTo, "»") || tally(upTo, "“") > tally(upTo, "”");
        const opensQuote = lineEnd(t) === ":" && /^\s*[«“]/u.test(texts[i + 1] ?? "");
        return inQuote || opensQuote ? 0 : linePause(t);
    });
    let best = null;
    let bestScore = null;
    for (let k = 0; k <= texts.length - 3; k += 2) {
        const plan = [...alternate(k), "flexa", ...alternate(texts.length - k - 1)];
        const ends = texts.filter((_, i) => plan[i] === 1);
        const count = (marks) => ends.filter((t) => marks.includes(lineEnd(t) || "-")).length;
        const score = [pauses.reduce((sum, p, i) => sum + (plan[i] === 1 ? p : 0), 0), count(".!?"), count(":")];
        const i = bestScore && score.findIndex((v, j) => v !== bestScore[j]);
        if (!bestScore || (i >= 0 && score[i] > bestScore[i])) [best, bestScore] = [plan, score];
    }
    return best;
}

// Semitono de 4 (user's de 4 marks, round 1): 2 lines -> bars 1, 4. Otherwise n // 4 passes of
// bars 1-4; the lines left over join a neighbour (two lines share a bar, never more), where the
// first line ends most weakly (linePause); ties -> joins nearest the verse's start or end, then
// the earliest. 3-line verses (and 1-line rubrics) don't fit: null.
function semitono4Plan(texts) {
    const n = texts.length;
    if (n === 2) return [0, 3];
    if (n < 4) return null;
    const groups = 4 * Math.floor(n / 4);
    let best = null;
    let bestKey = null;
    const pick = (joins, from) => { // joins: gaps (after line i) where two lines share a bar
        if (joins.length === n - groups) {
            const key = [joins.reduce((s, i) => s + linePause(texts[i]), 0),
                joins.reduce((s, i) => s + Math.min(i, n - 2 - i), 0), ...joins];
            const d = bestKey && key.findIndex((v, j) => v !== bestKey[j]);
            if (!bestKey || (d >= 0 && key[d] < bestKey[d])) [best, bestKey] = [joins, key];
            return;
        }
        for (let i = from; i < n - 1; i++) pick([...joins, i], i + 2);
    };
    pick([], 0);
    let bar = 0;
    return texts.map((_, i) => { const b = bar % 4; if (!best.includes(i)) bar++; return b; });
}

// The bar of each line ("flexa" or an index into bars), or null if the verse doesn't fit.
// De 3: one bar per line, so exactly 3 lines.
function versePlan(texts, f) {
    if (f.size === 2) return semitono2Plan(texts, Boolean(f.flexa));
    if (f.size === 4) return semitono4Plan(texts);
    return texts.length === f.size ? texts.map((_, i) => i) : null;
}

// Two lines sung to one bar: the first takes the chords counted from the start of the bar
// (spots "start"), the second those counted back from its stressed syllable ("accent").
// Without matching spots: the first chord on the first line, the rest on the second.
function splitBar(bar, spots) {
    const chords = bar.join(" ").split(/ (?!\()/);
    if (spots?.length !== chords.length) return [[chords.slice(0, 1), null], [chords.slice(1), null]];
    const part = (start) => [chords.filter((_, i) => (spots[i].from === "start") === start),
        spots.filter((s) => (s.from === "start") === start)];
    return [part(true), part(false)];
}

// Each chord over the syllable its melody note falls on (spots, from chordSpots); without
// spots, or if the melody's chords don't match the bar's: first chord over the first letter,
// the others over the last words, one word each. Chords move right if they would touch.
// An optional chord "(B7)" stays right after the one before it.
function chordLineText(text, bar, spots) {
    const starts = [...text.matchAll(/\S+/g)].map((m) => m.index + Math.max(0, m[0].search(/\p{L}/u)));
    const chords = bar.join(" ").split(/ (?!\()/);
    const units = lineSyllables(text);
    const accent = units.findLastIndex((u) => u.stress);
    const at = (i) => units[Math.min(Math.max(i, 0), units.length - 1)].col;
    const cols = spots?.length === chords.length && units.length
        ? spots.map(({ from, k }) => at(from === "start" ? k : (accent < 0 ? units.length - 1 : accent) - k))
        : chords.map((_, i) => starts[i === 0 ? 0 : starts.length - chords.length + i]);
    let line = "";
    chords.forEach((chord, i) => {
        const col = Math.max(cols[i] ?? 0, line ? line.length + 1 : 0);
        line = line.padEnd(col) + chord;
    });
    return line;
}

// Where the melody changes note after the reciting note (user, 2026-11-27): the bar's notes
// after it end on the line's last stressed syllable, one syllable each going back, never
// before the reciting note's syllable (spots.recto; a note landing there shares it: 2 notes).
// withRecto: false for the second of two lines on one bar (the reciting note is on the first).
// -> [[start, end, notes]]: the letters of each marked syllable.
function syllableMarks(text, spots, withRecto) {
    const units = lineSyllables(text);
    if (!spots || !spots.after || !units.length) return [];
    const accent = units.findLastIndex((u) => u.stress);
    const last = accent < 0 ? units.length - 1 : accent;
    const floor = withRecto ? Math.min(spots.recto, units.length - 1) : 0;
    const count = new Map();
    for (let k = spots.after - 1; k >= 0; k--) {
        const u = Math.max(last - k, floor);
        count.set(u, (count.get(u) ?? (withRecto && u === floor ? 1 : 0)) + 1);
    }
    return [...count].map(([u, notes]) => {
        const start = units[u].col;
        const wordEnd = start + text.slice(start).match(/^\p{L}*/u)[0].length;
        return [start, Math.min(wordEnd, units[u + 1]?.col ?? wordEnd), notes];
    });
}

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

function chordedLine({ text, bold }, chords, flexa, spots, marks = []) {
    if (!chords.length) {
        const plain = Object.assign(document.createElement("div"), { className: bold ? "lyric-line bold" : "lyric-line" });
        plain.append(markedText(text, marks));
        return plain;
    }
    const pair = Object.assign(document.createElement("div"), { className: bold ? "line-pair bold" : "line-pair" });
    const line = Object.assign(document.createElement("div"), { className: flexa ? "chord-line flexa" : "chord-line" });
    // separators in .sep spans, as lyrics.py chord_line_html writes them (transpose.js relies on it)
    line.innerHTML = chordLineText(text, chords, spots).replace(/[()|]/g, '<span class="sep">$&</span>');
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
        if (plan) verse.replaceChildren(...lines.map((line, i) => {
            if (plan[i] === "flexa") {
                return chordedLine(line, f.flexa, true, f.spots?.flexa, syllableMarks(line.text, f.spots?.flexa, true));
            }
            const [bar, spots] = [f.bars[plan[i]], f.spots?.bars[plan[i]]];
            const shared = plan[i + 1] === plan[i] ? 0 : plan[i - 1] === plan[i] ? 1 : -1; // de 4: two lines, one bar
            if (shared < 0) return chordedLine(line, bar, false, spots, syllableMarks(line.text, spots, true));
            const [chords, part] = splitBar(bar, spots)[shared];
            // two lines, one bar: the notes after the reciting one all fall on the second line
            const el = chordedLine(line, chords, false, part, shared ? syllableMarks(line.text, spots, false) : []);
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
function formulaFit(psalm) {
    const box = document.createElement("div");
    box.innerHTML = psalmLyrics.get(psalm) ?? psalm.querySelector(":scope > .lyrics").innerHTML;
    const verses = [...box.querySelectorAll(".verse")].map((verse) => [...verse.children].map((line) => line.textContent));
    const good = new Set(), bad = new Set();
    if (normalizeText(psalm.dataset.title).startsWith("cantico")) good.add("tonos_rectos");
    (verses.length && verses.every((lines) => lines.length === 3) ? good : bad).add("semitonos_3");
    if (verses.some((lines) => lines.length === 3 && letters(lines.join(" ")) !== STANDARD_GLORIA)) bad.add("semitonos_4");
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
