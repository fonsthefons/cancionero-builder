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

function renderMelody(element, shift = 0) {
    const abc = element.dataset.abc;
    const staff = document.createElement("div");
    element.replaceChildren(staff);
    // staffwidth: the size a phone shows at about 1:1 (the SVG scales to the width).
    ABCJS.renderAbc(staff, abc, {
        responsive: "resize", staffwidth: 380, visualTranspose: shift, add_classes: true,
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

    element.append(tabSvg(svg, element.dataset.tab, shift));
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
// "fret/string" at the x of its note. Frets move with the transposition on the
// same string (an octave down when they would go below the nut).
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
        const [fret, string] = token.split("/").map(Number);
        let shifted = fret + shift;
        if (shifted < 0) shifted += 12;
        if (notes[i] === undefined) return;
        content += `<text x="${notes[i]}" y="${y(string)}">${shifted}</text>`;
    });
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "melody-tab");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("aria-hidden", "true");
    svg.innerHTML = content;
    return svg;
}

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
