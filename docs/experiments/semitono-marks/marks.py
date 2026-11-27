"""Build the semitono marking page: psalm lines split into syllables, with the bar
(1, 2 or flexa) each line is sung to.

Usage: marks.py <semitono.md> <psalm.md>... -o <page.html> [--pred]
  --pred: lines start filled in by the rule (predict), for the user to correct.
       marks.py --test
"""
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).parent
VOWELS = set("aeiouáéíóúü")
STRONG = set("aeoáéóíú")  # accented í/ú break a diphthong like a, e, o do
ONSETS = {"bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "kl", "kr", "pl", "pr", "tr",
          "ch", "ll", "rr", "qu", "gu"}
HARD_STOP = set(".;:?!«»\"“”()")  # no sinalefa across these


def kinds(word):
    """'v' or 'c' per letter of a lowercase word."""
    out = []
    for i, ch in enumerate(word):
        nxt = word[i + 1] if i + 1 < len(word) else ""
        if ch == "y":
            out.append("v" if not nxt or nxt not in VOWELS else "c")
        elif ch == "u" and i > 0 and word[i - 1] in "qg" and nxt in ("e", "i", "é", "í"):
            out.append("c")  # silent u: que, guerra
        else:
            out.append("v" if ch in VOWELS else "c")
    return out


def syllabify(word):
    """Spanish orthographic syllables of one word, original case kept."""
    low = word.lower()
    k = kinds(low)
    nuclei = []  # [start, end) of each vowel group, split at hiatus
    i = 0
    while i < len(low):
        if k[i] != "v":
            i += 1
            continue
        start = i
        while i + 1 < len(low) and k[i + 1] == "v" and not (low[i] in STRONG and low[i + 1] in STRONG):
            i += 1
        nuclei.append([start, i + 1])
        i += 1
    if len(nuclei) < 2:
        return [word]
    cuts = []
    for (_, end), (nxt, _) in zip(nuclei, nuclei[1:]):
        cons = low[end:nxt]
        if len(cons) <= 1:
            cuts.append(end)
        elif cons[-2:] in ONSETS:
            cuts.append(nxt - 2)
        else:
            cuts.append(nxt - 1)
    bounds = [0, *cuts, len(word)]
    return [word[a:b] for a, b in zip(bounds, bounds[1:])]


ATONIC = set("el la los las lo le les de del a al y e o u ni en con por para sin que se me te nos os "
             "mi mis tu tus su sus un una unos unas pero si cuando como donde mientras hacia desde "
             "entre hasta según tan es".split())


def stress(word):
    """Index of the stressed syllable of a word, or None for an atonic word."""
    sylls = syllabify(word)
    if word.lower() in ATONIC:
        return None
    for i, s in enumerate(sylls):
        if set(s.lower()) & set("áéíóú"):
            return i
    if len(sylls) == 1:
        return 0
    return len(sylls) - 2 if word.lower()[-1] in "aeiouns" else len(sylls) - 1


def pieces(line):
    """The line as syllable pieces [{t, join}], join = sung together with the next
    piece (sinalefa). Punctuation and spaces stay on the piece before them; leading
    punctuation goes on the first piece of the next word."""
    out = []
    lead = ""
    for tok in re.findall(r"\w+|\W+", line):
        if not re.match(r"\w", tok):
            cut = next((i for i, ch in enumerate(tok) if ch in "¿¡«“("), len(tok))
            if out:
                out[-1]["t"] += tok[:cut]
            else:
                lead += tok[:cut]
            lead += tok[cut:]
            continue
        if out:
            prev = out[-1]["t"]
            core = re.sub(r"\W+$", "", prev)
            trail = prev[len(core):] + lead
            w = tok.lower()[1:] if tok.lower().startswith("h") else tok.lower()
            # no sinalefa onto or from a stressed vowel (user's marks, round 1)
            out[-1]["join"] = (" " in trail and not set(trail) & HARD_STOP
                               and not out[-1]["stress"] and stress(tok) != 0
                               and core[-1:].lower() in VOWELS | {"y"}
                               and (w[:1] in VOWELS or w == "y"))
        sylls = syllabify(tok)
        sylls[0] = lead + sylls[0]
        lead = ""
        st = stress(tok)
        out.extend({"t": s, "join": False, "stress": i == st} for i, s in enumerate(sylls))
    if lead and out:
        out[-1]["t"] += lead
    return out


def predict(stressed, n_notes):
    """Rule v2: unit where each note starts, from the units' stress flags. Last note on
    the last stressed unit, passing notes one per unit just before it, reciting note
    from unit 0 (sharing it with a passing note on short lines)."""
    accent = max((i for i, s in enumerate(stressed) if s), default=len(stressed) - 1)
    return [0] + [max(accent - k, 0) for k in range(n_notes - 2, 0, -1)] + [accent][: n_notes - 1]


def predict_state(ps, bar, n_notes):
    """The page's state for a line, filled in by the rule."""
    joins = [p["join"] for p in ps]
    firsts = [i for i in range(len(ps)) if i == 0 or not joins[i - 1]]
    stressed = [any(p["stress"] for p in ps[a:b]) for a, b in zip(firsts, firsts[1:] + [len(ps)])]
    notes = [firsts[u] for u in predict(stressed, n_notes)]
    return {"bar": bar, "joins": joins, "notes": notes, "chords": [None] * n_notes, "comment": ""}


def parse_bar(text):
    """Notes of one ABC bar: [{pitch, len, chord}]."""
    return [{"chord": c or None, "pitch": p, "len": int(n) if n else 1}
            for c, p, n in re.findall(r'(?:"([^"]+)")?([=^_]?[A-Ga-g][,\']*)(\d*)', text)]


