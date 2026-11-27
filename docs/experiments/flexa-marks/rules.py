"""Score flexa rule variants on marks files, and count how many of all odd verses each
variant moves compared with the current rule.

Usage: rules.py <liturgia songs dir> <flexa-marks.json>...
"""
import json
import sys
from pathlib import Path

from flexa import odd_verses, plan2
from marks import line_end, pause


def plan(texts, colon):
    """plan2 with ':' handled by `colon`: 'old' (as now), 'quote' (':' before a « line
    doesn't close a group), 'weak' (':' never closes a group well: pause 0, no tiebreak)."""
    alt = lambda n: [i % 2 for i in range(n)]
    best = best_score = None
    for k in range(0, len(texts) - 2, 2):
        p = [*alt(k), "flexa", *alt(len(texts) - k - 1)]
        idx = [i for i, b in enumerate(p) if b == 1]

        def pz(i):
            t = texts[i]
            if colon == "quote2":
                before = "".join(texts[: i + 1])
                if before.count("«") > before.count("»") or before.count("“") > before.count("”"):
                    return 0  # inside a quote: don't split it
                if line_end(t) == ":" and i + 1 < len(texts) and texts[i + 1].lstrip()[:1] in "«“":
                    return 0
                return pause(t)
            if line_end(t) == ":" and (colon == "weak" or (colon == "quote" and i + 1 < len(texts)
                                                           and texts[i + 1].lstrip()[:1] in "«“\"")):
                return 0
            return pause(t)
        count = lambda marks: sum((line_end(texts[i]) or "-") in marks for i in idx)
        score = (sum(pz(i) for i in idx), count(".!?"), 0 if colon == "weak" else count(":"))
        if best_score is None or score > best_score:
            best, best_score = p, score
    return best.index("flexa")


songs = Path(sys.argv[1])
marks = {}
for f in sys.argv[2:]:
    marks |= json.loads(Path(f).read_text())["marks"]
allv = odd_verses(songs)
for colon in ("old", "quote", "weak", "quote2"):
    ok = sum(plan(m["lines"], colon) == m["flexa"] for m in marks.values())
    moved = [f"{t}|{vi}" for t, vi, ls in allv if plan(ls, colon) != plan2(ls, True).index("flexa")]
    print(f"{colon}: {ok}/{len(marks)} marked; moves {len(moved)} of {len(allv)} odd verses")
    for k in moved:
        print("   ", k, "(marked)" if k in marks else "")
