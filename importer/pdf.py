"""Read the songs of a PDF songbook (one with real text, not a scan).

Works from each character's position on the page (pdfplumber), so it handles
proportional fonts and two-column pages:

1. Lines: characters grouped into lines, page by page; pages with two text
   columns (an empty strip down the middle) are read left column first.
   Page numbers and headers/footers repeated on many pages are dropped.
2. Songs: a song starts at a title, found by its font size: the most common
   size that is bigger than the lyrics. Even bigger lines are section headings
   (e.g. albums, "Misa"), which can become the songs' tags. Books whose titles
   are the size of the lyrics are split at numbered bold lines ("12. Title").
   "Capo 2" / "Cejilla 2" at the top of a song is its capo.
3. Chords: a chord line's chords are placed over the letter of the lyric line
   below that sits at the same height on the page (x position), so they stay
   over the right syllable whatever the font. Bold lines (choruses in many
   songbooks) are kept bold (`**` lines).
4. Lyric lines the PDF wrapped because they were too long are joined again
   when the line reached the column's right edge and clearly goes on (it ends
   in "de", "la", "the"... or the next line starts in lower case).
5. Each song is then cleaned like a pasted song (importer/clean.py): Spanish
   chord names to letters, section labels, an "Intro:" at the top.

Every song comes with notes on what looked doubtful, to check by hand.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from .chords import could_be_chord, is_filler
from .clean import clean_song, detect_chord_line

COLUMN_GAP = 10  # pt: an empty vertical strip at least this wide splits a page into 2 columns
VERSE_GAP = 1.6  # a gap between lines bigger than this many line heights starts a new verse
MAX_JOINED = 60  # joined lines longer than this are left as the PDF broke them
NUMBERED_RE = re.compile(r"\s*(\d{1,4})\s*[.)\-–]\s*(\S.*)")
# II-XVIII before a title; a lone "I", "V" or "X" only with a dash or dot ("I Will Follow" stays)
ROMAN_RE = re.compile(r"^\s*(?:[IVXL]{2,6}\b\s*[-–.:]?|[IVX]\s*[-–.:])\s*(?=\S)")
CAPO_RE = re.compile(r"\s*(?:cejilla|capo|capotraste)\s*(?:en|:)?\s*(\d{1,2})\b\s*(.*)", re.I)
DANGLING = {
    # Spanish
    "el", "la", "los", "las", "de", "del", "en", "a", "y", "e", "que", "por", "con", "tu", "tus", "mi",
    "mis", "su", "sus", "un", "una", "para", "al", "lo", "sin", "sobre", "hasta", "desde", "o", "ni",
    "se", "me", "te", "nos", "le", "les", "pero", "porque", "cuando", "sino", "tan", "muy",
    # English
    "the", "an", "and", "of", "to", "in", "on", "my", "your", "our", "his", "her", "their", "with",
    "for", "from", "at", "by", "but", "or", "if", "as", "is", "are", "that", "this",
}


@dataclass
class PdfLine:
    page: int
    column: int
    top: float
    bottom: float
    size: float  # most common font size on the line
    bold: bool  # most of its characters are bold
    chars: list  # [(char, x0, x1)], spaces included
    left: float = 0.0  # left edge of its column
    right: float = 0.0  # right edge of its column's text (over the whole book)
    layout: tuple = (1, 0)  # (columns on its page, its column)

    @property
    def text(self):
        return "".join(c for c, _, _ in self.chars)

    @property
    def x0(self):
        return self.chars[0][1]

    @property
    def x1(self):
        return self.chars[-1][2]


@dataclass
class PdfSong:
    title: str
    number: int | None = None  # as numbered in the PDF
    capo: str | None = None
    author: str | None = None
    section: str | None = None  # heading above it (album, part of the book)
    page: int = 0  # first page, counted from 1
    body: str = ""
    notes: list = field(default_factory=list)  # doubts to check
    lines: list = field(default_factory=list)  # PdfLine, while parsing

    @property
    def label(self):
        return (f"{self.number}. " if self.number else "") + self.title


# ---------- 1. lines ----------

def is_bold(fontname):
    return bool(re.search(r"bold|black|heavy|semibold|demi", fontname, re.I))


def column_split(chars, width):
    """x where the page splits into two columns, or None."""
    covered = [0] * (int(width) + 2)
    for ch in chars:
        for x in range(max(0, int(ch["x0"])), min(len(covered), int(ch["x1"]) + 1)):
            covered[x] += 1
    best, start = None, None
    low, high = int(width * 0.25), int(width * 0.75)
    for x in range(low, high + 1):
        if covered[x] == 0 and start is None:
            start = x
        elif covered[x] and start is not None:
            if x - start >= COLUMN_GAP and (best is None or x - start > best[1] - best[0]):
                best = (start, x)
            start = None
    if best is None:
        return None
    middle = (best[0] + best[1]) / 2
    left_rows = {round(ch["bottom"]) for ch in chars if ch["x1"] < middle}
    right_rows = {round(ch["bottom"]) for ch in chars if ch["x0"] > middle}
    if min(len(left_rows), len(right_rows)) < 3:
        return None  # a word or two on one side (a page number, a margin note): one column
    return middle


def rows_of(chars):
    """Characters -> rows (same baseline), each sorted left to right."""
    rows = []
    for ch in sorted(chars, key=lambda c: (round(c["bottom"]), c["x0"])):
        for row in rows:
            if abs(row[0]["bottom"] - ch["bottom"]) < 0.3 * ch["size"]:
                row.append(ch)
                break
        else:
            rows.append([ch])
    return [sorted(row, key=lambda c: c["x0"]) for row in sorted(rows, key=lambda r: r[0]["bottom"])]


def row_line(row, page_no, column):
    chars, prev, space = [], None, False
    for ch in row:
        if ch["text"].isspace() or not ch["text"]:
            space = True
            continue
        if prev is not None and (space or ch["x0"] - prev["x1"] > ch["size"] * 0.15):
            chars.append((" ", prev["x1"], ch["x0"]))
        space = False
        chars.append((ch["text"], ch["x0"], ch["x1"]))
        prev = ch
    if not chars:
        return None
    visible = [ch for ch in row if ch["text"].strip()]
    sizes = Counter(round(ch["size"], 1) for ch in visible)
    bold = sum(1 for ch in visible if is_bold(ch["fontname"])) > len(visible) / 2
    return PdfLine(page_no, column, min(c["top"] for c in visible), max(c["bottom"] for c in visible),
                   sizes.most_common(1)[0][0], bold, chars)


def page_lines(page, page_no):
    chars = [c for c in page.chars if c["text"].strip()]
    if not chars:
        return []
    split = column_split(chars, page.width)
    columns = [chars] if split is None else [[c for c in chars if c["x1"] <= split],
                                             [c for c in chars if c["x1"] > split]]
    lines = []
    for column, column_chars in enumerate(columns):
        if not column_chars:
            continue
        found = [line for line in (row_line(row, page_no, column) for row in rows_of(column_chars)) if line]
        left = min(line.x0 for line in found)
        for line in found:
            line.left = left
            line.layout = (len(columns), column)
        lines.extend(found)
    return lines


def set_right_edges(lines):
    """The right edge of each column's text, over the whole book (one page may
    hold only short lines): where the longest lines end. Columns are told apart
    by where they start (a left column on a page whose right column is empty is
    still a left column). A few lines overhang the edge (punctuation), so not
    the very longest."""
    ends = {}
    for line in lines:
        ends.setdefault(round(line.left / 10), []).append(line.x1)
    for key, xs in ends.items():
        xs.sort(reverse=True)
        ends[key] = xs[min(len(xs) - 1, max(3, len(xs) // 50))]
    for line in lines:
        line.right = ends[round(line.left / 10)]


def read_lines(path):
    import pdfplumber  # only needed here; installed with the builder's requirements

    lines, heights = [], {}
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            lines.extend(page_lines(page, page_no))
            heights[page_no] = page.height
    lines = drop_page_furniture(lines, heights)
    set_right_edges(lines)
    return lines


def drop_page_furniture(lines, heights):
    """Page numbers, and headers/footers repeated on many pages."""
    pages = len(heights) or 1
    edge = {}
    for line in lines:
        height = heights[line.page]
        if line.top < 0.08 * height or line.bottom > 0.92 * height:
            edge.setdefault(re.sub(r"\d+", "#", line.text.strip()), set()).add(line.page)
    repeated = {text for text, on in edge.items() if len(on) >= max(3, 0.3 * pages)}
    kept = []
    for line in lines:
        height = heights[line.page]
        at_edge = line.top < 0.08 * height or line.bottom > 0.92 * height
        if at_edge and (re.fullmatch(r"\s*[-–]?\s*\d{1,4}\s*[-–]?\s*", line.text)
                        or re.sub(r"\d+", "#", line.text.strip()) in repeated):
            continue
        kept.append(line)
    return kept


# ---------- 2. songs ----------

def body_size(lines):
    sizes = Counter()
    for line in lines:
        sizes[line.size] += len(line.chars)
    return sizes.most_common(1)[0][0]


def is_chord_row(line):
    text = line.text.replace("–", "-").replace("—", "-")  # "Am – G/B – C"
    return bool(detect_chord_line(text, ask=lambda text: False))


def title_sizes(lines, body):
    """(title size or None, sizes of section headings)."""
    bigger = Counter(line.size for line in lines if line.size >= body + 1 and not is_chord_row(line))
    if not bigger:
        return None, set()
    # titles: the most frequent bigger size; much rarer and bigger ones are headings
    title = max(bigger, key=lambda size: (bigger[size], -size))
    return title, {size for size in bigger if size > title + 0.5}


def split_title(text):
    """'12. Title - Author' -> (12, 'Title', 'Author'); number and author may be None."""
    number = None
    numbered = NUMBERED_RE.fullmatch(text)
    if numbered:
        number, text = int(numbered.group(1)), numbered.group(2)
    # "VI - Verónica", "XV – Soy libre": a part number in Roman numerals, not part of the title
    text = ROMAN_RE.sub("", text, count=1) or text
    title, author = text.strip(), None
    left, sep, right = title.rpartition(" - ")
    if sep and left and 0 < len(right.split()) <= 5:
        title, author = left.strip(), right.strip()
    return number, title, author


def nice_case(text):
    """TITLES IN CAPITALS -> 'Titles in capitals' (others are kept)."""
    letters = [c for c in text if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(letters) > 1:
        text = text.lower()
        for i, c in enumerate(text):
            if c.isalpha():
                return text[:i] + c.upper() + text[i + 1:]
    return text


def split_songs(lines):
    body = body_size(lines)
    title_size, heading_sizes = title_sizes(lines, body)
    songs, current, section, heading_open = [], None, None, False

    def is_title(line):
        if title_size is not None:
            return abs(line.size - title_size) <= 0.5 and not is_chord_row(line)
        return line.bold and NUMBERED_RE.fullmatch(line.text) is not None and not is_chord_row(line)

    previous = None
    for line in lines:
        if any(abs(line.size - size) <= 0.5 for size in heading_sizes):
            text = line.text.strip()
            section = (section + " " + text) if heading_open else text
            heading_open = True
            previous = None
            continue
        heading_open = False
        if is_title(line):
            continued = (previous is not None and current is not None and not current.lines
                         and previous.page == line.page and line.top - previous.bottom < line.size)
            if continued:  # a title on two lines
                current.title += " " + line.text.strip()
            else:
                current = PdfSong(title=line.text.strip(), section=section, page=line.page)
                songs.append(current)
            previous = line
            continue
        previous = None
        if current is None:
            continue  # cover, contents... before the first song
        capo = CAPO_RE.fullmatch(line.text) if not current.lines else None
        if capo and current.capo is None:
            current.capo = capo.group(1) + (f" {capo.group(2).strip()}" if capo.group(2).strip() else "")
            continue
        current.lines.append(line)

    for song in songs:
        song.number, title, song.author = split_title(song.title)
        song.title = nice_case(title)
        if song.section:
            song.section = nice_case(song.section).rstrip(" :")
    return songs


# ---------- 3./4. song text ----------

def char_index(x, lyric):
    """Index in the lyric line's text of the character at x (or past its end)."""
    chars = lyric.chars
    if x > chars[-1][2] + 1:
        width = (lyric.x1 - lyric.x0) / max(1, len(chars))
        return len(chars) + max(1, round((x - chars[-1][2]) / width))
    best = min(range(len(chars)), key=lambda i: abs(chars[i][1] - x))
    if chars[best][0] == " " and best + 1 < len(chars) and abs(chars[best + 1][1] - x) < 4:
        best += 1
    return best


