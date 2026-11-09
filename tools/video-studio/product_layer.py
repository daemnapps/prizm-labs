#!/usr/bin/env python3
"""Lay a real product on skin in a video: track the face mesh, plan the product's path on it, render the product from
its own 3D kit along that path, and put the holding hand back in front of it.

    python3 product_layer.py step  <take.mp4> --kit <kit> --beat 1.8,5.0 [--stand-in green] [--side left] [--out out.mp4]
                                   the chain step: the printed take (our voices on) in, the same take out with the
                                   product on the skin through the beat, sound kept; the stages' files beside it
    python3 product_layer.py run   <clip.mp4> --kit <product kit folder> [--plan plan.json] [--out work/]
    python3 product_layer.py track <clip.mp4> [--out work/]                    face mesh + hands per frame -> track.json
    python3 product_layer.py plan  <work/> [--plan plan.json]                  the path on the mesh -> path.json
    python3 product_layer.py render <work/> --kit <kit>                        the product, frame by frame (Blender)
    python3 product_layer.py comp  <work/>                                     hand in front, contact shadow, grade -> layered.mp4

The take is made with the hand holding a plain stand-in of the product's shape in one keyable colour (--stand-in
green): an empty hand opens flat and leaves the product nowhere to sit, and a stand-in the colour of the product is
lost against dark hair or clothes. The stand-in gives the grip; the product covers it.

What each stage does
  track   MediaPipe Face Landmarker (478-point mesh) and Hand Landmarker (21 points a hand) on every frame, and the
          keyed stand-in (its centre, long axis and size). The mesh regions the plan can name are listed in REGIONS
          (jaw, chin and cheek on each side of the face).
  plan    plan.json says what the product does, in beats:
            {"beat": {"start": 0.8, "bpm": 96},            or "seconds": [0.8, 5.0]  (the span the moves share out)
             "follow": "hand",                             "hand": ride the tracked palm when a hand is on the face,
                                                           the planned path where none is; "path": always the plan
             "side": "right",                              the subject's own right or left
             "moves": [{"do": "circles", "region": "jaw", "beats": 4, "circles": 4, "radius": 0.07},
                       {"do": "sweep",   "from": "jaw", "to": "cheek", "beats": 2}]}
          Every point of the path is a weighted mix of mesh points, so it rides the face as the head moves. The radius
          is a fraction of the face's width. One circle per beat unless "circles" says otherwise.
  render  The kit's own 3D model (model/render3d.json names the .blend and its root; kit.json size_cm the true size),
          held as a hand holds it, in the stand-in's own pose every frame (its narrow end is the tip, its lean toward
          the lens read from how short it looks): on the skin its tip where the stand-in's tip is and its body down
          in the palm (loose in an open palm, centred on the stand-in), bristles to the skin. The face's local surface normal
          (a plane fitted to the mesh points round the contact) sets which way it faces, the stand-in's long axis
          (or the face's up) its roll, its true height against the face's width its size. Light is read off the
          clip: a key direction fitted from how bright the skin is against which way it faces, the light's colour
          from the skin's brightest part, the fill from the frame's average. Blender (EEVEE), transparent frames,
          motion blur.
  comp    The hand from the clip stays in front of the product: its own pixels, cut out by a body-skin segmenter
          (hand skin, not face skin) round the tracked hand, never painted over or shadowed; a soft contact shadow
          on the skin round the product, the product's blacks and
          white balance matched to the clip, the clip's grain on top. Writes layered.mp4, side.mp4 (clip | layered)
          and check.mp4 (mesh regions, the planned path, the hand and where the product sits).

What holds and what breaks is in the method note beside this file (PRODUCT-LAYER.md).
Needs mediapipe, opencv and numpy (any Python with them) and Blender on the PATH or in BLENDER. Models are fetched once
from Google's MediaPipe model store into ~/.cache/product-layer. No brand, product or person is named here.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

MODELS = {
    "face": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
    "hand": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
    "seg": "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite",
}
CACHE = Path.home() / ".cache" / "product-layer"
FACE_WIDTH_CM = 14.5          # cheek to cheek (mesh points 234 to 454) on an adult face; sets the product's size

# Mesh regions, by the subject's own side (MediaPipe's "right" points sit on the left of an unmirrored picture).
# Each is an ordered run of mesh points; a region point is a weighted mix of a run point and the face centre (1, nose
# tip) so the path sits on the skin inside the outline, not on its edge.
REGIONS = {
    "jaw_right": [132, 58, 172, 136, 150, 149, 176],        # ear end to chin end, along the jawline
    "jaw_left": [361, 288, 397, 365, 379, 378, 400],
    "chin": [176, 148, 152, 377, 400],
    "cheek_right": [187, 205, 50, 117],                      # low cheek up to the cheekbone
    "cheek_left": [411, 425, 280, 346],
}
INSET = {"jaw": 0.16, "chin": 0.12, "cheek": 0.05}          # how far in from the run toward the nose tip
OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149,
        150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]


def model(name):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (f"{name}.tflite" if MODELS[name].endswith(".tflite") else f"{name}.task")
    if not f.exists():
        urllib.request.urlretrieve(MODELS[name], f)
    return str(f)


# ------------------------------------------------------------------------------------------------------ stand-in
# The take's hand holds a plain stand-in in one keyable colour; it is keyed out, its shape gives the product's place
# and roll, and the product covers it. Hue ranges are OpenCV's (0-180).
KEYS = {"green": ((35, 88), 60, 28), "blue": ((95, 130), 60, 28), "magenta": ((140, 170), 60, 28)}
SPILL = {"green": [1], "blue": [2], "magenta": [0, 2]}       # RGB channels the key colour casts onto skin


def standin_mask(bgr, key):
    (h0, h1), smin, vmin = KEYS[key]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= h0) & (hsv[..., 0] <= h1) & (hsv[..., 1] >= smin) & (hsv[..., 2] >= vmin)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))


def standin_fit(bgr, key, min_area=400):
    """The stand-in's largest keyed piece: its centre, long-axis direction (narrow end up) and length, or None."""
    m = standin_mask(bgr, key)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return None
    j = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    if st[j, cv2.CC_STAT_AREA] < min_area:
        return None
    ys, xs = np.nonzero(lab == j)
    pts = np.c_[xs, ys].astype(np.float32)
    hull = cv2.convexHull(pts)
    M = cv2.moments(hull)
    c = np.array([M["m10"] / M["m00"], M["m01"] / M["m00"]])
    X = pts - pts.mean(0)
    ev, evec = np.linalg.eigh(X.T @ X / len(X))
    ax = evec[:, 1]
    # the long axis points to the TIP, the narrow end: of the two ends, the one whose outer third is thinner across.
    # When the two ends read alike (fingers over one, or seen end-on), it points up the picture.
    side = X @ np.array([-ax[1], ax[0]])
    pr = X @ ax
    lo, hi = np.percentile(pr, [33, 67])
    a_w, b_w = side[pr >= hi].std() if (pr >= hi).sum() > 20 else 0, side[pr <= lo].std() if (pr <= lo).sum() > 20 else 0
    if a_w and b_w and min(a_w, b_w) < 0.9 * max(a_w, b_w):
        if b_w < a_w:
            ax = -ax
        by = "narrow end"
    else:
        if ax[1] > 0:
            ax = -ax
        by = "up the picture"
    proj = X @ ax
    tip = pts.mean(0) + ax * proj.max()
    tail = pts.mean(0) + ax * proj.min()
    return {"c": c.round(2).tolist(), "tip": tip.round(2).tolist(), "tail": tail.round(2).tolist(), "up": ax.round(4).tolist(), "long_px": round(float(proj.max() - proj.min()), 1),
            "elong": round(float(math.sqrt(ev[1] / max(ev[0], 1e-6))), 3), "tip_by": by,
            "edge": bool(xs.min() <= 1 or ys.min() <= 1 or xs.max() >= m.shape[1] - 2 or ys.max() >= m.shape[0] - 2),
            "area": int(st[j, cv2.CC_STAT_AREA])}


