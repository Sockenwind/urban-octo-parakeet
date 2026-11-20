"""Testmaterial wird komplett mit ffmpeg erzeugt – keine externen Dateien nötig."""
import os
import subprocess

import pytest

from klarbild.ffmpeg_tools import detect_ffmpeg, probe


def _ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


@pytest.fixture(scope="session")
def ff():
    return detect_ffmpeg()


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("media")
    still = str(d / "still.png")
    # Standbild mit viel Struktur als „Motiv“
    _ff("-f", "lavfi", "-i", "mandelbrot=size=480x360:start_scale=1.5", "-frames:v", "1", still)
    hum_noise = ("aevalsrc=0.25*sin(2*PI*440*t)*gt(mod(t\\,1)\\,0.5)+0.05*sin(2*PI*50*t)"
                 "+0.03*sin(2*PI*100*t)+0.02*sin(2*PI*150*t):s=48000")
    # verwackelt + verrauscht + Ton mit Brummen und Rauschen
    _ff("-loop", "1", "-framerate", "25", "-i", still,
        "-f", "lavfi", "-i", hum_noise, "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.03:r=48000:seed=42",
        "-filter_complex",
        "[0:v]crop=320:240:'80+40*sin(t*0.5)+5*sin(t*23)+3*sin(t*37)':'60+4*cos(t*19)+3*sin(t*41)',"
        "noise=alls=20:allf=t:all_seed=7,format=yuv420p[v];[1:a][2:a]amix=inputs=2:normalize=0[a]",
        "-map", "[v]", "-map", "[a]", "-t", "4", "-c:v", "ffv1", "-c:a", "pcm_s16le", str(d / "shaky.mkv"))
    # ruhig und sauber
    _ff("-loop", "1", "-framerate", "25", "-i", still, "-t", "3",
        "-vf", "crop=320:240:80:60,format=yuv420p", "-c:v", "ffv1", str(d / "calm.mkv"))
    # nur Ton
    _ff("-f", "lavfi", "-i", hum_noise, "-t", "5", "-ac", "2", "-c:a", "pcm_s16le", str(d / "audio.wav"))
    # Zeilensprung: echte Halbbilder aus 50p-Material
    _ff("-f", "lavfi", "-i", "testsrc2=size=320x240:rate=50", "-t", "3",
        "-vf", "tinterlace=mode=interleave_top,setfield=tff", "-flags", "+ilme+ildct",
        "-c:v", "libx264", "-crf", "16", str(d / "interlaced.mp4"))
    return d


@pytest.fixture(scope="session")
def shaky(ff, media_dir):
    return probe(ff, os.path.join(media_dir, "shaky.mkv"))


@pytest.fixture(scope="session")
def calm(ff, media_dir):
    return probe(ff, os.path.join(media_dir, "calm.mkv"))


@pytest.fixture(scope="session")
def audio_only(ff, media_dir):
    return probe(ff, os.path.join(media_dir, "audio.wav"))


@pytest.fixture(scope="session")
def interlaced(ff, media_dir):
    return probe(ff, os.path.join(media_dir, "interlaced.mp4"))
