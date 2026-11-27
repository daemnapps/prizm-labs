"""Build a designed email for Klaviyo, any brand: <run>/design/email.json in, <run>/klaviyo/ out.

Lifted from runs/email-production/brand-a/week-2026-10-12/klaviyo_build.py (the BRAND-A week of 12 Oct 2026),
with everything that was BRAND-A moved into the brand's design-system.json.

    python3 design/build.py <run folder> [<run folder> ...]

Writes <run>/klaviyo/:
    email.html   a 600px table: designed sections cut as crisp pictures (headless Chrome, the brand's own
                 fonts and colours); letters, buttons, GIFs, footer, and any section the brand keeps live
                 (`live_sections` in its look) as live HTML; every own link tagged for tracking
    assets/      every picture the email uses (uploaded to Klaviyo only on the owner's Approve)
    layout.json  where each section sits, measured once here (design/layout_file.py, LD-76 (email layout file))
    whole-email.jpg  the whole email as one picture; it and assets/ go to the run's Drive mirror
    card.json   what the Klaviyo approval page shows, with the product check (EMAIL-LINE step 4)

Nothing here talks to Klaviyo. The approval page (approve_klaviyo.py) does, on a person's click, as a DRAFT.
A rebuild keeps what a person already did on the card (the draft, the approval, the schedule).
"""
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "machine"))
import email_links  # noqa: E402  (the team's tracking standard: every own link tagged, partner links left alone)
import engine as EN  # noqa: E402
import layout_file as LF  # noqa: E402  (LD-76 (email layout file): the section map kept beside the email)
import look as L  # noqa: E402