# ---------------------------------------------------------------------------------------------------------- track
def track(clip, work, stand_in=None):
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model("face")), running_mode=vision.RunningMode.VIDEO, num_faces=1,
        output_facial_transformation_matrixes=True))
    hand = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model("hand")), running_mode=vision.RunningMode.VIDEO, num_hands=2,
        min_hand_detection_confidence=0.4, min_tracking_confidence=0.4))
    cap = cv2.VideoCapture(str(clip))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames, i = [], 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        ts = int(round(i * 1000 / fps))
        fr, hr = face.detect_for_video(img, ts), hand.detect_for_video(img, ts)
        row = {"i": i, "t": round(i / fps, 4), "face": None, "pose": None, "hands": []}
        if stand_in:
            row["stand_in"] = standin_fit(bgr, stand_in, min_area=int(W * H * 0.0015))
        if fr.face_landmarks:
            row["face"] = [[round(p.x * W, 2), round(p.y * H, 2), round(p.z * W, 2)] for p in fr.face_landmarks[0]]
            if fr.facial_transformation_matrixes:
                row["pose"] = np.asarray(fr.facial_transformation_matrixes[0]).round(5).tolist()
        for lm, hd in zip(hr.hand_landmarks, hr.handedness):
            row["hands"].append({"side": hd[0].category_name, "score": round(hd[0].score, 3),
                                 "points": [[round(p.x * W, 2), round(p.y * H, 2), round(p.z * W, 2)] for p in lm]})
        frames.append(row)
        i += 1
    work.mkdir(parents=True, exist_ok=True)
    out = {"clip": str(clip), "fps": fps, "size": [W, H], "regions": REGIONS, "frames": frames, "stand_in": stand_in,
           "found": {"face": sum(1 for f in frames if f["face"]), "hands": sum(1 for f in frames if f["hands"]), "of": len(frames)}}
    (work / "track.json").write_text(json.dumps(out))
    return out


