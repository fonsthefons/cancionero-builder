"""Check web/js/formula.js chord placement against the user's marks (semitono experiment).

For each marked line: the columns where formula.js writes the bar's chords vs the columns of
the syllables the user put each chord on. Lines the user accepted as variants are skipped.
"""
import json
import re
import sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

REPO = Path("/Users/fons/Documents/programs/cancionero-builder")
EXP = REPO / "docs/experiments/semitono-marks"
SONGS = Path("/Users/fons/Documents/programs/hymn_books/cancionero-liturgia/songs")
sys.path.insert(0, str(EXP))
from rules import ACCEPTED  # noqa: E402

RUNS = {"alegre5-round1-marks.json": "semitonos_de_2-11-alegre_5.md",
        "alegre5-round2-marks.json": "semitonos_de_2-11-alegre_5.md",
        "narrativo-breve-round3-marks.json": "semitonos_de_2-05-narrativo_breve.md"}


def first_letter(text):
    return max(0, re.search(r"\w", text).start()) if re.search(r"\w", text) else 0


with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page()
    pg.goto(f"file://{EXP}/js_chords.html")
    total = bad = 0
    for marks_file, semitono in RUNS.items():
        abc = yaml.safe_load((SONGS / semitono).read_text().split("---")[1])["melody"]
        data = json.loads((EXP / marks_file).read_text())
        for line in data["lines"]:
            if line["key"] in ACCEPTED or line["state"].get("pieces"):
                continue
            bar = line["bar"]
            names = [c["chord"] for c in line["chords"]]
            got = pg.evaluate("""([abc, text, bar, names]) => {
                const s = chordSpots(abc);
                const line = chordLineText(text, names, bar === "flexa" ? s.flexa : s.bars[bar]);
                return [...line.matchAll(/\\S+/g)].map((m) => m.index); }""", [abc, line["text"], bar, names])
            units = line["units"]
            want = [sum(len(u) for u in units[:c["unit"]]) + first_letter(units[c["unit"]]) for c in line["chords"]]
            total += 1
            if got != want:
                bad += 1
                print(f"DIFF {line['key']:<22} js {got} user {want}  {line['text']}")
    print(f"{total - bad}/{total} lines: formula.js chords where the user put them")
    b.close()
