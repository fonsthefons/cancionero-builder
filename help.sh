#!/usr/bin/env bash
# Print how to run this repo's main features.
cat <<'EOF'
cancionero-builder: builds song-book websites (one folder + GitHub Pages per book) from songs in markdown.

  .venv/bin/python cancionero.py new mybook
      create a book: folder, book.yaml, tags.yaml, first build, git, GitHub repo + Pages

  .venv/bin/python cancionero.py add mybook
      add songs interactively: a link, a search, pasted text, a PDF or a list

  .venv/bin/python cancionero.py add-list mybook list.txt
      add a list of songs without questions

  .venv/bin/python cancionero.py add-pdf mybook book.pdf
      import a PDF songbook

  .venv/bin/python cancionero.py links mybook
      find Spotify/YouTube links for songs that have none

  .venv/bin/python cancionero.py tags mybook
      show the book's tags and how many songs each has

  .venv/bin/python cancionero.py build mybook
      rebuild index.html after editing songs by hand

  .venv/bin/python cancionero.py publish mybook
      rebuild, commit and push: the website updates

  .venv/bin/python cancionero.py list
      list the books next to the builder

  .venv/bin/python cancionero.py help new
      step-by-step guide (also: help edit)
EOF
