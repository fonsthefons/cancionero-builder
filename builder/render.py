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


def horas_anchor(node):
    return "horas" + (f"-{node.path.replace('/', '-')}" if node.path else "")


def horas_html(node, fold_tags=True, fold_subtags=True, level=2):
    """The Liturgia de las Horas tree (only nodes with songs, see horas.fill): a
    folding section per branch; an hour lists "Part: N. Title" in part order."""
    if node.is_hour:
        body = '<ul class="song-list">\n' + "\n".join(
            f'<li><a href="#{song.anchor}">{escape(part.label)}: {escape(song_label(song))}</a></li>'
            for part in node.children for song in part.songs
        ) + "\n</ul>"
    else:
        body = "\n".join(horas_html(child, fold_tags, fold_subtags, level + 1) for child in node.children)
    return collapsible(
        horas_anchor(node), f"h{min(level, 6)}", node.label, body,
        "tag-index" if level == 2 else "subtag-index", is_open=not (fold_tags if level == 2 else fold_subtags),
    )


def nav_html(groups, horas=None):
    """Compact table of contents (tags and subtags) for the menu drawer."""
    items = [
        '<li><a class="nav-tag" href="#index">Contenido</a></li>',
        '<li><a class="nav-tag" href="#all-songs">All Songs</a></li>',
    ]
    if horas:
        branches = "".join(
            f'<li><a class="nav-subtag" href="#{horas_anchor(child)}">{escape(child.label)}</a></li>'
            for child in horas.children
        )
        items.append(f'<li><a class="nav-tag" href="#{horas_anchor(horas)}">{escape(horas.label)}</a>'
                     f'<ul class="nav-subtags">{branches}</ul></li>')
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


def melody_html(song):
    """Staff and guitar tab, drawn by web/js/melody.js (abcjs)."""
    if not song.melody:
        return ""
    abc = "X:1\nM:none\nL:1/4\n" + song.melody
    return f'<div class="melody" data-abc="{escape(abc)}" data-tab="{escape(song.tab or "")}"></div>\n'


PSALM_HTML = ('<button class="formula-pick" data-action="formula-pick">Choose fórmula…</button>\n'
              '<div class="psalm-formula"></div>\n')


def song_html(song, controls, psalm=False):
    # --chars (widest line) lets CSS size the lyrics so every line fits the screen.
    # data-title / data-autor: plain values for the session list and search.
    # psalm: a fórmula picker, and room for the chosen fórmula (web/js/formula.js).
    autor = f' data-autor="{escape(song.autor)}"' if song.autor else ""
    return (
        f'<article class="song" id="{song.anchor}" data-title="{escape(song.title)}"{autor} '
        f'style="--chars: {lyrics_columns(song.body)}">\n'
        f"<h3>{escape(song_label(song))}</h3>\n"
        f"{song_meta_html(song)}\n"
        f"{controls}\n"
        f"{PSALM_HTML if psalm else ''}"
        f"{melody_html(song)}"
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


def formula_choices(book, groups):
    """(psalm songs, fórmulas offered as [[group label, [[song id, title], ...]], ...])
    from book.yaml psalm_tags / formula_tag; nothing when either is unset or empty."""
    psalms, formulas = set(), []
    for group in groups:
        if group.tag.id in book.psalm_tags:
            psalms.update(id(song) for song in group.songs)
            psalms.update(id(song) for _, _, songs in group.subgroups for song in songs)
        if group.tag.id == book.formula_tag:
            parts = ([(group.tag.label, group.songs)] if group.songs else []) + [(label, songs) for _, label, songs in group.subgroups]
            formulas = [[label, [[song.anchor, song.title] for song in songs]] for label, songs in parts]
    return (psalms, formulas) if psalms and formulas else (set(), [])


def book_json(book, formulas=None):
    """Settings the page's scripts need (as `const BOOK = ...`)."""
    data = {"storagePrefix": book.storage_prefix, "notationSetting": book.notation_setting}
    if formulas:
        data["formulas"] = formulas
    # "</" can't appear inside a <script>; json.dumps never makes it but be safe
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_book(book, songs, groups, web_dir, horas=None):
    """horas: the filled horas.yaml tree (horas.fill), shown before the tags."""
    web = Path(web_dir)

    def read(name):
        return (web / name).read_text(encoding="utf-8")

    # core.js first (it defines helpers the feature scripts use), then the rest.
    # abcjs (480 kB) and melody.js only in books with a song `melody:`.
    # formula.js only in books with psalm fórmulas (book.yaml psalm_tags / formula_tag).
    melodies = any(song.melody for song in songs)
    psalms, formulas = formula_choices(book, groups)
    skip = {"core.js"} | (set() if melodies else {"melody.js"}) | (set() if formulas else {"formula.js"})
    scripts = [web / "js" / "core.js"] + sorted(p for p in (web / "js").glob("*.js") if p.name not in skip)
    if melodies:
        scripts.insert(0, web / "vendor" / "abcjs-basic-min.js")
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
            "book_json": book_json(book, formulas),
            "css": read("styles.css"),
            "scripts": "\n".join(
                f"<script>\n{p.read_text(encoding='utf-8')}</script>" for p in scripts
            ),
            "nav": nav_html(groups, horas),
            "tag_index": (horas_html(horas, book.fold_tags, book.fold_subtags) + "\n" if horas else "")
            + tag_index_html(groups, book.fold_tags, book.fold_subtags),
            "all_songs": collapsible("all-songs", "h2", "All Songs", song_list(songs), "tag-index"),
            "songs": "\n".join(song_html(song, controls, id(song) in psalms) for song in songs),
        },
    )
