"""Song keys: work out a song's key from its chords, and spell chords to fit a key.

The key is the key of the chords as written (a capo doesn't change it). It is
saved in the song file (`key: G`, `key: Em`) and shown under the title; the page
transposes it with the chords (web/js/transpose.js spells chords the same way).

Spelling: a chord's root is named by its degree in the key (in F, the chord a
fourth up is Bb, never A#); diminished chords lead up a semitone, so they take
the raised degree (G#dim in C); the bass of a slash chord is named from the
chord's own root (E/G#, D/F#, C/Bb).
"""

import re

from .lyrics import CHORD_RE, LABEL_RE, is_chord_line, label_chords_html

LETTERS = "CDEFGAB"
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
MAJOR_KEYS = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
MINOR_KEYS = ["Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm"]
FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb", "Dm", "Gm", "Cm", "Fm", "Bbm", "Ebm", "Abm"}
USUAL_KEYS = set(MAJOR_KEYS + MINOR_KEYS) | {"Gb", "C#", "D#m", "A#m", "Ebm", "Abm"}
KEY_RE = re.compile(r"[A-G][#b]?m?")
UNSURE = 0.5  # a key this little ahead of the next best is reported, and its chords left as written
# Letter steps above the tonic for each interval in semitones: b2 2 b3 3 4 #4 5 b6 6 b7 7
STEPS = [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6]
DIM_STEPS = {1: 0, 3: 1, 6: 3, 8: 4, 10: 5}  # leading-tone chords: #1 #2 #4 #5 #6
DIM_RE = re.compile(r"dim|°|o\b|m7b5")
CHORD_PARTS = re.compile(r"([A-G][#b]?)([^/]*)(?:/([A-G][#b]?)(.*))?")


def pitch(note):
    return (NATURAL[note[0]] + {"#": 1, "b": -1}.get(note[1:2], 0)) % 12


RAISED_STEPS = {6: 3}  # a minor chord a tritone up is on the raised 4th: F#m in C
AMBIGUOUS_ROOT = {1, 6}  # major chords a semitone or a tritone up: Db/C#, F#/Gb in C
AMBIGUOUS_MINOR = {1, 3, 8, 10}  # minor ones: C#m/Dbm, D#m/Ebm, G#m/Abm, A#m/Bbm in C
AMBIGUOUS_BASS = {1, 6, 8}  # G/G# (rising) or G/Ab? C/F# or C/Gb? C/Ab or C/G#?
ODD_NAMES = ("E#", "B#", "Cb", "Fb")


def spell(pc, tonic, flats, steps_for=None, written=None):
    """Name of pitch class `pc` as a degree above `tonic` (a note name).
    steps_for: {interval: letter steps} overriding STEPS (raised degrees).
    E#, B#, Cb and Fb only when the song wrote them (C#/E#); else F, C, B, E."""
    interval = (pc - pitch(tonic)) % 12
    steps = (steps_for or {}).get(interval, STEPS[interval])
    letter = LETTERS[(LETTERS.index(tonic[0]) + steps) % 7]
    accidental = (pc - NATURAL[letter] + 6) % 12 - 6
    name = letter + {1: "#", -1: "b", 0: ""}.get(accidental, "?")
    if "?" in name or (name in ODD_NAMES and name != written):
        return (FLAT_NAMES if flats else SHARP_NAMES)[pc]
    return name


def like_written(pc, written, flats):
    """`pc` named with the kind of accidental the song wrote (or the key's, if none)."""
    if pitch(written) == pc:
        return written
    if "#" in written:
        return SHARP_NAMES[pc]
    if "b" in written[1:]:
        return FLAT_NAMES[pc]
    return (FLAT_NAMES if flats else SHARP_NAMES)[pc]


def tonic_of(key):
    return key[:-1] if key.endswith("m") else key


def degree_tonic(key):
    """Chords are named by degrees of the major scale of the key signature: a minor
    key uses its relative major (Dm -> F), so Bb, Bbm and Ebdim in Dm read as in F."""
    tonic = tonic_of(key)
    if not key.endswith("m"):
        return tonic
    return spell((pitch(tonic) + 3) % 12, tonic, key in FLAT_KEYS)


