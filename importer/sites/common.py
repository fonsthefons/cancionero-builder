"""What site readers return, and helpers they share."""

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser


class SiteError(Exception):
    pass


@dataclass
class Draft:
    """A song as read from a site, before cleaning."""

    title: str | None
    artist: str | None
    text: str
    marked: bool  # chords wrapped as [ch]Am[/ch]
    capo: str | None = None


@dataclass
class Follow:
    """The song is on another page (e.g. a list of versions)."""

    url: str


def strip_tags(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


class PreText(HTMLParser):
    """Text of an HTML fragment, with the contents of chord tags marked [ch]..[/ch].

    `is_chord(tag, attrs)` says whether a tag wraps a chord name. <br> is a newline.
    """

    def __init__(self, is_chord):
        super().__init__(convert_charrefs=True)
        self.is_chord = is_chord
        self.parts = []
        self.chord_tags = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")
        elif self.is_chord(tag, dict(attrs)):
            self.chord_tags.append(tag)
            self.parts.append("[ch]")

    def handle_endtag(self, tag):
        if self.chord_tags and tag == self.chord_tags[-1]:
            self.chord_tags.pop()
            self.parts.append("[/ch]")

    def handle_data(self, data):
        self.parts.append(data)

    @classmethod
    def text(cls, fragment, is_chord):
        parser = cls(is_chord)
        parser.feed(fragment)
        parser.close()
        return "".join(parser.parts)
