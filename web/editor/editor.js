"use strict";
const TOKEN = document.querySelector("meta[name=token]").content;
const $ = (id) => document.getElementById(id);

let book = null;
// rows: the chord view; body: the song text (rows are only written back into it once a chord changed: `dirty`)
let song = { id: null, rows: [], body: "", dirty: false, textMode: false, siteArtist: "", extraTags: [], base: {}, semitono: {} };

async function api(path, data) {
    const response = await fetch(path, data === undefined ? {} : {
        method: "POST", headers: { "X-Token": TOKEN, "Content-Type": "application/json" }, body: JSON.stringify(data) });
    const body = await response.json();
    if (!response.ok) throw Object.assign(new Error(body.error || response.status), { status: response.status, body });
    return body;
}

function say(message, error = false) {
    $("status").textContent = message;
    $("status").className = error ? "error" : "";
}

async function run(message, work) {
    say(message);
    try {
        await work();
        if ($("status").textContent === message) say(""); // work may have set its own message
    } catch (e) { say(e.message, true); }
}

// ---------- rows <-> body ----------

function chordLine(chords) {
    let line = "";
    for (const [col, name] of [...chords].sort((a, b) => a[0] - b[0]))
        line = line.padEnd(line ? Math.max(col, line.length + 1) : col) + name; // keep >= 1 space between chords
    return line;
}

const isBlank = (row) => "text" in row && !row.text.trim();

// Bold rows get a ** line before them and one right after their last line (before any blank lines).
function serialize(rows) {
    const lines = [];
    let bold = false, end = 0; // end: just after the last non-blank line
    for (const row of rows) {
        if (!isBlank(row) && !!row.bold !== bold) {
            if (bold) lines.splice(end, 0, "**"); else lines.push("**");
            bold = !bold;
        }
        if ("text" in row) lines.push(row.text);
        else {
            if (row.chords.length) lines.push(chordLine(row.chords));
            if (row.lyric !== null) lines.push(row.lyric);
        }
        if (!isBlank(row)) end = lines.length;
    }
    if (bold) lines.splice(end, 0, "**");
    return lines.join("\n");
}

function currentBody() {
    if (song.textMode) return $("body").value;
    return song.dirty ? serialize(song.rows) : song.body;
}

// ---------- chord view ----------

function charWidth() {
    const probe = document.createElement("span");
    probe.textContent = "0".repeat(20);
    probe.style.cssText = "position:absolute;visibility:hidden;white-space:pre";
    $("grid").append(probe);
    const width = probe.getBoundingClientRect().width / 20;
    probe.remove();
    return width;
}

// Undo: snapshots of song.rows. `last` is the current state; the bottom of `undo` is the loaded song.
const history = { undo: [], redo: [], last: "[]" };

function resetHistory() { Object.assign(history, { undo: [], redo: [], last: JSON.stringify(song.rows) }); }

function commit() {
    const now = JSON.stringify(song.rows);
    if (now === history.last) return;
    history.undo.push(history.last);
    history.redo.length = 0; // in place: step() holds these arrays
    history.last = now;
}

function step(from, to) {
    commit();
    if (!from.length) return;
    to.push(history.last);
    history.last = from.pop();
    song.rows = JSON.parse(history.last);
    song.dirty = history.undo.length > 0; // back at the loaded song: save its body byte for byte
    renderGrid();
}

document.addEventListener("keydown", (e) => {
    if (!(e.metaKey || e.ctrlKey) || e.key.toLowerCase() !== "z" || song.textMode) return;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return; // their own undo
    e.preventDefault();
    if (e.shiftKey) step(history.redo, history.undo);
    else step(history.undo, history.redo);
});

function changed() { song.dirty = true; commit(); renderGrid(); }

