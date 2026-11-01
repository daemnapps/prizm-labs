"""THE PRODUCT PASS — the product in a made picture becomes the real product,
rendered from its kit's model (product_kit.py), never a drawn one (the owner,
2026-10-02: "eliminate all product slop … not even just for these tubes …
at scale").

    python3 product_pass.py <picture.png> --kit <kit.json> --out <out.png> [--what "the skincare tube"]

1. find   the drawn product: its box, lean and which side faces the camera
          (product_kit.detect)
2. render the kit's model facing the same way, at the box's size, leaned the
          same, on a transparent background (Blender, machine/blender/<kind>.py)
3. place  it over the drawn one; the fingers holding it stay on top (skin and
          nail tones inside the box are kept from the picture)
4. light  the render takes the picture's light: its colour, brightness and
          contrast matched to the drawn product's own pixels, plus the
          picture's grain
5. record what was done in <out>.json for the check (product_check.py)
Brand-agnostic: everything about the product comes from its kit.
"""
from __future__ import annotations

import argparse, json, random, subprocess, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"


def _load(name):
    import importlib.util as u
    sp = u.spec_from_file_location(name, HERE / f"{name}.py"); m = u.module_from_spec(sp); sp.loader.exec_module(m); return m


def finger_mask(img, box):
    """Inside the box: skin and painted-nail tones are fingers (kept on top)."""
    from PIL import Image, ImageFilter
    W, H = img.size; x0, y0, x1, y1 = [int(v) for v in (box[0] * W, box[1] * H, box[2] * W, box[3] * H)]
    m = Image.new("L", img.size, 0); mp = m.load(); px = img.load()
    for y in range(max(0, y0 - 4), min(H, y1 + 4)):
        for x in range(max(0, x0 - 4), min(W, x1 + 4)):
            r, g, b = px[x, y][:3]
            if (r - b > 62 and r - g > 28) or (r > 120 and r - g > 55):   # skin, red/pink nails
                mp[x, y] = 255
    return m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))


def render(kit_path, out_png, yaw, w, h):
    blend = HERE / "blender" / (json.loads(Path(kit_path).read_text()).get("kind", "tube") + ".py")
    subprocess.run([BLENDER, "-b", "-P", str(blend), "--", str(kit_path), str(out_png), str(yaw), "0", str(w), str(h), "1"],
                   check=True, capture_output=True)


def match_light(rend, img, box):
    """Shift the render's colour stats to the drawn product's own pixels."""
    from PIL import Image, ImageStat
    W, H = img.size
    region = img.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H))).convert("RGB")
    rs = ImageStat.Stat(rend.convert("RGB"), mask=rend.split()[3].point(lambda v: 255 if v > 200 else 0))
    ts = ImageStat.Stat(region)
    out = []
    for i, ch in enumerate(rend.convert("RGB").split()):
        g = (ts.stddev[i] / max(rs.stddev[i], 1)) ** 0.5           # half-way contrast match
        out.append(ch.point(lambda v, i=i, g=g: max(0, min(255, int((v - rs.mean[i]) * g + ts.median[i] * 0.6 + rs.mean[i] * 0.4)))))
    rgb = Image.merge("RGB", out)
    rgb.putalpha(rend.split()[3]); return rgb


def grain(im, amount=5):
    from PIL import Image
    px = im.load(); W, H = im.size; rnd = random.Random(7)
    for y in range(H):
        for x in range(W):
            p = px[x, y]
            if len(p) == 4 and p[3] == 0:
                continue
            n = rnd.randint(-amount, amount)
            px[x, y] = tuple(max(0, min(255, c + n)) for c in p[:3]) + ((p[3],) if len(p) == 4 else ())
    return im


def swap(picture, kit_path, out, what="the product", caller=None):
    from PIL import Image
    kit = json.loads(Path(kit_path).read_text())
    img = Image.open(picture).convert("RGB"); W, H = img.size
    found = _load("product_kit").detect(picture, what, caller=caller)
    x0, y0, x1, y1 = found["box"]; bw, bh = (x1 - x0) * W, (y1 - y0) * H
    yaw = {"front": 0, "three-quarter": 30, "side": 80, "back": 180}.get(found.get("facing") or "front", 0)
    with tempfile.TemporaryDirectory() as td:
        rp = Path(td) / "r.png"
        render(kit_path, rp, yaw, 1000, 1250)
        rend = Image.open(rp).convert("RGBA")
    rend = rend.crop(rend.split()[3].getbbox())
    # the drawn product's height sets the size; the check judges it against the hand
    s = bh / rend.height; rend = rend.resize((max(1, int(rend.width * s)), max(1, int(bh))), Image.LANCZOS)
    if abs(found.get("angle") or 0) > 1:
        rend = rend.rotate(-found["angle"], resample=Image.BICUBIC, expand=True)
    rend = grain(match_light(rend, img, found["box"]))
    cx, cy = (x0 + x1) / 2 * W, (y0 + y1) / 2 * H
    pos = (int(cx - rend.width / 2), int(cy - rend.height / 2))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); layer.paste(rend, pos, rend)
    fingers = finger_mask(img, found["box"])
    a = layer.split()[3]
    from PIL import ImageChops
    a = ImageChops.multiply(a, ImageChops.invert(fingers))
    res = Image.composite(layer.convert("RGB"), img, a)
    res.save(out)
    rec = {"picture": str(picture), "kit": str(kit_path), "found": found, "yaw": yaw, "placed_px": [pos[0], pos[1], rend.width, rend.height]}
    Path(str(out) + ".json").write_text(json.dumps(rec, indent=1))
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("picture"); ap.add_argument("--kit", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--what", default="the product")
    x = ap.parse_args()
    print(json.dumps(swap(x.picture, x.kit, x.out, x.what), indent=1))
