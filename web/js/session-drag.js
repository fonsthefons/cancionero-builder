// Drag and drop to reorder the Sing Session, from the ⠿ handle on each row.
//
// Uses pointer events, so mouse, finger and pencil share one code path.
// The handle has `touch-action: none` (styles.css): a drag that starts on it
// moves the song, while swiping anywhere else still scrolls the menu.
// The dragged row follows the pointer, the others slide aside to make room,
// and the new order is saved on release. Dragging near the top or bottom of
// the menu scrolls it. With a keyboard, ↑ / ↓ on a focused handle move the song.

const SESSION_DRAG = {
    edge: 56, // px from the menu's top/bottom edge where it starts scrolling
    edgeSpeed: 10, // px per frame at the very edge
};

const sessionList = document.querySelector(".session-list");
const sessionScroller = document.getElementById("drawer");
let sessionDrag = null;

function sessionDragLayout() {
    const d = sessionDrag;
    const scrolled = sessionScroller.scrollTop - d.startScroll;
    const dy = d.pointerY - d.startY + scrolled;
    const from = d.from;
    const center = d.rects[from].top + d.rects[from].height / 2 + dy;

    // Target slot: past the midpoint of a neighbour means taking its place.
    let to = from;
    for (let i = from + 1; i < d.items.length; i++) {
        if (center > d.rects[i].top + d.rects[i].height / 2) to = i;
    }
    for (let i = from - 1; i >= 0; i--) {
        if (center < d.rects[i].top + d.rects[i].height / 2) to = i;
    }
    d.to = to;

    d.item.style.transform = `translateY(${dy}px)`;
    d.items.forEach((item, i) => {
        if (i === from) return;
        let shift = 0;
        if (from < i && i <= to) shift = -d.step;
        if (to <= i && i < from) shift = d.step;
        item.style.transform = shift ? `translateY(${shift}px)` : "";
    });
}

// While dragging near the menu's edges, keep scrolling it.
function sessionDragAutoScroll() {
    if (!sessionDrag) return;
    const box = sessionScroller.getBoundingClientRect();
    const y = sessionDrag.pointerY;
    let speed = 0;
    if (y < box.top + SESSION_DRAG.edge) speed = -SESSION_DRAG.edgeSpeed * (1 - (y - box.top) / SESSION_DRAG.edge);
    if (y > box.bottom - SESSION_DRAG.edge) speed = SESSION_DRAG.edgeSpeed * (1 - (box.bottom - y) / SESSION_DRAG.edge);
    if (speed) {
        sessionScroller.scrollTop += Math.max(-SESSION_DRAG.edgeSpeed, Math.min(SESSION_DRAG.edgeSpeed, speed));
        sessionDragLayout();
    }
    sessionDrag.frame = requestAnimationFrame(sessionDragAutoScroll);
}

function endSessionDrag(commit) {
    const d = sessionDrag;
    if (!d) return;
    sessionDrag = null;
    cancelAnimationFrame(d.frame);
    sessionList.classList.remove("sorting");
    d.item.classList.remove("dragging");
    d.items.forEach((item) => { item.style.transform = ""; });
    if (commit && d.to !== d.from) moveInSession(d.item.dataset.song, d.to);
}

sessionList.addEventListener("pointerdown", (event) => {
    const handle = event.target.closest(".session-handle");
    if (!handle || sessionDrag || (event.pointerType === "mouse" && event.button !== 0)) return;
    event.preventDefault();

    const items = [...sessionList.children];
    const item = handle.closest("li");
    const from = items.indexOf(item);
    const rects = items.map((el) => el.getBoundingClientRect());
    // Distance a neighbour moves to make room: the dragged row plus the gap.
    const gap = items.length > 1
        ? (from < items.length - 1 ? rects[from + 1].top - rects[from].bottom : rects[from].top - rects[from - 1].bottom)
        : 0;

    sessionDrag = {
        handle, item, items, rects, from, to: from,
        step: rects[from].height + gap,
        startY: event.clientY,
        pointerY: event.clientY,
        startScroll: sessionScroller.scrollTop,
        pointerId: event.pointerId,
    };
    handle.setPointerCapture(event.pointerId);
    sessionList.classList.add("sorting");
    item.classList.add("dragging");
    sessionDrag.frame = requestAnimationFrame(sessionDragAutoScroll);
});

sessionList.addEventListener("pointermove", (event) => {
    if (!sessionDrag || event.pointerId !== sessionDrag.pointerId) return;
    sessionDrag.pointerY = event.clientY;
    sessionDragLayout();
});

sessionList.addEventListener("pointerup", (event) => {
    if (sessionDrag?.pointerId === event.pointerId) endSessionDrag(true);
});

sessionList.addEventListener("pointercancel", (event) => {
    if (sessionDrag?.pointerId === event.pointerId) endSessionDrag(false);
});

// Keyboard: ↑ / ↓ on a focused handle; focus follows the moved song.
sessionList.addEventListener("keydown", (event) => {
    const handle = event.target.closest(".session-handle");
    if (!handle || !["ArrowUp", "ArrowDown"].includes(event.key)) return;
    event.preventDefault();
    const id = handle.dataset.song;
    moveInSession(id, session.indexOf(id) + (event.key === "ArrowUp" ? -1 : 1));
    sessionList.querySelector(`.session-handle[data-song="${id}"]`)?.focus();
});
