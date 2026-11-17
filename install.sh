#!/usr/bin/env bash
# Install cancionero-builder on this Mac. Safe to re-run: what is in place is skipped.
set -uo pipefail
cd "$(dirname "$0")"
FAILED=()
try() { local what=$1; shift; echo "==> $what"; "$@" || FAILED+=("$what"); }

# 1. .venv with the pinned packages (Homebrew's python3 if there: macOS's own is old)
PY=python3; [ -x /opt/homebrew/bin/python3 ] && PY=/opt/homebrew/bin/python3
[ -x .venv/bin/python ] || try ".venv" "$PY" -m venv .venv
try "pip install -r requirements.txt" .venv/bin/python -m pip install -q -r requirements.txt

# 2. WebKit for the song sites that refuse plain downloads (the builder would otherwise offer it on first use)
try "playwright webkit" .venv/bin/python -m playwright install webkit

# 3. The book repos, next to this one in ../hymn_books (each one its own GitHub repo with Pages)
BOOKS=${CANCIONERO_BOOKS:-../hymn_books}
mkdir -p "$BOOKS"
for book in cancionero cancionero-hakuna cancionero-pagano cancionero-liturgia cancionero-organo; do
  [ -d "$BOOKS/$book" ] || try "clone $book" git clone -q "git@github.com:fonsthefons/$book.git" "$BOOKS/$book"
done

# 4. Tests
try "tests" .venv/bin/python -m pytest tests -q -p no:cacheprovider

echo
echo "================ SUMMARY ================"
if [ ${#FAILED[@]} -eq 0 ]; then echo "Everything installed OK."; else
  echo "FAILED (re-running ./install.sh is safe):"; for x in "${FAILED[@]}"; do echo " ✗ $x"; done
fi
cat <<'EOF'

EXTRA STEPS (by hand):
  • GitHub CLI logged in, to create and publish books: brew install gh && gh auth login
    (cloning the books above also needs your SSH key on GitHub).
  • Books in another folder: export CANCIONERO_BOOKS=/path/to/books.
  • Browser page checks (optional): PLAYWRIGHT_BROWSERS_PATH=scratch/browsers .venv/bin/python -m playwright install chromium webkit
EOF
[ ${#FAILED[@]} -eq 0 ]
