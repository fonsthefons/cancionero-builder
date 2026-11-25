"""Score the rule (marks.predict, on our automatic syllables and sinalefa) against the
user's marks. A line is right when every note starts on the same text position.

Usage: rules.py <marks.json>
"""
import json
import sys

from marks import pieces, predict
from show_marks import units

# Round 1 answers: a slip (41|7|3), taste (41|2|1, 41|3|4), short-line rule chosen after
# marking (41|1|1), santuario sung as a hiatus the page could not split (62|1|0).
ACCEPTED = {"Salmo 41|7|3", "Salmo 41|2|1", "Salmo 41|3|4", "Salmo 41|1|1", "Salmo 62, 2-9|1|0"}


def auto_units(text):
    out = []
    ps = pieces(text)
    for i, p in enumerate(ps):
        if i and ps[i - 1]["join"]:
            out[-1] = (out[-1][0] + p["t"], out[-1][1] or p["stress"])
        else:
            out.append((p["t"], p["stress"]))
    return out


def main(path):
    data = json.load(open(path))
    ok = accepted = 0
    for line in data["lines"]:
        user = [n["unit"] for n in line["notes"]]
        us = auto_units(line["text"])
        got = predict([s for _, s in us], len(user))
        pre = lambda u, i: "".join(t for t, _ in u[:i]).replace(" ", "")
        hit = [pre(us, g) for g in got] == [pre(units(line), u) for u in user]
        ok += hit
        if not hit and line["key"] in ACCEPTED:
            accepted += 1
        elif not hit:
            print(f"MISS {line['key']:<20} user {user} rule {got}  {line['text']}")
    n = len(data["lines"])
    print(f"{ok}/{n} lines exact, {ok + accepted}/{n} with accepted variants")


if __name__ == "__main__":
    main(sys.argv[1])
