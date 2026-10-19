// Transpose the chords of one song up or down by semitones.
//
// Chords are aligned by hand to exact letters, so transposing must never move
// a chord to another column. When a chord name gets longer (C -> C#) or
// shorter (C# -> D), the spaces after it shrink or grow to compensate, so
// every following chord still starts at its original column.

const NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const NOTES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const NOTE_RE = /[A-G][#b]?/g; // chord suffixes (m, maj7, sus4...) are lowercase

function transposeNote(note, shift) {
    const scale = note.includes("b") ? NOTES_FLAT : NOTES_SHARP;
    const index = scale.indexOf(note);
    if (index === -1) return note;
    return scale[(((index + shift) % 12) + 12) % 12];
}

// Chord names: letters (C D E) or solfège (Do Re Mi), a book-wide setting.
const NOTATIONS = { letters: "C D E", solfege: "Do Re Mi" };
const SOLFEGE = { C: "Do", D: "Re", E: "Mi", F: "Fa", G: "Sol", A: "La", B: "Si" };

// Transposes the root and the bass note: D/F# +2 -> E/G# (or Mi/Sol#)
function transposeChord(chord, shift) {
    const name = chord.replace(NOTE_RE, (note) => transposeNote(note, shift));
    if (document.body.dataset.notation !== "solfege") return name;
    return name.replace(/[A-G]/g, (letter) => SOLFEGE[letter]); // Am7 -> Lam7
}

// Original text between chords (spaces and separators like "(", ")", "|"),
// before any transposition.
const originalGaps = new WeakMap();

// Make a gap between chords `drift` columns shorter (drift > 0) or longer
// (drift < 0) by changing its runs of spaces, so the next chord stays put.
// Separators stay attached to their chord, and at least one space is kept
// wherever there was one. Returns [new text, drift that could not be absorbed].
function adjustGap(text, drift, isLastNode) {
    if (drift < 0) {
        const run = text.search(/ /);
        if (run === -1) return isLastNode ? [text, 0] : [text, drift];
        return [text.slice(0, run) + " ".repeat(-drift) + text.slice(run), 0];
    }
    const parts = text.split(/( +)/); // odd indexes are runs of spaces
    for (let i = 1; i < parts.length && drift > 0; i += 2) {
        const atEnd = isLastNode && i === parts.length - 2 && parts[i + 1] === "";
        const removable = parts[i].length - (atEnd ? 0 : 1);
        const removed = Math.max(0, Math.min(drift, removable));
        parts[i] = parts[i].slice(removed);
        drift -= removed;
    }
    return [parts.join(""), drift];
}

// Chord line as first built: [gap, chord, gap, chord, ..., gap]. The words
// outside .sep spans are the chords (lyrics.py chord_line_html); gaps are the
// spaces and separators between them.
const originalChordLines = new WeakMap();

function chordLineParts(line) {
    if (!originalChordLines.has(line)) {
        const parts = [""];
        line.childNodes.forEach((node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
                parts[parts.length - 1] += node.textContent; // separator
                return;
            }
            node.data.split(/( +)/).forEach((piece, i) => {
                if (i % 2 || !piece) parts[parts.length - 1] += piece;
                else parts.push(piece, "");
            });
        });
        originalChordLines.set(line, parts);
    }
    return originalChordLines.get(line);
}

// Write a chord line back: text, with each separator in its .sep span.
function setChordLine(line, parts) {
    const nodes = [];
    let text = "";
    parts.forEach((part, i) => {
        if (i % 2) {
            text += part;
            return;
        }
        part.split(/(\S+)/).forEach((piece, j) => {
            if (!(j % 2)) {
                text += piece;
                return;
            }
            if (text) nodes.push(text);
            text = "";
            nodes.push(Object.assign(document.createElement("span"), { className: "sep", textContent: piece }));
        });
    });
    if (text) nodes.push(text);
    line.replaceChildren(...nodes);
}

function transposeChordLine(line, shift) {
    const parts = chordLineParts(line);
    let drift = 0; // columns the next chord would move right (or left if < 0)
    setChordLine(line, parts.map((part, i) => {
        if (i % 2) {
            const chord = transposeChord(part, shift);
            drift += chord.length - part.length;
            return chord;
        }
        let gap;
        [gap, drift] = adjustGap(part, drift, i === parts.length - 1);
        return gap;
    }));
}

// "Intro: G Em ..." lines mix chords and words, so their chords keep a span each.
function transposeInlineChords(line, shift) {
    const nodes = [...line.childNodes];
    let drift = 0; // columns the next chord would move right (or left if < 0)

    nodes.forEach((node, i) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
            node.dataset.original ??= node.textContent;
            const chord = transposeChord(node.dataset.original, shift);
            drift += chord.length - node.dataset.original.length;
            node.textContent = chord;
            return;
        }
        if (!originalGaps.has(node)) originalGaps.set(node, node.data);
        [node.data, drift] = adjustGap(originalGaps.get(node), drift, i === nodes.length - 1);
    });
}

// Widest line of each song as built (--chars, see render.py).
const builtChars = new WeakMap();

// Rewrite a song's chords for its transposition and the current notation.
// Longer names (Sol#m vs G#m) can push a line past the widest one, so --chars
// grows with it and the lyrics still fit the screen.
function renderChords(song) {
    const shift = Number(song.dataset.transpose || 0);
    if (!builtChars.has(song)) builtChars.set(song, Number(song.style.getPropertyValue("--chars")));
    let widest = builtChars.get(song);
    song.querySelectorAll(".chord-line, .chord-inline").forEach((line) => {
        if (line.classList.contains("chord-line")) transposeChordLine(line, shift);
        else transposeInlineChords(line, shift);
        widest = Math.max(widest, line.textContent.length);
    });
    song.style.setProperty("--chars", widest);
}

function setTranspose(song, shift) {
    song.dataset.transpose = shift;
    renderChords(song);
    song.querySelector(".transpose-value").textContent = shift > 0 ? `+${shift}` : shift;
    songState.set(song, "transpose", shift || null); // remembered on this device
}

// Steps through -11..+11; one more step wraps back to 0 (same key).
function stepTranspose(song, step) {
    const shift = Number(song.dataset.transpose || 0) + step;
    setTranspose(song, Math.abs(shift) === 12 ? 0 : shift);
}

onAction("transpose-up", (button, song) => stepTranspose(song, +1));
onAction("transpose-down", (button, song) => stepTranspose(song, -1));
onAction("transpose-reset", (button, song) => setTranspose(song, 0));

// Restore the transpositions saved on this device.
songState.each("transpose", (song, shift) => {
    const valid = Number.isInteger(shift) && Math.abs(shift) < 12;
    setTranspose(song, valid ? shift : 0);
});

function setNotation(notation) {
    if (!(notation in NOTATIONS)) notation = "letters";
    const changed = notation !== (document.body.dataset.notation || "letters");
    document.body.dataset.notation = notation;
    prefs.set("notation", notation);
    setActionLabel("cycle-notation", NOTATIONS[notation]);
    if (changed) document.querySelectorAll(".song").forEach(renderChords);
}

onAction("cycle-notation", () => {
    setNotation(document.body.dataset.notation === "solfege" ? "letters" : "solfege");
});
// Books without the setting (book.yaml notation_setting: false) always show letters.
if (BOOK.notationSetting) setNotation(prefs.get("notation", "letters"));
