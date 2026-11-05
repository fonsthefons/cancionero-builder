"""Liturgia de las Horas: an optional horas.yaml with a tree of hours, shown first
in the contents. Songs are placed in its parts with `horas:` in their files.

    label: Liturgia de las Horas
    parts:                 # only holds YAML anchors (&laudes) to reuse lists
      laudes: &laudes [Apertura, Himno, Salmo 1, Benedictus]
    tree:
      Semana I:            # a mapping is a branch
        Domingo:
          Laudes: *laudes  # a list is an hour; its items are its parts

Every node's id is slug(label); a part's slot path joins the ids with "/", e.g.
semana_i/domingo/laudes/himno.

    lists:                 # optional: a section listing one part of every hour
      Himnos: {part: Himno, groups: [Laudes, Vísperas, Completas]}

shows "Himnos" > "Laudes" > "Lunes I: 5. Alfarero del hombre" (see part_list).
"""

import re
from dataclasses import dataclass, field, replace
from fnmatch import fnmatchcase
from pathlib import Path

import yaml

from .songs import SongError
from .text import slug

DEFAULT_LABEL = "Liturgia de las Horas"


@dataclass
class Node:
    label: str
    path: str  # ids joined with "/" ("" for the root)
    children: list = field(default_factory=list)  # an hour's children are its parts
    is_part: bool = False
    songs: list = field(default_factory=list)  # parts only, filled by fill()
    lists: dict = field(default_factory=dict)  # root only: horas.yaml `lists:`

    @property
    def is_hour(self):
        return bool(self.children) and self.children[0].is_part

    def parts(self):
        if self.is_part:
            yield self
        for child in self.children:
            yield from child.parts()

    def unmatched(self, patterns):
        """The patterns (a song's `horas:`) that match no part."""
        paths = [part.path for part in self.parts()]
        return [p for p in patterns if not any(fnmatchcase(path, normalize(p)) for path in paths)]


def normalize(pattern):
    """'Semana I/Domingo/*' -> 'semana_i/domingo/*': segments without glob
    characters are written as ids. `*` also crosses "/"."""
    return "/".join(s if any(c in s for c in "*?[") else slug(s) for s in str(pattern).split("/"))


def node(label, value, parent_path):
    path = "/".join(filter(None, [parent_path, slug(label)]))
    if isinstance(value, dict):
        return Node(str(label), path, [node(k, v, path) for k, v in value.items()])
    if isinstance(value, list):
        return Node(str(label), path, [Node(str(p), f"{path}/{slug(p)}", is_part=True) for p in value])
    raise SongError(f'horas.yaml: "{label}" must be a mapping (a branch) or a list of parts')


def load_horas(path):
    """The tree in horas.yaml (the root Node), or None when the book has none."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise SongError(f"{path}: {e}") from e
    if not isinstance(raw, dict) or not isinstance(raw.get("tree"), dict):
        raise SongError(f"{path}: needs a `tree:` mapping (see builder/horas.py)")
    lists = raw.get("lists") or {}
    if not isinstance(lists, dict) or not all(
            isinstance(v, dict) and v.get("part") and isinstance(v.get("groups"), list) for v in lists.values()):
        raise SongError(f"{path}: `lists:` must be like `Himnos: {{part: Himno, groups: [Laudes, Vísperas]}}`")
    return Node(str(raw.get("label") or DEFAULT_LABEL), "", [node(k, v, "") for k, v in raw["tree"].items()],
                lists={str(k): {"part": str(v["part"]), "groups": [str(g) for g in v["groups"]]}
                       for k, v in lists.items()})


WEEK = re.compile(r"semana\s+(\S+)", re.I)


def place(labels, group):
    """Where a part is, from its branch labels without the group's word:
    [Semana I, Lunes, Laudes] -> "Lunes I"; [Semana I, Domingo, Primeras Vísperas] ->
    "Domingo I (primeras)"; [Completas, Domingo (primeras Completas)] -> "Domingo (primeras)"."""
    rest = [" ".join(re.sub(re.escape(group), "", label, flags=re.I).split()).replace("( ", "(").replace(" )", ")")
            for label in labels]
    weeks = [m.group(1) for m in map(WEEK.fullmatch, rest) if m]
    others = [r for r in rest if r and not WEEK.fullmatch(r)]
    head = " ".join(others[:1] + weeks)
    return head + "".join(f" ({r.casefold()})" for r in others[1:])


def part_list(tree, part, groups):
    """[(group, [(place, song)])]: every `part` of the filled tree, in tree order, under
    the first group whose word is in one of its branch labels (empty groups left out)."""
    found = {g: [] for g in groups}

    def walk(node, labels):
        for child in node.children:
            if child.is_part and slug(child.label) == slug(part):
                group = next((g for g in groups if any(g.casefold() in l.casefold() for l in labels)), None)
                if group:
                    found[group].extend((place(labels, group), song) for song in child.songs)
            elif not child.is_part:
                walk(child, labels + [child.label])

    walk(tree, [])
    return [(g, items) for g, items in found.items() if items]


def fill(tree, songs):
    """Copy of the tree with each part's songs (in song order), keeping only nodes
    with a song somewhere below; None when no song is placed."""
    if tree.is_part:
        found = [song for song in songs if any(fnmatchcase(tree.path, normalize(p)) for p in song.horas)]
        return replace(tree, songs=found) if found else None
    children = [c for c in (fill(child, songs) for child in tree.children) if c]
    return replace(tree, children=children) if children else None
