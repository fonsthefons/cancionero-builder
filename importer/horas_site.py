"""Read the Liturgia de las Horas site (github.com/liturgiadelashoras/liturgiadelashoras.github.io,
cloned locally) and export the 4-week psalter (salterio).

The site has one folder per day, sync/<year>/<mes>/<dd>/, with index.htm (season, day,
"De la Feria. Salterio I") and one page per hour (laudes.htm, visperas.htm, completas.htm…).
Pages are ISO-8859-1 HTML where red FONTs are headings/markers (Salmo 23 - …, Ant 1., V.)
and black FONTs are the text, lines split by <BR>, stanzas by <BR><BR>.

read_day() and read_hour() are generic (any day, any hour, any season), so propios and
comunes (Adviento, Común de pastores…) can be read later with the same code. salterio()
picks plain Ordinary Time weekdays to build Semana I-IV.

    .venv/bin/python -m importer.horas_site <cloned repo> <out folder>
"""

import datetime
import json
from collections import Counter
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from builder.tags import yaml_text
from builder.text import slug

MONTHS = "ene feb mar abr may jun jul ago sep oct nov dic".split()
DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
WEEKS = ["I", "II", "III", "IV"]
RED = "#ff0000"
MARKER = re.compile(r"^(Ant\.?(?:\s*\d+)?\.?|V\.|R\.|N\.)$", re.I)
GOSPEL = re.compile(r"^c[aá]ntico de (zacar[ií]as|mar[ií]a|sime[oó]n)", re.I)


# ---------- one page ----------

