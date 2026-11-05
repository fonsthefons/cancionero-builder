// Psalm fórmulas (book.yaml psalm_tags / formula_tag; only in books that use them).
// A psalm's "Choose fórmula" button picks a semitono or tono recto from a list
// with search; that song's staff, tab and chords are copied above the psalm and
// follow the psalm's transposition. Remembered per psalm on this device
// (songState "formula") and carried in shared session links (session.js).
// Loads before session.js and transpose.js, so it checks their names exist.

// The fórmulas' staff and chords as built: copied now, before transpose.js
// rewrites any of them for their own saved transposition.
const formulaHtml = new Map(BOOK.formulas.flatMap(([, items]) => items).map(([id]) => {
    const song = document.getElementById(id);
    return [id, (song.querySelector(".melody")?.outerHTML ?? "") + song.querySelector(".lyrics").outerHTML];
}));

function setFormula(psalm, id) {
    if (!formulaHtml.has(id)) id = null;
    songState.set(psalm, "formula", id);
    psalm.querySelector(".formula-pick").textContent =
        id ? `Fórmula: ${document.getElementById(id).dataset.title}` : "Choose fórmula…";
    const box = psalm.querySelector(".psalm-formula");
    if (typeof playing !== "undefined" && playing?.song === psalm) stopMelody(); // melody.js
    box.innerHTML = id ? formulaHtml.get(id) : "";
    // Not yet defined while the page loads; melody.js and transpose.js then do this themselves.
    if (typeof melodyObserver !== "undefined") melodyObserver.observe(psalm);
    if (typeof renderChords === "function") renderChords(psalm);
    if (typeof renderSession === "function") renderSession();
}

songState.each("formula", (psalm, id) => {
    if (psalm.querySelector(".formula-pick")) setFormula(psalm, id);
});

// One list for every psalm: search box, the fórmulas by group, no fórmula / cancel.
const formulaDialog = Object.assign(document.createElement("dialog"), { className: "print-dialog formula-dialog" });
formulaDialog.innerHTML = `<input type="search" placeholder="Search fórmulas" aria-label="Search fórmulas">
<div class="formula-options"></div>
<div class="dialog-buttons"><button data-formula="">No fórmula</button><button>Cancel</button></div>`;
const formulaSearch = formulaDialog.querySelector("input");
const formulaOptions = formulaDialog.querySelector(".formula-options");
BOOK.formulas.forEach(([label, items]) => {
    const group = document.createElement("section");
    group.append(Object.assign(document.createElement("h4"), { textContent: label }));
    items.forEach(([id, title]) => {
        const option = Object.assign(document.createElement("button"), { textContent: title });
        Object.assign(option.dataset, { formula: id, search: normalizeText(`${label} ${title}`) });
        group.append(option);
    });
    formulaOptions.append(group);
});
document.body.append(formulaDialog);

let formulaPsalm = null;

// Every typed word must appear in the group or title: "4 glor" finds "Semitonos de 4 … Glorioso".
formulaSearch.addEventListener("input", () => {
    const words = normalizeText(formulaSearch.value).split(/\s+/).filter(Boolean);
    formulaOptions.querySelectorAll("section").forEach((group) => {
        const options = [...group.querySelectorAll("button")];
        options.forEach((option) => { option.hidden = !words.every((word) => option.dataset.search.includes(word)); });
        group.hidden = options.every((option) => option.hidden);
    });
});
formulaSearch.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault(); // else the same Enter clicks the picker button, focused again on close
    formulaOptions.querySelector("button:not([hidden])")?.click();
});

formulaDialog.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if ("formula" in button.dataset) setFormula(formulaPsalm, button.dataset.formula);
    formulaDialog.close();
});

onAction("formula-pick", (button, psalm) => {
    formulaPsalm = psalm;
    formulaSearch.value = "";
    formulaSearch.dispatchEvent(new Event("input"));
    const current = songState.get(psalm, "formula");
    formulaOptions.querySelectorAll("button").forEach((option) => {
        option.setAttribute("aria-pressed", option.dataset.formula === current);
    });
    formulaDialog.showModal();
    // Start at the current choice (and keep phones from opening the keyboard).
    const start = formulaOptions.querySelector('[aria-pressed="true"]') ?? formulaOptions.querySelector("button");
    start.focus();
    start.scrollIntoView({ block: "center" });
});
