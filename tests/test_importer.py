"""Tests of the importers that need no internet: cleaning, chord names, song
files, tag answers, lists, PDF helpers."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from builder.book import load_book  # noqa: E402
from builder.songs import load_song  # noqa: E402
from builder.tags import Taxonomy  # noqa: E402
from importer.ask import parse_tag_answer  # noqa: E402
from importer.batch import read_list  # noqa: E402
from importer.chords import Notation, could_be_chord  # noqa: E402
from importer.clean import clean_song  # noqa: E402
from importer.links import set_link  # noqa: E402
from importer.pdf import META_RE, column_split, nice_case, split_title  # noqa: E402
from importer.pdf_add import parse_selection  # noqa: E402
from importer.songfile import existing_song, write_song  # noqa: E402


def test_chord_names():
    notation = Notation(["Fm#", "D-E-F#m"])
    assert notation.convert("Fm#") == "F#m"
    assert notation.convert("Cm#7") == "C#m7"
    assert notation.convert("D-E-F#m") == "D-E-F#m"
    assert could_be_chord("D-E-F#m") and not could_be_chord("la-la-la")


def test_clean_keeps_solo_label():
    cleaned = clean_song("Solo: G Am C G\nG        C\nSome words here", from_web=False, intro=False)
    assert cleaned.body.split("\n")[0] == "Solo: G Am C G"


def test_clean_spanish_chords():
    cleaned = clean_song("LAm      SOL\nUna línea de letra", from_web=False, intro=False)
    assert cleaned.body.split("\n")[0] == "Am       G"


def make_book(tmp_path, settings="title: T\n"):
    (tmp_path / "songs").mkdir()
    (tmp_path / "book.yaml").write_text(settings, encoding="utf-8")
    return load_book(tmp_path)


def test_write_song(tmp_path):
    book = make_book(tmp_path, "title: T\ndefault_author: Hakuna\nrecord_added: true\n")
    path = write_song(book, "¿Por qué?", "Hakuna", "2", "https://x.y/z", {"misa": ["entrada"]}, "G\nla")
    assert path.name == "por_que.md"  # the book's own artist: not in the file name
    song = load_song(path)
    assert song.title == "¿Por qué?" and song.autor is None and song.capo == "2" and song.added
    assert song.tags == {"misa": ["entrada"]}
    other = write_song(book, "¿Por qué?", "Otro", None, "", {}, "G\nla")
    assert other.name == "por_que_otro.md"
    assert existing_song(book, "Por qué", "Hakuna") == path
    assert existing_song(book, "Por qué", "Otro") == other
    set_link(other, "https://open.spotify.com/track/abc")
    assert load_song(other).link == "https://open.spotify.com/track/abc"


def test_tag_answer():
    choices = Taxonomy.load(Path("/nonexistent")).choices() + [("misa", None, "Misa"), ("misa", "entrada", "Misa: Entrada")]
    picked = parse_tag_answer("1 2, Navidad, Tiempo litúrgico/Cuaresma", choices)
    assert picked == [("misa", None, None, None), ("misa", "entrada", None, None),
                      ("navidad", None, "Navidad", None),
                      ("tiempo_liturgico", "cuaresma", "Tiempo litúrgico", "Cuaresma")]
    assert isinstance(parse_tag_answer("7", choices), str)


def test_lists(tmp_path):
    plain = tmp_path / "want.txt"
    plain.write_text("Want:\nUno - Artista\nDos\nNOT YET:\nTres\n", encoding="utf-8")
    assert [(w.title, w.artist) for w in read_list(plain, "Want")] == [("Uno", "Artista"), ("Dos", "")]
    ug = tmp_path / "ug.txt"
    ug.write_text("Passenger\nGolden Leaves (ver 3)\nJan 28, 2015\nAll The Little Lights\nFeb 9, 2015 Tab\n",
                  encoding="utf-8")
    items = read_list(ug)
    assert [(w.artist, w.title, w.version, w.added, w.kind) for w in items] == [
        ("Passenger", "Golden Leaves", 3, "2015-01-28", ""),
        ("Passenger", "All The Little Lights", 1, "2015-02-09", "Tab")]


def test_pdf_helpers():
    assert split_title("12. Title - Some Author") == (12, "Title", "Some Author")
    assert split_title("30. VI - VERÓNICA") == (30, "VERÓNICA", None)
    assert split_title("I Will Follow") == (None, "I Will Follow", None)
    assert nice_case("SOPLA SEÑOR") == "Sopla señor" and nice_case("Mixed Case") == "Mixed Case"
    assert parse_selection("all", 5) == [0, 1, 2, 3, 4]
    assert parse_selection("1-2 4-", 5) == [0, 1, 3, 4]
    assert parse_selection("9", 5) is None


def test_pdf_printed_book():
    # the byline of a printed builder book
    meta = META_RE.fullmatch("Autor: Matt Redman Capo: 0, original 0 Link")
    assert meta.groups() == ("Matt Redman", "0, original 0")
    assert META_RE.fullmatch("Autor: popular Link").groups() == ("popular", None)
    assert META_RE.fullmatch("Autoridad y poder") is None

    # two columns under a title that runs into the right column
    def row(x0, x1, bottom, text="x"):
        return [{"x0": x, "x1": x + 5, "bottom": bottom, "text": text} for x in range(x0, x1, 6)]
    rows = [row(43, 310, 50)] + [row(43, 230, y) + row(307, 480, y) for y in range(80, 200, 14)]
    split, header = column_split(rows, 596)
    assert header == 1 and 230 < split < 307
    one_column = [row(43, 480, y) for y in range(80, 200, 14)]
    assert column_split(one_column, 596) is None
