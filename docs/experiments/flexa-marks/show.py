"""Print the verses where the user's flexa differs from the rule's, or has a note.

Usage: show.py <flexa-marks.json>
"""
import json
import sys
from pathlib import Path

marks = json.loads(Path(sys.argv[1]).read_text())["marks"]
bad = 0
for key, m in marks.items():
    if m["flexa"] == m["pred"] and not m["comment"]:
        continue
    bad += m["flexa"] != m["pred"]
    print(f"\n{key}  rule={m['pred']} user={m['flexa']}  {m['comment']}")
    for i, t in enumerate(m["lines"]):
        tag = ("U" if i == m["flexa"] else " ") + ("R" if i == m["pred"] else " ")
        print(f"  {tag} {i} {t}")
print(f"\n{len(marks) - bad}/{len(marks)} match")
