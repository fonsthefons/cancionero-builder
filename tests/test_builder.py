"""Tests of the build: chord lines, free tags, book settings, rendering.

    .venv/bin/python -m pytest tests
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from builder.book import BookError, load_book, settings_yaml  # noqa: E402
from builder.build import build_book, fix_far_chords  # noqa: E402
from builder.keys import detect_key, respell_chords, respell_line, transpose_key  # noqa: E402
from builder.lyrics import chord_line_html, is_chord_line, pack_far_chords, verse_html  # noqa: E402
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
    assert '"installTip": true' in html and 'class="install-banner"' not in html  # the tutorial says it now
    assert '<button data-action="cycle-notation"' not in html
    assert 'data-autor="Hakuna"' not in html  # the book's own artist isn't shown
    assert '<details class="tag-index" id="tag-t" open>' in html
    assert '"storagePrefix": "y."' in html


def test_progress_setting(tmp_path):
    with pytest.raises(BookError, match="progress must be true or false"):
        write_book(tmp_path / "x", settings="title: T\nprogress: yes please\n")
    song = {"a": SONG.format(title="Uno", extra="")}
    build_book(write_book(tmp_path / "off", songs=song))
    assert "doneSongs" not in (tmp_path / "off" / "index.html").read_text(encoding="utf-8")
    build_book(write_book(tmp_path / "on", settings="title: T\nprogress: true\n", songs=song))
    html = (tmp_path / "on" / "index.html").read_text(encoding="utf-8")
    assert "doneSongs" in html and '"progress": true' in html


def test_tag_pills(tmp_path):
    songs = {"a": SONG.format(title="Uno", extra="song_tags:\n  misa: [entrada, comunion]\n  Adoración: []\n"),
             "b": SONG.format(title="Dos", extra="")}
    build_book(write_book(tmp_path / "on", songs=songs))
    html = (tmp_path / "on" / "index.html").read_text(encoding="utf-8")
    pills = re.findall(r'<i class="(k\d+)">(\w+)</i>', html)
    assert [text for _, text in pills] == ["Ado", "Mis", "Com", "Ent"]
    assert len({cls for cls, _ in pills}) == 4 and html.count('<p class="pills">') == 1
    colours = re.findall(r"\.k\d+\{background:(hsl\([^)]*\))\}", html)
    assert len(colours) == len(set(colours)) == 4  # every pill of the song its own colour
    build_book(write_book(tmp_path / "off", settings="title: T\ntag_pills: false\n", songs=songs))
    assert 'class="pills"' not in (tmp_path / "off" / "index.html").read_text(encoding="utf-8")


def test_detect_key():
    assert detect_key("C G Am F\nC F G C\n")[0] == "C"
    assert detect_key("Am Dm G C\nF Dm E Am\n")[0] == "Am"
    assert detect_key("A E F#m D\nA E D A\n")[0] == "A"
    assert detect_key("G C D G\nEm C D G\n")[0] == "G"
    assert detect_key("Gb Db Ebm Cb\nGb Db Gb\n")[0] == "Gb"  # the song's own spelling of its tonic
    assert detect_key("just words\n") is None


def test_spell_chords():
    assert respell_chords(["F", "A#", "C7", "F"], "F") == ["F", "Bb", "C7", "F"]
    assert respell_chords(["C", "G/G#", "Am"], "C") == ["C", "G/G#", "Am"]  # ambiguous: as written
    assert respell_chords(["D", "F#/Bb", "Bm"], "D") == ["D", "F#/A#", "Bm"]  # the bass is the chord's 3rd
    assert respell_chords(["Am", "G#7", "C#m"], "Am") == ["Am", "G#7", "C#m"]  # V of C#m stays G#
    assert respell_chords(["Dm", "Bbm", "F"], "Dm") == ["Dm", "Bbm", "F"]
    assert respell_chords(["C", "Abdim", "Am"], "C") == ["C", "G#dim", "Am"]  # leads up to A
    assert respell_line("A#   C  A#-C", ["Bb", "C", "Bb", "C"]) == "Bb   C  Bb-C"
    assert respell_line("C#  F", ["Db", "F"]) == "Db  F"
    assert respell_line("E#m F", ["Fm", "F"]) == "Fm  F"  # shorter: the next chord stays in its column
    assert transpose_key("F", 2) == "G" and transpose_key("Em", 1) == "Fm" and transpose_key("Bb", 0) == "Bb"


def test_song_keys(tmp_path):
    songs = {"a": SONG.format(title="Uno", extra="").replace("---\n\n", "---\n\nF   A#   C7   F\nla la la\n", 1)}
    book = write_book(tmp_path / "on", songs=songs)
    result = build_book(book)
    text = (tmp_path / "on" / "songs" / "a.md").read_text(encoding="utf-8")
    assert text.startswith("---\ntitle: Uno\nkey: F\n") and "F   Bb   C7   F" in text
    assert result.keys_added == [("a", "F", None)] and "Song keys added" in result.report(book)
    html = (tmp_path / "on" / "index.html").read_text(encoding="utf-8")
    assert 'data-key="F"' in html and 'class="meta-item song-key">Key: F<' in html
    assert build_book(book).keys_added == []  # once written, the key is kept (fix it by hand if wrong)
    with pytest.raises(SongError, match="key must be"):
        build_book(write_book(tmp_path / "bad", songs={"a": SONG.format(title="Uno", extra="key: H\n")}))
    book = write_book(tmp_path / "off", settings="title: T\nsong_keys: false\n", songs=songs)
    build_book(book)
    assert "key:" not in (tmp_path / "off" / "songs" / "a.md").read_text(encoding="utf-8")


MELODY = 'melody: |\n  K:D\n  "D"F8 "A"G A | "Em"F2 z E D\ntab: {tab}\n'


def test_melody(tmp_path):
    for tab, error in [("4/4 0/3 2/3 | 4/4 2/4", "tab has 5 notes but melody has 6"),
                       ("4/4 0/3 2/3 | 4/4 2/4 0/7", '"0/7" is not fret/string')]:
        book = write_book(tmp_path / str(len(error)), songs={"a": SONG.format(title="Uno", extra=MELODY.format(tab=tab))})
        with pytest.raises(SongError, match=error):
            build_book(book)
    no_tab = 'melody: |\n  K:D\n  "D"F8 "A"G A\n'
    build_book(write_book(tmp_path / "no_tab", songs={"a": SONG.format(title="Uno", extra=no_tab)}))
    assert 'data-tab=""' in (tmp_path / "no_tab" / "index.html").read_text(encoding="utf-8")
    partial = MELODY.format(tab="4/4 0/3") + 'ignore: ["tab-melody-check"]\n'
    build_book(write_book(tmp_path / "partial", songs={"a": SONG.format(title="Uno", extra=partial)}))
    for tab, ignore, error in [("4/4 0/7", "tab-melody-check", '"0/7" is not fret/string'),
                               ("4/4 0/3", "typo", '"typo" is not a check')]:
        extra = MELODY.format(tab=tab) + f"ignore: [{ignore}]\n"
        book = write_book(tmp_path / ignore, songs={"a": SONG.format(title="Uno", extra=extra)})
        with pytest.raises(SongError, match=error):
            build_book(book)
    book = write_book(tmp_path / "ok", songs={
        "a": SONG.format(title="Uno", extra=MELODY.format(tab="4/4 0/3 2/3 | 4/4 2/4 0/4")),
        "b": SONG.format(title="Dos", extra="")})
    build_book(book)
    html = (tmp_path / "ok" / "index.html").read_text(encoding="utf-8")
    assert html.count('<div class="melody"') == 1
    assert html.count('class="melody-play"') == 1  # only the song with a melody
    assert 'data-abc="X:1\nM:none\nL:1/4\nK:D\n&quot;D&quot;F8' in html and "ABCJS" in html
    plain = write_book(tmp_path / "plain", songs={"b": SONG.format(title="Dos", extra="")})
    build_book(plain)
    html = (tmp_path / "plain" / "index.html").read_text(encoding="utf-8")
    assert "ABCJS" not in html and "renderMelody" not in html  # no 480 kB library


def test_psalm_formulas(tmp_path):
    songs = {
        "salmo": SONG.format(title="Salmo 1", extra="song_tags:\n  salmos: []\n"),
        "f1": SONG.format(title="Glorioso", extra="song_tags:\n  formulas: [semitonos_2]\n"
                          + MELODY.format(tab="4/4 0/3 2/3 | 4/4 2/4 0/4")),
        "otra": SONG.format(title="Otra", extra=""),
    }
    on = write_book(tmp_path / "on", "title: T\npsalm_tags: [salmos]\nformula_tag: formulas\n", songs)
    build_book(on)
    html = (tmp_path / "on" / "index.html").read_text(encoding="utf-8")
    assert html.count('data-action="formula-pick"') == 1 and "function setFormula" in html
    assert '"formulas": [["Semitonos 2", [["song-f1", "Glorioso"]], "semitonos_2"]]' in html
    assert html.count('class="melody-play"') == 2  # the fórmula, and the psalm (for its fórmula)
    off = write_book(tmp_path / "off", "title: T\n", songs)
    build_book(off)
    html = (tmp_path / "off" / "index.html").read_text(encoding="utf-8")
    assert 'data-action="formula-pick"' not in html and "function setFormula" not in html
    # formula_parts: a hymn without chords gets the picker, one with chords doesn't
    hymns = {**songs,
             "h1": "---\ntitle: Sin acordes\nhoras: [lunes/laudes/himno]\n---\n\nla la la\n",
             "h2": SONG.format(title="Con acordes", extra="horas: [lunes/laudes/himno]\n")}
    hy = write_book(tmp_path / "hy", "title: T\npsalm_tags: [salmos]\nformula_tag: formulas\nformula_parts: [Himno]\n", hymns)
    (tmp_path / "hy" / "horas.yaml").write_text("tree:\n  Lunes: {Laudes: [Himno]}\n", encoding="utf-8")
    build_book(hy)
    html = (tmp_path / "hy" / "index.html").read_text(encoding="utf-8")
    assert html.count('data-action="formula-pick"') == 2  # the psalm and "Sin acordes"


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


FAR = ("                                Em                F#\npodrá calmar de mi alma la tempestad\n"
       "                  A         G     F#\nque me amaste desde siempre\n"
       "            G\nque solo tú\n"
       "      Am    F    C    G\n Try\n")


def test_pack_far_chords():
    body, changed = pack_far_chords(FAR)
    assert changed == [1, 3]
    assert body.split("\n")[:6] == [
        "                                Em   F#", "podrá calmar de mi alma la tempestad",
        "                  A         G F#", "que me amaste desde siempre", "            G", "que solo tú"]
    assert body.endswith("      Am    F    C    G\n Try\n")  # 3+ chords past the lyric: an instrumental bit


def test_line_warnings_and_fix(tmp_path):
    long = "x" * 51
    book = write_book(tmp_path, settings="title: Test\nsong_keys: false\n", songs={
        "a": "---\ntitle: A\n---\n\n" + FAR + long + "\n",
        "b": "---\ntitle: B\nignore: [long-lines-check, far-chords-check]\n---\n\n" + FAR + long + "\n",
    })
    result = build_book(book)
    assert result.long_lines == {"a": [(5, 52), (13, 51)]} and result.far_chords == {"a": [5, 7]}
    report = result.report(book)
    assert "a.md: line 5, 13" in report and "a.md: line 5, 7" in report and "b.md" not in report
    assert fix_far_chords(book, result.far_chords) == 2
    text = (tmp_path / "songs" / "a.md").read_text(encoding="utf-8")
    assert text.startswith("---\ntitle: A\n---\n\n") and "Em   F#\n" in text
    again = build_book(book)
    assert again.far_chords == {} and again.long_lines == {"a": [(13, 51)]}  # packing fixed the long chord line
