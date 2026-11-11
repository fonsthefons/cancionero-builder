// Staff and guitar tab of songs with `melody:` (render.py melody_html), drawn
// with abcjs (web/vendor; it and this file are only in books with melodies).
//
// renderMelody(element, shift) draws one .melody and needs only abcjs, so a
// standalone page can reuse it. In the book a song's melody is drawn when the
// song comes near the screen (off-screen songs are skipped, see styles.css
// .song), when printing, and again when transposed or the notation changes
// (transpose.js renderChords calls refreshMelody).

const TAB_LINE = 10; // space between tab lines, in staff units
const TAB_GAP = 12; // between the staff (and notes under it) and the tab: 1.5 staff spaces

const melodyTunes = new WeakMap(); // .melody -> its abcjs tune, for playing

function renderMelody(element, shift = 0, width = 380) {
    if (playing?.element === element) stopMelody(); // redrawn: the notes to light are gone
    const abc = element.dataset.abc;
    const staff = document.createElement("div");
    element.replaceChildren(staff);
    // staffwidth: the size a phone shows at about 1:1 (the SVG scales to the width).
    const [tune] = ABCJS.renderAbc(staff, abc, {
        responsive: "resize", staffwidth: width, visualTranspose: shift, add_classes: true,
        paddingtop: 0, paddingbottom: 0, paddingleft: 0, paddingright: 0,
    });
    const svg = staff.querySelector("svg");
    const space = svg.querySelector(".abcjs-staff").getBBox().height / 4; // between staff lines

    // Chord names like the song's chord lines (transpose.js: sharps or flats, Do Re Mi).
    if (typeof transposeChord === "function") {
        const chords = [...abc.matchAll(/"([^"]*)"/g)].map((m) => m[1]);
        svg.querySelectorAll(".abcjs-chord").forEach((text, i) => {
            if (chords[i] !== undefined) text.textContent = transposeChord(chords[i], shift);
        });
    }

    // Reciting notes (breves, C8) square like hand-written chant. The notehead is
    // the path named after its pitch (others: "ledger", "accidentals.sharp"...).
    svg.querySelectorAll(".abcjs-note.abcjs-d2 > path").forEach((path) => {
        if (/^[_^=]*[A-Ga-g]/.test(path.dataset.name)) squareNotehead(path, space);
    });

    melodyTunes.set(element, tune);
    if (!element.dataset.tab) return; // staff only, no tab lines
    const tab = tabSvg(svg, element.dataset.tab, shift);
    element.append(tab);
    // Two-digit frets on short notes can touch: draw a wider staff (it scales to fit,
    // so notes get more room) until frets on the same string clear each other.
    const boxes = [...tab.querySelectorAll("text:not(.melody-tab-label)")].map((t) => t.getBBox());
    const touch = boxes.some((b, i) => i && b.y === boxes[i - 1].y && b.x < boxes[i - 1].x + boxes[i - 1].width + 5);
    if (touch && width < 600) renderMelody(element, shift, width + 40);
}

// The breve glyph (an oval between bars) redrawn as |□|: a hollow square with
// thick top and bottom, between two thin bars that stick out above and below.
function squareNotehead(path, space) {
    const box = path.getBBox();
    const x = box.x + box.width / 2 - space * 0.7, y = box.y + box.height / 2;
    const rect = (left, top, width, height) => `M${left} ${top}h${width}v${height}h${-width}z`;
    const thick = space * 0.3, thin = space * 0.15;
    path.setAttribute("d", rect(x, y - space / 2, space * 1.4, thick) + rect(x, y + space / 2 - thick, space * 1.4, thick)
        + rect(x, y - space, thin, space * 2) + rect(x + space * 1.4 - thin, y - space, thin, space * 2));
}

