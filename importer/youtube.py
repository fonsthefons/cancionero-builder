"""Find a song's YouTube video (used when it isn't on Spotify).

Searches the web (DuckDuckGo) for YouTube videos, then checks each one with
YouTube's public oEmbed service, which gives the video's real title and
channel: a video is kept only if its title has every word of the song's
title and, when the artist is known, the title or channel names the artist.
"""

import json
import re
import urllib.parse

from .fetch import FetchError, download
from .search import duckduckgo, plain_words

MAX_CHECKED = 6
VIDEO_RE = re.compile(r"https://(?:www\.|m\.)?youtube\.com/watch\?v=([\w-]{11})|https://youtu\.be/([\w-]{11})")
NO_ARTIST = {"popular", "anonimo", "anónimo", "tradicional"}


def video_info(video_id):
    """(title, channel) from YouTube's oEmbed service."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    data = json.loads(download("https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(url)))
    return data.get("title", ""), data.get("author_name", "")


def find_video(title, artist=""):
    """Link of the best matching video, or None. Raises FetchError if the search didn't answer."""
    artist = "" if artist.casefold() in NO_ARTIST else artist
    title_words, artist_words = plain_words(title), plain_words(artist)
    ids = []
    for result in duckduckgo(f"{title} {artist} youtube".strip()):
        match = VIDEO_RE.match(result.url)
        if match:
            video_id = match.group(1) or match.group(2)
            if video_id not in ids:
                ids.append(video_id)
    for video_id in ids[:MAX_CHECKED]:
        try:
            name, channel = video_info(video_id)
        except (FetchError, json.JSONDecodeError):
            continue
        if not all(w in plain_words(name) for w in title_words):
            continue
        if artist_words and not any(w in plain_words(name + " " + channel) for w in artist_words):
            continue
        return f"https://www.youtube.com/watch?v={video_id}"
    return None
