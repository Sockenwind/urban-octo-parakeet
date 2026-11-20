"""Rechte Seitenleiste: Einstellungen für Bild, Ton und Export."""
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QRadioButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget)

from ..analysis import Analysis
from ..exporters import USER_FORMATS
from ..ffmpeg_tools import FFmpegInfo, MediaInfo
from ..settings import (DEINTERLACE, DENOISE_METHODS, HUM, LOUDNESS_TARGETS, QUALITY, RESOLUTIONS, STAB_BORDERS,
                        STAB_MODES, AudioSettings, ExportSettings, JobSettings, VideoSettings)
from .widgets import (Card, ChoiceRow, LevelRows, Segmented, SliderRow, ToggleRow, note_label, section_label)


def _signed(v: int) -> str:
    return f"{v:+d}".replace("-", "−") if v else "0"


class SettingsPanel(QWidget):
    changed = Signal()          # Bild- oder Ton-Einstellung der aktuellen Datei geändert
    export_changed = Signal()
    listen = Signal(str)        # "before" | "after" | "stop"

    def __init__(self, ff: Optional[FFmpegInfo], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ff = ff
        self._loading = False
        self._settings = JobSettings()
        self._export = ExportSettings()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.setStyleSheet("QTabWidget::tab-bar { left: 16px; }")
        self.video_tab = self._build_video()
        self.audio_tab = self._build_audio()
        self.export_tab = self._build_export()
        self.tabs.addTab(self.video_tab, "Bild")
        self.tabs.addTab(self.audio_tab, "Ton")
        self.tabs.addTab(self.export_tab, "Export")
        lay.addWidget(self.tabs)
        self.set_entry(False)

    # ------------------------------------------------------------------ Aufbau
    @staticmethod
    def _scroll(*widgets: QWidget) -> QScrollArea:
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(16, 14, 16, 18)
        lay.setSpacing(12)
        for w in widgets:
            lay.addWidget(w)
        lay.addStretch(1)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(content)
        return area

    def _build_video(self) -> QWidget:
        an = Card("Analyse")
        self.v_rows = an.add(LevelRows("Noch nicht analysiert. Klicke oben auf „Analysieren“: KlarBild misst "
                                       "Rauschen, Verwacklung und Zeilensprung und stellt alles passend ein."))

        self.dn_card = Card("Entrauschen", "Entfernt Bildrauschen – z. B. bei wenig Licht oder alten Aufnahmen.", toggle=True)
        self.dn_method = self.dn_card.add(Segmented(DENOISE_METHODS, {
            "fast": "Sehr schnell, für leichtes Rauschen (hqdn3d).",
            "balanced": "Beste Mischung aus Qualität und Tempo (FFT-Entrauschen über mehrere Bilder).",
            "max": "Noch etwas sauberer, aber etwa 2–3× langsamer.",
        }))
        self.dn_strength = self.dn_card.add(SliderRow("Stärke"))
        self.deblock = self.dn_card.add(ToggleRow("Blockartefakte glätten", "Für stark komprimierte Videos mit Kästchen-Muster."))

        self.st_card = Card("Stabilisieren", "Gleicht Verwackeln aus. Das Bild wird dafür leicht vergrößert.", toggle=True)
        self.st_strength = self.st_card.add(SliderRow("Stärke", hint="Mehr = ruhigeres Bild, aber etwas mehr Zoom."))
        self.st_mode = self.st_card.add(ChoiceRow("Modus", STAB_MODES))
        self.st_border = self.st_card.add(ChoiceRow("Bildränder", STAB_BORDERS))
        self.st_note = self.st_card.add(note_label())
        if self.ff and not self.ff.has_vidstab:
            self.st_note.setText("Dein ffmpeg enthält kein vid.stab – es wird ein einfacheres Verfahren genutzt. "
                                 "Besser: „brew install ffmpeg-full“.")
            self.st_note.setVisible(True)

        di = Card("Zeilensprung", "Typisch für VHS, DV und alte Camcorder – erkennbar an Kammstreifen.")
        self.di_mode = di.add(Segmented(DEINTERLACE))
        self.di_double = di.add(ToggleRow("Doppelte Bildrate", "Flüssigere Bewegung (z. B. 50 statt 25 Bilder/s)."))

        fin = Card("Feinschliff")
        self.sharpen = fin.add(SliderRow("Schärfen"))
        self.brightness = fin.add(SliderRow("Helligkeit", -100, 100, _signed))
        self.contrast = fin.add(SliderRow("Kontrast", -100, 100, _signed))
        self.saturation = fin.add(SliderRow("Farbsättigung", -100, 100, _signed))
        self.resolution = fin.add(ChoiceRow("Ausgabegröße", RESOLUTIONS))

        for sig in (self.dn_card.toggled, self.dn_method.changed, self.dn_strength.changed, self.deblock.changed,
                    self.st_card.toggled, self.st_strength.changed, self.st_mode.changed, self.st_border.changed,
                    self.di_mode.changed, self.di_double.changed, self.sharpen.changed, self.brightness.changed,
                    self.contrast.changed, self.saturation.changed, self.resolution.changed):
            sig.connect(self._emit)
        self.st_mode.changed.connect(lambda _v: self._sync_enabled())
        self.di_mode.changed.connect(lambda _v: self._sync_enabled())
        return self._scroll(an, self.dn_card, self.st_card, di, fin)

    def _build_audio(self) -> QWidget:
        an = Card("Analyse")
        self.a_rows = an.add(LevelRows("Noch nicht analysiert. „Analysieren“ misst Lautheit, Rauschen, "
                                       "Brummen und Übersteuerung."))

        listen = Card("Hörprobe", "10 Sekunden ab der aktuellen Position im Zeitstrahl.")
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        self.btn_before = QPushButton("▶  Vorher")
        self.btn_after = QPushButton("▶  Nachher")
        self.btn_after.setObjectName("accentOutline")
        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedWidth(42)
        for b in (self.btn_before, self.btn_after, self.btn_stop):
            b.setCursor(Qt.PointingHandCursor)
        rl.addWidget(self.btn_before, 1)
        rl.addWidget(self.btn_after, 1)
        rl.addWidget(self.btn_stop)
        listen.add(row)
        self.listen_status = listen.add(QLabel(""))
        self.listen_status.setObjectName("hint")
        self.listen_status.setVisible(False)
        self.btn_before.clicked.connect(lambda: self.listen.emit("before"))
        self.btn_after.clicked.connect(lambda: self.listen.emit("after"))
        self.btn_stop.clicked.connect(lambda: self.listen.emit("stop"))
        self.listen_card = listen

        self.a_master = Card("Tonverbesserung", "Alle Ton-Filter gemeinsam ein- oder ausschalten.", toggle=True)

        self.noise_card = Card("Störgeräusche entfernen")
        self.hum = self.noise_card.add(ChoiceRow("Netzbrummen", HUM))
        self.highpass = self.noise_card.add(ToggleRow("Rumpeln entfernen", "Wind, Trittschall und Griffgeräusche unter 75 Hz."))
        self.a_denoise = self.noise_card.add(SliderRow("Rauschminderung", hint="Rauschen, Zischen, Lüfter- und Bandrauschen."))
        self.declick = self.noise_card.add(ToggleRow("Knackser entfernen", "Für Schallplatten, Kabel- und Funkstörungen."))
        self.declip = self.noise_card.add(ToggleRow("Übersteuerung reparieren", "Rekonstruiert abgeschnittene Spitzen."))

        self.sound_card = Card("Klang")
        self.voice = self.sound_card.add(ToggleRow("Sprache verständlicher", "Hebt Stimmen hervor und mildert Zischlaute."))
        self.compress = self.sound_card.add(SliderRow("Dynamik angleichen", hint="Leise Stellen lauter, laute leiser."))

        self.loud_card = Card("Lautheit angleichen", "Bringt den Ton auf eine einheitliche, angenehme Lautstärke.", toggle=True)
        self.target = self.loud_card.add(ChoiceRow("Ziel", LOUDNESS_TARGETS))

        track = Card("Tonspur")
        self.mute = track.add(ToggleRow("Ton entfernen", "Das Video wird ganz ohne Ton gespeichert."))

        for sig in (self.a_master.toggled, self.hum.changed, self.highpass.changed, self.a_denoise.changed,
                    self.declick.changed, self.declip.changed, self.voice.changed, self.compress.changed,
                    self.loud_card.toggled, self.target.changed, self.mute.changed):
            sig.connect(self._emit)
        self.a_master.toggled.connect(lambda _v: self._sync_enabled())
        self.mute.changed.connect(lambda _v: self._sync_enabled())
        return self._scroll(an, listen, self.a_master, self.noise_card, self.sound_card, self.loud_card, track)

    def _build_export(self) -> QWidget:
        fmt = Card("Format")
        self.format_group = QButtonGroup(self)
        self.format_radios: dict = {}
        fmt.add(section_label("Video"))
        for f in USER_FORMATS:
            if f.kind == "audio" and "audio" not in [x.kind for x in USER_FORMATS[:USER_FORMATS.index(f)]]:
                fmt.add(section_label("Nur Ton"))
            fmt.add(self._format_option(f))

        q = Card("Qualität")
        self.quality = q.add(Segmented(QUALITY))
        self.quality_hint = q.add(QLabel())
        self.quality_hint.setObjectName("hint")
        self.quality_hint.setWordWrap(True)
        self.hardware = q.add(ToggleRow("Hardware-Beschleunigung", "Schneller über den Grafikchip (Apple VideoToolbox), "
                                                                   "dafür etwas größere Dateien."))
        if not (self.ff and self.ff.has_videotoolbox):
            self.hardware.setEnabled(False)
            self.hardware.set_hint("Auf diesem Rechner nicht verfügbar (nur macOS).")

        loc = Card("Speicherort")
        self.loc_same = QRadioButton("Neben der Originaldatei")
        self.loc_folder = QRadioButton("In einem Ordner")
        self.loc_same.setChecked(True)
        loc.add(self.loc_same)
        loc.add(self.loc_folder)
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(28, 0, 0, 0)
        self.folder_label = QLabel("Kein Ordner gewählt")
        self.folder_label.setObjectName("hint")
        self.folder_btn = QPushButton("Wählen …")
        self.folder_btn.setCursor(Qt.PointingHandCursor)
        rl.addWidget(self.folder_label, 1)
        rl.addWidget(self.folder_btn)
        loc.add(row)
        suffix_row = QWidget()
        sl = QHBoxLayout(suffix_row)
        sl.setContentsMargins(0, 4, 0, 0)
        sl.addWidget(QLabel("Namenszusatz"))
        self.suffix = QLineEdit("_klarbild")
        self.suffix.setMaximumWidth(150)
        sl.addStretch(1)
        sl.addWidget(self.suffix)
        loc.add(suffix_row)
        self._folder = ""

        self.format_group.buttonClicked.connect(lambda _b: self._emit_export())
        self.quality.changed.connect(lambda _v: self._emit_export())
        self.hardware.changed.connect(lambda _v: self._emit_export())
        self.loc_same.toggled.connect(lambda _v: self._emit_export())
        self.folder_btn.clicked.connect(self._choose_folder)
        self.suffix.textChanged.connect(lambda _t: self._emit_export())
        return self._scroll(fmt, q, loc)

    def _format_option(self, f) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        rb = QRadioButton(f.label)
        rb.setCursor(Qt.PointingHandCursor)
        self.format_group.addButton(rb)
        self.format_radios[f.key] = rb
        desc = QLabel(f.description)
        desc.setObjectName("hint")
        desc.setWordWrap(True)
        desc.setContentsMargins(28, 0, 0, 0)
        lay.addWidget(rb)
        lay.addWidget(desc)
        return w

    # ------------------------------------------------------------------ Zustand
    def _emit(self, *_args) -> None:
        if not self._loading:
            self.changed.emit()

    def _emit_export(self) -> None:
        self._update_quality_hint()
        self.folder_btn.setEnabled(self.loc_folder.isChecked())
        if not self._loading:
            self.export_changed.emit()

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Zielordner wählen", self._folder or os.path.expanduser("~"))
        if folder:
            self._folder = folder
            self._show_folder()
            self.loc_folder.setChecked(True)
            self._emit_export()

    def _show_folder(self) -> None:
        text = self._folder or "Kein Ordner gewählt"
        fm = self.folder_label.fontMetrics()
        self.folder_label.setText(fm.elidedText(text, Qt.ElideMiddle, 220))
        self.folder_label.setToolTip(self._folder)

    def _update_quality_hint(self) -> None:
        key = self.export_settings().format
        if key == "mkv_ffv1":
            text = "FFV1 ist immer verlustfrei – die Stufe hat hier keinen Einfluss."
        elif key == "mov_prores":
            text = "Hoch = ProRes 422 HQ · Mittel = 422 · Klein = 422 LT."
        elif key in ("audio_wav", "audio_flac"):
            text = "Verlustfrei – die Stufe hat hier keinen Einfluss."
        else:
            text = "Hoch: kaum sichtbare Verluste · Klein: deutlich kleinere Datei."
        self.quality_hint.setText(text)

    def _sync_enabled(self) -> None:
        tripod = self.st_mode.value() == "tripod"
        self.st_strength.setEnabled(not tripod)
        self.di_double.setEnabled(self.di_mode.value() != "off")
        muted = self.mute.value()
        master = self.a_master.is_checked() and not muted
        self.a_master.setEnabled(not muted)
        for card in (self.noise_card, self.sound_card, self.loud_card, self.listen_card):
            card.setEnabled(master if card is not self.listen_card else not muted)

    def set_entry(self, has_entry: bool, has_video: bool = True, has_audio: bool = True) -> None:
        self.video_tab.setEnabled(has_entry and has_video)
        self.audio_tab.setEnabled(has_entry and has_audio)

    # ------------------------------------------------------------------ Laden / Lesen
    def load(self, settings: JobSettings, media: Optional[MediaInfo], analysis: Optional[Analysis]) -> None:
        self._loading = True
        self._settings = settings.copy()
        v, a = settings.video, settings.audio
        self.dn_card.set_checked(v.denoise_enabled)
        self.dn_method.set_silent(v.denoise_method)
        self.dn_strength.set_silent(v.denoise_strength)
        self.deblock.set_silent(v.deblock)
        self.st_card.set_checked(v.stabilize_enabled)
        self.st_strength.set_silent(v.stabilize_strength)
        self.st_mode.set_silent(v.stabilize_mode)
        self.st_border.set_silent(v.stabilize_border)
        self.di_mode.set_silent(v.deinterlace)
        self.di_double.set_silent(v.deinterlace_double_rate)
        self.sharpen.set_silent(v.sharpen)
        self.brightness.set_silent(v.brightness)
        self.contrast.set_silent(v.contrast)
        self.saturation.set_silent(v.saturation)
        self.resolution.set_silent(v.resolution)
        self.a_master.set_checked(a.enabled)
        self.hum.set_silent(a.hum)
        self.highpass.set_silent(a.highpass)
        self.a_denoise.set_silent(a.denoise)
        self.declick.set_silent(a.declick)
        self.declip.set_silent(a.declip)
        self.voice.set_silent(a.voice)
        self.compress.set_silent(a.compress)
        self.loud_card.set_checked(a.normalize)
        self.target.set_silent(a.target)
        self.mute.set_silent(a.mute)
        self.v_rows.set_rows(analysis.video_rows() if analysis else [])
        self.a_rows.set_rows(analysis.audio_rows() if analysis else [])
        self._sync_enabled()
        self.set_entry(media is not None, bool(media and media.has_video), bool(media and media.has_audio))
        self._loading = False

    def settings(self) -> JobSettings:
        base = self._settings.copy()
        v: VideoSettings = base.video
        v.denoise_enabled = self.dn_card.is_checked()
        v.denoise_method = self.dn_method.value()
        v.denoise_strength = self.dn_strength.value()
        v.deblock = self.deblock.value()
        v.stabilize_enabled = self.st_card.is_checked()
        v.stabilize_strength = self.st_strength.value()
        v.stabilize_mode = self.st_mode.value()
        v.stabilize_border = self.st_border.value()
        v.deinterlace = self.di_mode.value()
        v.deinterlace_double_rate = self.di_double.value()
        v.sharpen = self.sharpen.value()
        v.brightness = self.brightness.value()
        v.contrast = self.contrast.value()
        v.saturation = self.saturation.value()
        v.resolution = self.resolution.value()
        a: AudioSettings = base.audio
        a.enabled = self.a_master.is_checked()
        a.hum = self.hum.value()
        a.highpass = self.highpass.value()
        a.denoise = self.a_denoise.value()
        a.declick = self.declick.value()
        a.declip = self.declip.value()
        a.voice = self.voice.value()
        a.compress = self.compress.value()
        a.normalize = self.loud_card.is_checked()
        a.target = self.target.value()
        a.mute = self.mute.value()
        self._settings = base.copy()
        return base

    def load_export(self, ex: ExportSettings) -> None:
        self._loading = True
        rb = self.format_radios.get(ex.format) or self.format_radios["mp4_h264"]
        rb.setChecked(True)
        self.quality.set_silent(ex.quality)
        self.hardware.set_silent(ex.hardware and self.hardware.isEnabled())
        self._folder = ex.folder
        (self.loc_folder if ex.folder else self.loc_same).setChecked(True)
        self._show_folder()
        self.suffix.setText(ex.suffix or "_klarbild")
        self._update_quality_hint()
        self.folder_btn.setEnabled(self.loc_folder.isChecked())
        self._loading = False

    def export_settings(self) -> ExportSettings:
        key = next((k for k, rb in self.format_radios.items() if rb.isChecked()), "mp4_h264")
        return ExportSettings(
            format=key,
            quality=self.quality.value(),
            hardware=self.hardware.value() and self.hardware.isEnabled(),
            folder=self._folder if self.loc_folder.isChecked() else "",
            suffix=self.suffix.text().strip() or "_klarbild",
        )

    def set_listen_state(self, text: str, busy: bool = False) -> None:
        self.listen_status.setText(text)
        self.listen_status.setVisible(bool(text))
        self.btn_before.setEnabled(not busy)
        self.btn_after.setEnabled(not busy)
