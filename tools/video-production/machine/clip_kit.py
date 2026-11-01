"""clip_kit — the small shared helpers every clip tool uses (ffmpeg, files, the run folder names). Brand- and model-agnostic.

Split out of the retired Omni module (2026-10-26, the owner: the chain is Seedance only). Nothing here names a model.
"""
from __future__ import annotations

import base64
import importlib.util
import mimetypes
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lineparity = _load("lineparity")
vp_keys = _load("vp_keys")

def ffmpeg_path() -> str:
    for cand in [shutil.which("ffmpeg"), "/opt/homebrew/bin/ffmpeg"]:
        if cand and Path(cand).is_file():
            return cand
    raise SystemExit("ffmpeg not found")


def run_cmd(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def data_url(path: Path) -> str:
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode() if path.is_file() else ""
    return f"data:{mime};base64,{b64}"


def remux(clip: Path, audio: Path, out: Path) -> Path:
    """The clip's picture with this sound laid on it (video copied) — the upscaler's sound is never trusted."""
    out.parent.mkdir(parents=True, exist_ok=True)
    run_cmd([ffmpeg_path(), "-y", "-i", str(clip), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", str(out)])
    return out


# The voice finish: the cast voices measured dull next to a clip model's own sound (-19 dB vs -12 in the 4-10 kHz band,
# -26 vs -17 above 10 kHz); this lifts them to match. Laid on every off-camera line read (make_tts).
CRISP = "highshelf=f=3500:g=9:t=s:width=0.6,highshelf=f=9000:g=4,loudnorm=I=-16:TP=-1.5:LRA=11"


def crisp(audio, out):
    run_cmd([ffmpeg_path(), "-y", "-i", str(audio), "-af", CRISP, "-ar", "48000", str(out)])   # the edit's rate (P63)
    return Path(out)


# ---------------------------------------------------------------- the run folder's own names
# Written 2026-10-26 (the owner: the Omni names go too). A run keeps its clip results at clips/ledger.json and its
# per-call files at clips/calls/<call>/. A run made before then keeps clips/omni-ledger.json and clips/omni/<call>/ on
# disk (and on the Drive mirror); every reader goes through these two so both read right.
LEDGER = "ledger.json"
CALLS = "calls"
_OLD_LEDGER = "omni-ledger.json"
_OLD_CALLS = "omni"


def ledger_path(run) -> Path:
    c = Path(run) / "clips"
    return c / _OLD_LEDGER if (not (c / LEDGER).exists() and (c / _OLD_LEDGER).exists()) else c / LEDGER


def calls_dir(run) -> Path:
    c = Path(run) / "clips"
    return c / _OLD_CALLS if (not (c / CALLS).exists() and (c / _OLD_CALLS).exists()) else c / CALLS
