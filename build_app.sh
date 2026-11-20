#!/bin/bash
# Baut KlarBild.app für macOS mit PyInstaller.
#
# Liegt ein portables ffmpeg in vendor/ (siehe tools/bundle_ffmpeg_macos.sh), wird es in die
# App gepackt – dann braucht der Mac kein Homebrew. Lizenz von ffmpeg beachten (siehe README).
set -euo pipefail
cd "$(dirname "$0")"

python3 -m pip install -r requirements.txt pyinstaller pillow
rm -rf build dist
python3 tools/make_icon.py build/icon.png

python3 -m PyInstaller --noconfirm --windowed --name KlarBild --icon build/icon.png \
  --osx-bundle-identifier de.klarbild.app \
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.Qt3DCore \
  --exclude-module tkinter main.py

APP=dist/KlarBild.app
if [[ -x vendor/ffmpeg && -x vendor/ffprobe ]]; then
  echo "→ ffmpeg aus vendor/ wird eingepackt"
  DEST="$APP/Contents/Frameworks/bin"
  mkdir -p "$DEST"
  cp -R vendor/ffmpeg vendor/ffprobe vendor/libs "$DEST"/
  # Jede eingepackte Datei ad hoc signieren (auf Apple-Chips Pflicht), dann das ganze Paket
  find "$DEST" -type f -exec codesign --force --sign - {} \;
fi
codesign --force --sign - "$APP"
codesign --verify --deep --strict --verbose=1 "$APP"

echo
echo "Fertig: $APP – in den Programme-Ordner ziehen."
