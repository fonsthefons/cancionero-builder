# Cancionero builder

One builder for every song book (cancionero, cancionero-hakuna, cancionero-pagano and new
ones). Each book is its own folder and GitHub repo with Pages; it holds only songs and
settings. All the code — the build, adding songs, the web page — lives here.

## Main commands, step by step

`./help.sh` lists them with examples. If something breaks, see
[to_check_in_case_of_failure.md](to_check_in_case_of_failure.md).

**`add <book>`** (the usual day-to-day):
1. You give a link, a search, pasted text, a PDF or a list.
2. The importer reads the song from its site (with WebKit if the site blocks scripts) and cleans the title,
   author and chords.
3. It looks for a Spotify link (else YouTube) and asks about tags.
4. It writes `songs/<title>_<author>.md` in the book.

**`publish <book>`**:
1. Build: checks every song and the settings (it stops on the first invalid file), then writes `index.html`,
   `sw.js`, the manifest and the icons.
2. Commit in the book's repo, with a message that lists the new songs.
3. Push: GitHub Pages updates the website within a minute or two.

**`new <name>`**: creates the folder, `book.yaml` and `tags.yaml` (or copies a `--template`), does a first
build, runs `git init`, creates the GitHub repo with `gh`, turns on Pages and pushes.

## Setup

`./install.sh` does all of this: `.venv`, the packages, WebKit, and it clones the book repos into
`../hymn_books/`. Or by hand:

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt

Some song sites need a browser to read; the builder offers to install one the first time.
`gh` (GitHub CLI, logged in) is needed to create and publish books on GitHub.

## Commands

Run `.venv/bin/python cancionero.py` with no arguments for a menu, or:

| Command | What it does |
|---|---|
| `help [new\|edit]` | step by step: create a book, or add songs to / change one |
| `new [name]` | create a book: folder, `book.yaml`, `tags.yaml`, first build, git, GitHub repo + Pages (`--dry-run` only prints the GitHub steps; `--template liturgia` copies `templates/liturgia/`: its `tags.yaml`, `horas.yaml` and songs) |
| `add <book>` | add songs, asking as it goes: a link, a search, pasted text, a PDF or a list |
| `edit <book>` | a local page (127.0.0.1) to add or edit one song at a time: chords you click to place and drag, melody staff with draggable notes and Play, guitar tab, tags, the same sources as `add`. Save writes `songs/<name>.md` and rebuilds; Publish commits and pushes. Also option 6 of the `add` menu. Ctrl+C stops it |
| `add-list <book> <list.txt>` | add a list of songs without questions (`--section Want`, `--report file`) |
| `add-pdf <book> <songbook.pdf>` | import a PDF songbook (`--all`, `--author A`, `--section-tags`, `--links`) |
| `links <book>` | find Spotify/YouTube links for songs without one (`--ask`) |
| `tags <book>` | the book's tags and how many songs each has (`--write`: all into `tags.yaml`) |
| `build <book>` | rebuild `index.html` after editing songs by hand |
| `publish <book>` | rebuild, commit (message lists the new songs) and push: the website updates |
| `list` | the books next to the builder |

`<book>` is a folder name next to the builder (or in `$CANCIONERO_BOOKS`) or a path.

