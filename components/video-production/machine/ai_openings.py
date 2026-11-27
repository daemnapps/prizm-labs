#!/usr/bin/env python3
"""THE AI LANE'S OPENINGS (2026-11-21, brief-0380): the brief's other openings made on the chain's own steps, each one
replacing the first scene of the chain's cut, so the ad files as one flexible ad (control + every opening).

Each opening is its own small run under <run>/hooks/<hNN>/ (hook_variations.prepare, unchanged), fed from the chain's
cut instead of a video-edit folder: the replacement boundary comes from edit/EDIT.json and the control is the cut file
named. Its start picture is a 3D set print (GATE-4: a set request per opening, printed by image-production's print
runner, never the still door); its voice is the speaker's banked voice with the control's own settings; its clip is one
paid take through the same clip checklist, clip gate and clip runner as the body; its cut is edit_scenes' as for the
body; the Studio lays it as a hook version that replaces the first scene.

    python3 ai_openings.py prepare <run> --control <the control cut .mp4>     free: the opening folders
    python3 ai_openings.py voices  <run>                                      ElevenLabs: each opening's line
    python3 ai_openings.py prints  <run> [--dry-run]                          free: one set request per opening
        then image-production's print runner prints them (paid, under its cap):
        python3 components/image-production/print_runner.py --brand <b> --run <label> --cap <credits> --yes
    python3 ai_openings.py take    <run>                                      free: each kept print -> its start picture
    python3 ai_openings.py clips   <run> --yes --cap <credits>                paid: one take of each opening's clip
    python3 ai_openings.py studio  <run> --production <Studio production>     free: hook versions in the Studio
    python3 ai_openings.py status  <run>

The openings' text and concept are the brief's (plan.json `hooks`); the moving opening is the control's own motion (the
first scene's direction), started on the opening's own picture. Brand-agnostic.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
SYSTEM = "the system (production on Auto in Outlier Settings)"


def _load(name):
    sp = importlib.util.spec_from_file_location("aio_" + name, HERE / (name + ".py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _read(p, d=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return d


def _write(p, data):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def _slug(t):
    return re.sub(r"[^a-z0-9]+", "-", str(t).lower()).strip("-")


def _queue():
    root = WS / "components" / "image-production"
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from image_production import set_queue, set_gate
    return set_queue, set_gate


def _brief_doc(run):
    rj = _read(Path(run) / "run.json", {}) or {}
    bf = Path(rj.get("brief_from") or Path(run) / "brief.md")
    bf = bf if bf.is_absolute() else WS / bf
    try:
        blocks = re.findall(r"```json\s*\n(.*?)\n```", bf.read_text(), re.S)
        return json.loads(blocks[-1]) if blocks else {}
    except (OSError, ValueError):
        return {}


def edit_map_of(run):
    """The chain's cut as the edit map the openings read: each scene's spoken span on the cut's clock."""
    edit = _read(Path(run) / "edit" / "EDIT.json", {}) or {}
    rows, at = [], 0.0
    for r in edit.get("scenes") or []:
        w = (_read(Path(run) / r["words"], {}) or {}).get("words") or []
        if w:
            rows.append({"scene": r["scene"], "a": round(at + float(w[0]["start"]), 3),
                         "b": round(at + float(w[-1]["end"]), 3), "who": None})
        at += float(r["seconds"])
    return {"voice": rows, "from": "edit/EDIT.json (the chain's cut)"}


def matrix_of(plan, doc):
    """Each opening's line, picture concept and moving event: the brief's hook text and thumb, moving as the control's
    first scene moves (its own direction), started on the opening's own picture."""
    hooks = plan.get("hooks") or []
    ctrl = next((h for h in hooks if str(h.get("take", "")).lower() == "control"), {}) or {}
    first = next((s for s in doc.get("scenes") or [] if s.get("id") == ctrl.get("opener_scene")), {}) or {}
    moving = str((first.get("first_frame") or {}).get("action") or first.get("happens") or "").strip()
    rows, n = [], 0
    for h in hooks:
        if h is ctrl:
            continue
        n += 1
        rows.append({"id": "V%d" % n, "line": h.get("text"), "thumb": h.get("thumb"),
                     "scroll": "%s It moves as the control opening moves: %s" % (h.get("thumb") or "", moving)})
    return {"openings": rows, "format_contract": "the control's own first scene, its line and picture replaced"}


