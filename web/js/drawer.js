// Menu drawer (table of contents + settings), opened from the top bar.

function setDrawerOpen(open) {
    document.body.classList.toggle("drawer-open", open);
    document.getElementById("drawer").inert = !open;
}

onAction("open-drawer", () => setDrawerOpen(true));
onAction("close-drawer", () => setDrawerOpen(false));
setDrawerOpen(false);

// Close after jumping to a section, and with the Escape key.
document.getElementById("drawer").addEventListener("click", (event) => {
    if (event.target.closest("a")) setDrawerOpen(false);
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setDrawerOpen(false);
});
