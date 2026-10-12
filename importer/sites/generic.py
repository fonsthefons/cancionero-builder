"""Any other site: the largest <pre> block on the page, title from <title>.

Works for many chord sites, which show songs in a <pre>. Chords are not
marked, so chord lines are detected like in pasted text.
"""

import re

from ..clean import is_chord_text
from .common import Draft, PreText, SiteError, strip_tags

NAME = "Other site"
DOMAINS = ()


def parse(page, url):
    blocks = re.findall(r"<pre[^>]*>(.*?)</pre>", page, re.S | re.I)
    if not blocks:
        raise SiteError("this site isn't supported yet and has no song text block; copy the song and paste it instead")
    text = PreText.text(max(blocks, key=len), lambda tag, attrs: False)
    if not any(is_chord_text(line) for line in text.split("\n")):
        raise SiteError("no chords on this page (some sites draw them in a way that can't be read)")
    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    return Draft(
        title=strip_tags(title.group(1)).split("|")[0].strip() if title else None,
        artist=None,
        text=text,
        marked=False,
    )
