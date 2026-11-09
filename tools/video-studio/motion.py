#!/usr/bin/env python3
"""Motion: any clip in, the motion out (components/video-production/BRIEF-SPEC.md rule 7, "Motion sources", 2026-11-09).

A scene's motion is authored before anything is printed: a swipe's seconds, a phone recording of someone acting the beat
out, or a render of a 3D blocking. This reads the clip and gives back the motion, so it can be watched as moving
skeletons, approved, and then drive the take (take.py `motion`).

    python3 motion.py track <clip> --out <dir> [--from S] [--to S] [--fps 16] [--people 6] [--engine local|fal]
    python3 motion.py scene <scene dir> <clip> [--from S] [--to S] [--kind swipe|phone|3d] [--engine local|fal] [--name NAME]
    python3 motion.py approve <scene dir> [--by NAME]
    python3 motion.py blocking <spec.json> --out <clip.mp4> [--track]     a 3D blocking rendered to a clip (Blender)
    python3 motion.py program <take.json> --out <dir> | <scene dir>       our own motion, programmed from the take
                                                                           (motion_program.py): the default source

`track` writes into <dir>:
  pose.json      every frame: each person (kept as the same person across frames) with body (OpenPose 18 points, plus the
                 detector's 33), both hands (21 points each) and face points (outline, eyes, brows, lips); x, y as fractions
                 of the frame, with a confidence
  skeleton.mp4   the moving skeletons on black, OpenPose colours, at the processing rate (16 fps, what the pose route reads)
  overlay.mp4    the skeletons drawn over the clip, with the camera's path in the corner: the preview a person approves
  camera.json    the camera's own movement, separate from the people's: per frame pan x/y (fractions of the frame), push
                 in/out (scale) and roll (degrees), solved from the background with every person masked out; a summary
                 line (pans, pushes, shake) for the page
  sheet.jpg      six moments of the overlay side by side
  motion.json    what was read: source, span, engine, people, frames, cost, and the status (`tracked`, then `approved`)

`blocking` renders a blocking spec (stand-in people, an optional .glb set, beats such as "A reaches both hands to B's
cheeks from 1 s to 2 s", a camera that moves; see blocking_blender.py) through Blender, headless, into a clip the tracker
reads; `--track` tracks it straight after. Blender is MOTION_BLENDER, else `blender` on the path.

`scene` copies the clip into <scene dir>/motion/ and tracks it there; `approve` marks it ready for the take. The scene's
motion clip for take.py is motion.json `take_motion` ({"source", "from", "to", "approved": true}).

Engines: `local` (default) is MediaPipe on this machine (pose, hands and face landmarkers, several people), free.
`fal` sends each processed frame to fal's DWPose (an image of the skeleton per frame, no keypoints back): the skeleton
video only, paid per call; use it when the local reader misses people. Models download once into MOTION_MODELS
(default: motion-models in the user's cache folder). The local engine needs MediaPipe and OpenCV: MOTION_PYTHON names a Python that
has them, else the workspace's video-edit environment is used. No brand, product or person is named here.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

MODELS = Path(os.environ.get("MOTION_MODELS") or Path.home() / ("Library/Caches" if sys.platform == "darwin" else ".cache") / "motion-models")
MODEL_URLS = {
    "pose": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    "hand": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
    "face": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
    "person": "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite2/float16/latest/efficientdet_lite2.tflite",
}
FAL_DWPOSE = "fal-ai/dwpose"
FAL_DWPOSE_USD = 0.0006          # per frame image, as fal lists it
PREVIEW_W = 480                  # previews are made small: they are for watching the motion, not for printing

# MediaPipe's 33 body points -> OpenPose's 18 (neck = mid-shoulders)
OP18 = [0, None, 12, 14, 16, 11, 13, 15, 24, 26, 28, 23, 25, 27, 5, 2, 8, 7]
LIMBS = [(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13), (1, 0),
         (0, 14), (14, 16), (0, 15), (15, 17)]
COLORS = [(255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0), (85, 255, 0), (0, 255, 0),
          (0, 255, 85), (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255),
          (170, 0, 255), (255, 0, 255), (255, 0, 170), (255, 0, 85)]
HAND_EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (0, 9), (9, 10), (10, 11), (11, 12),
              (0, 13), (13, 14), (14, 15), (15, 16), (0, 17), (17, 18), (18, 19), (19, 20)]
# face points kept: the outline, brows, eyes, nose line and lips of MediaPipe's 478-point mesh
FACE_KEEP = sorted({10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176,
                    149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
                    70, 63, 105, 66, 107, 336, 296, 334, 293, 300,
                    33, 160, 158, 133, 153, 144, 362, 385, 387, 263, 373, 380, 468, 473,
                    168, 6, 197, 195, 5, 4, 1, 98, 327,
                    61, 40, 37, 0, 267, 270, 291, 321, 314, 17, 84, 91, 78, 81, 13, 311, 308, 402, 14, 178})


# ---------------------------------------------------------------- environment

def _has_reader():
    try:
        import cv2  # noqa: F401
        import mediapipe  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def reader_python():
    """A Python with MediaPipe and OpenCV: MOTION_PYTHON, this one, or the workspace's video-edit environment."""
    cands = [os.environ.get("MOTION_PYTHON")]
    if _has_reader():
        cands.append(sys.executable)
    roots = [ST.REPO, Path(ST.WRITING).parents[2] if len(Path(ST.WRITING).parents) > 2 else None]
    cands += [str(r / "components" / "video-edit" / ".venv" / "bin" / "python") for r in roots if r]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    raise SystemExit("no Python with MediaPipe and OpenCV: set MOTION_PYTHON, or set up components/video-edit/.venv")


