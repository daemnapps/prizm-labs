"""THE REAL LOGO — the image model never draws the brand's mark.

the owner, 2026-10-14: whenever an ad shows the brand as a mark it is the REAL
logo. The model drew the name as bold sans capitals; the real wordmark is
whatever the brand's kit holds. So the picture is made with the mark's place
left empty (`prompts/brand-mark-space-v1-owner.md`), the eyes find that place
(or a mark drawn anyway), the place is cleared to its own background, and the
brand's real wordmark is pasted: the light file on a dark ground, the dark file
on a light one, sized to the place.

    space_rule(brand)                       the rule for the picture prompt
    wordmark(brand, tone)                   the brand's real wordmark file, from its kit
    locate(picture, brand, ask, swipe=)     where the mark goes → pixel box | None
    put(picture, out, brand, box)           cleared and pasted → record
    apply(picture, out, brand, ask, swipe=) locate + put, or nothing when there is no place

The logo is found through the brand's kit (`context.logo_files`), never by a
path; nothing here names a brand. Stdlib + Pillow, Python 3.9.
"""
import json
from pathlib import Path

from . import context as C, prompting

TONES = {"light": ("white", "light", "reverse", "knockout"),
         "dark": ("black", "dark")}


def space_rule(brand):
    return prompting.body(prompting.latest("brand-mark-space")).replace(
        "{brand}", f"{brand} (or {brand.upper()})")


def wordmark(brand, tone):
    """The brand's wordmark raster for a ground. tone 'light' = a light mark for a
    dark ground. Prefers files named wordmark (not a submark or a combined
    lock-up), a raster with transparency, nearest the top of the kit."""
    files = [f for f in C.logo_files(brand) if f.suffix.lower() in (".png", ".webp")]
    words = TONES[tone]

    def score(f):
        n = f.name.lower()
        return (0 if "wordmark" in n else 1,
                0 if "submark" not in n else 1,
                0 if any(w in n for w in words) else 1,
                len(f.parts),
                -f.stat().st_size)
    ranked = sorted(files, key=score)
    if not ranked or "wordmark" not in ranked[0].name.lower() \
            or not any(w in ranked[0].name.lower() for w in words):
        raise FileNotFoundError(f"no {tone} wordmark in {brand}'s logo kit")
    return ranked[0]


def locate(picture, brand, ask, swipe=None):
    """The eyes' box for the mark, in pixels, or None when the picture has no place for one."""
    from PIL import Image
    q = prompting.body(prompting.latest("brand-mark-locate")).replace("{brand}", brand)
    images = ([Path(swipe)] if swipe else []) + [Path(picture)]
    raw = ask(images, q) or {}
    if isinstance(raw, list):                         # the eyes sometimes answer [ {...} ]
        raw = raw[0] if raw and isinstance(raw[0], dict) else {}
    b = raw.get("box_2d")
    if not b:
        return None, raw
    w, h = Image.open(picture).size
    y0, x0, y1, x1 = (float(v) for v in b)
    box = (x0 / 1000 * w, y0 / 1000 * h, x1 / 1000 * w, y1 / 1000 * h)
    if box[2] - box[0] < 8 or box[3] - box[1] < 4:
        return None, raw
    return box, raw


