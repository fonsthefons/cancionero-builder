"""Rendering the whole book into one self-contained HTML page.

The page layout lives in web/template.html; this module only fills its
`{{ placeholders }}` with HTML fragments built from the songs.
"""

import json
import re
from html import escape
from pathlib import Path

from .horas import part_list
from .lyrics import is_chord_line, lyrics_columns, lyrics_html
from .text import slug

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


def horas_lists(horas):
    """[(anchor, name, [(group anchor, group, [(place, song)])])] for horas.yaml `lists:`."""
    out = []
    for name, spec in (horas.lists if horas else {}).items():
        anchor = f"list-{slug(name)}"
        groups = [(f"{anchor}-{slug(g)}", g, items) for g, items in part_list(horas, spec["part"], spec["groups"])]
        if groups:
            out.append((anchor, name, groups))
    return out


def horas_lists_html(horas, fold_tags=True, fold_subtags=True):
    return "\n".join(collapsible(anchor, "h2", name, "\n".join(
        collapsible(g_anchor, "h3", group, '<ul class="song-list">\n' + "\n".join(
            f'<li><a href="#{song.anchor}">{escape(where)}: {escape(song_label(song))}</a></li>'
            for where, song in items) + "\n</ul>", "subtag-index", is_open=not fold_subtags)
        for g_anchor, group, items in groups), "tag-index", is_open=not fold_tags)
        for anchor, name, groups in horas_lists(horas))


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
    for anchor, name, lists in horas_lists(horas):
        sub = "".join(f'<li><a class="nav-subtag" href="#{a}">{escape(g)}</a></li>' for a, g, _ in lists)
        items.append(f'<li><a class="nav-tag" href="#{anchor}">{escape(name)}</a>'
                     f'<ul class="nav-subtags">{sub}</ul></li>')
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
    if song.key:  # transpose.js rewrites it with the chords
        items.append(f'<span class="meta-item song-key">Key: {escape(song.key)}</span>')
    if song.link:
        label = "Spotify link" if "spotify.com" in song.link else "YouTube link" if "youtu" in song.link else "Link"
        items.append(
            f'<a class="meta-item" href="{escape(song.link)}" target="_blank" rel="noopener">{label}</a>'
        )
    return f'<p class="song-meta">{"".join(items)}</p>' if items else ""


# Pastel colours: 15 hues in a light and a deeper shade, as (hue, lightness %).
PILL_COLOURS = [(hue, light) for light in (87, 76) for hue in range(0, 360, 24)]


def colour_gap(a, b):
    """How different two pill colours look: hue distance, plus 45 for another shade."""
    return min(abs(a[0] - b[0]), 360 - abs(a[0] - b[0])) + (45 if a[1] != b[1] else 0)


def pill_colours(keys, together):
    """A colour per pill, far from the colours of the pills it shares songs with
    (`together`: key -> {other key: songs shared}); the more songs two pills share,
    the more their colours are kept apart. Ties: the least used colour."""
    colours, used = {}, {c: 0 for c in PILL_COLOURS}

    def cost(key, colour):
        clash = 0
        for other, shared in together[key].items():
            if other in colours:
                gap = colour_gap(colour, colours[other])
                # the same colour twice in one song: never (when avoidable)
                clash += (shared + 3) * max(0, 100 - gap) ** 2 + (10**9 if gap == 0 else 0)
        return clash, used[colour]

    for _ in range(4):  # the first pass places each pill; later passes improve them
        for key in keys:
            if key in colours:
                used[colours.pop(key)] -= 1
            colours[key] = min(PILL_COLOURS, key=lambda colour: cost(key, colour))
            used[colours[key]] += 1
    return colours


def tag_pills(groups):
    """{(tag id, subtag id or None): (css class, text, colour)} in contents order. Every
    tag and subtag has its own class and its label's first 3 letters; pills that
    appear in the same song get clearly different pastel colours."""
    labels, songs = {}, {}
    for group in groups:
        labels[(group.tag.id, None)] = group.tag.label
        for song in group.songs:
            songs.setdefault(id(song), set()).add((group.tag.id, None))
        for sub_id, label, members in group.subgroups:
            labels[(group.tag.id, sub_id)] = label
            for song in members:
                songs.setdefault(id(song), set()).update({(group.tag.id, None), (group.tag.id, sub_id)})
    together = {key: {} for key in labels}
    for keys in songs.values():
        for key in keys:
            for other in keys - {key}:
                together[key][other] = together[key].get(other, 0) + 1
    colours = pill_colours(labels, together)
    return {key: (f"k{i}", label.strip()[:3], colours[key]) for i, (key, label) in enumerate(labels.items())}


def pills_css(pills):
    return "\n".join(f".{cls}{{background:hsl({hue} 70% {light}%)}}" for cls, _, (hue, light) in pills.values())


