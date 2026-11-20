"""Rendert das App-Symbol als PNG (für PyInstaller --icon):  python3 tools/make_icon.py build/icon.png"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QSize  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from klarbild.gui.theme import make_icon  # noqa: E402

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "icon.png"
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    app = QApplication([])
    make_icon(1024).pixmap(QSize(1024, 1024)).save(target, "PNG")
    print(target)
