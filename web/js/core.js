// Core helpers shared by every feature script. Loaded first.
//
// Buttons declare what they do with `data-action="name"`; features register
// a handler for that name with `onAction`. A single click listener dispatches.

const actionHandlers = {};

// handler(button, song) — `song` is the enclosing .song element, or null.
function onAction(name, handler) {
    actionHandlers[name] = handler;
}

document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const handler = actionHandlers[button.dataset.action];
    if (handler) handler(button, button.closest(".song"));
});

// Set the text of every button with this data-action (e.g. global toggles).
function setActionLabel(action, text) {
    document.querySelectorAll(`[data-action="${action}"]`)
        .forEach((button) => { button.textContent = text; });
}

// Preferences remembered on this device. Storage can be unavailable
// (private mode, blocked site data), so every access is guarded.
// The prefix (book.yaml storage_key) keeps this book's data apart from other
// books on the same site (<user>.github.io hosts every book of that user).
const STORAGE_PREFIX = BOOK.storagePrefix;
const prefs = {
    get(key, fallback) {
        try {
            return localStorage.getItem(STORAGE_PREFIX + key) ?? fallback;
        } catch {
            return fallback;
        }
    },
    set(key, value) {
        try {
            localStorage.setItem(STORAGE_PREFIX + key, value);
        } catch {
            // Not remembered; the setting still applies for this visit.
        }
    },
};

// Changes made to individual songs (transpose, chords, columns), remembered on
// this device: { "<song id>": { transpose: 3, chords: "hide" } }. Song ids come
// from the file name, so they stay the same when songs are added.
// Only non-default values are stored.
const songState = {
    all: (() => {
        try {
            const saved = JSON.parse(prefs.get("songs", "{}"));
            return saved && typeof saved === "object" ? saved : {};
        } catch {
            return {};
        }
    })(),

    get(song, key) {
        return this.all[song.id]?.[key];
    },

    // value null/undefined removes the key (back to the default).
    set(song, key, value) {
        const entry = this.all[song.id] ?? {};
        if (value === null || value === undefined) delete entry[key];
        else entry[key] = value;
        if (Object.keys(entry).length) this.all[song.id] = entry;
        else delete this.all[song.id];
        this.save();
    },

    // Forget one kind of change for every song (e.g. after a book-wide toggle).
    clearKey(key) {
        Object.keys(this.all).forEach((id) => {
            delete this.all[id][key];
            if (!Object.keys(this.all[id]).length) delete this.all[id];
        });
        this.save();
    },

    clearAll() {
        this.all = {};
        this.save();
    },

    save() {
        prefs.set("songs", JSON.stringify(this.all));
    },

    // Songs that still exist on the page with a saved value for `key`.
    each(key, callback) {
        Object.entries(this.all).forEach(([id, entry]) => {
            const song = document.getElementById(id);
            if (song?.classList.contains("song") && key in entry) callback(song, entry[key]);
        });
    },
};

// Forget saved changes of songs that no longer exist (deleted or renamed files).
Object.keys(songState.all).forEach((id) => {
    if (!document.getElementById(id)?.classList.contains("song")) delete songState.all[id];
});
songState.save();

// A display setting with a book-wide value (on <body data-NAME>) that a single
// song can override (on <article class="song" data-NAME>). CSS reads both.
// The book-wide value and the per-song overrides are remembered on this device.
//   values: [default, alternative], e.g. ["show", "hide"]
function songSetting(name, values, onGlobalChange) {
    const other = (value) => (value === values[0] ? values[1] : values[0]);
    const globalValue = () => document.body.dataset[name];

    function setGlobal(value) {
        document.body.dataset[name] = value;
        prefs.set(name, value);
        onGlobalChange(value);
    }

    const saved = prefs.get(name, values[0]);
    setGlobal(values.includes(saved) ? saved : values[0]);

    // Restore per-song overrides (ignoring any that now match the book-wide value).
    songState.each(name, (song, value) => {
        if (values.includes(value) && value !== globalValue()) song.dataset[name] = value;
        else songState.set(song, name, null);
    });

    function clearSongs() {
        document.querySelectorAll(`.song[data-${name}]`)
            .forEach((song) => delete song.dataset[name]);
        songState.clearKey(name);
    }

    return {
        // Flip one song; drop the override when it matches the book-wide value.
        toggleSong(song) {
            const next = other(song.dataset[name] || globalValue());
            if (next === globalValue()) delete song.dataset[name];
            else song.dataset[name] = next;
            songState.set(song, name, song.dataset[name]);
        },
        // Flip the whole book and clear all per-song overrides.
        toggleGlobal() {
            setGlobal(other(globalValue()));
            clearSongs();
        },
        clearSongs,
    };
}

// Lowercase and strip accents so "Señor" matches "senor".
function normalizeText(text) {
    return text.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}
