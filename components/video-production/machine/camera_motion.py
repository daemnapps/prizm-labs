#!/usr/bin/env python3
"""THE CAMERA AND MOTION PLAN — the station between the approved pictures and the clips (2026-11-20).

Owner ruling, 20 Nov 2026: every production moves through the process; the Studio only shows it. Six AI-lane ads were
made that day with clips that never moved: no camera or motion plan was made for any scene, and nothing refused a clip
without one. This station is that plan, made by the chain from what the writing already decided, and the clip route
carries it.

Per scene, from the accepted brief (its json block) and the director's 5d pick (`director/picks.json` beside the
brief, the scene's `director` record):

    camera   every shot's angle and camera move (the brief's `shots[].angle`, `shots[].camera_move`), each beat's camera
             where the beat names one, and where the camera ends (`last_frame.camera`)
    motion   the director's kept idea (title, premise), its movement line (the kept pitch's `movement`: what moves on
             every beat), and every beat in order: who does what, over which words, with which prop
    words    the CAMERA AND MOTION block that goes into every clip prompt of that scene, word for word

    <run>/clips/camera-motion.json     {"scenes": {sid: plan}, "held": {sid: why}, "brief_sha256", "made"}
    <run>/clips/CAMERA-MOTION.md       the same, to read

A scene with no director pick, no beat or no camera on any shot is HELD, with the reason. The clip plan is then stamped
(`apply`): every call gets its scenes' block in its prompt (the call's `prompt`, `seedance.prompt` and `params.prompt`
stay one text, so the clip gate's SENT check holds) and `camera_motion` naming what it carries; a call whose scene is
held, or that has no plan at all, is written into the plan's `problems`, and the live clip door (clips_run.run_live)
refuses a plan with problems before anything is spent. When the motion chain (components/motion) has run on a scene
in this run (`<run>/motion/<scene>/motion/camera.json`), its tracked camera is named beside the director's.

    python3 camera_motion.py plan <run dir> [--brief <5-brief.md>]     write the plan (free; no model is called)
    python3 camera_motion.py apply <run dir>                           stamp clips/plan.json (and plan-only.json)
    python3 camera_motion.py check <run dir>                           exit 1 when any clip lacks its plan

Nothing here spends anything or calls a model. No brand, product or person is named here.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

NO_CLIP = ("endcard", "card", "plate", "packshot")
BLOCK_HEAD = "CAMERA AND MOTION"
BLOCK_RE = re.compile(r"\n*" + BLOCK_HEAD + r" \(the director's plan[^\n]*\n(?:[^\n]+\n?)*?(?=\n\n|\Z)")


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def brief_doc(text: str) -> dict:
    """The brief's json block (its last one), or {}."""
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text or "", re.S)
    try:
        doc = json.loads(blocks[-1]) if blocks else {}
    except ValueError:
        return {}
    return doc if isinstance(doc, dict) else {}


def brief_of(run: Path, brief: Path | None = None) -> Path | None:
    """The accepted brief this run was started from: --brief, else run.json `brief_from`, else <run>/brief.md."""
    if brief:
        return Path(brief)
    rj = _read(Path(run) / "run.json", {}) or {}
    for c in (rj.get("brief_from"), Path(run) / "brief.md"):
        if c and Path(c).is_file():
            return Path(c)
    return None


def picks_of(brief: Path | None) -> dict:
    """The director's picks beside the brief (<writing run>/director/picks.json), keyed by scene; {} when none."""
    if not brief:
        return {}
    f = Path(brief).resolve().parent.parent / "director" / "picks.json"
    return ((_read(f, {}) or {}).get("picks") or {}) if f.is_file() else {}


def framemap_of(brief: Path | None) -> dict:
    """The swipe's frame map beside the brief's writing run, by shot id; {} when none."""
    if not brief:
        return {}
    f = Path(brief).resolve().parent.parent / "framemap" / "framemap.json"
    fm = _read(f, {}) or {}
    return {s.get("id"): s for s in fm.get("shots") or [] if s.get("id")}