# ----------------------------------------------------------------------------------------------------------- plan
def _smooth(a, k=5):
    """Centred moving average along time, edges held."""
    if len(a) < 3:
        return a
    k = min(k, len(a) // 2 * 2 + 1 - 2) if len(a) <= k else k
    pad = np.pad(a, [(k // 2, k // 2)] + [(0, 0)] * (a.ndim - 1), mode="edge")
    return np.stack([pad[j:j + len(a)] for j in range(k)]).mean(0)


def _fill(frames):
    """Frames where the face was lost hold the nearest found face."""
    have = [k for k, f in enumerate(frames) if f["face"]]
    if not have:
        raise SystemExit("no face found in the clip")
    for k, f in enumerate(frames):
        if not f["face"]:
            j = min(have, key=lambda h: abs(h - k))
            f["face"], f["pose"], f["held"] = frames[j]["face"], frames[j]["pose"], True
    return frames


def region_point(P, name, s, side):
    """A point on a named region: s in 0..1 along its run, pulled in toward the nose tip by the region's inset."""
    key = name if name in REGIONS else f"{name}_{side}"
    run = REGIONS[key]
    x = s * (len(run) - 1)
    j = min(int(x), len(run) - 2)
    a = P[run[j]] + (P[run[j + 1]] - P[run[j]]) * (x - j)
    return a + (P[1] - a) * INSET[key.split("_")[0]]


def face_axes(P):
    """The face's right and up directions in the picture (pixels a unit) and its width in pixels."""
    ex = P[454, :2] - P[234, :2]
    width = float(np.linalg.norm(P[454] - P[234]))
    ex = ex / (np.linalg.norm(ex) + 1e-9)
    ey = np.array([ex[1], -ex[0]])                     # 90 degrees from right, pointing up the face (y is down)
    if np.dot(ey, P[10, :2] - P[152, :2]) < 0:
        ey = -ey
    return ex, ey, width


def schedule(plan, total):
    """Each move's start and end in seconds."""
    b = plan.get("beat") or {}
    moves = plan["moves"]
    n = sum(m.get("beats", 1) for m in moves)
    if b.get("seconds"):
        t0, t1 = b["seconds"]
        spb = (t1 - t0) / n
    else:
        spb = 60.0 / float(b.get("bpm", 96))
        t0 = float(b.get("start", 0.0))
    out, t = [], t0
    for m in moves:
        d = m.get("beats", 1) * spb
        out.append((t, min(t + d, total), m))
        t += d
    return out, spb


def plan_path(work, plan):
    tr = json.loads((work / "track.json").read_text())
    frames = _fill(tr["frames"])
    fps, (W, H) = tr["fps"], tr["size"]
    total = len(frames) / fps
    side = plan.get("side", "right")
    sched, spb = schedule(plan, total)
    P_all = _smooth(np.array([f["face"] for f in frames], dtype=float), 3)
    rows = []
    for k, f in enumerate(frames):
        t, P = f["t"], P_all[k]
        ex, ey, width = face_axes(P)
        act = next(((a, b, m) for a, b, m in sched if a <= t < b), None)
        if act is None:
            rows.append({"i": k, "t": t, "on": False})
            continue
        a, b, m = act
        u = (t - a) / max(b - a, 1e-6)
        if m["do"] == "circles":
            c = region_point(P, m["region"], 0.15 + 0.7 * u, side)[:2]           # the centre walks along the region
            turns = m.get("circles", m.get("beats", 1))
            th = 2 * math.pi * turns * u
            r = m.get("radius", 0.07) * width
            p = c + r * (math.cos(th) * ex + math.sin(th) * ey)
        elif m["do"] == "sweep":
            e = 0.5 - 0.5 * math.cos(math.pi * u)                                 # eases in and out
            p0 = region_point(P, m["from"], 0.5, side)[:2]
            p1 = region_point(P, m["to"], 0.5, side)[:2]
            p = p0 + (p1 - p0) * e
        elif m["do"] == "hold":
            p = region_point(P, m["region"], m.get("at", 0.5), side)[:2]
        else:
            raise SystemExit(f"no move {m['do']!r}: circles, sweep, hold")
        rows.append({"i": k, "t": t, "on": True, "move": m["do"], "region": m.get("region") or m.get("to"),
                     "plan": [round(float(p[0]), 2), round(float(p[1]), 2)]})
    # follow the hand: while a hand holds the product it rides that hand, pressed to the skin when the hand is on the
    # face ("on skin"), in the palm when it is not ("carried"); one hand holds it for the whole clip, so it never jumps
    # to the other hand. With "follow": "path" it keeps to the plan (only right when the take was driven by the plan).
    follow = plan.get("follow", "hand")
    holder, last_top = None, [0.0, -1.0]
    for k, r in enumerate(rows):
        P = P_all[k]
        _, _, width = face_axes(P)
        if follow != "hand":
            r["hand"] = False
            if r["on"]:
                r["at"], r["top"], r["state"] = r["plan"], None, "on skin"
            continue
        si = frames[k].get("stand_in")
        if si:
            hull = cv2.convexHull(P[OVAL, :2].astype(np.float32))
            d = cv2.pointPolygonTest(hull, (float(si["c"][0]), float(si["c"][1])), True)
            # the device takes the stand-in's own direction every frame (owner, 9 Nov: "the tip" is its narrow end);
            # only a stand-in seen end-on (round) or cut by the frame's edge keeps the last direction read
            if si.get("elong", 2) >= 1.15 and not si.get("edge"):
                last_top = si["up"]
            r.update({"on": True, "hand": True, "at": si["c"], "c": si["c"], "tip": si.get("tip") or si["c"],
                      "anchor": "stand-in", "top": last_top, "by": "stand-in",
                      "state": "on skin" if d > -0.3 * width else "carried"})
            r.setdefault("plan", None)
            continue
        win = plan.get("window")
        got = _palm(frames[k], P, width, holder) if not win or win[0] <= frames[k]["t"] <= win[1] else None
        if got is None:
            r.update({"on": False, "hand": False})
            continue
        at, top, state, holder = got
        r.update({"on": True, "hand": True, "at": at, "top": top, "state": state, "by": "hand"})
        r.setdefault("plan", None)
    pts = np.array([r["at"] if r["on"] else [np.nan, np.nan] for r in rows], dtype=float)
    on = ~np.isnan(pts[:, 0])
    if on.any():
        sm = pts.copy()
        sm[on] = _smooth(pts[on], 5)
        for k, r in enumerate(rows):
            if r["on"]:
                r["at"] = [round(float(sm[k, 0]), 2), round(float(sm[k, 1]), 2)]
                if r.get("plan"):
                    r["drift"] = round(float(np.linalg.norm(sm[k] - np.array(r["plan"])) / face_axes(P_all[k])[2]), 3)
        # on the skin the device lies in the hand tip first (its tip at the stand-in's tip, its body down in the
        # palm); loose in an open palm it sits where the stand-in sits; it slides between the two over a few frames
        ks = [k for k, r in enumerate(rows) if r.get("anchor") == "stand-in"]
        if ks:
            # how far its long axis leans toward the lens: a stand-in that looks shorter than it does side-on is
            # turned toward the camera (its tip showing); side-on length-to-width is the clip's longest reading
            el = np.array([frames[k]["stand_in"].get("elong", 1.0) for k in ks])
            rt = max(float(np.percentile(el, 90)), 1.2)
            cos2 = np.clip((el ** 2 - 1) / (rt ** 2 - 1), 0, 1)
            tilt = _smooth(np.degrees(np.arccos(np.sqrt(cos2))), 7)
            # its direction holds from frame to frame (a stand-in does not flip end over end between frames); which
            # end is the tip is voted by every frame that could tell its narrow end, then held for the whole clip
            prev, agree, against, U = None, 0, 0, []
            for k in ks:
                si = frames[k]["stand_in"]
                u = np.array(si["up"], dtype=float)
                if prev is not None and (si.get("elong", 2) < 1.15 or si.get("edge")):
                    u = prev
                flipped = prev is not None and float(np.dot(u, prev)) < 0
                if flipped:
                    u = -u
                if si.get("tip_by") == "narrow end" and not si.get("edge"):
                    against, agree = (against + 1, agree) if flipped else (against, agree + 1)
                U.append(u)
                prev = u
            sign = -1.0 if against > agree else 1.0
            for k, u in zip(ks, U):
                u = u * sign
                rows[k]["top"] = u.round(4).tolist()
                si = frames[k]["stand_in"]                    # the tip is the end the held direction points to
                if si.get("tail") and float(np.dot(u, np.array(si["up"]))) < 0:
                    rows[k]["tip"] = si["tail"]
                else:
                    rows[k]["tip"] = si.get("tip") or si["c"]
            w = _smooth(np.array([1.0 if rows[k]["state"] == "on skin" else 0.0 for k in ks]), 9)
            C = _smooth(np.array([rows[k]["c"] for k in ks], dtype=float), 5)
            T = _smooth(np.array([rows[k]["tip"] for k in ks], dtype=float), 5)
            for k, wk, c, tp, tl in zip(ks, w, C, T, tilt):
                rows[k]["tip_w"] = round(float(wk), 3)
                rows[k]["tilt"] = round(float(tl * (1 - wk)), 1)     # loose in the palm only; on the skin it lies flat to it
                rows[k]["at"] = (c + (tp - c) * wk).round(2).tolist()
        tops = [k for k, r in enumerate(rows) if r["on"] and r.get("top")]
        if len(tops) > 2:                                   # the roll is steadied the same way as the place
            T = _smooth(np.array([rows[k]["top"] for k in tops], dtype=float), 7)
            for k, v in zip(tops, T):
                rows[k]["top"] = (v / (np.linalg.norm(v) + 1e-9)).round(4).tolist()
    out = {"plan": plan, "seconds_a_beat": round(spb, 4), "schedule": [[round(a, 3), round(b, 3), m["do"]] for a, b, m in sched],
           "fps": fps, "size": [W, H], "rows": rows}
    (work / "path.json").write_text(json.dumps(out, indent=0))
    return out


def _palm(f, P, width, holder=None):
    """Where the holding hand puts the product: (point, finger direction, "on skin" | "carried", which hand), or None.

    The holding hand is the first one seen nearest the face, then the same hand (by its side) for the rest of the clip.
    In a cupped hand the product sits under the knuckles; when that point is past the face mesh (a beard, the neck) but
    close, it is pulled onto the face; further off, the product is carried in the palm."""
    hull = cv2.convexHull(P[OVAL, :2].astype(np.float32))
    seen = []
    for h in f.get("hands") or []:
        Q = np.array(h["points"], dtype=float)
        c = Q[[5, 9, 13, 6, 10, 14], :2].mean(0)
        d = cv2.pointPolygonTest(hull, (float(c[0]), float(c[1])), True)
        seen.append((h["side"], Q, c, d))
    if holder:
        seen = [x for x in seen if x[0] == holder]
    if not seen:
        return None
    side, Q, c, d = max(seen, key=lambda x: x[3])
    top = Q[12, :2] - Q[0, :2]
    top = (top / (np.linalg.norm(top) + 1e-9)).round(4).tolist()
    if d < -0.35 * width:
        c = Q[[0, 5, 9, 13, 17], :2].mean(0) * 0.5 + Q[[5, 9, 13, 17], :2].mean(0) * 0.5
        return [round(float(c[0]), 2), round(float(c[1]), 2)], top, "carried", side
    if d < 0.04 * width:
        ctr = P[1, :2]
        for _ in range(40):
            c = c + (ctr - c) * 0.05
            if cv2.pointPolygonTest(hull, (float(c[0]), float(c[1])), True) >= 0.04 * width:
                break
    return [round(float(c[0]), 2), round(float(c[1]), 2)], top, "on skin", side


# --------------------------------------------------------------------------------------------------------- light
def light_of(clip, frames, step=10):
    """Key direction (camera space: x right, y up, z toward the camera), key and fill colour, from the skin."""
    cap = cv2.VideoCapture(str(clip))
    N, L = [], []
    tint = []
    for k in range(0, len(frames), step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, k)
        ok, bgr = cap.read()
        if not ok or not frames[k]["face"]:
            continue
        P = np.array(frames[k]["face"], dtype=float)
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        for j in range(0, 468, 3):
            n = _normal(P, P[j])
            x, y = int(P[j, 0]), int(P[j, 1])
            if 0 <= x < bgr.shape[1] and 0 <= y < bgr.shape[0] and n[2] > 0.2:
                N.append(n)
                L.append(lab[y, x, 0] / 255.0)
        mask = np.zeros(bgr.shape[:2], np.uint8)
        cv2.fillConvexPoly(mask, cv2.convexHull(P[OVAL, :2].astype(np.int32)), 255)
        skin = bgr[mask > 0].astype(float)
        bright = skin[skin.sum(1) >= np.percentile(skin.sum(1), 90)]
        tint.append((bright.mean(0)[::-1] / 255.0, bgr.reshape(-1, 3).mean(0)[::-1] / 255.0))
    N, L = np.array(N), np.array(L)
    A = np.c_[np.ones(len(N)), N]
    coef, *_ = np.linalg.lstsq(A, L, rcond=None)
    # the skin faces the camera mostly, so the fit reads the light's side (x, y) well and its depth (z) badly: keep the
    # side it found and set the key about 35 degrees off the lens on that side
    xy = coef[1:3] / (np.linalg.norm(coef[1:3]) + 1e-9)
    d = np.array([xy[0] * 0.7, xy[1] * 0.7, 1.0])
    d = d / np.linalg.norm(d)
    key = np.mean([a for a, _ in tint], 0)
    fill = np.mean([b for _, b in tint], 0)
    contrast = float(np.linalg.norm(coef[1:]) / max(coef[0], 1e-3))
    return {"dir": d.round(4).tolist(), "key_rgb": (key / key.max()).round(4).tolist(), "fill_rgb": fill.round(4).tolist(),
            "contrast": round(contrast, 3), "skin_mean": round(float(L.mean()), 3)}


def _normal(P, at, k=14):
    """The skin's outward normal at a picture point, from a plane fitted to the nearest mesh points (camera space)."""
    Q = P[:468]
    d = np.linalg.norm(Q[:, :2] - at[:2], axis=1)
    near = Q[np.argsort(d)[:k]]
    X = np.c_[near[:, 0], -near[:, 1], -near[:, 2]]   # picture (x right, y down, z away) -> camera (x right, y up, z toward)
    X = X - X.mean(0)
    n = np.linalg.svd(X)[2][2]
    return n if n[2] > 0 else -n


# ------------------------------------------------------------------------------------------------------- render
def kit_of(kit):
    kit = Path(kit)
    r3 = json.loads((kit / "model" / "render3d.json").read_text())
    size = json.loads((kit / "kit.json").read_text()).get("size_cm") or {}
    return {"blend": str((kit / "model" / r3["model"]["blend"].split("model/", 1)[-1]).resolve()), "root": r3["model"]["root"],
            "height_cm": float(size.get("height", 10)), "depth_cm": float(size.get("depth", 3))}


def poses(work, kit, tilt_deg=None):
    """One product placement a frame, in camera space and centimetres (the camera looks down -z, orthographic)."""
    tr = json.loads((work / "track.json").read_text())
    pa = json.loads((work / "path.json").read_text())
    frames = _fill(tr["frames"])
    W, H = tr["size"]
    K = kit_of(kit)
    light = light_of(tr["clip"], frames)
    P_all = _smooth(np.array([f["face"] for f in frames], dtype=float), 3)
    out = []
    for k, r in enumerate(pa["rows"]):
        if not r["on"]:
            out.append(None)
            continue
        P = P_all[k]
        ex, ey, width = face_axes(P)
        cm = FACE_WIDTH_CM / width                                    # centimetres a pixel at the face
        at = np.array(r["at"])
        n = _normal(P, at) if r.get("state") != "carried" else np.array([0.0, 0.0, 1.0])
        R0 = np.array(frames[k]["pose"])[:3, :3] if frames[k].get("pose") else np.eye(3)
        fwd = R0[:, 2] / (np.linalg.norm(R0[:, 2]) + 1e-9)            # the way the face looks, from the head pose
        # held in the hand, bristles to the skin: the skin's own way of facing decides how much of its side shows
        w_skin = 0.45 + 0.35 * r.get("tip_w", 0.0)
        n = (w_skin * n + (1 - w_skin) * fwd) if r.get("state") != "carried" else n                                    # pressed on the skin, but a hand holds it square
        n = n / np.linalg.norm(n)                                     # to the face, not to the jaw's edge
        up2 = np.array(r["top"]) if r.get("top") else _tilted_up(ex, ey, r, pa["plan"])
        up = np.array([up2[0], -up2[1], 0.0])                         # picture direction -> camera direction
        if r.get("tilt"):                                             # its tip turned toward the lens: the long axis
            tl = math.radians(r["tilt"])                              # leans out of the picture and the back turns
            up = np.array([up[0] * math.cos(tl), up[1] * math.cos(tl), math.sin(tl)])   # with it
            up = up / (np.linalg.norm(up) + 1e-9)
            n = n - up * np.dot(n, up)
            n = n / (np.linalg.norm(n) + 1e-9)
        else:
            up = up - n * np.dot(up, n)
            up = up / (np.linalg.norm(up) + 1e-9)
        back = n                                                      # the product's back faces out of the skin
        right = np.cross(up, back)                                    # model axes: x right, y back, z top
        R = np.c_[right, back, up]
        # the contact: the middle of the bristle pad sits on the skin, pressed in a little
        x, y = (at[0] - W / 2) * cm, (H / 2 - at[1]) * cm
        z = float(-np.median(P[:468, 2])) * cm * 0 - 100.0
        if r.get("anchor") == "stand-in":
            # the device lies in the hand: on the skin its tip where the stand-in's tip is and its body back down in
            # the palm, so the hand covers most of it and the tip shows (owner, 9 Nov); loose in a palm, centred
            tw = r.get("tip_w", 0.0)
            pad = np.array([0.0, 0.0, K["height_cm"] * (0.5 + 0.47 * tw)])
        else:
            pad = np.array([0.0, -K["depth_cm"] / 2 + 0.05, K["height_cm"] * 0.55])
        loc = np.array([x, y, z]) - R @ pad
        out.append({"i": k, "R": R.round(5).tolist(), "loc": loc.round(4).tolist()})
    data = {"size": [W, H], "width_cm": W * FACE_WIDTH_CM / float(np.median([face_axes(p)[2] for p in P_all])),
            "fps": tr["fps"], "kit": K, "light": light, "frames": out}
    (work / "poses.json").write_text(json.dumps(data))
    return data


def _tilted_up(ex, ey, r, plan):
    """With no hand to read, the product's top leans out toward the ear on the jaw and stands up the face elsewhere."""
    lean = {"jaw": 35, "chin": 0, "cheek": 15}.get(str(r.get("region") or "").split("_")[0], 10)
    sgn = -1 if plan.get("side", "right") == "right" else 1          # the subject's right is the picture's left
    a = math.radians(lean) * sgn
    return (ey * math.cos(a) + ex * math.sin(a)).tolist()


BLENDER_SCRIPT = r'''
import bpy, json, math, sys
from mathutils import Matrix, Vector
D = json.loads(open(sys.argv[sys.argv.index("--") + 1]).read())
out = sys.argv[sys.argv.index("--") + 2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
K = D["kit"]
with bpy.data.libraries.load(K["blend"], link=False) as (src, dst):
    dst.objects = list(src.objects)
keep = set()
def under(o):
    while o is not None:
        if o.name == K["root"]:
            return True
        o = o.parent
    return False
for o in dst.objects:
    if o is not None and under(o):
        sc.collection.objects.link(o); keep.add(o.name)
root = bpy.data.objects[K["root"]]
W, H = D["size"]
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.sensor_fit = "HORIZONTAL"; cam.data.ortho_scale = D["width_cm"]
cam.data.clip_start = 1; cam.data.clip_end = 500
L = D["light"]
sun = bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
sc.collection.objects.link(sun)
sun.rotation_mode = "QUATERNION"
sun.rotation_quaternion = Vector(L["dir"]).to_track_quat("Z", "Y")      # a sun shines down its -Z
sun.data.color = L["key_rgb"]; sun.data.energy = 3.0 * (0.6 + L["contrast"]); sun.data.angle = math.radians(12)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = list(L["fill_rgb"]) + [1]; bg.inputs[1].default_value = 0.55
sc.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE_NEXT"
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.fps = int(round(D["fps"]))
sc.view_settings.view_transform = "Standard"
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
root.rotation_mode = "QUATERNION"
last = None
first = None
for f in D["frames"]:
    if f is None:
        continue
    k = f["i"] + 1
    first = k if first is None else first
    M = Matrix([f["R"][0] + [f["loc"][0]], f["R"][1] + [f["loc"][1]], f["R"][2] + [f["loc"][2]], [0, 0, 0, 1]])
    root.matrix_world = M
    root.keyframe_insert("location", frame=k); root.keyframe_insert("rotation_quaternion", frame=k)
    root.hide_render = False; root.keyframe_insert("hide_render", frame=k)
    last = k
sc.frame_start, sc.frame_end = first, last
sc.render.filepath = out + "/"
bpy.ops.render.render(animation=True)
'''


def render(work, kit):
    data = poses(work, kit)
    rd = work / "render"
    if rd.exists():
        shutil.rmtree(rd)
    rd.mkdir(parents=True)
    (work / "blender_layer.py").write_text(BLENDER_SCRIPT)
    blender = os.environ.get("BLENDER") or shutil.which("blender") or "/Applications/Blender.app/Contents/MacOS/Blender"
    r = subprocess.run([blender, "-b", "--python", str(work / "blender_layer.py"), "--", str(work / "poses.json"), str(rd)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not list(rd.glob("*.png")):
        raise SystemExit("blender failed:\n" + (r.stdout[-1500:] + r.stderr[-1500:]))
    return data


# --------------------------------------------------------------------------------------------------------- comp
def hand_mask(Q, shape, width):
    """A hand's pixels from its 21 points: the palm and the four fingers as one filled shape (held fingers sit
    together, so nothing shows between them), grown by half a finger's width; the thumb as its own thick stroke, so
    the product shows in the gap between thumb and fingers, as it does in a real grip. Feathered."""
    m = np.zeros(shape, np.uint8)
    t = max(3, int(width * 0.08))
    body = Q[[0, 1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20], :2].astype(np.int32)
    cv2.fillConvexPoly(m, cv2.convexHull(body), 255)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (t, t)))
    for a, b in zip([0, 1, 2, 3], [1, 2, 3, 4]):
        cv2.line(m, tuple(Q[a, :2].astype(int)), tuple(Q[b, :2].astype(int)), 255, int(t * (1.2 if a < 2 else 1.0)), cv2.LINE_AA)
    cv2.circle(m, tuple(Q[4, :2].astype(int)), int(t * 0.5), 255, -1, cv2.LINE_AA)
    return cv2.GaussianBlur(m, (0, 0), max(1.0, t * 0.15)).astype(np.float32) / 255.0


def grade(rgb, a, frame, light):
    """The product matched to the clip: its body brought to the level of the clip's own blacks (a black object lit by the
    same light), highlights kept, white balance the clip's."""
    lum = frame.astype(np.float32).mean(2) / 255.0
    black = float(np.percentile(lum, 4))
    y = rgb.mean(2)
    m = a > 0.5
    if m.any():
        med = float(np.median(y[m]))
        gain = float(np.clip((black * 1.9 + 0.015) / max(med, 1e-3), 0.25, 1.6))
        w = np.clip((y - 0.35) / 0.5, 0, 1)[..., None]                 # bright parts (the light ring) keep their level
        rgb = rgb * (gain * (1 - w) + w)
    wb = np.array(light["fill_rgb"]) / (np.mean(light["fill_rgb"]) + 1e-6)
    rgb = rgb * (0.9 + 0.1 * wb) + black * 0.35
    return np.clip(rgb, 0, 1)


def _clean_standin(out, V, a, width, key="green"):
    """Any stand-in the product does not cover is filled from round it; its colour cast on the hand is taken off."""
    left = ((V > 0.5) & (a < 0.5)).astype(np.uint8) * 255
    img = (np.clip(out, 0, 1) * 255).astype(np.uint8)[:, :, ::-1].copy()
    if left.any():
        img = cv2.inpaint(img, cv2.dilate(left, np.ones((5, 5), np.uint8)), 6, cv2.INPAINT_TELEA)
    o = img[:, :, ::-1].astype(np.float32) / 255.0
    near = cv2.dilate((V > 0.5).astype(np.uint8), np.ones((int(width * 0.12) | 1,) * 2, np.uint8)).astype(bool)
    for ch in SPILL[key]:                          # the key colour's channel(s) held to the others' level
        g = o[..., ch]
        cap = np.max(np.delete(o, SPILL[key], axis=2), axis=2) if len(SPILL[key]) < 3 else g
        o[..., ch] = np.where(near & (g > cap), cap + (g - cap) * 0.15, g)
    return o


def _segmenter():
    try:
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=model("seg")), output_confidence_masks=True))
        return lambda bgr: seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,
                                                data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))).confidence_masks[2].numpy_view()
    except Exception:
        return None


