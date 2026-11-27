"""The designed-email engine: one email's spec (email.json) + the brand's look in, the email out.

Lifted from the brand_a week of 12 Oct 2026 (runs/email-production/brand_a/week-2026-10-12/design_system.py),
where every email was typed as code. Here an email is DATA, so any brand runs the same line (owner,
2026-10-17: "this process becomes agnostic because we're going to run the same process on brand_b").

    spec = json.load(open("<run>/design/email.json"))
    html = render(spec, look.load(brand, run_dir))         # the email's sections, for the preview
    secs = sections(spec, lk)                               # [(name, html)], read by build.py

The spec (written by the layout step, design2 prompt, checked by a person at step 2):

    {"brand", "label", "date", "kind": "design"|"letter", "theme": null|"<theme>", "concept", "culture",
     "subject", "preview", "link", "segments": [...], "notes": [...],
     "sections": [{"s": "<section>", ...its fields...}, ...]}

A picture field is a dict, one of:
    {"photo": "<ref>", "ratio": 1.0, "focus": [x, y]}            a real photo, cropped
    {"stage": "<ref>"}                                             a real cut-out on the brand's product stage
    {"glow": "<ref>", "fill": 0.72}                                a real cut-out on the brand's glow
    {"band": "<ref>", "y0": 0, "y1": 0.3, "x0": 0, "x1": 1}        one band of a real cut-out (a detail)
    {"proof": "<proof id>", "part": "full", "ratio": "1:1"}       real customer proof, from the proof index
    {"todo": "<what>", "brief": "<the picture brief>"}             a slot still to fill (blocks the build)
each with "alt" and "source": cut | photo | proof | made | make (where it came from, EMAIL-LINE step 3).
<ref> is a look.Look file reference (brand:, drive:, repo:, run:).
"""
import base64
import re
import html
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent))    # designed_email: the one rule for a quote's "verified buyer"
import look as L  # noqa: E402

E = html.escape
SOURCE = {"cut": "Real product, cut out", "photo": "Brand photo we own", "proof": "Real customer proof",
          "made": "Made from a real reference", "make": "To make, after your OK", "type": "Type only", "orn": "Ornament"}
_cache = {}


# ---------- pictures ----------

