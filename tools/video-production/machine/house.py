"""The Generative Model House, as this machine reads it (VIDEO-RULINGS V2, CHANGES.md P23, 2026-10-21).

the owner, 2026-10-20: "any of these generative tools that we build should just reference model house". The one place
that names a model is `components/generative-model-house/models.json`; this file only opens its public reader,
`model_house.model(job)`, and says which job each door of this machine asks for. Nothing here names a model.

    house.judge()                 -> the judge model id (behind.judge)
    house.clip("seedance")        -> {"id", "door", ...}   (clips.seedance)
    house.voice_model()           -> the voice model id (sound.voice)
    house.picture_model("edit")   -> the picture model id (pictures.generate / pictures.edit)
    house.words_model()           -> the word-timings model id (sound.words)
    house.picture_overflow()      -> {"model", "door", ...}   (pictures.overflow — the same model on fal)
    house.picture_backup()        -> the picture backup model id (pictures.backup)

A house that cannot be read is an error naming the file — never a silent fall back to a model written here.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
READER = HERE.parent.parent / "generative-model-house" / "model_house.py"
_MH = {}


def _mh():
    if "m" not in _MH:
        if not READER.is_file():
            raise SystemExit(f"the Generative Model House is not on this machine: {READER}")
        sp = importlib.util.spec_from_file_location("generative_model_house", READER)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _MH["m"] = m
    return _MH["m"]


def model(job: str):
    """The house's answer for a dotted job ('clips.seedance', 'behind.judge') — model_house.model, unchanged."""
    return _mh().model(job)


def judge() -> str:
    return str(model("behind.judge"))


def clip(name: str) -> dict:
    return dict(model(f"clips.{name}"))


def voice_model() -> str:
    return str(model("sound.voice")["model"])


def voice_design_model() -> str:
    return str(model("sound.voice_design")["model"])


def swap() -> dict:
    """The Genjutsu object swap (swipe_footage.swap): {"id", "door", "api", ...}."""
    return dict(model("swipe_footage.swap"))


def words_model() -> str:
    return str(model("sound.words")["model"])


def picture_model(kind: str = "generate") -> str:
    return str(model(f"pictures.{kind}")["model"])


def picture_overflow() -> dict:
    """RETIRED 2026-10-26: the fal overflow door is gone (pictures.overflow left the House). Kept so an old reader gets {}
    instead of a KeyError; the picture ladder in tools/image-production replaces it."""
    try:
        return dict(model("pictures.overflow"))
    except KeyError:
        return {}


def picture_backup() -> str:
    """The picture backup when GPT Image refuses (pictures.backup: Seedream 5 Pro on the Higgsfield command line)."""
    return str(model("pictures.backup")["model"])


def picture_object() -> str:
    """The third picture rung (pictures.object: Nano Banana Pro on the Higgsfield command line)."""
    return str(model("pictures.object")["model"])


def picture_safety_net() -> str:
    """The last rung of the picture ladder (pictures.safety_net: OpenAI direct), '' when the House has none."""
    try:
        return str(model("pictures.safety_net")["model"])
    except KeyError:
        return ""


def picture_door(kind: str = "generate") -> str:
    """The door a picture job goes through: 'higgsfield' (the command line) or 'openai' (the last rung only)."""
    return str(model(f"pictures.{kind}").get("door") or "")


def upscale() -> str:
    return str(model("behind.upscale"))


def upscale_alternate() -> dict:
    """The paid upscaler the house names as the alternate to the local one (behind.upscale_alternate)."""
    return dict(model("behind.upscale_alternate"))