def words_with_x(line):
    words, word, start = [], "", None
    for ch, x0, _ in line.chars:
        if ch == " ":
            if word:
                words.append((start, word))
            word = ""
        else:
            if not word:
                start = x0
            word += ch
    if word:
        words.append((start, word))
    return words


def place(chords):
    """[(column, chord)] -> text, each chord at its column, at least one space apart."""
    text = ""
    for column, chord in chords:
        column = max(column, len(text) + 1 if text else column)
        text = text.ljust(column) + chord
    return text


def average_char_width(lines):
    widths = [(line.x1 - line.x0) / len(line.chars) for line in lines if len(line.chars) > 10]
    return sorted(widths)[len(widths) // 2] if widths else 5.0


def song_units(song_lines):
    """Lines of a song -> units: {"gap", "bold", "chords": [(col, chord)], "lyric": PdfLine or None}."""
    units = []
    char_width = average_char_width(song_lines)
    height = Counter(round(b.top - a.top) for a, b in zip(song_lines, song_lines[1:])
                     if a.page == b.page and a.column == b.column and b.top > a.top)
    step = height.most_common(1)[0][0] if height else 14
    i = 0
    while i < len(song_lines):
        line = song_lines[i]
        prev = song_lines[i - 1] if i else None
        moved = prev is not None and (line.page != prev.page or line.column != prev.column)
        gap = prev is None or (not moved and line.top - prev.top > VERSE_GAP * step)
        if moved:  # a verse going on in the next column/page starts in lower case
            first_lyric = next((x for x in song_lines[i:i + 2] if not is_chord_row(x)), None)
            gap = not (first_lyric and first_lyric.text.lstrip("¡¿(“\"'")[:1].islower())
        if is_chord_row(line):
            nxt = song_lines[i + 1] if i + 1 < len(song_lines) else None
            if (nxt is not None and not is_chord_row(nxt) and nxt.page == line.page
                    and nxt.column == line.column and nxt.top - line.top <= VERSE_GAP * step):
                chords = [(char_index(x, nxt), word) for x, word in words_with_x(line)]
                units.append({"gap": gap, "bold": nxt.bold, "chords": chords, "lyric": nxt})
                i += 2
                continue
            chords = [(max(0, round((x - line.left) / char_width)), word) for x, word in words_with_x(line)]
            units.append({"gap": gap, "bold": line.bold, "chords": chords, "lyric": None})
        else:
            units.append({"gap": gap, "bold": line.bold, "chords": [], "lyric": line})
        i += 1
    return units


def joins(previous, unit):
    """Whether a lyric line is the rest of the previous one, wrapped by the PDF."""
    if unit["gap"] or previous["lyric"] is None or unit["lyric"] is None or previous["bold"] != unit["bold"]:
        return False
    last, line = previous["last"], unit["lyric"]
    if last.page != line.page or last.column != line.column:
        return False
    text = previous["text"].rstrip()
    if not text or text[-1] in ".!?…:;," or len(text) + len(line.text) > MAX_JOINED:
        return False
    first_word = line.text.split()[0] if line.text.split() else ""
    first_width = sum(x1 - x0 for ch, x0, x1 in line.chars[:len(first_word)])
    reached_edge = last.x1 + first_width + 3 > last.right
    last_word = text.split()[-1].lower()
    starts_lower = line.text.lstrip("¡¿(“\"'")[:1].islower()
    # A line never ends on "de", "la", "the"...: wherever it stops, it goes on.
    return last_word in DANGLING or (reached_edge and starts_lower)


def song_text(song):
    """The song's text, chords over their letters, bold parts between `**` lines."""
    units = song_units(song.lines)
    joined = []
    for unit in units:
        if joined and joins(joined[-1], unit):
            previous = joined[-1]
            offset = len(previous["text"]) + 1
            previous["chords"] += [(column + offset, chord) for column, chord in unit["chords"]]
            previous["text"] += " " + unit["lyric"].text
            previous["last"] = unit["lyric"]
            continue
        joined.append(dict(unit, text=unit["lyric"].text if unit["lyric"] else None,
                           last=unit["lyric"]))

    bold_units = sum(1 for unit in joined if unit["bold"])
    use_bold = 0 < bold_units < 0.8 * len(joined)  # an all-bold song: bold isn't a chorus
    out, bold = [], False
    for unit in joined:
        if unit["gap"] and out:
            if bold:  # close the bold part before the verse break
                out.append("**")
                bold = False
            out.append("")
        if use_bold and unit["bold"] != bold:
            out.append("**")
            bold = unit["bold"]
        if unit["chords"]:
            out.append(place(unit["chords"]).rstrip())
        if unit["text"] is not None:
            out.append(unit["text"].rstrip())
    if bold:
        out.append("**")
    return "\n".join(out)


def doubts(song, cleaned):
    notes = list(cleaned.notes)
    lines = [line for line in cleaned.body.split("\n") if line.strip()]
    chord_rows = sum(1 for line in song.lines if is_chord_row(line))
    if chord_rows == 0:
        notes.append("no chords found (lyrics only?)")
    if len(lines) < 4:
        notes.append("very short: is it a whole song?")
    suspects = [line.text.strip() for line in song.lines
                if not is_chord_row(line) and line.text.split() and ":" not in line.text  # "Intro: C G" is fine
                and sum(could_be_chord(w) or is_filler(w) for w in line.text.split()) > 0.6 * len(line.text.split())
                and len(line.text.split()) > 1]
    if suspects:
        notes.append(f"lines that look like chords but were read as lyrics: {'; '.join(suspects[:3])}")
    return notes


def is_contents(song):
    """A "song" that is really (part of) a table of contents: numbered titles, no chords."""
    numbered = sum(1 for line in song.lines if NUMBERED_RE.fullmatch(line.text))
    return numbered >= 0.6 * len(song.lines) and not any(is_chord_row(line) for line in song.lines)


def read_pdf(path):
    """[PdfSong] with body and notes, in the PDF's order."""
    songs = split_songs(read_lines(path))
    found = []
    for song in songs:
        if not song.lines or is_contents(song):
            continue  # a title with nothing under it, or a contents page
        text = song_text(song)
        cleaned = clean_song(text, marked=False, ask=lambda line: False, from_web=False, intro=False)
        song.body = cleaned.body
        if not song.capo and cleaned.capo:
            song.capo = cleaned.capo
        song.notes = doubts(song, cleaned)
        song.lines = []
        found.append(song)
    return found
