#!/usr/bin/env python3
"""Measure: a tracked clip's skeletons turned into what the bodies are doing, in numbers a person can read.

    python3 measure.py <motion dir> [--cuts 2.67,3.83] [--step 0.25]      prints the table the motion read is given

The tracker (motion.py) writes pose.json: points per person per frame. This turns them into:
  shots     the clip split at its cuts (given, e.g. from a frame map; else the tracker's own)
  tracks    inside a shot, each person kept as one track (the tracker's broken ids joined, passers-by dropped), lettered
            A, B, C from the left of the frame
  series    per track, per frame: lean (degrees the upper body tips from upright, 3D), head (degrees the head drops below
            level: a duck is positive), knees (degrees of bend: a squat is large), hips (how far the hips have dropped,
            in body heights), hand_l / hand_r (hand height: 0 at the hip, 1 at the shoulder, 1.5 at the face), turn
            (degrees the shoulders face away from the lens), x / y (where the head is in the frame), near (distance from
            this head to the nearest other head, in head heights) and fidget (small movement left after smoothing: real
            people never hold still)
  camera    per shot: the operator's own pan, tilt, push and shake, with sudden punch-ins marked as edits (a zoom added in
            the edit is not a camera move, and is never asked of a take)

The same measures are read off a reference and off a finished take, so the two can be set side by side (match.py).
Plain Python: no MediaPipe needed. No brand, product or person is named here.
"""
import json
import math
import sys
from pathlib import Path

MEASURES = ("lean", "head", "knees", "hips", "hand_l", "hand_r", "turn", "x", "y", "near", "fidget")
# what a change in each measure is called, for a person reading a row
WORDS = {"lean": ("leans in", "straightens"), "head": ("ducks the head", "lifts the head"), "knees": ("bends the knees", "stands up"),
         "hips": ("drops down", "rises"), "hand_l": ("raises the left hand", "lowers the left hand"),
         "hand_r": ("raises the right hand", "lowers the right hand"), "turn": ("turns away", "turns to the lens"),
         "x": ("moves right", "moves left"), "y": ("moves down the frame", "moves up the frame"),
         "near": ("moves apart", "closes in")}
# how much change counts as something happening (below it the body is holding)
FLOOR = {"lean": 8.0, "head": 8.0, "knees": 25.0, "hips": 0.12, "hand_l": 0.35, "hand_r": 0.35, "turn": 25.0, "x": 0.08,
         "y": 0.08, "near": 0.6}
PUNCH = 0.06          # a push of 6% or more inside a quarter second is an edit punch-in, not an operator


def _mid(a, b):
    return [(a[i] + b[i]) / 2 for i in range(len(a))]


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _len(v):
    return math.sqrt(sum(x * x for x in v)) or 1e-6


