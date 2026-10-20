"""Stage 8 — paste the swapped person (the lead) back onto the dressed charge, without touching the animal.

The motion-control swap re-draws the whole frame, including a bare (undressed) animal, so only the person's area is
taken from it. Built on the gas-station bear (a past piece), where three things went wrong and are now designed out:
  - the paste stopped partway across the frame and the gas hose came out in two pieces  -> --person-top pastes the
    full width below a line, so anything the person holds (hose, leash, rope) is pasted whole;
  - the swap's bare animal ghosted into the dressed one as it crossed the paste ("weird frame")  -> from --animal-at
    the paste is kept to --safe areas (below --safe-below, or left of --side-x / right of --side-x-right), never the
    animal's path;
  - two hoses overlapped when the paste faded out  -> hand back at --cut (pick the frame where the held object matches,
    use --score), hold the settled object on the side strip, ease the rest back over 0.3 s.

Usage:
  person_comp.py BASE.mp4 SWAP.mp4 ORIG.mp4 OUT.mp4 [options]
    BASE  the dressed charge (animal in the outfit, original person)
    SWAP  the motion-control render with the lead (made from ORIG)
    ORIG  the clip SWAP was made from (same timing as SWAP's source)
Options (bear values as defaults; set per piece and record them in piece.json):
  --person-top 0.42     paste only below this fraction of the height
  --animal-at 3.8       from this time the animal is on the forecourt: paste only the safe areas
  --safe-below 0.56     safe area 1: everything below this fraction of the height
  --side-x 0.3          safe area 2: the strip left of this fraction of the width (the pump side); 0 = none
  --side-x-right 0      safe area 3: the strip right of this fraction of the width; 0 = none
  --cut 4.71            hand back to the base here (0 = old fade at 4.35-4.5)
  --score               print how well the side strip matches the base per frame (pick --cut from it)
"""
import argparse, subprocess, os, cv2, numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("base"); ap.add_argument("swap"); ap.add_argument("orig"); ap.add_argument("out")
ap.add_argument("--person-top", type=float, default=0.42); ap.add_argument("--animal-at", type=float, default=3.8)
ap.add_argument("--safe-below", type=float, default=0.56); ap.add_argument("--side-x", type=float, default=0.3)
ap.add_argument("--side-x-right", type=float, default=0.0); ap.add_argument("--cut", type=float, default=4.71)
ap.add_argument("--score", action="store_true")
A = ap.parse_args()

def frames(p):
    cap = cv2.VideoCapture(p); fps = cap.get(cv2.CAP_PROP_FPS); out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        out.append(f)
    return out, fps
B, bf = frames(A.base); P, pf = frames(A.swap); O, of_ = frames(A.orig)
H, W = B[0].shape[:2]
P = [cv2.resize(f, (W, H)) for f in P]; O = [cv2.resize(f, (W, H)) for f in O]
dur_p, dur_o = len(P) / pf, len(O) / of_
END = dur_o - 0.05
def p_at(t): return P[int(np.clip(round(min(t, END) * dur_p / dur_o * pf), 0, len(P) - 1))]   # swap, stretched to source timing
def small(f): return cv2.cvtColor(cv2.resize(f, (W // 4, H // 4)), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
warp = np.eye(2, 3, dtype=np.float32)
_, warp = cv2.findTransformECC(small(B[0]), small(P[0]), warp, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
warp[:, 2] *= 4
def align(f): return cv2.warpAffine(f, warp, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)

zone = np.zeros((H, W), np.float32); zone[int(H * A.person_top):, :] = 1
safe = np.zeros((H, W), np.float32); safe[int(H * A.safe_below):, :] = 1
side = np.zeros((H, W), np.float32)
if A.side_x: safe[:, :int(W * A.side_x)] = 1; side[int(H * A.person_top):, :int(W * A.side_x)] = 1
if A.side_x_right: safe[:, int(W * A.side_x_right):] = 1; side[int(H * A.person_top):, int(W * A.side_x_right):] = 1
safef = cv2.GaussianBlur(safe, (0, 0), 12); sidef = cv2.GaussianBlur(side, (0, 0), 12)[..., None]

a = cv2.cvtColor(align(P[0]), cv2.COLOR_BGR2LAB).astype(np.float32); b = cv2.cvtColor(B[0], cv2.COLOR_BGR2LAB).astype(np.float32)
bg = (zone == 0)
ma, sa = a[bg].mean(0), a[bg].std(0) + 1e-6; mb, sb = b[bg].mean(0), b[bg].std(0)
def recol(f):
    x = cv2.cvtColor(f, cv2.COLOR_BGR2LAB).astype(np.float32); return cv2.cvtColor(((x - ma) / sa * sb + mb).clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
def blend(f, d, m): return (f.astype(np.float32) * (1 - m) + d.astype(np.float32) * m).astype(np.uint8)

tmp = A.out + ".tmp.mp4"
vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), bf, (W, H))
k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)); last = None
for i, f in enumerate(B):
    t = i / bf
    if t < (A.cut if A.cut else 4.5):
        d = recol(align(p_at(t))); o = O[int(np.clip(round(t * of_), 0, len(O) - 1))]
        diff = (np.abs(d.astype(np.int16) - o.astype(np.int16)).max(2) > 28).astype(np.uint8)     # where the lead is
        diff2 = (np.abs(o.astype(np.int16) - f.astype(np.int16)).max(2) > 28).astype(np.uint8)    # where the original person was
        m = cv2.dilate(np.maximum(diff, diff2), k).astype(np.float32) * zone
        if t >= A.animal_at:   # the animal is in the paste area now: ease into pasting only the safe areas, whole
            w = min(1.0, (t - A.animal_at) / 0.25); m = np.maximum(m * safef, safef * w)
        m = cv2.GaussianBlur(m, (0, 0), 6)[..., None] * (1.0 if (A.cut or t < 4.35) else max(0.0, (4.5 - t) / 0.15))
        if A.score and t >= A.animal_at:
            print(f"score {t:.3f} side-strip difference {np.abs(d.astype(np.int16) - f.astype(np.int16))[side > 0].mean():.2f}")
        f = blend(f, d, m); last = d
    elif A.cut and last is not None:   # hand-back: hold the settled side strip, ease the rest back over 0.3 s
        fade = max(0.0, 1 - (t - A.cut) / 0.3)
        if fade > 0: f = blend(f, recol(align(p_at(t))), safef[..., None] * fade * (1 - sidef))
        f = blend(f, last, sidef)
    vw.write(f)
vw.release()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", A.out], check=True)
os.remove(tmp); print("ok", len(B), "frames ->", A.out)
