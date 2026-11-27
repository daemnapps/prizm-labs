"""Words set on top: the picture is made with no caption, headline or overlay text, and the brief's own type layer is
set over it afterwards (swaps rule 4, components/image-teardown/tools/swaps.py).

    from image_production import words
    words.set_on_top("pic.png", type_layer)          # → {"ok", "plate", "elements", "notes"}

The model paints the photograph; the compositor (static/tools/compose.py: ImageMagick, no design tool) sets the words, so
they are character-exact and sit where the brief's layout puts them. The plate (the picture before the words) is kept
beside the result as `<name>.plate.<ext>`, so a change to the words never costs a new picture.

A cover's headline (`set_headline`, called inside the cover job, covers.py) is set the same way and by one type record
for every version of an ad: one face, one weight, one size, one band. `fit` finds the one size every headline fits at;
`layout` says where each line lands, before anything is spent.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import paths as P
from . import provenance as PV

STROKE = {"color": "#000000", "pct": 0.6}
NATIVE_EDGE = re.compile(r"(?i)\b(stroke|outline|drop shadow)\b")


def compose_tool():
    return P.home() / "static" / "tools" / "compose.py"


def elements_of(layer):
    """The elements a layer carries, whether it is the brief's {"layout", "elements"} object or a bare list."""
    return list(layer.get("elements") or layer.get("type_layer") or []) if isinstance(layer, dict) else list(layer or [])


def prepare(layer):
    """The layer as the compositor reads it. An element whose letterform says it is outlined (the native caption look) gets
    the outline the compositor draws; every other key is the brief's own."""
    out = dict(layer) if isinstance(layer, dict) else {"elements": list(layer or [])}
    els = []
    for e in elements_of(layer):
        e = dict(e)
        lf = str(e.get("letterform") or "")
        # a drop shadow is drawn as a shadow when the layout records one (`shadow`, 2026-10-28); turning "drop shadow"
        # into a thick outline made the headline too wide at every size and it shrank to a speck
        edge = NATIVE_EDGE.search(re.sub(r"(?i)drop shadow", "", lf) if e.get("shadow") else lf)
        if not e.get("stroke") and edge:
            e["stroke"] = dict(STROKE)
        els.append(e)
    out["elements"] = els
    out.pop("type_layer", None)
    return out


