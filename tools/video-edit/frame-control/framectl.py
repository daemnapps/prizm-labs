#!/usr/bin/env python3
"""FRAME CONTROL — the moves that made the music-video edit smooth, as one
brand-free toolkit an editor runs locally on any clip.

Written fresh for the workspace (2026-09-28, Damon: "all those video editing
elements that we created need to go inside the actual AI workspace repo").
What each move is and when to reach for it: FRAME-CONTROL.md beside
this file. Needs ffmpeg, numpy and opencv-python (cv2). No model, no network.

    python3 framectl.py clean   in.mp4 out.mp4 [--fps 30]
        drop repeated frames, rebuild real in-betweens (AI clips are often
        24fps padded to 30 — every 5th frame a duplicate — which reads as stutter)
    python3 framectl.py lastframe in.mp4 last.png
        the ACTUAL last frame — the start image for the next chained clip
    python3 framectl.py seams  a.mp4 b.mp4 [c.mp4 …]
        how hard each join jumps vs the clips' own median frame step (pass ≤ 2×)
    python3 framectl.py bridge a.mp4 b.mp4 out.mp4 [--k 10]
        flow-guided morph over the last k frames of a and first k of b — the
        FALLBACK when a join jumps and the clip can't be re-made from the real frame
    python3 framectl.py retime in.mp4 out.mp4 --slow 3.2:0.3:0.6 [--slow t:width:depth …] [--push 0.05]
        one continuous clock: slow-motion dips that never stop (depth ≤ 0.8),
        flow-tweened between frames, with an optional constant push-in
    python3 framectl.py surge in.mp4 out.mp4 --beat 1.4 --beat 2.6 [--width 0.14] [--depth 0.05]
        a quick zoom-punch at each beat time — a gaussian swell in scale,
        no change to playback speed (the "kick surge")
    python3 framectl.py blend a.mp4 b.mp4 out.mp4 --at 1.5 [--width 0.4]
        a look swap: two clips of the same motion, crossfaded into each other
        over `width` seconds around `at`, eased with smoothstep — call it again
        at each beat to chain several swaps across one clip (the "outfit blend")
    python3 framectl.py spin in.mp4 out.mp4 --lock 1.4 --dur 0.9 [--bounce-amp 0.09] [--bounce-freq 26]
        a full 360° turn that lands upright, eased with smootherstep, built
        from sub-frame samples (motion blur) each with its own small zoom
        (radial blur); a settling bounce plays at the lock point
    python3 framectl.py flick in.mp4 out.mp4 --from 4.0 --to 6.0 [--hold 0.15] [--fps 30]
        an eased flick: re-times the source span by how far it actually moved
        (optical flow), not by the clock, with a short hold before it starts
        and motion blur through the travel (the "eased flick-scroll")
    python3 framectl.py pushinto in.mp4 out.mp4 --corners x1,y1,x2,y2,x3,y3,x4,y4 [--land frame.png]
        push a tracked rectangle (tl,tr,br,bl) in a locked-off shot until it
        fills the frame, eased in, with motion blur; give --land a frame to
        land on for a seamless join into what comes next (the "pull-back",
        run in reverse)
    python3 framectl.py loopclose in.mp4 out.mp4 [--k 8]
        morphs the last k frames toward the clip's own first frame so it
        plays on repeat with no seam — the last frame IS the first
    python3 framectl.py loopcheck in.mp4
        how hard the wrap (last frame → first frame) jumps vs the clip's own
        median step — same pass line as `seams` (≤ 2×)
"""
import argparse, math, subprocess, tempfile
from pathlib import Path

import cv2
import numpy as np


def ff(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, a)], check=True)


def fps_of(p):
    cap = cv2.VideoCapture(str(p)); f = cap.get(cv2.CAP_PROP_FPS) or 30; cap.release()
    return f


def frames(p):
    cap = cv2.VideoCapture(str(p)); out = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        out.append(im)
    cap.release()
    return out


def write(frames_, out, fps):
    with tempfile.TemporaryDirectory() as t:
        for i, im in enumerate(frames_):
            cv2.imwrite(f"{t}/f{i:05d}.png", im)
        ff("-framerate", fps, "-i", f"{t}/f%05d.png", "-c:v", "libx264", "-crf", 16,
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out)


# ---- the moves -------------------------------------------------------------

def clean(src, out, fps=30):
    """Dedupe + motion-compensated interpolation to a steady frame rate."""
    ff("-i", src, "-vf", f"mpdecimate,minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
       "-c:v", "libx264", "-crf", 16, "-pix_fmt", "yuv420p", "-an", out)


def lastframe(src, out):
    """The real last frame, never the still the clip was aimed at."""
    fs = frames(src)
    cv2.imwrite(str(out), fs[-1])


_DIS = None