E = html.escape
_HS = os.path.expanduser("~/Library/Caches/chrome-headless-shell/chrome-headless-shell-mac-arm64/chrome-headless-shell")   # background-only browser: no Dock icon; Chrome is the fallback
CHROME = os.environ.get("CHROME_BIN") or (_HS if os.path.exists(_HS) else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
CSS_W, SCALE = 400, 3
MAGENTA = (255, 0, 255)
LIVE = ("letter", "cta", "foot", "gif", "hero_blink")


def utm(url, label):
    """Links go in plain; email_links.tag() tags every own link once the email is whole."""
    return url


def alt_of(sec):
    """The words a reader without pictures gets: the section's text and its pictures' alt text, never the review
    page's source label (engine.py's span.pk, "Made from a real reference"), which the clean render hides."""
    sec = re.sub(r'<span class="pk\b[^"]*">.*?</span>', " ", sec, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>', r" \1 ", sec))
    return re.sub(r"\s+", " ", html.unescape(t)).strip()[:300]


def screenshot(page, shot, tmp, height):
    """Headless Chrome's picture of our own page. Chrome gets its own profile folder in tmp: inside the lab-run
    write fence it cannot make one in its default home (LD-22 (Chrome in fenced runs)). If no picture comes, Chrome's
    own sandbox could not start (it cannot inside sandbox-exec): one retry without it. Chrome renders only our own
    page from file://, and the outer write fence still holds."""
    argv = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=%d" % SCALE,
            "--window-size=%d,%d" % (CSS_W, height), "--user-data-dir=%s" % (Path(tmp) / "chrome-profile"),
            "--screenshot=%s" % shot]
    url = "file://" + str(page)
    made = lambda: shot.is_file() and shot.stat().st_size > 0
    p = subprocess.run(argv + [url], capture_output=True, timeout=240)
    if not made():
        print("headless Chrome made no picture: retrying once without its own sandbox (--no-sandbox)")
        p = subprocess.run(argv + ["--no-sandbox", url], capture_output=True, timeout=240)
    if not made():
        err = p.stderr or b""
        err = err.decode("utf-8", "replace") if isinstance(err, bytes) else str(err)
        last = [ln for ln in err.splitlines() if ln.strip()][-3:]
        raise RuntimeError("headless Chrome made no picture of %s, with and without its own sandbox; its stderr ends: %s"
                           % (page, " | ".join(last) or "(nothing)"))


def slices(spec, lk, secs, tmp):
    """Every designed section cut as its own picture, at 3x."""
    t = lk.tokens(spec.get("theme"))
    th = spec.get("theme")
    body = "".join('<div class="em sl%s%s">%s</div><div class="bar"></div>' % (" th-%s" % th if th else "", EN.root_classes(lk), h) for _, h in secs)
    page = ("<!doctype html><meta charset=utf-8><style>%s\n%s\nhtml,body{margin:0;background:#ff00ff}"
            ".sl{width:%dpx;background:%s;overflow:hidden}.bar{height:6px;background:#ff00ff}.pk{display:none!important}</style>%s") % (
        EN.fonts(lk), EN.css(lk, th), CSS_W, t["canvas"], body)
    f = Path(tmp) / "page.html"; f.write_text(page)
    shot = Path(tmp) / "shot.png"
    screenshot(f, shot, tmp, 900 * len(secs) + 400)
    im = Image.open(shot).convert("RGB")
    W, H = im.size
    px = im.load()
    W = min(W, CSS_W * SCALE)           # headless Chrome never renders narrower than 500px: the email is the left 400
    bar = [all(px[x, y] == MAGENTA for x in range(0, W, 40)) for y in range(H)]
    runs, y = [], 0
    while y < H:
        if not bar[y]:
            y0 = y
            while y < H and not bar[y]:
                y += 1
            runs.append((y0, y))
        y += 1
    if len(runs) < len(secs):
        raise SystemExit("%s: cut %d pictures for %d sections (the page was taller than the window)" % (spec["label"], len(runs), len(secs)))
    return [im.crop((0, a, W, b)) for a, b in runs[:len(secs)]]


class Live:
    """Live HTML rows in the brand's colours (email clients ignore CSS variables, so the values go inline)."""

    def __init__(self, lk, spec):
        self.t = lk.tokens(spec.get("theme"))
        f = lk["fonts"]
        self.serif = "%s,%s" % (f["display"].get("fallback", "Georgia,serif"), "serif")
        self.sans = f["body"].get("fallback", "Helvetica,Arial,sans-serif")
        self.lk, self.spec = lk, spec

    def row(self, inner, pad="0", bg=None, line_bottom=None, bg_image=None):
        ln = ";border-bottom:1px solid %s" % line_bottom if line_bottom else ""
        bi = ";background-image:%s" % bg_image if bg_image else ""    # bg_image: this email only, soft light over the row's colour (clients without gradients show the colour)
        return '<tr><td style="padding:%s%s%s" bgcolor="%s">%s</td></tr>' % (pad, ln, bi, bg or (self.lk.get("layout") or {}).get("live_bg") or self.t["canvas"], inner)

    def button(self, label, url, bg=None, ink=None, grad=None, neon=None, glow=None, big=False):
        """grad (this email only): a CSS gradient over the button; bg is the flat colour clients without gradients show.
        neon (this email only): {"line", "glow", "haze"}: a lit-sign outline and glow round the button, the label lit too."""
        g = ";background-image:%s" % grad if grad else ""
        tg = ""
        if glow:    # a soft haze round the button (clients without box-shadow show none)
            g += ";box-shadow:%s" % glow
        if neon:
            g += ";border:2px solid %s;box-shadow:0 0 8px %s,0 0 20px %s,0 0 36px %s,inset 0 0 10px %s" % (
                neon["line"], neon["glow"], neon["glow"], neon.get("haze") or neon["glow"], neon["glow"])
            tg = ";text-shadow:0 0 6px %s,0 0 14px %s" % (neon["glow"], neon["glow"])
        lay = self.lk.get("layout") or {}
        rad = lay.get("button_radius") or "999px"
        if lay.get("button_wide"):    # this email only: the button runs the full width, like the hero's
            return ('<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%%" style="width:100%%"><tr>'
                    '<td bgcolor="%s" style="border-radius:%s%s"><a class="cta-btn cta-wide" href="%s" style="display:block;padding:%s;font:600 %dpx/1 %s;'
                    'letter-spacing:.12em;color:%s;text-decoration:none;text-transform:uppercase;text-align:center%s">%s</a></td></tr></table>') % (
                bg or lay.get("button_bg") or self.t["button"], rad, g, E(url), lay.get("button_pad") or "28px 10px", int(lay.get("button_font") or 13), self.sans, ink or self.t["button_ink"], tg, E(label))
        return ('<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:0 auto"><tr>'
                '<td bgcolor="%s" style="border-radius:999px%s"><a class="cta-btn" href="%s" style="display:inline-block;padding:%s;font:600 %dpx/1 %s;'
                'letter-spacing:.12em;color:%s;text-decoration:none;text-transform:uppercase%s">%s</a></td></tr></table>') % (
            bg or lay.get("button_bg") or self.t["button"], g, E(url), "24px 20px;min-width:280px;text-align:center;white-space:nowrap" if big else "18px 44px", 17 if big else 14, self.sans, ink or self.t["button_ink"], tg, E(label))

    def blink(self, s, link, assets):
        """The hero with its neon word blinking: the lit and dim frames cut like any section, one looping GIF.
        style.neon carries the lit colours; style.neon.dim the dim ones; style.blink the frame order and ms."""
        st = s.get("style") or {}
        nn = st.get("neon") or {}
        dim = dict(nn, **(nn.get("dim") or {}))
        th = self.spec.get("theme")
        lit_h = EN.s_hero_photo(self.lk, s, th)
        dim_h = EN.s_hero_photo(self.lk, dict(s, style=dict(st, neon=dim)), th)
        with tempfile.TemporaryDirectory() as tmp:
            lit, off = slices(self.spec, self.lk, [(None, lit_h), (None, dim_h)], tmp)
        w = 600
        fit = lambda im: im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        lit, off = fit(lit), fit(off)
        base = lit.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE)
        frames = {"on": base, "off": off.quantize(palette=base, dither=Image.NONE)}
        seq = st.get("blink") or [["on", 1300], ["off", 110], ["on", 150], ["off", 110], ["on", 1500]]
        name = "hero-blink.gif"
        frames[seq[0][0]].save(assets / name, save_all=True, append_images=[frames[k] for k, _ in seq[1:]],
                               duration=[ms for _, ms in seq], loop=0, optimize=False)
        return self.row('<a href="%s"><img src="assets/%s" width="600" alt="%s" style="display:block;width:100%%;max-width:600px;border:0"></a>' % (
            E(link), name, E(alt_of(lit_h))))

    def blink_cta(self, s, link, assets):
        """The button as a blinking picture (a link all the same, label as its alt text): a solid button lit by a soft
        haze, cut as a lit and a dim frame into one looping GIF. style.button_blink = {"bg", "ink", "haze", "dim_bg",
        "dim_haze", "seq"}; style.bg is the colour behind it."""
        st = s.get("style") or {}
        bb = st["button_blink"]
        shell = ('<section class="m m-cta" style="background:%s;padding:12px 0 18px;text-align:center"><a class="m-btn" style="'
                 'display:inline-block;background:%s;color:%s;border-radius:999px;padding:12px 29px;font-weight:600;font-size:9.4px;'
                 'line-height:1;letter-spacing:.12em;text-transform:uppercase;box-shadow:%s;opacity:%s">%s</a></section>')
        on = shell % (E(st.get("bg") or self.t["canvas"]), E(bb["bg"]), E(bb["ink"]), bb["haze"], 1, E(s["label"]))
        off = shell % (E(st.get("bg") or self.t["canvas"]), E(bb.get("dim_bg") or bb["bg"]), E(bb["ink"]), bb.get("dim_haze") or "none", 1, E(s["label"]))
        fit = lambda im: im.resize((600, round(im.height * 600 / im.width)), Image.LANCZOS)
        pu = bb.get("pulse")    # {"rgb", "frames", "ms", "lo", "hi"}: the haze swells and fades smoothly instead of blinking
        if pu:
            import math
            n = pu.get("frames", 12)
            lvl = [pu.get("lo", .12) + (pu.get("hi", .6) - pu.get("lo", .12)) * (.5 - .5 * math.cos(2 * math.pi * i / n)) for i in range(n)]
            htmls = [shell % (E(st.get("bg") or self.t["canvas"]), E(bb["bg"]), E(bb["ink"]),
                              "0 0 %dpx rgba(%s,%.2f),0 0 %dpx rgba(%s,%.2f)" % (6 + 4 * a_, pu["rgb"], a_, 14 + 12 * a_, pu["rgb"], a_ * .6), "%.2f" % (pu.get("dim", .78) + (1 - pu.get("dim", .78)) * (a_ - pu.get("lo", .12)) / ((pu.get("hi", .6) - pu.get("lo", .12)) or 1)), E(s["label"]))
                     for a_ in lvl]
            with tempfile.TemporaryDirectory() as tmp:
                ims = [fit(i) for i in slices(self.spec, self.lk, [(None, h) for h in htmls], tmp)]
            stack = Image.new("RGB", (ims[0].width, ims[0].height * n))
            for i, im in enumerate(ims):
                stack.paste(im, (0, i * ims[0].height))
            qs = [im.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG) for im in ims]    # each frame its own palette: a smooth gradient
            qs[0].save(assets / "cta-blink.gif", save_all=True, append_images=qs[1:], duration=pu.get("ms", 90), loop=0, optimize=False)
            lead = '<p style="margin:0 0 %s;text-align:center;font:400 15px/1.5 %s;color:%s">%s</p>' % (
                st.get("gap") or "0", self.sans, st.get("lead_ink") or st.get("ink") or self.t["muted"], E(s["lead"])) if s.get("lead") else ""
            return self.row(lead + '<a href="%s"><img src="assets/cta-blink.gif" width="600" alt="%s" style="display:block;width:100%%;max-width:600px;border:0"></a>' % (
                E(link), E(s["label"])), st.get("pad") or "18px 0 0", st.get("bg"))
        with tempfile.TemporaryDirectory() as tmp:
            lit, dim = slices(self.spec, self.lk, [(None, on), (None, off)], tmp)
        lit, dim = fit(lit), fit(dim)
        both = Image.new("RGB", (lit.width, lit.height + dim.height)); both.paste(lit, (0, 0)); both.paste(dim, (0, lit.height))
        base = both.quantize(colors=200, method=Image.MEDIANCUT, dither=Image.NONE)    # one palette for both frames
        frames = {"on": lit.quantize(palette=base, dither=Image.NONE), "off": dim.quantize(palette=base, dither=Image.NONE)}
        seq = bb.get("seq") or [["on", 1300], ["off", 110], ["on", 150], ["off", 110], ["on", 1500]]
        frames[seq[0][0]].save(assets / "cta-blink.gif", save_all=True, append_images=[frames[k] for k, _ in seq[1:]],
                               duration=[ms for _, ms in seq], loop=0, optimize=False)
        lead = '<p style="margin:0 0 %s;text-align:center;font:400 15px/1.5 %s;color:%s">%s</p>' % (
            st.get("gap") or "0", self.sans, st.get("lead_ink") or st.get("ink") or self.t["muted"], E(s["lead"])) if s.get("lead") else ""
        return self.row(lead + '<a href="%s"><img src="assets/cta-blink.gif" width="600" alt="%s" style="display:block;width:100%%;max-width:600px;border:0"></a>' % (
            E(link), E(s["label"])), st.get("pad") or "18px 0 0", st.get("bg"))

    def section(self, s, link, assets):
        t, n = self.t, s["s"]
        if n == "letter":
            out = ""
            if s.get("greeting"):
                out += '<p style="margin:0 0 16px;font:400 26px/1.2 %s;color:%s">%s</p>' % (self.serif, t["ink"], EN._t(s["greeting"]))
            for p in s["paras"]:
                out += '<p style="margin:0 0 16px;font:400 16px/1.6 %s;color:%s">%s</p>' % (self.sans, t["ink"], EN._t(p).replace("<i>", "<em>").replace("</i>", "</em>"))
            return self.row(out, "6px 33px 10px")
        if n == "hero_blink":
            return self.blink(s, link, assets)
        if n == "cta":
            st = s.get("style") or {}
            if st.get("button_blink"):
                return self.blink_cta(s, link, assets)    # this email only: {"bg", "ink", "lead_ink", "gap" (lead to button), "pad", "button", "button_ink", "button_gradient", "button_neon", "button_glow", "button_big", "bottom_line" (1px line under the row)}
            lead = '<p style="margin:0 0 %s;text-align:center;font:400 %dpx/1.5 %s;color:%s">%s</p>' % (st.get("gap") or "16px", int(st.get("lead_size") or 15), self.sans, st.get("lead_ink") or st.get("ink") or t["muted"], E(s["lead"])) if s.get("lead") else ""    # lead_size: this email only
            if st.get("lead_big") and s.get("lead") and st["lead_big"] in s["lead"]:    # this email only: the lead in three sizes, small / the key phrase big in serif / small
                pre, _, post = s["lead"].partition(st["lead_big"])
                sm = 'margin:0;text-align:center;font:400 %dpx/1.5 %s;color:%s' % (int(st.get("lead_size") or 13), self.sans, st.get("lead_ink") or t["muted"])
                lead = ('<p style="%s">%s</p><p style="margin:8px 0 8px;text-align:center;font:300 %dpx/1.15 %s;color:%s">%s</p><p style="%s;margin-bottom:%s">%s</p>') % (
                    sm, E(pre.strip()), int(st.get("big_size") or 28), self.serif, st.get("big_ink") or t["ink"], E(st["lead_big"]), sm, st.get("gap") or "16px", E(post.strip()))
            if st.get("top_rule"):    # this email only: a short gold line above the lead
                lead = ('<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:0 auto 18px"><tr><td width="44" height="1" bgcolor="%s" '
                        'style="width:44px;height:1px;line-height:1px;font-size:1px;background:%s">&nbsp;</td></tr></table>' % (E(st["top_rule"]), E(st["top_rule"]))) + lead
            btn = self.button(s["label"], link, st.get("button"), st.get("button_ink"), st.get("button_gradient"), st.get("button_neon"), st.get("button_glow"), st.get("button_big"))
            if st.get("lead_below") and lead:    # this email only: the button first, the words under it
                lead = lead.replace('margin:0 0 %s;' % (st.get("gap") or "16px"), 'margin:%s 0 0;' % (st.get("gap") or "16px"), 1)
                return self.row(btn + lead, st.get("pad") or "8px 33px 28px", st.get("bg"), st.get("bottom_line"), st.get("bg_image"))
            return self.row(lead + btn, st.get("pad") or "8px 33px 28px", st.get("bg"), st.get("bottom_line"), st.get("bg_image"))
        if n == "product":
            # a brand that keeps card text live (its look's live_sections): picture above, words and button live.
            # The picture was never written (2026-10-18: Brand-B's Black Friday card reached Klaviyo with no product
            # in it); it is cut here from the same figure the design shows, the product filling its square.
            top = ""
            if s.get("picture"):
                import base64
                pic = dict(s["picture"])
                if "stage" in pic:
                    pic.setdefault("fill", .82); pic.setdefault("cy", .5)
                fig = EN.picture(self.lk, pic, self.spec.get("theme"), 600)
                m = re.search(r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)', fig)
                if m:
                    name = "product-%s.%s" % (re.sub(r"[^a-z0-9]+", "-", s.get("name", "card").lower()).strip("-"), "jpg" if m.group(1) == "jpeg" else m.group(1))
                    (assets / name).write_bytes(base64.b64decode(m.group(2)))
                    top = '<a href="%s"><img src="assets/%s" width="300" alt="%s" style="display:block;margin:0 auto 16px;width:300px;max-width:100%%;border-radius:16px;border:0"></a>' % (
                        E(link), name, E((s.get("picture") or {}).get("alt", s.get("name", ""))))
            w = ' <s style="color:%s;font-size:15px">%s</s>' % (t["dim"], E(s["was"])) if s.get("was") else ""
            return self.row(top + '<p style="margin:0 0 4px;font:400 22px/1.2 %s;color:%s">%s</p><p style="margin:0 0 10px;font:400 15px/1.5 %s;color:%s">%s</p>'
                            '<p style="margin:0 0 14px;font:400 22px %s;color:%s">%s%s</p>' % (
                                self.serif, t["ink"], E(s["name"]), self.sans, t["muted"], E(s["line"]), self.serif, t["ink"], E(s["price"]), w)
                            + self.button(s["cta"], link), "8px 33px 26px")
        if n == "gif":
            p = self.lk.path(s["gif"]); name = p.name
            (assets / name).write_bytes(p.read_bytes())
            note = ' · <a href="%s" style="color:%s">%s</a>' % (E(s.get("link", "")), t["muted"], E(s["note"])) if s.get("note") else ""
            return self.row('<a href="%s"><img src="assets/%s" width="330" alt="%s" style="display:block;margin:0 auto;width:330px;max-width:100%%;border-radius:16px"></a>'
                            '<p style="margin:10px 0 0;text-align:center;font:400 13px/1.4 %s;color:%s"><b style="color:%s;font-weight:600">%s</b>%s</p>' % (
                                E(s.get("link", "")), name, E(s["caption"]), self.sans, t["muted"], t["ink"], E(s["caption"]), note), "22px 33px 22px")
        if n == "foot":
            f = self.lk.get("footer") or {}
            fst = s.get("style") or {}    # this email only: {"bg", "ink"} (colours of the footer row)
            fink = fst.get("ink") or t["muted"]
            links = " &nbsp;·&nbsp; ".join('<a href="%s" style="color:%s">%s</a>' % (E(utm(u, self.spec["label"])), fink, E(a)) for a, u in f.get("links", []))
            out = self.row('<p class="ft" style="margin:0;text-align:center;font:400 12px/1.8 %s;color:%s">%s<br>%s<br>'
                           '{%% unsubscribe "Unsubscribe" %%} &nbsp;·&nbsp; {%% manage_preferences "Preferences" %%}<br>{{ organization.name }} · {{ organization.full_address }}</p>'
                           % (self.sans, fink, links, E(f.get("line", ""))), "28px 33px 18px", fst.get("bg"))
            o = None if (s.get("style") or {}).get("no_ornament") else self.lk.ornament("foot", self.spec.get("theme"))    # no_ornament: this email only
            if o:
                im = Image.open(self.lk.path(o)).convert("RGB")
                crop = o.get("crop") if isinstance(o, dict) else None
                if crop:
                    im = im.crop(tuple(int(c * d) for c, d in zip(crop, (im.width, im.height, im.width, im.height))))
                im.resize((1200, int(1200 * im.height / im.width))).save(assets / "foot.jpg", quality=84)
                out += self.row('<img src="assets/foot.jpg" width="600" alt="" style="display:block;width:100%;max-width:600px">')
            return out
        raise ValueError("no live form for section %r" % n)


