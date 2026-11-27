#!/usr/bin/env python3
"""Retarget: the tracked real people become the 3D stand-ins' own movement (stage 3), and the tracked camera becomes
the 3D camera (stage 4).

    python3 retarget.py <motion dir> [--out <dir>] [--no-render]

<motion dir> holds a tracked reference (pose.json with `world` points, camera.json) and its motion read
(motion-read.json: which tracked person is which of our people). Writes <out>/spec.json, a blocking spec for
blocking_blender.py in which every person carries `track` (per frame: where the hips are on the floor plan and which
way every bone points) and the camera carries `track` (per frame: its turn, tilt, roll and lens), then renders it
through motion.py `blocking`, which writes the stand-ins' clip and their exact skeletons.

How a flat track becomes 3D: the tracker gives each body's own 3D pose in metres around the hips. Where that body
stands comes from its size in the frame (a body that reads half as tall is twice as far) and where it sits in the
frame, through a phone lens. The camera's tracked pan, tilt and push turn the 3D camera the same way, so the rehearsal
frames the stand-ins as the reference frames its people. An edit punch-in is left out: it is not a camera move.

The verbs (walk, reach, lean...) stay as the fallback for a person or a scene with no tracked reference
(motion_program.py). No brand, product or person is named here.
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import measure as ME  # noqa: E402

LENS = 26.0                  # a phone's main lens, as a 36 mm frame on the long side
CAM_H = 1.5
HIP_H = 0.92                 # the stand-in's hip joint above its feet
HOLD = 6                     # frames a person the tracker lost stays where they were before leaving the picture (a blink of the reader, not a person gone)
LATE = 10                    # frames into a shot within which someone first followed is taken to have been there from its start
RIG = 1.0                    # how much further off the stand-in stands than the tracked body (1 = where the real person stood)
PALETTE = [([0.75, 0.62, 0.50], [0.20, 0.18, 0.18]), ([0.15, 0.15, 0.17], [0.12, 0.12, 0.14]), ([0.42, 0.20, 0.55], [0.15, 0.15, 0.20]),
           ([0.80, 0.55, 0.15], [0.18, 0.16, 0.14]), ([0.20, 0.45, 0.70], [0.14, 0.14, 0.18]), ([0.25, 0.55, 0.35], [0.14, 0.16, 0.14])]
# stand-in bone -> the two tracked points it runs between (MediaPipe's 33)
LIMBS = {"upper_arm.L": (11, 13), "forearm.L": (13, 15), "hand.L": (15, 19), "upper_arm.R": (12, 14), "forearm.R": (14, 16),
         "hand.R": (16, 20), "thigh.L": (23, 25), "shin.L": (25, 27), "thigh.R": (24, 26), "shin.R": (26, 28)}


def _b(v):
    """A tracked world point (x right, y down, z away) in the 3D scene's axes (x right, y away, z up)."""
    return [v[0], v[2], -v[1]]


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _add(a, b):
    return [a[i] + b[i] for i in range(3)]


def _mid(a, b):
    return [(a[i] + b[i]) / 2 for i in range(len(a))]


def _norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1e-6
    return [x / n for x in v]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _frame(left, up):
    """An upright frame from a left-pointing and an up-pointing line: (left, forward, up), square to each other."""
    up = _norm(up)
    left = _norm(_sub(left, [up[i] * _dot(left, up) for i in range(3)]))
    return left, _cross(left, up), up


def _turn(v, yaw, tilt):
    """A camera-frame line turned into the scene: the camera tilted down by `tilt`, then turned right by `yaw`."""
    x, y, z = v
    y, z = y * math.cos(tilt) + z * math.sin(tilt), -y * math.sin(tilt) + z * math.cos(tilt)
    return [x * math.cos(yaw) + y * math.sin(yaw), -x * math.sin(yaw) + y * math.cos(yaw), z]


