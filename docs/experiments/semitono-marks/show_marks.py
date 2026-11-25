"""Print the user's marks compactly: each unit (sung syllable), STRESSED in capitals,
[X] before the unit where note X starts, {C} where a chord was moved by hand.
Then each note's position counted from the line's end (-1 = last syllable) and the
position of the last stressed syllable.

Usage: show_marks.py <marks.json>
"""
import json
import sys

from marks import pieces


def units(line):
    """[(text, stressed)] of the sung units, joins as the user left them."""
    ps = pieces(line["text"])
    if line["state"].get("pieces"):  # the user split a syllable in two (stress: display only)
        ps = [{"t": t, "stress": False} for t in line["state"]["pieces"]]
    joins = line["state"]["joins"]
    out = []
    for i, p in enumerate(ps):
        if i > 0 and joins[i - 1]:
            t, s = out[-1]
            out[-1] = (t + p["t"], s or p["stress"])
        else:
            out.append((p["t"], p["stress"]))
    assert [t for t, _ in out] == line["units"], (out, line["units"])
    return out


def main(path):
    data = json.load(open(path))
    for line in data["lines"]:
        us = units(line)
        n = len(us)
        starts = {}
        for note in line["notes"]:
            if note["unit"] is not None:
                starts.setdefault(note["unit"], []).append(note["pitch"])
        moved = {c["unit"]: c["chord"] for c in line["chords"] if c["moved"]}
        text = ""
        for i, (t, s) in enumerate(us):
            text += "".join(f"[{p}]" for p in starts.get(i, [])) + "".join(f"{{{moved[i]}}}" for _ in [0] if i in moved)
            text += t.upper() if s else t.lower()
        accent = max((i for i, (_, s) in enumerate(us) if s), default=None)
        rel = " ".join(f"{nt['pitch']}{nt['unit'] - n if nt['unit'] is not None else '?'}" for nt in line["notes"][1:])
        acc = accent - n if accent is not None else "?"
        print(f"{line['key']:<22} {str(line['bar']):<5} acc{acc:<3} {rel:<16} {text.strip()}"
              + (f"   # {line['comment']}" if line.get("comment") else ""))


if __name__ == "__main__":
    main(sys.argv[1])