def run_json(spec):
    """The copy run's own record beside this layout (its assignment names the occasion), or {}."""
    try:
        return json.loads((Path(spec.get("_run", "")) / "run.json").read_text())
    except (OSError, ValueError, TypeError):
        return {}


def _guarantee_rows(brand):
    """The brand's offers/guarantees.json rows, {} when it has none."""
    try:
        return json.loads((Path(L.brandpath.brand_root(brand, L.REPO / "brands")) / "offers" / "guarantees.json")
                          .read_text()).get("guarantees") or {}
    except (OSError, ValueError):
        return {}


def guarantees(brand, look_words):
    """[(name, verbatim)] an email may quote: the look's guarantee, then every surface wording in the brand's
    offers/guarantees.json. A brand can sign one wording per surface (a device, its formulations); an email quotes the
    one for what it sells, word for word, so any signed one passes and the check names it (the team, 2026-10-22: a CRUSH
    email quoting the formulations wording was held for not matching the device's)."""
    rows = _guarantee_rows(brand)
    return [("the look's", look_words)] + [(k, r["verbatim"]) for k, r in rows.items() if isinstance(r, dict) and r.get("verbatim")]


def term_problems(terms, text):
    """What a paraphrase of a guarantee gets wrong against its signed terms: {"all_of": [[any of these], ...] every group
    said at least once, "none_of": [never these]}, matched without case. [] when it keeps every term."""
    t = text.lower()
    out = ["does not say %s" % " / ".join('"%s"' % w for w in grp) for grp in terms.get("all_of", [])
           if not any(w.lower() in t for w in grp)]
    return out + ['says "%s"' % w for w in terms.get("none_of", []) if w.lower() in t]


