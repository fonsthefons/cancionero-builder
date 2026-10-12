"""Download a web page.

A plain download is tried first. Some sites (Cifra Club) refuse anything that
isn't a real browser; for those the page is opened in a headless Safari
engine (WebKit, via Playwright), if it is installed. See `browser_available`.
"""

import re
import urllib.error
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
BLOCKED_CODES = {401, 403, 429, 503}
TIMEOUT = 30  # seconds


class FetchError(Exception):
    pass


class Blocked(FetchError):
    """The site refuses plain downloads; a browser engine is needed."""


def decode(data, charset=None):
    """Page bytes to text: the server's charset, else the page's <meta charset>,
    else UTF-8, falling back to Windows-1252 (older Spanish sites)."""
    if not charset:
        meta = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", data[:4096], re.IGNORECASE)
        charset = meta.group(1).decode("ascii") if meta else None
    for encoding in (charset, "utf-8"):
        if encoding:
            try:
                return data.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                pass
    return data.decode("cp1252", errors="replace")


def download(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return decode(response.read(), response.headers.get_content_charset())
    except urllib.error.HTTPError as e:
        if e.code in BLOCKED_CODES:
            raise Blocked(f"the site refused the download (error {e.code})") from e
        raise FetchError(f"the site answered with error {e.code}") from e
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise FetchError(f"couldn't open the link ({getattr(e, 'reason', e)})") from e


def browser_available():
    """True if Playwright and its WebKit engine are installed."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            p.webkit.launch().close()
        return True
    except Exception:
        return False


def browser_download(url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.webkit.launch()
        try:
            page = browser.new_page()
            response = page.goto(url, timeout=TIMEOUT * 1000)
            if response is None or response.status >= 400:
                status = response.status if response else "none"
                raise FetchError(f"the site refused the page even in a browser (error {status})")
            return page.content()
        finally:
            browser.close()


def fetch(url, use_browser=False):
    """The page's HTML. Raises Blocked when only a browser could read it."""
    if use_browser:
        return browser_download(url)
    return download(url)
