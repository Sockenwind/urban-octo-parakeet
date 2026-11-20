"""Farbschema, Stylesheet und App-Symbol."""
from __future__ import annotations

import os
import sys
import tempfile

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QIcon, QLinearGradient, QPainter, QPainterPath,
                           QPalette, QPen, QPixmap)
from PySide6.QtWidgets import QApplication

BG = "#0f1115"
SURFACE = "#15181e"
CARD = "#1c2028"
CARD_HI = "#242a35"
BORDER = "#2a303b"
TEXT = "#e8ebf0"
MUTED = "#8a93a3"
ACCENT = "#3ecfb0"
ACCENT_HOVER = "#5ddcc0"
ACCENT_TEXT = "#04241e"
WARN = "#f2b84b"
BAD = "#ef6b73"
LEVEL_COLORS = {"ok": ACCENT, "warn": WARN, "bad": BAD}


def _asset_dir() -> str:
    path = os.path.join(tempfile.gettempdir(), "klarbild_theme")
    os.makedirs(path, exist_ok=True)
    return path


def _draw_asset(name: str, size: int, painter_fn) -> str:
    path = os.path.join(_asset_dir(), name)
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    painter_fn(p, size)
    p.end()
    pm.save(path, "PNG")
    return path.replace("\\", "/")


def _arrow(p: QPainter, s: int) -> None:
    p.setPen(QPen(QColor(MUTED), s * 0.12, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    path = QPainterPath()
    path.moveTo(s * 0.28, s * 0.4)
    path.lineTo(s * 0.5, s * 0.62)
    path.lineTo(s * 0.72, s * 0.4)
    p.drawPath(path)


def _radio_on(p: QPainter, s: int) -> None:
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(ACCENT))
    p.drawEllipse(QRectF(1, 1, s - 2, s - 2))
    p.setBrush(QColor(ACCENT_TEXT))
    p.drawEllipse(QRectF(s * 0.32, s * 0.32, s * 0.36, s * 0.36))


def _radio_off(p: QPainter, s: int) -> None:
    p.setPen(QPen(QColor("#4a5260"), 2))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(2, 2, s - 4, s - 4))


