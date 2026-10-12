// Offline home-screen app: on the hosted site, register sw.js so the book is
// saved and opens without internet. Skipped when index.html is opened as a file.

if ("serviceWorker" in navigator && /^https?:$/.test(location.protocol)) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("sw.js").catch(() => {});
    });
}
