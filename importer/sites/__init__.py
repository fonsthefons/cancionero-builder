"""One reader per website. Each module has:

    NAME = "Example"                # shown in search results
    DOMAINS = ("example.com",)      # matched against the end of the link's host
    def parse(page, url) -> Draft   # or a Follow(url) to read another page

To support a new site, add a module here and list it in SITES. Pages from
other sites go to `generic`, which takes the largest <pre> block.
SITES is also the order of preference for search results (importer/search.py).
"""

import re
from urllib.parse import urlparse

from . import cifraclub, generic, lacuerda, ultimate_guitar
from .common import Draft, Follow, SiteError

SITES = [ultimate_guitar, lacuerda, cifraclub]

__all__ = ["Draft", "Follow", "SiteError", "site_for", "saved_page_address", "SITES"]

CANONICAL_RE = re.compile(
    r"<link[^>]*rel=[\"']?canonical[^>]*href=[\"']([^\"']+)|<link[^>]*href=[\"']([^\"']+)[\"'][^>]*rel=[\"']?canonical"
    r"|<meta[^>]*og:url[^>]*content=[\"']([^\"']+)",
    re.IGNORECASE,
)


def saved_page_address(page):
    """The web address of a page saved from a browser: its canonical link, or
    else the first supported site it mentions."""
    match = CANONICAL_RE.search(page)
    if match:
        return next(group for group in match.groups() if group)
    for site in SITES:
        for domain in site.DOMAINS:
            if domain in page:
                return f"https://{domain}/"
    return ""


def site_for(url):
    host = (urlparse(url).hostname or "").lower()
    for site in SITES:
        if any(host == d or host.endswith("." + d) for d in site.DOMAINS):
            return site
    return generic
