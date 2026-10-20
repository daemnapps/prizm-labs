"""Make the splice from the real charge shot (shot2b.mp4, 30 fps) into the dressed Kling version (shot2-kling2.mp4,
24 fps) seamless: find the best cut frame + time offset, warp the real frames to Kling's geometry (ECC affine),
match colour (LAB mean/std), cross-blend 2 frames. Output shot2-seamless.mp4 at 24 fps, Kling's timing after the cut."""
import cv2, numpy as np, sys
def frames(p):
    cap = cv2.VideoCapture(p); fps = cap.get(cv2.CAP_PROP_FPS); out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        out.append(f)
    return out, fps
S, sf = frames("shot2b.mp4"); K, kf = frames("shot2-kling2.mp4")
H, W = K[0].shape[:2]
S = [cv2.resize(f, (W, H), interpolation=cv2.INTER_CUBIC) for f in S]
def s_at(t): return S[int(np.clip(round(t * sf), 0, len(S) - 1))]
def k_at(t): return K[int(np.clip(round(t * kf), 0, len(K) - 1))]
def small(f): return cv2.cvtColor(cv2.resize(f, (W // 4, H // 4)), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
def align(src, dst):
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        _, warp = cv2.findTransformECC(small(dst), small(src), warp, cv2.MOTION_AFFINE,
                                      (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    except cv2.error: pass
    warp[:, 2] *= 4
    return warp
def apply(src, warp): return cv2.warpAffine(src, warp, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
def colour(src, ref):
    a = cv2.cvtColor(src, cv2.COLOR_BGR2LAB).astype(np.float32); b = cv2.cvtColor(ref, cv2.COLOR_BGR2LAB).astype(np.float32)
    ma, sa = a.reshape(-1, 3).mean(0), a.reshape(-1, 3).std(0) + 1e-6; mb, sb = b.reshape(-1, 3).mean(0), b.reshape(-1, 3).std(0)
    return ma, sa, mb, sb
def recolour(src, st):
    ma, sa, mb, sb = st; a = cv2.cvtColor(src, cv2.COLOR_BGR2LAB).astype(np.float32)
    return cv2.cvtColor(((a - ma) / sa * sb + mb).clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
# geometry + colour measured on an empty-field frame pair (static phone camera), refined at the cut
base_w = align(s_at(0.05), k_at(0.05))
best = None
for tc in np.arange(0.50, 0.80, 1 / kf):                  # cut time on the 24 fps grid
    for off in np.arange(-0.20, 0.201, 1 / sf):           # real-clip time = tc + off
        s = apply(s_at(tc + off), base_w); k = k_at(tc)
        st = colour(s, k); s2 = recolour(s, st)
        d = float(np.mean((small(s2) - small(k)) ** 2))
        if best is None or d < best[0]: best = (d, round(float(tc), 4), round(float(off), 4))
d, TC, OFF = best; print("best cut", TC, "offset", OFF, "mse", round(d, 5))
w_cut = align(s_at(TC + OFF), k_at(TC))
st = colour(apply(s_at(TC + OFF), w_cut), k_at(TC))
vw = cv2.VideoWriter("_seam.mp4", cv2.VideoWriter_fourcc(*"mp4v"), kf, (W, H))
n = len(K); ci = int(round(TC * kf))
MASK = np.zeros((H, W, 1), np.float32); MASK[:, : int(W * 0.32)] = 1
MASK = cv2.GaussianBlur(MASK, (0, 0), W * 0.04)[..., None]
for i in range(n):
    t = i / kf
    if i < ci:
        f = recolour(apply(s_at(max(0.0, t + OFF)), w_cut), st)
    else:
        f = K[i]
    if ci - 1 <= i <= ci:                                     # 2-frame cross-blend on the seam
        r = recolour(apply(s_at(max(0.0, t + OFF)), w_cut), st)
        a = 0.66 if i == ci - 1 else 0.33
        f = cv2.addWeighted(r, a, K[i], 1 - a, 0)
    if ci - 1 <= i <= ci + 6:                                 # Kling's invented runner exits bottom-left here: patch that corner
        r = recolour(apply(s_at(max(0.0, t + OFF)), w_cut), st)
        f = (f.astype(np.float32) * (1 - MASK) + r.astype(np.float32) * MASK).astype(np.uint8)
    vw.write(f)
vw.release(); print("frames", n, "cut frame", ci)
