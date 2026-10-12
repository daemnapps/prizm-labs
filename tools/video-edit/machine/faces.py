#!/usr/bin/env python3
"""faces.py — where the face is, frame by frame, so text never sits on it.

    attach(sheet, root, fps=5) -> sheet      picture[i].face_track = [{t, x, y, w, h}] on the FINAL clock (% of frame)
    python3 machine/faces.py track <video> [--from s] [--seconds s] [--fps 5]   (helpers venv → JSON)

MediaPipe (Apache-2.0) Face Detector, the BlazeFace short-range model
(looks/models/blaze_face_short_range.tflite, Apache-2.0), run in the helpers venv on
frames ffmpeg pulls from the part of the clip the cut actually uses. placement.py reads
`face_track` before `subject_box`: a text layer is kept off the face boxes seen WHILE it
is on screen (not the whole scene's union). No venv → nothing is attached, placement
falls back to production's subject_box, then to face-blind (a WARN).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
sys.path.insert(0, str(HERE))
MODEL = TOOL / "looks/models/blaze_face_short_range.tflite"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"
TRACKED_KINDS = (None, "talking", "broll", "greenscreen")


def track_here(video: str, t0: float = 0.0, seconds: float | None = None, fps: float = 5.0, w: int = 360) -> dict:
    """Run inside the venv. Boxes in % of the frame, t in SOURCE seconds."""
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks.python import BaseOptions, vision
    if not MODEL.exists():
        import urllib.request
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        MODEL.write_bytes(urllib.request.urlopen(MODEL_URL, timeout=60).read())
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", video],
                           capture_output=True, text=True, check=True).stdout.strip().split(",")
    W0, H0 = int(probe[0]), int(probe[1])
    h = int(round(w * H0 / W0 / 2) * 2)
    cmd = ["ffmpeg", "-v", "error", "-ss", str(t0), "-i", video] + (["-t", str(seconds)] if seconds else []) + \
          ["-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    size = w * h * 3
    det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL), delegate=BaseOptions.Delegate.CPU), min_detection_confidence=0.5))
    boxes, n = [], len(raw) // size
    for i in range(n):
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.frombuffer(raw[i * size:(i + 1) * size], dtype=np.uint8).reshape(h, w, 3).copy())
        for d in det.detect(img).detections:
            b = d.bounding_box
            boxes.append({"t": round(t0 + i / fps, 3), "x": round(100 * b.origin_x / w, 2), "y": round(100 * b.origin_y / h, 2),
                          "w": round(100 * b.width / w, 2), "h": round(100 * b.height / h, 2),
                          "score": round(float(d.categories[0].score), 3) if d.categories else None})
    return {"frames": n, "fps": fps, "boxes": boxes, "size": [W0, H0], "by": f"mediapipe {mp.__version__} face detector (blaze_face_short_range)"}


def track(video: Path, t0: float, seconds: float, fps: float = 5.0) -> dict:
    import helpers
    return helpers.call("faces.py", "track", str(video), "--from", str(t0), "--seconds", str(seconds), "--fps", str(fps), timeout=600)


def attach(sheet: dict, root: Path, fps: float = 5.0) -> list[str]:
    """Track every clip a person can be in; returns notes (what was tracked, what fell back)."""
    notes, cache = [], {}
    for c in sheet.get("picture") or []:
        if c.get("kind") not in TRACKED_KINDS or c.get("still"):
            continue
        src = Path(c["src"]) if Path(c["src"]).is_absolute() else Path(root) / c["src"]
        if not src.is_file() or src.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        key = (str(src), c.get("source_start", 0), c["duration"])
        try:
            got = cache.get(key) or track(src, c.get("source_start", 0), c["duration"], fps)
        except Exception as e:
            notes.append(f"face tracking not run for {c['id']} ({type(e).__name__}: {str(e)[:120]}) — placement uses subject_box or is face-blind")
            continue
        cache[key] = got
        off = c["start"] - c.get("source_start", 0)
        c["face_track"] = [{**{k: b[k] for k in ("x", "y", "w", "h")}, "t": round(b["t"] + off, 3)} for b in got["boxes"]]
        if c.get("kind") == "greenscreen":  # the presenter is drawn smaller (cut-out) or in a card (pip): boxes onto the FRAME
            import placement as P
            meta = sheet.get("meta") or {}
            size = got.get("size") or [None, None]
            rect = P.presenter_rect((c.get("greenscreen") or {}).get("layout", "pip"), (size[0] / size[1]) if size[0] else None,
                                    meta.get("width", 1080), meta.get("height", 1920))
            c["face_track"] = [m for m in (P.to_frame(b, rect) for b in c["face_track"]) if m]
            c["face_track_space"] = f"frame — mapped through the {(c.get('greenscreen') or {}).get('layout', 'pip')} layout"
        c["face_track_frames"] = got["frames"]
        c["face_track_fps"] = got["fps"]
        c["face_track_by"] = got["by"]
        notes.append(f"faces: {c['id']} — {len(got['boxes'])} face box(es) over {got['frames']} frame(s)"
                     + ("" if got["boxes"] else " — no face found, so production's subject_box (or face-blind) stands"))
    return notes


if __name__ == "__main__":
    if sys.argv[1:2] == ["track"]:
        import argparse
        ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("video")
        ap.add_argument("--from", dest="t0", type=float, default=0.0); ap.add_argument("--seconds", type=float); ap.add_argument("--fps", type=float, default=5.0)
        a = ap.parse_args()
        print(json.dumps(track_here(a.video, a.t0, a.seconds, a.fps)))
    else:
        print(__doc__)
