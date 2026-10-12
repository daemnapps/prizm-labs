#!/usr/bin/env python3
"""python3 send_plan.py <calendar run> [--brand brand-b] — the month's sends, as a page
the owner approves. Reads the calendar's own slots.json and copy_plan's flags; invents nothing.
Writes send-plan.html + SEND-PLAN.md beside this file."""
import json, sys, html, datetime, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.append(str(HERE))
import copy_plan as C                                            # noqa: E402

run = pathlib.Path(sys.argv[1]).resolve()
slots = json.loads((run / "slots.json").read_text())
brand = json.loads((run / "run.json").read_text())["brand"]

flags = {}
for part in C.resolve(run):
    if isinstance(part, list):
        for row in part:
            if isinstance(row, dict) and row.get("label"):
                flags.setdefault(row["slot"], []).extend(row.get("flags") or [])

live = [s for s in slots if s.get("status") not in ("past", "dropped")]
live.sort(key=lambda s: (s["date"], s["id"]))
held = [s for s in slots if s.get("status") in ("past", "dropped")]

def day(d):
    return datetime.date.fromisoformat(d).strftime("%a %-d %b")

def ang(s):
    return (s.get("variants") or [{}])[0].get("angle") or s.get("about") or ""

# What each kind of email IS, in words he uses. A type with no entry keeps its own name.
PLAIN = {"founder-note": "A note from you",
         "content-request": "Asking them for their story",
         "problem-explainer": "Explaining the problem",
         "bundle": "The set, not the one bottle",
         "myth-correction": "Correcting what they believe",
         "guarantee": "The guarantee",
         "moment": "Something happening this week",
         "subscription-invite": "Put it on standing order",
         "what-went-wrong": "What went wrong, and what changed",
         "affiliate-feature": "A partner's product, not ours"}

# The checks speak to the machine. This is the same thing said to a person.
def plainly(word, slot):
    if "no live read" in word:
        return ("no market read for that week — it is news about us, so it does not need one"
                if slot["type"] == "founder-note" else "no market read for that week")
    if "no angle" in word:
        return "nothing to say yet — it needs an angle"
    if "no avatar" in word:
        return "no reader named, so there is no language to write from"
    if "no occasion" in word:
        return "nothing anchors it to this month"
    return word

CSS = """
:root{--ground:#F4F2EE;--card:#fff;--ink:#17191C;--mut:#5E6469;--line:#DCD8D1;--hair:#ECE8E2;
--ok:#1D6B45;--ok-bg:#E0EFE6;--warn:#8A5A16;--warn-bg:#F7EBD8;--ask:#7A2E2A;--ask-bg:#F7E2DE;--accent:#1F4E46}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ground:#101211;--card:#191C1C;--ink:#E7E9E7;
--mut:#9AA2A2;--line:#2A2F2E;--hair:#202525;--ok:#79C99A;--ok-bg:#142A1D;--warn:#E0B978;--warn-bg:#2C2312;
--ask:#E89388;--ask-bg:#2E1815;--accent:#8ACBBC}}
:root[data-theme="dark"]{--ground:#101211;--card:#191C1C;--ink:#E7E9E7;--mut:#9AA2A2;--line:#2A2F2E;--hair:#202525;
--ok:#79C99A;--ok-bg:#142A1D;--warn:#E0B978;--warn-bg:#2C2312;--ask:#E89388;--ask-bg:#2E1815;--accent:#8ACBBC}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font:16px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:900px;margin:0 auto;padding-inline:16px;padding-block:36px 72px}
.eyebrow{font:600 11px/1 ui-monospace,monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--mut)}
h1{font-size:clamp(30px,6vw,46px);line-height:1.02;letter-spacing:-.02em;margin:10px 0 10px;text-wrap:balance}
.lede{color:var(--mut);max-width:62ch;margin:0 0 26px;font-size:17px}
h2{font-size:21px;letter-spacing:-.01em;margin:36px 0 12px}
.row{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 10px;
display:grid;grid-template-columns:96px 1fr;gap:4px 16px}
.row .when{font:600 13px ui-monospace,monospace;color:var(--accent);padding-top:3px}
.row .when b{display:block;font-size:19px;color:var(--ink);letter-spacing:-.01em}
.row h3{margin:0 0 4px;font-size:17px;letter-spacing:-.01em}
.row p{margin:0 0 8px;color:var(--ink)}
.meta{font-size:13px;color:var(--mut)}
.meta b{color:var(--ink);font-weight:600}
.why{margin-top:5px;font-size:12.5px;opacity:.8}
.tag{display:inline-block;font:600 12px ui-sans-serif,system-ui,sans-serif;
padding:3px 8px;border-radius:99px;margin:0 6px 4px 0}
.t-ok{background:var(--ok-bg);color:var(--ok)} .t-warn{background:var(--warn-bg);color:var(--warn)}
.t-ask{background:var(--ask-bg);color:var(--ask)}
.first{border-color:var(--accent);border-width:2px}
.ask{background:var(--ask-bg);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 10px}
.ask h3{margin:0 0 6px;font-size:16px}.ask p{margin:0;font-size:15px}
.held{font-size:14px;color:var(--mut);margin:2px 0}
.trig{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:6px 16px;margin:0}
.trig div{display:grid;grid-template-columns:120px 1fr;gap:16px;padding:9px 0;border-bottom:1px solid var(--hair);font-size:15px}
.trig div:last-child{border-bottom:0}
.trig code{font:600 14px ui-monospace,monospace;color:var(--accent)}
footer{margin-top:44px;border-top:1px solid var(--line);padding-top:14px;font:12px/1.7 ui-monospace,monospace;color:var(--mut)}
@media(max-width:560px){.row,.trig div{grid-template-columns:1fr}.row .when b{display:inline;margin-right:8px}}
"""