def hand_pixels(bgr, hands, width, skin):
    """The hand's own pixels: body skin (not face skin) from the segmenter, kept inside the area round the hand's 21
    points (so the neck is not taken), feathered by a pixel or two. Falls back to the drawn mask without a segmenter."""
    H, W = bgr.shape[:2]
    drawn = np.zeros((H, W), np.float32)
    for h in hands:
        drawn = np.maximum(drawn, hand_mask(np.array(h["points"], dtype=float), (H, W), width))
    if skin is None or not hands:
        return drawn
    area = cv2.dilate((drawn > 0.05).astype(np.uint8), np.ones((int(width * 0.14) | 1,) * 2, np.uint8)).astype(np.float32)
    body = np.clip((np.asarray(skin(bgr), dtype=np.float32) - 0.25) / 0.5, 0, 1)
    return cv2.GaussianBlur(body * area, (0, 0), 0.8)


def comp(work):
    tr = json.loads((work / "track.json").read_text())
    pa = json.loads((work / "path.json").read_text())
    po = json.loads((work / "poses.json").read_text())
    frames = _fill(tr["frames"])
    W, H = tr["size"]
    fps = tr["fps"]
    cap = cv2.VideoCapture(tr["clip"])
    dirs = {"layered": work / "frames-layered", "check": work / "frames-check"}
    for d in dirs.values():
        if d.exists():
            shutil.rmtree(d)
        d.mkdir()
    rng = np.random.default_rng(7)
    skin = _segmenter()
    light = po["light"]
    sdir = np.array([-light["dir"][0], light["dir"][1]])            # the shadow falls away from the key (picture y down)
    for k, f in enumerate(frames):
        ok, bgr = cap.read()
        if not ok:
            break
        P = np.array(f["face"], dtype=float)
        _, _, width = face_axes(P)
        img = bgr[:, :, ::-1].astype(np.float32) / 255.0
        out = img.copy()
        png = work / "render" / f"{k + 1:04d}.png"
        r = pa["rows"][k] if k < len(pa["rows"]) else {"on": False}
        hm = hand_pixels(bgr, f.get("hands") or [], width, skin)
        key = tr.get("stand_in")
        V = cv2.dilate(standin_mask(bgr, key), np.ones((3, 3), np.uint8)).astype(np.float32) / 255.0 if key else None
        if V is not None:
            hm = hm * (1 - V)                       # where the stand-in shows, the hand is not in front
        if r.get("on") and png.exists():
            rgba = cv2.imread(str(png), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
            rgb, a = rgba[:, :, 2::-1], rgba[:, :, 3]
            rgb = grade(rgb, a, bgr, light)
            # contact shadow: the product's shape, softened and pushed away from the light, darkening the skin
            sh = cv2.GaussianBlur(a, (0, 0), width * 0.03)
            M = np.float32([[1, 0, sdir[0] * width * 0.025], [0, 1, sdir[1] * width * 0.025]])
            sh = cv2.warpAffine(sh, M, (W, H))
            out = out * (1 - 0.45 * (sh * (1 - hm))[..., None])        # no shadow on the fingers in front
            # the hand in the clip stays in front of the product; only where a hand is tracked
            a_vis = a * (1 - hm) if r.get("hand") else a
            out = out * (1 - a_vis[..., None]) + rgb * a_vis[..., None]
            if V is not None:
                out = _clean_standin(out, V, a, width, key)
            grain = rng.normal(0, 0.012, (H, W, 1)).astype(np.float32)
            out = np.clip(out + grain * a_vis[..., None], 0, 1)
        if V is not None and not (r.get("on") and png.exists()):
            out = _clean_standin(out, V, np.zeros((H, W), np.float32), width, key)
        cv2.imwrite(str(dirs["layered"] / f"{k:04d}.png"), (out[:, :, ::-1] * 255).astype(np.uint8))
        chk = (out[:, :, ::-1] * 255).astype(np.uint8).copy()
        for name, run in REGIONS.items():
            col = {"jaw": (0, 200, 255), "chin": (255, 120, 0), "cheek": (120, 255, 120)}[name.split("_")[0]]
            pts = np.array([P[j, :2] for j in run], np.int32)
            cv2.polylines(chk, [pts], False, col, 2, cv2.LINE_AA)
        for j in range(0, 468, 4):
            cv2.circle(chk, (int(P[j, 0]), int(P[j, 1])), 1, (200, 200, 200), -1)
        ons = [q for q in pa["rows"][:k + 1] if q.get("plan")]
        for q0, q1 in zip(ons, ons[1:]):
            cv2.line(chk, tuple(np.int32(q0["plan"])), tuple(np.int32(q1["plan"])), (255, 0, 255), 2, cv2.LINE_AA)
        if r.get("on"):
            cv2.circle(chk, tuple(np.int32(r["at"])), 7, (0, 255, 0) if r.get("hand") else (255, 0, 255), 2, cv2.LINE_AA)
        for h in f.get("hands") or []:
            Q = np.array(h["points"], dtype=float)
            for a_, b_ in [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
                           (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]:
                cv2.line(chk, tuple(Q[a_, :2].astype(int)), tuple(Q[b_, :2].astype(int)), (255, 255, 0), 1, cv2.LINE_AA)
        cv2.putText(chk, f"{f['t']:.2f}s  plan: {r.get('move') or '-'}  product: {r.get('state', '-') if r.get('on') else 'hidden'}",
                    (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(str(dirs["check"] / f"{k:04d}.png"), chk)
    enc = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17"]
    for name, d in dirs.items():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(d / "%04d.png")] + enc + [str(work / f"{name}.mp4")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tr["clip"], "-i", str(work / "layered.mp4"), "-filter_complex",
                    "[0:v][1:v]hstack=2", "-an"] + enc + [str(work / "side.mp4")], check=True)
    return {k: str(work / f"{k}.mp4") for k in ["layered", "side", "check"]}


# ----------------------------------------------------------------------------------------------------------- cli
DEFAULT_PLAN = {"beat": {"seconds": [1.0, 5.0]}, "follow": "hand", "side": "right",
                "moves": [{"do": "circles", "region": "jaw", "beats": 3, "circles": 3, "radius": 0.06},
                          {"do": "sweep", "from": "jaw", "to": "cheek", "beats": 1}]}


def step(take, kit, beat, out, plan=None, stand_in=None, side=None):
    """Product on skin as one step of the finished chain: the printed take (with our voices laid on) and the beat where
    the product is used in, the same take out with the real product on the skin, the take's own sound kept. Outside
    the beat the picture is the take's own, except where a keyed stand-in still shows (it is always covered)."""
    take, out = Path(take).resolve(), Path(out).resolve()
    work = out.parent / (out.stem + "-product-layer")
    plan = dict(plan or DEFAULT_PLAN)
    plan["beat"] = {"seconds": list(beat)}
    plan["window"] = list(beat)
    if side:
        plan["side"] = side
    t = track(take, work, stand_in)
    p = plan_path(work, plan)
    render(work, kit)
    comp(work)
    has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of",
                                "csv=p=0", str(take)], capture_output=True, text=True).stdout.strip() != ""
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(work / "layered.mp4")]
    cmd += (["-i", str(take), "-map", "0:v", "-map", "1:a", "-c:a", "copy"] if has_audio else [])
    subprocess.run(cmd + ["-c:v", "copy", "-shortest", str(out)], check=True)
    rows = p["rows"]
    inside = [r for r in rows if beat[0] <= r["t"] <= beat[1]]
    report = {"take": str(out), "work": str(work), "sound": has_audio,
              "product_frames": sum(1 for r in rows if r.get("on")),
              "beat_frames": len(inside), "beat_frames_without_product": sum(1 for r in inside if not r.get("on")),
              "by_stand_in": sum(1 for r in rows if r.get("by") == "stand-in"),
              "face_found": t["found"]["face"], "of": t["found"]["of"]}
    (work / "step.json").write_text(json.dumps(report, indent=1))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["step", "run", "track", "plan", "render", "comp"])
    ap.add_argument("src")
    ap.add_argument("--kit")
    ap.add_argument("--plan")
    ap.add_argument("--out")
    ap.add_argument("--beat", help="step: the seconds the product is used, start,end")
    ap.add_argument("--side", choices=["right", "left"], help="step: the subject's own side the product works on")
    ap.add_argument("--stand-in", choices=sorted(KEYS), help="the take's hand holds a stand-in of this colour")
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text()) if a.plan else DEFAULT_PLAN
    if a.stage == "step":
        if not (a.kit and a.beat):
            sys.exit("step needs --kit <product kit folder> and --beat start,end")
        out = a.out or str(Path(a.src).with_name(Path(a.src).stem + "-product.mp4"))
        beat = [float(x) for x in a.beat.split(",")]
        print(json.dumps(step(a.src, a.kit, beat, out, plan if a.plan else None, a.stand_in, a.side)))
        return
    if a.stage in ("run", "track"):
        work = Path(a.out or Path(a.src).with_suffix("")).resolve()
        t = track(Path(a.src).resolve(), work, a.stand_in)
        print(json.dumps({"track": str(work / "track.json"), "found": t["found"]}))
        if a.stage == "track":
            return
    else:
        work = Path(a.src).resolve()
    if a.stage in ("run", "plan"):
        p = plan_path(work, plan)
        print(json.dumps({"path": str(work / "path.json"), "on_hand": sum(1 for r in p["rows"] if r.get("hand")),
                          "on_plan": sum(1 for r in p["rows"] if r.get("on") and not r.get("hand"))}))
    if a.stage in ("run", "render"):
        if not a.kit:
            sys.exit("--kit <product kit folder> is needed to render")
        d = render(work, a.kit)
        print(json.dumps({"render": str(work / "render"), "light": d["light"]}))
    if a.stage in ("run", "comp"):
        print(json.dumps(comp(work)))


if __name__ == "__main__":
    main()
