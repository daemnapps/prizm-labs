#!/usr/bin/env python3
"""Where the pedestal's top surface actually is on this plate.

The format stands the product on a pedestal. The pedestal is a different
height and width in every generated plate, so a product placed at a fixed
percentage floats in front of it instead of standing on it — shipped that
way on 2026-09-02.

Finds the plinth: the central mass that is darker than the ground around it,
then its top edge and its width there. The product is stood on that.
"""
import subprocess, sys
from pathlib import Path


def sh(c):
    return subprocess.run(c, capture_output=True, text=True).stdout


def pedestal_top(plate, centre=0.56, search=(0.30, 0.80)):
    """Returns (top_y, left_x, right_x, h, w) in the plate's own pixels."""
    w, h = map(int, sh(["magick", "identify", "-format", "%w %h",
                        str(plate)]).split())
    # The GOLD TRIM is the signal, not darkness. The backdrop is charcoal
    # clay too, so a dark mask finds the sky and reports the same answer for
    # every plate — measured 2026-09-02, three plates, one number.
    # Gold: bright, warm, blue-poor.
    m = "/tmp/_ped.png"
    subprocess.run(["magick", str(plate),
                    "-fuzz", "26%", "-fill", "white", "-opaque", "#C8A24A",
                    "-fill", "black", "+opaque", "white",
                    "-colorspace", "gray", "-threshold", "50%",
                    "-morphology", "close", "disk:3", m], check=False)
    x0, x1 = int(w * (0.5 - centre / 2)), int(w * (0.5 + centre / 2))
    y0, y1 = int(h * search[0]), int(h * search[1])
    band = x1 - x0
    top = None
    for y in range(y0, y1, 4):
        v = sh(["magick", m, "-crop", f"{band}x4+{x0}+{y}", "+repage",
                "-format", "%[fx:mean]", "info:"]).strip()
        try:
            if float(v) > 0.06:          # a run of trim across the row
                top = y
                break
        except ValueError:
            continue
    if top is None:
        return None
    # its width at the top edge
    row = sh(["magick", m, "-crop", f"{w}x6+0+{top+6}", "+repage",
              "-format", "%[fx:mean]", "info:"])
    left, right = x0, x1
    for x in range(x0, x1, 4):
        v = sh(["magick", m, "-crop", f"4x10+{x}+{top+8}", "+repage",
                "-format", "%[fx:mean]", "info:"]).strip()
        try:
            if float(v) > 0.25:
                left = x
                break
        except ValueError:
            continue
    for x in range(x1, x0, -4):
        v = sh(["magick", m, "-crop", f"4x10+{x-4}+{top+8}", "+repage",
                "-format", "%[fx:mean]", "info:"]).strip()
        try:
            if float(v) > 0.25:
                right = x
                break
        except ValueError:
            continue
    return dict(top=top, left=left, right=right, frame_w=w, frame_h=h,
                top_pct=round(100 * top / h, 1),
                left_pct=round(100 * left / w, 1),
                right_pct=round(100 * right / w, 1))


if __name__ == "__main__":
    r = pedestal_top(Path(sys.argv[1]))
    print(r if r else "no pedestal found")
