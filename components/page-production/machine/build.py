#!/usr/bin/env python3
"""Build the written page in the brand's design: one HTML file plus its pictures and fonts, ready to look at.

    python3 build.py --brand <brand> --label <label>

Reads the run's page.json (page-writing) and pictures.json (pictures.py); the brand's look from
brands/<brand>/brand-identity/web-tokens.md (the token table, by token name, the same table every brand keeps),
web-fonts/fonts.json and the logo files. Writes runs/page-chain/<brand>/<label>/site/index.html + img/ + fonts/.
A slot still waiting for its 3D print shows a marked frame with what the print must show. Nothing is deployed.
Agnostic: no brand is named in here.
"""
import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "page-teardown" / "machine"))
import chain_io as C  # noqa: E402

E = html.escape
DEFAULTS = {"brand-primary": "#222", "brand-cta": "#222", "brand-cta-ink": "#fff", "brand-cta-hover": "#444",
            "brand-band": "#222", "brand-accent": "#c90", "surface-bg": "#fff", "surface-card": "#fafafa",
            "surface-alt": "#f2f2f2", "text-primary": "#111", "text-secondary": "#555", "text-inverse": "#fff",
            "border": "#ddd", "rating-star": "#fa0"}


def tokens(brand):
    t = dict(DEFAULTS)
    p = C.WS / "brands" / brand / "brand-identity" / "web-tokens.md"
    for m in re.finditer(r"^\|\s*([a-z][a-z-]+)\s*\|\s*`([^`]+)`", p.read_text() if p.is_file() else "", re.M):
        t[m.group(1)] = m.group(2)
    return t


def fonts(brand):
    d = C.WS / "brands" / brand / "brand-identity" / "web-fonts"
    f = d / "fonts.json"
    return (json.loads(f.read_text()) if f.is_file() else {}), d


def logo(brand, dark_ground=True):
    d = C.WS / "brands" / brand / "brand-identity"
    svgs = sorted(d.glob("*logo*.svg"), key=lambda p: p.name)
    light = [p for p in svgs if re.search(r"white|light|-dt|_light", p.name, re.I)]
    pick = (light or svgs) if dark_ground else ([p for p in svgs if p not in light] or svgs)
    return pick[0] if pick else None


def label_split(line):
    m = re.match(r"^\s*(\*\*)?([^:*]{2,60}?)(\*\*)?\s*:\s+(.+)$", line)
    if m:
        return f"<strong>{E(m.group(2).strip())}</strong> {E(m.group(4))}"
    return E(line).replace("**", "")


def pic(b, pics, run, site):
    slot = b.get("slot")
    rec = pics.get(slot) or {}
    ar = {"4:5": "4/5", "1:1": "1/1", "16:9": "16/9", "3:4": "3/4"}.get(b.get("aspect") or "4:5", "4/5")
    if rec.get("print"):
        src = C.WS / rec["print"]
        dst = site / "img" / f"{slot}.jpg"
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image
            im = Image.open(src).convert("RGB")
            im.thumbnail((1100, 1100 * 2))
            im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
        except Exception:  # noqa: BLE001
            shutil.copy(src, dst.with_suffix(src.suffix)); dst = dst.with_suffix(src.suffix)
        return (f'<figure class="pic" style="aspect-ratio:{ar}"><img src="img/{dst.name}" alt="{E(b.get("shows") or "")}" '
                f'loading="lazy"></figure>')
    return (f'<figure class="pic waiting" style="aspect-ratio:{ar}"><figcaption><b>Waiting for its 3D print</b>'
            f'<span>{E(b.get("shows") or "")}</span></figcaption></figure>')


