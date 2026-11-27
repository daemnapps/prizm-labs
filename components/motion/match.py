#!/usr/bin/env python3
"""The motion-match check: a finished clip set against the reference it was meant to move like (stage 5 / page stage 9).

    python3 match.py <motion dir> <clip> [--name take] [--cuts 2.7,3.8]

<motion dir> holds the tracked reference and its motion read. The clip (a take, or the 3D rehearsal) is tracked the
same way and measured with the same measures (measure.py), then set beside the reference beat by beat:
  per beat   did the move the read says proves the beat happen (the same measure moving the same way, at least half as
             far as the real people moved), and was it on time (half done within 0.4 s, or a fifth of the beat)
  the clip   the camera (a push, pan or tilt the reference does not make), the handheld shake, how alive the bodies are
             (a clip smoother than half the reference's small movement reads as generated), and the people seen
Writes <motion dir>/match-<name>.json: rows of {"beat", "name", "ok", "short", "detail", "reference", "clip", "holds"},
`held_by` (the failed rows that hold the motion back: the move itself, the stand-in on its footage, its framing, a lead
nobody followed; the other fails are noted), and the clip's own track under <motion dir>/match-<name>/. Tracking is free and runs on this machine; nothing is paid for.
No brand, product or person is named here.
"""
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import measure as ME  # noqa: E402

FAR = 0.5              # the clip's move must be at least this share of the reference's
LATE = 0.4             # seconds a move may be early or late (or a fifth of the beat, whichever is more)
CAM = 0.06             # a push, pan or tilt this much beyond the reference's is the clip's own invention
UNITS = {"lean": "°", "head": "°", "knees": "°", "turn": "°", "hips": " torso", "hand_l": "", "hand_r": "", "near": " heads"}


def _rows_for(tr, letters):
    """The rows of one of our people across the shots: the tracks the read mapped them to."""
    out = []
    for letter in letters or []:
        try:
            out += tr[int(letter[1:]) - 1]["people"][letter[0].upper()]["rows"]
        except (ValueError, IndexError, KeyError):
            continue
    return sorted(out, key=lambda r: r["t"])


def _move(rows, measure, a, b, want_up):
    """How far the measure moved the wanted way inside the window, and when it was half done."""
    c = ME.change(rows, measure, a, b)
    if not c:
        return None
    # the biggest move in the wanted direction: change() gives the biggest either way, so read both ends
    s = ME.series(rows, measure, a, b)
    vs = ME.smooth([v for _, v in s])
    ts = [t for t, _ in s]
    best = (0.0, None)
    lo_i = 0
    for i in range(len(vs)):                         # largest rise (or fall) from an earlier point to a later one
        if (vs[i] < vs[lo_i]) if want_up else (vs[i] > vs[lo_i]):
            lo_i = i
        d = (vs[i] - vs[lo_i]) if want_up else (vs[lo_i] - vs[i])
        if d > best[0]:
            half = (vs[i] + vs[lo_i]) / 2
            at = next((ts[k] for k in range(lo_i, i + 1) if ((vs[k] >= half) if want_up else (vs[k] <= half))), ts[i])
            best = (d, at)
    return {"by": round(best[0], 2), "at": best[1]}


