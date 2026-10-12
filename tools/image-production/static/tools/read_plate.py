#!/usr/bin/env python3
"""What is actually in this picture, in numbers.

    read_plate.py <plate>

The layout has been placing type at fixed percentages without ever looking
at the picture, and the picture has been generated without knowing where the
type would go. Two blind processes stapled together — which is why a
headline lands on a rock and nothing notices.

This is the eye. It answers three things a designer answers by looking:

  where is the subject      the busiest, most detailed region
  where is it quiet         large areas of low detail, ranked
  is it worth building on   does it have a subject and a quiet area at all

Everything is measured on a grid of the plate's own pixels, so it works on
any picture from any brand.
"""
import subprocess, sys
from pathlib import Path

GRID_W, GRID_H = 12, 20          # cells across and down


def sh(c):
    return subprocess.run(c, capture_output=True, text=True).stdout


def detail_map(plate):
    """Local detail per cell: edges, not brightness. A dark busy rock and a
    bright busy leaf are both busy; a smooth dark backdrop is not."""
    w, h = map(int, sh(["magick", "identify", "-format", "%w %h",
                        str(plate)]).split())
    # Standard deviation of the grey, not a normalised edge map. Auto-level
    # rescales the whole image so every cell came back the same number —
    # measured 2026-09-03, twelve cells, four identical decimals.
    e = "/tmp/_edges.png"
    subprocess.run(["magick", str(plate), "-colorspace", "gray", e],
                   check=False)
    cw, ch = w // GRID_W, h // GRID_H
    cells = []
    for gy in range(GRID_H):
        row = []
        for gx in range(GRID_W):
            v = sh(["magick", e, "-crop", f"{cw}x{ch}+{gx*cw}+{gy*ch}",
                    "+repage", "-format",
                    "%[fx:standard_deviation]", "info:"]).strip()
            try:
                row.append(float(v))
            except ValueError:
                row.append(0.0)
        cells.append(row)
    return cells, w, h


def rect(cells, gy0, gy1, gx0=0, gx1=GRID_W):
    n = (gy1 - gy0) * (gx1 - gx0)
    return sum(cells[y][x] for y in range(gy0, gy1)
               for x in range(gx0, gx1)) / max(n, 1)


def read(plate):
    cells, w, h = detail_map(plate)
    flat = [v for row in cells for v in row]
    busiest = max(flat)

    # the subject: the densest 3x3 block of cells
    best, sy, sx = -1, 0, 0
    for y in range(GRID_H - 2):
        for x in range(GRID_W - 2):
            v = rect(cells, y, y + 3, x, x + 3)
            if v > best:
                best, sy, sx = v, y, x

    # quiet bands: full-width horizontal runs, ranked by how calm they are.
    # Type is set in bands, so bands are what matter — not isolated cells.
    bands = []
    for y0 in range(GRID_H - 2):
        for y1 in range(y0 + 3, min(y0 + 8, GRID_H + 1)):
            bands.append({
                "top_pct": round(100 * y0 / GRID_H, 1),
                "bottom_pct": round(100 * y1 / GRID_H, 1),
                "detail": round(rect(cells, y0, y1), 4),
                "rows": y1 - y0,
            })
    bands.sort(key=lambda b: (b["detail"], -b["rows"]))

    return {
        "frame": [w, h],
        "subject": {
            "top_pct": round(100 * sy / GRID_H, 1),
            "bottom_pct": round(100 * (sy + 3) / GRID_H, 1),
            "left_pct": round(100 * sx / GRID_W, 1),
            "right_pct": round(100 * (sx + 3) / GRID_W, 1),
            "detail": round(best, 4),
        },
        "quiet_bands": bands[:6],
        "busiest_cell": round(busiest, 4),
        "mean_detail": round(sum(flat) / len(flat), 4),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(read(Path(sys.argv[1])), indent=1))
