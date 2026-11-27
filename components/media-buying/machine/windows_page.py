"""windows_page.py — the Ad Desk page for a desk with the one keep / kill rule (desk.json `rule`, meta_cpa_windows).

Called by desk_page.py; never run alone. Reads the run's report.json and decisions.jsonl. The rule on top, the
blended business, every judged ad as one row (3 / 7 / 14 days, daily frequency, share, call), the ads not judged
yet and the rule's evidence behind a tap, then the ads themselves, playable where the post is public.
"""
import html, json, re
from datetime import date

import analyze as A
import creative as CR

e = html.escape
LAB = {"keep": ("Keep", "on"), "prospect": ("Keep, prospecting", "pk"), "off": ("Kill", "no"), "too_early": ("Not judged", "")}
ORDER = {"prospect": 0, "keep": 1, "off": 2, "too_early": 3}


def m(v):
    return "—" if v is None else "${:,.0f}".format(v)


def short(name):
    """The words that tell two ads apart: the file-name parts every ad of the brand shares drop out."""
    s = re.sub(r"_batch-[0-9-]+?-([a-z])(?=_|$)", r"-\1", name or "")
    s = re.sub(r"^[a-z]+_[a-z-]+_(?=brief-)", "", s)
    s = re.sub(r"_[^_]*_(\d{8})_trybe=", " · ", s).replace("_", " · ")
    return s or name


def cell(w, line):
    if not w or not w["spend"]:
        return '<td class="w"><b>—</b></td>'
    c = w["cpa"]
    cls = "g" if c and c <= line else "r" if c or w["spend"] >= line * 2 else "n"
    return '<td class="w {}"><b>{}</b><small>{} · {}</small></td>'.format(cls, m(c) if c else "no sale", m(w["spend"]), w["sales"])


def label(f):
    return f.get("_name") or short(f["name"])


def row(f, line, calls):
    lab, cls = LAB[f["action"]]
    said = calls.get(f["flag"])
    mine = '<small>You: {}</small>'.format(e(said["said"])) if said else ""
    return ('<tr><td class="nm">{}<b>{}</b><small>{} · {}</small></td>{}<td class="num" data-l="Daily freq">{}</td><td class="num" data-l="Share">{:.0f}%</td>'
            '<td class="cl"><span class="st {}">{}</span>{}</td></tr>').format(
                '<img class="th" src="{}" alt="">'.format(f["_pic"]) if f.get("_pic") else "", e(label(f)), f["flag"], "Video" if f.get("_vid") else "Image", "".join(cell(f["windows"][n], line) for n in ("3", "7", "14")),
                f["freq7"] if f["freq7"] else "—", f["account_share7"] or 0, cls, lab, mine)


def table(fs, line, calls):
    return ('<div class="scroll"><table class="dec"><thead><tr><th>Ad</th><th>3 days</th><th>7 days</th><th>14 days</th><th>Daily freq</th><th>Share</th><th>Call</th></tr></thead>'
            '<tbody>{}</tbody></table></div>').format("".join(row(f, line, calls) for f in fs))


def evidence(R):
    out = ""
    for b in R.get("evidence", []):
        rows = "".join('<div><b>{}</b><span>{}</span><strong>{}</strong></div>'.format(*(e(str(x)) for x in r)) for r in b["rows"])
        out += '<div><h3>{}</h3><div class="tb">{}</div><p>{}</p></div>'.format(e(b["title"]), rows, e(b.get("note", "")))
    return out