class _Runs(HTMLParser):
    """The page body as [(is_red, text)], <BR> as "\n", source line wraps as spaces."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.colors = []
        self.runs = []
        self.on = False  # only inside <div id="cuerpo"> (skips the size links and the nav)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and attrs.get("id") == "cuerpo":
            self.on = True
        elif tag == "font":
            self.colors.append((attrs.get("color") or "").lower())
        elif tag == "br":
            self.add("\n")

    def handle_endtag(self, tag):
        if tag == "font" and self.colors:
            self.colors.pop()
        elif tag == "body":
            self.on = False

    def handle_data(self, data):
        self.add(re.sub(r"\s+", " ", data))

    def add(self, text):
        if not self.on:
            return
        red = bool(self.colors) and self.colors[-1] == RED
        if self.runs and self.runs[-1][0] == red:
            self.runs[-1] = (red, self.runs[-1][1] + text)
        else:
            self.runs.append((red, text))


def _tokens(page_html):
    """[(kind, text)]: ("head", line) for red lines, ("text", line) for black lines,
    ("blank", "") for empty black lines (stanza breaks)."""
    parser = _Runs()
    parser.feed(page_html)
    runs = []
    # A run in the middle of a line of the other colour joins that line: the black
    # "Aleluya" inside a red rubric, the red "R." in "(R. Aleluya)".
    raw = parser.runs
    for i, (red, text) in enumerate(raw):
        after = raw[i + 1][1].split("\n", 1)[0] if i + 1 < len(raw) else ""
        mid_line = runs and runs[-1][0] != red and "\n" not in text \
            and runs[-1][1].rsplit("\n", 1)[-1].strip() and after.strip()
        if mid_line:
            runs[-1] = (runs[-1][0], runs[-1][1] + text)
        elif runs and runs[-1][0] == red:
            runs[-1] = (red, runs[-1][1] + text)
        else:
            runs.append((red, text))
    out = []
    for red, text in runs:
        segments = text.split("\n")
        for n, line in enumerate(segments):
            line = re.sub(r" {2,}", " ", line.replace("\xa0", " ").strip())
            if red:
                if line:
                    out.append(("head", line))
            elif line:
                out.append(("text", line))
            elif n < len(segments) - 1:  # an empty line ended by <BR>, not the rest of one
                out.append(("blank", ""))
    return out


def is_section(heading):
    """Plain capital headings (SALMODIA, LECTURA BREVE Rm 13, 11b) start a section."""
    head = heading.split("(")[0]
    return bool(re.search(r"[A-ZÁÉÍÓÚÑ]{4}", head)) and not re.search(r"[a-záéíóúñ]{3}", head)


def kind_of(heading):
    h = heading.casefold()
    if GOSPEL.match(heading):
        return "evangelico"
    if re.match(r"salmo\b", h):  # not SALMODIA
        return "salmo"
    if re.match(r"c[aá]ntico\b(?! evang)", h):
        return "cantico"
    if h.startswith("himno"):
        return "himno"
    if is_section(heading):
        return "seccion"
    return "otro"


def read_hour(page_html):
    """An hour page as a list of parts, in page order:
    {heading, kind, section, antiphon, text}. `section` is the last plain heading
    (SALMODIA, LECTURA BREVE…); `antiphon` is the one announced before the part
    (Ant 1. …), `text` has stanzas split by blank lines, V./R. lines kept, and `notes`
    holds the red rubrics inside a psalm ("El cántico siguiente se dice con…")."""
    parts, section, pending, marker = [], "", None, None
    current, in_psalm = None, False  # in_psalm: until its antiphon is repeated
    for kind, text in _tokens(page_html):
        if kind == "head":
            if MARKER.match(text):
                marker = text
                continue
            if in_psalm and kind_of(text) == "otro":
                current["notes"].append(text)
                continue
            if kind_of(text) == "seccion":
                section = text.split("(")[0].strip()  # e.g. "LECTURA BREVE Rm 13, 11b" stays whole
            current = {"heading": text, "kind": kind_of(text), "section": section,
                       "antiphon": None, "lines": [], "notes": []}
            in_psalm = current["kind"] in ("salmo", "cantico", "evangelico")
            if pending and in_psalm:
                current["antiphon"], pending = pending, None
            parts.append(current)
            marker = None
            continue
        if marker and kind == "text":
            if marker.lower().startswith("ant"):
                # "Ant 1." announces the next psalm's antiphon; a bare "Ant." after a psalm
                # repeats it (dropped), except before the gospel canticle, where it's new.
                bare = not re.search(r"\d", marker)
                repeat = bare and current and current["antiphon"] is not None and current["lines"]
                if repeat:
                    in_psalm = False
                else:
                    pending = text
            elif current is not None:
                current["lines"].append(f"{marker[0]}. {text}")
            marker = None
            continue
        if current is not None:
            current["lines"].append(text if kind == "text" else "")
    for part in parts:
        part["text"] = "\n".join(part.pop("lines")).strip("\n")
        part["text"] = re.sub(r"\n{3,}", "\n\n", part["text"])
    return parts


def read_day(day_dir):
    """{date, season, title, label, salterio, hours} for one day folder. `hours` maps
    the page name (laudes, visperas…) to its parts; `salterio` is "I".."IV" or None."""
    day_dir = Path(day_dir)
    year, month, day = day_dir.parts[-3:]
    lines = [line for kind, line in _tokens(_page(day_dir / "index.htm")) if kind == "head"]
    season, title, label = (lines + ["", "", ""])[:3]
    found = re.search(r"Salterio (IV|I{1,3})\b", label)
    return {
        "date": datetime.date(int(year), MONTHS.index(month) + 1, int(day)),
        "season": season, "title": title, "label": label,
        "salterio": found.group(1) if found else None,
        "hours": {p.stem: read_hour(_page(p)) for p in sorted(day_dir.glob("*.htm")) if p.stem != "index"},
    }


def _page(path):
    return Path(path).read_bytes().decode("latin-1")


# ---------- the psalter ----------

def psalmody(parts):
    """The psalms and canticles of the hour's SALMODIA (not the invitatorio nor the
    gospel canticle)."""
    return [p for p in parts if p["kind"] in ("salmo", "cantico") and p["section"].startswith("SALMODIA")]


def himnos(parts):
    """The hour's himno (a one-item list, as salterio() wants a list of parts)."""
    return [p for p in parts if p["kind"] == "himno"]


