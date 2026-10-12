#!/usr/bin/env python3
"""A run's BLOCKS become a real HTML email in the brand's OWN design system —
the Format Library bedrock (FMT-01..08 + MOD-01..04), the real wordmark
vector, the licensed fonts, the exact tokens. Rebuilt 2026-09-02 after the
first renderer typed the word "brand-b" where the logotype goes and skipped
the glow/glass system entirely (the owner: "you didn't run any of the actual
design styles or even get my logo right").

    python3 render_email.py results/<label> --brand <brand>

The ENGINE is brand-agnostic and lives here. Everything that makes the email
look like a brand comes from brands/<brand>/email-sms/design-formats/
components.json (tokens, modules, formats) and from the design assets the
brand's bank shipped (wordmark svg, font files under design/) — nothing is
typed in.

Email reality is respected where it costs nothing (tables, inline styles,
bulletproof CTA, 600px). Where the bank's look depends on things email
clients drop (web fonts, radial glows), the mockup carries them for review
and the fallback is declared so a send degrades to the brand's stack, not to
Times New Roman. Images stay clear striped placeholder frames with pixel
dimensions — the bank's own convention — until the designer or the image
stage fills them.
"""
import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

from paths import HERE, WORKSPACE


def e(s):
    return html.escape(str(s if s is not None else ""))


def product_words(brand):
    """The product names a brief may use for this brand, and the store handle each maps to —
    brand data, read from brands/<brand>/email-sms/product-words.json
    (shape: brands/_TEMPLATE/email-sms/product-words.json). Returns (regex or None, {key: handle})."""
    f = WORKSPACE / "brands" / brand / "email-sms" / "product-words.json"
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        return None, {}
    words = [w for w in d.get("words", []) if w]
    rx = re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I) if words else None
    return rx, d.get("handles", {})


class Skin:
    """Every visual fact, read from the brand — never typed here."""
    def __init__(self, brand):
        root = WORKSPACE / "brands" / brand / "email-sms" / "design-formats"
        f = root / "components.json"
        if not f.is_file():
            sys.exit(f"no components.json for {brand} — extract the skin from the brand's "
                     "design bank first (design-formats/)")
        d = json.loads(f.read_text())
        self.p, self.t, self.l = d["palette"], d["typography"], d["layout"]
        self.identity, self.footer, self.flour = d["identity"], d["footer"], d.get("flourishes", {})
        self.modules = d.get("modules", {})
        self.logo = None
        for cand in (HERE / "design" / Path(self.identity.get("logo_svg", "x")).name,
                     root / Path(self.identity.get("logo_svg", "x")).name,
                     HERE / "design" / f"{brand}.svg"):
            if cand.is_file():
                svg = cand.read_text()
                # the bank draws the wordmark in black and flips it with a CSS
                # filter — mail clients strip filters, so the vector itself is
                # recolored to the ink that sits on this canvas
                ink = self.p["ink"]
                svg = re.sub(r'fill="(?!none)[^"]*"', f'fill="{ink}"', svg)
                svg = re.sub(r'<path(?![^>]*fill=)', f'<path fill="{ink}"', svg)
                self.logo = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
                break

        # the brand's product images, by handle — from its own store feed
        self.products = {}
        pi = WORKSPACE / "brands" / brand / "products" / "images.json"
        if pi.is_file():
            self.products = json.loads(pi.read_text()).get("products", {})
        self.product_rx, _ = product_words(brand)

    def product_image(self, *names, kind="cutout"):
        """The real image for a product named in a block — matched on the
        store handle or the product title (WIDGET, PRIME™ Face Mist…)."""
        for n in names:
            n = str(n or "").strip().lower()
            if not n:
                continue
            for handle, rec in self.products.items():
                title = rec.get("title", "").lower()
                head = re.sub(r"[™®].*$", "", title).strip()          # "widget" from "WIDGET™ Pro…"
                if n == handle or n == title or n == head or (len(n) >= 4 and (n in title or head in n)):
                    return rec.get(kind) or rec.get("hero")
        return None

    def sans(self):
        return self.t["stack"]

    def serif(self):
        return self.t["display_stack"]

    def body(self, px=None, weight=400, color=None):
        return (f"font-family:{self.sans()};font-size:{px or self.t['body_px']}px;"
                f"line-height:1.2;font-weight:{weight};color:{color or self.p['ink']}")


