#!/usr/bin/env python3
"""The Feedback Forms page — one self-contained HTML page and its Markdown
mirror, written from the brand configs and runs/feedback-forms/:

    python3 components/feedback-forms/docs/make_page.py

  runs/feedback-forms/_system/feedback-forms.html   the page (live form previews inside, submit off)
  runs/feedback-forms/_system/FEEDBACK-FORMS.md     the same content in Markdown, for the team

Reads brands/<b>/operations/feedback-stages.json + feedback-questions.json,
runs/feedback-forms/<b>/kill-list.json, runs/feedback-forms/_system/status.json and
runs/feedback-forms/_system/designer-draft.md. Writes nothing else.
"""
import html
import json
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS.parent))
import build as B  # noqa: E402

RUNS = B.WORKSPACE / "runs" / "feedback-forms"
OUT = RUNS / "_system"
AREA_LABEL = {"marketing": "Marketing", "product": "Product", "operations": "Operations",
              "customer-service": "Customer service", "customer-experience": "Customer experience", "website": "Website"}
TYPE_LABEL = {"choice": "tap", "multi": "taps", "scale": "score", "text": "open text"}
e = html.escape


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def data():
    status = jload(RUNS / "_system" / "status.json", {}) or {}
    out = []
    for b in B.brands():
        st, qs = B.load(b)
        kills = (jload(RUNS / b / "kill-list.json", {}) or {}).get("messages", [])
        lp = qs.get("language_pass")
        bank = (jload(B.WORKSPACE / lp / "queries.json", {}) or {}) if lp else {}
        cover = (jload(B.WORKSPACE / lp / "coverage.json", {}) or {}) if lp else {}
        out.append(dict(brand=b, stages=st, questions=qs, kills=kills, bank=bank, cover=cover, lp=lp,
                        status=(status.get("brands") or {}).get(b, {}),
                        runtime=B.runtime(st, qs, "preview"), logo=B.logo_data_uri(qs),
                        css=[l for l in B.brand_css(qs, fonts=False).splitlines() if l.startswith(".fb[")]))
    return out, status


def designer():
    t = (RUNS / "_system" / "designer-draft.md").read_text() if (RUNS / "_system" / "designer-draft.md").exists() else ""
    body = t.split("---", 2)[1] if t.count("---") >= 2 else t
    items = re.findall(r"^\d\. \*\*(.+?)\*\*\s*(.+)$", body, re.M)
    return items, t


def trig(s):
    t = s["klaviyo"]["trigger"]
    return f"{t['metric']}" + (f" ({t['integration']})" if t.get("integration") else "")


def n_q(q):
    base = [x for x in q["questions"] if not x.get("show_if")]
    extra = len(q["questions"]) - len(base)
    return f"{len(base)}" + (f" +{extra} follow-up" if extra else "")


# ---------------------------------------------------------------- HTML