// An input on a chord line at `col`; Enter or leaving it keeps the name, empty removes the chord.
function editChord(line, col, chord) {
    const input = document.createElement("input");
    input.value = chord ? chord[1] : "";
    input.style.left = col + "ch";
    line.append(input);
    input.focus();
    input.select();
    let done = false;
    const finish = (keep) => {
        if (done) return;
        done = true;
        const name = input.value.replace(/\s+/g, "");
        if (!keep || name === (chord ? chord[1] : "")) return input.remove();
        const chords = song.rows[line.dataset.row].chords;
        if (!name) chords.splice(chords.indexOf(chord), 1);
        else if (chord) chord[1] = name;
        else chords.push([col, name]);
        changed();
    };
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") finish(true);
        if (e.key === "Escape") finish(false);
    });
    input.addEventListener("blur", () => finish(true));
}

function chordElement(line, chord) {
    const span = document.createElement("span");
    // marks (-, |, (x2)) shown plain, as the book does (builder/lyrics.py SEPARATOR_RE)
    span.className = /^(?:[-|()]+|\(?[xX]\d{1,2}\)?)$/.test(chord[1]) ? "chord sep" : "chord";
    span.tabIndex = 0;
    span.textContent = chord[1];
    span.style.left = chord[0] + "ch";
    span.addEventListener("click", (e) => e.stopPropagation());
    span.addEventListener("keydown", (e) => {
        if (e.key !== "Delete" && e.key !== "Backspace") return;
        const chords = song.rows[line.dataset.row].chords;
        chords.splice(chords.indexOf(chord), 1);
        changed();
    });
    span.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        span.setPointerCapture(e.pointerId);
        const width = charWidth(), startX = e.clientX;
        let col = chord[0];
        const move = (m) => {
            col = Math.max(0, chord[0] + Math.round((m.clientX - startX) / width)); // snap to characters
            span.style.left = col + "ch";
        };
        const up = () => {
            span.removeEventListener("pointermove", move);
            span.removeEventListener("pointerup", up);
            if (col === chord[0]) return editChord(line, col, chord);
            chord[0] = col;
            changed();
        };
        span.addEventListener("pointermove", move);
        span.addEventListener("pointerup", up);
    });
    return span;
}

// ---------- splitting and joining lines ----------

function caretOffset(element) {
    const selection = getSelection();
    if (!selection.rangeCount) return null;
    const range = selection.getRangeAt(0), before = document.createRange();
    before.selectNodeContents(element);
    before.setEnd(range.startContainer, range.startOffset);
    return before.toString().length;
}

function focusRow(index, offset) {
    const element = $("grid").querySelector(`[data-edit="${index}"]`);
    if (!element) return;
    element.focus();
    const range = document.createRange(), node = element.firstChild;
    if (node) range.setStart(node, Math.min(offset, node.length)); else range.setStart(element, 0);
    range.collapse(true);
    getSelection().removeAllRanges();
    getSelection().addRange(range);
}

const withBold = (from, row) => (from.bold ? { ...row, bold: true } : row);

// Enter at `at` in row `index`: a lyric's chords from the second part's first letter on go down with it.
function splitRow(index, at) {
    const row = song.rows[index];
    let caret = [index + 1, 0];
    if ("text" in row) {
        song.rows.splice(index, 1, { ...row, text: row.text.slice(0, at) }, withBold(row, { text: row.text.slice(at) }));
    } else if (row.lyric === "" && !row.chords.length) {
        song.rows[index] = { text: "" }; // Enter on an empty line: a verse break
        caret = [index, 0];
    } else {
        const left = row.lyric.slice(0, at).trimEnd(), rest = row.lyric.slice(at);
        const right = rest.trimStart(), start = at + rest.length - right.length;
        if (!left.trim() && right) { // at the start: an empty line above
            song.rows.splice(index, 0, withBold(row, { chords: [], lyric: "" }));
            caret = [index + 1, at];
        } else {
            const moved = right ? row.chords.filter(([col]) => col >= start) : [];
            row.chords = row.chords.filter((chord) => !moved.includes(chord));
            row.lyric = left;
            song.rows.splice(index + 1, 0, withBold(row, { chords: moved.map(([col, name]) => [col - start, name]), lyric: right }));
        }
    }
    changed();
    focusRow(...caret);
}