def teardown_rows(brief: Path | None) -> list:
    """The swipe teardown's timed section table (storyboard_plan.swipe_sections) — the fallback for a swipe torn down
    before frame maps were kept: each row's span and its `Camera:` words. [] when none."""
    if not brief:
        return []
    f = Path(brief).resolve().parent.parent / "stages" / "1-teardown.md"
    if not f.is_file():
        return []
    try:
        import importlib.util as _iu
        sp = _iu.spec_from_file_location("cm_storyboard_plan", Path(__file__).resolve().parent / "storyboard_plan.py")
        sb = _iu.module_from_spec(sp); sp.loader.exec_module(sb)
        rows = sb.swipe_sections(f.read_text())
    except Exception:  # noqa: BLE001
        return []
    out = []
    for r in rows:
        m = re.search(r"Camera:\s*([^·]+)", str(r.get("visuals") or ""))
        out.append({"shot": r.get("id"), "start": r.get("start"), "end": r.get("end"),
                    "camera": (m.group(1).strip().rstrip(".") if m else "")})
    return out


def _secs(s: str) -> float:
    a, b = s.split(":")
    return int(a) * 60 + float(b)


def pattern_from_rows(sc: dict, rows: list) -> list:
    """A scene's swipe pattern from the teardown table: the rows its `source` times overlap ("0:07 - 0:16")."""
    m = re.search(r"(\d+:\d{2}(?:\.\d)?)\s*[-–]\s*(\d+:\d{2}(?:\.\d)?)", str(sc.get("source") or ""))
    if not m or not rows:
        return []
    a, b = _secs(m.group(1)), _secs(m.group(2))
    return [{"shot": r["shot"], "seconds": round(float(r["end"] or 0) - float(r["start"] or 0), 1),
             "camera": r["camera"], "moments": []}
            for r in rows if r.get("start") is not None and r.get("end") is not None
            and float(r["start"]) < b and float(r["end"]) > a and r.get("camera")]


def _verbs(does: str, n: int = 4) -> str:
    """A swipe moment's action as its first few words: the rhythm, never the swipe's own people or objects named."""
    return " ".join(str(does or "").split()[:n]).rstrip(",.;")


def swipe_pattern(sc: dict, shots_by_id: dict) -> list:
    """The swipe's motion pattern for the swipe shots a scene copies (its shots' `copies`, else its `source` K-id):
    per swipe shot, its measured camera and the timing of its moments, relative to the shot's start."""
    ks = [str(sh.get("copies")) for sh in sc.get("shots") or [] if sh.get("copies")]
    if not ks:
        m = re.match(r"\s*(K\d+)", str(sc.get("source") or ""))
        ks = [m.group(1)] if m else []
    out = []
    for k in dict.fromkeys(ks):
        s = shots_by_id.get(k)
        if not s:
            continue
        mp = s.get("map") or {}
        cam = mp.get("camera") or {}
        t0 = float(s.get("start") or 0)
        ms = [x for x in mp.get("moments") or [] if x.get("does")]
        if ms and all(float(x.get("t") or 0) < t0 for x in ms):
            t0 = 0.0                 # this frame map keeps moment times on the shot's own clock already
        mom = [{"at": round(float(x.get("t") or 0) - t0, 1), "does": _verbs(x.get("does"))} for x in ms]
        out.append({"shot": k, "seconds": s.get("seconds"),
                    "camera": ", ".join(str(cam[c]) for c in ("held", "move", "height", "distance") if cam.get(c)),
                    "moments": mom})
    return out


