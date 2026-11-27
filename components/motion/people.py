"""The people reader: every person in a clip found and kept apart, each with a 3D pose (runs under the reader Python).

motion.py `track` uses this when the reader Python has it (rtmlib + onnxruntime beside MediaPipe and OpenCV; `motion.py
setup` builds that Python). The older reader (MediaPipe alone) stays as the fallback: it reads one clear person well
and merges two people who touch (a kiss, a hug, someone leaning in on someone) into one skeleton.

Two readers, each for what it is good at:
  where everyone is   a crowd-trained 2D whole-body reader (RTMPose through rtmlib: a person finder, then body, hands and
                      face points per person). It keeps two bodies apart when they overlap.
  how deep each limb  MediaPipe's 3D pose, read on that one person with everyone else blurred out, and trusted only on
                      frames where its shoulders, hips and head land on that person's own 2D points.
The 3D pose written per person (`world`) is built bone by bone: the bone's direction and length in the picture are the
2D reader's (so the stand-in, filmed by the same camera, lines up with the footage); how far it tips out of the picture
follows from how short it reads; and whether it tips toward the lens or away is MediaPipe's word where it agreed, the
nearest agreeing frame's otherwise.

Output per person per frame, the same shape the older reader writes: body (OpenPose 18), body33 (MediaPipe's numbering,
the joints the measures read), world (those joints in metres around the hips: x right, y down, z away), hands, face,
box, id. No brand, product or person is named here.
"""
import math
from pathlib import Path

# COCO whole-body numbering: body 0-16, feet 17-22, face 23-90, left hand 91-111, right hand 112-132
C = {"nose": 0, "leye": 1, "reye": 2, "lear": 3, "rear": 4, "lsh": 5, "rsh": 6, "lel": 7, "rel": 8, "lwr": 9, "rwr": 10,
     "lhip": 11, "rhip": 12, "lkn": 13, "rkn": 14, "lank": 15, "rank": 16}
# COCO body point -> MediaPipe's number
TO33 = {0: 0, 1: 2, 2: 5, 3: 7, 4: 8, 5: 11, 6: 12, 7: 13, 8: 14, 9: 15, 10: 16, 11: 23, 12: 24, 13: 25, 14: 26, 15: 27, 16: 28}
# OpenPose 18 from COCO (1 = the neck, mid-shoulders)
OP18 = [0, None, 6, 8, 10, 5, 7, 9, 12, 14, 16, 11, 13, 15, 2, 1, 4, 3]
# bones: name -> (from, to, metres); "mid" points are made from pairs. Lengths are a plain adult's.
BONES = [("hipline", ("rhip",), ("lhip",), 0.20), ("spine", ("lhip", "rhip"), ("lsh", "rsh"), 0.48), ("shline", ("rsh",), ("lsh",), 0.36),
         ("neck", ("lsh", "rsh"), ("lear", "rear"), 0.21), ("earline", ("rear",), ("lear",), 0.15), ("face", ("lear", "rear"), ("nose",), 0.10),
         ("uarm.L", ("lsh",), ("lel",), 0.28), ("farm.L", ("lel",), ("lwr",), 0.26), ("uarm.R", ("rsh",), ("rel",), 0.28), ("farm.R", ("rel",), ("rwr",), 0.26),
         ("thigh.L", ("lhip",), ("lkn",), 0.44), ("shin.L", ("lkn",), ("lank",), 0.44), ("thigh.R", ("rhip",), ("rkn",), 0.44), ("shin.R", ("rkn",), ("rank",), 0.44)]
# which way a bone tips when nothing says: -1 toward the lens, +1 away (hands forward, elbows back, knees forward)
DEFAULT_SIGN = {"farm.L": -1, "farm.R": -1, "uarm.L": 1, "uarm.R": 1, "thigh.L": -1, "thigh.R": -1, "shin.L": 1, "shin.R": 1, "face": -1}
MP_PAIR = {"hipline": ((24,), (23,)), "spine": ((23, 24), (11, 12)), "shline": ((12,), (11,)), "neck": ((11, 12), (7, 8)), "earline": ((8,), (7,)),
           "face": ((7, 8), (0,)), "uarm.L": ((11,), (13,)), "farm.L": ((13,), (15,)), "uarm.R": ((12,), (14,)), "farm.R": ((14,), (16,)),
           "thigh.L": ((23,), (25,)), "shin.L": ((25,), (27,)), "thigh.R": ((24,), (26,)), "shin.R": ((26,), (28,))}
