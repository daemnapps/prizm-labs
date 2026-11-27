#!/usr/bin/env python3
"""Where the damage actually is on this plate.

The format frames the damage in a stroked square. The damage is in a different
place on every plate, so a square at a fixed position frames blank skin — which
is worse than no square, because it points confidently at nothing.

Finds the densest cluster of spots: darker-than-surrounding pixels, blurred to
mass them, then the strongest region above the copy block.
"""
import subprocess, sys
from pathlib import Path


def sh(c):
    return subprocess.run(c, capture_output=True, text=True).stdout


def spot_centre(plate, box_w_pct=55, top_limit=0.72, top_from=0.18):
    """`top_from`/`top_limit` bound the search to the band the design leaves
    free. Searching the whole frame finds the damage and then puts the box on
    top of the wordmark — measured 2026-09-02, five ads in six."""
    w, h = map(int, sh(["magick", "identify", "-format", "%w %h", str(plate)]).split())
    # spots are local dark patches: subtract a heavy blur, keep what is darker
    m = "/tmp/_spots.png"
    subprocess.run(["magick", str(plate), "-colorspace", "gray",
                    "(", "+clone", "-blur", "0x28", ")",
                    "-compose", "minus_dst", "-composite",
                    "-auto-level", "-threshold", "42%",
                    "-morphology", "close", "disk:4",
                    "-blur", "0x26", "-auto-level", m], check=False)
    # search a grid for the densest window
    bw = int(w * box_w_pct / 100)
    bh = int(bw * 0.72)
    best, bx, by = -1, (w - bw) // 2, int(h * 0.42)
    for gy in range(int(h * top_from), max(int(h * top_from) + 1,
                    int(h * top_limit) - bh), max(24, bh // 6)):
        for gx in range(0, w - bw, max(24, bw // 6)):
            v = sh(["magick", m, "-crop", f"{bw}x{bh}+{gx}+{gy}", "+repage",
                    "-format", "%[fx:mean]", "info:"])
            try:
                v = float(v)
            except ValueError:
                continue
            if v > best:
                best, bx, by = v, gx, gy
    return dict(x=bx, y=by, w=bw, h=bh, density=round(best, 4),
                frame_w=w, frame_h=h)


if __name__ == "__main__":
    r = spot_centre(Path(sys.argv[1]))
    print(f"{r['x']},{r['y']} {r['w']}x{r['h']}  density {r['density']}")
