"""Loading and validating song files (YAML frontmatter + lyrics)."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .text import spanish_sort_key

# Frontmatter fields a song may use. Anything else is reported as an error,
# which catches typos and mis-indented YAML.
REQUIRED_FIELDS = {"title"}
OPTIONAL_FIELDS = {"autor", "capo", "link", "added", "song_tags", "horas"}


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
    link: str | None = None
    added: str | None = None  # day the song was added; not shown
    horas: list = field(default_factory=list)  # slot patterns in horas.yaml, as written
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

    return Song(
        id=Path(path).stem,
        title=str(meta["title"]).strip(),
        body=body,
        tags=parse_tags(meta.get("song_tags")),
        autor=optional_text(meta.get("autor")),
        capo=optional_text(meta.get("capo")),
        link=link,
        added=optional_text(meta.get("added")),
        horas=parse_horas(meta.get("horas")),
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
