#!/usr/bin/env python3
"""Set the type layer over a generated plate. ImageMagick, no design tool.

The image model paints the picture; this sets the words. Anything that must be
character-exact — the guarantee, prices, product names — comes through here,
where it cannot be misspelled.

    python3 compose.py --plate plate.jpg --layer type-layer.json \
        --file 1 --out ad-01.png

Layer file = stage 5's DOCUMENT TWO. Per element:
  text, top_pct, left_pct, right_pct, align, cap_pct, color, case, tracking,
  file ("all", a value, or a list of file numbers)
Optional:
  font      key into FONTS, or a path
  box       {"fill": "#E68A00", "pad_pct": 1.2}  panel behind the text
  segments  [{"text": "IT WORKS", "color": "#FFF"}, ...]  one line, two colors
  stroke    {"color": "#000", "pct": 0.6}  an outline around the letters (the
            native caption look); "px" sets an exact width instead of pct

**The span wins over the cap height.** cap_pct sets the point size, but the
text is wrapped to the left/right span and, if a single word still overruns,
the size is stepped down until it fits. A headline that runs off the frame is
not a headline, and the chain's own legibility floor is about what reads —
not about what a number said.
"""

import argparse, json, subprocess, sys
from pathlib import Path

FONTS = {
    "compressed-grotesque": "/System/Library/Fonts/Supplemental/Impact.ttf",
    "condensed-grotesque": "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
    "grotesque":           "/System/Library/Fonts/HelveticaNeue.ttc",
    "humanist-sans":       "/System/Library/Fonts/HelveticaNeue.ttc",
    "geometric-sans":      "/System/Library/Fonts/Avenir Next.ttc",
    "serif":               "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "high-contrast-serif": "/System/Library/Fonts/Supplemental/Didot.ttc",
}

# A weight is a different FILE, not a flag. Measured cause, 2026-08-26: a clone
# of a bold headline came back in regular because the layer recorded "bold" in
# prose and the renderer had nowhere to put it — the words were right and the
# ad still looked wrong.
FONTS_BOLD = {
    "compressed-grotesque": "/System/Library/Fonts/Supplemental/Impact.ttf",
    "condensed-grotesque": "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
    "grotesque":           "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "humanist-sans":       "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "geometric-sans":      "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "serif":               "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "high-contrast-serif": "/System/Library/Fonts/Supplemental/Didot.ttc",
}
BOLD_WORDS = {"bold", "semibold", "semi-bold", "black", "heavy", "extrabold", "extra-bold"}
# Black is its own cut (2026-10-28)A family with no black cut on disk falls back to its bold.
FONTS_BLACK = {
    "grotesque":      "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "humanist-sans":  "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "geometric-sans": "/System/Library/Fonts/Supplemental/Arial Black.ttf",
}
BLACK_WORDS = {"black", "heavy", "extrabold", "extra-bold", "ultra", "ultrabold"}
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
MARK_FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"      # has the arrows and ticks the caption fonts lack
DEFAULT_FONT = "condensed-grotesque"
# the swipe's italic (2026-10-28): serif classes in their italic cut; a class with none keeps its upright face
FONTS_ITALIC = {
    "serif":               "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
    "high-contrast-serif": "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
}
CAP_RATIO = 0.715                      # cap height as a share of point size
TRACKING = {"tight": -1.5, "normal": 0.0, "standard": 0.0,
            "wide": 10.0, "very wide": 16.0, "": 0.0}


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def dims(path):
    w, h = sh(["magick", "identify", "-format", "%w %h", str(path)]).split()
    return int(w), int(h)


def cased(text, case):
    c = (case or "").lower()
    if c in ("upper", "uppercase", "all-caps", "caps"):
        return text.upper()
    if c in ("lower", "lowercase"):
        return text.lower()
    return text


def track_px(tr, pt):
    v = TRACKING.get(str(tr).lower(), 0.0) if not isinstance(tr, (int, float)) \
        else float(tr)
    return round(pt * v / 100, 2)


