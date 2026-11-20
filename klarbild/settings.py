"""Einstellungen für Bild, Ton und Export – reine Daten, ohne GUI-Abhängigkeit."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, replace

# Auswahl-Listen: interner Schlüssel -> Beschriftung in der Oberfläche
DENOISE_METHODS = {
    "fast": "Schnell",
    "balanced": "Ausgewogen",
    "max": "Maximal",
}
STAB_MODES = {
    "smooth": "Bewegung glätten",
    "tripod": "Stativ (Kamera soll stillstehen)",
}
STAB_BORDERS = {
    "zoom": "Automatisch zoomen (keine Ränder)",
    "fill": "Ränder mit Bildinhalt füllen",
    "black": "Schwarze Ränder",
}
DEINTERLACE = {
    "auto": "Automatisch",
    "on": "Immer",
    "off": "Aus",
}
RESOLUTIONS = {
    "original": "Original",
    "2160": "4K (2160p)",
    "1080": "Full HD (1080p)",
    "720": "HD (720p)",
    "480": "SD (480p)",
}
HUM = {
    "off": "Aus",
    "50": "50 Hz (Europa)",
    "60": "60 Hz (Amerika)",
}
LOUDNESS_TARGETS = {
    "-14": "Web & YouTube (−14 LUFS)",
    "-16": "Sprache & Podcast (−16 LUFS)",
    "-23": "TV-Norm EBU R128 (−23 LUFS)",
}
QUALITY = {
    "high": "Hoch",
    "medium": "Mittel",
    "small": "Klein",
}


class _Serializable:
    def to_dict(self) -> dict:
        return asdict(self)  # type: ignore[arg-type]

    @classmethod
    def from_dict(cls, data: dict | None):
        names = {f.name for f in fields(cls)}  # type: ignore[arg-type]
        return cls(**{k: v for k, v in (data or {}).items() if k in names})

    def copy(self):
        return replace(self)  # type: ignore[type-var]


@dataclass
class VideoSettings(_Serializable):
    deinterlace: str = "auto"
    deinterlace_double_rate: bool = False
    denoise_enabled: bool = True
    denoise_method: str = "balanced"
    denoise_strength: int = 40          # 0..100
    deblock: bool = False
    stabilize_enabled: bool = True
    stabilize_strength: int = 50        # 0..100
    stabilize_mode: str = "smooth"
    stabilize_border: str = "zoom"
    sharpen: int = 25                   # 0..100
    brightness: int = 0                 # -100..100
    contrast: int = 0                   # -100..100
    saturation: int = 0                 # -100..100
    resolution: str = "original"


@dataclass
class AudioSettings(_Serializable):
    enabled: bool = True
    mute: bool = False
    hum: str = "off"
    highpass: bool = True
    denoise: int = 35                   # 0..100
    declick: bool = False
    declip: bool = False
    voice: bool = False
    compress: int = 0                   # 0..100
    normalize: bool = True
    target: str = "-16"
    noise_floor_db: float | None = None  # aus der Analyse; verbessert die Rauschminderung


@dataclass
class ExportSettings(_Serializable):
    format: str = "mp4_h264"
    quality: str = "high"
    hardware: bool = False
    folder: str = ""                    # leer = neben der Originaldatei
    suffix: str = "_klarbild"


@dataclass
class JobSettings(_Serializable):
    video: VideoSettings = field(default_factory=VideoSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)

    def to_dict(self) -> dict:
        return {"video": self.video.to_dict(), "audio": self.audio.to_dict()}

    @classmethod
    def from_dict(cls, data: dict | None):
        data = data or {}
        return cls(VideoSettings.from_dict(data.get("video")), AudioSettings.from_dict(data.get("audio")))

    def copy(self):
        return JobSettings(self.video.copy(), self.audio.copy())
