#!/usr/bin/env python3
"""4:5 in, 9:16 out — solid ink bands, never the frame's own edges.

    pad.py <in.png> [<out.png>]        pad (or re-pad) one picture
    pad.py --check <png>               0 if the bands are solid, 1 if smeared

Ruled 2026-09-09 by Damon after a two-panel shipped with its top row of
pixels stretched into a 15% band — "slop". The band is a flat ground now:
ink #1A1A1A, 1856×3300, 490 px top and bottom. A picture that is already
9:16 is re-padded from its centre 4:5, so the content never changes — only
the bands do. SAFE-ZONE.md's flat-band rule wins; PIPELINE.md's "frame's own
edges" wording is retired.
"""
import sys
from pathlib import Path
from PIL import Image, ImageStat

W, H = 1856, 3300
INK = (26, 26, 26)
BAND = (H - W * 5 // 4) // 2          # 490


def content_4x5(im):
    """The 4:5 picture inside whatever we were handed."""
    w, h = im.size
    if abs(h / w - 1.25) < 0.02:
        return im
    if h / w > 1.4:                                   # padded 9:16 — take the centre
        ch = int(w * 5 / 4); top = (h - ch) // 2
        return im.crop((0, top, w, top + ch))
    raise SystemExit(f"{w}x{h} is neither 4:5 nor 9:16 — nothing to pad")


def pad(src, dst=None):
    im = Image.open(src).convert("RGB")
    c = content_4x5(im).resize((W, W * 5 // 4), Image.LANCZOS)
    out = Image.new("RGB", (W, H), INK)
    out.paste(c, (0, BAND))
    out.save(dst or src, "PNG")
    return dst or src


def solid(png, tol=6.0):
    """True when both bands are one flat colour — a smeared band has variance."""
    im = Image.open(png).convert("RGB"); w, h = im.size
    if h / w < 1.4:
        return True                                   # not padded, nothing to judge
    band = int(h * BAND / H)
    for box in ((0, 0, w, band - 4), (0, h - band + 4, w, h)):
        st = ImageStat.Stat(im.crop(box))
        if max(st.stddev) > tol:
            return False
    return True


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--check":
        ok = solid(a[1]); print("solid" if ok else "SMEARED band"); sys.exit(0 if ok else 1)
    print(pad(a[0], a[1] if len(a) > 1 else None))