CSS = """
:root{--bg:#f6f5f1;--surface:#ffffff;--surface-2:#efede7;--ink:#1d1c1a;--muted:#67635b;--line:#dedad0;
--accent:#2d5b4f;--accent-ink:#ffffff;--ok:#2e7a4d;--ok-bg:#e3f1e8;--draft:#8a5a00;--draft-bg:#f7ecd4;
--blocked:#a3261d;--blocked-bg:#f8e1de;--live:#1f5fa8;--live-bg:#e0ebf8;--shadow:0 1px 2px rgba(0,0,0,.05),0 4px 16px rgba(0,0,0,.04)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#131311;--surface:#1c1b19;--surface-2:#252420;
--ink:#ecebe5;--muted:#a3a097;--line:#35332e;--accent:#8cc3b1;--accent-ink:#10231d;--ok:#8fd1a6;--ok-bg:#1d3326;
--draft:#f0c46b;--draft-bg:#3a2e14;--blocked:#f29b92;--blocked-bg:#3d1f1b;--live:#9cc3f0;--live-bg:#1b2b3f;--shadow:none}}
:root[data-theme="dark"]{--bg:#131311;--surface:#1c1b19;--surface-2:#252420;--ink:#ecebe5;--muted:#a3a097;--line:#35332e;
--accent:#8cc3b1;--accent-ink:#10231d;--ok:#8fd1a6;--ok-bg:#1d3326;--draft:#f0c46b;--draft-bg:#3a2e14;--blocked:#f29b92;
--blocked-bg:#3d1f1b;--live:#9cc3f0;--live-bg:#1b2b3f;--shadow:none}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 "Instrument Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:28px 16px 80px}
h1,h2,h3{font-family:"Instrument Sans",system-ui,sans-serif;line-height:1.15;margin:0}
h1{font-size:34px;letter-spacing:-.02em}
h2{font-size:24px;letter-spacing:-.01em;margin:44px 0 6px}
h3{font-size:17px}
p{margin:0}
.sub{color:var(--muted);margin-top:8px;max-width:72ch}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;font-size:13px;font-weight:600;max-width:100%;overflow-wrap:anywhere}
.chip.ok{background:var(--ok-bg);color:var(--ok)}.chip.draft{background:var(--draft-bg);color:var(--draft)}
.chip.blocked{background:var(--blocked-bg);color:var(--blocked)}.chip.live{background:var(--live-bg);color:var(--live)}
.chip.plain{background:var(--surface-2);color:var(--muted)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:var(--shadow)}
.flow{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-top:14px}
.step{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px;position:relative}
.step b{display:block;font-size:14px}.step span{display:block;color:var(--muted);font-size:13px;margin-top:2px}
.step .who{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:4px}
@media (max-width:820px){.flow{grid-template-columns:1fr 1fr}}
.tabs{display:flex;gap:8px;margin:18px 0 0;flex-wrap:wrap}
.tab{appearance:none;border:1px solid var(--line);background:var(--surface);color:var(--ink);font:inherit;font-weight:600;
padding:9px 16px;border-radius:999px;cursor:pointer}
.tab[aria-selected="true"]{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.brand-panel[hidden]{display:none}
.split{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:20px;margin-top:16px;align-items:start}
.split>*{min-width:0}
@media (max-width:900px){.split{grid-template-columns:1fr}}
.tablewrap{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:640px}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);font-weight:700;background:var(--surface-2)}
tr:last-child td{border-bottom:0}
td .small{color:var(--muted);font-size:13px;display:block;margin-top:2px}
.phone{position:sticky;top:16px}
.phone-frame{border:1px solid var(--line);border-radius:26px;overflow:hidden;height:640px;background:var(--surface-2);box-shadow:var(--shadow);display:flex;flex-direction:column}
.phone-frame .fb{flex:1;overflow:auto;min-height:0}
.phone-note{color:var(--muted);font-size:13px;margin:8px 4px 0}
.stagepick{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.stagepick button{appearance:none;border:1px solid var(--line);background:var(--surface);color:var(--ink);font:inherit;font-size:12.5px;
padding:5px 10px;border-radius:999px;cursor:pointer}
.stagepick button[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
details.stage{background:var(--surface);border:1px solid var(--line);border-radius:12px;margin-top:10px}
details.stage>summary{cursor:pointer;padding:14px 16px;display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;list-style:none}
details.stage>summary::-webkit-details-marker{display:none}
details.stage>summary::before{content:"+";font-weight:700;color:var(--muted);width:14px}
details.stage[open]>summary::before{content:"–"}
.stage-body{padding:0 16px 16px}
ol.qs{margin:0;padding-left:0;list-style:none;display:grid;gap:10px}
ol.qs li{border-top:1px solid var(--line);padding-top:10px}
.q{font-weight:600}.q .n{color:var(--muted);font-weight:500;margin-right:6px}
.meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.tag{font-size:12px;padding:2px 8px;border-radius:6px;background:var(--surface-2);color:var(--muted)}
.tag.area{background:var(--live-bg);color:var(--live)}
.tag.type{background:var(--ok-bg);color:var(--ok)}
.opts{color:var(--muted);font-size:14px;margin-top:4px}
.old{color:var(--muted);font-size:13px;margin-top:4px;font-style:italic}
.email{margin-top:14px;background:var(--surface-2);border-radius:10px;padding:14px;font-size:14.5px}
.email .hd{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);font-weight:700;margin-bottom:6px}
.email p{margin:6px 0}
.btnlike{display:inline-block;background:var(--accent);color:var(--accent-ink);padding:6px 12px;border-radius:6px;font-weight:600;font-size:13px}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;word-break:break-all}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px}
@media (max-width:820px){.grid3{grid-template-columns:1fr}}
ul.clean{margin:8px 0 0;padding-left:18px}ul.clean li{margin:4px 0}
a{color:var(--accent)}
.foot{margin-top:48px;color:var(--muted);font-size:13px}
details.bank{margin-top:8px;border:1px dashed var(--line);border-radius:8px;background:var(--surface-2)}
details.bank>summary{cursor:pointer;padding:6px 10px;font-size:13px;font-weight:600;color:var(--accent)}
.bank-body{padding:0 12px 10px}
.bk-h{font-size:11.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);font-weight:700;margin:10px 0 4px}
.opt-h{font-size:14px;font-weight:600;margin:8px 0 2px}
.small-in{font-weight:400;color:var(--muted);font-size:13px}
ul.lines{margin:0;padding-left:16px}ul.lines li{margin:3px 0;font-size:14px}
.quote{display:block}
.small{color:var(--muted);font-size:12.5px;display:block}
.ba{font-size:14px;background:var(--surface);border-radius:6px;padding:8px 10px;margin-top:8px;border:1px solid var(--line)}
.lbl{display:inline-block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--draft);background:var(--draft-bg);border-radius:4px;padding:1px 6px;margin-right:4px}
.lbl.now{color:var(--ok);background:var(--ok-bg)}
.note{margin:0 0 10px;padding:10px 12px;border-radius:8px;background:var(--draft-bg);color:var(--ink);font-size:14px}
.themebtn{float:right;appearance:none;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer}
"""