// Backspace at the start of row `index`: joins it to the row above. Returns false when it can't.
function joinRow(index) {
    const row = song.rows[index], above = song.rows[index - 1];
    if (!above) return false;
    let caret;
    if (isBlank(above)) {
        song.rows.splice(index - 1, 1);
        caret = [index - 1, 0];
    } else if ("text" in row && "text" in above) {
        caret = [index - 1, above.text.length];
        above.text += row.text;
        song.rows.splice(index, 1);
    } else if (!("text" in row) && !("text" in above) && above.lyric !== null) {
        const left = above.lyric.trimEnd(), right = row.lyric.trimStart();
        // shortcut: chords of the line above that reach past its lyric push the joined ones right; fine for real songs
        const shift = (left ? left.length + 1 : 0) - (row.lyric.length - right.length);
        above.lyric = left && right ? left + " " + right : left + right;
        above.chords = [...above.chords, ...row.chords.map(([col, name]) => [Math.max(0, col + shift), name])];
        song.rows.splice(index, 1);
        caret = [index - 1, left && right ? left.length + 1 : left.length];
    } else return false;
    changed();
    focusRow(...caret);
    return true;
}

// Lyric and text lines are typed into in place; no re-render while typing so the caret stays put.
function editable(element, store, index) {
    element.contentEditable = "plaintext-only";
    element.spellcheck = false;
    element.dataset.edit = index;
    element.addEventListener("keydown", (e) => {
        if (e.isComposing) return;
        if (e.key === "Enter") {
            e.preventDefault();
            const range = getSelection().rangeCount && getSelection().getRangeAt(0);
            if (range && !range.collapsed) { range.deleteContents(); store(element.textContent); }
            commit(); // typing so far is its own undo step
            splitRow(index, caretOffset(element) ?? element.textContent.length);
        }
        if (e.key === "Backspace" && getSelection().isCollapsed && caretOffset(element) === 0) {
            commit();
            if (joinRow(index)) e.preventDefault();
        }
    });
    element.addEventListener("input", () => {
        store(element.textContent.replace(/\n/g, ""));
        song.dirty = true;
        element.closest("[data-block]")?.markLong();
        renderSemitono();
    });
    element.addEventListener("blur", commit); // one undo step per line edit
    element.addEventListener("beforeinput", (e) => { // the browser's own undo (Edit menu, editing commands)
        if (e.inputType === "historyUndo") { e.preventDefault(); step(history.undo, history.redo); }
        if (e.inputType === "historyRedo") { e.preventDefault(); step(history.redo, history.undo); }
    });
}

// A verse (rows between blank lines) is made bold or plain as a whole: choruses.
function newVerse(grid) {
    const verse = document.createElement("div"), button = document.createElement("button"), lines = document.createElement("div");
    verse.className = "verse";
    verse.rows = [];
    button.className = "bold-toggle";
    button.textContent = "B";
    button.title = "Bold (chorus) — Cmd/Ctrl+B";
    verse.toggle = () => {
        commit(); // a lyric edit in progress stays its own undo step
        const bold = !verse.rows.every((row) => row.bold);
        verse.rows.forEach((row) => { if (bold) row.bold = true; else delete row.bold; });
        changed();
    };
    button.addEventListener("click", verse.toggle);
    verse.append(button, lines);
    grid.append(verse);
    return verse;
}

document.addEventListener("keydown", (e) => {
    if (!(e.metaKey || e.ctrlKey) || e.key.toLowerCase() !== "b" || song.textMode) return;
    const verse = e.target.closest && e.target.closest("#grid .verse");
    if (!verse) return;
    e.preventDefault();
    verse.toggle();
});

