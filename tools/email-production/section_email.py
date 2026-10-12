#!/usr/bin/env python3
"""The designed email: a finished email laid into its format's sections.

    python3 section_email.py <run folder> --brand <brand> --briefs <picture-briefs.json>
    python3 section_email.py <run folder> --brand <brand> --briefs <…> --pictures <dir>
    python3 section_email.py <run folder> --brand <brand> --briefs <…> --dry-run   # no model call

the owner, 2026-10-08: "think about email design just like we think about landing
page design, because they're basically just many landing pages" — "you might as
well build in these other sections too, so we can get some saucy emails for
this first batch."

WHAT IT DOES
1. Reads the finished email (deliverable/email.json) and its week's picture
   brief: the FORMAT and the picture SLOTS (formats.json, EMAIL-FORMATS.md).
2. Stage 8s (prompts/stage8s-sections-*.md, the newest) moves the email's own
   words into the format's sections — no new claims; facts are the offer bank
   and the store's product names only. Written to deliverable/sections.json.
3. Lays it out: one 600px table per section, the brand's designed look
   (`brands/<brand>/email-sms/sections.json`, or `--look <file>`), each picture
   slot filled from `--pictures` by slot name (scene-1.png, detail-2.png,
   product-1.png, proof-3.png …) and every PRODUCT slot from the live store
   photo when no picture is given. Written to deliverable/preview-sections.html
   (pictures inline, opens anywhere) and deliverable/sections-klaviyo.html
   (picture slots as {{slot}} markers for the uploader to swap for hosted URLs).

Nothing is sent. This tool has no Klaviyo call; the draft is made by the
uploader after the owner has seen the preview.
"""
import argparse
import base64
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def workspace():
    if os.environ.get("AI_WORKSPACE"):
        return Path(os.environ["AI_WORKSPACE"]).expanduser().resolve()
    p = HERE
    while p != p.parent:
        if (p / "brands").is_dir() and (p / "components").is_dir():
            return p
        p = p.parent
    sys.exit("could not find the workspace root (set AI_WORKSPACE)")


WS = workspace()
FORMATS = json.loads((HERE / "formats.json").read_text())
SECTIONS_MODEL = "claude-sonnet-5"   # a "checks"-tier job: moving words, not writing them
DRIVE_PRODUCTS = ("Library/CloudStorage/GoogleDrive-{acct}/Shared drives/Shared Assets/"
                  "brands/{brand}/products")


# ------------------------------------------------------------------ inputs

