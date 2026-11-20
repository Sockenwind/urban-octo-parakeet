"""Ein Export-Auftrag von Anfang bis Ende: Analyse-Durchläufe, Filter, Encoder."""
from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass
from typing import Callable, Optional

from .analysis import Analysis
from .audio_filters import (audio_chain, loudnorm_apply_filter, loudnorm_measure_filter,
                            output_sample_rate, parse_loudnorm)
from .exporters import (FORMATS, ExportError, audio_codec_for, audio_encoder_args, container_args,
                        video_encoder_args)
from .ffmpeg_tools import CancelToken, Cancelled, FFmpegError, FFmpegInfo, MediaInfo, run_ffmpeg
from .settings import ExportSettings, JobSettings
from .video_filters import build_video_plan, target_size

ProgressFn = Callable[[float, str], None]

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


class PipelineError(RuntimeError):
    def __init__(self, message: str, log: str = ""):
        super().__init__(message)
        self.log = log


@dataclass
class Job:
    input: str
    output: str
    settings: JobSettings
    export: ExportSettings
    media: MediaInfo
    analysis: Optional[Analysis] = None
    start: Optional[float] = None       # nur einen Ausschnitt verarbeiten (Vorschau-Clip)
    duration: Optional[float] = None


def is_interlaced(job: Job) -> bool:
    mode = job.settings.video.deinterlace
    if mode == "on":
        return True
    if mode == "off":
        return False
    if job.analysis is not None and job.analysis.interlaced is not None:
        return job.analysis.interlaced
    return job.media.interlaced_flag


def _font() -> Optional[str]:
    return next((f for f in FONT_CANDIDATES if os.path.isfile(f)), None)


def _label(ff: FFmpegInfo, text: str, height: int) -> str:
    font = _font()
    if not ff.has_filter("drawtext") or not font:
        return ""
    size = max(14, height // 18)
    return (f",drawtext=fontfile='{font}':text='{text}':x={size}:y={size}:fontsize={size}"
            f":fontcolor=white:box=1:boxcolor=black@0.45:boxborderw={size // 2}")


def compare_graph(ff: FFmpegInfo, pre: str, main: str, media: MediaInfo, labels: bool) -> str:
    h = min(media.height or 720, 1280 if media.is_portrait else 720)
    h -= h % 2
    scale = f"scale=w=trunc(iw*sar*{h}/ih/2)*2:h={h}:flags=bicubic,setsar=1,format=yuv420p"
    lb = _label(ff, "Vorher", h) if labels else ""
    la = _label(ff, "Nachher", h) if labels else ""
    return (f"[0:v]split=2[kb][ka];[kb]{pre},{scale}{lb}[b];[ka]{main},{scale}{la}[a];"
            f"[b][a]hstack=inputs=2[v]")


def run_job(ff: FFmpegInfo, job: Job, on_progress: Optional[ProgressFn] = None,
            cancel: Optional[CancelToken] = None) -> str:
    """Verarbeitet einen Auftrag und liefert den Pfad der fertigen Datei."""
    fmt = FORMATS[job.export.format]
    media = job.media
    vs, aus = job.settings.video, job.settings.audio
    quality = job.export.quality

    want_video = fmt.kind != "audio" and media.has_video
    want_audio = media.has_audio and not aus.mute
    if fmt.kind == "audio" and not media.has_audio:
        raise PipelineError("Diese Datei enthält keine Tonspur – bitte ein Videoformat wählen.")
    if fmt.kind != "audio" and not media.has_video:
        raise PipelineError("Diese Datei enthält kein Bild – bitte ein Format „Nur Ton“ wählen.")

    seg = job.duration or max(0.1, media.duration - (job.start or 0))
    src = ["-ss", f"{job.start:.3f}"] if job.start else []
    if job.duration:
        src += ["-t", f"{job.duration:.3f}"]
    src += ["-i", os.path.abspath(job.input)]

    plan = build_video_plan(ff, vs, media, is_interlaced(job)) if want_video else None
    achain = audio_chain(ff, aus) if want_audio else []
    normalize = want_audio and aus.enabled and aus.normalize
    target = float(aus.target)

    stages = []
    if plan and plan.detect:
        stages.append(("detect", 0.5, "Verwacklung analysieren"))
    if normalize:
        stages.append(("measure", 0.08, "Lautheit messen"))
    stages.append(("encode", 1.0, "Video berechnen" if want_video else "Ton berechnen"))
    total = sum(w for _, w, _ in stages)
    done = 0.0

    def reporter(weight: float, text: str):
        base = done

        def report(frac: float) -> None:
            if on_progress:
                on_progress((base + weight * frac) / total, text)
        return report

    out = os.path.abspath(job.output)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="klarbild_")
    try:
        for key, weight, text in stages:
            report = reporter(weight, text)
            report(0.0)
            if key == "detect":
                run_ffmpeg(ff, src + ["-map", "0:v:0", "-an", "-vf", plan.detect, "-f", "null", "-"],
                           duration=seg, on_progress=report, cancel=cancel, cwd=tmp)
            elif key == "measure":
                chain = achain + [loudnorm_measure_filter(target)]
                log = run_ffmpeg(ff, src + ["-map", "0:a:0", "-vn", "-af", ",".join(chain), "-f", "null", "-"],
                                 duration=seg, on_progress=report, cancel=cancel, cwd=tmp)
                measured = parse_loudnorm(log)
                if measured:
                    rate = output_sample_rate(media.sample_rate, audio_codec_for(ff, fmt))
                    achain = achain + [loudnorm_apply_filter(target, measured, rate)]
            else:
                _encode(ff, job, fmt, plan, achain, want_video, want_audio, quality, src, out, seg,
                        report, cancel, tmp)
            done += weight
    except Cancelled:
        _remove(out)
        raise
    except (FFmpegError, ExportError) as exc:
        _remove(out)
        raise PipelineError(str(exc), getattr(exc, "log", "")) from exc
    finally:
        _cleanup(tmp)
    return out


