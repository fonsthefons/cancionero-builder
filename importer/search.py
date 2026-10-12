"""Find chord pages for a song title + artist.

Two sources, no account or key needed:
- DuckDuckGo's plain-HTML search for "<title> <artist> acordes";
- Ultimate Guitar's own search (by title, filtered by artist, best voted first),
  so there are results even if DuckDuckGo stops answering.

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

MAX_RESULTS = 8
MAX_PER_SITE = 3  # versions shown from one site, so other sites still appear


@dataclass
class Result:
    url: str
    label: str  # what to show: page title or "Artist - Song"

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


def duckduckgo(query):
    page = download("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query))
    results = []
    for href, label in re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        href = html.unescape(href)
        target = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg")
        url = target[0] if target else href
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("http") and "duckduckgo.com" not in url:
            results.append(Result(url, html.unescape(re.sub(r"<[^>]+>", "", label)).strip()))
    if not results and "anomaly" in page.lower():
        # After many searches in a short time DuckDuckGo asks to prove we're human.
        raise FetchError("the web search is busy (too many searches); try again in a few minutes")
    return results


def ultimate_guitar(title, artist):
    try:
        page = download("https://www.ultimate-guitar.com/search.php?search_type=title&value="
                        + urllib.parse.quote(title))
    except FetchError as e:
        if "404" in str(e):  # Ultimate Guitar answers "nothing found" with a 404
            return []
        raise
    store = re.search(r'class="js-store"\s+data-content="([^"]*)"', page)
    if not store:
        return []
    try:
        found = json.loads(html.unescape(store.group(1)))["store"]["page"]["data"]["results"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return []
    artist_words = plain_words(artist)
    chords = [
        r for r in found
        if r.get("type") == "Chords" and r.get("tab_url")
        and all(w in plain_words(r.get("artist_name", "")) for w in artist_words)
    ]
    chords.sort(key=lambda r: (r.get("votes") or 0), reverse=True)
    return [
        Result(r["tab_url"], f"{r.get('artist_name')} - {r.get('song_name')}"
               + (f" (rated {r['rating']:.1f} by {r['votes']})" if r.get("votes") else ""))
        for r in chords
    ]


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


def search(title, artist=""):
    """Best chord pages for the song, supported sites first. Raises FetchError if
    no search source answered at all."""
    found, errors = [], []
    for source in (lambda: duckduckgo(f"{title} {artist} acordes".strip()), lambda: ultimate_guitar(title, artist)):
        try:
            found += source()
        except FetchError as e:
            errors.append(e)
    if not found and errors:
        raise FetchError(f"the search didn't answer ({errors[0]})")

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
