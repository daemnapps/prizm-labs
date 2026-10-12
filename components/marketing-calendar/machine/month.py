#!/usr/bin/env python3
"""The month as a calendar. Days, and what goes out on them. Nothing else.

    python3 month.py                     # every month planned, newest first
    python3 month.py --run <brand>/2026-09
    python3 month.py --open

the owner, 2026-09-14: *"I just need to see the days the emails and such — we don't
need this big page with the buttons to generate text just yet, just a
calendar."*

So this is the calendar and only the calendar. No editing, no approving, no
hand-off, no chain panel — `board.py` is still there for the day the reviewing
starts. A month should be legible before it is operable, and the thing a person
actually wants to check first is the SHAPE of it: where the dense weeks are,
where the quiet ones are, what lands on a Saturday.
"""
import argparse
import datetime
import html
import json
import subprocess
from collections import Counter
from pathlib import Path

import paths
from paths import RUNS, rel
import chain as CH
import review as R

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CAT = {"Promotional": "ask", "Educational": "help", "Cultural": "belong",
       "Community": "real", "Brand": "brand", "Affiliate": "aff"}


def esc(x):
    return html.escape(str(x if x is not None else ""), quote=True)


def short_segment(s):
    """`Core | VIP Customer` reads as `VIP Customer` in a box this size."""
    return (s or "").split("|")[-1].strip()


def read(run_dir):
    run_dir = Path(run_dir)
    slots = json.loads((run_dir / "slots.json").read_text())
    if isinstance(slots, dict):
        slots = slots.get("slots", [])
    try:
        state = json.loads((run_dir / "run.json").read_text())
    except (FileNotFoundError, ValueError):
        state = {}
    slots = R.applied(slots, R.load(run_dir))       # the human's edits, if any
    return slots, state


def grid(slots, month, brand):
    try:
        y, m = (int(x) for x in month.split("-")[:2])
    except (ValueError, IndexError):
        return ""
    first = datetime.date(y, m, 1)
    nxt = datetime.date(y + (m == 12), (m % 12) + 1, 1)
    by_day = {}
    for s in slots:
        try:
            by_day.setdefault(datetime.date.fromisoformat(s["date"]).day, []).append(s)
        except (ValueError, KeyError, TypeError):
            pass

    cells = ['<div class="dow">' + "".join(f"<span>{d}</span>" for d in DOW) + "</div>",
             '<div class="days">']
    cells += ['<div class="pad"></div>'] * first.weekday()
    today = datetime.date.today()
    for n in range(1, (nxt - first).days + 1):
        d = datetime.date(y, m, n)
        here = by_day.get(n, [])
        klass = "day"
        if here:
            klass += " has"
        if d == today:
            klass += " today"
        if d.weekday() >= 5:
            klass += " wknd"
        sends = ""
        for s in here:
            cat = CAT.get(s.get("category"), "brand")
            offer = (f'<i class="of">{esc(s["offer"])}</i>'
                     if s.get("offer") and s["offer"] != "none" else "")
            vs = s.get("variants") or []
            many = (f'<i class="vs">{len(vs)} versions</i>' if len(vs) > 1 else "")
            sends += (f'<button class="send {cat}" data-key="{esc(brand)}/{esc(s["id"])}" '
                      f'data-cat="{esc(s.get("category"))}" '
                      f'data-seg="{esc(s.get("segment"))}" '
                      f'data-offer="{esc(s.get("offer"))}" '
                      f'data-avatar="{esc(" ".join(v.get("avatar") or "" for v in (s.get("variants") or [])))}">'
                      f'<b>{esc(s.get("type", ""))}</b>'
                      f'<span>{esc(short_segment(s.get("segment")))}</span>'
                      f'{offer}{many}</button>')
        cells.append(f'<div class="{klass}"><span class="n">{n}</span>{sends}</div>')
    cells.append("</div>")
    return "".join(cells)


def send_path(brand, src):
    """Repo-relative path of a send file, through brandpath's `email-sms` key; None for an empty or placeholder ('[') source."""
    if not src or src.startswith("["):
        return None
    from paths import WORKSPACE
    p = CH.BP.brand_path(brand, "email-sms", "sends", src, root=WORKSPACE / "brands")
    return Path(rel(p)).as_posix()