def openings(run):
    return (_read(Path(run) / "hooks" / "index.json", {}) or {}).get("openings") or []


def folder(run, row):
    return Path(run) / "hooks" / row["id"]


def prepare(run, control):
    run, control = Path(run).resolve(), Path(control).resolve()
    if not control.is_file():
        raise SystemExit("no control cut at %s" % control)
    ed = run / "edit" / "openings-control"
    _write(ed / "edit-map.json", edit_map_of(run))
    _write(ed / "decisions.json", {"from": "the chain's cut (edit_scenes.py)"})
    (ed / "renders").mkdir(parents=True, exist_ok=True)
    dst = ed / "renders" / "control.mp4"
    if not dst.is_file() or dst.read_bytes() != control.read_bytes():
        shutil.copy2(control, dst)
    plan = _read(run / "plan.json", {}) or {}
    idx = _load("hook_variations").prepare(run, ed, WS, matrix_of(plan, _brief_doc(run)), batch="hooks")
    doc = _brief_doc(run)
    sh = next((s for s in doc.get("scenes") or [] if s.get("id") == "S1"), {}) or {}
    shot = (sh.get("shots") or [{}])[0] or {}
    for row in idx["openings"]:              # the control's own direction is the opening's motion
        motion = {k: shot[k] for k in ("face", "gestures", "camera_move", "emotion") if shot.get(k)}
        if not (folder(run, row) / "motion.json").is_file():
            _write(folder(run, row) / "motion.json", motion)
    return idx


def voices(run):
    HV = _load("hook_variations")
    return {row["id"]: HV.make_voice(folder(run, row)) for row in openings(run)}


def request_id(run, row):
    return "%s-%s-s1-f1" % (_slug(Path(run).name), row["id"])


def prints(run, dry=False):
    """One 3D set request per opening (GATE-4): the opening's picture concept, then the control's first picture's own
    words for the place, people, outfits, props, camera and light; the control's cast, looks and props."""
    run = Path(run)
    Q, _ = _queue()
    brand = (_read(run / "run.json", {}) or {}).get("brand")
    base = Q.read(brand, "%s-s1-f1" % _slug(run.name)) or {}
    if not base:
        raise SystemExit("the control's first picture has no set request to take its place, people and set from")
    out = []
    for row in openings(run):
        rid = request_id(run, row)
        words = ("THIS PICTURE (%s): %s Everything else is the control opening's picture, as below: the same place, "
                 "people, outfits, set, camera and light. %s" % (row.get("title"), row.get("thumbnail") or row.get("visual"),
                                                                 base.get("scene") or ""))
        if not dry:
            Q.file(brand, "Opening picture %s for %s: %s" % (row["id"], run.name, row.get("title")), name=rid,
                   scene=words, products=[p.get("kit") if isinstance(p, dict) else p for p in base.get("products") or []],
                   cast=base.get("cast") or [], props=base.get("props") or [], looks=base.get("looks") or {},
                   source="ai_openings.py (the AI lane's openings)",
                   resume={"tool": "video-production", "run": run.name, "picture": "%s/S1-F1" % row["id"],
                           "command": "python3 components/video-production/machine/ai_openings.py take %s" % run})
        out.append(rid)
    return out


