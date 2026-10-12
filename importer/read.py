"""Read a song from a link: download, pick the site's reader, follow redirects
to the page that holds the song. Used by add_song.py and add_songs.py."""

from pathlib import Path

from .fetch import Blocked, browser_available, fetch
from .sites import Follow, SiteError, saved_page_address, site_for

MAX_FOLLOWS = 3


def read_song(link, use_browser=False):
    """Draft from a link or a saved page file. Raises fetch.Blocked when the
    site needs the browser engine, FetchError / SiteError when it can't be read."""
    for _ in range(MAX_FOLLOWS):
        path = Path(link).expanduser()
        if path.is_file():  # a page saved from the browser
            page = path.read_text(encoding="utf-8")
            link = saved_page_address(page) or link
        else:
            page = fetch(link, use_browser)
        draft = site_for(link).parse(page, link)
        if not isinstance(draft, Follow):
            return draft
        link = draft.url
    raise SiteError("couldn't find the song on that page")


def read_song_any_way(link):
    """Like read_song, but uses the browser engine on its own when a site
    blocks plain downloads and the engine is installed (no questions asked)."""
    try:
        return read_song(link)
    except Blocked:
        if not browser_available():
            raise
        return read_song(link, use_browser=True)
