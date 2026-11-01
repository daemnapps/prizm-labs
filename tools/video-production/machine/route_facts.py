"""route_facts — give every scene of a plan its route (SHOT-ROUTES.md) and make the route act (2026-10-20).

the owner, 2026-10-20: "make this real": the rule for when to use real footage, a swap or AI
generation is applied by the machine at the start of production, not by a session's judgment.

The facts come from what the run already has, so no prompt changes:
  the brief's scene  `source` names its swipe shot and times ("K01 0:00-0:11: …"), `to_camera`
                     and its line say talking, `kind` says card/screen/endcard, a footage match
                     from footage.py (`source_plan: cut`) says REAL
  the frame map      framemap/framemap.json of the teardown run: each shot K## is the stretch
                     between two cuts (so it is a clean single shot), its seconds, and its
                     moments and camera (so whether the motion is the point)

Then the route acts:
  REAL  the footage step already cuts it; nothing is generated
  SWAP  source_plan = "swap"; nothing is generated; a swap order (the frame map's own shot clip,
        the cast member's full sheet, the standard cast_swap prompt) is written to swap-orders.json
        for the Genjutsu door
  AI    made by the machine as before

    python3 route_facts.py <production run> [--framemap <dir>]   # writes ROUTES.md + swap-orders.json

Brand-agnostic: nothing here names a brand, a product or a person.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
STILL_KINDS = {"card", "screen", "endcard", "split", "greenscreen"}
MOVE_WORDS = re.compile(r"\b(walk|run|jump|flip|fly|flies|swing|spin|dance|kick|punch|fight|push|throw|catch|"
                        r"fall|lands?|strut|hang|wipe|spray|cut|turns?|leans?|reach|grab|lift|wave|shout|"
                        r"moves?|brush|stroke|tap|pull|rub|scrub|comb|press|slide|scrape|pour|dispens|clip|"
                        r"sweep|rais|point|gestur|fan|clap|stomp|shak|bounc|wiggl|thrust|swing|wav)\w*", re.I)


def _load(name):
    spec = importlib.util.spec_from_file_location(f"vm_rf_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def framemap_of(run: Path, plan: dict, given: str | None = None) -> Path | None:
    """The teardown run's frame map: given, else the plan's, else beside the brief this run came from."""
    cands = [Path(given)] if given else []
    if plan.get("framemap"):
        cands.append(Path(plan["framemap"]))
    rj = run / "run.json"
    if rj.is_file():
        bf = (json.loads(rj.read_text()) or {}).get("brief_from")
        if bf:
            b = Path(bf).resolve()
            cands += [b.parent.parent / "framemap", b.parent / "framemap"]
    for c in cands:
        if (c / "framemap.json").is_file():
            return c
    return None


def shots_of(fm: Path | None) -> dict:
    if not fm:
        return {}
    data = json.loads((fm / "framemap.json").read_text())
    return {s["id"]: s for s in data.get("shots") or [] if s.get("id")}


def _times(source: str):
    m = re.search(r"(\d+):(\d{2}(?:\.\d+)?)\s*[-–]\s*(\d+):(\d{2}(?:\.\d+)?)", source or "")
    if not m:
        return None
    a = int(m.group(1)) * 60 + float(m.group(2))
    b = int(m.group(3)) * 60 + float(m.group(4))
    return (a, b) if b > a else None


def motion_is_the_point(scene: dict, shot: dict | None) -> bool:
    """The motion carries the shot: the swipe shot moves (two or more actions, or the camera moves)
    and the scene itself is an action, not someone standing and talking."""
    if not shot:
        return False
    mp = shot.get("map") or {}
    moments = mp.get("moments") or []
    acts = sum(1 for m in moments if MOVE_WORDS.search(str(m.get("does") or "")))
    cam = mp.get("camera") or {}
    camera_moves = str(cam.get("move") or "").strip().lower() not in ("", "none", "still", "locked off")
    scene_moves = bool(MOVE_WORDS.search(" ".join(str(scene.get(k) or "") for k in ("happens", "source"))))
    return scene_moves and (acts >= 2 or camera_moves)


def facts(scene: dict, shots: dict, product_words=()) -> dict:
    src = str(scene.get("source") or "")
    sid = scene.get("swipe_shot") or (re.match(r"\s*(K\d+)\b", src).group(1) if re.match(r"\s*(K\d+)\b", src) else None)
    shot = shots.get(sid) if sid else None
    span = _times(src)
    secs = (span[1] - span[0]) if span else float((shot or {}).get("seconds") or scene.get("seconds") or 0)
    # a scene that spans past the end of its frame-map shot crosses a cut
    clean = bool(shot) and (not span or (span[0] >= float(shot.get("start", 0)) - 0.05
                                          and span[1] <= float(shot.get("end", 0)) + 0.05))
    text = " ".join(str(scene.get(k) or "") for k in ("happens", "props", "source")).lower()
    needs_product = any(w.lower() in text for w in product_words if w)
    shot_text = json.dumps((shot or {}).get("map") or {}).lower()
    slot = bool(re.search(r"\b(holds?|holding|in (his|her|their) hand|bottle|tube|jar|phone|basket|brush|tool)\b", shot_text))
    return {"id": scene.get("id"), "seconds": round(secs or 4.0, 2),
            "what": str(scene.get("happens") or src)[:80],
            "owned_footage": scene.get("source_plan") == "cut" and bool(scene.get("owned_file")),
            "talks_to_camera": bool(scene.get("to_camera")) and bool(str(scene.get("voice") or scene.get("say") or "").strip()),
            "motion_is_the_point": motion_is_the_point(scene, shot),
            "swipe_shot": sid if shot else None, "clean_single_shot": clean,
            "needs_product": needs_product, "product_slot_in_swipe": slot,
            "span": span}


def route_plan(run: Path, plan: dict, framemap: str | None = None, product_words=()) -> dict:
    """Route every scene; mark SWAP scenes so nothing is generated for them; return the routes."""
    sr = _load("shot_route")
    fm = framemap_of(run, plan, framemap)
    shots = shots_of(fm)
    rows, orders = [], []
    for s in plan.get("scenes") or []:
        if s.get("kind") in STILL_KINDS:
            rows.append({"id": s.get("id"), "route": "AI", "why": f"a {s.get('kind')}: made as a plate", "cost_usd": 0.0,
                         "seconds": 0})
            continue
        named = str(s.get("route") or "").upper()
        # A SCENE MAY NAME ITS OWN CLIP (2026-10-20): a presenter drawn from several swipes points each
        # scene at the teardown run whose frame map holds its shot
        s_fm = Path(s["framemap"]) if s.get("framemap") and (Path(s["framemap"]) / "framemap.json").is_file() else fm
        s_shots = shots_of(s_fm) if s_fm is not fm else shots
        f = facts(s, s_shots, product_words)
        if named in ("REAL", "SWAP", "AI"):
            r, why = named, "named in the brief"
            cost = {"REAL": 0.0, "SWAP": sr.swap_cost(f["seconds"]), "AI": sr.ai_cost(f["seconds"])}[named]
        else:
            r, why, cost = sr.route(f)
        s["route"], s["route_why"] = r, why
        rows.append({"id": s.get("id"), "route": r, "why": why, "seconds": f["seconds"], "cost_usd": cost,
                     "swipe_shot": f["swipe_shot"]})
        if r == "SWAP":
            s["source_plan"] = "swap"
            shot = s_shots.get(f["swipe_shot"]) or {}
            clip = (s_fm / "shots" / shot["clip"]) if s_fm and shot.get("clip") else None
            orders.append({"scene": s.get("id"), "swipe_shot": f["swipe_shot"],
                           "clip": str(clip) if clip else None, "span": f["span"],
                           "shot_start": float(shot.get("start") or 0),
                           "who": s.get("who"), "seconds": f["seconds"],
                           "note": "pad to 4 s forward+reverse when shorter; keep only the forward part in the edit"})
    secs = {k: round(sum(x["seconds"] for x in rows if x["route"] == k), 1) for k in ("REAL", "SWAP", "AI")}
    return {"framemap": str(fm) if fm else None, "rows": rows, "swap_orders": orders, "seconds": secs,
            "total_usd": round(sum(x["cost_usd"] for x in rows), 2)}


def markdown(res: dict, label: str = "") -> str:
    sec = res["seconds"]
    out = [f"# Shot routes{' — ' + label if label else ''}", "",
           "Every scene's route by SHOT-ROUTES.md, decided at the start of production. REAL is cut from footage "
           "we own, SWAP is the swipe's own shot with our cast swapped in (an order in swap-orders.json), AI is "
           "generated by this machine.", "",
           f"REAL {sec['REAL']}s · SWAP {sec['SWAP']}s · AI {sec['AI']}s · frame map: {res['framemap'] or 'none found'}", "",
           "| Scene | Route | Swipe shot | Seconds | Cost | Why |", "|---|---|---|---|---|---|"]
    for x in res["rows"]:
        out.append(f"| {x['id']} | {x['route']} | {x.get('swipe_shot') or ''} | {x['seconds']} | ${x['cost_usd']:.2f} | {x['why']} |")
    return "\n".join(out) + "\n"


def write(run: Path, plan: dict, framemap: str | None = None, product_words=()) -> dict:
    res = route_plan(run, plan, framemap, product_words)
    # A RE-ROUTE KEEPS WHAT IS MADE (2026-10-20): an order for the same scene and the same swipe shot carries
    # its status, job and file over, so routing again never sends a finished swap a second time
    old_p = run / "swap-orders.json"
    old = {(o.get("scene"), o.get("swipe_shot")): o for o in (json.loads(old_p.read_text()) if old_p.is_file() else [])}
    for o in res["swap_orders"]:
        prev = old.get((o["scene"], o["swipe_shot"]))
        if prev and prev.get("status"):
            o.update({k: v for k, v in prev.items() if k not in o or k in ("status", "file")})
    (run / "ROUTES.md").write_text(markdown(res, run.name))
    (run / "swap-orders.json").write_text(json.dumps(res["swap_orders"], indent=1))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Route every scene of a production run (SHOT-ROUTES.md).")
    ap.add_argument("run")
    ap.add_argument("--framemap")
    a = ap.parse_args(argv)
    run = Path(a.run)
    plan = json.loads((run / "plan.json").read_text())
    res = write(run, plan, a.framemap)
    print((run / "ROUTES.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
