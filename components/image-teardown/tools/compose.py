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
DEFAULT_FONT = "condensed-grotesque"
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


def draw(text, font, pt, color, kern, span_px, tmp, grav="west"):
    cmd = ["magick", "-background", "none", "-fill", color, "-font", font,
           "-pointsize", str(pt)]
    if kern:
        cmd += ["-kerning", str(kern)]
    # A segment is a fragment of one line: render it at its natural width with
    # label: (no wrapping). Only whole blocks get caption: and a wrap width.
    if span_px is None:
        cmd += ["-gravity", "west", f"label:{text}", str(tmp)]
    else:
        cmd += ["-size", f"{span_px}x", "-gravity", grav,
                f"caption:{text}", str(tmp)]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return dims(tmp)


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
                 grav if len(segs) == 1 else "west")
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

    tmpdir = Path(a.out).resolve().parent / ".compose-tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)

    cmd = ["magick", str(a.plate)]
    placed, notes, prev_bottom = 0, [], None

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

        # A gutter positions this block relative to the one above it — the
        # vertical rhythm the teardown measured. Absolute tops are what
        # collide once copy length changes; a gutter never does.
        gut = el.get("gutter_pct")
        if gut is not None and prev_bottom is not None:
            top_px = prev_bottom + round(float(gut) / 100 * H)
        else:
            top_px = round(float(el.get("top_pct", 0)) / 100 * H)
        pt0 = max(6, round((float(el.get("cap_pct", 3)) / 100 * H) / CAP_RATIO))
        key = el.get("font") or DEFAULT_FONT
        bold = str(el.get("weight", "")).strip().lower() in BOLD_WORDS
        table = FONTS_BOLD if bold else fonts
        font = table.get(key, fonts.get(key, key if "/" in str(key)
                                        else fonts[DEFAULT_FONT]))
        if bold and not Path(font).exists():          # no bold cut on disk
            font = fonts.get(key, fonts[DEFAULT_FONT])
        if not Path(font).exists():
            sys.exit(f"font not found for {el.get('element')!r}: {font}")
        kern = track_px(el.get("tracking", 0), pt0)

        align = (el.get("align") or "center").lower()

        # segments let one line carry two colors — the chain's accent split
        segs = el.get("segments") or [{"text": el.get("text", ""),
                                       "color": el.get("color", "#FFFFFF")}]
        block, pt_used = render_block(segs, font, pt0, kern, span_px, band_px,
                                      tmpdir, i, el.get("case"),
                                      el.get("measure"), el.get("max_lines"),
                                      {"center": "center", "right": "east"}
                                      .get(align, "west"))
        if block is None:
            continue
        if pt_used != pt0:
            notes.append(f"{el.get('element')}: {pt0}→{pt_used}pt "
                         f"({el.get('cap_pct')}% cap → "
                         f"{round(pt_used * CAP_RATIO / H * 100, 1)}%) "
                         f"to fit its span and band")

        bw, bh = dims(block)
        measure = el.get("measure")
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
            cmd += ["-fill", box.get("fill", "none"), "-draw",
                    f"rectangle {x - pad},{top_px - pad} "
                    f"{x + bw + pad},{top_px + bh + pad}"]
        for kc in keep:
            kx0, kx1 = kc.get("left", 0) / 100 * W, kc.get("right", 100) / 100 * W
            ky0, ky1 = kc.get("top", 0) / 100 * H, kc.get("bottom", 100) / 100 * H
            if not (x + bw < kx0 or x > kx1 or top_px + bh < ky0 or top_px > ky1):
                notes.append(f"{el.get('element')}: OVERLAPS keep-clear "
                             f"{kc.get('name', 'region')} — the plate needs "
                             f"regenerating, or this block needs moving")

        cmd += [str(block), "-gravity", "northwest",
                "-geometry", f"+{x}+{top_px}", "-composite"]
        prev_bottom = top_px + bh
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
