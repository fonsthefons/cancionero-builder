"""A song book's folder and its settings (book.yaml).

A book is a folder (its own git repo, published with GitHub Pages) holding:

    book.yaml             settings (below); the only required file besides songs/
    songs/*.md            one file per song
    tags.yaml             optional: labels and order of tags and subtags
    author_aliases.yaml   optional: author names as sites write them -> as the book does
    title_fixes.yaml      optional: song titles as Ultimate Guitar writes them -> as the book does
    logo.svg ...          optional files named in book.yaml
    index.html, sw.js, manifest.webmanifest   written by the build
    icon-180.png, icon-512.png                home-screen icons (a default is copied in)

Every setting except `title` is optional; DEFAULTS documents them.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_NAME = "book.yaml"

DEFAULTS = {
    # Shown in the top bar and as the page title.
    "title": None,
    # Name under the home-screen icon (default: the title).
    "short_name": None,
    # Saved settings and the offline copy are stored under this name. Books on the
    # same site (<user>.github.io) must use different names. Default: the folder name.
    "storage_key": None,
    # The page's language (<html lang>), used by browsers for hyphenation and voices.
    "lang": "es",
    "theme_color": "#397380",
    "background_color": "#f4f1ea",
    # The artist of most songs: suggested when adding songs, not written in their
    # files and not shown in the book (e.g. "Hakuna" for Hakuna's own songbook).
    "default_author": None,
    # Contents page: tags (and their subtags) start folded; tap to open.
    "fold_tags": True,
    "fold_subtags": True,
    # Settings menu offers chord names as Do Re Mi.
    "notation_setting": True,
    # First visit on the website: how to add the book to the home screen.
    # "popup", "banner" or "off".
    "install_tip": "popup",
    # SVG file (in the book folder) shown before the title in the top bar.
    "logo": None,
    # SVG file and text shown above the contents (a cover). Text: "\n" breaks lines.
    "cover_logo": None,
    "cover_title": None,
    # Where songs are looked for: "all" (Ultimate Guitar, LaCuerda, Cifra Club and
    # any other site) or a list of site names, e.g. [ultimate_guitar].
    "sites": "all",
    # Suggest/assign the tag "english" or "spanish" from the lyrics.
    "language_tags": False,
    # Write the date a song was added (`added:`) in its file.
    "record_added": False,
    # Strict tags: every tag and subtag must be in tags.yaml (else the build stops).
    # Free tags (default): any tag written in a song appears in the book.
    "strict_tags": False,
    # The book's web address, shown in its README (filled in when it is created).
    "url": None,
}
INSTALL_TIPS = ("popup", "banner", "off")
KEY_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


class BookError(Exception):
    pass


@dataclass
class Book:
    root: Path
    settings: dict = field(default_factory=dict)

    # ---------- paths ----------

    @property
    def songs_dir(self):
        return self.root / "songs"

    @property
    def tags_file(self):
        return self.root / "tags.yaml"

    @property
    def aliases_file(self):
        return self.root / "author_aliases.yaml"

    @property
    def title_fixes_file(self):
        return self.root / "title_fixes.yaml"

    @property
    def name(self):
        return self.root.name

    # ---------- settings ----------

    def __getattr__(self, key):
        # book.title, book.fold_tags, ...: the setting or its default
        if key in DEFAULTS and "settings" in self.__dict__:
            return self.settings.get(key, DEFAULTS[key])
        raise AttributeError(key)

    @property
    def display_short_name(self):
        return self.short_name or self.title

    @property
    def storage_prefix(self):
        return (self.storage_key or self.name) + "."

    def is_default_author(self, autor):
        return bool(self.default_author) and (autor or "").strip().casefold() == self.default_author.casefold()

    def uses_site(self, site_name):
        return self.sites == "all" or site_name in self.sites

    def file(self, name):
        """Text of a file named in the settings (e.g. logo), relative to the book."""
        path = self.root / name
        if not path.is_file():
            raise BookError(f'{CONFIG_NAME}: file "{name}" not found in {self.root}')
        return path.read_text(encoding="utf-8")


def validate(settings):
    """List of problems in a book.yaml dict."""
    errors = []
    unknown = sorted(set(settings) - set(DEFAULTS))
    if unknown:
        errors.append(f"unknown setting(s): {', '.join(unknown)} (allowed: {', '.join(DEFAULTS)})")
    if not str(settings.get("title") or "").strip():
        errors.append("missing setting: title")
    if settings.get("install_tip", "popup") not in INSTALL_TIPS:
        errors.append(f"install_tip must be one of: {', '.join(INSTALL_TIPS)}")
    key = settings.get("storage_key")
    if key is not None and not KEY_RE.fullmatch(str(key)):
        errors.append("storage_key may only have lowercase letters, digits and -")
    sites = settings.get("sites", "all")
    if sites != "all" and not (isinstance(sites, list) and all(isinstance(s, str) for s in sites)):
        errors.append('sites must be "all" or a list such as [ultimate_guitar]')
    for name in ("fold_tags", "fold_subtags", "notation_setting", "language_tags", "record_added", "strict_tags"):
        if name in settings and not isinstance(settings[name], bool):
            errors.append(f"{name} must be true or false")
    return errors


def load_book(root):
    """The book in folder `root`. Raises BookError when it isn't a valid book."""
    root = Path(root).expanduser().resolve()
    config = root / CONFIG_NAME
    if not config.is_file():
        raise BookError(f"{root} is not a song book (it has no {CONFIG_NAME})")
    try:
        settings = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise BookError(f"{config}: {e}") from e
    if not isinstance(settings, dict):
        raise BookError(f"{config}: must be a set of `key: value` settings")
    errors = validate(settings)
    if errors:
        raise BookError(f"{config}:\n  " + "\n  ".join(errors))
    return Book(root, settings)


def settings_yaml(settings):
    """book.yaml text for a dict of settings, with a comment on what the file is."""
    lines = [
        "# Settings of this song book. Every setting is explained in the builder's",
        "# builder/book.py (DEFAULTS). Rebuild after changing them.",
        "",
    ]
    for key in DEFAULTS:
        if key in settings and settings[key] is not None:
            value = settings[key]
            if isinstance(value, list):  # sites: [ultimate_guitar]
                text = f"{key}: [{', '.join(value)}]"
            else:
                text = yaml.safe_dump({key: value}, allow_unicode=True, default_flow_style=False, width=1000).rstrip()
            lines.append(text)
    return "\n".join(lines) + "\n"