def draw(text, font, pt, color, kern, span_px, tmp, grav="west", stroke=None):
    def one(fill, out, edge=None):
        cmd = ["magick", "-background", "none", "-fill", fill, "-font", font,
               "-pointsize", str(pt)]
        if edge:
            cmd += ["-stroke", edge[0], "-strokewidth", str(edge[1])]
        if kern:
            cmd += ["-kerning", str(kern)]
        # A segment is a fragment of one line: render it at its natural width with
        # label: (no wrapping). Only whole blocks get caption: and a wrap width.
        if span_px is None:
            cmd += ["-gravity", "west", f"label:{text}", str(out)]
        else:
            cmd += ["-size", f"{span_px}x", "-gravity", grav,
                    f"caption:{text}", str(out)]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    if not stroke:
        one(color, tmp)
        metallic(tmp, color)
        return dims(tmp)
    # THE OUTLINE (2026-10-23): native captions are white type with a dark
    # edge, readable on any picture. The edge is drawn as its own layer at
    # twice the width and the clean fill laid over it, so the letters keep
    # their weight instead of being eaten by the stroke.
    px = max(1, round(float(stroke.get("pct", 0.6)) * pt / 10)) if "px" not in stroke else int(stroke["px"])
    edge = Path(str(tmp) + ".edge.png")
    one(stroke.get("color", "#000000"), edge, (stroke.get("color", "#000000"), px * 2))
    one(color, tmp, (color, 0.01))
    subprocess.run(["magick", str(edge), str(tmp), "-gravity", "center", "-compose", "over",
                    "-composite", str(tmp)], capture_output=True, text=True, check=True)
    edge.unlink(missing_ok=True)
    return dims(tmp)


def torn_paper(pap, W, H, top_px, bh, tmpdir, i):
    """The swipe's torn white paper behind a block of words: irregular torn top and bottom edges, turned by the swipe's
    angle, a soft even drop shadow. Returns (png, x, y)."""
    import random
    from PIL import Image, ImageDraw, ImageFilter
    x0, x1 = round(float(pap.get("left_pct", 5)) / 100 * W), round(float(pap.get("right_pct", 95)) / 100 * W)
    y0 = top_px - round(float(pap.get("above_pct", 4)) / 100 * H)
    y1 = top_px + bh + round(float(pap.get("below_pct", 4)) / 100 * H)
    w, h, m = x1 - x0, y1 - y0, round(0.04 * W)
    rnd = random.Random(11)
    step = max(6, w // 60)
    top = [(x, m + rnd.randint(0, round(0.012 * H))) for x in range(m, m + w + 1, step)]
    bot = [(x, m + h - rnd.randint(0, round(0.012 * H))) for x in range(m + w, m - 1, -step)]
    left = [(m + rnd.randint(0, 4), y) for y in range(m + h, m, -step * 2)]
    mask = Image.new("L", (w + 2 * m, h + 2 * m), 0)
    ImageDraw.Draw(mask).polygon(top + [(m + w, m)] + bot + left, fill=255)
    mask = mask.rotate(float(pap.get("rotate_deg", 0)), resample=Image.BICUBIC, expand=False)
    shadow = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(round(0.008 * W))).point(lambda v: int(v * 0.35)))
    sheet = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    paper = Image.new("RGBA", mask.size, (255, 255, 255, 255))
    sheet.alpha_composite(shadow, (round(0.004 * W), round(0.006 * W)))
    paper.putalpha(mask)
    sheet.alpha_composite(paper)
    out = tmpdir / f"el{i:02d}_paper.png"
    sheet.save(out)
    return out, x0 - m, y0 - m


def is_gold(color):
    """A gold fill: a warm yellow, saturated enough to read as gold, not cream or white."""
    try:
        r, g, b = (int(str(color)[i:i + 2], 16) for i in (1, 3, 5))
    except ValueError:
        return False
    hi, lo = max(r, g, b), min(r, g, b)
    return hi >= 120 and (hi - lo) / hi >= 0.35 and r >= g > b and g >= 0.6 * r


def metallic(png, color):
    """Gold type is set as metal, never flat yellow (2026-10-28): the letters keep their shape, their fill becomes a vertical
    shine of the same gold, light at the top, the gold itself, a darker band below the middle, a light lip at the foot."""
    if not is_gold(color):
        return
    from PIL import Image
    r, g, b = (int(str(color)[i:i + 2], 16) for i in (1, 3, 5))
    mix = lambda t, k: tuple(round(c + (t - c) * k) for c in (r, g, b)) if t else tuple(round(c * k) for c in (r, g, b))
    stops = [(0.0, mix(255, 0.55)), (0.35, (r, g, b)), (0.62, mix(0, 0.62)), (0.85, mix(0, 0.85)), (1.0, mix(255, 0.3))]
    im = Image.open(png).convert("RGBA")
    w, h = im.size
    col = []
    for y in range(h):
        t = y / max(1, h - 1)
        (t0, c0), (t1, c1) = next((stops[i], stops[i + 1]) for i in range(len(stops) - 1) if t <= stops[i + 1][0])
        k = (t - t0) / max(1e-6, t1 - t0)
        col.append(tuple(round(a + (bb - a) * k) for a, bb in zip(c0, c1)))
    shine = Image.new("RGBA", (1, h))
    shine.putdata([c + (255,) for c in col])
    shine = shine.resize((w, h))
    shine.putalpha(im.getchannel("A"))
    shine.save(png)


