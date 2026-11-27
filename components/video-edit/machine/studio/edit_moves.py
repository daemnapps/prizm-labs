"""THE MOVES DIRECTOR IN THE EDIT (2026-11-17): each scene gets one edit move, chosen by the machine and laid in the
cut. The edit stage runs the director (video-edit moves/machine/director.py: shortlist, the creative director's three
pitches, one kept by its stated pick rule) and writes briefs/<production>/edit/moves-picks.json; to_studio.py lays the
picks into the cut sheet on the next build (a match or whip on a scene hand-off, a punch-in split on a beat).

    stage(n, B, R)   run the director (only when its facts changed) and return the edit stage's rows
    apply(B, sheet)  lay the picks into a cut sheet (to_studio.build): sheet["layers"]["transitions"], split clips

A pick the edit cannot lay (paid generation, no drawer yet, inside a scene's clip) is a gap with its reason, never
made. SWITCH: edit-stage.json "director" (false: no picks, nothing laid), "director_pitch" ("claude": the director
prompt through the chain's Claude door; "rules": the shortlist pitches, no model). VIDEO_STUDIO_EDIT_OFF=director.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os  # noqa: E402
import sys  # noqa: E402
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")  # the Studio's production side (settings, takes, voices) until each seam is cut
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))
FPS = 24000 / 1001
EDGE = 0.35


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def director():
    """video-edit's moves director, loaded by path (it is that component's front door for this pass)."""
    import settings as ST
    p = ST.part("video-edit") / "moves" / "machine" / "director.py"
    spec = importlib.util.spec_from_file_location("moves_director", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def picks(B):
    return _load(Path(B) / "edit" / "moves-picks.json", {}) or {}


# ---------------------------------------------------------------- lay: the picks into a cut sheet
def apply(B, sheet):
    """Lay every pick in edit/moves-picks.json into the cut sheet (to_studio's, before compose). A hand-off move is a
    `layers.transitions` row compose draws (match, whip); an in-scene move splits the scene's clip on its beat and
    punches the second piece in (compose's `punch`). Times are kept inside each scene, so a hook played first moves
    them with the scene. Writes sheet["director_moves"]; returns it."""
    import edit_stage as ES
    if not ES.part_on("director"):
        return []
    laid = []
    pics = sheet.get("picture") or []
    for e in picks(B).get("edits") or []:
        s = e["scene"]
        mine = [p for p in pics if (p.get("scene") or p["id"]) == s]
        if not mine:
            laid.append(dict(e, landed=None, why="the scene is not in this cut (a hook or variant replaced it)"))
            continue
        s0 = min(p["start"] for p in mine)
        if e.get("transition"):
            end = max(p["start"] + p["duration"] for p in mine)
            nxt = [p for p in pics if abs(p["start"] - end) < 0.05 and (p.get("scene") or p["id"]) != s]
            if not nxt:
                laid.append(dict(e, landed=None, why="no scene follows this one in this cut"))
                continue
            sheet.setdefault("layers", {}).setdefault("transitions", []).append(
                {"id": "director-%s" % s, "after_scene": s, "kind": e["transition"], "why": "moves director: %s" % e["move"]})
            laid.append(dict(e, landed="%s on the hand-off %s -> %s at %.2f s" % (
                e["transition"], s, nxt[0].get("scene") or nxt[0]["id"], end), at_cut=round(end, 3)))
        elif e.get("punch"):
            at = round(round(float(e["at_in_scene"]) * FPS) / FPS, 4)          # on the picture's own frame
            t = s0 + at
            clip = next((p for p in mine if not p.get("still") and p["start"] + EDGE <= t <= p["start"] + p["duration"] - EDGE), None)
            if not clip:
                laid.append(dict(e, landed=None, why="the beat falls within %.2f s of a cut or on a still frame" % EDGE))
                continue
            cut = round(t - clip["start"], 4)
            tail = dict(clip, id=clip["id"] + "-punch", start=round(clip["start"] + cut, 3),
                        duration=round(clip["duration"] - cut, 3), source_start=round(float(clip.get("source_start") or 0) + cut, 4),
                        punch=float(e["punch"]), label=(clip.get("label") or s) + " · punch-in on the beat",
                        why="moves director: %s on %s" % (e["move"], e["event"]))
            clip["duration"] = round(cut + 0.002, 3)                          # the Studio's 2 ms overlap at a join
            pics.insert(pics.index(clip) + 1, tail)
            laid.append(dict(e, landed="%s: %s cut on %.2f s, punched in to %d%%" % (e["move"], s, t, round(e["punch"] * 100)),
                             at_cut=round(t, 3)))
    sheet["director_moves"] = laid
    return laid


# ---------------------------------------------------------------- the edit stage's rows
def stage(n, B, R, say=lambda *a, **k: None):
    """Run the director for the production (a no-op when nothing it reads changed) and return one row per scene for
    edit/stage.json: laid when the last build's cut sheet carries the move, else why not. Never an open row: a pick
    lands on the next render by itself, a gap carries its reason."""
    import edit_stage as ES
    B = Path(B)
    D = director()
    rec = D.direct(B, R, ES.conf().get("director_pitch", "claude"), say=lambda m: say("check", "doing", m))
    built = {(x["scene"], x["move"]): x for x in (_load(B / "studio-build" / "cutsheet.json", {}) or {}).get("director_moves") or []}
    rows = []
    for r in rec.get("scenes") or []:
        p = r.get("pick") or {}
        edits = p.get("edits") or ([p["edit"]] if p.get("edit") else [])
        if not edits:
            rows.append({"id": "director-%s" % r["scene"], "kind": "director", "swipe_at": 0.0, "ours": None,
                         "what": "%s · %s" % (r["scene"], p.get("reason") or "no move"),
                         "reason": "the clean cut stays: " + (p.get("reason") or "no move the edit can lay")})
        for k, e in enumerate(edits):
            row = {"id": "director-%s" % r["scene"] + ("-%d" % (k + 1) if k else ""), "kind": "director",
                   "swipe_at": 0.0, "ours": e["at"],
                   "what": "%s · %s: %s at %.2f s (%s), %s; %s" % (r["scene"], p["name"], e["move"], e["at"], e["event"],
                                                                   p["from"], p["reason"])}
            b = built.get((r["scene"], e["move"]))
            if b and b.get("landed"):
                row["landed"] = "laid in the edit: " + b["landed"]
            elif b:
                row["reason"] = "picked, not laid: " + b.get("why", "")
            else:
                row["reason"] = "picked; it lands on the next render (to_studio lays edit/moves-picks.json)"
            rows.append(row)
        for g in r.get("gaps") or []:
            rows.append({"id": "director-%s-gap-%s" % (r["scene"], g["move"]), "kind": "director-gap", "swipe_at": 0.0,
                         "ours": None, "what": "%s · %s pitched `%s`" % (r["scene"], g.get("option"), g["move"]),
                         "reason": "a gap, not made: " + g["gap"]})
    return rows