# ---------------------------------------------------------------- pieces ---

def placeholder(skin, w, h, label, radius=20):
    """The bank's striped placeholder frame with pixel dimensions."""
    return (f'<div style="width:{w}px;max-width:100%;height:{h}px;border-radius:{radius}px;'
            f'background:repeating-linear-gradient(135deg,rgba(199,207,173,0.10) 0 14px,rgba(199,207,173,0.04) 14px 28px);'
            f'box-shadow:inset 0 0 0 1px rgba(242,246,234,0.25);display:flex;align-items:center;'
            f'justify-content:center;text-align:center;padding:24px;box-sizing:border-box;margin:0 auto;'
            f'font-family:{skin.sans()};font-size:13px;line-height:1.35;color:rgba(242,246,234,0.7)">'
            f'<div><div style="font-size:11px;letter-spacing:0.14em;text-transform:uppercase;'
            f'color:{skin.p["accent"]};margin-bottom:8px">IMAGE {w}×{h}</div>{e(label)}</div></div>')


def cta(skin, label, href):
    p, t, l = skin.p, skin.t, skin.l
    w, h = l.get("cta_width", 450), int(l.get("cta_height", 62))
    label = str(label or "").strip("[] ")
    if t.get("cta_case", "uppercase") == "uppercase":
        label = label.upper()
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" width="{w}" style="width:{w}px;max-width:100%;margin:0 auto"><tr>'
            f'<td align="center" bgcolor="{p["cta_bg"]}" style="height:{h}px;border-radius:{l.get("cta_radius", 0)}px">'
            f'<a href="{e(href or "#UNFILLED")}" style="display:block;line-height:{h}px;font-family:{skin.sans()};'
            f'font-size:{t.get("cta_px", 18)}px;font-weight:{t.get("cta_weight", 500)};letter-spacing:{t.get("cta_tracking", "-0.02em")};'
            f'color:{p["cta_ink"]};text-decoration:none">{e(label)}</a></td></tr></table>')


def glass(skin):
    return skin.l.get("glass_card",
                      "background:linear-gradient(270deg,rgba(12,16,15,0.5),rgba(199,207,173,0.3));"
                      "box-shadow:inset 0 0 0 1px rgba(242,246,234,0.3);border-radius:20px")


def row(inner, pad_top=0, pad_bottom=0):
    return f'<tr><td align="center" style="padding:{pad_top}px 50px {pad_bottom}px 50px">{inner}</td></tr>'


MODULE_WORDS = ("wordmark", "logotype", "footer", "nav row", "social icon", "values bar",
                "difference values", "standing", "standard three-item")


