#!/usr/bin/env python3
"""The copy channel map, generated — the master board.

    python3 channel_map_page.py

Three data files in, one page out:
    channel-map.json    the channels and which formats live on each
    format-bank.json    the full spec of every format on every channel
    library/index.json   live evidence counts, joined at build time

Edit a spec row, re-run, the board redraws. Nothing on the page is typed
into the page.
"""
import html, json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent   # the package root
OUT = HERE / "pages" / "copy-channel-map.html"


def esc(s):
    return html.escape(str(s))


def counts():
    """library format -> {origin: n}, machine excluded."""
    out = {}
    try:
        rows = json.loads((HERE / "library" / "index.json").read_text())["rows"]
    except Exception:
        return out
    for r in rows:
        if r["origin"] == "machine":
            continue
        d = out.setdefault(r["format"], {})
        d[r["origin"]] = d.get(r["origin"], 0) + 1
    return out


PROV_CLS = {"proven": "ok", "evidenced": "ev", "drafted": "dr"}

CSS = """
:root{
  --ground:#F1F2F0; --surface:#FFFFFF; --surface-2:#F7F8F6;
  --ink:#161A18; --body:#3B403D; --dim:#6C726E; --dimmer:#949A96;
  --line:#DFE3DF; --line-2:#ECEFEB;
  --accent:#1F4E5F; --accent-soft:#DCE8EA;
  --gold:#8A5A1F; --gold-soft:#F4EBDD;
  --ok:#2C6B60; --ok-soft:#E3EFEC;
  --display:"Bricolage Grotesque",system-ui,sans-serif;
  --serif:"Source Serif 4",Georgia,serif;
  --mono:"JetBrains Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#121513; --surface:#1A1E1C; --surface-2:#171A18;
  --ink:#ECEFEA; --body:#CDD3CE; --dim:#98A09A; --dimmer:#6B726D;
  --line:#2B302D; --line-2:#232725;
  --accent:#7FC2CE; --accent-soft:#16302F;
  --gold:#D9A85D; --gold-soft:#2B2114;
  --ok:#5FB3A4; --ok-soft:#162925;
}}
:root[data-theme="dark"]{
  --ground:#121513; --surface:#1A1E1C; --surface-2:#171A18;
  --ink:#ECEFEA; --body:#CDD3CE; --dim:#98A09A; --dimmer:#6B726D;
  --line:#2B302D; --line-2:#232725;
  --accent:#7FC2CE; --accent-soft:#16302F;
  --gold:#D9A85D; --gold-soft:#2B2114;
  --ok:#5FB3A4; --ok-soft:#162925;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--body);
  font:16.5px/1.6 var(--serif);-webkit-font-smoothing:antialiased;padding:0 20px 90px}
.wrap{max-width:54rem;margin:0 auto}
header.top{padding:56px 0 8px}
.eyebrow{font:600 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
h1{font-family:var(--display);font-size:clamp(30px,5vw,44px);line-height:1.04;
  margin:14px 0 0;letter-spacing:-.02em;color:var(--ink);font-weight:700;text-wrap:balance}
.stand{font-size:17px;color:var(--dim);margin-top:14px;max-width:37rem}

.brain{margin:32px 0 8px;background:var(--surface);border:1px solid var(--line);
  border-left:3px solid var(--accent);border-radius:8px;padding:18px 24px}
.brain b{color:var(--ink)}
.brain .l{font:600 10px var(--mono);letter-spacing:.1em;text-transform:uppercase;
  color:var(--accent);display:block;margin-bottom:8px}
.brain p{margin:0;max-width:42rem}

.legend{display:flex;gap:16px;flex-wrap:wrap;margin:18px 0 0;font:500 12px var(--mono);color:var(--dim)}
.legend .p{display:flex;align-items:center;gap:6px}
.dot{width:9px;height:9px;border-radius:5px;display:inline-block}
.dot.ok{background:var(--ok)} .dot.ev{background:var(--gold)} .dot.dr{background:var(--dimmer)}


.glance{background:var(--surface);border:1px solid var(--line);border-radius:10px;
  padding:20px 26px 14px;margin:22px 0}
.glance h3{font-family:var(--display);font-size:15px;margin:0 0 4px;color:var(--ink);font-weight:700}
.glance .gs{font-size:13.5px;color:var(--dimmer);margin:0 0 14px}
.g-ch{font:700 11px var(--mono);letter-spacing:.09em;text-transform:uppercase;
  color:var(--accent);margin:14px 0 6px}
.g-row{display:grid;grid-template-columns:11rem 1fr 4.5rem;gap:10px;align-items:center;
  padding:3px 0}
.g-row .n{font-size:13.5px;color:var(--ink);font-weight:600;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.g-bar{height:12px;border-radius:6px;background:var(--line-2);position:relative;overflow:hidden}
.g-fill{position:absolute;top:0;bottom:0;left:0;border-radius:6px}
.g-fill.ok{background:var(--ok)} .g-fill.ev{background:var(--gold)} .g-fill.dr{background:var(--dimmer)}
.g-n{font:600 11.5px var(--mono);color:var(--dim);text-align:right;font-variant-numeric:tabular-nums}

.ch{background:var(--surface);border:1px solid var(--line);border-radius:10px;
  margin:26px 0;overflow:hidden}
.ch-h{padding:20px 26px 16px;border-bottom:1px solid var(--line-2)}
.ch-h .n{font:700 12px var(--mono);color:var(--accent);letter-spacing:.06em}
.ch-h h2{font-family:var(--display);font-size:24px;margin:6px 0 0;color:var(--ink);
  font-weight:700;letter-spacing:-.015em;line-height:1.15}
.ch-h .state{margin:6px 0 0;font-size:15.5px;color:var(--dim);font-style:italic}

details{border-top:1px solid var(--line-2)}
details:first-of-type{border-top:0}
summary{cursor:pointer;padding:13px 26px;display:flex;align-items:baseline;gap:12px;list-style:none}
summary::-webkit-details-marker{display:none}
summary .f{font-family:var(--display);font-weight:700;font-size:16.5px;color:var(--ink)}
summary .w{color:var(--dim);font-size:14px}
summary .ev{margin-left:auto;font:600 11px var(--mono);color:var(--gold);white-space:nowrap;
  font-variant-numeric:tabular-nums}
.spec{padding:4px 26px 18px;background:var(--surface-2)}
.spec dl{display:grid;grid-template-columns:10rem 1fr;margin:0}
.spec dt{font:600 10px var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--dim);
  padding:8px 0;border-top:1px solid var(--line-2)}
.spec dd{margin:0;padding:8px 0;border-top:1px solid var(--line-2);font-size:15px}
.spec dt.rq,.spec dd.rq{color:var(--gold)}
.prov{font:500 12px var(--mono);padding:10px 0 2px;display:flex;gap:8px;align-items:center}
.prov.ok{color:var(--ok)} .prov.ev{color:var(--gold)} .prov.dr{color:var(--dimmer)}

.owners{display:grid;grid-template-columns:repeat(auto-fit,minmax(14rem,1fr));gap:14px;margin:8px 0 0}
.own{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:15px 18px}
.own .k{font:600 10px var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--dim)}
.own h4{font-family:var(--display);font-size:16.5px;margin:5px 0 4px;color:var(--ink);font-weight:700}
.own p{margin:0;font-size:14px;color:var(--dim);line-height:1.5}
h2.sec{font-family:var(--display);font-size:13px;letter-spacing:.11em;text-transform:uppercase;
  color:var(--dim);font-weight:700;margin:44px 0 10px;padding-bottom:8px;border-bottom:1px solid var(--line)}
ol.next{margin:8px 0 0;padding-left:1.4rem}
ol.next li{margin:0 0 10px;max-width:40rem}
footer{margin-top:48px;padding-top:18px;border-top:1px solid var(--line);
  font:12px/1.7 var(--mono);color:var(--dimmer)}
@media(max-width:560px){.spec dl{grid-template-columns:1fr}
  .spec dt{padding-bottom:0}.spec dd{padding-top:3px;border-top:0}}
"""


