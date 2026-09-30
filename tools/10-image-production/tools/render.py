#!/usr/bin/env python3
"""Render one finished ad from the format's own layout data.

    render.py <brief.md> <plate.png> <out.png> [packshot.png] [variant] [--picture|--over|--all] [--brand <brand>]

The brand's logo and colours are read from `brands/<brand>/brand-identity/`
(old name `identity/`). The
brand is the one named with `--brand`, else the one teardown recorded for the
brief's own run (`vars/brand_name.md`). There is no default brand.

Every swipe is a different format. The teardown measured that format and the
brief carries it as data: margins, per-zone position, measure, cap height,
alignment, case, colour, tracking, max lines, decorations, and the zones that
must stay clear. This renderer draws exactly that and nothing else.

**Measured cause, 2026-08-31: one hardcoded layout was applied to every
swipe.** Angle 02's design — centred wordmark, white square, headline box,
corner sticker — was drawn over angle 06 and angle 09, whose formats share
none of it. Both were shipped. The layout data had been sitting in the brief
unread the whole time. So: no element is drawn unless a zone names it. A
format with no wordmark zone gets no wordmark.
"""
import json, os, re, subprocess, sys
from pathlib import Path

W, H = 768, 1344
# Brand truth left the lab on 2026-09-02: the two homes were
# consolidated into the repo-root brands/. These paths pointed at the
# lab copy, so the packshot stopped existing and the product silently
# vanished from six finished ads.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

# Set per render by use_brand(). Until 2026-09-20 this was one brand's folder
# as a module constant, so every logo, colour and font read went to that brand
# whoever the ad was for.
BRAND = None
BRAND_NAME = None


def use_brand(name):
    """Point the renderer at a brand. A missing brand is an error, not a default."""
    global BRAND, BRAND_NAME
    BRAND_NAME = P.need_brand(name, "the logo and the brand's colours")
    BRAND = P.BRANDS / BRAND_NAME
    return BRAND


def brand_dir():
    if BRAND is None:
        P.need_brand(None, "the logo and the brand's colours")
    return BRAND


def brand_for_brief(brief, named=None):
    """--brand, else the brand teardown recorded beside this brief."""
    if named:
        return named
    f = Path(brief).resolve().parent.parent / "vars/brand_name.md"
    name = f.read_text().strip().lower() if f.is_file() else ""
    return name if name and (P.BRANDS / name).is_dir() else None


SUP = Path("/System/Library/Fonts/Supplemental")

FONTS = {
    ("grotesque", "bold"): "Arial Bold.ttf",
    ("grotesque", "medium"): "Arial.ttf",
    ("grotesque", "regular"): "Arial.ttf",
    ("compressed-grotesque", "bold"): "Arial Narrow Bold.ttf",
    ("compressed-grotesque", "medium"): "Arial Narrow.ttf",
    ("compressed-grotesque", "regular"): "Arial Narrow.ttf",
    ("serif", "bold"): "Georgia Bold.ttf",
    ("serif", "medium"): "Georgia.ttf",
    ("serif", "regular"): "Georgia.ttf",
}
TRACK = {"tight": -0.030, "standard": 0.0, "wide": 0.10}
_capcache = {}


def num(v, default=None):
    """A number from the brief, whatever shape the model wrote it in.

    Briefs are model-written, so a count arrives as 2, as "2", or as
    "[MISSING: max_lines]". Comparing a string to an int raised mid-build
    and killed a whole swipe's compose step on 2026-08-31. A value that is
    not a number is not a number — take the default and carry on."""
    if isinstance(v, bool) or v is None:
        return default
    if isinstance(v, (int, float)):
        return v
    m = re.search(r"-?\d+(?:\.\d+)?", str(v))
    return float(m.group()) if m else default


