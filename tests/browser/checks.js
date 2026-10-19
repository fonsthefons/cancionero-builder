// Measurement helpers injected into the built page by ui_test.py.

// The checks measure and click every song, so render them all, as if there
// were no content-visibility (skipped songs: skipped_song_checks in ui_check.py).
document.head.append(Object.assign(document.createElement("style"),
    { textContent: ".song { content-visibility: visible !important; }" }));

const MARK_RE = /\p{M}/u;
const columnsOf = (text) => [...text].filter((ch) => !MARK_RE.test(ch)).length;

function charWidth(lyrics) {
    const probe = document.createElement("span");
    probe.style.whiteSpace = "pre";
    probe.textContent = "M".repeat(40);
    lyrics.appendChild(probe);
    const w = probe.getBoundingClientRect().width / 40;
    probe.remove();
    return w;
}

// Every line as shown: chord lines, lyric lines, and the lyric that is a
// .line-pair's own text. { el, text, isChord, rect() }
function shownLines(song) {
    const lines = [];
    for (const el of song.querySelectorAll(".chord-line, .lyric-line, .line-pair")) {
        const range = document.createRange();
        if (el.matches(".line-pair")) {
            const texts = [...el.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE);
            if (!texts.length) continue; // its lyric is a .lyric-line of its own
            range.setStartBefore(texts[0]);
            range.setEndAfter(texts.at(-1));
        } else {
            range.selectNodeContents(el);
        }
        lines.push({ el, text: range.toString(), isChord: el.matches(".chord-line"), rect: () => range.getBoundingClientRect() });
    }
    return lines;
}

// Chords of a chord line (the words outside .sep spans) or of an "Intro:"
// line (.chord spans): [{ col, text, el }] (el: the .chord span, if any).
function chordsOf(line) {
    const chords = [];
    let col = 0;
    for (const node of line.childNodes) {
        if (line.matches(".chord-line") && node.nodeType === Node.TEXT_NODE) {
            for (const m of node.data.matchAll(/\S+/g)) {
                chords.push({ col: col + columnsOf(node.data.slice(0, m.index)), text: m[0] });
            }
        } else if (node.nodeType === Node.ELEMENT_NODE && node.matches(".chord")) {
            chords.push({ col, text: node.textContent, el: node });
        }
        col += columnsOf(node.textContent);
    }
    return chords;
}

// WebKit rounds a Range inside a text node to whole pixels, so to measure
// chords exactly every chord-line chord is wrapped in a .chord span (same
// look) for a while. Returns the function that puts the lines back.
function wrapChords() {
    const saved = [...document.querySelectorAll(".chord-line")].map((line) => [line, [...line.childNodes]]);
    saved.forEach(([line, nodes]) => line.replaceChildren(...nodes.flatMap((node) => (
        node.nodeType !== Node.TEXT_NODE ? [node] : node.data.split(/(\S+)/).filter(Boolean).map((piece) => (
            /\S/.test(piece) ? Object.assign(document.createElement("span"), { className: "chord", textContent: piece }) : piece))
    ))));
    return () => saved.forEach(([line, nodes]) => line.replaceChildren(...nodes));
}

// Every visible line must be exactly (columns x character width) wide, and
// every chord must start exactly at (its column x character width).
window.alignmentReport = () => {
    const bad = [];
    let lines = 0, chords = 0;
    const unwrap = wrapChords();
    for (const song of document.querySelectorAll(".song")) {
        const cw = charWidth(song.querySelector(".lyrics"));
        for (const line of shownLines(song)) {
            if (!line.el.offsetParent) continue;
            lines++;
            const expected = columnsOf(line.text) * cw;
            const actual = line.rect().width;
            if (Math.abs(actual - expected) > 1) {
                bad.push(`${song.id}: line width ${actual.toFixed(1)} != ${expected.toFixed(1)}: "${line.text}"`);
            }
            if (!line.isChord && !line.el.matches(".chord-inline")) continue;
            const left = line.el.getBoundingClientRect().left;
            chordsOf(line.el).forEach((chord) => {
                chords++;
                const x = chord.el.getBoundingClientRect().left - left;
                if (Math.abs(x - chord.col * cw) > 0.75) {
                    bad.push(`${song.id}: chord ${chord.text} at ${x.toFixed(1)}px, expected ${(chord.col * cw).toFixed(1)}`);
                }
            });
        }
    }
    unwrap();
    return { lines, chords, bad: bad.length, examples: bad.slice(0, 5) };
};

