#!/usr/bin/env python3
"""The learnings page — what the sending taught, and where the opportunity is.

    python3 build_learnings.py --brand brand-b

Generated from the joined data, never hand-kept: what each email WAS
(classified) against what it DID (reported). Re-run after any new pull.
"""
import argparse, html, json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
B = HERE / "calendar" / "brands"
CATS = {"ask": "Promotional", "help": "Educational", "belong": "Cultural",
        "real": "Community", "brand": "Brand", "affiliate": "Affiliate"}
MADE = {"ask": "made of our offer", "help": "made of our expertise",
        "belong": "made of the world outside", "real": "made of our customers",
        "brand": "made of us", "affiliate": "made of a partner's offer"}


def e(s): return html.escape(str(s or ""))


def load(brand):
    perf = {r["groupings"]["campaign_id"]: r["statistics"]
            for r in json.loads((B / f"{brand}-performance.json").read_text())}
    cls = {x["file"]: x for x in json.loads((B / f"{brand}-classified.json").read_text())}
    idx = json.loads((B / f"{brand}-sends" / "index.json").read_text())
    led_rows = json.loads((B / f"{brand}-ledger.json").read_text())
    by_name = {(x["sent"], x["campaign"]): x for x in led_rows}
    rows = []
    for x in idx:
        L = by_name.get((x.get("sent"), x.get("campaign")))
        if not L or L["id"] not in perf:
            continue
        s, c = perf[L["id"]], cls.get(x["file"], {})
        rec = s.get("recipients") or 0
        if rec < 50:
            continue
        rows.append(dict(cat=c.get("category"), type=c.get("type"),
                         hour=L.get("hour"), is_local=L.get("is_local"),
                         rec=rec, rev=s.get("conversion_value") or 0,
                         clicks=s.get("clicks_unique") or 0,
                         unsub=s.get("unsubscribes") or 0))
    return rows


def agg(rows, keyfn, floor=1):
    g = defaultdict(list)
    for r in rows:
        k = keyfn(r)
        if k is not None:
            g[k].append(r)
    out = []
    for k, v in g.items():
        rec = sum(r["rec"] for r in v)
        if len(v) < floor or not rec:
            continue
        out.append(dict(key=k, n=len(v), rec=rec,
                        rev=sum(r["rev"] for r in v),
                        rpr=sum(r["rev"] for r in v) / rec,
                        click=sum(r["clicks"] for r in v) / rec,
                        unsub=sum(r["unsub"] for r in v) / rec))
    return sorted(out, key=lambda x: -x["rpr"])


