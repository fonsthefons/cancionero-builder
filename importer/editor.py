"""The song editor: a page (web/editor/) served on this computer only, to add
and change a book's songs in the browser. Uses the same cleaning, searching and
song files as importer/add.py, without its questions.

    .venv/bin/python cancionero.py edit <book>     (Ctrl+C stops it)

Changes (POST) need the X-Token header: the page gets the token when it loads,
so other web pages open in the browser can't change the book.
"""

import html
import json
import mimetypes
import re
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from builder.build import build_book, load_book_songs
from builder.create import CreateError, publish_book
from builder.lyrics import CHORD_RE, LABEL_RE, BOLD_MARK, clean_line, is_chord_line, is_tablature
from builder.songs import SongError, load_song
from builder.tags import Taxonomy
from builder.text import slug

from .add import suggested_title
from .ask import save_tags
from .clean import clean_song
from .fetch import Blocked, FetchError
from .language import detect
from .read import read_song_any_way
from .search import search
from .sites import SiteError
from .songfile import (alias_for, book_songs, existing_song, is_web_link, load_aliases, remember_alias,
                       update_song, write_song)
from .spotify import find_tracks
from .youtube import find_video

WEB = Path(__file__).resolve().parent.parent / "web"
EDITOR = WEB / "editor"
SHARED = {"abcjs-basic-min.js": WEB / "vendor", "melody.js": WEB / "js", "transpose.js": WEB / "js"}


class ApiError(Exception):
    def __init__(self, status, body):
        super().__init__(body)
        self.status, self.body = status, body


def fail(message, status=400):
    raise ApiError(status, {"error": message})


# ---------- song text as rows ----------

def chord_word(word):
    """A chord the editor can move as one name: "G", or "(D)" (an optional chord)."""
    return bool(CHORD_RE.fullmatch(word) or (word[:1] == "(" and word[-1:] == ")" and CHORD_RE.fullmatch(word[1:-1])))


def rows(body):
    """The body as the editor shows it: [{chords: [[col, name]], lyric}] for a chord
    line over its lyric line (lyric None: chords alone) and a lyric line alone
    (chords []); {text} for blank, **, label and tablature lines, and for chord lines
    the editor can't write back as they are (marks like (x2) or |, tab characters)
    with the lyric line under them."""
    found, pending, kept = [], None, False
    for raw in body.split("\n"):
        line = clean_line(raw)
        special = (not line.strip() or line.strip() == BOLD_MARK or LABEL_RE.fullmatch(line)
                   or any(is_tablature(word) for word in line.split()))
        chords = not special and is_chord_line(line)
        if pending is not None and (special or chords):
            found.append({"chords": pending, "lyric": None})
            pending = None
        keep = chords and ("\t" in raw or not all(chord_word(word) for word in line.split()))
        if keep or special or (kept and not chords):
            found.append({"text": raw})
        elif chords:
            pending = [[m.start(), m.group()] for m in re.finditer(r"\S+", raw)]
        else:
            found.append({"chords": pending or [], "lyric": raw})
            pending = None
        kept = keep
    if pending is not None:
        found.append({"chords": pending, "lyric": None})
    return found


def song_text(book, body, capo=None, notes=()):
    return {"body": body, "capo": capo, "notes": list(notes),
            "language": detect(body)[0] if book.language_tags else None, "rows": rows(body)}


# ---------- the API ----------

def taxonomy_of(book):
    try:
        return load_book_songs(book)[1]
    except SongError:  # some song is broken: tags.yaml only
        return Taxonomy.load(book.tags_file, strict=book.strict_tags)


def song_path(book, song_id):
    """Path of one of the book's songs; anything else (../, unknown) is refused."""
    paths = {path.stem: path for path in book.songs_dir.glob("*.md")}
    if song_id not in paths:
        fail("there is no such song", 404)
    return paths[song_id]


