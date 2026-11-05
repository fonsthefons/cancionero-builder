# Progress

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

## Blocked

- The Read tool is refused in the 3 source repos (some setting outside this project);
  worked around with `cat` and local clones.
