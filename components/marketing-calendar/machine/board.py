#!/usr/bin/env python3
"""The review board: a planned month as a person reads and corrects it.

    python3 board.py ../../runs/marketing-calendar/<brand>/2026-09          # build board.html
    python3 board.py ../../runs/marketing-calendar/<brand>/2026-09 --open   # and open it

The calendar decides what exists and when. This is where a human disagrees:
every send on the month laid out at its real date, with the machine's reason
for it beside it, and the fields a reviewer may rewrite as fields they can
actually type into. Approve, mark for work, cut, leave a note — then hand the
approved sends to whatever writes the copy.

The page is static HTML and readable on its own. The editing and the hand-off
need `serve.py` running behind it; opened straight off disk it still shows the
whole month, and says so rather than failing silently.
"""
import argparse
import datetime
import html
import json
import re
import subprocess
import sys
from pathlib import Path

import chain as CH
import review as R

CATS = {"ask": "Promotional", "help": "Educational", "belong": "Cultural",
        "real": "Community", "brand": "Brand", "affiliate": "Affiliate"}
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def esc(x):
    return html.escape(str(x if x is not None else ""), quote=True)


def read_run(run_dir):
    run_dir = Path(run_dir)
    slots = json.loads((run_dir / "slots.json").read_text())
    if isinstance(slots, dict):
        slots = slots.get("slots", [])
    try:
        state = json.loads((run_dir / "run.json").read_text())
    except (FileNotFoundError, ValueError):
        state = {}
    checks = ""
    try:
        checks = (run_dir / "checks.md").read_text()
    except FileNotFoundError:
        pass
    return slots, state, checks


def split_checks(checks):
    """checks.md's two human-facing lists, back out as lists."""
    breaks, warns, bucket = [], [], None
    for line in checks.splitlines():
        if line.startswith("## Breaks"):
            bucket = breaks
        elif line.startswith("## Warnings"):
            bucket = warns
        elif line.startswith("## "):
            bucket = None
        elif bucket is not None and line.startswith("- "):
            bucket.append(line[2:].strip())
    return breaks, warns


def month_of(slots, state):
    m = state.get("month")
    if m:
        return m
    for s in slots:
        if s.get("date"):
            return s["date"][:7]
    return ""


# ------------------------------------------------------------- the pieces ---

def _shown(slot, name, fallback=None):
    rev = slot.get("_review", {}) or {}
    edits = rev.get("edits") or {}
    if name in edits:
        return edits[name], True
    v = fallback if fallback is not None else slot.get(name)
    return ("" if v is None else v), False


def fld(slot, name, label, kind="text", fallback=None, cls=""):
    val, edited = _shown(slot, name, fallback)
    orig = (slot.get("_orig") or {}).get(name)
    tag = (f'<textarea class="in {cls}" data-slot="{esc(slot["id"])}" '
           f'data-field="{name}" rows="2">{esc(val)}</textarea>'
           if kind == "area" else
           f'<input class="in {cls}" data-slot="{esc(slot["id"])}" '
           f'data-field="{name}" value="{esc(val)}">')
    was = (f'<span class="was" title="what the planner decided">was '
           f'{esc(orig)}</span>') if edited else ""
    return (f'<label class="f{" edited" if edited else ""}">'
            f'<span class="k">{esc(label)}</span>{tag}{was}</label>')


