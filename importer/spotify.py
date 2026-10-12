"""Find a song's Spotify track link, without a Spotify account.

Spotify's search API needs registered credentials, so this searches the web
(DuckDuckGo) for Spotify track pages instead. Search results carry cut-off or
stale titles, so every track found is checked against Spotify's own embed
page, which gives its real title and artists: a track is offered only if its
title has every word of the song's title and, when the artist is known, one
of its artists shares a word with it.
"""

import json
import re
from dataclasses import dataclass

from .fetch import FetchError, download
from .search import duckduckgo, plain_words

MAX_TRACKS = 3  # offered to the user
MAX_CHECKED = 8  # track pages looked at (about 0.3 s each)
TRACK_RE = re.compile(r"https://open\.spotify\.com/(?:intl-[a-z]+/)?track/([A-Za-z0-9]{22})")
NO_ARTIST = {"popular", "anonimo", "anónimo", "tradicional"}


@dataclass
class Track:
    url: str
    song: str
    artists: list

    @property
    def label(self):
        return f"{self.song} - {', '.join(self.artists)}"


def track_info(track_id):
    """(title, [artists]) from the track's embed page."""
    page = download(f"https://open.spotify.com/embed/track/{track_id}")
    data = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page, re.S)
    if not data:
        raise FetchError("unexpected Spotify page")
    entity = json.loads(data.group(1))["props"]["pageProps"]["state"]["data"]["entity"]
    return entity["name"], [a["name"] for a in entity.get("artists", [])]


def find_tracks(title, artist=""):
    """Best Spotify tracks for the song, checked; [] if none. Raises FetchError
    if the web search didn't answer."""
    artist = "" if artist.casefold() in NO_ARTIST else artist
    title_words, artist_words = plain_words(title), plain_words(artist)
    ids = []
    # The second query only when the first finds no tracks: fewer searches,
    # so the web search doesn't start asking to prove we're human.
    for query in (f"{title} {artist} spotify", f"site:open.spotify.com {title} {artist}"):
        for result in duckduckgo(query.strip()):
            track = TRACK_RE.match(result.url)
            if track and track.group(1) not in ids:
                ids.append(track.group(1))
        if ids:
            break

    tracks = []
    for track_id in ids[:MAX_CHECKED]:
        try:
            song, artists = track_info(track_id)
        except (FetchError, KeyError, TypeError, json.JSONDecodeError):
            continue
        if not all(w in plain_words(song) for w in title_words):
            continue
        if artist_words and not any(w in plain_words(" ".join(artists)) for w in artist_words):
            continue
        tracks.append(Track(f"https://open.spotify.com/track/{track_id}", song, artists))
    # Exact title first (Huracán before Huracán - En Vivo), otherwise search order.
    tracks.sort(key=lambda t: plain_words(t.song) != title_words)
    return tracks[:MAX_TRACKS]
