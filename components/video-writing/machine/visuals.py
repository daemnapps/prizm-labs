"""How the writing line uses the swipe for the pictures (owner rulings, 2026-11-20).

The owner's last word: "we use the swipe image to generate our version, and we still extract the motion patterns from
the swipe to generate our own." So the director's base is the swipe's shot (its composition) and its motion pattern,
with our people, place, product and idea layered on with the dials (`director_base` = "swipe"). The other settings
stay for the switch:

- lane `brief`: true = stage 5 v18 (staged fresh, the swipe as understanding only); false = v17 (the swipe as backbone).
- lane `director`: false = 5d v1 (the swipe's shot as backbone, no camera written); true = camera written, with
  `director_base` "swipe" (v3: the swipe's shot and motion pattern as base) or "ours" (v2: staged fresh).

Switch: visuals_ours.json beside this file; on one machine VISUALS_OURS_OFF=all|<lanes> and
VISUALS_DIRECTOR_BASE=swipe|ours.
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _cfg():
    try:
        return json.loads((HERE / "visuals_ours.json").read_text())
    except (OSError, ValueError):
        return {}


def ours(lane):
    off = {x.strip() for x in os.environ.get("VISUALS_OURS_OFF", "").split(",") if x.strip()}
    if "all" in off or lane in off:
        return False
    cfg = _cfg()
    return bool(cfg.get("on", True)) and bool((cfg.get("lanes") or {}).get(lane, True))


def director_base():
    """"swipe" (the swipe's shot and motion pattern are the base) or "ours" (staged fresh)."""
    v = os.environ.get("VISUALS_DIRECTOR_BASE", "").strip() or str(_cfg().get("director_base") or "swipe")
    return "ours" if v == "ours" else "swipe"
