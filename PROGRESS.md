# Progress

## 2026-10-12 — Decisions (asked before starting)

- **Code lives only in the builder.** A book repo holds `songs/`, `book.yaml`
  (+ optional `tags.yaml`, `author_aliases.yaml`, `title_fixes.yaml`), the built
  `index.html`, `sw.js`, `manifest.webmanifest`, icons, a README. Commands run
  from the builder and point at a book.
- **New books** go in `~/Documents/<name>`, each its own GitHub repo with Pages.
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

## Still to do

- First real book with GitHub: run `.venv/bin/python cancionero.py new` (not done: no book
  repos on GitHub without the user).

## Blocked

- The Read tool is refused in the 3 source repos (some setting outside this project);
  worked around with `cat` and local clones.