def slot_detail(s, brand, run_dir):
    """Everything this send is, and everything the writer will be handed.

    the owner, 2026-09-14: "I need to be able to click in and see the concept
    itself and the details that will go to the copy machine to actually
    write." These are the slot's own fields — the contract the copy machine
    reads — not a summary of them.
    """
    vs = s.get("variants") or [{"avatar": s.get("avatar"), "angle": ""}]
    src = s.get("source") or ""
    return {
        "id": s["id"], "brand": brand, "date": s.get("date"), "hour": s.get("hour"),
        "type": s.get("type"), "category": s.get("category"), "role": s.get("role"),
        "segment": s.get("segment"), "segments": s.get("segments") or [],
        "occasion": s.get("occasion"), "product": s.get("product"),
        "offer": s.get("offer"), "anchored": bool(s.get("anchored")),
        "affiliate": s.get("affiliate"),
        "follows": s.get("follows"), "then": s.get("then"),
        "why": s.get("why"), "spent": s.get("spent"),
        "variants": [{"avatar": v.get("avatar"), "angle": v.get("angle"),
                      "dropped": v.get("angle_dropped")} for v in vs],
        "source": src,
        "source_brand": s.get("source_brand"),
        "source_path": send_path(s.get("source_brand") or brand, src),
        "unfilled": src.startswith("["),
        "research": (f'results/research-{(s.get("date") or "")[:7]}/{s["id"]}.md'
                     if s.get("date") else None),
    }


def collections_weeks(slots):
    """The month's sends, grouped by ISO week."""
    out = {}
    for x in slots:
        try:
            d = datetime.date.fromisoformat(x["date"])
        except (ValueError, KeyError, TypeError):
            continue
        out.setdefault(d.isocalendar()[:2], []).append(x)
    return out


def summary(slots, brand):
    """The month at a glance — the shape, not the days.

    the owner, 2026-09-14: "at a higher level we should be able to see what's going
    out per brand per month at a high level, that way we can properly
    strategize it too."

    Four questions a person actually asks of a month before reading it: how
    much of it SELLS, what KINDS of send it is made of, WHO it reaches and how
    often, and WHICH offers it spends. Every chip filters the grid below it —
    the summary is the filter.
    """
    n = len(slots) or 1
    asks = sum(1 for x in slots if x.get("role") == "asks")
    with_offer = sum(1 for x in slots
                     if x.get("offer") not in (None, "none", ""))
    versions = sum(max(1, len(x.get("variants") or [])) for x in slots)
    cats = Counter(x.get("category") for x in slots)
    segs = Counter(x.get("segment") for x in slots)
    offs = Counter(x.get("offer") for x in slots
                   if x.get("offer") not in (None, "none", ""))
    avs = Counter(v.get("avatar") for x in slots
                  for v in (x.get("variants") or []) if v.get("avatar"))
    days = len({x.get("date") for x in slots})
    # the commercial floor, as a fact on the page rather than a rule in a file
    weeks = collections_weeks(slots)
    sold = sum(1 for rows in weeks.values()
               if any(str(r.get("offer") or "none").lower() != "none" for r in rows))

    bar = "".join(
        f'<i class="seg {CAT.get(c, "brand")}" style="flex:{k}" '
        f'title="{esc(c)} — {k}"></i>'
        for c, k in cats.most_common())

    def chips(counter, kind, short=False):
        return "".join(
            f'<button class="chip" data-filter="{kind}" data-value="{esc(v)}">'
            f'{esc(short_segment(v) if short else v)}<b>{k}</b></button>'
            for v, k in counter.most_common())

    def big(v, label, note="", bad=False):
        return (f'<div class="big{" bad" if bad else ""}"><b>{esc(v)}</b>'
                f'<span>{esc(label)}</span>'
                + (f'<i>{esc(note)}</i>' if note else "") + "</div>")

    return f"""
<div class="sum">
  <div class="bigs">
    {big(len(slots), "sends", f"across {days} days")}
    {big(versions, "versions", "one per avatar in a send" if versions != len(slots) else "one each")}
    {big(f"{round(asks / n * 100)}%", "of the month asks",
         f"{asks} ask{'' if asks == 1 else 's'} · the rule is {round(CH.ASK_SHARE * 100)}%",
         bad=asks < max(1, round(n * CH.ASK_SHARE)))}
    {big(f"{sold}/{len(weeks)}", "weeks with an offer",
         "every week should have one" if sold < len(weeks)
         else f"{len(offs)} offer{'' if len(offs) == 1 else 's'} spent",
         bad=sold < len(weeks))}
  </div>
  <div class="mix">{bar}</div>
  <div class="rows">
    <div class="crow"><span class="t">Kinds</span><div class="cs">{chips(cats, "cat")}</div></div>
    <div class="crow"><span class="t">Audience</span><div class="cs">{chips(segs, "seg", True)}</div></div>
    {f'<div class="crow"><span class="t">Avatars</span><div class="cs">{chips(avs, "avatar")}</div></div>' if avs else ''}
    {f'<div class="crow"><span class="t">Offers</span><div class="cs">{chips(offs, "offer")}</div></div>' if offs else '<div class="crow"><span class="t">Offers</span><div class="cs"><i class="none">nothing sold this month</i></div></div>'}
  </div>
</div>"""


