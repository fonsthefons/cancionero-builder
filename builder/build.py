"""Build a song book: its songs/*.md -> index.html (one self-contained page),
plus the files the home-screen app needs next to it (sw.js, manifest, icons)."""

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .render import fill_template, render_book
from .songs import SongError, load_songs
from .tags import Taxonomy

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
SITE_DIR = WEB_DIR / "site"
ICONS = ("icon-180.png", "icon-512.png")


@dataclass
class BuildResult:
    songs: list
    size: int  # bytes of index.html
    untagged: list = field(default_factory=list)  # song ids
    new_tags: list = field(default_factory=list)  # tags found only in songs

    def report(self, book):
        lines = [f"Built {book.name}/index.html: {len(self.songs)} songs, {self.size / 1e6:.2f} MB"]
        if self.untagged:
            lines.append(f"Songs without tags (only in All Songs): {', '.join(self.untagged)}")
        if self.new_tags:
            lines.append("Tags not in tags.yaml (shown with these labels; add them to tags.yaml "
                         "to change label or order): " + ", ".join(self.new_tags))
        return "\n".join(lines)


def load_book_songs(book):
    """(songs, taxonomy) of a book. Raises SongError listing every invalid song."""
    taxonomy = Taxonomy.load(book.tags_file, strict=book.strict_tags)
    songs = load_songs(book.songs_dir, taxonomy)
    for song in songs:
        if book.is_default_author(song.autor):
            song.autor = None  # the book's own artist isn't shown
    return songs, taxonomy


def manifest(book):
    data = {
        "name": book.title,
        "short_name": book.display_short_name,
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": book.background_color,
        "theme_color": book.theme_color,
        "icons": [
            {"src": "icon-180.png", "sizes": "180x180", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def write_if_changed(path, text):
    """Write only when the content differs, so git sees no change otherwise."""
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def build_book(book, web_dir=WEB_DIR):
    """Write the book's index.html, sw.js and manifest. Raises SongError."""
    songs, taxonomy = load_book_songs(book)
    html = render_book(book, songs, taxonomy.group(songs), web_dir)
    write_if_changed(book.root / "index.html", html)  # must stay at the root for GitHub Pages

    storage_key = book.storage_prefix.rstrip(".")
    sw = fill_template((SITE_DIR / "sw.js").read_text(encoding="utf-8"), {"storage_key": storage_key})
    write_if_changed(book.root / "sw.js", sw)  # must be its own file at the root
    write_if_changed(book.root / "manifest.webmanifest", manifest(book))
    for icon in ICONS:
        if not (book.root / icon).exists():
            shutil.copyfile(SITE_DIR / icon, book.root / icon)

    return BuildResult(
        songs=songs,
        size=len(html.encode("utf-8")),
        untagged=[song.id for song in songs if not song.tags],
        new_tags=[] if book.strict_tags else taxonomy.new_names(),
    )


__all__ = ["BuildResult", "SongError", "build_book", "load_book_songs", "manifest"]