def lum(hexv):
    """Relative luminance, sRGB."""
    try:
        c = [int(hexv[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    except (ValueError, IndexError):
        return 1.0
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def behind(e, d):
    """What is actually under this zone — a panel, the ground, or the picture.

    Checking type against the ground alone missed two real cases: copy the
    right colour for the ground sitting on a panel of nearly that colour,
    and white copy over a full-bleed photograph being called invisible
    because the nominal ground was also white. "#PHOTO" means the caller
    should measure the pixels instead of trusting a hex."""
    top = num(e.get("top_pct"), None)
    lay = d.get("layout", {}) or {}
    ground = lay.get("ground", "#FFFFFF")
    if (lay.get("picture") or {}).get("treatment") == "full_bleed":
        ground = "#PHOTO"
    if top is None:
        return ground
    for b in (d.get("layout", {}).get("blocks") or []):
        if num(b.get("top_pct"), 0) <= top <= num(b.get("bottom_pct"), 100):
            return b.get("color") or b.get("fill") or ground
    return ground


def neutral(hexv):
    """Greys, blacks and whites belong to no brand and carry through safely."""
    try:
        r, g, b = (int(hexv[i:i + 2], 16) for i in (1, 3, 5))
    except (ValueError, IndexError):
        return True
    return max(r, g, b) - min(r, g, b) < 24


def brand_colors(brand_dir):
    """Hexes this brand owns, from its identity folder. Empty is a real answer:
    a brand with no documented palette has no chromatic colour to spend."""
    out = set()
    for f in P.identity_dir(brand_dir).glob("*.md"):
        out |= {m.lower() for m in re.findall(r"#[0-9A-Fa-f]{6}", f.read_text())}
    return out


def safe_color(want, allowed, fallback, element, notes):
    """A chromatic colour that is not ours came from the swipe. Inheriting it
    puts a competitor's brand colour in our ad — the injection stage is meant
    to replace it, and when it does not, the renderer must not paint it.

    Measured cause, 2026-08-31: a headline shipped in <competitor>'s pink."""
    want = (want or fallback).lower()
    if neutral(want) or want in allowed:
        return want
    notes.append(f"{element}: {want} is not one of {BRAND_NAME or 'the brand'}'s colours "
                 f"(swipe accent leaked through injection) — drew {fallback}")
    return fallback


TMP = Path(f"/tmp/render-{os.getpid()}")


def sh(c):
    """Never wait forever on a draw. A magick call that reads and writes the
    same path can stall indefinitely; a stalled build looks identical to a
    slow one and eats the whole session."""
    try:
        return subprocess.run(c, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        print(f"    ! timed out: {' '.join(str(x) for x in c[:4])} ...")
        return subprocess.CompletedProcess(c, 1, "", "timeout")


class Canvas:
    """Ping-pongs between two files so no magick call is ever both the reader
    and the writer of one path."""

    def __init__(self, base):
        self.a, self.b, self.n = f"{base}-0.png", f"{base}-1.png", 0

    @property
    def cur(self):
        return self.a if self.n % 2 == 0 else self.b

    @property
    def nxt(self):
        return self.b if self.n % 2 == 0 else self.a

    def step(self):
        """Advance only if the write actually happened.

        Measured cause, 2026-09-02. One magick call failed, step() advanced
        anyway, and every stage after it read a file that had never been
        written — so the offer panel, three copy zones and the product all
        vanished from six ads while the build reported them clean. A failed
        stage must cost its own output, never everything downstream."""
        if not os.path.exists(self.nxt):
            self.misses = getattr(self, "misses", 0) + 1
            return False
        self.n += 1
        return True


def font_for(e):
    fam = (e.get("font") or "grotesque").lower()
    wt = (e.get("weight") or "regular").lower()
    if fam not in {f for f, _ in FONTS}:
        fam = "serif" if "serif" in fam else "grotesque"
    return str(SUP / FONTS.get((fam, wt), FONTS[(fam, "regular")]))


def cap_ratio(font):
    """Cap height as a fraction of pointsize, measured from the font itself."""
    if font not in _capcache:
        r = sh(["magick", "-background", "none", "-fill", "black", "-font", font,
                "-pointsize", "200", "label:H", "-trim", "-format", "%h", "info:"])
        try:
            _capcache[font] = int(r.stdout.strip()) / 200.0
        except ValueError:
            _capcache[font] = 0.716
    return _capcache[font]


def wrap(text, font, pt, kern, avail, max_lines):
    """Break copy to the measure it was given.

    The renderer only ever split on explicit breaks, so a paragraph written
    as one sentence was drawn as one line and ran off the frame — measured
    2026-09-01 on a body slot 172px over its measure. Wrapping comes before
    shrinking: copy should fill its measure at the size the template chose,
    not be shrunk until one long line happens to fit."""
    out = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for w in words:
            trial = f"{line} {w}".strip()
            r = sh(["magick", "-font", font, "-pointsize", str(pt),
                    "-kerning", f"{kern:.2f}", f"label:{trial}",
                    "-format", "%w", "info:"])
            try:
                wide = int(r.stdout.strip())
            except ValueError:
                wide = 0
            if wide > avail and line:
                out.append(line); line = w
            else:
                line = trial
        if line:
            out.append(line)
    if max_lines and len(out) > max_lines:
        return out[:int(max_lines)], True
    return out, False


def block(text, font, pt, kern, color, lead_mult=1.16, out=None):
    """One text block as a transparent PNG. Returns (path, w, h)."""
    out = out or f"{TMP}-blk.png"
    lead = int(round(pt * lead_mult))
    sh(["magick", "-background", "none", "-fill", color, "-font", font,
        "-pointsize", str(pt), "-kerning", f"{kern:.2f}",
        "-interline-spacing", str(lead - pt), f"label:{text}",
        "-trim", "+repage", out])
    r = sh(["magick", out, "-format", "%w %h", "info:"])
    w, h = (int(v) for v in r.stdout.split())
    return out, w, h


def draw_logo(e, canvas, notes, drawn=None):
    """The brand's real wordmark, never typeset.

    A wordmark is either right or it is wrong, and set in Arial it is
    wrong — an ad went out on 2026-08-31 with <brand> typed."""
    ident = P.identity_dir(brand_dir())          # brand-identity/, old identity/
    f = ident / "logo-white.png"
    if (e.get("tone") or "light") == "dark":
        f = ident / "logo-dark.png"
    if not f.is_file():
        notes.append(f"{e['element']}: no logo file at {f.name} — none drawn")
        return
    w = int(W * num(e.get("span_pct"), 26) / 100)
    x = int(W * num(e.get("left_pct"), 0) / 100)
    x = x + (int(W * num(e.get("right_pct"), 100) / 100) - x - w) // 2 \
        if (e.get("align") or "center") == "center" else x
    if drawn is not None:
        wh = int(w * 0.34)
        drawn.append((e["element"], x,
                      int(H * num(e.get("top_pct"), 6) / 100), x + w,
                      int(H * num(e.get("top_pct"), 6) / 100) + wh))
    sh(["magick", canvas.cur, "(", str(f), "-resize", f"{w}x", ")",
        "-gravity", "northwest",
        "-geometry", f"+{x}+{int(H * num(e.get('top_pct'), 6) / 100)}",
        "-composite", canvas.nxt])
    canvas.step()


def draw_frame(e, canvas, notes, plate=None, safe=None, drawn=None):
    """A stroked rectangle that points at the thing worth looking at.

    With `"find": "damage"` the rectangle is measured off this plate rather
    than fixed, because the damage is somewhere different in every
    photograph. A square at a fixed position frames blank skin, which is
    worse than no square: it points confidently at nothing. Measured
    2026-09-02 — a frame landed on a face while the spots were on a
    shoulder."""
    x0 = int(W * num(e.get("left_pct"), 10) / 100)
    x1 = int(W * num(e.get("right_pct"), 90) / 100)
    y0 = int(H * num(e.get("top_pct"), 30) / 100)
    y1 = int(H * num(e.get("bottom_pct"), 55) / 100)
    if e.get("find") == "damage" and plate:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from find_spots import spot_centre
            r = spot_centre(plate, box_w_pct=num(e.get("span_pct"), 52),
                            top_limit=num(e.get("search_to"), 0.72),
                            top_from=num(e.get("search_from"), 0.18))
            sx, sy = W / r["frame_w"], H / r["frame_h"]
            x0, y0 = int(r["x"] * sx), int(r["y"] * sy)
            x1, y1 = x0 + int(r["w"] * sx), y0 + int(r["h"] * sy)
            if safe:                       # never let it leave the feed crop
                t = int(H * num(safe.get("top_pct"), 0) / 100)
                b = int(H * num(safe.get("bottom_pct"), 100) / 100)
                shift = max(0, t - y0) - max(0, y1 - b)
                y0, y1 = y0 + shift, y1 + shift
            notes_density = r["density"]
            if notes_density < 0.05:
                notes.append(f"{e['element']}: the densest patch on this "
                             f"plate scores {notes_density} — there may be "
                             f"nothing worth framing")
        except Exception as exc:
            notes.append(f"{e['element']}: could not measure the damage "
                         f"({exc}) — drew the fixed rectangle")
    # Furniture collides too. A measured frame moves with the damage, so it
    # can land on the wordmark — which nothing noticed, because only type
    # was being tracked.
    if drawn is not None:
        for pe, px0, py0, px1, py1 in drawn:
            if x0 < px1 and x1 > px0 and y0 < py1 and y1 > py0:
                notes.append(f"{e['element']} overlaps {pe}")
        drawn.append((e["element"], x0, y0, x1, y1))
    sh(["magick", canvas.cur, "-fill", "none",
        "-stroke", e.get("color", "#FFFFFF"),
        "-strokewidth", str(int(num(e.get("stroke_px"), 6))),
        "-draw", f"rectangle {x0},{y0} {x1},{y1}", canvas.nxt])
    canvas.step()


def draw_zone(e, canvas, y_cursor, notes, allowed=frozenset(), variant="",
              ground="#FFFFFF", drawn=None, band=None):
    """Draw one text zone. Returns the y its ink ends at."""
    drawn = [] if drawn is None else drawn
    text = e.get("text") or ""
    if e.get("variants"):
        # The variant this build is for, not whichever came first. Zone copy
        # and picture variation have to name the same variant or the ad says
        # one thing and shows another.
        pick = next((v for v in e["variants"]
                     if v.get("label", "").lower() == variant.lower()), None)
        if variant and not pick:
            notes.append(f"{e['element']}: no copy variant '{variant}' — "
                         f"drew {e['variants'][0].get('label')}")
        text = (pick or e["variants"][0])["text"]
    if not text:
        return y_cursor
    if (e.get("case") or "").lower() == "upper":
        text = text.upper()

    # Models write a line break as "\n", and just as often as " / ". Splitting
    # on the newline alone printed a literal slash in the middle of a headline.
    text = re.sub(r"\s+/\s+", "\n", text)
    lines = text.split("\n")
    mx = num(e.get("max_lines"), None)

    font = font_for(e)
    x_l = int(W * (num(e.get("left_pct"), 0)) / 100)
    x_r = int(W * (num(e.get("right_pct"), 100)) / 100)
    avail = x_r - x_l
    color = safe_color(e.get("color"), allowed, "#111111", e["element"], notes)

    pt = int(round(W * 0 + (H * (num(e.get("cap_pct"), 2)) / 100) / cap_ratio(font)))
    kern = pt * TRACK.get((e.get("tracking") or "standard").lower(), 0.0)
    floor = int(pt * 0.45)
    # Scale to fit in one step, then verify. Stepping down 2pt at a time cost
    # two magick calls per point and stalled a four-zone format outright.
    lead = num(e.get("leading"), 1.16)
    # Shrink until the copy fits its measure AND its line count, and only
    # then call it too long. Wrapping at full size and reporting the
    # overflow first condemned copy that fits perfectly one step smaller —
    # every ad in a batch of six on 2026-09-02.
    src, clipped = text, False
    for _ in range(9):
        lines, clipped = wrap(src, font, pt, kern, avail, mx)
        text = "\n".join(lines)
        blk, bw, bh = block(text, font, pt, kern, color, lead)
        if bw <= avail and not clipped:
            break
        if pt <= floor:
            break
        pt = max(floor, int(pt * 0.92 if clipped else pt * avail / bw))
        kern = pt * TRACK.get((e.get("tracking") or "standard").lower(), 0.0)
    if clipped:
        notes.append(f"{e['element']}: copy needs more than {int(mx)} lines "
                     f"even at the smallest size allowed — write it shorter.")
    if bw > avail:
        notes.append(f"{e['element']}: copy still overruns its measure by "
                     f"{bw-avail}px at the smallest size allowed — the line is "
                     f"too long for this format, price it in characters")

    top = num(e.get("top_pct"), None)
    y = int(H * top / 100) if top is not None else \
        y_cursor + int(H * (num(e.get("gutter_pct"), 2)) / 100)

    # A flowed zone must clear what is already on the page in its own
    # columns — its panel included. Tuning the gutter only moves the
    # collision around; measuring it removes it.
    if top is None:
        pad_box = int(H * 0.012) if e.get("box") else 0
        for _pe, px0, py0, px1, py1 in drawn:
            if x_l < px1 and x_r > px0 and (y - pad_box) < py1:
                y = py1 + pad_box + int(H * 0.008)

    align = (e.get("align") or "left").lower()
    x = x_l if align == "left" else \
        x_l + (avail - bw) // 2 if align == "center" else x_r - bw

    box = e.get("box")
    if isinstance(box, dict) and any(
            isinstance(v, str) and v.startswith("[MISSING")
            for v in box.values()):
        # A placeholder is the brief saying it does not know. Drawing it with
        # a default is filling it in on the brief's behalf, silently.
        notes.append(f"{e['element']}: its panel carries a [MISSING] value — "
                     f"drew no panel rather than invent one")
        box = None
    if box:
        # A box is either a colour behind the copy, or a block with its own
        # measured rectangle — the offer block at the foot of a format is the
        # second kind, and it runs edge to edge.
        if isinstance(box, dict):
            # "fill" or "color" — briefs use both. Reading only one and
            # defaulting to white drew a page of empty white rectangles
            # over the copy, 2026-09-01.
            bc = box.get("fill") or box.get("color")
            if not bc:
                notes.append(f"{e['element']}: panel with no colour — "
                             f"drew none rather than guess white")
                bc = None
            bx0 = 0 if box.get("full_width") else x_l
            bx1 = W if box.get("full_width") else x_r
            by0 = int(H * box["top_pct"] / 100) if "top_pct" in box \
                else y - int(H * 0.012)
            by1 = int(H * box["bottom_pct"] / 100) if "bottom_pct" in box \
                else y + bh + int(H * 0.012)
            # centre the copy in the block it was given
            y = by0 + (by1 - by0 - bh) // 2
        else:
            bc, pad = box, int(H * 0.012)
            bx0, bx1, by0, by1 = x_l, x_r, y - pad, y + bh + pad
        # A panel is opaque. It hides whatever was drawn under it just as
        # surely as overlapping type does, so it counts as drawn.
        for pe, px0, py0, px1, py1 in drawn:
            if bx0 < px1 and bx1 > px0 and by0 < py1 and by1 > py0:
                notes.append(f"{e['element']}'s panel covers {pe} — "
                             f"{pe} is hidden behind it")
        drawn.append((f"{e['element']} panel", bx0, by0, bx1, by1))
        if bc:
            sh(["magick", canvas.cur, "-fill", bc,
                "-draw", f"rectangle {bx0},{by0} {bx1},{by1}", canvas.nxt])
            canvas.step()

    for d in (e.get("decorations") or []):
        d = d.lower()
        if "rule" not in d:
            continue
        m = re.search(r"#([0-9a-f]{6})", d, re.I)
        rc, gap, my = ("#" + m.group(1) if m else color), 22, y + bh // 2
        if "left of text" in d:
            sh(["magick", canvas.cur, "-stroke", rc, "-strokewidth", "2",
                "-draw", f"line {x_l},{my} {x-gap},{my}", canvas.nxt])
            canvas.step()
        if "right of text" in d:
            sh(["magick", canvas.cur, "-stroke", rc, "-strokewidth", "2",
                "-draw", f"line {x+bw+gap},{my} {x_r},{my}", canvas.nxt])
            canvas.step()

    # A zone with a panel is checked against its panel, not the ground.
    # Skipping the check whenever a box existed is what let a whole offer
    # row render as empty white rectangles — white type on white panels,
    # measured 2026-09-01.
    bx = e.get("box")
    against = ground
    if isinstance(bx, dict):
        against = bx.get("fill") or bx.get("color") or ground
    elif isinstance(bx, str):
        against = bx
    if against == "#PHOTO":
        # On a full-bleed photograph the background is the picture, not the
        # ground colour. Comparing white type to a nominal white ground
        # called legible copy invisible — 2026-09-01.
        r = sh(["magick", canvas.cur, "-crop", f"{bw}x{bh}+{x}+{y}",
                "+repage", "-colorspace", "gray",
                "-format", "%[fx:mean]", "info:"]).stdout.strip()
        try:
            m = float(r)
            against = "#%02X%02X%02X" % ((int(m * 255),) * 3)
        except ValueError:
            against = "#808080"
    if True:
        c = contrast(color, against)
        if c < 2.0:
            notes.append(f"{e['element']}: {color} on {against} — contrast "
                         f"{c:.1f}:1, this copy is invisible")
        elif c < 4.5:
            notes.append(f"{e['element']}: {color} on {against} — contrast "
                         f"{c:.1f}:1, below the readable floor of 4.5:1")
    # Declared bounds are a request; the drawn box is the fact. Copy sized
    # up to its cap height overruns the measure it was given, so checking
    # the declared rectangles passed an offer row whose three items sat on
    # top of each other — 2026-08-31.
    for pe, px0, py0, px1, py1 in drawn:
        if pe.startswith(e["element"]):
            continue          # a zone sitting on its own panel is the point
        if x < px1 and x + bw > px0 and y < py1 and y + bh > py0:
            notes.append(f"{e['element']} overlaps {pe} where they are "
                         f"actually drawn — one of them is unreadable")
    drawn.append((e["element"], x, y, x + bw, y + bh))

    if band and not e.get("box"):
        by0, by1 = band
        if y < by1 and y + bh > by0:
            r = sh(["magick", canvas.cur, "-crop",
                    f"{bw}x{bh}+{x}+{y}", "+repage", "-colorspace", "gray",
                    "-format", "%[fx:standard_deviation]", "info:"]).stdout
            try:
                if float(r.strip()) > 0.11:
                    notes.append(
                        f"{e['element']}: sits on the picture where it is "
                        f"busy — this copy cannot be read. It needs a panel "
                        f"behind it, or the picture needs to clear it.")
            except ValueError:
                pass

    sh(["magick", canvas.cur, blk, "-gravity", "northwest",
        "-geometry", f"+{x}+{y}", "-composite", canvas.nxt])
    canvas.step()
    return y + bh


def zone_is_clear(plate, t, l, b, r, notes, designed=False):
    """Is the rectangle the product needs actually empty on the plate?

    The plate prompt asks for it, and the model often ignores it. Nothing
    checked, so a tube was composited on top of a forearm that had spread
    into its zone. The check is cheap: a clear studio zone has low variance;
    a limb crossing it does not."""
    x, y = int(W * l / 100), int(H * t / 100)
    w, h = int(W * (r - l) / 100), int(H * (b - t) / 100)
    out = sh(["magick", str(plate), "-resize", f"{W}x{H}^", "-gravity", "center",
              "-extent", f"{W}x{H}", "-crop", f"{w}x{h}+{x}+{y}", "+repage",
              "-colorspace", "gray", "-format", "%[fx:standard_deviation]",
              "info:"]).stdout.strip()
    try:
        sd = float(out)
    except ValueError:
        return
    if designed:
        # The template put the product here on purpose, straddling the band
        # edge onto ground we paint ourselves. Nothing to check.
        return
    if sd > 0.09:
        notes.append(f"product zone {t}-{b}% x {l}-{r}% is not clear on the "
                     f"plate (variance {sd:.3f}) — the picture put content "
                     f"where the product goes")


def picture_plan(d):
    """Is the photograph the whole frame, or a band sitting on a ground?

    Measured cause, 2026-08-31 — from looking at the swipes themselves.
    Both <competitor> formats are white-ground designs: type on white, a
    contained picture band in the middle, a colour block or fine print
    below. The renderer was laying type over a full-bleed photograph, which
    is a different kind of ad entirely, and no amount of correct zone data
    fixes it.

    Derived, not measured: the format's own keep-clear rectangles say where
    the picture lives. When they occupy less than 60% of the height, the
    picture is a band. **Stage 2 should be recording the ground colour and
    the picture treatment outright** — deriving it here is a stand-in for a
    measurement that ought to exist."""
    pic = (d.get("layout", {}) or {}).get("picture")
    if isinstance(pic, dict) and pic.get("treatment"):
        if pic["treatment"] == "full_bleed":
            return None
        return (pic.get("top_pct", 32), pic.get("bottom_pct", 60))

    kc = [k for k in (d.get("layout", {}).get("keep_clear") or [])
          if not re.search(r"ui|safe", k.get("name", ""), re.I)]
    if not kc:
        return None
    top = min(k["top"] for k in kc)
    bot = max(k["bottom"] for k in kc)
    return None if bot - top >= 60 else (top, bot)


def product_slot(layout):
    """Where the product goes, in data.

    A template's own `layout.product` wins: a hand-tuned format puts the
    product where WE own the background — straddling the band edge onto the
    offer panel — rather than asking the generator to leave a hole in the
    photograph. Measured 2026-09-02: six good plates in a row were rejected
    because the model would not keep the right third of the frame empty, and
    the design, not the model, was the thing at fault. Never ask the picture
    to leave a hole for something we composite ourselves."""
    pr = layout.get("product") or (layout.get("layout", {}) or {}).get("product")
    if pr:
        return (pr["top"], pr["left"], pr["bottom"], pr["right"])
    for c in (layout.get("composited") or []):
        if (c.get("kind") or "") in {"product", "packshot"}:
            return (c["top_pct"], c["left_pct"],
                    c["top_pct"] + (c.get("height_pct") or 26),
                    c["left_pct"] + (c.get("span_pct") or 30))
    for k in (layout.get("layout", {}).get("keep_clear") or []):
        if re.search(r"product|tube|packshot", k.get("name", ""), re.I):
            return (k["top"], k["left"], k["bottom"], k["right"])
    return None


STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "your",
        "you", "that", "this", "it", "is", "are", "with", "at", "as", "by"}


def swiped_words(brief_path):
    """The words the swiped ad actually used, from the teardown record."""
    td = Path(brief_path).parent / "01-teardown.md"
    if not td.is_file():
        return []
    return [m.strip().lower() for m in
            re.findall(r'["\u201c]([^"\u201d]{12,90})["\u201d]', td.read_text())]


def too_close(ours, theirs):
    """Does our line reuse a run of the swipe's own words?

    Measured cause, 2026-08-31: injection returned "becomes your perfect
    skin" — the swiped ad's headline, word for word. The point of injection
    is that their structure carries our words; a verbatim line means the
    stage did nothing."""
    a = re.findall(r"[a-z']+", ours.lower())
    for t in theirs:
        b = re.findall(r"[a-z']+", t)
        for n in range(len(a), 2, -1):
            for i in range(len(a) - n + 1):
                run = a[i:i + n]
                if all(w in STOP for w in run):
                    continue          # "that becomes your" is not a claim
                if any(b[j:j + n] == run for j in range(len(b) - n + 1)):
                    return " ".join(run)
    return None


def draw_sticker(st, canvas, notes, drawn=None):
    """An angled callout stuck on the cluster — where the offer actually
    lives in a lot of these formats, and previously not drawn at all."""
    text = (st.get("text") or "").upper()
    if not text:
        return
    w = int(W * num(st.get("span_pct"), 26) / 100)
    pt = max(14, int(w / max(len(text), 1) * 1.55))
    font = str(SUP / "Arial Bold.ttf")
    lab, tw, th = block(text, font, pt, 0, st.get("text_color", "#FFFFFF"),
                        out=f"{TMP}-stk.png")
    padx, pady = int(pt * 0.55), int(pt * 0.40)
    sh(["magick", "-size", f"{tw+2*padx}x{th+2*pady}",
        f"xc:{st.get('color', '#111111')}",
        "(", lab, ")", "-gravity", "center", "-composite",
        "-background", "none", "-rotate", str(num(st.get("rotate_deg"), 0)),
        f"{TMP}-stk2.png"])
    # Stickers are drawn furniture and collide like anything else. Leaving
    # them out of the tracking let an adaptive headline land on one.
    if drawn is not None:
        sx = int(W * num(st.get("left_pct"), 10) / 100)
        sy = int(H * num(st.get("top_pct"), 50) / 100)
        drawn.append((f"sticker {text[:14]}", sx, sy,
                      sx + tw + 2 * padx, sy + th + 2 * pady))
    sh(["magick", canvas.cur, f"{TMP}-stk2.png", "-gravity", "northwest",
        "-geometry", f"+{int(W*num(st.get('left_pct'),10)/100)}"
                     f"+{int(H*num(st.get('top_pct'),50)/100)}",
        "-composite", canvas.nxt])
    canvas.step()


def draw_mark(mk, canvas, notes):
    """A non-text graphic the format carries — an icon or a symbol."""
    kind = (mk.get("kind") or "").lower()
    span = int(W * num(mk.get("span_pct"), 12) / 100)
    x, y = (int(W * num(mk.get("left_pct"), 8) / 100),
            int(H * num(mk.get("top_pct"), 8) / 100))
    c = mk.get("color", "#111111")
    if "triangle" in kind or "warning" in kind or "alert" in kind:
        r = int(span * 0.16)
        sh(["magick", "-size", f"{span}x{span}", "xc:none", "-fill", c,
            "-draw", f"polygon {span//2},{r} {span-r},{span-r} {r},{span-r}",
            "-fill", "white", "-stroke", "none",
            "-draw", f"rectangle {span//2-span//22},{int(span*.36)} "
                     f"{span//2+span//22},{int(span*.66)}",
            "-draw", f"circle {span//2},{int(span*.76)} "
                     f"{span//2+span//22},{int(span*.76)}", f"{TMP}-mk.png"])
    else:
        notes.append(f"mark '{kind}' has no drawing for it — not rendered")
        return
    sh(["magick", canvas.cur, f"{TMP}-mk.png", "-gravity", "northwest",
        "-geometry", f"+{x}+{y}", "-composite", canvas.nxt])
    canvas.step()


TEMPLATES = P.TEMPLATES


def load(brief):
    """The geometry comes from a hand-tuned template; the words come from the
    brief. Nothing else.

    **Ruled 2026-09-01.** Letting the model emit coordinates, panel colours
    and padding meant every run invented a new layout and every run broke in
    a new way — a missing ground, a missing band, a missing panel, then a
    black panel on every zone. None of those were content problems. The
    formats repeat; the words do not. So the template owns position, colour,
    size, measure and spacing, and the brief fills slots with copy.

    A brief that still carries its own geometry is read the old way, so
    nothing already written stops working."""
    d = json.loads(re.search(r"```json\s*(\{.*?\})\s*```",
                             Path(brief).read_text(), re.S).group(1))
    name = d.get("template")
    if not name:
        return d, None
    f = TEMPLATES / f"{name}.json"
    if not f.is_file():
        raise SystemExit(f"brief names template '{name}', which does not exist")
    t = json.loads(f.read_text())
    content = d.get("content") or {}
    out = {"layout": t["layout"], "elements": []}
    for e in t["elements"]:
        if e.get("kind"):
            out["elements"].append(dict(e))   # furniture: no copy to fill
            continue
        text = content.get(e.get("slot", ""))
        if not text:
            continue          # an empty slot is drawn as nothing, not as a box
        out["elements"].append({**e, "text": text})
    # Marks and stickers are the template's furniture. The template fixes
    # where they sit, their colour and their angle; the brief supplies only
    # the words that go on a sticker.
    if t.get("fixed_marks"):
        out["layout"]["marks"] = t["fixed_marks"]
    stk = []
    for st in (t.get("fixed_stickers") or []):
        text = content.get(st.get("slot", ""))
        if text:
            stk.append({**st, "text": text})
    if stk:
        out["layout"]["stickers"] = stk
    return out, name


def render(brief, plate, out, product=None, variant="", mode="all", brand=None):
    """mode: 'all' the finished ad · 'picture' ground+band+product only,
    the draft that goes out for polish · 'over' panels and type laid onto an
    already-finished picture, which is never re-banded.

    `brand` — the folder under brands/. Left out, it is the brand teardown
    recorded for this brief's run; if neither names one, the render stops."""
    use_brand(brand_for_brief(brief, brand))
    d, tpl = load(brief)
    lay, els, notes = d.get("layout", {}), d.get("elements", []), []
    if tpl:
        _t = json.loads((TEMPLATES / f"{tpl}.json").read_text())
        have = {x.get("slot") for x in els} | {
            x.get("slot") for x in (lay.get("stickers") or [])}
        missing = [e["slot"] for e in
                   _t["elements"] + (_t.get("fixed_stickers") or [])
                   if e.get("slot") and e["slot"] not in have]
        if missing:
            notes.append(f"template '{tpl}': no copy for {', '.join(missing)} "
                         f"— those slots are empty in the finished ad")

    canvas = Canvas(str(TMP))
    plan = None if mode == "over" else picture_plan(d)
    if mode == "over":
        sh(["magick", str(plate), "-resize", f"{W}x{H}!", canvas.cur])
    elif plan:
        # How much of the plate survives the band? A picture generated in the
        # wrong shape loses most of its frame here, and the crop takes the
        # composition with it.
        pw, ph = sh(["magick", "identify", "-format", "%w %h",
                     str(plate)]).stdout.split()
        want = W / (H * (plan[1] - plan[0]) / 100)
        got = int(pw) / int(ph)
        if got and (max(want, got) / min(want, got)) > 1.6:
            notes.append(
                f"the plate is {got:.2f}:1 but this band is {want:.2f}:1 — "
                f"most of the picture is cropped away. Generate it at the "
                f"band's shape.")
        t, b = plan
        by, bh = int(H * t / 100), int(H * (b - t) / 100)
        ground = (d.get("layout", {}).get("ground") or "#FFFFFF")
        if not d.get("layout", {}).get("ground"):
            notes.append("ground colour not in the format data — drew white")
        sh(["magick", "-size", f"{W}x{H}", f"xc:{ground}",
            "(", str(plate), "-resize", f"{W}x{bh}^", "-gravity", "center",
            "-extent", f"{W}x{bh}", ")",
            "-gravity", "northwest", "-geometry", f"+0+{by}", "-composite",
            canvas.cur])
    else:
        sh(["magick", str(plate), "-resize", f"{W}x{H}^", "-gravity", "center",
            "-extent", f"{W}x{H}", canvas.cur])

    slot = product_slot(d)
    if mode == "picture":
        # The draft goes out WITHOUT the product. The finishing pass re-draws
        # whatever it is given, and a re-drawn tube is a tube whose label has
        # turned to mush — measured 2026-08-31, "BRILLIANCE BODY SCRUB" came
        # back as smeared shapes. The scene is polished; the real product is
        # composited onto it afterwards, untouched.
        product = None
    # When a template declares where the product goes, that is a design
    # decision made against this exact format — not a guess to be second-
    # guessed by a variance check. The clearance test exists to catch
    # model-authored layouts putting the product on top of a limb.

    if mode == "picture":
        # The draft that goes out for polish: ground, band, product. No
        # panels, no type — a model asked to preserve type re-draws it, and
        # re-drawn type is broken type.
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        sh(["magick", canvas.cur, str(out)])
        for f in (canvas.a, canvas.b):
            Path(f).unlink(missing_ok=True)
        print(f"  {Path(out).name}  scene draft, no product "
              f"({'band' if plan else 'full'})")
        return notes

    # ADAPTIVE LAYOUT. A template can say "put this band of type wherever
    # this picture is quiet" instead of naming a percentage. The percentages
    # stay as the fallback, so a template still reads as a design — but on a
    # plate where the quiet is somewhere else, the type follows it.
    #
    # This is what stops a headline landing on a rock. Nothing was looking
    # at the picture before: the type was placed blind and the picture was
    # generated blind.
    adapt = (d.get("layout") or {}).get("adaptive")
    if adapt and plate and mode != "picture":
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from read_plate import read
            r = read(plate)
            safe = (d.get("layout") or {}).get("safe") or {}
            st = num(safe.get("top_pct"), 0)
            sb = num(safe.get("bottom_pct"), 100)
            # the quietest band that fits inside the safe zone
            # It is the TYPE BLOCK that must sit inside the safe zone, not
            # the band. A quiet band running 5-25% can still host a block at
            # 15-24%. Requiring the whole band inside rejected almost every
            # band, because the quietest part of a picture is usually its
            # empty top edge.
            band = None
            for b in r["quiet_bands"]:
                lo, hi = max(b["top_pct"], st), min(b["bottom_pct"], sb)
                if hi - lo >= 12:
                    band = dict(b, top_pct=lo, bottom_pct=hi)
                    break
            if band is None:
                notes.append("no quiet band overlaps the safe zone by enough "
                             "to set type in — used the fixed positions")
            if band:
                names = adapt if isinstance(adapt, list) else [adapt]
                movers = [e for e in els if e.get("slot") in names
                          or e.get("element") in names]
                if movers:
                    span = band["bottom_pct"] - band["top_pct"]
                    # cap height is not line height: a 4% cap with 3 lines
                    # and normal leading occupies about 4 x 3 x 1.55.
                    used = sum(num(e.get("cap_pct"), 2) *
                               (num(e.get("max_lines"), 1) or 1) * 1.55
                               for e in movers)
                    if used > span:
                        notes.append(
                            f"the quiet band is {span:.0f}% tall and this "
                            f"copy needs {used:.0f}% — left it at the "
                            f"template's positions rather than stacking it "
                            f"on itself")
                        movers = []
                    if movers:
                        y = band["top_pct"] + max(0, (span - used)) / 2
                        y = max(y, st)                   # never above the crop
                        if y + used > sb:                # nor below it
                            y = max(st, sb - used)
                        for e in movers:
                            e["top_pct"] = round(y, 1)
                            y += num(e.get("cap_pct"), 2) * \
                                 (num(e.get("max_lines"), 1) or 1) * 1.55
                        notes.append(
                            f"laid {', '.join(names)} into the quietest band "
                            f"({band['top_pct']}-{band['bottom_pct']}%, "
                            f"detail {band['detail']})")
        except Exception as exc:
            notes.append(f"could not read the plate ({exc}) — used the "
                         f"template's fixed positions")

    allowed = brand_colors(brand_dir())
    theirs = swiped_words(brief)
    for e in els:
        t = e.get("text") or (e.get("variants") or [{}])[0].get("text") or ""
        hit = too_close(t, theirs) if t else None
        if hit:
            notes.append(f"{e['element']}: \"{hit}\" is the swiped ad's own "
                         f"wording, carried through verbatim — injection did "
                         f"not replace it")
    # Zones that sit beside each other are not colliding. An offer block is
    # typically one row of two or three items sharing a top edge; comparing
    # only their vertical extents called every one of them a collision.
    for blk in (d.get("layout", {}).get("blocks") or []):
        sh(["magick", canvas.cur, "-fill", blk.get("color", "#000000"),
            "-draw", "rectangle "
            f"{int(W*num(blk.get("left_pct"), 0)/100)},"
            f"{int(H*num(blk.get("top_pct"), 0)/100)} "
            f"{int(W*num(blk.get("right_pct"), 100)/100)},"
            f"{int(H*num(blk.get("bottom_pct"), 100)/100)}", canvas.nxt])
        canvas.step()

    # The product goes on AFTER the panels. Composited first, the offer
    # panel painted straight over its lower half and the tube shipped
    # looking cut in two — 2026-09-02.
    designed = bool((d.get("layout") or {}).get("product"))

    # A product that stands ON something has to be measured against that
    # thing, not placed at a percentage. The pedestal is a different height
    # and width in every generated plate; a fixed slot floats the product in
    # front of it — shipped that way on 2026-09-02.
    stand = (d.get("layout") or {}).get("product_stands_on")
    if stand == "pedestal" and slot and plate and product:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from find_pedestal import pedestal_top
            r = pedestal_top(plate)
        except Exception as exc:
            r = None
            notes.append(f"pedestal measurement failed ({exc}) — the product "
                         f"was placed at its template position")
        if r:
            # Stand it: the product's BASE sits on the measured top, its width
            # is a share of that top, and its height follows the product's own
            # aspect. Anchoring the box's top instead left the tube floating
            # above the plinth — 2026-09-02.
            pw, ph = sh(["magick", "identify", "-format", "%w %h",
                         str(product)]).stdout.split()
            aspect = int(pw) / int(ph)
            top_w = r["right_pct"] - r["left_pct"]
            w_pct = top_w * num(
                (d.get("layout") or {}).get("product_width_of_top"), 0.52)
            # w_pct is a percentage, not a fraction — treating it as one
            # made the product 2293% of the frame tall.
            h_pct = ((w_pct / 100 * W) / aspect) / H * 100
            cx = (r["left_pct"] + r["right_pct"]) / 2
            base = r["top_pct"] + 0.6          # a hair into the surface
            slot = (base - h_pct, cx - w_pct / 2, base, cx + w_pct / 2)
            notes_ped = r["top_pct"]
        elif r is None and "pedestal measurement failed" not in "".join(notes):
            notes.append("could not find the pedestal on this plate — the "
                         "product was placed at its template position")

    if product and slot:
        t, l, b, r = slot
        zone_is_clear(plate, t, l, b, r, notes, designed)
        ph, pw = int(H * (b - t) / 100), int(W * (r - l) / 100)
        # Fit the box, not just its height. Sizing to height alone pushed a
        # tube past the frame edge and shipped it clipped.
        sh(["magick", canvas.cur,
            "(", str(product), "-resize", f"{pw}x{ph}",
            "(", "+clone", "-background", "black", "-shadow", "55x18+0+12", ")",
            "+swap", "-background", "none", "-layers", "merge", "+repage", ")",
            "-gravity", "northwest",
            "-geometry", f"+{int(W*l/100)}+{int(H*t/100)}", "-composite", canvas.nxt])
        canvas.step()

    # One list for the whole page. It used to be reset after the stickers
    # were drawn, which threw their rectangles away and let type land on
    # them unnoticed.
    drawn = []
    for st in (d.get("layout", {}).get("stickers") or []):
        draw_sticker(st, canvas, notes, drawn)
    for mk in (d.get("layout", {}).get("marks") or []):
        draw_mark(mk, canvas, notes)

    y, prev = 0, None
    for e in els:
        kind = e.get("kind")
        if kind == "logo":
            draw_logo(e, canvas, notes, drawn); continue
        if kind == "frame":
            draw_frame(e, canvas, notes, plate,
                       (d.get("layout") or {}).get("safe"), drawn); continue
        top = num(e.get("top_pct"), None)
        if top is not None and prev and int(H * top / 100) < prev[0]:
            a_l, a_r = e.get("left_pct", 0), e.get("right_pct", 100)
            if not (a_r <= prev[1] or a_l >= prev[2]):
                notes.append(f"{e['element']}: starts at {top}% but "
                             f"{prev[3]} above it ends at "
                             f"{round(100*prev[0]/H,1)}% in the same "
                             f"column — copy collides")
        y = draw_zone(e, canvas, y, notes, allowed, variant,
                       behind(e, d), drawn,
                       (int(H * plan[0] / 100), int(H * plan[1] / 100))
                       if plan else None)
        prev = (y, e.get("left_pct", 0), e.get("right_pct", 100), e["element"])

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sh(["magick", canvas.cur, str(out)])
    safe = (d.get("layout") or {}).get("safe")
    if safe and mode != "picture":
        t = int(H * num(safe.get("top_pct"), 0) / 100)
        b = int(H * num(safe.get("bottom_pct"), 100) / 100)
        for el, x0, y0, x1, y1 in drawn:
            if y0 < t or y1 > b:
                notes.append(
                    f"{el} sits outside the safe zone "
                    f"({round(100*y0/H,1)}-{round(100*y1/H,1)}% against "
                    f"{safe['top_pct']}-{safe['bottom_pct']}%) — it is cut "
                    f"off when the frame is cropped to 4x5")
        if slot:
            st, sl, sb, sr = slot
            if st < num(safe.get("top_pct"), 0) or sb > num(safe.get("bottom_pct"), 100):
                notes.append(f"the product sits outside the safe zone "
                             f"({st}-{sb}%) — it is cut off at 4x5")

    for f in (canvas.a, canvas.b):
        Path(f).unlink(missing_ok=True)
    zones = ", ".join(e["element"] for e in els)
    print(f"  {Path(out).name}  zones: {zones}"
          f"{'  product ' + str(slot) if slot and product else '  (no product zone)'}")
    for n in notes:
        print(f"    ! {n}")
    return notes


if __name__ == "__main__":
    argv, named = list(sys.argv[1:]), None
    for i, x in enumerate(argv):                 # --brand <name> or --brand=<name>
        if x == "--brand" and i + 1 < len(argv):
            named = argv[i + 1]; del argv[i:i + 2]; break
        if x.startswith("--brand="):
            named = x.split("=", 1)[1]; del argv[i]; break
    a = [x for x in argv if not x.startswith("--")]
    mode = next((x[2:] for x in argv if x.startswith("--")), "all")
    render(a[0], a[1], a[2],
           a[3] if len(a) > 3 else None,
           a[4] if len(a) > 4 else "", mode, brand=named)
