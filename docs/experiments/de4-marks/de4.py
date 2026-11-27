"""Build the semitono de 4 marking page: verses that aren't 4 lines long, from songs where de 4
isn't red in the picker (no 3-line verse other than the standard Gloria), with a guessed bar
(0-3) per line for the user to correct.

Guess: 2 lines -> bars 1, 4. More than 4 lines -> 4 groups of consecutive lines, one bar each,
joined where the lines end most weakly (marks.pause); ties -> join later lines.

Usage: de4.py <songs dir> -o <page.html> [--n 60] [--seed 1] [--min-lines 2] [marks.json...]  (marked verses left out)
       de4.py --test
"""
import json
import random
import re
import sys
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "semitono-marks"))
sys.path.insert(0, str(HERE.parents[2]))
from builder.lyrics import is_chord_line  # noqa: E402
from marks import pause, read_md  # noqa: E402
GLORIA = ("gloria al padre y al hijo y al espiritu santo como era en el principio "
          "ahora y siempre por los siglos de los siglos amen")


def letters(text):
    t = text.lower().translate(str.maketrans("áéíóúü", "aeiouu"))
    return " ".join(re.findall(r"[a-zñ]+", t))


def guess(texts):
    """Port of web/js/formula.js semitono4Plan (rule 'edge' in rules.py): bar 0-3 per line."""
    n = len(texts)
    if n == 2:
        return [0, 3]
    if n < 4:
        return list(range(n))
    k = n - 4 * (n // 4)
    ok = [js for js in combinations(range(n - 1), k) if all(b - a > 1 for a, b in zip(js, js[1:]))]
    best = min(ok, key=lambda js: (sum(pause(texts[i]) for i in js), sum(min(i, n - 2 - i) for i in js), js))
    bars, b = [], 0
    for i in range(n):
        bars.append(b % 4)
        b += i not in best
    return bars


def de4_verses(songs):
    """[(title, verse index, lines)] of verses != 4 lines in songs where de 4 fits."""
    out = []
    for path in sorted(songs.glob("*.md")):
        if not path.name.startswith(("salmo", "cantico", "himno")):
            continue
        meta, body = read_md(path)
        if any(is_chord_line(l) for l in body.splitlines() if l.strip()):
            continue  # its own chords: no semitono is picked for it
        verses = [[l.strip() for l in v.splitlines() if l.strip() and l.strip() != "**"]
                  for v in body.strip().split("\n\n")]
        verses = [v for v in verses if v]
        if any(len(v) == 3 and letters(" ".join(v)) != GLORIA for v in verses):
            continue  # de 4 is red for this song
        out += [(meta["title"], vi, v) for vi, v in enumerate(verses) if len(v) not in (1, 3, 4)]
    return out


def build(songs, n, seed, skip, min_lines=2):
    verses = de4_verses(songs)
    total = len(verses)
    verses = [v for v in verses if f"{v[0]}|{v[1]}" not in skip and len(v[2]) >= min_lines]
    random.Random(seed).shuffle(verses)
    picked = sorted(verses[:n], key=lambda v: (v[0], v[1]))
    items = [{"key": f"{t}|{vi}", "psalm": t, "verse": vi, "lines": ls, "pred": guess(ls)} for t, vi, ls in picked]
    return {"id": f"de4|seed{seed}|n{n}", "total": total, "verses": items}


def test():
    assert guess(["a,", "b."]) == [0, 3]
    ex = ["En el lecho me acuerdo de ti", "y velando medito en ti,", "porque fuiste mi auxilio,",
          "y a la sombra de tus alas canto con júbilo;", "mi alma está unida a ti,", "y tu diestra me sostiene."]
    assert guess(ex) == [0, 0, 1, 2, 3, 3], guess(ex)
    assert guess(["a,", "b;", "c", "d,", "e."]) == [0, 1, 2, 2, 3]
    assert guess(list("abcdefgh")) == [0, 1, 2, 3, 0, 1, 2, 3]  # 8 lines: two passes
    assert guess(["a", "b,", "c,", "d", "e", "f", "g", "h,", "i."]) == [0, 0, 1, 2, 3, 0, 1, 2, 3]
    assert letters("Gloria al Padre, y al Hijo, y al Espíritu Santo.\nComo era en el principio, "
                   "ahora y siempre,\npor los siglos de los siglos. Amén.") == GLORIA
    print("ok")


def main(argv):
    if argv == ["--test"]:
        return test()
    opt = lambda name, default: argv[argv.index(name) + 1] if name in argv else default
    skip = set()
    for a in argv:
        if a.endswith(".json"):
            skip |= set(json.loads(Path(a).read_text())["marks"])
    data = build(Path(argv[0]), int(opt("--n", 60)), int(opt("--seed", 1)), skip, int(opt("--min-lines", 2)))
    out = Path(opt("-o", None))
    out.write_text((HERE / "page.html").read_text().replace("/*DATA*/null", json.dumps(data, ensure_ascii=False)))
    print(f"{out}: {len(data['verses'])} of {data['total']} verses")


if __name__ == "__main__":
    main(sys.argv[1:])
