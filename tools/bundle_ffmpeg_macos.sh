#!/bin/bash
# Holt ffmpeg/ffprobe mit vid.stab aus Homebrew und macht sie portabel:
# alle benötigten Bibliotheken landen in vendor/libs, Verweise zeigen auf @executable_path/libs.
# build_app.sh packt vendor/ anschließend in die App. Nur für macOS.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v brew >/dev/null || { echo "Homebrew fehlt (https://brew.sh)"; exit 1; }
export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1

brew list dylibbundler >/dev/null 2>&1 || brew install dylibbundler

has_vidstab() { [[ -x "$1/ffmpeg" ]] && "$1/ffmpeg" -hide_banner -filters 2>/dev/null | grep -q vidstabdetect; }

brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
BIN="$(brew --prefix ffmpeg)/bin"
if ! has_vidstab "$BIN"; then
  echo "→ Homebrew-ffmpeg enthält kein vid.stab – nehme ffmpeg-full"
  brew list ffmpeg-full >/dev/null 2>&1 || brew install ffmpeg-full
  BIN="$(brew --prefix ffmpeg-full)/bin"
  has_vidstab "$BIN" || { echo "Auch ffmpeg-full hat kein vid.stab"; exit 1; }
fi
echo "→ Quelle: $BIN"

rm -rf vendor
mkdir -p vendor/libs
cp "$BIN/ffmpeg" "$BIN/ffprobe" vendor/
chmod u+w vendor/ffmpeg vendor/ffprobe

SEARCH=(-s "$(brew --prefix)/lib")
for d in "$(brew --prefix)"/opt/*/lib; do SEARCH+=(-s "$d"); done
# </dev/null: falls eine Bibliothek fehlt, abbrechen statt auf Eingabe zu warten
dylibbundler -cd -of -b -x vendor/ffmpeg -x vendor/ffprobe -d vendor/libs -p @executable_path/libs/ \
  "${SEARCH[@]}" </dev/null

if otool -L vendor/ffmpeg vendor/ffprobe vendor/libs/*.dylib | grep -E "$(brew --prefix)|/usr/local/(opt|Cellar)|@rpath"; then
  echo "Fehler: Es zeigen noch Verweise auf Homebrew."
  exit 1
fi
echo "→ $(ls vendor/libs | wc -l | tr -d ' ') Bibliotheken, $(du -sh vendor | cut -f1) insgesamt"
vendor/ffmpeg -hide_banner -version | head -1