def build(brand, run, r):
    R, line, P = r["rule"], r["rule"]["cpa"], r["rule"]["prospecting"]
    dp = A.desk_dir(brand) / "decisions.jsonl"
    every = [json.loads(x) for x in dp.read_text().splitlines() if x.strip()] if dp.exists() else []
    calls = {c["flag"]: c for c in every if c["asof"] == r["asof"]}
    ads = [f for f in r["flags"] if f["kind"] == "ad"]
    camps = [f for f in r["flags"] if f["kind"] == "campaign"]
    judged = sorted((f for f in ads if f["action"] != "too_early"), key=lambda f: (ORDER[f["action"]], -f["windows"]["14"]["spend"]))
    early = sorted((f for f in ads if f["action"] == "too_early" and f["windows"]["14"]["spend"] >= 5), key=lambda f: -f["windows"]["14"]["spend"])
    shown = judged + early
    uris, src = CR.fetch(run, [f["id"] for f in judged + early[:6]], width=480)
    names = A.load_desk(brand).get("names") or {}
    for f in ads:
        f["_name"], f["_pic"] = names.get(f["name"]), uris.get(f["id"])
    for f in shown:
        f["_vid"] = (src.get(f["id"]) or {}).get("is_video")
    if early[6:]:
        more = CR.sources([f["id"] for f in early[6:]])
        for f in early[6:]:
            f["_vid"] = (more.get(f["id"]) or {}).get("is_video")
    wall = [f for f in judged + early[:6] if uris.get(f["id"])]
    vids = CR.videos(run, [f["id"] for f in wall if f["_vid"]], src)
    W = r["windows"]
    b14 = W["14"]["business"]
    kp = [("Orders a day", "{:.0f}".format(b14["store_orders"] / 14)), ("Blended AOV", m(b14["store_revenue"] / b14["store_orders"]) if b14["store_orders"] else "—"),
          ("Profit per order", m(b14["contribution_per_order"])), ("Blended CPA", m(b14["blended_cpa"])),
          ("Live ads’ Meta CPA 3 · 7 · 14 days", " · ".join(m(W[n]["live_ads"]["cpa"]) for n in ("3", "7", "14")))]
    n = {k: sum(1 for f in judged if f["action"] == k) for k in ("keep", "prospect", "off")}
    cards = ""
    for f in wall:
        lab, cls = LAB[f["action"]]
        med = ('<video controls playsinline preload="none" poster="{}" src="{}"></video>'.format(uris[f["id"]], vids[f["id"]]) if f["id"] in vids
               else '<img src="{}" alt="" loading="lazy">'.format(uris[f["id"]]))
        href = (src.get(f["id"]) or {}).get("preview")
        cards += ('<article class="card">{}<div><span class="st {}">{}</span><b>{}</b><small>{} · {} a sale, 14 days</small>{}</div></article>').format(
            med, cls, lab, e(label(f)), m(f["windows"]["14"]["spend"]), m(f["windows"]["14"]["cpa"]),
            '<a href="{}">Open the post</a>'.format(e(href)) if href else "")
    budgets = "".join('<div class="bud"><b>{}</b><span class="st {}">{}</span><small>{}</small></div>'.format(
        e(c["name"]), "no" if c["action"] == "budget_down" else "on" if c["action"] == "budget_up" else "", A.ACTIONS[c["action"]] + " · " + c["flag"], e(c["why"])) for c in camps)
    return """<title>{name} Ad Desk</title><meta name="claude:viewport-fit-sides" content="cover"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Space+Grotesk:wght@600&display=swap"><style>{css}</style>
<div class="wrap"><header><h1>{name} Ad Desk</h1><span>Through {asof}</span></header>
<div class="rule"><div class="k"><small>Keep · {nk}</small><b>${line:.0f} or under</b><small>in any of 3, 7 or 14 days</small></div><div class="pk"><small>Keep, it’s prospecting · {np}</small><b>14 days to ${pc:.0f}</b><small>daily frequency {pf:g} or under · {ps:g}%+ of spend</small></div><div class="x"><small>Kill · {no}</small><b>Over ${line:.0f} in all 3</b></div><p>Meta CPA. Judged at ${ja:.0f} spent in 14 days. No sale by ${ns:.0f} is a kill.</p></div>
<div class="eq">{kp}</div>
<div class="box">{judged}</div>
<details class="box"><summary>Not judged yet · {ne} ads · {se} in 14 days</summary>{early}</details>
<details class="box"><summary>Budgets · {nc} campaigns</summary>{budgets}</details>
<details class="box"><summary>How ${line:.0f} was set</summary><div class="two">{ev}</div></details>
<h2>The ads</h2><main class="wall">{cards}</main>
<p class="src">Meta’s numbers from our daily copy. Blended = every order: funnel, storefront, subscriptions. The last days still gain sales as Meta credits late buyers. Daily frequency and share: 7 days. Salaries, apps and store fees are not in profit.</p></div><script>{js}</script>""".format(
        name=e(r.get("name") or brand), css=CSS, js=JS, asof=date.fromisoformat(r["asof"]).strftime("%b %d").replace(" 0", " "), line=line, pc=P["cpa14_up_to"], pf=P["daily_frequency7_up_to"], ps=P["share7_from_pct"],
        ja=R["judge_at_14d_spend"], ns=R["no_sale_off_at_14d_spend"], nk=n["keep"], np=n["prospect"], no=n["off"],
        kp="".join("<div><small>{}</small><b>{}</b></div>".format(a, b) for a, b in kp), judged=table(judged, line, calls), early=table(early, line, calls),
        ne=r["counts"]["too_early"], se=m(sum(f["windows"]["14"]["spend"] for f in ads if f["action"] == "too_early")), nc=len(camps), budgets=budgets, ev=evidence(R), cards=cards)


