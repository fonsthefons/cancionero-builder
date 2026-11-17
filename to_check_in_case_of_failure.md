# What to check when cancionero-builder fails

The builder stops with a message that names the file and the problem. Fix that file and run the same command again. First check that the code itself still works: `.venv/bin/python -m pytest tests -q -p no:cacheprovider`.

## `build` / `publish` stops

| Message | Where to look | What to do |
|---|---|---|
| `... is not a song book (it has no book.yaml)` | The book name or path | Run `cancionero.py list` to see the books it finds. They must be in `../hymn_books/` or `$CANCIONERO_BOOKS`. |
| `book.yaml: ...` (an unknown setting or a bad value) | `<book>/book.yaml` | Every setting and its default is in `builder/book.py` (`DEFAULTS`). YAML indentation and `:` matter. |
| `Invalid songs:` followed by one line per song | `<book>/songs/<file>.md` | Usually a frontmatter not closed with `---`, `missing field(s)`, a `link` without `http(s)://`, or `song_tags` written as a list instead of `misa: [entrada]`. |
| `tab has N notes but melody has M` | The song's `melody`/`tab` | Make the counts match, or add `ignore: ["tab-melody-check"]` when the tab covers only the first notes. |
| `horas.yaml: ...` / a `horas:` pattern that matches nothing | `<book>/horas.yaml` and the song's `horas:` | Check the slot path against the tree (ids joined with `/`). Quote patterns that start with `*`. |
| An unknown tag (with `strict_tags: true`) | `<book>/tags.yaml` | Add the tag to `tags.yaml`, or fix its spelling in the song. |

## `publish` / `new` (git and GitHub)

| Symptom | Cause | What to do |
|---|---|---|
| `couldn't ask GitHub who you are` | `gh` missing or logged out | `gh auth login`, then `gh auth status`. |
| `git push` rejected | The book repo changed on GitHub (an edit on the web, or another Mac) | `git -C ../hymn_books/<book> pull --rebase`, then `publish` again. |
| `... is not a git repo` | The book folder was copied, not cloned | Clone it again (`./install.sh` clones missing books). |
| `GitHub already has a repo` | `new` with a name already taken | Choose another name, or clone the existing repo instead. |
| The website doesn't change after `publish` | GitHub Pages is still building, or the phone is caching the old version | Wait 1–2 min. Check `https://github.com/fonsthefons/<book>/actions`. On the phone, reload the page (the old version is kept by `sw.js` for offline use). |

## Adding songs (`add`, `add-list`, `add-pdf`, `links`)

- **`the site refused the download (error 403)` / `the site answered with error N`**: that site blocks scripts. Install the browser engine: `.venv/bin/python -m playwright install webkit` (or `./install.sh`). If it still fails, the site changed its layout: paste the song's text instead (`add` → pasted text).
- **`couldn't open the link`**: no internet, or a wrong URL.
- **Spotify/YouTube link not found or wrong**: links are found through a DuckDuckGo search, which can be rate-limited for a while. Try again later, run `links <book> --ask` to pick the link yourself, or paste the link into the song's `link:` field.
- **`add-pdf` finds few songs**: it only reads text PDFs, not scans. OCR the PDF first with pdf-worker (`pdf-worker ocr book.pdf`). Then check the "doubtful songs" it lists.
- **Chords out of line**: chords must sit on their own line, above the letters, with spaces (not tabs).

## Install

- **`.venv` fails**: macOS's own `python3` is old. Delete `.venv` and re-run `./install.sh` (it uses Homebrew's Python).
- **Cloning a book fails**: your SSH key isn't on GitHub (`ssh -T git@github.com`), or the repo is private and your account has no access.
