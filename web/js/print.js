// Printing: a dialog to choose columns and chords, and a print layout where
// the whole index is unfolded (so every link to a song is in the PDF).

const printDialog = document.getElementById("print-dialog");

onAction("open-print", () => {
    setDrawerOpen(false);
    printDialog.showModal();
});

printDialog.addEventListener("close", () => {
    if (printDialog.returnValue !== "print") return;
    const form = printDialog.querySelector("form");
    document.body.dataset.printColumns = form.columns.value;
    document.body.dataset.printChords = form.chords.value;
    window.print();
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