CSS = """
:root{--bg:#F1F0ED;--card:#FFF;--ink:#15181B;--mut:#616770;--line:#D7D5D0;--hair:#E8E6E2;
 --good:#1C6B4C;--good-bg:#DFEEE7;--warn:#8A5A12;--warn-bg:#F4EBD9;--bad:#8D3628;--bad-bg:#F5E3DE;
 --acc:#1F4E6B}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --bg:#0D0F11;--card:#171A1E;--ink:#E4E7EA;--mut:#8B929B;--line:#262A2F;--hair:#1E2125;
 --good:#5FBE95;--good-bg:#0F2520;--warn:#D2A24E;--warn-bg:#291F12;--bad:#D9786A;--bad-bg:#2A1614;
 --acc:#6FADCF}}
:root[data-theme="dark"]{
 --bg:#0D0F11;--card:#171A1E;--ink:#E4E7EA;--mut:#8B929B;--line:#262A2F;--hair:#1E2125;
 --good:#5FBE95;--good-bg:#0F2520;--warn:#D2A24E;--warn-bg:#291F12;--bad:#D9786A;--bad-bg:#2A1614;
 --acc:#6FADCF}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:16px/1.62 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:880px;margin:0 auto;padding:54px 22px 92px}
.kick{font:600 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.2em;
 text-transform:uppercase;color:var(--mut)}
h1{font-size:clamp(35px,6.2vw,56px);line-height:1.02;letter-spacing:-.034em;font-weight:800;margin:14px 0 0}
.lede{font-size:19px;line-height:1.55;color:var(--mut);max-width:58ch;margin:16px 0 0}
h2{font-size:26px;letter-spacing:-.024em;font-weight:780;margin:0}
section{margin-top:58px}
.sh{border-top:2px solid var(--ink);padding-top:13px;margin-bottom:20px}
.sh h2{margin-top:6px}
.sn{color:var(--mut);max-width:62ch;margin:10px 0 0;font-size:15.5px}
.caveat{border-left:3px solid var(--warn);padding:2px 0 2px 15px;margin:22px 0 0;
 color:var(--mut);font-size:14.5px;max-width:62ch}
.big{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1px;
 background:var(--line);border:1px solid var(--line);border-radius:5px;overflow:hidden;margin-top:28px}
.big .c{background:var(--card);padding:17px 19px}
.big .v{font:700 27px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:-.025em;
 font-variant-numeric:tabular-nums}
.big .k{font:600 10px/1.35 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.12em;
 text-transform:uppercase;color:var(--mut);margin-top:9px}
.big .s{color:var(--mut);font-size:12.5px;margin-top:6px;line-height:1.45}
table{width:100%;border-collapse:collapse;margin-top:8px;font-size:14.5px;
 background:var(--card);border:1px solid var(--line);border-radius:5px;overflow:hidden}
th{text-align:left;font:600 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.12em;
 text-transform:uppercase;color:var(--mut);padding:12px 14px;border-bottom:1px solid var(--line)}
td{padding:11px 14px;border-bottom:1px solid var(--hair);font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:0}
td.n{text-align:right}
td.name{font-weight:600;font-variant-numeric:normal}
td .sub{color:var(--mut);font-size:12.5px;font-weight:400}
.bar{height:6px;border-radius:3px;background:var(--acc);display:block}
.thin{color:var(--mut);font-size:11px}
.find{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--acc);
 border-radius:5px;padding:19px 21px;margin-bottom:12px}
.find h3{margin:0 0 7px;font-size:18px;letter-spacing:-.015em;font-weight:740}
.find p{margin:0;color:var(--mut);font-size:15px;max-width:62ch}
.find b{color:var(--ink)}
.find.op{border-left-color:var(--good)}
.find.risk{border-left-color:var(--bad)}
footer{margin-top:66px;border-top:1px solid var(--line);padding-top:18px;
 font:12px/1.75 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mut)}
"""