def build():
    cmap = json.loads((HERE / "bank" / "channel-map.json").read_text(encoding="utf-8"))
    bank = {f["key"]: f for f in
            json.loads((HERE / "bank" / "format-bank.json").read_text(encoding="utf-8"))["formats"]}
    cnt = counts()
    total_ev = sum(sum(v.values()) for v in cnt.values())
    n_formats = sum(len(c["formats"]) for c in cmap["channels"])
    proven = sum(1 for f in bank.values() if f["provenance"].startswith("proven"))
    drafted = sum(1 for f in bank.values() if f["provenance"].startswith("drafted"))

    p = ['<title>Copy Channel Map</title>',
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&'
         'family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&'
         'family=JetBrains+Mono:wght@500;600;700&display=swap">',
         f"<style>{CSS}</style>",
         '<div class="wrap"><header class="top">',
         '<div class="eyebrow">the copy brain · the master board</div>',
         '<h1>The copy channel map</h1>',
         f'<p class="stand">{n_formats} formats across four channels, each with its '
         f'full writing spec and live evidence counts from the copy library '
         f'({total_ev:,} pieces). Generated from data — edit a spec row in '
         f'format-bank.json and the board redraws.</p></header>',
         f'<div class="brain"><span class="l">the operating principle</span>'
         f'<p>{esc(cmap["principle"]).replace("one brain", "<b>one brain</b>", 1)}</p></div>',
         '<div class="legend">'
         f'<span class="p"><span class="dot ok"></span>proven — a machine writes it today ({proven})</span>'
         f'<span class="p"><span class="dot ev"></span>evidenced — spec derived from library</span>'
         f'<span class="p"><span class="dot dr"></span>drafted — first-principles, refine me ({drafted})</span>'
         '</div>']

    # ── the bank at a glance: one picture, no clicks ──
    import math
    top = max((sum(sum(cnt.get(ck, {}).values()) for ck in fm.get("library", [])) or 1)
              for c in cmap["channels"] for fm in c["formats"])
    p.append('<div class="glance"><h3>The bank at a glance</h3>'
             '<p class="gs">One row per format. Bar length = evidence held in the copy library '
             '(square-root scale, so small counts stay visible). Colour = proven / evidenced / drafted.</p>')
    for ch in cmap["channels"]:
        p.append(f'<div class="g-ch">{esc(ch["name"])} — {esc(ch["state"]).lower()}</div>')
        for fm in ch["formats"]:
            spec = bank.get(fm["key"], {})
            cls = next((v for k, v in PROV_CLS.items()
                        if spec.get("provenance", "drafted").startswith(k)), "dr")
            ev = sum(sum(cnt.get(ck, {}).values()) for ck in fm.get("library", []))
            w = round(math.sqrt(ev) / math.sqrt(top) * 100, 1) if ev else 1.5
            p.append(f'<div class="g-row"><span class="n">{esc(fm["name"])}</span>'
                     f'<span class="g-bar"><span class="g-fill {cls}" style="width:{w}%"></span></span>'
                     f'<span class="g-n">{ev:,}</span></div>')
    p.append('</div>')

    for i, ch in enumerate(cmap["channels"], 1):
        p.append(f'<article class="ch"><div class="ch-h">'
                 f'<span class="n">{i} · {esc(ch["name"]).upper()}</span>'
                 f'<h2>{esc(ch["state"])}</h2>'
                 f'<p class="state">{esc(ch["line"])}</p></div>')
        for fm in ch["formats"]:
            spec = bank.get(fm["key"])
            ev = sum(sum(cnt.get(ck, {}).values()) for ck in fm.get("library", []))
            ev_s = f'{ev:,} in library' if ev else "no evidence yet"
            p.append(f'<details open><summary><span class="f">{esc(fm["name"])}</span>'
                     f'<span class="w">{esc(fm["what"])}</span>'
                     f'<span class="ev">{ev_s}</span></summary>')
            if spec:
                cls = next((v for k, v in PROV_CLS.items()
                            if spec["provenance"].startswith(k)), "dr")
                L = spec.get("length", {})
                p.append('<div class="spec"><dl>')
                p.append(f'<dt>Length</dt><dd>{L.get("min")}–{L.get("max")} {esc(L.get("unit",""))}</dd>')
                for key, lab in (("form", "Form"), ("opens_with", "Opens with"),
                                 ("carries_offer", "Carries the offer"),
                                 ("reads_as", "Reads as")):
                    p.append(f'<dt>{lab}</dt><dd>{esc(spec[key])}</dd>')
                if spec.get("requires"):
                    p.append(f'<dt class="rq">Requires</dt><dd class="rq">{esc(spec["requires"])}</dd>')
                p.append(f'<dt>Variations</dt><dd><b>{spec.get("variations")}</b> per source</dd>')
                p.append('</dl>'
                         f'<div class="prov {cls}"><span class="dot {cls}"></span>'
                         f'{esc(spec["provenance"])}</div></div>')
            else:
                p.append('<div class="spec"><div class="prov dr">'
                         f'<span class="dot dr"></span>spec via {esc(fm.get("spec","?"))}</div></div>')
            p.append('</details>')
        p.append('</article>')

    p.append('<h2 class="sec">Who owns what today</h2><div class="owners">')
    for o in cmap["owners"]:
        p.append(f'<div class="own"><span class="k">channels {esc(o["channels"])}</span>'
                 f'<h4>{esc(o["name"])}</h4><p>{esc(o["line"])}</p></div>')
    p.append('</div><h2 class="sec">The sequence</h2><ol class="next">')
    for s in cmap["sequence"]:
        p.append(f'<li>{esc(s)}</li>')
    p.append('</ol>')
    p.append('<footer>generated by channel_map_page.py from channel-map.json + '
             'format-bank.json + library/index.json · a channel is the reader\'s '
             'state when the words arrive — everything else follows from it<br>'
             'md mirror: docs/copy-channel-map.md · evidence counts exclude machine output</footer></div>')
    OUT.write_text("".join(p), encoding="utf-8")
    print(f"{OUT.name}: {OUT.stat().st_size:,} bytes · {n_formats} formats · {total_ev:,} evidence pieces joined")


if __name__ == "__main__":
    build()
