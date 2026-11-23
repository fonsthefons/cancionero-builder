// First-visit tour (and Settings > "Ver tutorial"): dims the page, boxes the
// controls of each step and labels them. Built on demand, removed when it ends.

const TOUR_STEPS = [
    {
        title: "Canciones",
        text: "Toca una canción del índice para abrirla, o búscala.",
        labels: [[".topbar .search input", "Buscar"], ["#index a", "Canciones"]],
        before() { scrollTo({ top: 0, behavior: "instant" }); }, // (no return: Chromium's scrollTo returns a Promise)
    },
    {
        title: "En cada canción",
        text: "Cada canción tiene sus propios controles.",
        labels: [
            ['[data-action="toggle-chords"]', "Ocultar acordes"],
            ['.stepper:has([data-action="transpose-up"])', "Tono"],
            ['[data-action="toggle-columns"]', "2 columnas"],
            ['.stepper:has([data-action="song-text-bigger"])', "Tamaño"],
            ['[data-action="session-toggle"]', "Añadir a sesión"],
        ],
        before() {
            const song = document.querySelector(".song:has(.chord-line)");
            const controls = song.querySelector(".controls");
            controls.scrollIntoView({ block: "center", behavior: "instant" });
            return controls;
        },
    },
    {
        title: "Barra superior",
        text: "El menú, y el autoscroll con su velocidad.",
        labels: [
            ['[data-action="open-drawer"]', "Menú"],
            ['[data-action="toggle-autoscroll"]', "Autoscroll"],
            ['[data-action="autoscroll-faster"]', "Velocidad"],
        ],
    },
    {
        title: "Menú",
        text: "Tu sesión de canciones y los ajustes del libro.",
        labels: [["#session summary", "Sesión: tu lista"], ["#settings h2", "Ajustes de todo el libro"]],
        before() {
            setDrawerOpen(true);
            drawerOpenedByTour = true;
            document.getElementById("drawer").scrollTop = 0;
        },
    },
];

let tour = null; // { el, spot, card, chips, n, root } while the tour is showing
let drawerOpenedByTour = false;

function startTutorial() {
    if (tour) return;
    document.body.classList.add("tour-on"); // shortens the menu so both labels fit
    const el = document.createElement("div");
    el.className = "tour";
    el.innerHTML = '<div class="tour-spot"></div><div class="tour-card"><h3></h3><p></p><div class="dialog-buttons">'
        + '<button data-action="tour-skip">Saltar</button><button data-action="tour-next"></button></div></div>';
    document.body.append(el);
    tour = { el, spot: el.firstChild, card: el.lastChild, chips: [], n: -1 };
    showTourStep(0);
}

function showTourStep(n) {
    const step = TOUR_STEPS[n];
    tour.n = n;
    tour.root = step.before?.() ?? document;
    tour.chips.forEach((chip) => chip.remove());
    tour.chips = step.labels.map(([, text]) => {
        const chip = document.createElement("div");
        chip.className = "tour-chip";
        chip.textContent = text;
        tour.el.append(chip);
        return chip;
    });
    tour.card.querySelector("h3").textContent = `Paso ${n + 1}/${TOUR_STEPS.length} · ${step.title}`;
    tour.card.querySelector("p").textContent = step.text;
    const next = tour.card.querySelector('[data-action="tour-next"]');
    next.textContent = n === TOUR_STEPS.length - 1 ? "Listo" : "Siguiente";
    next.focus();
    placeTour();
    setTimeout(placeTour, 350); // the menu is still sliding in, and songs may lay out late
}

const overlaps = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

function placeTour() {
    if (!tour) return;
    const vw = innerWidth, vh = innerHeight, gap = 12;
    const targets = TOUR_STEPS[tour.n].labels
        .map(([selector]) => tour.root.querySelector(selector)?.getBoundingClientRect());
    const union = targets.filter(Boolean).reduce((u, r) => ({
        left: Math.min(u.left, r.left), top: Math.min(u.top, r.top),
        right: Math.max(u.right, r.right), bottom: Math.max(u.bottom, r.bottom),
    }), { left: vw, top: vh, right: 0, bottom: 0 });
    const pad = 4;
    Object.assign(tour.spot.style, {
        left: `${union.left - pad}px`, top: `${union.top - pad}px`,
        width: `${union.right - union.left + 2 * pad}px`, height: `${union.bottom - union.top + 2 * pad}px`,
    });
    tour.card.classList.toggle("top", (union.top + union.bottom) / 2 > vh / 2);
    const placed = [tour.card.getBoundingClientRect()];
    tour.chips.forEach((chip, i) => {
        const r = targets[i];
        const w = chip.offsetWidth, h = chip.offsetHeight;
        const left = Math.min(Math.max(r.left + r.width / 2 - w / 2, 4), vw - w - 4);
        const sides = i % 2 ? ["above", "below"] : ["below", "above"]; // neighbours alternate
        const spot = (side) => {
            const top = side === "below" ? r.bottom + gap : r.top - h - gap;
            return { side, top, left, right: left + w, bottom: top + h };
        };
        const best = sides.map(spot).find((c) => c.top >= 4 && c.bottom <= vh - 4
            && !placed.some((p) => overlaps(c, p))) ?? spot(sides[0]);
        chip.dataset.side = best.side;
        chip.style.left = `${left}px`;
        chip.style.top = `${best.top}px`;
        chip.style.setProperty("--arrow-x", `${Math.min(Math.max(r.left + r.width / 2 - left, 10), w - 10)}px`);
        placed.push(best);
    });
}

function closeTour() {
    tour.el.remove();
    tour = null;
    document.body.classList.remove("tour-on");
    if (drawerOpenedByTour) setDrawerOpen(false);
    drawerOpenedByTour = false;
    scrollTo({ top: 0, behavior: "instant" });
    showInstallTip();
}

onAction("tour-next", () => (tour.n === TOUR_STEPS.length - 1 ? closeTour() : showTourStep(tour.n + 1)));
onAction("tour-skip", closeTour);
onAction("start-tutorial", () => {
    setDrawerOpen(false);
    startTutorial();
});
addEventListener("resize", placeTour);
addEventListener("scroll", placeTour);
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && tour) closeTour();
});

if (!prefs.get("tutorialSeen")) {
    prefs.set("tutorialSeen", "1");
    startTutorial();
}
