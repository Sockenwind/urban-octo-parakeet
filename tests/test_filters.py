"""Filterketten: richtige Filter in richtiger Reihenfolge, Ersatzfilter ohne vid.stab/fftdnoiz."""
from dataclasses import replace

from klarbild.audio_filters import audio_chain, loudnorm_apply_filter, parse_loudnorm
from klarbild.ffmpeg_tools import MediaInfo
from klarbild.settings import AudioSettings, JobSettings, VideoSettings
from klarbild.video_filters import build_video_plan, target_size

MEDIA = MediaInfo(path="x.mp4", duration=10, has_video=True, has_audio=True, width=1920, height=1080, fps=25)


def test_default_plan_order(ff):
    plan = build_video_plan(ff, VideoSettings(), MEDIA, interlaced=True)
    chain = plan.main
    assert chain.index("bwdif") < chain.index("fftdnoiz") < chain.index("vidstabtransform") < chain.index("cas")
    assert "vidstabdetect" in plan.detect and "vidstabtransform" not in plan.detect
    assert "vidstab" not in plan.preview          # Einzelbild-Vorschau ohne Stabilisierung
    assert plan.pre.startswith("bwdif")


def test_denoise_methods(ff):
    for method, needle in (("fast", "hqdn3d"), ("balanced", "fftdnoiz"), ("max", "overlap=0.75")):
        plan = build_video_plan(ff, VideoSettings(denoise_method=method, stabilize_enabled=False), MEDIA, False)
        assert needle in plan.main
        assert plan.detect is None


def test_everything_off_is_null(ff):
    vs = VideoSettings(denoise_enabled=False, stabilize_enabled=False, sharpen=0)
    plan = build_video_plan(ff, vs, MEDIA, False)
    assert plan.main == "null" and plan.preview == "null"


def test_fallbacks_without_vidstab_and_fftdnoiz(ff):
    poor = replace(ff, filters=frozenset(f for f in ff.filters if not f.startswith("vidstab") and f != "fftdnoiz"))
    plan = build_video_plan(poor, VideoSettings(), MEDIA, False)
    assert "deshake" in plan.main and "hqdn3d" in plan.main
    assert plan.detect is None
    assert len(plan.notes) == 2


FILTERS_V6 = """Filters:
  T.. = Timeline support
  .S. = Slice threading
  ..C = Command support
 ... abench            A->A       Benchmark part of a filtergraph.
 TSC fftdnoiz          V->V       Denoise frames using 3D FFT.
 ... vidstabdetect     V->V       Extract relative transformations.
 ... amix              N->A       Audio mixing.
 ... anoisesrc         |->A       Generate a noise audio signal.
"""
FILTERS_V7 = """Filters:
  T. = Timeline support
  .S = Slice threading
  A = Audio input/output
 .. abench            A->A       Benchmark part of a filtergraph.
 TS fftdnoiz          V->V       Denoise frames using 3D FFT.
 .. vidstabdetect     V->V       Extract relative transformations.
 .. amix              N->A       Audio mixing.
 .. anoisesrc         |->A       Generate a noise audio signal.
"""
ENCODERS = """Encoders:
 V..... = Video
 A..... = Audio
 ------
 V....D libx264              libx264 H.264 / AVC
 VFS... prores_ks            Apple ProRes
 A....D aac                  AAC (Advanced Audio Coding)
"""


def test_parsers_old_and_new_ffmpeg():
    from klarbild.ffmpeg_tools import _parse_encoders, _parse_filters
    expected = {"abench", "fftdnoiz", "vidstabdetect", "amix", "anoisesrc"}
    assert _parse_filters(FILTERS_V6) == expected
    assert _parse_filters(FILTERS_V7) == expected
    assert _parse_encoders(ENCODERS) == {"libx264", "prores_ks", "aac"}


def test_real_ffmpeg_detection_is_plausible(ff):
    assert len(ff.filters) > 200 and len(ff.encoders) > 50
    assert {"hqdn3d", "loudnorm", "afftdn", "scale"} <= ff.filters


def test_deshake_ranges_are_multiples_of_16():
    import re
    from klarbild.video_filters import deshake_filter
    for st in range(0, 101, 5):
        r = int(re.search(r"rx=(\d+)", deshake_filter(VideoSettings(stabilize_strength=st))).group(1))
        assert r % 16 == 0 and 16 <= r <= 64


def test_tripod_and_borders(ff):
    plan = build_video_plan(ff, VideoSettings(stabilize_mode="tripod", stabilize_border="black"), MEDIA, False)
    assert "tripod=1" in plan.detect and "tripod=1" in plan.main and "crop=black" in plan.main


def test_resolution_uses_short_side():
    portrait = replace(MEDIA, width=1080, height=1920)
    assert target_size(VideoSettings(resolution="720"), MEDIA) == (1280, 720)
    assert target_size(VideoSettings(resolution="720"), portrait) == (720, 1280)
    assert target_size(VideoSettings(), MEDIA) == (1920, 1080)


def test_audio_chain(ff):
    a = AudioSettings(hum="50", declick=True, declip=True, voice=True, compress=50, denoise=40)
    chain = audio_chain(ff, a)
    joined = ",".join(chain)
    for needle in ("adeclip", "adeclick", "bandreject=f=50", "bandreject=f=250", "highpass=f=100",
                   "afftdn", "equalizer", "deesser", "acompressor"):
        assert needle in joined
    assert audio_chain(ff, AudioSettings(enabled=False)) == []
    assert audio_chain(ff, AudioSettings(mute=True)) == []


def test_audio_chain_is_split_into_small_blocks():
    from klarbild.audio_filters import finish_chain
    assert finish_chain(["highpass=f=75"])[-1].startswith("asetnsamples=n=4096")
    assert finish_chain([]) == []


def test_loudnorm_parsing():
    log = 'blah\n[Parsed_loudnorm_0 @ 0x1]\n{\n "input_i" : "-27.5",\n "input_tp" : "-9.1",\n' \
          ' "input_lra" : "6.2",\n "input_thresh" : "-38.0",\n "target_offset" : "0.3"\n}\n'
    m = parse_loudnorm(log)
    assert m["input_i"] == "-27.5"
    f = loudnorm_apply_filter(-16, m, 48000)
    assert "measured_I=-27.5" in f and "linear=true" in f and f.endswith("aresample=48000")
    silent = log.replace('"-27.5"', '"-inf"')
    assert parse_loudnorm(silent) is None


def test_settings_roundtrip():
    js = JobSettings()
    js.video.denoise_strength = 77
    js.audio.hum = "60"
    back = JobSettings.from_dict(js.to_dict())
    assert back.video.denoise_strength == 77 and back.audio.hum == "60"
    assert JobSettings.from_dict({"video": {"unbekannt": 1}}).video.denoise_strength == 40
