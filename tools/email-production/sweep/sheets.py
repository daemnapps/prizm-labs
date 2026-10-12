#!/usr/bin/env python3
"""Contact sheets — every email's export beside its rebuild, small, one
image per board — so a whole board can be read in one look and the engine
defects found by family, not one email at a time.

    python3 sweep/sheets.py [board ...]     -> results/format-bank/<board>/sheet.png
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

HERE = Path(__file__).resolve().parent.parent
import os as _os
root = Path(_os.environ["FORMAT_BANK_DIR"]).resolve() if _os.environ.get("FORMAT_BANK_DIR") else HERE / "results" / "format-bank"
URLBASE = f"/results/{root.name}"
SCALE = 0.36
CELL_H = 1250
PER = 4


def trim(im):
    bg = Image.new("RGB", im.size, im.getpixel((0, im.size[1] - 1)))
    bbox = ImageChops.difference(im, bg).getbbox()
    return im.crop((0, 0, im.size[0], min(bbox[3] + 30, im.size[1]))) if bbox else im


def sheet(board):
    d = root / board
    rects = json.loads((d / "rects.json").read_text()) if (d / "rects.json").is_file() else []
    pairs = []
    for f in sorted(d.glob("[0-9][0-9]-clean.png")):
        i = int(f.stem[:2])
        clean = Image.open(f).convert("RGB")
        # the export picture the rebuild was read against (named in its spec)
        spec_f = d / f"{i:02d}-spec.json"
        shot = None
        if spec_f.is_file():
            try:
                shot = json.loads(spec_f.read_text()).get("export_picture")
            except Exception:
                shot = None
        orig = d / (shot or f"{i:02d}.png")
        o = Image.open(orig).convert("RGB") if orig.is_file() else None
        pairs.append((i, o, trim(clean)))
    if not pairs:
        return None
    cols = 2
    made = []
    for pg in range(0, len(pairs), PER):
        chunk = pairs[pg:pg + PER]
        cw = int(820 * 2 * SCALE) + 30
        rows_n = (len(chunk) + cols - 1) // cols
        W, H = cols * cw + 20, rows_n * (CELL_H + 40) + 20
        out = Image.new("RGB", (W, H), (30, 32, 30))
        dr = ImageDraw.Draw(out)
        for k, (i, o, c) in enumerate(chunk):
            x0 = 20 + (k % cols) * cw
            y0 = 20 + (k // cols) * (CELL_H + 40)
            dr.text((x0, y0), f"#{i:02d}  export | rebuild", fill=(200, 207, 173))
            y0 += 16
            if o is not None:
                oo = o.resize((int(o.size[0] * SCALE), int(o.size[1] * SCALE)))
                out.paste(oo.crop((0, 0, oo.size[0], min(oo.size[1], CELL_H))), (x0, y0))
            cc = c.resize((int(c.size[0] * SCALE), int(c.size[1] * SCALE)))
            out.paste(cc.crop((0, 0, cc.size[0], min(cc.size[1], CELL_H))), (x0 + int(820 * SCALE) + 10, y0))
        f = d / f"sheet-{pg // PER + 1:02d}.png"
        out.save(f); made.append(f)
    return made


if __name__ == "__main__":
    boards = sys.argv[1:] or sorted(p.name for p in root.iterdir() if p.is_dir())
    for b in boards:
        p = sheet(b)
        print(b, "->", p)