def guarantee_hit(brand, look_words, words, text=""):
    """(name, how) of the signed guarantee the email keeps, or (None, why not). Word for word anywhere in the email,
    the first letter's case free to follow its sentence ("In place of a date sixty days to ask…", brand-b-nov-08);
    or, for a guarantee whose row carries "terms", in other words inside the guarantee section itself (`text`) as long
    as it keeps every term (the team, 2026-10-27: Brand-B's email guarantee may be paraphrased; BRAND-A's stay word for
    word until the owner says)."""
    for k, v in guarantees(brand, look_words):
        if v and (v in words or (v[:1].lower() + v[1:]) in words):
            return k, "word for word"
    why = []
    for k, r in _guarantee_rows(brand).items():
        if isinstance(r, dict) and r.get("terms") and text:
            probs = term_problems(r["terms"], text)
            if not probs:
                return k, "by its terms"
            why.append("%s: %s" % (k, "; ".join(probs)))
    return None, "; ".join(why)


def picture_alts(spec):
    """Every picture's alt text in the email, with the kind of section it sits in ("poster", "photo_card", ...)."""
    out = []
    def walk(x, sec):
        if isinstance(x, dict):
            if x.get("alt") and any(k in x for k in ("photo", "proof", "stage", "glow", "gif", "todo")):
                out.append((sec, x["alt"]))
            for v in x.values():
                walk(v, sec)
        elif isinstance(x, list):
            for v in x:
                walk(v, sec)
    for s in spec.get("sections", []):
        walk(s, str(s.get("s") or "").replace("_", " "))
    return out


