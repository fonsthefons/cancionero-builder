// The index sections can be folded. When a link points inside a folded
// section, unfold it first so the jump lands on something visible.

function revealTarget(id) {
    let el = document.getElementById(id);
    for (; el; el = el.parentElement) {
        if (el.tagName === "DETAILS") el.open = true;
    }
}

document.addEventListener("click", (event) => {
    const link = event.target.closest('a[href^="#"]');
    if (link) revealTarget(decodeURIComponent(link.hash.slice(1)));
});
