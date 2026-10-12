"""Turning a song body (chords written above lyrics) into HTML.

A line is a chord line when every word on it is a chord (or a separator such
as `|`, `-`, `(`, `)`). Each chord line is paired with the lyric line below it
so the two never get split across columns or pages.

Chords are placed by hand with spaces so each one sits over an exact letter.
Every character must therefore stay exactly one column wide: lines are kept
verbatim (rendered with `white-space: pre` in a monospace font), and the only
changes are ones that keep columns identical (see `clean_line`).
"""

import re
import unicodedata
from html import escape

# Standard chord symbols: Em, B7, Cmaj7, D/F#, G#m, Bb, Asus4, Amadd9, GSus,
# A7sus2, C#m7b5, ...
CHORD_RE = re.compile(
    r"(?<!\w)("
    r"[A-G][#b]?"
    r"(?:m?(?:maj|min|dim|aug|[sS]us|add|dom)\d*|m\d*|\d+)?"
    r"(?:(?:maj|sus|add)\d+|[#b]\d+|\d+)*"  # further parts: 7sus2, m7b5, 9#11
    r"(?:/[A-G][#b]?(?:m|maj|min|dim|aug|sus|add|dom)?\d*)?"
    r")(?!\w)"
)
# also repeat marks: x2, (x4); not fingerings such as x32010 (shown as lyrics)
SEPARATOR_RE = re.compile(r"[-|()]+|\(?[xX]\d{1,2}\)?")
TAB_WIDTH = 2
BOLD_MARK = "**"


def clean_line(raw):
    """Normalize a line without moving any character to another column.

    - NFC joins letter + combining accent ("e" + "´") into one character
      ("é"), which is what the editor showed as a single column anyway.
    - Non-breaking spaces become plain spaces; tabs become TAB_WIDTH spaces.
    """
    line = unicodedata.normalize("NFC", raw).replace("\xa0", " ")
    return line.expandtabs(TAB_WIDTH).rstrip()


def line_columns(line):
    """Number of on-screen columns a cleaned line takes."""
    return sum(1 for ch in line if not unicodedata.combining(ch))


def lyrics_columns(body):
    """Columns of the widest line, used to size the text to fit the screen."""
    return max((line_columns(clean_line(raw)) for raw in body.split("\n")), default=0)


# Guitar tablature ("G|--2----0--|", "B-------"): a string name followed by a
# bar or dashes, or digits next to "--". Not a chord, though it starts with a
# letter like one. ("C7-9", "D--A" and "|C---|G---|" are chords.)
TAB_START_RE = re.compile(r"[A-Ga-g](?:\|[-\d]|-{2,}(?!-)(?![A-G]))")
TAB_DIGITS_RE = re.compile(r"--\d|\d--")


def is_tablature(word):
    return bool(TAB_START_RE.match(word) or TAB_DIGITS_RE.search(CHORD_RE.sub("", word)))


def is_chord_line(line):
    words = line.split()
    if not words:
        return False
    has_chord = False
    for word in words:
        if CHORD_RE.search(word) and not is_tablature(word):
            has_chord = True
        elif not SEPARATOR_RE.fullmatch(word):
            return False
    return has_chord


def chord_line_html(line):
    chords = CHORD_RE.sub(r'<span class="chord">\1</span>', escape(line, quote=False))
    return f'<div class="chord-line">{chords}</div>'


# "Intro: G Em C D", "Solo: F G Am (x2)": chords written after a label, on a
# line of their own or followed by the first lyrics ("Intro: E Hoy quiero...").
LABEL_RE = re.compile(r"(\s*(?:intro|solo|final|punteo|outro|out|puente|interludio)\s*:)(.*)", re.I)


def label_chords_html(rest):
    """Mark the chords after a label, up to the first word that isn't one."""
    words = re.split(r"(\s+)", rest)  # odd indexes are runs of spaces
    for i in range(0, len(words), 2):
        word = words[i]
        if word and not (word[0] in "ABCDEFG" or SEPARATOR_RE.fullmatch(word) or not re.search(r"\w", word)):
            return "".join(words[:i]), "".join(words[i:])
    return rest, ""


def lyric_line_html(line, bold=False):
    css_class = "lyric-line bold" if bold else "lyric-line"
    label = LABEL_RE.fullmatch(line)
    if label:
        chords, lyrics = label_chords_html(label.group(2))
        chords = CHORD_RE.sub(r'<span class="chord">\1</span>', escape(chords, quote=False))
        if "<span" in chords:
            # chord-inline: transpose.js rewrites these chords too
            html = escape(label.group(1), quote=False) + chords + escape(lyrics, quote=False)
            return f'<div class="{css_class} chord-inline">{html}</div>'
    return f'<div class="{css_class}">{escape(line, quote=False)}</div>'


def pair_html(*lines):
    return f'<div class="line-pair">{"".join(lines)}</div>'


def verse_html(verse):
    """One verse: a list of (raw line, bold) without blank lines."""
    parts = []
    pending_chords = None  # chord line waiting for its lyric line

    for raw, bold in verse:
        line = clean_line(raw)
        if not line.strip():
            continue
        if is_chord_line(line):
            if pending_chords:
                parts.append(pair_html(pending_chords))
            pending_chords = chord_line_html(line)
        elif pending_chords:
            parts.append(pair_html(pending_chords, lyric_line_html(line, bold)))
            pending_chords = None
        else:
            parts.append(lyric_line_html(line, bold))

    if pending_chords:
        parts.append(pair_html(pending_chords))
    return f'<div class="verse">{"".join(parts)}</div>' if parts else ""


def split_verses(body):
    """Body -> verses, each a list of (raw line, bold).

    Blank lines separate verses. A line holding only BOLD_MARK starts or ends
    a bold part (used for choruses); it isn't shown and may span verses.
    """
    verses, current, bold = [], [], False
    for raw in body.split("\n"):
        if raw.strip() == BOLD_MARK:
            bold = not bold
        elif not raw.strip():
            if current:
                verses.append(current)
            current = []
        else:
            current.append((raw, bold))
    if current:
        verses.append(current)
    return verses


def lyrics_html(body):
    # Only trim blank lines around the body: the first line's indentation
    # (e.g. a chord placed mid-line) must be kept.
    body = body.strip("\n")
    verses = "\n".join(filter(None, map(verse_html, split_verses(body))))
    return f'<div class="lyrics">\n{verses}\n</div>'
