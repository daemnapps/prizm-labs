"""Demo clips for the Motion Vocabulary terms that have no moment in AI Slop.

Each one is built from our own material only: the AI Slop plates (edit/plates/<n>/f*.jpg, the clean
real frames, with their person mattes) and the 3D objects exactly as rendered for the piece
(edit/comp/objtrack/obj_*.png). Nothing here reads or writes the AI Slop edit or its renders.

    ~/devel/daemn/tools/av/.venv/bin/python demos.py [term ...]      → clips/<term>.mp4 + clips/posters/<term>.jpg (360x640, H.264, no audio)
"""
import os, subprocess, sys, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
MV = os.path.normpath(os.path.join(HERE, "../../../productions/music-video"))
PLATES = os.path.join(MV, "edit/plates")
OBJ = os.path.join(MV, "edit/comp/objtrack")
OUT = os.path.join(HERE, "clips")
W, H, FPS = 360, 640, 30
MONO = "/System/Library/Fonts/Menlo.ttc"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
PINK, TEAL, VIOLET, WHITE = (255, 106, 154), (57, 211, 192), (165, 139, 255), (255, 255, 255)

def font(path, size): return ImageFont.truetype(path, size)
F_S, F_M, F_CAP = font(MONO, 11), font(MONO, 13), font(BOLD, 44)

_pc = {}
def plate(name):
    """All frames of a plate as 360x640 RGB images, plus its mattes (L, same size; white = him)."""
    if name not in _pc:
        d = os.path.join(PLATES, name)
        fs = sorted(f for f in os.listdir(d) if f.endswith(".jpg"))
        frames = [Image.open(os.path.join(d, f)).convert("RGB").resize((W, H), Image.LANCZOS) for f in fs]
        md = os.path.join(d, "matte")
        mattes = []
        for f in fs:
            p = os.path.join(md, f.replace(".jpg", ".png"))
            if not os.path.exists(p):   # mattes are one short: reuse the last
                p = os.path.join(md, sorted(os.listdir(md))[-1])
            mattes.append(Image.open(p).convert("L").resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1)))
        _pc[name] = (frames, mattes)
    return _pc[name]

def pp(seq, n):
    """Ping-pong a frame list out to n frames (so short plates can run longer without a jump)."""
    loop = seq + seq[-2:0:-1]
    return [loop[i % len(loop)] for i in range(n)]

def sprite(frame_no, height):
    """One of the piece's own 3D objects, cut from the object layer by its alpha, scaled to a height."""
    im = Image.open(os.path.join(OBJ, "obj_%04d.png" % frame_no)).convert("RGBA")
    im = im.crop(im.split()[-1].getbbox())
    return im.resize((max(1, round(im.width * height / im.height)), height), Image.LANCZOS)
HEADPHONES = lambda h: sprite(717, h)
KOI = lambda h: sprite(252, h)
BEERLAO = lambda h: sprite(460, h)

def chip(img, text, xy, fg=WHITE, bg=(0, 0, 0, 150), f=F_S, anchor="la"):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = d.textbbox(xy, text, font=f, anchor=anchor)
    d.rounded_rectangle((x0 - 6, y0 - 4, x1 + 6, y1 + 4), 5, fill=bg)
    d.text(xy, text, font=f, fill=fg, anchor=anchor)

