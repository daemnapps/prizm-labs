#!/usr/bin/env python3
"""product_front.py — a product's front view, big, cut from its own casting sheet (2026-11-25).

    product_front.py <product-sheet.png> <out.png>

On the sheet the front view is a few hundred pixels wide and its label is a smudge to a clip model: a paid edit sent the sheet
alone came back with an invented brand name; the same edit sent this picture came back with the right one. The sheet still
carries the shape from every side; this carries the printed words. Every sheet is the one grid (product_sheet.py), so the cut
is the same for all; a sheet of another width is scaled. Nothing is drawn. Needs ffmpeg. Python 3.9, standard library.
"""
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

GRID = 1656
CELL = (520, 506, 22, 114)                        # width, height, x, y of the FRONT tile on a 1656-wide sheet


def front(sheet, out=None):
    """The front view's own file. With no `out`, one kept by the sheet's own bytes in this machine's temp folder."""
    sheet, kept = Path(sheet), out is None
    out = Path(out) if out else Path(tempfile.gettempdir()) / "product-fronts" / (hashlib.sha256(sheet.read_bytes()).hexdigest()[:16] + ".png")
    if kept and out.is_file() and out.stat().st_size:
        return out
    w = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width", "-of", "csv=p=0", str(sheet)],
                           capture_output=True, text=True, check=True).stdout.strip().strip(","))
    k = w / GRID
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(sheet), "-vf",
                    "crop=%d:%d:%d:%d,scale=-2:1600:flags=lanczos" % tuple(round(x * k) for x in CELL), "-frames:v", "1", str(out)], check=True)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    print(front(sys.argv[1], sys.argv[2]))
