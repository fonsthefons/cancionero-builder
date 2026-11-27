"""Search (and slides) read every psalm's words the same with any fórmula
(semitonos de 4 joining lines included), "Sílabas" marks, chords hidden,
2 columns and bigger text; every psalm line typed into the search finds it.

Usage: .venv/bin/python tests/browser/search_check.py <book folder> [quick]
(a book with fórmulas, e.g. cancionero-liturgia, built first; quick: one fórmula per group)
"""
import json
import os
import sys
from pathlib import Path

here = Path(__file__).parent
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(here.parent.parent / "scratch" / "browsers"))

from playwright.sync_api import sync_playwright  # noqa: E402

URL = (Path(sys.argv[1]).resolve() / "index.html").as_uri()
CHROME = os.environ.get("CHROME")  # optional: a Chrome to use instead of Playwright's

# Every psalm: its words as built, from the search index and from slides.
SNAPSHOT = """() => {
  const words = (t) => searchText(t);
  const out = {};
  document.querySelectorAll('.song').forEach((song, i) => {
    if (!song.querySelector('.formula-pick')) return;
    const s = searchIndex[i];
    out[song.id] = {
      search: words(s.lyrics),
      slides: words(slideVerses(song.id).flat().map((l) => l.text).join(' ')),
      syl: song.querySelectorAll(':scope > .lyrics .syl').length,
      shared: song.querySelectorAll('.bar-shared').length,
      chorded: song.querySelectorAll(':scope > .lyrics .chord-line').length,
    };
  });
  return out;
}"""

# Every line of every psalm, typed into the search: the psalm is found, with a snippet.
LINE_SEARCH = """() => {
  const bad = [];
  let n = 0;
  document.querySelectorAll('.song').forEach((song, i) => {
    if (!song.querySelector('.formula-pick')) return;
    for (const line of searchIndex[i].lines) {
      if (searchText(line).length < 4) continue;
      n++;
      const hit = searchSongs(line).find((h) => h.song.id === song.id);
      if (!hit || (hit.snippet === '' && searchIndex[i].title.indexOf(searchText(line)) !== 0)) bad.push([song.id, line]);
      // a word cut short, as typed ("corrien")
      const w = searchText(line).split(' ').find((x) => x.length > 6);
      if (w && !searchSongs(w.slice(0, -2)).some((h) => h.song.id === song.id)) bad.push([song.id, 'prefix ' + w]);
    }
  });
  return { n, bad: bad.slice(0, 10), nbad: bad.length };
}"""

SET_ALL = """([id, extras]) => {
  document.querySelectorAll('.song').forEach((song) => {
    if (!song.querySelector('.formula-pick')) return;
    songState.set(song, 'formula', id);
    songState.set(song, 'syllables', extras ? true : null);
  });
  if (extras) {
    if (document.body.dataset.chords !== 'hide') chordsSetting.toggleGlobal();
    if (document.body.dataset.columns !== '2') columnsSetting.toggleGlobal();
    setTextScale(1.8);
  }
}"""

failures = 0
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME)
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(URL)
    base = page.evaluate(SNAPSHOT)
    ids = page.evaluate("() => BOOK.formulas.flatMap(([, items, tag]) => items.map(([id]) => [id, tag]))")
    print(len(base), "psalms,", len(ids), "fórmulas")
    todo = [(None, "none")] + ids
    if len(sys.argv) > 2:  # a quick run: the first fórmula of each group
        todo = [t for i, t in enumerate(todo) if i == 0 or t[1] != todo[i - 1][1]]
    for fid, tag in todo:
        for extras in (False, True):
            page.evaluate("() => localStorage.clear()")
            page.reload()
            page.evaluate(SET_ALL, [fid, extras])
            page.reload()
            now = page.evaluate(SNAPSHOT)
            wrong = [k for k in base if now[k]["search"] != base[k]["search"] or now[k]["slides"] != base[k]["slides"]]
            lines = page.evaluate(LINE_SEARCH)
            syl = sum(v["syl"] for v in now.values())
            shared = sum(v["shared"] for v in now.values())
            chorded = sum(1 for v in now.values() if v["chorded"])
            ok = not wrong and not lines["nbad"]
            failures += not ok
            print(f"{'OK  ' if ok else 'FAIL'} {tag:14} {fid or '-':45} extras={extras!s:5} "
                  f"chorded psalms={chorded:3} syl={syl:5} shared={shared:4} lines={lines['n']}",
                  "" if ok else json.dumps({"wrong": wrong[:5], "lines": lines["bad"]}, ensure_ascii=False))
    browser.close()
print("failures:", failures)
sys.exit(1 if failures else 0)
