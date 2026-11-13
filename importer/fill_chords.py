"""Copy chords onto stanzas that have lyrics only (a repeated verse or chorus
written once with chords and again without)."""

import re
import unicodedata

from builder.lyrics import BOLD_MARK, LABEL_RE, clean_line, is_chord_line

REPEAT_MARK_RE = re.compile(r"\(?\bx\d{1,2}\)?")


def _norm(line):
    text = unicodedata.normalize("NFD", clean_line(line).casefold())
    text = REPEAT_MARK_RE.sub("", "".join(c for c in text if not unicodedata.combining(c)))
    return " ".join(re.sub(r"[^\w\s]", "", text).split())


def _stanzas(lines):
    """Runs of non-blank lines as (line indexes, bold); `**` lines and blanks split."""
    stanzas, cur, bold, cur_bold = [], [], False, False
    for i, raw in enumerate(lines):
        if raw.strip() == BOLD_MARK or not raw.strip():
            if cur:
                stanzas.append((cur, cur_bold))
            cur = []
            bold = bold != (raw.strip() == BOLD_MARK)
        else:
            if not cur:
                cur_bold = bold
            cur.append(i)
    if cur:
        stanzas.append((cur, cur_bold))
    return stanzas


def _fit(chord_line, width):
    """Pull chords that end past `width` back (keeping order, 1+ space between).
    shortcut: a lyric shorter than all its chords makes them overlap; no known case."""
    chord_line = chord_line.rstrip()
    if len(chord_line) <= width:
        return chord_line
    tokens = [(m.start(), m.group()) for m in re.finditer(r"\S+", chord_line)]
    limit, starts = width, []
    for start, text in reversed(tokens):
        start = max(0, min(start, limit - len(text)))
        starts.append(start)
        limit = start - 1
    out = ""
    for start, (_, text) in zip(reversed(starts), tokens):
        out += " " * max(start - len(out), 1 if out else 0) + text
    return out


def _nearest(candidates, n):
    earlier = [c for c in candidates if c < n]
    later = [c for c in candidates if c > n]
    return earlier[-1] if earlier else (later[0] if later else None)


def fill_chords(body):
    """Return (new_body, filled, doubts). Only chord lines are inserted."""
    lines = body.split("\n")
    info = []  # per stanza: (indexes, bold, lyric indexes, has chords)
    for idx, bold in _stanzas(lines):
        lyrics = [i for i in idx if not is_chord_line(clean_line(lines[i]))]
        info.append((idx, bold, lyrics, len(lyrics) < len(idx)))
    withchords = [n for n, s in enumerate(info) if s[3]]
    texts = {n: tuple(_norm(lines[i]) for i in info[n][2]) for n in range(len(info))}

    inserts, filled, doubts = {}, [], []
    for n, (idx, bold, lyrics, has) in enumerate(info):
        if has or len(lyrics) < 2 or any(LABEL_RE.fullmatch(clean_line(lines[i])) for i in idx):
            continue
        model = _nearest([m for m in withchords if texts[m] == texts[n]], n)
        if model is None:
            same = [m for m in withchords if info[m][1] == bold and len(info[m][2]) == len(lyrics)]
            model = _nearest(same, n)
        name = f"stanza {n + 1} ({' '.join(lines[lyrics[0]].split()[:4])}…)"
        if model is None:
            counts = sorted({len(info[m][2]) for m in withchords if info[m][2]})
            doubts.append(f"{name}: {len(lyrics)} lines, stanzas with chords have {', '.join(map(str, counts))}")
            continue
        above = {}  # model lyric index -> chord line directly above it
        for prev, cur in zip(info[model][0], info[model][0][1:]):
            if is_chord_line(clean_line(lines[prev])) and cur in info[model][2]:
                above[cur] = lines[prev]
        for mine, theirs in zip(lyrics, info[model][2]):
            if theirs in above:
                inserts[mine] = _fit(above[theirs], len(clean_line(lines[mine])))
        filled.append(f"{name} <- stanza {model + 1}")

    out = []
    for i, raw in enumerate(lines):
        if i in inserts:
            out.append(inserts[i])
        out.append(raw)
    return "\n".join(out), filled, doubts
