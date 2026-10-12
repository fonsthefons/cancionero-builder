"""Cifra Club: the chord sheet is a <pre data-chord-content> with each chord in a <b>.

Title is the page's <h1>; artist and capo come from the page's embedded data.
Cifra Club blocks plain downloads, so this site needs the browser engine.
"""

import json
import re

from .common import Draft, PreText, SiteError, strip_tags

NAME = "Cifra Club"
DOMAINS = ("cifraclub.com", "cifraclub.com.br")


def embedded(page, pattern):
    """A value from the page's embedded (escaped) JSON, e.g. \\"capo\\":3."""
    match = re.search(pattern, page)
    if not match:
        return None
    try:
        return json.loads('"' + match.group(1) + '"')
    except json.JSONDecodeError:
        return match.group(1)


def parse(page, url):
    pre = re.search(r"<pre[^>]*data-chord-content[^>]*>(.*?)</pre>", page, re.S)
    if not pre:
        raise SiteError("couldn't find the chords on this Cifra Club page")
    title = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    artist = embedded(page, r'\\"artist\\":\{\\"id\\":\d+,\\"name\\":\\"(.*?)\\"')
    capo = re.search(r'\\"capo\\":(\d+)', page)
    return Draft(
        title=strip_tags(title.group(1)) if title else None,
        artist=artist,
        text=PreText.text(pre.group(1), lambda tag, attrs: tag == "b" and "data-chord-name" in attrs),
        marked=True,
        capo=capo.group(1) if capo and capo.group(1) != "0" else None,
    )
