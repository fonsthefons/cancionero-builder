"""Tests of the song editor's server (importer/editor.py), on a book in scratch/."""

import json
import shutil
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from builder.book import load_book  # noqa: E402
from builder.songs import load_song  # noqa: E402
from importer.editor import make_server, rows  # noqa: E402

SHEET = "G       D\nHello my friend\n\nEm\n**\nC\nonly words\n"


@pytest.fixture
def editor(request):
    root = ROOT / "scratch" / "test_editor" / request.node.name
    shutil.rmtree(root, ignore_errors=True)
    (root / "songs").mkdir(parents=True)
    (root / "book.yaml").write_text("title: T\nrecord_added: true\n", encoding="utf-8")
    server = make_server(load_book(root))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def call(path, data=None, token=server.token, host=None):
        request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}{path}",
                                         data=None if data is None else json.dumps(data).encode(),
                                         headers={"X-Token": token} if token else {})
        if host:
            request.add_header("Host", host)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    yield call, root
    server.shutdown()
    server.server_close()


def save(call, **fields):
    return call("/api/save", {"id": None, "title": "Hola", "autor": "Ana", "capo": "", "link": "", "tags": [],
                              "horas": [], "melody": "", "tab": "", "ignore": [], "body": SHEET, **fields})


def test_rows():
    assert rows(SHEET) == [
        {"chords": [[0, "G"], [8, "D"]], "lyric": "Hello my friend"},
        {"text": ""},
        {"chords": [[0, "Em"]], "lyric": None},
        {"chords": [[0, "C"]], "lyric": "only words", "bold": True},
        {"text": ""},
    ]
    assert rows("Intro: G D\ne|--2--|\nla la") == [{"text": "Intro: G D"}, {"text": "e|--2--|"},
                                                   {"chords": [], "lyric": "la la"}]


def test_rows_keep_chord_lines_with_marks():
    # writing these back from chord positions would drop (x2), the bars, the parens or the tab
    for line in ("G  D  (x2)", "| Em | C |", "(G", "G\tD"):
        assert rows(f"{line}\nla la\nC\nmore") == [{"text": line}, {"text": "la la"},
                                                   {"chords": [[0, "C"]], "lyric": "more"}]


def test_rows_bold():
    assert rows("**\nC\nChorus\nmore\n**\n\nVerse") == [
        {"chords": [[0, "C"]], "lyric": "Chorus", "bold": True}, {"chords": [], "lyric": "more", "bold": True},
        {"text": ""}, {"chords": [], "lyric": "Verse"}]
    # a ** may span verses; blank lines are never bold
    assert rows("**\nla\n\nlo\n**") == [{"chords": [], "lyric": "la", "bold": True}, {"text": ""},
                                       {"chords": [], "lyric": "lo", "bold": True}]


def test_rows_parenthesized_chord():
    assert rows("      G (D)\nTómala") == [{"chords": [[6, "G"], [8, "(D)"]], "lyric": "Tómala"}]


def test_host_header(editor):
    call, _ = editor
    assert call("/api/book", host="evil.example:80")[0] == 403
    assert call("/api/rows", {"body": "x"}, host="evil.example")[0] == 403
    assert call("/api/book")[0] == 200


def test_edit_keeps_no_date(editor):
    call, root = editor
    (root / "songs" / "old.md").write_text("---\ntitle: Old\n---\n\nla\n", encoding="utf-8")
    assert save(call, id="old", title="Old")[0] == 200
    assert load_song(root / "songs" / "old.md").added is None


def test_token_and_ids(editor):
    call, _ = editor
    assert call("/api/rows", {"body": "x"}, token=None)[0] == 403
    assert call("/api/rows", {"body": "x"}, token="wrong")[0] == 403
    assert call("/api/song?id=../book")[0] == 404
    assert call("/api/song?id=nothing")[0] == 404
    assert save(call, id="../book")[0] == 404
    assert call("/static/..%2Fbook.yaml")[0] == 404


def test_paste_rows(editor):
    call, _ = editor
    status, result = call("/api/paste", {"text": SHEET})
    assert status == 200
    assert {"chords": [[0, "G"], [8, "D"]], "lyric": "Hello my friend"} in result["rows"]


def test_save_new_and_edit(editor):
    call, root = editor
    status, result = save(call, tags=[["fiesta", None, "Fiesta", None]])
    assert status == 200 and result["file"] == "hola_ana.md" and "Built" in result["report"]
    path = root / "songs" / "hola_ana.md"
    added = load_song(path).added
    assert added and load_song(path).tags == {"fiesta": []}
    assert "fiesta" in (root / "tags.yaml").read_text(encoding="utf-8")
    assert call("/api/book")[1]["songs"] == [{"id": "hola_ana", "title": "Hola", "autor": "Ana",
                                                  "lyrics": ["Hello my friend", "only words"]}]

    assert save(call)[0] == 409  # same title again
    status, result = save(call, id="hola_ana", title="Adiós", melody="K:D\nDE", tab="2/2 0/1")
    assert status == 200 and result["file"] == "hola_ana.md"
    song = load_song(path)
    assert song.title == "Adiós" and song.added == added and song.tab == "2/2 0/1"
    assert call("/api/song?id=hola_ana")[1]["melody"] == "K:D\nDE"

    before = path.read_text(encoding="utf-8")
    status, result = save(call, id="hola_ana", melody="K:D\nDE", tab="2/2")
    assert status == 400 and "tab" in result["error"]
    assert path.read_text(encoding="utf-8") == before
    assert not list((root / "songs").glob("*.new"))
    assert save(call, title="Adiós", force=True)[1]["file"] == "adios_ana.md"
