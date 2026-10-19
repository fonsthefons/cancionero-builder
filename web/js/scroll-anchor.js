// Keep what's on screen still while songs above it change height (Safari).
//
// Off-screen songs are skipped by the browser (content-visibility in
// styles.css) and get their real height only when scrolled near, or when the
// text size changes. Browsers' own scroll anchoring hides that, but Safari's
// jumps a screen away, so there it is turned off and done here instead.
// shortcut: engine check by navigator.vendor (every iPhone browser is WebKit);
// drop this file once Safari's scroll anchoring handles skipped content.

if (navigator.vendor.startsWith("Apple")) {
    document.documentElement.style.overflowAnchor = "none";
    const songHeights = new WeakMap();

    const songResizes = new ResizeObserver((entries) => {
        let shift = 0;
        for (const entry of entries) {
            const height = entry.borderBoxSize[0].blockSize;
            const old = songHeights.get(entry.target);
            songHeights.set(entry.target, height);
            if (old === undefined) continue;
            // Songs that ended above the middle of the screen push the rest down.
            const top = entry.target.getBoundingClientRect().top;
            if (top < 0 && top + old < window.innerHeight / 2) shift += height - old;
        }
        if (shift) window.scrollBy(0, shift);
    });

    document.querySelectorAll(".song").forEach((song) => songResizes.observe(song));
}