def card(slot):
    sid = slot["id"]
    rev = slot.get("_review", {}) or {}
    status = rev.get("status", "pending")
    cop = (slot.get("_copy") or {}).get("state", "")
    d = slot.get("date") or ""
    try:
        dt = datetime.date.fromisoformat(d)
        day = f'{DOW[dt.weekday()]} {dt.day}'
        long = dt.strftime("%d %B %Y")
    except ValueError:
        day, long = d, d

    variants = slot.get("variants") or [{"avatar": slot.get("avatar"),
                                         "angle": slot.get("angle", "")}]
    angle_val = variants[0].get("angle", "") if variants else ""

    chips = []
    if slot.get("anchored"):
        chips.append('<i class="chip anchor">anchored to the date</i>')
    if slot.get("affiliate"):
        chips.append(f'<i class="chip">affiliate · {esc(slot["affiliate"])}</i>')
    if slot.get("follows"):
        chips.append(f'<i class="chip">follows {esc(slot["follows"])}</i>')
    if slot.get("then"):
        chips.append(f'<i class="chip">then {esc(slot["then"])}</i>')
    if cop:
        chips.append(f'<i class="chip copy {esc(cop)}">copy {esc(cop)}</i>')

    avatars = " · ".join(esc(v.get("avatar")) for v in variants if v.get("avatar"))
    dropped = variants[0].get("angle_dropped") if variants else None

    btns = "".join(
        f'<button class="st {s}{" on" if status == s else ""}" '
        f'data-slot="{esc(sid)}" data-status="{s}">{lbl}</button>'
        for s, lbl in (("approved", "Approve"), ("needs-work", "Needs work"),
                       ("cut", "Cut")))

    why = slot.get("why") or ""
    return f"""
<article class="slot s-{status}" id="s-{esc(sid)}" data-status="{status}"
         data-search="{esc((slot.get('type','') + ' ' + slot.get('segment','') + ' ' + (slot.get('occasion') or '') + ' ' + angle_val).lower())}">
  <header class="top">
    <div class="when"><b>{esc(day)}</b><span>{esc(long)} · {esc(slot.get('hour',''))}:00</span></div>
    <div class="head">
      <h3>{esc(slot.get('type',''))} <em>{esc(slot.get('category',''))}</em></h3>
      <p class="seg">{esc(slot.get('segment',''))}{f' · {avatars}' if avatars else ''}</p>
      <div class="chips">{''.join(chips)}</div>
    </div>
    <div class="acts">{btns}</div>
  </header>

  <div class="grid">
    {fld(slot, 'date', 'Date', cls='mono')}
    {fld(slot, 'hour', 'Hour', cls='mono')}
    {fld(slot, 'segment', 'Segment')}
    {fld(slot, 'type', 'Type')}
    {fld(slot, 'category', 'Category')}
    {fld(slot, 'role', 'Role in the arc')}
    {fld(slot, 'offer', 'Offer')}
    {fld(slot, 'product', 'Product')}
  </div>

  {fld(slot, 'occasion', 'What it is about', kind='area')}
  {fld(slot, 'angle', 'The angle — the line the copy has to carry',
       kind='area', fallback=angle_val)}

  <details class="why">
    <summary>Why the planner chose this</summary>
    <div class="whybody">
      <p>{esc(why)}</p>
      {f'<p class="drop"><b>Dropped:</b> {esc(dropped)}</p>' if dropped else ''}
      {f'<p class="src"><b>Source:</b> <code>{esc(slot["source"])}</code></p>' if slot.get('source') else ''}
      {f'<p class="src"><b>Spent before:</b> {esc(slot["spent"])}</p>' if slot.get('spent') else ''}
    </div>
  </details>

  <footer class="foot">
    <label class="note"><span class="k">Note for the writer</span>
      <textarea class="in" data-slot="{esc(sid)}" data-note="1" rows="2"
        placeholder="What to fix, what to keep, anything the copy must not say">{esc(rev.get('note',''))}</textarea>
    </label>
    <button class="write" data-slot="{esc(sid)}">Write the copy</button>
  </footer>
</article>"""