def _lag(ref_rows, clip_rows, measure, a, b, reach=1.5, step=1.0 / 16):
    """Seconds the clip's curve of a measure runs behind (+) or ahead (-) of the reference's inside a window: the shift
    that lays one on the other best. None when either hardly moves or they hardly overlap."""
    def sample(rows):
        s = ME.series(rows, measure, a - reach, b + reach)
        if len(s) < 4:
            return {}
        vs = ME.smooth([v for _, v in s])
        return {int(round(t / step)): v for (t, _), v in zip(s, vs)}
    R, K = sample(ref_rows), sample(clip_rows)
    keys = [k for k in R if a <= k * step <= b]
    if len(keys) < 6 or not K:
        return None
    rv = [R[k] for k in keys]
    if max(rv) - min(rv) < ME.FLOOR.get(measure, 0) * 0.5:
        return None
    best = None
    for sh in range(-int(reach / step), int(reach / step) + 1):
        pairs = [(R[k], K[k + sh]) for k in keys if k + sh in K]
        if len(pairs) < max(6, 0.6 * len(keys)):
            continue
        mr, mk = sum(p[0] for p in pairs) / len(pairs), sum(p[1] for p in pairs) / len(pairs)
        err = sum(((p[0] - mr) - (p[1] - mk)) ** 2 for p in pairs) / len(pairs) + 1e-4 * abs(sh)
        if best is None or err < best[0]:
            best = (err, sh)
    return round(best[1] * step, 2) if best else None