def melody(meta):
    body = "\n".join(l for l in meta["melody"].splitlines() if not re.match(r"^[A-Z]:", l))
    main, _, flexa = body.partition("||")
    return {"bars": [parse_bar(b) for b in main.split("|") if b.strip()],
            "flexa": parse_bar(flexa) if flexa.strip() else None}


def line_end(text):
    return re.sub(r"[\s»”\"’')\]]+$", "", text)[-1:]


def pause(text):
    end = line_end(text)
    return 2 if end and end in ".;:?!" else 1 if end == "," else 0


def plan2(texts, has_flexa):
    """Port of web/js/formula.js semitono2Plan: bar per line (0, 1, 'flexa') or None."""
    alt = lambda n: [i % 2 for i in range(n)]
    if len(texts) % 2 == 0:
        return alt(len(texts))
    if len(texts) < 3 or not has_flexa:
        return None

    def no_split(i):  # inside an open quote, or ":" right before one (flexa marks round 1)
        up_to = "".join(texts[: i + 1])
        nxt = texts[i + 1].lstrip()[:1] if i + 1 < len(texts) else ""
        return (up_to.count("«") > up_to.count("»") or up_to.count("“") > up_to.count("”")
                or (line_end(texts[i]) == ":" and nxt in ("«", "“")))
    pauses = [0 if no_split(i) else pause(t) for i, t in enumerate(texts)]
    best = best_score = None
    for k in range(0, len(texts) - 2, 2):
        plan = [*alt(k), "flexa", *alt(len(texts) - k - 1)]
        ends = [t for t, p in zip(texts, plan) if p == 1]
        count = lambda marks: sum((line_end(t) or "-") in marks for t in ends)
        score = (sum(p for p, b in zip(pauses, plan) if b == 1), count(".!?"), count(":"))
        if best_score is None or score > best_score:
            best, best_score = plan, score
    return best


def read_md(path):
    text = Path(path).read_text()
    _, front, body = text.split("---", 2)
    return yaml.safe_load(front), body


def build(semitono, psalms, pred=None):
    meta, _ = read_md(semitono)
    mel = melody(meta)
    lines = []
    for path in psalms:
        pmeta, body = read_md(path)
        verses = [v.splitlines() for v in body.strip().split("\n\n")]
        for vi, verse in enumerate(verses):
            plan = plan2(verse, mel["flexa"] is not None) or [0] * len(verse)
            for li, text in enumerate(verse):
                key = f"{pmeta['title']}|{vi}|{li}"
                ps = pieces(text)
                bar = plan[li]
                n = len(mel["flexa"] if bar == "flexa" else mel["bars"][bar])
                lines.append({"key": key, "psalm": pmeta["title"], "verse": vi, "line": li,
                              "text": text, "bar": bar, "pieces": ps,
                              "pred": predict_state(ps, bar, n) if pred else None})
    return {"id": f"{meta['title']}|{'|'.join(Path(p).stem for p in psalms)}",
            "semitono": meta["title"], "melody": mel, "lines": lines}


def test():
    assert syllabify("corrientes") == ["co", "rrien", "tes"], syllabify("corrientes")
    assert syllabify("Espíritu") == ["Es", "pí", "ri", "tu"]
    assert syllabify("alegría") == ["a", "le", "grí", "a"]
    assert syllabify("aclamaciones") == ["a", "cla", "ma", "cio", "nes"]
    assert syllabify("construir") == ["cons", "truir"]
    assert syllabify("que") == ["que"] and syllabify("guerra") == ["gue", "rra"]
    assert syllabify("rey") == ["rey"] and syllabify("muchacho") == ["mu", "cha", "cho"]
    p = pieces("Como busca la cierva")
    assert [x["t"] for x in p] == ["Co", "mo ", "bus", "ca ", "la ", "cier", "va"], p
    assert not any(x["join"] for x in p)
    p = pieces("corrientes de agua,")
    assert [x["t"] for x in p] == ["co", "rrien", "tes ", "de ", "a", "gua,"] and not p[3]["join"]
    assert pieces("se acongoja")[0]["join"]  # neither vowel stressed: sinalefa
    p = pieces("¿cuándo entraré a ver")
    assert p[0]["t"] == "¿cuán" and p[1]["join"] and not p[4]["join"], p  # entraré|a
    assert not pieces("Dios. Amén")[0]["join"]
    assert predict([False, True, False, False, True, False], 4) == [0, 2, 3, 4]  # llana
    assert predict([False, False, True, False], 4) == [0, 0, 1, 2]  # te re-CUER-do
    assert predict([True, False], 2) == [0, 0]  # flexa on a short line
    assert plan2(["a,", "b.", "c,", "d."], True) == [0, 1, 0, 1]
    assert plan2(["a", "b,", "c."], True) == ["flexa", 0, 1]
    # flexa marks round 1: a quote isn't split (Is 12, Salmo 117)
    assert plan2(["a;", "b;", "c:", "«d", "e!»."], True).index("flexa") == 2
    assert plan2(["a:", "b:", "«c,", "d,", "e.»"], True).index("flexa") == 2
    assert parse_bar('"D"F4 G A "G"B2') == [
        {"chord": "D", "pitch": "F", "len": 4}, {"chord": None, "pitch": "G", "len": 1},
        {"chord": None, "pitch": "A", "len": 1}, {"chord": "G", "pitch": "B", "len": 2}]
    print("ok")


def main(argv):
    if argv == ["--test"]:
        return test()
    out = Path(argv[argv.index("-o") + 1])
    files = [a for a in argv if a.endswith(".md")]
    data = build(files[0], files[1:], pred="--pred" in argv)
    page = (HERE / "page.html").read_text().replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
    out.write_text(page)
    print(f"{out}: {len(data['lines'])} lines")


if __name__ == "__main__":
    main(sys.argv[1:])
