"""Rauchtest der Oberfläche ohne Bildschirm (Qt „offscreen“)."""
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def app():
    from klarbild.gui import theme
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    theme.apply(application)
    return application


def wait(app, cond, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_main_window_flow(app, ff, shaky, audio_only, tmp_path):
    from klarbild.gui.main_window import MainWindow
    win = MainWindow(ff)
    win.store.clear()
    shown = []
    win._error_box = lambda *args: shown.append(args)              # kein modales Fenster im Test
    win.show()
    win.add_files([shaky.path, audio_only.path, shaky.path])          # Duplikat wird ignoriert
    assert len(win.entries) == 2
    assert wait(app, lambda: win.compare.before is not None and win.compare.after is not None)

    # Regler ändern → Einstellungen der Datei und neue Vorschau
    old_after = win.compare.after
    win.panel.dn_strength.slider.setValue(85)
    assert win.current.settings.video.denoise_strength == 85
    assert wait(app, lambda: win.compare.after is not old_after and not win.compare.busy_text)

    # Analyse übernimmt Empfehlungen
    win._analyze_current()
    assert wait(app, lambda: win.busy_task is None, 120)
    assert win.current.analysis is not None and win.current.settings.audio.hum == "50"
    assert win.panel.hum.value() == "50"

    # Export beider Dateien – die Tondatei wird bei MP4 automatisch als M4A gespeichert
    win.panel.loc_folder.setChecked(True)
    win.panel._folder = str(tmp_path)
    win.panel.format_radios["mp4_h264"].setChecked(True)
    win._export(list(win.entries))
    assert wait(app, lambda: win.runner is None, 180)
    assert os.path.exists(win.entries[0].output) and win.entries[0].output.endswith(".mp4")
    assert os.path.exists(win.entries[1].output) and win.entries[1].output.endswith(".m4a")
    assert not win._export_errors and not shown

    # Hörprobe wird berechnet (Abspielen ist im Test egal)
    win.file_list.setCurrentRow(1)
    win._listen("after")
    assert wait(app, lambda: len(win._listen_cache) == 1, 60)
    before, after = next(iter(win._listen_cache.values()))
    assert os.path.getsize(before) > 1000 and os.path.getsize(after) > 1000
    win.close()