def wrap_to_measure(text, measure):
    """Wrap on characters per line — the measure the teardown counted.

    Pixel width alone lets a longer word count change the line count silently.
    The measure is what a designer actually holds constant between variations."""
    out, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if len(trial) > measure and line:
            out.append(line); line = word
        else:
            line = trial
    if line:
        out.append(line)
    return "\n".join(out)


def lines_of(png):
    return None


def render_block(segs, font, pt, kern0, span_px, band_px, tmpdir, i, case,
                 measure=None, max_lines=None, grav="west"):
    """Render one element, stepping the size down until the whole block fits
    its span AND the vertical band before the next element starts.

    The chain sizes type from the source ad's word counts. Ours are longer, so
    a cap height that fitted four words overruns at twenty. Fitting here is
    not a design choice — it is the only way the specified positions survive
    contact with the specified copy. Every step-down is reported."""
    for _ in range(30):
        kern = round(kern0 * pt / max(pt, 1), 2) if kern0 else 0
        layers = []
        for si, seg in enumerate(segs):
            text = cased(str(seg.get("text", "")), case)
            text = text.replace(" / ", "\n").replace("\\n", "\n")
            if not text.strip():
                continue
            tmp = tmpdir / f"el{i:02d}_{si}.png"
            share = span_px if len(segs) == 1 else None
            draw(text, font, pt, seg.get("color", "#FFFFFF"), kern, share, tmp,
                 grav if len(segs) == 1 else "west", stroke=seg.get("stroke"))
            layers.append(tmp)
        if not layers:
            return None, pt
        if len(layers) > 1:
            # Butting fragments together with +append throws away the word
            # space and, with it, the typesetting. Instead lay each fragment
            # at the x its own words occupy inside the FULL line: render the
            # whole string, render each prefix, and place segment i at
            # width(prefix through i) - width(segment i). The space between
            # colours is then the font's real space advance, not a join.
            join = " "
            texts = [cased(str(sg.get("text", "")), case).strip()
                     for sg in segs]
            full = tmpdir / f"el{i:02d}_full.png"
            draw(join.join(texts), font, pt, "#000000", kern, None, full)
            fw, fh = dims(full)
            xs = []
            for n in range(len(texts)):
                if n == 0:
                    xs.append(0)
                    continue
                pre = tmpdir / f"el{i:02d}_pre{n}.png"
                draw(join.join(texts[:n + 1]), font, pt, "#000000", kern,
                     None, pre)
                pw, _ = dims(pre)
                sw, _ = dims(layers[n])
                xs.append(pw - sw)
            block = tmpdir / f"el{i:02d}_joined.png"
            cmd_join = ["magick", "-size", f"{fw}x{fh}", "xc:none"]
            # A fragment can carry its own panel — "SKIN" knocked white out of
            # red, "ALERT" black out of white, butted into one badge. Measured
            # cause, 2026-08-26: with only an element-level box, the two-tone
            # badge rebuilt as one red bar and the second panel vanished.
            # Boxes are drawn first, under every fragment, so no panel covers
            # the fragment beside it.
            pad = max(2, round(pt * 0.18))
            for n, sg in enumerate(segs):
                sbox = sg.get("box") or {}
                fill = sbox.get("fill")
                if not fill:
                    continue
                sw, _ = dims(layers[n])
                x0, x1 = max(0, xs[n] - pad), min(fw, xs[n] + sw + pad)
                cmd_join += ["-fill", fill, "-draw",
                             f"rectangle {x0},0 {x1},{fh}"]
            for n, lay in enumerate(layers):
                cmd_join += [str(lay), "-gravity", "west",
                             "-geometry", f"+{xs[n]}+0", "-composite"]
            cmd_join.append(str(block))
            sh(cmd_join)
        else:
            block = layers[0]
        w, h = dims(block)
        # line count from the rendered height and the point size — the only
        # honest way to count lines after ImageMagick has done the wrapping
        est_lines = max(1, round(h / (pt * 1.16)))
        if w <= span_px and (band_px is None or h <= band_px) \
                and (not max_lines or est_lines <= max_lines):
            return block, pt
        pt = int(pt * 0.92)
        if pt < 8:
            return block, pt
    return block, pt



def num(v, default=None):
    """A measurement, or the default — never a crash.

    Stage 6 writes `null` for an optional measurement it does not need and,
    when it cannot measure one, the literal string `[MISSING: cap_pct]`. Both
    reached the compositor as values and it died on the first of them —
    a placeholder in one field took down a whole ad (2026-09-14).
    """
    if isinstance(v, (int, float)):
        return v
    try:
        return float(str(v).strip().rstrip("%"))
    except (TypeError, ValueError):
        return default