def chain_strip(state):
    """The nine layers that made this month, in order, with what each produced
    — and for the two that think, the prompt file that decided it and a link
    to the prompt as actually sent. the owner's standing rule: every stage's prompt
    and every stage's output has to be visible on a page, or the only loop that
    matters (read the output, tighten the prompt) is broken."""
    rows = []
    for s in CH.ordered(state):
        r, st = s["run"] or {}, s["status"]
        made = ("—" if r.get("produced") is None
                else f'{r["produced"]} {s["unit"]}{"" if r["produced"] == 1 else "s"}')
        bits = []
        if r.get("prompt_name"):
            bits.append(f'<code>{esc(r["prompt_name"])}</code>')
        if r.get("seconds"):
            bits.append(f'{r["seconds"]}s')
        links = []
        for label, k in (("prompt sent", "sent"), ("reasoning", "reasoning"),
                         ("output", "out")):
            if r.get(k):
                links.append(f'<a href="{esc(r[k])}">{label}</a>')
        note = r.get("note") if st == "unrecorded" else None
        # A layer that ran on a partial brand record says so here, or the
        # month reads as confident as one planned on everything.
        if r.get("ran_on") == "degraded" and r.get("losing"):
            note = "ran on a partial record — " + r["losing"][0]
        elif (state.get("brand_readiness") or {}).get(s["key"], {}).get("losing"):
            note = ("ran on a partial record — "
                    + state["brand_readiness"][s["key"]]["losing"][0])
        rows.append(
            f'<div class="ly {st}">'
            f'<span class="ln">{s["n"]}</span>'
            f'<span class="lnm">{esc(s["name"])}</span>'
            f'<span class="lby {s["by"]}">{"thinks" if s["by"] == "ai" else "code"}</span>'
            f'<span class="lmade">{esc(made)}</span>'
            f'<span class="lbits">{" · ".join(bits)}</span>'
            f'<span class="llinks">{" · ".join(links)}</span>'
            + (f'<span class="lnote">{esc(note)}</span>' if note else '')
            + '</div>')
    degraded = [k for k, v in (state.get("brand_readiness") or {}).items()
                if v.get("verdict") == "degraded"]
    ev = state.get("events") or []
    foot = ""
    if ev:
        foot = ('<div class="lfoot">' + " · ".join(
            f'{esc(e.get("what"))} <i>{esc((e.get("at") or "")[5:16].replace("T", " "))}</i>'
            for e in ev[-2:]) + "</div>")
    warn = (f' · <b class="degwarn">{len(degraded)} layer(s) ran on a partial '
            f'record</b>') if degraded else ""
    return (f'<details class="chain"{" open" if degraded else ""}>'
            f'<summary>How this month was built — '
            f'{len(CH.STAGES)} layers, {len(CH.AI_KEYS)} of them thinking{warn}</summary>'
            f'<div class="lys">{"".join(rows)}</div>{foot}</details>')


def month_strip(slots, month):
    """The month in its own shape. A planner's output is a calendar; reading it
    only as a list hides the thing a person actually checks — the spacing."""
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
    for n in range(1, (nxt - first).days + 1):
        here = by_day.get(n, [])
        marks = "".join(
            f'<a class="pip s-{(s.get("_review") or {}).get("status","pending")}" '
            f'href="#s-{esc(s["id"])}" title="{esc(s.get("type",""))} · {esc(s.get("segment",""))}">'
            f'{esc(s.get("type",""))}</a>' for s in here)
        cells.append(f'<div class="day{" has" if here else ""}">'
                     f'<span class="n">{n}</span>{marks}</div>')
    cells.append("</div>")
    return f'<div class="strip">{"".join(cells)}</div>'


# --------------------------------------------------------------- the page ---

def render(run_dir, slots, state, checks):
    month = month_of(slots, state)
    breaks, warns = split_checks(checks)
    brand = state.get("brand") or Path(run_dir).parent.name or "—"
    try:
        title_month = datetime.date.fromisoformat(month + "-01").strftime("%B %Y")
    except ValueError:
        title_month = month

    counts = {"pending": 0, "approved": 0, "needs-work": 0, "cut": 0}
    for s in slots:
        counts[(s.get("_review") or {}).get("status", "pending")] += 1
    n = len(slots)
    done = counts["approved"] + counts["cut"]

    tiles = "".join(
        f'<button class="tab" data-filter="{k}"><b>{v}</b><span>{lbl}</span></button>'
        for k, v, lbl in (("all", n, "sends"), ("pending", counts["pending"], "not reviewed"),
                          ("approved", counts["approved"], "approved"),
                          ("needs-work", counts["needs-work"], "needs work"),
                          ("cut", counts["cut"], "cut")))

    def lst(items, kind):
        if not items:
            return ""
        rows = "".join(f"<li>{esc(i)}</li>" for i in items)
        return f'<section class="checks {kind}"><h2>{"Breaks" if kind=="bad" else "Warnings"}</h2><ul>{rows}</ul></section>'

    return f"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(brand)} · {esc(title_month)} — review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,640&family=Instrument+Sans:wght@400;500;600&family=Spline+Sans+Mono:wght@400;500&display=swap">
