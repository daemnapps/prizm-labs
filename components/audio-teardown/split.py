"""SPLIT — the voices lifted off the music, so every later read hears speech alone.

Demucs (Meta's open separation model, MIT licence) runs on this Mac in its own
venv, the venv named by DEMUCS_PYTHON — the same one the video chain's music naming uses.
Two tracks out: voices.mp3 and music.mp3 (everything that is not voice).

A swipe with no usable separation (Demucs missing, or it fails) falls back to
the full mix and SAYS so — `split: "mix"` on the sheet — never silently; no
music.mp3 is written then.

A stamp beside the tracks (split-source.json: the video's path, size and mtime)
says which video they came from; tracks from any other video are made again.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

DEMUCS = Path(os.environ.get("DEMUCS_PYTHON") or "/nonexistent/demucs-python")
STAMP = "split-source.json"


def _ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *map(str, args)], check=True)


def source(video):
    """What tracks are made from: the video's path, size and mtime — kept in the stamp beside them."""
    st = Path(video).stat()
    return {"video": str(Path(video).resolve()), "size": st.st_size, "mtime": st.st_mtime}


def _stamped(out_dir):
    try:
        return json.loads((out_dir / STAMP).read_text())
    except (OSError, ValueError):
        return {}


def _stamp(out_dir, src, split_done):
    (out_dir / STAMP).write_text(json.dumps(dict(src, split=split_done)) + "\n")


def mix(video, out_dir, fresh=False):
    """The full soundtrack, mono 16 kHz — what the listeners get when nothing is split.
    fresh: remake it even if one is there (it came from another video)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    a = out_dir / "mix.mp3"
    if fresh or not a.exists():
        _ff("-i", video, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", a)
    return a


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def split(video, out_dir):
    """{"voices": path, "music": path|None, "mix": path, "how": "demucs"|"mix", "why": str}
    Tracks already in out_dir are reused only when the stamp beside them names this
    video at its current size and mtime; otherwise they are made again."""
    out_dir.mkdir(parents=True, exist_ok=True)
    src, was = source(video), _stamped(out_dir)
    same = {k: was.get(k) for k in src} == src
    m = mix(video, out_dir, fresh=not same)
    voices, music = out_dir / "voices.mp3", out_dir / "music.mp3"
    if same and was.get("split") and voices.exists() and music.exists():
        return {"voices": voices, "music": music, "mix": m, "how": "demucs", "why": "already split"}
    _stamp(out_dir, src, False)                        # the mix is this video's; the split is not yet
    if not DEMUCS.exists():
        return {"voices": m, "music": None, "mix": m, "how": "mix", "why": "Demucs is not installed"}
    wav = out_dir / "stereo.wav"
    _ff("-i", video, "-vn", "-ac", "2", "-ar", "44100", wav)
    sep = out_dir / "sep"
    r = subprocess.run([str(DEMUCS), "-m", "demucs", "--two-stems", "vocals", "-o", str(sep), str(wav)],
                       capture_output=True, text=True)
    vw = next(sep.rglob("vocals.wav"), None) if sep.exists() else None
    nw = next(sep.rglob("no_vocals.wav"), None) if sep.exists() else None
    if r.returncode or not vw or not nw:
        return {"voices": m, "music": None, "mix": m, "how": "mix",
                "why": "Demucs failed: " + (r.stderr or "")[-200:]}
    _ff("-i", vw, "-ac", "1", "-ar", "16000", "-b:a", "64k", voices)
    _ff("-i", nw, "-b:a", "128k", music)
    shutil.rmtree(sep, ignore_errors=True)
    wav.unlink(missing_ok=True)
    _stamp(out_dir, src, True)
    return {"voices": voices, "music": music, "mix": m, "how": "demucs", "why": "voices lifted off the music"}
