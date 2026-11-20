"""Bildverbesserung: Filterketten für ffmpeg.

Reihenfolge der Kette (bewusst gewählt):
  HDR→SDR · Deinterlacing · Blockartefakte · Entrauschen · Stabilisieren · Farbe · Skalieren · Schärfen
Entrauscht wird vor dem Stabilisieren, weil die Interpolation der Stabilisierung das Rauschen
verschmiert und es danach schwerer zu entfernen ist.

Die Stärke-Zuordnungen wurden an der Xiph-Testsequenz „Foreman“ mit künstlichem Rauschen
per PSNR/SSIM abgestimmt (siehe README, Abschnitt „Wie die Filter abgestimmt wurden“).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .ffmpeg_tools import FFmpegInfo, MediaInfo
from .settings import VideoSettings

TRF_NAME = "transforms.trf"


def _s(value: float) -> float:
    return max(0.0, min(100.0, float(value))) / 100.0


# --------------------------------------------------------------------------- Einzelfilter

def tonemap_filter(ff: FFmpegInfo, media: MediaInfo) -> Optional[str]:
    """HDR-Videos (z. B. vom iPhone) in normales SDR umwandeln, sonst wirken sie blass."""
    if media.is_hdr and ff.has_filter("zscale") and ff.has_filter("tonemap"):
        return ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
                "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
    return None


def deinterlace_filter(ff: FFmpegInfo, vs: VideoSettings) -> str:
    mode = "send_field" if vs.deinterlace_double_rate else "send_frame"
    if ff.has_filter("bwdif"):
        return f"bwdif=mode={mode}:parity=auto:deint=all"
    return f"yadif=mode={mode}:parity=auto:deint=all"


def denoise_filters(ff: FFmpegInfo, vs: VideoSettings) -> list:
    s = _s(vs.denoise_strength)
    if not vs.denoise_enabled or s <= 0:
        return []
    method = vs.denoise_method
    if method != "fast" and not ff.has_filter("fftdnoiz"):
        method = "fast"
    if method == "fast":
        ls = 2 + 14 * s
        lt = 1.5 * ls
        return [f"hqdn3d={ls:.2f}:{0.75 * ls:.2f}:{lt:.2f}:{0.75 * lt:.2f}"]
    sigma = 2 + 40 * s
    if method == "balanced":
        return [fft_denoise(ff, f"fftdnoiz=sigma={sigma:.1f}:prev=1:next=1", shift=8)]
    # "max": mehr Blocküberlappung plus zeitliche Nachglättung
    t = 2 + 6 * s
    return [fft_denoise(ff, f"fftdnoiz=sigma={sigma:.1f}:prev=1:next=1:overlap=0.75", shift=4),
            f"hqdn3d=0:0:{t:.2f}:{0.75 * t:.2f}"]


def fft_denoise(ff: FFmpegInfo, fft: str, shift: int) -> str:
    """fftdnoiz arbeitet in überlappenden Blöcken und hinterlässt dabei ein feines Raster
    (gemessen: Filterwirkung schwankt um 28 % im 16-px-Takt, nach dem Schärfen 44 %).
    Abhilfe: ein zweiter Durchlauf mit um eine halbe Schrittweite verschobenem Raster, dann
    werden beide gemittelt. Das senkt das Raster auf 5–9 % (pixelweise Filter: 1,6 %)."""
    if not (ff.has_filter("blend") and ff.has_filter("fillborders")):
        return fft
    return (f"split[dnA][dnB];[dnA]{fft}[dnX];"
            f"[dnB]pad=iw+{shift}:ih+{shift}:{shift}:{shift},fillborders=left={shift}:top={shift}:mode=mirror,"
            f"{fft},crop=iw-{shift}:ih-{shift}:{shift}:{shift}[dnY];[dnX][dnY]blend=all_mode=average")


def stab_detect_filter(vs: VideoSettings, trf: str = TRF_NAME) -> str:
    s = _s(vs.stabilize_strength)
    shakiness = min(10, max(3, round(4 + 6 * s)))
    opts = [f"shakiness={shakiness}", "accuracy=15", "stepsize=6", f"result={trf}"]
    if vs.stabilize_mode == "tripod":
        opts.append("tripod=1")
    return "vidstabdetect=" + ":".join(opts)


def stab_transform_filter(vs: VideoSettings, trf: str = TRF_NAME) -> str:
    s = _s(vs.stabilize_strength)
    opts = [f"input={trf}", "interpol=bicubic"]
    if vs.stabilize_mode == "tripod":
        opts.append("tripod=1")
    else:
        opts.append(f"smoothing={round(5 + 45 * s)}")
    if vs.stabilize_border == "zoom":
        opts += ["optzoom=1", "crop=black"]
    elif vs.stabilize_border == "fill":
        opts += ["optzoom=0", "crop=keep"]
    else:
        opts += ["optzoom=0", "crop=black"]
    return "vidstabtransform=" + ":".join(opts)


def deshake_filter(vs: VideoSettings) -> str:
    """Einfacher Ersatz, falls ffmpeg ohne vid.stab gebaut wurde."""
    s = _s(vs.stabilize_strength)
    r = min(64, 16 * round(1 + 3 * s))           # deshake verlangt Vielfache von 16
    edge = "blank" if vs.stabilize_border == "black" else "mirror"
    return f"deshake=rx={r}:ry={r}:edge={edge}"


def color_filter(vs: VideoSettings) -> Optional[str]:
    if not (vs.brightness or vs.contrast or vs.saturation):
        return None
    b = vs.brightness / 100 * 0.15
    c = 1 + vs.contrast / 100 * 0.5
    sat = max(0.0, 1 + vs.saturation / 100)
    return f"eq=brightness={b:.3f}:contrast={c:.3f}:saturation={sat:.3f}"


def target_size(vs: VideoSettings, media: MediaInfo) -> tuple:
    """Ausgabegröße (Breite, Höhe) – „1080p“ bezieht sich immer auf die kurze Bildseite."""
    w, h = media.width, media.height
    if vs.resolution == "original" or not (w and h):
        return w, h
    short = int(vs.resolution)
    if media.is_portrait:
        nw, nh = short, round(h * short / w / 2) * 2
    else:
        nw, nh = round(w * short / h / 2) * 2, short
    return nw, nh


def scale_filter(vs: VideoSettings, media: MediaInfo) -> Optional[str]:
    if vs.resolution == "original":
        return None
    short = int(vs.resolution)
    return f"scale={short}:-2:flags=lanczos" if media.is_portrait else f"scale=-2:{short}:flags=lanczos"


def sharpen_filter(ff: FFmpegInfo, vs: VideoSettings) -> Optional[str]:
    s = _s(vs.sharpen)
    if s <= 0:
        return None
    if ff.has_filter("cas"):
        return f"cas=strength={0.9 * s:.2f}"
    return f"unsharp=5:5:{1.5 * s:.2f}:5:5:0"


# --------------------------------------------------------------------------- Gesamtplan

@dataclass
class VideoPlan:
    main: str                      # Kette für den Export
    preview: str                   # Kette für das Vorschaubild (ohne Stabilisierung)
    pre: str                       # nur HDR/Deinterlacing – für die „Vorher“-Seite im Vergleich
    detect: Optional[str] = None   # Kette für den Analyse-Durchlauf von vid.stab
    notes: list = field(default_factory=list)


def _join(parts: list) -> str:
    parts = [p for p in parts if p]
    return ",".join(parts) if parts else "null"


def build_video_plan(ff: FFmpegInfo, vs: VideoSettings, media: MediaInfo, interlaced: bool) -> VideoPlan:
    notes: list = []
    pre = [tonemap_filter(ff, media)]
    if media.is_hdr and not pre[0]:
        notes.append("HDR-Video: Dieses ffmpeg kann kein Tonemapping (zscale fehlt) – Farben können blass wirken.")
    if interlaced:
        pre.append(deinterlace_filter(ff, vs))
    if vs.deblock and ff.has_filter("deblock"):
        pre.append("deblock=filter=weak:block=8")
    den = denoise_filters(ff, vs)
    if vs.denoise_enabled and vs.denoise_method != "fast" and not ff.has_filter("fftdnoiz"):
        notes.append("Entrauschen: fftdnoiz fehlt in diesem ffmpeg – es wird der schnelle Filter verwendet.")

    stab = None
    detect = None
    if vs.stabilize_enabled:
        if ff.has_vidstab:
            light = ["hqdn3d=4:3:6:4.5"] if den else []
            detect = _join(pre + light + [stab_detect_filter(vs)])
            stab = stab_transform_filter(vs)
        else:
            stab = deshake_filter(vs)
            notes.append("Stabilisieren: ffmpeg ohne vid.stab – es wird das einfachere „deshake“ verwendet.")

    finish = [color_filter(vs), scale_filter(vs, media), sharpen_filter(ff, vs)]
    return VideoPlan(
        main=_join(pre + den + [stab] + finish),
        preview=_join(pre + den + finish),
        pre=_join(pre),
        detect=detect,
        notes=notes,
    )
