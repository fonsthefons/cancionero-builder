"""Build the flexa marking page: odd-length psalm verses (semitono de 2), each with the
line the current rule (formula.js semitono2Plan) puts the flexa on, for the user to correct.

Usage: flexa.py <songs dir> -o <page.html> [--n 60] [--seed 1] [--include "<title>|<verse>"]...
                [marks.json...]  (verses in these marks files are left out)
       flexa.py --test
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "semitono-marks"))
from marks import plan2, read_md  # noqa: E402


def odd_verses(songs):
    """[(title, verse index, lines)] for every odd-length verse of salmo/cántico files, Gloria left out."""
    out = []
    for path in sorted(songs.glob("*.md")):
        if not path.name.startswith(("salmo", "cantico")):
            continue
        meta, body = read_md(path)
        for vi, v in enumerate(body.strip().split("\n\n")):
            lines = [l.strip() for l in v.splitlines() if l.strip()]
            if len(lines) % 2 and len(lines) >= 3 and not lines[0].startswith("Gloria al Padre"):
                out.append((meta["title"], vi, lines))
    return out


def build(songs, n, seed, skip, include=()):
    verses = odd_verses(songs)
    total = len(verses)
    verses = [v for v in verses if f"{v[0]}|{v[1]}" not in skip]
    random.Random(seed).shuffle(verses)
    verses.sort(key=lambda v: f"{v[0]}|{v[1]}" not in include)  # forced keys first
    picked = sorted(verses[:n], key=lambda v: (v[0], v[1]))
    items = [{"key": f"{t}|{vi}", "psalm": t, "verse": vi, "lines": lines,
              "pred": plan2(lines, True).index("flexa")}
             for t, vi, lines in picked]
    return {"id": f"flexa|seed{seed}|n{n}", "total": total, "verses": items}


def test():
    assert plan2(["a", "b,", "c."], True).index("flexa") == 0
    assert plan2(["a,", "b.", "c", "d,", "e."], True).index("flexa") == 2
    print("ok")


def main(argv):
    if argv == ["--test"]:
        return test()
    opt = lambda name, default: argv[argv.index(name) + 1] if name in argv else default
    skip = set()
    for a in argv:
        if a.endswith(".json"):
            skip |= set(json.loads(Path(a).read_text())["marks"])
    include = {argv[i + 1] for i, a in enumerate(argv) if a == "--include"}
    data = build(Path(argv[0]), int(opt("--n", 60)), int(opt("--seed", 1)), skip, include)
    out = Path(opt("-o", None))
    page = (HERE / "page.html").read_text().replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
    out.write_text(page)
    print(f"{out}: {len(data['verses'])} of {data['total']} odd verses")


if __name__ == "__main__":
    main(sys.argv[1:])
