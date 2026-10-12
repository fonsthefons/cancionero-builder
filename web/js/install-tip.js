// First visit: how to add the book to the home screen (iPhone and Android) so
// it works offline. Shown once per browser, only on the hosted site (offline
// needs sw.js), and never inside the home-screen app itself.
//
// book.yaml `install_tip` picks the look: "popup" (a dialog, #install-tip),
// "banner" (a note at the bottom, .install-banner) or "off" (neither is on the page).

(() => {
    const popup = document.getElementById("install-tip");
    const banner = document.querySelector(".install-banner");
    const installed = window.matchMedia("(display-mode: standalone)").matches
        || navigator.standalone === true; // iOS home-screen app
    if ((!popup?.showModal && !banner) || installed || !/^https?:$/.test(location.protocol)) return;
    if (prefs.get("installTipSeen")) return;
    prefs.set("installTipSeen", "1");
    if (popup?.showModal) popup.showModal();
    else banner.hidden = false;
})();

onAction("close-install-tip", () => {
    const banner = document.querySelector(".install-banner");
    if (banner) banner.hidden = true;
});
