"""Check of the song editor page (web/editor/) in Chromium, on a copy of a scratch book:
pasted lyrics get empty chord lines, a chord is added by clicking and moved by dragging,
and saving writes it at its column; saving an existing song unchanged keeps its body;
a melody note dragged on the staff or deleted changes the ABC text, the tab is suggested
per note, and both are saved; a tab without a melody or with another note count is saved unchanged.

Usage: .venv/bin/python tests/browser/editor_check.py   (prints OK; browsers: scratch/browsers)
"""
import os
import re
import shutil
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / "scratch" / "browsers"))
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from builder.book import load_book  # noqa: E402
from builder.songs import load_song  # noqa: E402
from importer.editor import make_server  # noqa: E402
from importer.songfile import write_song  # noqa: E402

BODY = "G       D\nHello my friend\n\nEm\nsecond line\n"

root = ROOT / "scratch" / "editor_check"
shutil.rmtree(root, ignore_errors=True)
(root / "songs").mkdir(parents=True)
(root / "book.yaml").write_text("title: T\nrecord_added: true\n", encoding="utf-8")
book = load_book(root)
existing = write_song(book, "Existing", "Ana", None, "", {}, BODY)
before = load_song(existing).body
# tabs that don't fit the notes: saved unchanged
odd_tabs = [write_song(book, "Tab only", "Ana", None, "", {}, BODY, tab="0/1 |  2/1", ignore=["tab-melody-check"]),
            write_song(book, "Short tab", "Ana", None, "", {}, BODY, melody="K:C\nC D E", tab="0/1 | 2/1",
                       ignore=["tab-melody-check"])]

server = make_server(book)
threading.Thread(target=server.serve_forever, daemon=True).start()
problems = []


def check(label, ok):
    if not ok:
        problems.append(label)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(f"http://127.0.0.1:{server.server_port}/")
    page.wait_for_function("document.querySelectorAll('#picker option').length > 1")

    # paste lyrics only: every lyric has an empty chord line above it
    page.click("[data-src=paste]")
    page.fill("#paste-text", "Hello world\nSecond line")
    page.click("#paste-go")
    page.wait_for_selector("#grid .lyric")
    check("chord line per lyric", page.locator("#grid .chords").count() == page.locator("#grid .lyric").count() >= 2)

    # click at column 5 on the first chord line, type G
    cw = page.evaluate("(() => { const s = document.createElement('span'); s.textContent = '0'.repeat(20);"
                       "s.style.cssText = 'position:absolute;white-space:pre'; document.querySelector('#grid').append(s);"
                       "const w = s.getBoundingClientRect().width / 20; s.remove(); return w; })()")
    line = page.locator("#grid .chords").first
    line.click(position={"x": 5.5 * cw, "y": 8})
    page.keyboard.type("G")
    page.keyboard.press("Enter")
    chord = page.locator("#grid .chord").first
    check("chord at col 5", chord.evaluate("e => e.style.left") == "5ch")

    # drag it three columns right
    box = chord.bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 3 * cw, y, steps=6)
    page.mouse.up()
    check("chord at col 8", page.locator("#grid .chord").first.evaluate("e => e.style.left") == "8ch")

    # lyrics are typed into in place
    second = page.locator("#grid .lyric").nth(1)
    second.click()
    page.keyboard.press("End")
    page.keyboard.type(" edited")

    page.fill("#title", "Brand new")
    page.click("#save")
    page.wait_for_function("document.querySelector('#status').textContent.startsWith('Saved')")
    saved = [f for f in (root / "songs").glob("*.md") if f != existing and f not in odd_tabs]
    check("new song file", len(saved) == 1)
    if saved:
        lines = load_song(saved[0]).body.split("\n")
        check("chord line is 8 spaces + G", lines[lines.index("Hello world") - 1] == " " * 8 + "G")
        check("edited lyric saved", "Second line edited" in lines)

    # an existing song saved unchanged keeps its body
    page.select_option("#picker", existing.stem)
    page.wait_for_function("document.querySelector('#title').value == 'Existing'")
    page.click("#save")
    page.wait_for_function("document.querySelector('#status').textContent.startsWith('Saved')")
    check("existing body unchanged", load_song(existing).body == before)

    # melody: drag the 2nd note up one staff step, delete a note, suggested tab, save
    page.check("#has-melody")
    page.fill("#abc", "K:G\nG A B")
    page.wait_for_function("document.querySelectorAll('#melody-staff .abcjs-note').length == 3")

    def press_note(index, dy):  # abcjs' svg takes the pointer events, not the note: use the mouse
        box = page.locator("#melody-staff .abcjs-note").nth(index).bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        if dy:
            page.mouse.move(x, y + dy, steps=4)
        page.mouse.up()

    press_note(1, -4)  # one staff step is 3 px at scale 1
    check("drag up one step", page.input_value("#abc") == "K:G\nG B B")
    press_note(2, 0)
    page.click("[data-note=delete]")
    check("note deleted", page.input_value("#abc") == "K:G\nG B")
    page.check("#has-tab")
    tab = [page.locator("#tab-inputs input").nth(i).input_value() for i in range(page.locator("#tab-inputs input").count())]
    check("tab token per note", len(tab) == 2 and all(re.fullmatch(r"\d{1,2}/[1-6]", t) for t in tab))
    check("no tab error", page.text_content("#tab-error") == "")
    page.locator("#tab-inputs input").first.fill("")
    check("tab count error", page.text_content("#tab-error") == "tab has 1 notes but melody has 2")
    page.locator("#tab-inputs input").first.fill(tab[0])
    check("book look drawn", page.locator("#melody-look .melody-tab").count() == 1)
    page.click("#save")
    page.wait_for_function("document.querySelector('#status').textContent.startsWith('Saved')")
    saved_song = load_song(existing)
    check("melody saved", (saved_song.melody or "").strip() == "K:G\nG B")
    check("tab saved", saved_song.tab == " ".join(tab))

    for path in odd_tabs:
        loaded = load_song(path).tab
        page.select_option("#picker", path.stem)
        page.wait_for_function(f"document.querySelector('#title').value == {load_song(path).title!r}")
        page.click("#save")
        page.wait_for_function("document.querySelector('#status').textContent.startsWith('Saved')")
        check(f"{path.stem}: tab unchanged", load_song(path).tab == loaded)
    check("no page errors", not errors)
    browser.close()

server.shutdown()
server.server_close()
if problems or errors:
    print("FAIL:", problems, errors)
    sys.exit(1)
print("OK")
