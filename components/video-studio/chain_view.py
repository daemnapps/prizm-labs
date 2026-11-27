#!/usr/bin/env python3
"""The production chain's run, read for the Studio's Production page (owner rule, 20 Nov 2026: video work is always
shown in the Video Studio; the Studio shows the chain, it never does the chain's work).

Read-only. For a Studio production it finds the brief's chain run (components/video-production/machine/ai_lane.py):
the live run when it has a storyboard, else the dry run's sealed shadow. It reads only the chain's own files:

    dry-run/dry-run.json        every station's state and what it said, and the quote (dry run)
    ai_lane.py status           every station's state (live run)
    clips/camera-motion.json    per scene: our idea (the director's pick), each shot's camera (angle · move · why)
                                and the swipe shot it builds on, the swipe's motion pattern, the motion beats
    storyboard.json             the sections, their seconds and which swipe shots they copy
    BUDGET.md                   the budget's headline line

No production logic: nothing here plans, makes, checks or writes anything. No brand, product or person is named here.
"""
import json
import re
from pathlib import Path

import settings as ST

LANE = ST.chain("video-production", "ai_lane")


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def run_of(brief: dict):
    """(resolved run record, the run folder shown, 'live' | 'dry run') for a production's brief, or (None, None, why)."""
    wr = brief.get("brief") or brief.get("run")
    if not wr:
        return None, None, "this production names no writing run"
    try:
        r = LANE.resolve(wr)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        return None, None, "the chain cannot read this brief: " + str(e)[:160]
    live = LANE.run_dir(r)
    shadow = live / "dry-run" / "video-production" / r["brand"] / r["label"]
    if (live / "storyboard.json").is_file() or pictures_of(live):
        return r, live, "live"
    if (shadow / "storyboard.json").is_file() or (live / "dry-run" / "dry-run.json").is_file():
        return r, shadow, "dry run"
    return r, None, "the chain has not run on this brief yet"


def budget_line(run: Path) -> str:
    try:
        t = (run / "BUDGET.md").read_text()
    except OSError:
        return ""
    m = re.search(r"^\*\*Key:\*\*\s*(.+)$", t, re.M)
    return m.group(1).strip() if m else ""


def scene_view(p: dict) -> dict:
    """One scene's plan as the card shows it."""
    m, c = p.get("motion") or {}, p.get("camera") or {}
    if p.get("kind") == "split":                       # each side its own shots and beats
        sides = p.get("sides") or []
        shots = [dict(s, side=side) for side in sides for s in (c.get(side) or {}).get("shots") or []]
        beats = [dict(b, side=side) for side in sides for b in (m.get(side) or {}).get("beats") or []]
        title = "split: " + " · ".join(sides)
        swipe = []
    else:
        shots, beats, title, swipe = c.get("shots") or [], m.get("beats") or [], m.get("title") or "", m.get("swipe") or []
    return {"title": title, "premise": m.get("premise") or "", "movement": m.get("movement") or "",
            "sources": p.get("sources") or [],
            "shots": [{"shot": s.get("shot"), "angle": s.get("angle") or "", "move": s.get("move") or "",
                       "why": s.get("why") or "", "copies": s.get("copies") or "", "side": s.get("side")}
                      for s in shots],
            "swipe": [{"shot": x.get("shot"), "camera": x.get("camera") or "",
                       "moments": [{"at": y.get("at"), "does": y.get("does")} for y in x.get("moments") or []][:8]}
                      for x in swipe],
            "beats": [{"id": b.get("id"), "over": b.get("over") or "", "do": b.get("do") or "",
                       "action": b.get("action") or "", "camera": b.get("camera") or "", "side": b.get("side")}
                      for b in beats],
            "ends": c.get("ends") or ""}


def _brief_doc(r) -> dict:
    try:
        text = Path(r["brief"]).read_text()
        blocks = re.findall(r"```json\s*\n(.*?)\n```", text, re.S)
        return json.loads(blocks[-1]) if blocks else {}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def speaker_voice(brief: dict):
    """THE SPEAKER'S OWN BANKED VOICE (owner, 2026-11-20: a character speaks in their own saved voice, never the brand
    voice): the brief's main speaker (the cast member who speaks the most scenes) and their voice from the casting bank,
    runs/ai-elements/<brand>/casting/<bank>/voice.json — the one place the chain reads it too. {voice_id, voice, settings}
    or None."""
    r, _, _ = run_of(brief)
    if not r:
        return None
    doc = _brief_doc(r)
    bank = {str(c.get("id")).lower(): c.get("bank_id") or c.get("id") for c in doc.get("cast") or []}
    said = {}
    for sc in doc.get("scenes") or []:
        sp = str(sc.get("speaker") or "").lower()
        if sp in bank:
            said[sp] = said.get(sp, 0) + 1
    for who in sorted(said, key=lambda k: -said[k]):
        f = ST.REPO / "runs" / "ai-elements" / str(r.get("brand")) / "casting" / str(bank[who]) / "voice.json"
        v = _load(f, {}) or {}
        if v.get("voice_id"):
            return {"voice_id": v["voice_id"], "voice": v.get("name") or who, "settings": v.get("settings"),
                    "from": str(f.relative_to(ST.REPO))}
    return None


