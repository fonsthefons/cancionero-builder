"""Chord names: Spanish notation to letters, keeping every chord in its column.

Spanish songbooks write chords as Do Re Mi Fa Sol La Si, in any case
(DO, Do, do), with the usual endings: LAm = Am, Sol7 = G7, Sib = Bb,
Do/Sol = C/G. Some write minor chords in lower case next to all-capitals
majors ("DO mi" = C Em); that convention is only assumed when a song mixes
those two styles.

The book places chords by column (see builder/lyrics.py), so a renamed chord
must start in the same column as before. Letter names are never longer than
the Spanish ones, except for a few endings (º -> dim); then the extra
characters are taken from the spaces that follow.
"""

import re

from builder.lyrics import CHORD_RE, SEPARATOR_RE

SOLFEGE = {"do": "C", "re": "D", "mi": "E", "fa": "F", "sol": "G", "la": "A", "si": "B"}
SOLFEGE_RE = re.compile(r"(sol|do|re|mi|fa|la|si)([#b]?)(.*)", re.IGNORECASE)
LETTER_RE = re.compile(r"([A-G][#b]?)(.*)")

# Endings the book doesn't recognise, written the way it does.
SUFFIXES = {"M7": "maj7", "7M": "maj7", "-": "m", "-7": "m7", "º": "dim", "°": "dim", "+": "aug"}

# "(x2)", "x2", "2x", "X3": repeat marks that may sit on a chord line.
REPEAT_RE = re.compile(r"\(?(?:[xX]\s?\d+|\d+\s?[xX])\)?")


def is_letter_chord(token):
    return CHORD_RE.fullmatch(token) is not None


def _solfege_part(part, lowercase_minor, bass):
    match = SOLFEGE_RE.fullmatch(part)
    if not match:
        return None
    name, accidental, suffix = match.groups()
    if bass and suffix:
        return None
    suffix = SUFFIXES.get(suffix, suffix)
    if lowercase_minor and name.islower() and not re.match(r"m(?!aj)", suffix):
        suffix = "m" + suffix
    return SOLFEGE[name.lower()] + accidental + suffix


def solfege_to_letters(token, lowercase_minor=False):
    """'LAm' -> 'Am', 'Do/Sol' -> 'C/G'; None if it isn't a Spanish chord."""
    main, _, bass = token.partition("/")
    chord = _solfege_part(main, lowercase_minor, bass=False)
    if chord is None:
        return None
    if bass:
        bass = _solfege_part(bass, False, bass=True)
        if bass is None:
            return None
        chord += "/" + bass
    return chord if is_letter_chord(chord) else None


# "Fm#" / "Cm#7": a common typo for F#m / C#m7 (the sharp after the m).
MINOR_SHARP_TYPO_RE = re.compile(r"([A-G])m([#b])(\d*)")


def fix_letter_chord(token):
    """A letter chord as the book writes it ('C7M' -> 'Cmaj7', 'Fm#' -> 'F#m'), or None."""
    if is_letter_chord(token):
        return token
    main, _, bass = token.partition("/")
    typo = MINOR_SHARP_TYPO_RE.fullmatch(main)
    if typo:
        main = f"{typo.group(1)}{typo.group(2)}m{typo.group(3)}"
    match = LETTER_RE.fullmatch(main)
    if not match:
        return None
    chord = match.group(1) + SUFFIXES.get(match.group(2), match.group(2)) + ("/" + bass if bass else "")
    return chord if is_letter_chord(chord) else None


class Notation:
    """How a song writes its chords, decided from all of its chord names."""

    def __init__(self, tokens):
        solfege = [t for t in tokens if solfege_to_letters(t) and not fix_letter_chord(t)]
        letters = [t for t in tokens if fix_letter_chord(t) and not solfege_to_letters(t)]
        self.solfege = len(solfege) > len(letters)
        roots = [SOLFEGE_RE.match(t).group(1) for t in solfege]
        # "DO mi": all-capitals majors next to lower-case minors ("La la" is just a sentence).
        self.lowercase_minor = any(r.islower() for r in roots) and any(r.isupper() for r in roots)

    def convert(self, token):
        """Letter name of a chord token (or of each chord in "D-E-F#m"), or None if it isn't a chord."""
        parts = token.split("-")
        if len(parts) > 1 and all(parts) and all(fix_letter_chord(p) for p in parts):
            return "-".join(fix_letter_chord(p) for p in parts)
        spanish = solfege_to_letters(token, self.lowercase_minor)
        letter = fix_letter_chord(token)
        return (spanish or letter) if self.solfege else (letter or spanish)


def could_be_chord(token):
    """A chord, or a run of letter chords joined by dashes ("D-E-F#m"; not "la-la-la")."""
    if solfege_to_letters(token) is not None or fix_letter_chord(token) is not None:
        return True
    parts = token.split("-")
    return len(parts) > 1 and all(p and fix_letter_chord(p) for p in parts)


def is_filler(token):
    """Tokens allowed on a chord line besides chords: | - ( ) and repeat marks."""
    return SEPARATOR_RE.fullmatch(token) is not None or REPEAT_RE.fullmatch(token) is not None


def replace_spans(line, spans):
    """Replace (start, end, new_text) spans in a line, keeping columns.

    Every replacement starts in the column where the old text started. When a
    replacement is longer, the extra characters are taken from the spaces
    after it (always leaving at least one); when shorter, spaces are added.
    """
    out = ""
    pos = 0
    ahead = 0  # columns the output is ahead of the original
    for start, end, new in spans:
        gap = line[pos:start]
        if ahead > 0 and out:
            spaces = len(gap) - len(gap.lstrip(" "))
            take = min(ahead, max(0, spaces - 1))
            gap = gap[take:]
            ahead -= take
        elif ahead < 0:
            gap = " " * -ahead + gap
            ahead = 0
        out += gap + new
        ahead += len(new) - (end - start)
        pos = end
    tail = line[pos:]
    if tail.strip():
        if ahead > 0:
            spaces = len(tail) - len(tail.lstrip(" "))
            tail = tail[min(ahead, max(0, spaces - 1)):]
        elif ahead < 0:
            tail = " " * -ahead + tail
    return (out + tail).rstrip()