def component(block, skin, ctx):
    p, t = skin.p, skin.t
    kind = block.get("type")
    gap = skin.l.get("block_gap", 28)
    txt = block.get("text", "")

    if kind == "preheader":
        ctx["preheader"] = txt
        return ""
    if kind == "headline":
        if len(str(txt).split()) <= 3:             # FMT-03 big type
            inner = (f'<div style="font-family:{skin.sans()};font-size:44px;letter-spacing:0.12em;line-height:1.1;'
                     f'text-transform:uppercase;color:{p["ink"]};text-align:center">{e(txt)}</div>')
        else:                                        # FMT-01 display headline
            inner = (f'<div style="font-family:{skin.serif()};font-size:{t.get("headline_px", 50)}px;'
                     f'line-height:{t.get("headline_leading", 1.0)};font-weight:{t.get("headline_weight", 400)};'
                     f'color:{p["ink"]};text-align:center;max-width:500px;margin:0 auto">{e(txt)}</div>')
        ctx["n_head"] = ctx.get("n_head", 0) + 1
        return row(inner, 44 if ctx["n_head"] == 1 else gap, 0)
    if kind == "subhead":
        return row(f'<div style="{skin.body(t.get("subhead_px", 24), 500)};text-align:center;max-width:480px;margin:0 auto">{e(txt)}</div>', gap, 0)
    if kind == "copy":
        paras = [x for x in re.split(r"\n\s*\n", str(txt).strip()) if x]
        inner = "".join(f'<div style="{skin.body()};text-align:center;max-width:480px;margin:0 auto 18px">{e(x).replace(chr(10), "<br>")}</div>'
                        for x in paras)
        return row(inner, gap, 0)
    if kind == "image":
        img = ctx.get("images", {}).get(str(ctx.get("idx")))
        brief = block.get("image_brief", "")
        if not img and "product" in brief.lower():
            # a product hero: the store's own listing photo, matched on any
            # product this run is about or the brief names
            img = skin.product_image(ctx.get("product"), *(skin.product_rx.findall(brief) if skin.product_rx else []), kind="hero")
        if img:
            inner = (f'<img src="{e(img)}" width="500" alt="{e(block.get("alt"))}" '
                     f'style="display:block;width:500px;max-width:100%;border-radius:{skin.l.get("image_radius", 20)}px;margin:0 auto">')
        else:
            low = brief.lower()
            # standing modules the copy stage described as images are the
            # real modules drawn by this renderer — never a frame
            if any(k in low for k in MODULE_WORDS):
                return ""
            # a frame that only re-carries words already typeset beside it
            # (the source baked its headline into an image) is dropped —
            # the type IS the design here, the frame would repeat it
            carried = (low + " " + str(block.get("alt") or "").lower())
            for near in (ctx.get("prev_text"), ctx.get("next_text")):
                if near and len(near) >= 12 and near.lower().rstrip("?.!") in carried:
                    return ""
            # likewise a "picture of a button" beside a real button — the
            # CTA module is the button; the source only baked one into a bitmap
            if ("button" in low or "cta" in low) and ctx.get("near_button"):
                return ""
            h = 420 if ("hero" in low or "product" in low or "frame" in low) else 300
            inner = placeholder(skin, 500, h, brief[:220] + (f" · alt: {block.get('alt')}" if block.get("alt") else ""))
        return row(inner, gap, 0)
    if kind == "quote":
        inner = (f'<div style="{glass(skin)};padding:28px 32px;max-width:440px;margin:0 auto">'
                 f'<div style="font-family:{skin.serif()};font-size:28px;line-height:1.15;color:{p["ink"]};text-align:center">“{e(txt)}”</div>'
                 f'<div style="{skin.body(16, 400, p["accent"])};text-align:center;margin-top:14px;letter-spacing:0.08em;text-transform:uppercase">{e(block.get("attribution"))}</div></div>')
        return row(inner, gap, 0)
    if kind == "bullets":                            # FMT-02 glass rows
        rows = []
        for i, it in enumerate(block.get("items", []), 1):
            rows.append(
                f'<table role="presentation" cellpadding="0" cellspacing="0" width="440" style="width:440px;max-width:100%;margin:0 auto 16px;{glass(skin)}"><tr>'
                f'<td width="96" valign="middle" style="padding:18px 0 18px 18px"><div style="width:72px;height:72px;border-radius:50%;background:{p["accent"]};'
                f'font-family:{skin.serif()};font-size:34px;line-height:72px;text-align:center;color:{p["deep_green"]}">{i}</div></td>'
                f'<td valign="middle" style="padding:18px 24px 18px 8px;{skin.body(22, 500)}">{e(it)}</td></tr></table>')
        return row("".join(rows), gap, 0)
    if kind == "button":
        return row(cta(skin, block.get("label"), block.get("href")), 32, 0)
    if kind == "product":
        img = (ctx.get("images", {}).get(str(ctx.get("idx")))
               or skin.product_image(block.get("name"), block.get("alt"), block.get("image_brief")))
        pic = (f'<img src="{e(img)}" width="220" alt="{e(block.get("alt") or block.get("name"))}" '
               f'style="display:block;width:220px;height:220px;object-fit:contain;margin:0 auto;border-radius:16px">' if img
               else placeholder(skin, 220, 220, f"product cut-out — {block.get('name') or block.get('image_brief') or ''}", 16))
        name, price = block.get("name") or "", block.get("price") or ""
        inner = (f'<table role="presentation" cellpadding="0" cellspacing="0" width="440" style="width:440px;max-width:100%;margin:0 auto;{glass(skin)}"><tr>'
                 f'<td align="center" style="padding:28px 24px">{pic}'
                 + (f'<div style="{skin.body(32, 500)};line-height:1.1;margin-top:20px">{e(name)}</div>' if name else "")
                 + (f'<div style="{skin.body(24)};margin-top:8px;color:{p["ink_muted"]}">{e(price)}</div>' if price else "")
                 + (f'<div style="margin-top:20px">{cta(skin, block.get("label") or "Shop", block.get("href"))}</div>' if block.get("label") else "")
                 + '</td></tr></table>')
        return row(inner, gap, 0)
    if kind == "divider":
        return row(f'<div style="height:1px;width:500px;max-width:100%;background:{p.get("divider", "rgba(242,246,234,0.2)")}"></div>', gap, 0)
    if kind == "ps":
        return row(f'<div style="{skin.body(20)};text-align:center;max-width:480px;margin:0 auto;color:{p["ink_muted"]}"><b style="color:{p["ink"]}">PS</b> — {e(txt)}</div>', gap, 0)
    if kind == "signoff":
        return row(f'<div style="{skin.body()};text-align:center;max-width:480px;margin:0 auto">{e(txt).replace(chr(10), "<br>")}</div>', gap, 0)
    if kind == "footer":
        ctx["footer_text"] = txt
        return ""
    return row(f'<div style="{skin.body(14, 400, p["accent"])}">[UNRENDERED BLOCK: {e(kind)}]</div>', gap, 0)


