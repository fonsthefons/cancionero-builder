"""Ultimate Guitar: the page embeds the song as JSON (div.js-store), chords marked [ch]..[/ch]."""

import html
import json
import re

from .common import Draft, SiteError

NAME = "Ultimate Guitar"
DOMAINS = ("ultimate-guitar.com",)


def parse(page, url):
    store = re.search(r'class="js-store"\s+data-content="([^"]*)"', page)
    if not store:
        raise SiteError("couldn't find the song on this Ultimate Guitar page")
    try:
        data = json.loads(html.unescape(store.group(1)))["store"]["page"]["data"]
        tab, view = data["tab"], data["tab_view"]
        content = view["wiki_tab"]["content"]
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        raise SiteError("this Ultimate Guitar page has no chord sheet (Pro or Official tabs can't be read)") from e
    capo = (view.get("meta") or {}).get("capo")
    return Draft(
        title=tab.get("song_name"),
        artist=tab.get("artist_name"),
        text=content,
        marked=True,
        capo=str(capo) if capo else None,
    )
