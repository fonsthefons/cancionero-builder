"""Add a whole list of songs to a book, without questions.

Two kinds of list are understood:

1. One song per line, "Title - Artist" or just "Title" (then the artist is the
   book's default_author, if it has one). Blank lines and "# ..." are skipped.
   A line ending with ":" starts a section; with `section` only that section is
   read, so "NOT YET:" lists can sit below it.

2. Ultimate Guitar's list of saved songs ("My tabs"), copied as text: for each
   song the artist (left out when it's the same as the song above), the title,
   with "(ver N)" for a version other than the first, and the date it was saved,
   sometimes followed by the kind of page (Tab, Power, Guitar Pro, Official):

       Passenger
       Golden Leaves (ver 3)
       Jan 28, 2015

For each song it does what adding by search does, but decides by itself: find
chord pages, read the best ones, clean the song (importer/clean.py), find a
Spotify link (or a YouTube one), and write the song file. With a UG list, that
exact version is taken from Ultimate Guitar (or the best rated chords version
when it's gone, saying so) and the saved date is kept (`added:`).
Books with `language_tags` tag each song "english" or "spanish"; others leave
songs untagged. When it isn't sure, it writes nothing and says why:
- the song is already in the book (same title and author);
- no readable chord page whose title has every word of the song's title (and
  whose artist matches, when one is given);
- no artist given and the pages found are by different artists.
"""

import datetime
import re
import time
from dataclasses import dataclass
from pathlib import Path

from builder.lyrics import is_chord_line
from builder.songs import SongError

from .clean import clean_song
from .fetch import Blocked, FetchError
from .language import detect
from .read import read_song_any_way
from .search import find_versions, plain_words, search
from .sites import SiteError
from .songfile import alias_for, book_songs, load_aliases, write_song
from .spotify import find_tracks
from .titles import book_names, load_fixes
from .websearch import SearchBusy
from .youtube import find_video

NO_ARTIST = {"popular", "anonimo", "anónimo", "tradicional", "traditional"}
MAX_VERSIONS = 4  # chord pages read per song before giving up
MIN_PAIRS = 4  # chord lines over lyrics needed for a page to count
PAUSE = 15  # seconds between songs, so the web search doesn't get busy
WAITS = [60, 300, 900, 1800, 3600]  # seconds to wait when a site says "too many requests"
GENERIC_ARTISTS = {"popular", "misc", "praise", "songs", "catolicas", "catolica", "musica", "musicas",
                   "cantos", "canciones", "religiosas", "cristianas", "worship", "christian", "unknown"}

DATE_RE = re.compile(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})\s*(.*)")
VERSION_RE = re.compile(r"\s*\(ver (\d+)\)\s*$")
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


@dataclass
class Wanted:
    title: str  # as written in the list (UG: without "(ver N)")
    artist: str = ""  # as written in the list ("" when not given)
    version: int | None = None  # UG version; None: any (and not a UG list)
    added: str | None = None  # ISO date it was saved (UG lists)
    kind: str = ""  # UG: "", "Tab", "Power", "Guitar Pro", "Official"...
    line: int = 0

    @property
    def from_ug_list(self):
        return self.version is not None

    @property
    def label(self):
        if self.from_ug_list:
            version = f" (ver {self.version})" if self.version > 1 else ""
            kind = f" [{self.kind}]" if self.kind else ""
            return f"{self.artist} - {self.title}{version}{kind}"
        return self.title + (f" - {self.artist}" if self.artist else "")


# ---------- reading the list ----------

def iso_date(month, day, year):
    return datetime.date(int(year), MONTHS.index(month) + 1, int(day)).isoformat()


def read_list(path, section=None, warn=print):
    """[Wanted] from a list file (either kind)."""
    lines = [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines()]
    numbered = [(n, line) for n, line in enumerate(lines, start=1) if line and not line.startswith("#")]
    if any(DATE_RE.fullmatch(line) for _, line in numbered):
        return read_ug_list(numbered, warn)

    wanted, current = [], None
    for n, text in numbered:
        if text.endswith(":") or (section and text.casefold() == section.casefold()):
            current = text.rstrip(":").strip()
            continue
        if section and (current or "").casefold() != section.casefold():
            continue
        title, _, artist = text.partition(" - ")
        wanted.append(Wanted(title.strip(), artist.strip(), line=n))
    return wanted


