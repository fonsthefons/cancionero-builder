"""Online chord sheets as a second opinion for fill_chords.

fetch_online downloads (and caches) up to two online versions of a song;
guide uses them, offline, to check and extend what fill_chords did. Our song
always wins: online chords only say which of our stanzas a bare stanza copies,
or (moved to our key and spelled as ours) which of our chords go above which word.
"""

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from builder.lyrics import CHORD_RE, LABEL_RE, clean_line, is_chord_line

from .clean import clean_song
from .fill_chords import _fit, _norm, _stanzas, fill_chords
from .read import read_song_any_way
from .search import search

MAX_VERSIONS = 2
MIN_RATIO = 0.6  # lyric likeness to pair two stanzas; chord agreement to trust a version or a model
PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
PARTS_RE = re.compile(r"([A-G][#b]?)([^/]*)(?:/([A-G][#b]?))?")


def fetch_online(title, artist, cache_dir, stem):
    """[(url, chord-over-lyric text)] of up to 2 online versions, cached as
    cache_dir/<stem>-<n>.txt (url on line 1). Never raises for network or site errors."""
    cache_dir = Path(cache_dir)
    cached = sorted(cache_dir.glob(f"{stem}-[0-9].txt"))
    if cached:
        return [tuple(path.read_text(encoding="utf-8").split("\n", 1)) for path in cached]
    try:
        results = search(title, artist)
    except Exception:  # any search failure just means no versions
        return []
    versions = []
    for result in results:
        try:
            draft = read_song_any_way(result.url)
            text = clean_song(draft.text, marked=draft.marked).body
        except Exception:  # a page that can't be read is skipped
            continue
        if any(is_chord_line(clean_line(line)) for line in text.split("\n")):
            versions.append((draft.url or result.url, text))
        if len(versions) == MAX_VERSIONS:
            break
    cache_dir.mkdir(parents=True, exist_ok=True)
    for n, (url, text) in enumerate(versions, 1):
        (cache_dir / f"{stem}-{n}.txt").write_text(f"{url}\n{text}", encoding="utf-8")
    return versions


@dataclass
class Stanza:
    lyrics: list  # lyric line indexes (every line that isn't a chord line)
    above: dict  # lyric line index -> the chord line right above it
    chords: list  # chord names, in order
    words: list  # (line index, start, end, normalized word) of the lyrics
    text: tuple  # normalized lyric lines (fill_chords' "same lyrics" test)
    label: bool  # has an "Intro:"-like line


def _parse(lines):
    out = []
    for idx, _ in _stanzas(lines):
        chordy = {i for i in idx if is_chord_line(clean_line(lines[i]))}
        lyrics = [i for i in idx if i not in chordy]
        out.append(Stanza(
            lyrics=lyrics,
            above={cur: lines[prev] for prev, cur in zip(idx, idx[1:]) if prev in chordy and cur not in chordy},
            chords=[c for i in idx if i in chordy for c in CHORD_RE.findall(clean_line(lines[i]))],
            words=[(i, m.start(), m.end(), w) for i in lyrics
                   for m in re.finditer(r"\S+", clean_line(lines[i])) if (w := _norm(m.group()))],
            text=tuple(_norm(lines[i]) for i in lyrics),
            label=any(LABEL_RE.fullmatch(clean_line(lines[i])) for i in idx),
        ))
    return out


def _key(chord, shift=0, core=False):
    """Chord as pitch classes moved `shift` semitones, so enharmonic spellings
    compare equal; `core` keeps only root and minor (D7 ~ D, G/F# ~ G)."""
    root, suffix, bass = PARTS_RE.match(chord).groups()
    pitch = lambda note: (PITCH[note[0]] + note.count("#") - note.count("b") + shift) % 12  # noqa: E731
    if core:
        return pitch(root), suffix.startswith("m") and not suffix.startswith("maj")
    return pitch(root), suffix, bass and pitch(bass)


def _cores(chords, shift=0):
    return [_key(c, shift, core=True) for c in chords]


def _matcher(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False)


def _words(stanza):
    return [w for *_, w in stanza.words]


def _pair(mine, theirs):
    """Index of the online stanza with chords whose lyrics are most like ours, or None."""
    scored = [(_matcher(_words(mine), _words(other)).ratio(), -k) for k, other in enumerate(theirs)
              if other.chords and other.words and not other.label]
    ratio, k = max(scored, default=(0, 0))  # ties: the first one
    return -k if ratio >= MIN_RATIO else None


def _shift(ours, theirs, pairs):
    """(semitones that bring the online chords to our key, how well they then agree)."""
    matched = [(ours[n].chords, theirs[k].chords) for n, k in pairs.items() if ours[n].chords]

    def agreement(shift):
        hits = total = 0
        for mine, online in matched:
            a, b = _cores(mine), _cores(online, shift)
            hits += 2 * sum(block.size for block in _matcher(a, b).get_matching_blocks())
            total += len(a) + len(b)
        return hits / total if total else 0

    best = max(range(12), key=agreement)
    return best, agreement(best)


def _copy(lines, ours, n, m):
    """fill_chords' copy: the chord line above each of stanza m's lyric lines, fitted to n's."""
    return {mine: _fit(ours[m].above[theirs], len(clean_line(lines[mine])))
            for mine, theirs in zip(ours[n].lyrics, ours[m].lyrics) if theirs in ours[m].above}


