"""Add one song to a book, asking as it goes: from a web page, typed / pasted
in, or found by searching for its title and artist.

Cleans the song up (importer/clean.py), shows it, asks for title, author,
capo, a Spotify (or YouTube) link and tags, and writes songs/<title>_<author>.md
(songs/<title>.md for the book's own artist, book.yaml default_author).
"""

import subprocess
import sys

from builder.build import load_book_songs
from builder.songs import SongError
from builder.tags import Taxonomy

from .ask import ask, ask_chord_line, ask_number, ask_tags, ask_yes, read_pasted
from .clean import clean_song
from .fetch import Blocked, FetchError, browser_available
from .language import detect
from .read import read_song
from .search import search
from .sites import SITES, SiteError
from .songfile import alias_for, existing_song, is_web_link, load_aliases, remember_alias, write_song
from .spotify import find_tracks
from .titles import book_names, load_fixes
from .youtube import find_video


# ---------- getting the song ----------

def site_names(book):
    names = [site.NAME for site in SITES if book.uses_site(site.__name__.rsplit(".", 1)[-1])]
    return ", ".join(names) + (" or another site" if book.sites == "all" else "")


def offer_browser():
    """Blocked site: use (and if needed install) the headless browser engine."""
    print("This site only lets real browsers in, so it has to be opened in a hidden browser.")
    if browser_available():
        return True
    if not ask_yes("That needs a browser engine (about 100 MB, installed once). Install it now?"):
        return False
    for command in (
        [sys.executable, "-m", "pip", "install", "playwright"],
        [sys.executable, "-m", "playwright", "install", "webkit"],
    ):
        if subprocess.run(command).returncode != 0:
            print("The installation failed.")
            return False
    return browser_available()


def from_link(book, link):
    """Draft from a link or a saved page, or None on failure."""
    try:
        try:
            return read_song(link, sites=book.sites)
        except Blocked:
            if not offer_browser():
                print("Tip: open the page, copy the song, then choose option 2 and paste it.")
                return None
            return read_song(link, use_browser=True, sites=book.sites)
    except (FetchError, SiteError, OSError) as e:
        print(f"Couldn't read the song: {e}.")
        return None


def preview(text, marked, from_web=True):
    """Clean the song and show it. The cleaned song if it looks right, else None."""
    cleaned = clean_song(text, marked=marked, ask=ask_chord_line, from_web=from_web)
    print("\n" + "-" * 60 + "\n" + cleaned.body + "\n" + "-" * 60)
    for note in cleaned.notes:
        print(f"* {note}")
    return cleaned if ask_yes("\nDoes the song look right?", default=True) else None


def from_search(book, title, artist):
    """Search, then read results until one looks right: (Draft, Cleaned) or None."""
    print(f'Searching for "{title}"' + (f" by {artist}" if artist else "") + "...")
    try:
        results = search(title, artist, sites=book.sites)
    except FetchError as e:
        print(f"Couldn't search: {e}.")
        return None
    if not results:
        print("No chord pages found. Try another spelling, or leave the artist out.")
        return None
    tried = set()
    while True:
        print("\nFound:")
        for number, result in enumerate(results, start=1):
            mark = "  (tried)" if number in tried else ""
            label = result.label if len(result.label) <= 70 else result.label[:69] + "…"
            print(f"  {number}  {result.site_name:16} {label}{mark}")
        untried = [n for n in range(1, len(results) + 1) if n not in tried]
        if not untried:
            print("None of them worked.")
            return None
        number = ask_number("Which one? (0 to paste the song instead)", len(results), untried[0], allow_zero=True)
        if not number:
            return None
        tried.add(number)
        result = results[number - 1]
        print(f"Reading {result.url}")
        draft = from_link(book, result.url)
        if draft is None:
            continue
        cleaned = preview(draft.text, draft.marked)
        if cleaned is not None:
            return draft, cleaned


# ---------- details ----------

def ask_link(title, autor, offline=False):
    """Look the song up on Spotify (else YouTube) and offer what's found; the chosen link or ''."""
    if offline:
        return checked_link(ask("Link to a recording (Enter for none)"))
    tracks = []
    print("Looking for it on Spotify...")
    try:
        tracks = find_tracks(title, autor)
    except FetchError as e:
        print(f"Couldn't look it up: {e}.")
    if tracks:
        print("Found on Spotify:")
        for number, track in enumerate(tracks, start=1):
            print(f"  {number}  {track.label}\n     {track.url}")
        link = ask("Link: a number, another link, or - for none", "1")
        if link == "-":
            return ""
        if link.isdigit() and 1 <= int(link) <= len(tracks):
            return tracks[int(link) - 1].url
        return checked_link(link)
    print("Not found on Spotify; looking on YouTube...")
    try:
        video = find_video(title, autor)
    except FetchError as e:
        print(f"Couldn't look it up: {e}.")
        video = None
    if video:
        print(f"Found on YouTube: {video}")
        link = ask("Link: Enter takes it, paste another one, or - for none", video)
        return "" if link == "-" else checked_link(link)
    return checked_link(ask("Not found; paste a link (Enter for none)"))


