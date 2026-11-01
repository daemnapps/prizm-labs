"""The teardown's and the writing's one reader of the Generative Model House (VIDEO-RULINGS V2, the owner,
2026-10-20: "any of these generative tools that we build should just reference model house").

    import house
    house.model_id("behind.judge")   -> "gemini-3.1-pro-preview"
    house.model_id("sound.voice")    -> "eleven_v3"

It loads components/generative-model-house/model_house.py (its public surface, `model(job)`) by path, once.
A job the house does not have is refused by name there — never answered with a model typed here.
"""
import importlib.util
from pathlib import Path

_MH = Path(__file__).resolve().parents[2] / "generative-model-house" / "model_house.py"
_MOD = []


def _house():
    if not _MOD:
        spec = importlib.util.spec_from_file_location("model_house", _MH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MOD.append(mod)
    return _MOD[0]


def model(job):
    """The house's whole entry for a job (a dict, or a plain string such as behind.judge)."""
    return _house().model(job)


def model_id(job):
    """The model id a door is called with, for one job."""
    node = model(job)
    if isinstance(node, str):
        return node
    mid = node.get("model") or node.get("id")
    if not mid:
        raise KeyError(f"the Generative Model House names no model for '{job}'")
    return mid


def model_ids(job):
    """An ordered list of model ids for a job that names several (e.g. behind.judge_busy, the busy-model
    fallbacks in preference order)."""
    node = model(job)
    ids = node if isinstance(node, list) else (node.get("models") if isinstance(node, dict) else None)
    if not ids:
        raise KeyError(f"the Generative Model House names no model list for '{job}'")
    return list(ids)
