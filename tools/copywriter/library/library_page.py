#!/usr/bin/env python3
"""The copy library, on one page.

    python3 library/library_page.py

index.json is the truth; this draws it. Counts by channel and format, then
the copy itself — swiped and ours, never machine output — with the strongest
evidence first where a heat signal exists (live creatives, views).
"""
import html, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "pages" / "copy-library.html"

CHANNELS = [
    ("paid-social", "Paid social", "interrupted, skeptical, mid-scroll"),
    ("organic-social", "Organic social", "chosen, curious, native"),
    ("email", "Email", "permitted, private, one-to-one"),
    ("owned-pages", "Owned pages", "arrived, evaluating, deciding"),
]

SAMPLES = 4          # pieces shown per format; the rest are counted, not drawn
CLIP = 640           # chars of each piece shown


def esc(s):
    return html.escape(str(s))


def heat(r):
    t = r.get("tags") or {}
    return t.get("live_creatives") or t.get("views") or 0


def chip(r):
    t = r.get("tags") or {}
    a = r.get("audience") or {}
    bits = []
    if a.get("avatar"):
        bits.append(f"→ {a['avatar']}" + (f" · {a['funnel']}" if a.get("funnel") else ""))
    elif a.get("market"):
        bits.append("for: " + str(a["market"]).split("—")[0].strip())
    if t.get("live_creatives"):
        bits.append(f"{t['live_creatives']} live creatives")
    if t.get("views"):
        bits.append(f"{t['views']:,} views" if isinstance(t["views"], int) else f"{t['views']} views")
    if t.get("swipe_brand"):
        bits.append(t["swipe_brand"])
    if t.get("category"):
        bits.append(str(t["category"]))
    if r.get("brand") not in ("-", None, ""):
        bits.append(r["brand"])
    return " · ".join(str(b) for b in bits[:4])


CSS = """
:root{
  --ground:#F1F2F0; --surface:#FFFFFF; --surface-2:#F7F8F6;
  --ink:#161A18; --body:#3B403D; --dim:#6C726E; --dimmer:#949A96;
  --line:#DFE3DF; --line-2:#ECEFEB;
  --accent:#1F4E5F; --accent-soft:#DCE8EA;
  --gold:#8A5A1F; --gold-soft:#F4EBDD;
  --display:"Bricolage Grotesque",system-ui,sans-serif;
  --serif:"Source Serif 4",Georgia,serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#121513; --surface:#1A1E1C; --surface-2:#171A18;
  --ink:#ECEFEA; --body:#CDD3CE; --dim:#98A09A; --dimmer:#6B726D;
  --line:#2B302D; --line-2:#232725;
  --accent:#7FC2CE; --accent-soft:#16302F;
  --gold:#D9A85D; --gold-soft:#2B2114;
}}
:root[data-theme="dark"]{
  --ground:#121513; --surface:#1A1E1C; --surface-2:#171A18;
  --ink:#ECEFEA; --body:#CDD3CE; --dim:#98A09A; --dimmer:#6B726D;
  --line:#2B302D; --line-2:#232725;
  --accent:#7FC2CE; --accent-soft:#16302F;
  --gold:#D9A85D; --gold-soft:#2B2114;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--body);
  font:16.5px/1.6 var(--serif);-webkit-font-smoothing:antialiased;padding:0 20px 90px}
.wrap{max-width:52rem;margin:0 auto}
header.top{padding:56px 0 8px}
.eyebrow{font:600 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
h1{font-family:var(--display);font-size:clamp(30px,5vw,44px);line-height:1.04;
  margin:14px 0 0;letter-spacing:-.02em;color:var(--ink);font-weight:700}
.stand{font-size:17px;color:var(--dim);margin-top:14px;max-width:36rem}

.rule{background:var(--gold-soft);border:1px solid var(--gold);border-radius:8px;
  padding:15px 20px;margin:26px 0 0;font-size:15.5px;line-height:1.6}
.rule b{color:var(--gold)}
.rule code{font:.85em var(--mono)}
.total{display:flex;gap:26px;flex-wrap:wrap;margin:30px 0 6px;background:var(--surface);
  border:1px solid var(--line);border-radius:8px;padding:16px 22px}
.total .t{min-width:7rem}
.total dt{font:600 10px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--dim)}
.total dd{margin:2px 0 0;font-family:var(--display);font-size:24px;color:var(--ink);
  font-weight:700;font-variant-numeric:tabular-nums}

h2.ch{font-family:var(--display);font-size:22px;color:var(--ink);font-weight:700;
  margin:48px 0 2px;letter-spacing:-.015em}
.chstate{margin:0 0 14px;font-size:15px;color:var(--dimmer);font-style:italic}

details{background:var(--surface);border:1px solid var(--line);border-radius:8px;margin:10px 0}
summary{cursor:pointer;padding:14px 20px;display:flex;align-items:baseline;gap:12px;
  list-style:none}
summary::-webkit-details-marker{display:none}
summary .f{font-family:var(--display);font-weight:700;font-size:17px;color:var(--ink)}
summary .c{font:600 12px var(--mono);color:var(--accent);background:var(--accent-soft);
  padding:2px 9px;border-radius:10px;font-variant-numeric:tabular-nums}
summary .o{margin-left:auto;font:500 11px var(--mono);color:var(--dimmer)}
.piece{border-top:1px solid var(--line-2);padding:16px 20px}
.piece .m{font:500 11px var(--mono);color:var(--gold);margin-bottom:8px}
.piece .tx{white-space:pre-wrap;font-size:15.5px;line-height:1.62;color:var(--body);max-width:40rem}
.piece .tx b{color:var(--ink)}
.more{border-top:1px solid var(--line-2);padding:10px 20px;font:500 12px var(--mono);color:var(--dimmer)}
footer{margin-top:50px;padding-top:18px;border-top:1px solid var(--line);
  font:12px/1.7 var(--mono);color:var(--dimmer)}
"""