def person_frame(p, aspect, f_h, yaw=0.0, tilt=0.0):
    """One tracked person in one frame -> {"hip": [x, y, z] from the camera, before the floor is set, "dirs": {...}}."""
    b33, w = p.get("body33") or [], p.get("world") or []
    if len(b33) < 33 or len(w) < 33:
        return None
    # how big the body reads: flat lengths in the frame against the same lengths of its 3D pose, seen flat
    pairs = [(11, 12), (7, 8), (11, 23), (12, 24), (0, 11), (0, 12)]
    flat = real = 0.0
    for i, j in pairs:
        if min(b33[i][2], b33[j][2]) < 0.5:
            continue
        flat += math.hypot((b33[i][0] - b33[j][0]) * aspect, b33[i][1] - b33[j][1])
        real += math.hypot(w[i][0] - w[j][0], w[i][1] - w[j][1])
    if p.get("scale"):                                   # the people reader's own steadied size (frame heights per metre)
        depth = f_h / float(p["scale"])
    elif real < 0.05 or flat < 0.01:
        return None
    else:
        depth = f_h * real / flat
    sx, sy = _mid(b33[11][:2], b33[12][:2])
    sh_w = _mid(w[11], w[12])                                        # the shoulders, from the hips, in the tracker's axes
    # the shoulders from the camera (x right, y away, z up), then the hips under them
    sh = [(sx - 0.5) * aspect / f_h * depth, depth, -(sy - 0.5) / f_h * depth]
    hip = [x * RIG for x in _sub(sh, _b(sh_w))]
    dirs = {}
    l, f, u = _frame(_b(_sub(w[11], w[12])), _b(_sub(sh_w, _mid(w[23], w[24]))))
    dirs["spine"] = {"left": l, "up": u}
    hl, hf, hu = _frame(_b(_sub(w[23], w[24])), _b(_sub(sh_w, _mid(w[23], w[24]))))
    dirs["hips"] = {"left": hl, "up": hu}
    ears = _mid(w[7], w[8])
    face = _norm(_b(_sub(w[0], ears)))
    el = _norm(_b(_sub(w[7], w[8])))
    hup = _cross(face, el)                                           # up = forward x left
    dirs["head"] = {"left": el, "up": hup}
    dirs["neck"] = {"to": _norm(_b(_sub(ears, sh_w)))}
    for bone, (a, c) in LIMBS.items():
        if bone.startswith(("thigh", "shin")):
            # a leg the frame cuts off is a guess: the stand-in keeps its own straight leg
            if min(b33[a][2], b33[c][2]) < 0.55 or b33[c][1] > 0.97 or b33[a][1] > 0.97:
                continue
            if bone.startswith("shin") and bone.replace("shin", "thigh") not in dirs:
                continue
        dirs[bone] = {"to": _norm(_b(_sub(w[c], w[a])))}
    if yaw or tilt:
        hip = _turn(hip, yaw, tilt)
        for d in dirs.values():
            for k in d:
                d[k] = _turn(d[k], yaw, tilt)
    return {"hip": hip, "dirs": dirs, "depth": depth, "ray": [sh[0] / depth, 1.0, sh[2] / depth], "off": _b(sh_w)}


def _runs(rows, shot_of):
    """The frames a person is seen in, shot by shot: nothing is eased across a cut (the next shot is another place)."""
    runs = {}
    for i, r in enumerate(rows):
        if r:
            runs.setdefault(shot_of[i], []).append(i)
    return list(runs.values())