def read_ug_list(numbered, warn):
    wanted, block, artist = [], [], ""
    for n, line in numbered:
        date = DATE_RE.fullmatch(line)
        if not date:
            block.append((n, line))
            continue
        if len(block) >= 2:
            artist = block[-2][1]
        if not block or not artist:
            warn(f"Line {n}: a date with no song above it, skipped.")
            block = []
            continue
        if len(block) > 2:
            warn(f"Lines {block[0][0]}-{block[-3][0]}: not understood, skipped.")
        line_no, title = block[-1]
        version = VERSION_RE.search(title)
        wanted.append(Wanted(
            title=VERSION_RE.sub("", title).strip(),
            artist=artist,
            version=int(version.group(1)) if version else 1,
            added=iso_date(*date.group(1, 2, 3)),
            kind=date.group(4).strip(),
            line=line_no,
        ))
        block = []
    return wanted


def book_key(title, author):
    return " ".join(plain_words(title)), " ".join(plain_words(author or ""))


# ---------- choosing a version ----------

def chord_pairs(body):
    lines = body.split("\n")
    return sum(1 for i in range(1, len(lines)) if is_chord_line(lines[i - 1]) and lines[i].strip()
               and not is_chord_line(lines[i]))


def patiently(action, what, log):
    """Run action(); when a site says "too many requests", wait and try again."""
    for wait in WAITS + [None]:
        try:
            return action()
        except (Blocked, SearchBusy) as e:
            if wait is None:
                raise
            log(f"    {what}: {e}; waiting {wait // 60} min")
            time.sleep(wait)


def real_artist(name):
    """Artist words, or set() for compilations like 'Misc Praise Songs' / 'Músicas Católicas'."""
    words = set(plain_words(name or ""))
    return set() if not words or words <= GENERIC_ARTISTS else words


def choose_from_search(book, title, artist, log):
    """(result, draft, cleaned, note) from any allowed site, or a reason why not."""
    if artist.casefold() in NO_ARTIST:  # "popular" isn't a name to look for
        artist = ""
    title_words, artist_words = set(plain_words(title)), set(plain_words(artist))
    versions = []
    for result in patiently(lambda: search(title, artist, sites=book.sites), "search", log):
        if len(versions) == MAX_VERSIONS:
            break
        try:
            draft = patiently(lambda: read_song_any_way(result.url, sites=book.sites), "chord page", log)
        except (FetchError, SiteError, OSError):
            continue
        page_title = draft.title or result.label
        if not title_words <= set(plain_words(page_title)):
            continue
        page_artist = set(plain_words(draft.artist or "")) or set(plain_words(result.label + " " + result.url))
        if artist_words and not artist_words & page_artist:
            continue
        cleaned = clean_song(draft.text, draft.marked, ask=lambda line: False)
        if chord_pairs(cleaned.body) >= MIN_PAIRS:
            versions.append((result, draft, cleaned, ""))
    if not versions:
        return "no readable chord page with that title" + (f" by {artist}" if artist else "")
    if not artist:
        named = {}
        for _, draft, _, _ in versions:
            words = real_artist(draft.artist)
            if words:
                named.setdefault(frozenset(words), draft.artist)
        groups = list(named.values())
        if len(groups) > 1 and not all(set(plain_words(groups[0])) & set(plain_words(g)) for g in groups[1:]):
            return ("no artist given and the pages are by different artists: " + ", ".join(groups)
                    + " (add the artist to the list: Title - Artist)")
    return versions[0]