def month_block(run_dir):
    slots, state = read(run_dir)
    month = state.get("month") or (slots[0]["date"][:7] if slots else "")
    brand = state.get("brand") or Path(run_dir).parent.name
    try:
        title = datetime.date.fromisoformat(month + "-01").strftime("%B %Y")
    except ValueError:
        title = month
    span = (f'{slots[0]["date"]} to {slots[-1]["date"]}' if slots else "empty")
    checks = state.get("checks") or {}
    flags = []
    if checks.get("errors"):
        flags.append(f'<i class="flag bad">{checks["errors"]} break'
                     f'{"" if checks["errors"] == 1 else "s"}</i>')
    deg = [k for k, v in (state.get("brand_readiness") or {}).items()
           if v.get("verdict") == "degraded"]
    if deg:
        flags.append(f'<i class="flag warn">{len(deg)} layers ran on a partial record</i>')
    return f"""
<section class="mon" data-brand="{esc(brand)}">
  <header>
    <div>
      <div class="brand">{esc(brand)}</div>
      <h2>{esc(title)}</h2>
    </div>
    <div class="meta">
      <b>{len(slots)}</b> sends<span>{esc(span)}</span>
      <div class="flags">{"".join(flags)}</div>
    </div>
  </header>
  {summary(slots, brand)}
  <div class="cal">{grid(slots, month, brand)}</div>
</section>"""


def chain_block(title, rows, note):
    items = "".join(
        f'<div class="st2"><span class="who {"ai" if r["by"] == CH.AI else "code"}">'
        f'{"thinks" if r["by"] == CH.AI else "code"}</span>'
        f'<div><b>{esc(r["name"])}</b><p>{esc(r["does"])}</p>'
        f'<code>{esc(r["cmd"])}</code> <i>{esc(r["when"])}</i></div></div>'
        for r in rows)
    return (f'<div class="cgrp"><h4>{esc(title)}</h4>'
            f'<p class="cn">{esc(note)}</p>{items}</div>')


def chain_layers():
    items = "".join(
        f'<div class="st2 lay2"><span class="who {"ai" if s["by"] == CH.AI else "code"}">'
        f'{"thinks" if s["by"] == CH.AI else "code"}</span>'
        f'<div><b>{s["n"]}. {esc(s["name"])}</b><p>{esc(s["does"])}</p>'
        f'<code>{esc(s["folder"])}/</code></div></div>'
        for s in CH.STAGES)
    n_ai = len(CH.AI_KEYS)
    return (f'<div class="cgrp"><h4>The month — {len(CH.STAGES)} layers</h4>'
            f'<p class="cn">{n_ai} think; the other {len(CH.STAGES) - n_ai} are '
            f'code and cost nothing to re-run. Each writes into its own '
            f'numbered folder inside the month.</p>{items}</div>')


def render(runs):
    detail, brands = {}, []
    for r in runs:
        sl, st = read(r)
        b = st.get("brand") or Path(r).parent.name
        if b not in brands:
            brands.append(b)
        for x in sl:
            detail[f"{b}/{x['id']}"] = slot_detail(x, b, r)
    brands.sort()
    # ONE BRAND AT A TIME. the owner, 2026-09-14: "eventually, kind of like how we
    # have with the image ads, we have this thing where we can click into
    # brand-b or we can click into Brand A... so it's easy to just focus in on
    # one or the other at a time." Two brands stacked is a comparison; a person
    # planning a month wants one brand and nothing else on the page.
    tabs = ('<div class="brands">'
            + '<button class="btab" data-brand="*">All</button>'
            + "".join(f'<button class="btab" data-brand="{esc(b)}">{esc(b)}</button>'
                      for b in brands)
            + "</div>") if len(brands) > 1 else ""
    return f"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The calendar</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,640&family=Instrument+Sans:wght@400;500;600&family=Spline+Sans+Mono:wght@400;500&display=swap">
