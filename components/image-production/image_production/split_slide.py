"""The split slide of a habit-versus-product carousel, laid out in code (2026-11-23).

A proven carousel slide (a title, the habit photo and the product photo side by side, a label under each, arrows, the
two result photos, a caption under each, a ✗ under the habit and a ✓ under the product, a divider down the middle,
black bars top and bottom) is a layout, not a picture. The photos are made one by one (each a 3D-set print); this sets
them and every word in place, so the words are exact and one photo can change without touching the rest.

    from image_production import split_slide as SS
    SS.render(out, photos={"tl": p1, "tr": p2, "bl": p3, "br": p4},
              words={"title": "THE NECK", "label_l": "DRY SHAVING", "label_r": "brand_a FLEX™",
                     "cap_l": "( BACK IN A DAY OR TWO )", "cap_r": "( GOES WHERE YOUR HANDS NEVER REACH )"},
              style=SS.STYLE)

`LAYOUT` holds the boxes as fractions of the 9:16 frame, read off the winner (brief-0255, slide 2); `STYLE` the colours
and faces. A caller passes its own for another slide's measurements. `cover(out, photo, lines, style)` sets the cover.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1080, 1920
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
LAYOUT = {"bar_top": 0.149, "bar_bot": 0.851, "title": (0.169, 0.212),
          "tl": (0.080, 0.247, 0.422, 0.445), "tr": (0.576, 0.247, 0.918, 0.445),
          "labels_y": (0.451, 0.473), "arrows_y": (0.482, 0.520),
          "bl": (0.070, 0.521, 0.433, 0.702), "br": (0.566, 0.521, 0.932, 0.702),
          "caps_y": (0.718, 0.735), "x_mark": (0.194, 0.754, 0.337, 0.829), "v_mark": (0.680, 0.745, 0.845, 0.829),
          "divider": (0.497, 0.242, 0.502, 0.851)}
STYLE = {"ground": (26, 26, 26), "bars": (0, 0, 0), "title": (238, 231, 215), "title_edge": (0, 0, 0),
         "accent": (240, 216, 96), "label": (255, 255, 255), "caption": (205, 205, 205), "arrow": (238, 231, 215),
         "title_face": (AVENIR, 8), "label_face": (AVENIR, 0), "caption_face": (AVENIR, 2)}


def _face(face, px):
    path, idx = face
    return ImageFont.truetype(path, max(6, int(px)), index=idx)


def _fit(d, text, face, box_w, px):
    f = _face(face, px)
    while f.getlength(text) > box_w and px > 8:
        px -= 1
        f = _face(face, px)
    return f


def _box(b):
    return (round(b[0] * W), round(b[1] * H), round(b[2] * W), round(b[3] * H))


def _photo(im, path, b):
    l, t, r, bot = _box(b)
    p = ImageOps.fit(Image.open(path).convert("RGB"), (r - l, bot - t), Image.LANCZOS)
    im.paste(p, (l, t))


def _mark(d, b, kind, colour):
    """A hand-drawn ✗ or ✓: two thick strokes, slightly uneven, like a grease pencil."""
    l, t, r, bot = _box(b)
    w = max(8, round((r - l) * 0.11))
    if kind == "x":
        d.line([(l, t), (r, bot)], fill=colour, width=w, joint="curve")
        d.line([(r, t + 4), (l + 3, bot)], fill=colour, width=w, joint="curve")
    else:
        mid = (l + (r - l) * 0.38, bot)
        d.line([(l, t + (bot - t) * 0.55), mid], fill=colour, width=w, joint="curve")
        d.line([mid, (r, t)], fill=colour, width=w, joint="curve")


def _text(d, xy, text, f, fill, edge=None):
    d.text(xy, text, font=f, fill=fill, anchor="mm",
           stroke_width=max(2, round(f.size * 0.08)) if edge else 0, stroke_fill=edge)


def render(out, photos, words, layout=None, style=None):
    L, S = {**LAYOUT, **(layout or {})}, {**STYLE, **(style or {})}
    im = Image.new("RGB", (W, H), S["bars"])
    d = ImageDraw.Draw(im)
    d.rectangle((0, round(L["bar_top"] * H), W, round(L["bar_bot"] * H)), fill=S["ground"])
    for k in ("tl", "tr", "bl", "br"):
        _photo(im, photos[k], L[k])
    d = ImageDraw.Draw(im)
    dv = _box(L["divider"]); d.rectangle(dv, fill=S["accent"])
    t0, t1 = L["title"]
    _text(d, (W / 2, (t0 + t1) / 2 * H), words["title"],
          _fit(d, words["title"], S["title_face"], W * 0.84, (t1 - t0) * H * 1.25), S["title"], S["title_edge"])
    for side, box in (("l", L["tl"]), ("r", L["tr"])):
        cx = (box[0] + box[2]) / 2 * W
        y0, y1 = L["labels_y"]
        lab = words[f"label_{side}"]
        _text(d, (cx, (y0 + y1) / 2 * H), lab, _fit(d, lab, S["label_face"], W * 0.42, (y1 - y0) * H * 1.15), S["label"])
        a0, a1 = L["arrows_y"]
        ax, ay0, ay1 = cx, a0 * H, a1 * H
        d.line([(ax, ay0), (ax, ay1)], fill=S["arrow"], width=4)
        d.line([(ax - 14, ay1 - 16), (ax, ay1), (ax + 14, ay1 - 16)], fill=S["arrow"], width=4, joint="curve")
        c0, c1 = L["caps_y"]
        cap = words[f"cap_{side}"]
        lines = cap.split(" / ")
        size = (c1 - c0) * H * 1.1
        for i, line in enumerate(lines):
            f = _fit(d, line, S["caption_face"], W * 0.44, size)
            _text(d, (cx, (c0 + c1) / 2 * H + i * size * 1.2), line, f, S["caption"])
    # a two-line caption pushes both marks down by its extra line, so the marks never sit on the words
    c0, c1 = L["caps_y"]
    extra = (max(len(words["cap_l"].split(" / ")), len(words["cap_r"].split(" / "))) - 1) * (c1 - c0) * 1.32
    xm = (L["x_mark"][0], L["x_mark"][1] + extra, L["x_mark"][2], min(L["bar_bot"] - 0.005, L["x_mark"][3] + extra))
    vm = (L["v_mark"][0], L["v_mark"][1] + extra, L["v_mark"][2], min(L["bar_bot"] - 0.005, L["v_mark"][3] + extra))
    _mark(d, xm, "x", S["accent"])
    _mark(d, vm, "v", S["accent"])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    try:  # made by the tool (GATE-5): stamped only when what it was laid on was
        from . import provenance as PV
        PV.derive_from(out, [photos[k] for k in ("tl", "tr", "bl", "br")], "layout")
    except Exception:
        pass
    return {"ok": True, "out": str(out)}


def cover(out, photo, lines, style=None, accent_line=1, ys=(0.670, 0.725, 0.781)):
    """The cover: one photo filling the window between the bars, three lines over its lower third, one in the accent."""
    S = {**STYLE, **(style or {})}
    im = Image.new("RGB", (W, H), S["bars"])
    t, b = round(LAYOUT["bar_top"] * H), round(LAYOUT["bar_bot"] * H)
    im.paste(ImageOps.fit(Image.open(photo).convert("RGB"), (W, b - t), Image.LANCZOS), (0, t))
    d = ImageDraw.Draw(im)
    sizes = (0.024, 0.034, 0.020)
    faces = (S["title_face"], S["title_face"], S["caption_face"])
    cols = [(255, 255, 255), S["accent"], (190, 190, 190)]
    for i, (line, y, sz, fc) in enumerate(zip(lines, ys, sizes, faces)):
        f = _fit(d, line, fc, W * (0.9 if i == 1 else 0.66), sz * H * 1.3)
        _text(d, (W / 2, y * H), line, f, cols[i] if i != accent_line else S["accent"])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    try:  # made by the tool (GATE-5): stamped only when what it was laid on was
        from . import provenance as PV
        PV.derive_from(out, [photo], "layout")
    except Exception:
        pass
    return {"ok": True, "out": str(out)}