def product_check(spec, lk, words):
    """EMAIL-LINE step 4: every price, refused word and box fact in what this email shows, against the brand's look file."""
    ck = lk.get("check") or {}
    out = []
    prices = dict(ck.get("prices", {}))
    if not prices:                           # no price list in the look file: the offer bank's live prices are the list
        import gaps as G
        for row in G.offer_bank(spec["brand"]).values():
            for k in ("price", "funnel"):
                if row.get(k):
                    prices.setdefault(row[k], "%s · offer bank" % row["name"])
                    prices.setdefault(row[k].replace(".00", ""), "%s · offer bank" % row["name"])
        rj = run_json(spec)
        sale = G.sale_offer(spec["brand"], ((rj.get("assignment") or {}).get("occasion")) or "")
        for p in (sale or {}).get("prices", []):
            prices.setdefault(p, "%s · offer bank" % sale["name"])
    for p in sorted(set(re.findall(r"\$\d+(?:\.\d\d)?", words))):
        out.append(("ok" if p in prices else "PROBLEM", "price %s · %s" % (p, prices.get(p, "not in the brand's price list"))))
    for n in ck.get("never_words", []):
        if re.search(r"(?<!\w)%s(?!\w)" % re.escape(n), words, re.I):
            out.append(("PROBLEM", "says \"%s\" (the brand's never list)" % n))
    g = (lk.get("guarantee") or {}).get("words")
    if g and any(s["s"] == "guarantee" for s in spec["sections"]):
        text = " ".join(str(v) for x in spec["sections"] if x["s"] == "guarantee" for v in x.values() if isinstance(v, str) and v != "guarantee")
        name, how = guarantee_hit(spec["brand"], g, words, text)
        out.append(("ok", "guarantee %s (%s)" % (how, name)) if name else
                   ("PROBLEM", "guarantee not word for word" + (" nor by its terms (%s)" % how if how else "")))
    for x in ck.get("not_in_box", []):
        pat = r"\b%s\b" % re.escape(x["word"])
        pics = [(sec, a) for sec, a in picture_alts(spec) if re.search(pat, a, re.I)]
        for sec, a in pics:                  # a picture shows it: say which one and why, so the designer sees it at once
            out.append(("PROBLEM", "the %s picture shows the %s (\"%s\"): %s. Use a picture without it." % (sec, x["word"], a[:90], x["why"]), "picture"))
        if not pics and re.search(pat, words, re.I):
            out.append(("PROBLEM", "mentions \"%s\": %s" % (x["word"], x["why"])))
    if "in the box" in words.lower() and ck.get("in_the_box"):
        out.append(("ok", "in the box: %s (product file)" % ck["in_the_box"]))
    for m in sorted(set(re.findall(r"\[UNFILLED[^\]]*\]", words + json.dumps(spec["sections"], ensure_ascii=False)))):
        out.append(("PROBLEM", "an unfilled gap is still in the email: %s (run design/gaps.py --fill)" % m))
    for f in ck.get("flags", []):
        out.append(("PROBLEM", f))
    todo = [s for s in json.dumps(spec["sections"]).split('"todo"')[1:]]
    if todo:
        out.append(("PROBLEM", "%d picture slot(s) still to fill" % len(todo), "picture"))
    # a row "about" the picture is the designer's to fix; every other row is the words or the product (check.holds)
    return [dict({"result": r[0], "detail": r[1]}, **({"about": r[2]} if len(r) > 2 else {}))
            for r in (out or [("ok", "no prices or product claims")])]


