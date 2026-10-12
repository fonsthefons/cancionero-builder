"""Find chord pages for a song title + artist.

Two sources, no account or key needed:
- Ultimate Guitar's own search page, which embeds its results as JSON. Only
  public "Chords" sheets are kept (tabs, Guitar Pro, Power, Official and Pro
  versions can't be shown as chords over lyrics), whose title has every word of
  the song's title and whose artist has every word of the artist, when given.
  Each carries UG's version number ("ver 3" on the site), votes and rating, and
  whether it is a live performance (UG numbers live versions separately).
- DuckDuckGo's plain-HTML search for "<title> <artist> acordes", for the other
  sites (LaCuerda, Cifra Club, any other); only when the book uses them
  (book.yaml `sites`).

Results that don't mention the title (and the artist, when given) are dropped,
the same page under different addresses is listed once, and at most
MAX_PER_SITE versions are listed per site. Pages from supported sites come
first, in the order of sites.SITES; other sites follow (read with the generic
reader, which may or may not work).
"""

import html
import json
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass

from .fetch import FetchError, download
from .sites import SITES, generic, site_for
from .websearch import duckduckgo

MAX_RESULTS = 8
MAX_PER_SITE = 3  # versions shown from one site, so other sites still appear
MAX_PAGES = 3  # Ultimate Guitar search pages read (50 results each)


@dataclass
class Result:
    url: str
    label: str  # what to show: page title or "Artist - Song (ver 2), rated 4.8 by 120"
    # Ultimate Guitar only:
    artist: str = ""
    song: str = ""
    version: int = 1
    votes: int = 0
    rating: float = 0.0
    live: bool = False

    @property
    def site_name(self):
        site = site_for(self.url)
        return site.NAME if site is not generic else urllib.parse.urlparse(self.url).hostname.removeprefix("www.")

    @property
    def rank(self):
        site = site_for(self.url)
        return SITES.index(site) if site in SITES else len(SITES)