SRC_LABEL = {"survey": "old Google Form", "ticket": "support email", "comment": "ad comment", "community": "Reddit / forum",
             "review": "store review", "interview": "customer interview", "panel": "paid panel", "database": "customer database",
             "creator-comment": "creator comment", "dm": "DM"}


def bank_line(d, rid):
    """One bank row as the page shows it: the words, the id, how often said, what kind of source."""
    r = (d.get("bank") or {}).get("rows", {}).get(rid)
    if not r:
        return f"<li><span class='mono'>{e(rid)}</span></li>"
    said = f"said {r['said']}×" if (r.get("said") or 1) > 1 else "said once"
    src = SRC_LABEL.get(r.get("source_type"), r.get("source_type") or "")
    return (f"<li><span class='quote'>“{e(r['text'][:260])}{'…' if len(r['text']) > 260 else ''}”</span>"
            f"<span class='small'>{e(said)} · {e(r.get('lane') or '')} lane · {e(src)} · <span class='mono'>{e(rid.split('_', 3)[-1])}</span></span></li>")


def bank_block(d, x):
    """The 'from the bank' drawer under a question: before → after, the lines
    its wording came from, and each tap option's lines."""
    used = x.get("language_used") or []
    ol = x.get("options_language") or []
    if not used and not ol and not x.get("was"):
        return ""
    ba = ""
    if x.get("was") and x["was"] != x["text"]:
        ba = f"<div class='ba'><span class='lbl'>Before</span> {e(x['was'])}<br><span class='lbl now'>After</span> {e(x['text'])}</div>"
    elif x.get("was"):
        ba = "<div class='ba'><span class='lbl'>Wording kept</span> — the bank lines below back it.</div>"
    elif "was" in x:
        ba = "<div class='ba'><span class='lbl now'>New question</span> — written from the lines below.</div>"
    if x.get("was_options") and x["was_options"] != x.get("options"):
        ba += (f"<div class='ba'><span class='lbl'>Taps before</span> {e(' · '.join(x['was_options']))}<br>"
               f"<span class='lbl now'>Taps after</span> {e(' · '.join(x.get('options') or []))}</div>")
    words = (f"<div class='bk-h'>The wording came from</div><ul class='lines'>{''.join(bank_line(d, i) for i in used)}</ul>"
             if used else "<div class='bk-h'>The wording: no bank line — a plain question</div>")
    opts = ""
    for o in ol:
        head = (f"{e(o['option'])} <span class='small-in'>— {o['rows']} row{'s' if o['rows'] != 1 else ''} in this lane say it"
                + (f" · loudest said {o['said']}×" if (o.get('said') or 0) > 1 else "") + "</span>") if o.get("theme") else \
               f"{e(o['option'])} <span class='small-in'>— {e(o.get('note') or 'cited by hand')}</span>"
        lines = "".join(bank_line(d, i) for i in (o.get("language_used") or [])[:3])
        opts += f"<div class='opt-h'>{head}</div>" + (f"<ul class='lines'>{lines}</ul>" if lines else "")
    if opts:
        opts = "<div class='bk-h'>Each tap option, and the real answers behind it</div>" + opts
    n = len(used) + sum(len(o.get("language_used") or []) for o in ol)
    return (f"<details class='bank'><summary>From the bank · {n} line{'s' if n != 1 else ''}"
            + (" · wording changed" if x.get("was") and x["was"] != x["text"] else "") + "</summary>"
            f"<div class='bank-body'>{ba}{words}{opts}</div></details>")


def email_bank(d, sid, em, was):
    used = em.get("language_used") or []
    rows = []
    for k in ("subject", "preview", "button"):
        if was and was.get(k) is not None and was.get(k) != em.get(k):
            rows.append(f"<div class='ba'><span class='lbl'>{k.capitalize()} before</span> {e(was[k])}<br>"
                        f"<span class='lbl now'>After</span> {e(em[k])}</div>")
    if was and was.get("body") and was["body"] != em.get("body"):
        rows.append("<div class='ba'><span class='lbl'>Body before</span> " + " / ".join(e(p) for p in was["body"]) + "</div>")
    old = f"<p class='small'>Kept from the old email: {e(em['from_old'])}</p>" if em.get("from_old") else ""
    lines = f"<div class='bk-h'>The email's words came from</div><ul class='lines'>{''.join(bank_line(d, i) for i in used)}</ul>" if used else ""
    if not (rows or lines or old):
        return ""
    return f"<details class='bank'><summary>From the bank · the email · {len(used)} lines</summary><div class='bank-body'>{old}{''.join(rows)}{lines}</div></details>"


