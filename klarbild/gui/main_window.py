"""Hauptfenster von KlarBild."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, replace
from typing import Optional

from PySide6.QtCore import QSettings, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QImage, QKeySequence, QPixmap
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QProgressBar, QPushButton, QSlider,
                               QSplitter, QVBoxLayout, QWidget)

from .. import APP_NAME, __version__
from ..analysis import Analysis, analyze, apply_suggestions
from ..exporters import FORMATS, format_for, output_path
from ..ffmpeg_tools import FFmpegError, FFmpegInfo, MediaInfo, detect_ffmpeg, format_time, probe
from ..pipeline import Job, is_interlaced
from ..preview import audio_preview, frame_ppm, preview_clip, thumbnail_ppm
from ..settings import ExportSettings, JobSettings
from ..video_filters import build_video_plan
from . import theme
from .compare_view import CompareView
from .settings_panel import SettingsPanel
from .widgets import ElideLabel, FileItem, section_label
from .workers import CANCELLED, ExportRunner, Task

try:  # Hörprobe direkt im Programm abspielen (sonst mit dem Standardprogramm)
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except Exception:  # pragma: no cover
    QMediaPlayer = None  # type: ignore[assignment]

MEDIA_FILTER = ("Videos und Ton (*.mp4 *.mov *.m4v *.mkv *.avi *.mts *.m2ts *.mpg *.mpeg *.vob *.dv *.wmv "
                "*.flv *.webm *.3gp *.mxf *.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus *.aif *.aiff);;Alle Dateien (*)")
SQUARE_PIXELS = "scale=trunc(iw*sar/2)*2:ih,setsar=1"
REVEAL_LABEL = "Im Finder zeigen" if sys.platform == "darwin" else "Ordner öffnen"


@dataclass
class FileEntry:
    path: str
    media: MediaInfo
    settings: JobSettings = field(default_factory=JobSettings)
    analysis: Optional[Analysis] = None
    position: float = 0.0
    widget: Optional[FileItem] = None
    item: Optional[QListWidgetItem] = None
    output: str = ""


def _image(data: bytes) -> Optional[QImage]:
    img = QImage.fromData(data, "PPM")
    return None if img.isNull() else img


class MainWindow(QMainWindow):
    def __init__(self, ff: Optional[FFmpegInfo], ff_error: str = ""):
        super().__init__()
        self.ff = ff
        self.ff_error = ff_error
        self.store = QSettings("KlarBild", "KlarBild")
        self.entries: list = []
        self.current: Optional[FileEntry] = None
        self.runner: Optional[ExportRunner] = None
        self.busy_task: Optional[Task] = None
        self._gen_before = self._gen_after = 0
        self._tmp = tempfile.mkdtemp(prefix="klarbild_vorschau_")
        self._listen_cache: dict = {}
        self._last_output = ""

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(theme.make_icon())
        self.setMinimumSize(1100, 700)
        self.setAcceptDrops(True)

        root = QWidget()
        root.setObjectName("root")
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self._build_header())
        split = self.split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(1)
        split.setChildrenCollapsible(False)
        split.addWidget(self._build_sidebar())
        split.addWidget(self._build_center())
        split.addWidget(self._build_right())
        split.setStretchFactor(1, 1)
        split.setSizes([300, 760, 410])
        v.addWidget(split, 1)
        v.addWidget(self._build_footer())
        self.setCentralWidget(root)
        self._build_menu()

        self.after_timer = QTimer(self, singleShot=True, interval=450)
        self.after_timer.timeout.connect(lambda: self._render(before=False))
        self.pos_timer = QTimer(self, singleShot=True, interval=220)
        self.pos_timer.timeout.connect(self._render)

        self.player = None
        if QMediaPlayer is not None:
            self.player = QMediaPlayer(self)
            self.audio_out = QAudioOutput(self)
            self.player.setAudioOutput(self.audio_out)
            self.player.playbackStateChanged.connect(self._on_playback_state)

        try:
            self.panel.load_export(ExportSettings.from_dict(json.loads(self.store.value("export", "{}"))))
        except (ValueError, TypeError):
            self.panel.load_export(ExportSettings())
        geo = self.store.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(1480, 920)
        self._update_actions()
        if not ff:
            QTimer.singleShot(300, self._warn_missing_ffmpeg)

    # ================================================================== Aufbau
    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setObjectName("header")
        w.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(theme.make_icon().pixmap(QSize(34, 34)))
        lay.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel(APP_NAME)
        t.setObjectName("appTitle")
        s = QLabel("Video entrauschen · stabilisieren · Ton verbessern")
        s.setObjectName("hint")
        titles.addWidget(t)
        titles.addWidget(s)
        lay.addLayout(titles)
        lay.addStretch(1)
        self.ff_chip = QLabel()
        self.ff_chip.setObjectName("chip")
        self.ff_chip.setCursor(Qt.PointingHandCursor)
        self.ff_chip.mousePressEvent = lambda _e: self._choose_ffmpeg()
        self._update_ff_chip()
        lay.addWidget(self.ff_chip)
        self.btn_add = QPushButton("＋  Dateien hinzufügen")
        self.btn_add.clicked.connect(self._add_dialog)
        self.btn_analyze = QPushButton("Analysieren")
        self.btn_analyze.setObjectName("accentOutline")
        self.btn_analyze.setToolTip("Misst Rauschen, Verwacklung und Tonprobleme und stellt alles passend ein.")
        self.btn_analyze.clicked.connect(self._analyze_current)
        for b in (self.btn_add, self.btn_analyze):
            b.setCursor(Qt.PointingHandCursor)
            lay.addWidget(b)
        return w

    def _build_sidebar(self) -> QWidget:
        w = QWidget()
        w.setObjectName("sidebar")
        w.setAttribute(Qt.WA_StyledBackground, True)
        w.setMinimumWidth(240)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 14, 12, 12)
        lay.setSpacing(8)
        head = QHBoxLayout()
        head.addWidget(section_label("Dateien"))
        head.addStretch(1)
        self.count_label = QLabel("0")
        self.count_label.setObjectName("hint")
        head.addWidget(self.count_label)
        lay.addLayout(head)
        self.file_list = QListWidget()
        self.file_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.file_list.currentRowChanged.connect(self._on_select)
        lay.addWidget(self.file_list, 1)
        self.empty_hint = QLabel("Noch keine Dateien.\nZiehe Videos oder Tonaufnahmen\nin das Fenster.")
        self.empty_hint.setObjectName("hint")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.empty_hint)
        row = QHBoxLayout()
        self.btn_add2 = QPushButton("＋  Hinzufügen")
        self.btn_add2.clicked.connect(self._add_dialog)
        self.btn_remove = QPushButton("Entfernen")
        self.btn_remove.clicked.connect(self._remove_current)
        for b in (self.btn_add2, self.btn_remove):
            b.setCursor(Qt.PointingHandCursor)
            row.addWidget(b)
        lay.addLayout(row)
        return w

    def _build_center(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 12)
        lay.setSpacing(10)
        self.compare = CompareView()
        self.compare.files_dropped.connect(self.add_files)
        lay.addWidget(self.compare, 1)
        tl = QHBoxLayout()
        tl.setSpacing(10)
        self.time_label = QLabel("0:00")
        self.time_label.setObjectName("value")
        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setObjectName("timeline")
        self.timeline.setRange(0, 1000)
        self.timeline.setCursor(Qt.PointingHandCursor)
        self.timeline.valueChanged.connect(self._on_timeline)
        self.dur_label = QLabel("0:00")
        self.dur_label.setObjectName("value")
        tl.addWidget(self.time_label)
        tl.addWidget(self.timeline, 1)
        tl.addWidget(self.dur_label)
        lay.addLayout(tl)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_clip = QPushButton("▶  Vorschau-Clip (6 s)")
        self.btn_clip.setToolTip("Berechnet 6 Sekunden mit allen Einstellungen – inklusive Stabilisierung – "
                                 "als Vorher/Nachher-Video und spielt sie ab.")
        self.btn_clip.clicked.connect(self._preview_clip)
        self.btn_frame = QPushButton("Einzelbild speichern")
        self.btn_frame.clicked.connect(self._save_frame)
        self.btn_zoom = QPushButton("Einpassen")
        self.btn_zoom.clicked.connect(self.compare.reset_zoom)
        for b in (self.btn_clip, self.btn_frame, self.btn_zoom):
            b.setCursor(Qt.PointingHandCursor)
            row.addWidget(b)
        hint = ElideLabel("Maus bewegen: vergleichen · Mausrad: zoomen · Doppelklick: 100 %")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(hint, 1)
        lay.addLayout(row)
        return w

    def _build_right(self) -> QWidget:
        w = QWidget()
        w.setObjectName("rightPanel")
        w.setAttribute(Qt.WA_StyledBackground, True)
        w.setMinimumWidth(370)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 6, 0, 0)
        lay.setSpacing(0)
        self.panel = SettingsPanel(self.ff)
        self.panel.changed.connect(self._on_settings_changed)
        self.panel.export_changed.connect(self._save_export)
        self.panel.listen.connect(self._listen)
        lay.addWidget(self.panel, 1)
        actions = QWidget()
        al = QVBoxLayout(actions)
        al.setContentsMargins(16, 10, 16, 14)
        al.setSpacing(8)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_export = QPushButton("Exportieren")
        self.btn_export.setObjectName("primary")
        self.btn_export.clicked.connect(lambda: self._export([self.current] if self.current else []))
        self.btn_export_all = QPushButton("Alle exportieren")
        self.btn_export_all.clicked.connect(lambda: self._export(list(self.entries)))
        for b in (self.btn_export, self.btn_export_all):
            b.setCursor(Qt.PointingHandCursor)
        row.addWidget(self.btn_export, 3)
        row.addWidget(self.btn_export_all, 2)
        al.addLayout(row)
        self.btn_apply_all = QPushButton("Diese Einstellungen auf alle Dateien übertragen")
        self.btn_apply_all.setObjectName("ghost")
        self.btn_apply_all.setCursor(Qt.PointingHandCursor)
        self.btn_apply_all.clicked.connect(self._apply_to_all)
        al.addWidget(self.btn_apply_all)
        lay.addWidget(actions)
        return w

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setObjectName("footer")
        w.setAttribute(Qt.WA_StyledBackground, True)
        w.setFixedHeight(46)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(18, 8, 18, 8)
        lay.setSpacing(12)
        self.status = QLabel("Bereit.")
        self.status.setObjectName("muted")
        lay.addWidget(self.status, 1)
        self.btn_reveal = QPushButton(REVEAL_LABEL)
        self.btn_reveal.setObjectName("ghost")
        self.btn_reveal.setVisible(False)
        self.btn_reveal.clicked.connect(self._reveal_output)
        lay.addWidget(self.btn_reveal)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setFixedWidth(260)
        self.progress.setVisible(False)
        lay.addWidget(self.progress)
        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_cancel.setObjectName("danger")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel)
        lay.addWidget(self.btn_cancel)
        return w

    def _build_menu(self) -> None:
        m = self.menuBar().addMenu("Datei")
        a = QAction("Dateien hinzufügen …", self, shortcut=QKeySequence.Open)
        a.triggered.connect(self._add_dialog)
        m.addAction(a)
        a = QAction("Exportieren", self, shortcut=QKeySequence("Ctrl+E"))
        a.triggered.connect(lambda: self._export([self.current] if self.current else []))
        m.addAction(a)
        m.addSeparator()
        a = QAction("Beenden", self, shortcut=QKeySequence.Quit)
        a.triggered.connect(self.close)
        m.addAction(a)
        m = self.menuBar().addMenu("Einstellungen")
        a = QAction("ffmpeg auswählen …", self)
        a.triggered.connect(self._choose_ffmpeg)
        m.addAction(a)
        m = self.menuBar().addMenu("Hilfe")
        a = QAction(f"Über {APP_NAME}", self)
        a.triggered.connect(self._about)
        m.addAction(a)

    # ================================================================== Status
    def _update_ff_chip(self) -> None:
        if not self.ff:
            self.ff_chip.setText("ffmpeg fehlt – hier klicken")
            self.ff_chip.setStyleSheet(f"color: {theme.BAD};")
            self.ff_chip.setToolTip(self.ff_error)
            return
        stab = "vid.stab ✓" if self.ff.has_vidstab else "vid.stab ✗"
        self.ff_chip.setText(f"ffmpeg {self.ff.version.split('-')[0]} · {stab}")
        self.ff_chip.setStyleSheet("")
        self.ff_chip.setToolTip(f"{self.ff.ffmpeg}\nKlicken, um ein anderes ffmpeg zu wählen.")

    def _update_actions(self) -> None:
        has = self.current is not None
        busy = self.runner is not None
        ok = self.ff is not None
        self.btn_add.setEnabled(ok)
        self.btn_add2.setEnabled(ok)
        self.btn_analyze.setEnabled(ok and has and self.busy_task is None)
        self.btn_export.setEnabled(ok and has and not busy)
        self.btn_export_all.setEnabled(ok and len(self.entries) > 0 and not busy)
        self.btn_export_all.setText(f"Alle exportieren ({len(self.entries)})" if len(self.entries) > 1 else "Alle exportieren")
        self.btn_apply_all.setEnabled(has and len(self.entries) > 1)
        self.btn_remove.setEnabled(has and not busy)
        video = has and self.current.media.has_video
        self.btn_clip.setEnabled(ok and video and self.busy_task is None)
        self.btn_frame.setEnabled(video and self.compare.after is not None)
        self.btn_zoom.setEnabled(video)
        self.timeline.setEnabled(has)
        self.count_label.setText(str(len(self.entries)))
        self.empty_hint.setVisible(not self.entries)

    def _set_status(self, text: str, level: str = "muted") -> None:
        self.status.setText(text)
        color = theme.LEVEL_COLORS.get(level, theme.MUTED)
        self.status.setStyleSheet(f"color: {color};")

    def _show_progress(self, value: Optional[float], text: str = "", cancellable: bool = True) -> None:
        if value is None:
            self.progress.setVisible(False)
            self.btn_cancel.setVisible(False)
            return
        self.progress.setVisible(True)
        self.progress.setValue(int(value * 1000))
        self.btn_cancel.setVisible(cancellable)
        if text:
            self._set_status(text)

    # ================================================================== Dateien
    def _add_dialog(self) -> None:
        start = self.store.value("last_dir", os.path.expanduser("~"))
        paths, _ = QFileDialog.getOpenFileNames(self, "Videos oder Tonaufnahmen wählen", start, MEDIA_FILTER)
        if paths:
            self.store.setValue("last_dir", os.path.dirname(paths[0]))
            self.add_files(paths)

    def add_files(self, paths: list) -> None:
        if not self.ff:
            self._warn_missing_ffmpeg()
            return
        known = {e.path for e in self.entries}
        failed = []
        added: list = []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for path in paths:
                if os.path.isdir(path):
                    continue
                path = os.path.abspath(path)
                if path in known:
                    continue
                try:
                    media = probe(self.ff, path)
                except (FFmpegError, ValueError, OSError):
                    failed.append(os.path.basename(path))
                    continue
                entry = FileEntry(path, media)
                entry.position = media.duration * 0.3 if media.duration > 4 else 0.0
                self._add_entry(entry)
                known.add(path)
                added.append(entry)
        finally:
            QApplication.restoreOverrideCursor()
        if added:
            self.file_list.setCurrentRow(self.entries.index(added[0]))
            self._set_status(f"{len(added)} Datei(en) hinzugefügt. Tipp: „Analysieren“ stellt alles automatisch ein.")
        if failed:
            QMessageBox.warning(self, APP_NAME, "Diese Dateien konnten nicht gelesen werden:\n\n" + "\n".join(failed))
        self._update_actions()

    def _add_entry(self, entry: FileEntry) -> None:
        widget = FileItem(os.path.basename(entry.path), entry.media.summary())
        item = QListWidgetItem()
        item.setSizeHint(QSize(200, 78))
        self.file_list.addItem(item)
        self.file_list.setItemWidget(item, widget)
        entry.widget, entry.item = widget, item
        self.entries.append(entry)
        if entry.media.has_video:
            task = Task(thumbnail_ppm, self.ff, entry.media)
            task.signals.done.connect(lambda data, w=widget: self._set_thumb(w, data))
            task.start()
        else:
            widget.set_audio_icon()
            widget.set_status("Nur Ton", "muted")

    @staticmethod
    def _set_thumb(widget: FileItem, data: bytes) -> None:
        img = _image(data)
        if img:
            widget.set_thumbnail(QPixmap.fromImage(img))

    def _remove_current(self) -> None:
        row = self.file_list.currentRow()
        if row < 0 or self.runner:
            return
        self.entries.pop(row)
        self.file_list.takeItem(row)
        if not self.entries:
            self.current = None
            self.compare.clear()
            self.panel.load(JobSettings(), None, None)
        self._update_actions()

    def _on_select(self, row: int) -> None:
        self._stop_audio()
        if row < 0 or row >= len(self.entries):
            self.current = None
            self._update_actions()
            return
        e = self.entries[row]
        self.current = e
        self.panel.load(e.settings, e.media, e.analysis)
        self.timeline.blockSignals(True)
        self.timeline.setValue(int(1000 * e.position / e.media.duration) if e.media.duration else 0)
        self.timeline.blockSignals(False)
        self.time_label.setText(format_time(e.position))
        self.dur_label.setText(format_time(e.media.duration))
        if e.media.has_video:
            self.compare.clear()
            self._render()
        else:
            self.compare.clear("Nur Ton – keine Bildvorschau.\nIm Tab „Ton“ gibt es eine Hörprobe.")
            self.panel.tabs.setCurrentIndex(1)
        self._update_actions()

    # ================================================================== Vorschau
    def _on_timeline(self, value: int) -> None:
        if not self.current:
            return
        self.current.position = self.current.media.duration * value / 1000
        self.time_label.setText(format_time(self.current.position))
        self.pos_timer.start()

    def _on_settings_changed(self) -> None:
        if not self.current:
            return
        self.current.settings = self.panel.settings()
        self._listen_cache.clear()
        self.after_timer.start()

    def _render(self, before: bool = True) -> None:
        e = self.current
        if not e or not e.media.has_video or not self.ff:
            return
        t = e.position
        if before:
            self._gen_before += 1
            gen = self._gen_before
            task = Task(frame_ppm, self.ff, e.media, t, SQUARE_PIXELS)
            task.signals.done.connect(lambda data, g=gen, ent=e: self._before_ready(g, ent, data))
            task.start()
        self._gen_after += 1
        gen = self._gen_after
        job = Job(e.path, "", e.settings, ExportSettings(), e.media, e.analysis)
        plan = build_video_plan(self.ff, e.settings.video, e.media, is_interlaced(job))
        vf = plan.preview + "," + SQUARE_PIXELS if plan.preview != "null" else SQUARE_PIXELS
        self.compare.set_busy("Vorschau wird berechnet …")
        self.compare.after_hint = ("Stabilisierung siehst du im Vorschau-Clip" if e.settings.video.stabilize_enabled else "")
        task = Task(frame_ppm, self.ff, e.media, t, vf)
        task.signals.done.connect(lambda data, g=gen, ent=e: self._after_ready(g, ent, data))
        task.signals.failed.connect(lambda msg, _log, g=gen: self._after_failed(g, msg))
        task.start()

    def _before_ready(self, gen: int, entry: FileEntry, data: bytes) -> None:
        if gen == self._gen_before and entry is self.current:
            self.compare.set_before(_image(data))

    def _after_ready(self, gen: int, entry: FileEntry, data: bytes) -> None:
        if gen == self._gen_after and entry is self.current:
            self.compare.set_after(_image(data))
            self.compare.set_busy("")
            self._update_actions()

    def _after_failed(self, gen: int, msg: str) -> None:
        if gen == self._gen_after:
            self.compare.set_busy("")
            self._set_status(f"Vorschau fehlgeschlagen: {msg.splitlines()[-1] if msg else ''}", "bad")

    def _save_frame(self) -> None:
        img = self.compare.after
        if not img or not self.current:
            return
        stem = os.path.splitext(os.path.basename(self.current.path))[0]
        t = int(self.current.position)
        default = os.path.join(os.path.dirname(self.current.path), f"{stem}_bild_{t // 60}m{t % 60:02d}s.png")
        path, _ = QFileDialog.getSaveFileName(self, "Einzelbild speichern", default, "PNG-Bild (*.png);;JPEG-Bild (*.jpg)")
        if path:
            if img.save(path, quality=95):
                self._last_output = path
                self.btn_reveal.setVisible(True)
                self._set_status(f"Einzelbild gespeichert: {os.path.basename(path)}", "ok")
            else:
                self._set_status("Einzelbild konnte nicht gespeichert werden.", "bad")

    def _preview_clip(self) -> None:
        e = self.current
        if not e or not self.ff or self.busy_task:
            return
        task = Task(preview_clip, self.ff, e.settings.copy(), e.media, e.analysis, e.position, self._tmp,
                    progress=True, cancellable=True)
        task.signals.progress.connect(lambda f, t: self._show_progress(f, f"Vorschau-Clip: {t} …"))
        task.signals.done.connect(self._clip_ready)
        task.signals.failed.connect(lambda m, log: self._task_failed("Vorschau-Clip", m, log))
        self._start_busy(task)

    def _clip_ready(self, path: str) -> None:
        self._end_busy()
        self._set_status("Vorschau-Clip fertig – wird abgespielt.", "ok")
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    # ================================================================== Analyse
    def _analyze_current(self) -> None:
        e = self.current
        if not e or not self.ff or self.busy_task:
            return
        task = Task(analyze, self.ff, e.media, progress=True, cancellable=True)
        task.signals.progress.connect(lambda f, t: self._show_progress(f, f"Analyse: {t}"))
        task.signals.done.connect(lambda an, ent=e: self._analysis_done(ent, an))
        task.signals.failed.connect(lambda m, log: self._task_failed("Analyse", m, log))
        e.widget.set_status("Wird analysiert …", "warn")
        self._start_busy(task)

    def _analysis_done(self, entry: FileEntry, an: Analysis) -> None:
        self._end_busy()
        entry.analysis = an
        msgs = apply_suggestions(an, entry.settings)
        entry.widget.set_status("Analysiert ✓", "ok")
        self._listen_cache.clear()
        if entry is self.current:
            self.panel.load(entry.settings, entry.media, an)
            self._render(before=False)
        self._set_status("Analyse fertig – " + (" · ".join(msgs) if msgs else "keine Änderungen nötig."), "ok")
        self.status.setToolTip("\n".join(msgs))

    def _start_busy(self, task: Task) -> None:
        self.busy_task = task
        self.btn_reveal.setVisible(False)
        task.start()
        self._show_progress(0.0)
        self._update_actions()

    def _end_busy(self) -> None:
        self.busy_task = None
        self._show_progress(None)
        self._update_actions()

    def _task_failed(self, what: str, msg: str, log: str) -> None:
        self._end_busy()
        if self.current and self.current.widget and what == "Analyse":
            self.current.widget.set_status("Bereit", "muted")
        if msg == CANCELLED:
            self._set_status(f"{what} abgebrochen.")
            return
        self._set_status(f"{what} fehlgeschlagen.", "bad")
        self._error_box(f"{what} fehlgeschlagen", msg, log)

    # ================================================================== Hörprobe
    def _listen(self, which: str) -> None:
        if which == "stop":
            self._stop_audio()
            return
        e = self.current
        if not e or not self.ff or not e.media.has_audio:
            return
        key = (e.path, round(e.position, 1))
        if key in self._listen_cache:
            self._play(self._listen_cache[key][0 if which == "before" else 1], which)
            return
        self.panel.set_listen_state("Hörprobe wird berechnet …", busy=True)
        task = Task(audio_preview, self.ff, e.settings.copy(), e.media, e.analysis, e.position, self._tmp_listen())
        task.signals.done.connect(lambda paths, k=key, w=which: self._listen_ready(k, paths, w))
        task.signals.failed.connect(lambda m, log: (self.panel.set_listen_state("Hörprobe fehlgeschlagen."),
                                                    self._error_box("Hörprobe fehlgeschlagen", m, log)))
        task.start()

    def _tmp_listen(self) -> str:
        folder = tempfile.mkdtemp(prefix="hoer_", dir=self._tmp)
        return folder

    def _listen_ready(self, key, paths: tuple, which: str) -> None:
        self._listen_cache[key] = paths
        self._play(paths[0 if which == "before" else 1], which)

    def _play(self, path: str, which: str) -> None:
        label = "Vorher" if which == "before" else "Nachher"
        if self.player is None:
            self.panel.set_listen_state(f"{label} wird im Standardprogramm abgespielt.")
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.panel.set_listen_state(f"Spielt: {label}")

    def _stop_audio(self) -> None:
        if self.player is not None:
            self.player.stop()
        self.panel.set_listen_state("")

    def _on_playback_state(self, state) -> None:
        if self.player is not None and state == QMediaPlayer.PlaybackState.StoppedState:
            self.panel.set_listen_state("")

    # ================================================================== Export
    def _save_export(self) -> None:
        self.store.setValue("export", json.dumps(self.panel.export_settings().to_dict()))

    def _export(self, entries: list) -> None:
        entries = [e for e in entries if e]
        if not entries or not self.ff or self.runner:
            return
        ex = self.panel.export_settings()
        self._save_export()
        if ex.folder and not os.path.isdir(ex.folder):
            QMessageBox.warning(self, APP_NAME, "Der gewählte Zielordner existiert nicht mehr.")
            return

        def factory(e: FileEntry):
            def make() -> Job:
                key = format_for(ex.format, e.media.has_video)
                out = output_path(e.path, FORMATS[key], ex.folder, ex.suffix)
                e.output = out
                return Job(e.path, out, e.settings.copy(), replace(ex, format=key), e.media, e.analysis)
            return make

        self._export_entries = entries
        self._export_errors: list = []
        runner = ExportRunner(self.ff, [factory(e) for e in entries])
        s = runner.signals
        s.job_started.connect(self._job_started)
        s.job_progress.connect(self._job_progress)
        s.job_done.connect(self._job_done)
        s.job_failed.connect(self._job_failed)
        s.finished.connect(self._export_finished)
        self.runner = runner
        self.btn_reveal.setVisible(False)
        for e in entries:
            e.widget.set_status("Wartet …", "muted")
        runner.start()
        self._show_progress(0.0, "Export startet …")
        self._update_actions()

    def _job_started(self, i: int) -> None:
        e = self._export_entries[i]
        e.widget.set_status("Wird exportiert …", "warn")
        e.widget.set_progress(0.0)

    def _job_progress(self, i: int, frac: float, text: str) -> None:
        e = self._export_entries[i]
        n = len(self._export_entries)
        e.widget.set_progress(frac)
        overall = (i + frac) / n
        prefix = f"Exportiere {i + 1}/{n} · " if n > 1 else "Exportiere · "
        self._show_progress(overall, f"{prefix}{os.path.basename(e.path)} · {text} {int(frac * 100)} %")

    def _job_done(self, i: int, out: str) -> None:
        e = self._export_entries[i]
        e.widget.set_progress(None)
        e.widget.set_status("Fertig ✓", "ok")
        e.widget.setToolTip(out)
        self._last_output = out

    def _job_failed(self, i: int, msg: str, log: str) -> None:
        e = self._export_entries[i]
        e.widget.set_progress(None)
        e.widget.set_status("Fehler – Details im Hinweis", "bad")
        e.widget.setToolTip(msg)
        self._export_errors.append((os.path.basename(e.path), msg, log))

    def _export_finished(self, ok: int, failed: int, cancelled: bool) -> None:
        self.runner = None
        self._show_progress(None)
        for e in self._export_entries:
            e.widget.set_progress(None)
            if cancelled and e.widget.status.text() in ("Wartet …", "Wird exportiert …"):
                e.widget.set_status("Abgebrochen", "muted")
        if cancelled:
            self._set_status(f"Export abgebrochen. {ok} Datei(en) fertig.", "warn")
        elif failed:
            self._set_status(f"{ok} Datei(en) exportiert, {failed} fehlgeschlagen.", "bad")
        else:
            self._set_status(f"Fertig: {ok} Datei(en) exportiert.", "ok")
        self.btn_reveal.setVisible(bool(self._last_output) and ok > 0)
        self._update_actions()
        if self._export_errors:
            name, msg, log = self._export_errors[0]
            more = f"\n\n(+{len(self._export_errors) - 1} weitere)" if len(self._export_errors) > 1 else ""
            self._error_box("Export fehlgeschlagen", f"{name}:\n{msg}{more}", log)
        QApplication.alert(self)

    def _reveal_output(self) -> None:
        path = self._last_output
        if not path:
            return
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))

    def _cancel(self) -> None:
        if self.runner:
            self.runner.cancel()
            self._set_status("Wird abgebrochen …", "warn")
        if self.busy_task:
            self.busy_task.cancel()

    def _apply_to_all(self) -> None:
        if not self.current:
            return
        src = self.current.settings
        for e in self.entries:
            if e is self.current:
                continue
            floor = e.settings.audio.noise_floor_db
            e.settings = src.copy()
            e.settings.audio.noise_floor_db = floor
        self._set_status(f"Einstellungen auf {len(self.entries) - 1} weitere Datei(en) übertragen.", "ok")

    # ================================================================== ffmpeg / Hilfe
    def _warn_missing_ffmpeg(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Warning)
        box.setText("KlarBild braucht ffmpeg.")
        box.setInformativeText(
            "Auf dem Mac im Terminal:\n\n    brew install ffmpeg\n\n"
            "Für die beste Stabilisierung (vid.stab) eignet sich „ffmpeg-full“. "
            "Alternativ kannst du ein vorhandenes ffmpeg auswählen.")
        choose = box.addButton("ffmpeg auswählen …", QMessageBox.AcceptRole)
        box.addButton("Später", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is choose:
            self._choose_ffmpeg()

    def _choose_ffmpeg(self) -> None:
        if self.runner or self.busy_task:
            return
        path, _ = QFileDialog.getOpenFileName(self, "ffmpeg auswählen", "/opt/homebrew/bin" if sys.platform == "darwin" else "")
        if not path:
            return
        try:
            ff = detect_ffmpeg(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, APP_NAME, f"Das ist kein nutzbares ffmpeg:\n{exc}")
            return
        self.store.setValue("ffmpeg_path", ff.ffmpeg)
        QMessageBox.information(self, APP_NAME, "ffmpeg wurde gewählt. Bitte KlarBild neu starten, damit alle "
                                                "Funktionen das neue ffmpeg verwenden.")

    def _about(self) -> None:
        ff = f"{self.ff.ffmpeg} (Version {self.ff.version})" if self.ff else "nicht gefunden"
        QMessageBox.about(self, f"Über {APP_NAME}", (
            f"<h3>{APP_NAME} {__version__}</h3>"
            "<p>Videos entrauschen, stabilisieren und den Ton verbessern.</p>"
            f"<p><b>ffmpeg:</b> {ff}</p>"
            "<p>Verwendet ffmpeg (LGPL/GPL, als eigenständiges Programm aufgerufen), "
            "Qt for Python / PySide6 (LGPLv3) und NumPy (BSD). Keine Modelle mit "
            "Nur-nicht-kommerziell-Lizenz.</p>"))

    def _error_box(self, title: str, msg: str, log: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Warning)
        box.setText(title)
        box.setInformativeText(msg[-1500:])
        if log:
            box.setDetailedText(log[-8000:])
        box.exec()

    # ================================================================== Fenster
    def showEvent(self, e) -> None:
        super().showEvent(e)
        if not getattr(self, "_sized", False):
            self._sized = True
            QTimer.singleShot(0, lambda: self.split.setSizes([300, max(500, self.width() - 720), 420]))

    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e) -> None:
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.add_files(paths)

    def closeEvent(self, e) -> None:
        if self.runner:
            answer = QMessageBox.question(self, APP_NAME, "Ein Export läuft noch. Abbrechen und beenden?")
            if answer != QMessageBox.Yes:
                e.ignore()
                return
            self.runner.cancel()
        if self.busy_task:
            self.busy_task.cancel()
        self._stop_audio()
        self.store.setValue("geometry", self.saveGeometry())
        self._save_export()
        shutil.rmtree(self._tmp, ignore_errors=True)
        super().closeEvent(e)
