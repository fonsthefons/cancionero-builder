// Measurement helpers injected into the built page by ui_test.py.

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

function textWidth(el) {
    const range = document.createRange();
    range.selectNodeContents(el);
    return range.getBoundingClientRect().width;
}

// Column of each chord span inside its chord line.
function chordColumns(line) {
    const cols = [];
    let col = 0;
    for (const node of line.childNodes) {
        if (node.nodeType === Node.ELEMENT_NODE) cols.push(col);
        col += columnsOf(node.textContent);
    }
    return cols;
}

// Every visible line must be exactly (columns x character width) wide, and
// every chord must start exactly at (its column x character width).
window.alignmentReport = () => {
    const bad = [];
    let lines = 0, chords = 0;
    for (const song of document.querySelectorAll(".song")) {
        const lyrics = song.querySelector(".lyrics");
        const cw = charWidth(lyrics);
        for (const line of song.querySelectorAll(".chord-line, .lyric-line")) {
            if (!line.offsetParent) continue;
            lines++;
            const expected = columnsOf(line.textContent) * cw;
            const actual = textWidth(line);
            if (Math.abs(actual - expected) > 1) {
                bad.push(`${song.id}: line width ${actual.toFixed(1)} != ${expected.toFixed(1)}: "${line.textContent}"`);
            }
            if (!line.classList.contains("chord-line")) continue;
            const left = line.getBoundingClientRect().left;
            const spans = line.querySelectorAll(".chord");
            chordColumns(line).forEach((col, i) => {
                chords++;
                const x = spans[i].getBoundingClientRect().left - left;
                if (Math.abs(x - col * cw) > 0.75) {
                    bad.push(`${song.id}: chord ${spans[i].textContent} at ${x.toFixed(1)}px, expected ${(col * cw).toFixed(1)}`);
                }
            });
        }
    }
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
        const widest = Math.max(...[...song.querySelectorAll(".chord-line, .lyric-line")].map(textWidth));
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
    for (const song of document.querySelectorAll(".song")) {
        const lines = [...song.querySelectorAll(".chord-line")];
        const original = lines.map((l) => ({ text: l.textContent, cols: chordColumns(l) }));
        for (let shift = 1; shift <= 11; shift++) {
            setTranspose(song, shift);
            lines.forEach((line, i) => {
                const overLyrics = !!line.nextElementSibling?.classList.contains("lyric-line");
                const cols = chordColumns(line);
                const spans = line.querySelectorAll(".chord");
                cols.forEach((col, j) => {
                    checked++;
                    if (col === original[i].cols[j]) return;
                    moved++;
                    // Only allowed when there was no room: moved right, and no
                    // double space left between the previous chord and this one.
                    const prevEnd = j > 0 ? cols[j - 1] + spans[j - 1].textContent.length : 0;
                    const gap = [...line.textContent].slice(prevEnd, col).join("");
                    const noRoom = col > original[i].cols[j] && !gap.includes("  ");
                    const glued = gap !== "" && !gap.includes(" "); // e.g. "C#m-Bm"
                    if (!noRoom && !glued) {
                        unjustified++;
                        unjustifiedExamples.push(`${song.id} +${shift}: "${original[i].text}" -> "${line.textContent}"`);
                    }
                    if (!overLyrics) return;
                    movedOverLyrics++;
                    const key = `${song.id}|${i}`;
                    if (!seen.has(key) && movedExamples.length < 12) {
                        seen.add(key);
                        movedExamples.push(`${song.id} +${shift}:\n      "${original[i].text}"\n   -> "${line.textContent}"\n      "${line.nextElementSibling.textContent}"`);
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