def stylesheet() -> str:
    arrow = _draw_asset("arrow.png", 32, _arrow)
    r_on = _draw_asset("radio_on.png", 36, _radio_on)
    r_off = _draw_asset("radio_off.png", 36, _radio_off)
    return f"""
QWidget {{ color: {TEXT}; font-size: 13px; }}
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget#header {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
QWidget#sidebar, QWidget#rightPanel {{ background: {SURFACE}; }}
QWidget#footer {{ background: {SURFACE}; border-top: 1px solid {BORDER}; }}
QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#card QLabel {{ background: transparent; }}
QWidget#cardBody {{ background: transparent; }}
QLabel#appTitle {{ font-size: 18px; font-weight: 700; }}
QLabel#cardTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#sectionTitle {{ color: {MUTED}; font-size: 11px; font-weight: 700; }}
QLabel#muted, QLabel#hint {{ color: {MUTED}; }}
QLabel#hint {{ font-size: 12px; }}
QLabel#value {{ color: {MUTED}; }}
QLabel#chip {{ background: {CARD_HI}; border: 1px solid {BORDER}; border-radius: 11px; padding: 3px 10px; color: {MUTED}; font-size: 12px; }}
QLabel#note {{ background: #2a2414; border: 1px solid #4a3d1c; border-radius: 8px; padding: 8px 10px; color: {WARN}; font-size: 12px; }}

QPushButton {{ background: {CARD_HI}; border: 1px solid {BORDER}; border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ background: #2c3340; border-color: #384050; }}
QPushButton:pressed {{ background: #20252e; }}
QPushButton:disabled {{ color: #5a6170; background: #1d2129; }}
QPushButton#primary {{ background: {ACCENT}; color: {ACCENT_TEXT}; border: none; font-weight: 700; padding: 10px 18px; }}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: #2b4a44; color: #6d8a84; }}
QPushButton#accentOutline {{ background: transparent; color: {ACCENT}; border: 1px solid {ACCENT}; font-weight: 600; }}
QPushButton#accentOutline:hover {{ background: rgba(62, 207, 176, 0.12); }}
QPushButton#accentOutline:disabled {{ color: #4d6b65; border-color: #2f4743; }}
QPushButton#ghost {{ background: transparent; border: none; color: {MUTED}; padding: 6px 8px; }}
QPushButton#ghost:hover {{ color: {TEXT}; }}
QPushButton#danger {{ background: transparent; border: 1px solid #5a2f35; color: {BAD}; }}
QPushButton#danger:hover {{ background: rgba(239, 107, 115, 0.12); }}

QWidget#segmented {{ background: {CARD_HI}; border: 1px solid {BORDER}; border-radius: 9px; }}
QPushButton#seg {{ background: transparent; border: none; border-radius: 7px; padding: 6px 10px; color: {MUTED}; font-weight: 600; }}
QPushButton#seg:hover {{ color: {TEXT}; }}
QPushButton#seg:checked {{ background: {ACCENT}; color: {ACCENT_TEXT}; }}
QPushButton#seg:disabled {{ color: #4f5664; }}
QPushButton#seg:checked:disabled {{ background: #2b4a44; color: #6d8a84; }}

QSlider::groove:horizontal {{ height: 4px; background: #343b47; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::sub-page:horizontal:disabled {{ background: #3a4a48; }}
QSlider::handle:horizontal {{ background: #ffffff; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::handle:horizontal:disabled {{ background: #5a6170; }}
QSlider#timeline::groove:horizontal {{ height: 6px; border-radius: 3px; }}

QComboBox {{ background: {CARD_HI}; border: 1px solid {BORDER}; border-radius: 8px; padding: 5px 28px 5px 10px; }}
QComboBox:hover {{ border-color: #3a4352; }}
QComboBox:disabled {{ color: #5a6170; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url({arrow}); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: {CARD_HI}; border: 1px solid {BORDER}; selection-background-color: {ACCENT}; selection-color: {ACCENT_TEXT}; outline: none; padding: 4px; }}

QRadioButton {{ spacing: 10px; font-weight: 600; background: transparent; }}
QRadioButton::indicator {{ width: 18px; height: 18px; }}
QRadioButton::indicator:checked {{ image: url({r_on}); }}
QRadioButton::indicator:unchecked {{ image: url({r_off}); }}

QLineEdit {{ background: {CARD_HI}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 9px; selection-background-color: {ACCENT}; }}
QLineEdit:focus {{ border-color: {ACCENT}; }}

QTabWidget::pane {{ border: none; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{ background: transparent; color: {MUTED}; padding: 10px 0px; margin: 0 14px 0 0; border: none; border-bottom: 2px solid transparent; font-weight: 700; font-size: 13px; }}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #353c48; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ border-radius: 10px; margin: 2px 0px; }}
QListWidget::item:hover {{ background: #1c2129; }}
QListWidget::item:selected {{ background: #1d3531; }}

QProgressBar {{ background: #2a303b; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}

QSplitter::handle {{ background: {BORDER}; }}
QToolTip {{ background: {CARD_HI}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px; border-radius: 6px; }}
QMenu {{ background: {CARD}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {ACCENT}; color: {ACCENT_TEXT}; }}
QMenuBar {{ background: {SURFACE}; }}
QMenuBar::item:selected {{ background: {CARD_HI}; }}
QMessageBox {{ background: {CARD}; }}
"""


def make_icon(size: int = 256) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = float(size)
    grad = QLinearGradient(0, 0, s, s)
    grad.setColorAt(0, QColor("#46d9b9"))
    grad.setColorAt(1, QColor("#2a7fd4"))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawRoundedRect(QRectF(s * 0.06, s * 0.06, s * 0.88, s * 0.88), s * 0.22, s * 0.22)
    # Linse
    p.setBrush(QColor(255, 255, 255, 235))
    p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.27, s * 0.27)
    p.setBrush(QColor("#163a4a"))
    p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.17, s * 0.17)
    p.setBrush(QColor(255, 255, 255, 220))
    p.drawEllipse(QPointF(s * 0.56, s * 0.44), s * 0.05, s * 0.05)
    # Funkeln
    p.setPen(QPen(QColor(255, 255, 255), s * 0.035, Qt.SolidLine, Qt.RoundCap))
    cx, cy, r = s * 0.78, s * 0.22, s * 0.07
    p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
    p.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))
    p.end()
    return QIcon(pm)


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    for role, color in [
        (QPalette.Window, BG), (QPalette.WindowText, TEXT), (QPalette.Base, CARD),
        (QPalette.AlternateBase, CARD_HI), (QPalette.Text, TEXT), (QPalette.Button, CARD_HI),
        (QPalette.ButtonText, TEXT), (QPalette.Highlight, ACCENT), (QPalette.HighlightedText, ACCENT_TEXT),
        (QPalette.ToolTipBase, CARD_HI), (QPalette.ToolTipText, TEXT), (QPalette.PlaceholderText, MUTED),
    ]:
        pal.setColor(role, QColor(color))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor("#5a6170"))
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#5a6170"))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#5a6170"))
    app.setPalette(pal)
    if sys.platform != "darwin":
        families = set(QFontDatabase.families())
        for name in ("Inter", "Segoe UI", "Noto Sans", "DejaVu Sans"):
            if name in families:
                app.setFont(QFont(name, 10))
                break
    app.setStyleSheet(stylesheet())
    app.setWindowIcon(make_icon())
