// "Keep screen on" while playing. Only shown where the browser supports it
// (it needs the page served over https, e.g. GitHub Pages).

if ("wakeLock" in navigator) {
    let wakeLock = null;
    let wanted = false;

    document.querySelectorAll('[data-requires="wake-lock"]')
        .forEach((el) => { el.hidden = false; });

    async function acquire() {
        try {
            wakeLock = await navigator.wakeLock.request("screen");
        } catch {
            wakeLock = null; // e.g. low battery mode; try again on next visibility
        }
    }

    function render() {
        document.querySelectorAll('[data-action="toggle-wake-lock"]').forEach((button) => {
            button.textContent = wanted ? "On" : "Off";
            button.setAttribute("aria-pressed", wanted);
        });
    }

    onAction("toggle-wake-lock", async () => {
        wanted = !wanted;
        if (wanted) await acquire();
        else await wakeLock?.release();
        render();
    });

    // The browser drops the lock when the tab is hidden; take it back on return.
    document.addEventListener("visibilitychange", () => {
        if (wanted && document.visibilityState === "visible") acquire();
    });
}