def build(run_dir):
    run_dir = Path(run_dir).resolve()
    spec = json.loads((run_dir / "design" / "email.json").read_text()); spec["_run"] = str(run_dir)
    lk = L.load(spec["brand"], run_dir)
    spec = EN.house(spec, lk)            # LD-101 (Brand-B house look): the live rows take the house styles too
    label = spec["label"]
    link = utm(spec.get("link", ""), label)
    live = set(LIVE) | set(lk.get("live_sections", []))
    secs = EN.sections(spec, lk)
    # a live section is rendered from the spec, so walk the spec and the rendered sections together
    order = []
    for s in spec["sections"]:
        n = len(EN.sections({"sections": [s], "theme": spec.get("theme"), "label": label}, lk))
        order.append((s, n))
    out = run_dir / "klaviyo"
    assets = out / "assets"; assets.mkdir(parents=True, exist_ok=True)
    for f in assets.glob("*"):
        f.unlink()
    pics = [h for (s, n), chunk in zip(order, _chunks(secs, [n for _, n in order])) if s["s"] not in live for _, h in chunk]
    with tempfile.TemporaryDirectory() as tmp:
        cut = slices(spec, lk, [(None, h) for h in pics], tmp) if pics else []
    lv = Live(lk, spec)
    rows, n, ci, words = [], 0, 0, []
    # every row carries the layout section it came from (data-sec), so a review page can adjust one section at a time
    tag = lambda html, i: html.replace("<tr>", '<tr data-sec="%d">' % i)
    for si, ((s, k), chunk) in enumerate(zip(order, _chunks(secs, [k for _, k in order]))):
        words += [alt_of(h) for _, h in chunk]
        if s["s"] in live:
            rows.append(tag(lv.section(s, link, assets), si))
            continue
        for _, h in chunk:
            n += 1
            name = "s%02d.jpg" % n
            cut[ci].save(assets / name, quality=86, optimize=True, progressive=True); ci += 1
            href = utm((lk.get("logo") or {}).get("link", ""), label) if s["s"] in ("band", "mark") else link
            rows.append(tag(lv.row('<a href="%s"><img src="assets/%s" width="600" alt="%s" style="display:block;width:100%%;max-width:600px;border:0"></a>' % (
                E(href), name, E(alt_of(h)))), si))
    t = lv.t
    doc = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>%s</title><style>body{margin:0;padding:0;background:%s}a{color:%s}.ft a{color:inherit!important}@media (max-width:620px){.wrap{width:100%%!important}.cta-btn{padding:15px 22px!important;font-size:13px!important;min-width:0!important;letter-spacing:.1em!important}.cta-wide{padding:4.3vw 10px!important;font-size:3.2vw!important;letter-spacing:.12em!important}}</style></head>'
           '<body style="margin:0;padding:0;background:%s"><div style="display:none;max-height:0;overflow:hidden">%s</div>'
           '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" bgcolor="%s"><tr><td align="center">'
           '<table role="presentation" class="wrap" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px">%s</table>'
           '</td></tr></table></body></html>') % (E(spec["subject"]), t["canvas"], t["ink"], t["canvas"], E(spec.get("preview", "")), t["canvas"], "".join(rows))
    doc = email_links.tag(doc, spec["brand"], label, term=email_links.term_for(spec.get("segments", [])))
    left = email_links.problems(doc, spec["brand"])
    (out / "email.html").write_text(doc)
    layout_and_mirror(spec["brand"], run_dir)
    links =sorted({html.unescape(h) for h in re.findall(r'href="([^"]+)"', doc) if h.startswith("http")})
    checks = product_check(spec, lk, html.unescape(" ".join(words)))
    if left:
        checks.append({"result": "PROBLEM", "detail": "own links missing the tracking tags: %s" % ", ".join(left)})
    snd = lk.get("send") or {}
    card = dict(brand=spec["brand"], label=label, date=spec["date"], send_local=snd.get("local"), recipient_time_zone=snd.get("recipient_time_zone"),
                kind=spec["kind"], format=spec.get("format"), theme=spec.get("theme"), concept=spec.get("concept"), culture=spec.get("culture"),
                audience=audience_of(spec), segments=[s for s in spec.get("segments") or [] if isinstance(s, str) and s],
                subjects=[{"subject": spec["subject"], "preview": spec.get("preview", "")}], links=links, pictures=n,
                product_check=checks, flags=["Product check: " + c["detail"] for c in checks if c["result"] != "ok"],
                notes=spec.get("notes", []), status="draft", built_from="tools/email-production/design/build.py")
    if spec.get("from_label"):       # the email's own from-name (a founder's letter); else the brand's, as before
        card["from_label"] = spec["from_label"]
    old = json.loads((out / "card.json").read_text()) if (out / "card.json").is_file() else {}
    for k in ("klaviyo", "approval", "scheduled", "sent_back", "status", "segments", "audience", "final_check", "sections_ok", "eve_done", "links_confirmed", "eve_due"):
        if k in old:
            card[k] = old[k]
    if not [s for s in card.get("segments") or [] if isinstance(s, str) and s]:
        card["flags"].append("Segment unknown: the send names no segment — set it before approving")
    (out / "card.json").write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    kb = sum(f.stat().st_size for f in assets.iterdir()) // 1024
    print("%-30s %2d pictures, %d links, %d KB%s" % (label, n, len(links), kb, "  FLAG" if card["flags"] else ""))
    return card