IMG = (".png", ".jpg", ".jpeg", ".webp")


def pictures_of(run: Path) -> dict:
    """{key: file} for every start picture the run has made or taken (its direct.json), and every picture a clip call
    will send (`in-<call>-<n>`, read from clips/plan.json), when the file is there. Only these files are served."""
    made = _load(run / "direct.json", {}) or {}
    out = {k: v.get("file") for k, v in made.items()
           if isinstance(v, dict) and v.get("file") and Path(v["file"]).is_file()
           and str(v["file"]).lower().endswith(IMG)}
    for c in call_inputs(run, out):
        for i in c["inputs"]:
            if i.get("key"):
                out[i["key"]] = i["file"]
    return out


def _label(rel: str, job: str) -> tuple:
    """(kind, label) of one reference picture, by where it lives."""
    r = rel.lower()
    name = Path(rel).parent.name if Path(rel).parent.name not in ("sheets", "model", "formula") else ""
    if "-formula." in r or "/formula/" in r:
        return "texture", "texture sheet · " + rel.split("/products/")[-1].split("/")[0]
    if "/products/" in r:
        return "product", "product casting sheet · " + rel.split("/products/")[-1].split("/")[0]
    if "/casting/" in r:
        who = rel.split("/casting/")[-1].split("/")[0]
        return "person", who + " · " + Path(rel).stem.replace("-", " ")
    if "/props/" in r:
        return "prop", "prop · " + (name or Path(rel).stem).replace("-", " ")
    return "other", (job or Path(rel).name)[:60]


def call_inputs(run: Path, made=None) -> list:
    """Every clip call of the run's plan with every input it will send, in send order: the start picture, the shot
    pictures, the reference pictures (people, product casting sheet, texture sheet, props), the movement videos and
    the voice. Read from clips/plan.json; nothing is made."""
    plan = _load(run / "clips" / "plan.json", {}) or {}
    made = made if made is not None else {}
    ws = ST.REPO
    out = []
    for c in plan.get("calls") or []:
        cid = str(c.get("id") or "")
        ins = []
        start = str(c.get("start_frame") or "")
        sf = made.get(start) or next((str(f) for f in (run / "media" / (start + e) for e in IMG) if f.is_file()), None)
        ins.append({"kind": "start", "label": "start picture · " + start, "file": sf})
        for sp in c.get("shot_pictures") or []:
            ins.append({"kind": "shot", "label": "shot picture · " + str(sp.get("shot")), "file": str(ws / sp["file"])})
        for r in c.get("image_refs") or []:
            kind, label = _label(str(r.get("file") or ""), str(r.get("job") or ""))
            ins.append({"kind": kind, "label": label, "file": str(ws / str(r.get("file") or ""))})
        for v in c.get("refs") or []:
            if v.get("file"):
                ins.append({"kind": "movement", "label": "movement video · " + Path(str(v["file"])).stem, "file": None})
        if c.get("talking"):
            ins.append({"kind": "voice", "label": "voice · the scene's locked read", "file": None})
        for n, i in enumerate(ins, 1):
            i["n"] = n
            f = i.get("file")
            if f and Path(f).is_file() and str(f).lower().endswith(IMG) and re.fullmatch(r"[\w.-]+", cid):
                i["key"] = "in-%s-%d" % (cid, n)
            else:
                i["key"] = None
            i.pop("file", None) if i["kind"] in ("movement", "voice") else None
        refs = [i for i in ins if i["kind"] in ("person", "product", "texture", "prop")]
        probs = [p for p in plan.get("problems") or [] if cid and cid in str(p)]
        warn = None
        if not refs and (c.get("people") or c.get("talking") or any("RULE 11" in p or "RULE 12" in p for p in probs)):
            warn = "no casting sheets, product sheet or props go with this clip"
        ck = (_load(run / "clips" / "checklists.json", {}) or {}).get(cid) or {}
        out.append({"id": cid, "scenes": c.get("scenes") or [], "talking": bool(c.get("talking")),
                    "render": bool(c.get("render")), "inputs": ins, "warn": warn, "problems": probs,
                    "checklist": ck.get("rows") or [], "checked": ck.get("ok") if ck else None})
    return out


