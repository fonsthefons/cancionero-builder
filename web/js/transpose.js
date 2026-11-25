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

// Songs with a key (data-key, builder/keys.py) move each note by interval within
// the key: it keeps its letter distance from the tonic (E in C -> F# in D), so the
// spelling chosen in the song file carries over (Bb, not A#, in F; G#7 before C#m).
// Notes that would need E#, B#, Cb, Fb or a double accidental take the new key's
// sharps or flats instead.
const LETTERS = "CDEFGAB";
const NATURAL = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const MAJOR_KEYS = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
const MINOR_KEYS = ["Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm"];
const FLAT_KEYS = new Set(["F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb", "Dm", "Gm", "Cm", "Fm", "Bbm", "Ebm", "Abm"]);

function pitchOf(note) {
    return (NATURAL[note[0]] + (note[1] === "#" ? 1 : note[1] === "b" ? -1 : 0) + 12) % 12;
}

// The song's key moved `shift` semitones: { name, from, to, flats } (from/to: tonics).
function movedKey(key, shift) {
    const minor = key.endsWith("m");
    const tonic = minor ? key.slice(0, -1) : key;
    const name = shift ? (minor ? MINOR_KEYS : MAJOR_KEYS)[(pitchOf(tonic) + shift + 120) % 12] : key;
    return { name, from: tonic, to: minor ? name.slice(0, -1) : name, flats: FLAT_KEYS.has(name) };
}

function moveNote(note, shift, key) {
    const steps = (LETTERS.indexOf(note[0]) - LETTERS.indexOf(key.from[0]) + 7) % 7;
    const letter = LETTERS[(LETTERS.indexOf(key.to[0]) + steps) % 7];
    const pc = (pitchOf(note) + shift + 120) % 12;
    const accidental = ((pc - NATURAL[letter] + 18) % 12) - 6;
    const name = letter + ({ 1: "#", "-1": "b", 0: "" }[accidental] ?? "?");
    if (!name.includes("?") && !["E#", "B#", "Cb", "Fb"].includes(name)) return name;
    return (key.flats ? NOTES_FLAT : NOTES_SHARP)[pc];
}

// Chord names: letters (C D E) or solfège (Do Re Mi), a book-wide setting.
const NOTATIONS = { letters: "C D E", solfege: "Do Re Mi" };
const SOLFEGE = { C: "Do", D: "Re", E: "Mi", F: "Fa", G: "Sol", A: "La", B: "Si" };

// Transposes the root and the bass note: D/F# +2 -> E/G# (or Mi/Sol#).
// key: movedKey(...) for songs with a key, else null (sharps stay sharps).
function transposeChord(chord, shift, key = null) {
    const name = !shift ? chord
        : chord.replace(NOTE_RE, (note) => (key ? moveNote(note, shift, key) : transposeNote(note, shift)));
    return inNotation(name);
}

function inNotation(name) {
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

function transposeChordLine(line, shift, key) {
    const parts = chordLineParts(line);
    let drift = 0; // columns the next chord would move right (or left if < 0)
    setChordLine(line, parts.map((part, i) => {
        if (i % 2) {
            const chord = transposeChord(part, shift, key);
            drift += chord.length - part.length;
            return chord;
        }
        let gap;
        [gap, drift] = adjustGap(part, drift, i === parts.length - 1);
        return gap;
    }));
}

// "Intro: G Em ..." lines mix chords and words, so their chords keep a span each.
function transposeInlineChords(line, shift, key) {
    const nodes = [...line.childNodes];
    let drift = 0; // columns the next chord would move right (or left if < 0)

    nodes.forEach((node, i) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
            node.dataset.original ??= node.textContent;
            const chord = transposeChord(node.dataset.original, shift, key);
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
    const key = song.dataset.key ? movedKey(song.dataset.key, shift) : null;
    const keyLabel = song.querySelector(".song-key");
    if (keyLabel) keyLabel.textContent = `Key: ${inNotation(key.name)}`;
    if (!builtChars.has(song)) builtChars.set(song, Number(song.style.getPropertyValue("--chars")));
    let widest = builtChars.get(song);
    song.querySelectorAll(".chord-line, .chord-inline").forEach((line) => {
        if (line.classList.contains("chord-line")) transposeChordLine(line, shift, key);
        else transposeInlineChords(line, shift, key);
        widest = Math.max(widest, line.textContent.length);
    });
    song.style.setProperty("--chars", widest);
    // melody.js is only in books with melodies, so name refreshMelody only when there is one.
    song.querySelectorAll(".melody").forEach((melody) => refreshMelody(melody));
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
