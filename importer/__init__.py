"""Importing songs into the book (used by add_song.py).

    fetch.py   download a web page (falls back to a headless browser when a
               site blocks simple downloads)
    sites/     one reader per website, turning its page into a Draft
    chords.py  chord names: Spanish notation (Do, RE, mi...) to letters,
               rewriting chord lines without moving any chord off its letter
    clean.py   tidy the song text: spaces instead of tabs, no odd characters,
               no section labels, an "Intro:" at the top
"""