def plain_words(text):
    text = unicodedata.normalize("NFD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return [w for w in re.split(r"[^a-z0-9]+", text) if len(w) > 2 or w.isdigit()]


def mentions(result, words):
    haystack = " ".join(plain_words(urllib.parse.unquote(result.url) + " " + result.label))
    return all(word in haystack for word in words)


# ---------- Ultimate Guitar ----------

def ug_search_page(query, page=1):
    """(results as Ultimate Guitar gives them, number of pages)."""
    url = "https://www.ultimate-guitar.com/search.php?search_type=title&value=" + urllib.parse.quote(query)
    if page > 1:
        url += f"&page={page}"
    try:
        text = download(url)
    except FetchError as e:
        if "404" in str(e):  # Ultimate Guitar answers "nothing found" with a 404
            return [], 0
        raise
    store = re.search(r'class="js-store"\s+data-content="([^"]*)"', text)
    if not store:
        return [], 0
    try:
        data = json.loads(html.unescape(store.group(1)))["store"]["page"]["data"]
        return data.get("results") or [], (data.get("pagination") or {}).get("total") or 1
    except (KeyError, TypeError, json.JSONDecodeError):
        return [], 0


def ug_result(raw):
    performance = (raw.get("recording") or {}).get("performance")
    result = Result(
        url=raw["tab_url"],
        label="",
        artist=raw.get("artist_name") or "",
        song=raw.get("song_name") or "",
        version=raw.get("version") or 1,
        votes=raw.get("votes") or 0,
        rating=raw.get("rating") or 0.0,
        live=bool(performance),
    )
    result.label = f"{result.artist} - {result.song} (ver {result.version}{', live' if result.live else ''})" + (
        f", rated {result.rating:.1f} by {result.votes}" if result.votes else "")
    return result


def ug_chord_results(title, artist="", query=None, stop=None):
    """Every matching Chords result, reading up to MAX_PAGES pages of the search
    for `query` (default "artist title"). `stop(results)` ends the reading early."""
    title_words, artist_words = plain_words(title), plain_words(artist)
    results, seen = [], set()
    query = query or f"{artist} {title}".strip()
    page, pages = 1, 1
    while page <= min(pages, MAX_PAGES):
        found, pages = ug_search_page(query, page)
        for raw in found:
            if raw.get("type") != "Chords" or not raw.get("tab_url") or raw["tab_url"] in seen:
                continue
            if raw.get("tab_access_type") not in (None, "public"):
                continue
            result = ug_result(raw)
            if not all(w in plain_words(result.song) for w in title_words):
                continue
            if artist_words and not all(w in plain_words(result.artist) for w in artist_words):
                continue
            seen.add(result.url)
            results.append(result)
        if stop and stop(results):
            break
        page += 1
    return results


def ug_best_first(results, title):
    """Exact title first, studio before live, then most votes."""
    title_words = plain_words(title)
    return sorted(results, key=lambda r: (plain_words(r.song) != title_words, r.live, -r.votes))


def ultimate_guitar(title, artist=""):
    """Best Ultimate Guitar chord pages. When "artist title" finds nothing, the
    title alone is searched (UG may spell the artist differently)."""
    enough = lambda found: len(found) >= MAX_RESULTS  # noqa: E731
    results = ug_chord_results(title, artist, stop=enough)
    if not results and artist:
        results = ug_chord_results(title, artist, query=title, stop=enough)
    return ug_best_first(results, title)


def find_versions(title, artist, version=None):
    """Ultimate Guitar: (the wanted version or None, every matching chord page best first).

    `version` is Ultimate Guitar's version number; when two pages share it,
    the studio one (not live) with the most votes is taken."""

    def has_version(found):
        return version is not None and any(r.version == version and not r.live for r in found)

    results = ug_chord_results(title, artist, stop=has_version)
    if not results and artist:
        results = ug_chord_results(title, artist, query=title, stop=has_version)
    ordered = ug_best_first(results, title)
    title_words = plain_words(title)
    wanted = None
    if version is not None:
        same = [r for r in ordered if r.version == version and plain_words(r.song) == title_words]
        wanted = same[0] if same else None
    return wanted, ordered


# ---------- every site ----------

def web_results(title, artist):
    """Chord pages on any site, from a web search."""
    return [Result(hit.url, hit.label) for hit in duckduckgo(f"{title} {artist} acordes".strip())]


def page_key(result):
    """The same song page under different addresses gets the same key: Ultimate
    Guitar tab ids, LaCuerda's acordes./chords./.shtml variants, Cifra Club's
    .com / .com.br."""
    tab = re.search(r"ultimate-guitar\.com/.*?(\d{4,})/?$", result.url)
    if tab:
        return "ug", tab.group(1)
    parts = urllib.parse.urlparse(result.url)
    site = site_for(result.url)
    host = site.NAME if site is not generic else parts.hostname.removeprefix("www.")
    return host, parts.path.removesuffix(".shtml").rstrip("/").casefold()


def allowed(result, sites):
    if sites == "all":
        return True
    site = site_for(result.url)
    return site is not generic and site.__name__.rsplit(".", 1)[-1] in sites


def search(title, artist="", sites="all"):
    """Best chord pages for the song, supported sites first. `sites` is "all"
    or a list of site module names (book.yaml `sites`). Raises FetchError if no
    search source answered at all."""
    if sites != "all" and list(sites) == ["ultimate_guitar"]:
        return ultimate_guitar(title, artist)[:MAX_RESULTS]

    found, errors = [], []
    for source in (lambda: web_results(title, artist), lambda: ultimate_guitar(title, artist)):
        try:
            found += source()
        except FetchError as e:
            errors.append(e)
    if not found and errors:
        raise FetchError(f"the search didn't answer ({errors[0]})")

    found = [r for r in found if allowed(r, sites)]
    title_words = plain_words(title)
    relevant = [r for r in found if mentions(r, title_words)]
    with_artist = [r for r in relevant if mentions(r, plain_words(artist))]
    results, keys, per_site = [], set(), {}
    for result in sorted(with_artist or relevant, key=lambda r: r.rank):  # stable: keeps search order per site
        key = page_key(result)
        if key in keys or per_site.get(key[0], 0) >= MAX_PER_SITE:
            continue
        keys.add(key)
        per_site[key[0]] = per_site.get(key[0], 0) + 1
        results.append(result)
    return results[:MAX_RESULTS]
