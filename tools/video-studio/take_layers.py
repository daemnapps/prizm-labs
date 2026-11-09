#!/usr/bin/env python3
"""Every layer of a take, read back off the finished clip: each character's face (smile, jaw open, brow raise, eyes),
each character's body (hands up, moving, where they stand), and the camera (pan, tilt, push, shake).

    python3 take_layers.py <take.json> [--clip take.mp4] [--fps 6] [--out layers.json] [--frames frames.jpg]

The take.json `cast` names who is in the take and where to find each one once (ruled 2026-11-09, BRIEF-SPEC rule 8):
  "cast": {"HOST": {"sheet": "sheets/host.png", "seen": [t, x, y]}, ...}     x, y as fractions of the frame
  "cast": {"HOST": "sheets/host.png"}                                        a sheet alone works too
Each character is known by face (SFace likeness against their sheet, or against the face where they were `seen`); a face
that is no one's is left out. Eyes under a blindfold read as closed: their eye values mean nothing.

Faces: YuNet finds them, MediaPipe Face Landmarker reads each (478-point mesh + 52 blendshapes). Bodies: MediaPipe Pose
Landmarker under each face. Camera: the frame-to-frame shift of the whole picture.
The models are fetched once (MediaPipe's model store, OpenCV's model zoo) into ~/.cache/take-layers. Needs `mediapipe`, `opencv`
and `numpy` (any Python with them; the rest of the video studio stays on 3.9). No brand, product or person is named here.
"""
import json
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

MODELS = {
    "face.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
    "pose.task": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    "yunet.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "sface.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}
CACHE = Path.home() / ".cache" / "take-layers"
# the face values shown per character, each the mean of its blendshapes (0 = none, 1 = full)
FACE = {
    "smile": ("mouthSmileLeft", "mouthSmileRight"),
    "jaw_open": ("jawOpen",),
    "brow_raise": ("browInnerUp", "browOuterUpLeft", "browOuterUpRight"),
    "eyes_closed": ("eyeBlinkLeft", "eyeBlinkRight"),
    "frown": ("mouthFrownLeft", "mouthFrownRight", "noseSneerLeft", "noseSneerRight"),
    "lip_bite": ("mouthRollLower", "mouthPressLeft", "mouthPressRight"),
}
SAME = 0.30          # face-likeness (cosine) above which a face is taken as that character


def model(name):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / name
    if not f.exists():
        urllib.request.urlretrieve(MODELS[name], f)
    return str(f)


