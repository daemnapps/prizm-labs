"""CLIP QC — a made clip checked frame by frame against what it had to be
(the owner 2026-10-02: "going frame by frame … the most realistic-looking UGC").

  framing   the face's size and place over the first half-second against the
            approved start picture — a zoom or re-staging shows here
  camera    how much the frame moves, second by second, against the swipe's own
            footage of the moment — a locked frame on a handheld selfie shows here
  lips      how open the mouth is each frame against the loudness of the voice
            (best match within ±0.33 s) — lips that don't follow the line show here;
            and the mouth moving where the voice is silent
  sheet     eight frames side by side with the start picture, for the eye

    python3 clip_qc.py <clip.mp4> --picture <start.png> [--voice <line.mp3>] [--swipe <swipe.mp4>] [--sheet out.jpg]
Brand-agnostic; macOS Vision (vision/mouth.swift) + ffmpeg.
"""
from __future__ import annotations

import argparse, json, math, subprocess, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 12
# lip score calibration, Nova Section 1, 2 Oct: the real swipe footage scored 0.39,
# a model clip speaking its OWN audio (lips in sync by construction) 0.23, model clips
# driven by our voice 0.14-0.20. A rough signal: it ranks clips; the eye decides.
LIPS_OK = 0.22
# scene calibration, same day: Omni clips that kept the picture scored 0.08 first frame /
# 0.12-0.15 worst; the zoomed Seedance clip 0.22, the re-staged MiniMax clip 0.20, the clip
# that swapped in the swipe's own creator 0.20-0.24
SCENE_FIRST, SCENE_ANY = 0.15, 0.18


def _mouth_tool():
    b = HERE / "vision" / ".build" / "mouth"
    if not b.exists():
        b.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(HERE / "vision" / "mouth.swift"), "-o", str(b)], check=True)
    return b


def faces(folder) -> list[dict]:
    out = subprocess.run([str(_mouth_tool()), str(folder)], capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        f, x, y, w, h, o = line.split()
        rows.append({"file": f, "x": float(x), "y": float(y), "w": float(w), "h": float(h), "open": float(o)})
    return rows


def frames(video, folder, fps=FPS):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"fps={fps},scale=540:-2",
                    str(Path(folder) / "f%04d.jpg")], check=True)


def loudness(audio, n, fps=FPS):
    """RMS of the voice per video frame (n frames)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    import array
    a = array.array("h", raw); step = int(8000 / fps)
    env = []
    for i in range(n):
        seg = a[i * step:(i + 1) * step]
        env.append(math.sqrt(sum(v * v for v in seg) / len(seg)) if seg else 0.0)
    return env


def _corr(a, b):
    n = min(len(a), len(b))
    if n < 6:
        return 0.0
    a, b = a[:n], b[:n]
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a); vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def movement(rows) -> float:
    """How much the frame moves: mean frame-to-frame shift of the face centre, as a
    share of the frame, per second (a locked camera on a still head is ~0)."""
    pts = [((r["x"] + r["w"] / 2), (r["y"] + r["h"] / 2)) for r in rows if r["open"] >= 0]
    if len(pts) < 3:
        return 0.0
    d = [math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) for i in range(1, len(pts))]
    return round(sum(d) / len(d) * FPS, 4)


def check(clip, picture, voice=None, swipe=None, sheet=None) -> dict:
    with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as p, tempfile.TemporaryDirectory() as s:
        frames(clip, t)
        rows = faces(t)
        from PIL import Image
        Image.open(picture).convert("RGB").resize((540, 960)).save(Path(p) / "pic.jpg")
        pic = (faces(p) or [{}])[0]
        found = [r for r in rows if r["open"] >= 0]
        res = {"frames": len(rows), "face_found": round(len(found) / max(1, len(rows)), 2)}
        head = found[: max(1, FPS // 2)]
        if pic.get("h") and head:
            h = sum(r["h"] for r in head) / len(head)
            cx = sum(r["x"] + r["w"] / 2 for r in head) / len(head)
            res["framing"] = {"face_size_vs_picture": round(h / pic["h"], 2),
                              "face_shift_vs_picture": round(abs(cx - (pic["x"] + pic["w"] / 2)), 3),
                              "ok": 0.85 <= h / pic["h"] <= 1.15 and abs(cx - (pic["x"] + pic["w"] / 2)) < 0.08}
        # still OUR scene, every frame: each frame's difference from the start picture
        # at thumbnail size (a model that swaps in the swipe's own person and place jumps here)
        small = lambda im: list(im.convert("L").resize((36, 64)).tobytes())
        ref = small(Image.open(Path(p) / "pic.jpg"))
        diffs = [sum(abs(a - b) for a, b in zip(ref, small(Image.open(x)))) / (255 * len(ref))
                 for x in sorted(Path(t).glob("f*.jpg"))]
        if diffs:
            res["scene"] = {"first_frame_diff": round(diffs[0], 3), "worst_frame_diff": round(max(diffs), 3),
                            "ok": diffs[0] <= SCENE_FIRST and max(diffs) <= SCENE_ANY}
        res["camera"] = {"clip_movement": movement(rows)}
        if swipe:
            frames(swipe, s)
            sw = movement(faces(s))
            res["camera"]["swipe_movement"] = sw
            res["camera"]["ok"] = sw == 0 or 0.5 <= (res["camera"]["clip_movement"] / sw) <= 2.0
        if voice:
            env = loudness(voice, len(rows))
            mouth = [r["open"] if r["open"] >= 0 else 0.0 for r in rows]
            best = max(((_corr(mouth[max(0, -k):], env[max(0, k):]), k) for k in range(-4, 5)), key=lambda x: x[0])
            quiet = max(env) * 0.08 if env else 0
            silent = [m for m, e in zip(mouth, env) if e <= quiet]
            talk = [m for m, e in zip(mouth, env) if e > quiet]
            res["lips"] = {"match": round(best[0], 2), "lag_s": round(best[1] / FPS, 2),
                           "open_when_talking": round(sum(talk) / len(talk), 3) if talk else None,
                           "open_when_silent": round(sum(silent) / len(silent), 3) if silent else None,
                           "ok": best[0] >= LIPS_OK}
        if sheet:
            fl = sorted(Path(t).glob("f*.jpg")); pick = [fl[int(i * (len(fl) - 1) / 7)] for i in range(8)] if fl else []
            ims = [Image.open(Path(p) / "pic.jpg")] + [Image.open(x) for x in pick]
            ims = [i.resize((180, 320)) for i in ims]
            c = Image.new("RGB", (190 * len(ims), 320), "white")
            for i, im in enumerate(ims):
                c.paste(im, (i * 190, 0))
            c.save(sheet, quality=85); res["sheet"] = str(sheet)
    res["ok"] = all(v.get("ok", True) for v in res.values() if isinstance(v, dict))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("clip"); ap.add_argument("--picture", required=True)
    ap.add_argument("--voice"); ap.add_argument("--swipe"); ap.add_argument("--sheet")
    x = ap.parse_args()
    print(json.dumps(check(x.clip, x.picture, x.voice, x.swipe, x.sheet), indent=1))