def api_book(book, _):
    taxonomy = taxonomy_of(book)
    choices = taxonomy.choices()
    if book.strict_tags:  # as ask_tags: only flat tags and subtags
        choices = [c for c in choices if c[1] is not None or taxonomy.tags[c[0]].is_flat]
    return {"title": book.title, "default_author": book.default_author, "strict_tags": book.strict_tags,
            "has_horas": book.horas_file.exists(),
            "tags": [{"tag": tag, "sub": sub, "label": label} for tag, sub, label in choices],
            "songs": [{"id": path.stem, "title": song.title, "autor": song.autor} for path, song in book_songs(book)]}


def api_song(book, query):
    song = load_song(song_path(book, query.get("id", "")))
    return {"id": song.id, "title": song.title, "autor": song.autor, "capo": song.capo, "link": song.link,
            "added": song.added, "tags": song.tags, "horas": song.horas, "melody": song.melody,
            "tab": song.tab, "ignore": song.ignore, "body": song.body}


def api_rows(book, data):
    return song_text(book, text_field(data, "body"))


def api_paste(book, data):
    cleaned = clean_song(text_field(data, "text"), marked=False, ask=lambda line: True, from_web=False)
    return song_text(book, cleaned.body, cleaned.capo, cleaned.notes)


def api_fetch(book, data):
    link = text_field(data, "link").strip()
    if not is_web_link(link):  # read_song also opens files: only web pages from here
        fail("the link must start with https://")
    try:
        draft = read_song_any_way(link, sites=book.sites)
    except Blocked:
        fail("this site only lets real browsers in and the browser engine isn't installed; "
             "copy the song and paste it instead", 409)
    except (FetchError, SiteError, OSError) as e:
        fail(f"couldn't read the song: {e}")
    cleaned = clean_song(draft.text, marked=draft.marked)
    site_artist = (draft.artist or "").strip()
    return {**song_text(book, cleaned.body, draft.capo or cleaned.capo, cleaned.notes),
            "title": suggested_title(book, draft),
            "artist": alias_for(site_artist, load_aliases(book)) if site_artist else "",
            "site_artist": site_artist}


def api_search(book, data):
    try:
        results = search(text_field(data, "title"), text_field(data, "artist"), sites=book.sites)
    except FetchError as e:
        fail(f"couldn't search: {e}", 502)
    return [{"url": r.url, "site": r.site_name, "label": r.label} for r in results]


def api_links(book, data):
    """As ask_link: Spotify tracks, else a YouTube video."""
    title, autor = text_field(data, "title"), text_field(data, "autor")
    try:
        tracks = [{"url": t.url, "label": t.label} for t in find_tracks(title, autor)]
    except FetchError:
        tracks = []
    video = None
    if not tracks:
        try:
            video = find_video(title, autor)
        except FetchError:
            pass
    return {"spotify": tracks, "youtube": video or None}


def api_save(book, data):
    title = text_field(data, "title").strip()
    if not title:
        fail("the song needs a title")
    autor = text_field(data, "autor").strip() or None
    picked = []
    for item in list_field(data, "tags", list):
        tag, sub, tag_label, sub_label = (list(item) + [None] * 4)[:4]
        if not slug(tag or "") or (sub and not slug(sub)):
            fail(f'"{tag}" isn\'t a tag name (use letters or digits)')
        picked.append((slug(tag), slug(sub) if sub else None, tag_label or None, sub_label or None))
    taxonomy = taxonomy_of(book)
    if book.strict_tags and any(p[0] not in taxonomy.tags or (p[1] and p[1] not in taxonomy.tags[p[0]].subtags)
                                for p in picked):
        fail("this book only takes the tags listed in tags.yaml (book.yaml strict_tags)")
    fields = {"title": title, "autor": autor, "capo": text_field(data, "capo").strip() or None,
              "link": text_field(data, "link").strip(), "body": text_field(data, "body"),
              "horas": list_field(data, "horas", str), "melody": text_field(data, "melody"),
              "tab": text_field(data, "tab"), "ignore": list_field(data, "ignore", str)}

    if data.get("id"):
        path = song_path(book, str(data["id"]))
        added = load_song(path).added
        update_song(book, path, {**fields, "tags": save_tags(book, taxonomy, picked), "added": added})
    else:
        found = existing_song(book, title)
        if found and not data.get("force"):
            raise ApiError(409, {"exists": found.name})
        site_artist = text_field(data, "site_artist").strip()
        aliases = load_aliases(book)
        if site_artist and autor and autor != alias_for(site_artist, aliases) and autor != site_artist:
            remember_alias(book, site_artist, autor)
        tags = save_tags(book, taxonomy, picked)
        path = write_song(book, **{**fields, "tags": tags})
    try:
        report = build_book(book).report(book)
    except SongError as e:  # saved, but the book (this or another song) doesn't build
        report = str(e)
    return {"id": path.stem, "file": path.name, "report": report}


