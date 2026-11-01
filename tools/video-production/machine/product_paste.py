"""THE PRODUCT PASTE — the product in a made picture is replaced by the REAL product photographed at the
matching angle (2026-10-09, the owner: "there is so much slop in these images for the product … there's zero
reason for it"). The picture model draws the person, the hand and the room; the product's pixels come from
its kit's real turntable cut-outs (`sources/turntable-NNN.png`, one per 15°, cut from the store's own 360°
video). Every redraw-the-product edit before this one (product_fix.py) asked the model to draw it again,
and it drifted every time.

  find      the product's box (product_kit.detect) and its own pixels (product_check.product_mask, SAM)
  pose      the mask's lean and length along its own axis; every real angle is fitted to it at that lean
            and scale, the best overlap wins (front-facing angles only unless the picture shows the back)
  paste     the real cut-out over the drawn one; fingers stay on top (skin in front of the product is kept);
            a drawn bulge the real outline does not cover is filled from the pixels around it
  match     the cut-out takes the drawn product's light (brightness and contrast) and the picture's grain

Returns {"ok", "angle", "lean", "overlap", "file", "why"}. Brand-agnostic: a kit with no turntable
cut-outs is passed over (`ok: True`, `skipped`).

    python3 product_paste.py <picture.png> --kit <kit folder> [--out <out.png>] [--what "the black face brush"]
"""
from __future__ import annotations

import argparse, json, math, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_OVERLAP = 0.55
MAX_SHARE = 0.25       # a product taking more than a quarter of the frame is a wrong find, not the product (2026-10-23)      # below this the drawn thing is not the product at any angle: not pasted, held


def _load(name):
    import importlib.util as u
    sp = u.spec_from_file_location(name, HERE / f"{name}.py"); m = u.module_from_spec(sp); sp.loader.exec_module(m); return m


REAL_VIEWS = (("reference-front-transparent.png", 0), ("reference-34-transparent.png", 30),
              ("reference-back-transparent.png", 180))


def cutouts(kit: Path) -> list:
    """The kit's REAL cut-outs by angle: its turntable (one per 15°), else the real photo cut-outs the kit was built
    from (model/reference-front · -34 · -back, transparent) — so every kit with a real photo can be pasted (P68 add)."""
    out = []
    for f in sorted((kit / "sources").glob("turntable-[0-9][0-9][0-9].png")):
        m = re.search(r"(\d{3})", f.stem)
        out.append((int(m.group(1)), f))
    if not out:
        out = [(a, kit / "model" / n) for n, a in REAL_VIEWS if (kit / "model" / n).is_file()]
    return out


def axis(alpha):
    """(cx, cy, lean radians of the long axis from vertical, length, width) of a mask's pixels."""
    import numpy as np
    ys, xs = np.nonzero(np.asarray(alpha) > 127)
    if len(xs) < 50:
        return None
    cx, cy = xs.mean(), ys.mean()
    dx, dy = xs - cx, ys - cy
    cov = np.cov(np.vstack([dx, dy]))
    w, v = np.linalg.eigh(cov)
    ux, uy = v[:, 1]                                   # the long axis
    if uy > 0:
        ux, uy = -ux, -uy                              # pointing up
    along = dx * ux + dy * uy
    across = -dx * uy + dy * ux
    q = lambda a, f: float(np.quantile(a, f))
    length = q(along, .995) - q(along, .005)
    width = q(across, .995) - q(across, .005)
    lean = math.atan2(ux, -uy)                         # 0 = upright, + = top leans right
    return cx, cy, lean, length, width


def place(cut, size, cx, cy, lean, length):
    """The cut-out scaled to `length` along its long axis, leaned by `lean`, centred at (cx, cy) on a
    transparent canvas of `size`."""
    from PIL import Image
    a = axis(cut.split()[-1])
    if not a:
        return None
    s = length / max(a[3], 1e-6)
    c = cut.resize((max(1, int(cut.width * s)), max(1, int(cut.height * s))), Image.LANCZOS)
    c = c.rotate(-math.degrees(lean - a[2]), resample=Image.BICUBIC, expand=True)
    b = axis(c.split()[-1])
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(c, (int(round(cx - b[0])), int(round(cy - b[1]))))
    return canvas


def overlap(a, b) -> float:
    import numpy as np
    A, B = np.asarray(a) > 127, np.asarray(b) > 127
    u = (A | B).sum()
    return float((A & B).sum() / u) if u else 0.0


def skin(rgb):
    """Pixels that read as skin (YCbCr window that holds deep to light skin)."""
    import numpy as np
    y, cb, cr = [np.asarray(ch, dtype=np.float32) for ch in rgb.convert("YCbCr").split()]
    return (cr > 133) & (cr < 180) & (cb > 77) & (cb < 135) & (y > 25)