<style>
:root{{
  --bg:#F1F0EA; --card:#FFFFFF; --ink:#191B1D; --mut:#676C73; --dim:#9DA1A0;
  --line:#DBD9D2; --hair:#E9E7E1; --acc:#2E5D50; --acc-bg:#DFEBE6;
  --warn:#8A5A12; --warn-bg:#F5E9D2; --bad:#8E3B2F; --bad-bg:#F3DFDB;
  --ask:#8E3B2F; --help:#2E5D50; --belong:#7A5C1E; --real:#3F5E7A;
  --brandc:#5A4A6A; --aff:#6A5A3A;
  --sans:"Instrument Sans",system-ui,-apple-system,sans-serif;
  --serif:Fraunces,Georgia,serif;
  --mono:"Spline Sans Mono",ui-monospace,SFMono-Regular,monospace;
}}
@media (prefers-color-scheme:dark){{
  :root:not([data-theme="light"]){{
    --bg:#0E1012; --card:#16191C; --ink:#E6E8EA; --mut:#8E959D; --dim:#6B7278;
    --line:#272B30; --hair:#1E2226; --acc:#74B4A2; --acc-bg:#12251F;
    --warn:#D6A55B; --warn-bg:#2A2113; --bad:#E08877; --bad-bg:#2B1714;
    --ask:#E08877; --help:#74B4A2; --belong:#D6A55B; --real:#88AACB;
    --brandc:#A995BE; --aff:#BFAA7E;
  }}
}}
:root[data-theme="dark"]{{
  --bg:#0E1012; --card:#16191C; --ink:#E6E8EA; --mut:#8E959D; --dim:#6B7278;
  --line:#272B30; --hair:#1E2226; --acc:#74B4A2; --acc-bg:#12251F;
  --warn:#D6A55B; --warn-bg:#2A2113; --bad:#E08877; --bad-bg:#2B1714;
  --ask:#E08877; --help:#74B4A2; --belong:#D6A55B; --real:#88AACB;
  --brandc:#A995BE; --aff:#BFAA7E;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
     font-size:15px;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1180px;margin:0 auto;padding:34px 22px 80px;
      display:flex;flex-direction:column;gap:34px}}
h1{{font-family:var(--serif);font-weight:640;font-size:34px;margin:0;
   letter-spacing:-.02em}}
.lede{{color:var(--mut);font-size:14.5px;margin:6px 0 0}}

.mon{{display:flex;flex-direction:column;gap:12px}}
.mon>header{{display:flex;justify-content:space-between;align-items:flex-end;
            gap:16px;border-bottom:2px solid var(--ink);padding-bottom:10px;
            flex-wrap:wrap}}
.mon>header .brand{{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;
                   text-transform:uppercase;color:var(--mut)}}
.mon h2{{font-family:var(--serif);font-weight:640;font-size:27px;margin:2px 0 0;
        letter-spacing:-.015em}}
.meta{{text-align:right;font-size:13px;color:var(--mut);
      display:flex;flex-direction:column;gap:4px;align-items:flex-end}}
.meta b{{font-family:var(--serif);font-size:20px;color:var(--ink);
        margin-right:5px;font-weight:640}}
.meta span{{font-family:var(--mono);font-size:11px;color:var(--dim);margin-left:8px}}
.flags{{display:flex;gap:6px}}
.flag{{font-style:normal;font-family:var(--mono);font-size:10px;letter-spacing:.05em;
      border-radius:999px;padding:2px 9px}}
.flag.bad{{background:var(--bad-bg);color:var(--bad)}}
.flag.warn{{background:var(--warn-bg);color:var(--warn)}}

.cal{{background:var(--card);border:1px solid var(--line);border-radius:14px;
     padding:12px;overflow-x:auto}}
.dow,.days{{display:grid;grid-template-columns:repeat(7,minmax(132px,1fr));gap:6px}}
.dow span{{font-family:var(--mono);font-size:10px;letter-spacing:.14em;
          text-transform:uppercase;color:var(--mut);padding:0 4px 8px}}
.day,.pad{{min-height:104px}}
.day{{border:1px solid var(--hair);border-radius:9px;padding:6px;
     display:flex;flex-direction:column;gap:4px;background:var(--bg)}}
.day.wknd{{background:transparent}}
.day.has{{border-color:var(--line);background:var(--card)}}
.day.today{{border-color:var(--acc);box-shadow:inset 0 0 0 1px var(--acc)}}
.day .n{{font-family:var(--mono);font-size:11px;color:var(--dim);
        font-variant-numeric:tabular-nums}}
.day.today .n{{color:var(--acc);font-weight:500}}

.send{{border-left:3px solid var(--dim);background:var(--hair);border-radius:0 6px 6px 0;
      padding:4px 6px;display:flex;flex-direction:column;gap:1px}}
