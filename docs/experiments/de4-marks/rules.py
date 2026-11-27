"""Score de 4 bar-rule variants on marks files.

Every variant: passes = max(1, n // 4) runs of bars 1-4; n - 4*passes joins (a bar over two
consecutive lines), at most 2 lines per bar. Variants differ in which joins win.

Usage: rules.py <de4-marks.json>...
"""
import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

from de4 import pause


def bars_for(n, joins):
    out, g = [], 0
    for i in range(n):
        out.append(g % 4)
        g += i not in joins
    return out


def plan(texts, variant):
    n = len(texts)
    if n == 2:
        return [0, 3]
    if n < 4:
        return list(range(n))
    groups = 4 * max(1, n // 4)
    k = n - groups

    def key(js):
        p = sum(pause(texts[i]) for i in js)
        bars = bars_for(n, set(js))
        # the line ending bar 2 (in the first pass): the verse's middle when it ends strongly
        mid = -pause(texts[bars.index(2) - 1])
        if variant == "half":
            return (p, mid, sum(min(i, n - 2 - i) for i in js), sorted(js))
        if variant == "half-first":
            return (mid, p, sum(min(i, n - 2 - i) for i in js), sorted(js))
        edge = sum(min(i, n - 2 - i) for i in js)
        long = sum(len(texts[i]) + len(texts[i + 1]) > 60 for i in js)
        return {"late": (p, [-i for i in sorted(js, reverse=True)]),
                "early": (p, sorted(js)),
                "edge": (p, edge, sorted(js)),
                "long-edge": (long, p, edge, sorted(js)),
                "edge-long": (p, long, edge, sorted(js))}[variant]
    ok = [js for js in combinations(range(n - 1), k) if all(b - a > 1 for a, b in zip(js, js[1:]))]
    return bars_for(n, set(min(ok, key=key)))


marks = {}
for f in sys.argv[1:]:
    marks |= json.loads(Path(f).read_text())["marks"]
for v in ("late", "edge", "half", "half-first"):
    miss = [k for k, m in marks.items() if plan(m["lines"], v) != m["bars"]]
    sizes = Counter(len(marks[k]["lines"]) for k in miss)
    print(f"{v}: {len(marks) - len(miss)}/{len(marks)}; misses by size {dict(sizes)}")
    for k in miss:
        print("     ", k, [b + 1 for b in plan(marks[k]["lines"], v)], "user", [b + 1 for b in marks[k]["bars"]])
