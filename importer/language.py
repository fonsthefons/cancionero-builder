"""Is a song sung in English or Spanish? Its tag in tags.yaml says so.

Counts the different very common words of each language in the lyric lines
(chord lines are skipped): "the, and, you..." against "que, de, el, la...".
Words both languages use ("a", "me", "no", "son"...) are left out.
"""

import re

from builder.lyrics import is_chord_line

ENGLISH = set("""
the and you your i'm it's is are was were be been this that what when where with for from
have has had will would can can't don't not but all my me i we they them our there here
just like love know oh baby so if out up down into never ever every one got gonna
""".split())
SPANISH = set("""
que de el la los las y en un una por para con del al mi tu te se es lo le su sus pero
como cuando donde mas más yo tú él ella nos nosotros vida amor quiero sin hay ya muy
esta está este eso ese porque todo nada siempre nunca corazón voy vas soy eres
""".split())
MIN_WORDS = 6  # fewer different known words than this: not sure


def detect(body):
    """("english" | "spanish", sure). Not sure when the song has few known words
    or the two languages come out close; then the more likely one is given."""
    # Each word counts once, so a "la la la" chorus doesn't make a song Spanish.
    words = set()
    for line in body.split("\n"):
        if not is_chord_line(line):
            words.update(re.findall(r"[\w']+", line.casefold()))
    english, spanish = len(words & ENGLISH), len(words & SPANISH)
    language = "spanish" if spanish > english else "english"
    sure = english + spanish >= MIN_WORDS and max(english, spanish) >= 3 * min(english, spanish)
    return language, sure
