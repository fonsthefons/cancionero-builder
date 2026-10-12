"""Small text helpers shared by the build and the importers."""

import re
import unicodedata


def slug(text):
    """Plain lowercase id: 'Don't Cry' -> 'dont_cry', 'Déjame' -> 'dejame',
    'Pasión' -> 'pasion'. Used for song file names and tag ids."""
    plain = unicodedata.normalize("NFD", str(text).casefold().replace("'", "").replace("’", ""))
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", plain).strip("_")


def humanize(tag_id):
    """Label for an id with no label of its own: 'primer_ciclo' -> 'Primer ciclo'."""
    text = tag_id.replace("_", " ").replace("-", " ").strip()
    return text[:1].upper() + text[1:]


def spanish_sort_key(text):
    """Sort key for Spanish alphabetical order: accents are ignored (é = e,
    ü = u) and case too, but ñ is its own letter, right after n. Punctuation
    is ignored too, so "¿Por qué?" sorts under P and "(Tú) El..." under T."""
    text = unicodedata.normalize("NFC", text).casefold().replace("ñ", "n￿")
    letters = unicodedata.normalize("NFD", text)
    return "".join(c for c in letters if not unicodedata.combining(c) and (c.isalnum() or c in " ￿"))