def _angle(u, v):
    c = sum(a * b for a, b in zip(u, v)) / (_len(u) * _len(v))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def frame_measures(p, aspect=0.5625):
    """One person in one frame. World points: x right, y down, z away from the lens, metres around the hips.
    `aspect`: the frame's width over its height (points are fractions of each)."""
    out = {}
    b33, w = p.get("body33") or [], p.get("world") or []
    if len(b33) < 33:
        return out
    nose, neck2 = b33[0], _mid(b33[11][:2], b33[12][:2])
    out["x"], out["y"] = round(nose[0], 4), round(nose[1], 4)
    # the joints a rehearsal is laid over its footage by, where they are clearly seen, and the head-to-shoulders span
    out["pts"] = {str(k): [b33[k][0], b33[k][1]] for k in (0, 11, 12, 15, 16, 23, 24) if b33[k][2] > 0.5}
    if min(b33[0][2], b33[11][2], b33[12][2]) > 0.5:
        out["span"] = round(math.hypot((nose[0] - neck2[0]) * aspect, nose[1] - neck2[1]) + math.hypot((b33[11][0] - b33[12][0]) * aspect, b33[11][1] - b33[12][1]), 4)
    out["head_size"] = max(0.02, math.dist(b33[7][:2], b33[8][:2]) * 1.3, abs(neck2[1] - nose[1]) * 0.9)
    if len(w) >= 33:
        sh, hip = _mid(w[11], w[12]), _mid(w[23], w[24])
        spine = _sub(sh, hip)
        out["lean"] = round(_angle(spine, [0, -1, 0]), 1)
        ears = _mid(w[7], w[8])
        face = _sub(w[0], ears)                                       # ear line to nose: where the face points
        out["head"] = round(math.degrees(math.atan2(face[1], math.hypot(face[0], face[2]) or 1e-6)), 1)
        kn = []
        for h, k, a in ((23, 25, 27), (24, 26, 28)):
            # a knee is measured only when the whole leg is in the picture and read clearly (a leg the frame cuts off is a guess)
            if min(b33[h][2], b33[k][2], b33[a][2]) > 0.55 and max(b33[k][1], b33[a][1]) < 0.985:
                kn.append(180 - _angle(_sub(w[h], w[k]), _sub(w[a], w[k])))
        if kn:
            out["knees"] = round(sum(kn) / len(kn), 1)
        across = _sub(w[11], w[12])
        out["turn"] = round(math.degrees(math.atan2(abs(across[2]), abs(across[0]) or 1e-6)), 1)
        torso = _len(spine)
        for name, wr, s, h in (("hand_l", 15, 11, 23), ("hand_r", 16, 12, 24)):
            if b33[wr][2] > 0.4:
                out[name] = round((w[h][1] - w[wr][1]) / torso, 2)     # 0 at the hip, 1 at the shoulder
    if min(b33[23][2], b33[24][2]) > 0.4:
        out["hip_y"] = round((b33[23][1] + b33[24][1]) / 2, 4)
        out["body"] = max(0.05, abs(out["hip_y"] - neck2[1]))
    return out


def _size(p):
    """How big a person reads in the frame: shoulder line to nose, plus the shoulders' width (both survive a crop)."""
    b = p.get("body33") or []
    if len(b) < 13:
        return 1.0
    return max(0.01, math.dist(b[11][:2], b[12][:2]) + abs((b[11][1] + b[12][1]) / 2 - b[0][1]))


