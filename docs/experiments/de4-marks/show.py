"""Print the verses where the user's de 4 bars differ from the guess, or have a note.

Usage: show.py <de4-marks.json>
"""
import json
import sys
from collections import Counter
from pathlib import Path

marks = json.loads(Path(sys.argv[1]).read_text())["marks"]
bad, by_size = 0, Counter()
for key, m in marks.items():
    by_size[len(m["lines"]), m["bars"] == m["pred"]] += 1
    if m["bars"] == m["pred"] and not m["comment"]:
        continue
    bad += m["bars"] != m["pred"]
    print(f"\n{key}  {m['comment']}")
    for t, p, u in zip(m["lines"], m["pred"], m["bars"]):
        print(f"  guess {p + 1} user {u + 1}{'  <' if p != u else ''}  {t}")
print(f"\n{len(marks) - bad}/{len(marks)} match; (lines, match): {sorted(by_size.items())}")
