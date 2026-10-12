"""Creating a new song book (a folder that is its own git repo, published with
GitHub Pages), and publishing a book's changes.

A new book gets: book.yaml, an optional tags.yaml, songs/, a README for
whoever opens the repo, a .gitignore, and a first build (index.html, sw.js,
manifest, icons). Then git init + a first commit, and, when asked for, a GitHub
repo (gh CLI) with GitHub Pages serving the main branch.
"""

import re
import shutil
import subprocess
from pathlib import Path

from .book import CONFIG_NAME, load_book, settings_yaml
from .build import build_book
from .tags import add_to_tags_file
from .text import humanize, slug

BUILDER_ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,99}")
GITIGNORE = """.DS_Store
# written when importing a PDF: songs to check by hand
import-report.txt
"""


class CreateError(Exception):
    pass


def run(command, cwd=None, dry_run=False, log=print, capture=False):
    """Run a command (a list, no shell). In a dry run only print it."""
    shown = " ".join(command)
    if dry_run:
        log(f"  (dry run) {shown}")
        return ""
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        raise CreateError(f"`{shown}` failed:\n{(result.stderr or result.stdout).strip()}")
    return result.stdout.strip() if capture else ""


def check_name(name, books_dir):
    if not NAME_RE.fullmatch(name or ""):
        raise CreateError("the name may only have lowercase letters, digits and - (e.g. songs-to-learn)")
    if (Path(books_dir) / name).exists():
        raise CreateError(f"{Path(books_dir) / name} already exists")


def default_title(name):
    return humanize(name)


def readme(settings, url=None):
    title = settings["title"]
    lines = [
        f"# {title}",
        "",
        "A song book with chords, as one web page (`index.html`)"
        + (f", live at **{url}**." if url else "."),
        "",
        "This repo holds the book's songs and settings. The page is built with",
        "[cancionero-builder](https://github.com/fonsthefons/cancionero-builder): from the",
        "builder's folder,",
        "",
        "```bash",
        f".venv/bin/python cancionero.py add {settings['_name']}       # add songs (link, search, paste, PDF, list)",
        f".venv/bin/python cancionero.py build {settings['_name']}     # rebuild after editing a song by hand",
        f".venv/bin/python cancionero.py publish {settings['_name']}   # commit and push: the site updates in a minute",
        "```",
        "",
        "| Path | What it is |",
        "|------|------------|",
        "| `songs/*.md` | One file per song: details at the top, then the lyrics with chords above them |",
        "| `book.yaml` | The book's settings (title, author of most songs, which sites to search...) |",
        "| `tags.yaml` | Optional: labels and order of the tags and subtags |",
        "| `index.html`, `sw.js`, `manifest.webmanifest`, `icon-*.png` | Written by the build |",
        "",
        "A song file:",
        "",
        "```",
        "---",
        "title: Sopla Señor",
        "autor: popular",
        'capo: "2"',
        'link: "https://open.spotify.com/track/..."',
        "song_tags:",
        "  misa: [comunion]",
        "  Adoración: []",
        "---",
        "",
        "G              C",
        "First line of lyrics",
        "```",
        "",
        "Tags can be anything: a tag written in a song appears in the book's contents.",
        "",
    ]
    return "\n".join(lines)


def write_tags(path, tags):
    """tags: [(label, [subtag labels])] typed by the user."""
    for label, subtags in tags:
        if not subtags:
            add_to_tags_file(path, slug(label), label)
        for sub in subtags:
            add_to_tags_file(path, slug(label), label, slug(sub), sub)


