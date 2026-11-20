"""Selbsttest ohne Bedienung:  KlarBild --selftest

Prüft, ob ffmpeg gefunden wird und alle wichtigen Filter da sind, erzeugt einen kurzen Testclip,
analysiert ihn und exportiert ihn in mehreren Formaten. Mit QT_QPA_PLATFORM=offscreen wird
zusätzlich das Hauptfenster einmal aufgebaut. Rückgabe 0 = alles in Ordnung.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback

from . import APP_NAME, __version__


def _line(label: str, value) -> None:
    print(f"  {label:<14} {value}", flush=True)


def run() -> int:
    print(f"{APP_NAME} {__version__} – Selbsttest", flush=True)
    try:
        from .analysis import analyze
        from .exporters import FORMATS
        from .ffmpeg_tools import detect_ffmpeg, probe, run_ffmpeg
        from .pipeline import Job, run_job
        from .settings import ExportSettings, JobSettings

        ff = detect_ffmpeg()
        _line("ffmpeg:", ff.ffmpeg)
        _line("Version:", ff.version)
        _line("vid.stab:", "ja" if ff.has_vidstab else "nein")
        _line("fftdnoiz:", "ja" if ff.has_filter("fftdnoiz") else "nein")
        _line("VideoToolbox:", "ja" if ff.has_videotoolbox else "nein")
        _line("zscale (HDR):", "ja" if ff.has_filter("zscale") else "nein")

        with tempfile.TemporaryDirectory(prefix="klarbild_selftest_") as tmp:
            src = os.path.join(tmp, "test.mkv")
            run_ffmpeg(ff, ["-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25",
                            "-f", "lavfi", "-i", "sine=frequency=50:sample_rate=48000",
                            "-t", "2", "-vf", "noise=alls=15:allf=t", "-c:v", "ffv1", "-c:a", "pcm_s16le", src])
            media = probe(ff, src)
            an = analyze(ff, media)
            _line("Analyse:", f"Rauschen {an.noise:.1f}, Brummen {an.hum_hz} Hz")
            for key in ("mp4_h264", "mp4_hevc", "compare", "audio_m4a"):
                t = time.time()
                out = os.path.join(tmp, "out_" + key + FORMATS[key].ext)
                run_job(ff, Job(src, out, JobSettings(), ExportSettings(format=key, quality="small"), media, an))
                if os.path.getsize(out) < 1000:
                    raise RuntimeError(f"{key}: Ausgabe zu klein")
                _line(f"Export {key}:", f"ok ({time.time() - t:.1f} s)")

        if os.environ.get("QT_QPA_PLATFORM"):
            from PySide6.QtWidgets import QApplication

            from .gui import theme
            from .gui.main_window import MainWindow
            app = QApplication.instance() or QApplication([])
            theme.apply(app)
            win = MainWindow(ff)
            win.show()
            app.processEvents()
            win.close()
            _line("Oberfläche:", "ok")
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        print("SELBSTTEST FEHLGESCHLAGEN", flush=True)
        return 1
    print("SELBSTTEST OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(run())
