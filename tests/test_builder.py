"""Tests of the build: chord lines, free tags, book settings, rendering.

    .venv/bin/python -m pytest tests
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from builder.book import BookError, load_book, settings_yaml  # noqa: E402
from builder.build import build_book  # noqa: E402
from builder.lyrics import chord_line_html, is_chord_line, verse_html  # noqa: E402
from builder.songs import SongError  # noqa: E402
from builder.tags import Taxonomy, add_to_tags_file  # noqa: E402
from builder.text import slug, spanish_sort_key  # noqa: E402


@pytest.mark.parametrize("line", [
    "G  C  D", "Am7 A7sus2 C#m7b5", "D/F#  Em", "| C  | Am  F  | x2", "G D C D (x2)",
    "Bb/D  Bbm/Db  C7  C7-9  C7  F", "   G    D/F#    Em7     D--A", "|C---|C---|G---|G7---|",
    "Amadd9 GSus",
])
def test_chord_lines(line):
    assert is_chord_line(line)


@pytest.mark.parametrize("line", [
    "Sopla Señor, sopla en mí", "G|--2----2---2-2-2--1-----0---0----|  x3",
    "B|-10/12----12-10-12b-10--8/10-12-10--8--10b--8--|", "Bb  x13331", "B-----------------",
    "A ti te alabo", "",
])
def test_not_chord_lines(line):
    assert not is_chord_line(line)


def test_lyrics_html_is_slim():
    # Chords are the plain words of a chord line (no span each); separators are spans.
    assert chord_line_html("  C#m-Bm  G (x2) |") == (
        '<div class="chord-line">  C#m<span class="sep">-</span>Bm  G '
        '<span class="sep">(x2)</span> <span class="sep">|</span></div>')
    # A plain lyric is the pair's own text; "Intro:" chords keep their line and spans.
    verse = [("G      D", False), ("A ti te alabo", True), ("C", False), ("Intro: G D", False)]
    assert verse_html(verse) == (
        '<div class="verse"><div class="line-pair bold"><div class="chord-line">G      D</div>A ti te alabo</div>'
        '<div class="line-pair"><div class="chord-line">C</div><div class="lyric-line chord-inline">'
        'Intro: <span class="chord">G</span> <span class="chord">D</span></div></div></div>')


def test_slug_and_sort():
    assert slug("Don't Cry") == "dont_cry"
    assert slug("Tiempo litúrgico") == "tiempo_liturgico"
    titles = ["Ñu", "Nube", "¿Por qué?", "Déjate", "Dulce"]
    assert sorted(titles, key=spanish_sort_key) == ["Déjate", "Dulce", "Nube", "Ñu", "¿Por qué?"]


def write_book(root, settings="title: Test\n", songs=None, tags=None):
    (root / "songs").mkdir(parents=True)
    (root / "book.yaml").write_text(settings, encoding="utf-8")
    if tags is not None:
        (root / "tags.yaml").write_text(tags, encoding="utf-8")
    for name, text in (songs or {}).items():
        (root / "songs" / f"{name}.md").write_text(text, encoding="utf-8")
    return load_book(root)


SONG = "---\ntitle: {title}\n{extra}---\n\nG     C\nla la la\n"


def test_free_tags(tmp_path):
    book = write_book(tmp_path, songs={
        "a": SONG.format(title="Uno", extra="song_tags:\n  Misa: [Comunión]\n  Pasión: []\n"),
        "b": SONG.format(title="Dos", extra="song_tags:\n  misa: [comunion, entrada]\n"),
    }, tags="misa:\n  label: La Misa\n  subtags:\n    entrada: Entrada\n")
    result = build_book(book)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "La Misa" in html and "Comunión" in html and "Pasión" in html
    # tags.yaml's subtag first, then the found one
    assert html.index('id="tag-misa-entrada"') < html.index('id="tag-misa-comunion"')
    assert "Pasión (pasion)" in result.new_tags[0] or any("Pasión" in t for t in result.new_tags)
    assert (tmp_path / "sw.js").exists() and (tmp_path / "icon-512.png").exists()


def test_sw_cache_follows_icons(tmp_path):
    book = write_book(tmp_path, songs={"a": SONG.format(title="Uno", extra="")})
    build_book(book)
    first = (tmp_path / "sw.js").read_text(encoding="utf-8")
    assert "{{" not in first
    build_book(book)
    assert (tmp_path / "sw.js").read_text(encoding="utf-8") == first
    (tmp_path / "icon-512.png").write_bytes(b"new icon")
    build_book(book)
    assert (tmp_path / "sw.js").read_text(encoding="utf-8") != first


def test_strict_tags(tmp_path):
    book = write_book(tmp_path, settings="title: Test\nstrict_tags: true\n", songs={
        "a": SONG.format(title="Uno", extra="song_tags:\n  otra: []\n"),
    }, tags="misa:\n  label: Misa\n")
    with pytest.raises(SongError, match='unknown tag "otra"'):
        build_book(book)


def test_book_settings(tmp_path):
    with pytest.raises(BookError, match="unknown setting"):
        write_book(tmp_path / "x", settings="title: T\nfold_tagz: true\n")
    book = write_book(tmp_path / "y", settings="title: Libro\ninstall_tip: banner\nnotation_setting: false\n"
                      "default_author: Hakuna\nfold_tags: false\n", songs={
        "a": SONG.format(title="Uno", extra="autor: Hakuna\nsong_tags:\n  t: []\n")})
    build_book(book)
    html = (tmp_path / "y" / "index.html").read_text(encoding="utf-8")
    assert '<aside class="install-banner"' in html and 'id="install-tip"' not in html
    assert 'data-action="cycle-notation"' not in html
    assert 'data-autor="Hakuna"' not in html  # the book's own artist isn't shown
    assert '<details class="tag-index" id="tag-t" open>' in html
    assert '"storagePrefix": "y."' in html


def test_settings_yaml_round_trip(tmp_path):
    settings = {"title": "Cancionero: Misa", "sites": ["ultimate_guitar"], "language_tags": True}
    (tmp_path / "book.yaml").write_text(settings_yaml(settings), encoding="utf-8")
    assert load_book(tmp_path).settings == settings


def test_add_to_tags_file_keeps_comments(tmp_path):
    path = tmp_path / "tags.yaml"
    path.write_text("# my albums\n\nmisa:\n  label: Misa\n  subtags:\n    entrada: Entrada\n\notra:\n  label: Otra\n",
                    encoding="utf-8")
    add_to_tags_file(path, "misa", "Misa", "salida", "Salida")
    add_to_tags_file(path, "otra", "Otra", "uno", "Uno")
    add_to_tags_file(path, "nueva", "Nueva")
    add_to_tags_file(path, "misa", "Misa", "salida", "Salida")  # already there
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# my albums")
    tags = Taxonomy.load(path).tags
    assert list(tags) == ["misa", "otra", "nueva"]
    assert list(tags["misa"].subtags) == ["entrada", "salida"]
    assert tags["otra"].subtags == {"uno": "Uno"}
