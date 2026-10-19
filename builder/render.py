"""Rendering the whole book into one self-contained HTML page.

The page layout lives in web/template.html; this module only fills its
`{{ placeholders }}` with HTML fragments built from the songs.
"""

import json
import re
from html import escape
from pathlib import Path

from .lyrics import lyrics_columns, lyrics_html

PLACEHOLDER_RE = re.compile(r"{{\s*(\w+)\s*}}")


def fill_template(template, values):
    """Replace each {{ name }} once; inserted values are never re-scanned."""

    def replace(match):
        name = match.group(1)
        if name not in values:
            raise KeyError(f"template placeholder {{{{ {name} }}}} has no value")
        return values[name]

    return PLACEHOLDER_RE.sub(replace, template)


def tag_anchor(tag_id, subtag_id=None):
    return f"tag-{tag_id}" + (f"-{subtag_id}" if subtag_id else "")


def song_label(song):
    return f"{song.heading} - {song.autor}" if song.autor else song.heading


def song_link(song):
    return f'<li><a href="#{song.anchor}">{escape(song_label(song))}</a></li>'


def song_list(songs):
    return '<ul class="song-list">\n' + "\n".join(map(song_link, songs)) + "\n</ul>"


def collapsible(anchor, heading_tag, title, body, css_class, is_open=True):
    """A section that can be folded away. Printing always unfolds it (print.js)."""
    return (
        f'<details class="{css_class}" id="{anchor}"{" open" if is_open else ""}>'
        f"<summary><{heading_tag}>{escape(title)}</{heading_tag}></summary>\n"
        f"{body}\n</details>"
    )


def nav_html(groups):
    """Compact table of contents (tags and subtags) for the menu drawer."""
    items = [
        '<li><a class="nav-tag" href="#index">Contenido</a></li>',
        '<li><a class="nav-tag" href="#all-songs">All Songs</a></li>',
    ]
    for group in groups:
        subtags = "".join(
            f'<li><a class="nav-subtag" href="#{tag_anchor(group.tag.id, sub_id)}">'
            f"{escape(label)}</a></li>"
            for sub_id, label, _ in group.subgroups
        )
        items.append(
            f'<li><a class="nav-tag" href="#{tag_anchor(group.tag.id)}">'
            f"{escape(group.tag.label)}</a>"
            + (f'<ul class="nav-subtags">{subtags}</ul>' if subtags else "")
            + "</li>"
        )
    return '<ul class="nav">\n' + "\n".join(items) + "\n</ul>"


def tag_index_html(groups, fold_tags=True, fold_subtags=True):
    """Full index: every tag/subtag with the songs it contains. Folded sections
    show just their names until tapped (book.yaml fold_tags / fold_subtags)."""
    sections = []
    for group in groups:
        parts = [song_list(group.songs)] if group.songs else []
        for sub_id, label, songs in group.subgroups:
            parts.append(
                collapsible(
                    tag_anchor(group.tag.id, sub_id), "h3", label, song_list(songs), "subtag-index",
                    is_open=not fold_subtags,
                )
            )
        sections.append(
            collapsible(
                tag_anchor(group.tag.id), "h2", group.tag.label, "\n".join(parts), "tag-index",
                is_open=not fold_tags,
            )
        )
    return "\n".join(sections)


def song_meta_html(song):
    items = []
    if song.autor:
        items.append(f'<span class="meta-item">Autor: {escape(song.autor)}</span>')
    if song.capo:
        items.append(f'<span class="meta-item">Capo: {escape(song.capo)}</span>')
    if song.link:
        label = "Spotify link" if "spotify.com" in song.link else "YouTube link" if "youtu" in song.link else "Link"
        items.append(
            f'<a class="meta-item" href="{escape(song.link)}" target="_blank" rel="noopener">{label}</a>'
        )
    return f'<p class="song-meta">{"".join(items)}</p>' if items else ""


def song_html(song, controls):
    # --chars (widest line) lets CSS size the lyrics so every line fits the screen.
    # data-title / data-autor: plain values for the session list and search.
    autor = f' data-autor="{escape(song.autor)}"' if song.autor else ""
    return (
        f'<article class="song" id="{song.anchor}" data-title="{escape(song.title)}"{autor} '
        f'style="--chars: {lyrics_columns(song.body)}">\n'
        f"<h3>{escape(song_label(song))}</h3>\n"
        f"{song_meta_html(song)}\n"
        f"{controls}\n"
        f"{lyrics_html(song.body)}\n"
        "</article>"
    )


def svg_html(svg, css_class, label=None):
    """An SVG file's <svg> element, with a class (and a label, else hidden from
    screen readers). Leading XML declarations and comments are dropped."""
    start = svg.find("<svg")
    if start < 0:
        raise ValueError("not an SVG file (no <svg> element)")
    svg = svg[start:].strip()
    extra = f' class="{css_class}"' + (f' role="img" aria-label="{escape(label)}"' if label else ' aria-hidden="true"')
    return svg.replace("<svg", "<svg" + extra, 1)


def cover_html(book):
    """Logo and title above the contents (book.yaml cover_logo / cover_title)."""
    if not book.cover_logo and not book.cover_title:
        return ""
    parts = ['<header class="cover">']
    if book.cover_logo:
        parts.append("    " + svg_html(book.file(book.cover_logo), "logo", label=book.title))
    if book.cover_title:
        lines = "<br>".join(escape(line) for line in str(book.cover_title).split("\n"))
        parts.append(f'    <p class="cover-title">{lines}</p>')
    parts.append("  </header>\n  ")
    return "\n".join(parts)


def book_json(book):
    """Settings the page's scripts need (as `const BOOK = ...`)."""
    data = {"storagePrefix": book.storage_prefix, "notationSetting": book.notation_setting}
    # "</" can't appear inside a <script>; json.dumps never makes it but be safe
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_book(book, songs, groups, web_dir):
    web = Path(web_dir)

    def read(name):
        return (web / name).read_text(encoding="utf-8")

    # core.js first (it defines helpers the feature scripts use), then the rest.
    scripts = [web / "js" / "core.js"] + sorted(
        p for p in (web / "js").glob("*.js") if p.name != "core.js"
    )
    controls = read("song-controls.html").strip()
    install_tip = {"popup": read("parts/install-tip-popup.html"),
                   "banner": read("parts/install-tip-banner.html")}.get(book.install_tip, "")

    return fill_template(
        read("template.html"),
        {
            "lang": escape(book.lang),
            "title": escape(book.title),
            "short_name": escape(book.display_short_name),
            "theme_color": escape(book.theme_color),
            "logo": svg_html(book.file(book.logo), "logo-mark") if book.logo else "",
            "notation_setting": read("parts/notation-setting.html").rstrip("\n") if book.notation_setting else "",
            "cover": cover_html(book),
            "install_tip": install_tip.rstrip("\n"),
            "book_json": book_json(book),
            "css": read("styles.css"),
            "scripts": "\n".join(
                f"<script>\n{p.read_text(encoding='utf-8')}</script>" for p in scripts
            ),
            "nav": nav_html(groups),
            "tag_index": tag_index_html(groups, book.fold_tags, book.fold_subtags),
            "all_songs": collapsible("all-songs", "h2", "All Songs", song_list(songs), "tag-index"),
            "songs": "\n".join(song_html(song, controls) for song in songs),
        },
    )