MARK_GLYPHS = {"arrow": "\u2794", "arrow-right": "\u2794", "chevron": "\u203A", "check": "\u2713", "star": "\u2605"}


def attach_marks(layout, drawn):
    """A mark the layout records beside a line (an arrow in a price pill, a tick after a claim) belongs to that line:
    it rides at the end of it, in its own colour, wherever our longer words move it (2026-10-28: the swipe's orange
    arrow was recorded at the old pill's spot and never drawn). A mark with `attach_to` names its element; otherwise
    the element whose top is within 6% of the mark's top takes it."""
    for m in (layout or {}).get("marks") or []:
        glyph = MARK_GLYPHS.get(str(m.get("kind", "")).lower())
        if not glyph:
            continue
        el = next((e for e in drawn if e.get("element") == m.get("attach_to")), None)
        if el is None:
            mt = num(m.get("top_pct"))
            near = [(abs(num(e.get("top_pct"), -99) - mt), e) for e in drawn if mt is not None and num(e.get("top_pct")) is not None]
            near = [t for t in near if t[0] <= 6]
            el = min(near, key=lambda t: t[0])[1] if near else None
        if el is not None and not el.get("mark"):
            el["mark"] = {"glyph": glyph, "color": m.get("color", "#FFFFFF")}


def _emoji_png(chars, height, out):
    """Colour emoji, drawn by Pillow from the system's emoji font (ImageMagick cannot draw colour glyphs)."""
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(EMOJI_FONT, 160)
    w = int(f.getlength(chars)) + 20
    im = Image.new("RGBA", (w, 200), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), chars, font=f, embedded_color=True)
    im = im.crop(im.getbbox() or (0, 0, w, 200))
    im = im.resize((max(1, round(im.width * height / im.height)), height))
    im.save(out)
    return out