<style>
:root{{
  --bg:#F1F0EA; --card:#FFFFFF; --ink:#191B1D; --mut:#676C73;
  --line:#DBD9D2; --hair:#E9E7E1; --acc:#2E5D50; --acc-bg:#DFEBE6;
  --ok:#2E5D50; --ok-bg:#DFEBE6; --warn:#8A5A12; --warn-bg:#F5E9D2;
  --bad:#8E3B2F; --bad-bg:#F3DFDB;
  --sans:"Instrument Sans",system-ui,-apple-system,sans-serif;
  --serif:Fraunces,Georgia,serif;
  --mono:"Spline Sans Mono",ui-monospace,SFMono-Regular,monospace;
}}
@media (prefers-color-scheme:dark){{
  :root:not([data-theme="light"]){{
    --bg:#0E1012; --card:#16191C; --ink:#E6E8EA; --mut:#8E959D;
    --line:#272B30; --hair:#1E2226; --acc:#74B4A2; --acc-bg:#12251F;
    --ok:#74B4A2; --ok-bg:#12251F; --warn:#D6A55B; --warn-bg:#2A2113;
    --bad:#E08877; --bad-bg:#2B1714;
  }}
}}
:root[data-theme="dark"]{{
  --bg:#0E1012; --card:#16191C; --ink:#E6E8EA; --mut:#8E959D;
  --line:#272B30; --hair:#1E2226; --acc:#74B4A2; --acc-bg:#12251F;
  --ok:#74B4A2; --ok-bg:#12251F; --warn:#D6A55B; --warn-bg:#2A2113;
  --bad:#E08877; --bad-bg:#2B1714;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
     font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1080px;margin:0 auto;padding:34px 22px 120px;
      display:flex;flex-direction:column;gap:26px}}
h1{{font-family:var(--serif);font-weight:640;font-size:clamp(30px,5vw,46px);
   line-height:1.03;margin:0;letter-spacing:-.02em;text-wrap:balance}}
h2{{font-family:var(--serif);font-weight:600;font-size:21px;margin:0 0 8px}}
h3{{font-family:var(--serif);font-weight:640;font-size:19px;margin:0;letter-spacing:-.01em}}
h3 em{{font-style:normal;font-family:var(--sans);font-weight:500;font-size:12px;
      text-transform:uppercase;letter-spacing:.09em;color:var(--mut);margin-left:8px}}
p{{margin:0}}
.eyebrow{{font-family:var(--mono);font-size:11px;letter-spacing:.16em;
         text-transform:uppercase;color:var(--mut)}}
.lede{{color:var(--mut);max-width:62ch;margin-top:10px}}

/* ---- sticky rail ---- */
.rail{{position:sticky;top:0;z-index:20;background:var(--bg);
      border-bottom:1px solid var(--line);margin:0 -22px;padding:10px 22px;
      display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.tab{{background:var(--card);border:1px solid var(--line);border-radius:10px;
     padding:6px 11px;display:flex;gap:7px;align-items:baseline;cursor:pointer;
     font:inherit;color:var(--ink)}}
.tab b{{font-family:var(--mono);font-weight:500;font-variant-numeric:tabular-nums}}
.tab span{{color:var(--mut);font-size:12.5px}}
.tab.active{{background:var(--ink);color:var(--bg);border-color:var(--ink)}}
.tab.active span{{color:var(--bg);opacity:.75}}
.tab:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
.rail .sp{{flex:1}}
#q{{border:1px solid var(--line);background:var(--card);color:var(--ink);
   border-radius:10px;padding:7px 11px;font:inherit;min-width:180px}}
.bulk{{background:var(--acc);color:#fff;border:0;border-radius:10px;
      padding:8px 14px;font:inherit;font-weight:600;cursor:pointer}}

/* ---- the chain ---- */
.chain{{background:var(--card);border:1px solid var(--line);border-radius:14px;
       padding:13px 16px}}
.chain summary{{cursor:pointer;font-family:var(--mono);font-size:11px;
               letter-spacing:.11em;text-transform:uppercase;color:var(--mut)}}
.chain summary:focus-visible{{outline:2px solid var(--acc);border-radius:6px}}
.chain[open] summary{{margin-bottom:11px}}
.lys{{display:flex;flex-direction:column}}
.ly{{display:grid;grid-template-columns:26px 1fr 62px 104px 1fr auto;gap:11px;
    align-items:baseline;padding:7px 0;border-top:1px solid var(--hair);font-size:13.5px}}
.ly:first-child{{border-top:0}}
.ly.unrecorded{{color:var(--mut)}}
.ln{{font-family:var(--mono);font-size:11.5px;color:var(--dim,var(--mut));
    font-variant-numeric:tabular-nums}}
.lnm{{font-weight:600}}
.lby{{font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;
     border-radius:999px;padding:2px 7px;text-align:center}}
