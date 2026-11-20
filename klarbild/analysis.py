"""Automatische Analyse von Bild und Ton – liefert Messwerte und Einstellungs-Empfehlungen."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from .audio_filters import loudnorm_measure_filter, parse_loudnorm
from .ffmpeg_tools import CancelToken, FFmpegError, FFmpegInfo, MediaInfo, run_capture, run_log
from .settings import JobSettings, VideoSettings
from .video_filters import deinterlace_filter

ProgressFn = Callable[[float, str], None]


# --------------------------------------------------------------------------- Rohdaten lesen

def read_gray_frames(ff: FFmpegInfo, path: str, vf: str, width: int, height: int,
                     start: float = 0.0, max_frames: int = 1, duration: Optional[float] = None) -> np.ndarray:
    args = ["-ss", f"{start:.3f}"] if start > 0 else []
    if duration:
        args += ["-t", f"{duration:.3f}"]
    args += ["-i", path, "-map", "0:v:0", "-an", "-vf", vf, "-frames:v", str(max_frames),
             "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = run_capture(ff, args)
    n = len(raw) // (width * height)
    return np.frombuffer(raw[: n * width * height], dtype=np.uint8).reshape(n, height, width)


def read_pcm(ff: FFmpegInfo, path: str, rate: Optional[int], start: float = 0.0,
             duration: Optional[float] = None, mono: bool = True) -> np.ndarray:
    args = ["-ss", f"{start:.3f}"] if start > 0 else []
    if duration:
        args += ["-t", f"{duration:.3f}"]
    args += ["-i", path, "-map", "0:a:0", "-vn"]
    if mono:
        args += ["-ac", "1"]
    if rate:
        args += ["-ar", str(rate)]
    args += ["-f", "f32le", "-"]
    return np.frombuffer(run_capture(ff, args), dtype="<f4")


def _audio_segments(duration: float) -> list:
    """Kurze Dateien komplett, lange in drei Ausschnitten à 60 s."""
    if duration <= 240:
        return [(0.0, None)]
    return [(duration * p, 60.0) for p in (0.1, 0.45, 0.8)]


# --------------------------------------------------------------------------- Bild

def noise_sigma(frame: np.ndarray, block: int = 16) -> float:
    """Rauschschätzung auf zwei Skalen: volle Auflösung (feines Korn) und halbe Auflösung (grobes,
    „fleckiges“ Rauschen, z. B. bei hochskaliertem SD-Material). Weißes Rauschen halbiert sich beim
    Verkleinern, korreliertes nicht. Grobes Rauschen wird mit 1,4 gewichtet, weil es stärkeres
    Entrauschen braucht (gemessen an hochskaliertem, verrauschtem Foreman-Material)."""
    img = frame.astype(np.float32)
    h, w = (img.shape[0] // 2) * 2, (img.shape[1] // 2) * 2
    half = img[:h, :w].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
    return max(_immerkaer(img, block), 1.4 * _immerkaer(half, block))


def _immerkaer(img: np.ndarray, block: int) -> float:
    """Rauschschätzung nach Immerkær (1996), blockweise; flache Bereiche (30. Perzentil) zählen."""
    c = (img[:-2, :-2] - 2 * img[:-2, 1:-1] + img[:-2, 2:]
         - 2 * img[1:-1, :-2] + 4 * img[1:-1, 1:-1] - 2 * img[1:-1, 2:]
         + img[2:, :-2] - 2 * img[2:, 1:-1] + img[2:, 2:])
    h, w = (c.shape[0] // block) * block, (c.shape[1] // block) * block
    if h == 0 or w == 0:
        return float(math.sqrt(math.pi / 2) / 6 * np.mean(np.abs(c)))
    blocks = np.abs(c[:h, :w]).reshape(h // block, block, w // block, block).mean(axis=(1, 3))
    return float(math.sqrt(math.pi / 2) / 6 * np.percentile(blocks, 30))


def _phase_shift(a: np.ndarray, b: np.ndarray, window: np.ndarray) -> tuple:
    fa = np.fft.fft2((a - a.mean()) * window)
    fb = np.fft.fft2((b - b.mean()) * window)
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-9
    corr = np.fft.ifft2(r).real
    h, w = corr.shape
    y, x = np.unravel_index(int(np.argmax(corr)), corr.shape)
    peak = corr[y, x]

    def refine(m1: float, c0: float, p1: float) -> float:
        d = m1 - 2 * c0 + p1
        return 0.0 if abs(d) < 1e-12 else 0.5 * (m1 - p1) / d

    dx = x + refine(corr[y, (x - 1) % w], peak, corr[y, (x + 1) % w])
    dy = y + refine(corr[(y - 1) % h, x], peak, corr[(y + 1) % h, x])
    if dx > w / 2:
        dx -= w
    if dy > h / 2:
        dy -= h
    return dx, dy, float(peak)


def shake_from_frames(frames: np.ndarray, fps: float) -> Optional[float]:
    """Hochfrequentes Zittern der Kamerabahn als RMS in Prozent der Bildgröße."""
    if len(frames) < 8:
        return None
    n, h, w = frames.shape
    window = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    steps = []
    f = frames.astype(np.float32)
    for i in range(n - 1):
        dx, dy, peak = _phase_shift(f[i], f[i + 1], window)
        if peak < 0.04 or abs(dx) > w / 4 or abs(dy) > h / 4:   # Schnitt oder unzuverlässig
            dx = dy = 0.0
        steps.append((dx / w * 100, dy / h * 100))
    path = np.cumsum(np.array(steps), axis=0)
    k = max(5, int(round((fps or 25) * 0.5)) | 1)
    pad = k // 2
    padded = np.pad(path, ((pad, pad), (0, 0)), mode="edge")
    kernel = np.ones(k) / k
    smooth = np.stack([np.convolve(padded[:, j], kernel, mode="valid") for j in range(2)], axis=1)
    jitter = path - smooth
    return float(np.sqrt(np.mean(np.sum(jitter ** 2, axis=1))))


def detect_interlace(ff: FFmpegInfo, media: MediaInfo) -> tuple:
    start = media.duration * 0.3 if media.duration > 20 else 0.0
    log = run_log(ff, ["-ss", f"{start:.2f}", "-i", media.path, "-map", "0:v:0", "-an",
                       "-vf", "idet", "-frames:v", "400", "-f", "null", "-"])
    m = re.findall(r"Multi frame detection:\s*TFF:\s*(\d+)\s*BFF:\s*(\d+)\s*Progressive:\s*(\d+)\s*Undetermined:\s*(\d+)", log)
    if not m:
        return media.interlaced_flag, None
    tff, bff, prog, und = map(int, m[-1])
    inter = tff + bff
    if inter + prog < 20:                       # kaum Bewegung – Kennzeichnung der Datei vertrauen
        return media.interlaced_flag, (tff, bff, prog, und)
    return inter >= 0.5 * (inter + prog), (tff, bff, prog, und)


# --------------------------------------------------------------------------- Ton

def hum_score(signal: np.ndarray, rate: int, base: int) -> float:
    n = 16384 if len(signal) >= 16384 else 1 << max(10, int(math.log2(max(len(signal), 1024))))
    if len(signal) < n:
        return 0.0
    win = np.hanning(n)
    hop = n // 2
    spec = np.zeros(n // 2 + 1)
    count = 0
    for i in range(0, len(signal) - n + 1, hop):
        spec += np.abs(np.fft.rfft(signal[i:i + n] * win)) ** 2
        count += 1
    spec /= max(count, 1)
    freqs = np.fft.rfftfreq(n, 1 / rate)
    ratios = []
    for k in range(1, 5):
        f0 = base * k
        peak = spec[(freqs >= f0 - 1.2) & (freqs <= f0 + 1.2)]
        side = spec[((freqs >= f0 - 9) & (freqs <= f0 - 3)) | ((freqs >= f0 + 3) & (freqs <= f0 + 9))]
        if len(peak) and len(side):
            ratios.append(10 * math.log10((peak.max() + 1e-20) / (np.median(side) + 1e-20)))
    ratios.sort(reverse=True)
    return float(np.mean(ratios[:2])) if ratios else 0.0


def level_stats(signal: np.ndarray, rate: int) -> tuple:
    frame = int(rate * 0.05)
    n = len(signal) // frame
    if n < 10:
        return None, None
    rms = np.sqrt(np.mean(signal[: n * frame].reshape(n, frame).astype(np.float64) ** 2, axis=1))
    db = 20 * np.log10(rms + 1e-12)
    if np.mean(db < -90) > 0.05:                 # echte digitale Stille vorhanden = kein analoges Grundrauschen
        voiced = db[db > -90]
        return -90.0, (float(np.percentile(voiced, 95)) + 90.0) if len(voiced) else None
    db = db[db > -100]
    if len(db) < 10:
        return None, None
    floor = float(np.percentile(db, 10))
    return floor, float(np.percentile(db, 95)) - floor


def clip_ratio(samples: np.ndarray, channels: int) -> float:
    channels = max(1, channels)
    usable = len(samples) // channels * channels
    if usable == 0:
        return 0.0
    x = np.abs(samples[:usable].reshape(-1, channels))
    hot = x >= 0.98
    runs = hot[2:] & hot[1:-1] & hot[:-2]        # mind. 3 Samples am Anschlag = Übersteuerung
    return float(runs.sum()) / float(x.size)


# --------------------------------------------------------------------------- Ergebnis

@dataclass
class Analysis:
    interlaced: Optional[bool] = None
    idet: Optional[tuple] = None
    noise: Optional[float] = None       # geschätzte Rausch-Standardabweichung (0..255)
    shake: Optional[float] = None       # Zittern in % der Bildgröße
    loudness: Optional[float] = None    # LUFS
    true_peak: Optional[float] = None
    noise_floor: Optional[float] = None  # dBFS
    snr: Optional[float] = None         # dB
    hum_hz: Optional[int] = None
    hum_db: Optional[float] = None
    clipping: Optional[float] = None    # Anteil übersteuerter Samples

    # Bewertung für die Anzeige: (Beschriftung, Wert, Stufe "ok" | "warn" | "bad")
    def video_rows(self) -> list:
        rows = []
        if self.noise is not None:
            lvl = "ok" if self.noise < 2.8 else "warn" if self.noise < 7 else "bad"
            word = {"ok": "gering", "warn": "mittel", "bad": "stark"}[lvl]
            rows.append(("Bildrauschen", f"{word} (σ {self.noise:.1f})".replace(".", ","), lvl))
        if self.shake is not None:
            lvl = "ok" if self.shake < 0.2 else "warn" if self.shake < 0.8 else "bad"
            word = {"ok": "ruhig", "warn": "leicht verwackelt", "bad": "stark verwackelt"}[lvl]
            rows.append(("Verwacklung", word, lvl))
        if self.interlaced is not None:
            rows.append(("Zeilensprung", "ja – wird entfernt" if self.interlaced else "nein", "warn" if self.interlaced else "ok"))
        return rows

    def audio_rows(self) -> list:
        rows = []
        if self.loudness is not None:
            lvl = "ok" if -20 <= self.loudness <= -12 else "warn"
            rows.append(("Lautheit", f"{self.loudness:.1f} LUFS".replace(".", ",").replace("-", "−"), lvl))
        if self.noise_floor is not None:
            lvl = "ok" if (self.snr or 99) >= 40 else "warn" if (self.snr or 0) >= 25 else "bad"
            rows.append(("Grundrauschen", f"{self.noise_floor:.0f} dB · Abstand {self.snr:.0f} dB".replace("-", "−"), lvl))
        if self.hum_hz:
            rows.append(("Brummen", f"{self.hum_hz} Hz erkannt", "bad"))
        elif self.hum_db is not None:
            rows.append(("Brummen", "keins", "ok"))
        if self.clipping is not None:
            bad = self.clipping > 1e-4
            rows.append(("Übersteuerung", f"{self.clipping * 100:.2f} % der Samples".replace(".", ",") if bad else "keine", "bad" if bad else "ok"))
        return rows


def suggest_denoise_strength(sigma: float) -> int:
    # Abgestimmt an Foreman mit künstlichem Rauschen: geschätztes σ 5 / 9,7 / 15,4 hatte sein
    # PSNR-Optimum bei fftdnoiz-Sigma 6 / 24 / ≥38. Leicht darunter gewählt, damit nichts „plastisch“ wirkt.
    return int(round(min(85, max(10, (sigma - 2.5) * 7.5))))


def suggest_stab_strength(shake: float) -> int:
    # Testclips: ruhig 0,01 · Schwenk 0,10 · leichtes Zittern 0,7 · starkes Zittern 1,9
    return int(round(min(85, max(30, 30 + shake * 20))))


def apply_suggestions(an: Analysis, settings: JobSettings) -> list:
    """Übernimmt Empfehlungen in die Einstellungen und liefert erklärende Sätze."""
    v, a = settings.video, settings.audio
    msgs = []
    if an.noise is not None:
        if an.noise < 2.8:
            v.denoise_enabled = False
            msgs.append("Bild ist kaum verrauscht – Entrauschen aus.")
        else:
            v.denoise_enabled = True
            v.denoise_strength = suggest_denoise_strength(an.noise)
            msgs.append(f"Entrauschen auf {v.denoise_strength} % gesetzt.")
    if an.shake is not None:
        if an.shake < 0.2:
            v.stabilize_enabled = False
            msgs.append("Bild ist ruhig – Stabilisieren aus.")
        else:
            v.stabilize_enabled = True
            v.stabilize_strength = suggest_stab_strength(an.shake)
            msgs.append(f"Stabilisieren auf {v.stabilize_strength} % gesetzt.")
    if an.interlaced:
        msgs.append("Zeilensprung erkannt – wird automatisch entfernt.")
    if an.hum_hz:
        a.hum = str(an.hum_hz)
        msgs.append(f"Brummen bei {an.hum_hz} Hz wird herausgefiltert.")
    if an.snr is not None:
        snr = an.snr
        a.denoise = 70 if snr < 15 else 50 if snr < 25 else 35 if snr < 35 else 20 if snr < 45 else 0
        msgs.append(f"Ton-Rauschminderung auf {a.denoise} % gesetzt." if a.denoise else "Ton ist sauber – keine Rauschminderung.")
    if an.noise_floor is not None:
        a.noise_floor_db = round(an.noise_floor, 1)
    if an.clipping is not None and an.clipping > 1e-4:
        a.declip = True
        msgs.append("Übersteuerte Stellen werden repariert.")
    if an.loudness is not None:
        a.normalize = True
        if abs(an.loudness - float(a.target)) > 1:
            msgs.append(f"Lautheit wird von {round(an.loudness)} auf {a.target} LUFS gebracht.".replace("-", "−"))
        else:
            msgs.append("Lautheit passt bereits.")
    return msgs


# --------------------------------------------------------------------------- Ablauf

def analyze(ff: FFmpegInfo, media: MediaInfo, on_progress: Optional[ProgressFn] = None,
            cancel: Optional[CancelToken] = None) -> Analysis:
    an = Analysis()

    def step(frac: float, text: str) -> None:
        if cancel:
            cancel.check()
        if on_progress:
            on_progress(frac, text)

    if media.has_video and media.width and media.height:
        step(0.02, "Zeilensprung prüfen …")
        try:
            an.interlaced, an.idet = detect_interlace(ff, media)
        except FFmpegError:
            an.interlaced = media.interlaced_flag
        deint = deinterlace_filter(ff, VideoSettings()) + "," if an.interlaced else ""

        step(0.15, "Bildrauschen messen …")
        cw, ch = min(media.width, 512), min(media.height, 384)
        sigmas = []
        positions = [media.duration * p for p in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.85)] if media.duration > 2 else [0.0]
        for i, pos in enumerate(positions):
            step(0.15 + 0.3 * i / len(positions), "Bildrauschen messen …")
            try:
                fr = read_gray_frames(ff, media.path, f"{deint}crop={cw}:{ch},format=gray", cw, ch, start=pos)
            except FFmpegError:
                continue
            if len(fr):
                sigmas.append(noise_sigma(fr[0]))
        if sigmas:
            an.noise = float(np.median(sigmas))

        step(0.45, "Verwacklung messen …")
        seg = min(12.0, media.duration)
        start = max(0.0, min(media.duration * 0.2, media.duration - seg))
        w, h = (144, 256) if media.is_portrait else (256, 144)
        try:
            frames = read_gray_frames(ff, media.path, f"{deint}scale={w}:{h}:flags=area,format=gray", w, h,
                                      start=start, max_frames=400, duration=seg)
            an.shake = shake_from_frames(frames, media.fps)
        except FFmpegError:
            pass

    if media.has_audio:
        step(0.6, "Lautheit messen …")
        try:
            log = run_log(ff, ["-i", media.path, "-map", "0:a:0", "-vn", "-af", loudnorm_measure_filter(-16), "-f", "null", "-"])
            ln = parse_loudnorm(log)
            if ln:
                an.loudness = float(ln["input_i"])
                an.true_peak = float(ln["input_tp"])
        except FFmpegError:
            pass

        step(0.75, "Rauschen und Brummen im Ton suchen …")
        segs = _audio_segments(media.duration)
        try:
            speech = np.concatenate([read_pcm(ff, media.path, 16000, s, d) for s, d in segs])
            an.noise_floor, an.snr = level_stats(speech, 16000)
            low = np.concatenate([read_pcm(ff, media.path, 4000, s, d) for s, d in segs])
            s50, s60 = hum_score(low, 4000, 50), hum_score(low, 4000, 60)
            an.hum_db = max(s50, s60)
            if an.hum_db >= 10:
                an.hum_hz = 50 if s50 >= s60 else 60
        except FFmpegError:
            pass

        step(0.9, "Übersteuerung prüfen …")
        try:
            raw = np.concatenate([read_pcm(ff, media.path, None, s, min(d or 120, 120), mono=False) for s, d in segs[:2]])
            an.clipping = clip_ratio(raw, media.channels)
        except FFmpegError:
            pass

    step(1.0, "Analyse fertig")
    return an
