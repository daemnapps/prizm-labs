#!/usr/bin/env python3
"""Make (or refresh) a brand's page-kit project from the machine's kit and the
brand's own identity. Brand-agnostic: every colour, face and mark comes from
brands/<brand>/brand-identity/ (old name identity/), never from here.

    python3 scaffold.py --brand <brand> --funnel scrub --dest ~/Projects/<brand>-pages

Creates:
    <dest>/package.json, _data/campaigns.json
    <dest>/src/<funnel>/_layouts/base-landing.html     (from kit/)
    <dest>/src/<funnel>/_includes/**                    (the section library)
    <dest>/src/<funnel>/assets/css/landing/tokens.css   (from brand-identity/web-tokens.md)
    <dest>/src/<funnel>/assets/css/brand.css            (the brand's faces)
    <dest>/src/<funnel>/assets/images/**                (the library's icons + the brand's marks)
    <dest>/src/<funnel>/assets/config.js                (inert — the SDK is not this page's concern)
and runs npm install once. Re-running refreshes the kit copies and the skin;
it never touches pages or generated pictures already in the project.
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
KIT = HERE / "kit"
sys.path.insert(0, str(HERE / "machine"))
import page_paths as P   # noqa: E402
WORKSPACE = P.WORKSPACE   # AI_WORKSPACE, else found by walking up — never counted

TOKENS = ("brand-primary", "brand-cta", "brand-cta-ink", "brand-cta-hover", "brand-band",
          "brand-primary-dark", "brand-secondary", "brand-accent", "rating-star",
          "surface-bg", "surface-card", "surface-alt", "text-primary", "text-secondary", "text-inverse",
          "border", "font-heading", "font-body", "font-link")


def identity_dir(brand):
    """The brand's look: brand-identity/ (the v6 name), else the old identity/."""
    return P.identity_dir(brand)


def read_tokens(brand):
    p = identity_dir(brand) / "web-tokens.md"
    if not p.exists():
        sys.exit(f"{p.relative_to(WORKSPACE)} is missing — the brand's web skin has to be written down before a page can wear it")
    out = {}
    for line in p.read_text().splitlines():
        m = re.match(r"^\|\s*([a-z-]+)\s*\|\s*`?([^`|]+?)`?\s*\|", line)
        if m and m.group(1) in TOKENS:
            out[m.group(1)] = m.group(2).strip()
    missing = [t for t in TOKENS if t not in out]
    if missing:
        sys.exit(f"web-tokens.md is missing: {missing}")
    return out


def tokens_css(t):
    return f"""/* Written by the page machine's scaffold from brands/<brand>/brand-identity/web-tokens.md — edit that, not this. */
:root {{
  --brand-primary: {t['brand-primary']};
  --brand-primary-dark: {t['brand-primary-dark']};
  --brand-secondary: {t['brand-secondary']};
  --brand-accent: {t['brand-accent']};
  --brand-band: {t['brand-band']};
  --brand-cta: {t['brand-cta']};
  --brand-cta-ink: {t['brand-cta-ink']};
  --brand-cta-hover: {t['brand-cta-hover']};
  --surface-bg: {t['surface-bg']};
  --surface-card: {t['surface-card']};
  --surface-alt: {t['surface-alt']};
  --text-primary: {t['text-primary']};
  --text-secondary: {t['text-secondary']};
  --text-inverse: {t['text-inverse']};
  --border-default: {t['border']};
  --state-success: {t['brand-accent']};
  --state-warning: {t['rating-star']};
  --state-error: #B3261E;
  --rating-star: {t['rating-star']};
}}
""" + (KIT / "assets/css/landing/tokens.template.css").read_text().split("}", 1)[1]


def brand_css(t):
    link = t["font-link"]
    imp = f"@import url('{link}');\n" if link and link != "none" else ""
    return f"""{imp}/* The brand's faces, from brand-identity/web-tokens.md. Tailwind's `font-sans` is remapped so every block wears them. */
:root {{ --font-heading: {t['font-heading']}; --font-body: {t['font-body']}; }}
body, .font-sans {{ font-family: {t['font-body']} !important; }}
h1, h2, h3, .text-display, .text-heading-1, .text-heading-2, .text-heading-3 {{ font-family: {t['font-heading']} !important; }}
.text-yellow-400, .text-amber-400, .text-yellow-500 {{ color: var(--rating-star) !important; }}

""" + BUTTONS