def cast_of(doc: dict, sc: dict) -> list:
    """The scene's people as the brief casts them: [{id, bank}], ours (the cast bank), never the swipe's."""
    bank = {str(c.get("id")).lower(): c.get("bank_id") or c.get("id") for c in doc.get("cast") or []}
    ids = list((sc.get("looks") or {}).keys()) or [x for x in re.split(r"\W+", str(sc.get("who") or "").lower()) if x in bank]
    return [{"id": i, "bank": bank.get(str(i).lower(), i)} for i in dict.fromkeys(ids)]


def headshot(brand: str, bank: str):
    """A cast member's headshot from the cast bank (runs/ai-elements/<brand>/casting/<bank>/), or None."""
    if not re.fullmatch(r"[a-z0-9-]+", str(bank or "")) or not re.fullmatch(r"[a-z0-9-]+", str(brand or "")):
        return None
    home = ST.REPO / "runs" / "ai-elements" / brand / "casting" / bank
    for f in (home / "sheets" / "headshot.jpg", home / "sheets" / "headshot-crop.jpg", home / "master.jpg",
              home / "master.png"):
        if f.is_file():
            return str(f)
    return None


def view(n: str, brief: dict) -> dict:
    """Everything the Production page shows of the chain's run, read from the chain's files."""
    r, run, mode = run_of(brief)
    out = {"production": n, "mode": mode if run else None, "why": None if run else mode, "stations": [], "quote": None,
           "budget": "", "scenes": {}, "sections": [], "label": (r or {}).get("label"), "live_command": None}
    if not run:
        return out
    if mode == "dry run":
        dr = _load(run.parents[2] / "dry-run.json", {}) or {}
        out["stations"] = [{"id": s.get("station"), "state": s.get("state"), "said": s.get("said") or ""}
                           for s in dr.get("stations") or []]
        out["quote"] = dr.get("quote")
        out["live_command"] = dr.get("live")
        out["at"] = dr.get("at")
    else:
        try:
            stt = LANE.status(r)
            out["stations"] = [{"id": s["id"], "state": "done" if s["done"] else "waiting", "said": s["name"]}
                               for s in stt.get("stations") or []]
        except Exception as e:  # noqa: BLE001
            out["stations"] = [{"id": "status", "state": "stopped", "said": str(e)[:160]}]
        dr = _load(run / "dry-run" / "dry-run.json", {}) or {}
        out["quote"] = dr.get("quote")
    # the live run's own plan files once it has them; until then the dry run's (said as such)
    shadow = LANE.run_dir(r) / "dry-run" / "video-production" / r["brand"] / r["label"]
    def pick(rel):
        return run / rel if (run / rel).is_file() or mode == "dry run" else shadow / rel
    out["plan_from"] = "live" if (run / "clips" / "camera-motion.json").is_file() or mode == "dry run" else "dry run"
    out["budget"] = budget_line(pick("BUDGET.md").parent)
    cm = _load(pick("clips/camera-motion.json"), {}) or {}
    out["scenes"] = {sid: scene_view(p) for sid, p in (cm.get("scenes") or {}).items()}
    # our start picture for each scene (the run's own, once made or taken) and our cast for it, from the brief
    pics = pictures_of(run)
    doc = _brief_doc(r)
    out["brand"] = r.get("brand")
    for sc in doc.get("scenes") or []:
        sid = sc.get("id")
        if not sid:
            continue
        row = out["scenes"].setdefault(sid, {"title": "", "premise": "", "movement": "", "sources": [], "shots": [],
                                              "swipe": [], "beats": [], "ends": "", "unplanned": True})
        row["picture"] = next((k for k in (sid + "-F1", sid + "-PLATE", sid + "-ENDCARD") if k in pics), None)
        row["cast"] = cast_of(doc, sc)
    out["held"] = cm.get("held") or {}
    # every clip call's inputs, in send order, before anything is made (owner: the take's inputs laid out)
    out["calls"] = [dict(c, inputs=[{k: v for k, v in i.items() if k != "file"} for i in c["inputs"]])
                    for c in call_inputs(run, pics)] if mode != "dry run" else []
    sb = _load(pick("storyboard.json"), {}) or {}
    out["sections"] = [{"id": g.get("id"), "scenes": g.get("scenes") or [], "seconds": g.get("seconds"),
                        "maker": g.get("maker"), "swipe": [k.get("id") for k in (g.get("swipe") or {}).get("shots") or []]}
                       for g in sb.get("sections") or []]
    out["writing_run"] = (r or {}).get("writing_run")
    return out


def swipe_still(brief: dict, k: str):
    """The swipe shot's middle still from the writing run's frame map (the picture a shot builds on), or None."""
    if not re.fullmatch(r"K\d{1,3}", str(k or "")):
        return None
    r, _, _ = run_of(brief)
    if not r:
        return None
    shots = Path(r["writing_run"]) / "framemap" / "shots"
    for name in (k + "-mid.jpg", k + "-first.jpg", k + "-camera.jpg"):
        f = shots / name
        if f.is_file():
            return str(f)
    return None