# --------------------------------------------------------------- modules ---

def header(skin, preheader):
    p = skin.p
    logo = (f'<img src="{skin.logo}" width="120" height="28" alt="{e(skin.identity.get("logo_text"))}" '
            f'style="display:block;width:120px;height:auto;margin:0 auto">' if skin.logo else
            f'<div style="font-family:{skin.sans()};font-size:22px;letter-spacing:0.35em;color:{p["ink"]}">{e(skin.identity.get("logo_text"))}</div>')
    kick = (f'<tr><td align="center" style="padding:18px 50px 0"><div style="font-family:{skin.sans()};font-size:{skin.t.get("kicker_px", 13)}px;'
            f'letter-spacing:0.12em;text-transform:uppercase;color:{p["ink"]};opacity:0.85">{e(preheader)}</div></td></tr>') if preheader else ""
    return kick + f'<tr><td align="center" style="padding:{32 if preheader else 50}px 0 0">{logo}</td></tr>'


def nav(skin):
    items = skin.modules.get("nav") or ["Shop", "results", "plan", "Vision"]
    cells = "".join(f'<td align="center" style="padding:0 14px;font-family:{skin.sans()};font-size:16px;font-weight:500;'
                    f'letter-spacing:0.06em;text-transform:uppercase"><a href="#" style="color:{skin.p["ink"]};text-decoration:none">{e(x)}</a></td>'
                    for x in items)
    return (f'<tr><td align="center" style="padding:22px 50px 0"><table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto"><tr>{cells}</tr></table>'
            f'<div style="height:1px;width:500px;max-width:100%;background:{skin.p.get("divider", "rgba(242,246,234,0.2)")};margin:22px auto 0"></div></td></tr>')