def _whole_limbs(rows, shot_of, gap=6, least=8):
    """A limb is followed in stretches, never in flickers: inside a shot, sightings a few frames apart are joined (the
    frames between take the nearest sighting), and a stretch shorter than half a second is dropped (the stand-in keeps
    its own arm or leg there). A limb followed for a third of the shot or more keeps its nearest followed pose over the
    rest of the shot; a forearm seen for one frame is not followed at all."""
    for idx in _runs(rows, shot_of):
        for bone in LIMBS:
            have = [n for n, i in enumerate(idx) if bone in rows[i]["dirs"]]
            if not have:
                continue
            stretches, cur = [], [have[0]]
            for n in have[1:]:
                if n - cur[-1] <= gap:
                    cur.append(n)
                else:
                    stretches.append(cur)
                    cur = [n]
            stretches.append(cur)
            for st in stretches:
                if st[-1] - st[0] + 1 < least and len(have) < len(idx):
                    for n in st:
                        rows[idx[n]]["dirs"].pop(bone)
                    continue
                for n in range(st[0], st[-1] + 1):
                    if bone not in rows[idx[n]]["dirs"]:
                        rows[idx[n]]["dirs"][bone] = json.loads(json.dumps(rows[idx[min(st, key=lambda q: abs(q - n))]]["dirs"][bone]))
            # a limb followed for a good part of the shot was there for all of it: the frames before, between and after
            # take the nearest followed pose (an ankle drifting a pixel past the frame's edge does not straighten a crossed leg)
            kept = [n for n, i in enumerate(idx) if bone in rows[i]["dirs"]]
            if kept and len(kept) < len(idx) and len(kept) >= 0.35 * len(idx):
                for n, i in enumerate(idx):
                    if bone not in rows[i]["dirs"]:
                        rows[i]["dirs"][bone] = json.loads(json.dumps(rows[idx[min(kept, key=lambda q: abs(q - n))]]["dirs"][bone]))
        for i in idx:                                    # a forearm or shin with nothing above it to hang from is left alone too
            d = rows[i]["dirs"]
            for low, up in (("forearm.L", "upper_arm.L"), ("forearm.R", "upper_arm.R"), ("hand.L", "forearm.L"), ("hand.R", "forearm.R"),
                            ("shin.L", "thigh.L"), ("shin.R", "thigh.R")):
                if low in d and up not in d:
                    d.pop(low)


def _ease(rows, key, shot_of, w=2):
    """A running average over the frames a person is seen in (hips), inside each shot, so the stand-in does not jitter."""
    for idx in _runs(rows, shot_of):
        vals = [rows[i][key] for i in idx]
        for n, i in enumerate(idx):
            part = vals[max(0, n - w):n + w + 1]
            rows[i][key] = [sum(v[k] for v in part) / len(part) for k in range(3)]


def _ease_dirs(rows, shot_of, w=2):
    for idx in _runs(rows, shot_of):
        src = [json.loads(json.dumps(rows[i]["dirs"])) for i in idx]
        for n, i in enumerate(idx):
            part = src[max(0, n - w):n + w + 1]
            for bone, d in rows[i]["dirs"].items():
                for k in d:
                    have = [q[bone][k] for q in part if bone in q and k in q[bone]]
                    d[k] = _norm([sum(v[j] for v in have) / len(have) for j in range(3)])