def cover_table(d):
    c = d.get("cover") or {}
    if not c:
        return ""
    rows = "".join(
        f"<tr><td><b>{e(sid)}</b></td><td>{x['rows_queried']:,}</td><td>{x['questions_citing']} / {x['questions']}</td>"
        f"<td>{x['taps_citing']} / {x['taps']}</td><td>{'yes' if x.get('email_citing') else 'no'}</td>"
        f"<td>{e(x.get('language_note') or '')}</td></tr>" for sid, x in c.items())
    tq = sum(x["questions"] for x in c.values()); tc = sum(x["questions_citing"] for x in c.values())
    tt = sum(x["taps"] for x in c.values()); ttc = sum(x["taps_citing"] for x in c.values())
    nq = len((d.get("bank") or {}).get("queries") or [])
    return (f"<h3 style='margin-top:6px'>Where the words came from</h3>"
            f"<p class='sub' style='margin-bottom:10px'>Every question, tap option and email below was written from this brand's language bank, "
            f"queried through the language layer — {nq} queries over {(d.get('bank') or {}).get('bank_rows', 0):,} bank rows. "
            f"<b>{tc} of {tq}</b> questions and <b>{ttc} of {tt}</b> tap options cite real lines. Open “From the bank” under any question to see them. "
            f"Record: <span class='mono'>{e(d.get('lp') or '')}/queries.md</span></p>"
            "<div class='tablewrap'><table><thead><tr><th>Stage</th><th>Rows queried</th><th>Questions citing</th><th>Taps citing</th>"
            "<th>Email cites</th><th>Thin?</th></tr></thead><tbody>" + rows + "</tbody></table></div>")


def status_chip(s):
    if s.get("status") == "blocked":
        return '<span class="chip blocked">Blocked</span>'
    return '<span class="chip draft">Ready for email_lead</span>'