def api_publish(book, _):
    output = []
    try:
        publish_book(book, log=output.append)
    except (CreateError, SongError) as e:
        output.append(f"Couldn't publish: {e}")
    return {"output": "\n".join(output)}


def text_field(data, name):
    value = data.get(name)
    if value is not None and not isinstance(value, str):
        fail(f"{name} must be text")
    return value or ""


def list_field(data, name, kind):
    value = data.get(name) or []
    if not isinstance(value, list) or not all(isinstance(v, kind) for v in value):
        fail(f"{name} must be a list")
    return value


GET_API = {"/api/book": api_book, "/api/song": api_song}
POST_API = {"/api/rows": api_rows, "/api/paste": api_paste, "/api/fetch": api_fetch, "/api/search": api_search,
            "/api/links": api_links, "/api/save": api_save, "/api/publish": api_publish}


# ---------- the server ----------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet: the terminal shows only what the editor prints
        pass

    def parse_request(self):
        """Refuse other Host names: a web page could point its own name at 127.0.0.1
        (DNS rebinding) and read the token from the page."""
        if not super().parse_request():
            return False
        port = self.server.server_port
        if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            self.send_json(403, {"error": "wrong Host"})
            return False
        return True

    def send(self, status, data, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status, value):
        self.send(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def api(self, function, data):
        try:
            self.send_json(200, function(self.server.book, data))
        except ApiError as e:
            self.send_json(e.status, e.body)
        except (SongError, yaml.YAMLError) as e:
            self.send_json(400, {"error": str(e)})
        except Exception as e:  # the page shows it instead of waiting forever
            self.send_json(500, {"error": f"{type(e).__name__}: {e}"})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" and (EDITOR / "index.html").is_file():
            page = (EDITOR / "index.html").read_text(encoding="utf-8")
            page = page.replace("{{TOKEN}}", self.server.token).replace("{{BOOK}}", html.escape(self.server.book.title))
            return self.send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        if url.path.startswith("/static/"):
            name = url.path[len("/static/"):]
            folder = SHARED.get(name, EDITOR)
            path = folder / name
            if "/" not in name and "\\" not in name and not name.startswith(".") and path.is_file():
                kind = mimetypes.guess_type(name)[0] or "application/octet-stream"
                return self.send(200, path.read_bytes(), kind)
        if url.path in GET_API:
            return self.api(GET_API[url.path], {k: v[0] for k, v in parse_qs(url.query).items()})
        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        token = self.headers.get("X-Token", "")
        if not secrets.compare_digest(token.encode(), self.server.token.encode()):
            return self.send_json(403, {"error": "wrong or missing X-Token"})
        if path not in POST_API:
            return self.send_json(404, {"error": "not found"})
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except ValueError:
            data = None
        if not isinstance(data, dict):
            return self.send_json(400, {"error": "the request must be a JSON object"})
        with self.server.lock:  # one change at a time
            self.api(POST_API[path], data)


def make_server(book):
    """The editor's server on a free local port (not started yet)."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.book, server.token, server.lock = book, secrets.token_urlsafe(16), threading.Lock()
    return server


def serve(book):
    """Open the editor in the browser and serve it until Ctrl+C."""
    server = make_server(book)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"The song editor of {book.title} is open in your browser: {url}\nPress Ctrl+C here to stop it.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEditor stopped.")
    finally:
        server.server_close()