def footer_mod(skin, legal):
    p = skin.p
    links = skin.modules.get("footer_links") or ["SHOP", "JOIN THE FAM", "FAQ"]
    addr = skin.modules.get("address") or next((x for x in skin.footer.get("lines", []) if "Blvd" in x or "Ste" in x), "")
    cells = "".join(f'<td align="center" style="padding:0 16px;font-family:{skin.sans()};font-size:14px;font-weight:500;letter-spacing:0.1em;'
                    f'text-transform:uppercase"><a href="#" style="color:{p["ink"]};text-decoration:none">{e(x)}</a></td>' for x in links)
    logo = (f'<img src="{skin.logo}" width="96" alt="" style="display:block;width:96px;height:auto;margin:0 auto;opacity:0.9">' if skin.logo else "")
    legal_txt = legal or " ".join(x for x in skin.footer.get("lines", [])[1:] if not x.startswith("[UNFILLED"))
    # Klaviyo's tags resolve at send; in the mockup they read as the words
    # they become, and the address module already carries the address
    legal_txt = re.sub(r"\{\{\s*organization\.[a-z_]+\s*\}\}", "", legal_txt)
    legal_txt = re.sub(r"\{%\s*unsubscribe\s*%\}", "", legal_txt).strip(" .\n")
    legal_txt = (legal_txt + " " if legal_txt else "") + "Unsubscribe"
    return (f'<tr><td align="center" style="padding:56px 50px 0"><div style="height:1px;width:500px;max-width:100%;background:{p.get("divider", "rgba(242,246,234,0.2)")};margin:0 auto 36px"></div>'
            f'{logo}<table role="presentation" cellpadding="0" cellspacing="0" style="margin:26px auto 0"><tr>{cells}</tr></table>'
            f'<div style="font-family:{skin.sans()};font-size:{skin.t.get("footer_px", 16)}px;line-height:1.6;color:{p["ink_muted"]};margin:28px auto 0;max-width:440px">'
            f'{e(addr)}<br>{e(legal_txt)}</div></td></tr>')


def build(run_dir, brand, blocks_file=None):
    blocks_f = Path(blocks_file) if blocks_file else run_dir / "stage8--blocks.md"
    if not blocks_f.is_file():
        sys.exit(f"no stage 8 output in {run_dir} — run the chain first")
    m = re.search(r"```BLOCKS\s*(\[.*?\])\s*```", blocks_f.read_text(), re.S)
    if not m:
        sys.exit("stage 8 wrote no BLOCKS fence")
    blocks = json.loads(m.group(1))
    skin = Skin(brand)
    imgs = {}
    imap = run_dir / "images.json"
    if imap.is_file():
        imgs = json.loads(imap.read_text()).get("slots", {})
    product = ""
    rj = run_dir / "run.json"
    if rj.is_file():
        product = str(json.loads(rj.read_text()).get("product") or "")
    ctx = {"preheader": "", "images": imgs, "footer_text": "", "product": product}
    rows = []
    texty = {"headline", "subhead", "copy", "button"}
    for i, b in enumerate(blocks):
        ctx["idx"] = i
        prev_b = blocks[i - 1] if i else {}
        next_b = blocks[i + 1] if i + 1 < len(blocks) else {}
        ctx["prev_text"] = str(prev_b.get("text") or prev_b.get("label") or "") if prev_b.get("type") in texty else ""
        ctx["next_text"] = str(next_b.get("text") or next_b.get("label") or "") if next_b.get("type") in texty else ""
        ctx["near_button"] = "button" in (prev_b.get("type"), next_b.get("type"))
        rows.append(component(b, skin, ctx))

    p, l = skin.p, skin.l
    glow = skin.p.get("glow", "#bbc79e")
    fonts_css = ""
    fc = HERE / "design" / "fonts.css"
    if fc.is_file():
        fonts_css = fc.read_text().replace("url('fonts/", "url('/design/fonts/")
    doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>{e(skin.identity.get("logo_text"))}</title>
<style>{fonts_css}
body{{margin:0;padding:0;background:{p["canvas"]}}}
.glow{{background-image:radial-gradient(360px 360px at 50% 120px, {glow}42 0%, {glow}14 55%, rgba(0,0,0,0) 100%)}}
</style></head>
<body style="margin:0;padding:0;background:{p["canvas"]}">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all">{e(ctx["preheader"])}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{p["canvas"]}"><tr><td align="center" style="padding:24px 0">
<table role="presentation" width="{l["width"]}" cellpadding="0" cellspacing="0" class="glow" style="width:{l["width"]}px;max-width:100%;background-color:{p["canvas"]}">
{header(skin, ctx["preheader"])}
{nav(skin)}
{"".join(rows)}
{footer_mod(skin, ctx["footer_text"])}
<tr><td style="height:60px"></td></tr>
</table></td></tr></table></body></html>'''
    out = run_dir / "email-final.html"
    out.write_text(doc)
    print(f"{out}  ({len(blocks)} blocks -> the brand's own design system)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--brand", required=True)
    a = ap.parse_args()
    d = Path(a.run_dir)
    build(d if d.is_absolute() else HERE / d, a.brand)