def block(b, nxt, pics, run, site):
    t = b.get("type")
    tx = b.get("text") or ""
    if t == "eyebrow":
        return f'<p class="eyebrow">{E(tx)}</p>'
    if t == "headline":
        return f"<h1>{E(tx)}</h1>"
    if t == "subhead":
        return f'<p class="sub">{E(tx)}</p>'
    if t == "paragraph":
        return "".join(f"<p>{label_split(p) if i == 0 else E(p)}</p>" for i, p in enumerate(tx.split("\n\n")) if p.strip())
    if t in ("bullets", "steps"):
        tag = "ol" if t == "steps" else "ul"
        head = f"<p>{E(tx)}</p>" if tx else ""
        return head + f'<{tag} class="{t}">' + "".join(f"<li>{label_split(x)}</li>" for x in b.get("list") or []) + f"</{tag}>"
    if t == "items":
        head = f"<p>{E(tx)}</p>" if tx else ""
        cards = "".join(f'<div class="card"><span class="num">{i}</span><h3>{E(it.get("title", ""))}</h3>'
                        f'<p>{E(it.get("text", ""))}</p></div>' for i, it in enumerate(b.get("items") or [], 1))
        return head + f'<div class="cards">{cards}</div>'
    if t == "quote":
        return f'<blockquote><p>“{E(tx.strip(chr(34)).strip("“”"))}”</p><cite>— a customer</cite></blockquote>'
    if t == "faq":
        head = f"<p>{E(tx)}</p>" if tx else ""
        return head + "".join(f'<details><summary>{E(f.get("q", ""))}</summary><p>{E(f.get("a", ""))}</p></details>'
                              for f in b.get("faq") or [])
    if t == "offer":
        return f'<div class="offer">{"".join(f"<p>{E(x)}</p>" for x in tx.split(chr(10)) if x.strip())}</div>'
    if t == "guarantee":
        return f'<div class="guarantee"><p>{E(tx)}</p></div>'
    if t == "button":
        return f'<p class="cta-wrap"><a class="cta" href="{E(nxt)}">{E(tx)}</a></p>'
    if t == "picture":
        return pic(b, pics, run, site)
    if t == "note":
        return f'<p class="note">{E(tx)}</p>'
    return f"<p>{E(tx)}</p>" if tx else ""


