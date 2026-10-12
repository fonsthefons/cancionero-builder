"""LaCuerda: the song is a <pre> inside #t_body, chords in <A> tags, usually in
Spanish notation (LAm, SOL). A song's main page lists its versions; the first
version (.shtml) holds the full text.
"""

import re
from urllib.parse import urljoin

from .common import Draft, Follow, PreText, SiteError, strip_tags

NAME = "LaCuerda"
DOMAINS = ("lacuerda.net",)


def parse(page, url):
    body = re.search(r"<div id=t_body>\s*<pre[^>]*>(.*?)</pre>", page, re.S | re.I)
    if not body:
        version = re.search(r"href=['\"]([^'\"]+\.shtml)['\"]", page)
        if version:
            return Follow(urljoin(url, version.group(1)))
        raise SiteError("couldn't find the song on this LaCuerda page")
    title = re.search(r"<h1>(.*?)</h1>", page, re.S | re.I)
    artist = re.search(r"<h2>(.*?)</h2>", page, re.S | re.I)
    text = PreText.text(body.group(1), lambda tag, attrs: tag == "a")
    return Draft(
        title=strip_tags(re.sub(r"<span.*?</span>", "", title.group(1), flags=re.S)) if title else None,
        artist=strip_tags(artist.group(1)) if artist else None,
        text=text,
        marked=True,
    )
