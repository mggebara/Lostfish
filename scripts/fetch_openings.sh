#!/usr/bin/env bash
# Downloads the opening suites used by gauntlets into experiments/openings/ (gitignored).
#   scripts/fetch_openings.sh            # 8moves_v3.pgn (official-stockfish/books)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/experiments/openings"
BOOKS_URL="${BOOKS_URL:-https://github.com/official-stockfish/books/raw/master}"
mkdir -p "$DEST"

fetch_zip() {  # fetch_zip <name.pgn>
  local name="$1"
  if [[ -s "$DEST/$name" ]]; then echo "have $name"; return; fi
  local tmp; tmp="$(mktemp -d)"
  echo "download $BOOKS_URL/$name.zip"
  curl -fsSL --retry 3 -o "$tmp/$name.zip" "$BOOKS_URL/$name.zip"
  unzip -q -o "$tmp/$name.zip" "$name" -d "$tmp/out"
  mv "$tmp/out/$name" "$DEST/$name"
  rm -rf "$tmp"
  echo "$name: $(grep -c '^\[Event' "$DEST/$name" || true) games"
}

fetch_zip 8moves_v3.pgn