def model(name):
    MODELS.mkdir(parents=True, exist_ok=True)
    f = MODELS / Path(MODEL_URLS[name]).name
    if not f.exists():
        urllib.request.urlretrieve(MODEL_URLS[name], f)
    return str(f)


def seconds_of(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def cut(clip, out, start, end, fps):
    """The span at the processing rate, small enough to read fast; sound dropped."""
    span = ["-ss", f"{start:.3f}"] + (["-t", f"{end - start:.3f}"] if end else [])
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + span + ["-i", str(clip), "-an", "-vf",
                    f"fps={fps},scale='min(720,iw)':-2", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                    str(out)], check=True)


# ---------------------------------------------------------------- reading (runs under the reader Python)

def _people_ids(tracks, centers, frame_no, max_jump=0.12):
    """The same person keeps the same number across frames: nearest hip centre to where each one was last seen."""
    ids, free = [None] * len(centers), dict(tracks)
    for i, c in sorted(enumerate(centers), key=lambda x: x[1][0]):
        best = min(free.items(), key=lambda kv: math.dist(kv[1][0], c), default=None)
        if best and math.dist(best[1][0], c) < max_jump and frame_no - best[1][1] < 16:
            ids[i] = best[0]
            free.pop(best[0])
        else:
            ids[i] = max(list(tracks) + [-1]) + 1
        tracks[ids[i]] = (c, frame_no)
    return ids


def _crop(rgb, box, pad=0.12):
    """A person's box with room around it, in pixels, kept inside the frame."""
    H, W = rgb.shape[:2]
    x, y, w, h = box
    x0, y0 = max(0, int(x - w * pad)), max(0, int(y - h * pad * 0.6))
    x1, y1 = min(W, int(x + w * (1 + pad))), min(H, int(y + h * (1 + pad * 0.6)))
    return x0, y0, x1, y1