// Every line must fit inside its column without horizontal scrolling.
window.fitReport = () => {
    const overflowing = [];
    const sizes = [];
    for (const song of document.querySelectorAll(".song")) {
        const lyrics = song.querySelector(".lyrics");
        const style = getComputedStyle(lyrics);
        const cols = Number(style.columnCount) || 1;
        const gap = parseFloat(style.columnGap) || 0;
        const colWidth = (lyrics.clientWidth - (cols - 1) * gap) / cols;
        const widest = Math.max(...shownLines(song).map((line) => line.rect().width));
        sizes.push(parseFloat(style.fontSize));
        if (widest > colWidth + 0.5 || lyrics.scrollWidth > lyrics.clientWidth + 1) {
            overflowing.push(`${song.id} (${widest.toFixed(0)}px > ${colWidth.toFixed(0)}px)`);
        }
    }
    sizes.sort((a, b) => a - b);
    return {
        overflowing: overflowing.length,
        examples: overflowing.slice(0, 5),
        fontPx: { min: sizes[0], median: sizes[sizes.length >> 1], max: sizes[sizes.length - 1] },
        pageScrollsSideways: document.documentElement.scrollWidth > window.innerWidth,
    };
};

// Transpose every song through all 11 shifts: chords must keep their column
// (unless two chords are so close there is no space to absorb a longer name),
// and going back to 0 must restore every line exactly.
window.transposeReport = () => {
    let checked = 0, moved = 0, movedOverLyrics = 0, unjustified = 0;
    const unjustifiedExamples = [];
    const movedExamples = [];
    const seen = new Set();
    let restored = true;
    // The lyric under a chord line: its .line-pair's own text, if any.
    const lyricUnder = (line) => (line.parentElement.matches(".line-pair")
        ? [...line.parentElement.childNodes].filter((node) => node !== line).map((node) => node.textContent).join("")
        : null);
    for (const song of document.querySelectorAll(".song")) {
        const lines = [...song.querySelectorAll(".chord-line")];
        const original = lines.map((l) => ({ text: l.textContent, cols: chordsOf(l).map((c) => c.col) }));
        for (let shift = 1; shift <= 11; shift++) {
            setTranspose(song, shift);
            lines.forEach((line, i) => {
                const lyric = lyricUnder(line);
                const chords = chordsOf(line);
                chords.forEach(({ col }, j) => {
                    checked++;
                    if (col === original[i].cols[j]) return;
                    moved++;
                    // Only allowed when there was no room: moved right, and no
                    // double space left between the previous chord and this one.
                    const prevEnd = j > 0 ? chords[j - 1].col + chords[j - 1].text.length : 0;
                    const gap = [...line.textContent].slice(prevEnd, col).join("");
                    const noRoom = col > original[i].cols[j] && !gap.includes("  ");
                    const glued = gap !== "" && !gap.includes(" "); // e.g. "C#m-Bm"
                    if (!noRoom && !glued) {
                        unjustified++;
                        unjustifiedExamples.push(`${song.id} +${shift}: "${original[i].text}" -> "${line.textContent}"`);
                    }
                    if (lyric === null) return;
                    movedOverLyrics++;
                    const key = `${song.id}|${i}`;
                    if (!seen.has(key) && movedExamples.length < 12) {
                        seen.add(key);
                        movedExamples.push(`${song.id} +${shift}:\n      "${original[i].text}"\n   -> "${line.textContent}"\n      "${lyric}"`);
                    }
                });
            });
        }
        setTranspose(song, 0);
        lines.forEach((line, i) => {
            if (line.textContent !== original[i].text) restored = false;
        });
    }
    return {
        checked, moved, movedOverLyrics, movedExamples, restored,
        unjustified, unjustifiedExamples: unjustifiedExamples.slice(0, 5),
    };
};