def himno_title(part):
    """'Himno: SEÑOR, TÚ ME LLAMASTE.' -> 'Señor, tú me llamaste': the heading's words
    taken from the text, which has their real case; the heading capitalized otherwise."""
    words = part["heading"].split(":", 1)[-1].strip(" .").split()
    first = part["text"].split()[:len(words)]
    plain = lambda ws: [w.strip(",.;:!?¡¿").casefold() for w in ws]
    if plain(first) == plain(words):
        return " ".join(first).strip(",.;:")
    return " ".join(words).capitalize()


def day_dirs(repo):
    return sorted(Path(repo).glob("sync/20*/*/[0-3][0-9]"), key=lambda d: read_date(d))


def read_date(d):
    return datetime.date(int(d.parts[-3]), MONTHS.index(d.parts[-2]) + 1, int(d.parts[-1]))


def is_plain(day):
    return day["season"].startswith("TIEMPO ORDIN") and day["label"].startswith("De la Feria") and day["salterio"]


def slots(day, next_day):
    """[(slot path prefix, hour page)] this plain day gives to the psalter.
    Saturday evening is Sunday's I Vísperas (next week) and Domingo's primeras Completas.
    The evening hours count only when the next day is plain too: otherwise they may be
    the I Vísperas of a solemnity (a "feria" Thursday before the Sagrado Corazón)."""
    week = day["salterio"]
    weekday = DAYS[day["date"].weekday()]
    w = f"semana_{week.lower()}"
    out = [(f"{w}/{slug(weekday)}/laudes", "laudes")]
    if not (next_day and is_plain(next_day)):
        return out
    if weekday == "Sábado":
        out.append((f"semana_{next_day['salterio'].lower()}/domingo/primeras_visperas", "visperas"))
        out.append(("completas/" + slug("Domingo (primeras Completas)"), "completas"))
    elif weekday == "Domingo":
        out.append((f"{w}/domingo/segundas_visperas", "visperas"))
        out.append(("completas/" + slug("Domingo (segundas Completas)"), "completas"))
    else:
        out.append((f"{w}/{slug(weekday)}/visperas", "visperas"))
        out.append((f"completas/{slug(weekday)}", "completas"))
    return out


PART_NAMES = {  # order of the psalmody in each hour, as in horas.yaml
    "laudes": ["salmo_1", "cantico", "salmo_2"],
    "visperas": ["salmo_1", "salmo_2", "cantico"],
}


def part_names(page, count):
    if page == "completas":
        return ["salmo"] if count == 1 else [f"salmo_{i + 1}" for i in range(count)]
    return PART_NAMES[page] if count == 3 else [f"salmo_{i + 1}" for i in range(count)]


def salterio(repo, samples=5, pick=psalmody):
    """{slot prefix: {page, sources: [dates], parts: pick(hour parts)}}, plus notes on slots
    whose samples disagree. The site has typos (a missing verse range, a lost stanza break), so
    each slot reads `samples` plain days and keeps the version most of them share."""
    dirs = day_dirs(repo)
    found = {}  # prefix -> (page, [(date, parts)])
    days = [None] * len(dirs)

    def day_at(i):
        if days[i] is None:
            days[i] = read_day(dirs[i])
        return days[i]

    for i in range(len(dirs)):
        day = day_at(i)
        if not is_plain(day):
            continue
        next_day = day_at(i + 1) if i + 1 < len(dirs) else None
        for prefix, page in slots(day, next_day):
            page_, got = found.setdefault(prefix, (page, []))
            if len(got) < samples and page in day["hours"]:
                got.append((day["date"].isoformat(), pick(day["hours"][page])))

    result, problems = {}, []
    for prefix, (page, got) in found.items():
        votes = Counter(_key(parts) for _, parts in got)
        best, count = votes.most_common(1)[0]
        if count <= len(got) // 2:
            problems.append(f"{prefix}: no majority among {', '.join(d for d, _ in got)} ({count} agree)")
        parts = next(parts for _, parts in got if _key(parts) == best)
        result[prefix] = {"page": page, "sources": [d for d, p in got if _key(p) == best], "parts": parts}
    return result, problems