function renderGrid() {
    const grid = $("grid");
    grid.replaceChildren();
    let verse = null;
    song.rows.forEach((row, index) => {
        const block = document.createElement("div");
        if (isBlank(row)) verse = null;
        else {
            verse = verse || newVerse(grid);
            verse.rows.push(row);
            if (verse.rows.every((r) => r.bold)) verse.classList.add("bold");
            else verse.classList.remove("bold");
        }
        if ("text" in row) {
            block.className = "text";
            block.textContent = row.text;
            editable(block, (value) => { row.text = value; }, index);
        } else {
            const line = document.createElement("div");
            line.className = "chords";
            line.dataset.row = index;
            const end = Math.max(...row.chords.map(([col, name]) => col + name.length), (row.lyric || "").length);
            line.style.width = Math.max(end + 4, 24) + "ch";
            row.chords.forEach((chord) => line.append(chordElement(line, chord)));
            line.addEventListener("click", (e) => {
                if (e.target !== line) return;
                editChord(line, Math.floor((e.clientX - line.getBoundingClientRect().left) / charWidth()), null);
            });
            block.append(line);
            if (row.lyric !== null) {
                const lyric = document.createElement("div");
                lyric.className = "lyric";
                lyric.textContent = row.lyric;
                editable(lyric, (value) => { row.lyric = value; }, index);
                block.append(lyric);
            }
        }
        // as the build's long-lines warning (builder/lyrics.py LONG_LINE)
        block.dataset.block = index;
        block.markLong = () => block.classList.toggle("too-long", Math.max(
            ("text" in row ? row.text : row.lyric || "").trimEnd().length,
            ...(row.chords || []).map(([col, name]) => col + name.length)) > book.long_line);
        block.markLong();
        (verse ? verse.lastChild : grid).append(block);
    });
    renderSemitono();
}

function setText(data) {
    song.body = data.body;
    song.rows = data.rows;
    song.dirty = false;
    resetHistory();
    $("body").value = data.body;
    renderGrid();
    $("notes").replaceChildren(...(data.notes || []).map((note) => Object.assign(document.createElement("li"), { textContent: note })));
}

$("text-toggle").addEventListener("click", () => run("Reading the text...", async () => {
    if (!song.textMode) {
        $("body").value = currentBody();
    } else {
        setText(await api("/api/rows", { body: $("body").value }));
    }
    song.textMode = !song.textMode;
    $("body").hidden = !song.textMode;
    $("grid").hidden = song.textMode;
    $("text-toggle").textContent = song.textMode ? "Chords" : "Text";
}));

// ---------- semitono (song field `semitono`, docs/semitonos.md) ----------
// A psalm's lyrics with a semitono's chords where the book puts them (formula-core.js), to set
// the song's exceptions. song.semitono is kept as the song file writes it: bars 1-based, "f" = flexa.

let semitonos = []; // /api/formulas
const SEMITONO_PICK = "editor-semitono"; // localStorage: the semitono picked last

// song.semitono as formula.js reads data-semitono (builder/render.py song_html): bars 0-based, "flexa".
function semitonoEx() {
    const bars = Object.fromEntries(Object.entries(song.semitono.bars || {}).map(([size, verses]) => [size,
        Object.fromEntries(Object.entries(verses).map(([v, own]) => [v, own.map((b) => (b === "f" ? "flexa" : b - 1))]))]));
    return { ...song.semitono, bars };
}

// The lines of each verse as the book shows them (blank lines between verses; chord lines alone aren't lines).
function psalmVerses() {
    const verses = [[]];
    for (const row of song.rows) {
        const text = "text" in row ? row.text : row.lyric;
        if (text === null) continue;
        if (text.trim()) verses.at(-1).push(text.trim());
        else if (verses.at(-1).length) verses.push([]);
    }
    return verses.filter((lines) => lines.length);
}

