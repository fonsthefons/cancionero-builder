// Display settings: chords, columns, text size and theme.
// Book-wide choices are remembered on this device.

const chordsSetting = songSetting("chords", ["show", "hide"], (value) =>
    setActionLabel("toggle-all-chords", value === "hide" ? "Show all chords" : "Hide all chords"));

const columnsSetting = songSetting("columns", ["1", "2"], (value) =>
    setActionLabel("toggle-all-columns", value === "2" ? "1 column" : "2 columns"));

onAction("toggle-chords", (button, song) => chordsSetting.toggleSong(song));
onAction("toggle-columns", (button, song) => columnsSetting.toggleSong(song));
onAction("toggle-all-chords", () => chordsSetting.toggleGlobal());
onAction("toggle-all-columns", () => columnsSetting.toggleGlobal());

// Put every song back as written: transpose 0, no per-song chords/columns.
onAction("reset-songs", () => {
    document.querySelectorAll('.song[data-transpose]:not([data-transpose="0"])')
        .forEach((song) => setTranspose(song, 0));
    chordsSetting.clearSongs();
    columnsSetting.clearSongs();
    document.querySelectorAll(".song[data-song-scale]").forEach((song) => setSongScale(song, 1));
    songState.clearAll();
});

// ---- Text size: multiplies the fit-to-screen lyrics size (see styles.css) ----
// Book-wide (menu) and per song (song controls); the two multiply.

const TEXT_SCALE = { min: 0.4, max: 3, step: 0.1 };

const clampScale = (scale) =>
    Math.round(Math.min(TEXT_SCALE.max, Math.max(TEXT_SCALE.min, scale)) * 10) / 10;

function setSongScale(song, scale) {
    const rounded = clampScale(scale);
    song.style.setProperty("--song-scale", rounded);
    song.dataset.songScale = rounded;
    song.querySelector(".song-scale-value").textContent = `${Math.round(rounded * 100)}%`;
    songState.set(song, "textScale", rounded === 1 ? null : rounded);
}

const songScale = (song) => Number(song.dataset.songScale || 1);

onAction("song-text-smaller", (button, song) => setSongScale(song, songScale(song) - TEXT_SCALE.step));
onAction("song-text-bigger", (button, song) => setSongScale(song, songScale(song) + TEXT_SCALE.step));
onAction("song-text-reset", (button, song) => setSongScale(song, 1));
songState.each("textScale", (song, scale) => setSongScale(song, Number(scale) || 1));

function setTextScale(scale) {
    const rounded = clampScale(scale);
    document.body.style.setProperty("--text-scale", rounded);
    document.body.dataset.textScale = rounded;
    prefs.set("textScale", rounded);
    document.querySelectorAll(".text-scale-value")
        .forEach((el) => { el.textContent = `${Math.round(rounded * 100)}%`; });
}

const currentTextScale = () => Number(document.body.dataset.textScale);

onAction("text-smaller", () => setTextScale(currentTextScale() - TEXT_SCALE.step));
onAction("text-bigger", () => setTextScale(currentTextScale() + TEXT_SCALE.step));
onAction("text-reset", () => setTextScale(1));
setTextScale(Number(prefs.get("textScale", 1)) || 1);

// ---- Theme: auto (follow the system) / light / dark ----

const THEMES = { auto: "Auto", light: "Light", dark: "Dark" };

function setTheme(theme) {
    if (!(theme in THEMES)) theme = "auto";
    document.body.dataset.theme = theme;
    prefs.set("theme", theme);
    setActionLabel("cycle-theme", THEMES[theme]);
}

onAction("cycle-theme", () => {
    const names = Object.keys(THEMES);
    setTheme(names[(names.indexOf(document.body.dataset.theme) + 1) % names.length]);
});
setTheme(prefs.get("theme", "auto"));
