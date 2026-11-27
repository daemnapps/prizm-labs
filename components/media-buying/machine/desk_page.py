#!/usr/bin/env python3
"""desk_page.py — the Ad Desk page for owner: the ads themselves, grouped by the call to make, his calls beside them.

    python3 desk_page.py brand_b --out <page.html>

Reads runs/media-buying/<brand>/<latest>/report.json and decisions.jsonl, and each ad's own picture from the
warehouse's copy of the ad (creative.py — no Meta API), kept in <run>/art/. Writes one self-contained page
(published to the brand's one Ad Desk artifact — private, his). Picture-first: owner decides by looking
(5 Oct 2026: "I can't see any of the ads... I need to visualize this to make clear decisions").
"""
import argparse, html, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze as A
import creative as CR
import decide as D

GROUPS = [("off", "Turn off", "cut", "Bleeding — past the kill line, nothing working."),
          ("pull_up", "Your call", "ask", "Past a kill line, but something is working."),
          ("double_down", "Double down", "top", "Selling under break-even. Make more like these."),
          ("watch", "Watch", "watch", "Between the lines."),
          ("keep", "Keep", "good", "Within range.")]
TONE = {k: t for k, _, t, _ in GROUPS} | {"budget_down": "cut", "budget_up": "top", "budget_hold": "good", "too_early": "soft"}
LABEL = {k: l for k, l, _, _ in GROUPS} | {"too_early": "Too early", "budget_down": "Budget down", "budget_up": "Budget up", "budget_hold": "Hold"}
NOISE = set("brand_b brilliancebodyscrub bodyscrub brilliance body scrub static ai none spothider darkspots pigmentmemory proaging "
            "9x16 1x1 batch brief advertorial us offerpage quiz cpk".split())
e = html.escape


def money(v):
    return "—" if v is None else f"${v:,.0f}" if abs(v) >= 100 else f"${v:,.2f}"


def short(name):
    """A name a person can read: the words that differ between ads."""
    words = [w for w in re.split(r"[-_ ]+", name or "") if w and w.lower() not in NOISE
             and not re.fullmatch(r"(p\d+|\d{6}[a-z]|20\d\d|\d\d|[a-z]?\d+)", w.lower())]
    s = " ".join(words) or name
    return s[:46] + ("…" if len(s) > 46 else "")


def img(uri):
    return f'<img src="{uri}" alt="" loading="lazy">' if uri else ""


def tile(f, uri, src, call):
    be = f.get("break_even") or 0
    c = f.get("cpa7") or f.get("cpa")
    x = (c / be) if (c and be) else None
    href = (src or {}).get("preview") or ""
    pic = img(uri) or '<div class="noimg">no picture</div>'
    over = (f'<div class="over"><b>{money(c)}</b><span>{x:.1f}× break-even</span></div>' if x else
            f'<div class="over"><b>0 sales</b><span>{money(f.get("spend"))} spent</span></div>')
    mine = f'<div class="mine {"agree" if call["agreed"] else "over"}">You: {e(call["said"])}</div>' if call else ""
    link = f'href="{e(href)}" target="_blank" rel="noopener"' if href else ""
    return f"""<a class="tile {TONE[f['action']]}" {link}>
<div class="pic">{pic}<span class="badge">{f['flag']}</span>{'<span class="vid">▶</span>' if (src or {}).get('is_video') else ''}{over}</div>
<div class="meter"><span class="fill" style="width:{min(100, (x or 0) / 2 * 100):.0f}%"></span><span class="be"></span></div>
<div class="mini"><span>{money(f.get('_s7', 0))} this week</span><span>{f.get('purchases', 0)} sales</span><span>BE {money(be)}</span></div>
<div class="nm" title="{e(f['name'])}">{e(short(f['name']))}</div>{mine}</a>"""


def thumb(a, uri, cap):
    return f'<figure class="th {TONE[a["action"]]}" title="{e(a["flag"] + " · " + short(a["name"]))}">{img(uri)}<figcaption>{cap}</figcaption></figure>'