def flow(a, b):
    global _DIS
    if _DIS is None:
        _DIS = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    h, w = a.shape[:2]
    ga, gb = [cv2.cvtColor(cv2.resize(x, (w // 2, h // 2)), cv2.COLOR_BGR2GRAY) for x in (a, b)]
    return cv2.resize(_DIS.calc(ga, gb, None), (w, h)) * 2


def morph(a, b, t):
    """A frame t of the way from a to b: both warped toward each other along
    the optical flow while blending — one movement, not a cross-fade."""
    h, w = a.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    fab, fba = flow(a, b), flow(b, a)
    wa = cv2.remap(a, (gx - t * fba[..., 0]).astype(np.float32), (gy - t * fba[..., 1]).astype(np.float32),
                   cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    wb = cv2.remap(b, (gx - (1 - t) * fab[..., 0]).astype(np.float32), (gy - (1 - t) * fab[..., 1]).astype(np.float32),
                   cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return cv2.addWeighted(wa, 1 - t, wb, t, 0)


def step(a, b):
    return float(np.mean(cv2.absdiff(cv2.resize(a, (160, 284)), cv2.resize(b, (160, 284)))))


def seams(paths):
    """Per join: the jump across the cut vs the clips' own median step."""
    clips = [frames(p) for p in paths]
    rows = []
    for i in range(len(clips) - 1):
        a, b = clips[i], clips[i + 1]
        inner = [step(x, y) for c in (a, b) for x, y in zip(c, c[1:])]
        med = float(np.median(inner)) or 1e-6
        j = step(a[-1], b[0])
        rows.append((Path(paths[i]).name, Path(paths[i + 1]).name, j / med))
    return rows


def bridge(a_path, b_path, out, k=10):
    a, b = frames(a_path), frames(b_path)
    A, B = a[-k], b[k - 1]
    span = len(a[-k:]) + len(b[:k])
    mid = []
    for j in range(span):
        t = (j + 1) / (span + 1); t = t * t * (3 - 2 * t)          # smoothstep
        mid.append(morph(A, B, t))
    write(a[:-k] + mid + b[k:], out, fps_of(a_path))


def retime(src, out, slows, push=0.0):
    """One continuous clock. speed(x) = source frames per output frame; each
    slow is (at seconds, width seconds, depth 0–0.8) — a dip, never a freeze."""
    fs = frames(src); fps = fps_of(src); n = len(fs)

    def speed(x):
        s = 1.0
        for at, width, depth in slows:
            s -= depth * math.exp(-((x - at * fps) / (width * fps)) ** 2)
        return max(0.2, s)
    xs, pos = [], 0.0
    while pos < n - 1:
        xs.append(pos); pos += speed(pos)
    xs.append(n - 1)
    out_f = []
    h, w = fs[0].shape[:2]
    for i, x in enumerate(xs):
        k = int(x); t = x - k
        im = fs[k] if t < 0.04 or k + 1 >= n else morph(fs[k], fs[k + 1], t)
        if push:
            z = 1 + push * i / max(1, len(xs) - 1)
            M = cv2.getRotationMatrix2D((w / 2, h * 0.42), 0, z)
            im = cv2.warpAffine(im, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        out_f.append(im)
    write(out_f, out, fps)


def smoothstep(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def smootherstep(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (6 * u - 15) + 10)


def surge(src, out, beats, width=0.14, depth=0.05):
    """A quick zoom-punch at each beat time: a gaussian swell in scale, no
    change to playback speed."""
    fs = frames(src); fps = fps_of(src); h, w = fs[0].shape[:2]

    def swell(t):
        return sum(math.exp(-((t - b) / width) ** 2) for b in beats)
    out_f = []
    for i, im in enumerate(fs):
        z = 1 + depth * swell(i / fps)
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, z)
        out_f.append(cv2.warpAffine(im, M, (w, h), borderMode=cv2.BORDER_REFLECT))
    write(out_f, out, fps)


def blend(a_path, b_path, out, at, width=0.4):
    """A look swap: two same-length, same-motion clips crossfaded into each
    other over `width` seconds around `at`, eased with smoothstep."""
    a, b = frames(a_path), frames(b_path)
    fps = fps_of(a_path); n = min(len(a), len(b))
    out_f = []
    for i in range(n):
        e = smoothstep((i / fps - (at - width / 2)) / width)
        out_f.append(cv2.addWeighted(a[i], 1 - e, b[i], e, 0))
    write(out_f, out, fps)


def spin_state(t, lock, dur, bounce_amp, bounce_freq):
    ang, z = 0.0, 1.0
    if t >= lock:
        dt = t - lock
        z += bounce_amp * math.exp(-dt * 9) * math.sin(dt * bounce_freq)      # the settle at the lock
    if lock <= t < lock + dur:
        e = smootherstep((t - lock) / dur)
        ang = 360 * e
        c, s_ = abs(math.cos(math.radians(ang))), abs(math.sin(math.radians(ang)))
        h_over_w = 16 / 9
        z *= 1 + 0.55 * max(0, (c + s_ * h_over_w) - 1) / h_over_w            # push in to cover the turning corners
    return ang, z


def spin(src, out, lock, dur, bounce_amp=0.09, bounce_freq=26.0):
    """A full 360° turn that lands upright: sub-frame samples give motion
    blur, each sample's own small zoom spread gives radial blur."""
    fs = frames(src); fps = fps_of(src); h, w = fs[0].shape[:2]
    out_f = []
    for f, im in enumerate(fs):
        t = f / fps
        a0, _ = spin_state(t - 0.5 / fps, lock, dur, bounce_amp, bounce_freq)
        a1, _ = spin_state(t + 0.5 / fps, lock, dur, bounce_amp, bounce_freq)
        speed = abs(a1 - a0)                                                  # degrees per frame
        n = int(min(18, max(1, speed / 1.5)))
        acc = np.zeros_like(im, np.float32)
        for k in range(n):
            tt = t + (k / max(1, n - 1) - 0.5) * 0.5 / fps if n > 1 else t    # half-frame shutter
            ang, z = spin_state(tt, lock, dur, bounce_amp, bounce_freq)
            z *= 1 + 0.004 * speed * (k / max(1, n - 1) - 0.5) if n > 1 else 1
            M = cv2.getRotationMatrix2D((w / 2, h / 2), -ang, z)
            acc += cv2.warpAffine(im, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        out_f.append((acc / n).astype(np.uint8))
    write(out_f, out, fps)


def flick(src, out, t0, t1, hold=0.15, fps_out=None):
    """An eased flick: re-times a source span by how far it actually moved
    (optical flow), not by the clock, with a short hold before it starts and
    motion blur through the travel."""
    src_fps = fps_of(src); fs = frames(src)
    i0, i1 = int(t0 * src_fps), min(len(fs) - 1, int(round(t1 * src_fps)))
    seg = fs[i0:i1 + 1]
    fps_out = fps_out or src_fps
    disp = [0.0]
    for x, y in zip(seg, seg[1:]):
        f = flow(x, y)
        disp.append(disp[-1] + abs(float(np.median(f[..., 1]))))

    def pos_for(share):
        return float(np.interp(share * disp[-1], disp, np.arange(len(seg), dtype=float)))

    def frame_at(x):
        i = int(np.floor(x)); t = float(x - i)
        if t < 0.03 or i + 1 >= len(seg):
            return seg[min(i, len(seg) - 1)].astype(np.float32)
        return morph(seg[i], seg[i + 1], t).astype(np.float32)
    out_dur = t1 - t0
    n_out = max(2, int(round(out_dur * fps_out)))
    hold_n = int(round(hold * fps_out))
    out_f = []
    for i in range(n_out):
        if i <= hold_n:
            out_f.append(seg[0]); continue
        u = (i - hold_n) / max(1, n_out - 1 - hold_n)
        u0, u1 = max(0, u - 0.5 / n_out), min(1, u + 0.5 / n_out)
        x0, x1 = pos_for(smootherstep(u0)), pos_for(smootherstep(u1))
        xs = np.linspace(x0, x1, max(2, min(24, int(abs(x1 - x0) * 8) + 2)))    # dense: a streak, not ghost copies
        acc = sum(frame_at(x) for x in xs) / len(xs)
        out_f.append(acc.astype(np.uint8))
    write(out_f, out, fps_out)


def pushinto(src, out, corners, land=None):
    """Push a tracked rectangle (tl,tr,br,bl) in a locked-off shot until it
    fills the frame: eased in with smootherstep, motion-blurred across three
    sub-samples. With `land`, the last few frames blend into that image so
    the push joins straight into what comes next with no seam."""
    fs = frames(src); fps = fps_of(src); h, w = fs[0].shape[:2]
    q = np.float32(corners).reshape(4, 2)
    tgt = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    landing = cv2.imread(str(land)) if land else None
    n = len(fs)
    out_f = []
    for f, im in enumerate(fs):
        acc = np.zeros_like(im, np.float32)
        for j in range(3):
            u = min(1, max(0, (f + (j - 1) / 3) / max(1, n - 1)))
            e = smootherstep(u)
            M = cv2.getPerspectiveTransform(q, q + (tgt - q) * e)
            acc += cv2.warpPerspective(im, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        result = acc / 3
        if landing is not None and f >= n - 5:
            k = (f - (n - 5)) / 4
            result = result * (1 - k) + landing.astype(np.float32) * k
            if f == n - 1:
                result = landing.astype(np.float32)
        out_f.append(result.clip(0, 255).astype(np.uint8))
    write(out_f, out, fps)


def loopclose(src, out, k=8):
    """Morphs the last k frames toward the clip's own first frame, so it
    plays on repeat with no seam — the last frame IS the first."""
    fs = frames(src); fps = fps_of(src)
    span = 2 * k
    mid = [morph(fs[-k], fs[0], smoothstep((j + 1) / (span + 1))) for j in range(span)]
    mid[-1] = fs[0]                                                           # the last frame IS the first, exactly
    write(fs[:-k] + mid, out, fps)


def loopcheck(path):
    """The wrap seam (last frame → first frame) vs the clip's own median
    step — same pass line as `seams` (≤ 2×)."""
    fs = frames(path)
    inner = [step(x, y) for x, y in zip(fs, fs[1:])]
    med = float(np.median(inner)) or 1e-6
    return step(fs[-1], fs[0]) / med


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("clean"); c.add_argument("src"); c.add_argument("out"); c.add_argument("--fps", type=int, default=30)
    l = sp.add_parser("lastframe"); l.add_argument("src"); l.add_argument("out")
    s = sp.add_parser("seams"); s.add_argument("clips", nargs="+")
    b = sp.add_parser("bridge"); b.add_argument("a"); b.add_argument("b"); b.add_argument("out"); b.add_argument("--k", type=int, default=10)
    r = sp.add_parser("retime"); r.add_argument("src"); r.add_argument("out")
    r.add_argument("--slow", action="append", default=[], help="at:width:depth in seconds, e.g. 3.2:0.3:0.6")
    r.add_argument("--push", type=float, default=0.0)
    su = sp.add_parser("surge"); su.add_argument("src"); su.add_argument("out")
    su.add_argument("--beat", action="append", type=float, default=[], dest="beats", required=True)
    su.add_argument("--width", type=float, default=0.14); su.add_argument("--depth", type=float, default=0.05)
    bl = sp.add_parser("blend"); bl.add_argument("a"); bl.add_argument("b"); bl.add_argument("out")
    bl.add_argument("--at", type=float, required=True); bl.add_argument("--width", type=float, default=0.4)
    sn = sp.add_parser("spin"); sn.add_argument("src"); sn.add_argument("out")
    sn.add_argument("--lock", type=float, required=True); sn.add_argument("--dur", type=float, required=True)
    sn.add_argument("--bounce-amp", type=float, default=0.09); sn.add_argument("--bounce-freq", type=float, default=26.0)
    fl = sp.add_parser("flick"); fl.add_argument("src"); fl.add_argument("out")
    fl.add_argument("--from", type=float, required=True, dest="t0"); fl.add_argument("--to", type=float, required=True, dest="t1")
    fl.add_argument("--hold", type=float, default=0.15); fl.add_argument("--fps", type=float, default=None)
    pi = sp.add_parser("pushinto"); pi.add_argument("src"); pi.add_argument("out")
    pi.add_argument("--corners", required=True, help="x1,y1,x2,y2,x3,y3,x4,y4 — tl,tr,br,bl")
    pi.add_argument("--land", default=None)
    lc = sp.add_parser("loopclose"); lc.add_argument("src"); lc.add_argument("out"); lc.add_argument("--k", type=int, default=8)
    lk = sp.add_parser("loopcheck"); lk.add_argument("src")
    a = ap.parse_args()
    if a.cmd == "clean":
        clean(a.src, a.out, a.fps)
    elif a.cmd == "lastframe":
        lastframe(a.src, a.out)
    elif a.cmd == "seams":
        for x, y, ratio in seams(a.clips):
            print(f"  {x} → {y}: {ratio:.1f}× the median step  {'PASS' if ratio <= 2 else 'JUMPS — re-make from the real last frame'}")
    elif a.cmd == "bridge":
        bridge(a.a, a.b, a.out, a.k)
    elif a.cmd == "retime":
        retime(a.src, a.out, [tuple(map(float, s.split(":"))) for s in a.slow], a.push)
    elif a.cmd == "surge":
        surge(a.src, a.out, a.beats, a.width, a.depth)
    elif a.cmd == "blend":
        blend(a.a, a.b, a.out, a.at, a.width)
    elif a.cmd == "spin":
        spin(a.src, a.out, a.lock, a.dur, a.bounce_amp, a.bounce_freq)
    elif a.cmd == "flick":
        flick(a.src, a.out, a.t0, a.t1, a.hold, a.fps)
    elif a.cmd == "pushinto":
        pushinto(a.src, a.out, [float(x) for x in a.corners.split(",")], a.land)
    elif a.cmd == "loopclose":
        loopclose(a.src, a.out, a.k)
    elif a.cmd == "loopcheck":
        ratio = loopcheck(a.src)
        print(f"  wrap: {ratio:.1f}× the median step  {'PASS' if ratio <= 2 else 'JUMPS — try loopclose'}")


if __name__ == "__main__":
    main()
