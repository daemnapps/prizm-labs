#!/usr/bin/env python3
"""tiers_page — the ranked assets of every brand on one page: top 1% in full, top 2–5% and 6–10%
listed, under top 10% documented. Reads runs/media-buying/<brand>/tiers/<latest>/tiers.json.

    tiers_page.py        writes runs/media-buying/tiers.html and its mirror TIERS-damon.md
"""
import html, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
BASE = WS / "runs" / "media-buying"
LABEL = {"top-1": "Top 1%", "top-5": "Top 2–5%", "top-10": "Top 6–10%", "under-10": "Under top 10%"}
e = lambda s: html.escape(str(s if s is not None else ""))


def latest(brand):
    runs = sorted((BASE / brand / "tiers").glob("*/tiers.json"))
    return json.loads(runs[-1].read_text()) if runs else None


def money(x):
    return f"${x:,.0f}" if x is not None else "—"


def cpa(x):
    return f"${x:,.2f}" if x else "—"


def kind(g):
    return {"set": f"flexible ad · {len(g.get('media') or [])} videos/images", "video": "video", "image": "image",
            "ad": "no media on file"}.get(g["kind"], g["kind"])


def full(g):
    link = f'<a href="{e(g["instagram"])}" target="_blank" rel="noopener">watch it ↗</a>' if g.get("instagram") else "no post link on file"
    texts = "".join(f'<div class="txt">{e(t).replace(chr(10), "<br>")}</div>' for t in g["primary"][:3]) or '<div class="sm">no words on file</div>'
    more = f'<div class="sm">+{len(g["primary"]) - 3} more texts</div>' if len(g["primary"]) > 3 else ""
    heads = " · ".join(e(h) for h in g["headlines"][:5])
    names = ", ".join(e(a["ad_name"]) for a in g["ads"][:4]) + (f" +{len(g['ads']) - 4}" if len(g["ads"]) > 4 else "")
    return f'''<div class="card"><div class="top"><span class="rk">#{g["rank"]}</span><b>{int(g["purchases"]):,} purchases</b> · {money(g["spend"])} spend · CPA <b>{cpa(g["cpa"])}</b> · ROAS {g["roas"] or "—"} · {link}</div>
<div class="sm">{kind(g)} · ran in {len(g["ads"])} ad{"s" if len(g["ads"]) != 1 else ""} ({names}) · {e(g["first_day"])} → {e(g["last_day"])}</div>
{f'<div class="sm"><b>Headlines:</b> {heads}</div>' if heads else ""}{texts}{more}</div>'''


def row(g):
    link = f'<a href="{e(g["instagram"])}" target="_blank" rel="noopener">↗</a>' if g.get("instagram") else ""
    first = (g["primary"] or [""])[0].split("\n")[0][:110]
    return (f'<tr><td>{g["rank"]}</td><td>{int(g["purchases"]):,}</td><td>{money(g["spend"])}</td><td>{cpa(g["cpa"])}</td>'
            f'<td>{len(g["ads"])}</td><td>{e(g["ads"][0]["ad_name"])[:60]}</td><td>{e(first)}</td><td>{link}</td></tr>')


def table(rows):
    return ('<div class="scroll"><table><tr><th>#</th><th>Purchases</th><th>Spend</th><th>CPA</th><th>Ads</th>'
            '<th>First ad name</th><th>Opening line</th><th></th></tr>' + "".join(row(g) for g in rows) + "</table></div>")


def brand_section(name, d):
    s, rows = d["summary"], d["rows"]
    by = {t: [g for g in rows if g["tier"] == t] for t in LABEL}
    bars = "".join(f'<div class="bar"><div class="bl">{LABEL[t]} <span class="sm">· {s[t]["assets"]} assets</span></div>'
                   f'<div class="bt"><div class="bf t{t[-1] if t != "under-10" else "u"}" style="width:{s[t]["share_of_purchases"]}%"></div></div>'
                   f'<div class="bn">{s[t]["share_of_purchases"]}% of purchases · {s[t]["share_of_spend"]}% of spend · CPA {cpa(s[t]["cpa"])}</div></div>'
                   for t in LABEL)
    return f'''<section id="{e(d["brand"])}"><h2>{e(name)}</h2>
<p class="sm" style="margin:0">{d["ads"]:,} ads, {e(d["window"]["from"])} to {e(d["window"]["to"])} → <b>{d["assets"]:,} real assets</b> (each video, image or flexible-ad set once, every ad that ran it folded in) · ranked by purchases.</p>
<div class="bars">{bars}</div>
<h3>Top 1% — {len(by["top-1"])} assets</h3><div class="cards">{"".join(full(g) for g in by["top-1"])}</div>
<h3>Top 2–5% — {len(by["top-5"])} assets</h3>{table(by["top-5"])}
<h3>Top 6–10% — {len(by["top-10"])} assets</h3>{table(by["top-10"])}
<details><summary>Under top 10% — {len(by["under-10"])} assets, documented ({s["under-10"]["share_of_spend"]}% of spend, {s["under-10"]["share_of_purchases"]}% of purchases, CPA {cpa(s["under-10"]["cpa"])})</summary><p class="sm">The first 100 shown; all {len(by["under-10"])} are kept in the tiers file.</p>{table(by["under-10"][:100])}</details>
</section>'''