def _place(lines, mine, theirs, shift, spelling):
    """({our lyric index: chord line}, None) with the online stanza's chords,
    moved to our key and spelled as ours, above the word our lyrics share with
    the online ones; or (None, problem)."""
    blocks = _matcher(_words(mine), _words(theirs)).get_matching_blocks()
    to_ours = {j + d: i + d for i, j, size in blocks for d in range(size)}
    placed = {}  # our line index -> [(column, chord)]
    for lyric, chord_line in theirs.above.items():
        line_words = [(n, start, end) for n, (i, start, end, _) in enumerate(theirs.words) if i == lyric]
        if not line_words:
            continue
        for m in re.finditer(r"\S+", clean_line(chord_line)):
            if not CHORD_RE.fullmatch(m.group()):
                continue  # separators: |, (x2)
            chord = spelling.get(_key(m.group(), shift))
            if chord is None:
                return None, f"online chord {m.group()} isn't in our song"
            # the word under the chord, or the next one (a chord just before its word)
            n, start, _ = next((w for w in line_words if m.start() < w[2]), line_words[-1])
            if n not in to_ours:
                return None, f'online word "{theirs.words[n][3]}" isn\'t in our lyrics'
            i, our_start, our_end, _ = mine.words[to_ours[n]]
            placed.setdefault(i, []).append((our_start + min(max(m.start() - start, 0), our_end - our_start), chord))
    if not placed:
        return None, "no online chords above lyrics"
    out = {}
    for i, chords in placed.items():
        text = ""
        for column, chord in sorted(chords, key=lambda c: c[0]):
            text += " " * max(column - len(text), 1 if text else 0) + chord
        out[i] = _fit(text, len(clean_line(lines[i])))
    return out, None


def guide(body, online):
    """fill_chords(body), checked and extended with online versions [(url, text)].

    `body` is the song as it is (fill_chords runs here). Returns (new_body,
    filled, doubts); each note ends with its source: (shape), (same lyrics),
    (confirmed online) or (online: <url>)."""
    lines = body.split("\n")
    _, s1_filled, s1_doubts = fill_chords(body)
    ours = _parse(lines)

    def name(n):
        return f"stanza {n + 1} ({' '.join(lines[ours[n].lyrics[0]].split()[:4])}…)"

    models = {int(a) - 1: int(b) - 1 for a, b in (re.match(r"stanza (\d+) .*<- stanza (\d+)$", note).groups()
                                                  for note in s1_filled)}
    inserts, filled, doubts, general = {}, {}, {}, []
    for n, m in models.items():
        inserts.update(_copy(lines, ours, n, m))
        filled[n] = f"{name(n)} <- stanza {m + 1} ({'same lyrics' if ours[n].text == ours[m].text else 'shape'})"
    for note in s1_doubts:
        doubts.setdefault(int(re.match(r"stanza (\d+)", note).group(1)) - 1, []).append(f"{note} (shape)")

    spelling = {}  # chord key -> how our song writes it
    for raw in lines:
        line = clean_line(raw)
        label = LABEL_RE.fullmatch(line)
        for chord in CHORD_RE.findall(label.group(2) if label else line if is_chord_line(line) else ""):
            spelling.setdefault(_key(chord), chord)
    chorded = [n for n, s in enumerate(ours) if s.chords and not s.label]
    decided = set()  # stanzas an earlier online version already settled
    for url, text in online:
        theirs = _parse(text.split("\n"))
        pairs = {n: k for n, s in enumerate(ours)
                 if s.words and not s.label and (k := _pair(s, theirs)) is not None}
        shift, agreement = _shift(ours, theirs, pairs)
        source = f"online: {url}"
        if agreement < MIN_RATIO:
            general.append(f"online version in another arrangement ({source})")
            continue
        for n, k in pairs.items():
            if n in decided:
                continue
            online_cores = _cores(theirs[k].chords, shift)
            if ours[n].chords:  # had chords: never changed, only noted
                if _matcher(online_cores, _cores(ours[n].chords)).ratio() < MIN_RATIO:
                    doubts.setdefault(n, []).append(f"{name(n)}: online chords differ, left as is ({source})")
                decided.add(n)
            elif n in models:  # fill_chords picked a model: confirm it or take the one online agrees with
                scores = {m: _matcher(online_cores, _cores(ours[m].chords)).ratio() for m in [models[n], *chorded]
                          if m == models[n] or len(ours[m].lyrics) == len(ours[n].lyrics)}  # the model may have a label
                best = max(scores, key=lambda m: (scores[m], m == models[n]))
                if scores[best] < MIN_RATIO:
                    continue
                if best == models[n]:
                    filled[n] = f"{name(n)} <- stanza {best + 1} (confirmed online)"
                else:
                    for i in ours[n].lyrics:
                        inserts.pop(i, None)
                    inserts.update(_copy(lines, ours, n, best))
                    filled[n] = f"{name(n)} <- stanza {best + 1} ({source})"
                decided.add(n)
            else:  # fill_chords left it alone: our chords placed where the online ones are
                placed, problem = _place(lines, ours[n], theirs[k], shift, spelling)
                if problem:
                    doubts.setdefault(n, []).append(f"{name(n)}: {problem} ({source})")
                    continue
                inserts.update(placed)
                filled[n] = f"{name(n)} <- {source}"
                doubts[n] = []
                decided.add(n)

    out = []
    for i, raw in enumerate(lines):
        if i in inserts:
            out.append(inserts[i])
        out.append(raw)
    return ("\n".join(out), [filled[n] for n in sorted(filled)],
            general + [note for n in sorted(doubts) for note in doubts[n]])
