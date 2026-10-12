"""Find a Spotify (or YouTube) link for the songs of a book that have none.

Each song is looked up like when adding it (importer/spotify.py, youtube.py):
the first Spotify track whose title and artist match, else a YouTube video.
With `ask_each`, the tracks found are offered one song at a time.
The link is written into the song file (`link:`), nothing else changes.
"""

import json
import time

from builder.songs import split_frontmatter

from .ask import ask
from .batch import NO_ARTIST, find_link, patiently
from .fetch import FetchError
from .songfile import book_songs, is_web_link
from .spotify import find_tracks
from .youtube import find_video

PAUSE = 3  # seconds between songs, so the web search doesn't get busy


def set_link(path, link):
    """Write `link: "<link>"` into a song file's frontmatter (replacing an empty one)."""
    text = path.read_text(encoding="utf-8")
    split_frontmatter(text)  # raises if the file isn't a song
    lines = text.split("\n")
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    new = f"link: {json.dumps(link, ensure_ascii=False)}"
    for i in range(1, end):
        if lines[i].startswith("link:"):
            lines[i] = new
            break
    else:
        # after title/autor/capo, before added/song_tags
        at = next((i for i in range(1, end) if lines[i].startswith(("added:", "song_tags:"))), end)
        lines.insert(at, new)
    path.write_text("\n".join(lines), encoding="utf-8")


def choose(title, artist, log):
    """Offer what's found for one song; the chosen link, '' for none, None to stop."""
    try:
        tracks = patiently(lambda: find_tracks(title, artist), "web search", log)
        video = None if tracks else patiently(lambda: find_video(title, artist), "web search", log)
    except FetchError as e:
        log(f"    couldn't look it up: {e}")
        tracks, video = [], None
    options = [t.url for t in tracks] + ([video] if video else [])
    for n, track in enumerate(tracks, start=1):
        log(f"    {n}  {track.label}  {track.url}")
    if video:
        log(f"    {len(options)}  YouTube: {video}")
    answer = ask("    Link: a number, a link, Enter to skip, q to stop", "1" if options else None)
    if answer.lower() == "q":
        return None
    if answer.isdigit() and 1 <= int(answer) <= len(options):
        return options[int(answer) - 1]
    return answer if is_web_link(answer) else ""


def fill_links(book, ask_each=False, limit=None, log=print):
    """Look up links for songs without one. Returns the number of songs given a link."""
    missing = [(path, song) for path, song in book_songs(book) if not song.link]
    if limit is not None:
        missing = missing[:limit]
    log(f"{len(missing)} songs have no link.")
    done = 0
    for n, (path, song) in enumerate(missing, start=1):
        artist = song.autor or book.default_author or ""
        artist = "" if artist.casefold() in NO_ARTIST else artist
        log(f"[{n}/{len(missing)}] {song.title}" + (f" - {artist}" if artist else ""))
        if ask_each:
            link = choose(song.title, artist, log)
            if link is None:
                break
        else:
            link = find_link(song.title, artist, log)
            log(f"    {link or 'nothing found'}")
            if n < len(missing):
                time.sleep(PAUSE)
        if link:
            set_link(path, link)
            done += 1
    log(f"\nAdded a link to {done} songs.")
    return done
