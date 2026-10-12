"""Read a song from a link: download, pick the site's reader, follow redirects
to the page that holds the song."""

from pathlib import Path

from .fetch import Blocked, browser_available, fetch
from .sites import SITES, Follow, SiteError, generic, saved_page_address, site_for

MAX_FOLLOWS = 3


def check_allowed(link, sites):
    """Raise SiteError when the book doesn't take songs from the link's site
    (book.yaml `sites`); checked before downloading."""
    if sites == "all":
        return
    site = site_for(link)
    if site is generic or site.__name__.rsplit(".", 1)[-1] not in sites:
        names = ", ".join(s.NAME for s in SITES if s.__name__.rsplit(".", 1)[-1] in sites)
        raise SiteError(f"this book only reads songs from {names}; copy the song and paste it instead")


def read_song(link, use_browser=False, sites="all"):
    """Draft from a link or a saved page file. Raises fetch.Blocked when the
    site needs the browser engine, FetchError / SiteError when it can't be read."""
    for _ in range(MAX_FOLLOWS):
        path = Path(link).expanduser()
        if path.is_file():  # a page saved from the browser
            page = path.read_text(encoding="utf-8")
            link = saved_page_address(page) or link
            check_allowed(link, sites)
        else:
            check_allowed(link, sites)
            page = fetch(link, use_browser)
        draft = site_for(link).parse(page, link)
        if not isinstance(draft, Follow):
            draft.url = link
            return draft
        link = draft.url
    raise SiteError("couldn't find the song on that page")


def read_song_any_way(link, sites="all"):
    """Like read_song, but uses the browser engine on its own when a site
    blocks plain downloads and the engine is installed (no questions asked)."""
    try:
        return read_song(link, sites=sites)
    except Blocked:
        if not browser_available():
            raise
        return read_song(link, use_browser=True, sites=sites)