SEEN = 0.35            # a point the 2D reader is this sure of counts as seen
LIMB = 0.5             # an arm or a leg needs a surer read than the trunk: a limb read on a guess swings about
STEEP = {"spine": 55, "neck": 50}     # degrees: the trunk and neck never tip out of the picture further than this
AGREE = 0.35           # MediaPipe agrees when its shoulders, hips and nose sit within this share of a shoulder width


EDGE = 0.03            # this close to the frame's edge, a body joint below the head is where the reader ran out of picture


def edge_guess(b33):
    """A joint the frame cuts off is a guess, not a sighting: body joints outside the picture, or hugging its edge, are
    marked unseen (the head is left alone: a face at the edge is still a face)."""
    for m in (11, 12, 13, 14, 15, 16, 19, 20, 23, 24, 25, 26, 27, 28):
        x, y = b33[m][0], b33[m][1]
        if not (EDGE <= x <= 1 - EDGE and EDGE <= y <= 1 - EDGE):
            b33[m][2] = min(b33[m][2], 0.2)


def relift(pose):
    """A track already made, lifted again with today's rules (no clip needed): each bone keeps the toward-or-away it
    had, and everything else is worked out afresh from the 2D points."""
    for f in pose["frames"]:
        for q in f["people"]:
            edge_guess(q["body33"])
            if len(q.get("world") or []) >= 33:
                q["mp"] = q["world"]
    lift(pose["frames"], pose["width"], pose["height"])
    return pose


def _pt(kp, sc, names):
    """The point (or the middle of two), with the weaker of their scores."""
    xs = [kp[C[n]] for n in names]
    return (sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs)), min(sc[C[n]] for n in names)


def _hull(cv2, np, kp, sc, shape, grow):
    pts = np.array([kp[j] for j in range(17) if sc[j] > 0.3], np.int32)
    m = np.zeros(shape[:2], np.uint8)
    if len(pts) >= 3:
        cv2.fillConvexPoly(m, cv2.convexHull(pts), 255)
        m = cv2.dilate(m, np.ones((grow, grow), np.uint8))
    return m


