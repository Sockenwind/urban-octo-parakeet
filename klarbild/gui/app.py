"""Programmstart der Oberfläche."""
from __future__ import annotations

import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from .. import APP_NAME
from ..ffmpeg_tools import FFmpegNotFound, detect_ffmpeg
from . import theme
from .main_window import MainWindow


def main(argv: list | None = None) -> int:
    argv = sys.argv if argv is None else argv
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("KlarBild")
    theme.apply(app)

    override = QSettings("KlarBild", "KlarBild").value("ffmpeg_path", "") or None
    ff, error = None, ""
    try:
        ff = detect_ffmpeg(override)
    except FFmpegNotFound as exc:
        error = str(exc)

    win = MainWindow(ff, error)
    win.show()
    files = [a for a in argv[1:] if not a.startswith("-")]
    if files and ff:
        win.add_files(files)
    return app.exec()
