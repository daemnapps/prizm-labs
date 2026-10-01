#!/usr/bin/env python3
"""The format bank, on one page.

    python3 format_bank_page.py

formats.json is the truth; this only draws it. A new format is a new row in
that file — this page picks it up with no edit here, which is the whole point
of keeping formats as data rather than as a table someone maintains by hand.
"""
import html, json
from paths import HERE

SRC = HERE / "bank" / "formats.json"
OUT = HERE / "pages" / "format-bank.html"

# Every length bar is drawn against the longest format in the bank, so the
# four are comparable at a glance. Read off the data, never pinned — a longer
# format added later rescales the lot instead of running off the end.
def scale(formats):
    return max(f["length"]["max"] for f in formats)


def esc(s):
    return html.escape(str(s))


def bar(f, top):
    lo, hi = f["length"]["min"], f["length"]["max"]
    left, width = lo / top * 100, (hi - lo) / top * 100
    return (f'<div class="bar"><div class="bar-t" style="left:{left:.1f}%;'
            f'width:{max(width, 1.2):.1f}%"></div></div>'
            f'<div class="bar-n"><span>{lo}</span><span>{hi} {esc(f["length"]["unit"])}</span></div>')


ROWS = [("form", "Form"), ("opens_with", "Opens with"),
        ("reads_as", "Reads as"), ("carries_offer", "Carries the offer"),
        ("requires", "Requires"), ("channels", "Channels")]


def card(f, top, d):
    v = f.get("variations", d.get("variations"))
    out = [f'<article class="fmt">',
           f'<header class="fmt-h"><code>{esc(f["key"])}</code>',
           f'<h2>{esc(f["name"])}</h2>',
           f'<p class="what">{esc(f["what"])}</p></header>',
           f'<div class="len">{bar(f, top)}</div>',
           '<dl>']
    for k, label in ROWS:
        if k not in f:
            continue
        val = f[k]
        if isinstance(val, list):
            val = " · ".join(val)
        cls = ' class="req"' if k == "requires" else ""
        out.append(f"<dt{cls}>{esc(label)}</dt><dd{cls}>{esc(val)}</dd>")
    out.append(f"<dt>Variations</dt><dd><b>{v}</b> per source</dd>")
    out.append("</dl></article>")
    return "".join(out)


