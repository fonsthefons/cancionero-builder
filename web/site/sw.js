// Service worker: keeps a copy of the book so the home-screen app opens offline.
// Online, it fetches the newest book (and saves it); offline, or if the network
// takes too long, it shows the last saved copy. Only used on the hosted site:
// opening index.html as a file never registers it (see web/js/offline.js).

// Other books on the same site (<user>.github.io) have their own caches: only
// this book's older caches, with this prefix, are ever deleted. The prefix ends
// in "-v" so that "cancionero-v" never matches "cancionero-hakuna-v1".
// Written by the builder from book.yaml's storage_key.
const CACHE_PREFIX = "{{ storage_key }}-v";
const CACHE = CACHE_PREFIX + "1";
const PAGE = "./"; // the book; every page request is answered with it
const FILES = [PAGE, "manifest.webmanifest", "icon-180.png", "icon-512.png"];
const NETWORK_WAIT_MS = 4000; // slow signal: show the saved copy after this

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE)
            .then((cache) => cache.addAll(FILES))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(
                keys.filter((k) => k.startsWith(CACHE_PREFIX) && k !== CACHE)
                    .map((k) => caches.delete(k))))
            .then(() => self.clients.claim())
    );
});

// Fetch the book, skipping a stale browser cache, and save it when it arrives.
function fetchAndSave() {
    return fetch(PAGE, { cache: "no-cache" }).then((response) => {
        if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(PAGE, copy));
        }
        return response;
    });
}

// Newest book if it arrives in time, otherwise the saved copy.
function bookResponse(event) {
    const network = fetchAndSave();
    event.waitUntil(network.catch(() => {})); // keep saving after answering from the cache
    return new Promise((resolve) => {
        let done = false;
        const answer = (response) => {
            if (!done && response) {
                done = true;
                resolve(response);
            }
        };
        const fromCache = () => caches.match(PAGE).then(answer);
        const timer = setTimeout(fromCache, NETWORK_WAIT_MS);
        network
            .then((response) => {
                clearTimeout(timer);
                if (response.ok) answer(response);
                else fromCache().then(() => answer(response));
            })
            .catch(() => {
                clearTimeout(timer);
                caches.match(PAGE).then((saved) => answer(saved || Response.error()));
            });
    });
}

self.addEventListener("fetch", (event) => {
    const request = event.request;
    if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) return;
    if (request.mode === "navigate") {
        event.respondWith(bookResponse(event));
    } else {
        event.respondWith(caches.match(request, { ignoreSearch: true })
            .then((saved) => saved || fetch(request)));
    }
});