// Six tab lines (string 1 = high e on top) the width of the staff, with each
// "fret/string" at the x of its note. Frets move with the transposition; a fret
// below the nut moves to the next lower string (an octave up only on string 6).
const STRING_STEP = [0, 5, 4, 5, 5, 5]; // semitones from string n down to n+1
function shiftFret(fret, string, shift) {
    fret += shift;
    while (fret < 0 && string < 6) fret += STRING_STEP[string++];
    return [fret < 0 ? fret + 12 : fret, string];
}
function tabSvg(staffSvg, tab, shift) {
    const width = staffSvg.viewBox.baseVal.width;
    const lines = staffSvg.querySelector(".abcjs-staff").getBBox();
    const notes = [...staffSvg.querySelectorAll(".abcjs-note")].map((note) => {
        const box = note.getBBox();
        return box.x + box.width / 2;
    });
    const y = (string) => TAB_GAP + TAB_LINE * (string - 0.5);
    const height = y(6) + TAB_LINE / 2;
    let content = "";
    for (let string = 1; string <= 6; string++) {
        content += `<line x1="${lines.x}" x2="${lines.x + lines.width}" y1="${y(string)}" y2="${y(string)}"/>`;
    }
    // "TAB" down the left end, where the clef is on the staff
    [..."TAB"].forEach((letter, i) => {
        content += `<text class="melody-tab-label" x="${lines.x + 8}" y="${y(2.5 + i)}">${letter}</text>`;
    });
    tab.split(/\s+/).filter((token) => token.replace(/\|/g, "")).forEach((token, i) => {
        const [fret, string] = shiftFret(...token.split("/").map(Number), shift);
        if (notes[i] === undefined) return;
        content += `<text x="${notes[i]}" y="${y(string)}">${fret}</text>`;
    });
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "melody-tab");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("aria-hidden", "true");
    svg.innerHTML = content;
    return svg;
}

// Play / pause the melody (not the chords) with an organ-like tone made in the
// browser (no sound files, works offline), lighting each note as it sounds. It
// plays in the key on screen. One melody at a time. The button is in the song's
// controls (render.py PLAY_HTML) and plays the song's melody, or its fórmula.
const MELODY_QPM = 80; // quarter notes per minute, unless the melody sets Q:
const ORGAN = [[1, 0.5], [2, 0.3], [4, 0.12], [3, 0.08]]; // harmonic, level: 8', 4', 2' stops
let audio = null;
let playing = null; // {element, song, timer, out, paused}

function setButton(song, isPlaying) {
    const button = song?.querySelector(".melody-play");
    if (!button) return;
    button.textContent = isPlaying ? "⏸ Pause" : "▶ Melody";
    button.setAttribute("aria-label", isPlaying ? "Pause melody" : "Play melody");
}

function organNote(out, midi, seconds) {
    const start = audio.currentTime, end = start + Math.max(seconds, 0.08);
    const note = audio.createGain();
    note.gain.setValueAtTime(0, start);
    note.gain.linearRampToValueAtTime(0.25, start + 0.03);
    note.gain.setValueAtTime(0.25, end - 0.04); // a small gap between repeated notes
    note.gain.linearRampToValueAtTime(0, end);
    note.connect(out);
    ORGAN.forEach(([harmonic, level]) => {
        const osc = audio.createOscillator();
        const gain = audio.createGain();
        osc.frequency.value = 440 * 2 ** ((midi - 69) / 12) * harmonic;
        gain.gain.value = level;
        osc.connect(gain).connect(note);
        osc.start(start);
        osc.stop(end + 0.05);
    });
}

function soundNotes(notes) {
    notes.filter(([, seconds]) => seconds > 0.05).forEach(([midi, seconds]) => organNote(playing.out, midi, seconds));
}

function lightNotes(element, notes) {
    element.querySelectorAll(".melody-playing").forEach((n) => n.classList.remove("melody-playing"));
    notes.forEach((n) => n.classList.add("melody-playing"));
}

// A fresh output per start, so pausing silences the notes already sounding.
function newOutput() {
    const out = audio.createGain();
    out.connect(audio.destination);
    return out;
}