// The song's own bars for a verse (from 1), 0-based or null to remove them.
function setOwnBars(size, verse, bars) {
    const all = (song.semitono.bars ||= {});
    const verses = (all[size] ||= {});
    if (bars) verses[verse] = bars.map((b) => (b === "flexa" ? "f" : b + 1));
    else delete verses[verse];
    if (!Object.keys(verses).length) delete all[size];
    if (!Object.keys(all).length) delete song.semitono.bars;
    renderSemitono();
}

function setStress(key, n) {
    const stress = (song.semitono.stress ||= {});
    key = stressKey(key);
    if (n) stress[key] = n; else delete stress[key];
    if (!Object.keys(stress).length) delete song.semitono.stress;
    renderSemitono();
}

const element = (tag, className, text = "") => Object.assign(document.createElement(tag), { className, textContent: text });

// One line: its bar button, its chords over it (the melody's note changes underlined), its syllables.
function semitonoLine(text, i, plan, f, ex, onBar) {
    const b = plan?.[i];
    const line = element("div", "sem-line");
    const bar = element("button", "sem-bar", b === undefined ? "·" : b === "flexa" ? "f" : String(b + 1));
    bar.type = "button";
    bar.title = "Bar of this line: click for the next";
    bar.addEventListener("click", onBar);
    let chords = [], spots = null, marks = [];
    const block = element("div", "sem-text");
    if (b === "flexa") {
        [chords, spots] = [f.flexa, f.spots?.flexa];
        marks = syllableMarks(text, spots, true, ex);
    } else if (b !== undefined) {
        [chords, spots] = [f.bars[b], f.spots?.bars[b]];
        const shared = plan[i + 1] === b ? 0 : plan[i - 1] === b ? 1 : -1; // two lines, one bar
        if (shared < 0) marks = syllableMarks(text, spots, true, ex);
        else {
            marks = shared ? syllableMarks(text, spots, false, ex) : [];
            [chords, spots] = splitBar(chords, spots)[shared];
            block.classList.add("bar-shared");
        }
    }
    const lyric = element("div", "sem-lyric");
    let at = 0;
    for (const [start, end, notes] of marks.sort((x, y) => x[0] - y[0])) {
        lyric.append(text.slice(at, start), element("span", notes > 1 ? "syl syl2" : "syl", text.slice(start, end)));
        at = end;
    }
    lyric.append(text.slice(at));
    const units = lineSyllables(text, ex), accent = units.findLastIndex((u) => u.stress), own = song.semitono.stress?.[stressKey(text)];
    const chips = element("div", "sem-syllables");
    units.forEach((u, k) => {
        const chip = element("button", k === accent ? "stressed" : "",
            text.slice(u.col, units[k + 1]?.col ?? text.length).replace(/^[^\p{L}]+|[^\p{L}]+$/gu, ""));
        chip.type = "button";
        chip.addEventListener("click", () => setStress(text, k + 1));
        chips.append(chip);
    });
    if (own) {
        const clear = element("button", "clear", "×");
        Object.assign(clear, { type: "button", title: "Back to the line's own stress" });
        clear.addEventListener("click", () => setStress(text, null));
        chips.append(clear);
    }
    block.append(element("div", "sem-chords", chords.length ? chordLineText(text, chords, spots, ex) : ""), lyric, chips);
    line.append(bar, block);
    return line;
}

