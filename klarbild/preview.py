"""Vorschau: Einzelbilder, Vorschaubilder, Hörproben und kurze Vergleichs-Clips."""
from __future__ import annotations

import os
from typing import Optional

from .analysis import Analysis
from .ffmpeg_tools import CancelToken, FFmpegInfo, MediaInfo, run_capture, run_ffmpeg
from .pipeline import Job, ProgressFn, run_job
from .settings import ExportSettings, JobSettings


def _clamp_time(media: MediaInfo, t: float) -> float:
    return max(0.0, min(t, max(0.0, media.duration - 0.15)))


def frame_ppm(ff: FFmpegInfo, media: MediaInfo, t: float, vf: Optional[str] = None, warmup: float = 0.6) -> bytes:
    """Ein Bild bei Sekunde t als PPM. Mit Filtern wird kurz vorher begonnen, damit zeitliche
    Filter (Entrauschen über mehrere Bilder) eingeschwungen sind."""
    t = _clamp_time(media, t)
    if vf and vf != "null":
        start = max(0.0, t - warmup)
        args = ["-ss", f"{start:.3f}", "-i", media.path, "-map", "0:v:0", "-vf", vf]
        if t - start > 0.001:
            args += ["-ss", f"{t - start:.3f}"]
    else:
        args = ["-ss", f"{t:.3f}", "-i", media.path, "-map", "0:v:0"]
    args += ["-frames:v", "1", "-f", "image2pipe", "-vcodec", "ppm", "-"]
    data = run_capture(ff, args, timeout=300)
    if not data and t > 0:                       # Ende der Datei getroffen – etwas früher versuchen
        return frame_ppm(ff, media, t - 1.0, vf, warmup)
    return data


def thumbnail_ppm(ff: FFmpegInfo, media: MediaInfo, width: int = 240) -> bytes:
    t = media.duration * 0.15 if media.duration > 3 else 0.0
    return frame_ppm(ff, media, t, f"scale={width}:-2", warmup=0.0)


def audio_preview(ff: FFmpegInfo, settings: JobSettings, media: MediaInfo, analysis: Optional[Analysis],
                  start: float, folder: str, duration: float = 10.0) -> tuple:
    """Erzeugt zwei WAV-Dateien (vorher/nachher) für den direkten Hörvergleich."""
    start = max(0.0, min(start, max(0.0, media.duration - duration)))
    before = os.path.join(folder, "hoerprobe_vorher.wav")
    after = os.path.join(folder, "hoerprobe_nachher.wav")
    run_ffmpeg(ff, ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", media.path, "-map", "0:a:0",
                    "-vn", "-c:a", "pcm_s16le", before])
    if os.path.exists(after):
        os.remove(after)
    job = Job(media.path, after, settings, ExportSettings(format="preview_wav"), media, analysis,
              start=start, duration=duration)
    run_job(ff, job)
    return before, after


def preview_clip(ff: FFmpegInfo, settings: JobSettings, media: MediaInfo, analysis: Optional[Analysis],
                 start: float, folder: str, duration: float = 6.0,
                 on_progress: Optional[ProgressFn] = None, cancel: Optional[CancelToken] = None) -> str:
    """Kurzer Vorher/Nachher-Clip mit der kompletten Verarbeitung (inkl. Stabilisierung)."""
    start = max(0.0, min(start, max(0.0, media.duration - duration)))
    out = os.path.join(folder, f"vorschau_{int(start * 1000)}.mp4")
    if os.path.exists(out):
        os.remove(out)
    job = Job(media.path, out, settings, ExportSettings(format="compare", quality="medium"), media, analysis,
              start=start, duration=min(duration, media.duration))
    return run_job(ff, job, on_progress=on_progress, cancel=cancel)
