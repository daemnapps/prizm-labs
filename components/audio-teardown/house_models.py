"""The audio teardown's reader of the Generative Model House (VIDEO-RULINGS V2, owner, 2026-10-20: "any of
these generative tools that we build should just reference model house"; verify row 17, 2026-10-21).

    import house_models as H
    H.model_id("sound.speakers")        -> the speaker-label model
    H.model_ids("behind.judge_busy")    -> the busy-model fallbacks, in order

Loads components/generative-model-house/model_house.py (its public surface, `model(job)`) by path, once.
A job the house does not have is refused by name there.
"""
import importlib.util
from pathlib import Path

_MH = Path(__file__).resolve().parents[1] / "generative-model-house" / "model_house.py"
_MOD = []


def _house():
    if not _MOD:
        spec = importlib.util.spec_from_file_location("at_model_house", _MH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MOD.append(mod)
    return _MOD[0]


def model_id(job):
    node = _house().model(job)
    mid = node if isinstance(node, str) else (node.get("model") or node.get("id"))
    if not mid:
        raise KeyError(f"the Generative Model House names no model for '{job}'")
    return mid


def model_ids(job):
    node = _house().model(job)
    ids = node if isinstance(node, list) else node.get("models")
    if not ids:
        raise KeyError(f"the Generative Model House names no model list for '{job}'")
    return list(ids)