.lby.ai{{background:var(--acc-bg);color:var(--acc)}}
.lby.code{{background:var(--hair);color:var(--mut)}}
.lmade{{font-family:var(--mono);font-size:12px;color:var(--mut);
       font-variant-numeric:tabular-nums}}
.lbits,.llinks{{font-size:12px;color:var(--mut)}}
.lbits code{{font-family:var(--mono);font-size:11px;background:var(--hair);
            padding:1px 5px;border-radius:4px}}
.llinks a{{color:var(--acc);text-decoration:none;border-bottom:1px solid transparent}}
.llinks a:hover{{border-bottom-color:var(--acc)}}
.lnote{{grid-column:2/-1;font-size:12px;color:var(--warn);margin-top:2px}}
.degwarn{{color:var(--warn);font-weight:600;text-transform:none;letter-spacing:0;font-family:var(--sans);font-size:12px}}
.lfoot{{border-top:1px solid var(--hair);margin-top:9px;padding-top:9px;
       font-family:var(--mono);font-size:11px;color:var(--mut)}}
.lfoot i{{font-style:normal;color:var(--dim,var(--mut))}}
@media(max-width:760px){{
  .ly{{grid-template-columns:24px 1fr auto;gap:7px}}
  .lmade,.lbits,.llinks{{grid-column:2/-1}}
}}

/* ---- month strip ---- */
.strip{{background:var(--card);border:1px solid var(--line);border-radius:14px;
       padding:14px;overflow-x:auto}}
.dow,.days{{display:grid;grid-template-columns:repeat(7,minmax(96px,1fr));gap:6px}}
.dow span{{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;
          text-transform:uppercase;color:var(--mut);padding:0 2px 6px}}
.day{{min-height:66px;border:1px solid var(--hair);border-radius:9px;padding:5px;
     display:flex;flex-direction:column;gap:4px}}
.day.has{{border-color:var(--line);background:var(--bg)}}
.day .n{{font-family:var(--mono);font-size:11px;color:var(--mut);
        font-variant-numeric:tabular-nums}}
