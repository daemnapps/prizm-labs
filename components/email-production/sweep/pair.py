#!/usr/bin/env python3
"""One email at 1:1, export beside rebuild, cropped to a band — the
side-by-side the eye needs to call out centring, section breaks and fills.

    python3 sweep/pair.py <board> <NN> [y0] [y1]   -> scratch pair-<board>-NN-y0.png
"""
import json, os, sys
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent.parent
import os as _os
root = Path(_os.environ["FORMAT_BANK_DIR"]).resolve() if _os.environ.get("FORMAT_BANK_DIR") else HERE / "results" / "format-bank"
URLBASE = f"/results/{root.name}"
OUT = Path(os.environ.get("PAIR_OUT", "/private/tmp/claude-501/-Users-damondixon-Projects-ai-workspace/e9ec6931-750e-46f4-abfe-c324e2c720f1/scratchpad"))

board, i = sys.argv[1], int(sys.argv[2])
y0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
y1 = int(sys.argv[4]) if len(sys.argv) > 4 else y0 + 1400
d = root / board
spec = json.loads((d / f"{i:02d}-spec.json").read_text())
shot = spec.get("export_picture") or f"{i:02d}.png"
a = Image.open(d / shot).convert("RGB")
b = Image.open(d / f"{i:02d}-clean.png").convert("RGB")
W = max(a.size[0], b.size[0])
h = y1 - y0
out = Image.new("RGB", (W * 2 + 40, h + 30), (30, 32, 30))
dr = ImageDraw.Draw(out)
dr.text((10, 8), f"{board} #{i:02d}  export  y{y0}-{y1}", fill=(200, 207, 173))
dr.text((W + 50, 8), "rebuild", fill=(200, 207, 173))
out.paste(a.crop((0, y0, a.size[0], min(y1, a.size[1]))), (0, 30))
out.paste(b.crop((0, y0, b.size[0], min(y1, b.size[1]))), (W + 40, 30))
# a hairline every 200px so both sides read on one ruler
for yy in range(0, h, 200):
    dr.line([(0, 30 + yy), (W * 2 + 40, 30 + yy)], fill=(70, 74, 70), width=1)
    dr.text((W + 4, 32 + yy), str(y0 + yy), fill=(120, 126, 110))
f = OUT / f"pair-{board}-{i:02d}-{y0}.png"
out.save(f); print(f)
