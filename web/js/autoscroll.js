// Autoscroll: start/stop and speed buttons in the top bar.
//
// Scrolls the page smoothly at a steady speed while you play. If you scroll
// by hand or jump to a song meanwhile, it continues from where you land.
// Pauses while the menu is open and stops at the end of the page.

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

    // Moved by hand (or jumped to a song): continue from there.
    if (Math.abs(window.scrollY - autoscrollPosition) > 2) autoscrollPosition = window.scrollY;

    const bottom = document.documentElement.scrollHeight - window.innerHeight;
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