def build(brand):
    run = D.latest(brand)
    r = json.loads((run / "report.json").read_text())
    if r.get("rule"):
        import windows_page
        return windows_page.build(brand, run, r)
    dp = A.desk_dir(brand) / "decisions.jsonl"
    every = [json.loads(x) for x in dp.read_text().splitlines() if x.strip()] if dp.exists() else []
    calls = {c["flag"]: c for c in every if c["asof"] == r["asof"]}
    lg = D.log(brand)
    s, flags = r["store"], r["flags"]
    camps = {f["name"]: f for f in flags if f["kind"] == "campaign"}
    ads = [f for f in flags if f["kind"] == "ad"]
    for a in ads:
        c = camps.get(a["campaign"])
        a["_s7"] = (a.get("share7") or 0) / 100 * (c["spend7"] if c else 0)
    uris, src = CR.fetch(run, [a["id"] for a in ads])

    # the four numbers
    need = s["store_revenue"] / s["store_contribution"] if s["store_contribution"] else None
    gap = (s["blended_cpa"] or 0) - (s["contribution_per_order"] or 0)
    kpis = [("Store after ads · 7 days", ("−" if s["after_ads"] < 0 else "+") + money(abs(s["after_ads"])), s["after_ads"] >= 0, "contribution minus all Meta spend"),
            ("Blended CPA", money(s["blended_cpa"]), gap <= 0, f"needs to be under {money(s['contribution_per_order'])}"),
            ("Return on all spend", f"{s['mer']:.2f}×" if s["mer"] else "—", bool(s["mer"] and need and s["mer"] >= need), f"even at {need:.2f}×" if need else ""),
            ("Orders · 7 days", str(s["store_orders"]), True, f"{money(s['store_revenue'])} revenue")]
    tiles_k = "".join(f'<div class="kpi {"ok" if ok else "bad"}"><span>{e(k)}</span><b>{e(v)}</b><small>{e(n)}</small></div>' for k, v, ok, n in kpis)

    # where this week's money went
    order = ["double_down", "keep", "watch", "pull_up", "off", "too_early"]
    spent = {k: sum(a["_s7"] for a in ads if a["action"] == k) for k in order}
    tot = sum(spent.values()) or 1
    bar = "".join(f'<span class="seg {TONE[k]}" style="flex:{max(spent[k], tot * 0.012):.2f}"></span>' for k in order if spent[k] > 0)
    key = "".join(f'<span><i class="dot {TONE[k]}"></i>{LABEL[k]} <b>{money(spent[k])}</b> {100 * spent[k] / tot:.0f}%</span>' for k in order if spent[k] > 0)

    # campaigns, with their ads
    cblocks = ""
    for c in camps.values():
        be = c["break_even"] or 1
        meters = "".join(f'<div class="cm"><span>{lbl}</span><div class="meter"><span class="fill {TONE[c["action"]]}" style="width:{min(100, (v or 0) / (be * 2) * 100):.0f}%"></span><span class="be"></span></div><b>{money(v)}</b></div>'
                         for lbl, v in (("3 days", c.get("cpa3")), ("7 days", c.get("cpa7"))))
        mine = sorted((a for a in ads if a["campaign"] == c["name"] and a["_s7"] > 0), key=lambda a: -a["_s7"])
        strip = "".join(thumb(a, uris.get(a["id"]), money(a["_s7"])) for a in mine[:10])
        cblocks += (f'<div class="camp {TONE[c["action"]]}"><div class="ch"><span class="pill {TONE[c["action"]]}">{c["flag"]} · {LABEL[c["action"]]}</span>'
                    f'<b>{e(c["name"])}</b><small>{money(c["spend7"])} this week · {c["purchases7"]} sales · break-even {money(be)}</small></div>'
                    f'{meters}<div class="strip">{strip}</div><small class="soft">Its ads by this week\'s spend, biggest first.</small></div>')

    # the account on one map — every ad with a sale, as its own picture
    pts = [a for a in ads if (a.get("cpa7") or a.get("cpa")) and a.get("break_even")]
    W, H, P = 680, 340, 44
    xmax = max([a["_s7"] for a in pts] + [1]) * 1.12
    ymax = 3.0
    X = lambda v: P + 34 + (W - 2 * P - 34) * (min(v, xmax) / xmax) ** 0.5   # square-root scale: small spenders spread out
    Y = lambda v: H - P - (H - 2 * P) * min(v, ymax) / ymax
    defs, marks = "", ""
    for i, a in enumerate(pts):
        m = (a.get("cpa7") or a["cpa"]) / a["break_even"]
        rr = 13 + min(13, (a["spend"] ** 0.5) / 14)
        cx, cy = (X(a["_s7"]) if a["_s7"] > 0.5 else P + 10 + (i % 3) * 12), Y(m)   # not spending this week: the left lane
        defs += f'<clipPath id="c{i}"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}"/></clipPath>'
        pic = (f'<image href="{uris[a["id"]]}" x="{cx - rr:.1f}" y="{cy - rr:.1f}" width="{2 * rr:.1f}" height="{2 * rr:.1f}" '
               f'preserveAspectRatio="xMidYMid slice" clip-path="url(#c{i})"/>') if uris.get(a["id"]) else ""
        marks += (f'<g><title>{e(a["flag"])} {e(short(a["name"]))} — {money(a.get("cpa7") or a["cpa"])} = {m:.1f}× break-even · {money(a["_s7"])} this week</title>'
                  f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr + 2.5:.1f}" class="ring {TONE[a["action"]]}"/>{pic}'
                  f'<text x="{cx:.1f}" y="{cy - rr - 6:.1f}" class="lb" text-anchor="middle">{e(a["flag"])}</text></g>')
    bands = (f'<rect x="{P}" y="{Y(0.8):.1f}" width="{W - 2 * P}" height="{Y(0) - Y(0.8):.1f}" class="band top"/>'
             f'<rect x="{P}" y="{Y(ymax):.1f}" width="{W - 2 * P}" height="{Y(1.5) - Y(ymax):.1f}" class="band cut"/>'
             f'<line x1="{P}" x2="{W - P}" y1="{Y(1):.1f}" y2="{Y(1):.1f}" class="beline"/>'
             f'<text x="{W - P - 4}" y="{Y(1) - 6:.1f}" class="ax" text-anchor="end">break-even</text>'
             f'<text x="{W - P - 4}" y="{Y(0) - 8:.1f}" class="ax" text-anchor="end">making money · double down</text>'
             f'<text x="{W - P - 4}" y="{Y(ymax) + 16:.1f}" class="ax" text-anchor="end">losing money · cut</text>')
    ticks = "".join(f'<text x="{P - 8}" y="{Y(t) + 4:.1f}" class="ax" text-anchor="end">{t:g}×</text>' for t in (0, 1, 2, 3))
    ticks += f'<text x="{P + 22}" y="{H - P + 18}" class="ax" text-anchor="middle">none</text>'
    ticks += "".join(f'<text x="{X(v):.1f}" y="{H - P + 18}" class="ax" text-anchor="middle">{money(v)}</text>' for v in (xmax / 16, xmax / 4, xmax))
    svg = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Every ad with a sale, by this week\'s spend and its cost per sale"><defs>{defs}</defs>{bands}{ticks}'
           f'<text x="{W / 2}" y="{H - 6}" class="ax" text-anchor="middle">more spend this week →</text>'
           f'<text x="14" y="{H / 2}" class="ax" transform="rotate(-90 14 {H / 2})" text-anchor="middle">more expensive per sale ↑</text>{marks}</svg>')

    groups = ""
    for k, title, tone, means in GROUPS:
        fs = sorted((a for a in ads if a["action"] == k), key=lambda a: -(a["_s7"] or a["spend"]))
        if fs:
            groups += (f'<section class="grp"><h2><span class="pill {tone}">{title}</span> {len(fs)} ad{"s" if len(fs) > 1 else ""}</h2><p class="soft">{means}</p>'
                       f'<div class="grid">{"".join(tile(a, uris.get(a["id"]), src.get(a["id"]), calls.get(a["flag"])) for a in fs)}</div></section>')
    early = sorted((a for a in ads if a["action"] == "too_early"), key=lambda a: -a["spend"])
    wall = "".join(thumb(a, uris.get(a["id"]), money(a["spend"])) for a in early)
    fs_ = sorted(((k, v) for k, v in r.get("store_funnels", {}).items() if v["orders"] >= 3), key=lambda kv: -kv[1]["orders"])
    fmax = max([v["aov"] for _, v in fs_] + [1])
    fun = "".join(f'<div class="fn"><span class="nm">{e(k)}<small>{v["orders"]} orders</small></span><div class="fb"><span class="aov" style="width:{v["aov"] / fmax * 100:.0f}%"></span>'
                  f'<span class="ear" style="width:{v["contribution_per_order"] / fmax * 100:.0f}%"></span></div><b>{money(v["contribution_per_order"])}<small> of {money(v["aov"])}</small></b></div>' for k, v in fs_)
    agree = "".join(f"<li><b>{e(LABEL.get(k, k))}</b>: you agreed {v['agreed']} of {v['calls']}"
                    + (" · changed to " + ", ".join(f"{n}× {LABEL.get(c, c)}" for c, n in v["overruled_to"].items()) if v["overruled_to"] else "") + "</li>"
                    for k, v in lg["by_suggestion"].items()) or "<li>No calls yet. Say the flag and your call, with why.</li>"
    n_calls = sum(1 for f in flags if f["action"] in ("off", "pull_up", "budget_down", "budget_up", "double_down"))
    return f"""<title>Ad Desk</title>
<style>
:root{{--bg:#f3f1ec;--panel:#fff;--ink:#17181b;--soft:#646a72;--line:#e1ddd5;--top:#16794a;--top-soft:#e0f1e7;--good:#4f9b70;--watch:#a86f00;--watch-soft:#fbefd6;--cut:#c0442a;--cut-soft:#f8e1d9;--ask:#3150c2;--ask-soft:#e5eafb;--shade:rgba(0,0,0,.62);--on:#fff}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#121315;--panel:#1b1c1f;--ink:#ebebe8;--soft:#9aa0a8;--line:#2c2e33;--top:#4fb37f;--top-soft:#16301f;--good:#56a877;--watch:#d39a3a;--watch-soft:#3a2d12;--cut:#e0705a;--cut-soft:#3b1d16;--ask:#6f8ae8;--ask-soft:#1c2546;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#121315;--panel:#1b1c1f;--ink:#ebebe8;--soft:#9aa0a8;--line:#2c2e33;--top:#4fb37f;--top-soft:#16301f;--good:#56a877;--watch:#d39a3a;--watch-soft:#3a2d12;--cut:#e0705a;--cut-soft:#3b1d16;--ask:#6f8ae8;--ask-soft:#1c2546;color-scheme:dark}}
body{{background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0}}
.w{{max-width:1080px;margin:0 auto;padding-inline:16px;padding-block:24px 60px;display:grid;gap:18px}}
h1{{font-size:clamp(1.8rem,5vw,2.7rem);margin:0;letter-spacing:-.02em}} h2{{margin:0;font-size:1.1rem;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.soft{{color:var(--soft);margin:0;font-size:.88rem}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}}
.kpi{{border-radius:12px;padding:12px 14px;display:grid;gap:2px}} .kpi span{{font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;color:var(--soft)}}
.kpi b{{font-size:1.8rem;font-variant-numeric:tabular-nums;line-height:1.1}} .kpi small{{color:var(--soft);font-size:.8rem}}
.kpi.bad{{background:var(--cut-soft)}} .kpi.bad b{{color:var(--cut)}} .kpi.ok{{background:var(--top-soft)}} .kpi.ok b{{color:var(--top)}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;display:grid;gap:10px;min-width:0}}
.spend{{display:flex;height:26px;border-radius:7px;overflow:hidden;gap:2px}}
.seg.top{{background:var(--top)}} .seg.good{{background:var(--good)}} .seg.watch{{background:var(--watch)}} .seg.ask{{background:var(--ask)}} .seg.cut{{background:var(--cut)}} .seg.soft{{background:var(--line)}}
.key{{display:flex;flex-wrap:wrap;gap:14px;font-size:.86rem}} .key span{{display:flex;gap:6px;align-items:center}}
.dot{{width:11px;height:11px;border-radius:50%;display:inline-block}} .dot.top{{background:var(--top)}} .dot.good{{background:var(--good)}} .dot.watch{{background:var(--watch)}} .dot.ask{{background:var(--ask)}} .dot.cut{{background:var(--cut)}} .dot.soft{{background:var(--line)}}
.pill{{border-radius:999px;padding:3px 11px;font-size:.82rem;font-weight:700;white-space:nowrap;color:var(--on)}} .pill.cut{{background:var(--cut)}} .pill.top{{background:var(--top)}} .pill.ask{{background:var(--ask)}} .pill.watch{{background:var(--watch)}} .pill.good{{background:var(--good)}}
.grp{{display:grid;gap:10px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}}
.tile{{display:grid;gap:6px;text-decoration:none;color:inherit;background:var(--panel);border-radius:12px;padding:6px;border:3px solid var(--line);min-width:0}}
.tile.cut{{border-color:var(--cut)}} .tile.top{{border-color:var(--top)}} .tile.ask{{border-color:var(--ask)}} .tile.watch{{border-color:var(--watch)}} .tile.good{{border-color:var(--good)}}
.pic{{position:relative;aspect-ratio:4/5;border-radius:8px;overflow:hidden;background:var(--line)}} .pic img{{width:100%;height:100%;object-fit:cover;display:block}}
.noimg{{display:grid;place-items:center;height:100%;color:var(--soft);font-size:.8rem}}
.badge{{position:absolute;top:6px;left:6px;background:var(--shade);color:var(--on);font-weight:800;font-size:.8rem;border-radius:6px;padding:1px 7px}}
.vid{{position:absolute;top:6px;right:6px;background:var(--shade);color:var(--on);font-size:.7rem;border-radius:50%;width:22px;height:22px;display:grid;place-items:center}}
.over{{position:absolute;inset:auto 0 0 0;padding:22px 8px 7px;background:linear-gradient(transparent,var(--shade));color:var(--on);display:grid}}
.over b{{font-size:1.5rem;line-height:1;font-variant-numeric:tabular-nums}} .over span{{font-size:.78rem;font-weight:600}}
.meter{{position:relative;height:8px;border-radius:4px;background:var(--bg);overflow:hidden}} .meter .fill{{position:absolute;inset:0 auto 0 0;background:var(--watch)}}
.tile.top .meter .fill,.tile.good .meter .fill,.meter .fill.top,.meter .fill.good{{background:var(--top)}} .tile.cut .meter .fill,.meter .fill.cut{{background:var(--cut)}} .tile.ask .meter .fill{{background:var(--ask)}}
.meter .be{{position:absolute;left:50%;top:0;bottom:0;width:2px;background:var(--ink)}}
.mini{{display:flex;justify-content:space-between;gap:4px;font-size:.72rem;color:var(--soft);font-variant-numeric:tabular-nums;flex-wrap:wrap}}
.nm{{font-size:.76rem;color:var(--soft);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.mine{{font-size:.78rem;font-weight:700;border-radius:6px;padding:3px 7px}} .mine.agree{{background:var(--top-soft)}} .mine.over{{background:var(--ask-soft)}}
.camps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}
.camp{{border:1px solid var(--line);border-left:6px solid var(--line);border-radius:12px;padding:12px;display:grid;gap:8px;min-width:0;background:var(--panel)}} .camp.cut{{border-left-color:var(--cut)}} .camp.top{{border-left-color:var(--top)}}
.ch{{display:grid;gap:4px;justify-items:start}} .ch b{{overflow-wrap:anywhere}} .ch small{{color:var(--soft)}}
.cm{{display:grid;grid-template-columns:56px 1fr 56px;gap:8px;align-items:center;font-size:.82rem}} .cm b{{text-align:right;font-variant-numeric:tabular-nums}}
.strip{{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px}}
.th{{margin:0;flex:none;width:62px;display:grid;gap:2px;font-size:.68rem;text-align:center;color:var(--soft)}} .th img{{width:62px;height:78px;object-fit:cover;border-radius:6px;border:2px solid var(--line);display:block}}
.th.cut img{{border-color:var(--cut)}} .th.top img{{border-color:var(--top)}} .th.watch img{{border-color:var(--watch)}} .th.ask img{{border-color:var(--ask)}} .th.good img{{border-color:var(--good)}}
.wall{{display:flex;flex-wrap:wrap;gap:6px}}
.map{{overflow-x:auto}} .map svg{{width:100%;min-width:560px;height:auto;display:block}}
.ax{{fill:var(--soft);font-size:11px}} .lb{{fill:var(--ink);font-size:11px;font-weight:800}} .beline{{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:5 4}}
.band.top{{fill:var(--top-soft)}} .band.cut{{fill:var(--cut-soft)}}
.ring.top{{fill:var(--top)}} .ring.good{{fill:var(--good)}} .ring.watch{{fill:var(--watch)}} .ring.ask{{fill:var(--ask)}} .ring.cut{{fill:var(--cut)}} .ring.soft{{fill:var(--soft)}}
.fn{{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,2fr) auto;gap:10px;align-items:center;font-size:.86rem}} .fn .nm small{{display:block;color:var(--soft)}}
.fb{{position:relative;height:14px;background:var(--bg);border-radius:4px}} .fb .aov{{position:absolute;inset:0 auto 0 0;background:var(--top-soft);border-radius:4px}} .fb .ear{{position:absolute;inset:0 auto 0 0;background:var(--top);border-radius:4px}}
.fn b{{font-variant-numeric:tabular-nums;white-space:nowrap}} .fn b small{{color:var(--soft);font-weight:400}}
@media(max-width:520px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}} .fn{{grid-template-columns:1fr}}}}
</style>
<div class="w">
<header style="display:grid;gap:4px"><span class="soft" style="text-transform:uppercase;letter-spacing:.08em;font-size:.74rem">Ad Desk · {e(brand.title())} · through {r['asof']}</span>
<h1>{n_calls} calls to make</h1>
<p class="soft">Each ad is framed in its call's colour. Big number = cost per sale; the black line on its bar is break-even (what one order earns back). Tap an ad to open it.</p></header>
<div class="kpis">{tiles_k}</div>
<div class="card"><h2>Where this week's ad money went</h2><div class="spend">{bar}</div><div class="key">{key}</div></div>
{groups}
<section class="grp"><h2><span class="pill cut">Budgets</span> {len(camps)} campaigns</h2><div class="camps">{cblocks}</div></section>
<div class="card"><h2>The whole account on one map</h2><p class="soft">Every ad with a sale. Right = more spend this week. Up = more expensive per sale. Bigger = more spent in its life.</p><div class="map">{svg}</div></div>
<div class="card"><h2>Too early to judge · {len(early)} ads</h2><p class="soft">Under one break-even spent. Number = spent so far.</p><div class="wall">{wall}</div></div>
<div class="card"><h2>What one order earns, by funnel</h2><p class="soft">Light = what she pays. Dark = what's left after product, freight, shipping, fees, refunds — each funnel's break-even.</p>{fun}</div>
<div class="card"><h2>Your calls so far · {lg['calls']}</h2><ul style="margin:0;padding-left:18px">{agree}</ul></div>
</div>"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("brand"); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    Path(a.out).write_text(build(a.brand))
    print(a.out)


if __name__ == "__main__":
    main()