def read_people(small, fps, people, model_path, camera_step, people_ids):
    """(track, camera steps): every frame's people, each kept as the same person across frames."""
    import cv2
    import numpy as np
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python import vision as V
    from rtmlib import Wholebody
    whole = Wholebody(mode="balanced", backend="onnxruntime", device="cpu", to_openpose=False)
    pose = V.PoseLandmarker.create_from_options(V.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path("pose")), running_mode=V.RunningMode.IMAGE, num_poses=1,
        min_pose_detection_confidence=0.2, min_pose_presence_confidence=0.2))
    cap = cv2.VideoCapture(str(small))
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames, tracks, prev, cam, k = [], {}, None, [], 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        kps, scs = whole(bgr)
        found = []
        for i in range(len(kps)):
            kp, sc = kps[i], scs[i]
            upper = float(np.mean(sc[:13]))
            tall = float(kp[:17, 1][sc[:17] > 0.3].max() - kp[:17, 1][sc[:17] > 0.3].min()) if (sc[:17] > 0.3).sum() >= 4 else 0.0
            # a person: head and shoulders read clearly, and big enough to be somebody in the shot (not a face in the crowd)
            if upper < 0.42 or min(sc[C["lsh"]], sc[C["rsh"]]) < 0.3 or tall < 0.16 * H:
                continue
            found.append((tall, i))
        found = [i for _, i in sorted(found, reverse=True)[:people]]
        blur = cv2.GaussianBlur(bgr, (0, 0), 12) if len(found) > 1 else None
        bodies = []
        for i in found:
            kp, sc = kps[i], scs[i]
            sw = max(0.03 * W, float(np.linalg.norm(kp[C["lsh"]] - kp[C["rsh"]])), 0.5 * abs(float(_pt(kp, sc, ("lsh", "rsh"))[0][1] - kp[0][1])))
            b33 = [[0.0, 0.0, 0.0] for _ in range(33)]
            for c, m in TO33.items():
                x, y = float(kp[c][0]) / W, float(kp[c][1]) / H
                b33[m] = [round(x, 4), round(y, 4), round(float(sc[c]), 2)]
            edge_guess(b33)
            for m, tip, wr in ((19, 91 + 8, 9), (20, 112 + 8, 10)):            # the index fingertip, else on past the wrist
                if sc[tip] > 0.4:
                    b33[m] = [round(float(kp[tip][0]) / W, 4), round(float(kp[tip][1]) / H, 4), round(float(sc[tip]), 2)]
                else:
                    el = kp[wr - 2]
                    b33[m] = [round(float(kp[wr][0] + 0.3 * (kp[wr][0] - el[0])) / W, 4), round(float(kp[wr][1] + 0.3 * (kp[wr][1] - el[1])) / H, 4), round(float(sc[wr]) * 0.6, 2)]
            op = []
            for j in OP18:
                if j is None:
                    (x, y), s = _pt(kp, sc, ("lsh", "rsh"))
                    op.append([round(x / W, 4), round(y / H, 4), round(float(s), 2)])
                else:
                    op.append([round(float(kp[j][0]) / W, 4), round(float(kp[j][1]) / H, 4), round(float(sc[j]), 2)])
            seen = sc[:17] > 0.3
            xs, ys = kp[:17, 0][seen], kp[:17, 1][seen]
            x0, x1 = max(0.0, float(xs.min()) - sw * 0.5), min(float(W), float(xs.max()) + sw * 0.5)
            y0, y1 = max(0.0, float(ys.min()) - sw * 0.8), min(float(H), float(ys.max()) + sw * 0.3)
            body = {"body": op, "body33": b33, "hands": [], "face": [], "sw": sw / W,
                    "box": [round(x0 / W, 4), round(y0 / H, 4), round((x1 - x0) / W, 4), round((y1 - y0) / H, 4)]}
            for side, a in (("left", 91), ("right", 112)):
                if float(np.mean(sc[a:a + 21])) > 0.45:
                    body["hands"].append({"side": side, "points": [[round(float(p[0]) / W, 4), round(float(p[1]) / H, 4)] for p in kp[a:a + 21]]})
            if float(np.mean(sc[23:91])) > 0.5:
                body["face"] = [[round(float(p[0]) / W, 4), round(float(p[1]) / H, 4)] for p in kp[23:91]]
            # MediaPipe's 3D pose of this one person: everyone else blurred out of the crop first
            img = bgr
            if blur is not None:
                img = bgr.copy()
                own = _hull(cv2, np, kp, sc, bgr.shape, int(sw * 0.5) | 1)
                for j in found:
                    if j != i:
                        other = _hull(cv2, np, kps[j], scs[j], bgr.shape, int(sw * 0.35) | 1)
                        other[own > 0] = 0
                        img[other > 0] = blur[other > 0]
            cx0, cx1, cy0, cy1 = int(max(0, x0 - sw * 0.1)), int(min(W, x1 + sw * 0.1)), int(max(0, y0 - sw * 0.1)), int(min(H, y1 + sw * 0.1))
            body["mp"] = None
            if cx1 - cx0 > 24 and cy1 - cy0 > 32:
                sub = np.ascontiguousarray(cv2.cvtColor(img[cy0:cy1, cx0:cx1], cv2.COLOR_BGR2RGB))
                r = pose.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=sub))
                if r.pose_landmarks and r.pose_world_landmarks:
                    lm, errs = r.pose_landmarks[0], []
                    for c, m in ((5, 11), (6, 12), (11, 23), (12, 24), (0, 0)):
                        if sc[c] > 0.4:
                            errs.append(math.hypot(cx0 + lm[m].x * (cx1 - cx0) - kp[c][0], cy0 + lm[m].y * (cy1 - cy0) - kp[c][1]) / sw)
                    if errs and sorted(errs)[len(errs) // 2] < AGREE:
                        body["mp"] = [[q.x, q.y, q.z] for q in r.pose_world_landmarks[0]]
            bodies.append(body)
        centers = [tuple(b["body"][1][:2]) for b in bodies]
        for b, i in zip(bodies, people_ids(tracks, centers, k)):
            b["id"] = i
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        cam.append(camera_step(cv2, prev, gray, bodies, W, H))
        prev = gray
        frames.append({"t": round(k / fps, 3), "people": sorted(bodies, key=lambda b: b["id"])})
        k += 1
    lift(frames, W, H)
    return {"width": W, "height": H, "frames": frames, "reader": "rtm+mediapipe"}, cam


def _tilt_mp(mpw, pair):
    """How far a bone tips out of the picture in MediaPipe's 3D pose, in radians (+ away from the lens)."""
    a = [sum(mpw[i][k] for i in pair[0]) / len(pair[0]) for k in range(3)]
    b = [sum(mpw[i][k] for i in pair[1]) / len(pair[1]) for k in range(3)]
    v = [b[k] - a[k] for k in range(3)]
    return math.atan2(v[2], math.hypot(v[0], v[1]) or 1e-6)


def lift(frames, W, H):
    """Every person's `world` (33 joints, metres around the hips), bone by bone: the direction in the picture from the 2D
    points; the tilt toward or away from the lens from MediaPipe where it agreed, else from how short the bone reads."""
    by_id = {}
    for fi, f in enumerate(frames):
        for p in f["people"]:
            by_id.setdefault(p["id"], []).append((fi, p))
    for rows in by_id.values():
        # the person's size in the picture (frame heights per metre): the least foreshortened bone, steadied over time
        raw = []
        for _, p in rows:
            b = p["body33"]
            ratios = []
            for name, fa, fb, L in BONES:
                pa, pb = MP_PAIR[name]
                if min(b[i][2] for i in pa + pb) < SEEN:
                    continue
                ax, ay = sum(b[i][0] for i in pa) / len(pa) * W / H, sum(b[i][1] for i in pa) / len(pa)
                bx, by = sum(b[i][0] for i in pb) / len(pb) * W / H, sum(b[i][1] for i in pb) / len(pb)
                ratios.append(math.hypot(bx - ax, by - ay) / L)
            ratios.sort()
            raw.append(ratios[-2] if len(ratios) >= 3 else (ratios[-1] if ratios else None))
        known = [r for r in raw if r]
        if not known:
            for _, p in rows:
                p["world"] = []
            continue
        mid = sorted(known)[len(known) // 2]
        scale = []
        for n in range(len(rows)):
            part = sorted(r for r in raw[max(0, n - 8):n + 9] if r)
            s = part[len(part) // 2] if part else mid
            scale.append(max(0.75 * mid, min(1.35 * mid, s)))
        # each bone's tilt, frame by frame. How far it tips is read off the picture (a bone that reads shorter than it is
        # points toward or away from the lens), so the stand-in's limb is as long in the frame as the real one. Which way
        # it tips is MediaPipe's word on frames where it agreed, the nearest such frame's otherwise, else a plain guess.
        tilts = {}
        for name, _, _, L in BONES:
            pa, pb = MP_PAIR[name]
            mags, signs = [], []
            for n, (_, p) in enumerate(rows):
                b = p["body33"]
                if min(b[i][2] for i in pa + pb) < (LIMB if "." in name else SEEN):
                    mags.append(0.0)
                    signs.append(None)
                    continue
                ax, ay = sum(b[i][0] for i in pa) / len(pa) * W / H, sum(b[i][1] for i in pa) / len(pa)
                bx, by = sum(b[i][0] for i in pb) / len(pb) * W / H, sum(b[i][1] for i in pb) / len(pb)
                mags.append(min(math.radians(STEEP.get(name, 85)), math.acos(max(0.0, min(1.0, math.hypot(bx - ax, by - ay) / (L * scale[n]))))))
                signs.append((1 if _tilt_mp(p["mp"], MP_PAIR[name]) >= 0 else -1) if p.get("mp") else None)
            agreed = [n for n in range(len(rows)) if signs[n] is not None]
            vals = []
            for n, (_, p) in enumerate(rows):
                b = p["body33"]
                if signs[n] is not None:
                    sign, sure = signs[n], 1.0
                elif agreed:
                    sign, sure = signs[min(agreed, key=lambda q: abs(q - n))], 1.0
                elif name in ("hipline", "shline", "earline"):
                    # turned to the picture's left, the person's own left side is the near one
                    facing = b[0][0] - (b[7][0] + b[8][0]) / 2 if min(b[0][2], b[7][2], b[8][2]) > SEEN else b[0][0] - (b[11][0] + b[12][0]) / 2
                    sign, sure = (-1 if facing < 0 else 1), 1.0
                else:
                    sign, sure = DEFAULT_SIGN.get(name, -1), 1.0
                vals.append(sign * mags[n] * sure)
            # a bone only swaps from tipping toward the lens to tipping away by passing flat through the picture: a swap
            # while it is tipped well out of it is a misread, and the bone keeps the way it was tipping (a crossed leg
            # does not jump across a lap between two frames)
            flat = math.radians(15)
            first = [v for v in vals[:8] if abs(v) > flat]
            way = (1 if sum(1 for v in first if v > 0) * 2 >= len(first) else -1) if first else None
            for n in range(len(vals)):
                if abs(vals[n]) <= flat:
                    continue
                if way is not None and (vals[n] > 0) != (way > 0) and n > 0 and abs(vals[n - 1]) > flat and rows[n][0] - rows[n - 1][0] <= 8:
                    vals[n] = -vals[n]
                way = 1 if vals[n] > 0 else -1
            # steadied: the middle of five frames (a sign that flips for one frame is a misread)
            tilts[name] = [sorted(vals[max(0, n - 2):n + 3])[len(vals[max(0, n - 2):n + 3]) // 2] for n in range(len(vals))]
        for n, (_, p) in enumerate(rows):
            b, s = p["body33"], scale[n]

            def vec(name, L):
                pa, pb = MP_PAIR[name]
                ax, ay = sum(b[i][0] for i in pa) / len(pa) * W / H, sum(b[i][1] for i in pa) / len(pa)
                bx, by = sum(b[i][0] for i in pb) / len(pb) * W / H, sum(b[i][1] for i in pb) / len(pb)
                d = math.hypot(bx - ax, by - ay)
                if d < 1e-5 or min(b[i][2] for i in pa + pb) < (LIMB if "." in name else SEEN):
                    return None
                t = tilts[name][n]
                return [(bx - ax) / d * L * math.cos(t), (by - ay) / d * L * math.cos(t), L * math.sin(t)]
            w = [[0.0, 0.0, 0.0] for _ in range(33)]
            L = {name: length for name, _, _, length in BONES}
            hip = vec("hipline", L["hipline"]) or [L["hipline"], 0.0, 0.0]
            w[24], w[23] = [-hip[0] / 2, -hip[1] / 2, -hip[2] / 2], [hip[0] / 2, hip[1] / 2, hip[2] / 2]
            spine = vec("spine", L["spine"]) or [0.0, -L["spine"], 0.0]
            sh = vec("shline", L["shline"]) or [L["shline"], 0.0, 0.0]
            w[12], w[11] = [spine[k] - sh[k] / 2 for k in range(3)], [spine[k] + sh[k] / 2 for k in range(3)]
            neck = vec("neck", L["neck"]) or [0.0, -L["neck"], 0.0]
            ear = vec("earline", L["earline"]) or [L["earline"] * (1 if sh[0] >= 0 else -1), 0.0, 0.0]
            face = vec("face", L["face"]) or [0.0, 0.0, -L["face"]]
            one = [e for e in (7, 8) if b[e][2] > SEEN]
            if len(one) == 1 and b[0][2] > SEEN:
                # a head in profile: one ear is hidden behind it. The seen ear is the near one, so the ears run into the
                # picture and the face points along it, from that ear to the nose (not out at the lens)
                e = one[0]
                shx, shy = (b[11][0] + b[12][0]) / 2 * W / H, (b[11][1] + b[12][1]) / 2
                nx, ny = b[e][0] * W / H - shx, b[e][1] - shy
                nd = math.hypot(nx, ny) or 1e-6
                if min(b[11][2], b[12][2]) > SEEN:
                    neck = [nx / nd * L["neck"], ny / nd * L["neck"], 0.0]
                ear = [0.0, 0.0, -L["earline"] if e == 7 else L["earline"]]
                fx, fy = (b[0][0] - b[e][0]) * W / H, b[0][1] - b[e][1]
                fd = math.hypot(fx, fy) or 1e-6
                face = [fx / fd * L["face"], fy / fd * L["face"], 0.0]
            earmid = [spine[k] + neck[k] for k in range(3)]
            w[8], w[7] = [earmid[k] - ear[k] / 2 for k in range(3)], [earmid[k] + ear[k] / 2 for k in range(3)]
            w[0] = [earmid[k] + face[k] for k in range(3)]
            for a, c, name in ((11, 13, "uarm.L"), (13, 15, "farm.L"), (12, 14, "uarm.R"), (14, 16, "farm.R"),
                               (23, 25, "thigh.L"), (25, 27, "shin.L"), (24, 26, "thigh.R"), (26, 28, "shin.R")):
                v = vec(name, L[name]) or [0.0, L[name], 0.0]             # unseen: hangs straight down
                w[c] = [w[a][k] + v[k] for k in range(3)]
            for wr, el, tip in ((15, 13, 19), (16, 14, 20)):                # the hand carries on from the forearm
                fa = [w[wr][k] - w[el][k] for k in range(3)]
                nrm = math.sqrt(sum(x * x for x in fa)) or 1e-6
                if b[tip][2] > SEEN and b[wr][2] > SEEN:
                    dx, dy = (b[tip][0] - b[wr][0]) * W / H, b[tip][1] - b[wr][1]
                    d = math.hypot(dx, dy) or 1e-6
                    w[tip] = [w[wr][0] + dx / d * 0.09, w[wr][1] + dy / d * 0.09, w[wr][2] + fa[2] / nrm * 0.03]
                else:
                    w[tip] = [w[wr][k] + fa[k] / nrm * 0.09 for k in range(3)]
            p["world"] = [[round(x, 3) for x in q] for q in w]
            p["scale"] = round(s, 4)
    for f in frames:
        for p in f["people"]:
            p.pop("mp", None)
