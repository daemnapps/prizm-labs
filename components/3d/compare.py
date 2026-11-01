"""compare.py <local.png> <paid.png> <out.jpg> — side-by-side with labels."""
import sys
from PIL import Image, ImageDraw, ImageFont
a, b = Image.open(sys.argv[1]).convert("RGB"), Image.open(sys.argv[2]).convert("RGB")
h = 900
a, b = a.resize((int(a.width * h / a.height), h)), b.resize((int(b.width * h / b.height), h))
out = Image.new("RGB", (a.width + b.width + 20, h + 70), (18, 18, 22))
out.paste(a, (0, 70)); out.paste(b, (a.width + 20, 70))
d = ImageDraw.Draw(out)
try:
    f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
except Exception:
    f = ImageFont.load_default()
d.text((20, 18), "LOCAL (free, TRELLIS.2 on this Mac)", fill=(240, 240, 240), font=f)
d.text((a.width + 40, 18), "PAID (Meshy via Higgsfield)", fill=(240, 240, 240), font=f)
out.save(sys.argv[3], quality=90)
