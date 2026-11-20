"""Ende-zu-Ende: Analyse, alle Exportformate, Wirkung von Entrauschen/Stabilisieren/Tonfiltern."""
import json
import os
import subprocess
import threading

import pytest

from klarbild.analysis import analyze, apply_suggestions
from klarbild.exporters import FORMATS, USER_FORMATS, output_path
from klarbild.ffmpeg_tools import CancelToken, Cancelled, probe
from klarbild.pipeline import Job, PipelineError, run_job
from klarbild.preview import audio_preview, frame_ppm, preview_clip, thumbnail_ppm
from klarbild.settings import ExportSettings, JobSettings, VideoSettings


def streams(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)["streams"]


# --------------------------------------------------------------------------- Analyse

def test_analysis_finds_problems(ff, shaky):
    an = analyze(ff, shaky)
    assert an.noise > 4, an.noise
    assert an.shake > 0.5, an.shake
    assert an.interlaced is False
    assert an.hum_hz == 50
    assert an.loudness is not None and -30 < an.loudness < -10
    js = JobSettings()
    msgs = apply_suggestions(an, js)
    assert js.video.denoise_enabled and js.video.stabilize_enabled and js.audio.hum == "50"
    assert msgs


def test_analysis_calm_clip(ff, calm):
    an = analyze(ff, calm)
    assert an.shake < 0.2 and an.noise < 2.8
    js = JobSettings()
    apply_suggestions(an, js)
    assert not js.video.stabilize_enabled and not js.video.denoise_enabled


def test_interlace_detection(ff, interlaced):
    an = analyze(ff, interlaced)
    assert an.interlaced is True


def test_audio_only_analysis(ff, audio_only):
    an = analyze(ff, audio_only)
    assert an.noise is None and an.hum_hz == 50


# --------------------------------------------------------------------------- Export

@pytest.mark.parametrize("fmt", [f.key for f in USER_FORMATS])
def test_every_format(ff, shaky, tmp_path, fmt):
    ex = ExportSettings(format=fmt, quality="small", folder=str(tmp_path))
    out = output_path(shaky.path, FORMATS[fmt], ex.folder, ex.suffix)
    seen = []
    try:
        result = run_job(ff, Job(shaky.path, out, JobSettings(), ex, shaky, duration=2.0),
                         on_progress=lambda f, t: seen.append(f))
    except PipelineError as exc:
        print(exc.log[-4000:])          # erscheint bei einem Fehlschlag im Testbericht
        raise
    assert os.path.getsize(result) > 1000
    kinds = {s["codec_type"]: s for s in streams(result)}
    assert "audio" in kinds
    if FORMATS[fmt].kind == "audio":
        assert "video" not in kinds
    else:
        assert "video" in kinds
        if fmt == "compare":
            assert kinds["video"]["width"] == 2 * 320
    assert seen and seen[-1] == pytest.approx(1.0) and seen == sorted(seen)


def test_audio_fallback_format():
    from klarbild.exporters import format_for
    assert format_for("mp4_h264", False) == "audio_m4a"
    assert format_for("mov_prores", False) == "audio_wav"
    assert format_for("mkv_ffv1", False) == "audio_flac"
    assert format_for("mp4_h264", True) == "mp4_h264"
    assert format_for("audio_mp3", False) == "audio_mp3"


def test_flac_is_24_bit(ff, shaky, tmp_path):
    out = str(tmp_path / "ton.flac")
    run_job(ff, Job(shaky.path, out, JobSettings(), ExportSettings(format="audio_flac"), shaky, duration=1.0))
    info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=bits_per_raw_sample,sample_fmt",
                           "-of", "json", out], capture_output=True, text=True, check=True).stdout
    assert json.loads(info)["streams"][0]["bits_per_raw_sample"] == "24"


def test_error_summary_names_the_cause():
    from klarbild.ffmpeg_tools import _summarize
    log = ("Input #0 ...\n[flac @ 0x1] encoding as 32 bits-per-sample is experimental\n"
           "[af#0:0 @ 0x2] Terminating thread with return code -22 (Invalid argument)\nConversion failed!\n")
    assert _summarize(log).startswith("[flac @ 0x1] encoding as 32")


