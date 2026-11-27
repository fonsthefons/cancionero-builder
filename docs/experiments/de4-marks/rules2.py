"""Weighted de 4 join rule, grid-searched on marks files.

cost of joining line i with i+1 = a * pause(line i) + b * (letters of both lines) / 40
                                  + c * (distance of the join from the verse's start or end)
Lowest total cost wins (ties -> earliest). Passes and the 2-lines-per-bar limit as in de4.guess.

Usage: rules2.py <de4-marks.json>...
"""
import json
import sys
from itertools import combinations, product
from pathlib import Path

from de4 import guess, pause


def plan(texts, a, b, c, d=0, e=0):
    n = len(texts)
    if n == 2:
        return [0, 3]
    k = n - 4 * (n // 4)
    short = lambda t: len(t) <= 12
    cost = lambda i: (a * pause(texts[i]) + b * (len(texts[i]) + len(texts[i + 1])) / 40 + c * min(i, n - 2 - i)
                      - d * (short(texts[i]) or short(texts[i + 1])) + e * (n >= 8 and i < 4))
    ok = [js for js in combinations(range(n - 1), k) if all(y - x > 1 for x, y in zip(js, js[1:]))]
    best = min(ok, key=lambda js: (round(sum(cost(i) for i in js), 6), js))
    out, g = [], 0
    for i in range(n):
        out.append(g % 4)
        g += i not in best
    return out


marks = {}
for f in sys.argv[1:]:
    marks |= json.loads(Path(f).read_text())["marks"]
ms = list(marks.values())
base = sum(guess(m["lines"]) == m["bars"] for m in ms)
print(f"current rule: {base}/{len(ms)}")
res = []
for a, c, d, e in product([1, 2, 5], [0.1, 0.25, 0.5], [0, 1, 3, 10], [0, 0.5, 1, 3]):
    res.append((sum(plan(m["lines"], a, 0, c, d, e) == m["bars"] for m in ms), a, c, d, e))
res.sort(reverse=True)
for r in res[:12]:
    print(r)
