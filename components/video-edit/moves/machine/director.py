"""moves: the director on the chain (2026-11-17). For every scene of a Video Studio production: the shortlist
(suggest.py's scoring), the creative director's three pitches (prompts/creative-director-v2-owner.md), and ONE move
kept by a stated machine rule, written as edit data the Studio lays itself. No human pick, no paid generation: a move
that needs paid generation, or that the edit cannot draw yet, is recorded as a gap, never made.

    python3 director.py <production folder> [--run <writing run>] [--pitch rules|claude] [--force]

Writes <production>/edit/moves-picks.json (the edit data, the pitches, the reasons) and moves-picks.md (to read).
Called by the Studio's edit stage (components/video-studio/edit_moves.py); to_studio.py lays the picks into the cut.

THE PICK RULE (the same for every pitch, whoever pitched it):
  eligible   every move in the option is one the edit lays today for free (LAY), none breaks an owner edit ruling
             (OUT: flash frames, a repeated clip, dead air), and a hand-off move has a scene after it
  beat       +4 fires on a named change (hit, drop, section) or a downbeat, +3 on a beat, a hand-off +3 when it sits
             within TOL of a beat, +1 when it does not (a hand-off carries the words and never moves)
  scene      +3 a match cut whose two sides share a shape (round to round), +2 the same motion, else +0
  target     + wow x boldness (the brief's creative-controls target: stopping power, dramatisation, absurdity,
             intensity, mean / 4); -1.5 a frame-break or time move when the target's realism is 4 or more
  spread     -1 for each earlier scene that already carries the move
  Highest wins; a tie goes to the bolder move, then Safe, Bold, Wild order. No eligible pitch: the best eligible
  move on the shortlist is laid instead and the pitches are recorded as gaps. Nothing eligible at all: no move.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOVES = HERE.parent
sys.path.insert(0, str(HERE))
import suggest as SG  # noqa: E402  the shortlist's scoring, reused as it is

LIBRARY = MOVES / "library" / "moves-v1-owner.json"
PROMPT = MOVES / "prompts" / "creative-director-v2-owner.md"
RULE = "pick-rule-v1"
FPS = 24000 / 1001
FLOOR = 3.0                    # a move must score this by THE PICK RULE to replace the clean cut
TOL = 0.12                     # a hand-off this close to a beat is on it (video-edit looks/retention.json snap tolerance)
EDGE = 0.35                    # an in-scene move keeps this far from the scene's own cuts

# What the edit lays today, for free, with compose.py's own drawers (looks/transitions.json, a clip's `punch`).
LAY = {
    "match-cut-shape": {"where": "hand-off", "transition": "match",
                        "how": "a hard cut on the hand-off with compose's match settle (the in-clip eases from the "
                               "out-clip's scale); the two shapes must sit in the same place in the frame"},
    "match-cut-motion": {"where": "hand-off", "transition": "match",
                         "how": "a hard cut on the hand-off with compose's match settle, the motion carried across"},
    "whip-pan-handoff": {"where": "hand-off", "transition": "whip",
                         "how": "compose's whip: 0.1 s blur-slide out, 0.12 s blur-slide in, on the hand-off"},
    "punch-in-kick": {"where": "in-scene", "punch": 1.10,
                      "how": "the scene's clip split on the beat; the second piece punched in 10% (compose punch)"},
    "crash-zoom": {"where": "in-scene", "punch": 1.18,
                   "how": "the scene's clip split on the beat; the second piece punched in 18% (a jump, compose punch)"},
}
# Owner edit rulings (16-17 Nov): clean cuts, no flash frames, no repeated clip, no dead air, every cut on purpose.
OUT = {
    "flash-insert": "a flash frame between shots (owner: no flash frames)",
    "blink": "black frames between shots (owner: no flash frames)",
    "colour-flash": "a colour flash frame (owner: no flash frames)",
    "stutter": "repeats frames of the clip (owner: no repeated clip)",
    "in-and-out": "plays the same piece again (owner: no repeated clip)",
    "clone-each-pass": "the same footage again on each pass (owner: no repeated clip)",
    "smash-to-silence": "cuts to silence on a held frame (owner: no dead air)",
    "tape-stop": "runs down to a held frame (owner: no dead air)",
}
SHAPES = {
    "round": "collar ring rim seal coin lid cap plate bowl cup mug clock wheel button sun moon ball circle jar "
             "tub dial pearl orange lemon donut bagel hoop porthole".split(),
    "flat": "card letter envelope check cheque phone laptop screen door mirror page box drawer sign note".split(),
    "long": "tube pen bottle receiver brush razor stick wand pole candle".split(),
}
MOTIONS = "lift raise push pull turn roll press point rub drag open tap reach spin drop throw slide".split()
WORDS_ROLLS = {"C": "a card", "E": "the end card"}   # brief roll codes whose picture is set words
BOLD_DIALS = ("stopping_power", "dramatisation", "absurdity", "intensity")


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


_LIB = {}


def library():
    if not _LIB:
        _LIB.update({m["id"]: m for m in (load(LIBRARY, {}) or {}).get("moves") or []})
    return _LIB


# ---------------------------------------------------------------- the scene facts
def _take(B, s, brief):
    """(the scene's picked workflow take, its production take.json): either may be {}."""
    pick = (brief.get("picks") or {}).get(s) or "take-1"
    return load(B / "scenes" / s / ("%s.json" % pick), {}) or {}, load(B / "scenes" / s / "take.json", {}) or {}


def shots_of(s, prod, rows):
    """The scene's shots in order: [{"id", "what", "props"}], from the production take's beats, else the shot list."""
    out = {}
    for b in prod.get("beats") or []:
        sid = b.get("shot") or s
        x = out.setdefault(sid, {"id": sid, "what": [], "props": set()})
        x["what"].append(" ".join(v for v in (b.get("who"), b.get("action")) if v))
        x["props"].update(v for v in (b.get("prop"), b.get("target")) if v)
    if not out:
        for r in rows:
            if r.get("scene") == s:
                out[r["id"]] = {"id": r["id"], "what": [r.get("shows") or r.get("swipe_does") or ""], "props": set()}
    return [{"id": x["id"], "what": "; ".join(w for w in x["what"] if w), "props": sorted(x["props"])} for x in out.values()]


def shape_of(text):
    """{"round": "collar", ...}: the first word of each shape class named in a shot."""
    words = re.findall(r"[a-z]+", (text or "").lower())
    out = {}
    for k, vs in SHAPES.items():
        hit = next((w for w in words if w in vs or (w.endswith("s") and w[:-1] in vs)), None)
        if hit:
            out[k] = hit
    return out


def motion_of(text):
    """The motions a shot names, each by its base verb (lifts -> lift, presses -> press)."""
    words = set(re.findall(r"[a-z]+", (text or "").lower()))
    return sorted({v for v in MOTIONS if v in words or v + "s" in words or v + "es" in words})


def pair(a_text, b_text):
    """What the last shot of one scene and the first of the next share: ("shape", "round: collar -> seal") or
    ("motion", "lift"), or (None, "")."""
    sa, sb = shape_of(a_text), shape_of(b_text)
    for k in ("round", "flat", "long"):
        if k in sa and k in sb:
            return "shape", "%s: %s -> %s" % (k, sa[k], sb[k])
    common = sorted(set(motion_of(a_text)) & set(motion_of(b_text)))
    if common:
        return "motion", common[0]
    return None, ""


def _seconds(f):
    import subprocess
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def windows(B, brief, rows, seconds=_seconds):
    """{scene: (start, end)} on the ad's clock, how it was found, and the length. The rendered layout when the clips
    are made; before that the scenes laid end to end at the length of their own voice read (voice/continuous/<s>.mp3),
    else their words at 2.7 a second (2.5 s when silent), as to_studio.py estimates a slot; named as an estimate."""
    lay = load(B / "studio-build" / "layout.json", {}) or {}
    sc = {x["scene"]: (float(x["start"]), float(x["end"])) for x in lay.get("scenes") or []}
    if sc and all(s in sc for s in brief.get("order") or []):
        return sc, "the rendered cut's clock (studio-build/layout.json)", float(lay.get("length") or 0)
    est, at, by = {}, 0.0, set()
    for s in brief.get("order") or []:
        f = B / "voice" / "continuous" / ("%s.mp3" % s)
        d = seconds(f) if f.exists() else None
        if d:
            by.add("voice reads")
        else:
            wf, _ = _take(B, s, brief)
            n = len((wf.get("words") or "").split())
            d = round(n / 2.7, 2) if n else 2.5
            by.add("words at 2.7 a second")
        est[s] = (round(at, 3), round(at + d, 3))
        at += d
    return est, "an estimate: the clips are not made yet; scenes end to end at their %s" % " and ".join(sorted(by)), at


# ---------------------------------------------------------------- the music on the ad's clock
def swipe_clock(R, rows, wins):
    """The swipe's second -> ours, through the Studio's own clock (video-studio edit_stage.clock: the shot-list row
    that copies the swipe shot, its share of our scene), or None when the run has no frame map."""
    fm = load(Path(R) / "framemap" / "framemap.json", {}) or {}
    if not fm.get("shots"):
        return None
    sys.path.insert(0, str(MOVES.parents[1] / "video-studio"))
    import edit_stage as ES
    return ES.clock(fm, rows, {"scenes": [{"scene": s, "start": a, "end": b} for s, (a, b) in wins.items()]})


def music_events(B, R, wins, clock_from_layout, beats_fn=None, ours=None):
    """{"beats": [t], "downbeats": [t], "changes": [{"at", "what"}], "from": "..."} on the ad's clock.
    The production's bed when it has one (its beats read by librosa through video-edit beats.py, cached in
    edit/bed-beats.json; its cue sheet's sections), else the swipe's measured music (sound-sheet.json)."""
    bed_j, bed = load(B / "music" / "bed.json", None), B / "music" / "bed.mp3"
    if clock_from_layout and bed_j is not None and bed.exists():
        m0 = float(bed_j.get("starts_at") or 0.0) + min((a for a, _ in wins.values()), default=0.0)
        cache = B / "edit" / "bed-beats.json"
        c = load(cache, {}) or {}
        if c.get("mtime") != bed.stat().st_mtime:
            if beats_fn is None:
                sys.path.insert(0, str(MOVES.parent / "machine"))
                import beats as BT
                beats_fn = BT.detect
            got = beats_fn(bed)
            c = {"mtime": bed.stat().st_mtime, "beats": got.get("beats") or [], "tempo_bpm": got.get("tempo_bpm"),
                 "by": got.get("by")}
            cache.parent.mkdir(exist_ok=True)
            cache.write_text(json.dumps(c))
        beats = [round(m0 + b, 3) for b in c.get("beats") or []]
        changes = [{"at": round(m0 + float(x["at"]), 3), "what": x.get("what", "")}
                   for x in bed_j.get("cue_sheet") or [] if float(x.get("at", 0)) > 0.05]
        src = "the production's music bed (music/bed.mp3: beats by %s, %s BPM; sections from bed.json)" % (
            c.get("by") or "?", c.get("tempo_bpm"))
    else:                               # no bed yet: the bed the edit stage makes from the swipe's sound sheet
        mus = (load(Path(R) / "sound-sheet.json", {}) or {}).get("music") or {}
        me = mus.get("measured") or {}
        bpm = float(me.get("tempo_bpm") or 0) or None
        end = max((b for _, b in wins.values()), default=0.0)
        beats = [round(i * 60.0 / bpm, 3) for i in range(int(end * bpm / 60.0) + 1)] if bpm else []
        changes = []
        if ours:
            for x in me.get("changes") or (mus.get("heard") or {}).get("changes") or []:
                t = ours(float(x["at"]))
                if t is not None:
                    changes.append({"at": t, "what": "music " + str(x.get("what"))})
        src = ("a %s BPM grid from 0 s, the swipe's measured tempo (sound-sheet.json): the bed is made from it and is "
               "not made yet, so its beats are an estimate" % me.get("tempo_bpm"))
    downs = beats[::4]
    return {"beats": beats, "downbeats": downs, "changes": changes, "from": src,
            "bar_phase": "every 4th beat from the first one (the bar's phase is not measured)"}


def scene_events(ev, a, b, spoken):
    beats = [t for t in ev["beats"] if a <= t < b]
    tags = {"downbeat"} if any(a <= t < b for t in ev["downbeats"]) else set()
    if beats:
        tags.add("kick")
    ch = [c for c in ev["changes"] if a - 0.05 <= c["at"] < b]
    for c in ch:
        w = c["what"].lower()
        if "drop" in w or "break" in w:
            tags.update({"break"})
        if "hit" in w or "return" in w:
            tags.add("drop")
    if spoken:
        tags.add("vocal word")
    return sorted(tags), beats, ch


# ---------------------------------------------------------------- timing a move
def is_hit(change):
    """A change a move can land on: a hit, a return, a chorus. A drop-out or a break is space, not a hit."""
    w = change.get("what") or ""
    return bool(re.search(r"hit|return|chorus|drop\b", w, re.I)) and not re.search(r"drops out|break", w, re.I)


def moment(opt, move_id, sc, nxt):
    """When an option's move lands: the director's own `fires_at` when it sits within TOL of a named event clear of
    the scene's cuts (a hit, a downbeat, a beat), else the move's own first moment (fire)."""
    f = fire(move_id, sc, nxt)
    if not f or f["where"] != "in-scene":
        return f
    try:
        t = float(opt.get("fires_at"))
    except (TypeError, ValueError):
        return f
    lo, hi = sc["start"] + EDGE, sc["end"] - EDGE
    named = [(c["at"], re.sub(r"^(the )?", "the ", c["what"].strip(), count=1), "change") for c in sc["changes"] if is_hit(c)]
    named += [(d, "the downbeat at %.2f s" % d, "downbeat") for d in sc["downbeats"]]
    named += [(x, "the beat at %.2f s" % x, "beat") for x in sc["beats"]]
    near = [n for n in named if lo <= n[0] <= hi and abs(n[0] - t) <= TOL]
    if not near:
        return dict(f, note="the director's %.2f s sits on no beat clear of the cuts" % t)
    at, ev, kind = min(near, key=lambda n: (abs(n[0] - t), ["change", "downbeat", "beat"].index(n[2])))
    return {"at": at, "where": "in-scene", "event": ev, "kind": kind, "note": "the director's moment"}


def fire(move_id, sc, nxt):
    """When the move lands: {"at", "event", "where", "off_beat"} or None when it cannot land in this scene."""
    lay = LAY.get(move_id) or {}
    where = lay.get("where") or ("hand-off" if (library().get(move_id) or {}).get("family") == "transition" else "in-scene")
    a, b = sc["start"], sc["end"]
    if where == "hand-off":
        if not nxt:
            return None
        near = min(sc["all_beats"], key=lambda t: abs(t - b), default=None)
        off = round(b - near, 3) if near is not None else None
        on = off is not None and abs(off) <= TOL
        return {"at": round(b, 3), "where": "hand-off", "event": ("the hand-off, on the beat at %.2f s" % near) if on
                else "the hand-off (%s)" % ("%.2f s from the nearest beat" % abs(off) if off is not None else "no beat"),
                "on_beat": bool(on)}
    lo, hi = a + EDGE, b - EDGE
    for c in sorted(sc["changes"], key=lambda c: c["at"]):
        if is_hit(c) and lo <= c["at"] <= hi:
            return {"at": c["at"], "where": "in-scene", "event": re.sub(r"^(the )?", "the ", c["what"].strip(), count=1),
                    "kind": "change"}
    for t in sc["downbeats"]:
        if lo <= t <= hi:
            return {"at": t, "where": "in-scene", "event": "the downbeat at %.2f s" % t, "kind": "downbeat"}
    for t in sc["beats"]:
        if lo <= t <= hi:
            return {"at": t, "where": "in-scene", "event": "the beat at %.2f s" % t, "kind": "beat"}
    return None


# ---------------------------------------------------------------- the pitches
def rules_pitches(sc, nxt, lib, target=None, laid=None):
    """Three options when no director model is reachable: Safe = the move the edit lays today that scores best by
    THE PICK RULE, Bold = the shortlist's best move a viewer notices, Wild = its best wow-3 move. Same fields as the
    director's JSON."""
    cands = [c for c in sc["candidates"]]
    layable = []
    for i in LAY:
        s_, ok_, _, _ = judge({"moves": [i], "cost": "free"}, sc, nxt, target or {}, lib, laid or {})
        if ok_:
            layable.append((s_, i))
    layable = [{"id": i} for _, i in sorted(layable, key=lambda x: (-x[0], x[1]))]
    used, out = set(), []
    for name, ok in (("Safe", lambda m: m["wow"] <= 2), ("Bold", lambda m: m["wow"] >= 2), ("Wild", lambda m: m["wow"] >= 3)):
        pool = layable + cands          # what the edit lays first (best score first), then the shortlist
        c = next((c for c in pool if c["id"] not in used and ok(lib[c["id"]])), None) or \
            next((c for c in pool if c["id"] not in used), None)
        if not c:
            continue
        used.add(c["id"])
        f = fire(c["id"], sc, nxt) or {}
        m = lib[c["id"]]
        out.append({"option": name, "name": m["name"], "moves": [c["id"]], "fires_at": f.get("at"),
                    "event": f.get("event", "no moment in this scene"), "where": f.get("where", ""),
                    "you_see": m["what_you_see"], "cost": "paid" if "credit" in m["cost"] else "free",
                    "production_note": "", "by": "rules (shortlist order)"})
    return out


def fill_prompt(sc, prev, nxt, facts, lib):
    tpl = PROMPT.read_text().split("\n---\n")[1]
    cands = "\n".join("- `%s` %s — %s Reference: %s. Trigger: %s. Built: %s. Cost: %s. Cheap when: %s" % (
        c["id"], lib[c["id"]]["name"], lib[c["id"]]["what_you_see"], lib[c["id"]]["reference"],
        lib[c["id"]]["music_trigger"], lib[c["id"]]["build"], lib[c["id"]]["cost"], lib[c["id"]]["risk"])
        for c in sc["candidates"])
    near = lambda x, end: ("%s: %s" % (x["scene"], x["title"]) + (" — " + (x["shots"][-1 if end else 0]["what"] if x["shots"] else ""))) if x else "nothing (the ad starts/ends here)"  # noqa: E731
    val = {
        "project_title": facts["title"], "length_seconds": round(facts["length"], 1),
        "scene": sc["scene"], "start": "%.2f" % sc["start"], "end": "%.2f" % sc["end"], "clock_note": facts["clock"],
        "scene_title": sc["title"], "word": sc["word"] or "(no words)",
        "shots": "; ".join("%s: %s" % (s["id"], s["what"]) for s in sc["shots"]) or "(none written)",
        "kinds": ", ".join(sc["kinds"]), "previous_scene": near(prev, True), "next_scene": near(nxt, False),
        "event_tags": ", ".join(sc["tags"]) or "none",
        "beats": ", ".join("%.2f" % t for t in sc["beats"]) or "none in this scene",
        "changes": "; ".join("%.2f s %s" % (c["at"], c["what"]) for c in sc["changes"]) or "none",
        "controls": "\n".join("- %s: %s" % (k, v) for k, v in facts["target"].items()),
        "objects_in_scene": ", ".join(sc["objects"]) or "none named",
        "candidates_with_index_entries": cands,
        "layable": "\n".join("- `%s`: %s" % (k, v["how"]) for k, v in LAY.items()),
        "project_rules": facts["rules"],
    }
    for k, v in val.items():
        tpl = tpl.replace("{%s}" % k, str(v))
    return tpl


def claude_pitches(prompt, ask=None, model="sonnet"):
    """The director, run through the chain's one Claude door (run-kit claude_door). Returns (options, the answer)."""
    if ask is None:
        sys.path.insert(0, str(MOVES.parents[1] / "run-kit"))
        from run_kit import claude_door
        ask = lambda p: claude_door.ask(p, model=model)  # noqa: E731
    text = ask(prompt)
    blocks = re.findall(r"```json\s*(\[.*?\])\s*```", text, re.S)
    opts = json.loads(blocks[-1]) if blocks else []
    for o in opts:
        o["by"] = "the creative director (%s)" % PROMPT.name
    return opts, text


# ---------------------------------------------------------------- the machine pick
def boldness(target):
    vals = [float(target[k]) for k in BOLD_DIALS if k in target]
    return round(sum(vals) / len(vals) / 4.0, 3) if vals else 0.75


def judge(opt, sc, nxt, target, lib, used):
    """(score, eligible, why, gaps) for one option, by THE PICK RULE in the module notes."""
    why, gaps = [], []
    ids = [i for i in opt.get("moves") or [] if i]
    if not ids:
        return -99, False, ["names no move"], []
    for i in ids:
        if i not in lib:
            gaps.append({"move": i, "gap": "a new move, not in the index: add it to the library before the edit can lay it"})
        elif i in OUT:
            gaps.append({"move": i, "gap": OUT[i]})
        elif "credit" in lib[i]["cost"]:
            gaps.append({"move": i, "gap": "needs paid generation (%s): not made" % lib[i]["cost"]})
        elif i not in LAY:
            gaps.append({"move": i, "gap": "free on the Mac, but the edit has no drawer for it yet (%s)" % lib[i]["build"]})
    if opt.get("where") == "shot-change":
        gaps.append({"move": "+".join(ids), "gap": "lands inside the scene's clip, in production: %s" %
                     (opt.get("production_note") or "the shot must be framed for it")})
    moments = []
    for i in ids:
        need = {"match-cut-shape": "shape", "match-cut-motion": "motion"}.get(i)
        if need and opt.get("where") != "shot-change" and (sc["pair"][0] != need or not nxt):
            gaps.append({"move": i, "gap": "the shots either side of the hand-off share no %s (read from the shot words)"
                         % need})
        if (LAY.get(i) or {}).get("punch") and sc.get("roll") in WORDS_ROLLS:
            gaps.append({"move": i, "gap": "the scene's picture carries its own words (%s): a punch-in would crop them"
                         % WORDS_ROLLS[sc["roll"]]})
        f_ = moment(opt, i, sc, nxt) if i in lib else None
        if i in lib and not f_:
            gaps.append({"move": i, "gap": "no moment for it in this scene (no scene after it, or no beat clear of the cuts)"})
        moments.append(f_)
    if gaps:
        return -99, False, ["not laid: " + "; ".join(g["gap"] for g in gaps)], gaps
    if len({(f_["where"], f_["at"]) for f_ in moments}) < len(moments):
        return -99, False, ["not laid: two of its moves land on the same moment"], [
            {"move": "+".join(ids), "gap": "two of its moves land on the same moment"}]
    f, m = moments[0], lib[ids[0]]
    pts = 0.0
    if f["where"] == "hand-off":
        pts += 3 if f.get("on_beat") else 1
        why.append(f["event"])
    else:
        pts += 4 if f.get("kind") in ("change", "downbeat") else 3
        why.append("fires on " + f["event"] + (" (%s)" % f["note"] if f.get("note") else ""))
    kind, what = sc["pair"] if nxt else (None, "")
    if "match-cut-shape" in ids and kind == "shape":
        pts += 3
        why.append("the two sides share a shape (%s)" % what)
    elif "match-cut-motion" in ids and kind == "motion":
        pts += 2
        why.append("the same motion carries across (%s)" % what)
    if len(ids) > 1:
        why.append("laid together: " + " + ".join(ids))
    bo = boldness(target)
    pts += m["wow"] * bo
    why.append("wow %d x the target's boldness %.2f" % (m["wow"], bo))
    if m["family"] in ("frame-break", "time") and int(target.get("realism", 0)) >= 4:
        pts -= 1.5
        why.append("the target's realism %s keeps the frame whole (-1.5)" % target.get("realism"))
    if used.get(ids[0]):
        pts -= used[ids[0]]
        why.append("already laid in %d earlier scene(s) (-%d)" % (used[ids[0]], used[ids[0]]))
    return round(pts, 2), True, why, []


def pick(sc, nxt, pitches, target, lib, used):
    order = {"Safe": 0, "Bold": 1, "Wild": 2}
    judged = []
    for o in pitches:
        s, ok, why, gaps = judge(o, sc, nxt, target, lib, used)
        o.update({"score": s, "eligible": ok, "why": why, "gaps": gaps})
        judged.append(o)
    ok = [o for o in judged if o["eligible"]]
    src = "the director's %s"
    if not ok:                          # every pitch is a gap: the best move on the shortlist the edit can lay
        extra = []
        for c in sc["candidates"] + [{"id": i} for i in LAY]:
            o = {"option": "Shortlist", "name": lib[c["id"]]["name"], "moves": [c["id"]], "cost": "free"}
            s, e, why, _ = judge(o, sc, nxt, target, lib, used)
            if e and not any(x["moves"] == o["moves"] for x in extra):
                o.update({"score": s, "eligible": True, "why": why, "gaps": []})
                extra.append(o)
        ok = extra
        src = "the best move the edit lays from the shortlist%.0s (no pitch could be laid today)"
    if not ok:
        return None
    if max(o["score"] for o in ok) < FLOOR:          # owner: clean cuts; a move earns its place or the cut stays clean
        b_ = max(ok, key=lambda o: o["score"])
        return {"from": "the clean cut", "option": None, "name": "no move: the clean cut stays", "moves": [],
                "score": b_["score"], "reason": "the best layable move (%s, %s) scored %.1f, under the floor %.1f: %s"
                % (b_["moves"][0], b_["option"], b_["score"], FLOOR, "; ".join(b_["why"])), "how": "", "edit": None,
                "edits": [],
                "production_note": ""}
    best = max(ok, key=lambda o: (o["score"], lib[o["moves"][0]]["wow"], -order.get(o["option"], 3)))
    mid = best["moves"][0]
    edits = []
    for i in best["moves"]:
        f = moment(best, i, sc, nxt)
        lay = dict(LAY[i])
        lay.pop("how", None)
        e = {"scene": sc["scene"], "move": i, "at": f["at"], "at_in_scene": round(f["at"] - sc["start"], 3),
             "where": f["where"], "event": f["event"]}
        e.update(lay)
        if f["where"] == "hand-off":
            e["after_scene"] = sc["scene"]
            e["into_scene"] = nxt["scene"]
        edits.append(e)
    edit = edits[0]
    return {"from": src % best["option"], "option": best["option"], "name": best.get("name") or lib[mid]["name"],
            "moves": best["moves"], "edits": edits,
            "score": best["score"], "reason": "; ".join(best["why"]), "how": " / ".join(LAY[i]["how"] for i in best["moves"]),
            "edit": edit,
            "production_note": best.get("production_note") or ""}


# ---------------------------------------------------------------- the production
def target_of(brief):
    """The brief's creative-controls target for video: the preset the writing aims for (maxed unless the brief names
    one in creative_controls.preset), the brand's saved levels, the never-sterile floor."""
    sys.path.insert(0, str(MOVES.parents[1] / "creative-controls"))
    import creative_controls as CC
    preset = (brief.get("creative_controls") or {}).get("preset") or "maxed"
    brand = brief.get("brand") or (brief.get("shot_fill") or {}).get("brand")
    pr, levels = CC.target(preset, brand, "video")
    return preset, levels


def facts(B, R, beats_fn=None):
    B = Path(B)
    brief = load(B / "brief.json", {}) or {}
    rows = (load(B / "shot-list.json", {}) or {}).get("shots") or []
    wins, clock, length = windows(B, brief, rows)
    ev = music_events(B, R, wins, clock.startswith("the rendered"), beats_fn, swipe_clock(R, rows, wins))
    preset, target = target_of(brief)
    lib_ = library()
    index = [lib_[k] for k in lib_]
    scenes, seen = [], {}
    for s in brief.get("order") or []:
        if s not in wins:
            continue
        wf, prod = _take(B, s, brief)
        shots = shots_of(s, prod, rows)
        a, b = wins[s]
        word = (wf.get("words") or " ".join(x.get("say") or "" for x in prod.get("script") or [])).strip()
        tags, beats, ch = scene_events(ev, a, b, bool(word))
        lane = wf.get("lane") or brief.get("lane") or "ai"
        kinds = {"ai": ["ai"], "real": ["real"], "mix": ["mix"]}.get(lane, ["mix"])
        objs = sorted({p for x in shots for p in x["props"]} | {w for x in shots for w in shape_of(x["what"]).values()})
        text = [{"what": x["what"]} for x in shots]
        sc = {"scene": s, "title": wf.get("title") or s, "roll": wf.get("roll") or "", "start": a, "end": b,
              "word": word, "kinds": kinds,
              "shots": shots, "objects": objs, "tags": tags, "beats": beats, "changes": ch,
              "downbeats": [t for t in ev["downbeats"] if a <= t < b], "all_beats": ev["beats"]}
        fit = [m for m in index if m["objects"] in ([], ["*"]) or set(m["objects"]) & set(objs)]
        sc["candidates"] = SG.shortlist(fit, set(kinds), objs, set(tags), text, seen)
        scenes.append(sc)
    for i, sc in enumerate(scenes):
        nxt = scenes[i + 1] if i + 1 < len(scenes) else None
        sc["pair"] = pair(sc["shots"][-1]["what"] if sc["shots"] else "",
                          nxt["shots"][0]["what"] if nxt and nxt["shots"] else "") if nxt else (None, "")
        if sc["pair"][0] and not any(c["id"] == "match-cut-%s" % sc["pair"][0] for c in sc["candidates"]):
            m = lib_["match-cut-%s" % sc["pair"][0]]      # a matched pair at the hand-off puts its match cut on the list
            sc["candidates"].append({"id": m["id"], "name": m["name"], "family": m["family"], "score": None,
                                     "why": ["the hand-off pairs a %s (%s)" % (sc["pair"][0], sc["pair"][1])],
                                     "wow": m["wow"], "cost": m["cost"], "what_you_see": m["what_you_see"]})
    rules = ("Clean cuts, no flash frames, no repeated clip, no dead air, every cut placed on purpose; shot timing is "
             "never graded; the swipe's edit moves are suggestions only (owner, 16-17 Nov). The cast comes from the "
             "production's cast sheets.")
    return {"title": brief.get("title") or B.name, "length": length, "clock": clock, "music": ev["from"],
            "bar_phase": ev["bar_phase"], "preset": preset, "target": target, "rules": rules, "scenes": scenes}


def fingerprint(f, mode):
    keep = {k: f[k] for k in ("title", "clock", "target")}
    keep["scenes"] = [{k: sc[k] for k in ("scene", "start", "end", "word", "beats", "changes", "pair")} for sc in f["scenes"]]
    keep["shots"] = [[x["what"] for x in sc["shots"]] for sc in f["scenes"]]
    keep.update(code=hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:12], rule=RULE, prompt=PROMPT.name, library=LIBRARY.name, mode=mode, lay=sorted(LAY), out=sorted(OUT))
    return hashlib.sha1(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()[:16]


def direct(B, R, mode="rules", ask=None, force=False, beats_fn=None, say=lambda *a: None):
    """The whole pass for one production. Writes edit/moves-picks.json only when its facts changed (the same facts
    give the same file, so a render it triggers never triggers another). Returns the picks record."""
    B = Path(B)
    f = facts(B, R, beats_fn)
    fp = fingerprint(f, mode)
    out = B / "edit" / "moves-picks.json"
    old = load(out, {}) or {}
    if old.get("fingerprint") == fp and not force:
        return old
    lib = library()
    used, rows = {}, []
    for i, sc in enumerate(f["scenes"]):
        prev = f["scenes"][i - 1] if i else None
        nxt = f["scenes"][i + 1] if i + 1 < len(f["scenes"]) else None
        answer = None
        if mode == "claude":
            try:
                pitches, answer = claude_pitches(fill_prompt(sc, prev, nxt, f, lib), ask)
            except Exception as e:  # noqa: BLE001 — no door: the rules pitch, said in the record
                say("the director could not be reached (%s): the rules pitch this scene" % str(e)[:120])
                pitches = []
            if not pitches:
                pitches = rules_pitches(sc, nxt, lib, f["target"], used)
        else:
            pitches = rules_pitches(sc, nxt, lib, f["target"], used)
        p = pick(sc, nxt, pitches, f["target"], lib, used)
        if p and p["moves"]:
            used[p["moves"][0]] = used.get(p["moves"][0], 0) + 1
        gaps = [dict(g, option=o["option"]) for o in pitches for g in o.get("gaps") or []]
        rows.append({"scene": sc["scene"], "title": sc["title"], "start": sc["start"], "end": sc["end"],
                     "events": {"tags": sc["tags"], "beats": sc["beats"], "changes": sc["changes"]},
                     "hand_off_pair": {"kind": sc["pair"][0], "what": sc["pair"][1]},
                     "shortlist": [c["id"] for c in sc["candidates"]], "pitches": pitches, "pick": p, "gaps": gaps,
                     "director_answer": answer})
    rec = {"production": B.name, "fingerprint": fp, "pitch": mode, "rule": RULE, "prompt": PROMPT.name,
           "library": LIBRARY.name, "clock": f["clock"], "music": f["music"], "bar_phase": f["bar_phase"],
           "target": {"preset": f["preset"], "levels": f["target"], "boldness": boldness(f["target"])},
           "scenes": rows, "edits": [e for r in rows if r["pick"] for e in r["pick"]["edits"]]}
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    (out.with_suffix(".md")).write_text(markdown(rec))
    return rec


def markdown(rec):
    L = ["# Edit moves: %s" % rec["production"], "",
         "One move per scene, kept by the machine (%s). Clock: %s. Music: %s." % (rec["rule"], rec["clock"], rec["music"]),
         "Target: %s, boldness %.2f. Pitches: %s." % (rec["target"]["preset"], rec["target"]["boldness"], rec["pitch"]), ""]
    for r in rec["scenes"]:
        p = r["pick"]
        L.append("## %s · %s · %.2f–%.2f s" % (r["scene"], r["title"], r["start"], r["end"]))
        L.append("- **Laid:** " + ("`%s` %s at %.2f s (%s) — %s" % (p["moves"][0], p["name"], p["edit"]["at"],
                                                                      p["edit"]["event"], p["reason"]) if p and p["edit"]
                                   else ("nothing — " + p["reason"]) if p else "nothing"))
        for o in r["pitches"]:
            L.append("- %s: `%s` %s%s" % (o["option"], "+".join(o.get("moves") or []), o.get("name", ""),
                                         "" if o.get("eligible") else " — " + "; ".join(o.get("why") or [])))
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    run = a[a.index("--run") + 1] if "--run" in a else None
    mode = a[a.index("--pitch") + 1] if "--pitch" in a else "rules"
    B = Path(a[0])
    if run is None:
        brief = load(B / "brief.json", {}) or {}
        sys.path.insert(0, str(MOVES.parents[1] / "video-studio"))
        import settings as ST
        run = str(ST.WRITING / (brief.get("run") or brief.get("brief") or ""))
    rec = direct(B, run, mode, force="--force" in a, say=print)
    for r in rec["scenes"]:
        p = r["pick"]
        print("%-5s %6.2f-%6.2f  %s" % (r["scene"], r["start"], r["end"],
                                        ("%s at %.2f s · %s" % (p["moves"][0], p["edit"]["at"], p["edit"]["event"]))
                                        if p and p["edit"] else ("clean cut · " + p["reason"][:90]) if p else "no move"))
