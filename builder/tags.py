"""Tags and subtags: which exist, their labels and order, and grouping songs by them.

Free tags (the default): any tag or subtag written in a song file appears in
the book. A song may write a tag as an id (`primer_ciclo`) or as its label
(`Primer ciclo`, `Pasión`); both become the same id (`primer_ciclo`, `pasion`).

tags.yaml (optional) gives labels and order:

    <tag_id>:
      label: Text shown in the book
      subtags:            # optional
        <subtag_id>: Text shown in the book

Tags in tags.yaml come first, in its order; tags found only in songs follow,
alphabetically, labelled as the song wrote them ('primer_ciclo' -> 'Primer ciclo').

Strict tags (book.yaml `strict_tags: true`): only tags.yaml's tags and subtags
are allowed, and a tag with subtags needs at least one (the original rules).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .text import humanize, slug, spanish_sort_key


@dataclass
class Tag:
    id: str
    label: str
    subtags: dict[str, str] = field(default_factory=dict)  # id -> label, in order
    in_file: bool = True  # defined in tags.yaml (False: found in a song)
    subtags_in_file: set = field(default_factory=set)

    @property
    def is_flat(self):
        return not self.subtags


@dataclass
class TagGroup:
    """Songs of one tag, ready to render: flat songs plus (subtag label, songs)."""

    tag: Tag
    songs: list
    subgroups: list[tuple[str, str, list]]  # (subtag id, subtag label, songs)


def label_for(written):
    """Label for a tag as a song wrote it: an id gets humanized, a label is kept."""
    written = str(written).strip()
    return humanize(written) if written == slug(written) else written


class Taxonomy:
    def __init__(self, tags, strict=False):
        self.tags = {tag.id: tag for tag in tags}
        self.strict = strict

    @classmethod
    def load(cls, path, strict=False):
        """Tags from tags.yaml; no file means no predefined tags."""
        path = Path(path)
        raw = {}
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        tags = []
        for tag_id, spec in raw.items():
            spec = spec or {}
            subtags = {str(k): str(v) for k, v in (spec.get("subtags") or {}).items()}
            tags.append(Tag(id=str(tag_id), label=str(spec.get("label") or humanize(str(tag_id))),
                            subtags=subtags, subtags_in_file=set(subtags)))
        return cls(tags, strict=strict)

    def resolve(self, written):
        """A song's tags as written ({tag: [subtags]}) -> (by id, errors).

        Free tags: tags and subtags not seen before are added (labelled as written).
        Strict tags: they are errors, as are subtag rules broken.
        """
        resolved, errors = {}, []
        for written_tag, written_subs in written.items():
            tag_id = slug(written_tag) if str(written_tag) not in self.tags else str(written_tag)
            tag = self.tags.get(tag_id)
            if tag is None:
                if self.strict:
                    errors.append(f'unknown tag "{written_tag}" (allowed: {", ".join(self.tags)})')
                    continue
                tag = self.tags[tag_id] = Tag(tag_id, label_for(written_tag), in_file=False)
            sub_ids = []
            for written_sub in written_subs:
                sub_id = str(written_sub) if str(written_sub) in tag.subtags else slug(written_sub)
                if sub_id not in tag.subtags:
                    if self.strict:
                        errors.append(
                            f'unknown subtag "{written_sub}" under "{tag_id}"'
                            + (f' (allowed: {", ".join(tag.subtags)})' if tag.subtags else
                               f' ("{tag_id}" has no subtags, use `{tag_id}: []`)')
                        )
                        continue
                    tag.subtags[sub_id] = label_for(written_sub)
                if sub_id not in sub_ids:
                    sub_ids.append(sub_id)
            if self.strict and tag.subtags and not written_subs:
                errors.append(f'"{tag_id}" needs at least one subtag ({", ".join(tag.subtags)})')
            resolved[tag_id] = sub_ids
        return resolved, errors

    def finish(self):
        """After every song is resolved: tags and subtags found only in songs go
        after the ones from tags.yaml, alphabetically."""
        from_file = [tag for tag in self.tags.values() if tag.in_file]
        found = sorted((tag for tag in self.tags.values() if not tag.in_file),
                       key=lambda tag: spanish_sort_key(tag.label))
        self.tags = {tag.id: tag for tag in from_file + found}
        for tag in self.tags.values():
            extra = sorted((sid for sid in tag.subtags if sid not in tag.subtags_in_file),
                           key=lambda sid: spanish_sort_key(tag.subtags[sid]))
            ordered = [sid for sid in tag.subtags if sid in tag.subtags_in_file] + extra
            tag.subtags = {sid: tag.subtags[sid] for sid in ordered}

    def new_names(self):
        """Tags and subtags found in songs but not in tags.yaml, as 'Tag' / 'Tag: Subtag'."""
        names = []
        for tag in self.tags.values():
            if not tag.in_file:
                names.append(f"{tag.label} ({tag.id})")
            for sub_id, label in tag.subtags.items():
                if sub_id not in tag.subtags_in_file and tag.in_file:
                    names.append(f"{tag.label}: {label} ({tag.id}/{sub_id})")
        return names

    def choices(self):
        """(tag id, subtag id or None, label) for every tag and subtag, in order:
        what a song can be given (used when adding songs)."""
        found = []
        for tag in self.tags.values():
            found.append((tag.id, None, tag.label))
            for sub_id, sub_label in tag.subtags.items():
                found.append((tag.id, sub_id, f"{tag.label}: {sub_label}"))
        return found

    def group(self, songs):
        """Group songs by tag/subtag, in taxonomy order, skipping empty groups."""
        groups = []
        for tag in self.tags.values():
            tagged = [song for song in songs if tag.id in song.tags]
            if not tagged:
                continue
            flat = [song for song in tagged if not song.tags[tag.id]]
            subgroups = []
            for subtag_id, label in tag.subtags.items():
                members = [song for song in tagged if subtag_id in song.tags[tag.id]]
                if members:
                    subgroups.append((subtag_id, label, members))
            groups.append(TagGroup(tag=tag, songs=flat, subgroups=subgroups))
        return groups

    def to_yaml(self):
        """tags.yaml text for every tag and subtag (found ones included)."""
        lines = [
            "# Tags and subtags of this book: labels shown in the book, in this order.",
            "# Songs may also use tags that aren't listed here: they are added after these.",
            "#",
            "#   <tag_id>:",
            "#     label: Text shown in the book",
            "#     subtags:            # optional",
            "#       <subtag_id>: Text shown in the book",
            "",
        ]
        for tag in self.tags.values():
            lines.append(f"{tag.id}:")
            lines.append(f"  label: {yaml_text(tag.label)}")
            if tag.subtags:
                lines.append("  subtags:")
                lines.extend(f"    {sid}: {yaml_text(label)}" for sid, label in tag.subtags.items())
            lines.append("")
        return "\n".join(lines)


def add_to_tags_file(path, tag_id, tag_label, sub_id=None, sub_label=None):
    """Add a tag (or a subtag of a tag) to tags.yaml, keeping the rest of the file
    (comments included) as it is. Does nothing if it's already there."""
    path = Path(path)
    text = path.read_text(encoding="utf-8") if path.exists() else (
        "# Tags and subtags of this book: labels shown in the book, in this order.\n"
        "# Songs may also use tags that aren't listed here: they are added after these.\n"
    )
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.rstrip() == f"{tag_id}:"), None)
    if start is None:
        block = [f"{tag_id}:", f"  label: {yaml_text(tag_label)}"]
        if sub_id:
            block += ["  subtags:", f"    {sub_id}: {yaml_text(sub_label)}"]
        while lines and not lines[-1].strip():
            lines.pop()
        lines += [""] + block + [""]
    elif sub_id:
        end = start + 1
        while end < len(lines) and (not lines[end].strip() or lines[end].startswith((" ", "\t", "#"))):
            end += 1
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1  # the block's own lines, without the blank lines after it
        block = lines[start + 1:end]
        if any(re.match(rf"\s+{re.escape(sub_id)}\s*:", line) for line in block):
            return
        subtags_at = next((start + 1 + i for i, line in enumerate(block) if line.strip() == "subtags:"), None)
        new_line = f"    {sub_id}: {yaml_text(sub_label)}"
        if subtags_at is None:
            lines[end:end] = ["  subtags:", new_line]
        else:
            last = subtags_at
            while last + 1 < end and lines[last + 1].startswith("    "):
                last += 1
            lines.insert(last + 1, new_line)
    else:
        return
    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")


def yaml_text(text):
    """Text as a YAML value: plain if YAML reads it back unchanged, else quoted."""
    try:
        if yaml.safe_load(f"k: {text}") == {"k": text}:
            return text
    except yaml.YAMLError:
        pass
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