.send b{{font-size:12px;font-weight:600;line-height:1.25;word-break:break-word}}
.send span{{font-size:10.5px;color:var(--mut);line-height:1.25}}
.send i{{font-style:normal;font-family:var(--mono);font-size:9.5px;margin-top:2px}}
.send .of{{color:var(--acc)}}
.send .vs{{color:var(--dim)}}
.send.ask{{border-left-color:var(--ask)}} .send.ask b{{color:var(--ask)}}
.send.help{{border-left-color:var(--help)}}
.send.belong{{border-left-color:var(--belong)}}
.send.real{{border-left-color:var(--real)}}
.send.brand{{border-left-color:var(--brandc)}}
.send.aff{{border-left-color:var(--aff)}}

/* one brand at a time */
.brands{{display:flex;gap:6px;flex-wrap:wrap;border-bottom:1px solid var(--line);
        padding-bottom:14px;margin-bottom:-16px}}
.btab{{background:transparent;border:1px solid var(--line);border-radius:999px;
      padding:6px 15px;font:inherit;font-size:14px;color:var(--mut);cursor:pointer;
      text-transform:capitalize}}
.btab:hover{{border-color:var(--ink);color:var(--ink)}}
.btab.on{{background:var(--ink);border-color:var(--ink);color:var(--bg);font-weight:500}}
.btab:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
.mon[hidden]{{display:none}}

/* the month at a glance */
.sum{{display:flex;flex-direction:column;gap:13px}}
.bigs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
.big{{background:var(--card);border:1px solid var(--line);border-radius:11px;
     padding:12px 14px;display:flex;flex-direction:column;gap:1px}}
.big b{{font-family:var(--serif);font-weight:640;font-size:26px;line-height:1;
       letter-spacing:-.02em}}
.big span{{font-size:12.5px;color:var(--mut);margin-top:3px}}
.big.bad{{border-color:var(--bad);background:var(--bad-bg)}}
.big.bad b{{color:var(--bad)}}
.big i{{font-style:normal;font-family:var(--mono);font-size:10px;color:var(--dim);
       margin-top:3px;line-height:1.35}}
.mix{{display:flex;height:8px;border-radius:4px;overflow:hidden;gap:2px}}
.mix .seg{{display:block}}
.mix .ask{{background:var(--ask)}} .mix .help{{background:var(--help)}}
.mix .belong{{background:var(--belong)}} .mix .real{{background:var(--real)}}
.mix .brand{{background:var(--brandc)}} .mix .aff{{background:var(--aff)}}
.rows{{display:flex;flex-direction:column;gap:7px}}
.crow{{display:grid;grid-template-columns:74px 1fr;gap:12px;align-items:baseline}}
.crow .t{{font-family:var(--mono);font-size:10px;letter-spacing:.12em;
         text-transform:uppercase;color:var(--dim)}}
.cs{{display:flex;flex-wrap:wrap;gap:5px}}
.chip{{background:var(--card);border:1px solid var(--line);border-radius:999px;
      padding:3px 9px;font:inherit;font-size:12.5px;color:var(--ink);cursor:pointer;
      display:inline-flex;gap:6px;align-items:baseline}}
.chip b{{font-family:var(--mono);font-size:10.5px;color:var(--mut);font-weight:500}}
.chip:hover{{border-color:var(--ink)}}
.chip.on{{background:var(--ink);border-color:var(--ink);color:var(--bg)}}
.chip.on b{{color:var(--bg);opacity:.7}}
.chip:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
.cs .none{{font-style:normal;font-size:12.5px;color:var(--dim)}}
.send.dim{{opacity:.16}}

/* a send is a button now */
.send{{border:0;border-left:3px solid var(--dim);text-align:left;width:100%;
      font-family:inherit;cursor:pointer}}
.send:hover{{filter:brightness(.97)}}
.send:focus-visible{{outline:2px solid var(--acc);outline-offset:1px}}

/* the detail panel */
#veil{{position:fixed;inset:0;background:rgba(12,14,16,.42);backdrop-filter:blur(2px);
      opacity:0;pointer-events:none;transition:.16s;z-index:40}}
#veil.on{{opacity:1;pointer-events:auto}}
#panel{{position:fixed;top:0;right:0;bottom:0;width:min(560px,100%);z-index:50;
       background:var(--card);border-left:1px solid var(--line);
       transform:translateX(100%);transition:.2s cubic-bezier(.3,.8,.4,1);
       overflow-y:auto;display:flex;flex-direction:column}}
#panel.on{{transform:none}}
#panel .ph{{position:sticky;top:0;background:var(--card);
           border-bottom:1px solid var(--line);padding:18px 22px;
           display:flex;justify-content:space-between;align-items:flex-start;gap:14px}}
#panel .when{{font-family:var(--mono);font-size:11px;letter-spacing:.1em;
             text-transform:uppercase;color:var(--mut)}}
