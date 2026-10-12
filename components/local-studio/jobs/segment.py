"""SAM 2.1 video tracking on PyTorch MPS. Each --point X,Y (on frame 0) is its own object.
Writes <out>/masks-<i>.mp4 (white = object) and <out>/overlay.mp4. Runs in tools/av/.venv."""
import argparse, subprocess, tempfile, time, json
from pathlib import Path
import numpy as np, torch
from PIL import Image
from sam2.build_sam import build_sam2_video_predictor

ap = argparse.ArgumentParser()
ap.add_argument("input"); ap.add_argument("output"); ap.add_argument("--ckpt", required=True)
ap.add_argument("--cfg", default="configs/sam2.1/sam2.1_hiera_s.yaml")
ap.add_argument("--point", action="append", default=[]); ap.add_argument("--box"); ap.add_argument("--seconds", type=float)
a = ap.parse_args()
dev = "mps" if torch.backends.mps.is_available() else "cpu"
out = Path(a.output); out.mkdir(parents=True, exist_ok=True)
fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", a.input],
                     capture_output=True, text=True).stdout.strip()
COLORS = [(255, 60, 60), (60, 160, 255), (80, 220, 120), (255, 200, 40)]
with tempfile.TemporaryDirectory() as td:
    td = Path(td); (td / "f").mkdir()
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", a.input] + (["-t", str(a.seconds)] if a.seconds else []) + ["-q:v", "2", str(td / "f" / "%05d.jpg")]
    subprocess.run(cmd, check=True)
    frames = sorted((td / "f").glob("*.jpg"))
    pred = build_sam2_video_predictor(a.cfg, a.ckpt, device=dev)
    t0 = time.time()
    with torch.inference_mode():
        state = pred.init_state(video_path=str(td / "f"))
        objs = []
        for i, p in enumerate(a.point):
            x, y = map(float, p.split(","))
            pred.add_new_points_or_box(state, frame_idx=0, obj_id=i + 1, points=np.array([[x, y]], np.float32), labels=np.array([1], np.int32))
            objs.append(i + 1)
        if a.box:
            b = np.array(list(map(float, a.box.split(","))), np.float32)
            pred.add_new_points_or_box(state, frame_idx=0, obj_id=len(objs) + 1, box=b); objs.append(len(objs) + 1)
        masks = {}
        for fi, ids, logits in pred.propagate_in_video(state):
            masks[fi] = {oid: (logits[k, 0] > 0).cpu().numpy() for k, oid in enumerate(ids)}
    track_s = time.time() - t0
    (td / "ov").mkdir()
    for o in objs:
        (td / f"m{o}").mkdir()
    for fi, f in enumerate(frames):
        img = np.array(Image.open(f).convert("RGB")).astype(np.float32)
        for o in objs:
            m = masks.get(fi, {}).get(o)
            if m is None: m = np.zeros(img.shape[:2], bool)
            Image.fromarray((m * 255).astype(np.uint8)).save(td / f"m{o}" / f"{fi:05d}.png")
            c = np.array(COLORS[(o - 1) % len(COLORS)], np.float32)
            img[m] = img[m] * 0.45 + c * 0.55
        Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(td / "ov" / f"{fi:05d}.jpg", quality=92)
    enc = ["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", fps, "-i", str(td / "ov" / "%05d.jpg"), *enc, str(out / "overlay.mp4")], check=True)
    for o in objs:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", fps, "-i", str(td / f"m{o}" / "%05d.png"), *enc, str(out / f"masks-{o}.mp4")], check=True)
print(json.dumps({"device": dev, "frames": len(frames), "objects": len(objs), "track_seconds": round(track_s, 2),
                  "per_frame_s": round(track_s / max(len(frames), 1), 3)}))
