# Cancionero builder

One builder for every song book (cancionero, cancionero-hakuna, cancionero-pagano and new
ones). Each book is its own folder and GitHub repo with Pages; it holds only songs and
settings. All the code — the build, adding songs, the web page — lives here.

## Setup

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