.pip{{display:block;font-size:11px;line-height:1.25;padding:3px 5px;border-radius:6px;
     text-decoration:none;color:var(--ink);background:var(--hair);
     border-left:3px solid var(--mut);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pip.s-approved{{border-left-color:var(--ok);background:var(--ok-bg);color:var(--ok)}}
.pip.s-needs-work{{border-left-color:var(--warn);background:var(--warn-bg);color:var(--warn)}}
.pip.s-cut{{border-left-color:var(--bad);background:var(--bad-bg);color:var(--bad);
           text-decoration:line-through;opacity:.8}}
.pad{{min-height:66px}}

/* ---- checks ---- */
.checks{{border-radius:12px;padding:14px 16px;border:1px solid var(--line)}}
.checks.bad{{background:var(--bad-bg);border-color:var(--bad)}}
.checks.warn{{background:var(--warn-bg);border-color:var(--warn)}}
.checks ul{{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:5px}}
.checks li{{font-size:14px}}

/* ---- a send ---- */
.list{{display:flex;flex-direction:column;gap:14px}}
.slot{{background:var(--card);border:1px solid var(--line);border-radius:14px;
      padding:16px 18px;display:flex;flex-direction:column;gap:13px;
      border-left:4px solid var(--line);scroll-margin-top:78px}}
.slot.s-approved{{border-left-color:var(--ok)}}
.slot.s-needs-work{{border-left-color:var(--warn)}}
.slot.s-cut{{border-left-color:var(--bad);opacity:.62}}
.top{{display:grid;grid-template-columns:120px 1fr auto;gap:16px;align-items:start}}
.when b{{display:block;font-family:var(--serif);font-weight:640;font-size:22px;
        line-height:1.1;font-variant-numeric:tabular-nums}}
.when span{{font-family:var(--mono);font-size:11px;color:var(--mut)}}
.seg{{color:var(--mut);font-size:13.5px;margin-top:3px}}
.chips{{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}}
.chip{{font-style:normal;font-family:var(--mono);font-size:10.5px;letter-spacing:.05em;
      background:var(--hair);color:var(--mut);border-radius:999px;padding:3px 9px}}
.chip.anchor{{background:var(--acc-bg);color:var(--acc)}}
.chip.copy.done{{background:var(--ok-bg);color:var(--ok)}}
.chip.copy.running,.chip.copy.queued{{background:var(--warn-bg);color:var(--warn)}}
.chip.copy.failed{{background:var(--bad-bg);color:var(--bad)}}
.acts{{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}}
.st{{border:1px solid var(--line);background:transparent;color:var(--mut);
    border-radius:9px;padding:6px 11px;font:inherit;font-size:13px;cursor:pointer}}
.st:hover{{border-color:var(--ink);color:var(--ink)}}
.st.approved.on{{background:var(--ok);border-color:var(--ok);color:#fff}}
.st.needs-work.on{{background:var(--warn);border-color:var(--warn);color:#fff}}
.st.cut.on{{background:var(--bad);border-color:var(--bad);color:#fff}}
.st:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}

.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:10px}}
.f{{display:flex;flex-direction:column;gap:4px}}
.k{{font-family:var(--mono);font-size:10px;letter-spacing:.13em;
   text-transform:uppercase;color:var(--mut)}}
.in{{width:100%;border:1px solid var(--hair);background:var(--bg);color:var(--ink);
    border-radius:8px;padding:7px 9px;font:inherit;font-size:14px;resize:vertical}}
.in:focus{{outline:2px solid var(--acc);outline-offset:-1px;border-color:var(--acc)}}
.in.mono{{font-family:var(--mono);font-variant-numeric:tabular-nums}}
.f.edited .in{{border-color:var(--acc);background:var(--acc-bg)}}
.was{{font-family:var(--mono);font-size:10.5px;color:var(--mut)}}

.why{{border-top:1px solid var(--hair);padding-top:10px}}
.why summary{{cursor:pointer;font-family:var(--mono);font-size:11px;
             letter-spacing:.1em;text-transform:uppercase;color:var(--mut)}}
.why summary:focus-visible{{outline:2px solid var(--acc);border-radius:6px}}
.whybody{{display:flex;flex-direction:column;gap:8px;padding-top:9px;
         font-size:14px;color:var(--mut);max-width:74ch}}
.whybody b{{color:var(--ink);font-weight:600}}
.whybody code{{font-family:var(--mono);font-size:12px;word-break:break-all}}

.foot{{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:end;
      border-top:1px solid var(--hair);padding-top:12px}}
.note{{display:flex;flex-direction:column;gap:4px}}
.write{{background:var(--ink);color:var(--bg);border:0;border-radius:9px;
       padding:9px 15px;font:inherit;font-weight:600;cursor:pointer;white-space:nowrap}}
.write[disabled]{{opacity:.45;cursor:progress}}
.write:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}

#toast{{position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(20px);
       background:var(--ink);color:var(--bg);padding:11px 18px;border-radius:11px;
       font-size:13.5px;opacity:0;pointer-events:none;transition:.18s;z-index:50;
       max-width:min(560px,90vw)}}
#toast.on{{opacity:1;transform:translateX(-50%) translateY(0)}}
#toast.bad{{background:var(--bad);color:#fff}}
footer.meta{{color:var(--mut);font-size:12.5px;border-top:1px solid var(--line);
            padding-top:14px;font-family:var(--mono)}}
@media(max-width:760px){{
  .top{{grid-template-columns:1fr;gap:9px}}
  .acts{{justify-content:flex-start}}
  .foot{{grid-template-columns:1fr}}
  .dow,.days{{grid-template-columns:repeat(7,minmax(62px,1fr))}}
}}
@media(prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style>

<div class="wrap">
  <div>
    <div class="eyebrow">{esc(brand)} · planned month · {esc(n)} sends</div>
    <h1>{esc(title_month)}</h1>
    <p class="lede">Every send the planner placed, at its real date, with the reason
      it chose it. Rewrite anything that reads wrong, cut anything that shouldn't run,
      then hand the approved sends to the writer.</p>
  </div>

  <div class="rail">
    {tiles}
    <span class="sp"></span>
    <input id="q" type="search" placeholder="Filter by type, segment, angle…">
    <button class="bulk" id="writeAll">Write the copy for all approved</button>
  </div>

  {chain_strip(state)}
  {month_strip(slots, month)}
  {lst(breaks, "bad")}
  {lst(warns, "warn")}

  <div class="list" id="list">
    {"".join(card(s) for s in slots)}
  </div>

  <footer class="meta">
    {esc(done)}/{esc(n)} decided · built {datetime.datetime.now().strftime("%d %b %Y %H:%M")}
    · run <code>{esc(Path(run_dir).parent.name + '/' + Path(run_dir).name)}</code>
  </footer>
</div>

<div id="toast"></div>
<script>
const toast = (m, bad) => {{
  const t = document.getElementById('toast');
  t.textContent = m; t.className = 'on' + (bad ? ' bad' : '');
  clearTimeout(t._x); t._x = setTimeout(() => t.className = '', 3200);
}};
async function post(path, body) {{
  const r = await fetch(path, {{method:'POST', headers:{{'Content-Type':'application/json'}},
                               body: JSON.stringify(body)}});
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}}
const OFFLINE = "Open this through the review server to save changes — run serve.py.";

/* status */
document.querySelectorAll('.st').forEach(b => b.addEventListener('click', async () => {{
  const slot = b.dataset.slot, status = b.dataset.status;
  const art = document.getElementById('s-' + slot);
  const was = art.dataset.status;
  const next = was === status ? 'pending' : status;
  try {{ await post('/api/status', {{slot, status: next}}); }}
  catch (e) {{ return toast(OFFLINE, true); }}
  art.dataset.status = next;
  art.className = 'slot s-' + next;
  art.querySelectorAll('.st').forEach(x => x.classList.toggle('on', x.dataset.status === next));
  const pip = document.querySelector('.pip[href="#s-' + slot + '"]');
  if (pip) pip.className = 'pip s-' + next;
  recount();
}}));

/* edits + notes, saved when you leave the field */
document.querySelectorAll('.in').forEach(el => {{
  el._was = el.value;
  el.addEventListener('change', async () => {{
    if (el.value === el._was) return;
    const slot = el.dataset.slot;
    try {{
      if (el.dataset.note) await post('/api/note', {{slot, note: el.value}});
      else await post('/api/edit', {{slot, field: el.dataset.field, value: el.value}});
    }} catch (e) {{ el.value = el._was; return toast(OFFLINE, true); }}
    el._was = el.value;
    if (!el.dataset.note) el.closest('.f').classList.add('edited');
    toast('Saved.');
  }});
}});

/* hand off to the writer */
async function write(slots, btn) {{
  if (btn) btn.disabled = true;
  try {{
    const r = await post('/api/write', {{slots}});
    toast(r.message || ('Writing ' + slots.length + ' send' + (slots.length===1?'':'s') + '…'));
  }} catch (e) {{ toast(OFFLINE, true); }}
  finally {{ if (btn) btn.disabled = false; }}
}}
document.querySelectorAll('.write').forEach(b =>
  b.addEventListener('click', () => write([b.dataset.slot], b)));
document.getElementById('writeAll').addEventListener('click', e => {{
  const ids = [...document.querySelectorAll('.slot[data-status="approved"]')]
                .map(a => a.id.slice(2));
  if (!ids.length) return toast('Nothing is approved yet.', true);
  write(ids, e.target);
}});

/* filter + search */
let filter = 'all';
function apply() {{
  const q = document.getElementById('q').value.trim().toLowerCase();
  document.querySelectorAll('.slot').forEach(a => {{
    const okS = filter === 'all' || a.dataset.status === filter;
    const okQ = !q || a.dataset.search.includes(q);
    a.style.display = (okS && okQ) ? '' : 'none';
  }});
}}
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {{
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  t.classList.add('active'); filter = t.dataset.filter; apply();
}}));
document.getElementById('q').addEventListener('input', apply);
function recount() {{
  const c = {{all: 0, pending: 0, approved: 0, 'needs-work': 0, cut: 0}};
  document.querySelectorAll('.slot').forEach(a => {{ c.all++; c[a.dataset.status]++; }});
  document.querySelectorAll('.tab').forEach(t => t.querySelector('b').textContent = c[t.dataset.filter]);
  apply();
}}
document.querySelector('.tab').classList.add('active');
</script>
"""


def build(run_dir, quiet=False):
    run_dir = Path(run_dir)
    slots, state, checks = read_run(run_dir)
    merged = R.applied(slots, R.load(run_dir))
    out = run_dir / "board.html"
    out.write_text(render(run_dir, merged, state, checks))
    if not quiet:
        print(f"  -> board  ({len(merged)} sends) {out}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()
    p = build(a.run_dir)
    if a.open:
        subprocess.run(["open", str(p)])


if __name__ == "__main__":
    main()