def shots(pose, cuts=None, camera=None):
    """[(from, to)] in seconds: the clip split at its cuts. A cut given from outside (a frame map) is moved onto the
    frame where the picture really changes, when the camera record shows one within a fifth of a second (a frame map
    is often a frame out); a sliver shorter than three frames (a stray frame of the next shot) is no shot."""
    fps = float(pose.get("fps") or 16)
    end = pose["frames"][-1]["t"] + 1.0 / fps if pose["frames"] else 0.0
    fr = (camera or {}).get("frames") or []
    jumps = [(f["t"], f.get("jump") or 0.0) for f in fr]
    base = sorted(j for _, j in jumps)[len(jumps) // 2] if jumps else 0.0
    out = []
    for c in (cuts if cuts is not None else (camera or {}).get("cuts") or []):
        near = [(j, t) for t, j in jumps if abs(t - c) <= 0.2]
        if near and max(near)[0] >= max(0.05, 3 * base):
            c = max(near)[1]
        out.append(round(c, 3))
    for t, j in jumps:                                   # a cut nobody named, where the whole picture changes at once
        if j >= max(0.12, 6 * base) and all(abs(t - c) > 0.15 for c in out):
            out.append(round(t, 3))
    cs = sorted(set(c for c in out if 0.05 < c < end - 0.05))
    edges = [0.0] + cs + [end]
    return [(round(a, 3), round(b, 3)) for a, b in zip(edges, edges[1:]) if b - a >= 2.5 / fps]


def tracks(pose, cuts=None, camera=None, keep=0.3):
    """Each shot's people as joined tracks: [{"shot": k, "from", "to", "people": {"A": {"ids": [...], "rows": [...]}}}].
    A row is frame_measures plus `t` (seconds from the clip's start) and `f` (the frame's index in pose.json)."""
    out = []
    for k, (a, b) in enumerate(shots(pose, cuts, camera), 1):
        frames = [(i, f) for i, f in enumerate(pose["frames"]) if a - 1e-6 <= f["t"] < b - 1e-6]
        raw = {}
        for i, f in frames:
            for p in f["people"]:
                raw.setdefault(p["id"], []).append((i, f["t"], p))
        # join broken ids: a track that starts where another ended (near in place, soon after) is the same person
        order = sorted(raw, key=lambda pid: raw[pid][0][1])
        joined = []
        for pid in order:
            first = raw[pid][0]
            best = None
            for j in joined:
                last = j["rows"][-1]
                gap = first[1] - last[1]
                d = math.dist(first[2]["body"][1][:2], last[2]["body"][1][:2])
                h0, h1 = _size(last[2]), _size(first[2])                # someone small behind is not the person in front
                if min(h0, h1) / max(h0, h1) < 0.6:
                    continue
                if 0 < gap < 1.5 and d < 0.10 + 0.08 * gap and (best is None or d < best[0]):
                    best = (d, j)
            if best:
                best[1]["ids"].append(pid)
                best[1]["rows"] += raw[pid]
            else:
                joined.append({"ids": [pid], "rows": list(raw[pid])})
        need = max(4, keep * len(frames))
        kept = [j for j in joined if len(j["rows"]) >= need]
        if not kept and joined:
            kept = [max(joined, key=lambda j: len(j["rows"]))]
        kept.sort(key=lambda j: sum(r[2]["body"][1][0] for r in j["rows"]) / len(j["rows"]))     # left to right
        people = {}
        for n, j in enumerate(kept):
            rows = []
            for i, t, p in j["rows"]:
                m = frame_measures(p, pose["width"] / float(pose["height"]) if pose.get("height") else 0.5625)
                m.update({"t": round(t, 3), "f": i})
                rows.append(m)
            people[chr(65 + n)] = {"ids": j["ids"], "rows": rows}
        _relative(people)
        out.append({"shot": k, "from": a, "to": b, "people": people})
    return out


def named(pose, cuts=None):
    """A 3D rehearsal's exact track: its people carry their names, so each is one track for the whole clip.
    {name: rows}, measured as any other track."""
    people = {}
    for i, f in enumerate(pose["frames"]):
        for p in f["people"]:
            m = frame_measures(p, pose["width"] / float(pose["height"]) if pose.get("height") else 0.5625)
            if not m:
                continue
            m.update({"t": f["t"], "f": i})
            people.setdefault(p.get("name") or str(p["id"]), {"ids": [p["id"]], "rows": []})["rows"].append(m)
    # hips dropped is read inside each shot (a cut puts the person somewhere else), the rest across the people
    for a, b in shots(pose, cuts):
        part = {n: {"rows": [r for r in P["rows"] if a - 1e-6 <= r["t"] < b - 1e-6]} for n, P in people.items()}
        _relative({n: P for n, P in part.items() if P["rows"]})
    return {n: P["rows"] for n, P in people.items()}


def _relative(people):
    """The measures that need the whole track or the other people: hips dropped, nearest head, fidget."""
    for name, P in people.items():
        rows = P["rows"]
        base = next((r for r in rows if "hip_y" in r), None)
        for r in rows:
            if base and "hip_y" in r:
                r["hips"] = round((r["hip_y"] - base["hip_y"]) / base["body"], 2)
            near = None
            for other, Q in people.items():
                if other == name:
                    continue
                o = next((q for q in Q["rows"] if q["f"] == r["f"]), None)
                if o and "x" in o and "x" in r:
                    d = math.dist((r["x"], r["y"]), (o["x"], o["y"])) / ((r["head_size"] + o["head_size"]) / 2)
                    if near is None or d < near[0]:
                        near = (d, other)
            if near:
                r["near"], r["near_who"] = round(near[0], 2), near[1]
        xs = [(r.get("x"), r.get("y")) for r in rows]
        for i, r in enumerate(rows):
            win = [q for q in xs[max(0, i - 4):i + 5] if q[0] is not None]
            if r.get("x") is not None and len(win) >= 3:
                mx, my = sum(q[0] for q in win) / len(win), sum(q[1] for q in win) / len(win)
                r["fidget"] = round(math.dist((r["x"], r["y"]), (mx, my)) / r["head_size"], 3)


def series(rows, key, a=None, b=None):
    return [(r["t"], r[key]) for r in rows if key in r and (a is None or r["t"] >= a) and (b is None or r["t"] <= b)]


def smooth(vals, w=2):
    out = []
    for i in range(len(vals)):
        part = sorted(vals[max(0, i - w):i + w + 1])
        out.append(part[len(part) // 2])
    return out


def change(rows, key, a=None, b=None):
    """The biggest move of one measure inside a window: {"from", "to", "delta", "at" (when it is half done), "peak_t"}."""
    s = series(rows, key, a, b)
    if len(s) < 3:
        return None
    ts, vs = [x[0] for x in s], smooth([x[1] for x in s])
    lo, hi = min(range(len(vs)), key=vs.__getitem__), max(range(len(vs)), key=vs.__getitem__)
    first, last = (lo, hi) if lo < hi else (hi, lo)
    v0, v1 = vs[first], vs[last]
    half = (v0 + v1) / 2
    at = next((ts[i] for i in range(first, last + 1) if (vs[i] - half) * (v1 - v0) >= 0), ts[last])
    return {"from": round(v0, 2), "to": round(v1, 2), "delta": round(v1 - v0, 2), "at": round(at, 2), "peak_t": round(ts[last], 2),
            "start": round(vs[0], 2), "end": round(vs[-1], 2)}


def events(rows, a=None, b=None):
    """What a track does inside a window, biggest first: [{"measure", "words", ...change}] for every measure that moves
    more than its floor."""
    out = []
    for key in FLOOR:
        c = change(rows, key, a, b)
        if c and abs(c["delta"]) >= FLOOR[key]:
            c.update({"measure": key, "words": WORDS[key][0 if c["delta"] > 0 else 1], "size": round(abs(c["delta"]) / FLOOR[key], 2)})
            out.append(c)
    return sorted(out, key=lambda c: -c["size"])


def fidget(rows, a=None, b=None):
    s = [v for _, v in series(rows, "fidget", a, b)]
    return round(sum(s) / len(s), 4) if s else None


def camera_read(camera, shot_list, fps=16):
    """Per shot, the operator's own camera: the path with edit punch-ins taken out.
    [{"shot", "from", "to", "pan", "tilt", "push", "roll", "shake", "punch": [{"t", "push"}], "words"}]"""
    frames = (camera or {}).get("frames") or []
    out = []
    q = max(1, int(round(fps * 0.25)))
    for k, (a, b) in enumerate(shot_list, 1):
        fr = [f for f in frames if a - 1e-6 <= f["t"] < b - 1e-6]
        if len(fr) < 2:
            out.append({"shot": k, "from": a, "to": b, "pan": 0.0, "tilt": 0.0, "push": 0.0, "roll": 0.0, "shake": 0.0, "punch": [],
                        "words": "too short to read"})
            continue
        # per-frame steps inside the shot (the path restarts at every cut, so steps are differences)
        steps = [(0.0, 0.0, 1.0, 0.0)]
        for u, v in zip(fr, fr[1:]):
            if v.get("cut"):
                steps.append((0.0, 0.0, 1.0, 0.0))
            else:
                steps.append((v["pan_x"] - u["pan_x"], v["pan_y"] - u["pan_y"], v["zoom"] / (u["zoom"] or 1.0), v["roll"] - u["roll"]))
        punch, i = [], 0
        zs = [s[2] for s in steps]
        while i < len(zs):
            j = min(len(zs), i + q)
            run = 1.0
            for z in zs[i:j]:
                run *= z
            if abs(run - 1) >= PUNCH:
                punch.append({"t": round(fr[i]["t"], 2), "push": round((run - 1) * 100, 1)})
                for n in range(i, j):
                    zs[n] = 1.0
                i = j
            else:
                i += 1
        x = y = roll = 0.0
        z = 1.0
        path = []
        for (dx, dy, _, dr), zz, f in zip(steps, zs, fr):
            x, y, z, roll = x + dx, y + dy, z * zz, roll + dr
            path.append({"t": f["t"], "pan_x": round(x, 4), "pan_y": round(y, 4), "zoom": round(z, 4), "roll": round(roll, 2)})
        xs, ys = [p["pan_x"] for p in path], [p["pan_y"] for p in path]

        def sm(v, i):
            part = v[max(0, i - fps // 2):i + fps // 2 + 1]
            return sum(part) / len(part)
        shake = (sum((xs[i] - sm(xs, i)) ** 2 + (ys[i] - sm(ys, i)) ** 2 for i in range(len(path))) / len(path)) ** 0.5
        end = path[-1]
        edit_zoom = 0.0
        if abs(end["zoom"] - 1) > 0.04 and shake < 0.0015 and abs(end["pan_x"]) < 0.02 and abs(end["pan_y"]) < 0.02:
            # a zoom about the exact centre of a frame that neither drifts nor shakes was added in the edit: a person
            # walking a phone closer drifts and bobs. It is taken out of the operator's path.
            edit_zoom = end["zoom"] - 1
            for p in path:
                p["zoom"] = 1.0
        words = []
        if abs(end["pan_x"]) > 0.03:
            words.append("pans %s %.0f%%" % ("right" if end["pan_x"] > 0 else "left", abs(end["pan_x"]) * 100))
        if abs(end["pan_y"]) > 0.03:
            words.append("tilts %s %.0f%%" % ("down" if end["pan_y"] > 0 else "up", abs(end["pan_y"]) * 100))
        if abs(end["zoom"] - 1) > 0.04:
            words.append("pushes %s %.0f%%" % ("in" if end["zoom"] > 1 else "out", abs(end["zoom"] - 1) * 100))
        if not words:
            words.append("holds its frame")
        words.append("handheld shake " + ("strong" if shake > 0.01 else "light" if shake > 0.003 else "none"))
        if punch:
            words.append("edit punch-in at " + ", ".join("%.1f s" % p["t"] for p in punch) + " (added in the edit; not the camera)")
        if edit_zoom:
            words.append("edit zoom of %.0f%% over the shot (a slow centred zoom added in the edit; not the camera)" % (abs(edit_zoom) * 100))
        out.append({"shot": k, "from": a, "to": b, "pan": round(end["pan_x"], 4), "tilt": round(end["pan_y"], 4),
                    "push": round(end["zoom"] - 1, 4), "roll": round(end["roll"], 2), "shake": round(shake, 5), "punch": punch,
                    "edit_zoom": round(edit_zoom, 4), "words": ", ".join(words), "path": path})
    return out


def by_name(S, who):
    """A shot's people under OUR names: the tracks tagged as the same person joined (where two cover one frame, the
    track that sees more of them wins); extras and untagged tracks left out. {name: {"tags": [...], "rows": [...]}}"""
    out = {}
    for letter, P in sorted(S["people"].items(), key=lambda kv: -len(kv[1]["rows"])):
        name = who.get("%s%d" % (letter, S["shot"]))
        if not name or name == "extra":
            continue
        o = out.setdefault(name, {"tags": [], "rows": [], "have": set()})
        o["tags"].append("%s%d" % (letter, S["shot"]))
        for r in P["rows"]:
            if r["f"] not in o["have"]:
                o["have"].add(r["f"])
                o["rows"].append(r)
    for o in out.values():
        o.pop("have")
        o["rows"].sort(key=lambda r: r["t"])
    return out


def table(tr, cam, step=0.25, who=None):
    """The measures as text a model (or a person) reads: per shot, the people, what each does, and the camera.
    `who` ({tag: one of our names}): the people are listed under our names, the tags they came from beside them."""
    lines = []
    for S, C in zip(tr, cam):
        lines.append("SHOT %d  %.2f-%.2f s  camera: %s" % (S["shot"], S["from"], S["to"], C["words"]))
        if who:
            groups = [(name, "%s (from %s)" % (name, ", ".join(o["tags"])), o["rows"]) for name, o in by_name(S, who).items()]
        else:
            groups = [(name, "%s%d" % (name, S["shot"]), P["rows"]) for name, P in S["people"].items()]
        for name, title, rows in groups:
            if not rows:
                continue
            x0 = sum(r["x"] for r in rows[:3] if "x" in r) / max(1, len([r for r in rows[:3] if "x" in r]))
            lines.append("  %s  starts %.0f%% across the frame, seen %.2f-%.2f s" % (title, x0 * 100, rows[0]["t"], rows[-1]["t"]))
            for e in events(rows):
                lines.append("    %s: %s %s -> %s (half done at %.2f s, done by %.2f s)" % (e["measure"], e["words"], e["from"], e["to"], e["at"], e["peak_t"]))
            t = S["from"]
            while t < S["to"] - 1e-6:
                r = min(rows, key=lambda q: abs(q["t"] - t))
                if abs(r["t"] - t) <= step:
                    bits = ["%s %s" % (k, r[k]) for k in ("lean", "head", "knees", "hips", "hand_l", "hand_r", "turn", "near") if k in r]
                    lines.append("    %.2f s  %s" % (t, "  ".join(bits)))
                t += step
    return "\n".join(lines)


def tag_list(tr):
    """Every tag with where its box sits when first seen, for whoever maps the tags to people."""
    lines = []
    for S in tr:
        for letter, P in S["people"].items():
            r = next((q for q in P["rows"] if "x" in q), None)
            if r:
                lines.append("%s%d: shot %d (%.2f-%.2f s), head %.0f%% across and %.0f%% down the frame, followed %.2f-%.2f s" % (
                    letter, S["shot"], S["shot"], S["from"], S["to"], r["x"] * 100, r["y"] * 100, P["rows"][0]["t"], P["rows"][-1]["t"]))
    return "\n".join(lines)


def label(motion_dir, cuts=None, out=None):
    """The clip with each track's letter and box drawn on its person (A1, B1...), each track its own colour, so
    whoever reads the table can see who is who. Drawn large on a 720-wide copy. Needs OpenCV: run it under the
    tracker's Python (`measure.py _label <dir>`)."""
    import subprocess
    import cv2
    d = Path(motion_dir)
    pose, tr, _ = load(d, cuts)
    by_frame = [{p["id"]: p for p in f["people"]} for f in pose["frames"]]
    cols = [(0, 255, 255), (255, 200, 0), (120, 255, 120), (255, 120, 255), (120, 160, 255), (255, 255, 255)]
    at = {}
    for S in tr:
        for k, (name, P) in enumerate(S["people"].items()):
            for r in P["rows"]:
                src = next((by_frame[r["f"]][pid] for pid in P["ids"] if pid in by_frame[r["f"]]), None)
                if src and "x" in r:
                    at.setdefault(r["f"], []).append(("%s%d" % (name, S["shot"]), r["x"], r["y"], r["head_size"], src.get("box"), cols[k % len(cols)]))
    cap = cv2.VideoCapture(str(d / "read.mp4"))
    w0, h0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    W = 720
    H = int(round(h0 * W / w0 / 2) * 2)
    raw = d / "labelled.raw.mp4"
    vw = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), int(pose.get("fps") or 16), (W, H))
    i = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        img = cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC)
        used = []
        for tag, x, y, hs, box, col in at.get(i, []):
            # the tag sits ON the person: a dot on their nose with the tag beside it, in the colour of their box
            if box:
                cv2.rectangle(img, (int(box[0] * W), int(box[1] * H)), (int((box[0] + box[2]) * W), int((box[1] + box[3]) * H)), col, 2)
            nx, ny = int(x * W), int(y * H)
            cv2.circle(img, (nx, ny), 9, (0, 0, 0), -1)
            cv2.circle(img, (nx, ny), 6, col, -1)
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 3)
            # beside the nose, on the side away from the frame's middle so two people face to face keep their tags apart
            side = -1 if x < 0.5 else 1
            others = [o for o in at.get(i, []) if o[0] != tag]
            if others:
                side = -1 if x <= min(o[1] for o in others) else (1 if x >= max(o[1] for o in others) else side)
            px = nx + 14 if side > 0 else nx - 14 - tw
            px = max(4, min(W - tw - 4, px))
            py = max(th + 8, min(H - 8, ny + th // 2))
            while any(abs(py - uy) < th + 10 and abs(px - ux) < tw + 10 for ux, uy in used):
                py += th + 12
            used.append((px, py))
            cv2.rectangle(img, (px - 4, py - th - 6), (px + tw + 4, py + 6), (0, 0, 0), -1)
            cv2.putText(img, tag, (px, py), cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 3)
            cv2.line(img, (nx, ny), (px if side > 0 else px + tw, py - th // 2), col, 2)
        vw.write(img)
        i += 1
    vw.release()
    out = Path(out or d / "labelled.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", str(out)], check=True)
    raw.unlink()
    return str(out)


def read_of(motion_dir):
    """The motion read as it stands: the model's read, with who-is-who as a person corrected it when they did
    (who.json beside it: {"A1": "<one of our people>" or "extra"}; a correction wins over the model's word)."""
    d = Path(motion_dir)
    try:
        read = json.loads((d / "motion-read.json").read_text())
    except (OSError, ValueError):
        return {}
    try:
        who = {str(k).upper(): v for k, v in json.loads((d / "who.json").read_text()).items() if not str(k).startswith("_")}
    except (OSError, ValueError):
        who = {}
    if who:
        tags = {str(k).upper(): v for k, v in (read.get("tags") or {}).items()}
        if not tags:                                   # an older read kept only each person's list
            for p in read.get("people") or []:
                for t in p.get("reference") or []:
                    tags[str(t).upper()] = p["ours"]
        tags.update(who)
        people = list(read.get("people") or [])
        for name in sorted(set(v for v in who.values() if v != "extra") - {p["ours"] for p in people}):
            people.append({"ours": name, "role": "stands by"})
        for p in people:
            p["reference"] = sorted((t for t, n in tags.items() if n == p["ours"]), key=lambda t: (int(t[1:]) if t[1:].isdigit() else 0, t[0]))
        read.update({"tags": tags, "people": people, "who_corrected": sorted(who)})
    return read


def load(motion_dir, cuts=None, keep=0.3):
    d = Path(motion_dir)
    pose = json.loads((d / "pose.json").read_text())
    cam = json.loads((d / "camera.json").read_text()) if (d / "camera.json").exists() else {}
    tr = tracks(pose, cuts, cam, keep)
    return pose, tr, camera_read(cam, [(s["from"], s["to"]) for s in tr], int(pose.get("fps") or 16))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cuts = [float(x) for x in a[a.index("--cuts") + 1].split(",") if x] if "--cuts" in a else None
    if a[0] == "_label":
        print(label(a[1], cuts))
        sys.exit(0)
    _, tr, cam = load(a[0], cuts)
    print(table(tr, cam, float(a[a.index("--step") + 1]) if "--step" in a else 0.25))
