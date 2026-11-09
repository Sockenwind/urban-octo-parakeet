# MRS. ANTHROPE – Stage 1: "Road to the Gig"

Eine 8‑bit Beat-'em-up-Animation im Stil klassischer Arcade-Sidescroller (Double Dragon / Fatal Fury),
basierend auf dem MRS.-ANTHROPE-Titelbild. Sieht aus wie eine Bildschirmaufnahme aus dem Spiel:
Titelbildschirm → "PRESS START" → Stage-Karte → Straßenkampf mit scrollendem Hintergrund →
Club "THE PIT" → Bosskampf gegen THE PROMOTER → K.O. → STAGE CLEAR → Konzert der Band.

**Fertiges Video:** [`out/mrs-anthrope-stage1.mp4`](out/mrs-anthrope-stage1.mp4) – 1920×1080, 16:9, 60 fps, ca. 93 s, mit Chiptune-Soundtrack.

## Browsergame (spielbar, auch auf dem Handy)

`index.html` ist das spielbare Spiel – einfach im Browser öffnen (funktioniert auch direkt per Doppelklick als Datei).

- **Ablauf:** Titel → Figur wählen (VOX oder AXE, der andere kämpft als CPU-Partner mit) → Stage 1 mit drei
  Gegnerwellen auf der Straße → Eingang des Clubs "THE PIT" → Bosskampf gegen THE PROMOTER → Konzert.
- **Handy:** virtueller Stick links, Buttons **HIT** (Schlag, 3× = Combo), **JUMP** (Sprung, in der Luft HIT = Flugkick)
  und **SP** (Spezialattacke, lädt sich wieder auf). Hochformat: Controller unter dem Bild, Querformat: großes Bild mit
  halbtransparenten Buttons darüber. START = Pause.
- **Tastatur:** Pfeiltasten/WASD, J oder Z/Y = Schlag, K/X/Leertaste = Sprung, L/C = Spezial, Enter = Start/Pause, M = Ton.
- **Gamepad** wird ebenfalls unterstützt.
- 3 Leben, Continue-Countdown, Pizza heilt, Zeitlimit pro Abschnitt.

`demo.html` spielt die automatisch ablaufende Video-Version im Browser ab.

## Was drin ist

- Echte Low-Res-Grafik: alles wird in **320×180 Pixel** mit fester Palette gezeichnet und dann
  ganzzahlig (×6, Nearest Neighbor) auf 1080p hochskaliert – keine weichen Kanten.
- Titelbildschirm = das Original-Artwork (auf 240×180 Pixel / 32 Farben reduziert), mit blinkenden
  Truss-Lampen und blinkendem "PRESS START".
- Spielfiguren nach dem Artwork: **1P VOX** (Sänger, rote Haare, Bart, Tanktop, Mikro) und
  **2P AXE** (grüne Mütze, Bart, weiße Gitarre). Im Finale zusätzlich Gitarrist mit grüner Cap
  und Drummer.
- Gegner: Punks ("POSER", "SNOT", "SID"), "A AND R MAN", "BOUNCER", Boss "THE PROMOTER".
- Typische Arcade-Elemente: HUD mit Score, Lebensbalken, Timer, Gegnername + Balken, Treffer-Funken,
  Hitstop, Screenshake, Knockdowns, blinkende K.O.s, "GO →"-Pfeil, Spezialattacken
  (Schrei-Schallwelle "AAARGH!", Gitarren-Smash), Zeitlupen-K.O., Time Bonus.
- Selbst synthetisierter 8‑bit-Sound (Pulse/Triangle/Noise): Titel-Riff, Punk-Stage-Theme,
  Boss-Galopp, Clear-Jingle, Konzert mit Publikum, plus SFX – exakt zu den Spielereignissen synchron.
- Alles deterministisch (fester Zufalls-Seed): jeder Render ergibt dasselbe Video.

## Ansehen / neu rendern

```bash
# Spiel im Browser:  index.html öffnen      Demo-Video live: demo.html öffnen

# Video neu rendern (benötigt Node.js und ffmpeg):
node render.js                         # -> out/mrs-anthrope-stage1.mp4 (1920x1080)
node render.js --scale 4 --out 720p.mp4  # 1280x720
node render.js --wav                   # nur den Soundtrack (out/soundtrack.wav)

# Titelbild neu einlesen, falls assets/title_source.png ersetzt wird (benötigt Pillow):
python3 tools/make_assets.py
```

## Aufbau

| Datei | Inhalt |
|---|---|
| `js/engine.js` | indizierter Framebuffer, Palette, Pixel-Primitive, Pixel-Font |
| `js/game.js` | Figuren (Puppet-Rig + Pixel-Köpfe), Posen, Angriffe, KI, Level, HUD, Regie-Skript |
| `js/audio.js` | Chiptune-Synthesizer für Musik und Soundeffekte |
| `js/assets.js` | generiert aus `assets/title_source.png` |
| `render.js` | rendert das MP4 über ffmpeg |
| `index.html` | spielbares Browsergame (Touch, Tastatur, Gamepad) |
| `demo.html` | Browser-Player für die Demo-Animation |
| `tools/` | Asset-Konverter und Entwickler-Hilfen (`snap.js` = Kontaktbogen, `timeline.js` = Ablauf der Demo, `playtest.js` = Bot spielt das Spiel durch) |
