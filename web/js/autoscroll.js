// Autoscroll: start/stop and speed buttons in the top bar.
//
// Scrolls the page smoothly at a steady speed while you play. If you scroll
// by hand or jump to a song meanwhile, it continues from where you land.
// Pauses while the menu is open. Stops when the end of the song cut off by the
// bottom of the screen reaches the bottom; ▶ again goes on into the next song.

const AUTOSCROLL = {
    minSpeed: 1,
    maxSpeed: 10,
    defaultSpeed: 3,
    pxPerSecondPerStep: 6, // speed 3 = 18px/s, about one line every second on a phone
    maxFrameGap: 0.1, // seconds; avoids a jump after the tab was in the background
};

let autoscrollSpeed = AUTOSCROLL.defaultSpeed;
let autoscrollRunning = false;
let autoscrollFrame = null;
let autoscrollLastTime = null;
let autoscrollPosition = 0; // exact (fractional) position we scrolled to
let autoscrollSong = null; // the song being scrolled through; null = to the end of the page

// The song cut off by the bottom of the screen: the only one with more to show.
// Songs that end on screen are passed over, so ▶ after a stop goes on to the next song.
function songAtScreenBottom() {
    return [...document.querySelectorAll(".song")]
        // 2px: a stopped song may end up to ~2px below (stop tolerance + whole-pixel scrolling).
        .find((song) => song.getBoundingClientRect().bottom > window.innerHeight + 2) ?? null;
}

function renderAutoscroll() {
    document.querySelectorAll('[data-action="toggle-autoscroll"]').forEach((button) => {
        button.textContent = autoscrollRunning ? "⏸" : "▶";
        button.setAttribute("aria-pressed", autoscrollRunning);
        button.setAttribute("aria-label", autoscrollRunning ? "Stop autoscroll" : "Start autoscroll");
    });
    document.querySelectorAll(".autoscroll-speed")
        .forEach((el) => { el.textContent = autoscrollSpeed; });
}

function autoscrollStep(time) {
    autoscrollFrame = requestAnimationFrame(autoscrollStep);
    const dt = autoscrollLastTime === null
        ? 0
        : Math.min((time - autoscrollLastTime) / 1000, AUTOSCROLL.maxFrameGap);
    autoscrollLastTime = time;

    if (document.body.classList.contains("drawer-open")) return;

    // Moved by hand (or jumped to a song): continue from there, in the song now cut off.
    if (Math.abs(window.scrollY - autoscrollPosition) > 2) {
        autoscrollPosition = window.scrollY;
        autoscrollSong = songAtScreenBottom();
    }

    // Stop when the song's bottom reaches the screen's bottom (re-read every
    // frame: the song can grow or shrink with text size, columns or layout).
    const pageBottom = document.documentElement.scrollHeight - window.innerHeight;
    const songBottom = autoscrollSong
        ? window.scrollY + autoscrollSong.getBoundingClientRect().bottom - window.innerHeight
        : pageBottom;
    const bottom = Math.min(pageBottom, songBottom);
    if (autoscrollPosition >= bottom - 1) {
        setAutoscroll(false);
        return;
    }
    autoscrollPosition = Math.min(bottom, autoscrollPosition + autoscrollSpeed * AUTOSCROLL.pxPerSecondPerStep * dt);
    window.scrollTo(0, autoscrollPosition);
}

function setAutoscroll(running) {
    autoscrollRunning = running;
    cancelAnimationFrame(autoscrollFrame);
    autoscrollFrame = null;
    if (running) {
        autoscrollPosition = window.scrollY;
        autoscrollSong = songAtScreenBottom();
        autoscrollLastTime = null;
        autoscrollFrame = requestAnimationFrame(autoscrollStep);
    }
    renderAutoscroll();
}

function setAutoscrollSpeed(speed) {
    autoscrollSpeed = Math.min(AUTOSCROLL.maxSpeed, Math.max(AUTOSCROLL.minSpeed, speed));
    prefs.set("autoscrollSpeed", autoscrollSpeed);
    renderAutoscroll();
}

onAction("toggle-autoscroll", () => setAutoscroll(!autoscrollRunning));
onAction("autoscroll-faster", () => setAutoscrollSpeed(autoscrollSpeed + 1));
onAction("autoscroll-slower", () => setAutoscrollSpeed(autoscrollSpeed - 1));

setAutoscrollSpeed(Number(prefs.get("autoscrollSpeed", AUTOSCROLL.defaultSpeed)) || AUTOSCROLL.defaultSpeed);
