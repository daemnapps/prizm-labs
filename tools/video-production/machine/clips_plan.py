"""CLIPS FROM THE STORYBOARD (2026-10-02) — the step after the pictures.

`run.py start … --storyboard` made a start (and end) picture per section and
the owner approved them. This step plans exactly the clips storyboard.json
calls for, and nothing else:

  * every clip starts from an APPROVED picture already in media/ — a picture
    is never made again here; one that is missing stops the step, named;
  * NO HAND-OFFS FOR PEOPLE (the owner, 2026-10-03, providers.json
    ruling_2026_10_03_no_handoffs): a section with a person on screen starts
    EVERY clip from its approved picture, never from the clip before's last
    frame (17 of 17 clips from the approved picture held the face; 10 of 10
    handed-on clips drifted, worse each hop). Only a section with nobody in it
    starts a later clip from the real last frame of the clip before (pulled
    when it lands, `<clip>-LAST.png`), so those go in a later batch;
  * the end picture is attached only where the storyboard has one;
  * the voice is the recordings already in vo/ (never re-recorded): the lines
    said ON CAMERA travel as the clip's audio, everything else is silence on
    that track — the full read is laid under the picture at the edit;
  * a motion-transfer section carries the swipe's own footage of its span
    (the teardown's frame-map shot clips) as the motion reference; a second
    picture the storyboard made for another camera set-up inside the section
    (a cutaway) is its own clip, from that picture, over the shots it drives;
  * plates, cards and the endcard get no clip unless the storyboard gives
    them one; a section the storyboard marks `reuses` is not made twice;
  * the model is ONLY the ruled clip door (providers.json doors.<station>),
    checked through run.py's ruled_model lock;
  * every prompt is built from the brief's scenes the way every clip prompt is
    (model_inputs.clip_blocks — the four blocks), plus the frame rule
    `swipe_motion` from model-inputs.json, and written out verbatim to
    <run>/clips/PROMPTS.md;
  * cost: each clip's billed seconds × the door's rate, the TOTAL in the
    house format (platform.print_plan); sent in batches of the provider's
    batch_max.

When clips come back (`run.py record`), `after_record` pulls the last frames
the next clips start from and runs the clip review (marketing-chain-checks
review.after_stage), the same way the picture review runs.

Brand-agnostic: every name, file and word comes from the run's own files.
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# how hard the swipe footage is blurred before a clip model sees it: faces and words
# unreadable, the movement and the camera kept (the same idea as <K>-camera.jpg for pictures)
MOTION_BLUR = 30
GAP = 0.15          # between two lines on one clip — the storyboard's own gap (storyboard_plan.clips_of)
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_clips_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mi = _load("model_inputs")
platform = _load("platform")
sbp = _load("storyboard_plan")


def _read(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _rule(name: str) -> dict:
    return dict(((mi.contract().get("frame_rules") or {}).get(name)) or {})


# ------------------------------------------------------------ the pictures

def picture_ids(g: dict) -> dict:
    """The ids picture_jobs gave this section's pictures — the start, the end
    (when the storyboard has one) and any own picture for another set-up
    inside the section, with the swipe shots each drives."""
    out = {"start": None, "end": None, "own": [], "drives": [], "setups": []}
    shots = {k["id"]: k for k in (g.get("swipe") or {}).get("shots") or []}
    for f in g.get("frames") or []:
        w, sid = f.get("what", ""), f.get("from")
        if w == "card background":
            out["start"] = out["start"] or f"{sid}-PLATE"
        elif w.startswith("endcard"):
            out["start"] = out["start"] or (f"{sid}-ENDCARD" if w == "endcard plate" else f"{sid}-PACKSHOT")
        elif w == "end frame":
            out["end"] = f"{sid}-FLAST"
        elif w == "end frame (own picture)":
            out["end"] = f"{sid}-F1"
        elif w == "set-up frame":
            out.setdefault("setups", []).append({"scene": sid, "id": f"{sid}-F1"})
        elif f.get("own"):
            k = shots.get(f.get("copies")) or {}
            kind = re.sub(r"[^A-Z]", "", str(k.get("type", "shot")).upper())[:8]
            out["own"].append({"id": f"{sid}-{kind}-{k.get('id')}", "copies": f.get("copies"),
                               "drives": list(f.get("drives") or [f.get("copies")])})
        else:
            out["start"] = out["start"] or f"{sid}-F1"
            out["drives"] = list(f.get("drives") or [])
    return out


def section_people(g: dict) -> list[str]:
    """Our people on screen in a section (its `person · <id> · <look>` elements)."""
    return [e.split(" · ")[1] for e in g.get("elements") or [] if str(e).startswith("person · ")]


def no_handoff_breaks(jobs: list[dict], sections: dict) -> list[str]:
    """The guard: a clip with a person on screen that would start from a made
    frame (a clip's `-LAST`) is a stop, named — whatever planned it."""
    out = []
    for j in jobs:
        g = sections.get(j.get("section_id") or "") or {}
        if str(j.get("start_frame") or "").endswith("-LAST") and (j.get("characters") or section_people(g)):
            out.append(f"{j['id']}: a person is on screen but the clip would start from {j['start_frame']} — "
                       "a person's clip starts from the approved picture, never a clip's last frame (3 Oct)")
    return out


def picture_file(run: Path, iid: str) -> Path | None:
    made = (_read(run / "direct.json", {}) or {}).get(iid) or {}
    if made.get("file") and Path(made["file"]).is_file():
        return Path(made["file"])
    for ext in IMG_EXT:
        f = run / "media" / f"{iid}{ext}"
        if f.is_file():
            return f
    return None


# ------------------------------------------------------------ the clock

def section_clock(g: dict) -> dict:
    """{scene: (start, end)} on the section's own clock — the recorded lines
    one after another, GAP between them (the storyboard's own arithmetic)."""
    out, t = {}, 0.0
    for sid in g.get("scenes") or []:
        sec = float((g.get("voice") or {}).get(sid) or 0)
        if not sec:
            continue
        if out:
            t += GAP
        out[sid] = (round(t, 2), round(t + sec, 2))
        t += sec
    return out


def voice_file(g: dict, sid: str) -> str | None:
    """The recording a line plays from — found by its words at the storyboard
    (`voice_from`); a line only ESTIMATED from part of another take has no take
    of its own, and is never cut from one here."""
    how = str((g.get("voice_from") or {}).get(sid) or "")
    if how == "recorded":
        return f"vo/{sid}.mp3"
    m = re.match(r"recorded as (\S+)$", how)
    return f"vo/{m.group(1)}.mp3" if m else None


def shot_windows(g: dict) -> list[tuple[str, float, float]]:
    """Each swipe shot of the section on OUR clock: (id, from, to)."""
    shots = (g.get("swipe") or {}).get("shots") or []
    total = float(g.get("seconds") or 0)
    out = []
    for i, k in enumerate(shots):
        a = float(k.get("at") or 0)
        b = float(shots[i + 1].get("at") or total) if i + 1 < len(shots) else total
        out.append((k["id"], a, max(a, b)))
    return out


# ------------------------------------------------------------ the prompt

def _who(s: dict) -> str:
    return " ".join(str(s.get("who") or "").split("·")[0].split())


def merged_scene(cid: str, scs: list[dict], clock: dict, t0: float, t1: float,
                 timing: dict | None, first_override: dict | None = None,
                 end_attached: bool = False, talking: bool = False) -> dict:
    """The clip's scenes as ONE scene in the brief's own shape, so the clip
    prompt is assembled exactly the way every clip prompt is: the first frame
    of its first scene, the last frame of its last, every beat on the clip's
    own clock (each scene's beat spans, read off its recording, moved to where
    that line sits in the clip)."""
    first = dict(mi.frame_of(scs[0], "first"))
    if first_override:
        first.update(first_override)
    last = dict(mi.frame_of(scs[-1], "last"))
    beats = []
    for s in scs:
        a, z = clock.get(s["id"], (None, None))
        sec = (z - a) if a is not None else None
        wins = mi.beat_windows(s, sec, timing)
        if sec and any(y <= x or x < -0.05 or y > sec + 0.05 for x, y in wins):
            # the read's line times do not sit inside this recording (a take
            # moved by its words keeps its old times) — the beats share the
            # recording's real length instead
            wins = mi.beat_windows(s, sec, None)
        base = a if a is not None else t0
        for b, (x, y) in zip(mi.beats_of(s), wins):
            x, y = max(0.0, x) + base, max(0.0, y) + base
            if y <= t0 or x >= t1:
                continue                                  # outside this clip's window
            beats.append({**b, "at": [round(max(x, t0) - t0, 2), round(min(y, t1) - t0, 2)]})
    beats.sort(key=lambda b: b["at"][0])
    talkers = []
    for s in scs:
        w = _who(s)
        if s.get("to_camera") and (s.get("voice") or "").strip() and w and w not in talkers:
            talkers.append(w)
    happens = []
    for s in scs:
        h = " ".join(str(s.get("happens") or "").split())
        if h and h not in happens:
            happens.append(h)
    everyone = []
    for s in scs:
        w = _who(s)
        if w and w not in everyone:
            everyone.append(w)
    return {"id": cid, "setting": scs[0].get("setting"),
            "who": " and ".join(talkers) if talking and talkers else _who(scs[0]),
            "who_all": " and ".join(everyone),
            "happens": ", then ".join(happens),
            "to_camera": talking, "end_frame_attached": end_attached,
            "frames": [{**first, "role": "first"}, {**last, "role": "last"}],
            "beats": beats}


def clip_prompt(scene: dict, piece: dict | None, seconds: float, talking: bool,
                motion: bool) -> tuple[str, list[str]]:
    """(the prompt, what is missing). The four blocks from the contract; a
    motion-transfer clip also carries the `swipe_motion` frame rule and its
    camera words (the camera moves as the swipe's footage does)."""
    blocks, missing = mi.clip_blocks(scene, piece, seconds, None, talking)
    if missing:
        return "", missing
    if scene.get("who_all") and scene["who_all"] != scene.get("who"):
        # the summary names everyone the clip shows; @Audio1 names only who speaks on camera
        summary, _ = mi.summary_of({**scene, "who": scene["who_all"]}, piece)
        blocks[1] = summary or blocks[1]
    # the approved picture IS the first frame: the words never restate its framing
    # (2026-10-02: the brief's "close-up" made Seedance zoom past the picture)
    keep = _rule("first_frame_kept").get("says")
    if keep and blocks[0].startswith("@Image1"):
        audio_at = blocks[0].find("@Audio1")
        blocks[0] = keep + ((" " + blocks[0][audio_at:]) if audio_at > 0 else "")
    if motion:
        rule = _rule("swipe_motion")
        if not rule.get("says"):
            return "", ["model-inputs.json frame_rules.swipe_motion (the motion-reference rule)"]
        phrase, sentence, _ = mi.camera_of(scene)
        if phrase and rule.get("camera_phrase"):
            blocks[1] = blocks[1].replace(phrase, rule["camera_phrase"])
        if sentence and rule.get("camera_sentence"):
            blocks[3] = blocks[3].replace(sentence, rule["camera_sentence"])
        blocks[0] = blocks[0] + " " + rule["says"]
    return mi.clip_shape().get("separator", "\n\n").join(blocks), []


# ------------------------------------------------------------ the plan

def _station(talking: bool) -> str:
    return "talking" if talking else "motion"


def _door(station: str, reg: dict, ruled=None, pick: str | None = None) -> dict:
    slug = mi.model_of(station)
    if ruled is not None:
        ruled(reg, station, pick or slug)      # THE MODEL LOCK — a pick that is not the ruled model stops here
    return {"model": slug, "door": mi.door_of(station).get("id"),
            "params": mi.door_params(station), "resolution": mi.fixed_resolution(station),
            "span": mi.duration_span(station) or [4, 15]}


def _job(cid, g, n, scs, clock, t0, t1, start, end, after, motion_shots, run, timing,
         piece, reg, ruled, pick, first_override=None, kind_of_clip="clip"):
    """One clip, in the item shape the rest of the machine reads."""
    on_cam = [s for s in scs if s.get("to_camera") and (s.get("voice") or "").strip()
              and s["id"] in clock and clock[s["id"]][1] > t0 and clock[s["id"]][0] < t1]
    talking = bool(on_cam)
    station = _station(talking)
    d = _door(station, reg, ruled, pick)
    seconds = round(t1 - t0, 2)
    duration = int(max(int(d["span"][0]), math.ceil(seconds - 1e-6)))
    motion = bool(motion_shots)
    scene = merged_scene(cid, scs, clock, t0, t1, timing, first_override,
                         end_attached=bool(end), talking=talking)
    prompt, missing = clip_prompt(scene, piece, seconds, talking, motion)

    medias = [{"role": mi.first_frame_role(station), "value": start}]
    if end:
        medias.append({"role": "end_image", "value": end})
    audio, parts = None, []
    if talking:
        # the section's lines on this clip's clock: a line said on camera plays
        # from its recording, any other is silence on this track
        for s in scs:
            if s["id"] not in clock:
                continue
            a, z = clock[s["id"]]
            if z <= t0 or a >= t1:
                continue
            f = voice_file(g, s["id"]) if s in on_cam else None
            parts.append({"scene": s["id"], "file": f, "from": round(max(0.0, t0 - a), 2),
                          "at": round(max(a, t0) - t0, 2), "seconds": round(min(z, t1) - max(a, t0), 2)})
        whole = len(parts) == 1 and parts[0]["file"] and parts[0]["from"] == 0 \
            and abs(parts[0]["seconds"] - (clock[parts[0]["scene"]][1] - clock[parts[0]["scene"]][0])) < 0.01
        audio = parts[0]["file"] if whole else f"clips/audio/{cid}.mp3"
        medias.append({"role": "audio_references", "value": audio})
    ref = None
    if motion:
        # ALWAYS the blurred copy, never the swipe's own footage: live 2026-10-02, the raw
        # footage on Seedance replaced our picture with the real creator, her captions and
        # her shop sign. Blurred, it still carries the movement and the camera, not the face.
        ref = f"clips/refs/{cid}-motion.mp4"
        medias.append({"role": "video_references", "value": ref})
    people = sorted({e.split(" · ")[1] for e in g.get("elements") or [] if e.startswith("person · ")})
    params = {"prompt": prompt, "duration": duration, **d["params"]}
    if piece and piece.get("aspect"):
        params["aspect_ratio"] = piece["aspect"]
    if d["resolution"]:
        params["resolution"] = d["resolution"]
    return {
        "id": cid, "kind": station, "model": d["model"], "door": d["door"],
        "section": sbp.section_no(g["id"]), "section_id": g["id"], "n": n,
        "maker": g.get("maker"), "clip_is": kind_of_clip,
        "scenes": [s["id"] for s in scs if s["id"] in clock and clock[s["id"]][1] > t0 and clock[s["id"]][0] < t1]
        or [s["id"] for s in scs],
        "window": [round(t0, 2), round(t1, 2)], "seconds": seconds,
        "params": params, "medias": medias,
        "start_frame": start, "end_frame": end, "last_frame": end,
        "first_frame_role": mi.first_frame_role(station),
        "frames": [x for x in (start, end) if x],
        "after": after,
        "audio": audio, "audio_parts": parts,
        "motion_ref": {"shots": list(motion_shots), "file": ref} if motion else None,
        # a cutaway carries the same lines as the clip it cuts away from; the line
        # check is claimed once, by that clip (preflight rule 7: one claim a line)
        "lines": [] if kind_of_clip == "cutaway" else
        [s["id"] for s in on_cam if clock[s["id"]][0] >= t0 - 0.01 and clock[s["id"]][1] <= t1 + 0.01],
        "to_camera": talking,
        "beats": scene["beats"],
        "characters": people, "products": [],
        "prompt_missing": missing,
    }


_TEARDOWN: dict = {}


def sbp_teardown_dir(run: Path) -> Path:
    """The teardown run the storyboard was built from (storyboard.json `teardown`,
    relative to this machine folder)."""
    return _TEARDOWN.get(str(run)) or Path(".")


def cut_from_footage(scene_ids, by_id: dict) -> bool:
    """Every scene of a section is CUT from our own footage (footage.py's gate,
    2026-10-05): the section is made from that footage, no clip is generated."""
    ids = [s for s in scene_ids or [] if s]
    return bool(ids) and all((by_id.get(s) or {}).get("source_plan") == "cut"
                             and (by_id.get(s) or {}).get("owned_file") for s in ids)


def plan_clips(run: Path, sb: dict, scenes: list[dict], reg: dict, piece: dict | None = None,
               timing: dict | None = None, only: list[str] | None = None, ruled=None,
               pick: str | None = None) -> dict:
    """-> {"sections": [row], "jobs": [item], "problems": [one line each]}.
    A problem is a stop: nothing is planned around a missing picture or voice."""
    run = Path(run)
    td = sb.get("teardown")
    _TEARDOWN[str(run)] = (HERE / td).resolve() if td else Path(".")
    by_id = {s["id"]: s for s in scenes}
    want = None
    if only:
        want = set()
        for x in only:
            x = x.strip()
            m = re.match(r"^(?:G|Section\s*)?0*(\d+)$", x, re.I)
            want.add(f"G{int(m.group(1)):02d}" if m else x)
    rows, jobs, problems = [], [], []
    for n, g in enumerate(sb.get("sections") or [], 1):
        gid = g["id"]
        if want and gid not in want:
            continue
        row = {"n": n, "id": gid, "maker": g.get("maker"), "what": sbp.PLAIN.get(g.get("maker"), g.get("maker")),
               "seconds": g.get("seconds"), "clips": [], "note": ""}
        rows.append(row)
        if g.get("reuses"):
            src = next((x for x in sb.get("sections") or [] if x["id"] == g["reuses"]), {})
            row["note"] = (f"the same {'clip' if src.get('clips') else 'picture'} as "
                           f"{sbp.section_no(g['reuses'])} — not made twice")
            continue
        if cut_from_footage(g.get("scenes") or list(section_clock(g)), by_id):
            row["note"] = "cut from our own footage — no clip generated"
            continue
        if not g.get("clips"):
            row["note"] = "no clip — the picture is shown for its time"
            continue
        pics = picture_ids(g)
        need = [p for p in [pics["start"], pics["end"]] + [o["id"] for o in pics["own"]] if p]
        missing = [p for p in need if picture_file(run, p) is None]
        if missing:
            problems.append(f"{sbp.section_no(gid)} needs the approved picture {', '.join(missing)} — "
                            f"it is not in media/; make or restore it first")
            continue
        clock = section_clock(g)
        for sid in clock:
            sc = by_id.get(sid) or {}
            if sc.get("to_camera") and voice_file(g, sid) is None:
                problems.append(f"{sbp.section_no(gid)}: {sid} is said on camera but has no recording of its own "
                                f"({(g.get('voice_from') or {}).get(sid) or 'none'})")
            elif sc.get("to_camera") and not (run / voice_file(g, sid)).is_file():
                problems.append(f"{sbp.section_no(gid)}: {sid}'s recording {voice_file(g, sid)} is not in the run")
        scs_all = [by_id[s] for s in g["scenes"] if s in by_id]
        # every section copied from the swipe carries the swipe's own footage for its
        # span — a talking selfie too: the camera moves as her arm moves in the swipe
        # (the owner 2026-10-02: "notice how the camera movement was actually working with
        # her hand holding the video … the whole point is that it looks legit")
        motion = g.get("maker") == "motion transfer" or (g.get("maker") == "lip-sync" and not g.get("added"))
        wins = shot_windows(g) if motion else []
        own_shots = {k for o in pics["own"] for k in o["drives"]}
        prev = None
        total = len(g["clips"])
        for ci, c in enumerate(g["clips"], 1):
            cid = f"{gid}-C{ci}"
            scs = [by_id[s] for s in c.get("scenes") or [] if s in by_id]
            if not scs:
                problems.append(f"{sbp.section_no(gid)} clip {ci}: none of its scenes {c.get('scenes')} is in the brief")
                continue
            ts = [clock[s["id"]] for s in scs if s["id"] in clock]
            t0 = min(a for a, _ in ts) if ts else 0.0
            t1 = max(z for _, z in ts) if ts else float(c.get("seconds") or g.get("seconds") or 0)
            # no hand-offs for people (3 Oct): a person on screen always starts from the approved picture
            handed_on = ci > 1 and not section_people(g)
            start = f"{prev}-LAST" if handed_on else pics["start"]
            end = pics["end"] if ci == total else None
            shots = [k for k, a, z in wins if k not in own_shots and z > t0 and a < t1] if motion else []
            if motion and not shots:
                shots = [k for k in pics["drives"]] or [k for k, _, _ in wins if k not in own_shots]
            job = _job(cid, g, n, scs, clock, t0, t1, start, end, prev if handed_on else None, shots,
                       run, timing, piece, reg, ruled, pick)
            job["starts_from"] = c.get("starts_from")
            jobs.append(job)
            row["clips"].append(cid)
            prev = cid
        # a picture for ANOTHER camera set-up inside the section is its own clip,
        # from that picture, over the swipe shots it drives — the edit cuts to it
        for o in pics["own"]:
            ks = [w for w in wins if w[0] in o["drives"]]
            if not ks:
                continue
            t0 = min(a for _, a, _ in ks)
            t1 = max(z for _, _, z in ks)
            scs = [s for s in scs_all if s["id"] in clock and clock[s["id"]][1] > t0 and clock[s["id"]][0] < t1] or scs_all[:1]
            k = next((x for x in (g.get("swipe") or {}).get("shots") or [] if x["id"] == o["copies"]), {})
            # its first instant is the swipe shot's own first frame, our people in it
            first = {"subject": _swap(sb, gid, k.get("frame")), "composition": "", "action": ""}
            cid = f"{gid}-{o['copies']}"
            job = _job(cid, g, n, scs, clock, t0, t1, o["id"], None, None, [x[0] for x in ks],
                       run, timing, piece, reg, ruled, pick, first_override=first, kind_of_clip="cutaway")
            job["starts_from"] = f"its own picture {o['id']} — the other camera set-up inside the section"
            jobs.append(job)
            row["clips"].append(cid)
    problems += no_handoff_breaks(jobs, {g["id"]: g for g in sb.get("sections") or []})
    return {"sections": rows, "jobs": jobs, "problems": problems}


def _swap(sb: dict, gid: str, text) -> str:
    """The swipe's names for its people → ours (the storyboard's people map)."""
    t = " ".join(str(text or "").split())
    pm = sb.get("people_map") or {}
    lead_ours, lead_swipe = (pm.get("lead") or [None, None]) + [None] * (2 - len(pm.get("lead") or []))
    if lead_ours and lead_swipe:
        t = re.sub(rf"\b{re.escape(lead_swipe)}\b", lead_ours, t)
    for sw, ours in ((pm.get("others") or {}).get(gid) or {}).items():
        t = re.sub(rf"\b{re.escape(sw)}\b", ours, t)
    return t


# ------------------------------------------------------------ batches

def waves(jobs: list[dict]) -> list[list[dict]]:
    """Clips that start from a picture first; a clip that starts from the last
    frame of another goes in the wave after it."""
    depth, by = {}, {j["id"]: j for j in jobs}

    def d(j):
        if j["id"] not in depth:
            a = j.get("after")
            depth[j["id"]] = 0 if not a or a not in by else d(by[a]) + 1
        return depth[j["id"]]
    out: dict[int, list] = {}
    for j in jobs:
        out.setdefault(d(j), []).append(j)
    return [out[k] for k in sorted(out)]


def batches(jobs: list[dict], cap: int) -> list[list[dict]]:
    cap = max(1, int(cap or len(jobs) or 1))
    out = []
    for w in waves(jobs):
        out += [w[i:i + cap] for i in range(0, len(w), cap)]
    return out


# ------------------------------------------------------------ the checks

# What the storyboard decides that the per-scene contract does not know:
# a lip-sync section has no end picture (its last frame is said in words), a
# motion-transfer clip carries the swipe's footage. Shown, never silent.
DECIDED = [
    (re.compile(r"'end_image'|no LAST FRAME|frame\(s\) for this scene"),
     "no end picture — the storyboard made none for this section, so the clip ends where its last beat says, in words"),
    (re.compile(r"'video_references' media"),
     "the swipe's footage rides as video_references — the motion-transfer section's motion reference"),
]


def preflight_check(jobs: list[dict], run: Path, provider: str, cap: int) -> tuple[list[str], list[str], list[str]]:
    """The run's preflight on every clip batch, against a COPY of the run's
    records (so a check writes nothing into the run). -> (refusals, notes, warns)."""
    pre = _load("preflight")
    refusals, notes, warns = [], {}, []
    with tempfile.TemporaryDirectory() as tmp:
        shadow = Path(tmp) / run.name
        (shadow / "batches").mkdir(parents=True)
        for name in ("run.json", "lines.json", "frames.json", "verdicts.json", "brief.md"):
            if (run / name).is_file():
                shutil.copy2(run / name, shadow / name)
        for f in sorted((run / "batches").glob("*.json")) if (run / "batches").is_dir() else []:
            if not f.name.startswith("clips-"):
                shutil.copy2(f, shadow / "batches" / f.name)
        for i, chunk in enumerate(batches(jobs, cap), 1):
            p = Path(tmp) / f"clips-{i:02d}.json"
            p.write_text(json.dumps({"items": chunk}, indent=1))
            fails, w = pre.check(p, shadow, provider, pre.DEFAULT_BANK)
            warns += [x for x in w if "[rule 7]" not in x]
            r, n = sort_findings(fails)
            refusals += r
            for why, ids in n.items():
                notes.setdefault(why, []).extend(ids)
    return refusals, [f"{why} ({', '.join(sorted(set(ids)))})" for why, ids in notes.items()], warns


def sort_findings(fails: list[str]) -> tuple[list[str], dict]:
    """(refusals, {what the storyboard decided: [clip ids]}) — a finding the
    storyboard decided is shown as a note; every other one refuses."""
    refusals, notes = [], {}
    for f in fails:
        hit = next((why for rx, why in DECIDED if rx.search(f)), None)
        if hit:
            notes.setdefault(hit, []).append(f.split(":", 1)[0].split("]")[-1].strip())
        else:
            refusals.append(f)
    return refusals, notes


# ------------------------------------------------------------ the page

def _ref_line(j: dict) -> str:
    m = j.get("motion_ref")
    return f"{m['file']} (swipe shots {', '.join(m['shots'])})" if m else "—"


def _voice_line(j: dict) -> str:
    if not j.get("audio"):
        return "none on the clip (the read is laid under it at the edit)"
    said = [p for p in j.get("audio_parts") or [] if p.get("file")]
    if len(said) == 1 and said[0]["file"] == j["audio"]:
        return j["audio"]
    return f"{j['audio']} (silence where nobody speaks on camera) = " + " + ".join(f"{p['file']}" + (f" from {p['from']}s" if p.get("from") else "")
                                         for p in said)


def prompts_md(run: Path, res: dict, overall: dict, cap: int) -> str:
    jobs = {j["id"]: j for j in res["jobs"]}
    cost = {r["id"]: r for r in overall["rows"]}
    L = [f"# Clips — {len(res['jobs'])} clip(s) from the storyboard", "",
         "Every clip starts from a picture already approved in `media/`; nothing here makes a picture "
         "or records a voice. Lengths are seconds. The prompt under each clip is exactly what the model receives.", "",
         "| Section | What it is | Maker | Clips | Seconds | Start → end picture | Voice on the clip | Motion reference | Credits |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in res["sections"]:
        if not r["clips"]:
            L.append(f"| {r['n']} | {r['what']} | {r['maker']} | 0 | {r['seconds']} | — | — | — | 0 — {r['note']} |")
            continue
        for cid in r["clips"]:
            j = jobs[cid]
            L.append(f"| {r['n']} | {r['what']} | {r['maker']} | {cid} ({j['clip_is']}) | {j['seconds']} "
                     f"(billed {j['params']['duration']}) | {j['start_frame']} → {j['end_frame'] or '(in words)'} | "
                     f"{_voice_line(j)} | {_ref_line(j)} | {cost.get(cid, {}).get('credits')} |")
    L += ["", f"**TOTAL · {overall['count']} clip(s) · {overall['total_credits']} cr · ${overall['total_usd']:.3f}**", "",
          f"Sent in batches of {cap}; a clip that starts from another clip's last frame goes in a later batch.", ""]
    for i, b in enumerate(batches(res["jobs"], cap), 1):
        L.append(f"- batch {i}: {', '.join(j['id'] for j in b)}")
    for j in res["jobs"]:
        L += ["", f"## {j['section']} · {j['id']} — {j['maker']} ({j['clip_is']})", "",
              f"- **starts from**: `{j['start_frame']}` — {j.get('starts_from') or ''}",
              f"- **ends on**: `{j['end_frame']}`" if j["end_frame"] else "- **ends on**: no end picture — the last beat says where it lands",
              f"- **voice**: {_voice_line(j)}",
              f"- **motion reference**: {_ref_line(j)}",
              f"- **model**: {j['model']} on {j['door']} · {j['params']['duration']} s · "
              + " · ".join(f"{k} {v}" for k, v in j["params"].items() if k not in ("prompt", "duration")),
              f"- **credits**: {cost.get(j['id'], {}).get('credits')}",
              "", "```text", j["params"]["prompt"] or f"(NOT WRITTEN — missing: {'; '.join(j['prompt_missing'])})", "```"]
    return "\n".join(L) + "\n"


def print_sections(res: dict, overall: dict) -> None:
    jobs = {j["id"]: j for j in res["jobs"]}
    cost = {r["id"]: r for r in overall["rows"]}
    print("section · what it is · maker · clips · seconds · start → end picture · voice · motion reference · credits")
    for r in res["sections"]:
        if not r["clips"]:
            print(f"{r['n']} · {r['what']} · {r['maker']} · 0 · {r['seconds']}s · — · — · — · 0 — {r['note']}")
            continue
        for cid in r["clips"]:
            j = jobs[cid]
            print(f"{r['n']} · {r['what']} · {r['maker']} · {cid} ({j['clip_is']}) · {j['seconds']}s "
                  f"(billed {j['params']['duration']}s) · {j['start_frame']} → {j['end_frame'] or '(in words)'} · "
                  f"{_voice_line(j)} · {_ref_line(j)} · {cost.get(cid, {}).get('credits')} cr")


# ------------------------------------------------------------ making the inputs (no network)

def build_inputs(run: Path, jobs: list[dict], ffmpeg: str = "ffmpeg") -> list[str]:
    """The joined voice track and the joined swipe footage each clip carries —
    local ffmpeg only, no credits. -> what was written."""
    out = []
    for j in jobs:
        if j.get("audio", "").startswith("clips/audio/"):
            dest = run / j["audio"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            ins, filt, labels = [], [], []
            for i, p in enumerate(j["audio_parts"]):
                if p.get("file"):
                    ins += ["-ss", str(p.get("from") or 0), "-t", str(p["seconds"]), "-i", str(run / p["file"])]
                else:
                    ins += ["-f", "lavfi", "-t", str(p["seconds"]), "-i", "anullsrc=r=44100:cl=mono"]
                filt.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=mono,apad=pad_dur={GAP}[a{i}]"
                            if i < len(j["audio_parts"]) - 1 else f"[{i}:a]aresample=44100,aformat=channel_layouts=mono[a{i}]")
                labels.append(f"[a{i}]")
            fc = ";".join(filt) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=0:a=1[out]"
            subprocess.run([ffmpeg, "-y", "-v", "error", *ins, "-filter_complex", fc, "-map", "[out]", str(dest)],
                           check=True)
            out.append(str(dest))
        m = j.get("motion_ref") or {}
        if m and str(m.get("file", "")).startswith("clips/refs/"):
            dest = run / m["file"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shots = sbp_teardown_dir(run) / "framemap" / "shots"
            ins = []
            for k in m["shots"]:
                ins += ["-i", str(shots / f"{k}.mp4")]
            fc = ("".join(f"[{i}:v]" for i in range(len(m["shots"]))) + f"concat=n={len(m['shots'])}:v=1:a=0[c];"
                  f"[c]scale=720:-2,gblur=sigma={MOTION_BLUR}[v]")
            subprocess.run([ffmpeg, "-y", "-v", "error", *ins, "-filter_complex", fc, "-map", "[v]", str(dest)],
                           check=True)
            out.append(str(dest))
    return out


def submit_md(run: Path, res: dict, prov_label: str, cap: int) -> str:
    L = [f"# {run.name} — clips submit sheet", "",
         f"Provider: {prov_label}. Upload every file to the provider first (each becomes a media id), "
         "then submit each clip with its medias by role, its params and its prompt from `clips/PROMPTS.md`. "
         "Send the batches in order — a later batch holds clips that start from an earlier clip's last frame, "
         "which `run.py record` pulls into media/<clip>-LAST.png when that clip lands.", "",
         "Hand the results back as results.json, then: `python3 machine/run.py record " + str(run) + " --results results.json`", ""]
    for i, b in enumerate(batches(res["jobs"], cap), 1):
        L += [f"## Batch {i}", ""]
        for j in b:
            L.append(f"### {j['id']} — {j['model']} ({j['section']})")
            for m in j["medias"]:
                f = picture_file(run, m["value"]) if m["role"] in ("start_image", "end_image") else None
                L.append(f"- **{m['role']}**: `{f or m['value']}`")
            for k, v in j["params"].items():
                if k != "prompt":
                    L.append(f"- **{k}**: {v}")
            L.append("")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------ the step

def start(a, run: Path, plan: dict, reg: dict, timing: dict | None = None, ruled=None) -> int:
    """`run.py start … --clips [--only G05,G12] [--dry-run]`."""
    run = Path(run)
    sbf = run / "storyboard.json"
    if not sbf.is_file():
        print("REFUSED --clips: no storyboard.json in the run — storyboard_plan.py makes it, "
              "and --storyboard makes its pictures", file=sys.stderr)
        return 2
    if getattr(a, "storyboard", False):
        print("REFUSED --clips with --storyboard: pictures first, then clips — one step at a time", file=sys.stderr)
        return 2
    sb = json.loads(sbf.read_text())
    only = [x for x in str(getattr(a, "only", "") or "").split(",") if x.strip()] or None
    try:
        res = plan_clips(run, sb, plan.get("scenes") or [], reg, piece=plan.get("piece") or {},
                         timing=timing, only=only, ruled=ruled, pick=getattr(a, "clip_model", None))
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    for p in res["problems"]:
        print(f"STOP {p}", file=sys.stderr)
    if res["problems"]:
        print("nothing was planned", file=sys.stderr)
        return 2
    if not res["jobs"]:
        print("clips: the storyboard calls for no clip in " + (", ".join(only) if only else "this run"))
        return 0
    # the house the clip door is in (providers.json doors.<station>.primary)
    door_house = str(((reg.get("doors") or {}).get("motion") or {}).get("primary") or "")
    pname = getattr(a, "provider", None) or next(
        (n for n, p in (reg.get("providers") or {}).items() if p.get("family") == door_house), None)
    prov = (reg.get("providers") or {}).get(pname or "", {})
    overall = platform.plan(res["jobs"], prov, reg, forced=True)
    print(f"clips: {len(res['jobs'])} clip(s) from storyboard.json — every one from an approved picture; "
          f"door {pname} → {', '.join(sorted({j['model'] for j in res['jobs']}))}")
    print_sections(res, overall)
    print()
    platform.print_plan(overall)
    cap = int(prov.get("batch_max") or len(res["jobs"]))
    bs = batches(res["jobs"], cap)
    print(f"batches: {len(bs)} of up to {cap} — " + " · ".join(f"{i}: {', '.join(j['id'] for j in b)}"
                                                              for i, b in enumerate(bs, 1)))
    if overall["refusals"]:
        for r in overall["refusals"]:
            print(f"REFUSED {r}", file=sys.stderr)
        return 2
    refusals, notes, warns = preflight_check(res["jobs"], run, pname, cap)
    for w in warns:
        print(f"WARNING {w}")
    for n in notes:
        print(f"NOTE {n}")
    missing = [j["id"] for j in res["jobs"] if j.get("prompt_missing")]
    (run / "clips").mkdir(exist_ok=True)
    page = run / "clips" / "PROMPTS.md"
    page.write_text(prompts_md(run, res, overall, cap))
    print(f"prompts: {page}")
    if refusals or missing:
        for r in refusals:
            print(f"REFUSED {r}", file=sys.stderr)
        print("preflight failed — nothing submitted", file=sys.stderr)
        return 2
    if getattr(a, "dry_run", False):
        print("dry run — nothing built, nothing submitted, no credits spent")
        return 0
    if prov.get("confirm") and not getattr(a, "yes", False) and not platform.confirm(prov, False):
        print("declined")
        return 1
    built = build_inputs(run, res["jobs"])
    for f in built:
        print(f"built {f}")
    (run / "batches").mkdir(exist_ok=True)
    for old in (run / "batches").glob("clips-*.json"):
        old.unlink()
    for i, b in enumerate(bs, 1):
        (run / "batches" / f"clips-{i:02d}.json").write_text(json.dumps({"items": b}, indent=1) + "\n")
    (run / "clips" / "plan.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    sheet = run / "clips" / "SUBMIT.md"
    sheet.write_text(submit_md(run, res, prov.get("label", pname or "?"), cap))
    print(f"wrote {sheet} — the session submits on the clip door, then:")
    print(f"  python3 machine/run.py record {run} --results <results.json>")
    return 0


# ------------------------------------------------------------ after the clips land

def frames_of(clip: Path, out_dir: Path, ffmpeg: str = "ffmpeg") -> list[Path]:
    """First, middle and last frame of a clip, as pictures the reviewer reads."""
    out_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
                       capture_output=True, text=True)
    try:
        dur = float(r.stdout.strip())
    except ValueError:
        dur = 0.0
    got = []
    for name, t in (("first", 0.0), ("mid", dur / 2), ("last", max(0.0, dur - 0.05))):
        f = out_dir / f"{clip.stem}-{name}.jpg"
        subprocess.run([ffmpeg, "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(clip), "-frames:v", "1", str(f)],
                       check=False)
        if f.is_file():
            got.append(f)
    return got


def last_frame(clip: Path, dest: Path, ffmpeg: str = "ffmpeg") -> Path | None:
    """The real last frame of a clip — the picture the next clip starts from, in a section
    with nobody on screen only (a person's clip always starts from the approved picture)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-y", "-v", "error", "-sseof", "-0.1", "-i", str(clip), "-update", "1",
                    "-frames:v", "1", str(dest)], check=False)
    return dest if dest.is_file() else None


def review_clips(run, jobs, made, review=None, frames=None):
    """THE CLIP REVIEW — each clip that landed against its start (and end)
    picture and the swipe shots it copies, filed in qc-log/ (marketing-chain-checks
    review.after_stage), the same way review_pictures files the pictures."""
    try:
        if review is None:
            q = str(HERE.parent.parent.parent / "components" / "quality-checks")
            if q not in sys.path:
                sys.path.insert(0, q)
            from marketing_chain_checks import review
        frames = frames or frames_of
        run = Path(run)
        shots = sbp_teardown_dir(run) / "framemap" / "shots"
        rows = []
        for j in jobs:
            f = (made.get(j["id"]) or {}).get("file")
            if not f:
                continue
            f = Path(f) if Path(f).is_absolute() else run / f
            if not f.is_file():
                continue
            compare = [p for p in (picture_file(run, j["start_frame"]), picture_file(run, j["end_frame"] or "")) if p]
            for k in (j.get("motion_ref") or {}).get("shots") or []:
                compare += [shots / f"{k}-first.jpg", shots / f"{k}-last.jpg"]
            compare.append(j["params"]["prompt"])
            rows.append({"id": j["id"], "output": [str(x) for x in frames(f, run / "clips" / "review")],
                         "compare": [str(x) if isinstance(x, Path) else x for x in compare]})
        if rows:
            res = review.after_stage("video-production", "clips", run, items=rows)
            bad = [k for k, v in res.items() if isinstance(v, dict) and v.get("severity") in ("BLOCKER", "FIX")]
            print(f"clip review: {len(rows) - len(bad)} pass, {len(bad)} sent back — {run / 'qc-log' / 'QC-LOG.md'}")
        return rows
    except Exception as e:
        print(f"clip review not run ({type(e).__name__}: {e})")
        return []


def after_record(run, results: dict, review=None, frames=None, lastf=None) -> None:
    """Called by `run.py record`: the last frame of every landed clip another
    clip starts from, then the clip review."""
    run = Path(run)
    res = _read(run / "clips" / "plan.json", {}) or {}
    jobs = res.get("jobs") or []
    if not jobs:
        return
    sb = _read(run / "storyboard.json", {}) or {}
    if sb.get("teardown"):
        _TEARDOWN[str(run)] = (HERE / sb["teardown"]).resolve()
    ids = {j["id"] for j in jobs}
    landed = {k: v for k, v in (results or {}).items() if k in ids and v.get("file")}
    if not landed:
        return
    lastf = lastf or last_frame
    for j in jobs:
        a = j.get("after")
        if a in landed:
            f = Path(landed[a]["file"])
            f = f if f.is_absolute() else run / f
            got = lastf(f, run / "media" / f"{a}-LAST.png")
            print(f"  {j['id']}: starts from {got or 'NOT PULLED — ' + a + ' last frame'}")
    review_clips(run, [j for j in jobs if j["id"] in landed], landed, review=review, frames=frames)
