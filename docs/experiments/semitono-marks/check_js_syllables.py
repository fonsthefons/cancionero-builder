"""Check web/js/formula.js syllableMarks (the "Sílabas" underlines) against the user's marks:
for each marked line, the syllables where the notes after the reciting note start (and how many
notes start on each) vs what formula.js marks. Lines the user accepted as variants, or where the
user re-split syllables, are skipped (as in check_js_chords.py).
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

EXP = Path(__file__).parent
SONGS = Path("/Users/fons/Documents/programs/hymn_books/cancionero-liturgia/songs")
sys.path.insert(0, str(EXP))
from check_js_chords import RUNS, first_letter  # noqa: E402
from rules import ACCEPTED  # noqa: E402

with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page()
    pg.goto(f"file://{EXP}/js_chords.html")
    total = bad = 0
    for marks_file, semitono in RUNS.items():
        abc = yaml.safe_load((SONGS / semitono).read_text().split("---")[1])["melody"]
        for line in json.loads((EXP / marks_file).read_text())["lines"]:
            if line["key"] in ACCEPTED or line["state"].get("pieces"):
                continue
            units, notes = line["units"], line["notes"]
            recto = next((i for i, n in enumerate(notes) if n["len"] >= 4), 0)
            col = lambda u: sum(len(x) for x in units[:u]) + first_letter(units[u])
            want = Counter(col(n["unit"]) for n in notes[recto + 1:])
            for u in want:
                if u == col(notes[recto]["unit"]):
                    want[u] += 1
            got = pg.evaluate("""([abc, text, bar]) => {
                const s = chordSpots(abc);
                return syllableMarks(text, bar === "flexa" ? s.flexa : s.bars[bar], true).map(([a, , n]) => [a, n]); }""",
                              [abc, line["text"], line["bar"]])
            total += 1
            if dict(map(tuple, got)) != dict(want):
                bad += 1
                print(f"DIFF {line['key']:<22} js {sorted(map(tuple, got))} user {sorted(want.items())}  {line['text']}")
    print(f"{total - bad}/{total} lines: formula.js syllable marks where the user put the notes")
    b.close()
