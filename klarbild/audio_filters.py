"""Tonverbesserung: Filterketten für ffmpeg (Brummen, Rumpeln, Rauschen, Knackser, Sprache, Lautheit)."""
from __future__ import annotations

import json
import math
from typing import Optional

from .ffmpeg_tools import FFmpegInfo
from .settings import AudioSettings

TRUE_PEAK = -1.5


def _s(value: float) -> float:
    return max(0.0, min(100.0, float(value))) / 100.0


def hum_filters(base_hz: int) -> list:
    """Schmale Kerbfilter auf der Netzfrequenz und ihren ersten Obertönen."""
    qs = (12, 16, 20, 24, 28)
    return [f"bandreject=f={base_hz * k}:width_type=q:width={q}" for k, q in zip(range(1, 6), qs)]


def denoise_filter(a: AudioSettings) -> Optional[str]:
    s = _s(a.denoise)
    if s <= 0:
        return None
    nr = 6 + 24 * s                      # Absenkung in dB
    nf = -50.0 if a.noise_floor_db is None else max(-80.0, min(-20.0, a.noise_floor_db))
    return f"afftdn=nr={nr:.1f}:nf={nf:.0f}:tn=1:gs=8"


def compressor_filter(a: AudioSettings) -> Optional[str]:
    s = _s(a.compress)
    if s <= 0:
        return None
    ratio = 1.5 + 6.5 * s
    threshold = 10 ** ((-14 - 16 * s) / 20)  # −14 … −30 dBFS, linear angegeben
    return f"acompressor=threshold={threshold:.5f}:ratio={ratio:.2f}:attack=15:release=250:knee=4"


def audio_chain(ff: FFmpegInfo, a: AudioSettings) -> list:
    """Filterkette ohne Lautheits-Normalisierung (die braucht zwei Durchläufe, siehe unten)."""
    if not a.enabled or a.mute:
        return []
    chain: list = []
    if a.declip and ff.has_filter("adeclip"):
        chain.append("adeclip")
    if a.declick and ff.has_filter("adeclick"):
        chain.append("adeclick")
    if a.hum in ("50", "60"):
        chain += hum_filters(int(a.hum))
    if a.highpass or a.voice:
        chain.append(f"highpass=f={100 if a.voice else 75}:poles=2")
    dn = denoise_filter(a)
    if dn and ff.has_filter("afftdn"):
        chain.append(dn)
    if a.voice:
        chain += ["equalizer=f=250:t=q:w=1.2:g=-2", "equalizer=f=3200:t=q:w=1.0:g=3"]
        if ff.has_filter("deesser"):
            chain.append("deesser=i=0.35")
    comp = compressor_filter(a)
    if comp:
        chain.append(comp)
    return chain


def loudnorm_measure_filter(target: float) -> str:
    return f"loudnorm=I={target:g}:TP={TRUE_PEAK}:LRA=11:print_format=json"


def loudnorm_apply_filter(target: float, measured: dict, sample_rate: int) -> str:
    lra = max(11.0, min(50.0, float(measured["input_lra"]) + 1.0))
    return (
        f"loudnorm=I={target:g}:TP={TRUE_PEAK}:LRA={lra:.1f}"
        f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
        f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
        f":offset={measured['target_offset']}:linear=true"
        f",aresample={sample_rate}"
    )


def parse_loudnorm(log: str) -> Optional[dict]:
    """Liest das JSON, das loudnorm am Ende ins Protokoll schreibt. None bei Stille/Fehler."""
    end = log.rfind("}")
    start = log.rfind("{", 0, end)
    if start < 0 or end < 0:
        return None
    try:
        data = json.loads(log[start:end + 1])
        if not all(math.isfinite(float(data[k])) for k in ("input_i", "input_tp", "input_lra", "input_thresh")):
            return None
        return data
    except (ValueError, KeyError):
        return None


def finish_chain(chain: list) -> list:
    """loudnorm gibt seinen Puffer (mehrere Sekunden) als einen einzigen Block weiter. Ab ffmpeg 8
    reicht ffmpeg solche Blöcke unverändert an den Encoder – FLAC erlaubt aber höchstens 65 535
    Samples pro Block. Deshalb am Ende in handliche Blöcke aufteilen."""
    return chain + ["asetnsamples=n=4096:p=0"] if chain else chain


def output_sample_rate(source_rate: int, codec: str) -> int:
    if codec in ("libopus", "opus"):
        return 48000
    return source_rate if source_rate in (44100, 48000, 96000) else 48000
