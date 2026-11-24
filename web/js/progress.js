// Progress checkboxes (book.yaml progress: true; this file is only added then).
// A checkbox next to every song in the contents and a "Hecha" one at the end of
// every song; both show the same state. Ticked songs are green in the contents,
// and a tag or subtag turns green once every song in it is ticked.
// Saved on this device: ids of the ticked songs, as a JSON list under "done".

const doneSongs = new Set((() => {
    try {
        const saved = JSON.parse(prefs.get("done", "[]"));
        return Array.isArray(saved) ? saved : [];
    } catch {
        return [];
    }
})());

function progressBox(songId) {
    const box = document.createElement("input");
    box.type = "checkbox";
    box.className = "done-box";
    box.dataset.song = songId;
    box.setAttribute("aria-label", "Hecha");
    return box;
}

function paintProgress() {
    document.querySelectorAll(".done-box").forEach((box) => {
        box.checked = doneSongs.has(box.dataset.song);
    });
    document.querySelectorAll("#index .song-list li").forEach((item) => {
        const box = item.querySelector(".done-box");
        item.classList.toggle("done", Boolean(box && box.checked));
    });
    // A section (tag, subtag, All Songs) is done when every song inside it is.
    document.querySelectorAll("#index details").forEach((section) => {
        const items = [...section.querySelectorAll(".song-list li")];
        section.classList.toggle("done", items.length > 0 && items.every((li) => li.classList.contains("done")));
    });
}

// The raw href (not link.hash, which is percent-encoded) matches the song's id.
document.querySelectorAll('#index .song-list a[href^="#"]').forEach((link) => {
    link.before(progressBox(link.getAttribute("href").slice(1)));
});
document.querySelectorAll("article.song").forEach((song) => {
    const label = document.createElement("label");
    label.className = "done-toggle";
    label.append(progressBox(song.id), " Hecha");
    song.append(label);
});

document.addEventListener("change", (event) => {
    const box = event.target.closest(".done-box");
    if (!box) return;
    if (box.checked) doneSongs.add(box.dataset.song);
    else doneSongs.delete(box.dataset.song);
    prefs.set("done", JSON.stringify([...doneSongs]));
    paintProgress();
});

paintProgress();
