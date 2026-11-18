"use strict";
const TOKEN = document.querySelector("meta[name=token]").content;
const $ = (id) => document.getElementById(id);

let book = null;
// rows: the chord view; body: the song text (rows are only written back into it once a chord changed: `dirty`)
let song = { id: null, rows: [], body: "", dirty: false, textMode: false, siteArtist: "", extraTags: [], base: {} };

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
    span.className = "chord";
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

// Lyric and text lines are typed into in place; no re-render while typing so the caret stays put.
function editable(element, store) {
    element.contentEditable = "plaintext-only";
    element.spellcheck = false;
    element.addEventListener("keydown", (e) => { if (e.key === "Enter") e.preventDefault(); });
    element.addEventListener("input", () => {
        store(element.textContent.replace(/\n/g, ""));
        song.dirty = true;
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
            editable(block, (value) => { row.text = value; });
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
                editable(lyric, (value) => { row.lyric = value; });
                block.append(lyric);
            }
        }
        (verse ? verse.lastChild : grid).append(block);
    });
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
        fillPicker("");
        showSong({});
    } catch (e) { say(e.message, true); }
})();