def stage_table(d):
    rows = []
    for s in d["stages"]["stages"]:
        q = d["questions"]["stages"][s["stage"]]
        k = s["klaviyo"]
        rows.append(
            f"<tr><td><b>{e(s['label'])}</b><span class='small mono'>{e(s['stage'])}</span></td>"
            f"<td>{e(trig(s))}" + (f"<span class='small'>only if: {e('; '.join(k['trigger_filters']))}</span>" if k.get("trigger_filters") else "")
            + "".join(f"<span class='small'>• {e(f)}</span>" for f in k.get("flow_filters") or []) + "</td>"
            f"<td>{e(k['wait'])}</td><td>{n_q(q)}</td><td>{e(s['lane'])}</td><td>{status_chip(s)}"
            + (f"<span class='small'>{e(s['blocked_by'][:180])}{'…' if len(s['blocked_by']) > 180 else ''}</span>" if s.get("blocked_by") else "")
            + "</td></tr>")
    return ("<div class='tablewrap'><table><thead><tr><th>Stage</th><th>Trigger → filters</th><th>Wait</th>"
            "<th>Questions</th><th>Files into</th><th>Status</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def stage_details(d):
    out = []
    form = d["stages"]["form"]
    for s in d["stages"]["stages"]:
        sid = s["stage"]
        q = d["questions"]["stages"][sid]
        em = q["email"]
        items = []
        for x in q["questions"]:
            opts = f"<div class='opts'>Options: {e(' · '.join(x.get('options') or []))}{' · Other (types it)' if x.get('other') else ''}</div>" if x.get("options") else ""
            if x["type"] == "scale":
                opts = f"<div class='opts'>Score {x['min']}–{x['max']} ({e(x.get('low', ''))} → {e(x.get('high', ''))})</div>"
            cond = ""
            if x.get("show_if"):
                c = x["show_if"]
                cond = f"<div class='opts'>Only shown when “{e(c['q'])}” is {'one of' if c.get('in') else 'anything but'}: {e(', '.join(c.get('in') or c.get('not_in') or []))}</div>"
            old = f"<div class='old'>From the old form — {e(x['from_old'])}</div>" if x.get("from_old") else ""
            items.append(f"<li><div class='q'><span class='n'>{x['n']}.</span>{e(x['text'])}</div>{opts}{cond}"
                         f"<div class='meta'><span class='tag type'>{TYPE_LABEL.get(x['type'], x['type'])}</span>"
                         + "".join(f"<span class='tag area'>{e(AREA_LABEL.get(a, a))}</span>" for a in x.get("areas") or [])
                         + "".join(f"<span class='tag'>→ {e(y)}</span>" for y in x.get("yields") or [])
                         + f"</div>{old}{bank_block(d, x)}</li>")
        link = form["link"].replace("{stage}", sid)
        body = "".join(f"<p>{e(p)}</p>" for p in em["body"]) + f"<p><span class='btnlike'>{e(em['button'])}</span></p>" \
            + "".join(f"<p>{e(p)}</p>" for p in em.get("after") or [])
        out.append(
            f"<details class='stage'><summary><b>{e(s['label'])}</b><span class='chip plain'>{n_q(q)} questions</span>"
            f"{status_chip(s)}<span class='chip plain'>{e(s['klaviyo']['flow_name'])}</span></summary>"
            f"<div class='stage-body'><p class='sub' style='margin:0 0 10px'><b>{e(q['title'])}</b> — {e(q['intro'])}</p>"
            + (f"<p class='note'><b>Thin in the bank:</b> {e(q['language_note'])}</p>" if q.get("language_note") else "")
            + f"<ol class='qs'>{''.join(items)}</ol>"
            f"<div class='email'><div class='hd'>The email · from {e(d['stages']['email']['from_label'])}</div>"
            f"<p><b>Subject:</b> {e(em['subject'])}<br><b>Preview:</b> {e(em['preview'])}</p>{body}"
            f"<p class='mono'>Button link: {e(link)}</p>{email_bank(d, sid, em, (q.get('was') or {}).get('email'))}</div></div></details>")
    return "".join(out)


def kill_table(d):
    if not d["kills"]:
        return ("<p class='sub'>No kill list: reading this brand's Klaviyo flows needs its private key. "
                f"{e(d['questions']['label'])} has no old survey on file to replace.</p>")
    rows = "".join(
        f"<tr><td><b>{e(k['flow_name'])}</b><span class='small'>flow {e(k['flow_status'])}</span></td>"
        f"<td>{e(k['message_name'])}<span class='small'>“{e(k['subject'])}”</span></td>"
        f"<td><span class='chip {'live' if k['state'] == 'live' else 'plain'}'>{'Sending now' if k['state'] == 'live' else e(k['state'].capitalize())}</span></td>"
        f"<td>{e(k['form'])}</td><td>{e(k.get('replaced_by') or '—')}<span class='small'>{e(k.get('switch_off') or '')}</span></td></tr>"
        for k in d["kills"])
    return ("<div class='tablewrap'><table><thead><tr><th>Flow</th><th>Email</th><th>Today</th><th>Links to</th>"
            "<th>Replaced by · what would be switched off</th></tr></thead><tbody>" + rows + "</tbody></table></div>"
            "<p class='phone-note'>Read from Klaviyo 2026-09-29. Nothing on this list has been changed — switching anything off is owner's call.</p>")


def page():
    ds, status = data()
    vitems, _ = designer()
    blocked = sum(1 for d in ds for s in d["stages"]["stages"] if s.get("status") == "blocked")
    ready = sum(1 for d in ds for s in d["stages"]["stages"] if s.get("status") != "blocked")
    prs = {d["brand"]: (d["status"] or {}).get("pr") for d in ds}
    tabs = "".join(f"<button class='tab' role='tab' aria-selected='{'true' if i == 0 else 'false'}' data-b='{d['brand']}'>"
                   f"{e(d['questions']['label'])}</button>" for i, d in enumerate(ds))
    panels = []
    for i, d in enumerate(ds):
        b = d["brand"]
        form = d["stages"]["form"]
        pr = prs.get(b)
        picks = "".join(f"<button type='button' data-stage='{e(s)}' aria-pressed='{'true' if s == d['questions']['default_stage'] else 'false'}'>{e(s)}</button>"
                        for s in d["questions"]["stages"])
        panels.append(f"""
<section class="brand-panel" data-b="{b}" {'hidden' if i else ''}>
  <div class="chips">
    <span class="chip plain">Form: {e(form['url'])}</span>
    {f'<a class="chip draft" href="{e(pr)}">Pull request for email_lead</a>' if pr else '<span class="chip draft">Pull request: pending</span>'}
    <span class="chip plain">Klaviyo public id {e(d['stages']['klaviyo']['public_id'])}</span>
    <span class="chip {'ok' if (d['status'] or {}).get('pull', '').startswith('on') else 'blocked'}">Into the bank: {e((d['status'] or {}).get('pull', ''))}</span>
  </div>
  <div class="split">
    <div>
      {cover_table(d)}
      <h3 style="margin-top:26px">Stage map</h3>
      <p class="sub" style="margin-bottom:10px">Who gets which feedback email, when. What the flow already knows (orders, subscription, bought or not) rides along with the answers — the form never asks it.</p>
      {stage_table(d)}
      <h3 style="margin-top:26px">Every stage's questions, word for word</h3>
      <p class="sub">Blue tags = the part of the business the answer serves. Arrows = what it gives the language bank. Open-text answers become bank rows; taps and scores ride along on those rows.</p>
      {stage_details(d)}
    </div>
    <div class="phone">
      <div class="stagepick" data-b="{b}">{picks}</div>
      <div class="phone-frame"><div class="fb-mount" data-b="{b}"></div></div>
      <p class="phone-note">The real form, running. Tap through it — sending is switched off here; the last screen shows exactly what Klaviyo would receive.</p>
    </div>
  </div>
  <h3 style="margin-top:30px">Kill list — old Google Form surveys still in Klaviyo</h3>
  {kill_table(d)}
  <p class="sub" style="margin-top:10px"><b>End-to-end:</b> {e((d['status'] or {}).get('e2e', ''))}</p>
</section>""")
    brand_css = "\n".join(l for d in ds for l in d["css"])
    cfgs = {d["brand"]: dict(d["runtime"], look=dict(d["runtime"]["look"], logo=d["logo"])) for d in ds}
    cfgs_js = json.dumps(cfgs, ensure_ascii=False).replace("</", "<\\/")
    val = "".join(f"<li><b>{e(t)}</b> {e(re.sub(r'[`*]', '', rest))}</li>" for t, rest in vitems)
    nt = "".join(f"<li>{e(x)}</li>" for x in status.get("not_touched") or [])
    e2e = "".join(f'<span class="chip ok">{e(d["questions"]["label"])} end-to-end test passed</span>' for d in ds
                  if isinstance((d["status"] or {}).get("e2e"), str) and d["status"]["e2e"]
                  and not d["status"]["e2e"].startswith("Not run"))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Feedback Forms</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}
{B.ENGINE_CSS.read_text()}
{brand_css}
.fb{{min-height:100%}}
</style>
</head>
<body>
<div class="wrap">
  <button class="themebtn" type="button" id="themebtn">Light / dark</button>
  <h1>Feedback Forms</h1>
  <p class="sub">One feedback form per brand, one set of questions per customer stage, sent by Klaviyo at the right moment. Every answer lands in Klaviyo and is pulled into our language bank each morning — filed by stage, tagged by the part of the business it helps, searchable.</p>
  <div class="chips">
    <span class="chip live">Live: nothing yet</span>
    <span class="chip draft">{ready} stages ready for email_lead to build (Draft)</span>
    <span class="chip blocked">{blocked} stages blocked on access</span>
    {e2e}
  </div>

  <h2>How one answer travels</h2>
  <div class="flow">
    <div class="step"><div class="who">Klaviyo</div><b>Trigger</b><span>Something happens: delivered, refunded, checkout abandoned…</span></div>
    <div class="step"><div class="who">Klaviyo</div><b>Wait</b><span>1 day to 75 days, per stage</span></div>
    <div class="step"><div class="who">Klaviyo</div><b>Email</b><span>A short founder note, one button</span></div>
    <div class="step"><div class="who">Brand's own site</div><b>Form</b><span>One question at a time, on the phone</span></div>
    <div class="step"><div class="who">Klaviyo</div><b>“Submitted Feedback”</b><span>All answers, on that customer's profile</span></div>
    <div class="step"><div class="who">Our system, 05:30</div><b>Language bank</b><span>Filed by stage and business area</span></div>
  </div>

  <h2>By brand</h2>
  <div class="tabs" role="tablist">{tabs}</div>
  {''.join(panels)}

  <h2>email_lead installs it in Klaviyo</h2>
  <div class="grid3">
    <div class="card"><h3>1 · Review the form</h3><p class="sub">Each brand's form is a pull request on its page repo. Merging publishes the page; nothing is emailed yet.</p>
      <ul class="clean">{''.join(f"<li>{e(d['questions']['label'])}: " + (f"<a href='{e(prs[d['brand']])}'>{e(prs[d['brand']])}</a>" if prs.get(d['brand']) else "pending") + "</li>" for d in ds)}</ul></div>
    <div class="card"><h3>2 · Build the flows (Draft)</h3><p class="sub">One install sheet per brand: every flow's trigger, filters, wait, subject, email and the exact button link.</p>
      <ul class="clean">{''.join(f"<li><span class='mono'>{e(B.install_path(d['brand']).relative_to(B.WORKSPACE).as_posix())}</span></li>" for d in ds)}</ul></div>
    <div class="card"><h3>3 · owner says go</h3><p class="sub">Flows stay in Draft until you say go. Then the kill list above says which old survey emails to switch off.</p></div>
  </div>

  <h2>What only designer can unlock</h2>
  <div class="card"><p class="sub" style="margin:0 0 6px">Draft message, not sent: <span class="mono">runs/feedback-forms/_system/designer-draft.md</span></p><ol class="clean">{val}</ol></div>

  <h2>What was and wasn't touched</h2>
  <div class="card"><ul class="clean">{nt}</ul></div>

  <p class="foot">Built from brands/&lt;brand&gt;/operations/feedback-stages.json and feedback-questions.json by components/feedback-forms/docs/make_page.py · updated {e(status.get('updated', ''))}. Markdown copy: runs/feedback-forms/_system/FEEDBACK-FORMS.md.</p>