def _key(parts):
    return json.dumps([(p["heading"], p["antiphon"], p["text"]) for p in parts], ensure_ascii=False)


# ---------- writing ----------

PSALM = re.compile(r"salmo\s+(\d+)(.*)", re.I)
# the title starts after " - " or at a capital word that isn't a psalm part (I-IV, A, B)
TITLE_START = re.compile(r"\s?[-–]\s|\s(?=(?!(?:I{1,3}|IV|A|B)\b)[A-ZÁÉÍÓÚÑ¿¡]{2,})")
BIBLE_REF = re.compile(r"((?:[1-3]\s?)?[A-Z][a-z]{0,3}\.?\s*\d+\s*,\s*[\d\s.,;ab—–-]+)\s*$")


def song_title(heading):
    """'SALMO 62, 2-9 - EL ALMA…' -> 'Salmo 62, 2-9'; 'Cántico: … Is 33,13-16' ->
    'Cántico Is 33, 13-16'; psalm parts keep their roman numeral ('Salmo 17, 2-30 I')."""
    psalm = PSALM.match(heading)
    if psalm:
        verses = TITLE_START.split(psalm.group(2) + " ")[0]
        return " ".join(f"Salmo {psalm.group(1)}{verses}".replace(",", ", ").split()).strip(" .,")
    ref = BIBLE_REF.search(heading.strip(" ."))
    if ref:
        ref = re.sub(r"^(\w+)\.", r"\1", ref.group(1)).replace("—", "-").replace("–", "-")
        return "Cántico " + " ".join(ref.replace(",", ", ").split()).strip(" .,;")
    return heading.strip(" .")


def song_id(heading):
    """File name: 'salmo-062-2-9', 'cantico-is-33-13-16' (psalm numbers padded to sort)."""
    title = song_title(heading)
    title = re.sub(r"^Salmo (\d+)", lambda m: f"Salmo {int(m.group(1)):03d}", title)
    return slug(title).replace("_", "-")


def songs_from(result):
    """{song id: {title, heading, text, horas: [slot paths]}}; the same psalm in several
    slots becomes one song, unless its text differs (then it gets a -2 id)."""
    songs = {}
    for prefix in sorted(result):
        slot = result[prefix]
        parts = slot["parts"] or []
        for name, part in zip(part_names(slot["page"], len(parts)), parts):
            base = song_id(part["heading"])
            sid, n = base, 2
            while sid in songs and songs[sid]["text"] != part["text"]:
                sid, n = f"{base}-{n}", n + 1
            song = songs.setdefault(sid, {"title": song_title(part["heading"]), "heading": part["heading"],
                                          "text": part["text"], "horas": []})
            song["horas"].append(f"{prefix}/{name}")
    return songs


def song_text(song):
    horas = "\n".join(f"  - {h}" for h in song["horas"])
    # the Gloria as the book writes it (songs/salmo-086.md): its last line in two
    text = song["text"].replace("ahora y siempre, por los siglos", "ahora y siempre,\npor los siglos")
    return (f"---\ntitle: {yaml_text(song['title'])}\n"
            f"song_tags:\n  salmos: []\nhoras:\n{horas}\n---\n\n{text}\n")


def main(repo, out):
    out = Path(out)
    result, problems = salterio(repo)
    (out / "songs").mkdir(parents=True, exist_ok=True)
    (out / "salterio.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    songs = songs_from(result)
    for sid, song in songs.items():
        (out / "songs" / f"{sid}.md").write_text(song_text(song), encoding="utf-8")
    empty = [p for p, s in result.items() if not s["parts"]]
    print(f"{len(result)} slots, {len(songs)} songs, {len(problems)} disagreements, {len(empty)} empty")
    for line in problems + [f"{p}: no psalms" for p in empty]:
        print(" ", line)


if __name__ == "__main__":
    main(*sys.argv[1:3])