def read_local(small, fps, people):
    """Each person found first (a person detector), then read alone: body and face inside that person's box; hands on
    the whole frame, given to the nearest wrist. MediaPipe's pose reader on a whole frame finds one person and blends
    neighbours together; one box at a time it reads crowded line-ups."""
    import cv2
    import numpy as np
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python import vision as V
    IMG, VID = V.RunningMode.IMAGE, V.RunningMode.VIDEO
    det = V.ObjectDetector.create_from_options(V.ObjectDetectorOptions(
        base_options=BaseOptions(model_asset_path=model("person")), running_mode=VID, score_threshold=0.3,
        category_allowlist=["person"], max_results=people * 2))
    pose = V.PoseLandmarker.create_from_options(V.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model("pose")), running_mode=IMG, num_poses=1,
        min_pose_detection_confidence=0.3, min_pose_presence_confidence=0.3))
    hand = V.HandLandmarker.create_from_options(V.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model("hand")), running_mode=VID, num_hands=people * 2,
        min_hand_detection_confidence=0.35, min_hand_presence_confidence=0.35))
    face = V.FaceLandmarker.create_from_options(V.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model("face")), running_mode=IMG, num_faces=1,
        min_face_detection_confidence=0.3))
    cap = cv2.VideoCapture(str(small))
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames, tracks, prev, cam, k = [], {}, None, [], 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        rgb = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        ms = int(k * 1000 / fps)
        boxes = [d.bounding_box for d in det.detect_for_video(img, ms).detections]
        boxes = sorted(boxes, key=lambda b: -b.width * b.height)[:people]
        bodies = []
        if not boxes:
            boxes = _unseen_people(pose, rgb, people, W, H)   # stand-in figures (a 3D blocking) the person finder misses
        for b in boxes:
            x0, y0, x1, y1 = _crop(rgb, (b.origin_x, b.origin_y, b.width, b.height))
            if x1 - x0 < 24 or y1 - y0 < 48:
                continue
            sub = np.ascontiguousarray(rgb[y0:y1, x0:x1])
            pr = pose.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=sub))
            if not pr.pose_landmarks:
                continue
            cw, ch = x1 - x0, y1 - y0
            p33 = [[round((x0 + p.x * cw) / W, 4), round((y0 + p.y * ch) / H, 4), round(p.visibility, 2)] for p in pr.pose_landmarks[0]]
            op = []
            for j in OP18:
                if j is None:
                    a, c = p33[11], p33[12]
                    op.append([round((a[0] + c[0]) / 2, 4), round((a[1] + c[1]) / 2, 4), min(a[2], c[2])])
                else:
                    op.append(p33[j])
            body = {"body": op, "body33": p33, "hands": [], "face": [],
                    "box": [round(x0 / W, 4), round(y0 / H, 4), round(cw / W, 4), round(ch / H, 4)]}
            # not a person (a bottle, an arm on its own): the head and shoulders must read clearly
            core = [p33[j][2] for j in (0, 11, 12)]
            if min(core) < 0.5 or ch < H * 0.15:
                continue
            # a hand or an arm read as a whole tiny person: a real one fills a good part of its own box
            seen = [q for q in pr.pose_landmarks[0] if q.visibility > 0.5]
            if max(q.y for q in seen) - min(q.y for q in seen) < 0.35 and max(q.x for q in seen) - min(q.x for q in seen) < 0.35:
                continue
            if math.dist(p33[11][:2], p33[12][:2]) < 0.035 and math.dist(p33[0][:2], op[1][:2]) < 0.03:
                continue
            # the same person read twice (two overlapping boxes): keep the first, the larger box
            if any(math.dist(body["body"][1][:2], o["body"][1][:2]) < 0.05 or math.dist(body["body"][0][:2], o["body"][0][:2]) < 0.04
                   for o in bodies):
                continue
            hy1 = y0 + int(ch * 0.45)
            fsub = np.ascontiguousarray(rgb[y0:hy1, x0:x1])
            fr = face.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=fsub))
            if fr.face_landmarks:
                lms, fh = fr.face_landmarks[0], hy1 - y0
                body["face"] = [[round((x0 + lms[j].x * cw) / W, 4), round((y0 + lms[j].y * fh) / H, 4)] for j in FACE_KEEP if j < len(lms)]
            bodies.append(body)
        centers = [tuple(b["body"][1][:2]) for b in bodies]      # the neck: a line-up is often cut off at the waist
        for b, i in zip(bodies, _people_ids(tracks, centers, k)):
            b["id"] = i
        hr = hand.detect_for_video(img, ms)
        for lms, side in zip(hr.hand_landmarks, hr.handedness):
            pts = [[round(p.x, 4), round(p.y, 4)] for p in lms]
            owner = min(bodies, key=lambda b: min(math.dist(pts[0], b["body33"][15][:2]), math.dist(pts[0], b["body33"][16][:2])), default=None)
            if owner is not None and min(math.dist(pts[0], owner["body33"][15][:2]), math.dist(pts[0], owner["body33"][16][:2])) < 0.12:
                owner["hands"].append({"side": side[0].category_name.lower(), "points": pts})
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        cam.append(_camera_step(cv2, prev, gray, bodies, W, H))
        prev = gray
        frames.append({"t": round(k / fps, 3), "people": sorted(bodies, key=lambda b: b["id"])})
        k += 1
    _steady(frames)
    return {"width": W, "height": H, "frames": frames}, cam