</div>
<script>
window.FEEDBACK_CONFIGS = {cfgs_js};
</script>
<script>
{B.ENGINE_JS.read_text()}
</script>
<script>
(function () {{
  var stored = null;
  try {{ stored = localStorage.getItem("ff-theme"); }} catch (e) {{}}
  if (stored) document.documentElement.setAttribute("data-theme", stored);
  document.getElementById("themebtn").addEventListener("click", function () {{
    var dark = document.documentElement.getAttribute("data-theme") === "dark" ||
      (!document.documentElement.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
    var next = dark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {{ localStorage.setItem("ff-theme", next); }} catch (e) {{}}
  }});
  function show(b, stage) {{
    var el = document.querySelector('.fb-mount[data-b="' + b + '"]');
    el.innerHTML = ""; el.className = "fb-mount";
    FeedbackForm.mount(el, window.FEEDBACK_CONFIGS[b], {{ mode: "preview", stage: stage, scrub: false, autofocus: false,
      params: {{ stage: stage, email: "", kx: "", flow: null, message: null, test: false }} }});
    document.querySelectorAll('.stagepick[data-b="' + b + '"] button').forEach(function (x) {{
      x.setAttribute("aria-pressed", x.getAttribute("data-stage") === stage ? "true" : "false"); }});
  }}
  Object.keys(window.FEEDBACK_CONFIGS).forEach(function (b) {{ show(b, window.FEEDBACK_CONFIGS[b].default_stage); }});
  document.querySelectorAll(".stagepick button").forEach(function (btn) {{
    btn.addEventListener("click", function () {{ show(btn.parentNode.getAttribute("data-b"), btn.getAttribute("data-stage")); }});
  }});
  document.querySelectorAll(".tab").forEach(function (t) {{
    t.addEventListener("click", function () {{
      document.querySelectorAll(".tab").forEach(function (x) {{ x.setAttribute("aria-selected", x === t ? "true" : "false"); }});
      document.querySelectorAll(".brand-panel").forEach(function (p) {{ p.hidden = p.getAttribute("data-b") !== t.getAttribute("data-b"); }});
    }});
  }});
}})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------- Markdown mirror

def mirror():
    ds, status = data()
    _, vtext = designer()
    L = ["# Feedback Forms", "",
         f"_Mirror of the Feedback Forms page (runs/feedback-forms/_system/feedback-forms.html), generated by "
         f"`components/feedback-forms/docs/make_page.py` · updated {status.get('updated', '')}._", "",
         "One feedback form per brand, one set of questions per customer stage, sent by Klaviyo at the right moment. "
         "Every answer lands in Klaviyo as a \"Submitted Feedback\" event and is pulled into the language bank each "
         "morning — filed by stage, tagged by the part of the business it helps, searchable "
         "(`query_language.py --brand B --area website` / `--feedback-stage churned-refund`).", "",
         "**How one answer travels:** Klaviyo trigger → wait → email (one button) → the form on the brand's own site → "
         "\"Submitted Feedback\" event on the profile → `gather.py feedback` (daily 05:30) → language bank.", ""]
    for d in ds:
        st, qs, b = d["stages"], d["questions"], d["brand"]
        pr = (d["status"] or {}).get("pr")
        L += [f"## {qs['label']}", "",
              f"- Form: {st['form']['url']} — pull request: {pr or 'pending'}",
              f"- Klaviyo public id `{st['klaviyo']['public_id']}` · metric \"{st['klaviyo']['metric']}\"",
              f"- Install sheet for email_lead: `{B.install_path(b).relative_to(B.WORKSPACE).as_posix()}`",
              f"- Into the bank: {(d['status'] or {}).get('pull', '')}",
              f"- End-to-end: {(d['status'] or {}).get('e2e', '')}", "",
              "### Stage map", "",
              "| Stage | Trigger → filters | Wait | Questions | Files into | Status |", "|---|---|---|---|---|---|"]
        for s in st["stages"]:
            k = s["klaviyo"]
            filt = "; ".join((k.get("trigger_filters") or []) + (k.get("flow_filters") or []))
            L.append(f"| **{s['label']}** (`{s['stage']}`) | {trig(s)} — {filt} | {k['wait']} | {n_q(qs['stages'][s['stage']])} | "
                     f"{s['lane']} | {'BLOCKED — ' + s['blocked_by'] if s.get('status') == 'blocked' else 'ready for email_lead (Draft)'} |")
        c = d.get("cover") or {}
        if c:
            L += ["", "### Where the words came from", "",
                  f"Written from the language bank through the language layer — record: `{d.get('lp')}/queries.md`. "
                  "Every question, tap option and email cites the bank rows it came from (`language_used`).", "",
                  "| Stage | Rows queried | Questions citing | Taps citing | Email cites | Thin? |", "|---|---|---|---|---|---|"]
            for sid, x in c.items():
                L.append(f"| {sid} | {x['rows_queried']:,} | {x['questions_citing']} / {x['questions']} | {x['taps_citing']} / {x['taps']} | "
                         f"{'yes' if x.get('email_citing') else 'no'} | {x.get('language_note') or ''} |")
        L += ["", "### Questions, word for word", ""]
        for s in st["stages"]:
            q = qs["stages"][s["stage"]]
            em = q["email"]
            L += [f"#### {s['label']} — `{s['klaviyo']['flow_name']}`", "", f"**{q['title']}** — {q['intro']}", ""]
            if q.get("language_note"):
                L += [f"> **Thin in the bank:** {q['language_note']}", ""]
            for x in q["questions"]:
                extra = ""
                if x.get("options"):
                    extra = " — options: " + " · ".join(x["options"]) + (" · Other (types it)" if x.get("other") else "")
                if x["type"] == "scale":
                    extra = f" — score {x['min']}–{x['max']} ({x.get('low', '')} → {x.get('high', '')})"
                if x.get("show_if"):
                    c = x["show_if"]
                    extra += f" — only when `{c['q']}` is {'one of' if c.get('in') else 'anything but'} {', '.join(c.get('in') or c.get('not_in') or [])}"
                L.append(f"{x['n']}. **{x['text']}** _({TYPE_LABEL.get(x['type'], x['type'])})_{extra}  ")
                L.append(f"   areas: {', '.join(AREA_LABEL.get(a, a) for a in x.get('areas') or [])} · yields: {', '.join(x.get('yields') or [])}"
                         + (f" · from the old form: {x['from_old']}" if x.get("from_old") else "") + "  ")
                if x.get("was") and x["was"] != x["text"]:
                    L.append(f"   _Before:_ {x['was']} → _After:_ {x['text']}  ")
                if x.get("was_options") and x["was_options"] != x.get("options"):
                    L.append(f"   _Taps before:_ {' · '.join(x['was_options'])}  ")
                for rid in x.get("language_used") or []:
                    L.append(f"   - from the bank: {md_line(d, rid)}  ")
                for o in x.get("options_language") or []:
                    if o.get("theme"):
                        L.append(f"   - tap **{o['option']}** — {o['rows']} rows in this lane" + (f", loudest said {o['said']}×" if (o.get('said') or 0) > 1 else "")
                                 + ": " + " · ".join(md_line(d, i) for i in (o.get("language_used") or [])[:3]) + "  ")
                    else:
                        L.append(f"   - tap **{o['option']}** — {o.get('note') or 'cited by hand'}  ")
            link = st["form"]["link"].replace("{stage}", s["stage"])
            L += ["", f"Email — subject **{em['subject']}** · preview “{em['preview']}” · button **{em['button']}** → `{link}`", ""]
            L += [f"> {p}" for p in em["body"] + (em.get("after") or [])]
            L.append("")
            w = (q.get("was") or {}).get("email") or {}
            if w.get("subject") and w.get("subject") != em["subject"]:
                L.append(f"Subject before: {w['subject']}  ")
            if w.get("preview") and w.get("preview") != em["preview"]:
                L.append(f"Preview before: {w['preview']}  ")
            if em.get("from_old"):
                L.append(f"Kept from the old email: {em['from_old']}  ")
            for rid in em.get("language_used") or []:
                L.append(f"- email from the bank: {md_line(d, rid)}")
            L.append("")
        L += ["### Kill list — old Google Form surveys in Klaviyo (read-only)", ""]
        if d["kills"]:
            L += ["| Flow | Email | Today | Links to | Replaced by · what would be switched off |", "|---|---|---|---|---|"]
            for k in d["kills"]:
                L.append(f"| {k['flow_name']} (`{k['flow_id']}`, flow {k['flow_status']}) | {k['message_name']} (`{k['message_id']}`) "
                         f"| {'sending now' if k['state'] == 'live' else k['state']} | {k['form']} | {k.get('replaced_by') or '—'} — {k.get('switch_off') or ''} |")
        else:
            L.append("No kill list: reading this brand's Klaviyo flows needs its private key.")
        L.append("")
    L += ["## email_lead installs it in Klaviyo", "",
          "1. Review each brand's form pull request; merging publishes the page (nothing is emailed yet).",
          "2. Build every flow in **Draft** from the brand's install sheet (`runs/feedback-forms/<brand>/install/deliverable/feedback-klaviyo-install.md`).",
          "3. owner says go. Then the kill list says which old survey emails to switch off.", "",
          "## What was and wasn't touched", ""]
    L += [f"- {x}" for x in status.get("not_touched") or []]
    L += ["", "## What only designer can unlock (draft message — not sent)", "", "`runs/feedback-forms/_system/designer-draft.md`", ""]
    body = vtext.split("---", 2)[1].strip() if vtext.count("---") >= 2 else vtext
    L += [body, ""]
    return "\n".join(L)


def md_line(d, rid):
    r = (d.get("bank") or {}).get("rows", {}).get(rid)
    if not r:
        return f"`{rid}`"
    t = r["text"].replace("\n", " ")
    return f"“{t[:200]}{'…' if len(t) > 200 else ''}” ({'said ' + str(r['said']) + '×' if r['said'] > 1 else 'said once'}, `{rid.split('_', 3)[-1]}`)"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "feedback-forms.html").write_text(page())
    (OUT / "FEEDBACK-FORMS.md").write_text(mirror())
    print(f"wrote {OUT / 'feedback-forms.html'}\nwrote {OUT / 'FEEDBACK-FORMS.md'}")


if __name__ == "__main__":
    main()