#panel h3{{font-family:var(--serif);font-weight:640;font-size:24px;margin:4px 0 0;
          letter-spacing:-.015em}}
#panel .sub{{color:var(--mut);font-size:13.5px;margin-top:3px}}
#x{{border:1px solid var(--line);background:transparent;color:var(--mut);
   border-radius:8px;width:30px;height:30px;font-size:16px;cursor:pointer;flex:none}}
#x:hover{{border-color:var(--ink);color:var(--ink)}}
.pb{{padding:20px 22px 40px;display:flex;flex-direction:column;gap:20px}}
.blk{{display:flex;flex-direction:column;gap:7px}}
.blk>.t{{font-family:var(--mono);font-size:10px;letter-spacing:.14em;
        text-transform:uppercase;color:var(--dim)}}
.blk p{{margin:0;font-size:14px;line-height:1.5;color:var(--ink)}}
.blk p.q{{color:var(--mut)}}
.kv{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:9px}}
.kv div{{background:var(--bg);border:1px solid var(--hair);border-radius:8px;
        padding:8px 10px;display:flex;flex-direction:column;gap:2px}}
.kv .k{{font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;
       text-transform:uppercase;color:var(--dim)}}
.kv .v{{font-size:13.5px;font-weight:500;word-break:break-word}}
.var{{background:var(--acc-bg);border-left:3px solid var(--acc);
     border-radius:0 8px 8px 0;padding:11px 13px;display:flex;
     flex-direction:column;gap:4px}}
.var .av{{font-family:var(--mono);font-size:11px;color:var(--acc)}}
.var .an{{font-size:14px;line-height:1.45}}
.var .dr{{font-size:12px;color:var(--mut);border-top:1px solid var(--line);
         padding-top:6px;margin-top:2px}}
.hand{{background:var(--bg);border:1px dashed var(--line);border-radius:10px;
      padding:13px 15px;display:flex;flex-direction:column;gap:9px}}
.hand .row{{display:grid;grid-template-columns:96px 1fr;gap:12px;font-size:13px;
           align-items:baseline}}
.hand .row em{{font-style:normal;font-family:var(--mono);font-size:10px;
              letter-spacing:.1em;text-transform:uppercase;color:var(--dim)}}
.hand .row span{{font-family:var(--mono);font-size:12px;word-break:break-all;
                line-height:1.45}}
.hand .miss{{color:var(--bad)}}
.hand a{{color:var(--acc)}}
.hand .dim{{font-style:normal;color:var(--dim);font-size:11px}}
.why{{background:var(--bg);border-left:3px solid var(--line);padding:11px 14px;
     border-radius:0 8px 8px 0;font-size:13.5px;color:var(--mut);line-height:1.5}}
