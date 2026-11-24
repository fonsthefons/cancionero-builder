// First-visit tour (and Settings > "Ver tutorial"): dims the page, boxes the
// controls of each step and labels them. Built on demand, removed when it ends.
// Its last step also replaces the old "add to home screen" popup (book.yaml install_tip).
//
// labels: [selector, chip text]; a null text only widens the box, without a chip.
// before() sets the page up for the step (and may return the element to search in);
// after() undoes it when the step is left by Siguiente, Atrás or Saltar.

const offlineTip = () => BOOK.installTip && /^https?:$/.test(location.protocol)
    && !matchMedia("(display-mode: standalone)").matches && navigator.standalone !== true; // not in the home-screen app

let sessionBeforeTour = null; // the real session while the tour shows example songs

// Open the menu scrolled so `selector` is near its top, with room above for a label.
function showInDrawer(selector) {
    setDrawerOpen(true);
    const drawer = document.getElementById("drawer");
    const target = document.querySelector(selector).getBoundingClientRect().top;
    drawer.scrollTop += target - drawer.getBoundingClientRect().top - 56;
}

const TOUR_STEPS = [
    {
        title: "Canciones",
        text: "Toca una canción del índice para abrirla, o búscala.",
        labels: [[".topbar .search input", "Buscar"], ["#index a", "Canciones"]],
        before() {
            setDrawerOpen(false);
            scrollTo({ top: 0, behavior: "instant" }); // (no return: Chromium's scrollTo returns a Promise)
        },
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
            setDrawerOpen(false);
            const song = document.querySelector(".song:has(.chord-line)");
            const controls = song.querySelector(".controls");
            controls.scrollIntoView({ block: "center", behavior: "instant" });
            return controls;
        },
    },
    {
        title: "Sesión",
        text: () => (sessionBeforeTour.length ? "" : "<p>Ejemplo con 2 canciones (se quitan al seguir).</p>")
            + "<p>Tu lista de canciones para tocar, en el menú. Se guarda en este dispositivo.</p><ul>"
            + "<li><b>⠿</b> arrastra para cambiar el orden; <b>✕</b> quita la canción.</li>"
            + "<li><b>Add a song…</b> busca y añade canciones.</li>"
            + "<li><b>Share session</b>: envía un enlace con la lista.</li>"
            + "<li><b>Print session</b>: imprime o guarda en PDF solo estas canciones.</li>"
            + "<li><b>Create session PPT</b>: diapositivas con la letra para proyectar.</li>"
            + "<li><b>Clear session</b>: vacía la lista.</li></ul>",
        labels: [
            [".session-list li:first-child .session-handle", "Arrastrar"],
            [".session-list li:first-child [data-action='session-remove']", "Quitar"],
            ["#session summary", null],
            ['[data-action="session-clear"]', null],
        ],
        before() {
            sessionBeforeTour = session;
            if (!session.length) {
                // Shown, not saved: only `session` changes, never prefs.
                session = [...document.querySelectorAll(".song")].slice(0, 2).map((song) => song.id);
                renderSession();
            }
            document.getElementById("session").open = true;
            setDrawerOpen(true);
            document.getElementById("drawer").scrollTop = 0;
        },
        after() {
            session = sessionBeforeTour;
            renderSession();
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
        before() { setDrawerOpen(false); },
    },
    // Settings in two steps: on a phone all of them fill the screen, leaving no room for the card.
    {
        title: "Ajustes (1/2)",
        text: () => "<p>Cambian <b>todo el libro</b>, no solo una canción:</p><ul>"
            + "<li><b>Text size</b>: tamaño de la letra.</li>"
            + "<li><b>Hide all chords</b>: oculta o muestra los acordes.</li>"
            + (document.querySelector('[data-action="cycle-notation"]')
                ? "<li><b>Chord names</b>: acordes como C D E o Do Re Mi.</li>" : "")
            + "<li><b>2 columns</b>: las canciones a una o dos columnas.</li></ul>",
        labels: [ // the chip at an odd index goes above (see placeTour)
            ['.setting:has([data-action="toggle-all-columns"])', null],
            ["#settings h2", "Ajustes de todo el libro"],
        ],
        before() { showInDrawer("#settings h2"); },
    },
    {
        title: "Ajustes (2/2)",
        text: () => "<ul><li><b>Reset all</b>: deshace los cambios de cada canción (tono, acordes, columnas).</li>"
            + "<li><b>Theme</b>: claro, oscuro o automático.</li>"
            + (document.querySelector('[data-requires="wake-lock"]:not([hidden])')
                ? "<li><b>Keep screen on</b>: la pantalla no se apaga mientras tocas.</li>" : "")
            + "<li><b>Print</b>: imprime o guarda en PDF todo el libro.</li></ul>",
        labels: [
            ['.setting:has([data-action="open-print"])', null],
            ['.setting:has([data-action="reset-songs"])', "Más ajustes del libro"],
        ],
        before() { showInDrawer('.setting:has([data-action="reset-songs"])'); },
    },
    {
        title: "¡Listo!",
        text: () => "<p>Puedes volver a ver este tutorial abajo del todo en el menú.</p>"
            + (offlineTip() ? "<p><b>Para acceso offline</b>, añade el libro a la pantalla de inicio:</p><ul>"
                + "<li><b>iPhone</b> (Safari): Compartir → “Añadir a pantalla de inicio”</li>"
                + "<li><b>Android</b> (Chrome): menú ⋮ → “Añadir a pantalla de inicio”</li></ul>" : ""),
        labels: [['[data-action="start-tutorial"]', "Ver tutorial"]],
        before() {
            setDrawerOpen(true);
            const drawer = document.getElementById("drawer");
            drawer.scrollTop = drawer.scrollHeight;
        },
    },
];