def spell_chord(chord, key, shift=0):
    """`chord` moved `shift` semitones and spelled for `key` (the key after the shift)."""
    parts = CHORD_PARTS.fullmatch(chord)
    if not parts:
        return chord
    root, suffix, bass, bass_suffix = parts.groups()
    flats, tonic = key in FLAT_KEYS, degree_tonic(key)
    pc = (pitch(root) + shift) % 12
    kind = quality(suffix)
    interval = (pc - pitch(tonic)) % 12
    if kind == "dim":
        new_root = spell(pc, tonic, flats, DIM_STEPS)
    elif (kind == "m" and interval in AMBIGUOUS_MINOR) or (kind != "m" and interval in AMBIGUOUS_ROOT):
        new_root = like_written(pc, root, flats)
    else:
        new_root = spell(pc, tonic, flats, RAISED_STEPS if kind == "m" else None)
    if not bass:
        return new_root + suffix
    bass_pc = (pitch(bass) + shift) % 12
    if (bass_pc - pc) % 12 in AMBIGUOUS_BASS:
        new_bass = like_written(bass_pc, bass, flats)
    else:
        new_bass = spell(bass_pc, new_root, flats, written=bass if shift % 12 == 0 else None)
    return f"{new_root}{suffix}/{new_bass}{bass_suffix or ''}"


def transpose_key(key, shift):
    minor = key.endswith("m")
    if shift % 12 == 0:
        return key
    return (MINOR_KEYS if minor else MAJOR_KEYS)[(pitch(tonic_of(key)) + shift) % 12]


# ---- reading the chords of a song ----

def chord_lines(body):
    """(line index, chord text, start column) for each chord line or label line
    ("Intro: G D") of the body; label lines give the part after the label."""
    for i, line in enumerate(body.split("\n")):
        if is_chord_line(line):
            yield i, line, 0
            continue
        label = LABEL_RE.fullmatch(line)
        if label:
            chords, _ = label_chords_html(label.group(2))
            yield i, chords, len(label.group(1))


def song_chords(body):
    return [m.group(1) for _, text, _ in chord_lines(body) for m in CHORD_RE.finditer(text)]


def quality(suffix):
    """'M', 'm', 'dim' or None (sus, power chords: either)."""
    if DIM_RE.match(suffix):
        return "dim"
    if re.match(r"m(?!aj)|min", suffix):
        return "m"
    if re.match(r"sus|5\b", suffix):
        return None
    return "M"


# Chords of each kind of key: (semitones above the tonic, quality) -> how well it fits.
W_VV, W_B7, W_FIT, W_FIRST, W_LAST, W_SHARE, W_CADENCE = 0.45, 0.6, 25, 3, 0.5, 4, 4
MAJOR_FIT = {(0, "M"): 1, (2, "m"): 1, (4, "m"): 1, (5, "M"): 1, (7, "M"): 1, (9, "m"): 1, (11, "dim"): 1,
             (2, "M"): W_VV, (4, "M"): 0.5, (9, "M"): 0.4, (11, "M"): 0.3, (10, "M"): W_B7, (5, "m"): 0.5,
             (8, "M"): 0.4, (3, "M"): 0.3, (0, "m"): 0.1, (6, "dim"): 0.5, (1, "dim"): 0.5, (8, "dim"): 0.5}
MINOR_FIT = {(0, "m"): 1, (2, "dim"): 1, (3, "M"): 1, (5, "m"): 1, (7, "m"): 1, (8, "M"): 1, (10, "M"): 1,
             (7, "M"): 1, (11, "dim"): 0.8, (5, "M"): 0.5, (2, "m"): 0.4, (0, "M"): 0.4, (1, "M"): 0.4,
             (10, "m"): 0.2, (3, "m"): 0.1}
MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11}
MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10, 11}


def key_scores(chords):
    """{key name: score} over the 24 keys (higher fits better)."""
    parsed = []
    for chord in chords:
        parts = CHORD_PARTS.fullmatch(chord)
        if parts:
            parsed.append((pitch(parts.group(1)), quality(parts.group(2))))
    if not parsed:
        return {}
    first, last = parsed[0], parsed[-1]
    scores = {}
    for minor, names, fit, scale in ((False, MAJOR_KEYS, MAJOR_FIT, MAJOR_SCALE),
                                     (True, MINOR_KEYS, MINOR_FIT, MINOR_SCALE)):
        tonic_quality = "m" if minor else "M"
        for tonic in range(12):
            total = 0
            for pc, q in parsed:
                step = (pc - tonic) % 12
                total += (step in scale) * 0.8 if q is None else fit.get((step, q), 0)
            score = W_FIT * total / len(parsed)

            def is_tonic(chord):
                return chord[0] == tonic and chord[1] in (tonic_quality, None)

            share = sum(map(is_tonic, parsed)) / len(parsed)
            # cadences: the chord a fifth above (V, V7) moving to the tonic chord
            cadences = sum(is_tonic(b) and (a[0] - tonic) % 12 == 7 and a[1] in ("M", None)
                           for a, b in zip(parsed, parsed[1:]))
            score += (W_FIRST * is_tonic(first) + W_LAST * is_tonic(last) + W_SHARE * share
                      + W_CADENCE * cadences / len(parsed))
            scores[names[tonic]] = score
    return scores


