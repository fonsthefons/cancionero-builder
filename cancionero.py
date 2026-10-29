"""Create song books and add songs to them.

    .venv/bin/python cancionero.py                 a menu: create a book, add songs, publish...
    .venv/bin/python cancionero.py help [new|edit] how to create a book, or add songs to one
    .venv/bin/python cancionero.py new [name]      create a new song book (asks the rest)
    .venv/bin/python cancionero.py add <book>      add songs: link, search, paste, PDF, list
    .venv/bin/python cancionero.py add-list <book> <list.txt> [--section Want] [--report Checked.txt]
    .venv/bin/python cancionero.py add-pdf <book> <songbook.pdf> [--all] [--author A] [--section-tags] [--links]
    .venv/bin/python cancionero.py links <book> [--ask]   find Spotify/YouTube links for songs without one
    .venv/bin/python cancionero.py tags <book> [--write]  list the book's tags (--write: all of them into tags.yaml)
    .venv/bin/python cancionero.py build <book>    rebuild index.html after editing songs by hand
    .venv/bin/python cancionero.py publish <book>  rebuild, commit and push (the website updates)
    .venv/bin/python cancionero.py list            the books next to the builder

<book> is a book's folder name (looked for next to this builder, in
CANCIONERO_BOOKS if set) or a path to its folder.
"""

import argparse
import os
import sys
from pathlib import Path

from builder.book import BookError, load_book
from builder.build import build_book, load_book_songs
from builder.create import CreateError, create_book, default_title, publish_book
from builder.songs import SongError

ROOT = Path(__file__).resolve().parent
BOOKS_DIR = Path(os.environ.get("CANCIONERO_BOOKS", ROOT.parent / "hymn_books")).expanduser()


# ---------- finding books ----------

def find_books():
    """Folders next to the builder that are song books."""
    if not BOOKS_DIR.is_dir():
        return []
    return sorted(p for p in BOOKS_DIR.iterdir() if (p / "book.yaml").is_file())


def open_book(name):
    path = Path(name).expanduser()
    if not (path.is_absolute() or "/" in name or name.startswith(".")):
        path = BOOKS_DIR / name
    if not path.exists():
        books = ", ".join(p.name for p in find_books()) or "none yet"
        raise BookError(f"There is no book {path}. Create it with: cancionero.py new {path.name}"
                        f"\n(books found: {books}; more in: cancionero.py help)")
    return load_book(path)


def pick_book():
    from importer.ask import ask_number

    books = find_books()
    if not books:
        print(f"No song books in {BOOKS_DIR} yet. Create one first.")
        return None
    print("\nSong books:")
    for n, path in enumerate(books, start=1):
        print(f"  {n}  {path.name}")
    number = ask_number("Which book?", len(books), 1 if len(books) == 1 else None)
    return load_book(books[number - 1]) if number else None


def build_and_report(book):
    try:
        print(build_book(book).report(book))
        return True
    except SongError as e:
        print(e, file=sys.stderr)
        return False


# ---------- commands ----------

def ask_tags_setup():
    """Tags typed in when creating a book: [(label, [subtag labels])]."""
    from importer.ask import ask

    print("Type the tags, one at a time (e.g. Misa, Adoración, Navidad). Enter on an empty line to finish.")
    tags = []
    while True:
        label = ask("Tag")
        if not label:
            return tags
        subs = ask(f"  Subtags of {label}, separated by commas (Enter for none)")
        tags.append((label, [s.strip() for s in subs.split(",") if s.strip()]))


