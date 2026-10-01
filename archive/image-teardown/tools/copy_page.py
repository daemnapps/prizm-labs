#!/usr/bin/env python3
"""The long-form copy written for a brand's statics, on one page.

    copy_page.py --brand <brand> --out <brand>-copy.html

Damon, 2026-09-16: *"show me the copy written for the <brand> images that we
wrote copy for."*

Each piece is the copy machine's own stage-9 brief, lifted from
`copy/results/<run>/`, shown beside the swipe it was written from
and the draft picture it will sit under. Only THE COPY and THE OPENINGS are
shown — the offer notes and run flags stay in the brief. Nothing is
retyped; the page is rebuilt from the files.
"""
import argparse, html, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P
import briefs as B
import designer_page as D

ROOT = HERE.parent
COPY = P.LAB.parent.parent / "components" / "copywriter" / "results"


def section(t, start, stop):
    m = re.search(rf"^## {start}\b.*?\n(.*?)(?=^## {stop}\b|\Z)", t, re.S | re.M | re.I)
    return m.group(1).strip() if m else ""


def pieces(brand):
    reg = B.load()["briefs"]
    by_run = {r.get("run"): b for b, r in reg.items() if r.get("brand") == brand}
    out = []
    for d in sorted(COPY.glob(f"{brand}-*")):
        f = d / "stage9--brief.md"
        if not f.is_file():
            continue
        run = f"{brand}-{d.name}"
        bid = by_run.get(run)
        rec = reg.get(bid, {})
        t = f.read_text()
        drafts = sorted((ROOT / "drafts" / brand).glob(f"v*/{bid}-draft.png")) if bid else []
        out.append({
            "id": bid or "—", "slug": d.name, "run": run,
            "swipe": (rec.get("swipe") or {}).get("block") or d.name,
            "src": P.RUNS / run / "assets/source.jpg",
            "draft": drafts[-1] if drafts else None,
            "copy": section(t, "THE COPY", "THE OPENINGS"),
            "hooks": section(t, "THE OPENINGS", "WHAT TO WATCH"),
        })
    return out


CSS = """
.cp{margin:0 0 72px; padding-top:28px; border-top:2px solid var(--ink)}
.cp-head{display:flex; align-items:baseline; gap:14px; flex-wrap:wrap}
.cp-id{font-family:var(--disp); font-weight:800; font-size:32px; letter-spacing:-.02em}
.cp-src{font-family:var(--mono); font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--ink3)}
.cp-grid{display:grid; grid-template-columns:260px 1fr; gap:32px; margin-top:22px; align-items:start}
.cp-pics{display:grid; gap:14px; position:sticky; top:16px}
.cp-body h4{font-family:var(--disp); font-weight:700; font-size:18px; margin:28px 0 10px; letter-spacing:-.01em}
.cp-body h4:first-child{margin-top:0}
.cp-body p{font-size:16px; color:var(--ink); max-width:64ch}
.cp-body blockquote,.cp-body .quote{border-left:2px solid var(--rule); padding-left:16px}
.cp-body p.label{font-family:var(--disp); font-weight:700; font-size:15px; margin:24px 0 8px}
.cp-body ul,.cp-body ol{font-size:15.5px; padding-left:22px; max-width:64ch}
.cp-body li{margin:0 0 6px}
.cp-body hr{border:0; border-top:1px solid var(--rule2); margin:26px 0}
.cp-body em,.cp-body i{color:var(--ink2)}
.hooks{margin-top:34px; padding:22px 24px; background:var(--card); border:1px solid var(--rule); border-radius:3px}
.hooks > h3{font-family:var(--mono); font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--ink3); margin:0 0 12px}
.toc{display:flex; flex-wrap:wrap; gap:8px; margin:30px 0 56px}
.toc a{font-family:var(--mono); font-size:12px; font-weight:600; letter-spacing:.06em; color:var(--ink);
  text-decoration:none; border:1px solid var(--rule); border-radius:100px; padding:6px 14px; background:var(--card)}
.toc a:hover{border-color:var(--ink2)}
@media (max-width:720px){ .cp-grid{grid-template-columns:1fr} .cp-pics{position:static; grid-template-columns:1fr 1fr} }
"""


def quote_md(t):
    """Blockquoted bodies render as plain paragraphs; the '>' is Markdown's, not the copy's."""
    return re.sub(r"^>\s?", "", t, flags=re.M)


def build(brand, out):
    ps = pieces(brand)
    tpl = (HERE / "designer-page.html").read_text()
    head = tpl[:tpl.index("<header>")].replace("<title>Working a Brief</title>",
                                               f"<title>{brand.title()} Static Copy</title>")
    head = head.replace("</style>", CSS + "\n</style>", 1)
    toc = "".join(f'<a href="#c-{p["slug"]}">{html.escape(p["id"])}</a>' for p in ps)
    blocks = []
    for p in ps:
        pics = ""
        if p["src"].is_file():
            pics += (f'<figure><img loading="lazy" src="{D.thumb(p["src"])}" alt="The swipe">'
                     f'<figcaption><span>swipe</span><b>Theirs</b></figcaption></figure>')
        if p["draft"]:
            pics += (f'<figure><img loading="lazy" src="{D.thumb(p["draft"])}" alt="Our draft">'
                     f'<figcaption><span>draft</span><b>Ours</b></figcaption></figure>')
        blocks.append(f'''<article class="cp" id="c-{p["slug"]}">
  <div class="cp-head"><span class="cp-id">{html.escape(p["id"])}</span>
    <span class="cp-src">{html.escape(p["swipe"])}</span></div>
  <div class="cp-grid">
    <div class="cp-pics">{pics}</div>
    <div class="cp-body">{D.md(quote_md(p["copy"]))}
      <div class="hooks"><h3>The openings — all ship</h3>{D.md(quote_md(p["hooks"]))}</div>
    </div>
  </div>
</article>''')
    page = f'''{head}<div class="wrap" style="max-width:1080px">
<header>
  <div class="eyebrow"><span>{html.escape(brand)}</span><span>Long-form copy for the statics</span></div>
  <h1>{html.escape(brand.title())} Static Copy</h1>
  <p class="standfirst">The copy written for each image, in the order the briefs were
  opened. <b>Theirs</b> is the post it was swiped from, <b>Ours</b> is the draft
  picture it runs under. Every opening ships — the machine does not rank them.</p>
</header>
<nav class="toc">{toc}</nav>
{"".join(blocks)}
<footer><span>{len(ps)} pieces</span><span>from the copy machine&rsquo;s stage-9 briefs</span></footer>
</div>'''
    Path(out).write_text(page)
    return len(ps), len(page)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n, size = build(a.brand, a.out)
    print(f"{a.out}  ·  {n} pieces  ·  {size/1_000_000:.1f} MB")
