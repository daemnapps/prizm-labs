"""Stage 12 — the checks that must ALL pass before anything is called final. Each writes a picture to look at
(qc-*.jpg in the piece folder) and/or prints numbers. Every one of these exists because the lead caught it first.

  qc.py hair   SWAP.mp4 [x0 y0 x1 y1] [t0 t1]  every 3rd frame of the swapped person, cropped to them (bun, ponytail,
                                               the original person coming back). Fraction box, default the bear's pump.
  qc.py suit   MASTER.png SHOT1.mp4@t SHOT2.mp4@t ...   one frame of the garment from every shot beside the master,
                                               same height. Any shot whose colour, fabric, lapels or trousers differ fails.
  qc.py scrub  SHOT.mp4 [every]                 every Nth frame of a generated camera-move shot in a grid: the animal
                                               hidden behind anything, or a glitch frame, fails.
  qc.py zoom   CLIP.mp4 t0 t1 x0 y0 x1 y1       every frame of a time window, cropped (animal legs during a paste,
                                               a held object at a paste edge).
  qc.py jumps  CUT.mp4 [t0 t1]                  frame-to-frame change inside t0-t1; flags single-frame pops (a step over 2x its
                                               neighbours' median), away from cuts. Run it on the real-footage part (0 to the hit) and
                                               on every paste/hand-back window — not on camera-move shots (whips jump).
  qc.py core   CUT.mp4 [per_s]                  frames from every second of the cut in one sheet, to check every
                                               character's core elements from the cast folder's character.md (horns, ears, hair, glasses...).
  qc.py held   CUT.mp4                          held or repeated frames (must be 0).
"""
import subprocess, sys, os, re
import numpy as np
def ff(*a): subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *a], check=True)
cmd, args = sys.argv[1], sys.argv[2:]
if cmd == "hair":
    src = args[0]; box = list(map(float, args[1:5])) if len(args) >= 5 else [0.35, 0.4, 0.95, 0.8]
    t0, t1 = (map(float, args[5:7])) if len(args) >= 7 else (0, 99)
    x0, y0, x1, y1 = box
    ff("-i", src, "-vf", f"select='between(t\\,{t0}\\,{t1})*not(mod(n\\,3))',crop=iw*{x1-x0}:ih*{y1-y0}:iw*{x0}:ih*{y0},scale=150:-2,tile=12x4", "-frames:v", "1", "qc-hair.jpg"); print("qc-hair.jpg")
elif cmd == "suit":
    master, shots = args[0], args[1:]; ins, n = ["-i", master], 1
    for s in shots:
        f, t = s.rsplit("@", 1); ins += ["-ss", t, "-i", f]; n += 1
    chain = "".join(f"[{i}:v]scale=-2:520,setsar=1,format=yuvj420p[s{i}];" for i in range(n)) + "".join(f"[s{i}]" for i in range(n)) + f"hstack={n}"
    ff(*ins, "-filter_complex", chain, "-frames:v", "1", "qc-suit.jpg"); print("qc-suit.jpg")
elif cmd == "scrub":
    every = args[1] if len(args) > 1 else "3"
    ff("-i", args[0], "-vf", f"select='not(mod(n\\,{every}))',scale=-2:200,tile=14x4", "-frames:v", "1", "qc-scrub.jpg"); print("qc-scrub.jpg")
elif cmd == "zoom":
    f, t0, t1 = args[0], float(args[1]), float(args[2]); x0, y0, x1, y1 = map(float, args[3:7])
    ff("-ss", f"{t0}", "-t", f"{t1-t0}", "-i", f, "-vf", f"crop=iw*{x1-x0}:ih*{y1-y0}:iw*{x0}:ih*{y0},scale=240:-2,tile=9x3", "-frames:v", "1", "qc-zoom.jpg"); print("qc-zoom.jpg")
elif cmd == "jumps":
    import cv2
    f = args[0]; t0, t1 = (float(args[1]), float(args[2])) if len(args) > 2 else (0, 1e9)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", f, "-vf", "select='gt(scene,0.3)',showinfo", "-f", "null", "-"], capture_output=True, text=True).stderr
    cuts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", out)]
    cap = cv2.VideoCapture(f); fps = cap.get(5); prev, steps, i = None, [], 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if prev is not None: steps.append((i / fps, float(np.abs(g - prev).mean())))
        prev = g; i += 1
    # a pop is a single-frame spike against its neighbours (fast motion is sustained, a pop is not)
    vals = [s for _, s in steps]; bad = []
    for j, (t, v) in enumerate(steps):
        if not (t0 <= t <= t1) or any(abs(t - c) < 0.05 for c in cuts): continue
        nb = vals[max(0, j - 3):j] + vals[j + 1:j + 4]
        if nb and v > 2.0 * np.median(nb) and v > 2.0: bad.append((t, v))
    med = np.median(vals)
    print(f"cuts {cuts} | median step {med:.2f} | flagged {len(bad)}:", " ".join(f"{t:.2f}s({s:.1f})" for t, s in bad))
elif cmd == "core":
    per = args[1] if len(args) > 1 else "2"
    ff("-i", args[0], "-vf", f"fps={per},scale=-2:360,tile=10x5", "-frames:v", "1", "qc-core.jpg"); print("qc-core.jpg — check every character against the cast folder")
elif cmd == "held":
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", args[0], "-vf", "mpdecimate", "-f", "null", "-"], capture_output=True, text=True).stderr
    print("held frames:", out.count("drop"))
else:
    print(__doc__)
