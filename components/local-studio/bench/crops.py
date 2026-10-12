"""crops.py out.jpg x,y,w,h "label" img [...] — same region (in ORIGINAL pixels) from each image,
scaled to its own resolution, shown at one size. Pixel-peeping sheet for upscalers."""
import sys
from PIL import Image, ImageDraw, ImageFont
out, box, rest = sys.argv[1], list(map(int, sys.argv[2].split(","))), sys.argv[3:]
x, y, w, h = box
S = 560
f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
tiles = []
base_w = None
for i in range(0, len(rest), 2):
    label, p = rest[i], rest[i + 1]
    im = Image.open(p).convert("RGB")
    if base_w is None: base_w = im.width
    k = im.width / base_w
    c = im.crop((int(x * k), int(y * k), int((x + w) * k), int((y + h) * k))).resize((S, int(S * h / w)), Image.NEAREST if k == 1 else Image.LANCZOS)
    tiles.append((f"{label}  ({im.width}×{im.height})", c))
o = Image.new("RGB", (len(tiles) * (S + 12), tiles[0][1].height + 48), (16, 16, 20)); d = ImageDraw.Draw(o)
for i, (l, t) in enumerate(tiles):
    o.paste(t, (i * (S + 12), 48)); d.text((i * (S + 12) + 8, 12), l, fill=(235, 235, 235), font=f)
o.save(out, quality=90)