def _clean(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().rstrip(".")


def kept_pitch(pick: dict) -> dict:
    """The pitch the director kept (its title matches `kept.title`), else {}."""
    title = ((pick or {}).get("kept") or {}).get("title")
    return next((p for p in (pick or {}).get("pitches") or [] if p.get("title") == title), {}) if title else {}


def split_plan(sc: dict, tracked: dict | None = None) -> tuple[dict | None, str | None]:
    """A split scene: the director station does not stage splits (director.directable), so each side is planned from
    its own written shots and beats, and the block names both sides."""
    sides, held = {}, []
    for side in ("left", "right"):
        sd = (sc.get("split") or {}).get(side) or {}
        if not sd:
            continue
        sub = {"id": f"{sc.get('id')} {side}", "director": {"title": f"{side} side, as written"},
               "shots": sd.get("shots"), "beats": sd.get("beats"), "last_frame": sd.get("last_frame")}
        p, why = scene_plan(sub, None, tracked)
        if p:
            sides[side] = p
        else:
            held.append(f"{side}: {why}")
    if held or not sides:
        return None, "split scene — " + ("; ".join(held) or "no side written")
    words_ = "\n\n".join(p["words"] for p in sides.values())
    return {"scene": sc.get("id"), "kind": "split", "record": "the brief's own split sides (splits are not directed)",
            "camera": {s: p["camera"] for s, p in sides.items()}, "motion": {s: p["motion"] for s, p in sides.items()},
            "sides": list(sides), "words": words_,
            "side_words": {s: p["words"] for s, p in sides.items()},
            "side_shots": {s: [x["shot"] for x in p["camera"]["shots"]] for s, p in sides.items()}}, None


def scene_plan(sc: dict, pick: dict | None = None, tracked: dict | None = None,
               swipe: list | None = None) -> tuple[dict | None, str | None]:
    """(plan, None) or (None, why it is held) for one brief scene. `swipe` is the swipe's motion pattern for the shots
    the scene copies (swipe_pattern), carried beside the director's pick when production uses the swipe."""
    sid = sc.get("id")
    if str(sc.get("kind") or "").lower() == "split" and sc.get("split"):
        return split_plan(sc, tracked)
    d = sc.get("director") or {}
    pick = pick or {}
    if not d and not pick:
        return None, "no director pick (stage 5d) for this scene"
    shots = [{"shot": sh.get("id"), "angle": _clean(sh.get("angle")), "move": _clean(sh.get("camera_move")),
              "why": _clean(sh.get("camera_why")), "copies": sh.get("copies")}
             for sh in sc.get("shots") or []]
    shots = [s for s in shots if s["angle"] or s["move"]]
    beats = [{"id": b.get("id"), "shot": b.get("shot"), "who": _clean(b.get("who")), "do": _clean(b.get("do")),
              "action": _clean(b.get("action")), "over": _clean(b.get("over")), "prop": _clean(b.get("prop")),
              "camera": _clean(b.get("camera")) if _clean(b.get("camera")) not in ("", "held", "hold") else ""}
             for b in sc.get("beats") or pick.get("beats") or []]
    beats = [b for b in beats if b["do"] or b["action"]]
    if not beats:
        return None, "the director's pick has no beats: nothing says what moves"
    lf = sc.get("last_frame") if isinstance(sc.get("last_frame"), dict) else {}
    ends = _clean(lf.get("camera"))
    if not shots and not ends and not any(b["camera"] for b in beats) and not tracked:
        return None, "no camera on any shot (angle or camera_move) and none on the last frame"
    kp = kept_pitch(pick)
    motion = {"title": d.get("title") or (pick.get("kept") or {}).get("title") or "",
              "rung": d.get("rung") or (pick.get("kept") or {}).get("rung") or "",
              "premise": _clean(d.get("premise") or (pick.get("kept") or {}).get("premise")),
              "movement": _clean(kp.get("movement")),
              "happens": _clean(sc.get("happens") or pick.get("after")),
              "first_frame_action": _clean(pick.get("first_frame_action")),
              "beats": beats}
    camera = {"shots": shots, "ends": ends, "beats": [{"beat": b["id"], "camera": b["camera"]} for b in beats if b["camera"]]}
    if tracked:
        camera["tracked"] = tracked
    if swipe:
        camera["swipe"] = [{"shot": s["shot"], "camera": s["camera"]} for s in swipe]
        motion["swipe"] = swipe
    plan = {"scene": sid, "kind": sc.get("kind"), "record": d.get("record") or f"director/picks.json#{sid}",
            "camera": camera, "motion": motion,
            "sources": ((["the swipe's motion pattern (frame map)"] if any(s.get("moments") for s in swipe)
                         else ["the swipe's camera (teardown table)"]) if swipe else []) + ["the director's pick (5d)"]}
    plan["words"] = words(plan)
    return plan, None


def words(plan: dict) -> str:
    """The block every clip prompt of the scene carries, word for word."""
    m, c = plan["motion"], plan["camera"]
    head = f"{BLOCK_HEAD} (the director's plan for {plan['scene']}" + (f", \"{m['title']}\"" if m.get("title") else "") + "):"
    cam = "; ".join(f"{s['shot']}: " + ", ".join(x for x in (s["angle"], s["move"]) if x)
                    + (f" ({s['why']})" if s.get("why") else "") for s in c["shots"])
    if c.get("ends"):
        cam += ("; " if cam else "") + "it ends " + c["ends"]
    if c.get("tracked"):
        cam += ("; " if cam else "") + "follow the tracked camera of the motion reference"
    sw = m.get("swipe") or []
    base = "; ".join(f"{p['shot']} — camera {p['camera'] or 'as filmed'}" + (
        ", moving at " + ", ".join(f"{x['at']} s {x['does']}" for x in p["moments"][:8]) if p["moments"] else "")
        for p in sw)
    lines = [head, ("The swipe's motion pattern, the base (timing and camera only; our people, place and product "
                    "act it): " + base + ".") if base else "", "Camera: " + cam + "." if cam else ""]
    if m.get("movement"):
        lines.append("Movement: " + m["movement"] + ".")
    beat = []
    for b in m["beats"]:
        what = b["action"] or " ".join(x for x in (b["who"], b["do"]) if x)
        bit = (f"{b['id']} " if b["id"] else "") + (f"over \"{b['over']}\": " if b["over"] else "") + what
        if b["camera"]:
            bit += f" (camera: {b['camera']})"
        beat.append(bit)
    lines.append("Beat by beat, each one moving: " + "; ".join(beat) + ".")
    return "\n".join(x for x in lines if x)


def _tracked(run: Path, sid: str) -> dict | None:
    """The motion chain's tracked camera for this scene in this run, when it has run on it."""
    f = Path(run) / "motion" / str(sid) / "motion" / "camera.json"
    rec = _read(f, None)
    return {"file": str(f.relative_to(run)), "from": "the motion chain's track"} if rec else None


def plan(run: Path, brief: Path | None = None) -> dict:
    """Write <run>/clips/camera-motion.json (+ CAMERA-MOTION.md) and return it."""
    run = Path(run)
    bp = brief_of(run, brief)
    if not bp:
        raise SystemExit("camera and motion: no brief for this run (run.json brief_from, or <run>/brief.md)")
    text = bp.read_text()
    doc = brief_doc(text)
    picks = picks_of(bp)
    try:
        import importlib.util as _iu
        _sp = _iu.spec_from_file_location("cm_swipe_use", Path(__file__).resolve().parent / "swipe_use.py")
        _su = _iu.module_from_spec(_sp); _sp.loader.exec_module(_su)
        swipe_off = _su.off(doc)
    except Exception as e:  # noqa: BLE001 — owner ruling 2026-11-20: retry then fail loudly: never a guessed "swipe on"
        raise SystemExit(f"camera and motion: the swipe-use rule could not load ({type(e).__name__}: {e}) — "
                         f"no plan is made on a guess")
    fm = {} if swipe_off else framemap_of(bp)
    rows = [] if swipe_off or fm else teardown_rows(bp)
    scenes, held = {}, {}
    for sc in doc.get("scenes") or []:
        sid = sc.get("id")
        if not sid or str(sc.get("kind") or "").lower() in NO_CLIP:
            continue
        pat = swipe_pattern(sc, fm) if fm else pattern_from_rows(sc, rows)
        p, why = scene_plan(sc, picks.get(sid), _tracked(run, sid), pat or None)
        if p:
            scenes[sid] = p
        else:
            held[sid] = why
    res = {"schema": "camera-motion/v1", "made": time.strftime("%Y-%m-%dT%H:%M:%S"), "brief": str(bp),
           "swipe_off": swipe_off,
           "brief_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
           "picks": bool(picks), "scenes": scenes, "held": held}
    (run / "clips").mkdir(parents=True, exist_ok=True)
    (run / "clips" / "camera-motion.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    (run / "clips" / "CAMERA-MOTION.md").write_text(render(res))
    return res


def render(res: dict) -> str:
    out = [f"# Camera and motion — {len(res['scenes'])} scene(s) planned, {len(res['held'])} held", "",
           "From the accepted brief and the director's 5d pick. Every clip prompt of a scene carries its block below; "
           "a clip without one is refused before anything is spent.", ""]
    for sid, p in res["scenes"].items():
        title = p["motion"].get("title") if isinstance(p["motion"].get("title"), str) else "split: " + ", ".join(p.get("sides") or [])
        out += [f"## {sid} · {title or ''}", "", "```", p["words"], "```", ""]
    for sid, why in res["held"].items():
        out += [f"## {sid} · HELD", "", why, ""]
    return "\n".join(out)


def _with_block(prompt: str, block: str) -> str:
    """The prompt with the block in it once: an older block is replaced; placed before the constants paragraph."""
    p = BLOCK_RE.sub("", prompt or "").rstrip()
    parts = p.split("\n\n")
    at = next((i for i, x in enumerate(parts) if x.startswith("Constant throughout")), len(parts))
    return "\n\n".join(parts[:at] + [block] + parts[at:])


def words_for(p: dict, call: dict) -> str:
    """A scene's block for one call. A split scene's call shows only the sides it has pictures for (its start picture
    is the scene's first shot; its shot pictures name the rest): only those sides' plans go into it, never a side the
    picture does not show (2026-11-20)."""
    if p.get("kind") != "split" or not p.get("side_words"):
        return p["words"]
    shown = {s.get("shot") for s in call.get("shot_pictures") or []}
    ss = p.get("side_shots") or {}
    first = next((ids[0] for side in p.get("sides") or [] for ids in [ss.get(side) or []] if ids), None)
    if str(call.get("start_frame") or "").startswith(str(p.get("scene")) + "-") or p.get("scene") in shown:
        shown.add(first)                    # the scene's own start picture opens its first shot
    sides = [side for side in p.get("sides") or [] if shown & set(ss.get(side) or [])]
    return "\n\n".join(p["side_words"][s] for s in sides) if sides else p["words"]


def bind_shot_pictures(prompt: str, shots: list) -> str:
    """The call's shot pictures named in its prompt, in the order they are sent: right after the start (and end)
    picture, before the reference pictures, which move down by as many. Already bound: unchanged."""
    if not shots or "the opening picture of shot" in (prompt or ""):
        return prompt
    lines = (prompt or "").split("\n")
    img = [i for i, ln in enumerate(lines) if re.match(r"Image \d+ is ", ln)]
    fixed = [i for i in img if re.match(r"Image [12] is the (first|last) frame", lines[i])]
    at = (max(fixed) + 1) if fixed else (img[0] + 1 if img else 0)
    base = len(fixed) or 1
    n = len(shots)
    for i in img:
        m = re.match(r"Image (\d+) is a reference", lines[i])
        if m:
            lines[i] = lines[i].replace(f"Image {m.group(1)} ", f"Image {int(m.group(1)) + n} ", 1)
    new = [f"Image {base + 1 + k} is the opening picture of shot {s['shot']}: {s.get('job') or 'the shot opens on it'}."
           for k, s in enumerate(shots)]
    return "\n".join(lines[:at] + new + lines[at:])


def apply(run: Path, files=("plan.json", "plan-only.json")) -> list[str]:
    """Stamp the clip plan(s) with the scenes' blocks. Returns the problems it added (one per call that lacks a plan)."""
    run = Path(run)
    cm = _read(run / "clips" / "camera-motion.json", None)
    added = []
    for name in files:
        f = run / "clips" / name
        res = _read(f, None)
        if not isinstance(res, dict) or not res.get("calls"):
            continue
        probs = [p for p in res.get("problems") or [] if not str(p).startswith(BLOCK_HEAD)]
        for c in res["calls"]:
            sids = [s for s in c.get("scenes") or [] if s]
            if not cm:
                why = "no camera and motion plan for this run (camera_motion.py plan)"
            else:
                miss = [s for s in sids if s not in cm["scenes"]]
                why = ("; ".join(f"{s}: " + (cm["held"].get(s) or "not in the plan") for s in miss)) if miss or not sids \
                    else None
                if not sids:
                    why = "the call names no scene"
            if why:
                c["camera_motion"] = {"ok": False, "why": why}
                probs.append(f"{BLOCK_HEAD}: {c.get('id')} ({c.get('section') or c.get('section_id')}) has no camera "
                             f"and motion plan — {why}")
                continue
            if cm.get("swipe_off"):
                import importlib.util as _iu
                _sp = _iu.spec_from_file_location("cm_swipe_use2", Path(__file__).resolve().parent / "swipe_use.py")
                _su = _iu.module_from_spec(_sp); _sp.loader.exec_module(_su)
                swiped = _su.swipe_refs_of_call(c)
                if swiped:
                    probs.append(f"{BLOCK_HEAD}: {c.get('id')} carries the swipe ({', '.join(map(str, swiped))[:200]}) — "
                                 f"an AI-lane clip is made from our creative only (swipe-use.json)")
            block = "\n\n".join(words_for(cm["scenes"][s], c) for s in sids)
            new = _with_block(bind_shot_pictures(c.get("prompt") or "", c.get("shot_pictures") or []), block)
            c["prompt"] = new
            if isinstance(c.get("seedance"), dict):
                c["seedance"]["prompt"] = new
            if isinstance(c.get("params"), dict):
                c["params"]["prompt"] = new
            c["camera_motion"] = {"ok": True, "scenes": sids, "brief_sha256": cm["brief_sha256"]}
        added += [p for p in probs if str(p).startswith(BLOCK_HEAD)]
        res["problems"] = probs
        f.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    return added


def missing(run: Path, name: str = "plan.json") -> list[str]:
    """Every call in the clip plan that does not carry its camera and motion plan: [] = every clip has one."""
    res = _read(Path(run) / "clips" / name, {}) or {}
    return [str(c.get("id")) for c in res.get("calls") or [] if not (c.get("camera_motion") or {}).get("ok")]


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("run"); p.add_argument("--brief")
    sub.add_parser("apply").add_argument("run")
    sub.add_parser("check").add_argument("run")
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        res = plan(Path(a.run), Path(a.brief) if a.brief else None)
        print(f"camera and motion: {len(res['scenes'])} scene(s) planned, {len(res['held'])} held — "
              f"{Path(a.run) / 'clips' / 'CAMERA-MOTION.md'}")
        for sid, why in res["held"].items():
            print(f"  HELD {sid}: {why}")
        return 0 if not res["held"] else 1
    if a.cmd == "apply":
        for x in apply(Path(a.run)):
            print("STOP " + x)
        return 0
    gone = missing(Path(a.run))
    for i in gone:
        print(f"REFUSED {i}: no camera and motion plan in its prompt")
    return 1 if gone else 0


if __name__ == "__main__":
    sys.exit(main())