def fill(rgb, hole):
    """Fill the hole from its surroundings: repeated blur that only writes into the hole."""
    import numpy as np
    from PIL import Image, ImageFilter
    img = np.asarray(rgb, dtype=np.float32).copy()
    known = ~hole
    if not hole.any():
        return rgb
    for r in (2, 4, 8, 16, 32):
        w = Image.fromarray((known * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(r))
        wv = np.asarray(w, dtype=np.float32)[..., None] / 255
        src = Image.fromarray((img * known[..., None]).clip(0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(r))
        sv = np.asarray(src, dtype=np.float32)
        est = np.where(wv > 1e-3, sv / np.maximum(wv, 1e-3), 0)
        newly = hole & (wv[..., 0] > 0.15) & ~known
        img[newly] = est[newly]
        known = known | newly
        if known.all():
            break
    return Image.fromarray(img.clip(0, 255).astype("uint8"))


def paste(picture, kit, out=None, what="the product", caller=None, found=None, mask=None, shadow=False) -> dict:
    import numpy as np
    from PIL import Image, ImageFilter
    kit = Path(kit)
    cuts = cutouts(kit)
    if not cuts:
        return {"ok": True, "skipped": "no turntable cut-outs in the kit"}
    im = Image.open(picture).convert("RGB")
    W, H = im.size
    f = found or _load("product_kit").detect(picture, what, caller=caller)
    if not f or not f.get("box"):
        return {"ok": True, "skipped": "no product in this picture"}
    mask = (mask or _load("product_check").product_mask(picture, f["box"])).resize((W, H))
    m = axis(mask)
    if not m:
        return {"ok": False, "why": ["the product's pixels could not be found"]}
    cx, cy, lean, length, width = m
    if (np.asarray(mask) > 127).mean() > MAX_SHARE:
        # the finder took something far bigger than the product (a head, the whole frame): never paste over it
        return {"ok": False, "why": [f"the found 'product' covers {(np.asarray(mask) > 127).mean():.0%} of the picture; that is not the product"]}
    facing = (f.get("facing") or "").lower()
    if facing == "back":
        pool = [(a, p) for a, p in cuts if 135 <= a <= 225]
    elif facing == "front":
        pool = [(a, p) for a, p in cuts if not 135 <= a <= 225]
    else:                                              # side / three-quarter / unsure: every angle is a candidate
        pool = cuts
    # the silhouette alone cannot tell the bristle face from the smooth back, or up from down: each fit is
    # also scored on how much its light and texture look like the drawn product's (2026-10-09: a shower
    # close-up showing the back was matched to the front, upside down)
    gray = np.asarray(im.convert("L").filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    Mb = np.asarray(mask) > 127
    best = None
    for a, p in pool:
        cut = Image.open(p).convert("RGBA")
        for flip in (0.0, math.pi):                    # the bristle end may point up or down in the picture
            pl = place(cut, (W, H), cx, cy, lean + flip, length)
            if pl is None:
                continue
            al = pl.split()[-1]
            o = overlap(al, mask)
            both = (np.asarray(al) > 127) & Mb
            look = 0.0
            if both.sum() > 200:
                g2 = np.asarray(pl.convert("L").filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
                x, y = gray[both], g2[both]
                x, y = x - x.mean(), y - y.mean()
                look = float((x * y).sum() / (math.sqrt((x * x).sum() * (y * y).sum()) + 1e-6))
            score = o + 0.6 * look
            if not best or score > best[4]:
                best = (o, a, flip, pl, score, look)
    if not best or best[0] < MIN_OVERLAP:
        return {"ok": False, "overlap": round(best[0], 3) if best else 0,
                "why": [f"the drawn thing does not match the real product at any angle (overlap {best[0]:.2f})" if best
                        else "no angle fitted"]}
    o, ang, flip, pl, _score, look = best
    A = np.asarray(pl.split()[-1]) > 127
    M = np.asarray(mask) > 127
    S = skin(im)
    # fingers in front: skin that is not the drawn product, where the real product would be
    hand = A & ~M & S
    # also skin INSIDE the drawn mask's edge band (SAM sometimes takes a fingertip)
    edge = np.asarray(mask.filter(ImageFilter.MinFilter(9))) <= 127
    hand |= A & M & edge & S
    # the drawn product's bulge outside the real outline: filled from around it
    bulge = M & ~np.asarray(pl.filter(ImageFilter.MaxFilter(5)).split()[-1]).astype(bool) & ~S
    base = fill(im, bulge)
    # light: the cut-out takes the drawn product's brightness and contrast where both are
    rgb = np.asarray(pl.convert("RGB"), dtype=np.float32)
    src = np.asarray(im, dtype=np.float32)
    both = A & M & ~S
    if both.sum() > 200:
        # brightness only — the drawn product's COLOUR is exactly what is not trusted
        lum = lambda a: a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        ls, lr = lum(src[both]), lum(rgb[both])
        gain = float(np.clip((ls.mean() + 1) / (lr.mean() + 1), 0.6, 1.6))
        gain = 0.5 + 0.5 * gain
        rgb = np.where(A[..., None], rgb * gain, rgb)
    # grain: the picture's own fine noise
    hf = src - np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32)
    sigma = float(hf[~M].std()) if (~M).any() else 0.0
    rgb = rgb + np.random.default_rng(7).normal(0, sigma * 0.8, rgb.shape)
    # the cut-out's own light fringe (the turntable backdrop) is trimmed off its edge before it is laid in
    alpha = np.asarray(pl.split()[-1].filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255
    alpha = np.where(hand, 0, alpha)
    hand_soft = np.asarray(Image.fromarray((hand * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float32) / 255
    alpha = alpha * (1 - hand_soft)
    base_v = np.asarray(base, dtype=np.float32)
    if shadow:
        # a resting product's shadows, made from its own real outline (never drawn by a model). Two layers, as a real
        # object on a surface has (2026-10-28): a tight dark CONTACT shadow where it touches, and a wide soft AMBIENT shadow the
        # room's light leaves around it; both darken only the surface, never the product
        out_a = Image.fromarray((A * 255).astype("uint8"))
        drop = lambda k: out_a.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -max(1, int(length * k))))
        contact = np.asarray(drop(0.012).filter(ImageFilter.GaussianBlur(max(1.5, length * 0.012))), dtype=np.float32) / 255
        ambient = np.asarray(drop(0.04).filter(ImageFilter.GaussianBlur(max(3, length * 0.09))), dtype=np.float32) / 255
        dark = np.clip(0.62 * contact + 0.38 * ambient, 0, 0.8)
        base_v = base_v * (1 - dark * (1 - alpha))[..., None]
        # light wrap: the surface's own colour bleeds a little onto the product's edge, so the edge belongs to the room
        ring = np.clip(alpha - np.asarray(Image.fromarray((alpha * 255).astype("uint8")).filter(ImageFilter.MinFilter(7)),
                                          dtype=np.float32) / 255, 0, 1)
        wrap = np.asarray(Image.fromarray(base_v.clip(0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(max(3, length * 0.03))),
                          dtype=np.float32)
        rgb = rgb * (1 - 0.35 * ring[..., None]) + wrap * (0.35 * ring[..., None])
    outv = base_v * (1 - alpha[..., None]) + rgb.clip(0, 255) * alpha[..., None]
    out = Path(out or picture)
    Image.fromarray(outv.clip(0, 255).astype("uint8")).save(out)
    return {"ok": True, "angle": ang, "upside_down": bool(flip), "lean": round(math.degrees(lean), 1),
            "overlap": round(o, 3), "look": round(look, 3), "file": str(out), "why": [],
            # where it lies, for a caller that lays a 3D render over the same spot (model-inputs ground_product)
            "centre": [round(float(cx), 1), round(float(cy), 1)], "length": round(float(length), 1),
            "width": round(float(width), 1), "lean_rad": round(float(lean + flip), 4)}


VENV = HERE.parents[1] / "local-studio" / ".venv" / "bin" / "python"


def run(picture, kit, out=None, what="the product", caller=None, shadow=False) -> dict:
    """From any Python: the product is found here (the vision key lives in this environment), the paste
    runs in local-studio's environment (numpy, beside the SAM 2 the mask already needs)."""
    import subprocess, sys
    if not cutouts(Path(kit)):
        return {"ok": True, "skipped": "no turntable cut-outs in the kit"}
    f = _load("product_kit").detect(picture, what, caller=caller)
    if not f or not f.get("box"):
        return {"ok": True, "skipped": "no product in this picture"}
    try:
        import numpy  # noqa: F401
        return paste(picture, kit, out, what, found=f, shadow=shadow)
    except ImportError:
        pass
    py = str(VENV) if VENV.exists() else sys.executable
    r = subprocess.run([py, str(HERE / "product_paste.py"), str(picture), "--kit", str(kit), "--what", what,
                        "--found", json.dumps(f)] + (["--out", str(out)] if out else []) + (["--shadow"] if shadow else []),
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout[r.stdout.find("{"):])
    except ValueError:
        return {"ok": False, "why": [f"the paste did not run: {(r.stderr or r.stdout)[-300:]}"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("picture"); ap.add_argument("--kit", required=True)
    ap.add_argument("--out"); ap.add_argument("--what", default="the product")
    ap.add_argument("--found", help="the product finder's answer, as JSON (skips finding it again)")
    ap.add_argument("--shadow", action="store_true", help="a resting product: lay its contact shadow from its real outline")
    x = ap.parse_args()
    if x.found:
        print(json.dumps(paste(x.picture, x.kit, x.out, x.what, found=json.loads(x.found), shadow=x.shadow), indent=1))
    else:
        print(json.dumps(run(x.picture, x.kit, x.out, x.what, shadow=x.shadow), indent=1))