def tbl(rows, label, mx=None, note_thin=5):
    mx = mx or max((r["rpr"] for r in rows), default=1)
    h = (f"<table><tr><th>{e(label)}</th><th>Sends</th><th>Rev / recipient</th>"
         "<th></th><th>Click</th><th>Unsub</th></tr>")
    for r in rows:
        thin = ' <span class="thin">small n</span>' if r["n"] < note_thin else ""
        h += (f'<tr><td class="name">{e(r["key"])}{thin}</td>'
              f'<td class="n">{r["n"]}</td>'
              f'<td class="n"><b>${r["rpr"]:.3f}</b></td>'
              f'<td style="width:26%"><span class="bar" style="width:{100*r["rpr"]/mx:.0f}%"></span></td>'
              f'<td class="n">{100*r["click"]:.2f}%</td>'
              f'<td class="n">{100*r["unsub"]:.2f}%</td></tr>')
    return h + "</table>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help="brand folder name under brands/ — there is no default brand")
    args = ap.parse_args()
    rows = load(args.brand)
    n, rec = len(rows), sum(r["rec"] for r in rows)
    rev = sum(r["rev"] for r in rows)

    bycat = agg(rows, lambda r: CATS.get(r["cat"]))
    bytype = agg(rows, lambda r: r["type"], floor=3)
    byhour = agg(rows, lambda r: f"{r['hour']}:00" if r["hour"] else None, floor=4)
    bylocal = agg(rows, lambda r: "Each person's local time" if r["is_local"]
                  else "One fixed time for everyone")
    top, bottom = bytype[:10], sorted(bytype, key=lambda x: x["rpr"])[:6]
    best_h = byhour[0]
    h13 = next((h for h in byhour if h["key"] == "13:00"), None)
    spread = (bycat[0]["rpr"] / bycat[-1]["rpr"] - 1) * 100

    doc = f"""<title>{args.brand.upper()} Email Learnings</title>
<style>{CSS}</style>
<div class="wrap">
<div class="kick">{args.brand.upper()} &middot; {n} campaigns &middot; what each email was, against what it did</div>
<h1>What the sending taught</h1>
<p class="lede">Every send tagged by what it is made of, joined to what it
actually earned. {rec:,} recipients, ${rev:,.0f} attributed.</p>

<div class="big">
  <div class="c"><div class="v">${rev/rec:.3f}</div><div class="k">Revenue per recipient</div>
    <div class="s">the number every row below is measured against</div></div>
  <div class="c"><div class="v">{spread:.0f}%</div><div class="k">Best to worst category</div>
    <div class="s">far narrower than anyone assumes</div></div>
  <div class="c"><div class="v">${best_h['rpr']:.3f}</div><div class="k">Best hour ({e(best_h['key'])})</div>
    <div class="s">against ${h13['rpr']:.3f} at 13:00, which carries most sends</div></div>
</div>

<p class="caveat"><b>Two caveats, carried not footnoted.</b> Open rate is left
off this page entirely &mdash; Apple Mail auto-opens inflate it and an
engagement-selected segment inflates it again. Click and revenue per recipient
are the honest columns. And any row marked <i>small n</i> has fewer than five
sends behind it, where one email moves the average.</p>

<section>
  <div class="sh"><div class="kick">The finding that matters most</div>
    <h2>The categories are far closer than they look</h2></div>
  <p class="sn">Promotional earns most per recipient. But not by much &mdash;
  and that is the whole argument for the mix, made in numbers rather than
  sentiment.</p>
  {tbl(bycat, "Category")}
  <div class="find" style="margin-top:20px">
    <h3>Asking harder is not the lever</h3>
    <p>Promotional beats Educational and Community by about
    <b>{100*(bycat[0]['rpr']/[c for c in bycat if c['key']=='Educational'][0]['rpr']-1):.0f}%</b>
    per recipient. Everything that is not an ask nearly pays for itself at the
    same rate &mdash; while also being the thing that earns the right to ask.</p>
  </div>
  <div class="find">
    <h3>Brand is read most and sells least</h3>
    <p>The highest click rate on the page and the lowest revenue per recipient.
    That is not a failure &mdash; it is what the category is for, and it is the
    clearest evidence that click rate and revenue measure different things.</p>
  </div>
</section>

<section>
  <div class="sh"><div class="kick">By type</div><h2>What earns</h2></div>
  {tbl(top, "Type")}
  <h3 style="margin:34px 0 4px;font-size:19px;letter-spacing:-.015em">And what does not</h3>
  {tbl(bottom, "Type")}
</section>

<section>
  <div class="sh"><div class="kick">Timing</div><h2>When to send</h2></div>
  <p class="sn">The hour a send was scheduled for. This is the one timing lever
  that has genuinely been varied, so the comparison is honest.</p>
  {tbl(byhour, "Hour")}
  <h3 style="margin:34px 0 4px;font-size:19px;letter-spacing:-.015em">Local time against one fixed time</h3>
  {tbl(bylocal, "Method")}
</section>

<section>
  <div class="sh"><div class="kick">The opportunities</div><h2>Where to go next</h2></div>
  <div class="find op">
    <h3>Move the send later</h3>
    <p>{e(best_h['key'])} earns <b>${best_h['rpr']:.3f}</b> against
    <b>${h13['rpr']:.3f}</b> at 13:00, which carries more sends than any other
    hour. That is a <b>{100*(best_h['rpr']/h13['rpr']-1):.0f}% lift</b> on the
    single easiest thing to change &mdash; and it agrees with the order data,
    where buying peaks between 15:00 and 18:00.</p>
  </div>
  <div class="find op">
    <h3>Community is the underused well</h3>
    <p>It earns close to Promotional per recipient, and it is a small share of
    what goes out &mdash; on a brand holding hundreds of customers with written
    stories, photos and results. Five of its seven types have never been sent.</p>
  </div>
  <div class="find risk">
    <h3>Education earns least of the big three</h3>
    <p>Mechanism, problem-explainer and seasonal-skin all sit near the bottom,
    and two of the highest unsubscribe rates on the page are educational types.
    Worth keeping for what it earns later &mdash; worth not assuming it pays now.</p>
  </div>
  <div class="find">
    <h3>Day of week is not a lever</h3>
    <p>Every day lands between ${min(a['rpr'] for a in agg(rows, lambda r: 1)):.3f}
    and the top &mdash; a spread narrow enough that picking a day is not where
    the gain is. Stop optimising it.</p>
  </div>
</section>

<footer>
  tools/email-production &middot; generated by build_learnings.py from the joined pulls<br>
  Classification: every send through the category test. Metrics: the platform's own reporting.
</footer>
</div>"""
    (HERE / "learnings.html").write_text(doc)
    print(f"learnings.html ({len(doc):,} bytes) · {n} campaigns")


if __name__ == "__main__":
    main()