class _Box:
    def __init__(self, x, y, w, h):
        self.origin_x, self.origin_y, self.width, self.height = x, y, w, h


def _unseen_people(pose, rgb, people, W, H):
    """Boxes found by the pose reader itself on the whole frame, one person at a time: each one found is painted over
    so the next read finds the next person."""
    import numpy as np
    import mediapipe as mp
    work, boxes = rgb.copy(), []
    fill = rgb.reshape(-1, 3).mean(axis=0).astype(np.uint8)
    for _ in range(people):
        r = pose.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(work)))
        if not r.pose_landmarks:
            break
        lm = r.pose_landmarks[0]
        if min(lm[j].visibility for j in (0, 11, 12)) < 0.6:
            break
        xs = [q.x for q in lm if q.visibility > 0.3]
        ys = [q.y for q in lm if q.visibility > 0.3]
        x0, x1 = max(0.0, min(xs) - 0.03), min(1.0, max(xs) + 0.03)
        y0, y1 = max(0.0, min(ys) - 0.08), min(1.0, max(ys) + 0.03)
        boxes.append(_Box(x0 * W, y0 * H, (x1 - x0) * W, (y1 - y0) * H))
        work[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)] = fill
    return boxes


def _steady(frames, keep=0.5):
    """Each person's points eased against the last frame they were seen in, so a read frame by frame does not jitter."""
    last = {}
    for f in frames:
        for p in f["people"]:
            was = last.get(p["id"])
            if was is not None:
                for key in ("body", "body33"):
                    p[key] = [[round(keep * a[0] + (1 - keep) * b[0], 4), round(keep * a[1] + (1 - keep) * b[1], 4), a[2]]
                              if a[2] > 0.3 and b[2] > 0.3 else a for a, b in zip(p[key], was[key])]
            last[p["id"]] = p


