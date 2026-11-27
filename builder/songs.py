"""Loading and validating song files (YAML frontmatter + lyrics)."""

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .keys import KEY_RE
from .text import spanish_sort_key

# Frontmatter fields a song may use. Anything else is reported as an error,
# which catches typos and mis-indented YAML.
REQUIRED_FIELDS = {"title"}
OPTIONAL_FIELDS = {"key", "autor", "capo", "link", "added", "song_tags", "horas", "melody", "tab", "ignore", "semitono"}
# tab-melody-check: the tab covers only the first notes of the melody; long-lines-check and
# far-chords-check: build warnings (builder/build.py) the song is fine without
IGNORABLE_CHECKS = ("tab-melody-check", "long-lines-check", "far-chords-check")


class SongError(Exception):
    pass


@dataclass
class Song:
    id: str  # file name without extension; stable across builds
    title: str
    body: str
    tags: dict[str, list[str]]  # {tag: [subtags]}, flat tags have []
    autor: str | None = None
    capo: str | None = None
    key: str | None = None  # key of the chords as written ("G", "Em"); filled in by the build
    link: str | None = None
    added: str | None = None  # day the song was added; not shown
    horas: list = field(default_factory=list)  # slot patterns in horas.yaml, as written
    melody: str | None = None  # ABC notation body ("K:D\n...") shown as a staff
    tab: str | None = None  # guitar tab, one "fret/string" per melody note
    ignore: list = field(default_factory=list)  # IGNORABLE_CHECKS skipped
    semitono: dict = field(default_factory=dict)  # parse_semitono's result, 1-based as written
    number: int = 0  # assigned after sorting

    @property
    def anchor(self):
        slug = re.sub(r"[^\w-]+", "-", self.id.lower()).strip("-")
        return f"song-{slug}"

    @property
    def heading(self):
        return f"{self.number}. {self.title}"


def split_frontmatter(text):
    """Split "---\\n<yaml>\\n---\\n<body>" into (dict, body)."""
    lines = text.split("\n")
    if lines[0].strip() != "---":
        raise SongError("file must start with a `---` frontmatter block")
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            meta = yaml.safe_load("\n".join(lines[1:end])) or {}
            if not isinstance(meta, dict):
                raise SongError("frontmatter must be a set of `key: value` fields")
            return meta, "\n".join(lines[end + 1 :])
    raise SongError("frontmatter block is never closed with `---`")


def parse_tags(raw):
    """song_tags as written: {tag: [subtags]}. A plain list (`[misa, adoracion]`)
    is accepted too: tags without subtags."""
    if raw is None:
        return {}
    if isinstance(raw, list) and all(isinstance(tag, (str, int)) for tag in raw):
        return {str(tag): [] for tag in raw}
    if not isinstance(raw, dict):
        raise SongError("song_tags must be a mapping like `misa: [entrada]`")
    tags = {}
    for tag, subtags in raw.items():
        if subtags is None:
            subtags = []
        if isinstance(subtags, (str, int)):
            subtags = [subtags]
        if not isinstance(subtags, list):
            raise SongError(f'subtags of "{tag}" must be a list')
        tags[str(tag)] = [str(subtag) for subtag in subtags]
    return tags


def parse_horas(raw):
    """horas as written: a list of slot patterns; a single one is accepted too."""
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list) or not all(isinstance(p, str) for p in raw):
        raise SongError('horas must be a list like `[semana_i/domingo/laudes/himno, "*/magnificat"]`')
    return raw


def parse_ignore(raw):
    """ignore as written: a list of checks to skip; a single one is accepted too."""
    checks = [raw] if isinstance(raw, str) else raw or []
    if not isinstance(checks, list):
        raise SongError('ignore must be a list like `["tab-melody-check"]`')
    unknown = [check for check in checks if check not in IGNORABLE_CHECKS]
    if unknown:
        raise SongError(f'ignore: "{unknown[0]}" is not a check (allowed: {", ".join(sorted(IGNORABLE_CHECKS))})')
    return checks


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def parse_semitono(raw):
    """semitono as written (see README): {"bars": {"2": {verse: [bar | "f"]}}, "stress": {line: n},
    "split": {word: "si-ón"}}, normalized (str sizes, int verses); empty sections are dropped."""
    if raw is None:
        return {}
    if not isinstance(raw, dict) or raw.keys() - {"bars", "stress", "split"}:
        raise SongError("semitono must be a mapping with bars, stress and split")
    out = {}
    bars = raw.get("bars") or {}
    if not isinstance(bars, dict):
        raise SongError("semitono bars must be a mapping like `\"4\": {2: [1, 1, 2]}`")
    for size, verses in bars.items():
        if str(size) not in ("2", "3", "4") or not isinstance(verses, dict):
            raise SongError(f'semitono bars: "{size}" must be 2, 3 or 4 with verses under it')
        for verse, lines in verses.items():
            if isinstance(verse, str) and re.fullmatch(r"[0-9]+", verse):
                verse = int(verse)
            if not is_int(verse) or verse < 1:
                raise SongError(f'semitono bars {size}: verse "{verse}" must be a number from 1')
            for bar in lines if isinstance(lines, list) else [None]:
                if not (is_int(bar) and 1 <= bar <= int(size) or bar == "f" and str(size) == "2"):
                    raise SongError(f'semitono bars {size}, verse {verse}: each line needs a bar from 1 to {size}'
                                    + (' or "f"' if str(size) == "2" else ""))
            out.setdefault("bars", {}).setdefault(str(size), {})[verse] = lines
    for name, kind in (("stress", int), ("split", str)):
        entries = raw.get(name) or {}
        if not isinstance(entries, dict):
            raise SongError(f"semitono {name} must be a mapping")
        for text, value in entries.items():
            if not isinstance(text, str) or not (is_int(value) and value >= 1 if kind is int
                                                 else isinstance(value, str) and "-" in value):
                raise SongError(f'semitono {name}: "{text}" needs ' +
                                ("a syllable number from 1" if kind is int else 'syllables like "si-ón"'))
        if name == "split":  # the book looks words up lowercased
            entries = {unicodedata.normalize("NFC", text).lower(): unicodedata.normalize("NFC", value).lower()
                       for text, value in entries.items()}
            for text, value in entries.items():
                if value.replace("-", "") != text:
                    raise SongError(f'semitono split: "{value}" must spell "{text}" with dashes between syllables')
        if entries:
            out[name] = dict(entries)
    return out