def on_the_footage(ours, theirs, aspect=0.5625):
    """A 3D rehearsal laid over the footage it was made from: per person, how far the stand-in's joints sit from the
    real person's in the picture (in that person's head heights), and how big the stand-in reads against them.
    [(name, off, size)] over the frames both are seen in."""
    out = []
    for nm, ref_rows in ours.items():
        clip = {r["f"]: r for r in theirs.get(nm) or []}
        offs, sizes = [], []
        for r in ref_rows:
            c = clip.get(r["f"])
            if not c or "pts" not in r or "pts" not in c:
                continue
            ds = [math.hypot((r["pts"][k][0] - c["pts"][k][0]) * aspect, r["pts"][k][1] - c["pts"][k][1]) for k in r["pts"] if k in c["pts"]]
            if ds:
                offs.append(sorted(ds)[len(ds) // 2] / r["head_size"])
            if r.get("span") and c.get("span"):
                sizes.append(c["span"] / r["span"])
        if len(offs) >= 3:
            out.append((nm, round(sorted(offs)[len(offs) // 2], 2), round(sorted(sizes)[len(sizes) // 2], 2) if sizes else None))
    return out


def _hidden_by(m, others, aspect):
    """The name of a nearer person (a bigger head) whose body covers this person's head in the frame, or None."""
    for n, o, p in others:
        if o["head_size"] < 1.4 * m["head_size"]:
            continue
        b = p.get("body33") or []
        pts = [b[i] for i in (11, 12, 23, 24) if i < len(b) and b[i] and (len(b[i]) < 3 or b[i][2] > 0.3)]
        if len(pts) < 4:
            continue
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        if min(xs) <= m["x"] <= max(xs) and min(ys) <= m["y"] <= max(ys):      # the head inside the nearer one's torso
            return n
    return None


def _pair(shown, pic, aspect):
    """Rehearsal people to the picture's people all at once, the best fit of place and size over every pairing (a
    greedy left-to-right pass gave a person standing just behind another that other's body)."""
    import itertools
    names = [n for n, _ in shown]
    reh = dict(shown)

    def cost(r, c):
        off = math.hypot((c["x"] - r["x"]) * aspect, c["y"] - r["y"]) / r["head_size"]
        # how big the body reads: its torso (shoulders to hips) when both show it whole, a stand-in's head being no
        # real head's size; else shoulders to head; else the head alone (a close-up)
        size = ((c["torso"] / r["torso"]) if (r.get("torso") and c.get("torso")) else
                (c["span"] / r["span"]) if (r.get("span") and c.get("span")) else (c["head_size"] / r["head_size"]))
        return off + 3.0 * abs(math.log(max(size, 1e-3)))
    best, best_cost = {}, None
    k = min(len(names), len(pic))
    if len(names) <= 8 and len(pic) <= 8:
        for who in itertools.combinations(names, k):
            for got in itertools.permutations(range(len(pic)), k):
                total = sum(cost(reh[n], pic[i]) for n, i in zip(who, got))
                if best_cost is None or total < best_cost:
                    best_cost, best = total, {n: pic[i] for n, i in zip(who, got)}
        return best
    left = list(pic)                                   # a crowd: the nearest by place, as before
    for n in names:
        if left:
            c = min(left, key=lambda m: cost(reh[n], m))
            left.remove(c)
            best[n] = c
    return best


def start_rows(rehearsal_people, picture_people, aspect=0.5625, hidden=None):
    """A start picture against the rehearsal's first frame: is everyone there, where the rehearsal has them, and as
    big in the frame. `rehearsal_people`: the rehearsal's first frame (named, exact joints); `picture_people`: the
    people read off the picture. People are paired left to right. Rows in the usual shape."""
    rows = []

    def add(name, ok, short, detail):
        rows.append({"beat": 0, "name": name, "ok": ok, "short": short, "detail": detail, "reference": None, "clip": None, "holds": True})

    def facts(p):
        m = ME.frame_measures(p, aspect)
        if "x" not in m:
            return None
        b = p.get("body33") or []
        seen = lambda i: i < len(b) and b[i] and (len(b[i]) < 3 or b[i][2] > 0.5) and -0.05 <= b[i][1] <= 1.05
        if all(seen(i) for i in (11, 12, 23, 24)):
            sh = ((b[11][0] + b[12][0]) / 2, (b[11][1] + b[12][1]) / 2)
            hp = ((b[23][0] + b[24][0]) / 2, (b[23][1] + b[24][1]) / 2)
            m = dict(m, torso=math.hypot((sh[0] - hp[0]) * aspect, sh[1] - hp[1]))
        return m
    reh = [(p.get("name") or str(p.get("id")), facts(p), p) for p in rehearsal_people]
    reh = sorted([(n, m, p) for n, m, p in reh if m], key=lambda v: v[1]["x"])
    pic = sorted([m for m in (facts(p) for p in picture_people) if m], key=lambda m: m["x"])
    # a person the rehearsal itself hides (their head inside a nearer person's body) is not looked for in the picture
    if hidden is None:                                 # no word from the rehearsal's own render: read off the joints
        hidden = {n: by for n, m, p in reh for by in [_hidden_by(m, [(n2, m2, p2) for n2, m2, p2 in reh if n2 != n], aspect)] if by}
    shown = [(n, m) for n, m, p in reh if n not in hidden]
    add("start picture · people", len(pic) == len(shown), "%d, rehearsal %d" % (len(pic), len(shown)) + (
        " (+%d hidden in it)" % len(hidden) if hidden else ""),
        "The rehearsal's first frame shows %d people%s; the picture shows %d." % (
            len(shown), (" (%s hidden behind %s there)" % (", ".join(hidden), ", ".join(sorted(set(hidden.values()))))) if hidden else "", len(pic)))
    for n, by in hidden.items():
        add("start picture · " + n, None, "hidden behind %s, as in the rehearsal" % by,
            "%s stands behind %s in the rehearsal's first frame, so the picture does not show them either." % (n, by))
    pairs = _pair(shown, pic, aspect)
    for name, r in shown:
        c = pairs.get(name)
        if c is None:
            add("start picture · " + name, False, "not in the picture", "%s is in the rehearsal's first frame and nobody in the picture stands there." % name)
            continue
        off = math.hypot((c["x"] - r["x"]) * aspect, c["y"] - r["y"]) / r["head_size"]
        add("start picture · %s placed" % name, off <= 1.5, "%.1f heads off" % off,
            "%s's head in the picture sits %.1f head heights from where the rehearsal's first frame has it. Within one and a half passes." % (name, off))
        # how big the person reads: shoulders to head where both show them whole, else the head alone (a close-up
        # cuts the shoulders off, and a close-up drawn full-length is exactly the fault to catch)
        # how big the body reads: its torso (shoulders to hips) when both show it whole, a stand-in's head being no
        # real head's size; else shoulders to head; else the head alone (a close-up)
        size = ((c["torso"] / r["torso"]) if (r.get("torso") and c.get("torso")) else
                (c["span"] / r["span"]) if (r.get("span") and c.get("span")) else (c["head_size"] / r["head_size"]))
        ok = 0.75 <= size <= 1.33
        add("start picture · %s framing" % name, ok, "as the rehearsal" if ok else "%d%% of the rehearsal's size" % round(size * 100),
            "%s reads %d%% as big in the picture as in the rehearsal's first frame. Between 75%% and 133%% passes; outside it the picture was framed wider or tighter than the motion it must start." % (name, round(size * 100)))
    return rows


def pair_people(read, ref_tr, clip_tr, scale):
    """Which of the clip's tracked people is which of ours: through each shot of the reference, the clip's person
    standing in the same part of the frame at the same moment (mirrored when that fits better: a take may be staged
    the other way round)."""
    ours = {}
    for P in read.get("people") or []:
        ours[P["ours"]] = _rows_for(ref_tr, P.get("reference"))

    def where(rows, a, b):
        pts = [(r["x"], r["y"]) for r in rows if "x" in r and a <= r["t"] <= b]
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if len(pts) >= 3 else None
    got = {n: [] for n in ours}
    for S in ref_tr:
        a, b = S["from"], S["to"]                                      # the reference's shot, and the same seconds of the clip
        ca, cb = a / scale, b / scale
        refs = {n: where(rows, a, b) for n, rows in ours.items()}
        refs = {n: p for n, p in refs.items() if p}
        clips = {}
        for C in clip_tr:
            for k, P in C["people"].items():
                p = where(P["rows"], ca, cb)
                if p:
                    clips[(C["shot"], k)] = (p, P["rows"])
        best = None
        for flip in (False, True):
            left, pairs, cost = dict(clips), [], 0.0
            for n, p in sorted(refs.items(), key=lambda kv: kv[1][0], reverse=flip):
                if not left:
                    break
                px = 1 - p[0] if flip else p[0]
                k = min(left, key=lambda q: abs(left[q][0][0] - px) + 0.5 * abs(left[q][0][1] - p[1]))
                cost += abs(left[k][0][0] - px) + 0.5 * abs(left[k][0][1] - p[1])
                pairs.append((n, k))
                left.pop(k)
            cost += 0.5 * (len(refs) - len(pairs))
            if best is None or cost < best[0]:
                best = (cost, pairs)
        for n, k in (best[1] if best else []):
            got[n] += [r for r in clips[k][1] if ca - 1e-6 <= r["t"] <= cb + 1e-6]
    return ours, {n: sorted(r, key=lambda x: x["t"]) for n, r in got.items()}


def compare(motion_dir, clip_dir, name="take", clip_cuts=None):
    """The rows. `clip_dir` holds the clip's own track (pose.json, camera.json)."""
    d = Path(motion_dir)
    read = ME.read_of(d)
    ref = json.loads((d / "ref.json").read_text()) if (d / "ref.json").exists() else {}
    _, ref_tr, ref_cam = ME.load(d, ref.get("cuts"))
    pose, clip_tr, clip_cam = ME.load(clip_dir, clip_cuts, keep=0.08)     # a take is one long shot: a person seen for a tenth of it still counts
    ref_secs = float(read.get("seconds") or ref_tr[-1]["to"])
    clip_secs = clip_tr[-1]["to"] if clip_tr else 0.0
    scale = ref_secs / clip_secs if clip_secs else 1.0                  # clip seconds -> reference seconds
    if pose.get("exact") and any(p.get("name") for f in pose["frames"] for p in f["people"]):
        # a 3D rehearsal: its people are named and its joints exact, so nobody has to be found or paired
        ours = {P["ours"]: _rows_for(ref_tr, P.get("reference")) for P in read.get("people") or []}
        theirs = ME.named(pose, clip_cuts)
    else:
        ours, theirs = pair_people(read, ref_tr, clip_tr, scale)
    for nm in theirs:                                                  # the clip measured on the reference's clock
        theirs[nm] = [dict(r, t=round(r["t"] * scale, 3)) for r in theirs[nm]]
    rows = []

    def add(beat, nm, ok, short, detail="", r=None, c=None, holds=False):
        # holds: a fail on this row holds the motion back (the move itself, the stand-in on the footage, its framing, a lead
        # nobody followed); the rest are noted (timing read off a different body, a still bystander, the camera's small print)
        rows.append({"beat": beat, "name": nm, "ok": ok, "short": short, "detail": detail, "reference": r, "clip": c, "holds": holds})
    for k, b in enumerate(read.get("beats") or [], 1):
        c = b.get("check")
        label = "%d · %s" % (k, (b.get("what") or "")[:70])
        if not c:
            add(k, label, None, "no measure", "The read named no measure for this beat.")
            continue
        up = c.get("moves") != "down"
        mid = (b["from"] + b["to"]) / 2                            # inside the reference's own shot: a jump across a cut is not a move
        S = next((S for S in ref_tr if S["from"] <= mid < S["to"]), None)
        a0, b0 = max(b["from"] - 0.3, S["from"] if S else 0.0), min(b["to"] + 0.3, (S["to"] - 0.01) if S else b["to"] + 0.3)
        rm = _move(ours.get(c["who"]) or [], c["measure"], a0, b0, up)
        cm = _move(theirs.get(c["who"]) or [], c["measure"], a0 - (0.0 if pose.get("exact") else 0.3), b0 + (0.0 if pose.get("exact") else 0.3), up)
        unit = UNITS.get(c["measure"], "")
        word = ME.WORDS[c["measure"]][0 if up else 1]
        want = rm["by"] if rm and rm["by"] >= ME.FLOOR[c["measure"]] * 0.5 else float(c.get("by") or 0)
        want_at = rm["at"] if rm and rm["at"] is not None and rm["by"] >= ME.FLOOR[c["measure"]] * 0.5 else c.get("half_done_at")
        if cm is None:
            add(k, label, False, "%s can't be followed" % c["who"],
                "%s %s: the reference moves %s%s. In this clip %s's body is not in the frame long enough to follow through this beat (cropped too tight, or not there)." % (c["who"], word, want, unit, c["who"]),
                {"by": want, "at": want_at}, None, holds=True)
            continue
        happened = want > 0 and cm["by"] >= FAR * want
        add(k, label, bool(happened), "%s %s%s of %s%s" % (word, cm["by"], unit, round(want, 1), unit),
            "%s %s. Real people: %s%s. This clip: %s%s (needs at least half)." % (c["who"], word, round(want, 1), unit, cm["by"], unit),
            {"by": want, "at": want_at}, cm, holds=True)
        if happened and want_at is not None and cm["at"] is not None:
            slack = max(LATE, 0.2 * (b["to"] - b["from"]))
            # how far the clip's whole curve of that measure sits from the reference's (steadier than one half-way point)
            lag = _lag(ours.get(c["who"]) or [], theirs.get(c["who"]) or [], c["measure"], a0, b0)
            off = lag if lag is not None else cm["at"] - float(want_at)
            add(k, label + " · timing", abs(off) <= slack, ("on time" if abs(off) <= slack else "%.1f s %s" % (abs(off), "late" if off > 0 else "early")),
                "Half done at %.2f s in the reference, %.2f s in this clip (allowed ±%.1f s)." % (float(want_at), cm["at"], slack),
                {"at": want_at}, {"at": cm["at"]})
    # the camera: what the clip's camera does beyond the reference's, over the whole clip
    def total(cams, key):
        return max((abs(c[key]) for c in cams), default=0.0)
    if pose.get("exact"):
        # the rehearsal laid over the footage: the stand-in sits on the real person, and reads the same size
        for nm, off, size in on_the_footage(ours, theirs, pose["width"] / float(pose["height"]) if pose.get("height") else 0.5625):
            add(0, "on the footage · " + nm, off <= 1.0, "%.1f heads off" % off,
                "%s's stand-in sits %.1f head heights from the real person's joints in the picture (shoulders, hips, head, hands), over the frames both are seen. Within one head passes." % (nm, off), None, off, holds=True)
            if size is not None:
                add(0, "framing · " + nm, 0.75 <= size <= 1.33, ("as the footage" if 0.75 <= size <= 1.33 else "%d%% of the real size" % round(size * 100)),
                    "%s's stand-in reads %d%% as big in the frame as the real person (shoulders to head). Between 75%% and 133%% passes; outside it the rehearsal is framed wider or tighter than the footage." % (nm, round(size * 100)), 1.0, size, holds=True)
    ez = [c for c in clip_cam if c.get("edit_zoom")]
    if ez and not any(c.get("edit_zoom") for c in ref_cam):
        add(0, "camera · slow zoom", False, "zooms %.0f%%" % (100 * max(abs(c["edit_zoom"]) for c in ez)),
            "This clip zooms slowly about its centre with no drift or shake; the reference does not. A zoom belongs to the edit.")
    for key, word in (("push", "pushes in or out"), ("pan", "pans"), ("tilt", "tilts")):
        r, c = total(ref_cam, key), total(clip_cam, key)
        ok = c <= r + CAM
        add(0, "camera · " + word.split()[0], ok, ("as the reference" if ok else "%s %.0f%%, reference %.0f%%" % (word.split()[0], c * 100, r * 100)),
            "The reference's camera %s at most %.0f%% of the frame inside a shot; this clip's %.0f%%. A move the reference does not make was invented." % (word, r * 100, c * 100),
            round(r, 3), round(c, 3))
    punched = [p for c in clip_cam for p in c["punch"]]
    add(0, "camera · sudden zoom", not punched, "none" if not punched else "%d sudden zoom%s" % (len(punched), "s" if len(punched) > 1 else ""),
        "A zoom that snaps in belongs to the edit, never to a take." + ("".join(" At %.1f s: %+.0f%%." % (p["t"], p["push"]) for p in punched)),
        None, punched)
    rs, cs = max((c["shake"] for c in ref_cam), default=0), max((c["shake"] for c in clip_cam), default=0)

    def cls(v):
        return 2 if v > 0.01 else 1 if v > 0.003 else 0
    add(0, "camera · handheld", abs(cls(rs) - cls(cs)) <= 1, ["locked off", "light shake", "strong shake"][cls(cs)],
        "Reference: %s. This clip: %s." % (["locked off", "light shake", "strong shake"][cls(rs)], ["locked off", "light shake", "strong shake"][cls(cs)]), rs, cs)
    rf = [ME.fidget(r) for r in ours.values() if r]
    cf = [ME.fidget(r) for r in theirs.values() if r]
    rf, cf = [x for x in rf if x is not None], [x for x in cf if x is not None]
    if rf and cf:
        r, c = sum(rf) / len(rf), sum(cf) / len(cf)
        add(0, "bodies · alive", c >= 0.5 * r, "%.0f%% of real" % (100 * c / r if r else 0),
            "Real people never hold still: small movement after smoothing. Reference %.3f, this clip %.3f head-heights (needs at least half)." % (r, c), round(r, 4), round(c, 4))
    # everyone the footage shows must have been followed: a person the tracker never boxed cannot be rehearsed, and a
    # rehearsal measured against its own track would hide it
    tags = read.get("tags") or {}
    leads = {}                                           # per shot, the people a beat names: who starts, who answers, whose move proves it
    for bt in read.get("beats") or []:
        mid = (bt["from"] + bt["to"]) / 2
        S = next((S for S in ref_tr if S["from"] <= mid < S["to"]), None)
        if S:
            leads.setdefault(str(S["shot"]), set()).update(x for x in (bt.get("starts"), bt.get("answers"), (bt.get("check") or {}).get("who")) if x and x != "none")
    # (a fault of the reference's track: it is held against the rehearsal built from that track, never against a take)
    for shot, names in (sorted((read.get("visible") or {}).items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0) if pose.get("exact") else []):
        got = {n for t, n in tags.items() if t[1:] == str(shot)}
        S = next((S for S in ref_tr if str(S["shot"]) == str(shot)), None)
        if S is not None and not S.get("people"):
            # an insert: the tracker found no body anywhere in the shot (a face close-up, hands, the product), so there is
            # nothing to follow; the take carries it from the read's words. Noted, never a fail (12 Nov 2026)
            for nm in names:
                if nm not in got:
                    add(0, "reference · %s in shot %s" % (nm, shot), None, "insert: no body in the shot",
                        "Shot %s of the real footage shows no full body to track (a close-up of a face, hands or the product); "
                        "%s's part in it rides in the take's words." % (shot, nm))
            continue
        for nm in names:
            if nm not in got:
                lead = nm in leads.get(str(shot), set())        # someone who moves in this shot, or a bystander standing still
                add(0, "reference · %s in shot %s" % (nm, shot), False, "not followed" if lead else "not followed (stands still)",
                    "%s's reference person is in shot %s of the real footage, but the tracker did not follow them, so their movement is not in the rehearsal.%s"
                    % (nm, shot, "" if lead else " They take no part in any beat of this shot, so the take's first frame places them."), holds=lead)
    # both counted the same way: our people on screen at the same moment (one person split over two track ids is one)
    at = {}
    for nm, rws in ours.items():
        for r in rws:
            at.setdefault(r["f"], set()).add(nm)
    seen_ref = max((len(v) for v in at.values()), default=0)
    seen_clip = max((len(f["people"]) for f in pose["frames"]), default=0)       # the most in any one frame
    add(0, "people seen", seen_clip >= seen_ref, "%d, reference %d" % (seen_clip, seen_ref),
        "The most of our people on screen at the same moment: %d in the reference, %d in this clip." % (seen_ref, seen_clip), seen_ref, seen_clip)
    rec = {"clip": name, "reference_seconds": ref_secs, "clip_seconds": round(clip_secs, 2), "rows": rows,
           "held_by": ["%s: %s" % (r["name"], r["short"]) for r in rows if r["ok"] is False and r.get("holds")],
           "passed": sum(1 for r in rows if r["ok"] is True), "failed": sum(1 for r in rows if r["ok"] is False),
           "open": sum(1 for r in rows if r["ok"] is None), "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (d / ("match-%s.json" % name)).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


def match(motion_dir, clip, name="take", clip_cuts=None, exact_dir=None):
    """Track the clip (free, on this machine) and compare. `exact_dir`: a folder that already holds the clip's exact
    track (a 3D rehearsal writes its own), so nothing is read back from pictures."""
    import motion as MO
    d = Path(motion_dir)
    if exact_dir and not (Path(exact_dir) / "pose.json").exists():
        exact_dir = None
    cd = Path(exact_dir) if exact_dir else d / ("match-%s" % name)
    if not exact_dir:
        MO.track(clip, cd, kind="take")
    return compare(d, cd, name, clip_cuts)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    cuts = [float(x) for x in a[a.index("--cuts") + 1].split(",") if x] if "--cuts" in a else None
    rec = match(a[0], a[1], a[a.index("--name") + 1] if "--name" in a else "take", cuts)
    for r in rec["rows"]:
        print("%s  %-60s %s" % ({True: "PASS", False: "FAIL", None: " -- "}[r["ok"]], r["name"][:60], r["short"]))
    print("%d pass, %d fail" % (rec["passed"], rec["failed"]))