rows, md = [], [f"# The send plan — {brand}, rest of September 2026\n"]
for i, s in enumerate(live):
    f = flags.get(s["id"]) or []
    tags = "".join(f'<span class="tag t-warn">{html.escape(plainly(w, s))}</span>'
                   for _, w in f) or '<span class="tag t-ok">ready</span>'
    segs = ", ".join(s["segments"])
    sells = s.get("product") if s.get("product") not in (None, "none") else (
        s.get("offer") if s.get("offer") not in (None, "none") else None)
    rows.append(f"""<div class="row{' first' if i == 0 else ''}">
<div class="when"><b>{html.escape(day(s['date']))}</b>{html.escape(s['type'])}</div>
<div><h3>{html.escape(PLAIN.get(s['type'], s['type']))}</h3>
<p>{html.escape(ang(s))}</p>
<div class="meta"><b>to</b> {html.escape(segs)} · <b>as</b> {html.escape(s.get('avatar') or '—')} ·
<b>sells</b> {html.escape(sells or 'nothing')}</div>
<div class="meta why">why this one — {html.escape(s.get('occasion') or '')}</div>
<div style="margin-top:8px">{tags}</div></div></div>""")
    md.append(f"- **{day(s['date'])} · {PLAIN.get(s['type'], s['type'])}** (`{s['type']}`) → {segs} — {ang(s)[:150]}")

# The month's open questions for the person who rules the plan: [(question, the detail), ...].
# Written per month from that month's calendar — a record, so empty here.
ASKS = []
asks = "".join(f'<div class="ask"><h3>{html.escape(t)}</h3><p>{html.escape(b)}</p></div>' for t, b in ASKS)

TRIGGERS = [("calendar", "show me this plan again, current"),
            ("write", "write the drafts for the plan, show me them"),
            ("write &lt;date&gt;", "just that one, e.g. write tue"),
            ("images", "make the pictures for the drafts you approved"),
            ("push", "put the approved emails into Klaviyo as drafts — never sends"),
            ("hold &lt;date&gt;", "pull that send out of the month"),
            ("swap &lt;date&gt; &lt;type&gt;", "change what that send is"),
            ("again", "rewrite the last thing, with what I just told you")]
trig = "".join(f'<div><code>{c}</code><span>{html.escape(w)}</span></div>' for c, w in TRIGGERS)

heldhtml = "".join(f'<p class="held">· <b>{html.escape(s["id"])}</b> {html.escape(s["type"])} — '
                   f'{html.escape(s.get("note") or "")}</p>' for s in held)

page = f"""<meta charset="utf-8">
<title>The Send Plan</title>
<style>{CSS}</style>
<div class="wrap">
<div class="eyebrow">{html.escape(brand)} · built from the calendar, not typed · {datetime.date.today()}</div>
<h1>The send plan</h1>
<p class="lede">{len(live)} emails, {live[0]['date'][-5:].replace('-', '/')} to
{live[-1]['date'][-5:].replace('-', '/')}. Read them, tell me what to change, and I write the drafts.
Nothing goes near Klaviyo until you have read the words and the pictures.</p>
<h2>Your calls</h2>{asks}
<h2>The month</h2>{''.join(rows)}
<h2>Out of the month</h2>{heldhtml}
<h2>Say one word</h2><div class="trig">{trig}</div>
<footer>rebuilt by tools/email-production/send_plan.py from {html.escape(run.name)}/slots.json · mirror SEND-PLAN.md</footer>
</div>"""

(HERE / "send-plan.html").write_text(page)
(HERE / "SEND-PLAN.md").write_text("\n".join(md) + "\n")
print(f"{len(live)} sends -> send-plan.html")
