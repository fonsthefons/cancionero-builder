"""Add the songs of a PDF songbook to a book (importer/pdf.py reads them).

Asked as it goes (or decided by the options, without questions):
which songs, their author, whether the PDF's section headings (albums,
"Misa"...) become tags, and whether to look up a Spotify/YouTube link for each.
Songs already in the book are skipped. A report of what to check by hand is
written to <book>/import-report.txt (kept out of git).
"""

import time
from pathlib import Path

from builder.songs import SongError
from builder.tags import Taxonomy, add_to_tags_file
from builder.text import slug

from .ask import ask, ask_yes
from .batch import find_link
from .pdf import read_pdf
from .songfile import existing_song, write_song

REPORT_NAME = "import-report.txt"


def parse_selection(answer, count):
    """'all', '1-10 15 20-' -> sorted indexes (0-based); or None if not understood."""
    answer = answer.strip().lower()
    if answer in ("", "all", "todo", "todos", "*"):
        return list(range(count))
    chosen = set()
    for part in answer.replace(",", " ").split():
        first, dash, last = part.partition("-")
        try:
            start = int(first) if first else 1
            end = (int(last) if last else count) if dash else start
        except ValueError:
            return None
        if not 1 <= start <= end <= count:
            return None
        chosen.update(range(start - 1, end))
    return sorted(chosen)


def show(songs):
    for n, song in enumerate(songs, start=1):
        flag = "  !" if song.notes else ""
        section = f"  [{song.section}]" if song.section else ""
        print(f"  {n:3}  {song.label}{section}  (p. {song.page}){flag}")


def add_pdf(book, pdf_path, select=None, author=None, sections_as_tags=None, links=None, ask_user=True, log=print):
    """Import songs from a PDF. Options left as None are asked (when ask_user).
    Returns the paths of the songs written."""
    log(f"Reading {pdf_path} ...")
    songs = read_pdf(pdf_path)
    if not songs:
        log("No songs found. Is it a scanned PDF (pictures of pages)? Those can't be read; "
            "copy the songs and paste them instead.")
        return []
    sections = sorted({s.section for s in songs if s.section})
    doubtful = sum(1 for s in songs if s.notes)
    log(f"Found {len(songs)} songs" + (f" in {len(sections)} sections" if sections else "")
        + (f"; {doubtful} have something to check (marked !)" if doubtful else "") + ".")

    if select is None and ask_user:
        show(songs)
        while True:
            select = ask("Which songs? (all, or numbers like 1-10 15)", "all")
            if parse_selection(select, len(songs)) is not None:
                break
            print(f"Please type all, or numbers between 1 and {len(songs)}.")
    chosen = [songs[i] for i in parse_selection(select or "all", len(songs)) or []]

    authors_in_pdf = any(s.author for s in chosen)
    if author is None and ask_user:
        hint = "Enter keeps the authors written in the PDF" if authors_in_pdf else "Enter for none"
        author = ask(f"Author of these songs ({hint})", book.default_author)
    if sections_as_tags is None:
        sections_as_tags = bool(sections) and ask_user and ask_yes(
            f"Use the PDF's sections as tags ({', '.join(sections[:6])}{'...' if len(sections) > 6 else ''})?",
            default=True)
    if links is None:
        links = ask_user and ask_yes(
            f"Look up a Spotify/YouTube link for each song? (about 5 seconds per song, "
            f"{len(chosen) * 5 // 60 + 1} min)", default=False)

    taxonomy = Taxonomy.load(book.tags_file)
    written, report, from_this_pdf = [], [], set()
    for n, song in enumerate(chosen, start=1):
        autor = author or song.author or None
        found = existing_song(book, song.title, autor or book.default_author or "")
        if found and found.stem in from_this_pdf:
            # the same title twice in the songbook ("Aleluya" in two albums): both are kept
            song.title = f"{song.title} ({song.section or song.page})"
            found = existing_song(book, song.title, autor or book.default_author or "")
        if found:
            report.append(f"- {song.label}: already in the book as {found.name}, skipped")
            continue
        tags = {}
        if sections_as_tags and song.section:
            tag_id = slug(song.section)
            tags[tag_id] = []
            if tag_id not in taxonomy.tags:
                add_to_tags_file(book.tags_file, tag_id, song.section)
                taxonomy = Taxonomy.load(book.tags_file)
        link = ""
        if links:
            link = find_link(song.title, autor or "", log)
            if n < len(chosen):
                time.sleep(2)  # gently: the web search gets busy after many searches
        try:
            path = write_song(book, song.title, autor, song.capo, link, tags, song.body)
        except SongError as e:
            report.append(f"- {song.label}: NOT added, the song file came out invalid ({e})")
            continue
        written.append(path)
        from_this_pdf.add(path.stem)
        log(f"[{n}/{len(chosen)}] {song.label} -> songs/{path.name}")
        if song.notes:
            report.append(f"- songs/{path.name} ({song.label}, PDF page {song.page}):\n    "
                          + "\n    ".join(song.notes))

    log(f"\nAdded {len(written)} of {len(chosen)} songs.")
    if report:
        report_path = book.root / REPORT_NAME
        header = f"Import of {Path(pdf_path).name}: songs to check against the PDF\n\n"
        report_path.write_text(header + "\n".join(report) + "\n", encoding="utf-8")
        log(f"{len(report)} songs to check: see {report_path}")
    return written