def _clear(img, box, pad):
    """Fill the box from the ground just outside it — a horizontal blend of the
    left and right edge colours (the hand fix), averaged with the vertical blend
    of the top and bottom edges so a lit ground keeps its light — softened, and
    feathered into the picture so no patch shows."""
    from PIL import Image, ImageDraw, ImageFilter
    f = max(3, pad)                                   # the feather lies OUTSIDE the cleared box
    l, t, r, b = (int(round(v)) for v in box)
    l, t = max(2, l - pad - f), max(2, t - pad - f)
    r, b = min(img.width - 3, r + pad + f), min(img.height - 3, b + pad + f)
    rgb = img.convert("RGB")
    W, H = r - l, b - t
    left = [rgb.getpixel((l - 2, y)) for y in range(t, b)]
    right = [rgb.getpixel((r + 2, y)) for y in range(t, b)]
    top = [rgb.getpixel((x, t - 2)) for x in range(l, r)]
    bot = [rgb.getpixel((x, b + 2)) for x in range(l, r)]
    fill = Image.new("RGB", (W, H))
    px = fill.load()
    for yi in range(H):
        fy = yi / float(max(1, H - 1))
        for xi in range(W):
            fx = xi / float(max(1, W - 1))
            px[xi, yi] = tuple(int(0.5 * (left[yi][k] * (1 - fx) + right[yi][k] * fx)
                                   + 0.5 * (top[xi][k] * (1 - fy) + bot[xi][k] * fy))
                               for k in range(3))
    fill = fill.filter(ImageFilter.GaussianBlur(max(2, H * 0.15)))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle((f // 2, f // 2, W - f // 2, H - f // 2), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(1, f // 3)))
    out = rgb.copy()
    out.paste(fill, (l, t), mask)
    return out, (l + f, t + f, r - f, b - f)


def _text_extent(img, box):
    """The drawn letters often run past the eyes' box. Grow the box to every
    pixel on the same rows (and half the box's width either side) that stands
    out from the ground — so no letter is left to ghost through the fill."""
    l, t, r, b = box
    w, h = r - l, b - t
    L, R = max(0, int(l - 0.5 * w)), min(img.width, int(r + 0.5 * w))
    T, B = max(0, int(t - 0.15 * h)), min(img.height, int(b + 0.15 * h))
    reg = img.convert("L").crop((L, T, R, B))
    vals = sorted(reg.getdata())
    med = vals[len(vals) // 2]
    hit = reg.point(lambda v: 255 if abs(v - med) > 45 else 0)
    bb = hit.getbbox()
    if not bb:
        return box
    return (min(l, L + bb[0]), min(t, T + bb[1]), max(r, L + bb[2]), max(b, T + bb[3]))


def _luma(img, box):
    from PIL import ImageStat
    l, t, r, b = (int(v) for v in box)
    return ImageStat.Stat(img.crop((l, t, r, b)).convert("L")).mean[0]


def put(picture, out, brand, box, drawn=True):
    """Clear the place (when a mark was drawn there) and paste the real wordmark
    on it, light on dark / dark on light, as tall as the place and centred."""
    from PIL import Image
    img = Image.open(picture).convert("RGB")
    pad = int(max(4, (box[3] - box[1]) * 0.25))
    if drawn:
        img, cleared = _clear(img, _text_extent(img, box), pad)
    else:
        cleared = tuple(int(v) for v in box)
    tone = "light" if _luma(img, cleared) < 128 else "dark"
    src = wordmark(brand, tone)
    mark = Image.open(src).convert("RGBA")
    mark = mark.crop(mark.getchannel("A").getbbox() or (0, 0, mark.width, mark.height))
    bw, bh = box[2] - box[0], box[3] - box[1]
    s = min(bw / float(mark.width), bh / float(mark.height))
    mark = mark.resize((max(1, int(mark.width * s)), max(1, int(mark.height * s))), Image.LANCZOS)
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    pos = (int(round(cx - mark.width / 2.0)), int(round(cy - mark.height / 2.0)))
    base = img.convert("RGBA")
    base.alpha_composite(mark, pos)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out)
    return {"file": str(out), "logo": str(src), "tone": tone, "box": [round(v) for v in box],
            "cleared": list(cleared) if drawn else None, "size": list(mark.size)}


def apply(picture, out, brand, ask, swipe=None):
    """Locate and paste. Returns the record, or {"skipped": why} when there is no place."""
    box, raw = locate(picture, brand, ask, swipe)
    if box is None:
        return {"skipped": raw.get("why") or "no brand mark place in this picture", "raw": raw}
    rec = put(picture, out, brand, box, drawn=raw.get("drawn", True) is not False)
    rec["why"] = raw.get("why")
    return rec
