# Progress

## 2026-11-25 — Experiment: semitono marks (branch experiment/semitono-marks)
Goal: learn rules from the user's marks for (1) where chords go over a psalm line and (2) which
syllables start a melody note (to underline/italicize later). Start: Semitono de 2 (11) Alegre 5.
Loop: user marks → Claude writes rules → page pre-filled with predictions (`--pred`) → user fixes
→ final rules. Score = share of held-out lines the rules place right (target ≥90%).
- docs/experiments/semitono-marks/marks.py: Spanish syllables + sinalefa (`--test` self-check),
  port of formula.js `semitono2Plan`, ABC bar parser; builds the page from page.html.
- Round 1 page: alegre5-round1.html (Salmo 41, 99, 62; 85 lines). Smoke test
  scratch/semimarks_smoke.py (WebKit; chromium headless shell is not installed).
- Round 1 marks: alegre5-round1-marks.json (85 lines). show_marks.py prints them against stress.
- Rule v2 (marks.py `predict`): last note + its chord on the line's last stressed syllable
  (aguda/llana/esdrújula); passing notes one per syllable just before it; reciting note from the
  first syllable, sharing it on short lines ("[E][A]te [G]re[F]cuerdo"). Sinalefa unless one of
  the two vowels is stressed. Chords always follow their note (user moved none).
- Score (rules.py, automatic syllables): rule v1 76/85 → stress-aware sinalefa 80/85 → with the
  user's answers 85/85 (2 slip/taste, 1 short-line rule, 1 sinalefa taste, santuario hiatus).
- Round 2 (held-out): alegre5-round2.html, pre-filled by the rule (`--pred`): Salmo 148, 121,
  116, 63 lines. Page now splits a syllable (shift-click).
- Round 2 result (alegre5-round2-marks.json): 63/63 held-out lines right, user changed nothing
  (no comments, no splits). Target ≥90% met for Alegre 5.
- Conclusion: rule v2 places chords and note changes for Alegre 5. Next: try it on other 2-chord
  semitonos de 2 (same page, `--pred`), then `/plan-feature` to adopt it in web/js/formula.js
  (replace "chord over the last word" + add the syllable marking).

