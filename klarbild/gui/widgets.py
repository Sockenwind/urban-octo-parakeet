"""Wiederverwendbare Bedienelemente im KlarBild-Stil."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QComboBox, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QProgressBar, QPushButton, QSizePolicy, QSlider, QVBoxLayout, QWidget)

from . import theme


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    )


class ToggleSwitch(QAbstractButton):
    """Kleiner animierter Schalter."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(38, 22)
        self._pos = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.valueChanged.connect(self._set_pos)
        self.toggled.connect(self._animate)

    def _set_pos(self, value) -> None:
        self._pos = float(value)
        self.update()

    def _animate(self, on: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def set_silent(self, on: bool) -> None:
        self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(False)
        self._anim.stop()
        self._pos = 1.0 if on else 0.0
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(38, 22)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = _mix(QColor("#3a414d"), QColor(theme.ACCENT), self._pos)
        if not self.isEnabled():
            track = _mix(track, QColor(theme.CARD), 0.55)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, 38, 22), 11, 11)
        p.setBrush(QColor("#ffffff") if self.isEnabled() else QColor("#8a8f99"))
        p.drawEllipse(QRectF(3 + self._pos * 16, 3, 16, 16))


class Card(QFrame):
    """Abgerundete Karte mit Titel, optionalem Untertitel und optionalem Schalter."""

    toggled = Signal(bool)

    def __init__(self, title: str, subtitle: str = "", toggle: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(12)
        head = QHBoxLayout()
        head.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title = QLabel(title)
        self.title.setObjectName("cardTitle")
        titles.addWidget(self.title)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("hint")
            sub.setWordWrap(True)
            titles.addWidget(sub)
        head.addLayout(titles, 1)
        self.switch: Optional[ToggleSwitch] = None
        if toggle:
            self.switch = ToggleSwitch()
            self.switch.toggled.connect(self._on_toggle)
            head.addWidget(self.switch, 0, Qt.AlignTop)
        outer.addLayout(head)
        self.body = QWidget()
        self.body.setObjectName("cardBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(12)
        self.body.setVisible(False)          # erst sichtbar, wenn Inhalt hinzukommt
        outer.addWidget(self.body)

    def add(self, widget: QWidget) -> QWidget:
        self.body_layout.addWidget(widget)
        self.body.setVisible(True)
        return widget

    def _on_toggle(self, on: bool) -> None:
        self.body.setEnabled(on)
        self.toggled.emit(on)

    def set_checked(self, on: bool) -> None:
        if self.switch:
            self.switch.set_silent(on)
            self.body.setEnabled(on)

    def is_checked(self) -> bool:
        return self.switch.isChecked() if self.switch else True


class SliderRow(QWidget):
    changed = Signal(int)

    def __init__(self, title: str, lo: int = 0, hi: int = 100, fmt: Optional[Callable[[int], str]] = None,
                 hint: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._fmt = fmt or (lambda v: f"{v} %")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        row = QHBoxLayout()
        self.label = QLabel(title)
        self.value_label = QLabel()
        self.value_label.setObjectName("value")
        row.addWidget(self.label)
        row.addStretch(1)
        row.addWidget(self.value_label)
        lay.addLayout(row)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(lo, hi)
        self.slider.setCursor(Qt.PointingHandCursor)
        self.slider.valueChanged.connect(self._on_change)
        lay.addWidget(self.slider)
        if hint:
            h = QLabel(hint)
            h.setObjectName("hint")
            h.setWordWrap(True)
            lay.addWidget(h)
        self._on_change(self.slider.value(), emit=False)

    def _on_change(self, v: int, emit: bool = True) -> None:
        self.value_label.setText(self._fmt(v))
        if emit:
            self.changed.emit(v)

    def value(self) -> int:
        return self.slider.value()

    def set_silent(self, v: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(int(v))
        self.slider.blockSignals(False)
        self._on_change(self.slider.value(), emit=False)


class ToggleRow(QWidget):
    """Beschriftung (mit optionalem Hinweis) links, Schalter rechts."""

    changed = Signal(bool)

    def __init__(self, title: str, hint: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        self.label = QLabel(title)
        texts.addWidget(self.label)
        self.hint = QLabel(hint)
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        self.hint.setVisible(bool(hint))
        texts.addWidget(self.hint)
        lay.addLayout(texts, 1)
        self.switch = ToggleSwitch()
        self.switch.toggled.connect(self.changed.emit)
        lay.addWidget(self.switch, 0, Qt.AlignVCenter)

    def value(self) -> bool:
        return self.switch.isChecked()

    def set_silent(self, on: bool) -> None:
        self.switch.set_silent(on)

    def set_hint(self, text: str) -> None:
        self.hint.setText(text)
        self.hint.setVisible(bool(text))


class ChoiceRow(QWidget):
    changed = Signal(str)

    def __init__(self, title: str, choices: dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.label = QLabel(title)
        lay.addWidget(self.label)
        self.combo = QComboBox()
        self.combo.setCursor(Qt.PointingHandCursor)
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo.setMinimumContentsLength(12)
        for key, text in choices.items():
            self.combo.addItem(text, key)
        self.combo.currentIndexChanged.connect(lambda _i: self.changed.emit(self.value()))
        lay.addWidget(self.combo)

    def value(self) -> str:
        return self.combo.currentData()

    def set_silent(self, key) -> None:
        idx = self.combo.findData(key)
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(max(0, idx))
        self.combo.blockSignals(False)


class Segmented(QWidget):
    """Gruppe aus Umschalt-Knöpfen (wie ein iOS-Segmented-Control)."""

    changed = Signal(str)

    def __init__(self, choices: dict, tooltips: Optional[dict] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("segmented")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}
        for key, text in choices.items():
            b = QPushButton(text)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumWidth(40)
            if tooltips and key in tooltips:
                b.setToolTip(tooltips[key])
            self.group.addButton(b)
            self.buttons[key] = b
            lay.addWidget(b)
            b.clicked.connect(lambda _c=False, k=key: self.changed.emit(k))

    def value(self) -> str:
        for k, b in self.buttons.items():
            if b.isChecked():
                return k
        return next(iter(self.buttons))

    def set_silent(self, key: str) -> None:
        b = self.buttons.get(key) or next(iter(self.buttons.values()))
        b.setChecked(True)


class LevelRows(QWidget):
    """Messwerte mit farbigem Punkt (ok / Warnung / schlecht)."""

    def __init__(self, empty_text: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(7)
        self.empty_text = empty_text
        self.set_rows([])

    def set_rows(self, rows: list) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        if not rows:
            lbl = QLabel(self.empty_text)
            lbl.setObjectName("hint")
            lbl.setWordWrap(True)
            self.grid.addWidget(lbl, 0, 0, 1, 3)
            return
        for i, (name, value, level) in enumerate(rows):
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {theme.LEVEL_COLORS.get(level, theme.MUTED)}; font-size: 10px;")
            n = QLabel(name)
            n.setObjectName("muted")
            v = QLabel(value)
            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.grid.addWidget(dot, i, 0)
            self.grid.addWidget(n, i, 1)
            self.grid.addWidget(v, i, 2)
        self.grid.setColumnStretch(1, 1)


def rounded_pixmap(pm: QPixmap, w: int, h: int, radius: float = 7) -> QPixmap:
    out = QPixmap(w, h)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
    p.setClipPath(path)
    p.fillRect(0, 0, w, h, QColor("#0b0d10"))
    if not pm.isNull():
        scaled = pm.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.drawPixmap((w - scaled.width()) // 2, (h - scaled.height()) // 2, scaled)
    p.end()
    return out


class FileItem(QWidget):
    """Eintrag in der Dateiliste: Vorschaubild, Name, Eckdaten, Status, Fortschritt."""

    THUMB_W, THUMB_H = 84, 48

    def __init__(self, name: str, meta: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(10)
        self.thumb = QLabel()
        self.thumb.setFixedSize(self.THUMB_W, self.THUMB_H)
        self.thumb.setPixmap(rounded_pixmap(QPixmap(), self.THUMB_W, self.THUMB_H))
        lay.addWidget(self.thumb)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.name = QLabel()
        self.name.setStyleSheet("font-weight: 600;")
        self._full_name = name
        self.name.setToolTip(name)
        self.meta = QLabel(meta)
        self.meta.setObjectName("hint")
        self._full_meta = meta
        self.status = QLabel()
        self.status.setObjectName("hint")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setVisible(False)
        texts.addWidget(self.name)
        texts.addWidget(self.meta)
        texts.addWidget(self.status)
        texts.addWidget(self.progress)
        lay.addLayout(texts, 1)
        self.set_status("Bereit", "muted")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        fm = self.name.fontMetrics()
        width = max(60, self.width() - self.THUMB_W - 36)
        self.name.setText(fm.elidedText(self._full_name, Qt.ElideMiddle, width))
        self.meta.setText(self.meta.fontMetrics().elidedText(self._full_meta, Qt.ElideRight, width))

    def set_thumbnail(self, pm: QPixmap) -> None:
        self.thumb.setPixmap(rounded_pixmap(pm, self.THUMB_W, self.THUMB_H))

    def set_audio_icon(self) -> None:
        """Wellenform-Symbol für reine Tondateien."""
        w, h = self.THUMB_W, self.THUMB_H
        pm = QPixmap(w, h)
        pm.fill(QColor("#14211f"))
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.ACCENT))
        heights = [0.25, 0.5, 0.8, 0.45, 0.95, 0.6, 0.35, 0.7, 0.4, 0.2]
        bar, gap = 4, 3
        x0 = (w - len(heights) * (bar + gap) + gap) / 2
        for i, f in enumerate(heights):
            bh = h * 0.7 * f
            p.drawRoundedRect(QRectF(x0 + i * (bar + gap), (h - bh) / 2, bar, bh), 2, 2)
        p.end()
        self.thumb.setPixmap(rounded_pixmap(pm, w, h))

    def set_status(self, text: str, level: str = "muted") -> None:
        color = theme.LEVEL_COLORS.get(level, theme.MUTED)
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color}; font-size: 12px;")

    def set_progress(self, value: Optional[float]) -> None:
        if value is None:
            self.progress.setVisible(False)
        else:
            self.progress.setVisible(True)
            self.progress.setValue(int(value * 1000))


class ElideLabel(QLabel):
    """Einzeiliges Label, das bei Platzmangel mit „…“ kürzt statt die Breite zu erzwingen."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setToolTip(text)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setPen(self.palette().color(self.foregroundRole()))
        p.setFont(self.font())
        text = self.fontMetrics().elidedText(self.text(), Qt.ElideLeft, self.width())
        p.drawText(self.rect(), int(self.alignment()), text)


def section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("sectionTitle")
    return lbl


def note_label(text: str = "") -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("note")
    lbl.setWordWrap(True)
    lbl.setVisible(bool(text))
    return lbl
