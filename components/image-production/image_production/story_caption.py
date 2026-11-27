"""Story caption words set on top of a picture: the native Instagram story look (2026-11-23).

A story winner's words are its caption bubbles (white rounded boxes, black regular sans, centred) and a handle tag
(white, underlined, an emoji after it). The picture is made with none of them; this sets them on top in code, so every
character is exact and a words row never costs a new picture (the same rule as `words.set_on_top`, which has no
bubble or emoji).

    from image_production import story_caption as SC
    SC.render("plate.png", "out.png", {"handle": "@brand_a", "emoji": "🙏",
              "bubbles": [["Best Black Friday buy! king", "got the FLEX starting at $49!"], ["the sale is still live!"]]})

Places are fractions of the frame, read off the winner (`layout`); a caller may pass its own. Fonts are the
machine's own system fonts; a font missing on this machine is refused by name, never swapped silently.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TEXT_FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
HANDLE_FONT = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
EMOJI_SIZES = (160, 96, 64, 48, 40, 32, 20)   # the bitmap sizes Apple Color Emoji draws at

# read off the story winner at 900 x 1600 (IG Story Images): handle right edge, its centre line; the bubbles' centre
# line and the first bubble's top; letter size; the gap between bubbles; the box's padding and corner
LAYOUT = {"handle_right": 0.945, "handle_y": 0.573, "handle_size": 0.038, "emoji_size": 0.052,
          "bubble_x": 0.487, "bubble_top": 0.613, "size": 0.058, "line": 1.25, "gap": 0.025,
          "pad_x": 0.022, "pad_y": 0.016, "radius": 0.02}


def _font(path, size):
    if not Path(path).is_file():
        raise FileNotFoundError(f"story caption font missing on this machine: {path}")
    return ImageFont.truetype(path, size)


def _emoji(ch, px):
    """The emoji as a colour picture `px` tall (Apple Color Emoji draws only at its bitmap sizes)."""
    size = next((s for s in reversed(EMOJI_SIZES) if s >= px), EMOJI_SIZES[0])
    f = ImageFont.truetype(EMOJI_FONT, size)
    im = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox() or (0, 0, size, size))
    return im.resize((max(1, round(im.width * px / im.height)), px), Image.LANCZOS)


def _parts(line):
    """A bubble line as runs of (text, is_emoji): an emoji in a bubble is drawn as its own colour picture."""
    out = []
    for ch in line:
        e = ord(ch) >= 0x1F000
        if out and out[-1][1] == e and not e:
            out[-1][0] += ch
        elif ch != "\ufe0f":
            out.append([ch, e])
    return out


def _width(line, f, px):
    return sum((px * 1.02) if e else f.getlength(s) for s, e in _parts(line))


def _line(im, d, cx, cy, line, f, px):
    x = cx - _width(line, f, px) / 2
    for s, e in _parts(line):
        if e:
            em = _emoji(s, round(px))
            im.alpha_composite(em, (round(x), round(cy - em.height / 2)))
            x += px * 1.02
        else:
            d.text((x, cy), s, font=f, fill=(0, 0, 0, 255), anchor="lm")
            x += f.getlength(s)


def boxes(size, caption, layout=None):
    """Where each part lands, in pixels: {"handle": box, "bubbles": [box, ...]} with box = (l, t, r, b). Spends nothing."""
    L = {**LAYOUT, **(layout or {})}
    W, H = size
    f = _font(caption.get("font") or TEXT_FONT, round(L["size"] * W))
    out = {"bubbles": []}
    top = L["bubble_top"] * H
    lh = L["size"] * W * L["line"]
    for lines in caption.get("bubbles") or []:
        wmax = max(_width(t, f, L["size"] * W) for t in lines)
        w = wmax + 2 * L["pad_x"] * W
        h = lh * len(lines) + 2 * L["pad_y"] * H
        l = L["bubble_x"] * W - w / 2
        out["bubbles"].append(tuple(round(v) for v in (l, top, l + w, top + h)))
        top += h + L["gap"] * H
    return out


def render(plate, out, caption, layout=None):
    """Set the caption over `plate`, written to `out`. Returns {"ok", "out", "boxes"}. Raises when a bubble or the handle
    would leave the frame."""
    L = {**LAYOUT, **(layout or {})}
    im = Image.open(plate).convert("RGBA")
    W, H = im.size
    d = ImageDraw.Draw(im)
    f = _font(caption.get("font") or TEXT_FONT, round(L["size"] * W))
    lh = L["size"] * W * L["line"]
    bx = boxes((W, H), caption, L)
    for lines, (l, t, r, b) in zip(caption.get("bubbles") or [], bx["bubbles"]):
        if l < 0 or r > W or b > H:
            raise ValueError(f"caption bubble leaves the frame: {lines}")
        d.rounded_rectangle((l, t, r, b), radius=round(L["radius"] * W), fill=(255, 255, 255, 255))
        y = t + L["pad_y"] * H
        for line in lines:
            _line(im, d, (l + r) / 2, y + lh / 2, line, f, L["size"] * W)
            y += lh
    if caption.get("handle"):
        hf = _font(HANDLE_FONT, round(L["handle_size"] * W * 1.15))
        em = _emoji(caption["emoji"], round(L["emoji_size"] * W)) if caption.get("emoji") else None
        right = L["handle_right"] * W
        cy = L["handle_y"] * H
        if em is not None:
            im.alpha_composite(em, (round(right - em.width), round(cy - em.height / 2)))
            right -= em.width + 0.012 * W
        tw = hf.getlength(caption["handle"])
        if right - tw < 0:
            raise ValueError("handle leaves the frame")
        d.text((right, cy), caption["handle"], font=hf, fill=(255, 255, 255, 255), anchor="rm")
        uy = cy + L["handle_size"] * W * 0.62
        d.line((right - tw, uy, right, uy), fill=(255, 255, 255, 255), width=max(2, round(0.0025 * W)))
        bx["handle"] = (round(right - tw), round(cy - L["handle_size"] * W / 2), round(L["handle_right"] * W), round(uy))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(out)
    try:
        from . import provenance as PV
        PV.derive(out, PV.sha256(plate), "words")
    except Exception:
        pass
    return {"ok": True, "out": str(out), "boxes": bx}
