"""Writing song files into a book, and the book's name lists (author aliases).

Used by every way of adding songs (importer/add.py, batch.py, pdf.py).
"""

import datetime
import json
import re
from pathlib import Path

import yaml

from builder.songs import SongError, load_song
from builder.text import slug, spanish_sort_key
from builder.tags import yaml_text as yaml_value

NO_AUTHOR = "popular"  # file name part for songs with no author


# ---------- names ----------

def song_name(book, title, autor):
    """File name (without .md): <title>_<author>, or <title> for the book's own
    artist (book.yaml default_author)."""
    if book.is_default_author(autor):
        return slug(title)
    return slug(title) + "_" + slug(autor or NO_AUTHOR)


def free_path(songs_dir, name):
    path = Path(songs_dir) / f"{name}.md"
    number = 2
    while path.exists():
        path = Path(songs_dir) / f"{name}_{number}.md"
        number += 1
    return path


# ---------- the song file ----------

def song_file(book, title, autor, capo, link, tags, body, added=None):
    """Text of a song file. The book's own artist isn't written (it's the default)."""
    lines = ["---", f"title: {yaml_value(title)}"]
    if autor and not book.is_default_author(autor):
        lines.append(f"autor: {yaml_value(autor)}")
    # Quoted as JSON strings (valid YAML): capo "2" stays text, links keep their ":"
    if capo:
        lines.append(f"capo: {json.dumps(str(capo), ensure_ascii=False)}")
    if link:
        lines.append(f"link: {json.dumps(link, ensure_ascii=False)}")
    if added is None and book.record_added:
        added = datetime.date.today().isoformat()
    if added:
        lines.append(f'added: "{added}"')
    if tags:
        lines.append("song_tags:")
        for tag_id, subtags in tags.items():
            if subtags:
                lines.append(f"  {tag_id}:")
                lines.extend(f"    - {sub}" for sub in subtags)
            else:
                lines.append(f"  {tag_id}: []")
    return "\n".join(lines + ["---", "", body.strip("\n"), ""])


def write_song(book, title, autor, capo, link, tags, body, added=None):
    """Write a new song file; returns its path. Raises SongError (and writes
    nothing) if the file wouldn't be a valid song."""
    book.songs_dir.mkdir(parents=True, exist_ok=True)
    path = free_path(book.songs_dir, song_name(book, title, autor))
    path.write_text(song_file(book, title, autor, capo, link, tags, body, added), encoding="utf-8")
    try:
        load_song(path)
    except (SongError, yaml.YAMLError) as e:
        path.unlink()
        raise SongError(str(e)) from e
    return path


# ---------- songs already in the book ----------

def book_songs(book):
    """[(path, Song)] of every readable song in the book."""
    found = []
    for path in sorted(book.songs_dir.glob("*.md")):
        try:
            found.append((path, load_song(path)))
        except (SongError, yaml.YAMLError):
            continue
    return found


def existing_song(book, title, autor=None):
    """Path of a song with the same title (and author, when given), or None."""
    key = spanish_sort_key(title)
    for path, song in book_songs(book):
        if spanish_sort_key(song.title) != key:
            continue
        if autor is None:
            return path
        theirs = song.autor or book.default_author or ""
        if spanish_sort_key(theirs) == spanish_sort_key(autor):
            return path
    return None


# ---------- author aliases ----------

def load_aliases(book):
    """{author as sites write it: author as the book writes it}."""
    if not book.aliases_file.exists():
        return {}
    data = yaml.safe_load(book.aliases_file.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items()}


def alias_for(artist, aliases):
    lowered = {k.casefold(): v for k, v in aliases.items()}
    return lowered.get(artist.casefold(), artist)


def remember_alias(book, site_name, book_name):
    with book.aliases_file.open("a", encoding="utf-8") as f:
        f.write(f"{yaml_value(site_name)}: {yaml_value(book_name)}\n")


def is_web_link(text):
    return bool(re.match(r"https?://", text or ""))