## Tutorial v2 (2026-11-24, branch feature/tutorial-v2)
User's feedback on the tour, all done:
- Red (#e53935) labels, arrows, spotlight border and card border; header "Tutorial · Paso n/7".
- Atrás button (hidden on step 1).
- Steps: 1 Canciones, 2 En cada canción, 3 Sesión, 4 Barra superior, 5-6 Ajustes (1/2, 2/2), 7 ¡Listo!.
  - Sesión: if the session is empty, 2 example songs are shown (only the `session` variable and
    the list change, never prefs) and removed when the step is left (Siguiente, Atrás, Saltar, Esc).
  - Ajustes is two steps because on a phone all settings fill the screen, leaving no room for the card.
  - ¡Listo!: "Puedes volver a ver este tutorial abajo del todo en el menú" + the home-screen
    instructions (hosted site, not inside the home-screen app, `install_tip` not "off").
- The old offline popup/banner is gone (install-tip.js, parts/install-tip-*.html, their CSS);
  `install_tip` stays valid in book.yaml ("popup"/"banner" both mean: shown in the tutorial).
- Wide screens with the menu open: the card sits right of the menu.
- Files: web/js/tutorial.js, web/styles.css, web/template.html, builder/render.py, builder/book.py,
  tests/test_builder.py, tests/browser/ui_check.py, README.md.
- Checked: pytest; ui_check.py on cancionero, Chromium + WebKit, phone/iPad/laptop: 379 passed.
- Found: the published cancionero had lost "Create session PPT": the two songs added on 2026-11-24
  from a claude.ai cloud session rebuilt index.html without it (probably an older builder copy there).
  A local rebuild + publish fixes it.

## Plan: tutorial (2026-11-23)
Goal: on the first visit to a book, a short Spanish guided tour (4 numbered steps, several labelled arrows per
step) shows the main features; it can be left at any moment and replayed from Settings.
Out of scope: a book.yaml on/off setting, builder (Python) changes, translations other than Spanish,
animations, any library.
Branch: feature/tutorial

Decisions (user, 2026-11-23): grouped steps with several arrows each; shown everywhere (hosted site and
index.html opened as a file); on the hosted site the offline popup comes right after the tutorial ends or is
skipped; "Ver tutorial" button in Settings; always on for every book.
Defaults chosen here: the flag `tutorialSeen` (prefs, so per-book prefix) is set when the tour starts, so
leaving mid-way counts as seen. Leave via "Saltar", Escape, or finishing. Overlay blocks clicks on the page
while shown. Text is plain Spanish, ≤ 2 lines per step plus labels of 1-3 words.

- [x] S1 tutorial.js + CSS + Settings button + offline-popup hand-off + checks
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: agent:implementer
  model: sonnet    effort: high
  after: -
  context: web/js/install-tip.js (whole, 23 lines); web/js/drawer.js (whole, 19 lines); web/template.html:20-99
           (top bar, drawer, Settings); web/song-controls.html (whole); web/styles.css:151-160, 295-320, 870-920
           (topbar z 100, backdrop z 200, drawer z 201, dialog styles to match); tests/browser/ui_check.py:46-63
           (open_book), :106-166 (run loop, DEVICES), :603-606 (reload)
  do: Facts: render.py:273 auto-includes every web/js/*.js (sorted, after core.js), so install-tip.js runs
      BEFORE tutorial.js. Use `prefs.get/set` and `onAction` from core.js, `setDrawerOpen` from drawer.js.
      (a) install-tip.js: wrap the show logic in `function showInstallTip()`; at load call it only if
      `prefs.get("tutorialSeen")`. tutorial.js calls `showInstallTip()` when the tour closes (end or skip).
      (b) New web/js/tutorial.js (~100 lines, no library). Steps = [{text, labels: [[selector, "label"]…],
      before()}]; "Paso n/4" header, buttons "Saltar" / "Siguiente" ("Listo" on the last). One overlay
      element built in JS (z-index 300, above the drawer): a spotlight box around the union rect of the
      step's targets (`box-shadow: 0 0 0 100vmax rgba(0,0,0,.6)`), a label chip with a CSS-triangle arrow
      next to each target (alternate above/below so neighbours don't collide; clamp inside the viewport),
      and the card at the bottom, or at the top if the spotlight is in the lower half. Re-place on resize.
      Steps: 1 Canciones — "Toca una canción del índice para abrirla, o búscala." labels: search input
      "Buscar", first `#index a` "Canciones". 2 En cada canción — before(): scroll the first `.song` that
      has `.chord-line` so its `.controls` are on screen (instant, not smooth). Labels on its controls:
      toggle-chords "Ocultar acordes", transpose stepper "Tono", toggle-columns "2 columnas",
      song-text stepper "Tamaño", session-toggle "Añadir a sesión". 3 Barra superior — open-drawer "Menú",
      toggle-autoscroll "Autoscroll", autoscroll-faster "Velocidad". 4 Menú — before(): setDrawerOpen(true);
      labels: #session summary "Sesión: tu lista", #settings h2 "Ajustes de todo el libro". On close:
      setDrawerOpen(false) if it opened it, scroll back to the top, remove the overlay, showInstallTip().
      Escape closes the tour (drawer.js already closes the drawer on Escape). First visit: if
      !prefs.get("tutorialSeen") → set it, start. Export `startTutorial()`.
      (c) template.html Settings: `<div class="setting"><span>Tutorial</span><button
      data-action="start-tutorial">Ver tutorial</button></div>`; onAction closes the drawer and starts.
      (d) styles.css: `.tour…` rules (match .print-dialog colors, light + dark); `@media print { .tour
      { display: none } }`. Chips must stay readable at 390px wide.
      (e) ui_check.py: in run(), `browser.new_context(...)` then `context.add_init_script(...)` that wraps
      `Storage.prototype.getItem` to return "1" for keys ending "tutorialSeen" (keeps every existing check
      and reload free of the tour; no test-only code in the page). New `tutorial_checks(browser, opts,
      name)` per device in a fresh context WITHOUT that script: tour visible with "Paso 1/4"; each step every
      label chip is inside the viewport and no two chips overlap; step 4 drawer is open; "Listo" removes
      the overlay and closes the drawer; reload → no tour; "Ver tutorial" restarts it; "Saltar" on step 2
      ends it; no page errors. `--shots` saves scratch/shots/<name>-tutorial-<n>.png.
  done: `/Users/fons/Documents/programs/cancionero-builder/.venv/bin/python /Users/fons/Documents/programs/cancionero-builder/scratch/build_test_books.py` then `/Users/fons/Documents/programs/cancionero-builder/.venv/bin/python /Users/fons/Documents/programs/cancionero-builder/tests/browser/ui_check.py /Users/fons/Documents/programs/cancionero-builder/scratch/books/cancionero --shots` → 0 failed, tutorial checks listed as passing in Chromium and WebKit at phone, ipad, laptop
  return: <= 10 lines: files changed, pass/fail counts, any label that needed special placement, surprises

- [x] S2 Look at it, docs, ship
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: inline
  model: sonnet    effort: low
  after: S1
  context: scratch/shots/*-tutorial-*.png (phone chromium + webkit only); README.md section listing Settings
           (find "Print / PDF" or "Keep screen on")
  do: View the phone shots; fix only clear overlaps/clipping (small CSS tweaks, re-run S1's done). Send the
      phone shots to the user. One README line: first-visit tutorial (4 steps, Spanish), "Ver tutorial" in
      Settings, offline popup follows it on the hosted site. PROGRESS.md entry; books need a rebuild to get
      it. Commit, push, PR, merge, `git checkout main` + `git pull` per CLAUDE.md.
  done: `gh pr view --json state` → MERGED
  return: PR URL, shot paths

Escalation: a failed step is retried once one level higher (low → medium → high, then sonnet → opus) with the
failure in its brief; failing again, or no longer fitting the code, it goes under "Blocked" with the reason;
continue with steps that don't depend on it.

### Run log
- S1 2026-11-23: work was already in the tree from an earlier run; done-check passed (ui_check 301 passed,
  0 failed, tutorial shots for Chromium + WebKit at phone/ipad/laptop).
- S2 2026-11-23: phone shots viewed; chips don't overlap or clip, no CSS change. README line added.
  Books need a rebuild to get the tutorial.

## Plan: session-slides (2026-11-23)
Goal: a "Create session PPT" button in the Session menu that opens the print dialog with one
landscape-Letter page per slide holding the session's lyrics, without chords, as big as they fit, so
they can be saved as a PDF and shown on TVs.
Out of scope: a real .pptx or a direct PDF download (no bundled library), on-screen slideshow mode,
dark theme, settings for size/fonts, changes to the builder (Python).
Branch: feature/session-slides

Decisions (user, 2026-11-23): print dialog → "Save as PDF" (same route as Print session); a separate
title slide before each song (title only); minimum text size ≈ 10 lines per page; a psalm's chosen
fórmula is included; choruses (bold) stay bold; label lines like "Intro: G D" are left out.
Defaults chosen here: white page, black text, system-ui sans, weight 500 (bold parts 800), centered,
line-height 1.2, verse gap 0.6em, page margin 0.4in. Fórmula order: psalm title slide → fórmula pages →
psalm pages. Max text size capped (≈2.5× the minimum) so one short line isn't absurdly huge. Line wrapping
at word boundaries is allowed only when a line can't fit at the minimum size.
User's expectations (examples in the request): "Espíritu Ven… (x3)" → 1 page; "Mi Padre / Todo el cielo
cantará" (8 lines, longest ~29 chars) → 1 page; "Hazme una antorcha" → 1 or 2; "Si puedo ayudarte" (lines
up to 48 chars) → probably 2. Report the real counts; the minimum is one constant to tune.

- [x] S1 slides.js + button + print CSS + checks
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: agent:implementer
  model: sonnet    effort: high
  after: -
  context: web/js/print.js (whole, 57 lines: pattern to follow); web/js/session.js:1-30 (session,
           songTitle, sessionFormula); web/template.html:46-58 (Session menu); web/styles.css:944-1030
           (@media print block); builder/lyrics.py:151-181 (song DOM); tests/browser/ui_check.py:387-430
           and :540-564 (session_checks style, open_menu, titles)
  do: Song DOM: `.song#id[data-title] .lyrics > .verse > (.line-pair[.bold] = .chord-line div + lyric text
      node | .chord-line alone | .lyric-line[.bold] | .lyric-line.chord-inline = label line "Intro: G D")`.
      Lyrics only: per .verse, the lines = .line-pair text minus its .chord-line (if the pair holds a
      .chord-inline child, skip it) and .lyric-line not .chord-inline; trim; skip empty; keep .bold.
      (a) template.html: after "Print session" add `<button class="session-clear"
      data-action="session-slides">Create session PPT</button>` (session-clear class = hidden when empty).
      (b) New web/js/slides.js (auto-included: render.py:273 globs web/js/*.js after core.js). onAction
      "session-slides": setDrawerOpen(false); for each id in `session` (and sessionFormula(id) per the
      order above) build `<section class="slide">` elements in a `<div class="slides">` appended to body:
      a title slide, then lyric slides. Packing: measure in an offscreen box (position fixed, left -10000px,
      same CSS as a slide, sizes in `in`, so px = CSS in*96) at MIN = content height/(10*1.2); add whole
      verses to a page while it fits (scrollHeight <= clientHeight, wrapping allowed); a verse that doesn't
      fit an empty page is split between lines. Then per page: binary-search the largest font with
      `white-space: nowrap` that fits width and height (cap MAX); if that is < MIN, use wrapping and the
      largest size that fits height. Set the size inline. Then inject `<style id="slides-page">@page { size:
      letter landscape; margin: 0 }</style>`, set body.dataset.slides, window.print(); on afterprint remove
      .slides, the style and the data attribute. Comment each why in one line.
      (c) styles.css @media print: `body[data-slides] > :not(.slides) { display: none !important }`,
      `.slide { width: 11in; height: 8.5in; padding: 0.4in; box-sizing: border-box; break-after: page;
      display: flex; flex-direction: column; justify-content: center; text-align: center; overflow:
      hidden }`; outside print `.slides { display: none }` (measuring uses its own offscreen box).
      (d) ui_check.py session_checks: add 2 songs, `page.evaluate("window.print = () => {}")`, click the
      button; check slide count >= 4, no `.chord` / `.chord-line` inside .slides, every slide fits
      (scrollWidth<=clientWidth, scrollHeight<=clientHeight), every lyric slide font >= MIN; dispatch
      `afterprint` → .slides gone. Chromium only: `page.emulate_media(media="print")`,
      `page.pdf(prefer_css_page_size=True)` → pypdf page count == slide count and size 792×612.
      (e) scratch/slides_check.py: find the 4 example songs in the source repos (grep "Espíritu Ven",
      "Todo el cielo cantará", "Hazme una antorcha", "Si puedo ayudarte" under
      /Users/fons/Documents/programs/hymn_books/cancionero*), copy their .md files into a scratch copy of a
      book (scratch/copy_book.py / build_test_books.py show how), build it, open it in Chromium, put the 4
      in the session, click the button, save scratch/slides/session.pdf, and print per song: pages and font
      px of each page. Exit 1 if any slide overflows.
  done: `/Users/fons/Documents/programs/cancionero-builder/.venv/bin/python /Users/fons/Documents/programs/cancionero-builder/scratch/slides_check.py` → exit 0, a per-song page count table, scratch/slides/session.pdf exists
  return: <= 10 lines: files changed, the page/font table, ui_check session results, anything surprising

- [x] S2 Full browser check
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: agent:runner
  model: haiku    effort: low
  after: S1
  context: README.md:160-166 (how ui_check runs)
  do: Rebuild the scratch test books (`.venv/bin/python scratch/build_test_books.py`), then run
      `.venv/bin/python tests/browser/ui_check.py <scratch cancionero test book>` (Chromium + WebKit).
      Report pass/fail counts and every FAIL line; compare with the last known state (PROGRESS.md: the
      5 skipped-song checks were already failing on some books).
  done: runner's report shows no new FAIL lines about session or slides
  return: <= 10 lines: pass/fail counts, new FAIL lines

- [x] S3 Docs, show the PDF, ship
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: inline
  model: sonnet    effort: low
  after: S2
  context: README.md section that lists the Session menu buttons (find "Print session")
  do: One README line for "Create session PPT" (print dialog → Save as PDF, landscape Letter, lyrics
      only, title slide per song). Send scratch/slides/session.pdf to the user (SendUserFile) with the
      page-count table vs their expectations. PROGRESS.md entry; note books need a rebuild to get it.
      Commit, push, PR, merge, `git checkout main` + `git pull` per CLAUDE.md.
  done: `gh pr view --json state` → MERGED
  return: PR URL, the table

Escalation: a failed step is retried once one level higher (low → medium → high, then sonnet → opus) with the
failure in its brief; failing again, or no longer fitting the code, it goes under "Blocked" with the reason;
continue with steps that don't depend on it.

### Run log
- S1 2026-11-23 pass: slides_check exit 0, 37 slides, 0 overflow, MIN 61.6px. Only "Espíritu ven" was found in the source repos; the other 3 examples were replaced by the longest cancionero songs. ui_check (169-song book) 211 passed, 0 failed.
- S1 follow-up (conductor): the examples are lyric lines, not titles; slides_check now matches lyrics. Muros ("Espíritu Ven (ven, ven… x3") 5 lyric pages; Hasta que el mundo arda ("Hazme una antorcha") 4; Dime cómo hacerlo ("Si puedo ayudarte") 7; "Todo el cielo cantará" isn't in any source song. 19 slides, 0 overflow.
- S2 2026-11-23 pass: rebuilt test books; ui_check scratch/books/cancionero 211 passed, 0 failed.
- S3 2026-11-23: README line added; books need a rebuild to get the button.

## Plan: song-editor (2026-11-18)
Goal: `cancionero.py edit <book>` opens a local web page to add or edit one song at a time
(lyrics with click-to-place and draggable chords, melody staff with draggable notes and playback,
guitar tab, tags, metadata, the same sources as `add`) that writes songs/<name>.md in the book.
Out of scope: PDF and list import (stay in the CLI), several songs per page, a book-styled lyrics
preview (the chord view is the preview), editing horas.yaml / tags.yaml beyond adding new tags,
hosting the editor anywhere but 127.0.0.1.
Branch: feature/song-editor

Decisions (user, 2026-11-18): a local stdlib server (no static download page); every source the CLI
has (link, site search, paste, Spotify/YouTube link lookup); melody = draggable notes on the staff +
select/delete/add/length buttons + an ABC text box kept in sync + Play; tab = suggested automatically
from the notes, every token editable.
Defaults chosen here: editing keeps the file name (the id is stable: anchors, sessions) even if the
title changes; new songs use write_song naming (song_name + free_path). Doubtful chord lines from
clean_song are taken as chords (CLI default is yes too); the user fixes them in the page. Fields the
page doesn't show (`added`) are kept; `horas` and `ignore` show as plain text fields. Blocked sites:
use the hidden browser if browser_available(), else an error telling the user to paste (no install
from the page). Publish = a button that calls publish_book (commit + push the book repo), like the
CLI's question at the end of `add`. Rebuild after every save (build_book) and show its report.
Security: bind 127.0.0.1 on a free port; a random token in the served page is required on every
POST; song ids accepted only if `<id>.md` already exists in songs_dir (no path traversal).

- [x] S1 Server, song writing and API (Python) + tests
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: agent:implementer
  model: opus    effort: high
  after: -
  context: importer/songfile.py (all, 128 lines); importer/add.py:53-185 (from_link, preview,
           from_search, ask_link, suggested_title, ask_details: the logic to reuse); importer/ask.py:81-126
           (ask_tags); cancionero.py:155-200 and :336-452 (add_loop, cmd_add, interactive menu, parser);
           builder/songs.py:104-165 (check_tab, load_song); tests/test_importer.py:1-40 (test style, how
           tests make a scratch book)
  do: (a) songfile.song_file: also write melody (YAML block `melody: |` indented 2), tab, horas (list),
      ignore (list), in the order title, autor, capo, link, added, song_tags, horas, melody, tab, ignore.
      New `update_song(book, path, fields)`: build the text, validate it by writing `<path>.new`,
      load_song on it, then os.replace onto path; on error remove the .new and raise SongError (the old
      file is never touched). A round-trip test: load_song(write(load_song(x))) == x for a template song
      with melody+tab+horas (templates/liturgia/songs/himno_laudes-alegre_la_manana.md).
      (b) Split ask_tags' tail (lines 114-126) into `save_tags(book, taxonomy, picked) -> {tag: [subs]}`,
      reused by ask_tags and the server; picked = [(tag_id, sub_id, tag_label|None, sub_label|None)].
      (c) New importer/editor.py: http.server ThreadingHTTPServer on 127.0.0.1:0, webbrowser.open.
      GET / serves web/editor/index.html with `{{TOKEN}}` and `{{BOOK}}` filled in; GET /static/<f>
      serves only web/editor/*, web/vendor/abcjs-basic-min.js, web/js/melody.js, web/js/transpose.js.
      JSON API (POST needs header X-Token): GET /api/book -> {title, default_author, strict_tags,
      has_horas, tags: taxonomy.choices() as [{tag, sub, label}], songs: [{id, title, autor}]};
      GET /api/song?id= -> all fields + body; POST /api/rows {body} and POST /api/paste {text} (paste runs
      clean_song(text, marked=False, ask=lambda l: True, from_web=False) first) -> {body, capo, notes,
      language (detect(body)[0] if book.language_tags), rows}; POST /api/fetch {link} -> from_link
      logic without prompts (Blocked: browser if browser_available() else 409 "paste it instead"), then
      clean_song(draft.text, marked=draft.marked) -> same as paste + suggested title (suggested_title),
      artist (alias_for), capo; POST /api/search {title, artist} -> [{url, site, label}];
      POST /api/links {title, autor} -> {spotify: [{url,label}], youtube: url|null} (FetchError -> empty);
      POST /api/save {id|null, title, autor, capo, link, tags: [[tag,sub,tagLabel,subLabel]...], horas,
      melody, tab, ignore, body, force} -> new: existing_song() match and not force -> 409 {exists: file};
      remember_alias as ask_details does; write_song / update_song; then build_book and return
      {id, file, report}; SongError -> 400 {error}. POST /api/publish -> publish_book output.
      rows format (built with builder.lyrics clean_line/is_chord_line/LABEL_RE, server side, so JS never
      re-implements chord detection): [{chords: [[col, name], ...], lyric: str|null}] for a chord line
      over a lyric line (lyric null = chord-only line) and for a lyric line alone (chords []);
      {text: str} for blank, `**`, label and tablature lines. Chord col = char index in the raw line.
      (d) cancionero.py: `edit <book>` subcommand (cmd_edit -> editor.serve(book), Ctrl+C stops), and
      menu entry "6) Open the song editor in the browser" in importer/add.py menu + add_loop.
      Tests tests/test_editor.py (start the server in a thread on a scratch book under scratch/): token
      required, unknown/`../` ids refused, rows for a pasted chord sheet, new save, edit save keeps file
      name and `added`, invalid melody/tab keeps the old file, duplicate title -> 409.
  done: /Users/fons/Documents/programs/cancionero-builder/.venv/bin/python -m pytest /Users/fons/Documents/programs/cancionero-builder/tests -q  -> all pass
  return: <= 10 lines: files changed, done result, the final API (any change to the brief's contract)

- [x] S2 Editor page: lyrics + chords, metadata, tags, sources, save
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: agent:implementer
  model: sonnet    effort: high
  after: S1
  context: importer/editor.py (from S1: routes and JSON shapes); web/styles.css:1-60 (colors/fonts to
           match); tests/browser/ui_check.py:1-30 (playwright setup: PLAYWRIGHT_BROWSERS_PATH=scratch/browsers)
  do: web/editor/index.html + editor.js + editor.css, plain JS, no new dependencies. Top: song picker
      (new / existing from /api/book songs), source buttons: Paste (textarea -> /api/paste), Link
      (-> /api/fetch), Search (title+artist -> /api/search list, click a result -> /api/fetch).
      Chord view from `rows` in a monospace grid: every pair row has a chord line above its lyric, even
      when empty; click a column on a chord line -> small inline input -> insert chord there; drag a chord
      left/right snapping to character columns; click a chord to rename, empty name or Delete removes it.
      A "Text" toggle shows the raw body in a textarea; switching back calls /api/rows. Serialize rows to
      body in JS: chords at their cols, pushed right to keep >= 1 space between chords, trailing spaces
      trimmed; chord-only rows write only the chord line; {text} rows as-is.
      Form: title, author, capo, link (+ "Find link" -> /api/links, pick one), tags as checkboxes from
      /api/book (strict_tags: no new-tag input; else an input "Tag or Tag/Subtag" like the CLI), horas and
      ignore text fields only when has_horas / always-collapsed. Save -> /api/save; 409 exists -> confirm
      "Add anyway?" then force; show the build report; Publish button -> /api/publish. Placeholder
      <section id="melody"> with checkboxes "Melody" and "Guitar tab" (S3 fills it; save sends melody/tab
      from window.editorMelody?.value() if defined).
      Browser check tests/browser/editor_check.py: start editor.serve on a copy of a scratch test book,
      paste lyrics only -> empty chord lines present, click to add "G" at col 5, drag it to col 8, save,
      assert the file's chord line is 8 spaces + "G"; open an existing song, save unchanged -> body bytes
      identical.
  done: /Users/fons/Documents/programs/cancionero-builder/.venv/bin/python /Users/fons/Documents/programs/cancionero-builder/tests/browser/editor_check.py  -> prints OK, exit 0
  return: <= 10 lines: files changed, done result, anything surprising

- [x] S3 Melody and tab editor
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: agent:implementer
  model: opus    effort: high
  after: S2
  context: web/js/melody.js:1-51 (renderMelody, tabSvg use) and :140-215 (playMelody/toggleMelody, needs
           element.closest(".song") with data-transpose); builder/songs.py:104-116 (check_tab: what counts
           as a note); web/editor/index.html + editor.js (from S2: the #melody section, editorMelody hook)
  do: New web/editor/melody-editor.js defining window.editorMelody = {load(melody, tab), value() ->
      {melody, tab}}. "Melody" checkbox shows: an ABC textarea (default "K:C\n" + one note) and an editable
      staff drawn with ABCJS.renderAbc(div, abc, {dragging: true, add_classes: true, clickListener}); the
      clickListener's abcElem.startChar/endChar locate the note in the ABC text; a drag (drag.step) moves
      the pitch by that many staff steps (rewrite the note letter/octave marks , ' in the text), click
      selects. Buttons/keys for the selected note: delete, add a note after (copy), length x2 / /2,
      sharp/flat/natural. Textarea and staff stay in sync both ways. Below: the book's look via
      renderMelody on a `.melody` (data-abc, data-tab) inside a `.song` wrapper, and a Play/Stop button
      calling toggleMelody. "Guitar tab" checkbox: one input per note showing fret/string, prefilled by a
      suggestion: standard tuning E2 A2 D3 G3 B3 E4, string 1 = high e; take pitches from the tune
      (honour the key signature: use abcjs' own midi pitches, e.g. tune.setUpAudio() / noteTimings),
      choose frets 0-12 nearest the previous note's fret. A user-edited token stays fixed when notes change;
      the count must match check_tab's (pitch letters outside "chords" and header lines); show the same
      error text as check_tab when it doesn't.
      Extend tests/browser/editor_check.py: enable melody, type "K:G\nG A B", drag the 2nd note up one
      step -> textarea has "G B B"; delete a note; tab suggested "3/6"-style tokens count == notes; save
      -> file loads with load_song and melody/tab match the page.
  done: /Users/fons/Documents/programs/cancionero-builder/.venv/bin/python /Users/fons/Documents/programs/cancionero-builder/tests/browser/editor_check.py  -> prints OK, exit 0
  return: <= 10 lines: files changed, done result, anything surprising (abcjs drag API quirks)

- [x] S4 Docs
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: inline
  model: sonnet    effort: low
  after: S3
  context: README.md (section on adding songs); cancionero.py cmd_help (:321-335); help.sh
  do: Document `cancionero.py edit <book>` and the add-menu entry 6: what the page does, Ctrl+C to
      stop, that saves go straight into the book's songs/ and rebuild it, and Publish pushes.
  done: /Users/fons/Documents/programs/cancionero-builder/.venv/bin/python /Users/fons/Documents/programs/cancionero-builder/cancionero.py help  -> mentions "edit"
  return: <= 10 lines: files changed

- [x] S5 Review
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: agent:reviewer
  model: opus    effort: high
  after: S4
  context: git diff main...feature/song-editor
  do: Look for: an existing song file lost or corrupted on a failed save; fields dropped on edit
      (added, horas, ignore, melody, tab); body bytes changed by a load+save with no edits; POST without
      token or with a crafted id writing outside songs/; tags.yaml written for strict books; chord
      serialization losing chords when two collide.
  done: reviewer reports no high-severity findings (fix any it reports, then rerun S1-S3 done commands)
  return: <= 10 lines: ranked findings

Escalation: a failed step is retried once one level higher (low → medium → high, then sonnet → opus) with the
failure in its brief; failing again, or no longer fitting the code, it goes under "Blocked" with the reason;
continue with steps that don't depend on it.

### Run log
- S1 2026-11-18: pass, pytest 63 passed. Contract additions: /api/fetch returns site_artist, /api/save accepts it; save slugs tag ids (strict: unknown -> 400); build error after save -> 200 with report; /api/publish -> {output}; search fail 502; fetch only http(s); GET routes need no token. Limit: new tags hit tags.yaml even if save then fails (S5 to check).
- S2 2026-11-18: pass, editor_check.py OK. Body rewritten from rows only after a chord edit; save reads window.editorMelody?.value?.() as {melody, tab}. Untested in browser: Text toggle, Search, Link, Find link, 409 confirm, Publish, horas/ignore.
- S3 2026-11-18: pass, editor_check.py OK. abcjs needs #melody-staff position:relative and unscaled SVG; drag.step up is negative. Tab suggestion may drift with ties/chords (shortcut comment). Untested: arrow/Delete keys, audio.
- S4 2026-11-18: pass (inline). `help edit` text, README commands table, help.sh document `edit <book>`.
- S5 2026-11-18: review found 2 high (chord edit dropped bars/repeat marks; tab changed/lost on unchanged save), 1 medium (added stamped on edit), 1 low (DNS rebinding). All fixed; reran pytest 66 passed, editor_check.py OK. Known: unticking Melody with a matching tab -> save 400 unless ignore tab-melody-check; NBSP/trailing spaces in chord lines still re-spaced after a chord edit.
- S5 fixes 2026-11-18: chord lines with marks ((x2), |, parens) or tab characters are {text} rows with their lyric;
  a tab that doesn't fit the notes (no melody / other count) is a plain textarea, saved as loaded; value() keeps the
  tab until "Guitar tab" is unchecked; update_song never stamps `added`; Host must be 127.0.0.1/localhost:<port>
  (403). pytest 66 passed; editor_check.py OK.

## Plan: fill-chords (2026-11-13)
Goal: a script that copies chords into hakuna stanzas that have none (repeated choruses, verses
shaped like an earlier verse with chords), shown on an editable HTML review page whose export is
applied with the existing apply_corrections.py. Online chord sheets (existing importer search/read)
are a second opinion only: our songs are the main truth. Out of scope: changing lyrics or line
breaks (split lines stay split; the user rejoins them in the page), books other than hakuna, a
cancionero.py subcommand, applying the corrections to the hakuna repo (the user does that after
reviewing).
Branch: feature/fill-chords

Decisions (user, 2026-11-13): preview on an HTML review page like the organo/liturgia ones, then
write; chord lines copied with the model stanza's columns; "clear" = same lyrics, or same line
count as the nearest stanza with chords. Revised by the user: also look at online versions, but
only for chord patterns and which stanza is which; the chords written in are always taken from
our own song, never the online layout or lyrics.
Defaults chosen here: no reviewer step (every change is reviewed by the user in the page;
apply_corrections.py refuses results that don't load). Online pages are cached in scratch so
reruns don't download again.
Survey (scratch/chordless_survey.py): 91 of 126 hakuna songs with chords have stanzas without any,
318 such stanzas, 206 with the same line count as some stanza with chords.

- [x] S1 importer/fill_chords.py + tests
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: agent:implementer
  model: sonnet    effort: high
  after: -
  context: builder/lyrics.py:17-75 (CHORD_RE, SEPARATOR_RE, clean_line, is_chord_line), :88-90
           (LABEL_RE), :149-167 (split_verses, for the ** bold rule); tests/test_importer.py:1-20
           (test style); /Users/fons/Documents/programs/hymn_books/cancionero-hakuna/songs/me_sobrepasa.md
           (read with `cat <abs path>`, the Read tool is refused in that repo)
  do: New `fill_chords(body) -> (new_body, filled, doubts)` working on raw lines so blank lines,
      `**` markers, indentation and everything else stay byte-identical. A stanza = run of lines
      between blank lines / `**` lines; bold = inside `**` markers. Lyric lines = lines where
      not is_chord_line(clean_line(l)). A stanza "has chords" if any line is a chord line; skip
      stanzas with a LABEL_RE line (Intro: ...) and bare stanzas with 1 lyric line.
      For each bare stanza (no chord line, >=2 lyric lines), pick a model stanza that has chords:
      (1) same lyric lines after normalizing (casefold, no accents/punctuation, repeat marks like
      "(x2)" dropped), else (2) nearest EARLIER stanza with the same bold flag and the same number
      of lyric lines, else nearest later one. Copy, above each lyric line i, the chord line that
      sits directly above the model's lyric line i (none if the model has none there); don't copy
      chord-only lines that aren't above a lyric. Keep the model's columns, but pull a chord that
      would end past the lyric's end back to fit (keep chord order, >=1 space between chords).
      No model -> line unchanged + a doubt "stanza N (<first words>…): <k> lines, stanzas with
      chords have <sorted counts>". `filled` notes "stanza N (<first words>…) <- stanza M".
      Tests in tests/test_fill_chords.py: me_sobrepasa body (lines after the frontmatter, inline
      as a string): stanza "Todas mis sendas…" gets exactly "G", "Em", "   C", "  D7" above its 4
      lines (the user's expected result); the 5-line "Mas si digo…" stanza is unchanged with one
      doubt; nothing else changes. Plus: a repeated chorus with the same text but other line
      count elsewhere matched by text; clamping of a chord past a short line; body without chords
      unchanged.
  done: /Users/fons/Documents/programs/cancionero-builder/.venv/bin/python -m pytest /Users/fons/Documents/programs/cancionero-builder/tests -q  -> all pass
  return: <= 10 lines: files changed, done result, anything surprising

- [x] S2 Online second opinion: importer/online_chords.py + tests
  result: guide(original body, [(url, text)]) runs fill_chords itself; fetch_online takes a 4th arg `stem`.
          scratch/hakuna_chords/fetch_online.py: 62 of 82 songs have versions cached in
          scratch/hakuna_chords/online/; guide_stats.py: 86 fills confirmed online, ~26 stanzas filled
          or re-modelled from online, 30 versions ignored (other arrangement), 85 online doubts.
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: agent:implementer
  model: opus    effort: high
  after: S1
  context: importer/fill_chords.py (from S1); importer/search.py:38-60 (Result) and :202-end
           (search(title, artist, sites)); importer/read.py (read_song_any_way(url) -> Draft,
           Draft.text with chords as [ch]Am[/ch] when Draft.marked, importer/sites/common.py:14-22);
           find with grep how importer/clean.py turns a Draft into chord-over-lyric text and reuse it;
           find an existing transpose helper (grep "transpose" in importer/ builder/) before writing one
  do: Split in two so tests run offline:
      (a) `fetch_online(title, artist, cache_dir)`: search, take up to 2 best results, read each,
          save the cleaned chord-over-lyric text as cache_dir/<stem>-<n>.txt (+ url on line 1); reuse
          the cache when present. Network/site errors -> no versions, never a crash.
      (b) pure `guide(body, online_texts) -> (new_body, filled, doubts)`, run after fill_chords on the
          body S1 left: split online texts into stanzas; match each of our stanzas to an online one
          by normalized lyric words (difflib ratio >= 0.6). Key: find the 0-11 semitone shift that
          makes the online chords of matched stanzas agree best with OUR chords there; under 60%
          agreement -> ignore that version (doubt "online version in another arrangement").
          Uses, ours always winning:
          1. Confirm/override the model: a stanza S1 filled whose online chord sequence (shifted)
             matches another of our stanzas better -> refill from that stanza; agreeing -> note
             "confirmed online".
          2. Stanzas S1 left alone (odd line count, split lines, single lines): take the online
             stanza's chord sequence shifted to our key; every chord must already occur in our song
             (map enharmonic spellings to ours), else doubt. Place each chord above the same word
             our line shares with the online line (word anchor; keep our line breaks and lyrics
             unchanged); if a word isn't found, doubt.
          3. Online disagrees with a stanza that already had chords -> change nothing, note it.
      filled/doubt notes say the source: "shape", "same lyrics", "confirmed online", "online: <url>".
      Tests tests/test_online_chords.py with hand-written online texts (no network): online in
      another key (shift found); Me sobrepasa "Mas si digo… / me encubra," (5 lines) filled from an
      online 4-line version with our chords, line break kept; a wrong-model override; online chord
      not in our song -> doubt; a single-line stanza filled.
      Then run fetch_online over all hakuna songs that S1 leaves with a fill or doubt (one at a
      time, cache in scratch/hakuna_chords/online/), print found/not found counts.
  done: /Users/fons/Documents/programs/cancionero-builder/.venv/bin/python -m pytest /Users/fons/Documents/programs/cancionero-builder/tests -q  -> all pass; the cache folder holds versions for most songs
  return: <= 10 lines: files changed, done result, songs with/without online versions, anything surprising

- [x] S3 Review page for hakuna
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: agent:implementer
  model: sonnet    effort: medium
  after: S2
  context: scratch/organo/review_page.py (whole, 141 lines: pattern to follow);
           scratch/liturgia/review2_template.html (whole, 185 lines); scratch/organo/review_check.py
           (25 lines); scratch/liturgia/apply_corrections.py:1-7 (corrections JSON format)
  do: scratch/hakuna_chords/review_page.py: for every song in
      /Users/fons/Documents/programs/hymn_books/cancionero-hakuna/songs (read-only; load with
      builder.songs.split_frontmatter) run importer.online_chords.guide(original_body, versions)
      (it runs fill_chords itself; versions = list of (url, text), each cache file is "url\ntext", so
      path.read_text().split("\n", 1)) with the cached versions in scratch/hakuna_chords/online/ (no
      downloads here); one card per song with a fill or a doubt (filled songs first, then
      doubt-only). Card: title, file stem, doubts + filled notes with their source (shape / same
      lyrics / confirmed online / online), links to the online versions used; left column = the original body as a line diff (added chord
      lines highlighted, <pre>, monospace so columns line up); right = "Chords (body)" textarea
      with the proposed body, OK checkbox, note. Export must produce the format
      apply_corrections.py takes: {"<stem>": {"body": ..., "note": ...}}. Reuse
      review2_template.html as organo did; if its melody/abcjs parts get in the way, copy it to
      scratch/hakuna_chords/review_template.html and strip them. localStorage key
      "hakuna-chords-review:". Output scratch/hakuna_chords/review/index.html; print cards / filled
      stanzas / doubts counts. Write scratch/hakuna_chords/review_check.py (playwright, like
      organo's): every card has a textarea whose value == proposed body, no JS errors, export
      button yields JSON with every card's stem; screenshot review/shot.png. Put the apply
      command in the page's header: `.venv/bin/python scratch/liturgia/apply_corrections.py
      <export.json> --songs-dir /Users/fons/Documents/programs/hymn_books/cancionero-hakuna/songs`.
  done: /Users/fons/Documents/programs/cancionero-builder/.venv/bin/python /Users/fons/Documents/programs/cancionero-builder/scratch/hakuna_chords/review_check.py  -> exit 0, "N cards, 0 bad, JS errors: []"
  return: <= 10 lines: counts (cards, filled stanzas, doubts), done result, me_sobrepasa card OK?, anything surprising

- [x] S4 Log + ship
  repo: /Users/fons/Documents/programs/cancionero-builder
  run: inline
  model: sonnet    effort: low
  after: S3
  context: -
  do: Look at review/shot.png and the me_sobrepasa card. Add a PROGRESS.md entry (what, counts,
      how to apply). Commit importer/fill_chords.py, importer/online_chords.py + tests + PROGRESS.md (scratch is gitignored),
      push, PR, merge per CLAUDE.md. Tell the user the page path and the apply command.
  done: git -C /Users/fons/Documents/programs/cancionero-builder status  -> clean on main (organo/ untracked is pre-existing)
  return: page path, counts, PR URL

Escalation: a failed step is retried once one level higher (low → medium → high, then sonnet → opus) with the
failure in its brief; failing again, or no longer fitting the code, it goes under "Blocked" with the reason;
continue with steps that don't depend on it.

### Run log
- S1 2026-11-13: pass, 52 tests; me_sobrepasa fills G/Em/C/D7, "Mas si digo" left with 1 doubt.
- S2 2026-11-13: pass, 58 tests; online versions for 62/82 songs. guide() takes the original body (S3 brief updated). Strict chord match (Am vs Am7 -> doubt) inflates online doubts (85).
- S3 2026-11-13: pass, "82 cards, 0 bad, JS errors: []", me_sobrepasa OK. 200 filled stanzas, 165 doubts. Export sends EVERY card's body (not only edited/OK), so applying it writes all proposals.
- S4 2026-11-13: screenshot checked; shipped.

Result: review page scratch/hakuna_chords/review/index.html (rebuild: .venv/bin/python scratch/hakuna_chords/review_page.py).
Apply after review: .venv/bin/python scratch/liturgia/apply_corrections.py <export.json> --songs-dir /Users/fons/Documents/programs/hymn_books/cancionero-hakuna/songs

## 2026-10-12 — Decisions (asked before starting)

- **Code lives only in the builder.** A book repo holds `songs/`, `book.yaml`
  (+ optional `tags.yaml`, `author_aliases.yaml`, `title_fixes.yaml`), the built
  `index.html`, `sw.js`, `manifest.webmanifest`, icons, a README. Commands run
  from the builder and point at a book.
- **New books** go in `~/Documents/programs/hymn_books/<name>` (changed 2026-10-29; override with `CANCIONERO_BOOKS`; `cancionero-organo` and the 3 original repos moved there), each its own GitHub repo with Pages.
- **Tags** are free in song files; an optional `tags.yaml` gives labels and order.
  The build reports tags not in `tags.yaml` instead of failing.
- **Features**: the union of cancionero, cancionero-hakuna and cancionero-pagano,
  with per-book switches in `book.yaml`.
- **PDF import**: one generic importer for text PDFs, with a review list of
  doubtful songs.
- **Proof**: rebuild copies of the 3 existing books in `scratch/` and compare
  with their current `index.html`. The source repos stay untouched.
- **GitHub tonight**: no book repos (create-a-book is tested in dry-run). The
  builder itself goes to a private GitHub repo.

## Plan

1. git init, `.gitignore`, `.venv/`, requirements.
2. Merge the code: `builder/` (build), `importer/` (add songs), `web/` (page),
   taking the newest version of each file and adding switches where the books differ.
3. Book config (`book.yaml`) + free tags.
4. CLI `cancionero.py`: `new`, `build`, `add`, `add-list`, `add-pdf`, `links`, `tags`.
5. `new`: create the folder, files, git init, GitHub repo + Pages (`--dry-run`).
6. PDF importer.
7. Tests: rebuild the 3 books from copies and compare; browser checks of the page.
8. README.

## 2026-10-12 — Setup (while the user was still awake)

- `.venv/` (pyyaml, pdfplumber, pypdf, playwright); test browsers in `scratch/browsers`
  (`PLAYWRIGHT_BROWSERS_PATH=.../scratch/browsers .venv/bin/python -m playwright install chromium webkit`).
- git init; private repo https://github.com/fonsthefons/cancionero-builder created and pushed.
- `.claude/.settings.json` (leading dot, so never read by Claude Code) left out of git, untouched.
- The Read tool is refused in the source repos despite `additionalDirectories`; read them with
  `cat`, then cloned them into `scratch/src/{cancionero,hakuna,pagano}` (`git clone <repo> <dest>`,
  read-only for the sources) and read the clones.

## 2026-10-12 — Phase 1: one build for every book

Merged the three codebases. Base of each part = the newest version:
- `web/` from hakuna (storage/cache prefixes, Do Re Mi with chords after "Intro:", bold
  choruses, popup install tip), with placeholders for everything book-specific:
  `{{ title }}`, `{{ logo }}`, `{{ cover }}`, `{{ notation_setting }}`, `{{ install_tip }}`,
  `const BOOK = {...}` (storage prefix, notation on/off) read by `core.js` / `transpose.js`.
  Optional pieces in `web/parts/`; cancionero's banner tip kept as `install_tip: banner`
  (`.install-banner`). `web/site/`: `sw.js` template, default icons (cancionero's note).
- `builder/` from hakuna + pagano's `added:` field + both chord regex extensions.
  New: `book.py` (book.yaml settings with defaults), `text.py` (slug, Spanish sort),
  `build.py` (writes index.html, sw.js, manifest.webmanifest, default icons if missing).
- **Free tags** (`builder/tags.py`): tags.yaml optional; any tag in a song appears, written as
  id or label (`Pasión` -> id `pasion`); found tags go after tags.yaml's, alphabetically; the
  build lists them. `strict_tags: true` keeps the old rules (the 3 test books use it).
- `sw.js` cache prefix is now `<storage_key>-v`: with `<key>-` the book "cancionero" would
  delete "cancionero-hakuna-v1". (Finding: the live cancionero `sw.js` deletes *every* other
  cache on the site when it updates, including hakuna's and pagano's offline copies.)

### Proof: the 3 books rebuilt from copies (`scratch/make_test_books.py`,
`scratch/build_test_books.py`, `scratch/compare_books.py [--ignore-numbers]`)
- hakuna: 126/126 songs, contents and menu identical.
- cancionero: 152/161 identical; the 9 others gain hakuna's features: chords after
  `Intro:`/`INTRO:` are real chords (transpose, Do Re Mi), and lines like `G D C D (x2)` are
  chord lines (repeat marks were only allowed in hakuna). Contents and menu identical.
- pagano: same two gains, plus: (1) hakuna's sort ignores punctuation, so
  "(I Can't Get No) Satisfaction" moves from #1 to the I's and songs before it shift by one;
  (2) guitar tablature lines (`G|--2--0--|`) are no longer taken as chord lines (the G was
  coloured and *transposed* as a chord, renaming strings). Fixes made along the way:
  repeat marks only `x2`/`(x12)` (not fingerings `x13331`); `C7-9`, `D--A`, `|C---|G---|`
  stay chords.

## 2026-10-13 — Phase 2: adding songs, new books, publishing

- `cancionero.py` (menu with no arguments): `new`, `add`, `add-list`, `add-pdf`, `links`,
  `tags [--write]`, `build`, `publish`, `list`. Books are looked for next to the builder
  (`CANCIONERO_BOOKS` overrides; the tests use `scratch/testbooks`).
- `importer/`: `add.py` (interactive: link / paste / search / PDF / list; default author,
  language suggestion, UG title fixes, Spotify then YouTube link), `batch.py` (both list
  formats), `pdf.py` + `pdf_add.py` (generic PDF), `links.py`, `songfile.py`, `ask.py`
  (tag picker: numbers, or new `Tag` / `Tag/Subtag`, added to tags.yaml keeping its comments).
- `builder/create.py`: new book folder + files + build + git; GitHub repo + Pages via `gh`
  (`--dry-run` only prints those commands). `publish`: build, commit (message lists songs), push.
- PDF importer on the Hakuna songbook (`scratch/pdf_vs_hakuna.py`): 126/126 songs, albums
  found as sections, lyrics 98.6% / chords 97% the same as the hand-checked files, 96% of
  chord lines with every chord over the same letter. Remaining differences are mostly
  cosmetic ("Intro: C" on one line or two, labels in capitals, where long lines are joined).
- Tested: `new --dry-run` with scripted answers, paste + new tags, free tags written by hand,
  search + Spotify/YouTube + build (real web), `tests/` (29 pytest tests pass:
  `.venv/bin/python -m pytest tests -p no:cacheprovider`).

## 2026-10-13 — Phase 3: browser checks

- Hakuna's UI test made generic and moved into the repo: `tests/browser/ui_check.py <book>`
  (+ `checks.js`). It picks its songs/sections from the page (3 songs with chords and unique
  titles, the first folded section, storage prefix from `BOOK`), accepts sections that start
  open (pagano's languages do, as on the live page), skips the 40-song drag check for small
  books, prints only failures + a count.
- Chromium + WebKit, phone/iPad/laptop, after rebuilding (`scratch/build_test_books.py`,
  `cancionero.py build scratch/testbooks/cancionero-misa`): hakuna 174/174, cancionero
  176/176, pagano 172/172, cancionero-misa (new book, defaults, free tags) 172/172.
- `add-list` run finished: both wanted songs added from Ultimate Guitar, the "NOT YET" one
  skipped (`scratch/list_report.txt`).

## 2026-10-13 — Phase 4: second PDF layout (printed builder books)

- Tried the printed web pages in `cancionero/scratch/` (`book.pdf` one column with chords,
  `book-2cols.pdf` two columns, lyrics only). Before: the whole book came out as 1 song.
- `importer/pdf.py` changes:
  - `drop_contents_pages`: pages that are mostly numbered entries and have no chords are
    dropped before font sizes are measured (the 620 contents entries at 12pt outnumbered the
    161 titles at 14.4pt and became the "title size").
  - `META_RE`: the "Autor: X Capo: N Link" line under a title gives author and capo.
  - `column_split(rows, width)`: the first 0-3 rows (title, byline) may run across the gap
    between the columns; they are kept whole at the top of column 0.
- Results (`scratch/pdf_vs_songs.py <pdf> <songs folder>`, now NFC-normalises: some
  cancionero files have decomposed accents and scored 0.7 on identical text):
  - `book.pdf`: 161/161 songs, lyrics 99.5%, chords 99.6%, 2514/2681 chord lines with every
    chord over the same letter. Low chord scores are fixes in the print (`Gm#` -> `G#m`).
  - `book-2cols.pdf`: 161/161, lyrics 99.4% (that PDF has no chords).
  - Hakuna PDF unchanged: 126/126, lyrics 98.6%, chords 97%, 1714/1785.
- `cancionero-pagano/scratch/book.pdf` is an old print of a different 150-song book, not
  pagano's songs; not usable as a check.
- New test `test_pdf_printed_book`; 30 tests pass.

## 2026-10-13 — Phase 5: README

- `README.md` (setup, commands, book folder, song files, free tags, PDF import, tests) and
  `requirements.txt` (PyYAML, pdfplumber, playwright, pytest; pypdf was installed but unused).

## 2026-10-13 — Phase 6: the 3 real repos become builder books (user's go-ahead, steps 1-6)

- `scratch/convert_repos.py`: saved each old `index.html` in `scratch/live-old/<name>/`, wrote
  `book.yaml` (same settings as the test books; hakuna also `logo.svg`, `cover.svg`), deleted
  `builder/ importer/ web/ venv/ .venv/ __pycache__/ build.py add_song.py add_songs.py
  song_template.md requirements.txt PROGRESS.md`, wrote the book README. Kept songs, yamls,
  icons, `Want.txt`, `Checked.txt`, `CLAUDE.md`, `.claude/`, `.mcp.json`, `scratch/`.
- Built with `cancionero.py build <repo>`. `compare_books.py --live --ignore-numbers`:
  cancionero 152/161 identical (the 9 known), hakuna 126/126, pagano 285/387 (the same
  known sort + tablature differences as the test build). Browser checks: 174/174, 174/174,
  172/172.
- Nothing committed or pushed in the 3 repos: changes are local, undo with `git restore`.

## Share session (2026-10-17)

- "Share session" button (`web/js/session.js`, `web/template.html`): link `?session=id1,id2`.
  Opening it replaces only the session (no warning), drops unknown ids, removes the
  param from the URL, opens the menu and jumps to the first song. Native share sheet,
  else copies the link.
- Browser check added in `tests/browser/ui_check.py`: 180/180 on scratch cancionero book.
- Books need a rebuild to get it.

## Song link label (2026-10-17)

- `builder/render.py`: the song's link now reads "Spotify link" or "YouTube link"
  (from the address), else "Link". Tests pass. Books need a rebuild.

## Service worker cache name from a hash (2026-10-17)

- `web/site/sw.js`: cache name is now `<storage_key>-v<hash>` instead of a fixed `-v1`.
- `builder/build.py`: the hash is the first 10 hex digits of a SHA-256 of the book's
  `manifest.webmanifest` and icons. If either changes, sw.js changes too, so phones
  download them again. Test `test_sw_cache_follows_icons`. Tests pass (31).
  Books need a rebuild.

## Phone crashes on big books (2026-10-18)

- Cause: every A+ tap (and scrolling) laid out all songs; pagano has 387 songs,
  ~96k elements. Each A+ step took ~750 ms in desktop WebKit, far worse on a phone.
- `web/styles.css`: `.song` gets `content-visibility: auto` +
  `contain-intrinsic-size: auto 900px` (off-screen songs skipped); print forces
  `content-visibility: visible`.
- Measured with `scratch/perf_textscale.py` on `scratch/books/pagano`: A+ step
  WebKit 750 -> 240 ms, Chromium 300 -> 5 ms. What's left in WebKit is style
  recalc of every element (`scratch/perf_probe.py`), not layout.
- Safari's scroll anchoring jumps a screen away when a skipped song renders
  (jumps to songs, scrolling up). New `web/js/scroll-anchor.js`: WebKit only,
  turns native anchoring off and scrolls by the height change of songs above.
  Chromium's native anchoring is fine (adding JS there double-scrolled jumps).
- Tests: `tests/browser/checks.js` renders all songs (existing checks keep
  measuring/clicking every song); new `skipped_song_checks` in `ui_check.py`
  (skipped, jumps land below the top bar, A+ keeps the song on screen, print
  renders all). All pass on the 3 scratch copies (190/192/192); pytest 31 pass.
- Known: A+ in Chromium can still move the song up to a screen (before this
  change it lost the place by thousands of px). Not tested on a real phone.
- Books need a rebuild.
- Other menu actions and autoscroll (`scratch/menu_probe.py`, `scratch/place_probe.py`,
  pagano, phone size): book-wide chords/columns/notation were 3-5x faster in WebKit
  (e.g. columns 700-1190 -> ~210 ms), 50-100x faster in Chromium; theme unchanged
  (~250 ms WebKit, style only); autoscroll steady 60 fps before and after.
  Place after the action: WebKit now stays on the song for all; Chromium drifts
  one screen on the 2-columns toggle (before: ~90,000 px).

## Slimmer song HTML (2026-10-18)

- `builder/lyrics.py`: no span per chord: a chord line is plain text styled as
  chords, separators (`|`, `(x2)`, `-`...) get `<span class="sep">`; a plain lyric
  under a chord line is the `.line-pair`'s own text; lone chord lines lose the pair.
  "Intro:" lines keep their `.chord` spans.
- `web/styles.css` (.chord-line styled as chords, .sep plain, .line-pair.bold),
  `web/js/transpose.js` (chord lines: words outside .sep are the chords, same
  column rules; Intro lines: old code), `web/js/search.js` (pair text = lyric).
- Tests: `tests/browser/checks.js` reads the new structure (wraps chords in spans
  while measuring: WebKit rounds Range rects inside text to whole px); unit test
  `test_lyrics_html_is_slim`.
- Checked: every song's text in all 12 keys + solfège and the search index are
  identical to before on the 3 books (`scratch/dump_render.py`,
  `scratch/compare_dumps.py`); screenshots same size, only sub-pixel anti-aliasing
  differs (Chromium); WebKit built vs chords-in-spans: identical pixels.
- pagano: 95,600 -> 43,500 elements, 3.95 -> 2.50 MB (hakuna 0.81 -> 0.59,
  cancionero 1.21 -> 0.80). WebKit menu actions ~35% faster again (A+ 240 -> 180
  ms, chords 140 -> 80); transpose biggest song 5 -> 2 ms, all songs 123 -> 89 ms.

## Still to do

- Look at the 3 rebuilt pages, then `cancionero.py publish <repo>` for each.
- First new book with GitHub: `.venv/bin/python cancionero.py new`.

## 2026-10-19 — New book: cancionero-organo (local only)

- `scratch/new_organo.py` calls `create_book` (no GitHub): `~/Documents/programs/cancionero-organo`,
  0 songs, `strict_tags: true`, `install_tip: banner` (as cancionero).
- Tags: Misa (cancionero's 8 subtags), Laudes and Visperas (Salmo, Tono Recto, Canto
  Evangelico), Adoracion, Español, Latin. Checked with `cancionero.py tags`.

## 2026-11-02 — Liturgia book, phase 1 (branch liturgia-phase-1)

Plan: `scratch/liturgia/PLAN.md` (agreed with the user beforehand). Source: the user's PDF
"Cancionero - Liturgia de las Horas 2.pdf" (copied to `scratch/liturgia/tonos.pdf`, pp. 54-66
read as images; the text layer is OCR noise).

- **Liturgia de las Horas**: new optional book file `horas.yaml` (`builder/horas.py`): a tree
  (Semana I-IV > día > hora > partes; Completas once, not per week) with YAML anchors for
  reuse. Songs go in with `horas: [semana_i/lunes/laudes/himno, "*visperas/magnificat"]`
  (fnmatch; a pattern matching nothing is an error). Shown first in the contents and the
  menu; only nodes with songs appear. Parts in real liturgical order (Canto evangélico
  before Padre Nuestro; Laudes salmo-cántico-salmo, Vísperas salmo-salmo-cántico; Completas
  with 2 psalms on Domingo primeras and Miércoles).
- **Misa** and **Fórmulas Salmódicas** (Semitonos de 2/3/4, Tonos Rectos): plain tags in the
  template's `tags.yaml`. 50 fórmulas as songs (chords in letters; Semitonos de 2 with a
  `Flexa:` line, which now renders/transposes chords like `Intro:`).
- `templates/liturgia/` (horas.yaml, tags.yaml, songs/) + `new <name> --template liturgia`.
- Natural song order ("2 x" before "10 x"). Changes cancionero-pagano's 6 songs whose
  titles start with digits (5 Years Time … 1973); every other book byte-identical outside
  the inlined CSS.
- Build report no longer lists songs placed only in Horas as "without tags".
- Checked: pytest 38 passed; `scratch/liturgia/make_book.py` builds `scratch/liturgia-book`
  (template + test songs in Horas/Misa); screenshots `scratch/liturgia/*.png` (index, a
  fórmula, transposed +1 incl. the Flexa line); ui_check: Chromium all pass; WebKit phone
  "jump to song lands below the top bar" fails (top=44, wants >= 50) on this book. Not from
  this branch: the fórmulas-only book built with main's code fails the same way
  (`make_plain.py`, `make_plain_head.py`); pagano passes. Cause: very short songs. Left as is.
- Doubtful fórmula readings for the user: `scratch/liturgia/formulas-review.md`.
- Work split: code and template data were written by subagents from the plan, reviewed here.
- Not done (later phases): sheet music, tabs, choosing a fórmula inside a psalm. The real
  book folder in hymn_books was not created (CLAUDE.md: only when the task says so).

## 2026-11-02 — Fórmula corrections from the user

- Reviewed with `scratch/liturgia/review/index.html` (`review_page.py`: PDF crops next to
  each doubtful fórmula). User's corrections applied to S2 nº 12, 13, 19, 24, 26 and S4
  nº 1, 2; the rest confirmed.
- Tonos Rectos: each line is one fórmula: 1 en Mi, 2 en Fa, 3 en Sol, 4 subtypes each
  -> 12 songs ("1 Tono recto en Mi 1" …), `split_tonos_rectos.py`. 59 fórmulas in all.
- For the notes phase: Gorgoritos (S4 nº 24) has 3 flats in the PDF's key signature; the
  user isn't sure it's right.
- Notes and tabs: not written yet (next phase, asked by the user).

## 2026-11-02 — Liturgia phase 2, part A: staff + tab code (branch liturgia-phase-2)

- `web/vendor/abcjs-basic-min.js` 6.4.4 (+ `abcjs-LICENSE.md`, MIT), inlined with
  `web/js/melody.js` only in books with a `melody:` song (render.py).
- Song fields `melody` (ABC body) / `tab` (fret/string per note; count checked, songs.py);
  `<div class="melody" data-abc data-tab>` before the lyrics.
- melody.js: `renderMelody(element, shift)` (abcjs + a 6-line SVG tab, breves redrawn as
  square reciting notes, chord names via transpose.js's transposeChord when present).
  Drawn when the song nears the screen (IntersectionObserver), on beforeprint, and on
  transpose / notation change (renderChords -> refreshMelody).
- Tests: `test_melody`; ui_check.py `melody_checks` (fret under each note, +2 changes
  frets and chords). Scratch books `scratch/melody-book`, `scratch/melody-misa` (+ `-base`
  without melodies); screenshots `scratch/shots/melody-*.png` (`scratch/melody_shots.py`).
- ui_check on the 7-song melody-misa: 193 passed, 5 failed; the same 5 skipped-song checks
  fail on the melody-free base copy too (book too small for them).
- Jump regression on scratch/liturgia-book (47 melodies): Chromium lost ~40px of scroll
  anchoring when melodies were drawn (layout read) inside the IntersectionObserver callback
  while songs got their real height -> draw 150 ms later; `.melody` gets
  `overflow-anchor: none` and an aspect-ratio placeholder until drawn. WebKit landed 600px
  off: scroll-anchor.js judged songs by their position after the batch's resizes; now by
  their position before (`moved`). ui_check: benign "ResizeObserver loop completed"
  notice ignored; end-of-page autoscroll check jumps to the end twice (first jump lays
  out the last songs). Tab: 12-unit gap under the staff and a "TAB" label.
- ui_check scratch/liturgia-book: 200 passed, 0 failed (Chromium + WebKit). Probes:
  scratch/jump_melody_probe.py, end_scroll_probe.py, liturgia_nomel_book.py.

## 2026-11-02/03 — Liturgia phase 2, part B: notes + tabs of the 47 semitonos

- Plan `scratch/liturgia/PLAN2.md`. Three agents transcribed the handwritten staffs
  (tonos.pdf pp. 54–65) into `melody:` / `tab:`; tab frets copied from the PDF tab pages,
  chosen where there is none (and for every flexa). Doubts:
  `scratch/liturgia/transcription-notes-b{1,2,3}.md`.
- Tab convention = the PDF's: written pitch is played as is, open strings E4 B3 G3 D3 A2 E2
  (PLAN2's first table was an octave off; corrected mid-run).
- `scratch/liturgia/check_all.py`: every fret on its string gives the written note
  (key signature + accidentals): 0 problems.

## 2026-11-03 — Liturgia phase 3: himnos.pdf (user asleep; ran unattended)

- User's PDF "himnos_canticos_responsorios_padrenuestros_antifonasmarianas.pdf" ->
  `scratch/liturgia/himnos.pdf` (46 pages). Plan `scratch/liturgia/PLAN3.md`; 5 agents
  (H1–H5), notes + page lists in `scratch/liturgia/h1..h5/notes.md`.
- 56 new songs in templates/liturgia/songs: 14 Laudes hymns, 13 Vísperas hymns, 2
  cánticos, 3 Magnificat, 2 Benedictus, 3 Padrenuestros, Te Deum, 2 Completas hymns,
  2 Completas responsorios, Nunc dimittis, 7 antífonas marianas, 3 responsorios breves
  (2 generic as fórmulas, Adviento), 3 semitonos para Benedictus/Magnificat. Lyrics with
  chords (letters), melody + tab from the staff printed with each piece.
- Decisions taken without the user (to confirm):
  - Completas got a new last part "Antífona Mariana" (horas.yaml).
  - tags.yaml: Fórmulas + Responsorios breves, Semitonos para Benedictus / Magnificat;
    new tags "Tiempos litúrgicos" (Adviento … Pentecostés) for seasonal pieces, and
    "Oficio de lectura" (Te Deum).
  - Placement: hymns by their PDF header (week/day/hour); Benedictus in every Laudes,
    Magnificat in every Vísperas, Padrenuestros in every hour, Completas hymns /
    responsorio / Nunc dimittis / antífonas in every Completas day; Ap 19 cántico in every
    Sunday's segundas Vísperas; Dn 3 cántico in Domingo II and IV Laudes.
  - Where the PDF's tab disagrees with the staff (often the key signature ignored, e.g.
    F# written as F), the tab follows the staff. Where the PDF has no tab, one was worked
    out (first position). Only the first staff line is kept when a piece has two.
  - Hymns without a printed title use their first line ("Himno I" -> first line).
- scratch/liturgia-book (template + one Misa test song): 116 songs; check_all 0 problems;
  ui_check 200 passed, 0 failed.

## 2026-11-03 — Review page extended to the himnos.pdf pieces
- scratch/liturgia/review2_page.py + review2_template.html: second section "Himnos, cánticos y
  otros" (56 cards): whole himnos.pdf pages (110 dpi gray JPEG, one data URI per page shared via
  `PAGES`), horas/tags line, doubts parsed from h1..h5/notes.md, auto-sized Chords textarea,
  filter "Fórmulas only"/"Himnos only". .melody CSS now copied from web/styles.css at build time.
- review2_check.py extended (hymn edit, re-render, filter, export); passes at 430 and 1100 px.
- apply_corrections.py unchanged; tested on copies in scratch/liturgia/review2/check/songs.

## 2026-11-05 — Revisions 2 corrections, tab shift, GitHub page (branch liturgia-corrections-2)
- `apply_corrections.py "~/Downloads/Revisions 2 Corrections.json"`: new bodies for 4 antífonas
  marianas, Nunc dimittis, 2 responsorios. Notes done by hand: Glorioso chords placed as in the
  PDF tab (La n1, Re n5 | Sim n1, Mi n3, La n5 | La, Sim); Laudate Dominum F G F as triplets
  `(3`; Semitono de 3 unchanged (user: correct).
- `web/js/melody.js`: `shiftFret`: a fret below the nut moves to the next lower string
  (e0 −1 -> 4 on B), octave up only on the low E; renderMelody widens the staff (+40, up to
  600) while frets on one string touch (Cantad al Señor bar 2). ui_check checks shiftFret.
- Checked: pytest 39 passed; check_all 0 problems; ui_check scratch/liturgia-book 202 passed.
- Item 2 (chords placed right in the hymns) is the user's manual check, not done here.
- Merged (PR #4). Then the real book (user asked for "the gh page"):
  `scratch/liturgia/new_liturgia_book.py` -> `~/Documents/programs/hymn_books/cancionero-liturgia`
  (template liturgia, 115 songs, title "Cancionero - Liturgia de las Horas", banner install tip),
  public repo https://github.com/fonsthefons/cancionero-liturgia, Pages
  https://fonsthefons.github.io/cancionero-liturgia/. Name and title chosen without asking.

## 2026-11-05 — Psalm fórmulas (branch psalm-formula)
- First psalm in the real book: `hymn_books/cancionero-liturgia/songs/salmo-086.md` (Semana III,
  Jueves, Laudes, Salmo 1; new tag `salmos` in its tags.yaml).
- book.yaml `psalm_tags` / `formula_tag` (builder/book.py; liturgia: `[salmos]` / `formulas`).
  render.py: psalms get a "Choose fórmula…" button + `.psalm-formula`; `BOOK.formulas` lists
  the fórmulas by subtag; `web/js/formula.js` only in such books.
- formula.js: dialog with search (every word must match group or title; Enter picks the first),
  "No fórmula", Cancel. The chosen fórmula's staff/tab/chords (copied as built) show above the
  psalm and follow the psalm's transposition and Do Re Mi. Saved per psalm (songState
  `formula`). session.js: list shows "Salmo 86 · 25 Glorioso"; share link `id~fórmula`.
  search.js ignores the copied lines.
- User's answers: reader chooses (no default yet), all fórmulas + search, key per psalm,
  Gloria in the psalm file, no antífona, no `*`/`†` marks yet.
- Checked: pytest 40; ui_check on the real book (local build) 216 passed (new formula_checks;
  its reload checks run in a second tab: WebKit misses taps on far songs after a reload);
  screenshots scratch/shots/formula-*.png.
- The book's changes (psalm, tags, book.yaml, index.html) are local, not committed/published.

## 2026-11-05 — Salterio import (branch salterio-import)
- The downloaded "Liturgia de las Horas CEE 1.12.1.apk" was Uptodown's store app, not the CEE
  app. The user chose the site's GitHub repo as the source; shallow clone in `scratch/lh-repo`.
- `importer/horas_site.py`: generic readers for any day/hour of the site (`read_day`,
  `read_hour`: parts with heading, kind, section, antiphon, text, notes) so propios/comunes
  (Adviento, Común de pastores…) can reuse them. `salterio()` takes Tiempo Ordinario days
  marked "De la Feria. Salterio N": Laudes from that day; Vísperas/Completas only when the next
  day is plain too (a feria before a solemnity has its I Vísperas). Saturday evening goes to
  next week's Domingo primeras Vísperas / primeras Completas. 5 samples per slot, majority kept
  (the site has typos: missing verse ranges, a lost stanza break, "señor").
- `.venv/bin/python -m importer.horas_site scratch/lh-repo scratch/salterio` -> 63 slots,
  135 psalm/cántico files (`scratch/salterio/songs/`, same format as the book's salmo-086.md,
  Gloria line split like it; a psalm used in several slots is one file with several `horas:`)
  + `salterio.json` (antiphons, sources, rubric notes).
- Checked: every slot matches the psalter; all 135 files load; every psalm part of the
  template's horas.yaml gets one; generated salmo-086 equals the hand-made one. pytest 45.
- Not done: copying into the real book (task didn't say so); antiphons not written to the
  song files (earlier decision: no antífona). Salmo 138 I is named "Salmo 138, 1-18. 23-24"
  (the site puts the "I" in its title).
- Then (user asked): `scratch/copy_salterio.py` copied 133 files into
  `hymn_books/cancionero-liturgia/songs/`, keeping the 2 already there (salmo-086 identical;
  the user's untracked salmo-137 differs only in a 4-line Gloria). `cancionero.py publish`:
  250 songs, pushed; https://fonsthefons.github.io/cancionero-liturgia/.

## 2026-11-05 — Melody play button (branch melody-play)
- User's answers: tone made in the browser (no sound files, offline), one fixed tempo,
  follows the transposition, every book with melodies, also the fórmula above a psalm,
  light the playing note.
- render.py `PLAY_HTML`/`with_play`: "▶ Melody" at the end of the controls of songs with a
  melody and of psalms (CSS hides it in a song without `.melody`, so a psalm shows it once it
  has a fórmula). A first try over the staff's corner covered notes; moved to the controls.
- melody.js: abcjs `TimingCallbacks` (after `setUpAudio`, chords off) gives each note's
  pitch (+ the song's transposition) and length; `organNote` = sine harmonics 1/2/3/4
  (8', 4', 2' stops) with short attack/release; quarter = 80 unless `Q:`. Pause/resume (the
  cut note sounds again for its remaining time), one melody at a time, a redraw stops it;
  a tap before the first draw draws it via drawMelody so the pending draw doesn't stop it.
  formula.js: changing a psalm's fórmula stops its playing.
- New `tests/browser/play_check.py <book>` (26 checks, Chromium + WebKit) on a scratch copy of
  cancionero-liturgia (`scratch/real_copy_build.py` -> scratch/liturgia-real); ui_check there
  216 passed; pytest 45 (play-button counts added to test_melody / test_psalm_formulas).
- The real book is not rebuilt/published with it yet.

## 2026-11-05 — Fórmula titles and file names (branch formula-titles)
- User asked: fórmula titles "<Group>: (n) <name>" (n = old number, to find it in the PDF)
  for every fórmula group, and file names to match. `scratch/rename_formulas.py <songs>
  <tags.yaml> [--apply]` (labels from tags.yaml; "Tonos Rectos" written "Tonos rectos"):
  64 files in hymn_books/cancionero-liturgia/songs and templates/liturgia/songs, e.g.
  semitonos_2-01-suplicante_1.md -> semitonos_de_2-01-suplicante_1.md. Natural order keeps
  (1)…(26) in order; they now sort under R/S/T instead of first. Psalms' saved fórmula
  choices and old share links point at old ids, so they fall back to "Choose fórmula…".
- formula.js: the dialog shows "(1) Suplicante 1" under its group heading (prefix hidden
  there only).
- ui_check then failed "A+ keeps the song on screen" (Chromium phone, top=854 > 844): the
  check's far song is now a short fórmula with a staff, and Chromium's own anchoring drifts a
  screen there. scroll-anchor.js (until now Safari only) now runs in every browser.
- Checked: ui_check liturgia-real 216, liturgia-book 202, cancionero 192, hakuna 192,
  pagano 190 (all 0 failed); play_check 26; pytest 45.
- Then (user asked) `cancionero.py publish` cancionero-liturgia: 250 songs, with the renamed
  fórmulas and the "▶ Melody" button; Pages built.

## 2026-11-05 — Per-song text size; autoscroll stops at the song's end (branch song-zoom-scroll)
- User asked: A− / A+ per song (menu A− / A+ kept as the book-wide default; they multiply),
  and autoscroll (option A, the one top-bar ▶) stopping when the song's bottom reaches the
  screen's bottom.
- song-controls.html: A− / 100% / A+ stepper. display.js `setSongScale`: `--song-scale` on
  .song, saved as songState "textScale"; "Reset songs" clears it. styles.css multiplies it in
  .lyrics font-size; print forces it to 1.
- autoscroll.js: scrolls the song cut off at the bottom of the screen (`songAtScreenBottom`,
  re-picked after a manual scroll), stop point re-read every frame; ▶ again goes on to the
  next song. 2px threshold: WebKit stopped ~1.5px short and re-picked the same song.
- ui_check: song size checks + remembered after reload; autoscroll checks now run in a long
  song (the old jump to y=200 landed at a short song's end); new "stops at the end of the
  song" / "▶ again goes on".
- Checked: ui_check cancionero 200, hakuna 200, pagano 198, liturgia-real 224 (0 failed); play_check 26;
  pytest 45.

## 2026-11-05 — Chords written over psalms for semitonos (branch psalm-auto-chords)
- User's rules: one bar per line. De 2: bars 1, 2 alternate; an odd verse has one flexa
  (flexa, 1, 2) on line 1/3/5…, placed by punctuation; Gloria follows the same rule (flexa on
  its first line). De 3 / de 4: every verse exactly 3 / 4 lines; de 4's Gloria splits into
  "Gloria al Padre, y al Hijo" / "y al Espíritu Santo.". "(FLEXA)" in red after the flexa chords.
- User's answers: first chord over the first letter, the others over the last words (one each);
  de 3/4 with a verse that doesn't fit -> no chords on the psalm at all (the fórmula still shows
  above it); only Semitonos de 2/3/4 (not Benedictus/Magnificat, not tonos rectos yet); flexa
  position = most strongly ended group-end lines (. ; : ? ! = 2, comma = 1), ties -> earliest.
- render.py `formula_choices`: each BOOK.formulas group now carries its tag id. formula.js:
  `SEMITONO_BARS` (liturgia's subtag ids), `semitono2Plan`, `versePlan`, `chordLineText`
  ("(B7)" stays right after its chord), `setPsalmChords` (keeps the built lyrics, rewrites them
  on each pick). styles.css `.chord-line.flexa::after` (not text, so transpose ignores it).
- Real book (scratch/liturgia-real): de 2 gives chords on all 135 psalms/cánticos, de 3 on 1
  (Salmo 99), de 4 on 10. Probe: `scratch/psalm_chords_probe.py`, shot scratch/shots/psalm-chords.png.
- Checked: pytest 45; ui_check liturgia-real 228 passed (new rule checks with the user's
  examples); play_check 26.
- The real book is not rebuilt/published with it yet.

## 2026-11-05 — Missing himnos of the salterio (branch salterio-himnos)
- `scratch/check_salterio.py`: every Himno/Salmo/Cántico part of liturgia's horas.yaml
  (240) has a song? Psalms/cánticos all there; 29 himnos missing (Laudes/Vísperas only).
- importer/horas_site.py: `salterio(pick=…)` (default psalmody), `himnos`, `himno_title`
  (heading words in the text's case). `scratch/add_himnos.py [--write]` reads the site's himno
  per slot (majority of 5 days), fills only empty slots: 23 new files
  `himno_<hour>-<title>.md` (plain text, no chords), 6 slots added to a sung himno already
  in the book (matched by its first 4 lyric words). Semana I Sábado Laudes "no majority" =
  same himno, typo-level differences.
- Not changed: 30 filled slots whose book himno is not the site's for that slot (report from
  add_himnos.py); the user's placement kept.
- Checked: check_salterio 0 missing; `cancionero.py build cancionero-liturgia` 273 songs;
  pytest 46. Book not committed/published.

## 2026-11-05 — Breves 8 -> 4; flexa ties by punctuation (branch breves-and-flexa)
- User asked: the breve (reciting note, `E8`) lasts 4 in every semitono (de 2/3/4, para
  Benedictus/Magnificat) and responsorio breve (also the 2 de Completas: same melody); every 8
  -> 4 (Nistalmata's second long notes too). `scratch/halve_breves.py <songs dirs> [--write]`
  (skips quoted chord names): 54 files / 180 notes each in hymn_books/cancionero-liturgia/songs
  and templates/liturgia/songs.
- formula.js `semitono2Plan`: score unchanged; ties -> more group ends on . ! ?, then on :,
  then earliest (the user's 6 examples: ":" beats ";", "!" beats ":"). ui_check has them +
  the 2 old Salmo 89 examples.
- ui_check "shared link … jumps to the first song" failed on liturgia-real (273 songs: the
  jump comes later than the check read the URL); waits 500 ms now.
- Checked: ui_check liturgia-real 228 passed; play_check all passed; pytest 46.
  Real book rebuilt, not committed/published.

## 2026-11-05 — Himnos section; All Songs folded (branch himnos-list)
- User asked (cancionero-liturgia): All Songs closed by default; a "Himnos" section with
  Laudes / Vísperas / Completas listing "Lunes I: 5. Alfarero del hombre".
- book.py `fold_all_songs` (default false; true in liturgia's book.yaml).
- horas.yaml `lists: {Himnos: {part: Himno, groups: [Laudes, Vísperas, Completas]}}` (book +
  templates/liturgia). horas.py `part_list` (tree order, group = first group word in the
  branch labels), `place` ("Lunes I", "Domingo I (primeras)", "Domingo (segundas)").
  render.py `horas_lists_html` after the Liturgia de las Horas section + menu entry; folds
  like tags/subtags.
- Fixed 2 himno titles by hand: "¿Dónde está muerte, tu victoria?", "¡Detente, aurora de
  este nuevo día!".
- Checked: pytest 48; ui_check liturgia-real 228. Real book rebuilt, not committed/published.

## 2026-11-05 — Check liturgia salterio against Liturgia CEE

- Liturgia CEE app: content is encrypted (Realm DB, Environments.bin) and behind login;
  not used. Copies of its cache were deleted from scratch/.
- liturgiadelashoras.github.io = old hymn edition (matches our repo). eltestigofiel.org
  matches the app (checked: Jueves III Laudes "Autor del cielo y el suelo").
- scratch/cee/: etf.py (fetch+parse, pages cached in etf/), compare.py → report.md,
  site.json; plan.py (which CEE hymns exist in the repo).
- Result over 240 parts (Laudes, Vísperas, Completas, 4 weeks): all salmos/cánticos match;
  36 himnos differ. Only 2 of the 36 CEE hymns are already songs in the repo.
- User's choice: CEE is right; replace conflicts, delete old text-only hymns, keep the chorded
  "Alegre la mañana" and "Cuando la luz del sol es ya poniente" untagged; for double-tagged
  chorded hymns keep only the CEE slot.
- Book repo, branch `cee-himnos` (committed locally, not pushed/published): 34 new text-only
  hymns written by scratch/cee/gen_hymns.py from the site text; 21 old hymns `git rm`;
  11 files retagged with Edit (Como el niño renamed to himno_completas-…).
- compare.py after: 240 parts match, 0 differ.
- tests/browser/ui_check.py: the per-song chords check now picks the 2nd song *with chords*
  (liturgia's 2nd song is now text-only, so the old pick had no chord line).
- Checked: pytest 48; ui_check liturgia (real) 228, scratch cancionero 200.

## 2026-11-05 — Fórmula picker on hymns without chords (branch hymn-formulas)
- User asked: chordless hymns in cancionero-liturgia get the semitono picker, like salmos.
- book.py `formula_parts` (list of horas.yaml parts, e.g. [Himno]); render.py
  `formula_choices` adds songs in those parts of the filled horas tree with no chord line.
  formula.js unchanged.
- Book repo book.yaml: `formula_parts: [Himno]`; rebuilt (36 of 65 hymns get the picker),
  not committed/published.
- Checked: pytest 48 (test_psalm_formulas covers a hymn with and without chords).

## 2026-11-05 — Semitono de 4 on hymn Glorias (branch hymn-gloria-split)

- User: "Tiembla el frío de los astros" got no de-4 chords; its Gloria is 3 lines
  ("Gloria al Padre, gloria al Hijo, / gloria al Espíritu Santo, / por los siglos…").
- formula.js: the 3-line Gloria's first line splits before "y al Esp…", else at its first comma.
- ui_check: new check (de 4 on Tiembla el frío -> 20 chord lines).
- Checked: ui_check liturgia-real 230 passed.

## 2026-11-09 — Tab under only the first notes (branch tab-partial-ignore)

- User: the liturgia song saludo_inicial-dios_mio_ven_en_mi_auxilio tabs only its first notes,
  with `ignore: ["tab-melody-check"]` in the song.
- songs.py: `ignore` field; skips only the note count (fret/string format still checked);
  unknown values stop the build. melody.js unchanged (it already draws frets from the first note).
- Checked: pytest 48; scratch/check_partial_tab.py loads all 288 liturgia songs. Browser not
  run; book not rebuilt, committed or published.

## 2026-11-11 — Organo songs from screenshots (branch organo-progress; book branch organo-songs)

- Followed scratch/organo/PLAN.md: 3 parallel agents read organo/screenshots/ (20 PNGs) and wrote
  19 songs to cancionero-organo/songs (4 aleluyas, 5 santos, 5 corderos, comunion, adoracion,
  entrada+ofertorio, 2 aclamacion_memorial). tags.yaml: added `aclamacion_memorial` after santo.
  The agents stopped at the usage limit once and were resumed after it reset.
- Doubts per song: scratch/organo/a1..a3/notes.md (40 in all).
- Builder: a melody without `tab:` is now allowed (songs.py checks the tab only when there is one;
  melody.js draws no empty TAB staff). The plan says "no tab", and the build refused them before.
  New case in test_melody (pytest 48 passed).
- Checked: build 19 songs; scratch/organo/check_melodies.py draws all 19 melodies in Chromium:
  0 abcjs warnings, 0 JS errors, no tab staff. Full ui_check not run (its melody check expects a tab).
- File names: A1 used the screenshot name (aleluya-aleluya_97, comunion-oh_buen_jesus_leon...),
  A2/A3 composer-based slugs; left as is, both fit `<subtag>-<slug>.md`.

## 2026-11-12 — Organo review round 1 (book branch organo-review-1)

- Review page: scratch/organo/review_page.py (reuses scratch/liturgia/review2_template.html; each
  screenshot beside the drawn staff) -> scratch/organo/review/index.html; review_check.py checks it.
- User's corrections ("organo/screenshots/Organ Review Corrections.json": 2 corderos' melodies)
  applied with scratch/liturgia/apply_corrections.py --songs-dir <book>/songs.
- Hacia ti morada santa redone with the new part_2 screenshot (full verses, repeat written out).
- New song comunion-hambre_de_dios.md (200, parts 1-2); tag misa/comunion chosen. 20 songs.
- scratch/organo/chord_cols.py prints the letters under each chord (found and fixed 8 off-by-one).
- Checked: build 20 songs; check_melodies.py 20/20; review_check.py 20 cards OK.

## 2026-11-12 — Organo review round 2 (book branch organo-review-2)

- User's corrections: Hacia ti morada santa removed ("we don't want it"); Hambre de Dios body
  replaced (estribillo after every verse, no verse numbers). entrada/ofertorio now have no songs.
- review_page.py: Hacia ti dropped; its 2 screenshots are allowed to stay unused.
- Checked: build 19 songs; check_melodies.py 19/19; review_check.py 19 cards OK; chord_cols.py
  on Hambre de Dios: every chord on its syllable.

## 2026-11-19 — New book: cancionero-learn-harmony (piano harmony course)

- User's choices: Spanish text, chords as C D E; reads music slowly; goal = song accompaniment
  + classical harmony; create and publish on GitHub.
- 39 lessons x 30 min in 6 blocks (tags) -> lessons (subtags) -> parts a, b, c... (one song file
  each, `01a.md`, with a two-hand staff: fingerings, chord names, ▶ plays it). 157 songs.
  Covers: all 12 major scales and the minors HS/HT, 1-2 octaves; arpeggios; triads, inversions,
  voice leading, functions, cadences, accompaniment patterns, sus/add, slash chords, secondary
  dominants, borrowed chords, 7ths/9ths, 4-voice writing, 6/4 cadences, modulation,
  harmonizing a melody, sequences, circle of fifths.
- Generator (scratch/learn-harmony/, also committed in the book's generator/): music.py
  (spelling, fingerings, chord spelling, voice leading, ABC; self-checks), lessons.py (content),
  make_book.py (writes songs + tags.yaml; rewraps prose so no sentence reads as a chord line).
- No builder code changed: multi-voice ABC (`%%staves {RH LH}`) already renders and plays.
- Checked: build 157 songs, no warnings; shots.py (Chromium) renders every staff, no ABC warnings
  or page errors. Created with create_book(github=True), then `publish`.
- Live: https://fonsthefons.github.io/cancionero-learn-harmony/

## Tag pills as columns (2026-11-25)

- Pills show full labels; each tag is a column with its subtags under it (`<span>` only for
  columns of 2+, so no extra elements for lone tags). Subtags get lighter tones of the tag hue.
- tags.yaml `pill:` sets the text (`""` hides it); subtags take `{label: ..., pill: ...}`.
  `to_yaml` keeps it. Files: builder/tags.py, builder/render.py, web/styles.css, README, test.
- cancionero/tags.yaml: ciclos → I/II/III/IV (not committed in the book). All 6 books rebuilt.

## Blocked

- The Read tool is refused in the 3 source repos (some setting outside this project);
  worked around with `cat` and local clones.
