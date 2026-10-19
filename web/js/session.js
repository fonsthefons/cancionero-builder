// Sing Session: an ordered list of songs to practise or play, shown first in
// the menu. Songs are added from the session's search box or with the
// "+ Session" button on each song; reordered by dragging the ⠿ handle
// (session-drag.js); removed with ✕.
// The list is remembered on this device.

const SESSION_KEY = "session";

let session = (() => {
    try {
        const saved = JSON.parse(prefs.get(SESSION_KEY, "[]"));
        if (!Array.isArray(saved)) return [];
        // Keep songs that still exist, once each.
        return [...new Set(saved)].filter((id) => document.getElementById(id)?.classList.contains("song"));
    } catch {
        return [];
    }
})();

const songTitle = (id) => document.getElementById(id).dataset.title;

function renderSession() {
    const list = document.querySelector(".session-list");
    list.replaceChildren(...session.map((id) => {
        const item = document.createElement("li");
        item.dataset.song = id;

        const link = Object.assign(document.createElement("a"), { href: "#" + id, textContent: songTitle(id) });

        const remove = Object.assign(document.createElement("button"), { textContent: "✕" });
        Object.assign(remove.dataset, { action: "session-remove", song: id });
        remove.setAttribute("aria-label", "Remove from session");

        // Drag handle (see session-drag.js); arrow keys also move the song.
        const handle = Object.assign(document.createElement("button"), {
            className: "session-handle",
            textContent: "⠿",
        });
        handle.dataset.song = id;
        handle.setAttribute("aria-label", "Drag to reorder (or use the arrow keys)");

        item.append(link, remove, handle);
        return item;
    }));

    document.querySelector(".session-count").textContent = session.length ? `(${session.length})` : "";
    document.querySelector(".session-empty").hidden = session.length > 0;
    document.querySelectorAll(".session-clear").forEach((button) => { button.hidden = session.length === 0; });

    document.querySelectorAll('.song [data-action="session-toggle"]').forEach((button) => {
        const inSession = session.includes(button.closest(".song").id);
        button.textContent = inSession ? "✓ In session" : "+ Session";
        button.setAttribute("aria-pressed", inSession);
    });
}

function setSession(ids) {
    session = ids;
    prefs.set(SESSION_KEY, JSON.stringify(session));
    renderSession();
}

function addToSession(id) {
    if (!session.includes(id)) setSession([...session, id]);
}

function removeFromSession(id) {
    setSession(session.filter((other) => other !== id));
}

// Move a song to position `to` (0-based) in the session.
function moveInSession(id, to) {
    const from = session.indexOf(id);
    if (from === -1 || to < 0 || to >= session.length || to === from) return;
    const ids = session.filter((other) => other !== id);
    ids.splice(to, 0, id);
    setSession(ids);
}

onAction("session-add", (button) => addToSession(button.dataset.song));
onAction("session-remove", (button) => removeFromSession(button.dataset.song));
onAction("session-toggle", (button, song) => {
    if (session.includes(song.id)) removeFromSession(song.id);
    else addToSession(song.id);
});
onAction("session-clear", () => {
    if (confirm("Clear the whole session?")) setSession([]);
});

// Share: a link with ?session=id1,id2 that replaces the opener's session
// (only the session; their settings and song changes stay).
onAction("session-share", () => {
    const url = new URL(location.pathname, location.href);
    url.searchParams.set("session", session.join(","));
    const text = `Someone shared a song session with you (${document.title})`;
    const copy = () => (navigator.clipboard?.writeText(`${text}\n${url.href}`) ?? Promise.reject())
        .then(() => alert("Link copied"), () => prompt("Copy this link:", url.href));
    // Share sheet only on phones/tablets: desktop ones crash (Arc) or refuse file:// links (Safari).
    if (navigator.share && matchMedia("(pointer: coarse)").matches) {
        navigator.share({ title: document.title, text, url: url.href })
            .catch((error) => { if (error.name !== "AbortError") copy(); });
    } else copy();
});

const shared = new URLSearchParams(location.search).get("session");
if (shared !== null) {
    session = [...new Set(shared.split(","))].filter((id) => document.getElementById(id)?.classList.contains("song"));
    prefs.set(SESSION_KEY, JSON.stringify(session));
    try {
        history.replaceState(null, "", location.pathname + (session.length ? "#" + session[0] : ""));
    } catch {
        // Some browsers refuse this on file:// pages; the session is still applied.
    }
    if (session.length) document.getElementById(session[0]).scrollIntoView();
    setDrawerOpen(true);
}

renderSession();
