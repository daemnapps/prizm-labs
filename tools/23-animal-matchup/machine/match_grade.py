"""Match a whole shot's colour to a reference shot (LAB mean/std per channel, blended by STRENGTH).
Usage: match_grade.py SRC.mp4 REF.mp4 OUT.mp4 [STRENGTH=0.8]"""
import sys, subprocess, cv2, numpy as np
SRC, REF, OUT = sys.argv[1:4]; K = float(sys.argv[4]) if len(sys.argv) > 4 else 0.8
def stats(path, n=12):
    cap = cv2.VideoCapture(path); N = int(cap.get(7)); px = []
    for i in np.linspace(0, N - 1, n).astype(int):
        cap.set(1, i); ok, f = cap.read()
        if ok: px.append(cv2.cvtColor(f, cv2.COLOR_BGR2LAB).reshape(-1, 3)[::7].astype(np.float32))
    p = np.concatenate(px); return p.mean(0), p.std(0)
ms, ss = stats(SRC); mr, sr = stats(REF)
cap = cv2.VideoCapture(SRC); fps = cap.get(5); W, H = int(cap.get(3)), int(cap.get(4))
vw = cv2.VideoWriter("_mg.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
while True:
    ok, f = cap.read()
    if not ok: break
    lab = cv2.cvtColor(f, cv2.COLOR_BGR2LAB).astype(np.float32)
    t = (lab - ms) / ss * sr + mr
    lab = np.clip(lab * (1 - K) + t * K, 0, 255).astype(np.uint8)
    vw.write(cv2.cvtColor(lab, cv2.COLOR_LAB2BGR))
vw.release()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "_mg.mp4", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", OUT], check=True)
subprocess.run(["rm", "_mg.mp4"]); print("src", ms.round(1), "ref", mr.round(1))