def ui_icons(picture, layer):
    """A phone app's bar icons the layout records (`ui-icon-lock`, `-share`, `-ellipsis`): line icons drawn where the swipe
    has them, in the layout's colour (2026-11-02: a notes-app ad lost its three icons; they are no font's glyph)."""
    marks = [m for m in ((layer.get("layout") or {}).get("marks") or []) if str(m.get("kind", "")).startswith("ui-icon-")
             and str(m["kind"]) != "ui-icon-back"]         # the back arrow is the bar's own words
    if not marks:
        return
    from PIL import Image, ImageColor, ImageDraw
    im = Image.open(picture).convert("RGB")
    W, H = im.size
    for m in marks:
        sc = 4                                             # drawn large, then shrunk, for a clean line
        s = round(float(m.get("span_pct") or 3) * W / 100) * sc
        lw = max(sc, round(s * .09))
        c = ImageColor.getrgb(str(m.get("color") or "#000000"))
        ic = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(ic)
        k = m["kind"]
        if k == "ui-icon-lock":
            d.rounded_rectangle((s * .18, s * .46, s * .82, s * .96), s * .1, outline=c, width=lw)
            d.arc((s * .3, s * .08, s * .7, s * .72), 180, 360, fill=c, width=lw)
            d.line((s * .3, s * .4, s * .3, s * .46), fill=c, width=lw)
            d.line((s * .7, s * .4, s * .7, s * .46), fill=c, width=lw)
        elif k == "ui-icon-share":
            d.line((s * .3, s * .42, s * .14, s * .42, s * .14, s * .96, s * .86, s * .96, s * .86, s * .42, s * .7, s * .42), fill=c, width=lw, joint="curve")
            d.line((s * .5, s * .04, s * .5, s * .66), fill=c, width=lw)
            d.line((s * .3, s * .24, s * .5, s * .04, s * .7, s * .24), fill=c, width=lw, joint="curve")
        else:                                              # the ellipsis: three dots in a ring
            d.ellipse((s * .04, s * .04, s * .96, s * .96), outline=c, width=lw)
            for x in (.3, .5, .7):
                d.ellipse((s * (x - .05), s * .45, s * (x + .05), s * .55), fill=c)
        ic = ic.resize((s // sc, s // sc), Image.LANCZOS)
        im.paste(ic, (round(float(m.get("left_pct") or 0) * W / 100), round(float(m.get("top_pct") or 0) * H / 100)), ic)
    im.save(picture)


def set_on_top(picture, layer, out=None, plate=None):
    """Set `layer` over `picture`. Writes the result to `out` (default: over `picture`), and keeps the plate at `plate`
    (default: beside the picture)."""
    picture = Path(picture)
    out = Path(out) if out else picture
    els = elements_of(layer)
    if not els:
        return {"ok": True, "plate": str(picture), "elements": 0, "notes": ["the layer has no words"]}
    plate = Path(plate) if plate else picture.with_name(picture.stem + ".plate" + picture.suffix)
    plate.parent.mkdir(parents=True, exist_ok=True)
    if picture.resolve() == out.resolve() or not plate.is_file():
        shutil.copy2(picture, plate)
    if isinstance(layer, dict) and layer.get("design"):      # a designed layout, in the brand's own fonts, replaces the stamped type
        from . import design_type
        return design_type.render(plate, layer, out)         # render stamps it (made by the tool, RULE GATE-5)
    base = PV.sha256(plate)                                  # the tool's words count only over the tool's own picture
    work = Path(tempfile.mkdtemp(prefix="words-"))
    try:
        lf = work / "layer.json"
        lf.write_text(json.dumps(prepare(layer), ensure_ascii=False))
        r = subprocess.run([sys.executable, str(compose_tool()), "--plate", str(plate), "--layer", str(lf), "--out", str(out)],
                           capture_output=True, text=True)
        if r.returncode or not out.is_file():
            return {"ok": False, "plate": str(plate), "elements": 0, "notes": [(r.stderr or r.stdout).strip()[-300:] or "the compositor failed"]}
        ui_icons(out, layer)
        PV.derive(out, base, "words")
        return {"ok": True, "plate": str(plate), "elements": len(els),
                "notes": [l.strip() for l in r.stdout.splitlines() if l.strip()][-4:]}
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(out.resolve().parent / ".compose-tmp", ignore_errors=True)


# ── THE COVER'S HEADLINE: one type record for every version of an ad ─────────────────────────────────────────────────────
# The picture model paints no words on a cover. The headline is set here, inside the cover job, so it is character-exact,
# and every version of one ad carries the same face, weight, size and band (covers.ad_type). Sizes are pixels on a
# 1080x1920 frame; the band (`zone`) is in percent of the frame and stays inside the 4:5 safe zone.
TYPE_KEYS = ("face", "weight", "size_px", "min_size_px", "line_height", "max_lines", "zone", "align", "valign", "case",
             "fill", "stroke", "box")
SAFE_BAND = {"top": 14.8, "bottom": 85.2, "left": 5.0, "right": 95.0}
BASE_W, BASE_H = 1080, 1920
FONT_FILES = (".woff2", ".ttf", ".otf", ".ttc", ".woff")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class WordsRefused(ValueError):
    """The headline cannot be set as asked (no such face, a character the face cannot draw, words that do not fit).
    Raised before anything is sent, so nothing was spent."""


def faces_dir():
    """The type library the covers share with the video line: one folder per face, a manifest naming its files."""
    return P.sibling("video-edit", "looks", "fonts")


def face_file(face):
    """The font file for a face: a file on this machine (absolute, or below the workspace or the mounted Drive), or an
    id in the type library. A face that is neither is refused, never swapped for another."""
    s = str(face or "").strip()
    if not s:
        raise WordsRefused("the type names no face")
    p = Path(s).expanduser()
    homes = [Path(__file__).resolve().parents[3]]
    for find in (P.repo, lambda: P.drive_runs().parent):
        try:
            homes.append(find())
        except Exception:                                    # noqa: BLE001  no workspace or no Drive here: not a home
            pass
    for cand in ([p] if p.is_absolute() else [h / s for h in homes]):
        if cand.is_file() and cand.suffix.lower() in FONT_FILES:
            return cand
    d = faces_dir() / s
    if "/" not in s and d.is_dir():
        try:
            files = json.loads((d / "manifest.json").read_text()).get("files") or []
        except (OSError, ValueError):
            files = []
        named = [f["file"] for f in files if f.get("subset") == "latin"] + [f["file"] for f in files]
        for name in named + sorted(x.name for x in d.iterdir() if x.suffix.lower() in FONT_FILES):
            if (d / name).is_file():
                return d / name
    have = sorted(x.name for x in faces_dir().iterdir() if x.is_dir()) if faces_dir().is_dir() else []
    raise WordsRefused(f"the face `{s}` is not a font file on this machine and not an id in the type library "
                       f"({', '.join(have) or 'none found'})")


def _font(file, px, weight=None):
    from PIL import ImageFont
    f = ImageFont.truetype(str(file), max(1, int(round(px))))
    if weight is not None:
        try:
            axes = f.get_variation_axes()
        except Exception:                                    # noqa: BLE001  a static face: its weight is the file's
            axes = []
        if axes:
            vals = []
            for a in axes:
                name = a.get("name")
                name = name.decode("utf-8", "replace") if isinstance(name, bytes) else str(name or "")
                vals.append(max(a["minimum"], min(a["maximum"], float(weight))) if name.lower() == "weight" else a["default"])
            f.set_variation_by_axes(vals)
    return f


def _undrawable(font, text):
    """Characters the face has no glyph for: they would print as an empty box."""
    blank = font.getmask(chr(0x10FFFE))                      # a code point no face draws: what a missing glyph looks like
    blank = (blank.size, bytes(blank))
    out = []
    for ch in dict.fromkeys(text):
        if ch.isspace():
            continue
        m = font.getmask(ch)
        if m.size[0] == 0 or m.size[1] == 0 or (m.size, bytes(m)) == blank:
            out.append(ch)
    return out


def check_type(style):
    """Problems with a type record, [] when it can be set. Every key is named; an unknown key is a caller that thinks it
    asked for something."""
    bad = []
    if not isinstance(style, dict):
        return ["the type is not a mapping"]
    unknown = sorted(k for k in style if k not in TYPE_KEYS and not k.startswith("_"))
    if unknown:
        bad.append(f"the type carries keys nothing reads: {', '.join(unknown)} (have: {', '.join(TYPE_KEYS)})")
    for k in ("face", "size_px", "zone"):
        if not style.get(k):
            bad.append(f"the type has no `{k}`")
    z = style.get("zone") or {}
    if z:
        if any(k not in z for k in SAFE_BAND):
            bad.append("the band (`zone`) needs top, bottom, left and right, in percent of the frame")
        elif (z["top"] < SAFE_BAND["top"] or z["bottom"] > SAFE_BAND["bottom"] or z["left"] < SAFE_BAND["left"]
              or z["right"] > SAFE_BAND["right"] or z["top"] >= z["bottom"] or z["left"] >= z["right"]):
            bad.append(f"the band (`zone`) leaves the safe zone: keep it inside top {SAFE_BAND['top']}, bottom "
                       f"{SAFE_BAND['bottom']}, left {SAFE_BAND['left']}, right {SAFE_BAND['right']} percent")
    try:
        size, low = float(style.get("size_px") or 0), float(style.get("min_size_px") or style.get("size_px") or 0)
        if size <= 0 or low <= 0 or low > size:
            bad.append("`size_px` and `min_size_px` are pixels on a 1080x1920 frame, the smallest no larger than the size")
    except (TypeError, ValueError):
        bad.append("`size_px` and `min_size_px` are numbers")
    if style.get("align", "center") not in ("left", "center", "right"):
        bad.append("`align` is left, center or right")
    if style.get("valign", "center") not in ("top", "center", "bottom"):
        bad.append("`valign` is top, center or bottom")
    if style.get("case", "as-written") not in ("as-written", "upper"):
        bad.append("`case` is as-written or upper")
    for name, colour in (("fill", style.get("fill")), ("stroke.color", (style.get("stroke") or {}).get("color")),
                         ("box.fill", (style.get("box") or {}).get("fill"))):
        if colour is not None and not _HEX.match(str(colour)):
            bad.append(f"`{name}` is a colour written #RRGGBB")
    return bad


def _lines(text, font, span):
    """The headline wrapped to the band's width, word by word. A written line break is kept. None when one word alone is
    wider than the band."""
    out = []
    for para in str(text).replace("\\n", "\n").split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}".strip()
            if line and font.getlength(trial) > span:
                out.append(line)
                line = word
            else:
                line = trial
            if font.getlength(line) > span:
                return None
        if line:
            out.append(line)
    return out


def layout(text, style, size=(BASE_W, BASE_H), px=None):
    """Where the headline lands on a frame of `size`, at the type's size (or `px`, pixels on a 1080x1920 frame): the
    lines, each line's box and the box around them all. None when it does not fit the band at that size. Raises
    WordsRefused for a face that is missing or cannot draw a character. Draws nothing."""
    w, h = size
    k = h / float(BASE_H)
    base_px = float(px if px is not None else style["size_px"])
    font = _font(face_file(style["face"]), base_px * k, style.get("weight"))
    said = str(text or "").strip()
    said = said.upper() if style.get("case") == "upper" else said
    if not said:
        raise WordsRefused("there are no words to set")
    lost = _undrawable(font, said)
    if lost:
        raise WordsRefused(f"the face `{style['face']}` cannot draw: {' '.join(lost)} (they would print as empty boxes)")
    z = style["zone"]
    left, right, top, bottom = z["left"] / 100.0 * w, z["right"] / 100.0 * w, z["top"] / 100.0 * h, z["bottom"] / 100.0 * h
    box = style.get("box") or {}
    stroke = style.get("stroke") or {}
    pad = float(box.get("pad_px", 18)) * k if box else float(stroke.get("px", 0)) * k
    lines = _lines(said, font, (right - left) - 2 * pad)
    if not lines:
        return None
    lh = base_px * k * float(style.get("line_height", 1.16))
    block = lh * len(lines)
    if len(lines) > int(style.get("max_lines", 3)) or block > (bottom - top):
        return None
    valign = style.get("valign", "center")
    y0 = top if valign == "top" else (bottom - block if valign == "bottom" else top + ((bottom - top) - block) / 2.0)
    align = style.get("align", "center")
    rows = []
    for i, line in enumerate(lines):
        lw = font.getlength(line)
        x = left + pad if align == "left" else (right - pad - lw if align == "right" else left + ((right - left) - lw) / 2.0)
        rows.append([x, y0 + i * lh, x + lw, y0 + (i + 1) * lh])
    around = [max(0.0, min(r[0] for r in rows) - pad), max(0.0, y0 - (pad if not box else 0)),
              min(float(w), max(r[2] for r in rows) + pad), min(float(h), y0 + block + (pad if not box else 0))]
    return {"lines": lines, "size_px": base_px, "line_boxes": [[round(v, 1) for v in r] for r in rows],
            "box_px": [int(round(v)) for v in around], "frame": [w, h]}


def fit(headlines, style, size=(BASE_W, BASE_H)):
    """The one size (pixels on a 1080x1920 frame) every headline fits the band at: the type's `size_px`, stepped down
    to `min_size_px`. Raises WordsRefused naming the headline that does not fit even at the smallest."""
    top, low = float(style["size_px"]), float(style.get("min_size_px") or style["size_px"])
    px = top
    while px >= low:
        if all(layout(t, style, size, px) is not None for t in headlines):
            return px
        px -= 2.0
    worst = max(headlines, key=lambda t: len(str(t)))
    raise WordsRefused(f"the headline does not fit its band at the smallest size ({low:g} px, {style.get('max_lines', 3)} "
                       f"lines): \"{worst}\". Shorten it, or give the band more room (`zone`).")


def set_headline(picture, text, style, out=None, plate=None):
    """Set a cover's headline over `picture` by its type record, exactly as written. Writes `out` (default: over
    `picture`) and keeps the plate (the picture before the words). Returns the same shape as set_on_top, plus where the
    words landed."""
    from PIL import Image, ImageDraw
    picture = Path(picture)
    out = Path(out) if out else picture
    plate = Path(plate) if plate else picture.with_name(picture.stem + ".plate" + picture.suffix)
    plate.parent.mkdir(parents=True, exist_ok=True)
    if picture.resolve() == out.resolve() or not plate.is_file():
        shutil.copy2(picture, plate)
    im = Image.open(plate).convert("RGB")
    lay = layout(text, style, im.size)
    if lay is None:
        raise WordsRefused(f"the headline does not fit its band at {style['size_px']:g} px on a {im.size[0]}x{im.size[1]} "
                           f"picture: \"{text}\"")
    k = im.size[1] / float(BASE_H)
    font = _font(face_file(style["face"]), lay["size_px"] * k, style.get("weight"))
    box, stroke = style.get("box") or {}, style.get("stroke") or {}
    edge = int(round(float(stroke.get("px", 0)) * k)) if stroke else 0
    draw = ImageDraw.Draw(im)
    for line, (x0, y0, x1, y1) in zip(lay["lines"], lay["line_boxes"]):
        if box:
            pad = float(box.get("pad_px", 18)) * k
            draw.rounded_rectangle((x0 - pad, y0, x1 + pad, y1), radius=float(box.get("radius_px", 14)) * k,
                                   fill=box.get("fill", "#FFFFFF"))
        draw.text((x0, (y0 + y1) / 2.0), line, font=font, anchor="lm", fill=style.get("fill", "#FFFFFF"),
                  stroke_width=edge, stroke_fill=stroke.get("color", "#000000") if edge else None)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return {"ok": True, "plate": str(plate), "elements": 1, "lines": lay["lines"], "box_px": lay["box_px"],
            "size_px": lay["size_px"], "notes": [f"{len(lay['lines'])} line(s) at {lay['size_px']:g} px"]}
