// Printing: a dialog to choose columns and chords, and a print layout where
// the whole index is unfolded (so every link to a song is in the PDF).

const printDialog = document.getElementById("print-dialog");

let printingSession = false;

const openPrint = (sessionOnly) => {
    printingSession = sessionOnly;
    setDrawerOpen(false);
    printDialog.showModal();
};
onAction("open-print", () => openPrint(false));
onAction("print-session", () => openPrint(true));

// Session print: only the session's songs, in session order (moved to the
// top of <main> and put back after printing).
const songsMain = document.querySelector("main.songs");
let songOrder = null;

printDialog.addEventListener("close", () => {
    if (printDialog.returnValue !== "print") return;
    const form = printDialog.querySelector("form");
    document.body.dataset.printColumns = form.columns.value;
    document.body.dataset.printChords = form.chords.value;
    if (printingSession) {
        songOrder = [...songsMain.children];
        const picked = session.map((id) => document.getElementById(id));
        picked.forEach((song) => song.classList.add("print-pick"));
        songsMain.prepend(...picked);
        document.body.dataset.printSession = "";
    }
    window.print();
});

window.addEventListener("afterprint", () => {
    if (!songOrder) return;
    songsMain.append(...songOrder);
    songOrder = null;
    delete document.body.dataset.printSession;
    document.querySelectorAll(".print-pick").forEach((song) => song.classList.remove("print-pick"));
});

// However printing starts (button, Ctrl/Cmd+P, share sheet), unfold every
// index section for the printout and put the user's folds back afterwards.
let foldedForPrint = [];

window.addEventListener("beforeprint", () => {
    foldedForPrint = [...document.querySelectorAll(".index details:not([open])")];
    foldedForPrint.forEach((section) => { section.open = true; });
});

window.addEventListener("afterprint", () => {
    foldedForPrint.forEach((section) => { section.open = false; });
    foldedForPrint = [];
});