def create_book(name, settings, books_dir, tags=None, copy_tags_from=None, github=False, public=True,
                dry_run=False, log=print):
    """Create the book folder, build it, commit it; with `github`, create the repo
    and turn on GitHub Pages. Returns the Book."""
    check_name(name, books_dir)
    root = Path(books_dir) / name
    settings = dict(settings)
    settings.setdefault("title", default_title(name))
    settings.setdefault("storage_key", name)

    owner = None
    if github:
        try:  # read-only, so also in a dry run
            owner = run(["gh", "api", "user", "--jq", ".login"], log=log, capture=True)
        except (CreateError, OSError) as e:
            if not dry_run:
                raise CreateError(f"couldn't ask GitHub who you are (is `gh` installed and logged in?): {e}")
            owner = "<you>"
        if not dry_run:
            exists = subprocess.run(["gh", "repo", "view", f"{owner}/{name}"], capture_output=True)
            if exists.returncode == 0:
                raise CreateError(f"GitHub already has a repo {owner}/{name}")
        settings["url"] = f"https://{owner}.github.io/{name}/"

    root.mkdir(parents=True)
    try:
        book = make_files(root, name, settings, tags, copy_tags_from, log)
    except Exception:
        shutil.rmtree(root)  # only the folder made just now: try again from scratch
        raise

    run(["git", "init", "-q", "-b", "main"], cwd=root, log=log)
    run(["git", "add", "-A"], cwd=root, log=log)
    run(["git", "commit", "-q", "-m", f"New song book: {settings['title']}"], cwd=root, log=log)
    log(f"Created {root}")

    if github:
        visibility = "--public" if public else "--private"
        run(["gh", "repo", "create", f"{owner}/{name}", visibility, "--source", str(root),
             "--remote", "origin", "--push", "--description", f"Song book: {settings['title']}"],
            dry_run=dry_run, log=log)
        run(["gh", "api", "-X", "POST", f"repos/{owner}/{name}/pages",
             "-f", "source[branch]=main", "-f", "source[path]=/"], dry_run=dry_run, log=log)
        log(f"GitHub repo: https://github.com/{owner}/{name}")
        log(f"The book will be live in a minute or two at {settings['url']}")
    return book


def make_files(root, name, settings, tags, copy_tags_from, log):
    (root / "songs").mkdir()
    (root / "songs" / ".gitkeep").write_text("", encoding="utf-8")
    (root / CONFIG_NAME).write_text(settings_yaml(settings), encoding="utf-8")
    if copy_tags_from:
        (root / "tags.yaml").write_text(Path(copy_tags_from).read_text(encoding="utf-8"), encoding="utf-8")
    if tags:
        write_tags(root / "tags.yaml", tags)
    (root / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (root / "README.md").write_text(readme(dict(settings, _name=name), settings.get("url")), encoding="utf-8")

    book = load_book(root)
    log(build_book(book).report(book))
    return book


# ---------- publishing ----------

def changed_songs(root):
    """Song titles added / changed / removed since the last commit (from git status)."""
    out = run(["git", "status", "--porcelain", "--", "songs"], cwd=root, capture=True)
    added, changed, removed = [], [], []
    for line in out.splitlines():
        status, path = line[:2], line[3:].strip().strip('"')
        name = Path(path).stem.replace("_", " ")
        if not path.endswith(".md"):
            continue
        (removed if "D" in status else added if "?" in status or "A" in status else changed).append(name)
    return added, changed, removed


def commit_message(added, changed, removed):
    parts = []
    for verb, names in (("Add", added), ("Update", changed), ("Remove", removed)):
        if names:
            shown = ", ".join(names[:5]) + (f" and {len(names) - 5} more" if len(names) > 5 else "")
            parts.append(f"{verb} {shown}")
    return "; ".join(parts) or "Update the book"


def publish_book(book, message=None, dry_run=False, log=print):
    """Rebuild, commit everything and push. Returns False when there was nothing to publish."""
    log(build_book(book).report(book))
    if not (book.root / ".git").exists():
        raise CreateError(f"{book.root} is not a git repo")
    status = run(["git", "status", "--porcelain"], cwd=book.root, capture=True)
    if not status:
        log("Nothing to publish: no changes since the last commit.")
        return False
    message = message or commit_message(*changed_songs(book.root))
    run(["git", "add", "-A"], cwd=book.root, dry_run=dry_run, log=log)
    run(["git", "commit", "-q", "-m", message], cwd=book.root, dry_run=dry_run, log=log)
    remote = run(["git", "remote"], cwd=book.root, capture=True)
    if remote:
        run(["git", "push", "-q"], cwd=book.root, dry_run=dry_run, log=log)
        log(f"Published: {message}" + (f"\nThe site updates in a minute: {book.url}" if book.url else ""))
    else:
        log(f"Committed: {message} (no GitHub remote to push to)")
    return True