def paste(base, spr, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    s = spr
    if scale != 1.0:
        s = s.resize((max(1, round(s.width * scale)), max(1, round(s.height * scale))), Image.LANCZOS)
    if rot:
        s = s.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = s.split()[-1].point(lambda v: int(v * alpha)); s = s.copy(); s.putalpha(a)
    base.paste(s, (round(cx - s.width / 2), round(cy - s.height / 2)), s)

def hblur(img, r):
    """Horizontal motion blur of radius r px (a camera whip)."""
    if r < 1: return img
    a = np.asarray(img).astype(np.float32)
    k = int(r) * 2 + 1
    c = np.cumsum(np.pad(a, ((0, 0), (k // 2 + 1, k // 2), (0, 0)), mode="edge"), axis=1)
    return Image.fromarray(((c[:, k:] - c[:, :-k]) / k).clip(0, 255).astype(np.uint8))

def ease_io(t): return t * t * (3 - 2 * t)

def write(name, frames, poster_i=None):
    tmp = tempfile.mkdtemp()
    try:
        for i, f in enumerate(frames):
            f.convert("RGB").save(os.path.join(tmp, "f%04d.png" % i))
        out = os.path.join(OUT, name + ".mp4")
        for crf in (25, 28, 31):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%04d.png"),
                            "-an", "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p",
                            "-movflags", "+faststart", out], check=True)
            if os.path.getsize(out) < 560_000: break
        pi = len(frames) // 2 if poster_i is None else poster_i
        frames[pi].convert("RGB").save(os.path.join(OUT, "posters", name + ".jpg"), quality=82)
        print(name, len(frames), "frames", os.path.getsize(out) // 1024, "KB")
    finally:
        shutil.rmtree(tmp)

# ---------------------------------------------------------------------------------------------- demos
def timeline(img, t, pic_split, snd_split, a_lbl, b_lbl):
    """The J/L-cut strip: PICTURE and SOUND lanes, where each one switches from A to B, and a playhead."""
    d = ImageDraw.Draw(img, "RGBA")
    x0, x1, y = 16, W - 16, H - 92
    d.rounded_rectangle((8, y - 22, W - 8, H - 10), 10, fill=(10, 8, 20, 200))
    for row, (lbl, split) in enumerate((("PICTURE", pic_split), ("SOUND", snd_split))):
        yy = y + row * 36
        d.text((x0, yy - 13), lbl, font=F_S, fill=(200, 196, 220))
        xs = x0 + (x1 - x0) * split
        d.rectangle((x0, yy + 2, xs, yy + 20), fill=VIOLET + (255,)); d.text((x0 + 6, yy + 5), a_lbl, font=F_S, fill=(20, 10, 40))
        d.rectangle((xs, yy + 2, x1, yy + 20), fill=TEAL + (255,)); d.text((xs + 6, yy + 5), b_lbl, font=F_S, fill=(0, 40, 30))
    px = x0 + (x1 - x0) * t
    d.rectangle((px - 1, y - 16, px + 1, y + 58), fill=PINK + (255,))

def jl_cut(kind):
    A, _ = plate("17-footbridge"); B, _ = plate("16-padel-bandeja")
    n = 90
    pic, snd = (0.6, 0.4) if kind == "j" else (0.4, 0.6)
    fr = []
    for i in range(n):
        t = i / (n - 1)
        img = (A[i % len(A)] if t < pic else B[(i - int(pic * n)) % len(B)]).copy()
        hearing = "the falls" if t < snd else "the court"
        chip(img, "YOU HEAR: " + hearing.upper(), (W - 14, 16), fg=(20, 10, 40) if t < snd else (0, 40, 30),
             bg=(VIOLET if t < snd else TEAL) + (235,), anchor="ra")
        timeline(img, t, pic, snd, "A falls", "B court")
        fr.append(img)
    return fr

def cutaway():
    A, _ = plate("19-rev-5353"); n = 84
    fr = []
    for i in range(n):
        img = A[i % len(A)].copy()
        if 30 <= i < 54:   # the cutaway: a close shot of his hands, from the same take
            img = img.crop((125, 216, 275, 483)).resize((W, H), Image.LANCZOS)
            chip(img, "CUTAWAY · CLOSE ON HIS HANDS", (14, 16))
        else:
            chip(img, "MAIN SHOT", (14, 16))
        fr.append(img)
    return fr

def whip_pan():
    A, _ = plate("13-temple"); B, _ = plate("17-footbridge")
    n, s0, s1 = 72, 26, 40
    fr = []
    for i in range(n):
        if i < s0: img = A[i % len(A)]
        elif i >= s1: img = B[(i - s1) % len(B)]
        else:
            u = ease_io((i - s0) / (s1 - s0))
            strip = Image.new("RGB", (W * 2, H)); strip.paste(A[i % len(A)], (0, 0)); strip.paste(B[0], (W, 0))
            img = hblur(strip.crop((round(u * W), 0, round(u * W) + W, H)), 60 * np.sin(np.pi * u) + 2)
        fr.append(img.copy())
    return fr

def invisible_cut():
    A, _ = plate("11-desk"); B, _ = plate("18-rev-2471")
    n, mid = 60, 30
    fr = []
    ca = (205, 290)     # his sunglasses lens (360x640 frame, first frame of the selfie)
    cb = (228, 465)     # his black shorts (first frame at the falls)
    for i in range(n):  # frames held still during the push so the dark spot stays put; the cut sits in the black
        if i < mid:
            u = ease_io(i / (mid - 1)); z = 1 + 15 * u ** 2; src, c = A[0], ca
        else:
            u = ease_io((i - mid) / (n - mid - 1)); z = 16 - 15 * (1 - (1 - u) ** 2); src, c = B[0], cb
        w, h = W / z, H / z
        x = min(max(c[0] - w / 2, 0), W - w); y = min(max(c[1] - h / 2, 0), H - h)
        img = src.crop((round(x), round(y), round(x + w), round(y + h))).resize((W, H), Image.LANCZOS)
        fr.append(img)
    return fr + [f.copy() for f in B[:30]]

def slow_mo():
    tmp = tempfile.mkdtemp()
    try:
        d = os.path.join(PLATES, "14-padel-forehand")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", os.path.join(d, "f%04d.jpg"),
                        "-vf", f"scale={W}:{H},setpts=4*PTS,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1",
                        os.path.join(tmp, "s%04d.png")], check=True)
        slow = [Image.open(os.path.join(tmp, f)).convert("RGB") for f in sorted(os.listdir(tmp))]
    finally:
        shutil.rmtree(tmp)
    A, _ = plate("14-padel-forehand")
    fr = []
    for f in A:
        img = f.copy(); chip(img, "REAL SPEED · 1×", (14, 16)); fr.append(img)
    for f in slow:
        img = f.copy(); chip(img, "SLOW MOTION · ¼×", (14, 16), bg=PINK + (220,)); fr.append(img)
    return fr

def stutter():
    A, _ = plate("18-rev-2471")
    order = list(range(0, 16)) + [16, 17, 18] * 4 + list(range(19, 34)) + [34, 35, 36] * 4 + list(range(37, 48))
    fr = []
    for k, j in enumerate(order):
        img = A[j].copy()
        prev = order[k - 1] if k else -1
        if j < prev: chip(img, "STUTTER", (14, 16), bg=PINK + (220,))
        fr.append(img)
    return fr

def echo():
    A, M = plate("18-rev-2471")
    seq = list(range(48)) * 2
    fr = []
    bg0 = A[0]
    for k in range(len(seq)):
        img = A[seq[k]].copy()
        for lag, op in ((12, .22), (8, .35), (4, .55)):   # earlier copies of him, fading
            if k - lag < 0: continue
            j = seq[k - lag]
            m = M[j].point(lambda v: int(v * op))
            img.paste(A[j], (0, 0), m)
        img.paste(A[seq[k]], (0, 0), M[seq[k]])
        fr.append(img)
    return fr

def spaced_path(motion):
    """An object crossing the footbridge frame; faint markers every 3 frames show its speed (close = slow)."""
    A, _ = plate("17-footbridge")
    spr = HEADPHONES(78)
    n = 60
    xs = [40 + (W - 80) * motion(i / (n - 1)) for i in range(n)]
    y = 150
    fr = []
    for i in range(n + 20):
        img = A[i % len(A)].copy()
        d = ImageDraw.Draw(img, "RGBA")
        d.line((40, y + 58, W - 40, y + 58), fill=(255, 255, 255, 90), width=1)
        for j in range(0, n, 3):
            d.ellipse((xs[j] - 3, y + 55, xs[j] + 3, y + 61), fill=PINK + (230,))
        paste(img, spr, xs[min(i, n - 1)], y)
        fr.append(img)
    return fr

def overshoot():
    A, _ = plate("11-desk")
    spr = HEADPHONES(120)
    keys = [(0, 0.0), (8, 1.28), (13, 0.88), (17, 1.07), (21, 0.97), (24, 1.0)]
    def s_at(i):
        for (a, sa), (b, sb) in zip(keys, keys[1:]):
            if a <= i <= b: return sa + (sb - sa) * ease_io((i - a) / (b - a))
        return 1.0
    fr = []
    for i in range(66):
        img = A[i % len(A)].copy(); s = s_at(i)
        if s > 0.02: paste(img, spr, 180, 118, scale=s)
        fr.append(img)
    return fr

def follow_through():
    A, _ = plate("19-rev-5353")
    spr = HEADPHONES(110)
    stop = 16
    fr = []
    for i in range(72):
        img = A[i % len(A)].copy()
        if i <= stop:
            u = i / stop; x = -60 + (180 + 60) * (1 - (1 - u) ** 2); rot = 0
        else:   # the body has stopped; the headphones keep swinging on the band, dying away
            x = 180; t = (i - stop) / FPS; rot = 26 * np.exp(-3.2 * t) * np.cos(2 * np.pi * 1.6 * t)
        # swing around the top of the band
        s = spr.rotate(rot, resample=Image.BICUBIC, expand=True, center=(spr.width / 2, 0))
        paste(img, s, x, 120 + s.height / 2 - spr.height / 2)
        if i > stop + 2: chip(img, "BODY STOPPED · SWING CARRIES ON", (14, 16))
        fr.append(img)
    return fr

def camera_shake():
    A, _ = plate("16-padel-bandeja")
    hit = 30
    rng = np.random.default_rng(7)
    fr = []
    for i in range(len(A)):
        img = A[i]
        if i >= hit:
            k = np.exp(-(i - hit) / 4.0)
            dx, dy = rng.normal(0, 12 * k, 2); r = rng.normal(0, 1.6 * k)
            big = img.resize((round(W * 1.08), round(H * 1.08)), Image.LANCZOS).rotate(r, resample=Image.BICUBIC)
            x0 = (big.width - W) / 2 + dx; y0 = (big.height - H) / 2 + dy
            img = big.crop((round(x0), round(y0), round(x0) + W, round(y0) + H))
        else:
            img = img.resize((round(W * 1.08), round(H * 1.08)), Image.LANCZOS).crop((14, 26, 14 + W, 26 + H))
        fr.append(img)
    return fr + fr[-1:] * 8

def roto():
    A, M = plate("17-footbridge"); G, _ = plate("05-koi-pond")
    fr = []
    for i in range(96):
        j = i % len(A)
        if i < 30:
            img = A[j].copy(); chip(img, "THE FOOTAGE", (14, 16))
        elif i < 60:
            img = Image.merge("RGB", [M[j]] * 3); chip(img, "THE MATTE", (14, 16), fg=(0, 0, 0), bg=(255, 255, 255, 220))
        else:
            img = G[j % len(G)].copy(); img.paste(A[j], (0, 0), M[j]); chip(img, "HIM, ON A NEW BACKGROUND", (14, 16))
        fr.append(img)
    return fr

def keying():
    A, M = plate("19-rev-5353"); B, _ = plate("13-temple")
    green = Image.new("RGB", (W, H), (40, 200, 70))
    fr = []
    for i in range(90):
        j = i % len(A)
        gs = green.copy(); gs.paste(A[j], (0, 0), M[j])           # him on a green background
        if i < 36:
            img = gs; chip(img, "ON GREEN", (14, 16))
        else:                                                    # key the green out: every green pixel → see-through
            a = np.asarray(gs).astype(np.int16)
            key = ((a[..., 1] - np.maximum(a[..., 0], a[..., 2])) > 60)
            u = min(1, (i - 36) / 12)
            mask = Image.fromarray(((~key) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
            img = B[j % len(B)].copy()
            img = Image.blend(gs, img, u) if u < 1 else img
            img.paste(gs, (0, 0), mask)
            chip(img, "GREEN KEYED OUT", (14, 16))
        fr.append(img)
    return fr

def occlusion():
    A, M = plate("17-footbridge")
    spr = KOI(120)
    fr = []
    n = 84
    for i in range(n):
        j = i % len(A)
        img = A[j].copy()
        x = -60 + (W + 120) * i / (n - 1)
        paste(img, spr, x, 470)
        img.paste(A[j], (0, 0), M[j])      # he is closer, so he covers the koi as it passes behind
        chip(img, "THE KOI PASSES BEHIND HIM", (14, 16))
        fr.append(img)
    return fr

def grade():
    A, _ = plate("18-rev-2471")
    fr = []
    n = 90
    for i in range(n):
        src = A[i % len(A)]
        a = np.asarray(src).astype(np.float32) / 255
        g = (a - .5) * 1.18 + .5                                      # contrast
        lum = g.mean(axis=2, keepdims=True)
        g = lum + (g - lum) * 1.25                                    # saturation
        g = g * np.array([1.08, 1.0, 0.86]) + np.array([0.02, 0.0, -0.02])   # warm
        graded = Image.fromarray((g.clip(0, 1) * 255).astype(np.uint8))
        u = ease_io(0.5 + 0.5 * np.sin(2 * np.pi * i / n - np.pi / 2))
        xs = round(W * (0.15 + 0.7 * u))
        img = src.copy(); img.paste(graded.crop((xs, 0, W, H)), (xs, 0))
        d = ImageDraw.Draw(img); d.line((xs, 0, xs, H), fill=WHITE, width=2)
        chip(img, "BEFORE", (14, 16)); chip(img, "GRADED", (W - 14, 16), anchor="ra")
        fr.append(img)
    return fr

def sound_off():
    A, _ = plate("11-desk")
    words = ["NO SOUND", "STILL", "READS", "ON SCREEN"]
    fr = []
    for i in range(96):
        img = A[i % len(A)].copy()
        chip(img, "SOUND OFF", (14, 16), bg=(0, 0, 0, 180))
        w = words[min(i // 24, 3)]
        d = ImageDraw.Draw(img, "RGBA")
        bx = d.textbbox((W / 2, 470), w, font=F_CAP, anchor="mm")
        d.rounded_rectangle((bx[0] - 12, bx[1] - 10, bx[2] + 12, bx[3] + 10), 8, fill=(255, 255, 255, 240))
        d.text((W / 2, 470), w, font=F_CAP, fill=(20, 20, 28), anchor="mm")
        fr.append(img)
    return fr

DEMOS = {
    "j-cut": lambda: jl_cut("j"), "l-cut": lambda: jl_cut("l"), "cutaway": cutaway, "whip-pan": whip_pan,
    "invisible-cut": invisible_cut, "slow-mo": slow_mo, "stutter": stutter, "echo": echo,
    "linear": lambda: spaced_path(lambda t: t), "ease-in-out": lambda: spaced_path(ease_io),
    "overshoot": overshoot, "follow-through": follow_through, "camera-shake": camera_shake,
    "roto": roto, "keying": keying, "occlusion": occlusion, "grade": grade, "sound-off": sound_off,
}
POSTER = {"j-cut": 40, "l-cut": 40, "cutaway": 40, "whip-pan": 33, "invisible-cut": 27, "overshoot": 9,
          "follow-through": 22, "camera-shake": 32, "roto": 45, "keying": 60, "occlusion": 30, "sound-off": 60}

if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "posters"), exist_ok=True)
    for k in (sys.argv[1:] or DEMOS):
        write(k, DEMOS[k](), POSTER.get(k))