def detect_key(body):
    """(key, margin over the next best key, next best key) or None without chords.
    The key is spelled as the song spells its tonic when it does (Gb vs F#)."""
    chords = song_chords(body)
    scores = key_scores(chords)
    if not scores:
        return None
    ranked = sorted(scores, key=scores.get, reverse=True)
    best, second = ranked[0], ranked[1]
    suffix = "m" if best.endswith("m") else ""
    for chord in chords:  # the song's own spelling of its tonic, if it is a usual key name
        root = CHORD_PARTS.fullmatch(chord).group(1)
        if pitch(root) == pitch(tonic_of(best)):
            if root + suffix in USUAL_KEYS:
                best = root + suffix
            break
    return best, scores[ranked[0]] - scores[second], second


# ---- rewriting a song's chords for its key ----

def respell_line(text, names):
    """A chord line with its chords replaced by `names` (in order), each chord
    staying in its column: spaces after a chord that got longer (shorter) shrink (grow)."""
    out, pos, drift = [], 0, 0
    for match, chord in zip(CHORD_RE.finditer(text), names):
        gap = text[pos:match.start()]
        if drift > 0:  # the previous chord got longer: take spaces from this gap, keep one
            spaces = len(gap) - len(gap.rstrip(" "))
            take = min(drift, max(0, spaces - 1))
            gap = gap[:len(gap) - take]
            drift -= take
        elif drift < 0:
            gap += " " * -drift
            drift = 0
        drift += len(chord) - len(match.group(1))
        out.append(gap + chord)
        pos = match.end()
    rest = text[pos:]
    if drift < 0 and rest.strip():
        rest = " " * -drift + rest
    return "".join(out) + rest


def respell_chords(chords, key):
    """The song's chords (in order) spelled for `key`. A major or dominant chord
    followed by a chord a fourth up is named as that chord's fifth (G#7 -> C#m)."""
    names = [spell_chord(chord, key) for chord in chords]
    for i in range(len(chords) - 2, -1, -1):
        this, after = CHORD_PARTS.fullmatch(names[i]), CHORD_PARTS.fullmatch(names[i + 1])
        if not (this and after) or quality(this.group(2)) not in ("M", None):
            continue
        root, target = this.group(1), after.group(1)
        if (pitch(target) - pitch(root)) % 12 == 5:
            fifth = LETTERS[(LETTERS.index(target[0]) + 4) % 7]
            accidental = (pitch(root) - NATURAL[fifth] + 6) % 12 - 6
            if accidental in (-1, 0, 1) and fifth + {1: "#", -1: "b", 0: ""}[accidental] not in ODD_NAMES:
                named = fifth + {1: "#", -1: "b", 0: ""}[accidental]
                names[i] = named + names[i][len(root):]
    return names


def respell_body(body, key):
    """The body with every chord spelled for `key`, chords staying in their columns."""
    lines = body.split("\n")
    found = list(chord_lines(body))
    chords = [m.group(1) for _, text, _ in found for m in CHORD_RE.finditer(text)]
    names = iter(respell_chords(chords, key))
    for i, text, start in found:
        count = sum(1 for _ in CHORD_RE.finditer(text))
        line = lines[i]
        lines[i] = line[:start] + respell_line(text, [next(names) for _ in range(count)]) + line[start + len(text):]
    return "\n".join(lines)


def key_song_file(text, body):
    """(new file text, key, runner-up or None if sure) for a song file without `key:`,
    or None when its body has no chords. Confident keys also respell the chords."""
    found = detect_key(body)
    if not found:
        return None
    key, margin, second = found
    sure = margin >= UNSURE
    head = text[: len(text) - len(body)]
    lines = head.split("\n")
    at = next((i + 1 for i, line in enumerate(lines[1:], 1) if line.startswith("title:")), 1)
    lines.insert(at, f"key: {key}")
    return "\n".join(lines) + (respell_body(body, key) if sure else body), key, None if sure else second