## A book's folder

    book.yaml             settings; only `title` is required
    songs/*.md            one file per song
    tags.yaml             optional: labels and order of tags
    horas.yaml            optional: Liturgia de las Horas tree, shown first in the contents
    author_aliases.yaml   optional: author names as sites write them -> as the book does
    title_fixes.yaml      optional: titles as Ultimate Guitar writes them -> as the book does
    index.html, sw.js, manifest.webmanifest, icon-*.png   written by the build

Every `book.yaml` setting, with its default, is explained in `builder/book.py` (`DEFAULTS`):
title, storage key, colours, default author, folded contents, Do Re Mi setting, install tip
(popup / banner / off), logo and cover, song sites, language tags, `added:` dates, strict tags.

## Song files

    ---
    title: Sopla Señor
    autor: popular
    capo: "2"
    link: https://open.spotify.com/track/...
    song_tags:
      misa:
        - entrada
        - ofertorio
      navidad: []
    ---

    Intro:
    G D
    G              C
    Sopla, Señor...

Chords go on their own line above the lyrics, lined up with the letters. Lines between
`**` lines are shown bold (choruses). Chords after a label (`Intro:`, `Solo:`, `Final:`,
`Puente:`, `Flexa:`...) are chords too, and transpose.

A song can show a staff and a guitar tab above its lyrics (drawn with abcjs, which is only
added to books that use it); both follow the song's transposition:

    melody: |
      K:D
      "D"F8 "A"G A | "Em"F2 "D"E D || "D"F8 "Em"E
    tab: 2/1 3/1 5/1 | 2/1 0/1 3/2 || 2/1 0/1

`melody` is [ABC notation](https://abcnotation.com/wiki/abc:standard:v2.1) after the header
(`X:1`, `M:none`, `L:1/4` are added): `K:` key, notes `C`…`B` from middle C, `c`…`b` an
octave up, `B,` an octave down, lengths `C2` half, `C/` eighth, `C8` a breve (drawn as a
square reciting note), `^F` `_B` `=F` accidentals, `"Em"` the chord over the next note,
`|` and `||` bars. `tab` is one `fret/string` per note (string 1 = high e … 6 = low E;
`|` tokens are ignored); the build stops when the counts differ. For a tab under only the
first notes, add `ignore: ["tab-melody-check"]`. Frets move with the
transposition on the same string (12 frets up when they would go below 0).
A "▶ Melody" button in the song's controls plays the melody (not the chords) with an
organ-like tone made in the browser (works offline), at quarter = 80 unless the melody sets
`Q:`, in the key on screen, lighting each note; a psalm's button plays its chosen fórmula.

The build warns about lines over 50 columns (the whole song gets small on phones; the editor
marks them yellow) and chords written far past the end of their lyric; `cancionero.py`
offers to move those chords next to the lyric (y/n). A song turns either warning off with
`ignore: ["long-lines-check"]` or `ignore: ["far-chords-check"]`.

Songs are numbered in title order; numbers in titles count as numbers ("2 ..." before "10 ...").

**Tags are free**: any tag written in a song appears in the book, as an id (`pasion`) or a
label (`Pasión`). `tags.yaml` only sets labels and order; the build lists tags it doesn't
know. With `strict_tags: true` every tag must be in `tags.yaml`.

## Liturgia de las Horas (`horas.yaml`)

A book with a `horas.yaml` shows that tree first in its contents, before the tags. A
mapping is a branch, a list is an hour and its items are the hour's parts; YAML anchors
reuse lists (`parts:` only holds them). Nodes and parts with no song are hidden.

    label: Liturgia de las Horas
    parts:
      laudes: &laudes [Apertura, Himno, Salmo 1, Cántico, Salmo 2, Responsorio, Benedictus, Padre Nuestro]
    tree:
      Semana I:
        Domingo:
          Laudes: *laudes

A song is placed with `horas:`, a list of slot paths (ids of the labels joined with `/`):

    horas: [semana_i/domingo/laudes/himno, "*visperas/magnificat"]

`*` matches anything, `/` too (quote patterns that start with `*`). Labels work as well
(`Semana I/Domingo/Laudes/Himno`). A pattern that matches no part stops the build, and so
does `horas:` in a book without `horas.yaml`. `new --template liturgia` starts such a book.

## PDF songbooks

`add-pdf` reads text PDFs (not scans): it finds titles by font size, sections (albums,
parts) from bigger headings, one or two columns, chords over their letters, bold choruses,
and skips contents pages. It lists doubtful songs to check. Tried on the Hakuna songbook
(126/126 songs, lyrics 98.6%, chords 97% the same as the hand-checked files) and on printed
builder books (161/161, lyrics 99.5%, chords 99.6%).

## Tests

    .venv/bin/python -m pytest tests -p no:cacheprovider

Browser check of a built page (Chromium and WebKit; phone, iPad and laptop sizes; chord
alignment, transposition, search, menu, sing session, saved settings):

    PLAYWRIGHT_BROWSERS_PATH=scratch/browsers .venv/bin/python -m playwright install chromium webkit
    .venv/bin/python tests/browser/ui_check.py <book folder>

## Code

    cancionero.py   the command line
    builder/        book settings, songs, tags, the build, creating and publishing books
    importer/       adding songs: sites, search, cleaning, chords, PDF, links
    web/            the page: template, styles, scripts; web/site/ sw.js and default icons
