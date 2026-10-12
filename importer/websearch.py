"""Web search (DuckDuckGo's plain-HTML page), no account or key needed.

Used to find chord pages on any site (importer/search.py) and a song's
Spotify track or YouTube video (importer/spotify.py, importer/youtube.py).
"""

import html
import re
import urllib.parse
from dataclasses import dataclass

from .fetch import FetchError, download


class SearchBusy(FetchError):
    """After many searches in a short time DuckDuckGo asks to prove we're human."""


@dataclass
class Hit:
    url: str
    label: str  # the result's title


def duckduckgo(query):
    page = download("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query))
    hits = []
    for href, label in re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        href = html.unescape(href)
        target = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg")
        url = target[0] if target else href
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("http") and "duckduckgo.com" not in url:
            hits.append(Hit(url, html.unescape(re.sub(r"<[^>]+>", "", label)).strip()))
    if not hits and "anomaly" in page.lower():
        raise SearchBusy("the web search is busy (too many searches); try again in a few minutes")
    return hits