CSS = """
:root{
  --ground:#F1F2F0; --surface:#FFFFFF; --surface-2:#F7F8F6;
  --ink:#161A18; --body:#3B403D; --dim:#6C726E; --dimmer:#949A96;
  --line:#DFE3DF; --line-2:#ECEFEB;
  --accent:#1F4E5F; --accent-soft:#DCE8EA; --warn:#8A5A1F;
  --display:"Bricolage Grotesque",system-ui,sans-serif;
  --body-f:"Source Serif 4",Georgia,serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#121513; --surface:#1A1E1C; --surface-2:#171A18;
  --ink:#ECEFEA; --body:#CDD3CE; --dim:#98A09A; --dimmer:#6B726D;
  --line:#2B302D; --line-2:#232725;
  --accent:#7FC2CE; --accent-soft:#16302F; --warn:#D9A85D;
}}
:root[data-theme="dark"]{
  --ground:#121513; --surface:#1A1E1C; --surface-2:#171A18;
  --ink:#ECEFEA; --body:#CDD3CE; --dim:#98A09A; --dimmer:#6B726D;
  --line:#2B302D; --line-2:#232725;
  --accent:#7FC2CE; --accent-soft:#16302F; --warn:#D9A85D;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--body);
  font:17px/1.6 var(--body-f);-webkit-font-smoothing:antialiased;padding:0 20px 90px}
.wrap{max-width:50rem;margin:0 auto}
header.top{padding:58px 0 4px}
.eyebrow{font:600 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
h1{font-family:var(--display);font-size:clamp(30px,5vw,42px);line-height:1.05;
  margin:14px 0 0;letter-spacing:-.02em;color:var(--ink);font-weight:700}
.stand{font-size:17.5px;color:var(--dim);margin-top:14px;max-width:34rem}

.defaults{margin:34px 0 8px;background:var(--surface);border:1px solid var(--line);
  border-radius:8px;padding:16px 20px;display:flex;flex-wrap:wrap;gap:26px}
.defaults .d{min-width:8rem}
.defaults dt{font:600 10px var(--mono);letter-spacing:.1em;text-transform:uppercase;
  color:var(--dim);margin-bottom:3px}
.defaults dd{margin:0;font-family:var(--display);font-size:19px;color:var(--ink);font-weight:600}
.defaults dd small{font-family:var(--body-f);font-size:14px;color:var(--dim);font-weight:400}

.fmt{background:var(--surface);border:1px solid var(--line);border-radius:8px;
  padding:24px 24px 8px;margin:20px 0}
.fmt-h code{font:600 11px var(--mono);letter-spacing:.04em;color:var(--accent);
  background:var(--accent-soft);padding:3px 8px;border-radius:4px}
.fmt-h h2{font-family:var(--display);font-size:25px;line-height:1.15;margin:12px 0 0;
  color:var(--ink);font-weight:700;letter-spacing:-.015em}
.what{margin:8px 0 0;color:var(--dim);font-size:17px}

.len{margin:20px 0 4px}
.bar{position:relative;height:9px;border-radius:5px;background:var(--line-2);overflow:hidden}
.bar-t{position:absolute;top:0;bottom:0;background:var(--accent);border-radius:5px}
.bar-n{display:flex;justify-content:space-between;margin-top:6px;
  font:500 12px var(--mono);color:var(--dim);font-variant-numeric:tabular-nums}

dl{display:grid;grid-template-columns:10.5rem 1fr;gap:0;margin:18px 0 0}
dt{font:600 10px var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--dim);
  padding:11px 0;border-top:1px solid var(--line-2)}
dd{margin:0;padding:11px 0;border-top:1px solid var(--line-2);color:var(--body)}
dt.req,dd.req{color:var(--warn)}
dd b{color:var(--ink);font-weight:600}

footer{margin-top:46px;padding-top:18px;border-top:1px solid var(--line);
  font:12px/1.7 var(--mono);color:var(--dimmer)}
@media(max-width:560px){dl{grid-template-columns:1fr;gap:0}
  dt{padding-bottom:0;border-top:1px solid var(--line-2)}
  dd{padding-top:4px;border-top:0}}
"""


def build():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    fmts, dflt = d["formats"], d.get("defaults", {})
    top = scale(fmts)
    h = dflt.get("headlines", {}); ds = dflt.get("descriptions", {})

    p = ['<title>Copy Format Bank</title>',
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&'
         'family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&'
         'family=JetBrains+Mono:wght@500;600&display=swap">',
         f"<style>{CSS}</style>",
         '<div class="wrap"><header class="top">',
         '<div class="eyebrow">the copy machine · formats.json</div>',
         '<h1>Copy format bank</h1>',
         f'<p class="stand">The {len(fmts)} formats every source gets written to. '
         'Held as data, not as a table someone keeps by hand — a new format is a '
         'new row in the file, with no prompt edit and no code change.</p>',
         '</header>',
         '<div class="defaults">',
         f'<div class="d"><dt>Bodies per format</dt><dd>{dflt.get("variations","—")} '
         '<small>unless the row says otherwise</small></dd></div>',
         f'<div class="d"><dt>Headlines</dt><dd>{h.get("count","—")} '
         f'<small>at {h.get("words",["—"])[0]}–{h.get("words",["—","—"])[-1]} words</small></dd></div>',
         f'<div class="d"><dt>Descriptions</dt><dd>{ds.get("count","—")} '
         f'<small>at {ds.get("words",["—"])[0]} words</small></dd></div>',
         '</div>']
    p += [card(f, top, dflt) for f in fmts]
    p.append('<footer>copy/formats.json · length bars share one scale, '
             f'0–{top} words<br>every format is written for every source; the source '
             'decides what goes in them, never which ones exist</footer></div>')
    OUT.write_text("".join(p), encoding="utf-8")
    print(f"{OUT}  ({len(fmts)} formats)")


if __name__ == "__main__":
    build()