def page(brands):
    secs = "".join(brand_section(n, d) for n, d in brands)
    return f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Top 1% Ads</title>
<style>:root{{--bg:#f2f4f7;--p:#fff;--ink:#161b24;--soft:#5b6575;--line:#d8dee8;--acc:#3554c8;--t1:#1f7a4a;--t5:#5aa676;--t0:#9fcfb0;--u:#c9ced8}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#11141a;--p:#181d26;--ink:#e5e9f0;--soft:#9aa4b5;--line:#2a3240;--acc:#8fa6f5;--t1:#74d39c;--t5:#4c9a6a;--t0:#2f6a48;--u:#3a4250}}}}
body{{background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif;margin:0}}.w{{max-width:1000px;margin:0 auto;padding:24px 16px 60px;display:grid;gap:18px}}
section{{background:var(--p);border:1px solid var(--line);border-radius:10px;padding:18px;display:grid;gap:12px;min-width:0}}h1,h2{{margin:0}}h3{{margin:8px 0 0;font-size:1rem}}
.sm{{color:var(--soft);font-size:.82rem}}.call{{border:2px solid var(--acc)}}.cards{{display:grid;gap:10px}}.card{{border:1px solid var(--line);border-radius:8px;padding:12px;display:grid;gap:4px;min-width:0}}
.rk{{display:inline-block;background:var(--t1);color:var(--p);border-radius:6px;padding:0 6px;margin-right:6px;font-weight:700}}.txt{{font-size:.88rem;border-left:3px solid var(--line);padding-left:8px;margin-top:4px;overflow-wrap:anywhere}}
.bars{{display:grid;gap:6px}}.bar{{display:grid;grid-template-columns:170px 1fr 300px;gap:10px;align-items:center;font-size:.88rem}}.bt{{background:var(--bg);border-radius:4px;height:14px}}.bf{{height:14px;border-radius:4px}}
.t1{{background:var(--t1)}}.t5{{background:var(--t5)}}.t0{{background:var(--t0)}}.tu{{background:var(--u)}}@media (max-width:700px){{.bar{{grid-template-columns:1fr}}}}
table{{border-collapse:collapse;width:100%;font-size:.84rem}}td,th{{text-align:left;padding:5px 7px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--soft);font-weight:600}}.scroll{{overflow-x:auto}}
details summary{{cursor:pointer;font-weight:600;margin-top:8px}}a{{color:var(--acc)}}</style>
<div class="w"><header><h1>Top 1% Ads</h1><p class="sm">Every real asset each brand ran, ranked by purchases. Only the top 10% gets worked on; everything under it is documented. From our database's copy of Meta — no Meta calls.</p></header>
<section class="call"><h2>The goal</h2><p style="margin:0">"That's the goal: to create 1% top ads all the time." the owner, 2 Oct. Rank everything, work only on the top 10%, and find out why the bottom 90% isn't the top 1% — against our marketing doctrine, the avatars, the research and the brand — so the system has pass/fail rules and stops repeating what the bottom 90% did.</p></section>
{secs}
<section><h2>The words on this page</h2><p class="sm" style="margin:0"><b>Real asset</b>: one video or image (or one flexible ad's set of them), shown once with every ad that ran it folded in. <b>Ranked by</b>: purchases driven. <b>Tiers</b> are by count of assets: top 1% = the first 1% of assets, and so on. <b>CPA</b> = spend ÷ purchases. A flexible ad's set is one asset because Meta doesn't split its sales by video.</p></section></div>'''


def main():
    brands = [(n, latest(b)) for b, n in (("brand-b", "Brand B"), ("brand-a", "Brand A"))]
    brands = [(n, d) for n, d in brands if d]
    out = BASE / "tiers.html"
    out.write_text(page(brands))
    md = ["# Top 1% Ads", "", "Every real asset each brand ran, ranked by purchases (from the warehouse copy of Meta). "
          "the owner, 2 Oct 2026: \"That's the goal: to create 1% top ads all the time.\"", ""]
    for n, d in brands:
        md += [f"## {n}", f"{d['ads']:,} ads, {d['window']['from']} to {d['window']['to']} → {d['assets']:,} real assets.", "",
               "| Tier | Assets | Share of purchases | Share of spend | CPA |", "|---|---|---|---|---|"]
        md += [f"| {LABEL[t]} | {v['assets']} | {v['share_of_purchases']}% | {v['share_of_spend']}% | {cpa(v['cpa'])} |"
               for t, v in d["summary"].items()]
        md += ["", "Top 1%:", ""] + [f"{g['rank']}. {int(g['purchases']):,} purchases · {money(g['spend'])} · CPA {cpa(g['cpa'])} · "
                                     f"{len(g['ads'])} ads · {g['ads'][0]['ad_name']} — \"{((g['primary'] or ['(no words on file)'])[0].splitlines() or [''])[0][:100]}\""
                                     for g in d["rows"] if g["tier"] == "top-1"] + [""]
    (BASE / "TIERS-damon.md").write_text("\n".join(md) + "\n")
    print(f"wrote {out.relative_to(WS)} and TIERS-damon.md")


if __name__ == "__main__":
    main()
