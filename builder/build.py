"""Build a song book: its songs/*.md -> index.html (one self-contained page),
plus the files the home-screen app needs next to it (sw.js, manifest, icons)."""

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .horas import fill, load_horas
from .lyrics import LONG_LINE, long_lines, pack_far_chords
from .render import fill_template, render_book
from .songs import SongError, load_songs, split_frontmatter
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
    long_lines: dict = field(default_factory=dict)  # song id -> [(line number, columns)]
    far_chords: dict = field(default_factory=dict)  # song id -> [line numbers] pack_far_chords would change

    def report(self, book):
        lines = [f"Built {book.name}/index.html: {len(self.songs)} songs, {self.size / 1e6:.2f} MB"]
        if self.untagged:
            lines.append(f"Songs without tags (only in All Songs): {', '.join(self.untagged)}")
        if self.new_tags:
            lines.append("Tags not in tags.yaml (shown with these labels; add them to tags.yaml "
                         "to change label or order): " + ", ".join(self.new_tags))
        if self.long_lines:
            lines.append(f"Warning: lines over {LONG_LINE} columns (the whole song gets small on phones; split them,"
                         " e.g. with Enter in the editor, or add ignore: [long-lines-check]):\n" + "\n".join(
                             f"  {song_id}.md: line {', '.join(str(n) for n, _ in found)}"
                             for song_id, found in self.long_lines.items()))
        if self.far_chords:
            lines.append("Warning: chords far past the end of their lyric (fixable: they move next to it;"
                         " or add ignore: [far-chords-check]):\n" + "\n".join(
                             f"  {song_id}.md: line {', '.join(map(str, found))}" for song_id, found in self.far_chords.items()))
        return "\n".join(lines)


def fix_far_chords(book, song_ids):
    """Move the far chords of these songs next to their lyric, in their files. Returns the lines changed."""
    count = 0
    for song_id in song_ids:
        path = book.songs_dir / f"{song_id}.md"
        text = path.read_text(encoding="utf-8")
        body = split_frontmatter(text)[1]
        packed, changed = pack_far_chords(body)
        if changed:
            path.write_text(text[: len(text) - len(body)] + packed, encoding="utf-8")
            count += len(changed)
    return count


def load_book_songs(book):
    """(songs, taxonomy) of a book. Raises SongError listing every invalid song."""
    taxonomy = Taxonomy.load(book.tags_file, strict=book.strict_tags)
    songs = load_songs(book.songs_dir, taxonomy, load_horas(book.horas_file))
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
    horas = load_horas(book.horas_file)
    html = render_book(book, songs, taxonomy.group(songs), web_dir, horas and fill(horas, songs))
    write_if_changed(book.root / "index.html", html)  # must stay at the root for GitHub Pages

    write_if_changed(book.root / "manifest.webmanifest", manifest(book))
    for icon in ICONS:
        if not (book.root / icon).exists():
            shutil.copyfile(SITE_DIR / icon, book.root / icon)

    # sw.js serves these from its cache, so they only update when its cache name does
    digest = hashlib.sha256()
    for name in ("manifest.webmanifest", *ICONS):
        digest.update((book.root / name).read_bytes())
    storage_key = book.storage_prefix.rstrip(".")
    sw = fill_template((SITE_DIR / "sw.js").read_text(encoding="utf-8"),
                       {"storage_key": storage_key, "version": digest.hexdigest()[:10]})
    write_if_changed(book.root / "sw.js", sw)  # must be its own file at the root

    return BuildResult(
        songs=songs,
        size=len(html.encode("utf-8")),
        untagged=[song.id for song in songs if not song.tags and not song.horas],
        new_tags=[] if book.strict_tags else taxonomy.new_names(),
        long_lines={s.id: [(n + body_start(book, s), cols) for n, cols in found] for s in songs
                    if "long-lines-check" not in s.ignore and (found := long_lines(s.body))},
        far_chords={s.id: [n + body_start(book, s) for n in found] for s in songs
                    if "far-chords-check" not in s.ignore and (found := pack_far_chords(s.body)[1])},
    )


def body_start(book, song):
    """Lines before the song's body in its file (body line numbers + this = file line numbers)."""
    return (book.songs_dir / f"{song.id}.md").read_text(encoding="utf-8").count("\n") - song.body.count("\n")


__all__ = ["BuildResult", "SongError", "build_book", "fix_far_chords", "load_book_songs", "manifest"]