def trailing(el, segs, font, pt, kern, block, tmpdir, i, align):
    """The swipe's emoji and its attached mark, set after the LAST line of the block (2026-10-28: both were dropped)."""
    emoji, mark = str(el.get("emoji") or "").strip(), el.get("mark")
    if not (emoji or mark) or len(segs) != 1:
        return None
    from PIL import Image
    text = cased(str(segs[0].get("text", "")), el.get("case")).replace(" / ", "\n").replace("\\n", "\n")
    last = [l for l in text.split("\n") if l.strip()][-1]
    lp = tmpdir / f"el{i:02d}_last.png"
    lw, lh = draw(last, font, pt, "#000000", kern, None, lp)
    base = Image.open(block).convert("RGBA")
    bw, bh = base.size
    lx = 0 if align == "left" else bw - lw if align == "right" else (bw - lw) // 2
    gap = round(pt * 0.25)
    parts = []
    if emoji:
        parts.append(Image.open(_emoji_png(emoji, round(pt * 0.95), tmpdir / f"el{i:02d}_emoji.png")).convert("RGBA"))
    if mark:
        mp = tmpdir / f"el{i:02d}_mark.png"
        draw(mark["glyph"], MARK_FONT if Path(MARK_FONT).exists() else font, pt, mark.get("color", "#FFFFFF"), 0, None, mp)
        parts.append(Image.open(mp).convert("RGBA"))
    add = sum(p.width + gap for p in parts)
    grow = max(0, lx + lw + add - bw)
    left_pad = grow if align == "right" else grow // 2 if align == "center" else 0
    canvas = Image.new("RGBA", (bw + grow + (grow // 2 if align == "center" else 0), bh), (0, 0, 0, 0))
    canvas.paste(base, (left_pad, 0), base)
    cx = left_pad + lx + lw + gap
    for p in parts:
        bb = p.getbbox() or (0, 0, p.width, p.height)          # centre the glyph's ink on the last line's ink
        p = p.crop(bb)
        canvas.paste(p, (cx, max(0, bh - lh // 2 - p.height // 2 - round(pt * 0.06))), p)
        cx += p.width + gap
    out = tmpdir / f"el{i:02d}_tail.png"
    canvas.save(out)
    return out


def shadowed(el, block, tmpdir, i, pt, x, y):
    """The letters' own soft shadow (`shadow` {color, blur_pct, offset_pct}), the native-caption look the swipe's
    headline sits on (2026-10-28). Returns (picture, x, y) to composite."""
    sh_ = el.get("shadow")
    if not sh_ or el.get("box"):
        return block, x, y
    sigma = max(1, round(float(num(sh_.get("blur_pct"), 0.6)) / 100 * pt * 10))
    off = max(0, round(float(num(sh_.get("offset_pct"), 0.25)) / 100 * pt * 10))
    out = tmpdir / f"el{i:02d}_shadow.png"
    sh(["magick", str(block), "(", "+clone", "-background", sh_.get("color", "#000000"), "-shadow",
        f"60x{sigma}+0+{off}", ")", "+swap", "-background", "none", "-layers", "merge", "+repage", str(out)])
    return out, x - 2 * sigma, y - 2 * sigma + off


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plate", required=True)
    ap.add_argument("--layer", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--file", help="only elements whose 'file' is this value, "
                                   "contains it, or is 'all'")
    ap.add_argument("--font-map")
    a = ap.parse_args()

    fonts = dict(FONTS)
    if a.font_map:
        fonts.update(json.loads(Path(a.font_map).read_text()))

    W, H = dims(a.plate)
    raw = json.loads(Path(a.layer).read_text())
    if isinstance(raw, dict):
        layout = raw.get("layout", {})
        layer = raw.get("elements") or raw.get("type_layer") or []
    else:
        layout, layer = {}, raw
    M = layout.get("margins", {})
    keep = layout.get("keep_clear", [])

    # Unique per output: two ads composed at the same time shared one
    # temp dir and overwrote each other's fragments (2026-09-14).
    tmpdir = Path(a.out).resolve().parent / f".compose-tmp-{Path(a.out).stem}"
    tmpdir.mkdir(parents=True, exist_ok=True)

    cmd = ["magick", str(a.plate)]
    placed, notes, prev_bottom, prev_grown = 0, [], None, None

    # elements that will actually be drawn, in vertical order — each one's
    # band runs to the next one's top edge, which is what stops the specified
    # positions colliding once our copy wraps further than the source's did
    drawn = []
    for el in layer:
        who = el.get("file", "all")
        if a.file and who != "all":
            wanted = who if isinstance(who, list) else [who]
            if a.file not in [str(w) for w in wanted]:
                continue
        drawn.append(el)
    for el in drawn:
        # a box with no fill and no visible line is no box: the layout read writes {"fill": "none"} on bare type, and
        # treating it as a box hid the letters' own shadow and trimmed the block (2026-10-28)
        b = el.get("box")
        if isinstance(b, dict):
            st = b.get("stroke") or {}
            if st and not num(st.get("width_pct"), 0):
                b.pop("stroke", None)
            if str(b.get("fill") or "none").lower() in ("none", "transparent", "") and not b.get("stroke"):
                el.pop("box", None)
            elif str(b.get("fill") or "none").lower() in ("none", "transparent", "") and b.get("stroke"):
                # an outline box over a busy picture is backed by a see-through dark panel so its words read (the owner,
                # 2026-10-28: "I can barely read the text ... it blends too much"); the outline stays the look
                b["fill"] = b.get("backing") or "#1A1A1A99"
    attach_marks(layout, drawn)
    # Declared order IS reading order. Sorting by top_pct looked harmless
    # until gutter-positioned elements (which have no top_pct) sorted to the
    # front and stacked on the headline. Do not re-sort.

    for i, el in enumerate(drawn):
        # A zone's own declared height wins. Falling back to "the gap to the
        # next element" lets a zone grow into empty frame and swallow the
        # picture — which is exactly how a two-line subhead became five lines
        # of type over the subject's face on 2026-08-19.
        nxt = drawn[i + 1] if i + 1 < len(drawn) else None
        own = el.get("height_pct")
        if own is not None:
            band_pct = float(own)
        else:
            band_pct = (float(nxt.get("top_pct", 100)) - float(el.get("top_pct", 0))
                        if nxt else 100 - float(el.get("top_pct", 0)))
        band_px = max(40, round(band_pct / 100 * H)) - round(0.005 * H)

        left = float(el.get("left_pct", M.get("left", 0)))
        right = float(el.get("right_pct", 100 - M.get("right", 0)))
        span_px = max(40, round((right - left) / 100 * W))
        # a box's padding sits OUTSIDE its words: take it off the span, so the box itself stays inside the frame
        # (2026-10-28: a widened price pill ran off both edges)
        boxpad = round(float(num((el.get("box") or {}).get("pad_pct"), 1.0)) / 100 * H) if el.get("box") else 0
        span_px = max(40, span_px - 2 * boxpad)

        # A gutter positions this block relative to the one above it — the
        # vertical rhythm the teardown measured. Absolute tops are what
        # collide once copy length changes; a gutter never does.
        gut = num(el.get("gutter_pct"))
        if gut is not None and prev_bottom is not None:
            top_px = prev_bottom + round(gut / 100 * H)
            # copy shorter than the swipe's never pulls the next block up out of its own place (2026-10-28: an offer bar
            # rose over the product because the list above it ran two lines shorter)
            if num(el.get("top_pct")) is not None:
                top_px = max(top_px, round(num(el.get("top_pct")) / 100 * H))
            if prev_grown is not None:
                # the block above grew past its own band (a second line): this one keeps the place it was laid out
                # for while there is room, and only moves down when the grown block would reach it (2026-10-27: a
                # two-line top caption pushed the next line onto the subject's neck)
                top_px = max(prev_grown[0] + round(gut / 100 * H), prev_bottom + round(0.01 * H))
        else:
            top_px = round(num(el.get("top_pct"), 0) / 100 * H)
        # no measured cap height: the zone's own height says how big its type is (one line ≈ 0.7 of the zone; 2026-10-28,
        # a swipe's giant "SALE" came out at the 3% default because the read left cap_pct empty)
        cap = num(el.get("cap_pct"))
        if cap is None and num(el.get("height_pct")):
            lines = max(1, int(num(el.get("max_lines")) or 1))
            cap = num(el.get("height_pct")) * 0.7 / lines
        pt0 = max(6, round(((cap if cap is not None else 3) / 100 * H) / CAP_RATIO))
        key = el.get("font") or DEFAULT_FONT
        wt = str(el.get("weight", "")).strip().lower()
        bold = wt in BOLD_WORDS
        table = FONTS_BOLD if bold else fonts
        if wt in BLACK_WORDS and Path(FONTS_BLACK.get(key, "")).exists():
            table = FONTS_BLACK
        font = table.get(key, fonts.get(key, key if "/" in str(key)
                                        else fonts[DEFAULT_FONT]))
        if bold and not Path(font).exists():          # no bold cut on disk
            font = fonts.get(key, fonts[DEFAULT_FONT])
        if el.get("italic") and Path(FONTS_ITALIC.get(key, "")).exists():
            font = FONTS_ITALIC[key]
        if not Path(font).exists():
            sys.exit(f"font not found for {el.get('element')!r}: {font}")
        kern = track_px(el.get("tracking", 0), pt0)

        align = (el.get("align") or "center").lower()

        # segments let one line carry two colors — the chain's accent split
        segs = el.get("segments") or [{"text": el.get("text", ""),
                                       "color": el.get("color", "#FFFFFF")}]
        if el.get("stroke"):
            segs = [dict(s, stroke=s.get("stroke") or el["stroke"]) for s in segs]
        # A line break a person typed (" / ") is a line, never a reason to shrink (the owner, 2026-10-27: "we should be
        # able to create new line breaks in copy as needed"): the zone takes as many lines as were typed, its band
        # grows with them.
        typed = max(str(s.get("text", "")).replace("\\n", "\n").replace(" / ", "\n").count("\n") + 1 for s in segs)
        max_lines_el = max(num(el.get("max_lines")) or 1, typed) if el.get("max_lines") or typed > 1 else None
        band_decl = band_px
        if typed > 1 and not (num(el.get("height_pct")) and (num(el.get("max_lines")) or 1) >= typed):
            # a band measured for ONE line grows with the typed lines; a zone measured for its whole block (its own
            # height, as many lines as typed) does not, or a five-line block grew over the product (2026-10-28)
            band_px = band_px * typed
        block, pt_used = render_block(segs, font, pt0, kern, span_px, band_px,
                                      tmpdir, i, el.get("case"),
                                      None if typed > 1 else num(el.get("measure")), max_lines_el,
                                      {"center": "center", "right": "east"}
                                      .get(align, "west"))
        if block is not None and pt_used < pt0:
            # Widen before shrinking (the owner, 2026-10-27, on a top line set at half the size of the two under it: "I
            # can barely read the top line"). The swipe's span was measured around ITS words; ours run longer, and a
            # line that only fits by shrinking gets the frame's full measure first (same centre for a centred line).
            # The narrower span is kept only when the wide one buys no size.
            ml, mr = float(M.get("left", 3)), 100 - float(M.get("right", 3))
            wl, wr = (ml, mr) if align == "center" else (left, mr) if align != "right" else (ml, right)
            if align == "center":
                half = min((left + right) / 2 - ml, mr - (left + right) / 2)
                wl, wr = (left + right) / 2 - half, (left + right) / 2 + half
            # widening never crosses a keep-clear area beside the block (2026-10-28: a left-hand checklist widened
            # straight across the product it sits beside)
            btop = top_px / H * 100
            bbot = btop + band_px / H * 100
            for kc in keep:
                if kc.get("top", 0) < bbot and kc.get("bottom", 100) > btop:
                    if kc.get("left", 0) >= right - 0.01:
                        wr = min(wr, float(kc.get("left", 100)))
                    if kc.get("right", 100) <= left + 0.01:
                        wl = max(wl, float(kc.get("right", 0)))
            if align == "center":
                half = min((left + right) / 2 - wl, wr - (left + right) / 2)
                wl, wr = (left + right) / 2 - half, (left + right) / 2 + half
            wide_px = max(40, round((wr - wl) / 100 * W) - 2 * boxpad)
            if wide_px > span_px:
                b2, p2 = render_block(segs, font, pt0, kern, wide_px, band_px, tmpdir, i, el.get("case"),
                                      None, max_lines_el,
                                      {"center": "center", "right": "east"}.get(align, "west"))
                if b2 is not None and p2 > pt_used:
                    block, pt_used, left, right, span_px = b2, p2, wl, wr, wide_px
                    notes.append(f"{el.get('element')}: widened to {round(wl)}–{round(wr)}% so it keeps its size")
        one_line_box = bool(el.get("box")) and (num(el.get("max_lines")) or 1) <= 1 and typed == 1
        # a boxed line breaks only when one line would leave it under 60% of its size (our badge line ran 54
        # characters against the swipe's 34 and came out unreadable)
        if block is not None and (pt_used < 0.8 * pt0 and (max_lines_el or 1) < 2 and not one_line_box
                                  or one_line_box and pt_used < 0.6 * pt0):
            # a boxed one-line element (a pill, a badge) is one line: it widens and shrinks, it never breaks (2026-10-28,
            # a price pill broke onto two lines and grew into a block a third of the frame wide)
            # Break onto a second line before shrinking past four-fifths (the owner, 2026-10-27: the five longer top lines
            # came out a third the size of the lines under them). The block below follows by its gutter.
            b3, p3 = render_block(segs, font, pt0, kern, span_px, (band_px or 0) * 2 or None, tmpdir, i,
                                  el.get("case"), None, 2, {"center": "center", "right": "east"}.get(align, "west"))
            if b3 is not None and p3 > pt_used:
                block, pt_used = b3, p3
                notes.append(f"{el.get('element')}: broke onto two lines so it keeps its size")
        if block is not None and pt_used < pt0:
            # Widen before shrinking (the owner, 2026-10-27, on a top line set at half the size of the two under it: "I
            # can barely read the top line"). The swipe's span was measured around ITS words; ours run longer, and a
            # line that only fits by shrinking gets the frame's full measure first (same centre for a centred line).
            # The narrower span is kept only when the wide one buys no size.
            ml, mr = float(M.get("left", 3)), 100 - float(M.get("right", 3))
            wl, wr = (ml, mr) if align == "center" else (left, mr) if align != "right" else (ml, right)
            if align == "center":
                half = min((left + right) / 2 - ml, mr - (left + right) / 2)
                wl, wr = (left + right) / 2 - half, (left + right) / 2 + half
            wide_px = max(40, round((wr - wl) / 100 * W))
            if wide_px > span_px:
                b2, p2 = render_block(segs, font, pt0, kern, wide_px, band_px, tmpdir, i, el.get("case"),
                                      None, num(el.get("max_lines")),
                                      {"center": "center", "right": "east"}.get(align, "west"))
                if b2 is not None and p2 > pt_used:
                    block, pt_used, left, right, span_px = b2, p2, wl, wr, wide_px
                    notes.append(f"{el.get('element')}: widened to {round(wl)}–{round(wr)}% so it keeps its size")
        if block is not None and pt_used < 0.8 * pt0 and (num(el.get("max_lines")) or 1) < 2:
            # Break onto a second line before shrinking past four-fifths (the owner, 2026-10-27: the five longer top lines
            # came out a third the size of the lines under them). The block below follows by its gutter.
            b3, p3 = render_block(segs, font, pt0, kern, span_px, (band_px or 0) * 2 or None, tmpdir, i,
                                  el.get("case"), None, 2, {"center": "center", "right": "east"}.get(align, "west"))
            if b3 is not None and p3 > pt_used:
                block, pt_used = b3, p3
                notes.append(f"{el.get('element')}: broke onto two lines so it keeps its size")
        if block is None:
            continue
        if pt_used != pt0:
            notes.append(f"{el.get('element')}: {pt0}→{pt_used}pt "
                         f"({el.get('cap_pct')}% cap → "
                         f"{round(pt_used * CAP_RATIO / H * 100, 1)}%) "
                         f"to fit its span and band")

        if el.get("box"):
            # a box hugs its words: a wrapped caption is as wide as its whole span, and a pill drawn round that
            # stretched across the frame (2026-10-28)
            hug = tmpdir / f"el{i:02d}_hug.png"
            sh(["magick", str(block), "-trim", "+repage", str(hug)])
            block = hug
        tail = trailing(el, segs, font, pt_used, kern, block, tmpdir, i, align)
        if tail:
            block = tail
        bw, bh = dims(block)
        measure = num(el.get("measure"))   # may be "[MISSING: measure]"
        if measure:
            longest = max((len(l) for seg in segs
                           for l in str(seg.get("text", "")).split(" / ")), default=0)
            body = " ".join(str(seg.get("text", "")) for seg in segs)
            if len(body) > measure * (el.get("max_lines") or 2):
                notes.append(
                    f"{el.get('element')}: copy is {len(body)} characters "
                    f"against a measure of {measure} x {el.get('max_lines') or 2} "
                    f"lines = {measure * (el.get('max_lines') or 2)}. The source "
                    f"line fitted; ours does not, so the size dropped to make "
                    f"room. This is a copy-length decision, not a layout one.")
        if align == "center":
            x = round((left + right) / 2 / 100 * W - bw / 2)
        elif align == "right":
            x = round(right / 100 * W - bw)
        else:
            x = round(left / 100 * W)

        box = el.get("box")
        if box:
            pad = round(float(box.get("pad_pct", 1.0)) / 100 * H)
            x0, y0, x1, y1 = x - pad, top_px - pad, x + bw + pad, top_px + bh + pad
            r = round(float(num(box.get("radius_pct"), 0) or 0) / 100 * H)
            shape = f"roundrectangle {x0},{y0} {x1},{y1} {r},{r}" if r else f"rectangle {x0},{y0} {x1},{y1}"
            st = box.get("stroke") or {}
            fill = box.get("fill") or "none"
            if st:
                sw_px = max(1, round(float(num(st.get("width_pct"), 0.3)) / 100 * H))
                cmd += ["-fill", fill, "-stroke", st.get("color", "#FFFFFF"), "-strokewidth", str(sw_px),
                        "-draw", shape, "-stroke", "none", "-strokewidth", "0"]
            elif is_gold(fill):
                # a gold button is metal too, the same shine as gold type
                from PIL import Image, ImageDraw
                plate_box = Path(tmpdir) / f"box{i}.png"
                m = Image.new("L", (x1 - x0, y1 - y0), 0)
                ImageDraw.Draw(m).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius=r, fill=255)
                Image.merge("RGBA", (m, m, m, m)).save(plate_box)
                metallic(plate_box, fill)
                cmd += [str(plate_box), "-gravity", "northwest", "-geometry", f"+{x0}+{y0}", "-composite"]
            else:
                cmd += ["-fill", fill, "-draw", shape]
        for kc in keep:
            kx0, kx1 = kc.get("left", 0) / 100 * W, kc.get("right", 100) / 100 * W
            ky0, ky1 = kc.get("top", 0) / 100 * H, kc.get("bottom", 100) / 100 * H
            if not (x + bw < kx0 or x > kx1 or top_px + bh < ky0 or top_px > ky1):
                notes.append(f"{el.get('element')}: OVERLAPS keep-clear "
                             f"{kc.get('name', 'region')} — the plate needs "
                             f"regenerating, or this block needs moving")

        pap = el.get("paper")
        if pap:
            pp, pxx, pyy = torn_paper(pap, W, H, top_px, bh, tmpdir, i)
            cmd += [str(pp), "-gravity", "northwest", "-geometry", f"+{pxx}+{pyy}", "-composite"]
        put, px_, py_ = shadowed(el, block, tmpdir, i, pt_used, x, top_px)
        cmd += [str(put), "-gravity", "northwest",
                "-geometry", f"+{px_}+{py_}", "-composite"]
        bul = el.get("bullet") or {}
        if bul.get("lines") and bul.get("of"):
            # the swipe's bullets HANG: drawn just left of the text axis at each item's first line, so every line of an
            # item starts on the same axis (2026-10-28)
            lh = bh / float(bul["of"])
            bp = tmpdir / f"el{i:02d}_bullet.png"
            bw_, bh_ = draw(bul.get("glyph", "\u2022"), font, pt_used, el.get("color", "#FFFFFF"), 0, None, bp)
            gap = round(pt_used * 0.55)
            for k in bul["lines"]:
                by = round(top_px + k * lh + (lh - bh_) / 2)
                cmd += [str(bp), "-gravity", "northwest", "-geometry", f"+{max(0, x - gap - bw_)}+{by}", "-composite"]
        prev_bottom = top_px + bh
        prev_grown = (top_px + band_decl, bh) if bh > band_decl + round(0.005 * H) else None
        placed += 1

    if not placed:
        sys.exit("no elements matched — check --file against the layer's "
                 "'file' values")
    cmd.append(str(a.out))
    subprocess.run(cmd, check=True)
    for n in notes:
        print(f"  note: {n}")
    print(f"{placed} elements set on {W}x{H} → {a.out}")


if __name__ == "__main__":
    main()
