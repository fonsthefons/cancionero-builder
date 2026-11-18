"use strict";
// Melody and guitar tab of the song editor (index.html #melody): an ABC textarea and an
// editable staff kept in sync, the book's look (melody.js renderMelody) with Play, and
// one fret/string input per note. editor.js calls load() when a song opens and value() to save.
(() => {
    const $ = (id) => document.getElementById(id);
    const OPEN = [64, 59, 55, 50, 45, 40]; // midi of the open strings 1 (high e) .. 6 (low E)
    const STEPS = "CDEFGAB";
    const NOTE = /"[^"]*"|![^!]*!|([_^=]*)([A-Ga-g])([,']*)(\d*(?:\/+\d*)?)/g; // group 2 set: a note
    const DEFAULT = "K:C\nC";

    let selected = null; // startChar (abcjs) of the selected note
    let tokens = []; // per note: the fret/string the user typed (kept when notes change), or empty
    let loadedTab = "";
    let freeTab = null; // the tab as text when it doesn't fit the notes (no melody, other count): saved as typed
    let tune = null;

    const abc = () => $("abc").value;

    // builder/songs.py check_tab's count: pitch letters outside "chords", !decorations! and header lines.
    function noteCount(text) {
        const body = text.replace(/^[A-Za-z]:.*$/gm, "").replace(/"[^"]*"|![^!]*!/g, "");
        return (body.match(/[A-Ga-g]/g) || []).length;
    }

    // check_tab's error text, or "".
    function tabError(melody, tab) {
        const found = tab.split(/\s+/).filter((t) => t.replace(/\|/g, ""));
        const bad = found.find((t) => !/^\d{1,2}\/[1-6]$/.test(t));
        if (bad !== undefined) return `tab: "${bad}" is not fret/string (like 2/1, string 1 = high e … 6 = low E)`;
        const notes = noteCount(melody);
        return found.length === notes ? "" : `tab has ${found.length} notes but melody has ${notes}`;
    }

    // The first note at or after `start` (skipping a "chord" or !decoration! before it).
    function noteAt(start) {
        for (const m of abc().slice(start).matchAll(NOTE)) {
            if (!m[2]) continue;
            const at = start + m.index;
            return { start: at, end: at + m[0].length, acc: m[1], letter: m[2], octave: m[3], length: m[4],
                     pitchStart: at + m[1].length, pitchEnd: at + m[1].length + m[2].length + m[3].length };
        }
        return null;
    }

    // Staff steps from C, (C = 0, c = 7, c' = 14, C, = -7) and back.
    function stepOf(n) {
        const marks = (mark) => n.octave.split(mark).length - 1;
        return STEPS.indexOf(n.letter.toUpperCase()) + 7 * ((n.letter >= "a") + marks("'") - marks(","));
    }
    function spell(step) {
        const octave = Math.floor(step / 7), letter = STEPS[step - 7 * octave];
        return octave > 0 ? letter.toLowerCase() + "'".repeat(octave - 1) : letter + ",".repeat(-octave);
    }

    // An ABC length ("", "2", "/", "3/2"...) times up/down.
    function scaleLength(length, up, down) {
        const [, num, slashes, den] = length.match(/^(\d*)(\/*)(\d*)$/);
        let n = Number(num || 1) * up, d = (slashes ? Number(den || 2 ** slashes.length) : 1) * down;
        const gcd = (a, b) => (b ? gcd(b, a % b) : a), g = gcd(n, d);
        n /= g;
        d /= g;
        return (n === 1 ? "" : String(n)) + (d === 1 ? "" : "/" + d);
    }

    function replace(start, end, text, select) {
        $("abc").value = abc().slice(0, start) + text + abc().slice(end);
        selected = select;
        update();
    }

    function edit(action, steps = 0) {
        const n = selected === null ? null : noteAt(selected);
        if (!n) return;
        const index = noteCount(abc().slice(0, n.start)); // the note's tab token
        if (action === "move") replace(n.pitchStart, n.pitchEnd, spell(stepOf(n) + steps), selected);
        else if (action === "delete") {
            tokens.splice(index, 1);
            const after = abc()[n.end] === " ", before = !after && abc()[selected - 1] === " "; // and one space
            replace(selected - (before ? 1 : 0), n.end + (after ? 1 : 0), "", null);
        } else if (action === "copy") {
            tokens.splice(index + 1, 0, "");
            replace(n.end, n.end, " " + abc().slice(n.start, n.end), n.end + 1);
        } else if (action === "longer" || action === "shorter") {
            const length = action === "longer" ? scaleLength(n.length, 2, 1) : scaleLength(n.length, 1, 2);
            replace(n.pitchEnd, n.end, length, selected);
        } else replace(n.start, n.pitchStart, n.acc === action ? "" : action, selected); // ^ _ =: toggle
    }

    // abcjs calls this on a click (drag.step 0) or at the end of a drag (or arrow keys).
    function clicked(element, _tune, _classes, _analysis, drag) {
        if (element.el_type !== "note" || !element.pitches) return; // rests, bars, clef...
        selected = element.startChar;
        // quirk: drag.step counts staff steps downwards (screen y), so up is negative
        if (drag?.step) edit("move", -drag.step);
    }

    // The midi pitch of each sounding note (abcjs: key signature and accidentals applied).
    // shortcut: tied notes sound once and chords give several, so later notes can take a
    // neighbour's pitch; only the suggested frets suffer (the user can type them).
    function midiPitches() {
        tune.setUpAudio({ chordsOff: true });
        return tune.setTiming().flatMap((event) => (event.midiPitches || [])
            .filter((p) => p.cmd === "note").map((p) => p.pitch));
    }

    // fret/string for `pitch` (an octave moved into range), frets 0-12 nearest `previous`.
    function suggest(pitch, previous) {
        while (pitch < OPEN[5]) pitch += 12;
        while (pitch > OPEN[0] + 12) pitch -= 12;
        let best = null;
        OPEN.forEach((open, i) => {
            const fret = pitch - open;
            if (fret >= 0 && fret <= 12 && (!best || Math.abs(fret - previous) < Math.abs(best[0] - previous))) best = [fret, i + 1];
        });
        return best.join("/");
    }

    function tabValue() {
        if (freeTab !== null) return freeTab;
        const tab = [...$("tab-inputs").querySelectorAll("input")].map((i) => i.value.trim()).filter(Boolean).join(" ");
        const plain = (t) => t.split(/\s+/).filter((x) => x.replace(/\|/g, "")).join(" ");
        return tab === plain(loadedTab) ? loadedTab : tab; // unchanged: keep its bars and spacing
    }

    function look() {
        let element = $("melody-look").querySelector(".melody");
        if (!element) { // made here, not in the page: melody.js would draw it (empty) when it comes on screen
            element = document.createElement("div");
            element.className = "melody";
            $("melody-look").prepend(element);
        }
        element.dataset.abc = abc();
        element.dataset.tab = $("has-tab").checked ? tabValue() : "";
        if (noteCount(abc())) renderMelody(element);
        else element.replaceChildren();
    }

    function showTabError() {
        $("tab-error").textContent = tabError(abc(), tabValue());
    }

    function renderTab() {
        if (freeTab !== null) {
            const area = document.createElement("textarea");
            area.value = freeTab;
            area.setAttribute("aria-label", "Guitar tab");
            area.addEventListener("input", () => {
                freeTab = area.value;
                showTabError();
                look();
            });
            $("tab-inputs").replaceChildren(area);
            return showTabError();
        }
        const count = noteCount(abc()), pitches = count ? midiPitches() : [];
        let fret = 0;
        const inputs = [];
        for (let i = 0; i < count; i++) {
            const input = document.createElement("input");
            input.value = tokens[i] || suggest(pitches[i] ?? pitches.at(-1) ?? OPEN[0], fret);
            fret = Number(input.value.split("/")[0]) || fret;
            input.addEventListener("input", () => {
                tokens[i] = input.value.trim();
                showTabError();
                look();
            });
            inputs.push(input);
        }
        $("tab-inputs").replaceChildren(...inputs);
        showTabError();
    }

    function update() {
        [tune] = ABCJS.renderAbc("melody-staff", abc(), { dragging: true, add_classes: true, clickListener: clicked });
        if (selected !== null) tune.getElementFromChar(selected)?.abselem?.highlight();
        if ($("has-tab").checked) renderTab();
        look();
    }

    function show() {
        const on = $("has-melody").checked;
        $("melody-edit").hidden = !on;
        $("tab-edit").hidden = !on || !$("has-tab").checked;
        if (on) update();
    }

    $("abc").addEventListener("input", () => { selected = null; update(); });
    $("has-melody").addEventListener("change", show);
    $("has-tab").addEventListener("change", show);
    document.querySelectorAll("[data-note]").forEach((button) => button.addEventListener("click", () => edit(button.dataset.note)));
    $("melody-staff").addEventListener("keydown", (e) => {
        if (e.key === "Delete" || e.key === "Backspace") edit("delete");
    });

    window.editorMelody = {
        load(melody, tab) {
            $("has-melody").checked = !!melody;
            $("has-tab").checked = !!tab;
            $("abc").value = melody || DEFAULT;
            loadedTab = tab || "";
            tokens = loadedTab.split(/\s+/).filter((t) => t.replace(/\|/g, ""));
            freeTab = loadedTab && tokens.length !== noteCount(melody || "") ? loadedTab : null;
            selected = null;
            $("tab-inputs").replaceChildren(); // not the last song's
            show();
        },
        value() { // the tab stays (even without a melody) until "Guitar tab" is unchecked
            return { melody: $("has-melody").checked ? abc() : "", tab: $("has-tab").checked ? tabValue() : "" };
        },
    };
})();