def choose_from_ug(book, item, log):
    """(result, draft, cleaned, note) for a UG-list item, or a reason why not."""
    exact = item.version if not item.kind else None  # tabs / Official: any chords version
    wanted, results = patiently(lambda: find_versions(item.title, item.artist, exact), "Ultimate Guitar search", log)
    if not results:
        return f'no chords on Ultimate Guitar for "{item.title}" by {item.artist}'
    order = [wanted] + [r for r in results if r is not wanted] if wanted else results
    note = ""
    if item.kind:
        note = f"the list has a {item.kind} page; used chords ver {order[0].version}"
    elif exact and not wanted:
        note = f"ver {exact} not found on Ultimate Guitar; used ver {order[0].version} instead"
    tried = []
    for result in order[:MAX_VERSIONS]:
        try:
            draft = patiently(lambda: read_song_any_way(result.url), "Ultimate Guitar page", log)
        except (FetchError, SiteError, OSError) as e:
            tried.append(f"ver {result.version}: {e}")
            continue
        cleaned = clean_song(draft.text, draft.marked, ask=lambda line: False)
        if chord_pairs(cleaned.body) < MIN_PAIRS:
            tried.append(f"ver {result.version}: hardly any chords over lyrics")
            continue
        if result is not order[0]:
            note = (note + "; " if note else "") + f"ver {order[0].version} unusable, used ver {result.version}"
        return result, draft, cleaned, note
    return "no usable chords page (" + "; ".join(tried) + ")"


# ---------- names ----------

def nice_title(typed, found):
    """The site's spelling (accents) with the capitals as typed: 'Dios está aqui' + 'Dios Está Aquí'
    -> 'Dios está aquí'. Falls back to what was typed."""
    if not found or plain_words(typed) != plain_words(found):
        return typed[:1].upper() + typed[1:]
    typed_words = re.findall(r"[^\W_]+", typed)
    found_words = re.findall(r"[^\W_]+", found)
    if len(typed_words) != len(found_words):
        return typed[:1].upper() + typed[1:]
    parts = re.split(r"([^\W_]+)", found)
    out, n = [], 0
    for part in parts:
        if re.fullmatch(r"[^\W_]+", part):
            mine = typed_words[n]
            part = part.lower() if mine.islower() else part
            n += 1
        out.append(part)
    title = "".join(out)
    return title[:1].upper() + title[1:]


def choose_author(book, typed, site_artist, aliases):
    """A remembered alias of the site's name; else the book's spelling of the typed
    artist ('schoenstatt' -> 'Schoenstatt'); else the site's name (not compilations
    like 'Misc Praise Songs'); else the typed artist; else 'popular'."""
    if site_artist and alias_for(site_artist, aliases) != site_artist:
        return alias_for(site_artist, aliases)
    if typed:
        authors = {}
        for _, song in book_songs(book):
            if song.autor:
                authors.setdefault(" ".join(plain_words(song.autor)), song.autor)
        known = authors.get(" ".join(plain_words(typed)))
        # 'Trigo' -> 'Trigo Trece' when exactly one author in the book contains the typed words
        containing = [a for key, a in authors.items() if set(plain_words(typed)) <= set(key.split())]
        if known or len(containing) == 1:
            return known or containing[0]
        if book.is_default_author(typed):
            return book.default_author
    if real_artist(site_artist):
        return site_artist
    if typed:
        return " ".join(w[:1].upper() + w[1:] for w in typed.split())
    return "popular"


def find_link(title, artist, log):
    try:
        tracks = patiently(lambda: find_tracks(title, artist), "web search", log)
        if tracks:
            return tracks[0].url
        return patiently(lambda: find_video(title, artist), "web search", log) or ""
    except FetchError:
        return ""


# ---------- adding ----------

