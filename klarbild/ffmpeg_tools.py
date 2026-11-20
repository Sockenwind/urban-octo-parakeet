"""ffmpeg finden, Fähigkeiten prüfen, Medien untersuchen und ffmpeg mit Fortschritt ausführen.

ffmpeg wird bewusst als eigenständiges Programm aufgerufen (nicht gelinkt). Dadurch bleibt
KlarBild lizenzrechtlich unabhängig von der jeweiligen ffmpeg-Variante (LGPL/GPL).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from collections import deque
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Optional

# macOS-Apps, die aus dem Finder gestartet werden, erben den PATH der Shell nicht.
# Deshalb werden die üblichen Homebrew-Orte zusätzlich durchsucht.
PREFERRED_DIRS = [
    "/opt/homebrew/opt/ffmpeg-full/bin",
    "/usr/local/opt/ffmpeg-full/bin",
]
FALLBACK_DIRS = [
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/opt/local/bin",
    "/usr/bin",
]

_POPEN_EXTRA = {"creationflags": 0x08000000} if sys.platform == "win32" else {}

ProgressFn = Callable[[float], None]


class FFmpegNotFound(RuntimeError):
    pass


class FFmpegError(RuntimeError):
    def __init__(self, message: str, log: str = ""):
        super().__init__(message)
        self.log = log


class Cancelled(Exception):
    pass


def _exe(name: str) -> str:
    return name + ".exe" if sys.platform == "win32" else name


@dataclass(frozen=True)
class FFmpegInfo:
    ffmpeg: str
    ffprobe: str
    version: str
    filters: frozenset
    encoders: frozenset

    def has_filter(self, name: str) -> bool:
        return name in self.filters

    def has_encoder(self, name: str) -> bool:
        return name in self.encoders

    @property
    def has_vidstab(self) -> bool:
        return {"vidstabdetect", "vidstabtransform"} <= self.filters

    @property
    def has_videotoolbox(self) -> bool:
        return "h264_videotoolbox" in self.encoders


# Die Markierungsspalten ändern sich zwischen ffmpeg-Versionen (6.x: „TSC“, ab 7: „TS“).
# Deshalb nur an der Form der Zeile erkennen, nicht an der genauen Spaltenbreite.
_FLAGS = re.compile(r"[A-Z.|]{1,8}")
_IO = re.compile(r"[AVN|]*->[AVN|]*")


def _parse_filters(text: str) -> set:
    names = set()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and _FLAGS.fullmatch(parts[0]) and _IO.fullmatch(parts[2]):
            names.add(parts[1])
    return names


def _parse_encoders(text: str) -> set:
    names = set()
    for line in text.splitlines():
        parts = line.split()
        if (len(parts) >= 3 and parts[1] != "=" and parts[0][:1] in "VAS"
                and _FLAGS.fullmatch(parts[0]) and not parts[0].startswith("-")):
            names.add(parts[1])
    return names


def _run_text(cmd: list, timeout: float = 30) -> str:
    res = subprocess.run(
        cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, **_POPEN_EXTRA,
    )
    return res.stdout + res.stderr


def inspect_ffmpeg(path: str) -> FFmpegInfo:
    first = _run_text([path, "-hide_banner", "-version"]).splitlines()
    if not first or not first[0].startswith("ffmpeg version"):
        raise FFmpegNotFound(f"{path} ist kein ffmpeg")
    version = first[0].split()[2]
    filters = _parse_filters(_run_text([path, "-hide_banner", "-filters"]))
    encoders = _parse_encoders(_run_text([path, "-hide_banner", "-encoders"]))
    probe = os.path.join(os.path.dirname(path), _exe("ffprobe"))
    if not os.path.isfile(probe):
        probe = shutil.which(_exe("ffprobe")) or ""
    if not probe:
        raise FFmpegNotFound("ffprobe wurde nicht gefunden")
    return FFmpegInfo(path, probe, version, frozenset(filters), frozenset(encoders))


def _candidates(override: Optional[str]) -> list:
    found: list = []

    def add(p: Optional[str]) -> None:
        if p and p not in found and os.path.isfile(p) and os.access(p, os.X_OK):
            found.append(p)

    add(override)
    add(os.environ.get("KLARBILD_FFMPEG"))
    for base in (getattr(sys, "_MEIPASS", None), os.path.dirname(os.path.abspath(sys.argv[0] or "."))):
        if base:
            add(os.path.join(base, "bin", _exe("ffmpeg")))
    for d in PREFERRED_DIRS:
        add(os.path.join(d, "ffmpeg"))
    add(shutil.which(_exe("ffmpeg")))
    for d in FALLBACK_DIRS:
        add(os.path.join(d, "ffmpeg"))
    return found


def detect_ffmpeg(override: Optional[str] = None) -> FFmpegInfo:
    """Sucht ffmpeg. Eine vom Nutzer gewählte Datei gewinnt; sonst wird eine Variante mit vid.stab bevorzugt."""
    usable = []
    for path in _candidates(override):
        try:
            info = inspect_ffmpeg(path)
        except Exception:
            continue
        if path == override or info.has_vidstab:
            return info
        usable.append(info)
    if usable:
        return usable[0]
    raise FFmpegNotFound(
        "ffmpeg wurde nicht gefunden. Auf dem Mac: „brew install ffmpeg“ im Terminal ausführen "
        "oder in KlarBild unter „ffmpeg auswählen…“ den Pfad angeben."
    )


# --------------------------------------------------------------------------- Medien-Infos

@dataclass
class MediaInfo:
    path: str
    duration: float = 0.0
    has_video: bool = False
    has_audio: bool = False
    width: int = 0          # Anzeigegröße (Drehung berücksichtigt)
    height: int = 0
    fps: float = 0.0
    video_codec: str = ""
    pix_fmt: str = ""
    field_order: str = ""
    color_transfer: str = ""
    audio_codec: str = ""
    sample_rate: int = 0
    channels: int = 0

    @property
    def is_hdr(self) -> bool:
        return self.color_transfer in ("smpte2084", "arib-std-b67")

    @property
    def interlaced_flag(self) -> bool:
        return self.field_order in ("tt", "bb", "tb", "bt")

    @property
    def is_portrait(self) -> bool:
        return self.height > self.width

    def summary(self) -> str:
        parts = []
        if self.has_video:
            parts.append(f"{self.width}×{self.height}")
            if self.fps:
                parts.append(f"{self.fps:.3g} fps".replace(".", ","))
        elif self.has_audio:
            parts.append("Nur Ton")
        parts.append(format_time(self.duration))
        return " · ".join(parts)


def format_time(seconds: float) -> str:
    seconds = max(0, int(round(seconds or 0)))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _rate(text: Optional[str]) -> float:
    try:
        value = Fraction(text or "0")
        return float(value) if value > 0 else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def _rotation(stream: dict) -> int:
    for sd in stream.get("side_data_list", []) or []:
        if "rotation" in sd:
            try:
                return int(float(sd["rotation"]))
            except (TypeError, ValueError):
                pass
    try:
        return int(stream.get("tags", {}).get("rotate", 0))
    except (TypeError, ValueError):
        return 0


def probe(ff: FFmpegInfo, path: str) -> MediaInfo:
    out = subprocess.run(
        [ff.ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=60, **_POPEN_EXTRA,
    )
    if out.returncode != 0:
        raise FFmpegError(f"Datei kann nicht gelesen werden: {os.path.basename(path)}", out.stderr)
    data = json.loads(out.stdout or "{}")
    info = MediaInfo(path=path)
    try:
        info.duration = float(data.get("format", {}).get("duration") or 0)
    except ValueError:
        info.duration = 0.0
    for st in data.get("streams", []):
        kind = st.get("codec_type")
        disposition = st.get("disposition", {}) or {}
        if kind == "video" and not info.has_video and not disposition.get("attached_pic"):
            info.has_video = True
            w, h = int(st.get("width") or 0), int(st.get("height") or 0)
            if abs(_rotation(st)) % 180 == 90:
                w, h = h, w
            info.width, info.height = w, h
            info.fps = _rate(st.get("avg_frame_rate")) or _rate(st.get("r_frame_rate"))
            info.video_codec = st.get("codec_name", "")
            info.pix_fmt = st.get("pix_fmt", "")
            info.field_order = st.get("field_order", "") or ""
            info.color_transfer = st.get("color_transfer", "") or ""
            if not info.duration:
                info.duration = float(st.get("duration") or 0)
        elif kind == "audio" and not info.has_audio:
            info.has_audio = True
            info.audio_codec = st.get("codec_name", "")
            info.sample_rate = int(st.get("sample_rate") or 0)
            info.channels = int(st.get("channels") or 0)
            if not info.duration:
                info.duration = float(st.get("duration") or 0)
    if not info.has_video and not info.has_audio:
        raise FFmpegError(f"Keine Bild- oder Tonspur gefunden: {os.path.basename(path)}")
    return info


# --------------------------------------------------------------------------- Ausführen

class CancelToken:
    """Wird zwischen GUI und Hintergrundarbeit geteilt; bricht den laufenden ffmpeg-Prozess ab."""

    def __init__(self) -> None:
        self._cancelled = False
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            proc = self._proc
        if proc is not None and proc.poll() is None:
            proc.terminate()

    def attach(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._proc = proc
            cancelled = self._cancelled
        if cancelled:
            proc.terminate()

    def detach(self) -> None:
        with self._lock:
            self._proc = None

    def check(self) -> None:
        if self._cancelled:
            raise Cancelled()


_ERROR_HINT = re.compile(r"error|invalid|must|failed|cannot|unknown|not found|no such|unable", re.I)


def _summarize(log: str) -> str:
    lines = [ln.strip() for ln in log.splitlines() if ln.strip()]
    errors = [ln for ln in lines if _ERROR_HINT.search(ln)]
    return "\n".join((errors or lines)[-4:]) or "ffmpeg ist ohne Meldung fehlgeschlagen"


def run_ffmpeg(
    ff: FFmpegInfo,
    args: list,
    *,
    duration: Optional[float] = None,
    on_progress: Optional[ProgressFn] = None,
    cancel: Optional[CancelToken] = None,
    cwd: Optional[str] = None,
) -> str:
    """Führt ffmpeg aus, meldet den Fortschritt (0..1) und liefert das stderr-Protokoll."""
    if cancel:
        cancel.check()
    cmd = [ff.ffmpeg, "-hide_banner", "-nostdin", "-y", "-progress", "pipe:1", "-nostats", *args]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", cwd=cwd, **_POPEN_EXTRA,
    )
    err_lines: deque = deque(maxlen=4000)
    reader = threading.Thread(target=lambda: err_lines.extend(proc.stderr), daemon=True)
    reader.start()
    if cancel:
        cancel.attach(proc)
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            key, _, value = line.strip().partition("=")
            if key == "out_time_us" and duration and on_progress:
                try:
                    on_progress(max(0.0, min(1.0, int(value) / 1e6 / duration)))
                except ValueError:
                    pass
        proc.wait()
    finally:
        reader.join(timeout=10)
        if cancel:
            cancel.detach()
    log = "".join(err_lines)
    if cancel and cancel.cancelled:
        raise Cancelled()
    if proc.returncode != 0:
        raise FFmpegError(_summarize(log), log)
    if on_progress:
        on_progress(1.0)
    return log


def run_capture(ff: FFmpegInfo, args: list, timeout: float = 300) -> bytes:
    """Führt ffmpeg aus und liefert stdout als Bytes (z. B. Einzelbilder oder PCM-Daten)."""
    cmd = [ff.ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", *args]
    res = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, **_POPEN_EXTRA)
    if res.returncode != 0:
        log = res.stderr.decode("utf-8", "replace")
        raise FFmpegError(_summarize(log), log)
    return res.stdout


def run_log(ff: FFmpegInfo, args: list, timeout: float = 600) -> str:
    """Führt ffmpeg ohne Ausgabe-Datei aus und liefert das stderr-Protokoll (für Messungen)."""
    cmd = [ff.ffmpeg, "-hide_banner", "-nostdin", *args]
    res = subprocess.run(
        cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, **_POPEN_EXTRA,
    )
    if res.returncode != 0:
        raise FFmpegError(_summarize(res.stderr), res.stderr)
    return res.stderr
