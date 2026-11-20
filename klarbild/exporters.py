"""Exportformate: Codec- und Container-Einstellungen für ffmpeg."""
from __future__ import annotations

import os
from dataclasses import dataclass

from .ffmpeg_tools import FFmpegInfo


class ExportError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExportFormat:
    key: str
    label: str
    description: str
    ext: str
    kind: str          # "video" | "compare" | "audio"
    audio_codec: str


_FORMATS = [
    ExportFormat("mp4_h264", "MP4 · H.264", "Läuft überall: Handy, Fernseher, Web, Messenger.", ".mp4", "video", "aac"),
    ExportFormat("mp4_hevc", "MP4 · H.265 (HEVC)", "Etwa halb so groß bei gleicher Qualität. Ideal für Apple-Geräte.", ".mp4", "video", "aac"),
    ExportFormat("mov_prores", "MOV · ProRes 422", "Für Final Cut, DaVinci Resolve, Premiere. Sehr große Dateien.", ".mov", "video", "pcm_s24le"),
    ExportFormat("mkv_ffv1", "MKV · FFV1 verlustfrei", "Zum Archivieren – ohne jeden Qualitätsverlust.", ".mkv", "video", "flac"),
    ExportFormat("webm_vp9", "WebM · VP9", "Offenes Format für Websites.", ".webm", "video", "libopus"),
    ExportFormat("compare", "Vorher/Nachher-Video", "Original und Ergebnis nebeneinander – zum Zeigen.", ".mp4", "compare", "aac"),
    ExportFormat("audio_wav", "Nur Ton · WAV", "Unkomprimiert, 24 Bit – für die Weiterbearbeitung.", ".wav", "audio", "pcm_s24le"),
    ExportFormat("audio_flac", "Nur Ton · FLAC", "Verlustfrei komprimiert.", ".flac", "audio", "flac"),
    ExportFormat("audio_m4a", "Nur Ton · M4A (AAC)", "Klein und überall abspielbar.", ".m4a", "audio", "aac"),
    ExportFormat("audio_mp3", "Nur Ton · MP3", "Maximale Kompatibilität.", ".mp3", "audio", "libmp3lame"),
    # intern für die Hörprobe – wird in der Oberfläche nicht angeboten
    ExportFormat("preview_wav", "Hörprobe", "", ".wav", "audio", "pcm_s16le"),
]
FORMATS = {f.key: f for f in _FORMATS}
USER_FORMATS = [f for f in _FORMATS if not f.key.startswith("preview")]

# Reine Tondateien bekommen bei einem Videoformat automatisch das passende Tonformat.
_AUDIO_FALLBACK = {"mov_prores": "audio_wav", "mkv_ffv1": "audio_flac"}


def format_for(key: str, has_video: bool) -> str:
    if not has_video and FORMATS[key].kind != "audio":
        return _AUDIO_FALLBACK.get(key, "audio_m4a")
    return key


_CRF = {
    "libx264": {"high": 18, "medium": 21, "small": 25},
    "libx265": {"high": 20, "medium": 23, "small": 27},
    "libvpx-vp9": {"high": 28, "medium": 32, "small": 36},
}
_BITS_PER_PIXEL = {"high": 0.14, "medium": 0.09, "small": 0.055}   # für Hardware-Encoder


def _hw_bitrate(quality: str, w: int, h: int, fps: float, factor: float = 1.0) -> str:
    kbps = _BITS_PER_PIXEL.get(quality, 0.09) * max(w, 16) * max(h, 16) * (fps or 25) * factor / 1000
    return f"{max(500, int(kbps))}k"