def take(run):
    """Each opening's kept print is its start picture (copied, nothing generated): hooks/<hNN>/media/S1-F1.png."""
    run = Path(run)
    _, SG = _queue()
    brand = (_read(run / "run.json", {}) or {}).get("brand")
    got = {}
    for row in openings(run):
        rid = request_id(run, row)
        kp = SG.kept_print(brand, rid)
        if kp is None:
            got[row["id"]] = "waiting for its kept print (%s)" % rid
            continue
        f = folder(run, row)
        dst = f / "media" / "S1-F1.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(kp, dst)
        made = _read(f / "direct.json", {}) or {}
        made["S1-F1"] = {"file": str(dst), "model": "3d set print", "door": "3d-print", "taken_from": str(kp), "set": rid,
                         "record": "runs/image-production/%s/sets/%s/set.json" % (brand, rid),
                         "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "note": "the kept 3D set print is the picture"}
        _write(f / "direct.json", made)
        got[row["id"]] = str(kp)
    return got


def _plan(op):
    """The opening's clip plan in the clip runner's shape (route, totals), from hook_variations.plan_clip."""
    call = _load("hook_variations").plan_clip(op, WS)
    # the control's swipe folder rides with each opening's storyboard (the clip gate's PATHS check reads it)
    parent0 = WS / (_read(op / "opening.json", {}) or {})["source"]["source_run"]
    sb = _read(op / "storyboard.json", {}) or {}
    td = (_read(parent0 / "storyboard.json", {}) or {}).get("teardown")
    if td and not sb.get("teardown"):
        _write(op / "storyboard.json", dict(sb, teardown=td))
    # the request as it is sent, the body planner's shape (clips_run: prompt, duration, aspect, resolution); the
    # clip gate holds a call whose shown words are not its sent words
    pp = next((c.get("params") for c in (_read(WS / (_read(op / "opening.json", {}) or {})["source"]["source_run"]
                                                / "clips" / "plan.json", {}) or {}).get("calls") or []
               if "S1" in (c.get("scenes") or []) and c.get("params")), {}) or {}
    call["params"] = {"prompt": call.get("prompt"), "duration": call.get("duration"),
                      "aspect_ratio": pp.get("aspect_ratio", "9:16"), "resolution": call.get("resolution") or pp.get("resolution")}
    secs = int(call.get("duration") or 0)
    usd = float(call.get("usd") or 0)
    res = _read(op / "clips" / "plan.json", {}) or {}
    res.update(route="seedance", format=None, calls=[call], tts=[], problems=[],
               totals={"calls": 1, "clip_seconds": secs, "clip_usd": usd, "upscale_seconds": 0, "upscale_usd": 0.0,
                       "talking_calls": 1, "voice_swaps": 1, "tts_lines": 0, "tts_chars": 0, "spend_usd": usd,
                       "takes": 1, "usd_all_takes": usd, "max_tries": 1, "usd_worst": usd})
    # the control's own camera plan for its first scene (the director's camera lines only: its beats were timed to
    # the control's words), then the clip rules every body clip carries, then the movement pieces cut (local, free)
    parent = WS / (_read(op / "opening.json", {}) or {})["source"]["source_run"]
    pc = next((c for c in (_read(parent / "clips" / "plan.json", {}) or {}).get("calls") or []
               if "S1" in (c.get("scenes") or [])), {}) or {}
    cam = next((p for p in str(pc.get("prompt") or "").split("\n\n") if p.startswith("CAMERA AND MOTION")), "")
    cam = "\n".join(ln for ln in cam.split("\n") if ln.startswith(("CAMERA AND MOTION", "Camera:")))
    if cam and "CAMERA AND MOTION" not in (call.get("prompt") or ""):
        paras = (call.get("prompt") or "").split("\n\n")
        at = next((i for i, x in enumerate(paras) if x.startswith("Constant throughout")), len(paras))
        call["prompt"] = "\n\n".join(paras[:at] + [cam] + paras[at:])
        if isinstance(call.get("seedance"), dict):
            call["seedance"]["prompt"] = call["prompt"]
    cm = _read(parent / "clips" / "camera-motion.json", {}) or {}
    _write(op / "clips" / "camera-motion.json", {**cm, "scenes": {"S1": (cm.get("scenes") or {}).get("S1") or {}}})
    _write(op / "clips" / "plan.json", res)
    _load("clip_rules").apply(op)
    CR = _load("clips_run")
    CR.build_refs(op, res["calls"], CR.route_cfg(), WS)
    return (_read(op / "clips" / "plan.json", {}) or {}).get("calls", [call])[0]


def clips(run, yes=False, cap=None, rate=3.25):
    """One paid take of each opening's clip, through the body's own checklist, gate and runner; the cap counts what this
    pass sends (seconds x rate) and stops before an opening that would pass it. A refused clip is a gap."""
    run = Path(run)
    CK, CG, CR = _load("clip_checklist"), _load("clip_gate"), _load("clips_run")
    spent, out = 0.0, {}
    for row in openings(run):
        op = folder(run, row)
        if (op / "clips" / "G01-C1.mp4").is_file():
            out[row["id"]] = "made"
            continue
        if not (op / "media" / "S1-F1.png").is_file() or not (op / "vo" / "S1.mp3").is_file():
            out[row["id"]] = "not ready: needs its kept print (take) and its voice (voices)"
            continue
        call = _plan(op)
        est = round(max(4, int(call.get("duration") or 4)) * rate, 1)
        if cap is not None and spent + est > cap:
            out[row["id"]] = "STOP at the cap: %s of %s credits sent, this opening needs about %s" % (spent, cap, est)
            break
        bad = CK.build(op)
        CG.check(op)
        CG.approve(op, SYSTEM)
        red = [x for r in (CG.check(op).get("calls") or []) for x in r.get("red") or []]
        if bad or red:
            out[row["id"]] = "held: " + "; ".join((bad + red)[:4])
            continue
        if not yes:
            out[row["id"]] = "ready, about %s credits (run with --yes to make it)" % est
            continue
        rc = CR.run_live(op, yes=True)
        spent += est
        out[row["id"]] = "made" if (op / "clips" / "G01-C1.mp4").is_file() else "not made (rc %s; clips/ledger.json)" % rc
        if out[row["id"]] == "made":
            _load("edit_scenes").build(op)
    return out


def studio(run, production):
    """Each made opening as a Studio hook version: scenes/<hNN>/take-1.json replacing the first scene, laid from the
    opening's own cut (edit_scenes) the way the body's scenes are; brief.json `hooks` names them."""
    sv = WS / "components" / "video-studio"
    if str(sv) not in sys.path:
        sys.path.insert(0, str(sv))
    import ai_shots as A
    import settings as ST
    B = ST.BRIEFS / production
    brief = json.loads((B / "brief.json").read_text())
    done = []
    for row in openings(run):
        op = folder(run, row)
        edit = _read(op / "edit" / "EDIT.json", {}) or {}
        if not edit.get("scenes"):
            continue
        hid = "H%s" % row["id"][1:].lstrip("0")
        tf = B / "scenes" / hid / "take-1.json"
        tf.parent.mkdir(parents=True, exist_ok=True)
        if not tf.is_file():
            # the Studio's full take shape (schema, brief, scene, take, title, lane, roll, pictures, clock, words,
            # subjects), taken from the first scene's own take, the opening's title and line on it (2026-11-21: a take
            # with only its steps stopped the version render at its `title`)
            s1 = _read(B / "scenes" / "S1" / ((brief.get("picks") or {}).get("S1", "take-1") + ".json"), {}) or {}
            take = {k: v for k, v in s1.items() if k not in ("steps", "sources", "from")}
            take.update(scene=hid, take="take-1", title=row.get("title") or hid, words=row.get("text") or "",
                        replaces="S1", steps=[], sources={},
                        note="opening %s: %s" % (row["id"], row.get("title")))
            tf.write_text(json.dumps(take, indent=1, ensure_ascii=False))
        brief.setdefault("picks", {})[hid] = "take-1"
        A.lay_edit(B, brief, hid, edit["scenes"], op)
        wf = json.loads(tf.read_text())
        wf["replaces"] = "S1"
        tf.write_text(json.dumps(wf, indent=1, ensure_ascii=False))
        if hid not in (brief.get("hooks") or []):
            brief.setdefault("hooks", []).append(hid)
        done.append(hid)
    (B / "brief.json").write_text(json.dumps(brief, indent=1, ensure_ascii=False))
    return done


def status(run):
    run = Path(run)
    _, SG = _queue()
    brand = (_read(run / "run.json", {}) or {}).get("brand")
    rows = []
    for row in openings(run):
        op = folder(run, row)
        rows.append({"id": row["id"], "title": row.get("title"),
                     "voice": (op / "vo" / "S1.mp3").is_file(),
                     "print": SG.kept_print(brand, request_id(run, row)) is not None,
                     "picture": (op / "media" / "S1-F1.png").is_file(),
                     "clip": (op / "clips" / "G01-C1.mp4").is_file(),
                     "cut": (op / "edit" / "EDIT.json").is_file()})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["prepare", "voices", "prints", "take", "clips", "studio", "status"])
    ap.add_argument("run")
    ap.add_argument("--control")
    ap.add_argument("--production")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--cap", type=float)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    run = Path(a.run).resolve()
    if a.cmd == "prepare":
        if not a.control:
            ap.error("prepare needs --control <the control cut>")
        res = prepare(run, a.control)
        res = [(r["id"], r.get("title")) for r in res["openings"]]
    elif a.cmd == "voices":
        res = voices(run)
    elif a.cmd == "prints":
        res = prints(run, a.dry_run)
    elif a.cmd == "take":
        res = take(run)
    elif a.cmd == "clips":
        res = clips(run, a.yes, a.cap)
    elif a.cmd == "studio":
        if not a.production:
            ap.error("studio needs --production <the Studio production>")
        res = studio(run, a.production)
    else:
        res = status(run)
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
