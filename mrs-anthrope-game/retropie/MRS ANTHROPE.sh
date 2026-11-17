#!/bin/bash
# MRS. ANTHROPE - Road to the Gig  |  RetroPie "Ports" launcher
#
# Copy this file together with mrs-anthrope.html into ~/RetroPie/roms/ports/
# (network share: \\RETROPIE\roms\ports), restart EmulationStation and start it from "Ports".
# The first start installs a minimal X server + Chromium (internet needed, takes a few minutes).
# Quit: hold SELECT+START on the gamepad (or press F10 on a keyboard).

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME="$DIR/mrs-anthrope.html"
LOG="/dev/shm/mrs-anthrope.log"

find_browser() { command -v chromium-browser || command -v chromium; }

if [ ! -f "$GAME" ]; then
  echo "mrs-anthrope.html nicht gefunden (erwartet in $DIR)."
  sleep 10; exit 1
fi

if [ -z "$(find_browser)" ] || ! command -v xinit >/dev/null || ! command -v xdotool >/dev/null; then
  clear
  echo "=================================================================="
  echo " MRS. ANTHROPE - einmalige Installation (Browser + Grafikserver)"
  echo " Internet noetig, das dauert ein paar Minuten ..."
  echo "=================================================================="
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends xserver-xorg xserver-xorg-legacy xinit x11-xserver-utils xdotool
  sudo apt-get install -y --no-install-recommends chromium-browser || sudo apt-get install -y --no-install-recommends chromium
  # allow starting the X server from the EmulationStation console
  printf 'allowed_users=anybody\nneeds_root_rights=yes\n' | sudo tee /etc/X11/Xwrapper.config >/dev/null
  if [ -z "$(find_browser)" ] || ! command -v xinit >/dev/null || ! command -v xdotool >/dev/null; then
    echo
    echo "Installation fehlgeschlagen - bitte Internetverbindung pruefen und erneut starten."
    sleep 12; exit 1
  fi
fi
BROWSER="$(find_browser)"

SESSION="$(mktemp /dev/shm/mrs-anthrope-session.XXXXXX)"
cat > "$SESSION" <<EOF
#!/bin/bash
xset s off -dpms s noblank 2>/dev/null
"$BROWSER" --kiosk --start-fullscreen --noerrdialogs --disable-infobars --no-first-run \\
  --autoplay-policy=no-user-gesture-required --disable-features=Translate,TranslateUI \\
  --disable-session-crashed-bubble --check-for-update-interval=31536000 --password-store=basic \\
  --user-data-dir=/dev/shm/mrs-anthrope-chromium "file://$GAME#pi" &
PID=\$!
# the game sets its window title to MRS-ANTHROPE-QUIT when SELECT+START is held
while kill -0 \$PID 2>/dev/null; do
  if xdotool search --name MRS-ANTHROPE-QUIT >/dev/null 2>&1; then sleep 0.5; kill \$PID; break; fi
  sleep 0.5
done
wait \$PID 2>/dev/null
EOF
chmod +x "$SESSION"
xinit "$SESSION" -- :0 -nocursor -nolisten tcp >"$LOG" 2>&1
rm -f "$SESSION"