def cmd_new(args):
    from importer.ask import ask, ask_yes

    print("\nNew song book\n")
    name = args.name
    while True:
        name = name or ask("Name of the book's folder and repo (e.g. cancionero-misa, songs-to-learn)")
        try:
            from builder.create import check_name
            check_name(name, BOOKS_DIR)
            break
        except CreateError as e:
            print(f"Sorry: {e}.")
            name = None
    settings = {"title": ask("Title shown in the book", default_title(name))}
    author = ask("Artist of most songs, suggested when adding and not shown (Enter for none)")
    if author:
        settings["default_author"] = author

    print("\nTags (the book's contents, e.g. Misa > Entrada, Comunión):")
    print("  1) None for now: write any tag in the songs as you add them (it appears in the book)")
    print("  2) Type them now")
    print("  3) Copy the tags of another book")
    choice = ask("Choose", "1")
    tags, copy_from = None, None
    if choice == "2":
        tags = ask_tags_setup()
    elif choice == "3":
        from importer.ask import ask_number

        # any book folder with a tags.yaml (the original repos too)
        sources = [p for p in sorted(BOOKS_DIR.iterdir()) if (p / "tags.yaml").is_file()]
        for n, path in enumerate(sources, start=1):
            print(f"  {n}  {path.name}")
        number = ask_number("Which one?", len(sources)) if sources else None
        copy_from = sources[number - 1] / "tags.yaml" if number else None

    print("\nWhere should songs be looked for?")
    print("  1) Everywhere: Ultimate Guitar, LaCuerda, Cifra Club and any other site")
    print("  2) Ultimate Guitar only")
    if ask("Choose", "1") == "2":
        settings["sites"] = ["ultimate_guitar"]
    if ask_yes("Tag each song English or Spanish automatically (from its lyrics)?"):
        settings["language_tags"] = True
    print("(More settings: the book's book.yaml; see builder/book.py.)")

    github = ask_yes("\nCreate its GitHub repo and website now (public, GitHub Pages)?", default=not args.dry_run)
    try:
        book = create_book(name, settings, BOOKS_DIR, tags=tags, copy_tags_from=copy_from,
                           github=github or args.dry_run, dry_run=args.dry_run)
    except (CreateError, BookError) as e:
        print(f"Couldn't create the book: {e}")
        return 1
    if ask_yes("\nAdd songs now?", default=True):
        return add_loop(book, offline=False)
    print(f"Add songs later with: .venv/bin/python cancionero.py add {name}")
    return 0


def add_loop(book, offline=False):
    """The add menu, again and again until Done; then offer to publish."""
    from importer.add import add_song, menu
    from importer.ask import ask, ask_yes
    from importer.batch import add_list
    from importer.pdf_add import add_pdf

    added = 0
    while True:
        choice = menu(book)
        if choice in ("0", "q", ""):
            break
        if choice in ("1", "2", "3"):
            added += 1 if add_song(book, choice, offline=offline) else 0
        elif choice == "4":
            path = ask("Path of the PDF file (you can drag it into this window)").strip().strip("'\"")
            if path:
                added += len(add_pdf(book, Path(path).expanduser()))
        elif choice == "5":
            path = ask("Path of the list file (one song per line: Title - Artist)").strip().strip("'\"")
            if path:
                section = ask("Only the songs under this heading (Enter for all)") or None
                added += len(add_list(book, Path(path).expanduser(), section=section)[0])
        else:
            print("Please choose a number from the menu.")
            continue
        build_and_report(book)
    if added and (book.root / ".git").exists() and ask_yes("Publish the changes now (commit and push)?", default=True):
        try:
            publish_book(book)
        except CreateError as e:
            print(f"Couldn't publish: {e}")
    return 0


def cmd_add(args):
    return add_loop(open_book(args.book), offline=args.offline)


def cmd_add_list(args):
    from importer.batch import add_list

    book = open_book(args.book)
    added, _ = add_list(book, args.list, section=args.section, report=args.report, limit=args.limit)
    if added and not args.no_build:
        build_and_report(book)
    return 0


def cmd_add_pdf(args):
    from importer.pdf_add import add_pdf

    book = open_book(args.book)
    quiet = args.all
    written = add_pdf(book, args.pdf, select="all" if args.all else None, author=args.author,
                      sections_as_tags=True if args.section_tags else (False if quiet else None),
                      links=True if args.links else (False if quiet else None), ask_user=not quiet)
    if written and not args.no_build:
        build_and_report(book)
    return 0


def cmd_links(args):
    from importer.links import fill_links

    book = open_book(args.book)
    if fill_links(book, ask_each=args.ask, limit=args.limit) and not args.no_build:
        build_and_report(book)
    return 0


