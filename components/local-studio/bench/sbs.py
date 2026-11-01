"""sbs.py out.jpg "label A" a.png "label B" b.png [...] — labelled side-by-side at one height."""
import sys
from PIL import Image, ImageDraw, ImageFont
out, rest = sys.argv[1], sys.argv[2:]
pairs = [(rest[i], rest[i + 1]) for i in range(0, len(rest), 2)]
H = int(__import__("os").environ.get("SBS_H", 900))
ims = []
for label, p in pairs:
    im = Image.open(p)
    if im.mode == "RGBA":  # show cut-outs on a checkerboard
        bg = Image.new("RGB", im.size, (200, 200, 200)); d = ImageDraw.Draw(bg); s = 32
        for y in range(0, im.height, s):
            for x in range(0, im.width, s):
                if (x // s + y // s) % 2: d.rectangle([x, y, x + s, y + s], fill=(150, 150, 150))
        bg.paste(im, (0, 0), im); im = bg
    im = im.convert("RGB"); ims.append((label, im.resize((int(im.width * H / im.height), H), Image.LANCZOS)))
W = sum(i.width for _, i in ims) + 16 * (len(ims) - 1)
o = Image.new("RGB", (W, H + 64), (16, 16, 20)); d = ImageDraw.Draw(o)
try: f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
except Exception: f = ImageFont.load_default()
x = 0
for label, im in ims:
    o.paste(im, (x, 64)); d.text((x + 12, 16), label, fill=(235, 235, 235), font=f); x += im.width + 16
o.save(out, quality=88)