BUTTONS = r"""/* Pictures: a cover-cropped photograph keeps its upper third — that is where a face or a hand is. */
section img[class*="object-cover"] { object-position: 50% 22%; }
@media (max-width: 767px) { section img[class*="h-[300px]"] { height: 440px; object-position: 50% 38%; } }
/* Buttons: the library paints every call to action with --brand-primary and white type.
   The brand's own button (brand-identity/web-tokens.md, "Buttons") wears the cta ground with dark type. */
a.bg-\[var\(--brand-primary\)\], button.bg-\[var\(--brand-primary\)\],
.bg-\[var\(--brand-primary\)\][href], .bg-\[var\(--brand-primary\)\][type="button"], .bg-\[var\(--brand-primary\)\][type="submit"] {
  background-color: var(--brand-cta) !important; color: var(--brand-cta-ink) !important;
  text-transform: uppercase; font-weight: 700 !important; letter-spacing: 1.2px; border-radius: 5px !important;
}
a.bg-\[var\(--brand-primary\)\] *, button.bg-\[var\(--brand-primary\)\] * { color: var(--brand-cta-ink) !important; }
a.bg-\[var\(--brand-primary\)\]:hover, button.bg-\[var\(--brand-primary\)\]:hover { background-color: var(--brand-cta-hover) !important; }
a.bg-\[var\(--brand-primary\)\] img, button.bg-\[var\(--brand-primary\)\] img { filter: brightness(0); }
a.bg-\[color\:var\(--brand-primary\)\], button.bg-\[color\:var\(--brand-primary\)\] {
  background-color: var(--brand-cta) !important; color: var(--brand-cta-ink) !important;
  text-transform: uppercase; font-weight: 700 !important; letter-spacing: 1.2px; border-radius: 5px !important;
}
a.bg-\[color\:var\(--brand-primary\)\] *, button.bg-\[color\:var\(--brand-primary\)\] * { color: var(--brand-cta-ink) !important; }
a.bg-\[color\:var\(--brand-primary\)\] img, button.bg-\[color\:var\(--brand-primary\)\] img { filter: brightness(0); }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True); ap.add_argument("--funnel", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--store-url", default=""); ap.add_argument("--store-name", default="")
    a = ap.parse_args()
    dest = Path(a.dest).expanduser()
    src = dest / "src" / a.funnel
    (src / "_layouts").mkdir(parents=True, exist_ok=True)
    (src / "assets" / "css" / "landing").mkdir(parents=True, exist_ok=True)
    (src / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (dest / "_data").mkdir(exist_ok=True)

    shutil.copy(KIT / "_layouts/base-landing.html", src / "_layouts/base-landing.html")
    if (src / "_includes").exists():
        shutil.rmtree(src / "_includes")
    shutil.copytree(KIT / "_includes", src / "_includes")
    for d in (KIT / "assets/images").iterdir():
        if d.is_dir():
            if (src / "assets/images" / d.name).exists():
                shutil.rmtree(src / "assets/images" / d.name)
            shutil.copytree(d, src / "assets/images" / d.name)
    if (KIT / "assets/js").exists():                     # the library's section behaviours
        if (src / "assets/js").exists(): shutil.rmtree(src / "assets/js")
        shutil.copytree(KIT / "assets/js", src / "assets/js")
    def saturated(hexs):
        h = hexs.lstrip("#"); h = "".join(c*2 for c in h) if len(h) == 3 else h
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        return (max(r, g, b) - min(r, g, b)) > 40
    tok0 = read_tokens(a.brand)
    for svg in (src / "assets/images").rglob("*.svg"):
        if "brand" in svg.parts: continue
        txt = svg.read_text(errors="ignore")
        # a colour, never an entity (&#226;) or an id reference (#clip0)
        new = re.sub(r'(?<![&\w])#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?![0-9A-Fa-f\w])', lambda m: tok0["brand-primary"] if saturated(m.group(0)) else m.group(0), txt)
        if new != txt: svg.write_text(new)
    ident = identity_dir(a.brand)
    (src / "assets/images/brand").mkdir(exist_ok=True)
    for p in ident.glob("*"):
        if p.suffix.lower() in (".png", ".svg"):
            shutil.copy(p, src / "assets/images/brand" / p.name)

    t = read_tokens(a.brand)
    (src / "assets/css/landing/tokens.css").write_text(tokens_css(t))
    (src / "assets/css/brand.css").write_text(brand_css(t))
    if not (src / "assets/config.js").exists():
        (src / "assets/config.js").write_text("// Inert: this project builds pre-sells only; the offer page carries the cart.\nwindow.nextConfig = window.nextConfig || {};\n")

    pkg = json.loads((KIT / "package.json").read_text())
    pkg["name"] = f"{a.brand}-pages"; pkg["description"] = f"{a.brand} pre-sells, built by the page machine"
    pkg["scripts"]["build"] = "campaign-build"
    (dest / "package.json").write_text(json.dumps(pkg, indent=2) + "\n")
    camp_path = dest / "_data/campaigns.json"
    camps = json.loads(camp_path.read_text()) if camp_path.exists() else {}
    camps.setdefault(a.funnel, {
        "name": f"{a.brand} {a.funnel}", "description": f"{a.brand} {a.funnel} pre-sells", "entry_url": "",
        "sdk_version": "0.4.38", "store_name": a.store_name or a.brand, "store_url": a.store_url,
        "store_terms": "", "store_privacy": "", "store_contact": "", "store_returns": "", "store_shipping": "",
        "store_phone": "", "store_phone_tel": "", "gtm_id": "", "fb_pixel_id": "", "og_image": ""})
    camp_path.write_text(json.dumps(camps, indent=2) + "\n")
    if not (dest / "node_modules").exists():
        print("npm install …")
        r = subprocess.run(["npm", "install", "--silent"], cwd=dest, capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stderr[-800:])
    print("scaffolded", dest)


if __name__ == "__main__":
    main()