def _encode(ff, job, fmt, plan, achain, want_video, want_audio, quality, src, out, seg, report, cancel, tmp):
    media = job.media
    args = list(src)
    vargs: list = []
    if want_video:
        size = target_size(job.settings.video, media)
        fps = media.fps * (2 if job.settings.video.deinterlace_double_rate and is_interlaced(job) else 1)
        ten_bit = "10" in media.pix_fmt or "p010" in media.pix_fmt
        vargs = video_encoder_args(ff, fmt, quality, job.export.hardware, size, fps, ten_bit)
    aargs: list = []
    if want_audio:
        aargs = ["-map", "0:a:0"]
        if achain:
            aargs += ["-af", ",".join(achain)]
        aargs += audio_encoder_args(ff, fmt, quality)
        if audio_codec_for(ff, fmt) in ("libopus", "opus"):
            aargs += ["-ar", "48000"]
    else:
        aargs = ["-an"]
    tail = ["-map_metadata", "0", "-max_muxing_queue_size", "4096", *container_args(fmt), out]

    if fmt.kind == "compare":
        for labels in (True, False):
            graph = compare_graph(ff, plan.pre, plan.main, media, labels)
            try:
                run_ffmpeg(ff, args + ["-filter_complex", graph, "-map", "[v]", *vargs, *aargs, *tail],
                           duration=seg, on_progress=report, cancel=cancel, cwd=tmp)
                return
            except FFmpegError:
                if not labels:
                    raise
        return
    if want_video:
        args += ["-map", "0:v:0", "-vf", plan.main, *vargs]
    else:
        args += ["-vn"]
    run_ffmpeg(ff, args + aargs + tail, duration=seg, on_progress=report, cancel=cancel, cwd=tmp)


def _remove(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _cleanup(folder: str) -> None:
    try:
        for name in os.listdir(folder):
            os.remove(os.path.join(folder, name))
        os.rmdir(folder)
    except OSError:
        pass


def open_in_system(path: str) -> None:
    """Datei oder Ordner mit dem Standardprogramm öffnen (ohne Qt, für Skripte)."""
    import subprocess
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", path])
