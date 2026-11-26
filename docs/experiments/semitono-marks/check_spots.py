"""For every semitono in cancionero-liturgia: do the melody's chords (formula.js chordSpots)
match the chord line's chords, bar by bar? Prints the ones that fall back, and the spots."""
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

REPO = Path("/Users/fons/Documents/programs/cancionero-builder")
SONGS = Path("/Users/fons/Documents/programs/hymn_books/cancionero-liturgia/songs")

with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page()
    pg.goto(f"file://{REPO}/docs/experiments/semitono-marks/js_chords.html")
    ok = 0
    files = sorted(SONGS.glob("semitonos_de_*.md"))
    for f in files:
        _, front, body = f.read_text().split("---", 2)
        abc = yaml.safe_load(front)["melody"]
        lines = [l for l in body.strip().splitlines() if l.strip()]
        bars = [bar.split() for bar in lines[0].split("|")]
        flexa = next((l.split(":", 1)[1].split() for l in lines[1:] if l.lower().startswith("flexa")), None)
        groups = lambda names: " ".join(names).replace(" (", "\0(").split(" ")  # noqa: E731
        res = pg.evaluate("abc => chordSpots(abc)", abc)
        miss = [i for i, bar in enumerate(bars) if i >= len(res["bars"]) or len(res["bars"][i]) != len(groups(bar))]
        if flexa and (not res["flexa"] or len(res["flexa"]) != len(groups(flexa))):
            miss.append("flexa")
        short = lambda s: " ".join(f"{x['from'][0]}{x['k']}" for x in s)  # noqa: E731
        print(f"{'OK  ' if not miss else 'FALL'} {f.stem:<45} {' | '.join(short(s) for s in res['bars'])}"
              + (f" || {short(res['flexa'])}" if res["flexa"] else "") + (f"   fallback: {miss}" if miss else ""))
        ok += not miss
    print(f"{ok}/{len(files)} semitonos use the melody")
    b.close()