let tour = null; // { el, spot, card, chips, n, root } while the tour is showing

function startTutorial() {
    if (tour) return;
    document.body.classList.add("tour-on"); // shortens the menu so session and settings fit
    const el = document.createElement("div");
    el.className = "tour";
    el.innerHTML = '<div class="tour-spot"></div><div class="tour-card"><h3></h3><h4></h4><div class="tour-text"></div>'
        + '<div class="dialog-buttons"><button data-action="tour-skip">Saltar</button>'
        + '<button data-action="tour-back">Atrás</button><button data-action="tour-next"></button></div></div>';
    document.body.append(el);
    tour = { el, spot: el.firstChild, card: el.lastChild, chips: [], n: -1 };
    showTourStep(0);
}

function leaveTourStep() {
    if (tour.n >= 0) TOUR_STEPS[tour.n].after?.();
}

function showTourStep(n) {
    leaveTourStep();
    const step = TOUR_STEPS[n];
    tour.n = n;
    tour.root = step.before?.() ?? document;
    tour.chips.forEach((chip) => chip?.remove());
    tour.chips = step.labels.map(([, text]) => {
        if (!text) return null;
        const chip = document.createElement("div");
        chip.className = "tour-chip";
        chip.textContent = text;
        tour.el.append(chip);
        return chip;
    });
    tour.card.querySelector("h3").textContent = `Tutorial · Paso ${n + 1}/${TOUR_STEPS.length}`;
    tour.card.querySelector("h4").textContent = step.title;
    const text = typeof step.text === "function" ? step.text() : `<p>${step.text}</p>`;
    tour.card.querySelector(".tour-text").innerHTML = text; // our own fixed strings, never song data
    tour.card.querySelector('[data-action="tour-back"]').hidden = n === 0;
    const next = tour.card.querySelector('[data-action="tour-next"]');
    next.textContent = n === TOUR_STEPS.length - 1 ? "Terminar" : "Siguiente";
    next.focus();
    placeTour();
    setTimeout(placeTour, 350); // the menu is still sliding in, and songs may lay out late
}

const overlaps = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

function placeTour() {
    if (!tour) return;
    const vw = innerWidth, vh = innerHeight, gap = 12;
    const targets = TOUR_STEPS[tour.n].labels
        .map(([selector]) => tour.root.querySelector(selector)?.getBoundingClientRect())
        .map((r) => (r?.width ? r : null)); // hidden controls (e.g. no session buttons) don't count
    const union = targets.filter(Boolean).reduce((u, r) => ({
        left: Math.min(u.left, r.left), top: Math.min(u.top, r.top),
        right: Math.max(u.right, r.right), bottom: Math.max(u.bottom, r.bottom),
    }), { left: vw, top: vh, right: 0, bottom: 0 });
    const pad = 4;
    Object.assign(tour.spot.style, {
        left: `${union.left - pad}px`, top: `${union.top - pad}px`,
        width: `${union.right - union.left + 2 * pad}px`, height: `${union.bottom - union.top + 2 * pad}px`,
    });
    // Wide screens with the menu open: the card goes beside the menu, not over it.
    const drawer = document.getElementById("drawer").getBoundingClientRect();
    const beside = document.body.classList.contains("drawer-open") && vw - drawer.right >= 440;
    tour.card.classList.toggle("beside", beside);
    tour.card.classList.toggle("top", !beside && (union.top + union.bottom) / 2 > vh / 2);
    const placed = [tour.card.getBoundingClientRect()];
    tour.chips.forEach((chip, i) => {
        const r = targets[i];
        if (!chip) return;
        chip.hidden = !r;
        if (!r) return;
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
    leaveTourStep();
    tour.el.remove();
    tour = null;
    document.body.classList.remove("tour-on");
    setDrawerOpen(false);
    scrollTo({ top: 0, behavior: "instant" });
}

onAction("tour-next", () => (tour.n === TOUR_STEPS.length - 1 ? closeTour() : showTourStep(tour.n + 1)));
onAction("tour-back", () => showTourStep(tour.n - 1));
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
