"""web/js/formula.js semitono4Plan against the Python port (de4.guess) on every de 4 verse,
and against the user's marks.

Usage: check_js.py <liturgia songs dir> <de4-marks.json>...
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from de4 import de4_verses, guess

EXP = Path(__file__).parent.parent / "semitono-marks"
verses = [v for v in de4_verses(Path(sys.argv[1]))]
marks = {}
for f in sys.argv[2:]:
    marks |= json.loads(Path(f).read_text())["marks"]

with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page()
    pg.goto(f"file://{EXP}/js_chords.html")
    js = pg.evaluate("(vs) => vs.map((ls) => semitono4Plan(ls))", [v[2] for v in verses])
    b.close()

diff = [f"{t}|{vi}" for (t, vi, ls), j in zip(verses, js) if guess(ls) != j]
print(f"JS = Python on {len(verses) - len(diff)}/{len(verses)} de 4 verses", diff or "")
got = dict(zip((f"{t}|{vi}" for t, vi, _ in verses), js))
ok = sum(got[k] == m["bars"] for k, m in marks.items())
print(f"JS = user on {ok}/{len(marks)} marked verses")
