#!/usr/bin/env python3
"""Build one finished ad in the swiped format.

    compose_ad.py <run> <plate> <out> "LINE 1" "LINE 2" "LINE 3"

The format: wordmark centred at the top · a white-stroked square framing the
damage · the headline in a white box flush against the square's bottom edge,
sharing its left and right · the product as an outlined sticker rotated over
the box's corner.

**The square goes where the damage is, not where it was last time.** Every
plate puts the spots somewhere else, and a square at a fixed position frames
blank skin — worse than no square, because it points confidently at nothing.
"""
import subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
from find_spots import spot_centre

W, H = 768, 1344
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
BOX_H = 190           # the headline block
STROKE = 6


def sh(c):
    subprocess.run(c, check=False, capture_output=True)


def build(run, plate, out, lines, sticker, logo):
    run = Path(run)
    src = run / "iterations" / f"{plate}.png"
    fit = "/tmp/_fit.png"
    sh(["magick", str(src), "-resize", f"{W}x{H}^", "-gravity", "center",
        "-extent", f"{W}x{H}", fit])

    s = spot_centre(Path(fit), box_w_pct=55, top_limit=0.62)
    x, y, bw, bh = s["x"], s["y"], s["w"], s["h"]
    # keep the whole lockup on the frame
    x = max(64, min(x, W - bw - 64))
    y = max(300, min(y, H - bh - BOX_H - 150))

    a = "/tmp/_a.png"
    sh(["magick", fit,
        "-fill", "none", "-stroke", "white", "-strokewidth", str(STROKE),
        "-draw", f"rectangle {x},{y} {x+bw},{y+bh}",
        "-stroke", "none", "-fill", "white",
        "-draw", f"rectangle {x},{y+bh} {x+bw},{y+bh+BOX_H}", a])

    # Size the type to the box it has, rather than assuming 43pt fits. The
    # sticker overlaps the box's right corner, so the copy stops short of it —
    # a headline whose last two characters sit under the product is not a
    # headline, it is a mistake nobody chose.
    avail = bw - 56
    pt = 46
    while pt > 24:
        widest = 0
        for ln in lines:
            r = subprocess.run(
                ["magick", "-font", FONT, "-pointsize", str(pt),
                 f"label:{ln}", "-format", "%w", "info:"],
                capture_output=True, text=True)
            try:
                widest = max(widest, int(r.stdout.strip()))
            except ValueError:
                pass
        if widest <= avail:
            break
        pt -= 2

    b = "/tmp/_b.png"
    lead = int(pt * 1.16)
    cmd = ["magick", a, "-font", FONT, "-pointsize", str(pt),
           "-fill", "#141414", "-gravity", "northwest"]
    for i, ln in enumerate(lines):
        cmd += ["-annotate", f"+{x+28}+{y+bh+28+i*lead}", ln]
    cmd.append(b)
    sh(cmd)

    sh(["magick", b,
        "(", str(sticker), "-resize", "x440", ")",
        "-gravity", "northwest",
        # The sticker clips the box's corner — it does not sit on the copy.
        # Overlapping into the text is the difference between a designed
        # overlap and a mistake.
        # Anchored to the box's bottom-right corner, below the copy. The
        # sticker is rotated, so its corner juts further left than its
        # bounding box suggests — sitting it beside the text put it through
        # the last two characters of every line.
        # No left clamp. Clamping it back onto the frame dragged it into the
        # copy — a sticker bleeding off the right edge is normal for this
        # format, a sticker sitting on the headline is not.
        "-geometry", f"+{x+bw-56}+{y+bh+BOX_H-236}", "-composite",
        "(", str(logo), "-resize", "250x", ")",
        "-gravity", "north", "-geometry", "+0+76", "-composite",
        str(run / "finals" / f"{out}.png")])
    print(f"  {out}  square at {x},{y} (density {s['density']})")


if __name__ == "__main__":
    run, plate, out = sys.argv[1:4]
    lines = sys.argv[4:7]
    build(run, plate, out, lines, Path("/tmp/sticker-rot.png"),
          P.BRANDS / "<brand>/identity/logo-white.png")