def pills_html(song, pills):
    """One <i> per tag and per subtag of the song (book.yaml tag_pills)."""
    items = [
        f'<i class="{cls}">{escape(text)}</i>'
        for (tag_id, sub_id), (cls, text, _) in pills.items()
        if tag_id in song.tags and (sub_id is None or sub_id in song.tags[tag_id])
    ]
    return f'<p class="pills">{"".join(items)}</p>\n' if items else ""


def melody_html(song):
    """Staff and guitar tab, drawn by web/js/melody.js (abcjs)."""
    if not song.melody:
        return ""
    abc = "X:1\nM:none\nL:1/4\n" + song.melody
    return f'<div class="melody" data-abc="{escape(abc)}" data-tab="{escape(song.tab or "")}"></div>\n'


PLAY_HTML = '<button class="melody-play" aria-label="Play melody">▶ Melody</button>\n'


def with_play(controls):
    """The song's controls plus melody.js's play / pause button, at the end of the row."""
    head, tail = controls.rsplit("</div>", 1)
    return f"{head}  {PLAY_HTML}</div>{tail}"


PSALM_HTML = ('<button class="formula-pick" data-action="formula-pick">Choose fórmula…</button>\n'
              '<div class="psalm-formula"></div>\n')


def song_html(song, controls, psalm=False, pills=None):
    # --chars (widest line) lets CSS size the lyrics so every line fits the screen.
    # data-title / data-autor: plain values for the session list and search.
    # psalm: a fórmula picker, and room for the chosen fórmula (web/js/formula.js).
    # A psalm's play button shows only with a fórmula (CSS .song:has(.melody)).
    autor = f' data-autor="{escape(song.autor)}"' if song.autor else ""
    autor += f' data-key="{escape(song.key)}"' if song.key else ""
    if song.melody or psalm:
        controls = with_play(controls)
    return (
        f'<article class="song" id="{song.anchor}" data-title="{escape(song.title)}"{autor} '
        f'style="--chars: {lyrics_columns(song.body)}">\n'
        f"<h3>{escape(song_label(song))}</h3>\n"
        f"{song_meta_html(song)}\n"
        f"{pills_html(song, pills) if pills else ''}"
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


def formula_choices(book, groups, horas=None):
    """(psalm songs, fórmulas offered as [[group label, [[song id, title], ...], tag id], ...])
    from book.yaml psalm_tags / formula_tag; nothing when either is unset or empty.
    The tag id is the subtag's (or the tag's, for fórmulas without one).
    Songs without chords in a `formula_parts` part of the filled horas tree count as psalms."""
    psalms, formulas = set(), []
    wanted = {slug(p) for p in book.formula_parts}
    if horas and wanted:
        psalms.update(id(song) for part in horas.parts() if slug(part.label) in wanted
                      for song in part.songs if not any(map(is_chord_line, song.body.splitlines())))
    for group in groups:
        if group.tag.id in book.psalm_tags:
            psalms.update(id(song) for song in group.songs)
            psalms.update(id(song) for _, _, songs in group.subgroups for song in songs)
        if group.tag.id == book.formula_tag:
            parts = ([(group.tag.id, group.tag.label, group.songs)] if group.songs else []) + group.subgroups
            formulas = [[label, [[song.anchor, song.title] for song in songs], tag] for tag, label, songs in parts]
    return (psalms, formulas) if psalms and formulas else (set(), [])


def book_json(book, formulas=None):
    """Settings the page's scripts need (as `const BOOK = ...`)."""
    data = {"storagePrefix": book.storage_prefix, "notationSetting": book.notation_setting,
            "installTip": book.install_tip != "off", "progress": book.progress}
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
    psalms, formulas = formula_choices(book, groups, horas)
    # progress.js only in books with book.yaml progress: true.
    skip = ({"core.js"} | (set() if melodies else {"melody.js"}) | (set() if formulas else {"formula.js"})
            | (set() if book.progress else {"progress.js"}))
    scripts = [web / "js" / "core.js"] + sorted(p for p in (web / "js").glob("*.js") if p.name not in skip)
    if melodies:
        scripts.insert(0, web / "vendor" / "abcjs-basic-min.js")
    controls = read("song-controls.html").strip()
    pills = tag_pills(groups) if book.tag_pills else {}
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
            "book_json": book_json(book, formulas),
            "css": read("styles.css") + pills_css(pills),
            "scripts": "\n".join(
                f"<script>\n{p.read_text(encoding='utf-8')}</script>" for p in scripts
            ),
            "nav": nav_html(groups, horas),
            "tag_index": (horas_html(horas, book.fold_tags, book.fold_subtags) + "\n" if horas else "")
            + (horas_lists_html(horas, book.fold_tags, book.fold_subtags) + "\n" if horas_lists(horas) else "")
            + tag_index_html(groups, book.fold_tags, book.fold_subtags),
            "all_songs": collapsible("all-songs", "h2", "All Songs", song_list(songs), "tag-index",
                                     is_open=not book.fold_all_songs),
            "songs": "\n".join(song_html(song, controls, id(song) in psalms, pills) for song in songs),
        },
    )
