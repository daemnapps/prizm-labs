#!/usr/bin/env python3
"""Stage 9 — build the page from its layout and pictures, in the brand's
page-kit project, and place the built page where the funnel serves it.

    python3 build_site.py scrub-base-01 --page base \
        --dest ~/Projects/<brand>-pages \
        --target ~/Projects/<brand>/scrub/en/us/v2_archive \
        --deploy-prefix /scrub/en/us/v2_archive \
        --offer-url /scrub/en/us/v2c/select.html \
        --tracking-js /scrub/en/us/v2c/js/jquery-3.6.0.min.js /scrub/en/us/v2c/js/campaign.js /scrub/en/us/v2c/js/landing-v2.js

What it does, in order:
  1. writes src/<funnel>/<page-name>.html — front matter from the layout's
     sections (every slot as the layout filled it, every picture slot pointing
     at the picture made for it), then one include per section in order
  2. adds the brand's legal strip (brands/<brand>/funnels/<funnel>/legal.md) as
     the last section, and a nav at the top if the layout chose none
  3. runs the page kit's build
  4. rewrites the built page's asset paths to the deploy prefix, points every
     offer link at the offer page, and appends the funnel's own tracking
     scripts so the click carries its parameters the way the live page's does
  5. copies the page and the kit's css/images into the target folder

Brand-agnostic: nothing here names a brand; every value comes from the run,
the layout, the brand folder or the flags.
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "machine"))
import page_paths as P   # noqa: E402
WORKSPACE = P.WORKSPACE   # AI_WORKSPACE, else found by walking up — never counted


def yq(v):
    """A front-matter string, safely quoted."""
    if v is None: v = ""
    v = str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{v}"'


def legal_fields(brand, funnel):
    p = WORKSPACE / "brands" / brand / "funnels" / funnel / "legal.md"
    if not p.exists():
        return {}
    txt = p.read_text()
    f = {}
    m = re.search(r"^heading:\s*(.+)$", txt, re.M); f["legal_1_heading"] = m.group(1).strip() if m else "Disclaimer"
    items = re.findall(r"^- (.+)$", txt, re.M)
    for i, it in enumerate(items[:8], 1):
        f[f"legal_1_item_{i}"] = it.strip()
    m = re.search(r"^statement:\s*(.+)$", txt, re.M); f["legal_1_statement"] = m.group(1).strip() if m else ""
    m = re.search(r"^copyright:\s*(.+)$", txt, re.M); f["legal_1_copyright"] = m.group(1).strip() if m else ""
    return f


def prune_empties(html):
    """A library block renders a bordered box, a stat tile, a gallery cell for
    every slot whether or not the words filled it. An empty one is a blank
    bar on the page. Remove, repeatedly, every element inside a section that
    holds no text and no picture — a spacer or a decorative rule goes with
    them, which is the right trade."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("  ! bs4 missing — empty boxes not pruned"); return html
    soup = BeautifulSoup(html, "html.parser")
    KEEP = {"img", "svg", "video", "iframe", "input", "select", "textarea", "button", "picture", "source", "hr", "br"}
    changed = True; rounds = 0
    while changed and rounds < 8:
        changed = False; rounds += 1
        for el in list(soup.select("section *")):
            if el.name in KEEP or el.name in ("script", "style", "a"): continue
            if el.find(list(KEEP | {"a"})): continue
            if el.get_text(strip=True): continue
            el.decompose(); changed = True
    return str(soup)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label"); ap.add_argument("--page", default="base")
    ap.add_argument("--dest", required=True); ap.add_argument("--target", required=True)
    ap.add_argument("--deploy-prefix", required=True); ap.add_argument("--offer-url", required=True)
    ap.add_argument("--tracking-js", nargs="*", default=[])
    ap.add_argument("--no-build", action="store_true", help="write the source page only")
    a = ap.parse_args()
    run = P.need_run(a.label)   # either home: runs/page-machine/<brand>/, then the old runs/
    state = json.loads((run / "run.json").read_text())
    brand, funnel = state["brand"], state["funnel"]
    suffix = "" if a.page == "base" else f"-{a.page}"
    plan = json.loads((run / f"layout{suffix}.json").read_text())
    pics = json.loads((run / f"pictures{suffix}.json").read_text()) if (run / f"pictures{suffix}.json").exists() else {}
    base_pics = json.loads((run / "pictures.json").read_text()) if (run / "pictures.json").exists() else {}
    aliases = json.loads((run / "picture-aliases.json").read_text()) if (run / "picture-aliases.json").exists() else {}
    for s0 in plan["sections"]:
        for pic in s0.get("pictures", []):
            for key in ("id", "reuse"):
                v = pic.get(key)
                if v and v not in base_pics and v not in pics and v in aliases:
                    pic["reuse"] = aliases[v]
    page_name = plan["page_name"]
    dest = Path(a.dest).expanduser(); src = dest / "src" / funnel

    # 1. front matter + includes
    fm = {"page_layout": plan.get("layout", "base-landing.html"), "page_type": "product",
          "title": "", "next_url": "select", "cta_text": "", "guarantee_text": ""}
    ident_dir = P.identity_dir(brand)                 # brand-identity/, old identity/
    # The library's blocks use fixed variable names, so a block can appear once
    # per page as shipped. A second use gets its own copy of the include with
    # every variable suffixed (problemsolution_4_ -> problemsolution_4__2_), so
    # the sections render their own words instead of the last one's.
    seen, blocks = {}, []
    for s in plan["sections"]:
        b = s["block"]; seen[b] = seen.get(b, 0) + 1
        n = seen[b]
        prefix = b.replace("-", "_") + "_"
        if n > 1:
            newp = f"{b.replace('-', '_')}__{n}_"
            tpl = (src / "_includes" / "landing" / f"{b}.html").read_text()
            tpl2 = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(prefix), newp, tpl)
            (src / "_includes" / "landing" / f"{b}__{n}.html").write_text(tpl2)
            s["fields"] = {(newp + k[len(prefix):] if k.startswith(prefix) else k): v for k, v in s.get("fields", {}).items()}
            for pic in s.get("pictures", []):
                if pic["field"].startswith(prefix):
                    pic["field"] = newp + pic["field"][len(prefix):]
            blocks.append(f"{b}__{n}")
        else:
            blocks.append(b)
    for s in plan["sections"]:
        for k, v in s.get("fields", {}).items():
            if isinstance(v, str) and (v.startswith(f"brands/{brand}/brand-identity/") or v.startswith(f"brands/{brand}/identity/")):
                v = "images/brand/" + Path(v).name          # the brand's marks live in the project as images/brand/
            if isinstance(v, str) and v.startswith("brands/") and re.search(r"\.(png|jpe?g|webp|svg)$", v) and (WORKSPACE / v).exists():
                (src / "assets/images/product").mkdir(parents=True, exist_ok=True)
                shutil.copy(WORKSPACE / v, src / "assets/images/product" / Path(v).name)
                v = "images/product/" + Path(v).name
            if isinstance(v, str) and "|" in v and (k.endswith("_tiers")):
                v = [{"label": t.strip()} for t in v.split("|") if t.strip()]
            elif isinstance(v, str) and "|" in v and (k.endswith("_includes") or k.endswith("_items") or k.endswith("_bullets")):
                v = [t.strip() for t in v.split("|") if t.strip()]
            elif isinstance(v, str) and k.endswith("_includes") and v:
                v = [v]
            if isinstance(v, str) and "[UNFILLED" in v:
                print(f"  ! {k}: carried an [UNFILLED] note — left empty on the page; the hole stays in the brief")
                v = ""
            fm[k] = v
            if k.endswith("headline") and not fm["title"]:
                fm["title"] = v
        for pic in s.get("pictures", []):
            rec = pics.get(pic["id"]) or {}
            if rec.get("reuse"):
                rec = base_pics.get(rec["reuse"]) or pics.get(rec["reuse"]) or {}
            if not rec.get("asset") and pic.get("reuse"):
                rec = base_pics.get(pic["reuse"]) or {}
            if rec.get("asset"):
                fm[pic["field"]] = rec["asset"]
                alt_key = pic["field"] + "_alt"
                fm.setdefault(alt_key, pic.get("alt", ""))
            elif pic.get("aspect") == "none" and pic.get("brief", "").startswith("images/"):
                fm[pic["field"]] = pic["brief"].split()[0]
    if not fm["cta_text"]:
        for k, v in fm.items():
            if k.endswith("cta_text") and v: fm["cta_text"] = v; break
    fm["cta_text"] = fm["cta_text"] or "See the offer"
    cp = fm.get("cta_params", "")
    m = re.search(r"guarantee=([^;|]+)", cp) if isinstance(cp, str) else None
    if m:
        fm["guarantee_text"] = m.group(1).strip()
    m = re.search(r"text=([^;|]+)", cp) if isinstance(cp, str) else None
    if m and not fm["cta_text"]:
        fm["cta_text"] = m.group(1).strip()
    fm["cta_params"] = ""
    if not fm["guarantee_text"] or not re.search(r"money back|guarantee|refund|every penny|\d+\s*days?", str(fm["guarantee_text"]), re.I):
        fm["guarantee_text"] = ""
        for k, v in fm.items():
            if "guarantee" in k and isinstance(v, str) and v and not k.endswith("_alt") and not k.endswith("_image") \
               and re.search(r"money back|guarantee|refund|every penny|\d+\s*days?", v, re.I):
                m = re.search(r"(\d+)\s*[- ]?\s*day", v, re.I)
                fm["guarantee_text"] = f"{m.group(1)}-Day Money Back" if m else v[:60]; break
    # a guarantee badge is typeset by the page, never generated: a plain SVG in the brand's colours
    badge_keys = [k for k in fm if k.endswith("badge_image") and not fm.get(k)]
    for blk in blocks:
        if blk.startswith("hero-4") and "hero_4_badge_image" not in fm:
            badge_keys.append("hero_4_badge_image"); fm["hero_4_badge_image"] = ""
    try:
        from PIL import Image, ImageDraw, ImageFont
        tok = {}
        for line in (P.identity_dir(brand) / "web-tokens.md").read_text().splitlines():
            m = re.match(r"^\|\s*([a-z-]+)\s*\|\s*`?([^`|]+?)`?\s*\|", line)
            if m: tok[m.group(1)] = m.group(2).strip()
        accent = tok.get("brand-accent", "#B19A6F"); ink = tok.get("text-inverse", "#FFFFFF")
        g = fm.get("guarantee_text") or "Money back guarantee"
        big = re.search(r"(\d+)\s*[- ]?\s*(day|days)", g, re.I)
        top, mid, bottom = (big.group(1), big.group(2).upper(), "MONEY BACK") if big else ("", g.upper()[:14], "GUARANTEE")
        S = 512; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse((8, 8, S - 8, S - 8), fill=accent); d.ellipse((34, 34, S - 34, S - 34), outline=ink, width=4)
        def font(sz):
            for cand in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial Bold.ttf"):
                try: return ImageFont.truetype(cand, sz)
                except Exception: pass
            return ImageFont.load_default()
        def centre(txt, y, sz):
            f = font(sz); w = d.textlength(txt, font=f); d.text(((S - w) / 2, y), txt, font=f, fill=ink)
        if top: centre(top, 120, 150); centre(mid, 275, 64); centre(bottom, 350, 44)
        else: centre(mid, 190, 60); centre(bottom, 270, 44)
        (src / "assets/images/brand").mkdir(parents=True, exist_ok=True)
        im.save(src / "assets/images/brand/guarantee-badge.png")
        for k in badge_keys: fm[k] = "images/brand/guarantee-badge.png"
        badge_keys = []
    except Exception as e:
        print("  ! badge:", e)
    if badge_keys:
        (src / "assets/images/brand").mkdir(parents=True, exist_ok=True)
        label = next((fm[k] for k in fm if k.endswith("badge_alt") and fm[k]), "Money back guarantee")
        words = label.replace("guarantee", "").replace("Guarantee", "").strip().upper()
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160"><circle cx="80" cy="80" r="76" fill="var(--brand-accent,#B19A6F)"/><circle cx="80" cy="80" r="66" fill="none" stroke="#fff" stroke-width="2" opacity=".7"/><text x="80" y="72" text-anchor="middle" font-family="sans-serif" font-size="15" font-weight="700" fill="#fff" letter-spacing="1">{words[:18]}</text><text x="80" y="96" text-anchor="middle" font-family="sans-serif" font-size="13" font-weight="600" fill="#fff" letter-spacing="1">GUARANTEE</text></svg>'''
        (src / "assets/images/brand/guarantee-badge.svg").write_text(svg)
        for k in badge_keys: fm[k] = "images/brand/guarantee-badge.svg"
    # footer links from the funnel's legal record
    lg = (WORKSPACE / "brands" / brand / "funnels" / funnel / "legal.md")
    if lg.exists():
        urls = re.findall(r"(Terms[^h]*?(https?://\S+))|(Privacy[^h]*?(https?://\S+))|(Contact[^h]*?(https?://\S+))", lg.read_text())
        found = {}
        for t in urls:
            if t[1]: found["terms"] = t[1]
            if t[3]: found["privacy"] = t[3]
            if t[5]: found["contact"] = t[5]
        for k, u in found.items():
            fm.setdefault(f"footer_1_{k}_url", u)
    fm["styles"] = ["css/brand.css"]
    # a section whose every slot came out empty (a hole the chain left, nothing else) is not built
    kept = []
    for blk, sec in zip(blocks, plan["sections"]):
        has_text = any(isinstance(fm.get(k), str) and fm.get(k).strip() for k in sec.get("fields", {}))
        has_pic = any(fm.get(pic["field"]) for pic in sec.get("pictures", []))
        if has_text or has_pic or blk.startswith(("nav-", "footer-", "legal-", "cta-")):
            kept.append(blk)
        else:
            print(f"  ! {blk}: every slot empty — section left out")
    blocks = kept
    if not any(b.startswith("nav-") for b in blocks):
        blocks.insert(0, "nav-2")
        fm.setdefault("nav_logo_image", "images/brand/logo-dark.png")
        fm.setdefault("nav_logo_alt", brand)
        fm.setdefault("nav_2_offer_text", "")
        short = [v for k, v in fm.items() if k.endswith("cta_text") and isinstance(v, str) and 0 < len(v) <= 18]
        fm.setdefault("nav_2_cta_text", short[0] if short else "See the offer")   # the nav button is narrow
    if len(str(fm.get("nav_2_cta_text", ""))) > 18:
        short = [v for k, v in fm.items() if k.endswith("cta_text") and isinstance(v, str) and 0 < len(v) <= 18]
        fm["nav_2_cta_text"] = short[0] if short else "See the offer"
    legal = legal_fields(brand, funnel)
    if legal:
        if "legal-1" not in blocks: blocks.append("legal-1")
        fm.update(legal)          # the funnel's legal file always wins over whatever the layout put in these slots

    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for x in v:
                if isinstance(x, dict):
                    first = True
                    for kk, vv in x.items():
                        lines.append(f"  {'- ' if first else '  '}{kk}: {yq(vv)}"); first = False
                else:
                    lines.append(f"  - {yq(x)}")
        else:
            lines.append(f"{k}: {yq(v)}")
    lines.append("---")
    lines += [f"{{% campaign_include 'landing/{b}.html' %}}" for b in blocks]
    page_src = src / f"{page_name}.html"
    page_src.write_text("\n".join(lines) + "\n")
    print("wrote", page_src)
    if a.no_build:
        return

    # 3. build
    r = subprocess.run(["npm", "run", "-s", "build"], cwd=dest, capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n" + (r.stderr or r.stdout)[-2000:])
    built = dest / "_site" / funnel / page_name / "index.html"
    if not built.exists():
        sys.exit(f"built page not found at {built}")
    html = built.read_text()

    # 4. paths, links, tracking
    prefix = a.deploy_prefix.rstrip("/")
    OFFER = "\u0000OFFER\u0000"                       # a placeholder, so the prefix rewrite cannot touch the offer link
    html = re.sub(rf'href="/{funnel}/{re.escape(fm["next_url"])}/?"', f'href="{OFFER}"', html)
    html = re.sub(rf'href="{re.escape(fm["next_url"])}"', f'href="{OFFER}"', html)   # blocks that print next_url raw
    KIT = "\u0000KIT\u0000"
    for folder in ("css", "images", "fonts", "js", "video", "img"):
        html = html.replace(f'"/{funnel}/{folder}/', f'"{KIT}{folder}/')
    html = html.replace(f'"/{funnel}/config.js', f'"{KIT}config.js')
    html = html.replace(f'href="/{funnel}/', f'href="{prefix}/')
    html = html.replace(KIT, f"{prefix}/kit/").replace(OFFER, a.offer_url)
    # an empty picture slot renders as a broken image; drop those tags
    html = re.sub(r'<img\b[^>]*\bsrc=""[^>]*>', "", html)
    html = re.sub(r'<img\b[^>]*\bsrc="' + re.escape(prefix) + r'/kit/images/"[^>]*>', "", html)
    track = "".join(f'<script src="{s}"></script>\n' for s in a.tracking_js)
    track += f"""<script>
(function () {{
  var offer = '{a.offer_url}';
  function links() {{ return Array.prototype.slice.call(document.querySelectorAll('a[href^="' + offer + '"]')); }}
  function set() {{
    var ok = window.campaign && typeof campaign.getSuccessUrl === 'function';
    links().forEach(function (a) {{ a.href = ok ? campaign.getSuccessUrl(offer) : offer; }});
    return ok;
  }}
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', set); else set();
  window.addEventListener('load', set);
  var n = 0, poll = setInterval(function () {{ if (set() || ++n >= 20) clearInterval(poll); }}, 250);
}})();
</script>
"""
    html = prune_empties(html)
    # Netlify serves the funnel's images as cacheable for a month, so a changed
    # file at the same address never refreshes in a browser that has seen it.
    # A content hash on the address makes a changed file a new address.
    import hashlib
    def stamp(m):
        rel = m.group(2)
        f = dest / "_site" / funnel / rel
        if not f.exists(): return m.group(0)
        h = hashlib.md5(f.read_bytes()).hexdigest()[:8]
        return f'{m.group(1)}{prefix}/kit/{rel}?v={h}"'
    html = re.sub(r'((?:src|href)=")' + re.escape(prefix) + r'/kit/([^"?]+)"', stamp, html)
    html = html.replace("</body>", track + "</body>")

    # 5. place
    target = Path(a.target).expanduser(); target.mkdir(parents=True, exist_ok=True)
    (target / f"{page_name}.html").write_text(html)
    kit = target / "kit"; kit.mkdir(exist_ok=True)
    for folder in ("css", "images", "fonts", "js"):
        srcf = dest / "_site" / funnel / folder
        if srcf.exists():
            if (kit / folder).exists(): shutil.rmtree(kit / folder)
            shutil.copytree(srcf, kit / folder)
    if (dest / "_site" / funnel / "config.js").exists():
        shutil.copy(dest / "_site" / funnel / "config.js", kit / "config.js")
    print("placed", target / f"{page_name}.html", "+ kit/")


if __name__ == "__main__":
    main()
