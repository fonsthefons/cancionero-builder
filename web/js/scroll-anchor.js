// Keep what's on screen still while songs above it change height.
//
// Off-screen songs are skipped by the browser (content-visibility in
// styles.css) and get their real height only when scrolled near, or when the
// text size changes. Browsers' own scroll anchoring should hide that, but
// Safari's jumps a screen away, and Chromium's drifts about a screen on A+
// among short songs with staffs (the liturgia fórmulas), so it is turned off
// and done here instead.

document.documentElement.style.overflowAnchor = "none";
const songHeights = new WeakMap();

const songResizes = new ResizeObserver((entries) => {
    let shift = 0;
    let moved = 0; // how far earlier songs of this batch moved this one (entries are in page order)
    for (const entry of entries) {
        const height = entry.borderBoxSize[0].blockSize;
        const old = songHeights.get(entry.target);
        songHeights.set(entry.target, height);
        if (old === undefined) continue;
        // Songs that ended above the middle of the screen (before resizing) push the rest down.
        const top = entry.target.getBoundingClientRect().top - moved;
        if (top < 0 && top + old < window.innerHeight / 2) shift += height - old;
        moved += height - old;
    }
    if (shift) window.scrollBy(0, shift);
});

document.querySelectorAll(".song").forEach((song) => songResizes.observe(song));