def _steady_depth(rows, shot_of, cam_of, band=0.3, w=4):
    """How far off a person stands, steadied: inside a shot it stays within a band of that shot's middle value (one
    bad frame, or a passer-by read as this person, cannot throw the stand-in across the room), then eased; the hips
    are placed again from it."""
    by_shot = {}
    for i, r in enumerate(rows):
        if r:
            by_shot.setdefault(shot_of[i], []).append(i)
    for idx in by_shot.values():
        ds = sorted(rows[i]["depth"] for i in idx)
        mid = ds[len(ds) // 2]
        vals = [max(mid * (1 - band), min(mid * (1 + band), rows[i]["depth"])) for i in idx]
        for n, i in enumerate(idx):
            part = vals[max(0, n - w):n + w + 1]
            d = sum(part) / len(part)
            r = rows[i]
            sh = [r["ray"][0] * d, d, r["ray"][2] * d]
            hip = [x * RIG for x in _sub(sh, r["off"])]
            r["hip"], r["depth"] = _turn(hip, *cam_of[i]) if any(cam_of[i]) else hip, d


def build(motion_dir, cast=None, size=(480, 854)):
    """The blocking spec: our people driven by the tracked people the motion read mapped them to."""
    d = Path(motion_dir)
    pose = json.loads((d / "pose.json").read_text())
    read = ME.read_of(d)                               # who-is-who as corrected by a person, when they did
    ref = json.loads((d / "ref.json").read_text()) if (d / "ref.json").exists() else {}
    cam = json.loads((d / "camera.json").read_text()) if (d / "camera.json").exists() else {}
    fps = int(pose.get("fps") or 16)
    n = len(pose["frames"])
    aspect = pose["width"] / float(pose["height"])
    f0 = LENS / 36.0                                                  # focal length in frame heights
    tr = ME.tracks(pose, ref.get("cuts"), cam)
    shots = [(s["from"], s["to"]) for s in tr]
    cams = ME.camera_read(cam, shots, fps)
    # the camera per frame: the operator's path inside each shot (edit punch-ins already taken out)
    fov_v = 2 * math.atan(0.5 / f0)
    cam_rows = [{"yaw": 0.0, "tilt": 0.0, "roll": 0.0, "zoom": 1.0, "shot": 0} for _ in range(n)]
    for k, C in enumerate(cams):
        for p in C.get("path") or []:
            i = int(round(p["t"] * fps))
            if 0 <= i < n:
                cam_rows[i] = {"yaw": p["pan_x"] * fov_v * aspect, "tilt": p["pan_y"] * fov_v, "roll": math.radians(p["roll"]),
                               "zoom": p["zoom"], "shot": k}
    for i, f in enumerate(pose["frames"]):
        cam_rows[i]["shot"] = next((k for k, (a, b) in enumerate(shots) if a - 1e-6 <= f["t"] < b - 1e-6), len(shots) - 1)
    # each of our people -> per frame, the tracked person they move like
    by_frame = [{p["id"]: p for p in f["people"]} for f in pose["frames"]]
    people, notes = [], []
    names = [p["ours"] for p in read.get("people") or []]
    for k, P in enumerate(read.get("people") or []):
        rows = [None] * n
        def seen(letter):                                           # the tag that sees more of the person goes first
            try:
                return -len(tr[int(letter[1:]) - 1]["people"][letter[0].upper()]["rows"])
            except (ValueError, IndexError, KeyError):
                return 0
        for letter in sorted(P.get("reference") or [], key=seen):
            try:
                name, shot = letter[0].upper(), int(letter[1:])
                T = tr[shot - 1]["people"][name]
            except (ValueError, IndexError, KeyError):
                notes.append("%s: the read names %s, which the track does not have" % (P["ours"], letter))
                continue
            for r in T["rows"]:
                i = r["f"]
                if rows[i] is not None:                              # an earlier tag of theirs already covers this frame
                    continue
                src = next((by_frame[i][pid] for pid in T["ids"] if pid in by_frame[i]), None)
                c = cam_rows[i]
                got = person_frame(src, aspect, f0 * c["zoom"], c["yaw"], c["tilt"]) if src else None
                if got:
                    rows[i] = got
        if not any(rows):
            notes.append("%s: not seen in the reference; left out of the rehearsal (the verbs are the fallback)" % P["ours"])
            continue
        _steady_depth(rows, [c["shot"] for c in cam_rows], [(c["yaw"], c["tilt"]) for c in cam_rows])
        _whole_limbs(rows, [c["shot"] for c in cam_rows])
        _ease(rows, "hip", [c["shot"] for c in cam_rows])
        _ease_dirs(rows, [c["shot"] for c in cam_rows])
        people.append({"name": P["ours"], "rows": rows})
    # the floor: per shot, the camera's height is set so the people it sees stand on the floor at their full height
    for k in range(len(shots)):
        idx = [i for i in range(n) if cam_rows[i]["shot"] == k]
        firsts = []
        for P in people:
            seen = sorted(P["rows"][i]["hip"][2] for i in idx if P["rows"][i])
            if seen:
                firsts.append(seen[int(len(seen) * 0.8)])               # their standing height: the hips at their highest
        lift = (HIP_H - sorted(firsts)[len(firsts) // 2]) if firsts else CAM_H
        lift = max(0.6, min(2.4, lift))
        for i in idx:
            cam_rows[i]["height"] = round(lift, 3)
    out_people = []
    for k, P in enumerate(people):
        track, last, last_shot, held = [], None, None, 0
        for i, r in enumerate(P["rows"]):
            c = cam_rows[i]
            if r:
                h = r["hip"]
                last = {"at": [round(h[0], 3), round(h[1], 3), round(h[2] + c["height"] - HIP_H, 3)],
                        "dirs": {b: {kk: [round(x, 3) for x in v] for kk, v in d.items()} for b, d in r["dirs"].items()}}
                last_shot, held = c["shot"], 0
                track.append(last)
            elif last is not None and last_shot == c["shot"] and held < HOLD:
                held += 1
                track.append(last)                                    # missed for a few frames: holds where it was
            else:
                track.append(None)                                    # lost (gone behind someone, or out of the shot): out of sight
        for k2 in range(len(shots)):
            idx = [i for i in range(n) if cam_rows[i]["shot"] == k2]
            seen = [i for i in idx if track[i]]
            if not seen:
                continue
            # the first and last frame of a run are where a tracker is least sure (someone stepping out from behind another,
            # a cut a frame away): each takes its settled neighbour's pose
            if len(seen) >= 6:
                track[seen[0]], track[seen[-1]] = track[seen[2]], track[seen[-3]]
                track[seen[1]], track[seen[-2]] = track[seen[2]], track[seen[-3]]
            if seen[0] - idx[0] <= LATE:                              # first followed a few frames into the shot: there from its start
                for i in idx:
                    if i < seen[0]:
                        track[i] = track[seen[0]]
        first = next((t for t in track if t), {"at": [0, 3, 0]})
        col, legs = PALETTE[k % len(PALETTE)]
        look = ((cast or {}).get(P["name"]) or {})
        person = {"name": P["name"], "at": first["at"][:2], "face": 0, "color": look.get("color") or col,
                  "legs": look.get("legs") or legs, "skin": look.get("skin") or [0.45, 0.30, 0.22], "track": track}
        if look.get("build"):                                     # the cast member's own torso (build.py)
            person["build"] = look["build"]
        out_people.append(person)
    spec = {"fps": fps, "seconds": round(n / float(fps), 3), "size": list(size), "people": out_people, "beats": [],
            "camera": {"at": [0, 0, CAM_H], "lens": LENS,
                       "track": [{"yaw": round(c["yaw"], 4), "tilt": round(c["tilt"], 4), "roll": round(c["roll"], 4),
                                  "lens": round(LENS * c["zoom"], 2), "height": c.get("height", CAM_H)} for c in cam_rows]},
            "sky": [0.20, 0.20, 0.23], "floor": [0.42, 0.40, 0.38], "from_track": True,
            "cuts": [round(a, 3) for a, _ in shots[1:]], "notes": notes}
    return spec


def rehearse(motion_dir, out=None, cast=None, render=True):
    """spec.json written and rendered: the stand-ins' clip, their exact skeletons and previews, in <out>."""
    import motion as MO
    d = Path(motion_dir)
    out = Path(out or d / "rehearsal")
    out.mkdir(parents=True, exist_ok=True)
    spec = build(d, cast)
    spec["render"] = render
    (out / "spec.json").write_text(json.dumps(spec, separators=(",", ":")))
    rec = MO.blocking(out / "spec.json", out / "blocking.mp4", exact=True, motion_dir=out)
    m = rec["motion"]
    m.update({"kind": "real-skeleton", "people_names": [p["name"] for p in spec["people"]], "notes": spec["notes"],
              "cuts": spec["cuts"]})
    m["take_motion"]["approved"] = False
    (out / "motion.json").write_text(json.dumps(m, indent=1))
    return m


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    m = rehearse(a[0], a[a.index("--out") + 1] if "--out" in a else None, render="--no-render" not in a)
    print(json.dumps({k: m.get(k) for k in ("source", "frames", "people_names", "notes", "camera", "seconds_to_read")}, indent=1))
