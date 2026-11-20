"""Vorher/Nachher-Ansicht mit Teiler, Zoom und Verschieben."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import theme


class CompareView(QWidget):
    files_dropped = Signal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setMinimumSize(420, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.before: Optional[QImage] = None
        self.after: Optional[QImage] = None
        self.split = 0.5
        self.zoom = 1.0                     # 1.0 = eingepasst
        self.center = QPointF(0.5, 0.5)     # Bildpunkt (normiert) in der Fenstermitte
        self.busy_text = ""
        self.placeholder = "Videos hierher ziehen\noder oben auf „Dateien hinzufügen“ klicken"
        self.after_hint = ""
        self._drag_from: Optional[QPointF] = None
        self._drop_active = False

    # ------------------------------------------------------------------ API
    def set_before(self, img: Optional[QImage]) -> None:
        self.before = img
        self.update()

    def set_after(self, img: Optional[QImage]) -> None:
        self.after = img
        self.update()

    def clear(self, placeholder: Optional[str] = None) -> None:
        self.before = self.after = None
        self.zoom = 1.0
        self.center = QPointF(0.5, 0.5)
        if placeholder is not None:
            self.placeholder = placeholder
        self.update()

    def set_busy(self, text: str) -> None:
        self.busy_text = text
        self.update()

    def reset_zoom(self) -> None:
        self.zoom = 1.0
        self.center = QPointF(0.5, 0.5)
        self.update()

    # ------------------------------------------------------------------ Geometrie
    def _base(self) -> Optional[QImage]:
        return self.before or self.after

    def _fit_scale(self) -> float:
        img = self._base()
        if not img or img.isNull():
            return 1.0
        return min(self.width() / img.width(), self.height() / img.height())

    def _target(self) -> QRectF:
        img = self._base()
        s = self._fit_scale() * self.zoom
        w, h = img.width() * s, img.height() * s
        x = self.width() / 2 - self.center.x() * w
        y = self.height() / 2 - self.center.y() * h
        return QRectF(x, y, w, h)

    def _clamp_center(self) -> None:
        if self.zoom <= 1.0:
            self.center = QPointF(0.5, 0.5)
            return
        t = self._target()
        half_w = self.width() / 2 / t.width()
        half_h = self.height() / 2 / t.height()
        cx = min(max(self.center.x(), half_w), 1 - half_w) if half_w < 0.5 else 0.5
        cy = min(max(self.center.y(), half_h), 1 - half_h) if half_h < 0.5 else 0.5
        self.center = QPointF(cx, cy)

    # ------------------------------------------------------------------ Zeichnen
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#0a0c0f"))
        img = self._base()
        if not img or img.isNull():
            self._paint_placeholder(p)
            return
        target = self._target()
        pixel_level = self._fit_scale() * self.zoom >= 1.0
        p.setRenderHint(QPainter.SmoothPixmapTransform, not pixel_level)
        split_x = self.width() * self.split

        p.save()
        p.setClipRect(QRectF(0, 0, split_x, self.height()))
        if self.before:
            p.drawImage(target, self.before)
        p.restore()

        p.save()
        p.setClipRect(QRectF(split_x, 0, self.width() - split_x, self.height()))
        if self.after:
            p.drawImage(target, self.after)
        elif self.before:
            p.drawImage(target, self.before)
            p.fillRect(QRectF(split_x, 0, self.width() - split_x, self.height()), QColor(10, 12, 15, 150))
        p.restore()

        # Teiler
        p.setPen(QPen(QColor(255, 255, 255, 230), 2))
        p.drawLine(QPointF(split_x, 0), QPointF(split_x, self.height()))
        cy = self.height() / 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QPointF(split_x, cy), 15, 15)
        p.setPen(QPen(QColor("#1a1d23"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        for d in (-1, 1):
            path = QPainterPath()
            path.moveTo(split_x + d * 4, cy - 5)
            path.lineTo(split_x + d * 9, cy)
            path.lineTo(split_x + d * 4, cy + 5)
            p.drawPath(path)

        self._pill(p, "VORHER", QPointF(14, 14), align_right=False)
        self._pill(p, "NACHHER", QPointF(self.width() - 14, 14), align_right=True, accent=True)
        if self.zoom > 1.001:
            pct = round(self._fit_scale() * self.zoom * 100)
            self._pill(p, f"{pct} %", QPointF(14, self.height() - 40), align_right=False)
        if self.after_hint:
            self._pill(p, self.after_hint, QPointF(self.width() - 14, 46), align_right=True, small=True)
        if self.busy_text:
            self._pill(p, self.busy_text, QPointF(self.width() / 2, self.height() - 40), center=True, accent=True)

    def _pill(self, p: QPainter, text: str, pos: QPointF, align_right: bool = False, center: bool = False,
              accent: bool = False, small: bool = False) -> None:
        f = QFont(self.font())
        f.setPixelSize(11 if small else 12)
        f.setBold(not small)
        p.setFont(f)
        fm = p.fontMetrics()
        w = fm.horizontalAdvance(text) + 20
        h = 24 if not small else 22
        x = pos.x() - w / 2 if center else (pos.x() - w if align_right else pos.x())
        rect = QRectF(x, pos.y(), w, h)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(62, 207, 176, 235) if accent else QColor(12, 14, 18, 190))
        p.drawRoundedRect(rect, h / 2, h / 2)
        p.setPen(QColor(theme.ACCENT_TEXT) if accent else QColor("#ffffff"))
        p.drawText(rect, Qt.AlignCenter, text)

    def _paint_placeholder(self, p: QPainter) -> None:
        r = QRectF(self.rect()).adjusted(24, 24, -24, -24)
        pen = QPen(QColor(theme.ACCENT if self._drop_active else "#2f3642"), 2, Qt.DashLine)
        p.setPen(pen)
        p.setBrush(QColor(62, 207, 176, 18) if self._drop_active else Qt.NoBrush)
        p.drawRoundedRect(r, 18, 18)
        f = QFont(self.font())
        f.setPixelSize(15)
        p.setFont(f)
        p.setPen(QColor(theme.MUTED))
        p.drawText(r, Qt.AlignCenter, self.busy_text or self.placeholder)

    # ------------------------------------------------------------------ Maus
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._drag_from = e.position()
            if self.zoom > 1.001:
                self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, _e) -> None:
        self._drag_from = None
        self.unsetCursor()

    def mouseMoveEvent(self, e) -> None:
        pos = e.position()
        if self._drag_from is not None and self.zoom > 1.001 and self._base():
            t = self._target()
            delta = pos - self._drag_from
            self.center = QPointF(self.center.x() - delta.x() / t.width(), self.center.y() - delta.y() / t.height())
            self._drag_from = pos
            self._clamp_center()
        else:
            self.split = min(max(pos.x() / max(1, self.width()), 0.0), 1.0)
        self.update()

    def wheelEvent(self, e) -> None:
        if not self._base():
            return
        steps = e.angleDelta().y() / 120.0
        if steps == 0:
            return
        self._zoom_at(e.position(), self.zoom * (1.18 ** steps))

    def mouseDoubleClickEvent(self, e) -> None:
        if not self._base():
            return
        one_to_one = 1.0 / self._fit_scale()
        self._zoom_at(e.position(), 1.0 if self.zoom > 1.001 else max(one_to_one, 2.0))

    def _zoom_at(self, pos: QPointF, new_zoom: float) -> None:
        new_zoom = min(max(new_zoom, 1.0), 16.0)
        t = self._target()
        img_pt = QPointF((pos.x() - t.x()) / t.width(), (pos.y() - t.y()) / t.height())
        self.zoom = new_zoom
        t2 = self._target()
        # Bildpunkt unter dem Mauszeiger festhalten
        self.center = QPointF(
            img_pt.x() - (pos.x() - self.width() / 2) / t2.width(),
            img_pt.y() - (pos.y() - self.height() / 2) / t2.height(),
        )
        self._clamp_center()
        self.update()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._clamp_center()

    # ------------------------------------------------------------------ Drag & Drop
    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drop_active = True
            self.update()

    def dragLeaveEvent(self, _e) -> None:
        self._drop_active = False
        self.update()

    def dropEvent(self, e) -> None:
        self._drop_active = False
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
        self.update()