def layout_and_mirror(brand, run_dir):
    """LD-76 (email layout file), right after email.html is written: its section map (klaviyo/layout.json), the
    whole-email picture once, then klaviyo/assets/* and that picture onto the run's Drive mirror. Each failure is
    printed by name and none of them fails the build."""
    lay = LF.write_safe(run_dir)
    if lay:
        try:
            LF.shot(run_dir, lay["height"])
        except Exception as e:  # noqa: BLE001 -- named below, never silent
            print("whole-email picture: NOT made — %s: %s" % (type(e).__name__, e))
    done = LF.mirror_build(brand, run_dir)
    # PF-21 (pictures reach every Mac): the run:media pictures email.json names, so another Mac can rebuild it
    m = LF.mirror_media(brand, run_dir)
    if m["put"]:
        print("   drive: media/ %d picture%s put" % (len(m["put"]), "" if len(m["put"]) == 1 else "s"))
    if m["error"]:
        print("   drive: media/ NOT mirrored — %s" % m["error"])
    if m["not_here"]:
        print("   drive: media/ not on this Mac and not in its Drive ledger: %s" % ", ".join(m["not_here"]))
    return done


def audience_of(spec):
    """The card's audience: the spec's own when it names one, else its segment names joined — a non-string (an old
    spec's [null]) is skipped, never a crash (LD-67 (design keeps segment))."""
    if "audience" in spec:
        return spec["audience"]
    return ", ".join(s for s in spec.get("segments") or [] if isinstance(s, str) and s)


def _chunks(seq, sizes):
    i = 0
    for k in sizes:
        yield seq[i:i + k]
        i += k


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for d in sys.argv[1:]:
        build(d)
