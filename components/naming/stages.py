"""The one vocabulary for creative in motion — read it, never retype it (stages.json).

    import stages
    stages.stage("Your OK")        -> {"id": "final-needs-you", "name": "Final OK · needs you", ...}
    stages.kind("static")          -> {"id": "image-ad", "name": "Image ad", ...}
    stages.flag("Stopped")         -> {"id": "stuck", "name": "Stuck", ...}
    stages.ORDER                   -> the eight stage ids, in order

A tool's own step word that maps to nothing returns None — add it to `from` in stages.json, never a
second word list in the tool. Brand-agnostic.
"""
import json
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parent / "stages.json").read_text())
ORDER = [s["id"] for s in _D["stages"]]
STAGES, TYPES, FLAGS = _D["stages"], _D["types"], _D["flags"]


def _find(rows, word):
    w = (word or "").strip().lower()
    for r in rows:
        if w == r["id"] or w == r["name"].lower() or w in (f.lower() for f in r.get("from", [])):
            return r
    return None


def stage(word):
    return _find(STAGES, word)


def kind(word):
    return _find(TYPES, word)


def flag(word):
    return _find(FLAGS, word)


def all_words():
    """For a page: {"stages": [...], "types": [...], "flags": [...]} with ids and display names only."""
    pick = lambda rows: [{"id": r["id"], "name": r["name"], **({"needs_damon": True} if r.get("needs_damon") else {})} for r in rows]
    return {"stages": pick(STAGES), "types": pick(TYPES), "flags": pick(FLAGS)}
