#!/usr/bin/env python3
"""edit_map.py — the edit, as a map: every layer of the ad on one clock, cut the way the
swipe is cut, from the clips the Omni route made. Builds the timeline; renders nothing.

    python3 edit_map.py <video-production-run> [--out <dir>]

Writes <out>/edit-map.json (default runs/video-edit/<brand>/<label>/). The production run is
only read.

THE CLOCK (the owner, 3 Oct 2026: "think about the principle"): in every piece one thing sets the
time and everything else is fitted to it. Here every LINE sets its own time — its real sound,
end to end:
  · said on camera  → the clip's own span of that line (lip-synced; never re-timed)
  · said off camera → its own track (cloned voice), its real length
  · a sound (mm-hmm) → its own track; the person on screen nods
Lines follow in script order, one breath apart (the pace dial); dead air is never laid.
The swipe sets everything else: its cuts inside a section (frame_control.cuts_at), where it
goes to a second angle (cutaway clips), its push-ins, its words on screen, its sound cues —
each mapped from the plan's clock onto the real one through the line it falls in.

EDIT MOVES, never a remake first (the owner, 3 Oct: "see what editing moves can be done first"):
  · a clip's sound is kept ONLY across its scripted on-camera words (`spans`) — anything the
    model made up off camera is never heard
  · a line a clip cut off (CUT_OFF) is taken from another angle that says it whole
  · fixes per clip (FIXES): a punch-in that crops out burned-in words, …
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

SOUND_UNDER = 0.7       # a mm-hmm starts this share of its length before the other person's line ends
BREATH = 0.15          # between two lines: a breath, never dead air (pace "tight" keeps ≤ 0.25 s)
PUNCH = 1.07           # the jump-cut punch-in (settled T-2, 23 Sep): 7 %
LEAD = 0.06            # picture starts a hair before the first word

MOUTH_TOP = 0.71       # the face box starts at the brows; the lips sit ~3/4 down (checked on frames) — mouths.py reads it
LOOKS = json.loads((Path(__file__).resolve().parent.parent / "looks" / "edit-looks.json").read_text())
# Moves for things a clip got wrong that an edit can hide live in the AD's decisions.json, never here:
#   "fixes": {"<clip id>": {"crop": {"from": s, "to": s, "scale": x, "y": 0-1, "why": "…"}}}


def _read(p, d=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else d


def swipe_len(g) -> float | None:
    sp = (g.get("swipe") or {}).get("span")
    return round(sp[1] - sp[0], 2) if sp else None


def dur(f) -> float:
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True).stdout.strip()
    return float(o or 0)


PAD_IN, PAD_OUT = 0.08, 0.18   # a line's sound starts a hair early and rings out — no clipped first/last syllable

# Where each part of a face sits, from the face box (top = the brows, height = brows to chin): (down the box, crop
# width as a share of the face width). A close-up frames the part the words name (the owner, 4 Oct 2026).
PARTS = {"upper lip": (0.74, 1.0), "lips": (0.80, 1.0), "mouth": (0.80, 1.0), "chin": (0.98, 1.1),
         "jawline": (0.86, 1.6), "cheeks": (0.52, 1.5), "temples": (0.15, 1.15), "forehead": (-0.15, 1.4),
         "under-eyes": (0.30, 1.3), "eyes": (0.22, 1.4), "nose": (0.45, 1.1), "neck": (1.35, 1.6)}
PART_WORDS = [("upper lip", r"upper lip"), ("lips", r"\blips?\b"), ("mouth", r"\bmouth\b"), ("chin", r"\bchin\b"),
              ("jawline", r"\bjaw(line)?\b"), ("cheeks", r"\bcheek(s|bones?)?\b"), ("temples", r"\btemples?\b"),
              ("forehead", r"\bforehead\b"), ("under-eyes", r"under(-| )?eyes?"), ("eyes", r"\beyes?\b"),
              ("nose", r"\bnose\b"), ("neck", r"\bneck\b")]
MOUTH_PARTS = {"upper lip", "lips", "mouth", "chin", "jawline"}


CHEEK_ZOOM = 2.2


def hide_mouth(covers, sounds, a: float, b: float, pl: dict) -> bool:
    """Must this close-up keep her mouth out of frame? Yes for words added in her voice (her lips don't say them),
    and where her lips move with no words — unless a murmur of hers (mm-hmm) is heard over that moment."""
    if str(pl.get("scene") or "").endswith("+") or pl.get("hide_mouth"):
        return True
    # 4 Oct (the owner: "you're showing her talking when she should not be talking"): her mm-hmm does NOT excuse a
    # mouth that moves like talking — mouths.py measured it reading as speech
    return any(c["why"] == "lips move, no words" and c["a"] < b and c["b"] > a for c in covers)


def others_talking(lines, lead: str, a: float, b: float) -> bool:
    """Is someone other than the lead speaking over this stretch? Then her mouth stays out of a close-up — a still
    mouth there is fine, but the tracker can miss a small movement (4 Oct: 'good jawline')."""
    return any(l["who"] != lead and l["kind"] != "sound" and l["a"] < b and l["b"] > a for l in lines)


def part_named(lines, a: float, b: float, pl: dict):
    """The face part being talked about while a close-up is up -> (part, the words) | (None, None). A line's words
    are placed across it in order; the named part said nearest the close-up wins, looking through the lines over
    the close-up first, then the lines of its section. `pl["frames"]` names it outright."""
    if pl.get("frames") in PARTS and pl["frames"] != "cheeks":
        return pl["frames"], None
    mid = (a + b) / 2
    over = [l for l in lines if l["a"] < b + 0.3 and l["b"] > a - 0.3]
    secs = {o.get("section") for o in over if o.get("section")}
    for near in (over, [l for l in lines if l.get("section") in secs and l["a"] < b]):
        hit = _nearest_part(near, mid)
        if hit:
            return hit[1], hit[2]
    return None, None


def _nearest_part(near, mid):
    best = None
    for l in near:
        txt = l["text"]
        n = max(1, len(txt))
        taken = []                                       # "upper lip" wins over the "lip" inside it
        for part, rx in PART_WORDS:
            for mt in re.finditer(rx, txt, flags=re.I):
                if any(x <= mt.start() < y for x, y in taken):
                    continue
                taken.append(mt.span())
                t = l["a"] + (mt.start() / n) * (l["b"] - l["a"])
                d = abs(t - mid)
                if best is None or d < best[0]:
                    best = (d, part, txt[max(0, mt.start() - 20): mt.end() + 10].strip())
    return best

LIPS_MOVING = 0.05             # mouth movement (mean frame-to-frame change) above this with no words = cover it
TEXT_BANDS = [(0.10, 0.24), (0.60, 0.72)]   # where words may sit (inside the 4:5 band), tried in order


def _section_people(g) -> list:
    return [x for x in (g.get("elements") or []) if str(x).startswith("person")]


def tracks(vm: Path, out: Path, clip_ids) -> dict:
    """Per clip, 10 times a second: the largest face's box and how open the mouth is (macOS Vision)."""
    import sys, tempfile
    d = out / "tracks"; d.mkdir(parents=True, exist_ok=True)
    have = {}
    for cid in clip_ids:
        f = d / f"{cid}.json"
        if not f.exists():
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-production" / "machine"))
            import clip_qc as Q
            with tempfile.TemporaryDirectory() as t:
                Q.frames(vm / "clips" / f"{cid}.mp4", t, fps=10)
                rows = Q.faces(t)
            f.write_text(json.dumps([{"t": round(i / 10, 2), **{k: r[k] for k in ("x", "y", "w", "h", "open")}}
                                     for i, r in enumerate(rows)]))
        have[cid] = json.loads(f.read_text())
    return have


def build(vm: Path, out: Path | None = None, hook: str | None = None) -> dict:
    vm = Path(vm)
    out = Path(out) if out else None
    dec = _read(out / "decisions.json", {}) if out else {}
    FIXES = (dec or {}).get("fixes") or {}
    drop = set(((dec or {}).get("drop_sections") or {}).get("ids") or [])
    no_pic = set(((dec or {}).get("drop_picture") or {}).get("ids") or [])
    plan = _read(vm / "clips" / "plan.json")
    # hook versions (the owner, 3 Oct: "you need to generate the hook variations … then cut up as the variations"):
    # an opening clip made per hook in the brief (`hook` on the call); one version swaps it in for the control
    base_calls = [c for c in plan["calls"] if not c.get("hook")]
    if hook:
        hc = next((c for c in plan["calls"] if c["id"] == hook), None)
        if hc is None:
            raise SystemExit(f"no hook clip {hook} in the plan")
        base_calls = [dict(hc, id=hc["id"], clip_is="clip") if (c["section_id"] == hc["section_id"] and c["clip_is"] == "clip"
                      and c["lines"][0]["scene"] == hc["lines"][0]["scene"]) else c for c in base_calls]
    plan = {**plan, "calls": base_calls}
    sb = _read(vm / "storyboard.json")
    led = _read(vm / "clips" / "omni-ledger.json", {})
    run = _read(vm / "run.json", {})
    tts = {t["scene"]: t for t in plan["tts"]}
    calls = {c["id"]: c for c in plan["calls"]}
    lay = sb.get("layers") or {}
    fc = {x["section"]: x for x in lay.get("frame_control") or []}
    texts = [x for x in lay.get("text") or [] if x.get("section")]
    sfx = lay.get("sfx") or []
    sec_by_id = {g["id"]: g for g in sb["sections"]}

    def spans_of(cid):
        """{scene: (s0, s1)} — where each scripted on-camera line sits inside the clip."""
        c = calls[cid]; sp = (led.get(cid) or {}).get("spans") or []
        on = [l["scene"] for l in c["lines"] if l["on_camera"]]
        return {sc: tuple(sp[i]) for i, sc in enumerate(on) if i < len(sp)}

    lens = {}

    def clip_len(cid):
        if cid not in lens:
            f = vm / "clips" / f"{cid}.mp4"
            lens[cid] = dur(f) if f.exists() else float(calls[cid]["duration"])
        return lens[cid]

    def whole(cid):
        return ((led.get(cid) or {}).get("line_check") or {}).get("verdict") != "CUT_OFF"

    t = 0.0
    pull_next = None
    sections, lines, picture, voice, sounds, notes = [], [], [], [], [], []
    for n, g in enumerate(sb["sections"], 1):
        gid, g0 = g["id"], float(g.get("starts") or 0)
        if gid in drop:
            notes.append(f"Section {n} ({gid}) taken out — " + (dec["drop_sections"].get(f"why_{gid.lower()}") or dec["drop_sections"]["why"]))
            continue
        src_g = sec_by_id.get(g.get("reuses")) if g.get("reuses") else g
        cs = [c for c in plan["calls"] if c["section_id"] == src_g["id"]]
        mains = [c for c in cs if c["clip_is"] == "clip"]
        cuts = [c for c in cs if c["clip_is"] == "cutaway"]
        a_sec = t
        # ---- a card / end card: the plate held for the swipe's own length
        def plate_of(sec):
            for sc in (sec_by_id.get(sec.get("reuses")) or sec)["scenes"]:
                for role in ("PLATE", "ENDCARD", "PACKSHOT"):
                    for ext in ("png", "jpg"):
                        if (vm / "media" / f"{sc}-{role}.{ext}").exists():
                            return f"media/{sc}-{role}.{ext}"
            return None
        if not cs and (not g.get("reuses") or plate_of(g)):
            hold = float(g.get("seconds") or 1.0)
            picture.append({"a": round(t, 3), "b": round(t + hold, 3), "kind": "plate", "section": gid,
                            "src": plate_of(g),
                            "name": g.get("setting") or g.get("maker")})
            t += hold
            sections.append({"n": n, "id": gid, "a": round(a_sec, 3), "b": round(t, 3), "name": g.get("setting"),
                             "swipe_s": swipe_len(g)})
            continue
        # ---- the section's lines, script order, each with its real sound
        seen, sec_lines = set(), []
        for sc in g["scenes"]:
            if sc in seen:
                continue
            seen.add(sc)
            holders = [c for c in cs if any(l["scene"] == sc for l in c["lines"])]
            lrow = next((l for c in holders for l in c["lines"] if l["scene"] == sc), None)
            if lrow is None and sc not in tts:
                continue
            plan_at = None
            for c in holders:
                for l in c["lines"]:
                    if l["scene"] == sc:
                        # a line split across clips (part 1/2, 2/2 …) runs from the first part's start to the LAST
                        # part's end (2026-10-08, the athlete: only the first part was kept, so the interviewer's 14.5 s question
                        # was mapped onto a 4 s window and the wrong clip played under it)
                        span = (c["window"][0] + l["at"], c["window"][0] + l["until"])
                        plan_at = span if plan_at is None else (min(plan_at[0], span[0]), max(plan_at[1], span[1]))
            on = lrow and lrow.get("on_camera")
            parts = [c for c in holders if c["clip_is"] == "clip" and
                     any(l["scene"] == sc and l.get("on_camera") and l.get("part") for l in c["lines"])]
            if on and len(parts) > 1:
                # one long line said across several clips (part 1/3, 2/3 …): each clip says its part
                for c in parts:
                    l_ = next(l for l in c["lines"] if l["scene"] == sc)
                    sp = spans_of(c["id"]).get(sc)
                    if sp:
                        sp = (max(0.0, sp[0] - PAD_IN), min(clip_len(c["id"]), sp[1] + PAD_OUT))
                    if not sp:
                        notes.append(f"{sc} part {l_.get('part')}: {c['id']} holds no words for it")
                        continue
                    sec_lines.append({"scene": sc, "part": l_.get("part"), "who": l_["speaker"], "text": l_["text"],
                                      "kind": "in clip", "clip": c["id"], "in": sp[0], "len": round(sp[1] - sp[0], 3),
                                      "plan": (c["window"][0] + l_["at"], c["window"][0] + l_["until"])})
                continue
            if on:
                # the clip that says it whole: the main clip unless it cut the line off, then a cutaway
                order = [c for c in holders if c["clip_is"] == "clip"] + [c for c in holders if c["clip_is"] == "cutaway"]
                pick = next((c for c in order if sc in spans_of(c["id"]) and whole(c["id"])), None) or \
                    next((c for c in order if sc in spans_of(c["id"])), None)
                if pick is None:
                    notes.append(f"{sc}: said on camera but no clip holds its words — off its own track instead")
                    on = False
                else:
                    s0, s1 = spans_of(pick["id"])[sc]
                    s0, s1 = max(0.0, s0 - PAD_IN), min(clip_len(pick["id"]), s1 + PAD_OUT)
                    if not whole(pick["id"]):
                        notes.append(f"{sc}: every clip cut it off — {pick['id']} used, line ends early")
                    elif pick["clip_is"] == "cutaway" and not whole(next(iter([c for c in holders if c['clip_is'] == 'clip']), pick)["id"]):
                        notes.append(f"{sc}: the main clip cut it off — taken whole from the second angle {pick['id']}")
                    sec_lines.append({"scene": sc, "who": lrow["speaker"], "text": lrow["text"], "kind": "in clip",
                                      "clip": pick["id"], "in": s0, "len": round(s1 - s0, 3), "plan": plan_at})
                    continue
            tt = tts.get(sc) or tts.get(f"{sc}")
            if tt is None:
                notes.append(f"{sc}: no sound for it")
                continue
            f = vm / tt["out"]
            sec_lines.append({"scene": sc, "who": tt["speaker"], "text": tt["text"],
                              "kind": "sound" if tt.get("sound") else "own track", "file": tt["out"],
                              "len": round(dur(f), 3) if f.exists() else float(tt.get("seconds") or 1), "plan": plan_at,
                              "nod": bool(lrow and lrow.get("nod"))})
        # ---- the words each clip actually says: follow a line to its last scripted word (the span the words
        #      check found can stop short of a word said right at the clip's end), trim a half-said word, and add
        #      a missing phrase right after its line (the owner, 3 Oct: "make sure things are cut cleanly")
        for l in sec_lines:
            if l["kind"] != "in clip":
                continue
            tw = _read(vm / "clips" / "omni" / l["clip"] / "transcript-words.json", [])
            tw = tw.get("words", tw) if isinstance(tw, dict) else tw
            last = re.sub(r"[^a-z]", "", l["text"].split()[-1].lower())[:6] if l["text"].split() else ""
            end = l["in"] + l["len"]
            for w in tw or []:                               # only the line's own LAST word, said within 1 s
                if w.get("type", "word") != "word" or not (end - PAD_OUT - 0.05 <= w["start"] <= end + 1.0):
                    continue
                if last and len(last) >= 4 and re.sub(r"[^a-z]", "", w["text"].lower())[:6][:len(last)][:5] == last[:5] \
                        and w["end"] <= clip_len(l["clip"]) + 0.01:
                    end = max(end, min(clip_len(l["clip"]), w["end"] + PAD_OUT))
            # a patch laid into this clip that runs past the line's own end: the shot runs on to the patch's end,
            # as far as the clip's own footage goes (2026-10-09, a TV-shopping ad: a re-said line tail ran 0.6 s
            # longer than the dropped one and spilled onto the next speaker's shot)
            for pa in (dec or {}).get("audio_patches") or []:
                f = out / pa["file"] if out else None
                if pa.get("clip") == l["clip"] and f and f.exists() and l["in"] <= float(pa["at"]) <= end + 0.05:
                    end = max(end, min(clip_len(l["clip"]), float(pa["at"]) + dur(f) + PAD_OUT))
            l["len"] = round(end - l["in"], 3)
            key = l["scene"] + ("#" + l["part"] if l.get("part") else "")
            tr = ((dec or {}).get("trim_line") or {}).get(key)
            if tr:
                l["len"] = round(min(l["len"], float(tr["to"]) - l["in"]), 3)
                notes.append(f"{key}: trimmed at {tr['to']}s of {l['clip']} — {tr.get('why', '')}")
        for add in (dec or {}).get("add_lines") or []:
            i = next((i for i, l in enumerate(sec_lines) if l["scene"] == add["after_scene"] and
                      (not add.get("part") or l.get("part") == add["part"])), None)
            f = out / add["file"] if out else None
            if i is None or not (f and f.exists()):
                continue
            ref = sec_lines[i]
            if ref["text"].rstrip().endswith(add["text"].strip()):
                ref["text"] = ref["text"].rstrip()[: -len(add["text"].strip())].rstrip()
            sec_lines.insert(i + 1, {"scene": add["after_scene"] + "+", **({"part": add["part"]} if add.get("part") else {}),
                                     "who": ref["who"], "text": add["text"], "kind": "own track",
                                     "file": add["file"], "len": round(dur(f), 3), "plan": ref.get("plan"), "added": add.get("why"),
                                     "base": out is not None})
        # ---- lay them one breath apart; the real clock for this section
        over_on = ((dec or {}).get("sounds") or {}).get("overlap", True)
        for i, l in enumerate(sec_lines):
            prev = sec_lines[i - 1] if i else None
            if over_on and prev is not None and l["kind"] == "sound" and prev["kind"] != "sound" and prev["who"] != l["who"]:
                # a listener's mm-hmm goes UNDER the end of the other person's line, the way people really murmur
                # (the swipe: "Surgeon 1 speaks, Creator murmurs"; the owner 4 Oct: "the overlays of the umms and the
                # MHMMs") — it never takes a gap of its own
                a_ = max(prev["a"] + 0.3, prev["b"] - SOUND_UNDER * l["len"])
                l["a"], l["b"] = round(a_, 3), round(a_ + l["len"], 3)
                l["under"] = prev["scene"]
                t = max(t, a_ + l["len"])
                continue
            if i:
                t += BREATH
            l["a"], l["b"] = round(t, 3), round(t + l["len"], 3)
            t += l["len"]
        if not sec_lines:
            t += float(g.get("seconds") or 0.5)
        b_sec = t

        def real(p):
            """plan-clock second (section-relative) → real second, through the line it falls in."""
            for l in sec_lines:
                pa, pb = l["plan"] or (None, None)
                if pa is not None and pa - 1e-6 <= p <= pb + 1e-6:
                    return l["a"] + (p - pa) / max(pb - pa, 1e-3) * l["len"]
            befores = [l for l in sec_lines if l["plan"] and l["plan"][1] <= p]
            return befores[-1]["b"] if befores else a_sec

        if gid in no_pic:
            # its picture is taken out; its lines keep going (the owner: "keep the talking going to the next"): the clip
            # before runs on as far as it has frames, the next section's first shot comes in early for the rest
            prev = max((p for p in picture if p.get("clip")), key=lambda p: p["b"], default=None)
            if prev is not None:
                room = clip_len(prev["clip"]) - (prev["in"] + (prev["b"] - prev["a"]))
                prev["b"] = round(min(b_sec, prev["b"] + max(0.0, room - 0.05)), 3)
                if prev["b"] < b_sec - 0.04:
                    pull_next = prev["b"]
            for l in sec_lines:
                l.update(section=gid)
                (voice if l["kind"] != "sound" else sounds).append(l)
            sections.append({"n": n, "id": gid, "a": round(a_sec, 3), "b": round(b_sec, 3), "name": g.get("setting"),
                             "plan_s": float(g.get("seconds") or 0), "swipe_s": swipe_len(g), "picture_out": True})
            notes.append(f"Section {n} ({gid}): picture taken out, its line runs over the picture before — "
                         f"{dec['drop_picture']['why']}")
            continue
        # ---- the picture: an on-camera line shows the clip that says it (lips in sync); the rest
        #      follow the plan — the main clip, and the second angle where the swipe cuts to it
        segs = []
        for l in sec_lines:
            if l["kind"] == "in clip":
                segs.append({"a": l["a"] - (LEAD if not segs else 0), "b": l["b"], "clip": l["clip"],
                             "in": max(0.0, l["in"] - (LEAD if not segs else 0)), "lip": True, "scene": l["scene"]})
        # fill every gap with the plan's picture for that moment
        def plan_clip(p):
            for c in cuts:
                if c["window"][0] <= p < c["window"][1]:
                    return c
            hit = next((c for c in mains if c["window"][0] <= p < c["window"][1]), None)
            if hit or not mains:
                return hit
            # a breath between two windows (the plan leaves ~0.15 s between clips): the NEAREST clip, never the
            # section's last one (2026-10-08, the athlete: the gap fell back to the guest talking under the interviewer's question)
            nxt_ = [c for c in mains if c["window"][0] >= p]
            return min(nxt_, key=lambda c: c["window"][0]) if nxt_ else \
                min(mains, key=lambda c: abs(p - c["window"][1]))
        filled, cursor = [], a_sec
        for s in sorted(segs, key=lambda s: s["a"]) + [{"a": b_sec, "b": b_sec, "end": True}]:
            if s["a"] > cursor + 1e-3:
                # walk the gap in small steps, switching clip where the plan does
                x = cursor
                while x < s["a"] - 1e-3:
                    # which plan second is x? invert real() by scanning lines
                    p = None
                    for l in sec_lines:
                        if l["a"] - BREATH <= x <= l["b"] + 1e-6 and l["plan"]:
                            frac = max(0.0, min(1.0, (x - l["a"]) / max(l["len"], 1e-3)))
                            p = l["plan"][0] + frac * (l["plan"][1] - l["plan"][0]); break
                    if p is None:
                        p = (x - a_sec) / max(b_sec - a_sec, 1e-3) * float(src_g.get("seconds") or 1)
                    c = plan_clip(p)
                    if c is None:
                        break
                    # run this clip until the plan switches
                    edges = sorted({real(e) for cc in cuts for e in cc["window"]} | {real(e) for cc in mains for e in cc["window"]})
                    nxt = min([e for e in edges if e > x + 1e-3] + [s["a"]])
                    ip = max(0.0, p - c["window"][0])
                    filled.append({"a": x, "b": nxt, "clip": c["id"], "in": round(ip, 3), "lip": False})
                    x = nxt
            if not s.get("end"):
                filled.append(s)
                cursor = s["b"]
        # the swipe's jump cuts inside the section: punch in / out on each, where it pushes in
        # punch in / out only where the swipe cuts (2026-10-08, the athlete: a one-camera swipe got alternate shots zoomed
        # in for no reason — "referencing the swipe itself so that we're not … doing all this adjustment")
        push = bool((fc.get(gid) or {}).get("cuts_at")) and (bool((fc.get(gid) or {}).get("push_in")) or bool(_section_people(src_g)))
        jc = sorted(real(x) for x in (fc.get(gid) or {}).get("cuts_at") or [])
        k = 0
        for s in filled:
            s["a"], s["b"] = round(s["a"], 3), round(s["b"], 3)
            if s["b"] - s["a"] < 0.04:
                continue
            fix = (FIXES.get(s["clip"]) or {}).get("crop")
            pieces = [s]
            for x in jc:
                for p_ in list(pieces):
                    if p_["a"] + 0.3 < x < p_["b"] - 0.3:
                        pieces.remove(p_)
                        left = {**p_, "b": round(x, 3)}
                        right = {**p_, "a": round(x, 3), "in": round(p_["in"] + (x - p_["a"]), 3)}
                        pieces += [left, right]
            clen = clip_len(p_clip := s["clip"])
            for p_ in pieces:
                if p_["in"] + (p_["b"] - p_["a"]) > clen + 0.05:
                    over = round(p_["in"] + (p_["b"] - p_["a"]) - clen, 2)
                    p_["in"] = round(max(0.0, clen - (p_["b"] - p_["a"])), 3)
                    if p_["in"] == 0.0:
                        notes.append(f"{p_clip} runs {over}s short at {p_['a']:.1f}s — the last frame holds")
            for p_ in sorted(pieces, key=lambda q: q["a"]):
                scale = PUNCH if (push and k % 2 == 1) else 1.0
                row = {**p_, "section": gid, "kind": calls[p_["clip"]]["clip_is"], "scale": scale}
                if fix and p_["in"] < fix["to"] and p_["in"] + (p_["b"] - p_["a"]) > fix["from"]:
                    row.update(scale=fix["scale"], y=fix["y"], fix=fix["why"])
                # a shot that measures a frame or two off against its own voice is slid by that much, nothing else
                # (2026-10-09: an edit move, never a remake) — decisions.json fixes.<clip>.nudge {from, to, by, why}
                # the whole cut measured a frame off against its voice (every talking shot −0.9 to −1.2 frames,
                # 2026-10-09): one offset for every clip piece, decisions.json picture_offset (seconds), not a nudge per shot
                off = float((dec or {}).get("picture_offset") or 0.0)
                if off:
                    row["in"] = round(max(0.0, row["in"] + off), 3)
                nd = (FIXES.get(p_["clip"]) or {}).get("nudge")
                if nd and nd["from"] <= p_["in"] < nd["to"]:
                    row["in"] = round(max(0.0, row["in"] + float(nd["by"])), 3)
                    row["nudge"] = nd.get("why")
                picture.append(row)
                k += 1
        if pull_next is not None:
            first = min((p for p in picture if p["section"] == gid), key=lambda p: p["a"], default=None)
            if first is not None:
                if first.get("lip"):
                    notes.append(f"{gid}: the picture before ran out {first['a'] - pull_next:.1f}s early and the next shot is a lip-synced line — holds")
                else:
                    first["a"] = round(pull_next, 3)          # comes in early; the shot just plays a moment longer
            pull_next = None
        for l in sec_lines:
            l.update(section=gid)
            (voice if l["kind"] != "sound" else sounds).append(l)
        sections.append({"n": n, "id": gid, "a": round(a_sec, 3), "b": round(b_sec, 3), "name": g.get("setting"),
                         "plan_s": float(g.get("seconds") or 0),
                         "swipe_s": swipe_len(g)})
    # ---- no black, no freeze: a shot asked to run longer than its clip has frames plays a touch slower
    #      (never below 0.75x, never on a lip-synced line); past that it is named for a cover
    for p in picture:
        if not p.get("clip"):
            continue
        clen, ln = clip_len(p["clip"]), p["b"] - p["a"]
        if p["in"] + ln <= clen - 0.04:
            continue
        if p.get("lip"):
            notes.append(f"{p['clip']} at {p['a']:.1f}s: a lip-synced line runs past the clip's end — needs a cover")
            continue
        p["in"] = round(max(0.0, min(p["in"], clen - ln - 0.05)), 3)
        if p["in"] + ln > clen - 0.04:
            sp = round((clen - 0.05 - p["in"]) / ln, 3)
            if sp >= 0.75:
                p["speed"] = sp
            else:
                notes.append(f"{p['clip']} at {p['a']:.1f}s: {ln:.1f}s of screen from {clen - p['in']:.1f}s of clip — needs a cover")
                p["speed"] = 0.75
    # ---- the swipe's words on screen and sound cues, on the real clock
    sec_at = {s["id"]: s for s in sections}
    words_on = []
    keep_kinds = set(((dec or {}).get("text_keep") or {}).get("kinds") or [])
    for x in texts:
        if keep_kinds and x.get("kind") not in keep_kinds:
            continue
        s = sec_at.get(x["section"])
        if not s:
            continue
        hs = float(((dec or {}).get("text_keep") or {}).get("headline_seconds") or LOOKS["defaults"]["headline_seconds"])
        a = s["a"]; b = s["b"] if x.get("kind") != "hook headline" else min(s["b"], a + hs)
        said = [l for l in voice + sounds if x.get("scene") and l["scene"] == x["scene"]]
        if said and x.get("kind") != "hook headline":   # words on screen live with the line they belong to
            a, b = min(l["a"] for l in said), max(l["b"] for l in said)
            key = " ".join(" ".join(x["words"]).split()[:2]).lower().strip(".,")
            hit = [l for l in said if key and key in l["text"].lower()]
            if hit and len(said) > 1:                  # a long line in parts: from the part that says these words
                a = hit[0]["a"]
        flat = " ".join(" ".join(w.split()) for w in x["words"]).replace(" / ", " ")
        if any(" ".join(" ".join(v.split()) for v in w["words"]).replace(" / ", " ") == flat and w["section"] == x["section"]
               for w in words_on):
            continue                                       # the same words twice (headline + on-screen copy): once
        words_on.append({"a": a, "b": b, "kind": x["kind"], "words": x["words"], "look": x.get("look"),
                         "look_id": ((dec or {}).get("text_looks") or {}).get(x["kind"]), "section": x["section"]})
    # option cards: a native text pop as a section starts (the owner, 3 Oct: "in between each of these
    # doctors we need to have something like option 1, option 2, option 3 … let's not do the paper thing just do
    # something that looks natively edited")
    ocd = (dec or {}).get("option_cards") or {}
    for oc_ in ocd.get("cards") or []:
        s_ = sec_at.get(oc_["section"])
        if s_:
            secs = float(oc_.get("seconds") or ocd.get("seconds") or LOOKS["defaults"]["option_seconds"])
            words_on.append({"a": s_["a"], "b": round(s_["a"] + secs, 3), "kind": "option card", "words": [oc_["text"]],
                             "section": oc_["section"], "look_id": ocd.get("look_id"),
                             **({"y": float(ocd["y"])} if ocd.get("y") is not None else {})})
    # the cards' own words (receipts, end card), word for word from the plan
    scenes = {x["id"]: x for x in (_read(vm / "plan.json", {}) or {}).get("scenes") or []}
    for g in sb["sections"]:
        s = sec_at.get(g["id"])
        if not s or any(w["section"] == g["id"] for w in words_on if w["kind"] in ("card", "endcard text")):
            continue
        if keep_kinds and not keep_kinds & {"card", "endcard"}:
            continue
        for sc in g["scenes"]:
            k = scenes.get(sc) or {}
            data = k.get(k.get("kind") or "") or {}
            ws = data.get("lines") or data.get("offer_lines")
            if ws and k.get("kind") in ("card", "endcard") and not any(w["section"] == g["id"] for w in words_on):
                words_on.append({"a": s["a"], "b": s["b"], "kind": k["kind"], "words": ws, "section": g["id"]})
    cues = [{"a": sec_at[x["section"]]["a"], "what": x["what"], "made": False, "section": x["section"]}
            for x in sfx if x.get("section") in sec_at]
    music = (lay.get("music") or [{}])[0]
    mu = (dec or {}).get("music") or {}
    mf = out / mu["file"] if out and mu.get("file") else None
    if mf is not None and mf.exists():
        md = dur(mf)
        music = {"what": music.get("what"), "made": True, "file": mu["file"], "a": 0.0, "b": round(min(md, t), 3),
                 "under_voice_db": mu.get("under_voice_db", LOOKS["mix"]["music_under_voice_db"]),
                 "in_pauses_db": mu.get("in_pauses_db", LOOKS["mix"]["music_in_pauses_db"]),
                 "why": mu.get("why")}
    # ---- faces and mouths: words off the face; lips that move with no words get covered
    covers = []
    lead = ((dec or {}).get("story") or {}).get("lead") or next((l["who"] for l in voice if l["kind"] == "in clip"), "")
    tk = {}
    if out is not None:
        tk = tracks(vm, out, sorted({p["clip"] for p in picture if p.get("clip")}))

        def rows(p, a=None, b=None):
            a = p["a"] if a is None else a; b = p["b"] if b is None else b
            t0 = p["in"] + (a - p["a"]); t1 = t0 + (b - a)
            return [r for r in tk.get(p["clip"], []) if t0 - 0.05 <= r["t"] <= t1 + 0.05 and r["w"] > 0]

        for p in picture:
            if p["kind"] == "plate" or p.get("lip"):
                continue
            x = p["a"]
            while x < p["b"] - 0.2:
                y = min(p["b"], x + 0.5)
                o = [r["open"] for r in rows(p, x, y) if r["open"] >= 0]
                if len(o) >= 3 and sum(abs(u - v) for u, v in zip(o, o[1:])) / (len(o) - 1) > LIPS_MOVING:
                    if covers and covers[-1]["why"] == "lips move, no words" and covers[-1]["b"] >= x - 0.05:
                        covers[-1]["b"] = round(y, 3)
                    else:
                        covers.append({"a": round(x, 3), "b": round(y, 3), "why": "lips move, no words", "clip": p["clip"],
                                       "section": p["section"]})
                x = y

        def face_box(a, b):
            bx = None
            for p in picture:
                if p.get("clip") and p["a"] < b and p["b"] > a:
                    for r in rows(p, max(a, p["a"]), min(b, p["b"])):
                        top, bot = r["y"], r["y"] + r["h"]   # the mouth tool reports top-down (checked on frames, 3 Oct)
                        bx = (top, bot) if bx is None else (min(bx[0], top), max(bx[1], bot))
            return bx

        for w in words_on:
            if w["kind"] == "option card":
                continue                                      # top centre, a native text pop
            fb = face_box(w["a"], w["b"])
            w["y"] = TEXT_BANDS[0][0]
            for lo, hi in TEXT_BANDS:
                if fb is None or hi < fb[0] - 0.02 or lo > fb[1] + 0.02:
                    w["y"] = lo; break
            else:
                w["y"] = 0.80 if fb and fb[1] < 0.78 else 0.06
                w["face_note"] = "no clear band — set clear of the face's widest reach"
            w["face"] = fb
        for l in voice:
            fb = face_box(l["a"], l["b"])
            l["cap_y"] = 0.80 if not fb or fb[1] < 0.76 else 0.88
    # ---- cover with B-roll: lips moving with no words, the joins where one clip restarts after another,
    #      and the moments the brief wants shown (how to use it, real results)
    joins = []
    pic_sorted = sorted([p for p in picture if p.get("clip")], key=lambda p: p["a"])
    for x, y in zip(pic_sorted, pic_sorted[1:]):
        if x["clip"] != y["clip"] and x["section"] == y["section"] and calls[x["clip"]]["clip_is"] == calls[y["clip"]]["clip_is"] == "clip":
            joins.append({"a": round(max(x["a"], y["a"] - 0.4), 3), "b": round(min(y["b"], y["a"] + 0.4), 3),
                          "why": "one clip restarts after another", "section": x["section"]})
    wanted = []
    for w_ in ((dec or {}).get("broll") or {}).get("wanted") or []:
        for l in voice:
            if l["scene"] in w_["scenes"]:
                wanted.append({"a": l["a"], "b": l["b"], "why": f"show: {w_['show']}", "section": l["section"], "scene": l["scene"]})
    covers = sorted(covers + joins + wanted, key=lambda c: c["a"])
    # ---- the B-roll laid: real footage on top of the picture (the clip under it keeps playing, so its sound stays)
    br = (dec or {}).get("broll") or {}
    secs_each = float(br.get("seconds") or 4.0)
    broll = []
    for pl in br.get("place") or []:
        if pl.get("insert"):
            hits = [c for c in covers if c.get("clip") == pl["at_cover"] and c["why"] == "lips move, no words"]
            c = hits[int(pl.get("nth", 1)) - 1] if len(hits) >= int(pl.get("nth", 1)) else None
            if c is None:
                notes.append(f"insert for {pl['at_cover']}: no such cover"); continue
            a0 = max(0.0, c["a"] - 0.1)
            broll.append({"a": round(a0, 3), "b": round(a0 + float(pl["len"]), 3), "name": pl["insert"], "clip": pl["insert"],
                          "in": float(pl.get("in") or 0), "why": pl.get("why"), "insert": True})
            continue
        if pl.get("calm"):
            hits = [c for c in covers if c.get("clip") == pl["at_cover"] and c["why"] == "lips move, no words"]
            c = hits[int(pl.get("nth", 1)) - 1] if len(hits) >= int(pl.get("nth", 1)) else None
            if c is None:
                notes.append(f"calm insert for {pl['at_cover']}: no such cover"); continue
            need = round(max(1.5, min(secs_each, c["b"] - c["a"] + 0.4)), 2)
            setting = next((g.get("setting") for g in sb["sections"] if g["id"] == c["section"]), None)
            same_room = [x["id"] for x in plan["calls"] if next((g.get("setting") for g in sb["sections"]
                                                                  if g["id"] == x["section_id"]), None) == setting]
            used = [(r["clip"], r["in"], r["in"] + (r["b"] - r["a"])) for r in broll if r.get("insert")]
            best = None
            for cid in same_room:
                rows_ = [r for r in tk.get(cid, []) if r["w"] > 0 and r["open"] >= 0]
                for i in range(len(rows_)):
                    w_ = [r for r in rows_ if rows_[i]["t"] <= r["t"] <= rows_[i]["t"] + need]
                    if len(w_) < need * 8:
                        continue
                    o = [r["open"] for r in w_]
                    mv = sum(abs(u - v) for u, v in zip(o, o[1:])) / max(1, len(o) - 1)
                    t0 = rows_[i]["t"]
                    if any(u == cid and t0 < e and t0 + need > s_ for u, s_, e in used):
                        continue
                    if t0 + need > clip_len(cid) - 0.1:
                        continue
                    if best is None or mv < best[0]:
                        best = (mv, cid, t0)
            if best is None or best[0] > 0.025:
                notes.append(f"calm insert for {pl['at_cover']}: no quiet moment of her in that room — needs B-roll"); continue
            a0 = max(0.0, c["a"] - 0.2)
            broll.append({"a": round(a0, 3), "b": round(a0 + need, 3), "name": best[1], "clip": best[1], "in": best[2],
                          "why": pl.get("why") or "lips move, no words — a quiet moment of her from the same room", "insert": True})
            continue
        if pl.get("clip_window"):
            # a stretch of one clip, by the clip's own time (a glitch seen in it, e.g. a third hand at 1.5–5.0 s)
            ps = [p for p in picture if p.get("clip") == pl["clip_window"]]
            hits = []
            for p in ps:
                lo, hi = p["in"], p["in"] + (p["b"] - p["a"]) * p.get("speed", 1)
                x0, x1 = max(lo, pl["from"]), min(hi, pl["to"])
                if x1 > x0:
                    hits.append((p["a"] + (x0 - lo) / p.get("speed", 1), p["a"] + (x1 - lo) / p.get("speed", 1)))
            if not hits:
                notes.append(f"B-roll for {pl['clip_window']} {pl['from']}–{pl['to']}s: that stretch is not in the cut"); continue
            a0 = min(h[0] for h in hits) - 0.15
            end = max(h[1] for h in hits) + 0.15
            pl = {**pl, "scene": "window"}                   # cover exactly the stretch
        elif pl.get("at_cover"):
            c = next((c for c in covers if c.get("clip") == pl["at_cover"] and c["why"] == "lips move, no words"), None)
            if c is None:
                notes.append(f"B-roll for {pl['at_cover']}: no such cover"); continue
            a0 = max(0.0, c["a"] - 0.3); end = a0 + secs_each * len(pl["clips"])
        else:
            ls = [l for l in voice + sounds if l["scene"] == pl["scene"] and (not pl.get("part") or l.get("part") == pl["part"])]
            if not ls:
                notes.append(f"B-roll for {pl['scene']}: the line is not in the cut"); continue
            a0 = min(l["a"] for l in ls) + float(pl.get("from") or 0)
            end = max(l["b"] for l in ls)
            if pl.get("until_scene"):
                us = [l for l in voice + sounds if l["scene"] == pl["until_scene"]]
                end = max([l["b"] for l in us] + [end])
                ix = next((i for i, x in enumerate(sections) if us and x["id"] == us[0]["section"]), None)
                sec_end = sections[ix]["b"] if ix is not None else None
                while ix is not None and ix + 1 < len(sections) and sections[ix + 1].get("picture_out"):
                    ix += 1; sec_end = sections[ix]["b"]   # a section with no picture of its own rolls on too
                if sec_end:
                    end = max(end, sec_end)              # "keep rolling": to the end of that section
        t_ = a0
        for name in pl["clips"]:
            if t_ >= end - 0.5:
                break
            f = (out / "broll" / f"{name}.mp4") if out else None
            if f is not None and not f.exists():
                notes.append(f"B-roll {name}: not pulled yet — slot left as it is"); continue
            ln = min(secs_each, dur(f) if f and f.exists() else secs_each)
            if pl.get("scene") == "window":
                b_ = min(t_ + ln, max(end, t_ + 1.5))           # a cover over a glitch ends with the glitch
            elif pl.get("scene"):
                b_ = min(t_ + ln, max(end, t_ + 1.6))          # never a flash, even over a short line
            else:
                b_ = t_ + ln
            if b_ - t_ < 1.5 and broll and abs(broll[-1]["b"] - t_) < 0.01:
                broll[-1]["b"] = round(b_, 3)               # never a flash: the piece before runs a moment longer
                t_ = b_
                continue
            broll.append({"a": round(t_, 3), "b": round(b_, 3), "name": name, "file": f"broll/{name}.mp4", "why": pl.get("why"),
                          **({"failed_solution": True} if pl.get("failed_solution") else {})})
            t_ = b_
        if t_ < end - 0.6 and pl.get("scene"):
            notes.append(f"B-roll for {pl['scene']}: {end - t_:.1f}s left uncovered — add a clip")
    for r in broll:
        if r.get("insert"):
            room = clip_len(r["clip"]) - 0.05 - r.get("in", 0)
        else:
            f = out / r["file"] if out else None
            room = (dur(f) - 0.05) if f and f.exists() else secs_each
        if r["b"] - r["a"] > room:
            r["speed"] = round(max(0.75, room / (r["b"] - r["a"])), 3)
    def clip_to_edit(cid, t0, t1):
        """A stretch of a clip's own time → where it sits in the cut (first..last on screen)."""
        hits = []
        for p in picture:
            if p.get("clip") != cid:
                continue
            sp = p.get("speed", 1); lo, hi = p["in"], p["in"] + (p["b"] - p["a"]) * sp
            x0, x1 = max(lo, t0), min(hi, t1)
            if x1 > x0:
                hits.append((p["a"] + (x0 - lo) / sp, p["a"] + (x1 - lo) / sp))
        return (min(h[0] for h in hits), max(h[1] for h in hits)) if hits else None

    # ---- audio patches: a word fixed in the edit (the clip's sound muted across it, the patch laid in)
    patches = []
    for pa in (dec or {}).get("audio_patches") or []:
        win = clip_to_edit(pa["clip"], pa["from"], pa["to"])
        at = clip_to_edit(pa["clip"], pa["at"], pa["at"] + 0.01)
        f = out / pa["file"] if out else None
        if not win or not at or not (f and f.exists()):
            notes.append(f"audio patch {pa['file']}: not placed (stretch not in the cut, or file missing)"); continue
        # the clip's own words stay muted to the end of the line (or the fix's end): a fix that ends before the
        # original does let the old word's tail through after it (4 Oct: "refund" heard cut off)
        line_end = max((l["b"] for l in voice if l.get("clip") == pa["clip"] and l["a"] <= win[0] + 0.05 <= l["b"]),
                       default=win[1])
        b_fix = at[0] + dur(f)
        patches.append({"mute_a": round(win[0], 3), "mute_b": round(max(win[1], line_end, b_fix), 3), "a": round(at[0], 3),
                        "b": round(b_fix, 3), "file": pa["file"], "why": pa.get("why")})
    # ---- the story guard: until the section where the product comes in, the screen is the lead's own
    #      experience — no other people, products or results (the owner, 3 Oct: "we're focusing on the woman in
    #      the chair's experience. we don't really show anything results related of other people or product
    #      until much later")
    st = (dec or {}).get("story") or {}
    lead_until = next((x["a"] for x in sections if x["id"] == st.get("lead_only_until")), None)
    if lead_until is not None:
        keep = []
        for r in broll:
            if not r.get("insert") and not r.get("failed_solution") and r["a"] < lead_until - 0.05:
                notes.append(f"B-roll {r['name']} at {r['a']:.1f}s refused — before {st['lead_only_until']} the screen is the lead's own experience")
            else:
                keep.append(r)
        broll = keep
    # ---- close-up on the lead: a tight crop of the very moment on screen, framed on the part being talked about
    #      ABOVE the mouth — reads as the camera pushing in, hides lips that move with no words
    for pl in (dec or {}).get("closeups") or []:
        if pl.get("clip_window"):
            win = clip_to_edit(pl["clip_window"], pl["from"], pl["to"])
            if not win:
                notes.append(f"close-up for {pl['clip_window']}: that stretch is not in the cut"); continue
            w0, w1 = win[0] - 0.1, win[1] + 0.1
        elif pl.get("at_cover"):
            hits = [c for c in covers if c.get("clip") == pl["at_cover"] and c["why"] == "lips move, no words"]
            c = hits[int(pl.get("nth", 1)) - 1] if len(hits) >= int(pl.get("nth", 1)) else None
            if c is None:
                notes.append(f"close-up for {pl['at_cover']}: no such cover"); continue
            w0, w1 = c["a"] - 0.2, c["b"] + 0.2
        else:
            ls = [l for l in voice + sounds if l["scene"] == pl["scene"] and (not pl.get("part") or l.get("part") == pl["part"])]
            if not ls:
                notes.append(f"close-up for {pl['scene']}: line not in the cut"); continue
            w0, w1 = min(l["a"] for l in ls) + float(pl.get("from") or 0), max(l["b"] for l in ls)
        zoom = float(pl.get("zoom") or 2.6)
        new = []
        for p in picture:
            if not p.get("clip") or p["b"] <= w0 or p["a"] >= w1:
                new.append(p); continue
            a, b = max(p["a"], w0), min(p["b"], w1)
            sp = p.get("speed", 1)
            if a > p["a"] + 0.04:
                new.append({**p, "b": round(a, 3)})
            rows_ = [r for r in tk.get(p["clip"], []) if r["w"] > 0 and p["in"] + (a - p["a"]) * sp - 0.1 <= r["t"] <= p["in"] + (b - p["a"]) * sp + 0.1]
            if b - a < 0.5:
                rows_ = []                                   # never a flash of a close-up
            if rows_:
                # ONE face: a tracker that hops between two people would average to the empty space between them
                # (2026-10-09: a close-up framed the wall between two faces) — keep the face seen most
                groups = []
                for r in sorted(rows_, key=lambda r: r["x"] + r["w"] / 2):
                    cx = r["x"] + r["w"] / 2
                    if groups and cx - (groups[-1][-1]["x"] + groups[-1][-1]["w"] / 2) <= max(0.08, r["w"] * 0.5):
                        groups[-1].append(r)
                    else:
                        groups.append([r])
                rows_ = max(groups, key=len)
                fx = sum(r["x"] + r["w"] / 2 for r in rows_) / len(rows_)
                ftop = sum(r["y"] for r in rows_) / len(rows_); fh = sum(r["h"] for r in rows_) / len(rows_)
                fw = sum(r["w"] for r in rows_) / len(rows_)
                mouth_top = ftop + MOUTH_TOP * fh
                part, said = part_named(voice + sounds, a, b, pl)
                must_hide = hide_mouth(covers, sounds, a, b, pl) or others_talking(voice, lead, a, b)
                if part:
                    # the part being talked about, framed (the owner, 4 Oct: "we were talking about her lips, so you're
                    # supposed to zoom into the lips … when we're talking about her temples, you zoom into the temples")
                    yr, k = PARTS[part]
                    z = min(3.2, max(1.6, 1.0 / max(0.05, k * fw)))
                    half = 0.5 / z
                    cy = max(half, min(1 - half, ftop + yr * fh))
                    if must_hide and cy + half > mouth_top:
                        part = None                          # it would show her talking with no words: the cover wins
                if part:
                    pass                                     # framed above
                elif not must_hide:
                    # nothing named and the mouth can show: the cheeks, the middle of the face (never the forehead:
                    # 4 Oct "zooming into her forehead randomly")
                    part = "cheeks"
                    z = CHEEK_ZOOM
                    half = 0.5 / z
                    cy = max(half, min(1 - half, ftop + PARTS["cheeks"][0] * fh))
                else:
                    # nothing named and her lips would move with no sound of hers: eyes and cheeks, mouth out of frame
                    z = min(3.2, max(zoom, 1.0 / max(0.12, mouth_top - 0.02)))
                    half = 0.5 / z
                    cy = max(half, mouth_top - half - 0.02)
                    if cy - half < ftop - 0.02:              # the crop's top must not climb above the brows
                        z = min(3.2, 1.0 / max(0.05, mouth_top - ftop)); half = 0.5 / z
                        cy = max(half, mouth_top - half - 0.02)
                mid = {**p, "a": round(a, 3), "b": round(b, 3), "in": round(p["in"] + (a - p["a"]) * sp, 3),
                       "scale": round(z, 2), "x": round(fx, 3), "y": round(cy, 3),
                       "closeup": pl.get("why") or "close-up on her", "frames": part or "eyes and cheeks",
                       **({"said": said} if said else {})}
                if not part and cy + half > mouth_top + 0.005:
                    notes.append(f"close-up at {a:.1f}s: her mouth sits too high to crop out — needs another cover")
                if part in MOUTH_PARTS and any(c["why"] == "lips move, no words" and c["a"] < b and c["b"] > a for c in covers):
                    notes.append(f"close-up at {a:.1f}s frames her {part} (\"{said}\") while her lips move with no words")
            else:
                mid = {**p, "a": round(a, 3), "b": round(b, 3), "in": round(p["in"] + (a - p["a"]) * sp, 3)}
                if b - a >= 0.5:
                    notes.append(f"close-up at {a:.1f}s: no face found in {p['clip']} — left as it is")
            new.append(mid)
            if b < p["b"] - 0.04:
                new.append({**p, "a": round(b, 3), "in": round(p["in"] + (b - p["a"]) * sp, 3)})
        picture[:] = sorted(new, key=lambda q: q["a"])
        for c in covers:
            if c["why"] == "lips move, no words" and w0 <= c["a"] + 0.05 and w1 >= c["b"] - 0.05:
                c["covered"] = True
    for l in voice:                                       # a close-up fills the frame with her face: captions go low
        if any(p.get("closeup") and p["a"] < l["b"] and p["b"] > l["a"] for p in picture):
            l["cap_y"] = 0.88
    broll.sort(key=lambda r: r["a"])
    for x, y in zip(broll, broll[1:]):
        if y["a"] < x["b"]:
            x["b"] = y["a"]                                  # never two B-roll on top of each other
    for c in covers:
        c["covered"] = c.get("covered") or any(r["a"] <= c["a"] + 0.05 and r["b"] >= c["b"] - 0.05 for r in broll)
    for f in FIXES:
        if f in calls:
            notes.append(f"{f}: {list(FIXES[f].values())[0]['why']}")
    return {"from_run": str(vm), "brand": run.get("brand"), "label": run.get("label"),
            "total": round(t, 3), "swipe_total": sb.get("swipe_seconds"), "plan_total": sb.get("seconds"),
            "clock": "every line sets its own time (its real sound); lines one breath apart; the swipe sets the cuts, angles, push-ins, words and cues",
            "sections": sections, "picture": picture, "voice": voice, "sounds": sounds,
            "covers": covers, "broll": broll, "patches": patches, "text": words_on, "captions": {"look": next((x.get("look") for x in lay.get("text") or [] if x.get("kind") == "captions"), None),
                         "look_id": ((dec or {}).get("captions") or {}).get("look_id") or ((dec or {}).get("captions") or {}).get("look")},
            "lead": lead,
            "sfx": cues, "music": music if music.get("made") else {"what": music.get("what"), "made": False}, "notes": notes,
            "moves": ["sound kept only across each clip's scripted words (made-up off-camera talk is never heard)",
                      "a cut-off line taken whole from another angle", "punch-ins on the swipe's cuts where it pushes in",
                      *[f"{k}: {list(v.values())[0]['why']}" for k, v in FIXES.items()]]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="the edit as a map — builds the timeline, renders nothing")
    ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--hooks", action="store_true",
                                                                  help="also cut one version per hook clip (edit-map-<hook>.json)")
    a = ap.parse_args(argv)
    vm = Path(a.run)
    run_ = _read(vm / "run.json", {})
    root = Path(__file__).resolve().parents[3]
    out = Path(a.out) if a.out else root / "runs" / "video-edit" / (run_.get("brand") or "brand") / (run_.get("label") or "ad")
    out.mkdir(parents=True, exist_ok=True)
    m = build(vm, out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "edit-map.json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n")
    if a.hooks:
        for hc in [c for c in _read(vm / "clips" / "plan.json")["calls"] if c.get("hook")]:
            if not (vm / "clips" / f"{hc['id']}.mp4").exists():
                print(f"  hook {hc['id']}: clip not made yet"); continue
            hm = build(vm, out, hook=hc["id"]); hm["hook"] = hc["hook"]
            (out / f"edit-map-{hc['id']}.json").write_text(json.dumps(hm, indent=1, ensure_ascii=False) + "\n")
            print(f"  hook version {hc['id']} ({hc['hook']}): {hm['total']:.1f}s")
    print(f"covers: {sum(c['why'] == 'lips move, no words' for c in m['covers'])} lips-without-words · "
          f"{sum(c['why'].startswith('one clip') for c in m['covers'])} restarts · {sum(c['why'].startswith('show') for c in m['covers'])} show-it moments")
    print(f"edit map: {m['total']:.1f}s (swipe {m['swipe_total']}s) · {len(m['picture'])} picture cuts · "
          f"{len(m['voice'])} lines · {len(m['sounds'])} sounds · {len(m['text'])} words on screen → {out / 'edit-map.json'}")
    for n in m["notes"]:
        print("  note  " + n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
