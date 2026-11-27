"""Change a line of words that sits on a flat ground, in code (2026-11-23).

A winner made with its words painted into the picture (a carousel slide) has no type layer to edit. When a line sits on
a flat ground (a solid colour field, or crushed near-black), changing it is the words step, not a new picture: the old
line's box is filled with the ground around it, and the new line is set in its place in a matching face, size and
colour, centred where the old one was. Nothing is generated. A ground that is not flat is refused (`flat_enough`), so
this never paints over a photograph.

    from image_production import flat_caption as FC
    FC.replace("slide-07.png", "out.png", box=(566, 1380, 1040, 1416), text="( FLEX STARTING AT $49 )",
               font="/System/Library/Fonts/Avenir Next.ttc#2")   # "path#index" picks a face in a collection

Also `recolour(picture, out, src, dst, tol)`: a flat ground colour changed to another, only where it is the ground
(connected to the frame edge or to a field of that colour), so the same colour inside a photo is left alone.
"""
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _ring(im, box, pad):
    l, t, r, b = box
    W, H = im.size
    px = im.load()
    pts = []
    for x in range(max(0, l - pad), min(W, r + pad)):
        for y in (max(0, t - pad), min(H - 1, b + pad)):
            pts.append(px[x, y])
    for y in range(max(0, t - pad), min(H, b + pad)):
        for x in (max(0, l - pad), min(W - 1, r + pad)):
            pts.append(px[x, y])
    return pts


def ground(im, box, pad=6):
    """The ground colour around `box`, and how flat it is (largest channel spread)."""
    pts = _ring(im.convert("RGB"), box, pad)
    med = tuple(sorted(p[i] for p in pts)[len(pts) // 2] for i in range(3))
    spread = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3))
    return med, spread


def flat_enough(im, box, limit=40):
    return ground(im, box)[1] <= limit


def ink_box(im, box, is_ink):
    """The tight box of the old line's letters inside `box` (`is_ink(rgb)`), or None."""
    px = im.convert("RGB").load()
    l, t, r, b = box
    xs, ys = [], []
    for y in range(t, b):
        for x in range(l, r):
            if is_ink(px[x, y]):
                xs.append(x)
                ys.append(y)
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1) if xs else None


def fill_between(im, box, pad=4, band=3):
    """Fill `box` from the ground around it: each pixel is blended from the ground just above and below it in its
    column and just left and right of it in its row, so a gentle gradient or grain in the ground carries through and no
    flat patch shows."""
    l, t, r, b = box
    W, H = im.size
    px = im.load()

    def avg(pts):
        pts = [px[x, y] for x, y in pts if 0 <= x < W and 0 <= y < H]
        return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3)) if pts else (0, 0, 0)
    top = [avg([(x, t - pad - k) for k in range(band)]) for x in range(l, r)]
    bot = [avg([(x, b + pad + k) for k in range(band)]) for x in range(l, r)]
    lef = [avg([(l - pad - k, y) for k in range(band)]) for y in range(t, b)]
    rig = [avg([(r + pad + k, y) for k in range(band)]) for y in range(t, b)]
    for y in range(t, b):
        v = (y - t) / max(1, b - t - 1)
        for x in range(l, r):
            u = (x - l) / max(1, r - l - 1)
            a = tuple(top[x - l][i] * (1 - v) + bot[x - l][i] * v for i in range(3))
            c = tuple(lef[y - t][i] * (1 - u) + rig[y - t][i] * u for i in range(3))
            px[x, y] = tuple(round((a[i] + c[i]) / 2) for i in range(3))


def replace(picture, out, box, text, font, color=(255, 255, 255), cap_px=None, limit=40):
    """Fill `box` with its ground and set `text` centred on it. `cap_px` is the height of a capital H (default: the box's
    height). Raises when the ground is not flat or the new line is wider than the frame's margin allows."""
    im = Image.open(picture).convert("RGB")
    g, spread = ground(im, box)
    if spread > limit:
        raise ValueError(f"the ground under the old words is not flat (spread {spread}); this is a picture change, not a words change")
    l, t, r, b = box
    fill_between(im, box)
    d = ImageDraw.Draw(im)
    cap = cap_px or (b - t)
    size = cap
    path, index = (font.rsplit("#", 1)[0], int(font.rsplit("#", 1)[1])) if "#" in str(font) else (font, 0)
    f = ImageFont.truetype(path, size, index=index)
    for _ in range(40):                                   # size so a capital H is `cap` pixels tall
        hb = f.getbbox("H")
        h = hb[3] - hb[1]
        if abs(h - cap) <= 0.5:
            break
        size = max(4, round(size * cap / max(h, 1)))
        f = ImageFont.truetype(path, size, index=index)
    w = f.getlength(text)
    if w > im.width * 0.96:
        raise ValueError(f"the new words are wider than the frame: {text}")
    d.text(((l + r) / 2, (t + b) / 2), text, font=f, fill=color, anchor="mm")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    try:  # made by the tool (GATE-5): stamped only when what it was laid on was (read before an in-place save)
        from . import provenance as PV
        _base = PV.sha256(picture)
    except Exception:
        _base = None
    im.save(out)
    try:
        from . import provenance as PV
        PV.derive(out, _base, "words")
    except Exception:
        pass
    return {"ok": True, "out": str(out), "ground": g, "size": size, "width": round(w)}


def recolour(picture, out, src, dst, tol=28, seeds=None):
    """Change the flat ground colour `src` to `dst` where it is the ground: every pixel within `tol` of `src` reached
    from `seeds` (default: the frame's edge pixels of that colour) through pixels of that colour. Anti-aliased edges
    keep their mix. Returns the share of the frame changed."""
    im = Image.open(picture).convert("RGB")
    W, H = im.size
    px = im.load()

    def near(p, c=src, k=tol):
        return all(abs(p[i] - c[i]) <= k for i in range(3))

    seen = bytearray(W * H)
    q = deque()
    starts = seeds or [(x, y) for y in range(H) for x in (0, W - 1)] + [(x, y) for x in range(W) for y in (0, H - 1)]
    for x, y in starts:
        if near(px[x, y]) and not seen[y * W + x]:
            seen[y * W + x] = 1
            q.append((x, y))
    n = 0
    while q:
        x, y = q.popleft()
        n += 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < W and 0 <= ny < H and not seen[ny * W + nx] and near(px[nx, ny]):
                seen[ny * W + nx] = 1
                q.append((nx, ny))
    # the fill, then the soft edge: a pixel next to the ground is moved by how much of the ground colour it holds
    for y in range(H):
        row = y * W
        for x in range(W):
            if seen[row + x]:
                p = px[x, y]
                px[x, y] = tuple(max(0, min(255, dst[i] + (p[i] - src[i]))) for i in range(3))
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if seen[y * W + x]:
                continue
            if seen[y * W + x - 1] or seen[y * W + x + 1] or seen[(y - 1) * W + x] or seen[(y + 1) * W + x]:
                p = px[x, y]
                a = max(0.0, 1 - sum(abs(p[i] - src[i]) for i in range(3)) / 240)
                px[x, y] = tuple(round(p[i] + a * (dst[i] - src[i])) for i in range(3))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    try:  # made by the tool (GATE-5): stamped only when what it was laid on was (read before an in-place save)
        from . import provenance as PV
        _base = PV.sha256(picture)
    except Exception:
        _base = None
    im.save(out)
    try:
        from . import provenance as PV
        PV.derive(out, _base, "recolour")
    except Exception:
        pass
    return {"ok": True, "out": str(out), "share": round(n / (W * H), 3)}