def build():
    data = json.loads((HERE / "index.json").read_text(encoding="utf-8"))
    rows = [r for r in data["rows"] if r["origin"] != "machine"]
    swiped = sum(1 for r in rows if r["origin"] == "swiped")
    ours = sum(1 for r in rows if r["origin"] == "ours")

    p = ['<title>Copy Library</title>',
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&'
         'family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&'
         'family=JetBrains+Mono:wght@500;600&display=swap">',
         f"<style>{CSS}</style>",
         '<div class="wrap"><header class="top">',
         '<div class="eyebrow">the copy brain · evidence</div>',
         '<h1>The copy library</h1>',
         '<p class="stand">Every piece of copy we hold, categorized against the '
         'channel map. Swiped copy ran in the wild on someone else\'s money; '
         'ours ran on ours. Machine output is filed but never counted as '
         'evidence.</p></header>',
         '<div class="rule"><b>The sourcing rule.</b> Copy inherits its audience '
         'from where it was sourced — a swipe aimed at a 54-year-old woman never '
         'feeds copy aimed at a 15-year-old. Every piece carries who its source '
         'wrote for; which of OUR avatars may draw on it is a ruling in '
         '<code>library/sources.json</code>, and an empty ruling quarantines the '
         'source from injection until it is made.</div>',
         '<div class="total">',
         f'<div class="t"><dt>Pieces</dt><dd>{len(rows):,}</dd></div>',
         f'<div class="t"><dt>Swiped</dt><dd>{swiped:,}</dd></div>',
         f'<div class="t"><dt>Ours, shipped</dt><dd>{ours:,}</dd></div>',
         '</div>']

    for ch, name, state in CHANNELS:
        crows = [r for r in rows if r["channel"] == ch]
        if not crows:
            continue
        p.append(f'<h2 class="ch">{esc(name)} — {len(crows):,}</h2>')
        p.append(f'<p class="chstate">{esc(state)}</p>')
        fmts = sorted({r["format"] for r in crows})
        for fmt in fmts:
            frows = sorted((r for r in crows if r["format"] == fmt),
                           key=heat, reverse=True)
            o = " + ".join(sorted({r["origin"] for r in frows}))
            p.append(f'<details><summary><span class="f">{esc(fmt)}</span>'
                     f'<span class="c">{len(frows):,}</span>'
                     f'<span class="o">{esc(o)}</span></summary>')
            shown = 0
            for r in frows:
                if shown >= SAMPLES:
                    break
                tx = r["text"].strip()
                if not tx:
                    continue
                clip = tx[:CLIP] + ("…" if len(tx) > CLIP else "")
                meta = chip(r)
                p.append('<div class="piece">'
                         + (f'<div class="m">{esc(meta)}</div>' if meta else "")
                         + f'<div class="tx">{esc(clip)}</div></div>')
                shown += 1
            rest = len(frows) - shown
            if rest > 0:
                p.append(f'<div class="more">+ {rest:,} more in library/index.json</div>')
            p.append('</details>')

    p.append('<footer>built from library/index.json · rebuild with '
             'build_library.py then this script · strongest heat signal first '
             'where one exists (live creatives, views)<br>'
             'origins: swiped = ran in the wild · ours = we shipped it · '
             'machine output filed separately, never as evidence</footer></div>')
    OUT.write_text("".join(p), encoding="utf-8")
    print(f"{OUT.name}: {OUT.stat().st_size:,} bytes · {len(rows):,} evidence rows")


if __name__ == "__main__":
    build()