class Eyes:
    """The four readers: find faces (YuNet), tell faces apart (SFace), read a face (MediaPipe mesh + blendshapes) and
    read a body (MediaPipe pose)."""

    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        self.mp = mp
        self.det = cv2.FaceDetectorYN.create(model("yunet.onnx"), "", (320, 320), 0.6, 0.3, 50)
        self.rec = cv2.FaceRecognizerSF.create(model("sface.onnx"), "")
        self.mesh = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model("face.task")), num_faces=1, output_face_blendshapes=True,
            min_face_detection_confidence=0.2, min_face_presence_confidence=0.2))
        self.pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model("pose.task")), num_poses=3, min_pose_detection_confidence=0.3))

    def img(self, a):
        return self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(cv2.cvtColor(a, cv2.COLOR_BGR2RGB)))

    def faces(self, frame, up=2.0):
        """Every face in the frame: box, likeness vector, and (where the mesh reads it) the face values and mesh."""
        H, W = frame.shape[:2]
        big = cv2.resize(frame, None, fx=up, fy=up)
        self.det.setInputSize((big.shape[1], big.shape[0]))
        _, rows = self.det.detect(big)
        out = []
        for r in (rows if rows is not None else []):
            r = r.copy()
            r[:14] /= up
            x, y, w, h = r[:4]
            if w < W * 0.035:
                continue
            f = {"cx": float(x + w / 2), "cy": float(y + h / 2), "w": float(w), "h": float(h), "score": float(r[14]),
                 "vec": self.rec.feature(self.rec.alignCrop(frame, r)).ravel(), "hair": hair(frame, x, y, w, h)}
            m = 0.6
            x0, y0 = int(max(0, x - m * w)), int(max(0, y - m * h))
            x1, y1 = int(min(W, x + w * (1 + m))), int(min(H, y + h * (1 + m)))
            crop = frame[y0:y1, x0:x1]
            if crop.size:
                s = 256 / max(crop.shape[:2])
                res = self.mesh.detect(self.img(cv2.resize(crop, None, fx=s, fy=s)))
                if res.face_blendshapes:
                    d = {b.category_name: b.score for b in res.face_blendshapes[0]}
                    f["face"] = {k: round(float(np.mean([d[n] for n in v])), 3) for k, v in FACE.items()}
                    f["pts"] = np.array([[p.x * crop.shape[1] + x0, p.y * crop.shape[0] + y0] for p in res.face_landmarks[0]])
            f["body"] = self.body(frame, f)
            out.append(f)
        return out

    def body(self, frame, f):
        """The body under a face (the pose whose nose sits on that face): hands up against the shoulders, arm points."""
        H, W = frame.shape[:2]
        x0, x1 = int(max(0, f["cx"] - 2.6 * f["w"])), int(min(W, f["cx"] + 2.6 * f["w"]))
        y0, y1 = int(max(0, f["cy"] - 1.2 * f["h"])), int(min(H, f["cy"] + 6.5 * f["h"]))
        crop = frame[y0:y1, x0:x1]
        if crop.size == 0:
            return None
        r = self.pose.detect(self.img(crop))
        best = None
        for lm in r.pose_landmarks:
            P = np.array([[p.x * crop.shape[1] + x0, p.y * crop.shape[0] + y0, p.visibility] for p in lm])
            d = np.hypot(*(P[0, :2] - [f["cx"], f["cy"]]))
            mid = (P[11, 0] + P[12, 0]) / 2
            shy = (P[11, 1] + P[12, 1]) / 2
            ear = np.hypot(*(P[7, :2] - P[8, :2]))         # the ears sit about a face apart on the face's own body
            if (d < 0.4 * f["w"] and abs(mid - f["cx"]) < 0.8 * f["w"] and shy > f["cy"] + 0.4 * f["h"]
                    and 0.3 * f["w"] < ear < 1.6 * f["w"] and (best is None or d < best[0])):
                best = (d, P)
        if best is None:
            return None
        P = best[1]
        sh = (P[11, 1] + P[12, 1]) / 2
        up = [bool(P[i, 2] > 0.4 and P[i, 1] < sh) for i in (15, 16)]
        return {"pts": P, "hands_up": sum(up) / 2.0}


def camera(prev, cur):
    """How the whole picture moved between two frames: pan (x), tilt (y) as fractions of the frame, push (scale)."""
    a, b = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY), cv2.cvtColor(cur, cv2.COLOR_BGR2GRAY)
    p0 = cv2.goodFeaturesToTrack(a, 300, 0.01, 8)
    if p0 is None:
        return 0.0, 0.0, 1.0
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None)
    ok = st.ravel() == 1
    if ok.sum() < 12:
        return 0.0, 0.0, 1.0
    m, _ = cv2.estimateAffinePartial2D(p0[ok], p1[ok], method=cv2.RANSAC)
    if m is None:
        return 0.0, 0.0, 1.0
    H, W = a.shape
    return float(m[0, 2] / W), float(m[1, 2] / H), float(np.hypot(m[0, 0], m[1, 0]))


def hair(frame, x, y, w, h):
    """The colour (Lab) of the hair just above a face box: tells apart two faces the likeness can't (a blindfold)."""
    H, W = frame.shape[:2]
    x0, x1 = int(max(0, x + 0.15 * w)), int(min(W, x + 0.85 * w))
    y0, y1 = int(max(0, y - 0.3 * h)), int(max(1, min(H, y + 0.05 * h)))
    p = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32) if y1 > y0 and x1 > x0 else []
    return np.median(p, 0) if len(p) else np.array([128.0, 128, 128])