def checked_link(link):
    while link and not is_web_link(link):
        link = ask("The link must start with https:// (Enter for none)")
    return link


def suggested_title(book, draft):
    """The page's title; Ultimate Guitar's with its apostrophes back (titles.py)."""
    if not draft or not draft.title:
        return None
    if "ultimate-guitar" in (draft.url or "") or book.sites != "all":
        return book_names(draft.artist or "", draft.title, load_fixes(book.title_fixes_file))[0]
    return draft.title


def ask_details(book, taxonomy, draft, cleaned, searched_artist="", offline=False):
    """Title, author, capo, link and tags; None if the user stops."""
    print()
    title = ask("Title", suggested_title(book, draft))
    while not title:
        title = ask("Title (required)")
    found = existing_song(book, title)
    if found and not ask_yes(f'"{title}" is already in the book ({found.name}). Add it anyway?'):
        return None

    aliases = load_aliases(book)
    site_artist = (draft.artist or "").strip() if draft else ""
    default_author = (alias_for(site_artist, aliases) if site_artist else searched_artist) \
        or book.default_author or "popular"
    autor = ask("Author", default_author)
    if site_artist and autor and autor != alias_for(site_artist, aliases) and autor != site_artist:
        remember_alias(book, site_artist, autor)
        print(f'Remembered: "{site_artist}" will be written "{autor}" next time.')
    capo = ask("Capo (Enter for none)", (draft.capo if draft else None) or cleaned.capo)
    link = ask_link(title, autor, offline)
    suggested = detect(cleaned.body)[0] if book.language_tags else None
    tags = ask_tags(book, taxonomy, suggested)
    return title, autor, capo, link, tags


# ---------- main ----------

def get_song(book, choice):
    """(draft or None, cleaned, searched artist) for menu choice 1-3, or None."""
    searched_artist = ""
    if choice == "3":
        song_title = ask("Song title")
        searched_artist = ask("Artist" if book.default_author else "Artist (Enter to skip)", book.default_author)
        got = from_search(book, song_title, searched_artist) if song_title else None
    elif choice == "1":
        link = ask("Link to the song (or a saved web page file)")
        draft = from_link(book, link) if link else None
        got = (draft, preview(draft.text, draft.marked)) if draft else None
        if got and got[1] is None:
            print("Nothing added. Tip: paste the song (option 2) and fix it by hand, or fix the file after adding it.")
            return None
    else:
        got = None
    if got is None:
        if choice != "2" and not ask_yes("Paste the song instead?", default=True):
            return None
        text = read_pasted()
        if not text.strip():
            print("No song text, nothing added.")
            return None
        cleaned = preview(text, marked=False, from_web=False)
        if cleaned is None:
            print("Nothing added. Fix the text and paste it again, or fix the file after adding it.")
            return None
        got = (None, cleaned)
    return got[0], got[1], searched_artist


def add_song(book, choice, offline=False):
    """Add one song (menu choice "1" link, "2" paste, "3" search). The new file's path or None."""
    got = get_song(book, choice)
    if got is None:
        return None
    draft, cleaned, searched_artist = got
    try:
        _, taxonomy = load_book_songs(book)
    except SongError:
        taxonomy = Taxonomy.load(book.tags_file, strict=book.strict_tags)  # some song is broken: tags.yaml only
    details = ask_details(book, taxonomy, draft, cleaned, searched_artist, offline)
    if details is None:
        return None
    title, autor, capo, link, tags = details
    try:
        path = write_song(book, title, autor, capo, link, tags, cleaned.body)
    except SongError as e:
        print(f"Couldn't add the song: {e}")
        return None
    print(f"\nAdded songs/{path.name}")
    if not tags:
        print("It has no tags, so it only appears in All Songs.")
    return path


def menu(book):
    print(f"\nAdd a song to {book.title}\n")
    print(f"  1) From a web page ({site_names(book)})")
    print("  2) Type or paste it in")
    print("  3) Search for it by title and artist")
    print("  4) From a PDF songbook")
    print("  5) A list of songs (Title - Artist, one per line), added without questions")
    print("  0) Done")
    return ask("Choose", "3")
