#!/usr/bin/env python3
"""The briefs tool, as one shareable page.

    brief_bundle.py --out briefs.html

Damon, 2026-09-14: *"We had that page where we had all the <brand> briefs
and the <brand> briefs, and you just click into <brand> or <brand>."*

That page is `briefs/` — eighteen files served on 8792, and the thing he
actually uses. An artifact is one file, so this folds the whole site into
one: the brand chooser, both brand lists and every brief page, with the
links between them rewritten to a hash router. **Nothing is redesigned and
nothing is re-worded** — it is the same pages, bundled, because the page he
asked to share is the page he already has.

**Why this is a bundler and not a renderer.** `brief_page.py` owns how a
brief looks; a second renderer would be a second truth and they would drift.
This reads that one's output.

Every picture in those pages is already a `data:` URI, so the bundle is
self-contained by the time it gets here. The stylesheet is byte-identical
across all eighteen, so it is kept once.
"""
import argparse, html, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brief_page as BP
import briefs as B

PAGES = BP.OUT


def split(t):
    """A generated page's head bits and its body, without re-parsing HTML."""
    title = (re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1]
    css = "".join(re.findall(r"<style>(.*?)</style>", t, re.S))
    fonts = re.findall(r'<link rel="stylesheet" href="(https://fonts[^"]+)"', t)
    body = re.sub(r"<style>.*?</style>", "", t, flags=re.S)
    body = re.sub(r"<meta[^>]*>|<title>.*?</title>|<link[^>]*>", "", body,
                  flags=re.S)
    return title, css, fonts, body.strip()


def build(out):
    order = ["index"]
    order += sorted(p.stem for p in PAGES.glob("brand-*.html"))
    order += sorted(p.stem for p in PAGES.glob("p[0-9]*.html"))

    css_seen, fonts, sections, titles = [], [], [], {}
    for name in order:
        f = PAGES / f"{name}.html"
        if not f.is_file():
            continue
        title, css, fnt, body = split(f.read_text())
        titles[name] = title
        if css and css not in css_seen:
            css_seen.append(css)
        for u in fnt:
            if u not in fonts:
                fonts.append(u)
        # index.html → brand-<brand>.html → p143.html become #index,
        # #brand-<brand>, #p143. Nothing else about the markup moves.
        body = re.sub(r'href="([A-Za-z0-9_-]+)\.html"', r'href="#\1"', body)
        sections.append(
            f'<div class="pg" id="pg-{name}" data-title="{html.escape(title)}"'
            f'{"" if name == "index" else " hidden"}>{body}</div>')

    # Which brand each brief belongs to, so the crumb can offer the step
    # back to its list rather than all the way to the chooser.
    reg = B.load()["briefs"]
    owner = {b: r["brand"] for b, r in reg.items() if r.get("brand")}

    link = "".join(f'<link rel="stylesheet" href="{u}">' for u in fonts)
    style = "\n".join(css_seen)

    return Path(out).write_text(f"""<title>Briefs</title>{link}
<style>
{style}
/* --- the bundle: eighteen pages in one file ------------------------- */
.pg[hidden]{{display:none !important}}
.bundlebar{{position:sticky; top:0; z-index:40; display:flex; gap:14px;
  align-items:center; padding:10px 20px; background:var(--ground);
  border-bottom:1px solid var(--line); font:600 11px var(--mono);
  letter-spacing:.12em; text-transform:uppercase}}
.bundlebar a{{color:var(--ink-3); text-decoration:none}}
.bundlebar a:hover{{color:var(--ink)}}
.bundlebar .here{{color:var(--ink)}}
.bundlebar .sep{{color:var(--ink-3); opacity:.5}}
@media print{{.bundlebar{{display:none}}}}
</style>

<nav class="bundlebar" id="bar"></nav>
{"".join(sections)}

<script>
var TITLES = {{{", ".join(f'"{k}": "{html.escape(v)}"' for k, v in titles.items())}}};
var OWNER = {{{", ".join(f'"{k}": "{v}"' for k, v in sorted(owner.items()))}}};
function go(id){{
  if(!document.getElementById("pg-" + id)) id = "index";
  document.querySelectorAll(".pg").forEach(function(p){{
    p.hidden = (p.id !== "pg-" + id);
  }});
  var bar = document.getElementById("bar"), bits = [];
  if(id === "index"){{
    bits.push('<span class="here">Briefs</span>');
  }} else {{
    bits.push('<a href="#index">Briefs</a><span class="sep">/</span>');
    if(id.indexOf("brand-") === 0){{
      bits.push('<span class="here">' + id.slice(6) + '</span>');
    }} else {{
      var b = OWNER[id];
      if(b && document.getElementById("pg-brand-" + b)){{
        bits.push('<a href="#brand-' + b + '">' + b + '</a><span class="sep">/</span>');
      }}
      bits.push('<span class="here">' + id + '</span>');
    }}
  }}
  bar.innerHTML = bits.join(" ");
  document.title = TITLES[id] || "Briefs";
  window.scrollTo(0, 0);
}}
window.addEventListener("hashchange", function(){{
  go(location.hash.replace(/^#/, "") || "index");
}});
go(location.hash.replace(/^#/, "") || "index");
</script>
""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n = build(a.out)
    pages = len(list(PAGES.glob("*.html")))
    print(f"{a.out}  ·  {pages} pages  ·  {n/1_000_000:.1f} MB")