CSS = """/* Layout: the rule, the business, one decision table, then the ads */
:root{--bg:#fafafa;--pane:#fff;--fg:#18181b;--mut:#63636e;--line:#e4e4e7;--acc:#047857;--soft:#ecfdf5;--red:#b42318;--rs:#fef2f1;--blue:#1d4ed8;--bs:#eff4ff;--head:"Space Grotesk",system-ui,sans-serif;--text:Inter,system-ui,sans-serif}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111113;--pane:#19191c;--fg:#f4f4f5;--mut:#a1a1aa;--line:#2c2c31;--acc:#34d399;--soft:#10291f;--red:#f78a80;--rs:#331816;--blue:#93b4ff;--bs:#172036;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#111113;--pane:#19191c;--fg:#f4f4f5;--mut:#a1a1aa;--line:#2c2c31;--acc:#34d399;--soft:#10291f;--red:#f78a80;--rs:#331816;--blue:#93b4ff;--bs:#172036;color-scheme:dark}
*{box-sizing:border-box}body{background:var(--bg);color:var(--fg);font:15px/1.45 var(--text);font-variant-numeric:tabular-nums}
.wrap{max-width:1240px;margin:0 auto;padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:14px;grid-template-columns:minmax(0,1fr)}
header{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:6px 20px}h1{font:600 28px/1.15 var(--head);margin:0}h2{font:600 18px var(--head);margin:10px 0 0}header span{color:var(--mut)}
.rule{display:grid;grid-template-columns:1fr 1.25fr 1fr;border-radius:8px;overflow:hidden;border:1px solid var(--line);background:var(--pane)}.rule div{padding:18px 20px}.rule .k{background:var(--soft);color:var(--acc)}.rule .pk{background:var(--bs);color:var(--blue)}.rule .x{background:var(--rs);color:var(--red)}.rule small{font-size:14px}.rule b{display:block;font:600 32px/1.15 var(--head)}.rule p{grid-column:1/-1;margin:0;padding:11px 20px;font-size:14px}
.eq{display:grid;grid-template-columns:repeat(4,1fr) 1.5fr;border:1px solid var(--line);background:var(--pane);border-radius:8px;overflow:hidden}.eq div{padding:14px 16px;min-width:0;border-left:1px solid var(--line)}.eq div:first-child{border-left:0}.eq small{display:block;color:var(--mut);font-size:13px}.eq b{font:600 24px/1.2 var(--head)}
.box{background:var(--pane);border:1px solid var(--line);border-radius:8px;padding:14px 16px;min-width:0}.box h3{font:600 16px var(--head);margin:12px 0 8px}.box p{margin:8px 0 0;font-size:13px;color:var(--mut)}summary{cursor:pointer;font-size:14px;color:var(--mut)}
.two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 24px}.tb div{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;padding:7px 0;border-bottom:1px solid var(--line);font-size:14px}.tb div:last-child{border-bottom:0}.tb span{color:var(--mut)}.tb strong{text-align:right}
.st{display:inline-block;padding:1px 9px;border-radius:99px;border:1px solid var(--line);font-size:13px;white-space:nowrap}.st.on{background:var(--soft);color:var(--acc);border-color:transparent}.st.pk{background:var(--bs);color:var(--blue);border-color:transparent}.st.no{background:var(--rs);color:var(--red);border-color:transparent}
.scroll{overflow-x:auto}.dec{border-collapse:collapse;width:100%;font-size:14px}.dec td,.dec th{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line)}.dec th{font-size:12px;color:var(--mut);font-weight:400}.dec th:first-child,.dec td:first-child{padding-left:0;overflow-wrap:anywhere}.dec small{display:block;color:var(--mut);font-size:12px}.dec .th{float:left;width:34px;height:46px;object-fit:cover;border-radius:4px;margin-right:10px}.dec .w b{font:600 18px/1.1 var(--head)}.dec .g{background:var(--soft)}.dec .g b{color:var(--acc)}.dec .r{background:var(--rs)}.dec .r b{color:var(--red)}.dec tbody tr:last-child td{border-bottom:0}
.bud{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;padding:8px 0;border-bottom:1px solid var(--line)}.bud:last-child{border:0}.bud b{overflow-wrap:anywhere}.bud small{color:var(--mut);flex-basis:100%}
.wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}.card{background:var(--pane);border:1px solid var(--line);border-radius:8px;padding:10px;min-width:0;display:grid;gap:8px;align-content:start}.card video,.card img{display:block;width:100%;aspect-ratio:9/16;object-fit:cover;background:#000;border-radius:5px}.card div{display:grid;gap:4px;justify-items:start;min-width:0}.card b{font-size:14px;overflow-wrap:anywhere}.card small{color:var(--mut)}a{color:var(--acc);font-size:13px}:focus-visible{outline:2px solid var(--acc);outline-offset:2px}.src{font-size:13px;color:var(--mut);margin:6px 0 0}
@media(max-width:900px){.two{grid-template-columns:minmax(0,1fr)}}
@media(max-width:600px){.rule{grid-template-columns:1fr}.rule b{font-size:26px}.eq{grid-template-columns:1fr 1fr}.eq div{border-left:0;border-top:1px solid var(--line)}.eq div:last-child{grid-column:1/-1}.wall{grid-template-columns:1fr 1fr}.dec,.dec tbody{display:block}.dec thead{display:none}.dec tr{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;padding:12px 0;border-bottom:1px solid var(--line)}.dec td{border:0;padding:7px 9px;border-radius:5px}.dec td.nm{grid-column:1/-1;padding:0}.dec .nm small{display:inline;margin-left:6px}.dec td.num{padding:4px 9px}.dec td.num::before{content:attr(data-l);color:var(--mut);font-size:12px;display:block}.dec td.cl{align-self:end;padding:4px 0}.st{white-space:normal}.dec .w::before{display:block;font-size:11px;color:var(--mut)}.dec .w:nth-of-type(2)::before{content:'3 days'}.dec .w:nth-of-type(3)::before{content:'7 days'}.dec .w:nth-of-type(4)::before{content:'14 days'}}"""
JS = "document.addEventListener('play',function(ev){document.querySelectorAll('video').forEach(function(v){if(v!==ev.target)v.pause()})},true);"