def _camera_step(cv2, prev, gray, bodies, W, H):
    """The background's movement between two frames, people masked out: (dx, dy, scale, roll) of the camera."""
    import numpy as np
    if prev is None:
        return [0.0, 0.0, 1.0, 0.0, 0]
    h1, h2 = (cv2.calcHist([g], [0], None, [32], [0, 256]) for g in (prev, gray))
    if cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL) < 0.6:          # a cut: the camera starts again, nothing carried over
        return [0.0, 0.0, 1.0, 0.0, -1]
    mask = np.full(gray.shape, 255, np.uint8)
    for b in bodies:
        x0, y0, bw, bh = b["box"]
        mask[max(0, int(y0 * H)):int((y0 + bh) * H), max(0, int(x0 * W)):int((x0 + bw) * W)] = 0
    pts = cv2.goodFeaturesToTrack(prev, maxCorners=500, qualityLevel=0.01, minDistance=7, mask=mask)
    if pts is None or len(pts) < 12:
        return [0.0, 0.0, 1.0, 0.0, 0]
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, gray, pts, None)
    good = st.reshape(-1) == 1
    if good.sum() < 12:
        return [0.0, 0.0, 1.0, 0.0, int(good.sum())]
    M, inl = cv2.estimateAffinePartial2D(pts[good], nxt[good], method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if M is None or inl is None or inl.sum() < 25:      # too little background left to trust: count the camera as still
        return [0.0, 0.0, 1.0, 0.0, 0 if inl is None else int(inl.sum())]
    s = math.hypot(M[0, 0], M[1, 0])
    # the background moving left means the camera turned right: the camera's move is the opposite of the picture's
    return [round(-M[0, 2] / W, 5), round(-M[1, 2] / H, 5), round(s or 1.0, 5),
            round(-math.degrees(math.atan2(M[1, 0], M[0, 0])), 3), int(inl.sum()) if inl is not None else 0]


def camera_path(steps, fps):
    x = y = roll = 0.0
    z = 1.0
    path, cuts = [], []
    for i, (dx, dy, s, r, n) in enumerate(steps):
        if n == -1:
            cuts.append(round(i / fps, 3))
            x = y = roll = 0.0
            z = 1.0
        x, y, z, roll = x + dx, y + dy, z * s, roll + r
        path.append({"t": round(i / fps, 3), "pan_x": round(x, 4), "pan_y": round(y, 4), "zoom": round(z, 4),
                     "roll": round(roll, 2), "points": n, "cut": n == -1})
    if not path:
        return {"frames": [], "summary": "no frames"}
    # handheld shake: what is left of the movement after a one-second smoothing
    w = max(1, int(fps))

    def smooth(v, i):
        part = v[max(0, i - w // 2):i + w // 2 + 1]
        return sum(part) / len(part)
    xs, ys = [p["pan_x"] for p in path], [p["pan_y"] for p in path]
    shake = (sum((xs[i] - smooth(xs, i)) ** 2 + (ys[i] - smooth(ys, i)) ** 2 for i in range(len(path))) / len(path)) ** 0.5
    end = path[-1]
    words = []
    if abs(end["pan_x"]) > 0.03:
        words.append(f"pans {'right' if end['pan_x'] > 0 else 'left'} {abs(end['pan_x']) * 100:.0f}% of the frame")
    if abs(end["pan_y"]) > 0.03:
        words.append(f"tilts {'down' if end['pan_y'] > 0 else 'up'} {abs(end['pan_y']) * 100:.0f}%")
    if abs(end["zoom"] - 1) > 0.04:
        words.append(f"pushes {'in' if end['zoom'] > 1 else 'out'} {abs(end['zoom'] - 1) * 100:.0f}%")
    if abs(end["roll"]) > 2:
        words.append(f"rolls {end['roll']:.0f}°")
    words.append("handheld shake " + ("strong" if shake > 0.01 else "light" if shake > 0.003 else "none (locked off)"))
    if cuts:
        words.insert(0, f"{len(cuts)} cut{'s' if len(cuts) > 1 else ''} (at {', '.join(f'{c:.1f}' for c in cuts[:6])} s); since the last cut")
    return {"frames": path, "cuts": cuts, "shake": round(shake, 5), "summary": ", ".join(words) or "still"}


def draw(track, cam, small, out_dir, fps):
    """skeleton.mp4 (black), overlay.mp4 (over the clip, camera path in the corner) and sheet.jpg."""
    import cv2
    import numpy as np
    W, H = track["width"], track["height"]
    pw = PREVIEW_W
    ph = int(round(H * pw / W / 2) * 2)
    sk = cv2.VideoWriter(str(out_dir / "skeleton.raw.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    ov = cv2.VideoWriter(str(out_dir / "overlay.raw.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (pw, ph))
    cap = cv2.VideoCapture(str(small)) if small and Path(small).exists() else None
    stick = max(2, int(W / 180))
    stills = []
    for i, fr in enumerate(track["frames"]):
        ok, bgr = cap.read() if cap is not None else (False, None)
        if not ok:
            if cap is not None and not track.get("exact"):
                break
            bgr = np.full((H, W, 3), 38, np.uint8)        # skeletons only: no picture behind them
        canvas = np.zeros((H, W, 3), np.uint8)
        for p in fr["people"]:
            pts = [(int(x * W), int(y * H), c) for x, y, c in p["body"]]
            for n, (a, b) in enumerate(LIMBS):
                if pts[a][2] > 0.3 and pts[b][2] > 0.3:
                    c = COLORS[n][::-1]
                    (x1, y1, _), (x2, y2, _) = pts[a], pts[b]
                    L = math.hypot(x2 - x1, y2 - y1)
                    ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
                    poly = cv2.ellipse2Poly(((x1 + x2) // 2, (y1 + y2) // 2), (int(L / 2), stick), int(ang), 0, 360, 1)
                    cv2.fillConvexPoly(canvas, poly, tuple(int(v * 0.6) for v in c))
            for n, (x, y, c) in enumerate(pts):
                if c > 0.3:
                    cv2.circle(canvas, (x, y), stick + 1, COLORS[n][::-1], -1)
            for h in p["hands"]:
                hp = [(int(x * W), int(y * H)) for x, y in h["points"]]
                for n, (a, b) in enumerate(HAND_EDGES):
                    hsv = np.uint8([[[int(n / len(HAND_EDGES) * 179), 255, 255]]])
                    cv2.line(canvas, hp[a], hp[b], tuple(int(v) for v in cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]), max(1, stick // 2))
                for q in hp:
                    cv2.circle(canvas, q, max(1, stick // 2), (255, 0, 0), -1)
            for x, y in p["face"]:
                cv2.circle(canvas, (int(x * W), int(y * H)), max(1, stick // 3), (255, 255, 255), -1)
            if pts[0][2] > 0.3 or pts[1][2] > 0.3:
                at = pts[0] if pts[0][2] > 0.3 else pts[1]
                cv2.putText(canvas, str(p.get("name") or p["id"] + 1), (at[0] + 8, at[1] - 12), cv2.FONT_HERSHEY_SIMPLEX, W / 900, (255, 255, 255), 2)
        sk.write(canvas)
        small_bg = cv2.resize((bgr * 0.45).astype(np.uint8), (pw, ph))
        mixed = np.where(cv2.resize(canvas, (pw, ph)).sum(axis=2, keepdims=True) > 30, cv2.resize(canvas, (pw, ph)), small_bg)
        _corner(cv2, mixed, cam["frames"][: i + 1], pw, ph)
        cv2.putText(mixed, f"{fr['t']:.1f}s  {len(fr['people'])} people", (8, ph - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        ov.write(mixed)
        stills.append(mixed)
    sk.release()
    ov.release()
    for name in ("skeleton", "overlay"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out_dir / f"{name}.raw.mp4"), "-c:v", "libx264", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_dir / f"{name}.mp4")], check=True)
        (out_dir / f"{name}.raw.mp4").unlink()
    if stills:
        pick = [stills[min(len(stills) - 1, int(j * (len(stills) - 1) / 5))] for j in range(6)]
        cv2.imwrite(str(out_dir / "sheet.jpg"), np.hstack(pick), [cv2.IMWRITE_JPEG_QUALITY, 82])


def _corner(cv2, img, path, pw, ph):
    """The camera's path so far in the top-right corner: a frame box that drifts, grows (push in) and turns."""
    box = int(pw * 0.26)
    x0, y0 = pw - box - 8, 8
    cv2.rectangle(img, (x0, y0), (x0 + box, y0 + int(box * 1.3)), (60, 60, 60), -1)
    cx, cy, k = x0 + box // 2, y0 + int(box * 0.65), box * 0.9
    trail = [(int(cx + p["pan_x"] * k), int(cy + p["pan_y"] * k)) for p in path]
    for a, b in zip(trail, trail[1:]):
        cv2.line(img, a, b, (90, 200, 150), 1)
    if path:
        p = path[-1]
        w, h = box * 0.32 / p["zoom"], box * 0.42 / p["zoom"]
        rect = ((trail[-1][0], trail[-1][1]), (w, h), p["roll"])
        pts = cv2.boxPoints(rect).astype(int)
        cv2.polylines(img, [pts], True, (255, 255, 255), 1)
    cv2.putText(img, "camera", (x0 + 4, y0 + int(box * 1.3) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (200, 200, 200), 1)


def read_fal(small, fps, out_dir):
    """fal's DWPose, one call per frame: a skeleton image back per frame (no keypoints), joined into skeleton.mp4."""
    import take as T
    frames_dir = out_dir / "fal-frames"
    frames_dir.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(small), str(frames_dir / "in-%04d.png")], check=True)
    ins = sorted(frames_dir.glob("in-*.png"))

    def one(f):
        done = frames_dir / f.name.replace("in-", "pose-")
        if done.exists():
            return
        _, res = T._fal(FAL_DWPOSE, {"image_url": [str(f)], "draw_mode": "full-pose"})
        url = (res.get("image") or {}).get("url")
        if not url:
            raise SystemExit(f"fal DWPose answered with no image: {str(res)[:200]}")
        urllib.request.urlretrieve(url, done)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(int(os.environ.get("MOTION_FAL_AT_ONCE") or 16)) as pool:
        list(pool.map(one, ins))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(frames_dir / "pose-%04d.png"),
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(out_dir / "skeleton.mp4")], check=True)
    return len(ins), round(len(ins) * FAL_DWPOSE_USD, 4)


def _read(small, out_dir, fps, people):
    """Runs under the reader Python: pose.json, camera.json and the previews."""
    track, steps = read_local(small, fps, people)
    cam = camera_path(steps, fps)
    track["fps"] = fps
    (out_dir / "pose.json").write_text(json.dumps(track, separators=(",", ":")))
    (out_dir / "camera.json").write_text(json.dumps(cam, indent=0))
    draw(track, cam, small, out_dir, fps)
    ids = {p["id"] for f in track["frames"] for p in f["people"]}
    seen = [len(f["people"]) for f in track["frames"]]
    hands = sum(len(p["hands"]) for f in track["frames"] for p in f["people"])
    faces = sum(1 for f in track["frames"] for p in f["people"] if p["face"])
    return {"frames": len(seen), "people_max": max(seen or [0]), "people_ids": len(ids),
            "frames_with_people": sum(1 for s in seen if s), "hands_seen": hands, "faces_seen": faces,
            "camera": cam["summary"]}


def _draw(blk, clip, out_dir):
    """Runs under the reader Python: the exact skeletons written by Blender, drawn into the previews."""
    track = json.loads((blk / "pose.json").read_text())
    cam = camera_path(json.loads((blk / "camera-steps.json").read_text())["steps"], track["fps"])
    (out_dir / "pose.json").write_text(json.dumps(track, separators=(",", ":")))
    (out_dir / "camera.json").write_text(json.dumps(cam, indent=0))
    draw(track, cam, clip, out_dir, track["fps"])
    seen = [len(f["people"]) for f in track["frames"]]
    return {"frames": len(seen), "people_max": max(seen or [0]), "people_ids": len(track.get("names") or []),
            "frames_with_people": sum(1 for x in seen if x), "hands_seen": sum(2 * x for x in seen), "faces_seen": 0,
            "camera": cam["summary"], "exact": True}


# ---------------------------------------------------------------- the commands

def track(clip, out_dir, start=0.0, end=None, fps=16, people=6, engine="local", kind=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    small = out_dir / "read.mp4"
    cut(clip, small, float(start or 0), float(end) if end else None, fps)
    rec = {"source": str(clip), "from": float(start or 0), "to": float(end) if end else round(seconds_of(clip), 3),
           "kind": kind, "fps": fps, "engine": engine, "status": "tracked", "tracked_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if engine == "fal":
        n, usd = read_fal(small, fps, out_dir)
        rec.update({"frames": n, "cost_usd": usd, "files": {"skeleton": "skeleton.mp4"}})
    else:
        py = reader_python()
        r = subprocess.run([py, str(Path(__file__).resolve()), "_read", str(small), str(out_dir), str(fps), str(people)],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("the motion reader failed: " + (r.stderr or r.stdout)[-600:])
        rec.update(json.loads(r.stdout.strip().splitlines()[-1]))
        rec.update({"cost_usd": 0.0, "files": {"pose": "pose.json", "skeleton": "skeleton.mp4", "overlay": "overlay.mp4",
                                              "camera": "camera.json", "sheet": "sheet.jpg"}})
    rec["seconds_to_read"] = round(time.time() - t0, 1)
    rec["take_motion"] = {"source": rec["source"], "from": rec["from"], "to": rec["to"], "approved": False,
                          "skeleton": str(out_dir / "skeleton.mp4")}
    (out_dir / "motion.json").write_text(json.dumps(rec, indent=1))
    return rec


def scene(scene_dir, clip, start=0.0, end=None, kind="phone", engine="local", fps=16, people=6, name=None):
    """A clip becomes the scene's motion: copied into <scene>/motion/, tracked there, waiting for approval."""
    d = Path(scene_dir) / "motion"
    d.mkdir(parents=True, exist_ok=True)
    src = d / ("source" + (Path(clip).suffix.lower() or ".mp4"))
    if Path(clip).resolve() != src.resolve():
        shutil.copyfile(clip, src)
    rec = track(src, d, start, end, fps, people, engine, kind)
    rec["original"] = name or Path(clip).name
    (d / "motion.json").write_text(json.dumps(rec, indent=1))
    return rec


def approve(scene_dir, by=None):
    f = Path(scene_dir) / "motion" / "motion.json"
    rec = json.loads(f.read_text())
    rec.update({"status": "approved", "approved_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "approved_by": by})
    rec["take_motion"]["approved"] = True
    f.write_text(json.dumps(rec, indent=1))
    return rec


def blender():
    for c in (os.environ.get("MOTION_BLENDER"), shutil.which("blender"), "/Applications/Blender.app/Contents/MacOS/Blender"):
        if c and os.path.isfile(c):
            return c
    raise SystemExit("no Blender: set MOTION_BLENDER")


def blocking(spec, out, then_track=False, exact=True, motion_dir=None):
    """A 3D blocking spec rendered headless into a clip at the spec's rate (16 fps by default), with the figures' exact
    skeletons drawn into the previews (`exact`), or read back by the tracker (`then_track`)."""
    out = Path(out)
    blk = out.parent / (out.stem + "-blender")
    shutil.rmtree(blk, ignore_errors=True)
    blk.mkdir(parents=True)
    t0 = time.time()
    r = subprocess.run([blender(), "-b", "--factory-startup", "-P", str(HERE / "blocking_blender.py"), "--", str(spec), str(blk)],
                       capture_output=True, text=True)
    if r.returncode or not (blk / "pose.json").exists():
        raise SystemExit("Blender could not build the blocking: " + (r.stderr or r.stdout)[-800:])
    fps = int(json.loads(Path(spec).read_text()).get("fps") or 16)
    pngs = sorted(blk.glob("f-*.png"))
    if pngs:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-pattern_type", "glob", "-i", str(blk / "f-*.png"),
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], check=True)
    rec = {"clip": str(out) if pngs else None, "frames": len(pngs), "seconds_to_render": round(time.time() - t0, 1)}
    if exact:
        md = Path(motion_dir) if motion_dir else out.parent / (out.stem + "-motion")
        md.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([reader_python(), str(Path(__file__).resolve()), "_draw", str(blk), str(out) if pngs else "", str(md)],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("could not draw the skeletons: " + (r.stderr or r.stdout)[-600:])
        m = {"source": str(out), "from": 0.0, "to": round(seconds_of(out), 3) if pngs else float(json.loads(Path(spec).read_text()).get("seconds") or 0),
             "kind": "3d", "fps": fps, "engine": "blender", "status": "ready", "tracked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "cost_usd": 0.0, "files": {"pose": "pose.json", "skeleton": "skeleton.mp4", "overlay": "overlay.mp4",
                                         "camera": "camera.json", "sheet": "sheet.jpg"}}
        m.update(json.loads(r.stdout.strip().splitlines()[-1]))
        m["seconds_to_read"] = rec["seconds_to_render"]
        m["take_motion"] = {"source": str(out), "from": 0.0, "to": m["to"], "approved": True, "pose": str(md / "skeleton.mp4")}
        (md / "motion.json").write_text(json.dumps(m, indent=1))
        rec["motion"] = m
    if then_track:
        rec["tracked"] = track(out, out.parent / (out.stem + "-tracked"), fps=fps, kind="3d")
    shutil.rmtree(blk, ignore_errors=True)
    return rec


def _arg(argv, name, default=None, cast=str):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "_read":
        print(json.dumps(_read(Path(a[1]), Path(a[2]), int(a[3]), int(a[4]))))
    elif a[0] == "track":
        print(json.dumps(track(a[1], _arg(a, "--out", "motion"), _arg(a, "--from", 0.0, float), _arg(a, "--to", None, float),
                               _arg(a, "--fps", 16, int), _arg(a, "--people", 6, int), _arg(a, "--engine", "local")), indent=1))
    elif a[0] == "scene":
        print(json.dumps(scene(a[1], a[2], _arg(a, "--from", 0.0, float), _arg(a, "--to", None, float), _arg(a, "--kind", "phone"),
                               _arg(a, "--engine", "local"), name=_arg(a, "--name")), indent=1))
    elif a[0] == "_draw":
        print(json.dumps(_draw(Path(a[1]), a[2] or None, Path(a[3]))))
    elif a[0] == "blocking":
        print(json.dumps(blocking(a[1], _arg(a, "--out", "blocking.mp4"), "--track" in a), indent=1))
    elif a[0] == "program":
        import motion_program as MP
        print(json.dumps(MP.program_scene(a[1]) if Path(a[1]).is_dir() else
                         MP.program(json.loads(Path(a[1]).read_text()), _arg(a, "--out", "motion")), indent=1))
    elif a[0] == "approve":
        print(json.dumps(approve(a[1], _arg(a, "--by")), indent=1))
    else:
        sys.exit(__doc__)