def _uri(im, q=82):
    b = io.BytesIO()
    im.convert("RGB").save(b, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def _png(im):
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def _rgb(hexs):
    h = hexs.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _crop(im, ratio, focus):
    W, H = im.size
    if W / H > ratio:
        nw = int(H * ratio); x = int((W - nw) * focus[0]); return im.crop((x, 0, x + nw, H))
    nh = int(W / ratio); y = int((H - nh) * focus[1]); return im.crop((0, y, W, y + nh))


def photo(lk, ref, ratio=1.0, w=640, focus=(0.5, 0.5), top=0.0, bottom=0.0):
    key = ("p", lk.brand, ref, ratio, w, tuple(focus), top, bottom)
    if key not in _cache:
        im = ImageOps.exif_transpose(Image.open(lk.path(ref))).convert("RGB")    # phone photos carry their turn in a tag; honour it
        W, H = im.size
        im = im.crop((0, int(H * top), W, int(H * (1 - bottom))))
        _cache[key] = _uri(_crop(im, ratio, focus).resize((w, int(w / ratio)), Image.LANCZOS))
    return _cache[key]


def _cutout(lk, ref):
    pr = Image.open(lk.path(ref)).convert("RGBA")
    return pr.crop(pr.getbbox())


def _glow_ground(lk, w, h, strength=0.42, theme=None):
    t = lk.tokens(theme)
    base, tint = _rgb(t["canvas"]), tuple(int(x) for x in t["glow_rgb"].split(","))
    can = Image.new("RGBA", (w, h), base + (255,))
    g = Image.new("RGBA", (w, h), tint + (0,))
    ImageDraw.Draw(g).ellipse((-w * .2, -h * .2, w * 1.2, h * 1.2), fill=tint + (int(255 * strength * .6),))
    return Image.alpha_composite(can, g.filter(ImageFilter.GaussianBlur(min(w, h) * .2)))


def glow(lk, ref, ratio=1.0, w=640, fill=0.72, cy=0.5, theme=None):
    """A real cut-out floating on the brand's glow, with a soft shadow (it never stands loose)."""
    key = ("g", lk.brand, ref, ratio, w, fill, cy, theme)
    if key not in _cache:
        h = int(w / ratio)
        can = _glow_ground(lk, w, h, theme=theme)
        pr = _cutout(lk, ref)
        s = min(w * fill / pr.width, h * fill / pr.height)
        pr = pr.resize((max(1, int(pr.width * s)), max(1, int(pr.height * s))), Image.LANCZOS)
        x, y = (w - pr.width) // 2, int(h * cy - pr.height / 2)
        sh = Image.new("RGBA", can.size, (0, 0, 0, 0)); a = pr.split()[3].point(lambda v: int(v * 0.55))
        blk = Image.new("RGBA", pr.size, (0, 0, 0, 255)); blk.putalpha(a); sh.paste(blk, (x, y + int(h * .03)), blk)
        can = Image.alpha_composite(can, sh.filter(ImageFilter.GaussianBlur(w * .03)))
        lay = Image.new("RGBA", can.size, (0, 0, 0, 0)); lay.paste(pr, (x, y), pr)
        _cache[key] = _uri(Image.alpha_composite(can, lay))
    return _cache[key]


def stage(lk, ref, w=640, fill=0.46, cy=0.40, theme=None):
    """The real cut-out over the brand's empty product stage (its `stage` ornament); its glow when it has none."""
    st = lk.ornament("stage", theme)
    if not st:
        return glow(lk, ref, 1.0, w, fill * 1.5, cy + .1, theme)
    key = ("st", lk.brand, ref, w, fill, cy, theme)
    if key not in _cache:
        bg = Image.open(lk.path(st)).convert("RGBA")
        bg = bg.crop((0, int(bg.height * .1), bg.width, bg.height)); bg = bg.resize((w, int(w * bg.height / bg.width)), Image.LANCZOS)
        pr = _cutout(lk, ref)
        s = bg.height * fill / pr.height; pr = pr.resize((int(pr.width * s), int(pr.height * s)), Image.LANCZOS)
        x, y = (bg.width - pr.width) // 2, int(bg.height * cy - pr.height / 2)
        gl = Image.new("RGBA", bg.size, (0, 0, 0, 0)); a = pr.split()[3].point(lambda v: int(v * .6))
        sh = Image.new("RGBA", pr.size, (0, 0, 0, 255)); sh.putalpha(a); gl.paste(sh, (x + int(w * .02), y + int(w * .03)), sh)
        bg = Image.alpha_composite(bg, gl.filter(ImageFilter.GaussianBlur(w * .025)))
        lay = Image.new("RGBA", bg.size, (0, 0, 0, 0)); lay.paste(pr, (x, y), pr)
        _cache[key] = _uri(Image.alpha_composite(bg, lay), 84)
    return _cache[key]


def band(lk, ref, y0, y1, w=360, x0=0.0, x1=1.0, theme=None):
    """One band of a real cut-out (y0..y1 of its height) on the glow, filling a square: a detail that shows what it names."""
    key = ("b", lk.brand, ref, y0, y1, w, x0, x1, theme)
    if key not in _cache:
        pr = _cutout(lk, ref)
        b = pr.crop((int(pr.width * x0), int(pr.height * y0), int(pr.width * x1), int(pr.height * y1)))
        s = min(w / b.width, w / b.height) * .96
        b = b.resize((int(b.width * s), int(b.height * s)), Image.LANCZOS)
        can = _glow_ground(lk, w, w, theme=theme)
        can.alpha_composite(b, ((w - b.width) // 2, (w - b.height) // 2))
        _cache[key] = _uri(can)
    return _cache[key]


_proof = None


def proof(lk, item, part="full", ratio="1:1", w=480, focus=0.5, at=0.5):
    """Real proof, cut by the proof index's own extract (components/asset-index/machine/proof.py), cached in the run."""
    global _proof
    key = ("pr", lk.brand, item, part, ratio, w, focus, at)
    if key not in _cache:
        cache = (lk.run_dir or HERE) / "proof"
        cache.mkdir(parents=True, exist_ok=True)
        out = cache / ("%s-%s-%s-%d.jpg" % (item, part, ratio.replace(":", "x"), w))
        if not out.exists():
            if _proof is None:
                import importlib.util
                sp = importlib.util.spec_from_file_location("proof", L.REPO / "components/asset-index/machine/proof.py")
                _proof = importlib.util.module_from_spec(sp); sp.loader.exec_module(_proof)
            _proof.extract(lk.brand, item, part, ratio, w, at, str(out), focus=focus)
        _cache[key] = _uri(Image.open(out), 84)
    return _cache[key]


def orn(lk, name, w, theme=None, opaque=False):
    o = lk.ornament(name, theme)
    if not o:
        return None
    key = ("o", lk.brand, name, w, theme, opaque)
    if key not in _cache:
        im = Image.open(lk.path(o))
        crop = o.get("crop") if isinstance(o, dict) else None
        if crop:
            im = im.crop(tuple(int(c * d) for c, d in zip(crop, (im.width, im.height, im.width, im.height))))
        if not opaque and im.mode == "RGBA":
            im = im.crop(im.split()[3].point(lambda v: 255 if v > 24 else 0).getbbox())
        im = im.resize((w, int(w * im.height / im.width)), Image.LANCZOS)
        _cache[key] = _uri(im, 84) if opaque else _png(im)
    return _cache[key]


def picture(lk, p, theme=None, w=640, rounded=True):
    """A picture field → the figure the section shows."""
    if not p:
        return ""
    src = p.get("source", "photo")
    alt = p.get("alt", "")
    if "todo" in p:
        return ('<figure class="m-todo" style="aspect-ratio:%s"><span class="pk pk-make">%s</span><b>%s</b><p>%s</p></figure>'
                % (E(str(p.get("ratio", "1/1"))), SOURCE["make"], E(p["todo"]), E(p.get("brief", ""))))
    w = p.get("w", w)
    if "photo" in p:
        u = photo(lk, p["photo"], p.get("ratio", 1.0), w, p.get("focus", (.5, .5)), p.get("top", 0), p.get("bottom", 0))
    elif "stage" in p:
        u = stage(lk, p["stage"], w, p.get("fill", .46), p.get("cy", .40), theme)
    elif "glow" in p:
        u = glow(lk, p["glow"], p.get("ratio", 1.0), w, p.get("fill", .72), p.get("cy", .5), theme)
    elif "band" in p:
        u = band(lk, p["band"], p["y0"], p["y1"], w, p.get("x0", 0), p.get("x1", 1), theme)
    elif "proof" in p:
        u = proof(lk, p["proof"], p.get("part", "full"), p.get("ratio", "1:1"), w, p.get("focus", .5), p.get("at", .5))
    else:
        raise ValueError("a picture needs one of photo / stage / glow / band / proof / todo: %r" % p)
    return '<figure class="m-pic%s"><img src="%s" alt="%s"><span class="pk pk-%s">%s</span></figure>' % (
        " r" if rounded and p.get("rounded", True) else "", u, E(alt), src, SOURCE.get(src, src))


# ---------- sections ----------
# Each takes (lk, sec, theme) and returns html. `sec` is the spec's dict. Copy fields may carry <i> for the accent word.

def _t(x):
    """Copy as written, with <i> and <b> kept and everything else escaped."""
    s = E(x or "")
    for tag in ("i", "b", "br", "s"):
        s = s.replace("&lt;%s&gt;" % tag, "<%s>" % tag).replace("&lt;/%s&gt;" % tag, "</%s>" % tag)
    return s


def _logo(lk, cls):
    lg = lk["logo"]
    u = "data:image/svg+xml;base64," + base64.b64encode(lk.path(lg["file"]).read_bytes()).decode() \
        if str(lg["file"]).endswith(".svg") else _png(Image.open(lk.path(lg["file"])))
    h = ' style="height:%dpx"' % lg["height"] if lg.get("height") else ""
    return '<img class="m-logo-img" src="%s" alt="%s"%s>' % (u, E(lg.get("alt", lk.brand)), h)


def s_band(lk, s, th):
    """The slim header: the brand's real logo over its band ornament (or its canvas)."""
    if (s.get("style") or {}).get("gold"):    # this email only: a matte brand-gold bar (flat, soft tone shift, one dark rule under), logo in dark ink
        lg = _logo(lk, "m-logo-img").replace("<img ", '<img style="filter:brightness(0) opacity(.9);height:22px;position:relative;z-index:2" ', 1)
        bg = "linear-gradient(180deg,#CDAF50 0%,#C9A94A 55%,#B8993F 100%)"
        return ('<header class="m-head m-flat" style="background:%s;padding:16px 0 15px;box-shadow:inset 0 -3px 0 #4A3210">%s</header>') % (bg, lg)
    if (s.get("style") or {}).get("modern"):    # this email only: a flat bar, logo left, a small letter-spaced tag right, one hairline under
        ink = s["style"].get("ink")    # this email only: dark letters (logo and tag) on a light bar, so the header stands out from the dark email
        lg = _logo(lk, "m-logo-img").replace("<img ", '<img style="margin:0;height:20px;filter:%s" ' % ("brightness(0)" if ink else "none"), 1)
        tag = ('<span style="font:600 10.5px/1 var(--sans);letter-spacing:.2em;text-transform:uppercase;color:%s">%s</span>' % (
            E(ink or lk.get("tokens", {}).get("orn_mid", "#C9A94A")), E(s["style"].get("tag", "")))) if s["style"].get("tag") else ""
        return ('<header class="m-head m-flat" style="background:%s;padding:20px 24px 19px;display:flex;align-items:center;justify-content:space-between;'
                'border-bottom:%s">%s%s</header>') % (E(s["style"].get("bg", "#0C100F")), "0" if ink else "1px solid rgba(242,246,234,.14)", lg, tag)
    if (s.get("style") or {}).get("bg"):    # this email only: one flat colour instead of the band ornament
        st = ' style="background:%s%s"' % (E(s["style"]["bg"]), ";padding:%s" % E(s["style"]["pad"]) if s["style"].get("pad") else "")
        return '<header class="m-head m-flat"%s>%s</header>' % (st, _logo(lk, "m-logo-img"))
    bg = orn(lk, "band", 1200, th, opaque=True)
    st = ' style="background-image:url(%s)"' % bg if bg else ""
    return '<header class="m-head"%s>%s</header>' % (st, _logo(lk, "m-logo-img"))


def s_mark(lk, s, th):
    """The logo alone, for letters."""
    return '<div class="m-mark">%s</div>' % _logo(lk, "m-logo-img")


def s_versus(lk, s, th):
    """This email only: the headline, then two cards side by side ("what he said" / "what's on his face"), each a skin picture over a caption;
    the real CRUSH tube (the cut-out) stands on the seam between them, whole, on a soft gold glow.
    {"headline", "left"/"right": {"label","line","skin": photo}}"""
    gold = "#C9A94A"
    def src(ph):
        m = re.search(r'src="([^"]+)"', picture(lk, {"photo": ph, "ratio": 1.0, "alt": "", "source": "made"}, th, 700, rounded=False))
        return m.group(1) if m else ""
    cut = Image.open(lk.path("product:crush")).convert("RGBA"); cut.thumbnail((420, 1400))
    b = io.BytesIO(); cut.save(b, "PNG"); tube = "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
    h = int(((s.get("style") or {}).get("tube_h", 190)))
    def card(side, bgc, border, tint):
        x = s[side]
        return ('<div style="background:%s;%sborder-radius:14px;display:flex;flex-direction:column">'
                '<img src="%s" style="width:100%%;display:block;aspect-ratio:.95;object-fit:cover;border-radius:13px 13px 0 0">'
                '<div style="flex:1;padding:14px 14px 16px;min-height:90px"><div style="font:500 10px var(--sans);letter-spacing:.16em;color:%s;margin:0 0 5px">%s</div>'
                '<div style="font:300 20px/1.12 var(--serif)">%s</div></div></div>') % (bgc, border, src(x["skin"]), tint, E(x["label"]), E(x["line"]))
    left = card("left", "linear-gradient(160deg,#2A352F,#1B2320)", "border:1px solid rgba(187,199,158,.25);", "#BBC79E")
    right = card("right", "linear-gradient(160deg,#4A3210,#2B1B07)", "border:1px solid rgba(201,169,74,.55);", gold)
    seam = ('<div style="position:absolute;left:50%%;top:%d%%;transform:translate(-50%%,-50%%);z-index:3;text-align:center">'
            '<div style="position:absolute;left:50%%;top:50%%;transform:translate(-50%%,-50%%);width:%dpx;height:%dpx;background:radial-gradient(ellipse 50%% 50%% at 50%% 50%%,rgba(240,190,80,.5) 0,rgba(0,0,0,0) 100%%)"></div>'
            '<img src="%s" style="position:relative;height:%dpx;width:auto;display:block;filter:drop-shadow(0 8px 14px rgba(0,0,0,.65))"></div>') % (int(((s.get("style") or {}).get("tube_top", 40))), int(h * 1.1), int(h * 1.2), tube, h)
    bgx, logo = "", ""
    if s.get("texture"):    # this email only: one dark stone texture behind the logo AND the hero, so the header and the hero read as one section
        tx = Image.open(lk.path(s["texture"])).convert("RGB"); tx.thumbnail((900, 1300))
        b2 = io.BytesIO(); tx.save(b2, "JPEG", quality=85)
        bgx = ",linear-gradient(180deg,rgba(8,11,10,.2) 0,rgba(8,11,10,0) 55%%,#101614 100%%),url(data:image/jpeg;base64,%s) center top/cover no-repeat #0E1311" % base64.b64encode(b2.getvalue()).decode()
    if s.get("logo"):
        logo = '<div style="padding:0 0 %dpx">%s</div>' % (int((s.get("style") or {}).get("logo_gap", 22)), _logo(lk, "m-logo-img").replace("<img ", '<img style="height:22px;margin:0 auto;display:block" ', 1))
    return ('<section class="m" style="padding:%s 22px %dpx;text-align:center;background:radial-gradient(ellipse 380px 260px at 50%% 0%%,rgba(%s,.30) 0,rgba(0,0,0,0) 100%%)%s">'
            '%s<div style="font:300 34px/1.05 var(--serif);padding:0 8px %dpx">%s</div>'
            '<div style="position:relative;display:grid;grid-template-columns:1fr 1fr;gap:10px;text-align:left">%s%s%s</div>%s</section>') % ("20px" if logo else "26px", int((s.get("style") or {}).get("pad_bottom", 28)), E((s.get("style") or {}).get("top_glow", "150,100,20")), bgx, logo, int((s.get("style") or {}).get("head_gap", 16)), _t(s["headline"]).replace("<i>", '<i style="color:%s">' % E(s["style"]["i_color"])) if (s.get("style") or {}).get("i_color") else _t(s["headline"]), left, right, seam,
            '<span style="position:absolute;left:0;right:0;bottom:0;height:1px;z-index:2;background:%s"></span>' % E(s["style"]["bottom_line"]) if (s.get("style") or {}).get("bottom_line") else "")


def s_hero_type(lk, s, th):
    st = s.get("style") or {}    # this email only: {"plain_eyebrow": no gold lines round the small line above the headline, "pad_bottom": px under the picture}
    sec = ' style="padding-bottom:%dpx"' % int(st["pad_bottom"]) if st.get("pad_bottom") is not None else ""
    return '<section class="m m-herotype"%s><div class="m-eye%s">%s</div><h1>%s</h1>%s</section>' % (
        sec, " m-eye-plain" if st.get("plain_eyebrow") else "", E(s.get("eyebrow", "")), _t(s["headline"]), picture(lk, s.get("picture"), th))


def s_hero_photo(lk, s, th):
    """A headline, a line and a full-width picture. An optional "style" on the section, for THIS email only:
    {"bg": colour behind the section, "ink": text colour, "frame": 1px line round the picture,
    "rounded": true for the same round corners as the email's other pictures}."""
    st = s.get("style") or {}
    if st.get("cover_top"):    # this email only: one tall picture is the whole hero; the eyebrow, headline, line and button sit on its empty top (no overlay on the picture)
        pic = picture(lk, s["picture"], th, 600, rounded=False).replace("<img ", '<img style="width:100%;display:block;border-radius:0" ', 1)
        eye = '<div class="m-eye" style="text-align:center">%s</div>' % E(s["eyebrow"]) if s.get("eyebrow") else ""
        sub = '<p style="margin:0 auto 16px;text-align:center;font-size:14.5px;line-height:1.4;color:var(--ink);opacity:.9;max-width:380px;margin-left:auto;margin-right:auto;text-wrap:balance">%s</p>' % _t(s["sub"]) if s.get("sub") else ""
        btn = '<a class="m-btn">%s</a>' % E(s["cta"]) if s.get("cta") else ""
        return ('<section class="m m-herocover" style="padding:0;position:relative;overflow:hidden">%s'
                '<div style="position:absolute;left:0;right:0;top:%dpx;padding:0 33px;text-align:center">%s'
                '<h1 style="font:300 46px/0.98 var(--serif);margin:0 0 14px;text-align:center;text-wrap:balance">%s</h1>%s%s</div></section>') % (
            pic, int(st.get("text_top", 26)), eye, _t(s["headline"]), sub, btn)
    if st.get("cover"):    # this email only: the picture fills the whole top (logo over it, headline + line + button over its lower part)
        deep = E(st.get("deep", "6,43,20"))
        side = int(st.get("text_side", 36))
        pic = picture(lk, s["picture"], th, 600, rounded=False).replace("<img ", '<img style="width:100%;display:block;border-radius:0" ', 1)
        lg = _logo(lk, "m-logo-img").replace("<img ", '<img style="height:22px;filter:drop-shadow(0 2px 10px rgba(0,0,0,.7))" ', 1)
        btn = '<div style="padding:22px %dpx 0"><a class="m-btn">%s</a></div>' % (side, E(s["cta"])) if s.get("cta") else ""
        sub = '<p style="margin:0;padding:0 %dpx;font-size:16px;line-height:1.45">%s</p>' % (int(st.get("sub_side", 6)), E(s["sub"])) if s.get("sub") else ""
        return ('<section class="m m-herocover" style="padding:0;position:relative;overflow:hidden">%s'
                '<div style="position:absolute;left:0;right:0;top:0;height:22%%;background:linear-gradient(rgba(%s,.85),rgba(%s,0))"></div>'
                '<div style="position:absolute;left:0;right:0;bottom:0;height:%d%%;background:%slinear-gradient(rgba(%s,0),rgba(%s,.9) 45%%,rgb(%s))"></div>'
                '<div style="position:absolute;left:0;right:0;top:20px;text-align:center">%s</div>'
                '<div style="position:absolute;left:0;right:0;bottom:%dpx;text-align:center"><h1 style="font:300 36px/1.05 var(--serif);margin:0 0 12px;padding:0 24px">%s</h1>%s%s</div></section>') % (
            pic, deep, deep, int(st.get("fade_h", 55)), ("radial-gradient(ellipse 380px 190px at 50%% 62%%,%s 0,rgba(0,0,0,0) 100%%)," % E(st["flare"])) if st.get("flare") else "", deep, deep, deep, lg, int(st.get("bottom", 34)), _t(s["headline"]), sub, btn)
    ink = ' style="color:%s"' % E(st["ink"]) if st.get("ink") else ""
    sub = "<p%s>%s</p>" % (ink, E(s["sub"])) if s.get("sub") else ""
    pic = picture(lk, s.get("picture"), th, rounded=bool(st.get("rounded")))
    if st.get("frame"):
        pic = pic.replace("<img ", '<img style="border:1px solid %s" ' % E(st["frame"]), 1)
    box = "".join(x for x in ("background:%s;" % E(st["bg"]) if st.get("bg") else "",
                             "padding:%s;" % E(st["pad"]) if st.get("pad") else "") if x)
    box = ' style="%s"' % box if box else ""
    head = _t(s["headline"])
    nn = st.get("neon")    # {"word", "color", "glow", "glow2"}: that word lit like a neon sign, glow2 the outer haze
    if nn and nn["word"] in head:
        head = head.replace(nn["word"], '<span style="color:%s;text-shadow:0 0 4px %s,0 0 14px %s,0 0 28px %s,0 0 46px %s">%s</span>' % (
            E(nn["color"]), E(nn["glow"]), E(nn["glow"]), E(nn.get("glow2") or nn["glow"]), E(nn.get("glow2") or nn["glow"]), nn["word"]), 1)
    if st.get("pad") and sub:
        sub = sub.replace("<p", '<p style="margin-bottom:0%s"' % (";color:%s" % E(st["ink"]) if st.get("ink") else ""), 1) \
            if "style=" not in sub else sub.replace('style="', 'style="margin-bottom:0;', 1)
    side = int(st.get("text_side", 0))    # this email only: space left and right of the words and the button
    btn = '<div style="padding:20px %dpx 22px"><a class="m-btn">%s</a></div>' % (side or 3, E(s["cta"])) if s.get("cta") else ""    # a button between the line and the picture
    if side:
        ink = (ink[:-1] + ';padding:0 %dpx"' % (side + 40) if ink else ' style="padding:0 %dpx"' % (side + 40))
        sub = sub.replace("<p", '<p style="padding:0 %dpx"' % side, 1) if "style=" not in sub else sub.replace('style="', 'style="padding:0 %dpx;' % side, 1)
    if st.get("text_below"):    # this email only: the picture first, then the headline, the line and the button
        _g = int(st.get("btn_gap", 6))    # btn_gap: the same space above the button (under the line) and below it
        btn = btn.replace("padding:20px", "padding:%dpx" % int(st.get("btn_top", _g - 10)), 1).replace("px 22px\"", "px %dpx\"" % _g, 1)
        h1a = ' style="margin-top:%dpx;padding:0 12px;%s"' % (int(st.get("h1_top", 8)), "" if st.get("h1_wrap") else "white-space:nowrap")    # one line
        sub = sub.replace("padding:0 %dpx" % side, "padding:0 %dpx" % int(st.get("sub_side", side)), 1) if side else sub
        ft = st.get("fade_top")    # {"h": px, "c": "r,g,b"}: the top of the picture melts into the header's colour, no seam under the logo
        if ft:
            pic = ('<div style="position:relative">%s<div style="position:absolute;left:0;right:0;top:0;height:%dpx;'
                   'background:linear-gradient(180deg,rgb(%s),rgba(%s,0))"></div></div>') % (pic, int(ft["h"]), E(ft["c"]), E(ft["c"]))
        return '<section class="m m-herophoto"%s>%s<h1%s>%s</h1>%s%s</section>' % (box, pic, h1a, head, sub, btn)
    if st.get("bgpic"):    # this email only: one tall picture is the whole section's background, from the nav to the bottom; headline, line and button lie on its empty top, no shade
        m = re.search(r'src="([^"]+)"', pic)
        btn = btn.replace("padding:20px", "padding:%dpx" % int(st.get("btn_top", 4)), 1)
        return ('<section class="m m-herophoto" style="padding:24px 22px 0;box-sizing:border-box;aspect-ratio:%s;background:#0C100F url(%s) center %s/100%% auto no-repeat;overflow:hidden">'
                '<h1%s>%s</h1>%s%s</section>') % (E(st.get("aspect", "1/2")), m.group(1) if m else "", ("%dpx" % int(st["bg_top"])) if st.get("bg_top") is not None else "bottom", ink, head, sub, btn)
    return '<section class="m m-herophoto"%s><h1%s>%s</h1>%s%s%s</section>' % (box, ink, head, sub, btn, pic)


def s_hero_blink(lk, s, th):
    """hero_photo whose neon word blinks: this is the lit frame (what the page and Outlook show); the email's
    live build cuts the lit and dim frames into one looping GIF (build.py Live.blink)."""
    return s_hero_photo(lk, s, th)


def s_hero_bg(lk, s, th):
    """The hero with its picture as the background: headline, sub-line and button lie over it, a line of small print
    under the button. Built as one picture in the email (the whole hero is a link; its alt text carries the words).
    style (this email only): {"height", "ink", "button", "button_ink", "shade"}."""
    st = s.get("style") or {}
    fig = picture(lk, s["picture"], th, 600, rounded=False)
    m = re.search(r'src="([^"]+)"', fig)
    src = m.group(1) if m else ""
    h = int(st.get("height", 400))    # the section is drawn 400 wide, then enlarged to the email's 600
    ink = E(st.get("ink", "#FFFFFF"))
    shade = st.get("shade", "rgba(25,17,14,.82)")
    btn = ('<a class="m-btn" style="display:%s;background:%s;color:%s;border-radius:%s;padding:%s;font-weight:600;'
           'font-size:%spx;line-height:1;letter-spacing:.12em;text-transform:uppercase">%s</a>') % (
        "block" if st.get("btn_wide") else "inline-block", E(st.get("button", "#FFFFFF")), E(st.get("button_ink", "#19110E")), E(st.get("btn_radius", "999px")), E(st.get("btn_pad", "13px 30px")), E(st.get("btn_font", "10")), E(s["cta"]))    # btn_wide / btn_radius: this email only, so the drawn button is the live button's twin    # btn_pad / btn_font: this email only, so the drawn button is the same size as the live one
    note = '<p style="margin:9px 0 0;font-size:10.5px;line-height:1.4;color:%s">%s</p>' % (ink, E(s["note"])) if s.get("note") else ""
    base = E(st.get("base", "#2B1F1A")); pos = E(st.get("pos", "center 38%"))    # this email only: the colour behind the picture and where it sits
    head = _t(s["headline"]).replace("<i>", '<i style="color:%s">' % E(st.get("i_ink", "#EBC7AE")))
    eyebrow = ('<div style="font:500 10.5px var(--sans);letter-spacing:.16em;text-transform:uppercase;margin:0 0 10px;color:%s">%s</div>' % (ink, E(s["eyebrow"]))) if s.get("eyebrow") else ""    # this email only
    if st.get("logo"):    # this email only: the brand's logo lies on the picture, top centre (the picture's own wall is the header)
        lg = _logo(lk, "m-logo-img").replace("<img ", '<img style="height:%dpx;display:block;margin:0 auto%s" ' % (int(st.get("logo_h", 20)), ";filter:brightness(0) opacity(.88)" if st.get("logo_dark") else ""), 1)    # logo_dark: this email only, the logo dark on a light picture
        eyebrow = '<div style="padding:0 0 %dpx">%s</div>' % (int(st.get("logo_gap", 26)), lg) + eyebrow
    return ('<section class="m m-herobg" style="padding:0;height:%dpx;position:relative;overflow:hidden;background:%s url(%s) %s/100%% auto no-repeat">'
            '<div style="position:absolute;inset:0;background:linear-gradient(180deg,%s 0%%,rgba(25,17,14,0) %d%%,rgba(25,17,14,0) 66%%,%s 100%%)"></div>'
            '<div style="position:relative;text-align:%s;padding:%dpx %dpx 0;color:%s%s">%s<h1 style="font:300 %dpx/%s var(--serif);margin:0 0 8px;color:%s%s">%s</h1>'
            '<p style="margin:0 %dpx;font-size:%spx;line-height:1.45;color:%s">%s</p></div>'
            '<div style="position:absolute;left:0;right:0;bottom:%dpx;text-align:center;padding:0 %dpx">%s%s</div></section>') % (
        h, base, src, pos, shade, int(st.get("fade", 34)), shade, E(st.get("align", "center")), int(st.get("text_top", 20)), int(st.get("text_pad", 16)), ink, (";text-shadow:%s" % E(st["text_shadow"])) if st.get("text_shadow") else "", eyebrow, int(st.get("h1_px", 34)), "1.02" if st.get("caps") else "1.05", ink, ";text-transform:uppercase;letter-spacing:.015em" if st.get("caps") else "", head, int(st.get("sub_side", 0)), E(str(st.get("sub_px", 15))), ink, E(s.get("sub", "")), int(st.get("btn_bottom", 14)), int(st.get("btn_side", 16)), btn, note)


def s_display(lk, s, th):
    return '<section class="m m-display m-left"><h2>%s</h2></section>' % _t(s["text"])


def _gl(st, html):
    """This email only: style {"gold_line": "#C9A94A"} puts a thin short line of that colour above the section's headline."""
    if not st.get("gold_line"):
        return html
    line = '<div style="width:56px;height:2px;background:%s;margin:0 0 16px"></div>' % E(st["gold_line"])
    return html.replace("<h2", line + "<h2", 1)


def s_headline(lk, s, th):
    """A turn: a headline and one line. An optional "style" for THIS email only: {"bg", "ink", "pad"}."""
    st = s.get("style") or {}
    if s.get("picture") and st.get("overlay"):    # this email only: a wide picture, the headline over its lower half (first sentence big, the rest italic), the line under it
        fade = E(st.get("fade", "12,16,15"))
        a, _, b = s["text"].partition(". ")
        a = a + "." if b else a
        pic = picture(lk, s["picture"], th, 560, rounded=False).replace("<img ", '<img style="width:100%;display:block;border-radius:0;aspect-ratio:1.05;object-fit:cover" ', 1)
        ft = ('<div style="position:absolute;left:0;right:0;top:0;height:%d%%;background:linear-gradient(rgb(%s),rgba(%s,0))"></div>' % (int(st["fade_top"]), fade, fade)).replace("%", "%%") if st.get("fade_top") else ""    # fade_top: this email only, the top of the picture melts into the page too
        return ('<section style="padding:0;margin:0"><div style="position:relative">%s' + ft +
                '<div style="position:absolute;left:0;right:0;bottom:0;height:70%%;background:linear-gradient(rgba(%s,0),rgba(%s,.92) 70%%,rgb(%s))"></div>'
                '<div style="position:absolute;left:0;right:0;bottom:12px;text-align:center;padding:0 22px">'
                '<div style="font:300 32px/1.1 var(--serif)">%s</div><div style="font:italic 300 32px/1.1 var(--serif);color:var(--accent);margin-top:4px">%s</div></div></div>'
                '<p style="font:400 16px/1.5 var(--sans);margin:0;padding:6px 30px 40px;text-align:center">%s</p></section>') % (
            pic, fade, fade, fade, _t(a), _t(b), _t(s["sub"]))
    if st.get("diagram"):    # this email only: the headline, then a gold line drawing of the hair turning back under the skin, then the line
        gold, sage = E(st.get("gold", "#C9A94A")), "var(--accent)"
        a, sep, b = s["text"].partition(" and ")
        b = (sep.strip() + " " + b) if sep else ""
        svg = ('<svg viewBox="0 0 380 170" width="100%%" style="display:block"><defs><linearGradient id="sk" x1="0" y1="0" x2="0" y2="1">'
               '<stop offset="0" stop-color="#2A3A2C"/><stop offset="1" stop-color="#0E1A12"/></linearGradient></defs>'
               '<path d="M0 62 Q85 62 130 62 Q170 28 210 62 Q255 62 380 62 L380 170 L0 170Z" fill="url(#sk)"/>'
               '<path d="M0 62 Q85 62 130 62 Q170 28 210 62 Q255 62 380 62" fill="none" stroke="%s" stroke-width="2"/>'
               '<path d="M120 150 C130 118 150 96 176 92 C204 88 214 66 196 56 C184 50 170 58 176 70" fill="none" stroke="#F2F6EA" stroke-width="3" stroke-linecap="round"/>'
               '<circle cx="176" cy="70" r="4" fill="#E26B5B"/>'
               '<g fill="#BBC79E" opacity=".25"><circle cx="40" cy="110" r="1.6"/><circle cx="70" cy="140" r="1.6"/><circle cx="300" cy="120" r="1.6"/><circle cx="340" cy="150" r="1.6"/><circle cx="260" cy="150" r="1.6"/><circle cx="40" cy="150" r="1.6"/><circle cx="90" cy="100" r="1.6"/></g>'
               '<text x="20" y="40" fill="%s" font-size="11" letter-spacing="2" font-family="sans-serif">THE HAIR TURNED</text><path d="M122 44 L150 70 L168 84" stroke="%s" stroke-width="1" fill="none"/>'
               '<text x="10" y="132" fill="#BBC79E" font-size="11" letter-spacing="2" font-family="sans-serif">WENT BACK IN</text>'
'<text x="228" y="40" fill="%s" font-size="11" letter-spacing="2" font-family="sans-serif">BUMP</text>'
               '<text x="236" y="112" fill="#BBC79E" font-size="11" letter-spacing="2" font-family="sans-serif">STILL GROWING</text>'
               '<path d="M226 44 L205 56" stroke="%s" stroke-width="1"/><path d="M234 108 L200 94" stroke="#BBC79E" stroke-width="1"/></svg>') % (gold, gold, gold, gold, gold)
        return ('<section class="m" style="padding:%spx 26px %spx;text-align:center"><div style="font:300 %dpx/1.08 var(--serif);margin-bottom:6px">%s%s</div>'
                '<div style="margin:%dpx 0 %dpx;background:rgba(0,0,0,.25);border:1px solid rgba(201,169,74,.5);border-radius:14px;padding:14px">%s</div>'
                '<p style="font:400 16px/1.5 var(--sans);margin:0">%s</p></section>') % (
            int(st.get("pad_top", 44)), int(st.get("pad_bottom", 48)), int(st.get("size", 36)), _t(a), '<br><i style="color:var(--accent)">%s</i>' % _t(b) if b else "",
            int(st.get("gap_top", 22)), int(st.get("gap_bottom", 18)), svg, _t(s["sub"]))
    if st.get("date_look"):    # this email only: the date as a premium black wall-calendar page: the month's whole grid faint, the one day lit in a glowing sage disc, binder rings on top, the occasion below
        import calendar as _cal
        a, _, b = re.sub(r"</?i>", "", s["text"]).partition(". ")
        a = a + "." if b else a
        m = re.match(r"\s*(\w+)\s+(\d+)\s+(\w+)", b or "")
        wd, dy, mo = m.groups() if m else ("", "0", b or "")
        dy = int(dy or 0)
        mnum = list(_cal.month_name).index(mo) if mo in list(_cal.month_name) else 11
        yr = int(st.get("year", 2026))
        weeks = _cal.Calendar(firstweekday=6).monthdayscalendar(yr, mnum)
        cell = lambda d: ('<td style="width:14.28%%;height:38px;text-align:center;padding:0">%s</td>' % (
            '<span style="display:inline-block;width:36px;height:36px;line-height:36px;border-radius:50%%;background:#C7CFAD;color:#0A0D0C;font:600 16px/36px var(--sans);'
            'box-shadow:0 0 0 5px rgba(199,207,173,.16),0 0 22px 6px rgba(199,207,173,.55),0 0 54px 14px rgba(199,207,173,.28)">%d</span>' % d if d == dy else
            '<span style="font:400 14px/38px var(--sans);color:rgba(207,212,200,.38)">%s</span>' % (d or "")))
        rows = "".join("<tr>%s</tr>" % "".join(cell(d) for d in w) for w in weeks)
        heads = "".join('<td style="width:14.28%%;text-align:center;font:500 10.5px/1 var(--sans);letter-spacing:.16em;color:rgba(199,207,173,.75);padding:0 0 10px">%s</td>' % x for x in "SMTWTFS")
        ring = ('<span style="position:absolute;top:-9px;%s:62px;width:11px;height:26px;border-radius:6px;background:linear-gradient(90deg,#8E948D,#E9ECE4 45%%,#7A817A);'
                'box-shadow:0 3px 6px rgba(0,0,0,.6)"></span>')
        return ('<section class="m" style="padding:30px 30px 36px"><div style="position:relative;background:linear-gradient(180deg,#0E1311,#070909);'
                'border:1px solid rgba(199,207,173,.34);border-radius:6px;box-shadow:0 18px 40px rgba(0,0,0,.55),0 0 0 6px rgba(199,207,173,.04);text-align:center">%s%s'
                '<div style="padding:34px 22px 0"><div style="font:500 12px/1 var(--sans);letter-spacing:.34em;color:#C7CFAD;text-transform:uppercase">%s &nbsp;%d</div>'
                '<div style="height:1px;margin:16px 10px 20px;background:linear-gradient(90deg,rgba(199,207,173,0),rgba(199,207,173,.55),rgba(199,207,173,0))"></div>'
                '<table style="width:100%%;border-collapse:collapse;table-layout:fixed"><tr>%s</tr>%s</table></div>'
                '<div style="margin:22px 22px 0;height:1px;background:linear-gradient(90deg,rgba(199,207,173,0),rgba(199,207,173,.45),rgba(199,207,173,0))"></div>'
                '<div style="padding:26px 20px 34px"><div style="font:300 50px/1.02 var(--serif);color:#F2F6EA;text-wrap:balance;text-shadow:0 0 14px rgba(199,207,173,.65),0 0 40px rgba(199,207,173,.35)">%s</div>'
                '<p style="font:400 15.5px/1.5 var(--sans);margin:16px 0 0;color:#CFD4C8;text-wrap:balance;text-align:center">%s</p></div></div></section>') % (
            ring % "left", ring % "right", E(mo), yr, heads, rows, E(a), E(s.get("sub", "")))
    ink = ' style="color:%s"' % E(st["ink"]) if st.get("ink") else ""
    box = "".join(x for x in ("background:%s;" % E(st["bg"]) if st.get("bg") else "",
                             "padding:%s;" % E(st["pad"]) if st.get("pad") else "") if x)
    box = ' style="%s"' % box if box else ""
    sp = ' style="%s%s"' % ("color:%s;" % E(st["sub_ink"]) if st.get("sub_ink") else "", "font-size:%dpx;" % int(st["sub_size"]) if st.get("sub_size") else "") if (st.get("sub_ink") or st.get("sub_size")) else ink    # this email only: the line under the headline, smaller and softer
    if st.get("center"):    # this email only: the headline and its line centred (the engine's capitals / noon look would left-align them)
        ink = ' style="text-align:center;%s"' % ("color:%s;" % E(st["ink"]) if st.get("ink") else "")
        sp = ' style="text-align:center;%s"' % ("color:%s;" % E(st["sub_ink"]) if st.get("sub_ink") else "")
    if st.get("gap") is not None:    # this email only: the space under the headline, in px (the line under it then sits closer)
        _g = "margin-bottom:%dpx;" % int(st["gap"])
        ink = (ink[:-1] + ";" + _g + '"') if ink else ' style="%s"' % _g
        _p = "margin-top:0;line-height:1.35;"
        sp = (sp[:-1] + ";" + _p + '"') if sp else ' style="%s"' % _p
    if st.get("h2_px"):    # this email only: the headline's own size in px
        _f = "font-size:%dpx;" % int(st["h2_px"])
        ink = (ink[:-1] + ";" + _f + '"') if ink else ' style="%s"' % _f
    return _gl(st, '<section class="m m-turn"%s><h2%s>%s</h2>%s</section>' % (box, ink, _t(s["text"]), "<p%s>%s</p>" % (sp, _t(s["sub"])) if s.get("sub") else ""))


def s_letter(lk, s, th):
    out = []
    if s.get("greeting"):
        out.append(s_display(lk, {"text": s["greeting"]}, th))
    out.append('<section class="m m-letter">' + "".join("<p>%s</p>" % _t(p) for p in s["paras"]) + "</section>")
    return out


def s_split(lk, s, th):
    """This email only: the words as a big lead line, two side-by-side cards (jaw / cheek) and a small note under them.
    {"lead": text (<i> shows in the sage italic), "cards": [{"label","text"}, {"label","text"}], "note"}"""
    sage, gold = "#BBC79E", "#C9A94A"
    lbl = lambda c, tx: '<div style="font:500 10px var(--sans);letter-spacing:.16em;text-transform:uppercase;color:%s;margin:0 0 8px">%s</div>' % (c, E(tx))
    card = lambda bg, bd, c, x: ('<div style="background:%s;border:1px solid %s;border-radius:14px;padding:16px 15px 18px">%s'
                                 '<div style="font:400 14.5px/1.45 var(--sans)">%s</div></div>') % (bg, bd, lbl(c, x["label"]), _t(x["text"]))
    a, b = s["cards"]
    return ('<section class="m" style="padding:34px 22px 30px;text-align:center">'
            '<div style="font:300 31px/1.12 var(--serif);padding:0 6px 22px">%s</div>'
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;text-align:left">%s%s</div>'
            '<div style="font:400 12.5px/1.5 var(--sans);color:%s;padding:18px 10px 0">%s</div></section>') % (
        _t(s["lead"]).replace("<i>", '<i style="color:%s">' % sage),
        card("linear-gradient(160deg,#27312C,#1A211E)", "rgba(187,199,158,.25)", sage, a),
        card("linear-gradient(160deg,#4A3210,#2B1B07)", "rgba(201,169,74,.55)", gold, b), E((s.get("style") or {}).get("note_ink", "#CABBAC")), E(s["note"]))


def s_quote(lk, s, th):
    st = s.get("style") or {}    # this email only: {"bg": the card's own background (a colour, or lights over a colour)}
    if st.get("texture"):    # this email only: the card sits on the dark green stone texture
        tx = Image.open(lk.path(st["texture"])).convert("RGB"); tx.thumbnail((800, 600))
        b2 = io.BytesIO(); tx.save(b2, "JPEG", quality=80)
        st = dict(st, bg="url(data:image/jpeg;base64,%s) center/cover no-repeat #0E1311" % base64.b64encode(b2.getvalue()).decode())
    bg = ' style="background:%s"' % E(st["bg"]) if st.get("bg") else ""
    qi = ' style="color:%s"' % E(st["ink"]) if st.get("ink") else ""    # this email only: the words in this colour (for a pale card), the name in "cite_ink"
    ci = ' style="color:%s"' % E(st.get("cite_ink") or st["ink"]) if st.get("ink") else ""
    sp = ' style="padding:%s"' % E(st["pad"]) if st.get("pad") else ""    # this email only: the gap round the card, and the card's own top and bottom room
    if st.get("card_pad"):
        bg = bg[:-1] + ";padding:%s\"" % E(st["card_pad"]) if bg else ' style="padding:%s"' % E(st["card_pad"])
    lf = ";text-align:left" if st.get("left") else ""    # left: this email only, the eyebrow, words and name all aligned left
    eb = '<div class="m-eye" style="margin-bottom:12px;color:var(--eyebrow)%s">%s</div>' % (lf, E(s["eyebrow"])) if s.get("eyebrow") else ""    # an optional small line above the words
    if lf:
        bg = (bg[:-1] + lf + '"') if bg else ' style="text-align:left"'
        qi = (qi[:-1] + lf + '"') if qi else ' style="text-align:left"'
        ci = (ci[:-1] + lf + '"') if ci else ' style="text-align:left"'
    fr = "" if st.get("no_corners") else " e-frame"    # no_corners: this email only, no gold corner ornaments on the card
    return '<section class="m"%s><div class="m-quote%s"%s>%s<blockquote%s>“%s”</blockquote><cite%s>%s</cite></div></section>' % (sp, fr, bg, eb, qi, E(s["quote"]), ci, E(s["who"]))


def s_bigquote(lk, s, th):
    if s.get("texture"):    # this email only: the quote sits on the same dark stone texture as the top of the email
        tx = Image.open(lk.path(s["texture"])).convert("RGB"); tx.thumbnail((800, 1100))
        b2 = io.BytesIO(); tx.save(b2, "JPEG", quality=85)
        bg = "url(data:image/jpeg;base64,%s) center/cover no-repeat #0E1311" % base64.b64encode(b2.getvalue()).decode()
        return '<section class="m m-bigquote" style="background:%s;padding:%s"><div class="m-eye">%s</div><blockquote>“%s”</blockquote><cite>%s</cite></section>' % (
            bg, E((s.get("style") or {}).get("pad", "34px 22px 32px")), E(s.get("eyebrow", "")), E(s["quote"]), E(s["who"]))
    bst = s.get("style") or {}
    pad = bst.get("pad")    # this email only: room round the quote, e.g. "34px 22px 70px"
    if bst.get("eye_gap") is not None or bst.get("quote_gap") is not None or bst.get("cite_body"):    # this email only: tighter gaps between the lines; the last line in body text (not spaced caps)
        eg, qg = int(bst.get("eye_gap", 14)), int(bst.get("quote_gap", 14))
        qlh = ";line-height:%s" % E(str(bst["quote_lh"])) if bst.get("quote_lh") else ""
        cs = ' style="display:block;font:400 15px/1.5 var(--sans);letter-spacing:0;text-transform:none;color:var(--body,#43362F);max-width:300px;margin:0 auto"' if bst.get("cite_body") else ""
        return ('<section class="m m-bigquote"%s><div class="m-eye" style="margin-bottom:%dpx">%s</div><blockquote style="margin:0 0 %dpx%s">\u201c%s\u201d</blockquote><cite%s>%s</cite></section>' % (
            ' style="padding:%s"' % E(pad) if pad else "", eg, E(s.get("eyebrow", "")), qg, qlh, E(s["quote"]), cs, E(s["who"])))
    return '<section class="m m-bigquote"%s><div class="m-eye">%s</div><blockquote>“%s”</blockquote><cite>%s</cite></section>' % (
        ' style="padding:%s"' % E(pad) if pad else "", E(s.get("eyebrow", "")), E(s["quote"]), E(s["who"]))


def s_specs(lk, s, th):
    st = s.get("style") or {}    # this email only: {"bg": the block's own background (a colour or gradients), "line": the dividers, "ink": the small words}
    if st.get("bg"):
        ln = E(st.get("line", "rgba(242,246,234,.22)"))
        cell = lambda i, a, b: '<div style="background:transparent;%s"><b%s>%s</b><span style="color:%s">%s</span></div>' % (
            "border-left:1px solid %s;" % ln if i else "",
            ' style="background:none;-webkit-background-clip:border-box;background-clip:border-box;color:%s"' % E(st["num"]) if st.get("num") else "", E(a), E(st.get("ink", "#F2F6EA")), E(b))
        return '<section class="m"><div class="m-specs" style="background:%s;gap:0;border:1px solid %s">%s</div></section>' % (
            E(st["bg"]), ln, "".join(cell(i, a, b) for i, (a, b) in enumerate(s["items"])))
    return '<section class="m"><div class="m-specs">' + "".join("<div><b>%s</b><span>%s</span></div>" % (E(a), E(b)) for a, b in s["items"]) + "</div></section>"


def s_answers(lk, s, th):
    """This email only: "Two bumps. Two answers." as two product cards (jaw / cheek), a short gold line, then one wide card for the device behind both.
    {"title", "bridge": small words on the line, "tiles": [{"picture","label","name","line"} x3]}: the first two are the answers, the third the device."""
    sage, gold = "#BBC79E", "#C9A94A"
    a, b, c = s["tiles"]
    def cut(ph):    # a real packshot cut-out standing on a soft gold glow
        im = Image.open(lk.path(ph["glow"])).convert("RGBA"); im.thumbnail((420, 700))
        bt = io.BytesIO(); im.save(bt, "PNG"); return "data:image/png;base64," + base64.b64encode(bt.getvalue()).decode()
    def src(pc):
        if pc.get("glow"):
            return cut(pc)
        m = re.search(r'src="([^"]+)"', picture(lk, pc, th, 700, rounded=False))
        return m.group(1) if m else ""
    lbl = lambda col, tx: '<div style="font:500 10px var(--sans);letter-spacing:.16em;text-transform:uppercase;color:%s;margin:0 0 6px">%s</div>' % (col, E(tx))
    def card(x, bg, bd, col):
        if x["picture"].get("glow"):    # a cut-out standing on a soft glow
            img = ('<div style="height:170px;display:flex;align-items:center;justify-content:center;background:radial-gradient(ellipse 120px 120px at 50%% 55%%,rgba(201,169,74,.28),rgba(0,0,0,0))">'
                   '<img src="%s" style="height:150px;width:auto"></div>') % src(x["picture"])
        else:    # a photo filling the top of the card
            img = '<div style="height:170px"><img src="%s" style="display:block;width:100%%;height:170px;object-fit:cover"></div>' % src(x["picture"])
        return ('<div style="background:%s;border:1px solid %s;border-radius:16px;overflow:hidden;text-align:left">%s'
                '<div style="padding:12px 14px 16px">%s<div style="font:600 17px/1.2 var(--sans);margin:0 0 6px">%s</div><div style="font:400 14px/1.45 var(--sans);color:#F2F6EA">%s</div></div></div>') % (
            bg, bd, img, lbl(col, x["label"]), E(x["name"]), E(x["line"]))
    two = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">%s%s</div>' % (
        card(a, "linear-gradient(160deg,#27312C,#1A211E)", "rgba(187,199,158,.25)", sage),
        card(b, "linear-gradient(160deg,#4A3210,#2B1B07)", "rgba(201,169,74,.55)", gold))
    bridge = ('<div style="display:flex;flex-direction:column;align-items:center"><div style="width:1px;height:22px;background:linear-gradient(rgba(201,169,74,.8),rgba(201,169,74,.2))"></div>'
              '<div style="font:500 10px var(--sans);letter-spacing:.2em;text-transform:uppercase;color:%s;padding:4px 0 6px">%s</div><div style="width:1px;height:14px;background:rgba(201,169,74,.6)"></div></div>') % (gold, E(s["bridge"]))
    dv = s.get("device") or {}    # this email only: the device card's own colours {"bg","border","ink","label"}
    dev = ('<div style="display:flex;gap:14px;align-items:center;background:%s;border:1px solid %s;border-radius:16px;overflow:hidden;text-align:left;color:%s">'
           '<img src="%s" style="width:42%%;display:block"><div style="padding:14px 14px 14px 0">%s<div style="font:600 17px/1.2 var(--sans);margin:0 0 6px">%s</div><div style="font:400 14px/1.45 var(--sans)">%s</div></div></div>') % (
        dv.get("bg", "linear-gradient(160deg,#27312C,#1A211E)"), dv.get("border", "rgba(187,199,158,.25)"), dv.get("ink", "inherit"),
        src(c["picture"]), lbl(dv.get("label", gold), c["label"]), E(c["name"]), E(c["line"]))
    return '<section class="m" style="padding:30px 22px 30px"><div style="font:300 31px/1.1 var(--serif);text-align:center;padding:0 0 18px">%s</div>%s%s%s</section>' % (_t(s["title"]), two, bridge, dev)


def s_steps2(lk, s, th):
    """This email only: a centred headline, two chips joined by an arrow (step one in green-grey glass, step two in bronze), then one small line.
    {"lead" (<i> shows in sage), "chips": [one, two], "note"}"""
    sage, gold = "#BBC79E", "#C9A94A"
    chip = lambda tx, bg, bd, c: ('<div style="flex:1;text-align:center;background:%s;border:1px solid %s;border-radius:14px;padding:14px 8px">'
                                  '<div style="font:500 10px var(--sans);letter-spacing:.18em;text-transform:uppercase;color:%s">%s</div></div>') % (bg, bd, c, E(tx))
    a, b = s["chips"]
    return ('<section class="m" style="padding:%s;text-align:center"><div style="font:300 31px/1.12 var(--serif);padding:0 6px 20px">%s</div>'
            '<div style="display:flex;align-items:center;gap:10px;padding:0 0 20px">%s<div style="color:%s;font:300 22px var(--serif)">\u2192</div>%s</div>'
            '<div style="font:400 15px/1.45 var(--sans)">%s</div></section>') % (
        E((s.get("style") or {}).get("pad", "34px 22px 30px")), _t(s["lead"]).replace("<i>", '<i style="color:%s">' % sage),
        chip(a, "linear-gradient(160deg,#27312C,#1A211E)", "rgba(187,199,158,.3)", sage), gold,
        chip(b, "linear-gradient(160deg,#4A3210,#2B1B07)", "rgba(201,169,74,.55)", gold), E(s["note"]))


def s_count(lk, s, th):
    """This email only: the two products standing on soft gold glows, then a one-line statement and one small line.
    {"title": "Two. That's the count.", "sub", "pics": [a cut-out ref each, two]}"""
    sage = "#BBC79E"
    def cut(ref):
        im = Image.open(lk.path(ref)).convert("RGBA"); im.thumbnail((300, 520))
        bt = io.BytesIO(); im.save(bt, "PNG"); return "data:image/png;base64," + base64.b64encode(bt.getvalue()).decode()
    if s.get("image"):    # this email only: one picture (the lit display case) in place of the two product cut-outs
        if s["image"].get("png"):    # a cut-out with a see-through background, kept as a PNG
            pim = Image.open(lk.path(s["image"]["png"])).convert("RGBA"); pim.thumbnail((700, 700))
            bp = io.BytesIO(); pim.save(bp, "PNG")
            class _M:    # the same shape the picture() match gives
                @staticmethod
                def group(_i): return "data:image/png;base64," + base64.b64encode(bp.getvalue()).decode()
            m = _M
        else:
            m = re.search(r'src="([^"]+)"', picture(lk, s["image"], th, 700, rounded=False))
        a, _, b = s["title"].partition(". ")
        cst = s.get("style") or {}    # this email only: {"bg": the panel's colour, "feather": the picture's edges melt into it}
        bgc = E(cst.get("bg", "")); fe = int(cst.get("feather", 0))
        # the sides and the bottom melt into the colour; the top stays sharp
        veil = ('<div style="position:absolute;left:0;right:0;top:0;bottom:0;background:linear-gradient(90deg,%s,rgba(0,0,0,0) %dpx,rgba(0,0,0,0) calc(100%% - %dpx),%s),'
                'linear-gradient(0deg,%s,rgba(0,0,0,0) %dpx)"></div>') % (bgc, fe, fe, bgc, bgc, fe) if (fe and bgc) else ""
        return ('<section class="m" style="padding:26px 22px 30px;text-align:center%s"><div style="padding:0 0 18px"><div style="position:relative;max-width:340px;margin:0 auto"><img src="%s" alt="%s" style="display:block;width:100%%;border-radius:%s">%s</div></div>'
                '<div style="font:300 31px/1.1 var(--serif)">%s <i style="color:%s">%s</i></div><div style="font:400 15px/1.45 var(--sans);padding-top:12px">%s</div></section>') % (
            ";background:%s" % bgc if bgc else "", m.group(1) if m else "", E(s["image"].get("alt", "")), "0" if fe else "12px", veil, E(a + "."), sage, E(b), E(s["sub"]))
    glow = ('<div style="width:150px;height:190px;display:flex;align-items:center;justify-content:center;'
            'background:radial-gradient(ellipse 68px 86px at 50%% 50%%,rgba(201,169,74,.32),rgba(0,0,0,0))"><img src="%s" style="height:146px;width:auto"></div>')
    a, _, b = s["title"].partition(". ")
    return ('<section class="m" style="padding:30px 22px 30px;text-align:center"><div style="display:flex;justify-content:center;align-items:flex-end;gap:0;padding:0 0 12px">%s%s</div>'
            '<div style="font:300 36px/1.05 var(--serif)">%s <i style="color:%s">%s</i></div><div style="font:400 15px/1.45 var(--sans);padding-top:12px">%s</div></section>') % (
        glow % cut(s["pics"][0]), glow % cut(s["pics"][1]), E(a + "."), sage, E(b), E(s["sub"]))


def s_diamond(lk, s, th):
    """This email only: a thin divider, gold lines fading outward from a small green gem set in gold."""
    gold = "#C9A94A"
    line = lambda d: '<div style="flex:1;height:1px;background:linear-gradient(%s,rgba(201,169,74,0),rgba(201,169,74,.85))"></div>' % d
    gem = ('<div style="width:14px;height:14px;transform:rotate(45deg);background:linear-gradient(135deg,#6FD07A,#1E7A3A 55%%,#0B3D1C);border:1.5px solid %s;box-shadow:0 0 8px rgba(111,208,122,.45)"></div>' % gold)
    dot = '<div style="width:5px;height:5px;transform:rotate(45deg);background:%s"></div>' % gold
    dbg = (s.get("style") or {}).get("bg")    # this email only: the colour the divider sits on
    return '<section class="m" style="padding:%s 36px%s"><div style="display:flex;align-items:center;gap:10px">%s%s%s%s%s</div><span class="vh">a divider</span></section>' % (
        E((s.get("style") or {}).get("pad", "14px")), ";background:%s" % E(dbg) if dbg else "", line("90deg"), dot, gem, dot, line("270deg"))


def s_infographic(lk, s, th):
    """House section (a brand's `house` in its look file): the story as three white cards, each a gold-ringed line icon, a small caps label and the copy's own sentence (sans),
    then one serif closing line. {"title", "rows": [{"icon": "snow|drop|spot", "label", "text"}], "final"}, style {"ink", "gold", "muted", "label",
    "final_size", "pad_top", "pad_bottom"}"""
    ist = s.get("style") or {}
    esp, gold, mut, brn = ist.get("ink", "#422F28"), ist.get("gold", "#B19A6F"), ist.get("muted", "#71625B"), ist.get("label", "#8A7458")
    ICON = {"snow": '<path d="M12 3v18M4.6 7.5l14.8 9M19.4 7.5l-14.8 9M9.5 4.5L12 7l2.5-2.5M9.5 19.5L12 17l2.5 2.5"/>',
            "heat": '<path d="M7 4c-2 3 2 5 0 8s2 5 0 8M12 4c-2 3 2 5 0 8s2 5 0 8M17 4c-2 3 2 5 0 8s2 5 0 8"/>',
            "drop": '<path d="M12 3c4 5 6 8 6 11a6 6 0 0 1-12 0c0-3 2-6 6-11z"/><path d="M9.5 15a2.6 2.6 0 0 0 2.5 2.4"/>',
            "spot": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2.6" fill="%s"/>' % esp}
    def card(x):
        return ('<div style="display:flex;gap:14px;align-items:flex-start;background:#fff;border:1px solid rgba(66,47,40,.14);border-radius:16px;padding:16px;margin-bottom:10px;text-align:left;box-shadow:0 6px 18px rgba(66,47,40,.06)">'
                '<div style="flex:none;width:42px;height:42px;border-radius:50%%;background:#fff;border:1.5px solid %s;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 12px rgba(66,47,40,.10)">'
                '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">%s</svg></div>'
                '<div><div style="font:500 10px var(--sans);letter-spacing:.2em;text-transform:uppercase;color:%s;padding-bottom:5px">%s</div>'
                '<div style="font:400 14.5px/1.5 var(--sans);color:%s">%s</div></div></div>') % (gold, esp, ICON.get(x["icon"], ICON["drop"]), brn, E(x["label"]), mut, E(x["text"]))
    fs = int(ist.get("final_size", 21))
    return ('<section class="m" style="padding:%dpx 22px %dpx"><div style="font:300 28px/1.1 var(--serif);color:%s;text-align:center;padding:0 4px 20px">%s</div>%s'
            '<div style="font:300 %dpx/1.2 var(--serif);color:%s;text-align:center;padding:16px 8px 0">%s</div></section>') % (
        int(ist.get("pad_top", 30)), int(ist.get("pad_bottom", 26)), esp, _t(s["title"]), "".join(card(x) for x in s["rows"]), fs, esp, _t(s["final"]))


def s_flow(lk, s, th):
    """A modern infographic in the brand_b tones (nov-30, 2026-11-17): optional `pair` of two big gold-ringed nodes joined by a + (name, job, icon), then a `steps` rail,
    a gold line running down through ringed icon nodes, each a serif lead and a sans line, then an optional `last` card in deep brown with gold edge.
    {"pair": [{"icon","name","job"}], "steps": [{"icon","lead","text"}], "last": {"icon","lead","text"}}, style {"bg","ink","gold","muted","dark","blush"}"""
    st = s.get("style") or {}
    bg, ink, gold, mut = st.get("bg", "#FBF8F2"), st.get("ink", "#19110E"), st.get("gold", "#B19A6F"), st.get("muted", "#6B5E55")
    dark, blush = st.get("dark", "#3A2820"), st.get("blush", "#F2DDD6")
    IC = {"spot": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2.6" fill="currentColor"/>',
          "calendar": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M8 3v4M16 3v4"/>',
          "repeat": '<path d="M4 12a8 8 0 0 1 14-5.3L20 9"/><path d="M20 4v5h-5"/><path d="M20 12a8 8 0 0 1-14 5.3L4 15"/><path d="M4 20v-5h5"/>',
          "crystal": '<path d="M12 3l7 6-7 12L5 9z"/><path d="M5 9h14M9.5 9L12 3l2.5 6M9.5 9L12 21l2.5-12"/>',
          "root": '<path d="M12 3c3.5 4 5 7 5 10a5 5 0 0 1-10 0c0-3 1.5-6 5-10z"/><path d="M12 11v6"/>',
          "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>',
          "drop": '<path d="M12 3c4 5 6 8 6 11a6 6 0 0 1-12 0c0-3 2-6 6-11z"/>',
          "shield": '<path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z"/><path d="M9 12l2 2 4-4"/>'}
    svg = lambda k, px, col: ('<svg width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">%s</svg>'
                              % (px, px, col, IC.get(k, IC["spot"])))
    out = ""
    pair = s.get("pair") or []
    if pair:
        def node(x):
            return ('<div style="flex:1;text-align:center"><div style="width:84px;height:84px;margin:0 auto;border-radius:50%%;background:%s;border:1.5px solid %s;'
                    'display:flex;align-items:center;justify-content:center;box-shadow:0 8px 20px rgba(58,40,32,.10)">%s</div>'
                    '<div style="font:400 21px/1.15 var(--serif);color:%s;padding:12px 4px 4px">%s</div>'
                    '<div style="font:400 13.5px/1.4 var(--sans);color:%s;padding:0 6px">%s</div></div>') % (blush, gold, svg(x["icon"], 38, ink), ink, E(x["name"]), mut, E(x["job"]))
        plus = ('<div style="flex:none;width:30px;height:30px;margin-top:27px;border-radius:50%%;background:%s;color:#fff;text-align:center;font:400 20px/29px var(--sans)">+</div>' % gold)
        out += '<div style="display:flex;align-items:flex-start;gap:6px;padding:4px 0 6px">%s</div>' % (node(pair[0]) + plus + node(pair[1]))
        out += '<div style="width:1.5px;height:26px;background:%s;margin:10px auto 0"></div>' % gold
    steps = s.get("steps") or []
    if steps:
        rows = ""
        for i, x in enumerate(steps):
            rows += ('<div style="display:flex;gap:14px;align-items:flex-start;position:relative;padding:0 0 %dpx">'
                     '<div style="flex:none;width:52px;height:52px;border-radius:50%%;background:#fff;border:1.5px solid %s;display:flex;align-items:center;justify-content:center;position:relative;box-shadow:0 4px 12px rgba(58,40,32,.10)">%s</div>'
                     '<div style="flex:1;padding-top:%dpx"><div style="font:400 19px/1.2 var(--serif);color:%s">%s</div>%s</div></div>') % (
                18, gold, svg(x["icon"], 24, ink), 6 if x.get("text") else 14, ink, E(x["lead"]),
                '<div style="font:400 14px/1.5 var(--sans);color:%s;padding-top:5px">%s</div>' % (mut, E(x["text"])) if x.get("text") else "")
        out += ('<div style="position:relative;padding-top:6px"><div style="position:absolute;left:25px;top:30px;bottom:%dpx;width:1.5px;background:%s"></div>%s</div>'
                % (40 if s.get("last") else 40, gold, rows))
    last = s.get("last")
    if last:
        out += ('<div style="margin-top:6px;background:%s;border:1.5px solid %s;border-radius:20px;padding:18px 18px;display:flex;gap:14px;align-items:center">'
                '<div style="flex:none;width:52px;height:52px;border-radius:50%%;border:1.5px solid %s;display:flex;align-items:center;justify-content:center">%s</div>'
                '<div><div style="font:400 20px/1.2 var(--serif);color:#FBFAF5">%s</div><div style="font:400 15px/1.4 var(--sans);color:#D2BC8A;padding-top:4px">%s</div></div></div>') % (
            dark, gold, gold, svg(last.get("icon", "shield"), 26, "#D2BC8A"), E(last["lead"]), E(last.get("text", "")))
    return '<section class="m" style="background:%s;padding:%s"><div class="m-bx">%s</div></section>' % (E(bg), E(st.get("pad", "20px 24px 26px")), out)


def s_ritual(lk, s, th):
    """House section (a brand's `house` in its look file): a full-width picture, a serif headline, then the steps stacked, each a picture on the left and its words on the right, all on a deep brown with soft flare lights.
    {"picture", "title", "steps": [{"picture", "eyebrow", "title", "text"}]}, style {"base", "pic_ratio", "title_top", "pad_bottom", "ink", "gold", "soft"}"""
    st = s.get("style") or {}
    base = E(st.get("base", "#3A2820")); cream, gold, soft = E(st.get("ink", "#FBFAF5")), E(st.get("gold", "#D2BC8A")), E(st.get("soft", "#D9CFC0"))
    def src(pc, w):
        m = re.search(r'src="([^"]+)"', picture(lk, pc, th, w, rounded=False))
        return m.group(1) if m else ""
    flares = ("radial-gradient(ellipse 380px 240px at 96%% 14%%,rgba(232,176,112,.42) 0,rgba(0,0,0,0) 100%%),"
              "radial-gradient(ellipse 300px 300px at 0%% 46%%,rgba(196,160,108,.34) 0,rgba(0,0,0,0) 100%%),"
              "radial-gradient(ellipse 340px 220px at 90%% 78%%,rgba(206,128,84,.36) 0,rgba(0,0,0,0) 100%%),"
              "radial-gradient(ellipse 260px 160px at 22%% 100%%,rgba(240,206,150,.22) 0,rgba(0,0,0,0) 100%%),"
              "linear-gradient(160deg,rgba(255,255,255,.05) 0,rgba(0,0,0,0) 38%%,rgba(0,0,0,.20) 100%%),%s") % base
    top = ('<div style="position:relative"><img src="%s" alt="%s" style="display:block;width:100%%;aspect-ratio:%s;object-fit:cover">'
           '<div style="position:absolute;left:0;right:0;bottom:0;height:46%%;background:linear-gradient(rgba(58,40,32,0),%s)"></div></div>') % (
        src(s["picture"], 800), E(s["picture"].get("alt", "")), E(st.get("pic_ratio", "2.1")), base)
    def row(i, x, last):    # a frosted-glass card: the picture on the left, the words on the right
        return ('<div style="display:flex;gap:14px;align-items:center;background:rgba(251,250,245,.13);border:1px solid rgba(251,250,245,.34);border-radius:18px;padding:12px;margin-bottom:12px;'
                'backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);text-align:left;box-shadow:0 8px 24px rgba(0,0,0,.18)">'
                '<img src="%s" alt="%s" style="flex:none;width:25%%;aspect-ratio:1;object-fit:cover;border-radius:12px">'
                '<div><div style="font:500 20px/1.15 var(--serif);color:%s;padding-bottom:6px">%s</div>'
                '<div style="font:400 14px/1.45 var(--sans);color:%s">%s</div></div></div>') % (
            src(x["picture"], 360), E(x["picture"].get("alt", "")), cream, E(x["title"]), soft, E(x["text"]))
    n = len(s["steps"])
    return ('<section class="m" style="padding:0;background:%s">%s<div style="padding:%dpx 22px %dpx"><div style="font:300 27px/1.12 var(--serif);color:%s;text-align:center;padding:0 0 18px">%s</div>%s</div></section>') % (
        flares, top, int(st.get("title_top", 34)), int(st.get("pad_bottom", 14)), cream, _t(s["title"]), "".join(row(i, x, i == n - 1) for i, x in enumerate(s["steps"])))


def s_finale(lk, s, th):
    """House section (a brand's `house` in its look file): the closing set like the dark "ritual" section above it: deep brown with soft flare lights, a cream serif headline, one frosted-glass card (small picture left, the quote right).
    {"title", "sub", "picture", "quote"}, style {"base", "split", "pad_top", "pad_bottom", "ink", "soft"}"""
    st = s.get("style") or {}
    base = E(st.get("base", "#3A2820")); cream, soft = E(st.get("ink", "#FBFAF5")), E(st.get("soft", "#D9CFC0"))
    m = re.search(r'src="([^"]+)"', picture(lk, s["picture"], th, 400, rounded=False))
    flares = ("linear-gradient(180deg,rgba(0,0,0,0) calc(100%% - 70px),%s 100%%),"    # the bottom settles into the flat colour the button row below uses
              "radial-gradient(ellipse 380px 240px at 96%% 8%%,rgba(232,176,112,.40) 0,rgba(0,0,0,0) 100%%),"
              "radial-gradient(ellipse 300px 300px at 0%% 50%%,rgba(196,160,108,.30) 0,rgba(0,0,0,0) 100%%),"
              "linear-gradient(160deg,rgba(255,255,255,.05) 0,rgba(0,0,0,0) 40%%),%s") % (base, base)
    card = ('<div style="display:flex;gap:14px;align-items:center;background:rgba(251,250,245,.13);border:1px solid rgba(251,250,245,.34);border-radius:18px;padding:12px;'
            'backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);text-align:left;box-shadow:0 8px 24px rgba(0,0,0,.18)"><img src="%s" alt="%s" style="flex:none;width:25%%;aspect-ratio:1;object-fit:cover;border-radius:12px">'
            '<div style="font:500 17px/1.3 var(--serif);color:%s">%s</div></div>') % (m.group(1) if m else "", E(s["picture"].get("alt", "")), cream, E(s["quote"]))
    if st.get("split"):    # the picture tall on the left, the headline and its line on the right, the glass quote full width under them
        glass = ('<div style="background:rgba(251,250,245,.13);border:1px solid rgba(251,250,245,.34);border-radius:18px;padding:18px 18px 20px;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);'
                 'font:500 17px/1.3 var(--serif);color:%s;text-align:left;box-shadow:0 8px 24px rgba(0,0,0,.18)">%s</div>') % (cream, E(s["quote"]))
        return ('<section class="m" style="padding:0;background:%s"><div style="padding:%dpx 22px %dpx"><div style="display:flex;gap:16px;align-items:center">'
                '<img src="%s" alt="%s" style="flex:none;width:44%%;aspect-ratio:3/4;object-fit:cover;border-radius:16px;border:1px solid rgba(210,188,138,.55)">'
                '<div><div style="font:300 23px/1.12 var(--serif);color:%s;text-align:left;text-wrap:balance">%s</div>'
                '<div style="font:400 13px/1.5 var(--sans);color:%s;text-align:left;padding-top:10px">%s</div></div></div><div style="height:18px"></div>%s<div style="height:8px"></div></div></section>') % (
            flares, int(st.get("pad_top", 34)), int(st.get("pad_bottom", 4)), m.group(1) if m else "", E(s["picture"].get("alt", "")), cream, _t(s["title"]), soft, E(s["sub"]), glass)
    return ('<section class="m" style="padding:0;background:%s"><div style="padding:%dpx 22px 4px"><div style="font:300 28px/1.12 var(--serif);color:%s;text-align:center;text-wrap:balance">%s</div>'
            '<div style="font:400 14px/1.5 var(--sans);color:%s;text-align:center;padding:12px 8px 22px">%s</div>%s</div></section>') % (
        flares, int(st.get("pad_top", 40)), cream, _t(s["title"]), soft, E(s["sub"]), card)


def s_closing(lk, s, th):
    """House section (a brand's `house` in its look file): the closing as a plain headline in the brand serif and one line under it in sans, no ornament, so the brand's own serif is drawn
    (a live row can only use a stand-in font). {"head", "sub"}, style {"bg", "ink", "soft"}"""
    st = s.get("style") or {}
    return ('<section class="m" style="padding:%dpx 30px 8px;background:%s;text-align:center"><div style="font:300 29px/1.15 var(--serif);color:%s;text-wrap:balance">%s</div>'
            '<div style="font:400 14px/1.5 var(--sans);color:%s;padding-top:12px">%s</div></section>') % (
        int(st.get("pad_top", 40)), E(st.get("bg", "#FBFAF5")), E(st.get("ink", "#422F28")), E(s["head"]), E(st.get("soft", "#71625B")), E(s["sub"]))


def s_hero_top(lk, s, th):
    """House section (a brand's `house` in its look file): the top of the hero as a picture: the headline and the line over the upper part of a photo, fading to one solid colour so a LIVE button row can sit
    directly under the line (a live button keeps its size on a phone; a button drawn into a picture shrinks with it). {"headline", "sub", "picture"}, style {"base", "height", "shade", "pos", "text_top", "accent"}"""
    st = s.get("style") or {}
    m = re.search(r'src="([^"]+)"', picture(lk, s["picture"], th, 600, rounded=False))
    base = st.get("base", "25,17,14"); h = int(st.get("height", 215)); shade = st.get("shade", "rgba(25,17,14,.80)")
    head = _t(s["headline"]).replace("<i>", '<i style="color:%s">' % E(st.get("accent", "#F6DDA0")))
    return ('<section class="m m-herobg" style="padding:0;height:%dpx;position:relative;overflow:hidden;background:rgb(%s) url(%s) center %s/100%% auto no-repeat">'
            '<div style="position:absolute;inset:0;background:linear-gradient(180deg,%s 0%%,%s 38%%,rgb(%s) 100%%)"></div>'
            '<div style="position:relative;text-align:center;padding:%dpx 16px 0;color:#fff"><h1 style="font:300 34px/1.05 var(--serif);margin:0 0 8px;color:#fff">%s</h1>'
            '<p style="margin:0 18px;font-size:15px;line-height:1.45;color:#fff">%s</p></div></section>') % (
        h, base, m.group(1) if m else "", E(st.get("pos", "0px")), shade, shade.replace(".80", ".62"), base, int(st.get("text_top", 24)), head, E(s.get("sub", "")))


def s_hero_hands(lk, s, th):
    """House section (a brand's `house` in its look file): the lower part of the same hero photo, melting up out of the solid colour the live button row above it sits on. {"picture"}, style {"base", "height", "pos"}"""
    st = s.get("style") or {}
    m = re.search(r'src="([^"]+)"', picture(lk, s["picture"], th, 600, rounded=False))
    base = st.get("base", "25,17,14"); h = int(st.get("height", 250))
    return ('<section class="m m-herobg" style="padding:0;height:%dpx;position:relative;overflow:hidden;background:rgb(%s) url(%s) center %s/100%% auto no-repeat">'
            '<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgb(%s) 0%%,rgba(%s,0) 30%%)"></div><span class="vh">%s</span></section>') % (
        h, base, m.group(1) if m else "", E(st.get("pos", "bottom")), base, base, E(s["picture"].get("alt", "")))


def s_notes(lk, s, th):
    """House section (a brand's `house` in its look file): customers' words with no picture: each note on the deep band, the words in the serif, who said it in a
    small line under them. {"title", "sub", "notes": [{"quote", "who"}]}, style {"bg", "ink", "soft", "pad"}"""
    st = s.get("style") or {}
    bg, ink, soft = E(st.get("bg", "#3A2820")), E(st.get("ink", "#FBFAF5")), E(st.get("soft", "#D2BC8A"))
    head = ('<div style="font:300 28px/1.15 var(--serif);color:%s;text-wrap:balance">%s</div>' % (ink, _t(s["title"]))) if s.get("title") else ""
    sub = ('<div style="font:400 14px/1.5 var(--sans);color:%s;padding-top:10px">%s</div>' % (soft, E(s["sub"]))) if s.get("sub") else ""
    note = ('<div style="padding:26px 6px 0"><div style="font:300 22px/1.3 var(--serif);color:%s;text-wrap:balance">\u201c%s\u201d</div>'
            '<div style="font:400 12px/1.5 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:%s;padding-top:10px">%s</div></div>')
    if st.get("cards"):    # this email only: each message in its own white box, the words in the body sans
        card = ('<div style="background:%s;border:1px solid rgba(66,47,40,.14);border-radius:16px;padding:22px 20px 20px;margin:0 0 12px;text-align:left;box-shadow:0 6px 18px rgba(66,47,40,.06)">'
                '<div style="font:400 16px/1.55 var(--sans);color:%s">\u201c%s\u201d</div>'
                '<div style="font:500 10.5px/1.5 var(--sans);letter-spacing:.16em;text-transform:uppercase;color:%s;padding-top:12px">%s</div></div>')
        box = E(st.get("card_bg", "#FFFFFF"))
        return '<section class="m" style="padding:%s;background:%s;text-align:center">%s%s<div style="padding-top:22px">%s</div></section>' % (
            E(st.get("pad", "40px 22px 28px")), bg, head, sub, "".join(card % (box, ink, E(x["quote"]), soft, E(x["who"])) for x in s["notes"]))
    return '<section class="m" style="padding:%s;background:%s;text-align:center">%s%s%s</section>' % (
        E(st.get("pad", "40px 28px 40px")), bg, head, sub, "".join(note % (ink, E(x["quote"]), soft, E(x["who"])) for x in s["notes"]))


def s_on_camera(lk, s, th):
    """House section (a brand's `house` in its look file): real people on camera: one to three pictures side by side, each at its own shape (a still from a clip
    stays as tall as the clip), in a thin gold frame, her first name and her own line from that clip under it.
    {"eyebrow", "title", "people": [{"picture", "name", "line"}]}, style {"bg", "ink", "soft", "frame"}"""
    st = s.get("style") or {}
    bg, ink, soft, frame = E(st.get("bg", "#3A2820")), E(st.get("ink", "#FBFAF5")), E(st.get("soft", "#D2BC8A")), E(st.get("frame", "#D2BC8A"))
    people = s["people"]
    w = {1: 320, 2: 260, 3: 170}.get(len(people), 170)
    def cell(x):
        m = re.search(r'src="([^"]+)"', picture(lk, x["picture"], th, w * 2, rounded=False))
        line = ('<div style="font:300 18px/1.35 var(--serif);color:%s;padding-top:14px;text-wrap:balance">\u201c%s\u201d</div>' % (ink, E(x["line"]))) if x.get("line") else ""
        return ('<td style="width:%d%%;padding:0 7px;vertical-align:top"><div style="border:1px solid %s;padding:5px">'
                '<img src="%s" alt="%s" style="display:block;width:100%%;height:auto%s"></div>%s'
                '%s</td>') % (
            100 // len(people), "transparent" if st.get("round") else frame, m.group(1) if m else "", E(x["picture"].get("alt", x.get("name", ""))), ";border-radius:%dpx" % int(st["round"]) if st.get("round") else "", line,
            ('<div style="font:400 11.5px/1.5 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:%s;padding-top:9px">%s</div>' % (soft, E(x["name"]))) if x.get("name") and not st.get("no_names") else "")    # no_names: this email only, no first name under the picture    # round: this email only, no frame and rounded corners on the picture
    eye = ('<div style="font:400 12px/1.5 var(--sans);letter-spacing:.16em;text-transform:uppercase;color:%s;padding-bottom:8px">%s</div>' % (soft, E(s["eyebrow"]))) if s.get("eyebrow") else ""
    return ('<section class="m" style="padding:%s;background:%s;text-align:center">%s<div style="font:300 26px/1.2 var(--serif);color:%s;padding:0 12px %dpx;text-wrap:balance">%s</div>'
            '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="table-layout:fixed;margin:0 auto;max-width:%dpx"><tr>%s</tr></table></section>') % (
        E(st.get("pad", "44px 16px 46px")), bg, eye, ink, int(st.get("title_gap", 24)), _t(s["title"]), (w + 14) * len(people), "".join(cell(x) for x in people))


def s_stackpics(lk, s, th):
    """This email only (brand_b): the steps stacked, each a picture with a white card riding up over its bottom edge (small label, serif title, the copy's sentence), on one soft background.
    {"title", "cards": [{"picture", "eyebrow", "title", "text"}]}, style {"bg"}"""
    esp, gold, mut, brn = "#422F28", "#B19A6F", "#71625B", "#8A7458"
    bg = E((s.get("style") or {}).get("bg", "#EFD9C8"))
    def card(i, x):
        m = re.search(r'src="([^"]+)"', picture(lk, x["picture"], th, 700, rounded=False))
        return ('<div style="position:relative;margin-bottom:22px"><img src="%s" alt="%s" style="display:block;width:100%%;aspect-ratio:1.25;object-fit:cover;border-radius:16px">'
                '<div style="background:#fff;border-radius:14px;padding:14px 16px 16px;margin:-38px 12px 0;position:relative;text-align:left;box-shadow:0 8px 20px rgba(66,47,40,.12)">'
                '<div style="font:500 9.5px var(--sans);letter-spacing:.18em;text-transform:uppercase;color:%s;padding-bottom:5px">%d \u00b7 %s</div>'
                '<div style="font:500 20px/1.15 var(--serif);color:%s;padding-bottom:5px">%s</div>'
                '<div style="font:400 14.5px/1.45 var(--sans);color:%s">%s</div></div></div>') % (
            m.group(1) if m else "", E(x["picture"].get("alt", "")), brn, i + 1, E(x["eyebrow"]), esp, E(x["title"]), mut, E(x["text"]))
    return ('<section class="m" style="padding:30px 22px 8px;background:%s"><div style="font:300 26px/1.12 var(--serif);color:%s;text-align:center;padding:0 0 20px">%s</div>%s</section>') % (
        bg, esp, _t(s["title"]), "".join(card(i, x) for i, x in enumerate(s["cards"])))


def s_advice(lk, s, th):
    """This email only (brand_b): numbered white cards on one gold line, each with a line icon, a short serif title and the copy's own sentence.
    {"title", "cards": [{"icon": "scrub|press|cream", "title", "text"}]}"""
    esp, gold, mut = "#422F28", "#B19A6F", "#71625B"
    ICON = {"scrub": '<circle cx="12" cy="12" r="7.5"/><path d="M8.5 12.5c1.2-2 2.6-2 3.5 0s2.3 2 3.5 0"/>',
            "press": '<path d="M12 4v10M8 10.5l4 4 4-4M6 19h12"/>',
            "cream": '<rect x="8" y="9" width="8" height="11" rx="2"/><path d="M10 9V6h4v3M10 13.5h4"/>'}
    n = len(s["cards"])
    def card(i, x):
        return ('<div style="position:relative;display:flex;gap:14px;align-items:flex-start;padding:0 0 14px">'
                '<div style="flex:none;width:44px;height:44px;border-radius:50%%;background:#fff;border:1.5px solid %s;color:%s;font:500 20px/41px var(--serif);text-align:center;position:relative;z-index:2">%d</div>'
                '<div style="flex:1;background:#fff;border:1px solid rgba(66,47,40,.14);border-radius:16px;padding:16px 16px 17px;text-align:left;box-shadow:0 6px 18px rgba(66,47,40,.06)">'
                '<div style="display:flex;justify-content:space-between;align-items:center;padding:0 0 8px;border-bottom:1px solid rgba(177,154,111,.45);margin-bottom:10px">'
                '<div><div style="font:500 9.5px var(--sans);letter-spacing:.18em;text-transform:uppercase;color:#8A7458;padding-bottom:4px">%s</div><div style="font:500 20px/1.15 var(--serif);color:%s">%s</div></div>'
                '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="flex:none;margin-left:10px">%s</svg></div>'
                '<div style="font:400 14.5px/1.5 var(--sans);color:%s">%s</div></div></div>') % (
            gold, esp, i + 1, E(x.get("eyebrow", "")), esp, E(x["title"]), gold, ICON.get(x["icon"], ICON["scrub"]), mut, E(x["text"]))
    line = '<div style="position:absolute;left:21px;top:30px;bottom:44px;width:1px;background:linear-gradient(%s,rgba(177,154,111,.2))"></div>' % gold
    return ('<section class="m" style="padding:26px 22px 14px"><div style="font:300 26px/1.12 var(--serif);color:%s;text-align:center;padding:0 0 20px">%s</div>'
            '<div style="position:relative">%s%s</div></section>') % (esp, _t(s["title"]), line, "".join(card(i, x) for i, x in enumerate(s["cards"])))


def s_pquote(lk, s, th):
    """This email only (brand_b): one line as a premium quotation: squared sand card, hairline gold frame, the brand's own corner ornaments, a big gold mark, the line in serif italic."""
    esp, gold = "#422F28", "#B19A6F"
    cu = orn(lk, "corner", 200, th)
    corner = lambda pos, turn: ('<i style="position:absolute;%s;width:46px;height:46px;background:url(%s) no-repeat center/contain%s"></i>' % (pos, cu, ";transform:rotate(180deg)" if turn else "")) if cu else ""
    who = '<div style="font:500 10.5px var(--sans);letter-spacing:.22em;text-transform:uppercase;color:%s;padding-top:18px">%s</div>' % (gold, E(s["who"])) if s.get("who") else ""
    return ('<section class="m" style="padding:30px 22px"><div style="position:relative;text-align:center;background:linear-gradient(180deg,#FBF6EC,#F4EDDA);border:1px solid rgba(177,154,111,.55);border-radius:4px;padding:46px 34px 40px">'
            '<div style="position:absolute;left:8px;right:8px;top:8px;bottom:8px;border:1px solid rgba(177,154,111,.28);border-radius:2px;pointer-events:none"></div>%s%s'
            '<div style="font:300 70px/.6 var(--serif);color:%s;height:34px">\u201c</div>'
            '<div style="font:italic 300 25px/1.32 var(--serif);color:%s;text-wrap:balance">%s</div>'
            '<div style="display:flex;align-items:center;justify-content:center;gap:10px;padding-top:22px"><div style="width:44px;height:1px;background:linear-gradient(90deg,rgba(177,154,111,0),%s)"></div>'
            '<div style="width:7px;height:7px;transform:rotate(45deg);border:1px solid %s"></div><div style="width:44px;height:1px;background:linear-gradient(270deg,rgba(177,154,111,0),%s)"></div></div>%s</div></section>') % (
        corner("left:14px;top:14px", False), corner("right:14px;bottom:14px", True), gold, esp, E(s["quote"]), gold, gold, gold, who)


def s_tiles(lk, s, th):
    st = s.get("style") or {}    # this email only: {"cols": columns in the grid, "bottom_line": 1px line under the section, "title_gap": px under the title}
    t = '<h2%s>%s</h2>' % (' style="margin-bottom:%dpx"' % int(st["title_gap"]) if st.get("title_gap") else "", _t(s["title"])) if s.get("title") else ""
    css = "".join(x for x in ("border-bottom:1px solid %s;" % E(st["bottom_line"]) if st.get("bottom_line") else "",) if x)
    grid = ' style="grid-template-columns:repeat(%d,1fr);gap:12px 10px"' % int(st["cols"]) if st.get("cols") else ""
    ICONS = {    # minimal line icons (this email only: a tile's "icon"); drawn on a 24px grid in the text colour
        "window": '<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M12 3v18M4 12h16"/>',
        "sink": '<path d="M3 12h18v1.5a5.5 5.5 0 0 1-5.5 5.5h-7A5.5 5.5 0 0 1 3 13.5z"/><path d="M12 12V6.5A2.5 2.5 0 0 1 14.5 4H17"/>',
        "railing": '<path d="M3 8h18M3 17h18M6 8v12M12 8v12M18 8v12"/>',
        "lamp": '<path d="M8.5 3h7l3 8h-13z"/><path d="M12 11v8M8 21h8"/>',
    }
    def icon(x):
        g = ICONS.get(x.get("icon"))
        return ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
                'stroke-linejoin="round" style="vertical-align:-3px;margin-right:7px">%s</svg>' % g) if g else ""
    return '<section class="m m-tiles"%s>%s<div class="m-tgrid"%s>%s</div></section>' % (' style="%s"' % css if css else "", t, grid, "".join(
        '<div class="m-tile">%s<b>%s%s</b><span>%s</span></div>' % (picture(lk, x["picture"], th, 360), icon(x), E(x["name"]), E(x.get("line", ""))) for x in s["tiles"]))


def s_routine(lk, s, th):
    """A routine in order: a title, then one card per step (picture on the left, "STEP n", name and line on the right).
    steps: [{"picture": {...}, "tag": "the clearing", "name": "...", "line": "..."}]"""
    gap = (s.get("style") or {}).get("title_gap")    # this email only: the space under the title
    h = '<h2%s>%s</h2>' % (' style="margin-bottom:%s"' % E(gap) if gap else "", _t(s["title"])) if s.get("title") else ""
    rst = s.get("style") or {}    # this email only: {"flip": picture and words swap sides on every other card, "no_steps": no "Step n" line}
    def card(i, x):
        eye = "" if rst.get("no_steps") else '<div class="m-reye">Step %d · %s</div>' % (i + 1, E(x.get("tag", "")))
        if rst.get("tag_only") and x.get("tag"):    # this email only: the small label above the name, without "Step n"
            eye = '<div class="m-reye"%s>%s</div>' % (' style="color:#9A7A2E;font-weight:700"' if x.get("badge") else "", E(x["tag"]))
        words = '<div class="m-rtext">%s<h3>%s</h3><p>%s</p></div>' % (eye, E(x["name"]), E(x.get("line", "")))
        pic = picture(lk, x["picture"], th, 360)
        card_css = ""
        if x.get("badge"):    # this email only: a filled badge on the picture's corner (a free gift), and a gold line round the card
            pic = '<div style="position:relative">%s<span style="position:absolute;left:-12px;top:-12px;width:62px;height:62px;border-radius:50%%;background:linear-gradient(145deg,#F4DFA0,#C9A650);border:2px solid #FFF8E6;box-shadow:0 0 0 1px #C9A650,0 4px 12px rgba(120,90,30,.35);text-align:center;color:#3A2A12;font:800 13px/62px var(--sans);letter-spacing:.12em">%s</span></div>' % (pic, E(x["badge"]))
            card_css = ";background:linear-gradient(135deg,#FFFBF0,#F5E6BE);border:1px solid #D4B66A;box-shadow:inset 0 0 0 4px #FFFBF0,inset 0 0 0 5px #D4B66A,0 10px 26px rgba(177,154,111,.35);--ink:#2E2014;--muted:#5C4A36;color:#5C4A36"
        if rst.get("flip") and i % 2:
            return '<div class="m-rstep" style="grid-template-columns:1fr 44%%%s">%s%s</div>' % (card_css, words, pic)
        return '<div class="m-rstep"%s>%s%s</div>' % (' style="%s"' % card_css.lstrip(";") if card_css else "", pic, words)
    cards = "".join(card(i, x) for i, x in enumerate(s["steps"]))
    if rst.get("columns"):    # this email only: the steps side by side, each a lifted card {"col_bg", "col_line"}: picture, name, line
        col = lambda x: ('<div style="background:%s;border:1px solid %s;border-radius:12px;overflow:hidden;text-align:center">%s'
                         '<div style="padding:10px 8px 14px"><h3 style="font:600 14px/1.2 var(--sans);margin:0 0 6px">%s</h3>'
                         '<p style="font-size:12px;line-height:1.35;margin:0">%s</p></div></div>') % (
            E(rst.get("col_bg", "#0B3A1D")), E(rst.get("col_line", "rgba(190,205,170,.35)")),
            picture(lk, x["picture"], th, 240).replace("<img ", '<img style="border-radius:0;display:block;width:100%" ', 1), E(x["name"]), E(x.get("line", "")))
        cards = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;align-items:stretch">%s</div>' % "".join(col(x) for x in s["steps"])
    if rst.get("steps_row"):    # this email only: the steps equal, side by side, square pictures with a thin gold outline, name and line under each
        gold = E(rst.get("gold", "#C9A94A"))
        col = lambda i, x: ('<div style="text-align:center">'
                            '<div>%s</div>'
                            '<h3 style="font:600 15px/1.2 var(--sans);margin:12px 0 5px">%s</h3><p style="font-size:13px;line-height:1.4;margin:0">%s</p></div>') % (
            picture(lk, x["picture"], th, 240).replace("<img ", '<img style="aspect-ratio:1;object-fit:cover;width:100%%;display:block;border-radius:10px;border:1px solid %s" ' % gold, 1),
            E(x["name"]), E(x.get("line", "")))
        cards = ('<div style="position:relative">'
                 '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">%s</div></div>') % "".join(col(i, x) for i, x in enumerate(s["steps"]))
    if rst.get("white_cards"):    # this email only: three white rounded cards, the picture full across the top, a gold number badge on its corner, name and line under it
        import re as _re
        gold = E(rst.get("gold", "#B19A6F"))
        def wc(x):
            m = _re.match(r"^\s*(\d+)\s+(.*)$", x["name"])
            num, nm = (m.group(1), m.group(2)) if m else ("", x["name"])
            badge = ('<span style="position:absolute;left:8px;top:8px;width:26px;height:26px;border-radius:50%%;background:#FBF8F2;border:1px solid %s;color:#19110E;font:600 12px/24px var(--sans);text-align:center">%s</span>' % (gold, E(num))) if num else ""
            pic = picture(lk, x["picture"], th, 240).replace("<img ", '<img style="aspect-ratio:1;object-fit:cover;width:100%;display:block;border-radius:0" ', 1)
            return ('<div style="background:#FFFFFF;border:1px solid %s;border-radius:14px;overflow:hidden;text-align:left;box-shadow:0 2px 8px rgba(25,17,14,.06)">'
                    '<div style="position:relative">%s%s</div><div style="padding:12px 10px 14px"><h3 style="font:600 15px/1.2 var(--sans);margin:0 0 5px">%s</h3>'
                    '<p style="font-size:12.5px;line-height:1.4;margin:0">%s</p></div></div>') % (gold, pic, badge, E(nm), E(x.get("line", "")))
        cards = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;align-items:stretch">%s</div>' % "".join(wc(x) for x in s["steps"])
    if rst.get("rows"):    # this email only: three rows, a square picture on the left (number badge on its corner), name and the whole line on the right, a gold hairline between rows
        import re as _re
        gold = E(rst.get("gold", "#B19A6F")); pw = int(rst.get("pic_w", 150))
        def rw(i, x):
            m = _re.match(r"^\s*(\d+)\s+(.*)$", x["name"])
            num, nm = (m.group(1), m.group(2)) if m else ("", x["name"])
            badge = ('<span style="position:absolute;left:6px;top:6px;width:26px;height:26px;border-radius:50%%;background:#FBF8F2;border:1px solid %s;color:#19110E;font:600 12px/24px var(--sans);text-align:center">%s</span>' % (gold, E(num))) if num else ""
            pic = picture(lk, x["picture"], th, 300).replace("<img ", '<img style="aspect-ratio:1;object-fit:cover;width:100%%;display:block;border-radius:12px;border:1px solid %s" ' % gold, 1)
            return ('<div style="display:flex;gap:16px;align-items:center;text-align:left;padding:%s;border-top:%s">'
                    '<div style="position:relative;flex:0 0 %dpx;width:%dpx">%s%s</div>'
                    '<div style="flex:1"><h3 style="font:600 17px/1.2 var(--sans);margin:0 0 6px">%s</h3><p style="font-size:14.5px;line-height:1.5;margin:0">%s</p></div></div>') % (
                "16px 0", ("1px solid %s" % gold) if i else "0", pw, pw, pic, badge, E(nm), E(x.get("line", "")))
        cards = '<div>%s</div>' % "".join(rw(i, x) for i, x in enumerate(s["steps"]))
    if rst.get("white_box"):    # this email only: the three steps as rows inside ONE white rounded box with a gold line round it
        import re as _re
        gold = E(rst.get("gold", "#B19A6F")); pw = int(rst.get("pic_w", 132))
        def wb(i, x):
            m = _re.match(r"^\s*(\d+)\s+(.*)$", x["name"])
            num, nm = (m.group(1), m.group(2)) if m else ("", x["name"])
            badge = ('<span style="position:absolute;left:6px;top:6px;width:26px;height:26px;border-radius:50%%;background:#FEFCF8;border:1px solid %s;color:#19110E;font:600 12px/24px var(--sans);text-align:center">%s</span>' % (gold, E(num))) if num else ""
            pic = picture(lk, x["picture"], th, 300).replace("<img ", '<img style="aspect-ratio:1;object-fit:cover;width:100%%;display:block;border-radius:10px" ', 1)
            return ('<div style="display:flex;gap:16px;align-items:center;text-align:left;padding:16px 16px;border-top:%s">'
                    '<div style="position:relative;flex:0 0 %dpx;width:%dpx">%s%s</div>'
                    '<div style="flex:1"><h3 style="font:600 17px/1.2 var(--sans);margin:0 0 6px">%s</h3><p style="font-size:14.5px;line-height:1.5;margin:0">%s</p></div></div>') % (
                ("0.5px solid %s" % gold) if i else "0", pw, pw, pic, badge, E(nm), E(x.get("line", "")))
        cards = '<div style="background:#FFFFFF;border:0.5px solid %s;border-radius:16px;overflow:hidden">%s</div>' % (gold, "".join(wb(i, x) for i, x in enumerate(s["steps"])))
    if rst.get("lead_two"):    # this email only: step 1 big across the top, steps 2 and 3 side by side under it; no cards, a hairline round each picture
        line = E(rst.get("line", "rgba(242,246,234,.22)"))
        def pic(x, ratio, w):
            return picture(lk, x["picture"], th, w).replace("<img ", '<img style="aspect-ratio:%s;object-fit:cover;width:100%%;display:block;border-radius:10px;border:1px solid %s" ' % (ratio, line), 1)
        words = lambda x, big: ('<h3 style="font:600 %dpx/1.2 var(--sans);margin:10px 0 4px">%s</h3><p style="font-size:%dpx;line-height:1.4;margin:0">%s</p>' %
                                (17 if big else 15, E(x["name"]), 15 if big else 13, E(x.get("line", ""))))
        a, b, c2 = s["steps"][:3]
        cards = ('<div style="text-align:center">%s%s</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:18px;text-align:center">'
                 '<div>%s%s</div><div>%s%s</div></div>') % (pic(a, "1.35", 560), words(a, True), pic(b, "1", 280), words(b, False), pic(c2, "1", 280), words(c2, False))
    pad = (s.get("style") or {}).get("pad")    # this email only
    return '<section class="m m-routine"%s>%s%s</section>' % (' style="padding:%s"' % E(pad) if pad else "", h, cards)


def s_box(lk, s, th):
    """A title, one big picture and tiles. An optional "style" for THIS email only: {"bg", "ink", "pad",
    "frame" (1px line round each picture), "hero_ratio" (the big picture's shape, e.g. "3/2"), "neon": {"color", "glow", "glow2"} lights the whole title like a neon sign}."""
    st = s.get("style") or {}
    ink = ' style="color:%s"' % E(st["ink"]) if st.get("ink") else ""
    def pic1(x):
        h = picture(lk, x["picture"], th)
        return h.replace("<img ", '<img style="border:1px solid %s" ' % E(st["frame"]), 1) if st.get("frame") else h    # frame: a 1px line round each picture
    t = lambda x: '<div class="m-bx"%s>%s<b%s>%s</b><span%s>%s</span></div>' % (
        ' style="text-align:center;justify-items:center"' if st.get("center") else "", pic1(x), ink, E(x["name"]),
        (ink[:-1] + ';text-wrap:balance;max-width:170px"' if ink else ' style="text-wrap:balance;max-width:170px"') if st.get("center") else ink, E(x.get("line", "")))    # center: this email only, tile words centred under their pictures
    hero = t(s["hero"]) if s.get("hero") else ""    # a box of tiles alone (two steps, no big picture) is a layout the model writes
    if hero and st.get("hero_ratio"):    # the big picture's own shape (e.g. "3/2") instead of the default square
        hero = hero.replace('<img style="', '<img style="aspect-ratio:%s;' % E(st["hero_ratio"]), 1) if '<img style="' in hero \
            else hero.replace("<img ", '<img style="aspect-ratio:%s" ' % E(st["hero_ratio"]), 1)
    c = '<p class="m-close"%s>%s</p>' % (ink, _t(s["close"])) if s.get("close") else ""
    nn = st.get("neon")
    hs = ""
    if nn:
        hs = ' style="color:%s;text-shadow:0 0 4px %s,0 0 14px %s,0 0 28px %s,0 0 46px %s"' % (
            E(nn["color"]), E(nn["glow"]), E(nn["glow"]), E(nn.get("glow2") or nn["glow"]), E(nn.get("glow2") or nn["glow"]))
    elif ink:
        hs = ink
    box = "".join(x for x in ("background:%s;" % E(st["bg"]) if st.get("bg") else "",
                             "border-top:0.5px solid %s;" % E(st["top_line"]) if st.get("top_line") else "",    # this email only: a 1px line across the top, as a divider
                             "padding:%s;" % E(st["pad"]) if st.get("pad") else "") if x)
    box = ' style="%s"' % box if box else ""
    if st.get("big"):    # this email only: the title as big as the hero's headline, centred
        hs = ' style="font:300 34px/1.05 var(--serif);margin:6px 0 18px;text-wrap:balance%s"' % (";color:%s" % E(st["ink"]) if st.get("ink") else "")
    btn = '<div style="padding:%dpx 3px 0"><a class="m-btn">%s</a></div>' % (int(st.get("btn_top", 22)), E(s["cta"])) if s.get("cta") else ""    # this email only: a button at the end of the section
    def hl(x):    # this email only (style "free_tile"): the free item as a full-width sage panel, the picture beside its name, a dark FREE badge on top
        return ('<div class="m-bx" style="grid-column:1/-1;display:flex;gap:16px;align-items:center;background:#BBC79E;border-radius:18px;padding:12px;text-align:left;justify-items:start">'
                '<div style="flex:0 0 42%%">%s</div><div style="flex:1"><span style="display:inline-block;background:#0C100F;color:#BBC79E;font:600 12px/1 var(--sans);letter-spacing:.18em;padding:7px 12px;border-radius:999px">%s</span>'
                '<b style="display:block;color:#0C100F;font:300 26px/1.1 var(--serif);margin:12px 0 6px">%s</b><span style="display:block;color:#0C100F;font:500 15px/1.35 var(--sans)">%s</span></div></div>') % (
            pic1(x), E(st["free_tile"]), E(x["name"]), E(x.get("line", "")))
    tl = "".join(hl(x) if st.get("free_tile") else t(x) for x in s.get("tiles", []))
    return '<section class="m m-box"%s><h2%s>%s</h2>%s<div class="m-bxg">%s</div>%s%s</section>' % (box, hs, _t(s["title"]), hero, tl, c, btn)


def s_reach(lk, s, th):
    """This email only (nov-31): a plain stacked graphic, left-aligned capitals title, quiet rows with a cross for what does not reach, one sage row with a tick for what does.
    {"title", "no": [[label, line]], "yes": [label, line]}"""
    row = lambda mark, mbg, mink, a, b, bg, ink, bd: ('<div style="display:flex;align-items:center;gap:14px;background:%s;border:1px solid %s;border-radius:16px;padding:16px 16px;margin-bottom:10px">'
        '<span style="flex:none;width:30px;height:30px;border-radius:50%%;text-align:center;font:600 16px/30px var(--sans);background:%s;color:%s">%s</span>'
        '<div style="text-align:left"><b style="display:block;font:600 17px/1.2 var(--sans);color:%s">%s</b><span style="display:block;font:400 15px/1.35 var(--sans);color:%s;margin-top:3px">%s</span></div></div>') % (
        bg, bd, mbg, mink, mark, ink, E(a), ink, E(b))
    no = "".join(row("\u2715", "rgba(255,255,255,.10)", "#8E938A", a, b, "#141816", "#B8BDB2", "rgba(255,255,255,.12)") for a, b in s["no"])
    a, b = s["yes"]
    yes = row("\u2713", "#0C100F", "#BBC79E", a, b, "#BBC79E", "#0C100F", "#BBC79E")
    return '<section class="m" style="padding:46px 22px 30px"><h2 style="font:300 34px/1.05 var(--serif);text-transform:uppercase;text-align:left;margin:0 0 22px;color:#F2F6EA;text-wrap:balance">%s</h2>%s%s</section>' % (_t(s["title"]), no, yes)


def s_free_panel(lk, s, th):
    """This email only (nov-31): the free item as a full-width sage panel: the picture beside its name, a gold FREE tag with a light sweep across it (_shine 0..1 is where the sweep is;
    build.py cuts frames of it into one looping GIF, like the blinking button). {"tag", "name", "line", "picture"}"""
    sh = float(s.get("_shine", .5))
    pos = int(round(-60 + 220 * sh))
    gold = "linear-gradient(110deg,#E0A310 0%,#FFE98A 25%,#F7C93B 50%,#FFE98A 75%,#E0A310 100%)"    # the store's own gold badge (brand_a.com, dx2-p__badge)
    spark = lambda c, o: '<i style="position:absolute;%s;color:#FFF6CF;font-style:normal;font-size:%dpx;opacity:%.2f">\u2726</i>' % (c, 11 if o > .5 else 8, o)
    return ('<section class="m"><div class="m-bx" style="display:flex;gap:16px;align-items:center;background:#BBC79E;border-radius:18px;padding:12px;text-align:left">'
            '<div style="flex:0 0 42%%">%s</div><div style="flex:1"><span style="position:relative;display:inline-block;background:%s;color:#062B14;font:500 13px/1 var(--sans);letter-spacing:.16em;padding:8px 16px;border-radius:999px;box-shadow:inset 0 0 0 1px rgba(6,43,20,.45);opacity:%.0f">%s</span>'
            '<b style="display:block;color:#0C100F;font:300 26px/1.1 var(--serif);margin:12px 0 6px">%s</b><span style="display:block;color:#0C100F;font:500 15px/1.35 var(--sans)">%s</span></div></div></section>') % (
        picture(lk, s["picture"], th), gold, 1, E(s["tag"]),
        E(s["name"]), E(s.get("line", "")))


def s_selfies(lk, s, th):
    st = s.get("style") or {}    # nov-27 (2026-11-16): {"bg", "ink"} so the grid can sit on a dark ground
    n = '<p class="m-cap">%s</p>' % E(s["note"]) if s.get("note") else ""
    sec = ' style="background:%s"' % E(st["bg"]) if st.get("bg") else ""
    h2 = ' style="color:%s"' % E(st["ink"]) if st.get("ink") else ""
    return '<section class="m m-selfies"' + sec + '><h2' + h2 + '>%s</h2><div class="m-sfg">%s</div>%s</section>' % (_t(s["title"]), "".join(
        '<div class="m-sf">%s%s</div>' % (picture(lk, x["picture"], th, 300),      # a face with no words of its own
                                          "<q>%s</q>" % E(x["quote"]) if x.get("quote") else "")  # carries no quote marks
        for x in s["items"]), n)


def s_photo_card(lk, s, th):
    t = "<h3>%s</h3>" % E(s["title"]) if s.get("title") else ""
    st = s.get("style") or {}    # this email only: {"margin"} (the gap round the card; "0" removes the light strip above the picture), {"top_line"} (a 1px line on top, as a divider)
    css = "".join(x for x in ("margin:%s;" % E(st["margin"]) if st.get("margin") is not None else "",
                             "border-top:0.5px solid %s;" % E(st["top_line"]) if st.get("top_line") else "",
                             "padding-bottom:%dpx;" % int(st["pad_bottom"]) if st.get("pad_bottom") else "",    # this email only: room under the words box, and the colour the section settles into at its bottom edge
                             "background:linear-gradient(180deg,rgba(0,0,0,0) calc(100%% - %dpx),%s 100%%);" % (int(st["pad_bottom"]) + 30, E(st["bottom_bg"])) if st.get("bottom_bg") else "") if x)
    box = ' style="%s"' % css if css else ""
    if st.get("green_card"):    # this email only: the words in a deep-green card with the brand's gold corners, like the quote card
        cu = orn(lk, "corner", 260, th)
        corner = lambda pos, turn: '<i style="position:absolute;%s;width:60px;height:60px;background:url(%s) no-repeat center/contain%s"></i>' % (
            pos, cu, ";transform:rotate(180deg)" if turn else "")
        glass = ('<div class="m-glass" style="background:%s;border-radius:18px;padding:40px 34px 38px">%s%s%s<p>%s</p></div>') % (
            E(st.get("card_bg", "#132B1A")), corner("top:16px;left:16px", False), corner("bottom:16px;right:16px", True), t, _t(s["text"]))
        return '<section class="m-photocard"%s>%s%s</section>' % (box, picture(lk, s["picture"], th, rounded=False), glass)
    pic = picture(lk, s["picture"], th, rounded=False)
    if st.get("top_fade"):    # this email only: the picture melts into the colour of the section above, e.g. "6,43,20"
        c = E(st["top_fade"])
        pic = pic.replace("</figure>", "") if False else pic
        pic = ('<div style="position:relative">%s<div style="position:absolute;left:0;right:0;top:0;height:%dpx;'
               'background:%slinear-gradient(rgb(%s),rgba(%s,.55) 45%%,rgba(%s,0))"></div></div>') % (
            pic, int(st.get("fade_px", 150)),
            ("radial-gradient(ellipse 185px %dpx at 0%% 0%%,rgb(%s) 0,rgba(%s,0) 100%%)," % (int(st.get("fade_px", 150)), E(st["fade_glow"]), E(st["fade_glow"]))) if st.get("fade_glow") else "", c, c, c)
    gcss = "".join(x for x in ("margin-top:-%dpx;" % int(st["glass_up"]) if st.get("glass_up") else "",
                              "background:%s;border-color:rgba(244,205,120,.35);" % E(st["glass_bg"]) if st.get("glass_bg") else "") if x)
    if s.get("head"):    # this email only: a serif heading (with an italic word) in the words box, instead of the small title
        t = '<h2 style="font:300 %dpx/1.1 var(--serif);margin:0 0 %dpx;color:%s;text-align:%s">%s</h2>' % (int(st.get("head_px", 28)), int(st.get("head_gap", 8)), E(st.get("glass_ink", "#19110E")), E(st.get("head_align", "center")), _t(s["head"]))
    if st.get("glass_css"): gcss += st["glass_css"]    # glass_css: this email only, extra style for the words box (shadow, centring, padding)
    if st.get("glass_ink"):    # this email only: the words in this colour (for a pale box), the small title in "glass_title" or the same
        gcss += "color:%s;" % E(st["glass_ink"])
        t = t.replace("<h3", '<h3 style="color:%s"' % E(st.get("glass_title") or st["glass_ink"]), 1)
    if st.get("card_inside"):    # this email only: the words box sits inside the picture's bottom, so the picture runs to the section's edge
        gcss += "position:absolute;left:0;right:0;bottom:%dpx;margin:0 22px;" % int(st.get("card_inside_gap", 18))
        box = ' style="%sposition:relative;line-height:0"' % css
        t = t.replace("<h3", '<h3 style="line-height:1.4"', 1)
        gcss += "line-height:1.3;"
    up = ' style="%s"' % gcss if gcss else ""    # this email only: how far the words box rides up over the picture, and its own background
    words = _t(s["text"])
    if st.get("mix"):    # this email only: the box's first sentence in the serif, the rest in the sans, small
        m = re.match(r"(.+?[.!?])(\s+)(.+)$", s["text"], re.S)
        if m:
            words = '%s<span style="display:block;margin-top:10px;font:400 15px/1.5 var(--sans);color:var(--muted)">%s</span>' % (_t(m.group(1)), _t(m.group(3)))
        else:
            words = '<span style="font:400 15px/1.5 var(--sans)">%s</span>' % _t(s["text"])
    return '<section class="m-photocard"%s>%s<div class="m-glass"%s>%s<p%s>%s</p></div></section>' % (box, pic, up, t, (' style="%s"' % E(st["glass_p"])) if st.get("glass_p") else "", words)    # glass_p: this email only, the words' own style


def s_ingredients(lk, s, th):
    """A list of ingredients, each row a picture, a serif name and its one job. A card with a hairline frame.
    items: [{"picture": {...}, "name": "Sea salt", "job": "clears the old spotted skin off"}]; close: a line under it."""
    st = s.get("style") or {}    # this email only: {"top_line": 1px line across the top of the section, "close_sans": the closing line in body text instead of the serif}
    css = "".join(x for x in ("border-top:0.5px solid %s;" % E(st["top_line"]) if st.get("top_line") else "",
                             "background:%s;" % E(st["bg"]) if st.get("bg") else "",    # bg: this email only, the section's own colour
                             "padding:%s;" % E(st["pad"]) if st.get("pad") else "") if x)
    box = ' style="%s"' % css if css else ""
    IC = {"spot": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2.6" fill="currentColor"/>',    # an item's "icon" in place of a picture (nov-24, 2026-11-16)
          "calendar": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M8 3v4M16 3v4"/>',
          "repeat": '<path d="M4 12a8 8 0 0 1 14-5.3L20 9"/><path d="M20 4v5h-5"/><path d="M20 12a8 8 0 0 1-14 5.3L4 15"/><path d="M4 20v-5h5"/>',
          "crystal": '<path d="M12 3l7 6-7 12L5 9z"/><path d="M5 9h14M9.5 9L12 3l2.5 6M9.5 9L12 21l2.5-12"/>',    # nov-27 (2026-11-16): sea salt, turmeric, moringa
          "root": '<path d="M12 3c3.5 4 5 7 5 10a5 5 0 0 1-10 0c0-3 1.5-6 5-10z"/><path d="M12 11v6"/>',
          "leaf": '<path d="M5 19C5 10 10 5 19 5c0 9-5 14-14 14z"/><path d="M5 19l9-9"/>',
          "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>',    # nov-27 (2026-11-16): Radiance Body Cream rows
          "drop": '<path d="M12 3c4 5 6 8 6 11a6 6 0 0 1-12 0c0-3 2-6 6-11z"/>',
          "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
          "shield": '<path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z"/>'}
    gold = st.get("icon_gold", "#B19A6F")
    def lead(x):
        if x.get("icon") and not x.get("picture"):
            return ('<div style="flex:none;width:54px;height:54px;border-radius:50%%;background:#fff;border:1.5px solid %s;display:flex;align-items:center;justify-content:center;color:#422F28">'
                    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">%s</svg></div>') % (E(gold), IC.get(x["icon"], IC["spot"]))
        return picture(lk, x["picture"], th, 200)
    rows = "".join(
        '<div class="m-irow">%s<div class="m-itext"><h3>%s</h3><p>%s</p></div></div>' % (lead(x), E(x["name"]), E(x["job"]))
        for x in s["items"])
    c = '<p class="m-close"%s>%s</p>' % (' style="font:400 15px/1.5 var(--sans);color:var(--ink)"' if st.get("close_sans") else "", _t(s["close"])) if s.get("close") else ""
    h2 = "<h2>%s</h2>" % _t(s["title"]) if s.get("title") else ""    # nov-27 (2026-11-16): a list with no title leaves no empty heading gap
    return '<section class="m m-ingr"%s>%s<div class="m-icard">%s</div>%s</section>' % (box, h2, rows, c)


def s_arrows(lk, s, th):
    st = s.get("style") or {}    # this email only: {"top_line": 1px line across the top, "frame": 1px line round the white box, "close_body": px, the closing line in body text}
    cb = ' style="font:400 %dpx/1.5 var(--sans);margin:20px 0 0"' % int(st["close_body"]) if st.get("close_body") else ""
    c = '<p class="m-close"%s>%s</p>' % (cb, _t(s["close"])) if s.get("close") else ""
    if s.get("close") and st.get("quote_card"):    # this email only: the closing quote in a deep-green rounded box with the brand's gold corners, the speaker under it
        import re as _re
        mq = _re.match(r'^["\u201c](.+?)["\u201d]\s*(.*)$', s["close"].strip())
        q, who = (mq.group(1), mq.group(2)) if mq else (s["close"], "")
        cu = orn(lk, "corner", 260, th)
        corner = lambda pos, turn: '<i style="position:absolute;%s;width:60px;height:60px;background:url(%s) no-repeat center/contain%s"></i>' % (
            pos, cu, ";transform:rotate(180deg)" if turn else "")
        c = ('<div style="position:relative;background:%s;border-radius:18px;padding:44px 34px 40px;margin:22px 0 0">%s%s'
             '<blockquote style="margin:0%s;font:300 21px/1.3 var(--serif);color:#F2F6EA;text-align:left">\u201c%s\u201d</blockquote>%s</div>') % (
            E(st.get("card_bg", "#132B1A")), corner("top:16px;left:16px", False), corner("bottom:16px;right:16px", True),
            " 0 16px" if who else "", E(q),
            '<cite style="display:block;font:500 11px var(--sans);letter-spacing:.16em;text-transform:uppercase;color:#BBC79E;font-style:normal">%s</cite>' % E(who.rstrip(".")) if who else "")
    box = ' style="%s%s"' % ("border-top:0.5px solid %s;" % E(st["top_line"]) if st.get("top_line") else "", "background:%s;" % E(st["bg"]) if st.get("bg") else "") if (st.get("top_line") or st.get("bg")) else ""    # bg: this email only, the section's own colour
    ul = ' style="border:1px solid %s"' % E(st["frame"]) if st.get("frame") else ""
    if st.get("shadow"):    # this email only: a soft shadow under the white box (css box-shadow value), so it stands off the page
        ul = ' style="%sbox-shadow:%s"' % ("border:1px solid %s;" % E(st["frame"]) if st.get("frame") else "", E(st["shadow"]))
    if st.get("pills"):    # this email only: each row a rounded pill with a tick, "label: line"
        pill = ('<li style="display:flex;justify-content:flex-start;align-items:center;gap:12px;background:%s;color:%s;border-radius:999px;padding:11px 18px 11px 12px;font-size:14px;line-height:1.3">'
                '<i style="flex:none;width:24px;height:24px;border-radius:50%%%%;background:%s;color:%s;text-align:center;line-height:24px;font-style:normal;font-size:13px">\u2713</i>'
                '<div style="color:%s;text-align:left;flex:1"><b style="font-weight:600">%%s</b>%%s</div></li>') % (
            E(st.get("pill_bg", "#C7CFAD")), E(st.get("pill_ink", "#0C100F")), E(st.get("tick_bg", "#0C100F")), E(st.get("tick_ink", "#C7CFAD")), E(st.get("pill_ink", "#0C100F")))
        return '<section class="m m-arrows"%s><h2>%s</h2><ul style="display:grid;gap:10px;background:none;border-radius:0">%s</ul>%s</section>' % (
            box, _t(s["title"]), "".join(pill % (E(a), (" \u2014 " + E(b)) if b else "") for a, b in s["items"]), c)
    if st.get("stack"):    # this email only: every row a fixed label column beside its line, both left-aligned, one gold hairline between rows
        lw = int(st.get("label_w", 104))
        rows = "".join('<li style="display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px 18px;border-top:%s;font-size:15px"><b style="flex:none;white-space:nowrap">%s</b><span style="text-align:right">%s</span></li>' % (
            "0.5px solid %s" % E(st.get("rule", "#B19A6F")) if i else "0", E(a), E(b)) for i, (a, b) in enumerate(s["items"]))
        return '<section class="m m-arrows"%s><h2>%s</h2><ul style="display:block;background:#FFFFFF;border:0.5px solid %s;border-radius:16px;padding:0;overflow:hidden">%s</ul>%s</section>' % (box, _t(s["title"]), E(st.get("rule", "#B19A6F")), rows, c)
    hi = st.get("hi")    # this email only: the row (index, -1 = last) lit in a deep green with brighter, bolder words, so it stands out from the rest
    hi = (len(s["items"]) + int(hi)) if (hi is not None and int(hi) < 0) else hi
    def _row(i, a, b, pc=None):
        if st.get("stacked"):    # this email only: each row its name over its line, both left-aligned, a thin line between rows, the lit row in sage with dark words
            lit = hi is not None and i == int(hi)
            th_ = ('<div style="flex:none;width:76px;border-radius:8px;overflow:hidden">%s</div>' % picture(lk, pc, th)) if pc else ""    # an optional picture in front of the row
            return ('<li style="display:flex;align-items:center;gap:16px;padding:%s;background:%s;border-top:%s">' + th_.replace("%", "%%") + '<div style="flex:1;min-width:0"><b style="display:block;font:600 %dpx var(--sans);letter-spacing:.04em;color:%s;margin:0 0 4px">%s</b>'
                    '<span style="display:block;text-align:left;font:400 15px/1.4 var(--sans);color:%s">%s</span></div></li>') % (
                "18px 18px 20px" if lit else "15px 18px 16px", E(st.get("hi_bg", "#BBC79E")) if lit else "transparent",
                "0" if i == 0 else "1px solid rgba(187,199,158,.22)", int(st.get("hi_size", 18)) if lit else 16,
                E(st.get("hi_ink", "#0C100F")) if lit else "#F2F6EA", E(a), E(st.get("hi_ink", "#0C100F")) if lit else "#CFD4C8", E(b))
        if hi is not None and i == int(hi):
            return ('<li style="background:%s;padding:17px 16px;font-size:%dpx"><b style="font-weight:700;color:%s">%s</b>'
                    '<span style="color:%s;font-weight:500">%s</span></li>') % (E(st.get("hi_bg", "#1E4A2C")), int(st.get("hi_size", 17)), E(st.get("hi_ink", "#F2F6EA")), E(a), E(st.get("hi_ink", "#E3EAD2")), E(b))
        return "<li><b>%s</b><span>%s</span></li>" % (E(a), E(b))
    if st.get("stacked"):    # no arrows in front of the lines, rows on the page's own dark
        ul = (ul or "").replace('style="', 'style="background:#1D2A22;', 1) if ul else ' style="background:#1D2A22"'
        c = '<style>.m-arrows li span::before{content:none!important}</style>' + c
    return _gl(st, '<section class="m m-arrows"%s><h2>%s</h2><ul%s>%s</ul>%s</section>' % (box, _t(s["title"]), ul, "".join(
        _row(i, x[0], x[1], x[2] if len(x) > 2 else None) for i, x in enumerate(s["items"])), c))


def s_grid(lk, s, th):
    st = s.get("style") or {}    # this email only: {"pad": the section's padding}
    box = ' style="padding:%s"' % E(st["pad"]) if st.get("pad") else ""
    return '<section class="m m-grid"%s><div class="m-g6">%s</div><p>%s</p></section>' % (
        box, "".join(picture(lk, p, th, 300) for p in s["pictures"]), E(s.get("caption", "")))


def s_picture(lk, s, th):
    """One picture with an optional caption under it (a before/after, a wide scene)."""
    st = s.get("style") or {}    # this email only: {"bg", "ink", "frame", "rounded", "pad", "ratio"}, as on hero_photo
    ink = ' style="color:%s"' % E(st["ink"]) if st.get("ink") else ""
    top = st.get("caption_top")    # this email only: the words above the picture, centred, as a sub-line
    cs = "font-size:%dpx;line-height:1.4;" % int(st["caption_size"]) if st.get("caption_size") else ""    # this email only: the words under the picture, bigger
    cin = ' style="%s%s%s"' % (cs, "color:%s;" % E(st["ink"]) if st.get("ink") else "", "text-align:center" if st.get("caption_center") else "") if (st.get("caption_center") or cs) else ink    # caption_size alone now bigger too
    cap = '<p class="m-cap"%s>%s</p>' % (cin, _t(s["caption"])) if s.get("caption") and not top else ""
    if s.get("caption") and top:
        top = '<p style="text-align:center;font-size:17px;line-height:1.4;margin:0 0 14px;%s">%s</p>' % (
            "color:%s" % E(st["ink"]) if st.get("ink") else "", _t(s["caption"]))
    else:
        top = ""
    if st.get("subhead"):    # this email only: a centred serif sub-headline above the picture
        top = '<h3 style="font:300 26px/1.15 var(--serif);text-align:center;margin:0 0 14px;%s">%s</h3>' % (
            "color:%s" % E(st["ink"]) if st.get("ink") else "", _t(st["subhead"])) + top
    pic = picture(lk, s["picture"], th, 560, rounded=bool(st.get("rounded", True)))
    if st.get("rounded") is False:    # this email only: edge to edge, square corners
        pic = pic.replace("<img ", '<img style="border-radius:0" ', 1)
    if st.get("ratio"):    # show the picture in this shape (e.g. "9/16", the whole frame) instead of the default crop
        pic = pic.replace("<img ", '<img style="aspect-ratio:%s;object-fit:cover" ' % E(st["ratio"]), 1)
    if st.get("frame"):
        pic = pic.replace("<img ", '<img style="border:1px solid %s" ' % E(st["frame"]), 1)
    if st.get("fade"):    # this email only: {"c": "r,g,b", "top": %, "bottom": %}: the picture melts into the page at its top and bottom
        c = E(st["fade"].get("c", "12,16,15"))
        g = "".join('<div style="position:absolute;left:0;right:0;%s:0;height:%d%%;background:linear-gradient(%s)"></div>' % (
            side, int(h), "rgb(%s),rgba(%s,0)" % (c, c) if side == "top" else "rgba(%s,0),rgb(%s)" % (c, c))
            for side, h in (("top", st["fade"].get("top", 0)), ("bottom", st["fade"].get("bottom", 0))) if h)
        pic = '<div style="position:relative">%s%s</div>' % (pic, g)
    if st.get("width"):    # a narrower picture, centred, same shape
        pic = '<div style="width:%s;margin:0 auto">%s</div>' % (E(st["width"]), pic)
    box = "".join(x for x in ("background:%s;" % E(st["bg"]) if st.get("bg") else "",
                             "padding:%s;" % E(st["pad"]) if st.get("pad") else "") if x)
    box = ' style="%s"' % box if box else ""
    return '<section class="m m-tophalf"%s>%s%s%s</section>' % (box, top, pic, cap)


def _credit(s):
    """The quote's credit, with "verified buyer" only for someone who bought: a credit naming a public place (a comment,
    a survey, Reddit, YouTube) or "verified": false says where the words were said and nothing more (brand_a dec-19,
    2026-11-17). The rule is designed_email.badge, which the delivery gate reads too."""
    import designed_email as DE
    return E(s.get("who") or "") + (" \u00b7 verified buyer" if DE.badge(s) else "")


def s_example(lk, s, th):
    """A customer's words with that customer's own picture over them, or words only when there is none (2026-10-30)."""
    st = s.get("style") or {}
    pic = picture(lk, s["picture"], th, 560) if s.get("picture") else ""    # this email only: {"quote_card": true} puts the quote and name in a deep-green rounded card with gold corners
    if st.get("quote_card"):
        gold = E(st.get("gold", "#C9A94A"))
        cu = orn(lk, "corner", 260, th)    # the brand's own gold corner ornament, top left; turned round for the bottom right
        corner = lambda pos, turn: '<i style="position:absolute;%s;width:60px;height:60px;background:url(%s) no-repeat center/contain%s"></i>' % (
            pos, cu, ";transform:rotate(180deg)" if turn else "")
        card = ('<div style="position:relative;background:%s;border-radius:18px;padding:40px 34px 38px;margin:18px 0 0">%s%s'
                '<blockquote style="margin:0 0 16px;font:300 21px/1.28 var(--serif);color:#F2F6EA">\u201c%s\u201d</blockquote>'
                '<cite style="display:block;font:500 11px var(--sans);letter-spacing:.16em;text-transform:uppercase;color:#BBC79E;font-style:normal">%s</cite></div>') % (
            E(st.get("card_bg", "#132B1A")), corner("top:16px;left:16px", False), corner("bottom:16px;right:16px", True), E(s["quote"]), _credit(s))
        ask = '<p style="font:400 16px/1.45 var(--sans);margin:0 0 16px;padding:0 34px;text-align:center">%s</p>' % _t(s["ask"]) if s.get("ask") else ""
        if s.get("ask") and st.get("ask_lead"):    # this email only: that line in the serif, italic, in the accent, between two short rules
            ac = E(st.get("ask_color", "#BBC79E"))
            rule = '<span style="display:block;width:44px;height:1px;background:%s;margin:0 auto;opacity:.6"></span>' % ac if st.get("ask_rules", True) else ""
            ask = ('<div style="padding:0 30px 4px;text-align:center">%s<p style="font:italic 300 %dpx/1.25 var(--serif);color:%s;margin:%dpx 0;text-wrap:balance">%s</p>%s</div>'
                   % (rule, int(st.get("ask_size", 25)), ac, 14 if rule else 0, _t(s["ask"]), rule))
        return '<section class="m m-example">%s%s%s</section>' % (ask, pic, card)
    return ('<section class="m m-example">%s<blockquote>“%s”</blockquote><cite>%s</cite><p class="m-ex-ask">%s</p></section>'
            % (pic, E(s["quote"]), _credit(s), _t(s.get("ask", ""))))


def s_product(lk, s, th):
    st = s.get("style") or {}
    if st.get("on_pic"):    # this email only: the picture runs full width with calm space at its top; the headline, line and button sit on that space, no overlay
        pic = dict(s["picture"])
        fig = picture(lk, pic, th, 1200, rounded=False)
        m = re.search(r'src="([^"]+)"', fig)
        return ('<section style="padding:0;margin:0"><div role="img" aria-label="%s" style="background:url(%s) center bottom/cover no-repeat;min-height:%dpx;text-align:center">'
                '<div style="padding:%s"><h3 style="font:300 27px/1.1 var(--serif);margin:0 0 10px">%s</h3>'
                '<p style="font:400 14.5px/1.45 var(--sans);margin:0 auto 18px;max-width:320px">%s</p><a class="m-btn">%s</a></div></div></section>') % (
            E(pic.get("alt", "")), m.group(1) if m else "", int(st.get("pic_h", 520)), E(st.get("text_pad", "34px 24px 0")), E(s["name"]), E(s["line"]), E(s["cta"]))
    if st.get("big_cta"):    # this email only: a full-width call-to-action panel: headline, line, the email's own large button, then the product picture as the hero; one dark ground with a warm gold glow, no seam
        base = E(st.get("base", "#060503"))
        br = E(st.get("base_rgb", "6,5,3"))
        pic = dict(s["picture"])
        if "stage" in pic:
            pic.setdefault("fill", .82); pic.setdefault("cy", .5)
        fig = picture(lk, pic, th, 640, rounded=False)
        m = re.search(r'src="([^"]+)"', fig)
        img = ('<div role="img" aria-label="%s" style="height:%dpx;background:linear-gradient(%s,rgba(%s,0) %dpx),url(%s) center %s/cover no-repeat"></div>' % (
            E(pic.get("alt", "")), int(st.get("pic_h", 410)), base, br, int(st.get("seam_px", 30)), m.group(1) if m else "", E(st.get("pic_pos", "15%"))))
        return ('<section style="padding:0;margin:0"><div style="background:radial-gradient(ellipse 330px 150px at 50%% 100%%,rgba(150,100,12,.38) 0,rgba(0,0,0,0) 100%%),%s;text-align:center">'
                '<div style="padding:30px 24px 20px"><h3 style="font:300 27px/1.1 var(--serif);margin:0 0 10px">%s</h3>'
                '<p style="font:400 14.5px/1.45 var(--sans);margin:0 auto 18px;max-width:320px">%s</p>'
                '<a class="m-btn">%s</a></div>%s</div></section>') % (
            base, E(s["name"]), E(s["line"]), E(s["cta"]), img)
    if st.get("gold_card"):    # this email only: a dark gold-brown rounded card, the words and button on the left, the picture running full height on the right
        bg = E(st.get("card_bg", "#2F2006"))
        pic = dict(s["picture"])
        if "stage" in pic:
            pic.setdefault("fill", .82); pic.setdefault("cy", .5)
        fig = picture(lk, pic, th, 400, rounded=False)
        m = re.search(r'src="([^"]+)"', fig)
        img = '<div role="img" aria-label="%s" style="position:absolute;left:0;top:0;right:0;bottom:0;background:url(%s) center/cover no-repeat"></div>' % (E(pic.get("alt", "")), m.group(1) if m else "")
        return ('<section class="m"><div style="display:flex;background:%s;border-radius:18px;overflow:hidden;min-height:%dpx">'
                '<div style="flex:1 1 52%%;padding:26px 18px 26px 22px;display:flex;flex-direction:column;justify-content:center">'
                '<h3 style="font:600 22px/1.15 var(--sans);margin:0 0 12px">%s</h3>'
                '<p style="font:400 15px/1.45 var(--sans);margin:0 0 20px">%s</p><a class="m-btn" style="font-size:12.5px;padding:15px 6px;letter-spacing:.08em;white-space:nowrap">%s</a></div>'
                '<div style="flex:0 0 46%%;position:relative">%s</div></div></section>') % (
            bg, int(st.get("min_h", 290)), E(s["name"]), E(s["line"]), E(s["cta"]), img)
    w = "<s>%s</s>" % E(s["was"]) if s.get("was") else ""
    pic = dict(s["picture"])
    if "stage" in pic:                       # a card thumbnail: the product fills it (at the stage's 46% the tube read as a speck)
        pic.setdefault("fill", .82); pic.setdefault("cy", .5)
    return ('<section class="m"><div class="m-card">%s<div><h3>%s</h3><p>%s</p><div class="m-price"><b>%s</b>%s</div><a class="m-btn">%s</a></div></div></section>'
            % (picture(lk, pic, th, 300), E(s["name"]), E(s["line"]), E(s["price"]), w, E(s["cta"])))


def _seal(lk, th):
    g = lk.get("guarantee") or {}
    u = orn(lk, "seal", 300, th)
    st = ' style="background-image:url(%s)"' % u if u else ""
    return '<div class="e-seal"%s><b>%s</b><small>%s</small></div>' % (st, E(str(g.get("seal_big", ""))), E(g.get("seal_small", "")))


def s_guarantee(lk, s, th):
    g = lk.get("guarantee") or {}
    st = s.get("style") or {}    # this email only: {"flat": no lines above and below, "margin", "pad"}
    css = "".join(x for x in ("border-top:0;border-bottom:0;" if st.get("flat") else "",
                             "margin:%s;" % E(st["margin"]) if st.get("margin") is not None else "",
                             "padding:%s;" % E(st["pad"]) if st.get("pad") else "") if x)
    if st.get("combo") == "row":    # this email only: the compact form — the turn, then ONE gold-lined card holding the seal beside the guarantee, then the button
        bg, ink, gold = E(st.get("bg", "#19110E")), E(st.get("ink", "#FFFFFF")), E(st.get("gold", "#B19A6F"))
        btn = ('<a class="m-btn" style="display:%s;background:%s;color:%s;border-radius:999px;padding:%s;font-weight:600;'
               'font-size:11px;letter-spacing:.12em;text-transform:uppercase;text-align:center">%s</a>') % ("inline-block" if st.get("btn_inline") else "block", E(st.get("button", "#FFFFFF")), E(st.get("button_ink", "#19110E")), "16px 34px" if st.get("btn_inline") else "16px 20px", E(s["cta"]))    # btn_inline: this email only, a button that fits its words
        if st.get("no_btn"): btn = ""    # no_btn: this email only, the button is a live button in the next section
        if st.get("stack"):    # this email only: airy and centred — the turn, a short gold rule, the seal, the guarantee under it; no box
            return ('<section class="m m-guar" style="background:%s;color:%s;border:0;margin:0;padding:%s;text-align:center">'
                    '%s'
                    '<div style="display:flex;justify-content:center;zoom:1.12;margin:0 0 14px">%s</div>'
                    '<h3 style="margin:0 0 8px;color:%s;font:300 26px/1.1 var(--serif)">%s</h3>'
                    '<p style="margin:0 auto;max-width:300px;font-size:15px;line-height:1.5;color:%s;opacity:.88">%s</p></section>') % (
                bg, ink, E(st.get("pad", "44px 30px 10px")), ('<h2 style="margin:0 0 20px;color:%s;font:300 30px/1.1 var(--serif)">%s</h2><span style="display:block;width:48px;height:1px;background:%s;margin:0 auto 26px"></span>' % (ink, _t(s["lead"]), gold)) if s.get("lead") else "", _seal(lk, th),
                ink, _t(s.get("head") or g.get("head", "")), ink, E(s.get("line") or g["words"]))
        if st.get("card_only") and st.get("centered"):    # this email only: seal, heading and line stacked in the middle, no box
            return ('<section class="m m-guar" style="background:%s;color:%s;border:0;margin:0;padding:%s;text-align:center">'
                    '<div style="display:flex;justify-content:center;margin:0 0 14px">%s</div>'
                    '<h2 style="margin:0 0 10px;color:%s;font:300 32px/1.1 var(--serif)">%s</h2>'
                    '<p style="margin:0 auto;max-width:400px;font-size:15px;line-height:1.5;color:%s;opacity:.88">%s</p></section>') % (
                E(st.get("bg", "#FBF8F2")), E(st.get("ink", "#19110E")), E(st.get("pad", "36px 28px 6px")), _seal(lk, th),
                E(st.get("ink", "#19110E")), _t(s.get("head") or g.get("head", "")), E(st.get("ink", "#19110E")), E(s.get("line") or g["words"]))
        if st.get("card_only"):    # this email only: just the gold-lined card, seal beside the guarantee (no turn above it, no button)
            return ('<section class="m m-guar" style="background:%s;color:%s;border:0;margin:0;padding:%s;text-align:center">'
                    '<div style="display:flex;align-items:center;gap:18px;text-align:left;border:1px solid %s;border-radius:16px;padding:20px 22px;background:%s">'
                    '<div style="flex:0 0 96px;zoom:.82">%s</div><div><h3 style="margin:0 0 6px;color:%s;font:300 24px/1.1 var(--serif)">%s</h3>'
                    '<p style="margin:0;font-size:14.5px;line-height:1.45;color:%s">%s</p></div></div></section>') % (
                bg, ink, E(st.get("pad", "8px 18px 6px")), gold, E(st.get("card_bg", "transparent")), _seal(lk, th),
                ink, _t(s.get("head") or g.get("head", "")), ink, E(s.get("line") or g["words"]))
        return ('<section class="m m-guar" style="background:%s;color:%s;border:0;margin:0;padding:%s;text-align:center">'
                '<h2 style="margin:0 0 8px;color:%s;font:300 28px/1.1 var(--serif)">%s</h2>'
                '<p style="margin:0 auto 22px;max-width:430px;font-size:15px;line-height:1.45;color:%s;opacity:.88">%s</p>'
                '<div style="display:flex;align-items:center;gap:18px;text-align:left;border:1px solid %s;border-radius:16px;padding:18px 20px;margin:0 0 %dpx;background:%s">'
                '<div style="flex:0 0 96px;zoom:.82">%s</div><div><h3 style="margin:0 0 6px;color:%s;font:300 24px/1.1 var(--serif)">%s</h3>'
                '<p style="margin:0;font-size:14.5px;line-height:1.45;color:%s;opacity:.88">%s</p></div></div>%s</section>') % (
            bg, ink, E(st.get("pad", "36px 24px 32px")), ink, _t(s["lead"]), ink, E(s["sub"]), gold, int(st.get("card_gap", 20)), E(st.get("card_bg", "transparent")), _seal(lk, th),
            ink, _t(s.get("head") or g.get("head", "")), ink, E(s.get("line") or g["words"]), btn)
    if st.get("combo"):    # this email only: a turn ("lead" + "sub") and the guarantee (seal, head, line, button) as ONE dark section
        bg, ink, gold = E(st.get("bg", "#19110E")), E(st.get("ink", "#FFFFFF")), E(st.get("gold", "#B19A6F"))
        btn = ('<a class="m-btn" style="display:inline-block;background:%s;color:%s;border-radius:999px;padding:15px 36px;font-weight:600;'
               'font-size:11px;letter-spacing:.12em;text-transform:uppercase">%s</a>') % (E(st.get("button", "#FFFFFF")), E(st.get("button_ink", "#19110E")), E(s["cta"]))
        return ('<section class="m m-guar" style="background:%s;color:%s;border:0;padding:%s;text-align:center">'
                '<h2 style="margin:0 0 12px;color:%s;font:300 30px/1.1 var(--serif)">%s</h2>'
                '<p style="margin:0 auto;max-width:430px;font-size:15px;line-height:1.5;color:%s;opacity:.88">%s</p>'
                '<span style="display:block;width:56px;height:1px;background:%s;margin:30px auto 26px"></span>'
                '<div style="color:%s">%s</div>'
                '<h2 style="margin:8px 0 10px;color:%s;font:300 28px/1.1 var(--serif)">%s</h2>'
                '<p style="margin:0 auto 26px;max-width:400px;font-size:15px;line-height:1.5;color:%s;opacity:.88">%s</p>%s</section>') % (
            bg, ink, E(st.get("pad", "56px 28px 56px")), ink, _t(s["lead"]), ink, E(s["sub"]), gold, "#19110E", _seal(lk, th),
            ink, _t(s.get("head") or g.get("head", "")), ink, E(s.get("line") or g["words"]), btn)
    if st.get("card"):    # this email only: the lead line, the seal, the guarantee in a deep-green card with the brand's gold corners; the button under it
        cu = orn(lk, "corner", 260, th)
        corner = lambda pos, turn: '<i style="position:absolute;%s;width:60px;height:60px;background:url(%s) no-repeat center/contain%s"></i>' % (
            pos, cu, ";transform:rotate(180deg)" if turn else "")
        lead = ('<p style="font:300 %dpx/1.25 var(--serif);margin:0 0 20px">%s</p>'
                '<span style="display:block;width:44px;height:1px;background:#BBC79E;margin:0 auto 24px;opacity:.6"></span>' % (int(st.get("lead_size", 24)), _t(s["lead"]))) if s.get("lead") else ""
        if st.get("frame"):    # a gold double-line frame, square corners, a soft gold light behind: not the quote card
            gold = E(st.get("gold", "#C9A94A"))
            rnd = st.get("round")    # one thin gold line with rounded corners and nothing else
            box = ('background:radial-gradient(ellipse 360px 260px at 50%% 0%%,rgba(201,169,74,.12) 0,rgba(0,0,0,0) 100%%);border:1px solid %s;'
                   '%sborder-radius:%dpx;padding:50px 34px 40px') % (gold, "" if rnd else "box-shadow:inset 0 0 0 7px #0C100F,inset 0 0 0 8px rgba(201,169,74,.55);", 20 if rnd else 0)
            lead = lead.replace("#BBC79E", gold)
            corners = "" if rnd else (corner("top:12px;left:12px", False) + corner("top:12px;right:12px;transform:rotate(90deg)", False)
                       + corner("bottom:12px;left:12px;transform:rotate(-90deg)", False) + corner("bottom:12px;right:12px", True))
        else:
            box = "background:%s;border-radius:18px;padding:44px 30px 34px" % E(st.get("card_bg", "#132B1A"))
            corners = corner("top:16px;left:16px", False) + corner("bottom:16px;right:16px", True)
        card = ('<div style="position:relative;%s;margin:0 0 22px">%s%s%s'
                '<h2 style="margin:6px 0 8px">%s</h2><p style="margin:0">%s</p></div>') % (
            box, corners, lead, _seal(lk, th),
            _t(s.get("head") or g.get("head", "")), E(s.get("line") or g["words"]))
        return '<section class="m m-guar" style="border-top:0;border-bottom:0;padding-top:8px">%s<a class="m-btn">%s</a></section>' % (card, E(s["cta"]))
    btn = '<a class="m-btn">%s</a>' % E(s["cta"]) if s["cta"] else ""
    if st.get("btn_font") and s["cta"]:    # this email only: the drawn button sized and shaped like the email's other buttons ({"button","button_ink","btn_radius","btn_pad","btn_font"})
        btn = ('<a class="m-btn" style="display:inline-block;background:%s;color:%s;border-radius:%s;padding:%s;font-weight:600;font-size:%spx;'
               'line-height:1;letter-spacing:.12em;text-transform:uppercase">%s</a>') % (E(st.get("button", "#19110E")), E(st.get("button_ink", "#FFFFFF")),
                E(st.get("btn_radius", "3px")), E(st.get("btn_pad", "10.6px 23px")), E(st["btn_font"]), E(s["cta"]))
    return '<section class="m m-guar"%s>%s<h2>%s</h2><p>%s</p>%s</section>' % (
        ' style="%s"' % css if css else "", _seal(lk, th), _t(s.get("head") or g.get("head", "")), E(s.get("line") or g["words"]), btn)


def s_deal(lk, s, th):
    n = (s.get("style") or {}).get("body_from")    # this email only: lines from this one on are body text, not display serif
    body = 'style="font:400 15px/1.5 var(--sans);color:var(--muted);margin:6px 0 0"'
    pad = (s.get("style") or {}).get("pad")    # this email only
    return '<section class="m m-deal"%s>%s<div class="m-eye">%s</div>%s</section>' % (
        ' style="padding:%s"' % E(pad) if pad else "", _seal(lk, th), E(s.get("eyebrow", "")),
        "".join("<p %s>%s</p>" % (body, _t(x)) if n is not None and i >= n else "<p>%s</p>" % _t(x) for i, x in enumerate(s["lines"])))


def s_offer(lk, s, th):
    """The price in display type, then the live button."""
    w = " <s>%s</s>" % E(s["was"]) if s.get("was") else ""
    bar = '<section class="m m-pricebar"><p><b>%s</b>%s</p></section>' % (E(s["price"]), w)
    # a layout may write the button as words, as {"label", "link"} or not at all (brand_a dec-13/dec-15, 2026-11-16):
    # the words are the label, and no button is no button, never a crash of the whole build
    cta = s.get("cta")
    label = cta.get("label") if isinstance(cta, dict) else cta
    return [bar, s_cta(lk, {"label": label}, th)] if label else [bar]


def s_cta(lk, s, th):
    l = "<p>%s</p>" % E(s["lead"]) if s.get("lead") else ""
    return '<section class="m m-cta">%s<a class="m-btn">%s</a></section>' % (l, E(s["label"]))


def s_rule(lk, s, th):
    """A divider ornament between sections (`rule` in design emails, `fan` in letters, a theme's own `divider`)."""
    name = s.get("ornament", "rule")
    u = orn(lk, name, 760, th)
    if not u:
        return ""
    return '<section class="m m-orn"><div class="e-gems" role="presentation" style="background-image:url(%s)"></div><span class="vh">a divider</span></section>' % u


def s_sign(lk, s, th):
    sg = lk.get("sign") or {}
    if (s.get("style") or {}).get("align") == "center":    # this email only
        pb = ";padding-bottom:%dpx" % int(s["style"]["pad_bottom"]) if s["style"].get("pad_bottom") is not None else ""
        return '<section class="m m-signature" style="text-align:center%s"><span>%s</span><small>%s</small></section>' % (pb, E(s.get("name") or sg.get("name", "")), E(s.get("role") or sg.get("role", "")))
    return '<section class="m m-signature"><span>%s</span><small>%s</small></section>' % (E(s.get("name") or sg.get("name", "")), E(s.get("role") or sg.get("role", "")))


def s_gif(lk, s, th):
    """A real clip the brand owns, looping, linked to the post (gifs live in the run: run:gifs/<name>.gif)."""
    src = "data:image/gif;base64," + base64.b64encode(lk.path(s["gif"]).read_bytes()).decode()
    return ('<section class="m m-gif" data-gif="%s" data-link="%s"><a href="%s"><img src="%s" alt="%s"></a><p>%s<b>%s</b>%s</p></section>'
            % (E(s["gif"]), E(s.get("link", "")), E(s.get("link", "")), src, E(s["caption"]), (E(s["quote"]) + " ") if s.get("quote") else "", E(s["caption"]),
               " · %s" % E(s["note"]) if s.get("note") else ""))    # quote: this email only, the words in normal text and only the name bold


def s_foot(lk, s, th):
    f = lk.get("footer") or {}
    u = orn(lk, "foot", 1200, th, opaque=True)
    st = ' style="background-image:url(%s)"' % u if u else ""
    logo = '<div class="m-footlogo">%s</div>' % _logo(lk, "m-logo-img") if f.get("logo") else ""
    return '<footer class="m-foot%s"%s>%s%s<br>Unsubscribe · Preferences</footer>' % ("" if (u and not f.get("logo")) else " on-band", st, logo, E(f.get("line", "")))


def s_hero_overlay(lk, s, th):
    """A full-width photo with the headline, one line and the button set on it, over a fade into a colour from the photo."""
    pic = picture(lk, s["picture"], th, rounded=False)
    sub = "<p>%s</p>" % _t(s["sub"]) if s.get("sub") else ""
    btn = '<a class="m-btn m-btn-light">%s</a>' % E(s["cta"]) if s.get("cta") else ""
    pos = "top" if s.get("words") == "top" else "bottom"
    fade = E(s.get("fade", "rgba(0,0,0,.55)"))
    return ('<section class="m-overlay m-ov-%s">%s<div class="m-ovw" style="--fade:%s"><h1>%s</h1>%s%s</div></section>'
            % (pos, pic, fade, _t(s["headline"]), sub, btn))


def s_photo_row(lk, s, th):
    """Two or three photos side by side, a caption under each."""
    items = s["items"]
    return '<section class="m m-prow m-prow-%d">%s%s</section>' % (len(items), "".join(
        '<div>%s%s</div>' % (picture(lk, x["picture"], th, 400), '<span>%s</span>' % E(x["caption"]) if x.get("caption") else "") for x in items),
        '<p class="m-cap">%s</p>' % _t(s["caption"]) if s.get("caption") else "")


def s_callout(lk, s, th):
    """A hairline-bordered box with one serif line."""
    return '<section class="m"><div class="m-callout">%s</div></section>' % _t(s["text"])


def s_timeline(lk, s, th):
    """Points on a line (Week 1 / 4 / 8): each a label and a short line."""
    pts = s["points"]
    return '<section class="m m-tl"><div class="m-tlrow">%s</div></section>' % "".join(
        '<div class="m-tlp%s"><b>%s</b><i></i><span>%s</span></div>' % (" dim" if x.get("dim") else "", E(x["label"]), E(x["line"])) for x in pts)


def s_poster(lk, s, th):
    """The key visual, full bleed, no margin: the blow-out an email opens on. Optional big title under it."""
    st = s.get("style") or {}    # this email only: {"title_size", "pad"} to pull the words up under the picture
    title = '<h1%s>%s</h1>' % (' style="font-size:%dpx;margin-bottom:8px"' % int(st["title_size"]) if st.get("title_size") else "", _t(s["title"])) if s.get("title") else ""
    if st.get("accent") and title:    # this email only: the italic word in the title in this colour
        title = title.replace("<i>", '<i style="color:%s">' % E(st["accent"]))
    ps = ("margin-bottom:12px;" if st.get("pad") else "") + ("color:%s;" % E(st["sub_ink"]) if st.get("sub_ink") else "")    # sub_ink: this email only, the sub-line's own colour
    sub = '<p%s>%s</p>' % (' style="%s"' % ps if ps else "", _t(s["sub"])) if s.get("sub") else ""
    cta = '<a class="m-btn">%s</a>' % E(s["cta"]) if s.get("cta") else ""
    if st.get("left"):    # this email only: the title and its line left-aligned, title in capitals (the NOON look)
        tt = "" if st.get("no_caps") else "text-transform:uppercase;"    # no_caps: this email only, left-aligned title kept in its own case (editor, 2026-11-20, brand_a-nov-44)
        title = title.replace("<h1", '<h1 style="text-align:left;%sletter-spacing:.01em"' % tt if "style=" not in title else "<h1", 1) if "style=" not in title else title.replace('style="', 'style="text-align:left;%s' % tt, 1)
        sub = sub.replace("<p", '<p style="text-align:left"', 1) if "style=" not in sub else sub.replace('style="', 'style="text-align:left;', 1)
    words = '<div class="m-postw"%s>%s%s%s</div>' % (' style="padding:%s"' % E(st["pad"]) if st.get("pad") else "", title, sub, cta) if (title or sub or cta) else ""
    gap = ' style="padding-bottom:%dpx"' % int(st["gap_bottom"]) if st.get("gap_bottom") else ""    # this email only: empty space under the picture
    return '<section class="m-poster"%s>%s%s</section>' % (gap, picture(lk, s["picture"], th, 1200, rounded=False), words)


def s_ticker(lk, s, th):
    """A band of the moment's words repeating across, in the accent (BLACK FRIDAY · BLACK FRIDAY · …)."""
    w = E(s.get("text", "")).upper()
    st = s.get("style") or {}
    if st.get("center"):    # this email only: the words once, centred between two stars, nothing cut off at the edge
        inner = "<i>\u2726</i>" + ("<span>%s</span><i>\u2726</i>" % w) * int(st.get("repeat", 1))    # repeat: this email only, the words N times with a star between each
        if st.get("size"):    # this email only: a longer line of words, smaller type so it still fits on one line
            inner = inner.replace("<span>", '<span style="margin:0 8px">')
            inner = '<span style="font-size:%spx;letter-spacing:.12em">%s</span>' % (E(str(st["size"])), inner)
        band = '<section class="m-ticker" style="text-align:center%s%s"><div>%s</div></section>' % (
            ";background:%s" % E(st["bg"]) if st.get("bg") else "",(";color:%s" % E(st["ink"]) if st.get("ink") else "") + (";box-shadow:%s" % E(st["shadow"]) if st.get("shadow") else ""), inner)
    elif st.get("badge"):    # this email only: a flat gold label, not a button: gold-gradient letters between two fading hairlines, small diamonds
        rule = lambda d: ('<span style="margin:0;flex:1;height:1px;background:linear-gradient(%s,rgba(201,169,74,0),rgba(240,216,96,.6))"></span>' % d)
        dia = '<i style="opacity:1;display:block;width:6px;height:6px;transform:rotate(45deg);background:#D9BC58;box-shadow:0 0 8px rgba(240,216,96,.8)"></i>'
        band = ('<section class="m-ticker" style="background:none;padding:6px 24px 20px;display:flex;align-items:center;gap:14px">%s%s'
                '<span style="margin:0;font:600 13px/1 var(--sans);letter-spacing:.34em;text-transform:uppercase;background:linear-gradient(180deg,#F8EBB0,#D4B552 60%%,#B89A3F);-webkit-background-clip:text;background-clip:text;color:transparent;-webkit-text-fill-color:transparent">%s</span>'
                '%s%s</section>') % (rule("270deg"), dia, w, dia, rule("90deg"))
    else:
        band = '<section class="m-ticker"><div>%s</div></section>' % (("<span>%s</span><i>\u2726</i>" % w) * 6)
    gap = st.get("top_gap")    # this email only: empty space above the band (it belongs to this section, so the section above ends sooner)
    return '<div style="padding-top:%dpx">%s</div>' % (int(gap), band) if gap else band


def s_annotated(lk, s, th):
    """One picture in the middle with short labels either side, each on a hairline that ends in a dot at the picture
    (the way a product is annotated). {"title", "picture", "left": [labels], "right": [labels], "close"}; style (this email
    only): {"bg", "ink", "line", "pad", "pic_w": picture width in %}."""
    st = s.get("style") or {}
    ink, line = E(st.get("ink", "#2A1D18")), E(st.get("line", "#8A5A3C"))
    pw = int(st.get("pic_w", 50))
    def lab(x, right):
        dot = '<b style="flex:none;width:7px;height:7px;border-radius:50%%;background:%s"></b>' % line
        bar = '<i style="flex:1;height:1px;background:%s;min-width:8px"></i>' % line
        txt = '<span style="flex:none;max-width:78px;font:500 10px/1.3 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:%s;text-align:%s">%s</span>' % (ink, "left" if right else "right", E(x))
        return '<div style="display:flex;align-items:center;gap:6px">%s</div>' % ((dot + bar + txt) if right else (txt + bar + dot))
    col = lambda items, right: '<div style="flex:1;min-width:0;display:flex;flex-direction:column;justify-content:space-around;gap:16px">%s</div>' % "".join(lab(x, right) for x in items)
    pic = picture(lk, s["picture"], th, 400, rounded=False).replace("<img ", '<img style="width:100%;display:block;border-radius:0" ', 1)
    close = '<p style="font:400 15px/1.5 var(--sans);color:%s;text-align:center;margin:20px 8px 0">%s</p>' % (ink, _t(s["close"])) if s.get("close") else ""
    return ('<section class="m" style="padding:%s;background:%s;text-align:center"><div style="font:300 28px/1.1 var(--serif);color:%s;padding:0 6px 14px">%s</div>'
            '<div style="display:flex;align-items:stretch;gap:6px">%s<div style="flex:none;width:%d%%">%s</div>%s</div>%s</section>') % (
        E(st.get("pad", "30px 18px 30px")), E(st.get("bg", "#F3ECE2")), ink, _t(s["title"]), col(s.get("left", []), False), pw, pic, col(s.get("right", []), True), close)


def s_compare(lk, s, th):
    """Two things side by side on one white card, a serif name over each column and the rows between hairlines.
    {"title", "sub", "left": "Isaan", "right": "Milan", "rows": [[left words, right words]], "close"}; style (this email
    only): {"bg", "ink", "line"}."""
    st = s.get("style") or {}
    if st.get("modern"):    # this email only: two soft cards, the left one quiet with crosses, the right one lit in the brand's green with ticks
        row = lambda t, mark, ink, bd: ('<div style="display:flex;align-items:center;gap:10px;min-height:64px;padding:8px 0;border-top:1px solid %s">'
                                        '<span style="flex:none;width:22px;height:22px;border-radius:50%%;text-align:center;font:600 12px/22px var(--sans);%s">%s</span>'
                                        '<span style="font:500 14px/1.3 var(--sans);color:%s">%s</span></div>') % (bd, mark[1], mark[0], ink, E(t))
        no = ("\u2715", "background:rgba(255,255,255,.08);color:#8E938A")
        yes = ("\u2713", "background:#C7CFAD;color:#0C100F")
        lcol = "".join(row(r[0], no, "#B8BDB2", "rgba(255,255,255,.08)") for r in s["rows"])
        rcol = "".join(row(r[1], yes, "#F2F6EA", "rgba(199,207,173,.22)") for r in s["rows"])
        return ('<section class="m" style="padding:46px 22px 30px;background:%s"><div style="font:300 30px/1.1 var(--serif);color:#F2F6EA;text-align:center;padding:0 0 18px">%s</div>'
                '<div style="display:flex;gap:10px;align-items:stretch">'
                '<div style="flex:1;border:1px solid rgba(255,255,255,.12);border-radius:18px;padding:16px 14px 6px;background:#141816">'
                '<div style="font:500 11px var(--sans);letter-spacing:.16em;text-transform:uppercase;color:#8E938A;padding-bottom:12px">%s</div>%s</div>'
                '<div style="flex:1;border:1px solid rgba(199,207,173,.65);border-radius:18px;padding:16px 14px 6px;background:linear-gradient(160deg,#16422A,#0B2417);box-shadow:0 0 28px rgba(187,199,158,.18)">'
                '<div style="font:300 22px/1 var(--serif);color:#C7CFAD;padding-bottom:10px">%s</div>%s</div></div></section>') % (
            E(st.get("bg", "#0C100F")), _t(s["title"]), E(s["left"]), lcol, E(s["right"]), rcol)
    ink, line = E(st.get("ink", "#2A1D18")), E(st.get("line", "#B19A6F"))
    rows = "".join('<div style="display:grid;grid-template-columns:1fr 1fr;border-top:1px solid %s">%s</div>' % (
        line, "".join('<div style="padding:16px 12px;font:500 15px/1.35 var(--sans);color:%s;text-align:center;%s">%s</div>' % (
            ink, "border-left:1px solid %s;" % line if i else "", E(x)) for i, x in enumerate(r))) for r in s["rows"])
    head = '<div style="display:grid;grid-template-columns:1fr 1fr">%s</div>' % "".join(
        '<div style="padding:22px 12px 16px;font:300 28px/1.1 var(--serif);color:%s;text-align:center;%s">%s</div>' % (
            ink, "border-left:1px solid %s;" % line if i else "", E(x)) for i, x in enumerate((s["left"], s["right"])))
    sub = '<p style="font:400 15px/1.5 var(--sans);color:%s;text-align:center;margin:0 12px 18px">%s</p>' % (ink, _t(s["sub"])) if s.get("sub") else ""
    close = '<p style="font:400 15px/1.5 var(--sans);color:%s;text-align:center;margin:18px 8px 0">%s</p>' % (ink, _t(s["close"])) if s.get("close") else ""
    if st.get("hi"):    # this email only (NOON's lit column): the right column on a lighter ground, its words in the dark ink
        hi = E(st["hi"])
        head = head.replace('border-left:1px solid %s;' % line, 'border-left:1px solid %s;background:%s;color:%s;' % (line, hi, E(st.get("hi_ink", "#0C100F"))), 1)
        rows = rows.replace('border-left:1px solid %s;' % line, 'border-left:1px solid %s;background:%s;color:%s;' % (line, hi, E(st.get("hi_ink", "#0C100F"))))
    return ('<section class="m" style="padding:30px 18px;background:%s;text-align:center"><div style="font:300 30px/1.1 var(--serif);color:%s;padding:0 6px 14px">%s</div>%s'
            '<div style="background:%s;border-radius:%s;overflow:hidden;box-shadow:0 8px 26px rgba(66,47,40,.10)">%s%s</div>%s</section>') % (
        E(st.get("bg", "#F3ECE2")), E(st.get("title_ink", st.get("ink", "#2A1D18"))), _t(s["title"]), sub, E(st.get("card", "#fff")), E(st.get("radius", "18px")), head, rows, close)


def s_chapter(lk, s, th):
    """A centred block of words on a colour: an optional small caps line, an optional large serif heading, then short paragraphs
    in a narrow column. The words are the email's own; this only sets them. {"eyebrow", "head", "paras": [..]}; style (this
    email only): {"bg", "ink", "soft": the small line, "pad", "head_px", "body_px", "width"}."""
    st = s.get("style") or {}
    ink, soft = E(st.get("ink", "#2A1D18")), E(st.get("soft", "#8A5A3C"))
    eye = '<div style="font:500 10.5px/1.3 var(--sans);letter-spacing:.2em;text-transform:uppercase;color:%s;margin:0 0 14px">%s</div>' % (soft, E(s["eyebrow"])) if s.get("eyebrow") else ""
    head = '<h2 style="font:300 %dpx/1.08 var(--serif);color:%s;margin:0 0 %dpx;letter-spacing:-.005em">%s</h2>' % (
        int(st.get("head_px", 36)), ink, 16 if s.get("paras") else 0, _t(s["head"])) if s.get("head") else ""
    paras = "".join('<p style="font:400 %dpx/1.65 var(--sans);color:%s;margin:0 0 14px">%s</p>' % (int(st.get("body_px", 16)), ink, _t(x)) for x in s.get("paras", []))
    return ('<section class="m" style="padding:%s;background:%s;text-align:center"><div style="max-width:%dpx;margin:0 auto">%s%s%s</div></section>') % (
        E(st.get("pad", "44px 28px 30px")), E(st.get("bg", "#FBFAF5")), int(st.get("width", 460)), eye, head, paras)


def _pl(st, k, d):
    return E(st.get(k, d))


def s_plain_logo(lk, s, th):
    """Minimal header: the brand's logo alone, dark, centred on white. style: {"bg", "h", "pad"}."""
    st = s.get("style") or {}
    lg = _logo(lk, "m-logo-img").replace("<img ", '<img style="filter:brightness(0) opacity(.88);height:%dpx;display:block;margin:0 auto" ' % int(st.get("h", 22)), 1)
    return '<section class="m" style="padding:%s;background:%s">%s</section>' % (_pl(st, "pad", "34px 20px 26px"), _pl(st, "bg", "#FBFAF5"), lg)


def s_plain(lk, s, th):
    """Quiet type on a plain ground: a tiny spaced-caps line, a heading, short paragraphs, and customers' words in italic serif.
    {"eyebrow", "head", "paras", "quotes": [{"quote","who"}], "rule": true for a hairline under}; style: {"bg","ink","body_ink","pad","align","head_px","body_px","width","head_font": serif|sans}."""
    st = s.get("style") or {}
    ink, body = _pl(st, "ink", "#2A1D18"), _pl(st, "body_ink", "#43362F")
    al = _pl(st, "align", "center")
    out = []
    if s.get("eyebrow"):
        out.append('<div style="font:500 10px/1.5 var(--sans);letter-spacing:.2em;text-transform:uppercase;color:%s;margin:0 0 16px">%s</div>' % (ink, E(s["eyebrow"])))
    if s.get("head"):
        hf = "var(--sans)" if st.get("head_font") == "sans" else "var(--serif)"
        out.append('<h2 style="font:%s %dpx/1.1 %s;color:%s;margin:0 0 %dpx;text-wrap:balance">%s</h2>' % ("500" if st.get("head_font") == "sans" else "300", int(st.get("head_px", 28)), hf, ink, int(st.get("head_gap", 18)), _t(s["head"])))
    for x in s.get("paras", []):
        out.append('<p style="font:400 %dpx/1.6 var(--sans);color:%s;margin:0 auto 16px;max-width:%dpx;text-wrap:pretty">%s</p>' % (int(st.get("body_px", 16)), body, int(st.get("body_w", 380)), _t(x)))
    for q in s.get("quotes", []):
        out.append('<p style="font:%s 300 %dpx/1.2 var(--serif);color:%s;margin:0 0 %dpx">\u201c%s\u201d</p>%s' % ("normal" if st.get("quote_upright") else "italic", int(st.get("quote_px", 22)), ink, 14 if q.get("who") else 40, E(q["quote"]),
            ('<div style="font:500 9.5px/1.4 var(--sans);letter-spacing:.2em;text-transform:uppercase;color:%s;margin:0 0 44px">%s</div>' % (_pl(st, "who_ink", body), E(q["who"]))) if q.get("who") else ""))
    if out:    # the section's own padding sets the gap to its neighbours, so the last element adds none
        ms = list(re.finditer(r"margin:0 (auto|0) \d+px", out[-1]))
        if ms:
            m = ms[-1]
            out[-1] = out[-1][:m.start()] + "margin:0 " + m.group(1) + " 0" + out[-1][m.end():]
    rule = '<div style="height:1px;background:%s;margin:%s"></div>' % (_pl(st, "rule_ink", "rgba(42,29,24,.22)"), "0 24px") if s.get("rule") else ""    # rule_ink: this email only, the hairline's colour (e.g. the brand gold)
    if not out and rule:    # a divider alone: say so for readers without pictures
        out.append('<span class="vh">a divider</span>')
    return '<section class="m" style="padding:%s;background:%s;text-align:%s"><div style="max-width:%dpx;margin:0 auto">%s</div>%s</section>' % (
        _pl(st, "pad", "34px 28px 14px"), _pl(st, "bg", "#FBFAF5"), al, int(st.get("width", 520)), "".join(out), rule)


def s_plain_list(lk, s, th):
    """Hairline rows, a small caps label on the left and its words on the right (a quiet table). {"title", "rows": [[label, words]]}."""
    st = s.get("style") or {}
    ink, body = _pl(st, "ink", "#2A1D18"), _pl(st, "body_ink", "#43362F")
    line = "1px solid rgba(42,29,24,.22)"
    title = '<div style="font:500 10px/1.5 var(--sans);letter-spacing:.2em;text-transform:uppercase;color:%s;padding:0 0 14px">%s</div>' % (ink, E(s["title"])) if s.get("title") else ""
    rows = "".join('<div style="display:flex;gap:18px;justify-content:space-between;align-items:baseline;padding:15px 0;border-top:%s;text-align:left">'
                   '<div style="flex:none;width:34%%;font:500 11px/1.4 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:%s">%s</div>'
                   '<div style="flex:1;font:400 15px/1.5 var(--sans);color:%s">%s</div></div>' % (line, ink, E(a), body, E(b)) for a, b in s["rows"])
    return '<section class="m" style="padding:%s;background:%s">%s%s<div style="border-top:%s"></div></section>' % (
        _pl(st, "pad", "26px 28px 30px"), _pl(st, "bg", "#FBFAF5"), title, rows, line)


def s_plain_photo(lk, s, th):
    """One or two clean pictures set in the margins, no frame; two sit edge to edge. {"items": [{"picture"}]}; style: {"bg","pad"}."""
    st = s.get("style") or {}
    its = s["items"]
    imgs = []
    for x in its:
        f = picture(lk, x["picture"], th, 640 if len(its) == 1 else 400, rounded=False)
        sty = "width:100%;display:block;border-radius:0" + ("" if len(its) == 1 else ";aspect-ratio:1;object-fit:cover")
        imgs.append('<div style="flex:1;min-width:0">%s</div>' % f.replace("<img ", '<img style="%s" ' % sty, 1))
    return '<section class="m" style="padding:%s;background:%s"><div style="display:flex;gap:0">%s</div></section>' % (
        _pl(st, "pad", "0 20px"), _pl(st, "bg", "#FBFAF5"), "".join(imgs))


def s_plain_strip(lk, s, th):
    """A full-width band with three or four short facts in a row: a serif figure over a small line. {"items": [[figure, line]]}; style: {"bg","ink","pad"}."""
    st = s.get("style") or {}
    ink = _pl(st, "ink", "#2A1D18")
    cells = "".join('<div style="flex:1;min-width:0;padding:0 4px"><div style="font:300 17px/1.1 var(--serif);color:%s;white-space:nowrap">%s</div>'
                    '<div style="font:400 9px/1.4 var(--sans);color:%s;margin-top:5px">%s</div></div>' % (ink, E(a), ink, E(b)) for a, b in s["items"])
    return '<section class="m" style="padding:%s;background:%s;text-align:center"><div style="display:flex;gap:4px">%s</div></section>' % (_pl(st, "pad", "40px 18px"), _pl(st, "bg", "#E8DCC4"), cells)


def s_plain_mosaic(lk, s, th):
    """Three pictures in a tight mosaic: two stacked on the left, one tall on the right, a few pixels between. {"items": [top-left, bottom-left, tall right]} (each {"picture"}); style: {"bg","pad","gap","w": the mosaic's width in px (600 minus its side padding)}."""
    st = s.get("style") or {}
    g = int(st.get("gap", 4))
    w = int(st.get("w", 320))
    cw = (w - g) // 2                    # one column
    rh = cw                              # the stacked pictures are square; the tall one spans both
    def cell(x, h):
        f = picture(lk, x["picture"], th, 400, rounded=False)
        return '<div style="width:%dpx">%s</div>' % (cw, f.replace("<img ", '<img style="width:%dpx;height:%dpx;display:block;object-fit:cover;border-radius:0" ' % (cw, h), 1))
    its = s["items"]
    left = '<div style="display:flex;flex-direction:column;gap:%dpx">%s%s</div>' % (g, cell(its[0], rh), cell(its[1], rh))
    return '<section class="m" style="padding:%s;background:%s"><div style="display:flex;gap:%dpx;align-items:flex-start">%s%s</div></section>' % (
        _pl(st, "pad", "0 40px"), _pl(st, "bg", "#FBFAF5"), g, left, cell(its[2], rh * 2 + g))


def s_plain_row(lk, s, th):
    """A picture on one side and short words on the other, like a product row: serif title, a small paragraph. {"picture","title","text","side": "left"|"right"}; style: {"bg","pad","ink"}."""
    st = s.get("style") or {}
    ink, body = _pl(st, "ink", "#2A1D18"), _pl(st, "body_ink", "#43362F")
    f = picture(lk, s["picture"], th, 300, rounded=False).replace("<img ", '<img style="width:100%;aspect-ratio:1;object-fit:cover;display:block;border-radius:0" ', 1)
    img = '<div style="flex:0 0 42%%;min-width:0">%s</div>' % f
    txt = ('<div style="flex:1;min-width:0;text-align:left"><div style="font:300 17px/1.15 var(--serif);color:%s;margin:0 0 7px">%s</div>'
           '<div style="font:400 10px/1.55 var(--sans);color:%s">%s</div></div>') % (ink, _t(s["title"]), body, _t(s["text"]))
    return '<section class="m" style="padding:%s;background:%s"><div style="display:flex;gap:18px;align-items:center">%s</div></section>' % (
        _pl(st, "pad", "22px 29px"), _pl(st, "bg", "#FBFAF5"), (img + txt) if s.get("side", "left") == "left" else (txt + img))


def s_plain_card(lk, s, th):
    """A soft rounded card on a warm gradient, a round gold badge on top, a heading and a few lines. {"badge": big figure, "badge_sub": small caps under it, "head", "paras"};
    style: {"bg": the ground round the card, "pad", "ink", "body_ink", "head_px", "radius"}."""
    st = s.get("style") or {}
    ink, body = _pl(st, "ink", "#2A1D18"), _pl(st, "body_ink", "#43362F")
    badge = ""
    if s.get("badge"):
        gold = _pl(st, "gold", "#9C7C30")
        # a flat line emblem, no fill: two fine gold rings, the figure in serif, the small word spaced under it
        badge = ('<div style="width:64px;height:64px;margin:0 auto 18px;border-radius:50%%;border:0.7px solid %s;display:flex;align-items:center;justify-content:center">'
                 '<div style="width:56px;height:56px;border-radius:50%%;border:0.4px solid %s;display:flex;flex-direction:column;align-items:center;justify-content:center">'
                 '<div style="font:300 27px/1 var(--serif);color:%s;letter-spacing:.01em">%s</div>'
                 '<div style="font:500 5.6px/1 var(--sans);letter-spacing:.34em;color:%s;margin:4px 0 0 .34em">%s</div></div></div>') % (gold, gold, gold, E(s["badge"]), gold, E(s.get("badge_sub", "")))
    head = '<h2 style="font:400 %dpx/1.12 var(--serif);color:%s;margin:0 0 12px">%s</h2>' % (int(st.get("head_px", 22)), ink, _t(s["head"])) if s.get("head") else ""
    paras = "".join('<p style="font:400 11px/1.6 var(--sans);color:%s;margin:0 auto 8px;max-width:290px">%s</p>' % (body, _t(x)) for x in s.get("paras", []))
    bgc = ("linear-gradient(100deg,#E2E0D7 0%,#EBE0C3 24%,#EBD9BB 48%,#EBD4C4 76%,#E5D9CD 100%),radial-gradient(ellipse 160px 120px at 74% 30%,rgba(236,206,196,.55),rgba(0,0,0,0))")
    return ('<section class="m" style="padding:%s;background:%s"><div style="border-radius:%dpx;background:%s;padding:34px 22px 30px;text-align:center">%s%s%s</div></section>') % (
        _pl(st, "pad", "10px 20px"), _pl(st, "bg", "#FBFAF5"), int(st.get("radius", 11)), bgc, badge, head, paras)


def s_link(lk, s, th):
    return '<section class="m m-link"><a>%s →</a></section>' % E(s["text"])


SECTIONS = {k[2:]: v for k, v in dict(globals()).items() if k.startswith("s_") and callable(v)}
# editor's own Figma look (2026-11-17, brand_b-nov-33): opt-in fg_* sections, used only by an email whose email.json names them.
import figma_look as _FG  # noqa: E402
SECTIONS.update(_FG.FG)


def house(spec, lk):
    """A brand's house look: an email the layout marked `"look": "house"` takes the brand's house styles
    (`house.styles` in its look file) as each section's DEFAULT style, its own style over them (the email wins);
    a section with a `variant` takes "<name>:<variant>" when the house has one. Any other email, or a brand with no
    house, comes back unchanged, so nothing drawn before changes. Returns a new spec; the one given is not touched."""
    styles = (lk.get("house") or {}).get("styles") or {}
    if spec.get("look") != "house" or not styles:
        return spec
    out = []
    for s in spec["sections"]:
        d = styles.get("%s:%s" % (s["s"], s["variant"])) if s.get("variant") else None
        d = d if d is not None else styles.get(s["s"])
        out.append(dict(s, style=dict(d, **(s.get("style") or {}))) if d else s)
    return dict(spec, sections=out)


def buying_defaults(spec):
    """The sections with every buying section's button label and price filled: the email's own main button label and
    no price, never a crash (2026-11-08: four Black Friday layouts held on KeyError 'cta' / 'price'). The image
    engine and the live Klaviyo rows (build.py) both draw from this, so neither crashes where the other would not."""
    main_cta = next((x.get("label") or x.get("cta") for x in spec["sections"] if x.get("s") == "cta" and (x.get("label") or x.get("cta"))),
                    next((x["cta"] for x in spec["sections"] if x.get("cta")), "Shop now"))
    out = []
    for s in spec["sections"]:
        name = s.get("s", "")
        if name in ("guarantee", "product", "offer", "pricebar") or "price" in s or name.endswith("product"):
            s = dict(s)
            if name == "guarantee" and s.get("no_cta"):    # this email only: the guarantee carries no button
                s["cta"] = ""
            s.setdefault("cta", main_cta)
            if name in ("product", "pricebar", "offer"):
                s.setdefault("price", "")
        out.append(s)
    return out


def sections(spec, lk):
    """[(section name, html)] in order. A theme repaints every section; the brand palette is the default."""
    spec = house(spec, lk)
    th = spec.get("theme")
    out = []
    for s in buying_defaults(spec):
        name = s["s"]
        if name not in SECTIONS:
            raise ValueError("%s: no section called %r (have: %s)" % (spec.get("label"), name, ", ".join(sorted(SECTIONS))))
        if isinstance(s.get("cta"), dict):    # a button written as {"label", "link"}: every section takes its words
            s = dict(s, cta=s["cta"].get("label") or "")   # (brand_a dec-13/dec-15, 2026-11-16)
        h = SECTIONS[name](lk, s, th)
        for x in (h if isinstance(h, list) else [h]):
            if x and s.get("ground") in ("alt", "panel"):
                x = x.replace('class="', 'class="g-%s ' % s["ground"], 1)
            if x and th:
                x = x.replace('class="', 'class="th-%s ' % th, 1)
            if x and s.get("pad_y"):    # this email only: less (or more) room above and below this section, {"top": px, "bottom": px}
                py = s["pad_y"]
                css_y = "".join(("padding-top:%dpx;" % int(py["top"])) if py.get("top") is not None else "") + \
                        "".join(("padding-bottom:%dpx;" % int(py["bottom"])) if py.get("bottom") is not None else "")
                if re.match(r'<section[^>]*\sstyle="', x):
                    x = re.sub(r'^(<section[^>]*?\sstyle=")', lambda m: m.group(1) + css_y, x, count=1)
                else:
                    x = re.sub(r'^<section', '<section style="%s"' % css_y, x, count=1)
            if x and s.get("bg"):    # this email only: one flat colour behind the whole section (e.g. a light beige instead of white)
                bgcss = "background:%s;" % E(s["bg"])
                if re.match(r'<section[^>]*\sstyle="', x):
                    x = re.sub(r'^(<section[^>]*?\sstyle=")', lambda m: m.group(1) + bgcss, x, count=1)
                else:
                    x = re.sub(r'^<section', '<section style="%s"' % bgcss, x, count=1)
            if x and s.get("rule"):    # this email only: a thin gold hairline across the top of the section, fading at both ends. {"color"}
                c = E((s["rule"] if isinstance(s["rule"], dict) else {}).get("color", "201,169,74"))
                x = re.sub(r'^(<section[^>]*>)', lambda m: m.group(1) + '<span style="position:absolute;left:8%%;right:8%%;top:0;height:1px;z-index:2;background:linear-gradient(90deg,rgba(%s,0),rgba(%s,.85) 25%%,rgba(%s,.85) 75%%,rgba(%s,0))"></span>' % (c, c, c, c), x, count=1)
            if x and s.get("glow"):    # this email only: soft out-of-focus light behind the section, [{"x": "0%", "y": "40%", "r": 220, "c": "rgba(199,207,173,.2)"}, ...]
                lay = ",".join(("radial-gradient(ellipse %dpx %dpx at %s %s,%s 0,rgba(0,0,0,0) 100%%)" % (int(g.get("r", 220)), int(g["ry"]), E(g.get("x", "50%")), E(g.get("y", "50%")), E(g["c"]))) if g.get("ry") else
                               ("radial-gradient(circle at %s %s,%s 0,rgba(0,0,0,0) %dpx)" % (E(g.get("x", "50%")), E(g.get("y", "50%")), E(g["c"]), int(g.get("r", 220))))
                               for g in s["glow"])    # "ry" makes it a flat ellipse (r wide, ry tall) so it fades out before the section's top and bottom
                if s.get("glow_bg"):    # this email only: a deep colour under the lights (the brand's green)
                    lay += ",%s" % E(s["glow_bg"])
                x = '<div class="gl" style="background:%s">%s</div>' % (lay, x)
            if x:
                out.append((name, x))
    return out


# ---------- the page around the sections ----------

def fonts(lk):
    out = []
    for role in ("display", "body", "button"):
        f = lk["fonts"].get(role)
        if not f:
            continue
        for x in f.get("files", []):
            p = lk.path(x["file"])
            if p and p.exists():
                fmt = "woff2" if p.suffix == ".woff2" else "woff" if p.suffix == ".woff" else "truetype"
                out.append("@font-face{font-family:'%s';src:url(data:font/%s;base64,%s) format('%s');font-weight:%d;font-display:swap}" % (
                    f["family"], fmt, base64.b64encode(p.read_bytes()).decode(), fmt, x.get("weight", 400)))
    return "\n".join(out)


def css(lk, theme=None):
    t = lk.tokens()
    def block(tk):
        return ";".join("--%s:%s" % (k.replace("_", "-"), v) for k, v in tk.items())
    f = lk["fonts"]
    root = ".em{%s;--serif:'%s',%s;--sans:'%s',%s}" % (block(t), f["display"]["family"], f["display"].get("fallback", "Georgia,serif"),
                                                     f["body"]["family"], f["body"].get("fallback", "Helvetica,Arial,sans-serif"))
    themes = "".join(".em .th-%s,.em.th-%s{%s;background-color:%s;color:%s}" % (k, k, block(v.get("tokens", {})), v["tokens"].get("canvas", t["canvas"]),
                                                                          v["tokens"].get("ink", t["ink"]))
                     for k, v in (lk.get("themes") or {}).items() if not k.startswith("_"))
    lay = lk.get("layout") or {}
    if lay.get("h2_px"):
        root = root[:-1] + ";--h2:%dpx}" % lay["h2_px"]
    if lay.get("button_radius"):
        root = root[:-1] + ";--btn-radius:%s}" % lay["button_radius"]
    if lay.get("button_bg"):    # this email only: every button in this colour (e.g. white)
        root = root[:-1] + ";--btn-bg:%s}" % lay["button_bg"]
    if f.get("button"):
        root = root[:-1] + ";--btnfont:'%s',%s}" % (f["button"]["family"], f["body"].get("fallback", "sans-serif"))
    grain = ""
    if lay.get("grain"):    # this email only: fine film grain over every designed section + a soft green light from the left, like a lit charcoal wall
        nz = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' "
              "baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 1.6 -.55'/></filter>"
              "<rect width='100%25' height='100%25' filter='url(%23n)'/></svg>")
        op = float(lay["grain"]) if lay["grain"] not in (True, 1) else .22
        grain = (".em .m{position:relative;background-image:radial-gradient(ellipse 85%% 70%% at 12%% 45%%,rgba(92,120,98,.20) 0,rgba(92,120,98,0) 100%%)}"
                 ".em .m::after,.em .m-head.m-flat::before{content:'';position:absolute;inset:0;background:url(\"%s\");background-size:150px 150px;opacity:%s;pointer-events:none;z-index:1}"
                 ".em .m-head.m-flat{position:relative}") % (nz, op)
    corner = orn(lk, "corner", 120, theme)
    extra = ".e-frame::before,.e-frame::after{background-image:url(%s)}" % corner if corner else ".e-frame::before,.e-frame::after{display:none}"
    body_px = ".em .m-letter p{font-size:%dpx;line-height:1.6}" % int(lay["body_px"]) if lay.get("body_px") else ""    # this email only: the letter's body text size
    caps = (".em .m-turn h2,.em .m-display h2,.em .m-tiles h2,.em .m-guar h2{text-transform:uppercase;letter-spacing:.015em;line-height:1.02;text-align:left}"
            ".em .m-turn p{text-align:left}.em .m-turn h2 i{text-transform:none}.em .m-guar h2{text-align:center}"
            ".em .m-herophoto h1,.em .m-box h2{font:300 42px/1.02 var(--serif);text-transform:uppercase;text-align:left;letter-spacing:.01em;text-wrap:balance}"
            ".em .m-herophoto h1 i,.em .m-box h2 i{font-style:normal}.em .m-herophoto p{text-align:left}") if lay.get("caps") else ""    # this email only: big left-aligned capital headlines (the grand dark look)
    noon = (".em .m-herotype{background:radial-gradient(110% 75% at 50% 0%,rgba(var(--glow-rgb),.20),rgba(0,0,0,0) 72%)}"
            ".em .m-herotype .m-eye{text-align:left}.em .m-herotype .m-eye::before{display:none}"
            ".em .m-herotype h1{font:300 50px/0.98 var(--serif);text-align:left;letter-spacing:-.005em;text-wrap:balance}"
            ".em .m-arrows h2{text-align:left;font-size:30px}.em .m-close{text-align:left}"
            ".em .m:not(.m-head):not(.m-foot):not(.m-guar):not(.m-herotype){padding-top:18px;padding-bottom:18px}"
            ".em .m-example .m-ex-ask{margin:14px 0 0}.em .m-turn h2{margin-bottom:12px}.em .m-arrows h2{margin-bottom:30px}.em .m-glass{margin-top:-60px}.em .m-arrows{padding-top:48px}") if lay.get("noon") else ""    # this email only: the NOON look, kept in the brand's serif (editor, 2026-11-10: no sans headlines): big left-aligned headline, soft light at the top
    left = (".em .m-herophoto h1,.em .m-box h2{text-align:left}.em .m-herophoto h1{margin-left:0!important;margin-right:0!important;padding:0!important}"
            ".em .m-herophoto p{text-align:left;margin-left:0!important;margin-right:0!important;padding:0!important}") if lay.get("left_heads") else ""    # this email only: headlines left-aligned, in the serif as it is (no capitals)
    if lay.get("center_lines"):    # this email only (editor, 2026-11-20, brand_a-nov-45): with align center, the small lines under pictures and on cards centred too
        left += ".em .m-cap,.em .m-glass,.em .m-glass h3,.em .m-glass p{text-align:center}"
    if lay.get("center_heads"):    # this email only (editor, 2026-11-20, brand_a-nov-44): every headline and the line under it centred, the hero's words too
        left += (".em .m-postw,.em .m-postw h1,.em .m-postw p,.em .m-turn h2,.em .m-turn p,.em .m-arrows h2,.em .m-arrows .m-close,"
                 ".em .m-box h2,.em .m-guar h2,.em .m-guar p{text-align:center!important}")
    h2_size = ".em .m-turn h2{font:300 37px/1.05 var(--serif);text-align:center}.em .m-turn h2 i{font-style:italic}" if lay.get("h2_like_hero") else ""    # this email only: a headline between pictures at the hero headline's size
    h2_i = ".em .m-turn h2 i{color:%s}" % lay["h2_i_ink"] if lay.get("h2_i_ink") else ""    # this email only: the italic word in a headline in this colour (e.g. the sage the hero's italic word has)
    mono = ""
    if lay.get("mono_bold"):    # this email only: headlines and words on the left, a silver fade behind the hero, small white buttons; the brand ornaments stay
        mono = (".em .m-btn:empty{display:none}.em .m-quote,.em .m-quote .m-eye,.em .m-quote cite,.em .m-quote blockquote{text-align:left}.em .m-routine h2{font:300 40px/1.08 var(--serif);text-align:center;margin:0 6px 20px}.em .m-ovw,.em .m-ovw h1,.em .m-ovw p{text-align:center}.em .m-guar,.em .m-guar h2,.em .m-guar p{text-align:center!important}.em{text-align:left}.em .m-btn-light{display:block;background:var(--button);color:var(--button-ink);border-radius:var(--btn-radius,0);padding:20px 10px;text-align:center;font:500 15px var(--sans);letter-spacing:.1em;text-transform:uppercase}.em .m-foot,.em .m-foot[style]{background-image:none!important;padding:26px 16px 30px!important;margin-top:0}"
                ".em .m-herophoto,.em .m-turn,.em .m-tiles,.em .m-guar,.em .m-bigquote{text-align:left}"
                ".em .m-herophoto{padding:34px 0 0;background:linear-gradient(180deg,#0A0A0A 0,#1B1C1E 55%,#0A0A0A 100%)}"
                ".em .m-herophoto h1,.em .m-bigquote blockquote,.em .m-guar h2,.em .m-tiles h2,.em .m-turn h2{font:300 40px/1.08 var(--serif);text-align:left;text-wrap:balance}"
                ".em .m-herophoto h1{margin:0 24px 14px!important;padding:0!important;font-size:44px}.em .m-herophoto p{padding:0!important;margin:0 24px 18px;text-align:left;color:var(--muted);font-size:15px}"
                ".em .m-herophoto>div{padding:0 24px 22px!important}.em .m-herophoto .m-pic{margin:0;position:relative}.em .m-herophoto .m-pic::before{content:\"\";position:absolute;left:0;right:0;top:0;height:38%;background:linear-gradient(#17181A,rgba(23,24,26,0));z-index:1}.em .m-herophoto .m-pic::after{content:\"\";position:absolute;left:0;right:0;bottom:0;height:22%;background:linear-gradient(rgba(12,16,15,0),#0C100F);z-index:1}"
                ".em .m-pic,.em .m-pic.r,.em .m-pic img,.em .m-pic.r img{border-radius:0}.em .m-tile .m-pic.r,.em .m-tile .m-pic.r img{border-radius:6px}"
                ".em .m-guar{padding:34px 24px 40px;border:0;background:linear-gradient(180deg,#0A0A0A,#17181A);margin:0}"
                ".em .m-guar h2{font-size:34px;margin:0 0 12px}.em .m-guar p{text-align:left;color:var(--muted)}"
                ".em .m-bigquote{padding:34px 24px 10px}.em .m-bigquote blockquote{font-size:30px}.em .m-bigquote .m-eye,.em .m-bigquote cite{color:var(--muted);text-align:left}"
                ".em .m-tiles{padding:30px 18px 6px}.em .m-tiles h2{font-size:26px;margin:0 6px 16px}.em .m-tile b{font-weight:600}"
                ".em .m-turn{padding:26px 24px 10px}.em .m-turn h2{font-size:34px}"
                ".em .m-ovw{text-align:left;padding:26px 24px 34px}.em .m-ovw h1{font-size:40px;line-height:1.08}.em .m-ov-top .m-ovw{text-align:center}.em .m-ov-top .m-ovw h1,.em .m-ov-top .m-ovw p{text-align:center}.em .m-ov-top .m-ovw{top:0;bottom:0}.em .m-ov-top .m-ovw .m-btn-light{position:absolute;left:24px;right:24px;bottom:30px}.em .m-ov-top .m-pic img{aspect-ratio:auto}.em .m-ov-top .m-ovw{padding:30px 24px 0;background:none}.em .m-ov-top .m-ovw p{font-size:14.5px;margin:0 0 14px}.em .m-ov-top .m-ovw p{color:var(--muted);margin:0 0 18px}.em .m-ov-bottom .m-ovw .m-btn{margin-top:6px}.em .m-rtext h3{font:300 26px/1.1 var(--serif)}.em .m-rtext p{font-size:15px}.em .m-routine h2{margin:0 0 18px}.em .m-rstep{background:linear-gradient(160deg,rgba(70,56,22,.5),rgba(18,14,7,.55))!important;border:1px solid rgba(201,169,74,.38)!important}.em .m-glass{background:linear-gradient(160deg,rgba(10,70,35,.75),rgba(6,43,20,.7))!important;border:1px solid rgba(201,169,74,.38)!important}"
                ".em .m-glass{border-radius:6px;background:#141516}.em .m-glass p{font:300 20px/1.25 var(--serif)}.em .m-glass h3{color:var(--muted)}")
    sans = (".em .m-quote blockquote,.em .m-glass p,.em .m-bigquote blockquote,.em .m-example blockquote,.em .m-close{font:400 18px/1.5 var(--sans);letter-spacing:0}"
            ".em .m-specs b{font:600 38px/1 var(--sans);letter-spacing:-.01em}.em .m-specs span{font-size:11px;letter-spacing:.14em;text-transform:uppercase}"
            ".em .m-specs div{padding:22px 4px 20px}") if lay.get("sans_body") else ""    # this email only (editor, 2026-11-17): serif only for headlines; quotes, card words and figures in the sans so they read easily
    qs = lay.get("quote_serif")    # this email only (editor, 2026-11-19): what a customer said reads in the headline serif, a highlighted voice; true, or {"size": px}
    qser = (".em .m-quote blockquote,.em .m-bigquote blockquote{font:300 %dpx/1.2 var(--serif);letter-spacing:0;text-wrap:balance}" % int((qs if isinstance(qs, dict) else {}).get("size", 28))) if qs else ""
    return root + themes + (HERE / "email.css").read_text() + extra + grain + body_px + caps + noon + left + h2_size + h2_i + mono + sans + qser


def render(spec, lk, clean=False):
    """The email as one phone-width HTML block (the preview and the page both use it)."""
    body = "".join(h for _, h in sections(spec, lk))
    th = spec.get("theme")
    return '<style>%s\n%s%s</style><div class="em%s%s">%s</div>' % (
        fonts(lk), css(lk, th), " .pk{display:none}" if clean else "", " th-%s" % th if th else "", root_classes(lk), body)


def root_classes(lk):
    lay = lk.get("layout") or {}
    return ("" if lay.get("align") != "center" else " a-center") + ("" if not lay.get("compact_buttons") else " b-compact")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Render one designed email from its spec, for the preview.")
    ap.add_argument("spec", help="<run>/design/email.json")
    ap.add_argument("--out", help="where to write the preview (default: beside the spec)")
    ap.add_argument("--clean", action="store_true", help="hide the picture-source tags")
    a = ap.parse_args()
    f = Path(a.spec)
    spec = json.loads(f.read_text())
    run_dir = f.parent.parent
    lk = L.load(spec["brand"], run_dir)
    page = ('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s</title><body style="margin:0;background:#222"><div style="width:400px;margin:0">%s</div>') % (
        E(spec.get("subject", spec.get("label", ""))), render(spec, lk, a.clean))
    out = Path(a.out) if a.out else f.with_name("preview.html")
    out.write_text(page)
    print("%s · %d sections · %d KB → %s" % (spec.get("label"), len(sections(spec, lk)), len(page) // 1024, out))


if __name__ == "__main__":
    main()
