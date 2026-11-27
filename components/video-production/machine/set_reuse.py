#!/usr/bin/env python3
"""set_reuse.py — a place the brand already banked is used before a new one is printed (2026-11-25).

`banked_set(brand, row, style)` -> (bank id, why) or (None, ""). The same kind of place (the name's own last word), the
brief's words for it covered by the bank's, no clash of day and night or of whose place it is, the same style, its wide
picture on file. Anything less makes a new one, as before. The model check that a bound element matches the brief
(element_match.py) still runs after. Reads only. Any brand; Python 3.9, standard library.
"""
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
PIC = (".png", ".jpg", ".jpeg", ".webp")
FLOOR = 0.6
LOOSE = {"room", "set", "table", "studio", "stage", "office", "house", "shop", "place", "scene", "corner"}   # says too little on its own
LOOK = set("white black grey gray beige cream brown dark bright red blue green teak wood wooden marble slate stone brick tile tiled "
           "modern rustic vintage luxury clinical traditional".split())
CLASH = (({"night", "evening", "midnight", "dark"}, {"day", "daylight", "morning", "noon", "sunny", "afternoon", "daytime"}),
         ({"outdoor", "outside", "street", "yard"}, {"indoor", "inside"}),
         ({"doll", "miniature", "cartoon", "clay", "lego", "animated", "anime", "pixel"}, set()),
         ({"rural", "village", "farmhouse", "paddy"}, set()),
         ({"christmas", "holiday", "halloween", "thanksgiving"}, set()))


def _made():
    f = HERE.parents[1] / "asset-index" / "machine" / "made.py"
    s = importlib.util.spec_from_file_location("set_reuse_made", str(f))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _bag(text):
    return set(re.findall(r"[a-z]+", str(text or "").lower()))


def clash(a, b):
    for x, y in CLASH:
        if y and ((a & x and b & y and not b & x) or (a & y and b & x and not b & y)):
            return True
        if not y and (a & x) != (b & x):                                   # a season's dressing is in both or in neither
            return True
    return False


def _style(folder):
    try:
        return json.loads((folder / "spec.json").read_text()).get("style_id") or None
    except (OSError, ValueError, AttributeError):
        return None


def banked_set(brand, row, style=None, ws=None, rows=None):
    ws = Path(ws or WS)
    M = _made()
    name = re.sub(r"^(the|a|an)[- ]", "", str(row.get("id") or "").lower()).replace("-", " ")
    noun = (re.findall(r"[a-z]+", name) or [""])[-1]
    if not noun:
        return None, ""
    said = "%s %s" % (name, row.get("description") or "")
    asked = _bag(said + " %s %s" % (row.get("time_of_day") or "", row.get("light") or ""))
    rows = [r for r in (M.elements(ws, brand) if rows is None else rows) if r["kind"] == "place"]
    best = None
    for r in rows:
        bank = _bag(str(r.get("name") or "").replace("-", " "))
        if noun.rstrip("s") not in {w.rstrip("s") for w in bank} or clash(asked, _bag(r["what"])):
            continue
        owner = re.match(r"([a-z]+)['’]s ", name)
        if owner and owner.group(1) not in _bag(r["name"].replace("-", " ")) | _bag(r["what"]):
            continue                                                       # somebody's own place is theirs
        if noun in LOOSE and not (set(M.words(name)) - {noun}) & set(M.words(r["name"].replace("-", " "))):
            continue
        home = ws / "runs" / "ai-elements" / brand / "sets" / r["name"]
        if not any((home / "plates" / ("wide" + e)).is_file() for e in PIC):
            continue
        if style and _style(home) != style:
            continue
        want, got = set(M.words(said)), set(M.words(r["what"] + " " + r["name"].replace("-", " ")))
        looks = _bag(said) & LOOK                                          # what it is made of and its colours must be there
        if looks and len(looks & _bag(r["what"])) < 0.6 * len(looks):
            continue
        score = len(want & got) / max(1, min(len(want), 14))
        if score >= FLOOR and (best is None or score > best[0]):
            best = (score, r["name"])
    return (best[1], "the brand already has this place (%d%% of the brief's words for it)" % round(min(1, best[0]) * 100)) if best else (None, "")