def add_one(book, item, in_book, aliases, fixes, log):
    """('added', path, details) or ('uncertain', None, reason)."""
    if item.from_ug_list:
        title, author = book_names(item.artist, item.title, fixes)
        author = alias_for(author, aliases)
    else:
        title, author = item.title, item.artist or book.default_author or ""
    key = book_key(title, author)
    if key in in_book or (not author and any(k[0] == key[0] for k in in_book)):
        return "uncertain", None, f"already in the book as {in_book.get(key, 'a song with that title')}"

    try:
        chosen = choose_from_ug(book, item, log) if item.from_ug_list else choose_from_search(book, title, author, log)
    except FetchError as e:
        return "uncertain", None, f"search failed ({e}); try again later"
    if isinstance(chosen, str):
        return "uncertain", None, chosen
    result, draft, cleaned, note = chosen

    if not item.from_ug_list:
        title = nice_title(title, draft.title)
        author = choose_author(book, author, (draft.artist or "").strip(), aliases)
    capo = draft.capo or cleaned.capo
    tags, language_note = {}, ""
    if book.language_tags:
        language, sure = detect(cleaned.body)
        tags = {language: []}
        if not sure:
            language_note = f"language unclear, tagged {language}: check it"
    link = find_link(title, "" if author.casefold() in NO_ARTIST else author, log)

    try:
        path = write_song(book, title, author, capo, link, tags, cleaned.body, item.added)
    except SongError as e:
        return "uncertain", None, f"the song file came out invalid ({e})"
    in_book[book_key(title, author)] = path.stem
    details = [f"ver {result.version} from {result.url}" if item.from_ug_list else f"from {result.url}"]
    details += [n for n in (note, language_note) if n]
    if not link:
        details.append("no Spotify/YouTube link found")
    if cleaned.notes:
        details.append("notes: " + "; ".join(cleaned.notes))
    return "added", path, "; ".join(details)


def without_repeats(book, wanted, aliases, fixes):
    """UG lists: one item per song and author, the most recently saved one.
    Returns (kept in list order, [(dropped, kept)])."""
    def key(item):
        if item.from_ug_list:
            title, author = book_names(item.artist, item.title, fixes)
            return book_key(title, alias_for(author, aliases))
        return book_key(item.title, item.artist)

    chosen = {}
    for item in wanted:
        best = chosen.get(key(item))
        if best is None or (item.added or "", item.line) >= (best.added or "", best.line):
            chosen[key(item)] = item
    kept = set(id(item) for item in chosen.values())
    dropped = [(item, chosen[key(item)]) for item in wanted if id(item) not in kept]
    return [item for item in wanted if id(item) in kept], dropped


def record(report_file, section, entries):
    """Add entries under 'section:' in report_file (creating the section at the end)."""
    if not entries:
        return
    path = Path(report_file)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    header = f"{section}:"
    if header in [line.strip() for line in lines]:
        start = [line.strip() for line in lines].index(header)
        end = start + 1
        while end < len(lines) and lines[end].strip() and not lines[end].strip().endswith(":"):
            end += 1
        lines[end:end] = entries
    else:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", header] + entries
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_list(book, list_file, section=None, report=None, limit=None, pause=PAUSE, log=print):
    """Add every song of a list. Returns (added paths, uncertain lines)."""
    aliases, fixes = load_aliases(book), load_fixes(book.title_fixes_file)
    songs, repeats = without_repeats(book, read_list(list_file, section, warn=log), aliases, fixes)
    for item, kept in repeats:
        log(f"Repeat: {item.label} (line {item.line}) -> using line {kept.line}")
    in_book = {book_key(song.title, song.autor or book.default_author or ""): path.stem
               for path, song in book_songs(book)}
    if limit is not None:
        songs = songs[:limit]
    log(f"{len(songs)} songs to look at.")

    added, uncertain = [], []
    for n, item in enumerate(songs, start=1):
        if n > 1 and pause:
            time.sleep(pause)
        log(f"[{n}/{len(songs)}] {item.label}")
        status, path, details = add_one(book, item, in_book, aliases, fixes, log)
        log(f"    {status.upper()}: {path.name if path else ''} {details}")
        if status == "added":
            added.append(path)
            entry = f"{path.stem}  ({item.label}; {details})"
        else:
            entry = f"{item.label}  (line {item.line}; {details})"
            uncertain.append(entry)
        if report:  # as we go, so an interruption loses nothing
            record(report, "claude-added" if status == "added" else "claude-uncertain", [entry])
    log(f"\nAdded {len(added)}, uncertain {len(uncertain)}.")
    return added, uncertain