def cmd_tags(args):
    book = open_book(args.book)
    try:
        songs, taxonomy = load_book_songs(book)
    except SongError as e:
        print(e, file=sys.stderr)
        return 1
    for tag in taxonomy.tags.values():
        count = sum(1 for s in songs if tag.id in s.tags)
        where = "" if tag.in_file else "   (only in songs)"
        print(f"{tag.label} [{tag.id}]: {count} songs{where}")
        for sub_id, label in tag.subtags.items():
            sub_count = sum(1 for s in songs if sub_id in s.tags.get(tag.id, []))
            print(f"    {label} [{sub_id}]: {sub_count} songs")
    if args.write:
        book.tags_file.write_text(taxonomy.to_yaml(), encoding="utf-8")
        print(f"Wrote every tag to {book.tags_file}: edit labels and order there.")
    return 0


def cmd_build(args):
    return 0 if build_and_report(open_book(args.book)) else 1


def cmd_publish(args):
    try:
        publish_book(open_book(args.book), message=args.message, dry_run=args.dry_run)
    except (CreateError, SongError) as e:
        print(f"Couldn't publish: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_list(args):
    books = find_books()
    if not books:
        print(f"No song books in {BOOKS_DIR}.")
    for path in books:
        try:
            book = load_book(path)
            count = len(list(book.songs_dir.glob("*.md")))
            print(f"{path.name:30} {book.title} ({count} songs){'  ' + book.url if book.url else ''}")
        except BookError as e:
            print(f"{path.name:30} (book.yaml has a problem: {e})")
    return 0


RUN = ".venv/bin/python cancionero.py"

HELP = {
    "new": f"""\
CREATE A NEW BOOK

  1. {RUN} new my-book
     Asks for the title, the usual artist and the first tags, then makes the
     folder ~/Documents/programs/hymn_books/my-book (its own git repo), builds it, and creates the
     GitHub repo and its website. Try it first with --dry-run: the folder is
     made, the GitHub steps are only shown.

  2. Add songs (see "help edit"), for example:
     {RUN} add my-book
     {RUN} add-pdf my-book ~/Downloads/songbook.pdf

  3. Look at it on this computer:  open ~/Documents/programs/hymn_books/my-book/index.html

  4. Put it online:  {RUN} publish my-book
     The website (https://<you>.github.io/my-book/) updates in a minute or two.
""",
    "edit": f"""\
WORK ON AN EXISTING BOOK

  See your books:          {RUN} list

  Add songs, asking as it goes (a link, a search, pasted text, a PDF or a list):
                           {RUN} add my-book
  Add a PDF songbook:      {RUN} add-pdf my-book songbook.pdf
                           (songs to check go to my-book/import-report.txt)
  Add a list of songs:     {RUN} add-list my-book list.txt
                           (one song per line: Title - Artist)
  Find Spotify/YouTube links for songs without one:
                           {RUN} links my-book

  Edit a song by hand:     change ~/Documents/programs/hymn_books/my-book/songs/<song>.md, then
                           {RUN} build my-book
  Remove a song:           delete its file in songs/, then build
  See the tags:            {RUN} tags my-book
  Labels/order of tags:    edit my-book/tags.yaml, then build
  Book settings (title, colours, folded contents...):
                           edit my-book/book.yaml, then build

  Put the changes online:  {RUN} publish my-book
""",
}


def cmd_help(args):
    topic = getattr(args, "topic", None)
    if topic in HELP:
        print(HELP[topic])
    else:
        print(f"Song books: what do you want to do?\n\n"
              f"  Create a new book:              {RUN} help new\n"
              f"  Add songs to / change a book:   {RUN} help edit\n"
              f"  Every command and option:       {RUN} --help\n"
              f"  A menu that asks you:           {RUN}\n")
        print(HELP["new"])
        print(HELP["edit"])
    return 0


def interactive():
    from importer.ask import ask

    print("Song books\n")
    print("  1) Create a new song book")
    print("  2) Add songs to a book")
    print("  3) Find Spotify/YouTube links for a book's songs")
    print("  4) Rebuild a book (after editing songs by hand)")
    print("  5) Publish a book (commit and push)")
    print("  6) List the books")
    print("  7) Help: how to create a book or add songs")
    choice = ask("Choose", "2" if find_books() else "1")
    if choice == "1":
        return cmd_new(argparse.Namespace(name=None, dry_run=False))
    if choice == "6":
        return cmd_list(None)
    if choice == "7":
        return cmd_help(None)
    book = pick_book()
    if book is None:
        return 1
    if choice == "2":
        return add_loop(book)
    if choice == "3":
        from importer.links import fill_links
        fill_links(book, ask_each=True)
        return 0 if build_and_report(book) else 1
    if choice == "4":
        return 0 if build_and_report(book) else 1
    if choice == "5":
        return cmd_publish(argparse.Namespace(book=str(book.root), message=None, dry_run=False))
    print("Please choose a number from the menu.")
    return 1


def parser():
    p = argparse.ArgumentParser(description="Create song books and add songs to them.",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="command")

    c = sub.add_parser("help", help="how to create a book, or add songs to one")
    c.add_argument("topic", nargs="?", choices=sorted(HELP), help="new: create a book; edit: change one")
    c.set_defaults(run=cmd_help)

    c = sub.add_parser("new", help="create a new song book")
    c.add_argument("name", nargs="?", help="folder and repo name, e.g. songs-to-learn")
    c.add_argument("--dry-run", action="store_true", help="create the folder but only show the GitHub commands")
    c.set_defaults(run=cmd_new)

    c = sub.add_parser("add", help="add songs, asking as it goes")
    c.add_argument("book")
    c.add_argument("--offline", action="store_true", help="don't look up Spotify/YouTube links")
    c.set_defaults(run=cmd_add)

    c = sub.add_parser("add-list", help="add a list of songs without questions")
    c.add_argument("book")
    c.add_argument("list", type=Path, help="one song per line (Title - Artist), or Ultimate Guitar's saved list")
    c.add_argument("--section", help="only read this section of the list (e.g. Want)")
    c.add_argument("--report", type=Path, help="add the results to this file (e.g. Checked.txt)")
    c.add_argument("--limit", type=int, help="add at most this many songs")
    c.add_argument("--no-build", action="store_true")
    c.set_defaults(run=cmd_add_list)

    c = sub.add_parser("add-pdf", help="add the songs of a PDF songbook")
    c.add_argument("book")
    c.add_argument("pdf", type=Path)
    c.add_argument("--all", action="store_true", help="every song, no questions")
    c.add_argument("--author", help="author of the songs (default: as written in the PDF)")
    c.add_argument("--section-tags", action="store_true", help="the PDF's section headings become tags")
    c.add_argument("--links", action="store_true", help="look up Spotify/YouTube links (slow)")
    c.add_argument("--no-build", action="store_true")
    c.set_defaults(run=cmd_add_pdf)

    c = sub.add_parser("links", help="find Spotify/YouTube links for songs without one")
    c.add_argument("book")
    c.add_argument("--ask", action="store_true", help="choose the link for each song")
    c.add_argument("--limit", type=int)
    c.add_argument("--no-build", action="store_true")
    c.set_defaults(run=cmd_links)

    c = sub.add_parser("tags", help="list the book's tags and how many songs each has")
    c.add_argument("book")
    c.add_argument("--write", action="store_true", help="write every tag (also those only in songs) to tags.yaml")
    c.set_defaults(run=cmd_tags)

    c = sub.add_parser("build", help="rebuild a book's index.html")
    c.add_argument("book")
    c.set_defaults(run=cmd_build)

    c = sub.add_parser("publish", help="rebuild, commit and push a book")
    c.add_argument("book")
    c.add_argument("-m", "--message", help="commit message (default: the songs added/changed)")
    c.add_argument("--dry-run", action="store_true", help="only show the git commands")
    c.set_defaults(run=cmd_publish)

    c = sub.add_parser("list", help="list the song books")
    c.set_defaults(run=cmd_list)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if not args.command:
            return interactive()
        return args.run(args)
    except BookError as e:
        print(e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