function renderSemitono() {
    const psalm = pickedTags().some(([tag]) => (book.psalm_tags || []).includes(tag));
    $("semitono").hidden = !semitonos.length || !psalm;
    if ($("semitono").hidden) return;
    const s = semitonos.find((x) => x.id === $("semitono-pick").value) || semitonos[0];
    const f = { size: s.size, bars: s.chords, flexa: s.flexa, spots: s.abc ? chordSpots(s.abc) : null };
    const ex = semitonoEx();
    // next bar: 1 … size, then the flexa (de 2 with one), then 1 again
    const next = (b) => (b === "flexa" ? 0 : b + 1 < f.size ? b + 1 : f.size === 2 && f.flexa ? "flexa" : 0);
    $("semitono-verses").replaceChildren(...psalmVerses().map((lines, v) => {
        const texts = gloriaSplit(lines, f.size), verse = v + 1;
        const own = song.semitono.bars?.[f.size]?.[verse];
        const plan = versePlan(texts, f, ex, verse);
        const box = element("div", own && own.length !== texts.length ? "sem-verse wrong" : "sem-verse");
        texts.forEach((text, i) => box.append(semitonoLine(text, i, plan, f, ex, () => {
            const bars = [...(plan ?? texts.map(() => 0))];
            bars[i] = next(bars[i]);
            setOwnBars(f.size, verse, bars);
        })));
        if (own) {
            const reset = element("button", "link", own.length !== texts.length
                ? `reset (its bars are for ${own.length} lines, it has ${texts.length})` : "reset");
            reset.type = "button";
            reset.addEventListener("click", () => setOwnBars(f.size, verse, null));
            box.append(reset);
        }
        return box;
    }));
    $("splits").replaceChildren(...Object.entries(song.semitono.split || {}).map(([word, parts]) => {
        const item = element("li", "", `${word}: ${parts} `);
        const remove = element("button", "link", "×");
        Object.assign(remove, { type: "button", title: "Remove" });
        remove.addEventListener("click", () => {
            delete song.semitono.split[word];
            if (!Object.keys(song.semitono.split).length) delete song.semitono.split;
            renderSemitono();
        });
        item.append(remove);
        return item;
    }));
}

$("split-add").addEventListener("click", () => {
    const word = $("split-word").value.trim().toLowerCase(), parts = $("split-syllables").value.trim().toLowerCase();
    if (!word || !parts.includes("-") || parts.replace(/-/g, "") !== word)
        return say(`Syllables must be the word with - between them, like si-ón`, true);
    (song.semitono.split ||= {})[word] = parts;
    $("split-word").value = $("split-syllables").value = "";
    renderSemitono();
});
$("semitono-pick").addEventListener("change", () => {
    localStorage.setItem(SEMITONO_PICK, $("semitono-pick").value);
    renderSemitono();
});
$("tag-boxes").addEventListener("change", renderSemitono);

// ---------- sources ----------

document.querySelectorAll("[data-src]").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll(".panel").forEach((panel) => { panel.hidden = panel.id !== "src-" + button.dataset.src; });
}));

function fillFrom(data) {
    setText(data);
    if (data.capo) $("capo").value = data.capo;
    if (data.title !== undefined) $("title").value = data.title;
    if (data.artist) $("autor").value = data.artist;
    if (data.site_artist !== undefined) song.siteArtist = data.site_artist;
}

$("paste-go").addEventListener("click", () => run("Cleaning the text...", async () =>
    fillFrom(await api("/api/paste", { text: $("paste-text").value }))));

async function fetchSong(link) {
    fillFrom(await api("/api/fetch", { link }));
    $("link").value = link;
}

$("fetch-go").addEventListener("click", () => run("Reading the page...", () => fetchSong($("fetch-link").value)));

$("search-go").addEventListener("click", () => run("Searching...", async () => {
    const results = await api("/api/search", { title: $("search-title").value, artist: $("search-artist").value });
    $("results").replaceChildren(...results.map((r) => {
        const item = document.createElement("li"), button = document.createElement("button");
        button.type = "button";
        button.textContent = `${r.site}: ${r.label}`;
        button.addEventListener("click", () => run("Reading the page...", () => fetchSong(r.url)));
        item.append(button);
        return item;
    }));
    if (!results.length) say("No results");
}));

