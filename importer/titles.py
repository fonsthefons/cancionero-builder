"""Book titles and authors from Ultimate Guitar's names.

Ultimate Guitar drops apostrophes from titles ("Dont Cry", "Im Yours"). Common
contractions get theirs back here; anything else (possessives such as
"Heavens Door", "Knockin", odd capitals such as "Ymca") is written in
title_fixes.yaml, which wins over the rules.

Compilation "artists" such as "Misc Musicals" write the show in the title
("Les Misérables - Stars"): the show becomes the author and the rest the title.
Without a show ("Misc Christmas" - "Silent Night") the author is "Traditional".
"""

import re
from pathlib import Path

import yaml

NO_AUTHOR = "Traditional"

CONTRACTIONS = {
    "dont": "don't", "cant": "can't", "wont": "won't", "aint": "ain't", "isnt": "isn't",
    "arent": "aren't", "doesnt": "doesn't", "didnt": "didn't", "wasnt": "wasn't", "werent": "weren't",
    "couldnt": "couldn't", "shouldnt": "shouldn't", "wouldnt": "wouldn't", "havent": "haven't",
    "hasnt": "hasn't", "im": "I'm", "ive": "I've", "ill": "I'll", "id": "I'd", "youre": "you're",
    "youve": "you've", "youll": "you'll", "youd": "you'd", "theyre": "they're", "weve": "we've",
    "thats": "that's", "thatll": "that'll", "whats": "what's", "shes": "she's", "hes": "he's",
    "its": "it's", "lets": "let's", "theres": "there's", "heres": "here's", "whos": "who's",
}


def load_fixes(path):
    """A book's title_fixes.yaml: {title as Ultimate Guitar writes it: title for the book}."""
    if not Path(path).exists():
        return {}
    return {str(k): str(v) for k, v in (yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}).items()}


def with_apostrophes(title):
    """'Dont Think Twice Its All Right' -> "Don't Think Twice It's All Right"."""

    def fix(match):
        word = match.group()
        fixed = CONTRACTIONS.get(word.casefold())
        if fixed is None:
            return word
        if fixed.startswith("I'"):
            return fixed
        return fixed[:1].upper() + fixed[1:] if word[:1].isupper() else fixed

    return re.sub(r"[^\W_]+", fix, title)


def is_compilation(artist):
    return artist.casefold().startswith("misc ")


def book_names(ug_artist, ug_title, fixes):
    """(title, author) for the book from Ultimate Guitar's artist and title
    (without "(ver N)"). The author is still to be passed through
    author_aliases.yaml."""
    title, author = ug_title.strip(), ug_artist.strip()
    if is_compilation(author):
        show, sep, song = title.partition(" - ")
        title, author = (song.strip(), show.strip()) if sep else (title, NO_AUTHOR)
    lowered = {k.casefold(): v for k, v in fixes.items()}
    title = lowered.get(title.casefold()) or with_apostrophes(title)
    return title, author