CSS = """
{faces}
:root{{--p:{brand-primary};--cta:{brand-cta};--cta-ink:{brand-cta-ink};--cta-h:{brand-cta-hover};--band:{brand-band};
--acc:{brand-accent};--bg:{surface-bg};--card:{surface-card};--alt:{surface-alt};--ink:{text-primary};
--ink2:{text-secondary};--inv:{text-inverse};--line:{border};--hf:{hf};--bf:{bf};--btnf:{btnf}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:400 18px/1.6 var(--bf)}}
header.bar{{background:var(--band);padding:14px 20px;text-align:center}}header.bar img{{height:26px}}
main{{max-width:760px;margin:0 auto;padding:0 20px 40px}}
section{{padding:28px 0;border-bottom:1px solid color-mix(in srgb,var(--line) 35%,transparent)}}
section.hero{{border:0;padding-top:36px}}
h1{{font:500 clamp(30px,6vw,46px)/1.12 var(--hf);text-transform:{hcase};letter-spacing:.01em;margin:6px 0 12px}}
h2{{font:500 clamp(23px,4vw,30px)/1.2 var(--hf);text-transform:{hcase};margin:0 0 12px}}
h3{{font:600 19px/1.3 var(--bf);margin:6px 0}}
.eyebrow{{font:600 13px/1.2 var(--btnf);text-transform:uppercase;letter-spacing:.12em;color:var(--ink2);margin:0}}
.sub{{font-size:20px;color:var(--ink2)}}
ul,ol{{padding-left:22px}}li{{margin:8px 0}}ol.steps li::marker{{font-weight:700;color:var(--p)}}
.cards{{display:grid;gap:14px}}.card{{background:var(--card);border:1px solid var(--line);padding:16px 18px;border-radius:{rad}}}
.card .num{{display:inline-block;font:700 13px var(--btnf);background:var(--band);color:var(--inv);padding:2px 9px;border-radius:{rad}}}
.card p{{margin:4px 0 0}}
blockquote{{margin:18px 0;padding:16px 20px;background:var(--alt);border-left:4px solid var(--p)}}
blockquote p{{margin:0;font-size:19px}}cite{{display:block;margin-top:6px;font:600 13px var(--btnf);color:var(--ink2);font-style:normal}}
details{{border-top:1px solid var(--line);padding:12px 0}}summary{{font-weight:700;cursor:pointer}}
.offer{{background:var(--band);color:var(--inv);padding:20px 22px;margin:16px 0;border-radius:{rad}}}.offer p{{margin:4px 0}}
.guarantee{{border:2px solid var(--acc);padding:14px 18px;margin:14px 0;border-radius:{rad}}}
.cta-wrap{{text-align:center;margin:22px 0}}
.cta{{display:inline-block;background:var(--cta);color:var(--cta-ink);font:700 16px/1 var(--btnf);text-transform:uppercase;
letter-spacing:.08em;padding:18px 34px;text-decoration:none;border:{bborder};border-radius:{rad}}}.cta:hover{{background:var(--cta-h)}}
.pic{{margin:18px 0;overflow:hidden;background:var(--alt);border-radius:{rad}}}.pic img{{width:100%;height:100%;object-fit:cover;display:block}}
.pic.waiting{{display:flex;align-items:center;justify-content:center;border:2px dashed var(--line);padding:18px}}
.pic.waiting figcaption{{font-size:14px;color:var(--ink2);text-align:center}}.pic.waiting b{{display:block;color:var(--ink);margin-bottom:6px}}
.note{{font-size:14px;color:var(--ink2)}}
footer{{background:var(--band);color:var(--inv);text-align:center;padding:22px;font-size:13px}}
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True); ap.add_argument("--label", required=True)
    a = ap.parse_args(argv)
    run = C.Run(a.brand, a.label)
    page = json.loads((run.dir / "page.json").read_text())
    pics = json.loads((run.dir / "pictures.json").read_text()) if (run.dir / "pictures.json").exists() else {}
    nxt = run.state.get("next_url") or "#"
    site = run.dir / "site"
    if site.exists():
        shutil.rmtree(site)
    (site / "fonts").mkdir(parents=True)
    tk = tokens(a.brand)
    fj, fdir = fonts(a.brand)
    faces = ""
    for f in fj.get("faces", []):
        shutil.copy(fdir / f["file"], site / "fonts" / f["file"])
        faces += (f"@font-face{{font-family:'{f['family']}';src:url(fonts/{f['file']}) format('woff2');"
                  f"font-weight:{f.get('weight', 400)};font-display:swap}}\n")
    css = CSS.format(faces=faces, hf=fj.get("heading", tk.get("font-heading", "sans-serif")),
                     bf=fj.get("body", tk.get("font-body", "sans-serif")), btnf=fj.get("button", "sans-serif"),
                     hcase=fj.get("heading_case", "none"), rad=fj.get("button_radius", "4px"),
                     bborder=fj.get("button_border", "none"), **tk)
    lg = logo(a.brand)
    head = ""
    if lg:
        shutil.copy(lg, site / lg.name)
        head = f'<header class="bar"><img src="{lg.name}" alt="{E(a.brand)}"></header>'
    body = []
    for i, s in enumerate(page.get("sections", [])):
        inner = "".join(block(b, nxt, pics, run, site) for b in s.get("blocks", []))
        if i:   # one h1 per page: a later section's headline is its section heading
            inner = inner.replace("<h1>", "<h2>").replace("</h1>", "</h2>")
        body.append(f'<section class="{"hero" if i == 0 else ""}">{inner}</section>')
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
           f'content="width=device-width,initial-scale=1"><title>{E(page.get("title", ""))}</title>'
           f'<meta name="description" content="{E(page.get("meta_description", ""))}"><meta name="robots" content="noindex">'
           f"<style>{css}</style></head><body>{head}<main>{''.join(body)}</main>"
           f"<footer>© {E(a.brand.upper())}</footer></body></html>")
    (site / "index.html").write_text(doc)
    print(f"built {site / 'index.html'}")
    filed = C.file_build(run)
    if filed:
        print(f"filed: {run.state['page']} {run.state['version']} on the page list")


if __name__ == "__main__":
    main()
