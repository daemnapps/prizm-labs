#!/usr/bin/env python3
"""Whether production may use the swipe for a brief (owner ruling, 2026-11-20).

"After the script is written, the swipe's job is done": every picture and clip of an AI-lane ad is generated from our
creative. The switch is swipe-use.json beside this file (`ai_lane_uses_swipe`, false by the ruling). Every production
door that would feed the swipe in asks `off(doc)` first:

    storyboard_plan.build   no swipe sections, frame map or transcript: sections and lengths from our brief and voice;
                            no swipe shot put first on a picture (with_swipe_camera)
    run.py                  no SWAP route (route_facts.write swipe=False); every picture item stripped of swipe
                            frames (`strip`), wherever they were bound (element_refs' composition frame, swipe-edit)
    camera_motion.apply     a clip call still carrying swipe footage as a reference is a problem the live door refuses

Nothing here names a brand, product or person.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SWITCH = HERE / "swipe-use.json"
SWIPE_PATH = re.compile(r"(^|/)framemap/")
# the prompt sentences that bind a swipe frame (model-inputs frame_rules.swipe_camera, element_refs COMPOSITION_RULE)
SWIPE_WORDS = re.compile(r"[^.]*\b(swipe composition reference|swipe shot|the swipe's (?:shot|frame|camera))\b[^.]*\.\s*",
                         re.I)


def uses_swipe() -> bool:
    import os
    f = Path(os.environ.get("VP_SWIPE_USE") or SWITCH)        # VP_SWIPE_USE: another switch file (tests)
    try:
        return bool(json.loads(f.read_text()).get("ai_lane_uses_swipe"))
    except (OSError, ValueError):
        return False


def lane_of(doc) -> str:
    doc = doc if isinstance(doc, dict) else {}
    return str(doc.get("lane") or (doc.get("piece") or {}).get("lane") or "").lower()


def off(doc) -> bool:
    """True when production must not use the swipe for this brief: an AI-lane brief, with the switch at its ruling."""
    return lane_of(doc) == "ai" and not uses_swipe()


def is_swipe_file(value) -> bool:
    return bool(SWIPE_PATH.search(str(value or "").replace("\\", "/")))


def strip(item: dict) -> tuple:
    """(item, removed): the item with every swipe frame taken out of its references and the sentences that bind one
    taken out of its prompt."""
    medias = item.get("medias") or []
    keep = [m for m in medias if not (isinstance(m, dict) and is_swipe_file(m.get("value")))]
    removed = [m.get("value") for m in medias if m not in keep]
    for k in ("refs",):
        if isinstance(item.get(k), list):
            removed += [r for r in item[k] if is_swipe_file(r)]
            item[k] = [r for r in item[k] if not is_swipe_file(r)]
    if removed:
        item["medias"] = keep
    params = item.get("params") if isinstance(item.get("params"), dict) else None
    if params and isinstance(params.get("prompt"), str) and (removed or item.get("swipe_camera") or item.get("swipe_composition")):
        params["prompt"] = " ".join(SWIPE_WORDS.sub("", params["prompt"]).split())
    for k in ("swipe_camera", "swipe_composition", "copies_swipe_shot"):
        item.pop(k, None)
    return item, removed


def swipe_refs_of_call(call: dict) -> list:
    """The swipe files a clip call still carries (picture or motion reference)."""
    out = []
    for k in ("refs", "image_refs"):
        for r in call.get(k) or []:
            v = r.get("file") or r.get("value") or r.get("path") if isinstance(r, dict) else r
            if is_swipe_file(v):
                out.append(v)
    for k in ("start_frame", "end_frame"):
        v = call.get(k)
        if isinstance(v, str) and is_swipe_file(v):
            out.append(v)
    return out