def check_tab(melody, tab, count_notes=True):
    """Each note of the melody needs one "fret/string" tab token (bars are ignored).
    count_notes=False keeps the token check but allows any number of them."""
    # shortcut: counts pitch letters outside "chords" and header lines; ABC chords
    # ([CEG]), grace notes and !decorations! would miscount; fine for the fórmulas.
    body = re.sub(r'"[^"]*"|![^!]*!', "", re.sub(r"(?m)^[A-Za-z]:.*$", "", melody or ""))
    notes = len(re.findall(r"[A-Ga-g]", body))
    tokens = [t for t in (tab or "").split() if t.strip("|")]
    bad = [t for t in tokens if not re.fullmatch(r"\d{1,2}/[1-6]", t)]
    if bad:
        raise SongError(f'tab: "{bad[0]}" is not fret/string (like 2/1, string 1 = high e … 6 = low E)')
    if count_notes and len(tokens) != notes:
        raise SongError(f"tab has {len(tokens)} notes but melody has {notes}")


def song_sort_key(song):
    # natural order: "2 ..." before "10 ..." (runs of digits compared as numbers)
    words = re.split(r"(\d+)", spanish_sort_key(song.title))
    return [int(w) if i % 2 else w for i, w in enumerate(words)], song.id


def optional_text(value):
    if value is None:
        return None
    return str(value).strip() or None


def load_song(path):
    """A song file as written (tags not resolved against the book's tags)."""
    meta, body = split_frontmatter(Path(path).read_text(encoding="utf-8"))

    missing = REQUIRED_FIELDS - meta.keys()
    unknown = meta.keys() - REQUIRED_FIELDS - OPTIONAL_FIELDS
    if missing:
        raise SongError(f"missing field(s): {', '.join(sorted(missing))}")
    if unknown:
        raise SongError(
            f"unknown field(s): {', '.join(sorted(unknown))} "
            f"(allowed: {', '.join(sorted(REQUIRED_FIELDS | OPTIONAL_FIELDS))})"
        )

    link = optional_text(meta.get("link"))
    if link and not re.match(r"https?://", link):
        raise SongError(f'link must be a web address starting with http:// or https:// (got "{link}")')
    melody, tab = optional_text(meta.get("melody")), optional_text(meta.get("tab"))
    ignore = parse_ignore(meta.get("ignore"))
    key = optional_text(meta.get("key"))
    if key and not KEY_RE.fullmatch(key):
        raise SongError(f'key must be a key like G, Bb, F#m or Em (got "{key}")')
    if tab:  # a melody without a tab is allowed (staff only)
        check_tab(melody, tab, count_notes="tab-melody-check" not in ignore)

    return Song(
        id=Path(path).stem,
        title=str(meta["title"]).strip(),
        body=body,
        tags=parse_tags(meta.get("song_tags")),
        autor=optional_text(meta.get("autor")),
        capo=optional_text(meta.get("capo")),
        key=key,
        link=link,
        added=optional_text(meta.get("added")),
        horas=parse_horas(meta.get("horas")),
        melody=melody,
        tab=tab,
        ignore=ignore,
        semitono=parse_semitono(meta.get("semitono")),
    )


def load_songs(songs_dir, taxonomy, horas=None):
    """Load every song, resolve its tags, check its `horas:` against the horas.yaml
    tree (horas.Node, None: the book has none), and number them alphabetically by title.

    Raises SongError listing every problem found, so they can all be fixed at once.
    """
    songs, errors = [], []

    for path in sorted(Path(songs_dir).glob("*.md")):
        try:
            song = load_song(path)
        except (SongError, yaml.YAMLError) as e:
            errors.append(f"  {path}: {e}")
            continue
        song.tags, problems = taxonomy.resolve(song.tags)
        errors.extend(f"  {path}: {e}" for e in problems)
        if song.horas and horas is None:
            errors.append(f"  {path}: horas: the book has no horas.yaml")
        elif song.horas:
            errors.extend(f'  {path}: horas: "{p}" matches no part of horas.yaml' for p in horas.unmatched(song.horas))
        songs.append(song)

    if errors:
        raise SongError("Invalid songs:\n" + "\n".join(errors))

    taxonomy.finish()
    songs.sort(key=song_sort_key)
    for number, song in enumerate(songs, start=1):
        song.number = number
    return songs