def test_output_names_never_overwrite(tmp_path):
    src = tmp_path / "film.mp4"
    src.write_bytes(b"x")
    first = output_path(str(src), FORMATS["mp4_h264"])
    open(first, "w").close()
    second = output_path(str(src), FORMATS["mp4_h264"])
    assert first.endswith("film_klarbild.mp4") and second.endswith("film_klarbild-2.mp4")
    assert output_path(str(src), FORMATS["compare"]).endswith("film_vergleich.mp4")


def test_denoise_and_stabilize_work(ff, shaky, tmp_path):
    out = str(tmp_path / "fixed.mkv")
    js = JobSettings()
    js.video = VideoSettings(denoise_strength=60, stabilize_strength=60, sharpen=0)
    run_job(ff, Job(shaky.path, out, js, ExportSettings(format="mkv_ffv1"), shaky))
    before, after = analyze(ff, shaky), analyze(ff, probe(ff, out))
    assert after.noise < before.noise * 0.6, (before.noise, after.noise)
    assert after.shake < before.shake * 0.5, (before.shake, after.shake)
    assert after.hum_hz == 50                                 # ohne Kerbfilter bleibt das Brummen …
    js.audio.hum = "50"
    out2 = str(tmp_path / "fixed2.wav")
    run_job(ff, Job(shaky.path, out2, js, ExportSettings(format="audio_wav"), shaky))
    fixed = analyze(ff, probe(ff, out2))
    assert fixed.hum_hz is None and fixed.hum_db < 10          # … mit Kerbfilter unter der Erkennungsschwelle
    assert abs(fixed.loudness - (-16)) < 1.0                   # Lautheit genau auf Ziel


def test_audio_only_file(ff, audio_only, tmp_path):
    out = str(tmp_path / "a.flac")
    run_job(ff, Job(audio_only.path, out, JobSettings(), ExportSettings(format="audio_flac"), audio_only))
    assert streams(out)[0]["codec_name"] == "flac"
    with pytest.raises(PipelineError):
        run_job(ff, Job(audio_only.path, str(tmp_path / "v.mp4"), JobSettings(), ExportSettings(), audio_only))


def test_mute_removes_audio(ff, shaky, tmp_path):
    js = JobSettings()
    js.audio.mute = True
    js.video.stabilize_enabled = False
    out = str(tmp_path / "stumm.mp4")
    run_job(ff, Job(shaky.path, out, js, ExportSettings(), shaky, duration=1.0))
    assert [s["codec_type"] for s in streams(out)] == ["video"]


def test_cancel_removes_partial_file(ff, shaky, tmp_path):
    out = str(tmp_path / "abbruch.mp4")
    token = CancelToken()
    js = JobSettings()
    js.video.denoise_method = "max"
    started = threading.Event()

    def progress(f, _t):
        started.set()
        if f > 0.05:
            token.cancel()

    with pytest.raises(Cancelled):
        run_job(ff, Job(shaky.path, out, js, ExportSettings(), shaky), on_progress=progress, cancel=token)
    assert started.is_set() and not os.path.exists(out)


# --------------------------------------------------------------------------- Vorschau

def test_preview_helpers(ff, shaky, tmp_path):
    raw = frame_ppm(ff, shaky, 1.5, "fftdnoiz=sigma=10")
    assert raw.startswith(b"P6")
    assert thumbnail_ppm(ff, shaky).startswith(b"P6")
    assert frame_ppm(ff, shaky, 999).startswith(b"P6")        # hinter dem Ende → letztes Bild
    before, after = audio_preview(ff, JobSettings(), shaky, None, 1.0, str(tmp_path), duration=2.0)
    assert os.path.getsize(before) > 1000 and os.path.getsize(after) > 1000
    clip = preview_clip(ff, JobSettings(), shaky, None, 0.5, str(tmp_path), duration=2.0)
    assert streams(clip)[0]["width"] == 640