def latest_prompt():
    found = sorted((HERE / "prompts").glob("stage8s-sections-v*-*.md"),
                   key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    if not found:
        sys.exit("no prompts/stage8s-sections-v*.md")
    return found[-1]


def brief_for(briefs_file, label):
    b = json.loads(Path(briefs_file).read_text())
    for m in b["emails"]:
        if m["label"] == label:
            return m
    sys.exit(f"{label}: not in {briefs_file}")


def store(brand):
    f = WS / "brands" / brand / "products" / "store.json"
    return json.loads(f.read_text())["products"] if f.is_file() else []


def store_entry(brand, product):
    """A kit slug (daily-face-wash) or a store handle (wash) → the store's entry."""
    for p in store(brand):
        if p["handle"] == product or product.startswith(p["handle"] + "-"):
            return p
    return None


def facts(brand, offer, products):
    bank = (WS / "brands" / brand / "products" / "offer-bank.md")
    text = bank.read_text() if bank.is_file() else ""
    out = []
    g = re.search(r"^## Guarantees\n(.*?)(?=^## )", text, re.S | re.M)
    if g:
        out.append("GUARANTEES (word for word):\n" + g.group(1).strip())
    if offer and offer != "none":
        m = re.search(rf"^## {re.escape(offer)}\b.*?(?=^## |\Z)", text, re.S | re.M)
        if m:
            out.append("THE OFFER:\n" + m.group(0).strip())
    names = []
    for p in products:
        e = store_entry(brand, p)
        if e:
            names.append(f"- product id `{p}`: {e['title']} — {e['url']}")
    if names:
        out.append("PRODUCT NAMES (use exactly):\n" + "\n".join(names))
    return "\n\n".join(out) or "(none on file)"


def resolved_format(fmt, products):
    """The format with its P* slots expanded to one P per product."""
    f = json.loads(json.dumps(FORMATS["formats"][fmt]))
    for s in f["sections"]:
        pics = []
        for k in s.get("pictures", []):
            pics += ["P"] * max(1, len(products)) if k == "P*" else [k]
        if pics:
            s["pictures"] = pics
    return f


# ------------------------------------------------------------------ stage 8s

def run_8s(email, fmt, fmt_spec, fact_text, out_dir, dry=False):
    tpl = latest_prompt().read_text()
    prompt = (tpl.replace("{format_json}", json.dumps({"id": fmt, **fmt_spec}, indent=1))
                 .replace("{facts}", fact_text)
                 .replace("{email_json}", json.dumps(email, indent=1, ensure_ascii=False)))
    (out_dir / "stage8s--prompt-sent.md").write_text(prompt)
    if dry:
        print(f"  dry run: stage 8s prompt written ({len(prompt):,} chars), no model call")
        return None
    r = subprocess.run(["claude", "-p", "--model", SECTIONS_MODEL, "--output-format", "text"],
                       input=prompt, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        sys.exit(f"stage 8s failed on {SECTIONS_MODEL}: {(r.stderr or r.stdout)[:400]}")
    (out_dir / "stage8s--sections.md").write_text(r.stdout)
    m = re.search(r"```SECTIONS\s*\n(.*?)```", r.stdout, re.S)
    if not m:
        sys.exit("stage 8s returned no SECTIONS block — see stage8s--sections.md")
    return json.loads(m.group(1))


# ------------------------------------------------------------------ pictures

def drive_products(brand):
    for acct in [a for a in os.environ.get("GDRIVE_ACCOUNTS", "").split(",") if a]:   # Drive for Desktop account emails
        d = Path.home() / DRIVE_PRODUCTS.format(acct=acct, brand=brand)
        if d.is_dir():
            return d
    return None


def product_photo(brand, product):
    """The live store's first photo of the product, on the Drive."""
    root = drive_products(brand)
    if not root:
        return None
    for d in sorted(root.glob(f"{product}/shopify-*"), reverse=True):
        pics = sorted(p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
        if pics:
            return pics[0]
    return None


def slot_names(sections):
    """Every picture slot in order, named the way the files are: scene-1, product-2 …"""
    count, names = {}, []
    word = {"S": "scene", "P": "product", "D": "detail", "R": "proof"}
    for si, s in enumerate(sections):
        for pi, p in enumerate(s.get("pictures") or []):
            k = word.get(p.get("kind"), "scene")
            count[k] = count.get(k, 0) + 1
            names.append((si, pi, f"{k}-{count[k]}"))
    return names


def data_uri(path):
    p = Path(path)
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    if p.stat().st_size > 900_000:      # keep the preview light: a 600px jpeg copy
        small = Path("/tmp") / f"sec-{p.stem}-{p.stat().st_size}.jpg"
        if not small.exists():
            subprocess.run(["sips", "-Z", "1200", "-s", "format", "jpeg", str(p), "--out", str(small)],
                           capture_output=True)
        p, mime = small, "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


# ------------------------------------------------------------------ the look

DEFAULT_LOOK = {
    "page": "#0E0E0E", "card": "#1A1A1A", "ink": "#F5F2EC", "muted": "#A8A29A",
    "accent": "#F0D860", "accent_dark": "#908448", "panel": "#232323", "rule": "#2E2B24",
    "button": "#F0D860", "button_text": "#1A1A1A",
    "headline": "ivypresto-display, Georgia, Times, 'Times New Roman', serif",
    "body": "neue-haas-unica, Arial, 'Helvetica Neue', Helvetica, sans-serif",
}


def look_for(brand, look_file):
    lk = dict(DEFAULT_LOOK)
    for f in (WS / "brands" / brand / "email-sms" / "sections.json", Path(look_file) if look_file else None):
        if f and f.is_file():
            lk.update(json.loads(f.read_text()).get("look", {}))
    simple = WS / "brands" / brand / "email-sms" / "simple.json"
    s = json.loads(simple.read_text()) if simple.is_file() else {}
    lk["logo"] = (s.get("logo") or {})
    lk["signoff"] = s.get("signoff") or []
    lk["tagline"] = s.get("tagline") or ""
    lk["greeting"] = s.get("greeting") or ""
    return lk


# ------------------------------------------------------------------ render

def esc(t):
    t = html.escape(str(t or "").strip())
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t).replace("\n", "<br>")


def render(sec, lk, pics, email, klaviyo=False):
    L = lk
    H = f"font-family:{L['headline']};color:{L['ink']};"
    B = f"font-family:{L['body']};color:{L['ink']};font-size:16px;line-height:1.55;"
    M = f"font-family:{L['body']};color:{L['muted']};font-size:13px;line-height:1.5;"
    rows = []

    def pic(si, pi, width=600, radius=0):
        src = pics.get((si, pi))
        if not src:
            return ""
        alt = esc(((sec["sections"][si].get("pictures") or [{}])[pi] or {}).get("alt"))
        return (f'<img src="{src}" alt="{alt}" width="{width}" style="display:block;width:100%;'
                f'max-width:{width}px;height:auto;border:0;border-radius:{radius}px;">')

    def btn(b):
        b = b or email.get("button") or {}
        return (f'<tr><td align="center" style="padding:8px 32px 36px;"><a href="{html.escape(b.get("link") or "#")}" '
                f'style="display:inline-block;background:{L["button"]};color:{L["button_text"]};{B}color:{L["button_text"]};'
                f'font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:15px;text-decoration:none;'
                f'padding:18px 34px;border-radius:4px;">{esc(b.get("label"))}</a></td></tr>')

    def title(t, size=30, pad="0 32px 14px"):
        return (f'<tr><td style="padding:{pad};{H}font-size:{size}px;line-height:1.12;">{esc(t)}</td></tr>'
                if t else "")

    def texts(ts, pad="0 32px 18px"):
        return "".join(f'<tr><td style="padding:{pad};{B}">{esc(t)}</td></tr>' for t in (ts or []) if t)

    def grid(cells, cols):
        out, row = [], []
        w = int(100 / cols)
        for i, c in enumerate(cells):
            row.append(f'<td width="{w}%" valign="top" style="padding:6px;">{c}</td>')
            if len(row) == cols or i == len(cells) - 1:
                row += ['<td></td>'] * (cols - len(row))
                out.append("<tr>" + "".join(row) + "</tr>")
                row = []
        return (f'<tr><td style="padding:0 26px 18px;"><table role="presentation" width="100%" '
                f'cellpadding="0" cellspacing="0">{"".join(out)}</table></td></tr>')

    for si, s in enumerate(sec["sections"]):
        n = s.get("name")
        items = s.get("items") or []
        npics = len(s.get("pictures") or [])
        if n == "header-section":
            logo = L.get("logo") or {}
            src = logo.get("url", "")
            rows.append(f'<tr><td align="center" style="padding:30px 0 22px;border-bottom:1px solid {L["rule"]};">'
                        f'<a href="{html.escape(logo.get("link", "#"))}"><img src="{src}" alt="{esc(logo.get("alt"))}" '
                        f'width="{logo.get("width", 100)}" style="display:block;height:auto;border:0;'
                        f'filter:invert(1);"></a></td></tr>')
        elif n == "hero-section":
            if npics:
                rows.append(f'<tr><td style="padding:0;">{pic(si, 0)}</td></tr>')
            rows.append(f'<tr><td style="height:28px;line-height:28px;">&nbsp;</td></tr>')
            rows.append(title(s.get("title") or email.get("headline"), 34))
            if L.get("greeting") and si <= 1:
                rows.append(texts([L["greeting"]]))
            rows.append(texts(s.get("text")))
        elif n in ("mechanism-section", "routine-steps-section", "symptoms-section"):
            rows.append(f'<tr><td style="padding:10px 32px 0;"><div style="height:1px;background:{L["rule"]};"></div></td></tr>')
            rows.append(title(s.get("title"), 24, "22px 32px 12px"))
            rows.append(texts(s.get("text")))
            if items:
                cells = []
                for i, it in enumerate(items):
                    img = pic(si, i, 180, 8) if i < npics else ""
                    num = (f'<div style="{H}color:{L["accent"]};font-size:26px;line-height:1;">{i + 1:02d}</div>'
                           if n == "routine-steps-section" else "")
                    cells.append(f'<div style="background:{L["panel"]};border-radius:10px;padding:14px;">'
                                 f'{img}{num}<div style="{B}font-weight:700;color:{L["accent"]};font-size:14px;'
                                 f'text-transform:uppercase;letter-spacing:.05em;margin-top:10px;">{esc(it.get("title"))}</div>'
                                 f'<div style="{B}font-size:14px;margin-top:4px;">{esc(it.get("text"))}</div></div>')
                rows.append(grid(cells, 3 if len(cells) >= 3 else len(cells)))
        elif n == "product-row-section":
            rows.append(title(s.get("title"), 24, "22px 32px 12px"))
            rows.append(texts(s.get("text")))
            cells = []
            for i, it in enumerate(items or [{}] * npics):
                cells.append(f'<div style="background:#FFFFFF;border-radius:10px;padding:10px;">{pic(si, i, 180, 6)}</div>'
                             f'<div style="{B}font-weight:700;color:{L["accent"]};font-size:15px;margin-top:10px;">'
                             f'{esc(it.get("title"))}</div><div style="{B}font-size:14px;margin-top:2px;">{esc(it.get("text"))}</div>')
            rows.append(grid(cells, min(3, max(1, len(cells)))))
        elif n == "cards-section":
            for i in range(npics):
                rows.append(f'<tr><td style="padding:8px 32px 16px;">{pic(si, i, 536, 10)}</td></tr>')
            rows.append(title(s.get("title"), 26, "6px 32px 12px"))
            rows.append(texts(s.get("text")))
        elif n in ("review-section", "b4a-section"):
            rows.append(title(s.get("title"), 24, "22px 32px 12px"))
            cells = [f'{pic(si, i, 180, 8)}<div style="{M}margin-top:6px;">{esc((items[i] if i < len(items) else {}).get("text"))}</div>'
                     for i in range(npics)]
            rows.append(grid(cells, 3 if n == "review-section" else 1))
            rows.append(texts(s.get("text")))
        elif n == "stat-proof-section":
            rows.append(f'<tr><td align="center" style="padding:18px 32px;{H}color:{L["accent"]};font-size:52px;">'
                        f'{esc(s.get("title"))}</td></tr>')
            rows.append(texts(s.get("text"), "0 48px 18px"))
        elif n in ("offer-section", "pricing-section", "guarantee-section"):
            inner = ""
            if npics:
                inner += f'<div style="background:#FFFFFF;border-radius:8px;padding:8px;margin-bottom:14px;">{pic(si, 0, 480, 6)}</div>'
            if s.get("title"):
                inner += f'<div style="{H}font-size:24px;color:{L["accent"]};margin-bottom:8px;">{esc(s["title"])}</div>'
            inner += "".join(f'<div style="{B}margin-bottom:8px;">{esc(t)}</div>' for t in s.get("text") or [] if t)
            if inner:
                rows.append(f'<tr><td style="padding:10px 32px 22px;"><div style="border:1px solid {L["accent_dark"]};'
                            f'border-radius:12px;padding:22px;background:{L["panel"]};">{inner}</div></td></tr>')
        elif n == "social-section":
            rows.append(texts(s.get("text"), "0 32px 12px"))
        elif n == "cta-section":
            rows.append(btn(s.get("button")))
        elif n == "footer-section":
            so = "<br>".join(esc(x) for x in L.get("signoff") or [])
            if so:
                rows.append(f'<tr><td style="padding:6px 32px 28px;{B}">{so}</td></tr>')
            rows.append(f'<tr><td align="center" style="padding:24px 32px 30px;border-top:1px solid {L["rule"]};{M}">'
                        + (f"{esc(L['tagline'])}<br><br>" if L.get("tagline") else "")
                        + 'No longer find value in our emails? <a href="{% unsubscribe_link %}" '
                          f'style="color:{L["muted"]};">Unsubscribe</a><br>'
                          "{{ organization.name }} · {{ organization.full_address }}</td></tr>")
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{esc(email.get("headline"))}</title></head>'
            f'<body style="margin:0;padding:0;background:{L["page"]};">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{L["page"]};">'
            f'<tr><td align="center" style="padding:24px 8px;">'
            f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
            f'style="width:100%;max-width:600px;background:{L["card"]};border-radius:6px;overflow:hidden;">'
            + "".join(r for r in rows if r) + "</table></td></tr></table></body></html>\n")


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--briefs", required=True, help="the week's picture-briefs.json")
    ap.add_argument("--pictures", help="folder of slot pictures: scene-1.png, detail-1.png …")
    ap.add_argument("--look", help="a look file ({'look': {...}}) when the brand has no sections.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="use deliverable/sections.json, no model call")
    a = ap.parse_args()

    run = Path(a.run).resolve()
    out = run / "deliverable"
    email = json.loads((out / "email.json").read_text())
    b = brief_for(a.briefs, run.name)
    fmt = b.get("format") or FORMATS["type_to_format"].get(b.get("type"), FORMATS["_default"])
    products = [x["what"] for x in b.get("slots", []) if x["kind"] == "P"]
    spec = resolved_format(fmt, products)
    offer = ((json.loads((run / "run.json").read_text()) if (run / "run.json").is_file() else {})
             .get("assignment", {}).get("offer"))
    print(f"{run.name}: format {fmt} · {sum(len(s.get('pictures', [])) for s in spec['sections'])} picture slots")

    if a.reuse and (out / "sections.json").is_file():
        sec = json.loads((out / "sections.json").read_text())
    else:
        sec = run_8s(email, fmt, spec, facts(a.brand, offer, products), out, a.dry_run)
        if sec is None:
            return
        (out / "sections.json").write_text(json.dumps(sec, indent=1, ensure_ascii=False))

    # pictures: given files by slot name, else the live store photo for products
    pics, kl, missing = {}, {}, []
    pdir = Path(a.pictures) if a.pictures else None
    pq = list(products)
    for si, pi, name in slot_names(sec["sections"]):
        p = sec["sections"][si]["pictures"][pi]
        f = next((pdir / f"{name}{x}" for x in (".png", ".jpg", ".jpeg") if pdir and (pdir / f"{name}{x}").is_file()), None)
        if not f and p.get("kind") == "P":
            prod = p.get("product") or (pq.pop(0) if pq else None)
            f = product_photo(a.brand, prod) if prod else None
        if f:
            pics[(si, pi)] = data_uri(f)
            kl[(si, pi)] = "{{" + name + "}}"
        else:
            missing.append(name)
    lk = look_for(a.brand, a.look)
    (out / "preview-sections.html").write_text(render(sec, lk, pics, email))
    (out / "sections-klaviyo.html").write_text(render(sec, lk, kl, email, klaviyo=True))
    print(f"  wrote deliverable/preview-sections.html" + (f" · waiting on pictures: {', '.join(missing)}" if missing else ""))


if __name__ == "__main__":
    main()
