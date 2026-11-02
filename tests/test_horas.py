"""Tests of the Liturgia de las Horas tree (horas.yaml), natural song order, the
Flexa label and `new --template`.

    .venv/bin/python -m pytest tests
"""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from builder import create  # noqa: E402
from builder.build import build_book, load_book_songs  # noqa: E402
from builder.horas import load_horas  # noqa: E402
from builder.lyrics import lyric_line_html  # noqa: E402
from builder.songs import SongError  # noqa: E402
from test_builder import SONG, write_book  # noqa: E402

HORAS = """\
label: Liturgia de las Horas
parts:
  laudes: &laudes [Apertura, Himno, Benedictus]
  visperas: &visperas [Apertura, Himno, Magnificat]
tree:
  Semana I: &semana
    Domingo:
      Primeras Vísperas: *visperas
      Laudes: *laudes
    Lunes: {Laudes: *laudes, Vísperas: *visperas}
  Semana II: *semana
  Completas:
    Lunes: [Himno, Nunc Dimittis]
"""


@pytest.fixture
def scratch(request):
    """A fresh folder in scratch/ (never the system temp folder)."""
    path = ROOT / "scratch" / "test_horas" / request.node.name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True)
    return path


def test_tree(scratch):
    (scratch / "horas.yaml").write_text(HORAS, encoding="utf-8")
    tree = load_horas(scratch / "horas.yaml")
    assert tree.label == "Liturgia de las Horas"
    assert [c.label for c in tree.children] == ["Semana I", "Semana II", "Completas"]  # not `parts`
    paths = [part.path for part in tree.parts()]
    assert paths[:3] == ["semana_i/domingo/primeras_visperas/apertura", "semana_i/domingo/primeras_visperas/himno",
                         "semana_i/domingo/primeras_visperas/magnificat"]
    assert "semana_ii/lunes/visperas/magnificat" in paths and "completas/lunes/nunc_dimittis" in paths
    assert tree.unmatched(["Semana I/Domingo/Laudes/Himno", "*visperas/magnificat", "semana_i/*/himno",
                           "semana_i/domingo/laudes/himnno", "semana_iii/*"]) == [
        "semana_i/domingo/laudes/himnno", "semana_iii/*"]
    assert load_horas(scratch / "none.yaml") is None


def test_horas_errors(scratch):
    book = write_book(scratch / "a", songs={"x": SONG.format(title="X", extra="horas: semana_i/lunes/laudes/himno\n")})
    with pytest.raises(SongError, match="no horas.yaml"):
        load_book_songs(book)
    book = write_book(scratch / "b", songs={"x": SONG.format(title="X", extra="horas: [semana_9/*]\n")})
    (book.horas_file).write_text(HORAS, encoding="utf-8")
    with pytest.raises(SongError, match='"semana_9/\\*" matches no part'):
        load_book_songs(book)


def test_horas_contents(scratch):
    book = write_book(scratch, songs={
        "a": SONG.format(title="Benedictus", extra="horas: [semana_i/domingo/laudes/benedictus]\n"),
        "b": SONG.format(title="Abre mis labios", extra="horas: [semana_i/domingo/laudes/apertura]\n"
                                                         "song_tags:\n  misa: [entrada]\n"),
        "c": SONG.format(title="Magnificat", extra='horas: ["*visperas/magnificat"]\n'),
    })
    book.horas_file.write_text(HORAS, encoding="utf-8")
    build_book(book)
    html = (scratch / "index.html").read_text(encoding="utf-8")
    index = html[html.index('<section id="index"'):html.index("</section>", html.index('<section id="index"'))]
    # Horas first, then the tags; parts in horas.yaml order, empty ones left out
    assert index.index('id="horas"') < index.index('id="tag-misa"')
    laudes = index[index.index('id="horas-semana_i-domingo-laudes"'):]
    assert laudes.index("Apertura: 1. Abre mis labios") < laudes.index("Benedictus: 2. Benedictus")
    assert "Himno:" not in index and "horas-completas" not in index
    assert 'id="horas-semana_ii-lunes-visperas"' in index and "Magnificat: 3. Magnificat" in index
    assert '<details class="subtag-index" id="horas-semana_i-domingo"><summary><h4>Domingo</h4>' in index
    nav = html[html.index('<ul class="nav">'):]
    assert '<a class="nav-subtag" href="#horas-semana_ii">Semana II</a>' in nav and "#horas-completas" not in nav


def test_flexa_label():
    assert lyric_line_html("Flexa: D A") == (
        '<div class="lyric-line chord-inline">Flexa: <span class="chord">D</span> <span class="chord">A</span></div>')


def test_natural_order(scratch):
    book = write_book(scratch, songs={name: SONG.format(title=title, extra="") for name, title in
                                      [("a", "10 Alegre"), ("b", "2 Suplicante"), ("c", "Ave"), ("d", "1 Narrativo")]})
    songs, _ = load_book_songs(book)
    assert [s.title for s in songs] == ["1 Narrativo", "2 Suplicante", "10 Alegre", "Ave"]


def test_new_from_template(scratch, monkeypatch):
    template = scratch / "templates" / "liturgia"
    (template / "songs").mkdir(parents=True)
    (template / "tags.yaml").write_text("misa:\n  label: Misa\n", encoding="utf-8")
    (template / "horas.yaml").write_text(HORAS, encoding="utf-8")
    (template / "songs" / "himno.md").write_text(
        SONG.format(title="Himno", extra="horas: [completas/lunes/himno]\n"), encoding="utf-8")
    (scratch / "other-tags.yaml").write_text("otra:\n  label: Otra\n", encoding="utf-8")
    monkeypatch.setattr(create, "TEMPLATES_DIR", scratch / "templates")
    books = scratch / "books"

    with pytest.raises(create.CreateError, match='no template "nada".*found: liturgia'):
        create.create_book("x", {}, books, template="nada", log=lambda _: None)
    book = create.create_book("lit", {}, books, copy_tags_from=scratch / "other-tags.yaml", template="liturgia",
                              dry_run=True, log=lambda _: None)
    assert (book.root / "tags.yaml").read_text(encoding="utf-8") == "misa:\n  label: Misa\n"  # template wins
    assert (book.root / "horas.yaml").is_file() and (book.root / "songs" / "himno.md").is_file()
    assert 'id="horas-completas-lunes"' in (book.root / "index.html").read_text(encoding="utf-8")