def _cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def like(f, refs):
    """How alike a face is to a character's references: face likeness, less a hair-colour difference."""
    return max(_cos(f["vec"], g["vec"]) - float(np.linalg.norm(f["hair"] - g["hair"])) / 250.0 for g in refs)


def read(take, clip=None, fps=6.0, frames_out=None, base=None):
    """Read every layer off a take. Each character is known by face: from their character sheet (`cast` NAME `sheet`),
    or from one place they were `seen` in the take ([t, x, y], fractions of the frame)."""
    clip = clip or take["out"]
    base = Path(base or ".")
    cast = {n: (c if isinstance(c, dict) else {"sheet": c}) for n, c in (take.get("cast") or {}).items()}
    if not cast:
        raise SystemExit("take.json needs a `cast`: each character with a `sheet` picture or a `seen` point [t, x, y]")
    eyes = Eyes()
    gallery = {}
    for n, c in cast.items():                      # sheets first: the largest face on the sheet is that character
        if c.get("sheet") and not c.get("seen"):
            im = cv2.imread(str(base / c["sheet"]))
            fs = eyes.faces(im) if im is not None else []
            if fs:
                gallery[n] = [max(fs, key=lambda f: f["w"])]
    cap = cv2.VideoCapture(str(clip))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 24
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    step = max(1, int(round(src_fps / fps)))
    samples, prev = [], None
    for i in range(0, n, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if not ok:
            break
        t = i / src_fps
        fs = eyes.faces(fr)
        for name, c in cast.items():               # a `seen` point: the face nearest it, at that time
            if c.get("seen") and name not in gallery and abs(t - c["seen"][0]) <= step / src_fps / 2 + 1e-6:
                near = min(fs, key=lambda f: np.hypot(f["cx"] / W - c["seen"][1], f["cy"] / H - c["seen"][2]), default=None)
                if near is not None:
                    gallery[name] = [near]
        cam = camera(prev, fr) if prev is not None else (0.0, 0.0, 1.0)
        prev = fr
        samples.append({"t": round(t, 2), "faces": fs, "cam": cam, "frame": fr if frames_out else None})
    missing = [k for k in cast if k not in gallery]
    if missing:
        raise SystemExit(f"could not find these characters' faces (sheet or seen point): {missing}")
    names = list(cast)
    for _ in range(2):                             # two passes: the second uses every confident match as a reference too
        grown = {k: list(v[:1]) for k, v in gallery.items()}
        last = {}
        for s in samples:
            fs, s["who"] = s["faces"], []

            def near(f, k):                        # still where they were a moment ago: more likely the same person
                if k not in last or s["t"] - last[k][0] > 0.7:
                    return 0.0
                return 0.25 * max(0.0, 1 - np.hypot(f["cx"] - last[k][1], f["cy"] - last[k][2]) / (0.6 * f["w"]))
            pairs = sorted(((like(f, gallery[k]) + near(f, k), fi, k) for fi, f in enumerate(fs) for k in names), reverse=True)
            used_f, used_k = set(), set()
            for sim, fi, k in pairs:
                if sim < SAME or fi in used_f or k in used_k:
                    continue
                used_f.add(fi)
                used_k.add(k)
                s["who"].append((k, fi))
                last[k] = (s["t"], fs[fi]["cx"], fs[fi]["cy"])
                if sim > SAME + 0.15 and len(grown[k]) < 40:
                    grown[k].append(fs[fi])
        gallery = grown
    tracks = {k: [] for k in names}
    prev_b = {}
    for s in samples:
        for name, fi in s["who"]:
            f = s["faces"][fi]
            row = {"t": s["t"], "x": round(f["cx"] / W, 3), "y": round(f["cy"] / H, 3), "size": round(f["w"] / W, 3)}
            row.update(f.get("face") or {})
            b = f["body"]
            if b is not None:
                pts = b["pts"][[11, 12, 13, 14, 15, 16], :2]
                # moving: how far the arms and shoulders moved since the last sample, less the camera's own move,
                # in shoulder widths per second
                sw = max(8.0, abs(b["pts"][11, 0] - b["pts"][12, 0]))
                if name in prev_b and s["t"] - prev_b[name][0] < 1.0:
                    pt, pp = prev_b[name]
                    shift = np.array([s["cam"][0] * W, s["cam"][1] * H])
                    mv = float(np.median(np.linalg.norm(pts - pp - shift, axis=1)) / sw / max(1e-3, s["t"] - pt))
                    row["moving"] = round(min(3.0, mv), 3)
                prev_b[name] = (s["t"], pts)
                row["hands_up"] = b["hands_up"]
            tracks[name].append(row)
    cam = [{"t": s["t"], "pan": round(s["cam"][0], 4), "tilt": round(s["cam"][1], 4), "push": round(s["cam"][2] - 1, 4)}
           for s in samples]
    out = {"clip": str(clip), "fps": fps, "size": [W, H], "seconds": round(n / src_fps, 2), "cast": names,
           "tracks": tracks, "camera": cam,
           "found": {k: round(len(v) / max(1, len(samples)), 2) for k, v in tracks.items()},
           "note": "face values 0-1 from MediaPipe blendshapes; moving in shoulder widths per second; camera per sample"}
    if frames_out:
        draw_frames(samples, names, frames_out)
    return out


COLOURS = [(215, 91, 43), (46, 56, 180), (77, 168, 31), (31, 121, 183), (160, 60, 160), (40, 160, 160), (90, 90, 90)]


def draw_frames(samples, names, out, every=3.0, width=1600):
    """A strip of frames with each character's face mesh and skeleton drawn in their own colour."""
    picks, nxt = [], 0.0
    for s in samples:
        if s["t"] >= nxt and len(s.get("who") or []) >= 2:
            picks.append(s)
            nxt = s["t"] + every
    tiles = []
    for s in picks:
        fr = s["frame"].copy()
        for name, fi in s["who"]:
            c = COLOURS[names.index(name) % len(COLOURS)]
            f = s["faces"][fi]
            for x, y in (f["pts"][::3] if "pts" in f else []):
                cv2.circle(fr, (int(x), int(y)), 1, c, -1)
            b = f.get("body")
            if b is not None:
                P = b["pts"]
                for a, z in [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24)]:
                    if P[a, 2] > 0.4 and P[z, 2] > 0.4:
                        cv2.line(fr, (int(P[a, 0]), int(P[a, 1])), (int(P[z, 0]), int(P[z, 1])), c, 3)
            cv2.rectangle(fr, (int(f["cx"] - f["w"] / 2), int(f["cy"] - f["h"] / 2)), (int(f["cx"] + f["w"] / 2), int(f["cy"] + f["h"] / 2)), c, 2)
            cv2.putText(fr, name, (int(f["cx"] - f["w"] / 2), int(f["cy"] - f["h"] / 2) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, c, 2)
        cv2.putText(fr, f"{s['t']:.0f}s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        tiles.append(fr)
    if not tiles:
        return
    h = min(t.shape[0] for t in tiles)
    strip = np.hstack([cv2.resize(t, (int(t.shape[1] * h / t.shape[0]), h)) for t in tiles])
    s = width / strip.shape[1]
    cv2.imwrite(str(out), cv2.resize(strip, None, fx=s, fy=s), [cv2.IMWRITE_JPEG_QUALITY, 82])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    a = sys.argv[1:]

    def opt(k, d=None):
        return a[a.index(k) + 1] if k in a else d
    tk = json.loads(Path(a[0]).read_text())
    res = read(tk, clip=opt("--clip"), fps=float(opt("--fps", 6)), frames_out=opt("--frames"), base=Path(a[0]).parent)
    o = opt("--out") or str(Path(opt("--clip") or tk["out"]).with_suffix(".layers.json"))
    Path(o).write_text(json.dumps(res))
    print(json.dumps({"layers": o, "found": res["found"], "seconds": res["seconds"]}))
