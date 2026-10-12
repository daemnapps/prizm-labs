#!/usr/bin/env python3
"""mouths.py — is the lead talking only when they are talking? (the owner, 4 Oct 2026: "Some of the stuff she's lip-syncing,
she's voicing over … she's talking when she should not be talking, or you're showing her talking when she should
not be talking.")

    python3 mouths.py <video-production-run> [--out <edit run dir>] [--map edit-map.json]

Walks what is actually on screen (render_map.flatten — the same shots the render makes), ten times a second, and
holds her mouth against the sound:
  TALKING, NO VOICE   her mouth is in frame and moving, and she is not the one heard (someone else talks, or nobody)
  VOICE, WRONG MOUTH  her voice is heard — a line laid as its own track, a word fix, an added line, or her clip's line
                      over a different shot — while her mouth is in frame
A murmur of hers (mm-hmm) over a still or barely moving mouth is fine (a closed-mouth hum). B-roll, inserts and a
close-up cropped above her mouth hide it. The mouth comes from the clip's face track (tracks/<clip>.json: the face
box and how open the mouth is). Writes <out>/mouths.json; exits 1 if anything is found.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_map as RM  # noqa: E402
from edit_map import LIPS_MOVING, MOUTH_TOP  # noqa: E402

STEP = 0.1
MOUTH_BOT = 1.0                         # the mouth runs from MOUTH_TOP (edit_map) to the bottom of the face box
MIN_RUN = 0.3                           # a finding shorter than this is a blink of the tracker, not something seen
MURMUR_OK = 2.5 * LIPS_MOVING           # a hum moves the mouth a little; more than this reads as talking


def at(track: list[dict], t: float) -> dict | None:
    rows = [r for r in track if abs(r["t"] - t) <= 0.051 and r["w"] > 0]
    return rows[0] if rows else None


def moving(track: list[dict], t: float) -> float | None:
    o = [r["open"] for r in track if t - 0.25 <= r["t"] <= t + 0.25 and r["w"] > 0 and r["open"] >= 0]
    if len(o) < 3:
        return None
    return sum(abs(u - v) for u, v in zip(o, o[1:])) / (len(o) - 1)


def lead_of(m: dict) -> str:
    """The person whose mouth is held to the sound: the ad's `lead` (decisions.json story.lead → edit map), else
    the first speaker heard in their own clip."""
    return m.get("lead") or next((l["who"] for l in m["voice"] if l["kind"] == "in clip"), "")


def people_in(m: dict) -> dict:
    """{clip: {person, …}} — who is IN each clip's picture, from the production run's brief (the scene's `who`).
    Empty when the run does not say, and then every shot is taken to hold the lead (the one-lead ads this check
    was built on). 2026-10-09, a TV-shopping ad: the host speaks off camera over the mannequin and the guest
    by design; the face tracked in those shots is theirs, not hers, so her voice there is a voice-over, not a
    wrong mouth — and a guest's own on-camera line is her line being said, not talking with no voice."""
    try:
        run = Path(m.get("from_run") or "")
        calls = json.loads((run / "clips" / "plan.json").read_text()).get("calls") or []
        scenes = {s.get("id"): str(s.get("who") or "") for s in json.loads((run / "plan.json").read_text()).get("scenes") or []}
    except (OSError, ValueError, TypeError):
        return {}
    import re
    out = {}
    for c in calls:
        sid = str(c.get("start_frame") or "").split("-")[0]
        if sid not in scenes:                               # a piece carried on from the last frame (its start frame is the clip before's last frame)
            sid = next((l.get("scene") for l in c.get("lines") or [] if isinstance(l, dict)), sid)
        who = scenes.get(sid, "")
        if who:
            out[c["id"]] = {p for p in (c.get("people") or []) if re.search(r"\b" + re.escape(p) + r"\b", who, re.I)}
    return out


def check(m: dict, tracks: dict, lead: str) -> list[dict]:
    segs = RM.flatten(m)
    inside = people_in(m)
    heard = [(l["a"], l["b"], l) for l in m["voice"] + m["sounds"]]
    fixes = [(p["a"], p["b"]) for p in m.get("patches") or []]
    mutes = [(p["mute_a"], p["mute_b"]) for p in m.get("patches") or []]
    found, t = [], 0.0
    while t < m["total"]:
        s = next((x for x in segs if x["a"] <= t < x["b"]), None)
        t_ = t; t = round(t + STEP, 3)
        if not s or s["kind"] != "clip" or not s.get("clip"):
            continue                                       # B-roll, an insert, a plate: no mouth of hers
        tr = tracks.get(s["clip"]) or []
        src_t = s.get("in", 0) + (t_ - s["a"]) * float(s.get("speed") or 1)
        r = at(tr, round(src_t, 1))
        if not r:
            continue
        x0, y0, x1, y1 = RM.crop_box(s)
        my0, my1 = r["y"] + MOUTH_TOP * r["h"], r["y"] + MOUTH_BOT * r["h"]
        mx = r["x"] + r["w"] / 2
        if not (my1 > y0 + 0.01 and my0 < y1 - 0.01 and x0 < mx < x1):
            continue                                       # the crop keeps her mouth out of frame
        mv = moving(tr, src_t) or 0.0
        in_shot = inside.get(s["clip"])
        lead_here = in_shot is None or lead in in_shot          # unknown → the one-lead reading, as before
        hers = [l for a, b, l in heard if a <= t_ < b and l["who"] == lead]
        others = [l for a, b, l in heard if a <= t_ < b and l["who"] != lead]
        # the clip's own line being said, by whoever is in it (a guest's on-camera line is synced too)
        synced = [l for a, b, l in heard if a <= t_ < b and l["kind"] == "in clip" and l.get("clip") == s["clip"]
                  and (lead_here or l["who"] != lead) and not any(a <= t_ < b for a, b in mutes)]
        voiceover = [l for l in hers if lead_here and (l["kind"] in ("own track",)
                     or (l["kind"] == "in clip" and l.get("clip") != s["clip"]))]
        if any(a <= t_ < b for a, b in fixes):
            voiceover.append({"scene": "word fix", "text": "a word said again in her voice"})
        murmur = [l for l in hers if l["kind"] == "sound"]
        if voiceover and not synced:
            kind, why = "VOICE, WRONG MOUTH", voiceover[0]
        elif mv > LIPS_MOVING and not synced and not (murmur and mv <= MURMUR_OK):
            kind, why = "TALKING, NO VOICE", (others[0] if others else {"scene": "—", "text": "nobody is speaking"})
        else:
            continue
        row = {"kind": kind, "a": t_, "b": t, "clip": s["clip"], "move": round(mv, 3),
               "line": why.get("scene"), "heard": (why.get("who", "") + ": " if why.get("who") else "") + why.get("text", "")[:70],
               "shot": "close-up" if s.get("closeup") else ("punch-in" if float(s.get("scale") or 1) > 1 else "wide")}
        last = found[-1] if found else None
        if last and last["kind"] == kind and last["clip"] == row["clip"] and abs(last["b"] - t_) < 1e-6 and last["line"] == row["line"]:
            last["b"] = t
        else:
            found.append(row)
    return [f for f in found if f["b"] - f["a"] >= MIN_RUN]


def reviewed(found: list[dict], out: Path | None) -> list[dict]:
    """Findings a person checked by eye and found closed-lipped, as the ad's decisions.json `mouths_reviewed` records
    them: {clip, line, max_move, by, why}. Only a TALKING, NO VOICE finding on that clip and line, moving no more than
    max_move, is let through — anything stronger still stops the line (2026-10-08, the athlete: a full beard and head turns
    read 0.05–0.08 on a listening face whose lips the frame strips show closed; real talking read 0.10–0.25)."""
    try:
        rows = json.loads((Path(out) / "decisions.json").read_text()).get("mouths_reviewed") or [] if out else []
    except (OSError, ValueError):
        rows = []
    def ok(f):
        return f["kind"] == "TALKING, NO VOICE" and any(
            r.get("clip") == f["clip"] and r.get("line") == f["line"] and f["move"] <= float(r.get("max_move") or 0)
            for r in rows)
    return [f for f in found if not ok(f)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--map", default="edit-map.json")
    ap.add_argument("--lead")
    a = ap.parse_args(argv)
    vm = Path(a.run)
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out) if a.out else HERE.parents[2] / "runs" / "video-edit" / rj["brand"] / rj["label"]
    m = json.loads((out / a.map).read_text())
    lead = a.lead or lead_of(m)
    tracks = {f.stem: json.loads(f.read_text()) for f in (out / "tracks").glob("*.json")}
    found = reviewed(check(m, tracks, lead), out)
    (out / "mouths.json").write_text(json.dumps(found, indent=1))
    for f in found:
        print(f"  {f['a']:6.1f}–{f['b']:6.1f}s  {f['kind']:<18} {f['clip']:<10} {f['shot']:<9} {f['line']}: {f['heard']}")
    print(f"mouths: {len(found)} finding(s) · lead {lead}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