$("find-link").addEventListener("click", () => run("Looking for a link...", async () => {
    const found = await api("/api/links", { title: $("title").value, autor: $("autor").value });
    const choices = found.spotify.map((t) => [t.label, t.url]);
    if (found.youtube) choices.push(["YouTube", found.youtube]);
    $("link-choices").replaceChildren(...choices.map(([label, url]) => {
        const item = document.createElement("li"), button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.addEventListener("click", () => { $("link").value = url; $("link-choices").replaceChildren(); });
        item.append(button);
        return item;
    }));
    if (!choices.length) say("No link found");
}));

// ---------- the form ----------

const lines = (text) => text.split("\n").map((l) => l.trim()).filter(Boolean);
const tagKey = (tag, sub) => JSON.stringify([tag, sub]);

function renderTags(picked) {
    $("tag-boxes").replaceChildren(...book.tags.map((t) => {
        const label = document.createElement("label"), box = document.createElement("input");
        box.type = "checkbox";
        box.dataset.tag = t.tag;
        box.dataset.sub = t.sub ?? "";
        box.checked = picked.has(tagKey(t.tag, t.sub));
        label.append(box, " " + t.label);
        return label;
    }));
}

function showSong(data) { // data: /api/song, or {} for a new song
    const tags = data.tags || {};
    const picked = new Set(), shown = new Set(book.tags.map((t) => tagKey(t.tag, t.sub)));
    song.extraTags = []; // the song's tags with no checkbox (strict books hide some): kept when saving
    for (const [tag, subs] of Object.entries(tags))
        for (const sub of subs.length ? subs : [null])
            if (shown.has(tagKey(tag, sub))) picked.add(tagKey(tag, sub));
            else song.extraTags.push([tag, sub, null, null]);
    renderTags(picked);
    song.id = data.id || null;
    song.base = data;
    song.siteArtist = "";
    $("title").value = data.title || "";
    $("autor").value = data.id ? data.autor || "" : book.default_author || "";
    $("capo").value = data.capo ?? "";
    $("link").value = data.link || "";
    $("horas").value = (data.horas || []).join("\n");
    $("ignore").value = (data.ignore || []).join("\n");
    $("new-tags").value = "";
    window.editorMelody.load(data.melody || "", data.tab || ""); // melody-editor.js; sets the checkboxes
    $("report").textContent = "";
    $("link-choices").replaceChildren();
    $("results").replaceChildren();
    song.semitono = structuredClone(data.semitono || {});
    setText({ body: data.body || "", rows: data.rows || [] });
}

async function pick(id) {
    if (!id) return showSong({});
    const data = await api("/api/song?id=" + encodeURIComponent(id));
    showSong({ ...data, rows: (await api("/api/rows", { body: data.body })).rows });
}

function fillPicker(selected) {
    $("picker").replaceChildren(new Option("(new song)", ""), ...book.songs.map((s) => new Option(s.title + (s.autor ? " - " + s.autor : ""), s.id)));
    $("picker").value = selected || "";
}

$("picker").addEventListener("change", () => run("Opening...", () => pick($("picker").value)));

// Song search, ranked as the book's (web/js/search.js): title start, title words, author, lyric phrase, any words.
const searchText = (t) => (t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\p{L}\p{N}]+/gu, " ").trim();

function findSongs(query) {
    const phrase = searchText(query), words = phrase.split(" ");
    if (!phrase) return [];
    const hasAll = (text) => words.every((w) => text.includes(w));
    return book.songs.map((s, order) => {
        const title = searchText(s.title), autor = searchText(s.autor), lines = s.lyrics.map(searchText);
        const lyrics = " " + lines.join(" ") + " ";
        const rank = title.startsWith(phrase) ? 1 : hasAll(title) ? 2 : hasAll(autor) ? 3
            : lyrics.includes(" " + phrase) ? 4 : hasAll(title + " " + autor + lyrics) ? 5 : null;
        let i = rank >= 4 ? lines.findIndex((l) => (" " + l).includes(" " + phrase)) : -1;
        if (rank === 5 && i < 0) i = lines.findIndex((l) => l.includes(words[0]));
        return { s, order, rank, snippet: i >= 0 ? s.lyrics[i] : "" };
    }).filter((h) => h.rank !== null).sort((a, b) => a.rank - b.rank || a.order - b.order).slice(0, 50);
}

