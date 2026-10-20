"""Stage 6 — pull a garment colour that drifted back to the master's colour, pixel by pixel (HSV band).

Edit models drift small, fast, low-res garments (the bear's lilac lapel came out pink). ffmpeg's huesaturation cannot
move a pale pink; this can. Only pixels inside the band move, feathered; saturated reds (pumps, signs) and grey
backgrounds sit outside it.

Usage: garment_grade.py SRC.mp4|png DST [--hue-lo 155 --hue-hi 3 --sat 45-150 --val-min 110 --to-hue 136 --val 0.64 --sat-mul 1.05]
Defaults = the bear's pink lapel -> dusty lilac. OpenCV hue runs 0-179; a band that wraps (lo > hi) means hue >= lo or <= hi.
Measure the band on the drifted pixels and the target hue on the master before running.
"""
import argparse, cv2, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--hue-lo", type=float, default=155); ap.add_argument("--hue-hi", type=float, default=3)
ap.add_argument("--sat", default="45-150"); ap.add_argument("--val-min", type=float, default=110)
ap.add_argument("--to-hue", type=float, default=136); ap.add_argument("--val", type=float, default=0.64)
ap.add_argument("--sat-mul", type=float, default=1.05)
A = ap.parse_args(); s_lo, s_hi = map(float, A.sat.split("-"))
def grade(im):
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(np.float32); H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    band = ((H >= A.hue_lo) | (H <= A.hue_hi)) if A.hue_lo > A.hue_hi else ((H >= A.hue_lo) & (H <= A.hue_hi))
    m = cv2.GaussianBlur((band & (S >= s_lo) & (S <= s_hi) & (V > A.val_min)).astype(np.float32), (0, 0), 1.5)
    H2 = np.where(m > 0, A.to_hue, H); V2 = V * (1 - (1 - A.val) * m); S2 = S * (1 + (A.sat_mul - 1) * m)
    return cv2.cvtColor(np.stack([H * (1 - m) + H2 * m, S2, V2], -1).clip(0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)
if A.src.lower().endswith((".png", ".jpg")):
    cv2.imwrite(A.dst, grade(cv2.imread(A.src))); raise SystemExit
import subprocess, os
cap = cv2.VideoCapture(A.src); fps = cap.get(cv2.CAP_PROP_FPS); w, h = int(cap.get(3)), int(cap.get(4))
tmp = A.dst + ".tmp.mp4"; vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
while True:
    ok, f = cap.read()
    if not ok: break
    vw.write(grade(f))
vw.release()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", A.dst], check=True); os.remove(tmp)