def video_encoder_args(ff: FFmpegInfo, fmt: ExportFormat, quality: str, hardware: bool,
                       size: tuple, fps: float, ten_bit: bool = False) -> list:
    w, h = size
    key = "mp4_h264" if fmt.kind == "compare" else fmt.key
    if key == "mp4_h264":
        if (hardware or not ff.has_encoder("libx264")) and ff.has_encoder("h264_videotoolbox"):
            return ["-c:v", "h264_videotoolbox", "-b:v", _hw_bitrate(quality, w, h, fps),
                    "-profile:v", "high", "-pix_fmt", "yuv420p"]
        if ff.has_encoder("libx264"):
            return ["-c:v", "libx264", "-preset", "slow" if quality == "high" else "medium",
                    "-crf", str(_CRF["libx264"][quality]), "-profile:v", "high", "-pix_fmt", "yuv420p"]
        if ff.has_encoder("libopenh264"):
            return ["-c:v", "libopenh264", "-b:v", _hw_bitrate(quality, w, h, fps), "-pix_fmt", "yuv420p"]
        raise ExportError("Dieses ffmpeg kann kein H.264 schreiben.")
    if key == "mp4_hevc":
        if (hardware or not ff.has_encoder("libx265")) and ff.has_encoder("hevc_videotoolbox"):
            return ["-c:v", "hevc_videotoolbox", "-b:v", _hw_bitrate(quality, w, h, fps, 0.65),
                    "-tag:v", "hvc1", "-pix_fmt", "p010le" if ten_bit else "yuv420p"]
        if ff.has_encoder("libx265"):
            return ["-c:v", "libx265", "-preset", "medium", "-crf", str(_CRF["libx265"][quality]),
                    "-tag:v", "hvc1", "-pix_fmt", "yuv420p10le" if ten_bit else "yuv420p",
                    "-x265-params", "log-level=error"]
        raise ExportError("Dieses ffmpeg kann kein H.265 schreiben.")
    if key == "mov_prores":
        if not ff.has_encoder("prores_ks"):
            raise ExportError("Dieses ffmpeg kann kein ProRes schreiben.")
        profile = {"high": "3", "medium": "2", "small": "1"}[quality]
        return ["-c:v", "prores_ks", "-profile:v", profile, "-vendor", "apl0", "-pix_fmt", "yuv422p10le"]
    if key == "mkv_ffv1":
        return ["-c:v", "ffv1", "-level", "3", "-g", "1", "-slicecrc", "1"]
    if key == "webm_vp9":
        if not ff.has_encoder("libvpx-vp9"):
            raise ExportError("Dieses ffmpeg kann kein VP9 schreiben.")
        speed = {"high": "2", "medium": "3", "small": "4"}[quality]
        return ["-c:v", "libvpx-vp9", "-crf", str(_CRF["libvpx-vp9"][quality]), "-b:v", "0",
                "-row-mt", "1", "-deadline", "good", "-cpu-used", speed, "-pix_fmt", "yuv420p"]
    raise ExportError(f"Unbekanntes Format: {fmt.key}")


def audio_codec_for(ff: FFmpegInfo, fmt: ExportFormat) -> str:
    codec = fmt.audio_codec
    if codec == "libopus" and not ff.has_encoder("libopus"):
        return "libvorbis" if ff.has_encoder("libvorbis") else "opus"
    if codec == "libmp3lame" and not ff.has_encoder("libmp3lame"):
        raise ExportError("Dieses ffmpeg kann kein MP3 schreiben (libmp3lame fehlt).")
    return codec


def audio_encoder_args(ff: FFmpegInfo, fmt: ExportFormat, quality: str) -> list:
    codec = audio_codec_for(ff, fmt)
    if codec == "aac":
        return ["-c:a", "aac", "-b:a", {"high": "256k", "medium": "192k", "small": "128k"}[quality]]
    if codec in ("libopus", "opus"):
        args = ["-c:a", codec, "-b:a", {"high": "160k", "medium": "128k", "small": "96k"}[quality]]
        return args + (["-strict", "-2"] if codec == "opus" else [])
    if codec == "libvorbis":
        return ["-c:a", "libvorbis", "-q:a", {"high": "7", "medium": "5", "small": "3"}[quality]]
    if codec == "libmp3lame":
        return ["-c:a", "libmp3lame", "-q:a", {"high": "0", "medium": "2", "small": "5"}[quality]]
    return ["-c:a", codec]


def container_args(fmt: ExportFormat) -> list:
    if fmt.ext in (".mp4", ".mov", ".m4a"):
        return ["-movflags", "+faststart"]
    return []


def output_path(input_path: str, fmt: ExportFormat, folder: str = "", suffix: str = "_klarbild") -> str:
    """Zielpfad neben dem Original (oder im gewählten Ordner); vorhandene Dateien werden nie überschrieben."""
    stem = os.path.splitext(os.path.basename(input_path))[0]
    if fmt.kind == "compare":
        suffix = "_vergleich"
    directory = folder or os.path.dirname(os.path.abspath(input_path))
    candidate = os.path.join(directory, f"{stem}{suffix}{fmt.ext}")
    n = 2
    while os.path.exists(candidate) or os.path.abspath(candidate) == os.path.abspath(input_path):
        candidate = os.path.join(directory, f"{stem}{suffix}-{n}{fmt.ext}")
        n += 1
    return candidate