function stopMelody() {
    if (!playing) return;
    const { element, song, timer, out } = playing;
    playing = null;
    timer.stop();
    out.disconnect();
    lightNotes(element, []);
    setButton(song, false);
}

function playMelody(element) {
    const song = element.closest(".song");
    const shift = Number(song?.dataset.transpose || 0);
    // Not drawn yet (tapped right away), or copied HTML: draw it now, marked as drawn so
    // the pending draw doesn't redraw it (a redraw stops the playing).
    if (!melodyTunes.has(element)) {
        delete element.dataset.drawn;
        drawMelody(element);
    }
    const tune = melodyTunes.get(element);
    // iOS Safari leaves the context "interrupted"/suspended after the app is backgrounded,
    // and resume() can't revive it: start a fresh one (this runs inside the tap).
    if (audio?.state !== "running") {
        audio?.close();
        audio = new AudioContext();
    }
    audio.resume();
    tune.setUpAudio({ chordsOff: true });
    const timer = new ABCJS.TimingCallbacks(tune, {
        qpm: tune.metaText.tempo ? undefined : MELODY_QPM,
        eventCallback: (event) => {
            if (playing?.timer !== timer) return; // stopped, or another melody started
            if (!event) return stopMelody(); // the end
            lightNotes(element, (event.elements || []).flat());
            const notes = event.midiPitches.filter((p) => p.cmd === "note").map((p) =>
                [p.pitch + shift, (p.duration * event.millisecondsPerMeasure) / 1000]);
            playing.sounding = { notes, at: audio.currentTime };
            soundNotes(notes);
        },
    });
    playing = { element, song, timer, out: newOutput(), paused: false, sounding: null };
    setButton(song, true);
    timer.start();
}

function toggleMelody(element) {
    if (playing?.element !== element) {
        stopMelody();
        return playMelody(element);
    }
    const { sounding } = playing;
    if (playing.paused) {
        playing.out = newOutput();
        playing.paused = false;
        // The note cut by the pause sounds again for the time it had left (a reciting
        // note can last seconds); the timer then resumes where it paused.
        if (sounding) {
            soundNotes(sounding.notes.map(([midi, seconds]) => [midi, seconds - sounding.played]));
            sounding.at = audio.currentTime - sounding.played;
        }
        playing.timer.start();
    } else {
        playing.timer.pause();
        playing.out.disconnect();
        playing.paused = true;
        if (sounding) sounding.played = audio.currentTime - sounding.at;
    }
    setButton(playing.song, !playing.paused);
}

document.addEventListener("click", (e) => {
    const melody = e.target.closest(".melody-play")?.closest(".song").querySelector(".melody");
    if (melody) toggleMelody(melody);
});

// In the book: draw a song's melody once it is near the screen.
const songsNearScreen = new Set();

function drawMelody(element) {
    const song = element.closest(".song");
    const drawn = `${song.dataset.transpose || 0} ${document.body.dataset.notation}`;
    if (element.dataset.drawn === drawn) return;
    element.dataset.drawn = drawn;
    renderMelody(element, Number(song.dataset.transpose || 0));
}

function refreshMelody(element) {
    if (songsNearScreen.has(element.closest(".song"))) drawMelody(element);
}

const melodyObserver = new IntersectionObserver((entries) => {
    entries.forEach(({ target, isIntersecting }) => {
        if (!isIntersecting) return songsNearScreen.delete(target);
        songsNearScreen.add(target);
        // Later, not now: drawing reads layout, and reading it while songs are
        // still getting their real height (a jump) breaks Chromium's scroll anchoring.
        setTimeout(() => target.querySelectorAll(".melody").forEach(drawMelody), 150);
    });
}, { rootMargin: "100% 0px" });

document.querySelectorAll(".song .melody").forEach((element) => melodyObserver.observe(element.closest(".song")));
window.addEventListener("beforeprint", () => document.querySelectorAll(".song .melody").forEach(drawMelody));