function showFound() {
    const found = findSongs($("song-find").value);
    $("song-found").replaceChildren(...(found.length ? found.map(({ s, snippet }) => {
        const item = document.createElement("button");
        item.type = "button";
        item.dataset.song = s.id;
        item.textContent = s.title + (s.autor ? " - " + s.autor : "");
        if (snippet) item.append(Object.assign(document.createElement("span"), { textContent: snippet }));
        return item;
    }) : [Object.assign(document.createElement("div"), { textContent: "No songs found" })]));
    $("song-found").hidden = !$("song-find").value.trim();
}

$("song-find").addEventListener("input", showFound);
$("song-find").addEventListener("focus", showFound);
$("song-find").addEventListener("keydown", (e) => {
    if (e.key === "Escape") { $("song-find").value = ""; $("song-found").hidden = true; }
    if (e.key === "Enter") $("song-found").querySelector("button")?.click();
});
$("song-found").addEventListener("click", (e) => {
    const id = e.target.closest("button")?.dataset.song;
    if (!id) return;
    $("song-find").value = "";
    $("song-found").hidden = true;
    $("picker").value = id;
    $("picker").dispatchEvent(new Event("change"));
});
document.addEventListener("click", (e) => { if (!$("song-search").contains(e.target)) $("song-found").hidden = true; });

function pickedTags() {
    const chosen = [...document.querySelectorAll("#tag-boxes input:checked")].map((b) => [b.dataset.tag, b.dataset.sub || null, null, null]);
    const typed = book.strict_tags ? [] : $("new-tags").value.split(",").map((t) => t.trim()).filter(Boolean).map((t) => {
        const [tag, sub] = t.split("/").map((s) => s.trim());
        return [tag, sub || null, tag, sub || null];
    });
    return [...song.extraTags, ...chosen, ...typed];
}

async function save(force = false) {
    const extra = window.editorMelody?.value?.() || {};
    const data = {
        id: song.id, force, site_artist: song.siteArtist,
        title: $("title").value, autor: $("autor").value, capo: String($("capo").value), link: $("link").value,
        body: currentBody(), tags: pickedTags(),
        horas: book.has_horas ? lines($("horas").value) : song.base.horas || [],
        ignore: lines($("ignore").value),
        melody: extra.melody ?? song.base.melody ?? "", tab: extra.tab ?? song.base.tab ?? "",
        semitono: song.semitono, // {} removes it
    };
    let result;
    try {
        result = await api("/api/save", data);
    } catch (e) {
        if (e.status === 409 && e.body.exists && confirm(`${e.body.exists} already exists. Add anyway?`)) return save(true);
        throw e;
    }
    $("report").textContent = result.report;
    song.id = result.id;
    book = await api("/api/book");
    fillPicker(result.id);
    say("Saved " + result.file);
}

$("save").addEventListener("click", () => run("Saving...", () => save()));
$("publish").addEventListener("click", () => run("Publishing...", async () => {
    $("report").textContent = (await api("/api/publish", {})).output;
}));

(async () => {
    try {
        book = await api("/api/book");
        $("horas-label").hidden = !book.has_horas;
        $("new-tags-label").hidden = book.strict_tags;
        semitonos = await api("/api/formulas");
        $("semitono-pick").replaceChildren(...semitonos.map((s) => new Option(s.title, s.id)));
        $("semitono-pick").value = localStorage.getItem(SEMITONO_PICK) || "";
        if ($("semitono-pick").selectedIndex < 0) $("semitono-pick").selectedIndex = 0;
        fillPicker("");
        showSong({});
    } catch (e) { say(e.message, true); }
})();