@media(max-width:600px){{#panel{{width:100%}}}}

.key{{display:flex;gap:14px;flex-wrap:wrap;color:var(--mut);font-size:12px;
     border-top:1px solid var(--line);padding-top:14px}}
.key i{{font-style:normal;display:inline-block;width:9px;height:9px;
       border-radius:2px;margin-right:6px;vertical-align:baseline}}
/* how a month gets made */
.how{{background:var(--card);border:1px solid var(--line);border-radius:13px;
     padding:14px 17px}}
.how summary{{cursor:pointer;font-family:var(--mono);font-size:11px;
             letter-spacing:.11em;text-transform:uppercase;color:var(--mut)}}
.how[open] summary{{margin-bottom:14px}}
.howb{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}}
.cgrp h4{{font-family:var(--serif);font-weight:640;font-size:16px;margin:0 0 3px}}
.cn{{font-size:12.5px;color:var(--mut);margin:0 0 10px;line-height:1.4}}
.st2{{display:grid;grid-template-columns:54px 1fr;gap:10px;padding:7px 0;
     border-top:1px solid var(--hair)}}
.st2 b{{font-size:13.5px;font-weight:600}}
.st2 p{{font-size:12.5px;color:var(--mut);margin:2px 0 4px;line-height:1.4}}
.st2 code{{font-family:var(--mono);font-size:10.5px;background:var(--bg);
          padding:1px 5px;border-radius:4px;word-break:break-all}}
.st2 i{{font-style:normal;font-family:var(--mono);font-size:10px;color:var(--dim)}}
.who{{font-family:var(--mono);font-size:9px;letter-spacing:.08em;text-transform:uppercase;
     border-radius:999px;padding:2px 0;text-align:center;height:fit-content}}
.who.ai{{background:var(--acc-bg);color:var(--acc)}}
.who.code{{background:var(--hair);color:var(--dim)}}

footer{{color:var(--dim);font-size:12px;font-family:var(--mono)}}
@media(max-width:900px){{
  .dow{{display:none}}
  .days{{grid-template-columns:1fr}}
  .pad{{display:none}}
  .day{{min-height:0}}
  .day:not(.has){{display:none}}
  .day .n::after{{content:" — " attr(data-d)}}
}}
@media print{{
  body{{background:#fff}}
  .cal{{border:0;padding:0}}
  .mon{{break-inside:avoid}}
}}
</style>

<div class="wrap">
  <div>
    <h1>The calendar</h1>
    <p class="lede">Every month planned, at its real dates. What goes out, to whom,
      and what it sells.</p>
  </div>

  {tabs}
  {"".join(month_block(r) for r in runs)}

  <div class="key">
    <span><i style="background:var(--ask)"></i>Promotional</span>
    <span><i style="background:var(--help)"></i>Educational</span>
    <span><i style="background:var(--belong)"></i>Cultural</span>
    <span><i style="background:var(--real)"></i>Community</span>
    <span><i style="background:var(--brandc)"></i>Brand</span>
    <span><i style="background:var(--aff)"></i>Affiliate</span>
  </div>

  <details class="how">
    <summary>How a month gets made — {len(CH.BEFORE)} steps before, {len(CH.STAGES)} layers, {len(CH.AFTER)} after</summary>
    <div class="howb">
      {chain_block("Before the month", CH.BEFORE,
                   "Per brand, and rarely. These change what the brand KNOWS.")}
      {chain_layers()}
      {chain_block("After the month", CH.AFTER, "Every plan, and free.")}
    </div>
  </details>

  <footer>built {datetime.datetime.now().strftime("%d %b %Y %H:%M")} · click a send to see it</footer>
</div>

<div id="veil"></div>
<aside id="panel" aria-hidden="true"></aside>

<script>
const SLOTS = {json.dumps(detail)};
const esc = t => String(t ?? "").replace(/[&<>"]/g, c =>
  ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
const panel = document.getElementById("panel");
const veil  = document.getElementById("veil");

function row(label, value, missing) {{
  return `<div class="row"><em>${{esc(label)}}</em><span class="${{missing?"miss":""}}">${{esc(value)}}</span></div>`;
}}
function kv(label, value) {{
  if (value === null || value === undefined || value === "" ) return "";
  return `<div><span class="k">${{esc(label)}}</span><span class="v">${{esc(value)}}</span></div>`;
}}

function open(key) {{
  const s = SLOTS[key];
  if (!s) return;
  const when = new Date(s.date + "T00:00:00").toLocaleDateString(undefined,
    {{weekday:"long", day:"numeric", month:"long"}});
  const vars = (s.variants || []).map(v => `
    <div class="var">
      ${{v.avatar ? `<span class="av">${{esc(v.avatar)}}</span>` : ""}}
      <span class="an">${{esc(v.angle || "— no angle decided upstream —")}}</span>
      ${{v.dropped ? `<span class="dr">dropped: ${{esc(v.dropped)}}</span>` : ""}}
    </div>`).join("");

  panel.innerHTML = `
    <div class="ph">
      <div>
        <div class="when">${{esc(s.brand)}} · ${{esc(s.id)}} · ${{esc(when)}} ${{esc(s.hour)}}:00</div>
        <h3>${{esc(s.type)}}</h3>
        <div class="sub">${{esc(s.category)}} · ${{esc(s.segment)}}</div>
      </div>
      <button id="x" aria-label="Close">&times;</button>
    </div>
    <div class="pb">

      <div class="blk">
        <span class="t">The concept</span>
        <p>${{esc(s.occasion || "—")}}</p>
      </div>

      <div class="blk">
        <span class="t">The angle — the line the copy has to carry</span>
        ${{vars || "<p class='q'>none</p>"}}
      </div>

      <div class="blk">
        <span class="t">The slot</span>
        <div class="kv">
          ${{kv("role in the arc", s.role)}}
          ${{kv("offer", s.offer)}}
          ${{kv("product", s.product)}}
          ${{kv("avatar", (s.variants||[]).map(v=>v.avatar).filter(Boolean).join(" · "))}}
          ${{s.anchored ? kv("anchored", "to this date") : ""}}
          ${{s.affiliate ? kv("affiliate", s.affiliate) : ""}}
          ${{s.follows ? kv("follows", s.follows) : ""}}
          ${{s.then ? kv("then", s.then) : ""}}
        </div>
      </div>

      <div class="blk">
        <span class="t">What goes to the copy machine</span>
        <div class="hand">
          ${{s.unfilled
              ? row("format", "NO FORMAT — this brand has no email of this type to write from", true)
              : `<div class="row"><em>format</em><span><a href="/source?path=${{encodeURIComponent(s.source_path)}}" target="_blank">${{esc(s.source)}}</a><br><i class="dim">${{esc(s.source_path)}}</i></span></div>`}}
          ${{s.source_brand ? row("borrowed", "the shape comes from " + s.source_brand
                                  + "; the send is still " + s.brand) : ""}}
          ${{row("occasion", s.occasion || "none")}}
          ${{row("send date", s.date + "  " + s.hour + ":00")}}
          ${{row("offer", s.offer === "none" ? "none — and that is a decision, not a gap" : s.offer)}}
          ${{row("research", s.research || "none")}}
        </div>
      </div>

      <div class="blk">
        <span class="t">Why the planner chose this</span>
        <div class="why">${{esc(s.why || "—")}}
          ${{s.spent ? "<br><br>" + esc(s.spent) : ""}}</div>
      </div>

    </div>`;
  panel.classList.add("on"); veil.classList.add("on");
  panel.setAttribute("aria-hidden", "false");
  document.getElementById("x").onclick = close;
  document.getElementById("x").focus();
}}
function close() {{
  panel.classList.remove("on"); veil.classList.remove("on");
  panel.setAttribute("aria-hidden", "true");
}}
document.querySelectorAll(".send").forEach(b =>
  b.addEventListener("click", () => open(b.dataset.key)));

/* the summary IS the filter — a chip dims everything it does not describe,
   inside its own month, so two brands can be read side by side */
document.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => {{
  const mon = c.closest(".mon");
  const same = c.classList.contains("on");
  mon.querySelectorAll(".chip").forEach(x => x.classList.remove("on"));
  if (!same) c.classList.add("on");
  const f = same ? null : c.dataset.filter, v = same ? null : c.dataset.value;
  mon.querySelectorAll(".send").forEach(s => {{
    const hit = !f || (f === "avatar"
      ? (s.dataset.avatar || "").split(" ").includes(v)
      : s.dataset[f] === v);
    s.classList.toggle("dim", !hit);
  }});
}}));
veil.addEventListener("click", close);

/* one brand at a time — the choice survives a rebuild of the page */
const KEY = "calendar.brand";
function showBrand(b) {{
  document.querySelectorAll(".mon").forEach(m =>
    m.hidden = !(b === "*" || m.dataset.brand === b));
  document.querySelectorAll(".btab").forEach(t =>
    t.classList.toggle("on", t.dataset.brand === b));
  try {{ localStorage.setItem(KEY, b); }} catch (e) {{ /* private window */ }}
}}
document.querySelectorAll(".btab").forEach(t =>
  t.addEventListener("click", () => showBrand(t.dataset.brand)));
if (document.querySelector(".btab")) {{
  let want = "*";
  try {{ want = localStorage.getItem(KEY) || "*"; }} catch (e) {{}}
  if (!document.querySelector(`.btab[data-brand="${{want}}"]`)) want = "*";
  showBrand(want);
}}
document.addEventListener("keydown", e => {{ if (e.key === "Escape") close(); }});
</script>
"""


def build(out=None, run=None, quiet=False, extra=()):
    if run:
        p = Path(run)
        runs = [p if p.is_dir() else RUNS / run]
    else:
        roots = [RUNS] + [Path(x).expanduser() for x in extra]
        # every root is a shelf: <root>/<brand>/<YYYY-MM>/
        found = [d for r in roots for d in paths.months(r)]
        # one month per brand: a folder that is a replay of a month another
        # folder holds LIVE would otherwise show twice, and the stale one wins
        # nothing by being seen.
        best = {}
        for d in found:
            try:
                st = json.loads((d / "run.json").read_text())
                key = (st.get("brand"), st.get("month"))
            except (OSError, ValueError):
                key = (str(d), None)
            m = (d / "slots.json").stat().st_mtime
            if key not in best or m > best[key][0]:
                best[key] = (m, d)
        runs = [d for _, d in sorted(best.values(), reverse=True)]
    if not runs:
        raise SystemExit(f"no planned months in {RUNS}")
    out = Path(out) if out else paths.SYSTEM / "calendar.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(runs))
    if not quiet:
        print(f"-> {rel(out)}  ({len(runs)} month(s))")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--from", dest="extra", action="append", default=[],
                    help="another folder holding planned months; repeatable")
    ap.add_argument("--out")
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()
    p = build(a.out, a.run, extra=a.extra)
    if a.open:
        subprocess.run(["open", str(p)])


if __name__ == "__main__":
    main()
