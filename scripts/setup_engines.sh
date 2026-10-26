#!/usr/bin/env bash
# Downloads pinned engine binaries and tablebases into ./engines and ./tb.
#   scripts/setup_engines.sh            # Stockfish + fastchess (fast)
#   scripts/setup_engines.sh --syzygy   # also Syzygy 3-4-5 piece tablebases (~1 GB)
# Versions are pinned here and mirrored in configs/lostfish.yaml. Re-running is idempotent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SF_TAG="${SF_TAG:-sf_19}"
FC_TAG="${FC_TAG:-v1.8.2-alpha}"
SYZYGY_BASE="${SYZYGY_BASE:-https://tablebase.lichess.ovh/tables/standard}"   # has 3-4-5-wdl/ and 3-4-5-dtz/
WITH_SYZYGY=0
for a in "$@"; do [[ "$a" == "--syzygy" ]] && WITH_SYZYGY=1; done

OS="$(uname -s)"; ARCH="$(uname -m)"
case "$OS-$ARCH" in
  Darwin-arm64)  SF_ASSET="stockfish-macos-universal.tar.gz"; FC_ASSET="fastchess-mac-arm64.tar" ;;
  Darwin-x86_64) SF_ASSET="stockfish-macos-universal.tar.gz"; FC_ASSET="fastchess-mac-x86-64.tar" ;;
  Linux-x86_64)  SF_ASSET="stockfish-linux-x86-64-universal.tar.gz"; FC_ASSET="fastchess-linux-x86-64.tar" ;;
  Linux-aarch64) SF_ASSET="stockfish-linux-arm64-universal.tar.gz";      FC_ASSET="fastchess-linux-arm64.tar" ;;
  *) echo "unsupported platform $OS-$ARCH" >&2; exit 1 ;;
esac

mkdir -p engines/_dl tb

fetch() {  # fetch <url> <dest>
  local url="$1" dest="$2"
  if [[ -s "$dest" ]]; then echo "have $(basename "$dest")"; return; fi
  echo "download $url"
  curl -fL --retry 3 -C - -o "$dest.part" "$url" && mv "$dest.part" "$dest"
}

# --- Stockfish ---------------------------------------------------------------
if [[ ! -x engines/stockfish ]] || ! grep -q "$SF_TAG" engines/stockfish.version 2>/dev/null; then
  fetch "https://github.com/official-stockfish/Stockfish/releases/download/$SF_TAG/$SF_ASSET" "engines/_dl/$SF_ASSET"
  rm -rf engines/_dl/sf && mkdir -p engines/_dl/sf
  tar -xf "engines/_dl/$SF_ASSET" -C engines/_dl/sf
  SF_BIN="$(find engines/_dl/sf -type f -perm -u+x -name 'stockfish*' ! -name '*.nnue' | head -1)"
  [[ -n "$SF_BIN" ]] || { echo "no stockfish binary in $SF_ASSET" >&2; exit 1; }
  cp "$SF_BIN" engines/stockfish && chmod +x engines/stockfish
  echo "$SF_TAG" > engines/stockfish.version
fi
echo "stockfish: $(echo uci | engines/stockfish | grep '^id name')"

# --- fastchess ---------------------------------------------------------------
if [[ ! -x engines/fastchess ]] || ! grep -q "$FC_TAG" engines/fastchess.version 2>/dev/null; then
  fetch "https://github.com/Disservin/fastchess/releases/download/$FC_TAG/$FC_ASSET" "engines/_dl/$FC_ASSET"
  rm -rf engines/_dl/fc && mkdir -p engines/_dl/fc
  tar -xf "engines/_dl/$FC_ASSET" -C engines/_dl/fc
  FC_BIN="$(find engines/_dl/fc -type f -name 'fastchess*' ! -name '*.tar' | head -1)"
  [[ -n "$FC_BIN" ]] || { echo "no fastchess binary in $FC_ASSET" >&2; exit 1; }
  cp "$FC_BIN" engines/fastchess && chmod +x engines/fastchess
  echo "$FC_TAG" > engines/fastchess.version
fi
echo "fastchess: $(engines/fastchess --version 2>&1 | head -1)"

# --- Syzygy 3-4-5 -------------------------------------------------------------
if [[ "$WITH_SYZYGY" == 1 ]]; then
  mkdir -p tb/syzygy
  for sub in 3-4-5-wdl 3-4-5-dtz; do
    LIST="$(curl -fsL "$SYZYGY_BASE/$sub/" | grep -oE 'href="K[A-Z]*v[A-Z]*\.rtb[wz]"' | sed -E 's/href="(.*)"/\1/' | sort -u)"
    N="$(echo "$LIST" | wc -l | tr -d ' ')"
    echo "syzygy $sub: $N files"
    i=0
    for f in $LIST; do
      i=$((i+1))
      [[ -s "tb/syzygy/$f" ]] && continue
      printf '[%3d/%s] %s\n' "$i" "$N" "$f"
      curl -fsL --retry 5 -C - -o "tb/syzygy/$f.part" "$SYZYGY_BASE/$sub/$f" && mv "tb/syzygy/$f.part" "tb/syzygy/$f"
    done
  done
  echo "syzygy: $(ls tb/syzygy | wc -l | tr -d ' ') files, $(du -sh tb/syzygy | cut -f1)"
fi
echo "done"
