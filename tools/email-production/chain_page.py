#!/usr/bin/env python3
"""The Email Chain page — every station from the calendar to a Klaviyo draft,
every writing step with what it is handed, what it makes, which model runs it
and its prompt verbatim.

    python3 chain_page.py            # -> email-chain.html + EMAIL-CHAIN.md

the owner, 2026-09-19: "let's be very, very clear on the full email chain and
where we're at… what are the exact steps that we take? What prompts are we
using? What chain reactions are being created… We need to start tweaking each
of those knobs from there."

The step list, the models and the inputs are READ from email.py, and the
prompts from prompts/ — so the page cannot describe a chain the code does not
run. The plain-English lines and the knobs are written here, by hand, and are
the part to keep current.
"""
import html
import json
import re
import os
from pathlib import Path


def _workspace(start=__file__):
    """The workspace root, FOUND by walking up — never counted with parents[N].

    The count here was right only while this file sat in lab/. The move
    to components/ on 2026-09-22 made it resolve to ~/Projects, one level too
    high — outside the repo entirely. A marker cannot go quietly wrong the next
    time something moves. AI_WORKSPACE still wins when it names a workspace.
    """
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError(f"no workspace found upward of {here}")



HERE = Path(__file__).resolve().parent
WS = _workspace()

# ---------------------------------------------------------------- read code
src = (HERE / "email.py").read_text()
STAGES = re.findall(r'dict\(key="(\w+)", tier="(\w+)", id="(\w+)", name="([^"]+)"', src)
TIERS = dict(re.findall(r'"(reads|checks|designs)":\s*"([^"]+)"', src))
FEEDS = {m.group(1): re.findall(r"(\w+)=", m.group(2)) for m in re.finditer(
    r'run_stage\("(\w+)", out_dir, MODEL\("\w+"\), state,(.*?)\)(?:; save\(\))?\n', src, re.S)}


def prompt_for(key):
    best, bv = None, -1
    for f in (HERE / "prompts").glob(f"{key}-*.md"):
        m = re.search(r"-v(\d+)-", f.name)
        if m and int(m.group(1)) > bv:
            best, bv = f, int(m.group(1))
    return best


# ------------------------------------------------------- the words, by hand
PLAIN = {  # what each input is, in plain words
    "today": "today's date", "source": "the old email it is built on",
    "formats": "the brand's email formats", "source_reference": "why that email was picked",
    "avatars": "the avatar list", "segment": "who receives it",
    "awareness_levels": "the five awareness levels (doctrine)", "triage": "step 0's answers",
    "record": "step 1's record", "spec": "step 2's skeleton",
    "context_index": "an index of everything the brand knows",
    "always": "files every run loads", "always_loaded": "files every run loads",
    "occasion": "the moment it's tied to", "send_date": "the day it goes out",
    "market": "the market", "avatar": "the avatar's profile",
    "notable_customers": "named customers", "research": "the week's research file",
    "live_read": "step 2c's week", "offer_rule": "what it may sell",
    "brand_context": "step 2b's picks", "brand_name": "the brand's name",
    "sender_identity": "who it's from", "language_bank": "the avatar's voice rules",
    "product_file": "the product", "angle": "the calendar's argument",
    "reviewer_note": "the reviewer's note", "injection": "step 3's draft",
    "offer_file": "the offer bank", "objection_bank": "the objection bank",
    "placement": "step 4's plan", "customer_language": "real customer sentences",
    "hook_ledger": "subject lines already used", "subject_count": "how many subjects",
    "body": "the email so far", "close": "step 7's finished email",
    "subject_set": "step 5's subject lines", "blocks": "step 8's email",
    "techniques": "the seven techniques (doctrine)",
}
STEP = {  # what it does · what it makes · the knob · state
    "stage0": ("Reads the old email and decides five things: is it already an ad or an organic post, which format, who sends it, which avatar, how aware the reader is.",
               "five answers every later step obeys",
               "A wrong call here is inherited by all eleven steps after it.", "ok"),
    "stage1": ("Writes down exactly what the old email does — its parts, buttons, weight, voice. No opinions. Keeps three things apart: the message, the page furniture (logo row, nav, category links, social row, footer) and anything broken in the old email (a dropped letter, a dead merge tag).",
               "an objective record of the old email, in three parts",
               "New prompt (v2). Watch the first runs: is anything that was really message being filed as furniture?", "new"),
    "stage2": ("Strips the brand, the medium AND the subject out of the record, leaving only the persuasion skeleton.",
               "the skeleton the new email is built on",
               "This is the step that stops us 'rewriting the old email'. If emails still read like their source, tune this prompt. New prompt (v2): built from the message only — furniture never becomes a move, a broken line is never carried into our subject or preview. Every step after it no longer sees the furniture at all.", "new"),
    "stage1b": ("Looks through everything Brand B knows and picks only what this email needs.",
                "the brand files this email uses",
                "Brand B hands it 1.7MB, too big for Haiku, so it moves up to Opus every time. Trimming the input would put it back on Haiku.", "tune"),
    "stage1c": ("Turns the week's research into things the email can use: what's happening, and a way to invite the reader in.",
                "the week this email lands in",
                "BROKEN: the research files it reads are question lists written on Sep 10 for the OLD calendar's numbering. The Sep 23 email is being handed Sep 21's questions for a different audience, and no answers.", "broken"),
    "stage3": ("THE MAIN WRITING STEP. Writes our email into the skeleton, with the avatar's voice, the product and the calendar's argument.",
               "the first full draft",
               "Spice (tone, humour, pacing) and the awareness-level guidance aren't given to this step yet. They go here first.", "tune"),
    "stage4": ("Decides, writes nothing: where the product enters, how long it runs, how many buttons and pictures.",
               "the plan the writing steps must follow",
               "It still plans for the old designed layout (3 buttons, 4 pictures) that step 8 then throws away. Tell it the simple shape.", "tune"),
    "stage5": ("Writes the subject line and preview it's tested against, plus variations — checked against the awareness levels and every subject line already used.",
               "the subject + preview set",
               "The Brand A test came back with no preview text on the main subject line. Require one.", "tune"),
    "stage6": ("Only for organic sources: adds the selling structure a post never had.",
               "a commercially built body", "Skipped when the old email was already an ad.", "ok"),
    "stage7": ("Lands it: the objection at the moment of doubt, the ending, and a PS if it earns one.",
               "the finished email, end to end", "", "ok"),
    "stage8": ("Lays the finished email into the simple shape: headline, hero picture direction, copy, offer line, one button. Carries the words, never adds.",
               "the email as data, ready to build", "New today. Watch what it cuts.", "new"),
    "stage9": ("Writes a build brief for a person building the email by hand in Klaviyo.",
               "a brief nobody needs now",
               "The simple email builds itself, so this step is spare. Dropping it saves one call per email.", "tune"),
}
STATE = {"ok": ("Works", "ok"), "tune": ("Tune", "tune"), "broken": ("Broken", "bad"),
         "new": ("New today", "new"), "none": ("Not built", "none")}

LINE = [  # the whole line, station by station
    ("Brand record", "Before any month", "Check the brand can run, mine its old sends for moments, file them.",
     "Control Room: check-brand · mine-moments · file-moments", "ok"),
    ("The calendar", "Once a month", "Nine layers: holidays → moments → who's live → dates → concepts & arguments → email types → offers → affiliates → order. Two of them are AI.",
     "Control Room: plan-month", "ok"),
    ("Review", "Once a month", "The PM reads the month on the calendar page and rewrites or cuts sends. Those edits are kept separate, so a re-plan never wipes them.",
     "The calendar page, localhost:8788", "ok"),
    ("Hand-off", "Per send", "Turns each calendar send into the exact instruction the writing chain gets, and flags anything that would fail before money is spent.",
     "copy_plan.py (the check) · brief.py (the instruction)", "ok"),
    ("Writing", "Per send · ~12 min", "Twelve steps, below. Five on Opus, three on Sonnet, four on Haiku.",
     "tools/email-production/run_month.py — not in the Control Room yet", "tune"),
    ("Pictures & layout", "Per send · ~2 min", "GPT makes the hero and the offer picture; the email is laid out in Brand B's look.",
     "simple_email.py", "new"),
    ("Price check", "Per send", "Every price in the email must be one the offer bank sells today for that send's offer, or nothing goes to Klaviyo.",
     "simple_email.py — runs before every push", "new"),
    ("Klaviyo", "Per send", "A draft campaign, to the send's own segment, with the main subject line. Never sent by the machine — a person presses Schedule.",
     "simple_email.py --push", "new"),
    ("Scheduling", "Per send", "Each draft is set for its calendar day at 1pm in the recipient's own time zone — Brand B's best-earning hour across 209 of its own sends.",
     "brands/brand-b/email-sms/simple.json → send_time", "new"),
    ("Learnings", "After sends", "Klaviyo results joined to what each email was; next month's calendar plans from them.",
     "pull/learnings.py", "ok"),
]

WEEK = [  # Brand B, Sep 20–30 — from the rebuilt calendar; this pass writes avatar-one only
    ("Sun 20", "sep-05", "last-chance", "Lead", "Basics Set", "not this pass — gift-buyer email"),
    ("Mon 21", "sep-06", "content-request", "VIP Customer", "—", "to write"),
    ("Tue 22", "sep-07", "problem-explainer", "Lead", "—", "to write"),
    ("Wed 23", "sep-08", "bundle", "One-Time Customer", "The Daily Set", "written · HELD in Klaviyo — sold a size the store dropped"),
    ("Thu 24", "sep-09", "affiliate-feature", "Churned", "—", "can't write — no format on file"),
    ("Fri 25", "sep-10", "myth-correction", "Lead", "—", "not this pass — avatar-two email"),
    ("Sat 26", "sep-11", "guarantee", "One-Time Customer", "none — the type needs one", "to write"),
    ("Sun 27", "sep-12", "moment", "Lead", "—", "to write"),
    ("Mon 28", "sep-13", "subscription-invite", "Subscriber", "CORE™", "to write"),
    ("Tue 29", "sep-14", "what-went-wrong", "Churned", "—", "to write"),
    ("Wed 30", "sep-15", "guarantee", "Subscriber", "CORE™", "to write"),
]

KNOBS = [
    ("Fix the week's research", "Step 2c is reading stale question lists from the old calendar. Regenerate them for the rebuilt September, and actually answer them, before writing next week.", "broken"),
    ("Tell step 4 the simple shape", "It plans three buttons and four pictures that step 8 then cuts. One button, a hero and an optional offer picture, planned from the start.", "tune"),
    ("Put spice and awareness into step 3", "The tone dials from the marketing doctrine (humour, delivery, pacing, register) and the awareness guidance, bound into the main writing step, then 5 and 7.", "tune"),
    ("Require a preview line", "Step 5's main subject line can come back with no preview.", "tune"),
    ("Drop step 9", "A hand-build brief nothing reads any more. One fewer call per email.", "tune"),
    ("Product files list sizes that aren't for sale", "The Sep 23 email sold '2 x The Daily Set, $__' — a size the store removed. The product file lists every size ever made; the writer took it from there. The price check now stops it reaching Klaviyo; the product file should mark what's live.", "broken"),
    ("Writing in the Control Room", "Add 'write emails' next to plan-month, so a week of emails is one trigger.", "none"),
    ("The old email's nav and footer words", "FIXED in the prompts, to be proven on the next real run: the writer had copied the old email's navigation and footer words into our body, and a typo from its preview line into ours. Step 1 (v2) now files furniture and broken lines under their own headings; step 2 (v2) builds from the message only; later steps never see the furniture.", "new"),
    ("The dry run is free", "FIXED: the dry run used to run step 0 before it stopped, so every check spent a call and left a folder behind. It now stops before any step, reports what only step 0 can know as 'decided at triage', and writes nothing.", "ok"),
    ("One set of checks", "FIXED: the price check, the unfilled check and the check step's reader are the shared ones every chain uses. check.json now says which gate held the email (delivery) instead of blaming prices for everything.", "ok"),
    ("An email type nobody defined", "FIXED: a send whose type is not in the element library or the brand's own type list is blocked before a word is written, with the real types named.", "ok"),
]


# ---------------------------------------------------------------- render
def e(s):
    return html.escape(str(s))


def chip(state):
    label, cls = STATE[state]
    return f'<span class="chip {cls}">{label}</span>'


def page():
    stages = []
    for key, tier, sid, name in STAGES:
        does, makes, knob, st = STEP.get(key, ("", "", "", "ok"))
        pf = prompt_for(key)
        fed = ", ".join(PLAIN.get(f, f) for f in FEEDS.get(key, []) if f != "today")
        model = TIERS[tier].replace("claude-", "").split("-2025")[0]
        if key == "stage1b":
            model += " → opus for Brand B"
        prompt = pf.read_text() if pf else "(no prompt file)"
        stages.append(f"""
<article class="step {st}" id="{key}">
  <div class="sn">{e(sid)}</div>
  <div class="sb">
    <div class="sh"><h3>{e(name)}</h3>{chip(st)}<span class="model m-{tier}">{e(model)}</span></div>
    <p class="does">{e(does)}</p>
    <dl>
      <dt>Handed</dt><dd>{e(fed)}</dd>
      <dt>Makes</dt><dd>{e(makes)}</dd>
      {f'<dt>Knob</dt><dd class="knob">{e(knob)}</dd>' if knob else ''}
    </dl>
    <details><summary>The prompt · <code>{e(pf.name if pf else '')}</code> · {len(prompt.splitlines())} lines</summary>
      <pre>{e(prompt)}</pre></details>
  </div>
</article>""")

    line = "".join(f"""
<li class="st {s}"><div class="stt"><b>{e(n)}</b>{chip(s)}</div>
<div class="when">{e(w)}</div><p>{e(d)}</p><div class="how">{e(h)}</div></li>""" for n, w, d, h, s in LINE)
    week = "".join(f"<tr><td>{e(d)}</td><td><code>{e(i)}</code></td><td>{e(t)}</td><td>{e(g)}</td><td>{e(o)}</td><td>{e(s)}</td></tr>"
                   for d, i, t, g, o, s in WEEK)
    knobs = "".join(f'<li class="{s}"><div class="kt"><b>{e(t)}</b>{chip(s)}</div><p>{e(d)}</p></li>'
                    for t, d, s in KNOBS)
    return TEMPLATE.format(line=line, week=week, stages="".join(stages), knobs=knobs,
                           n=len(STAGES))


TEMPLATE = """<meta charset="utf-8">
<title>The Email Chain</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--ground:#F3F4F1;--card:#FFFFFF;--ink:#17191A;--mut:#5E655F;--line:#DADDD6;--hair:#E9EBE6;
--accent:#3A5A40;--accent-bg:#E3ECE4;--tune:#8A5C0F;--tune-bg:#F5EBD6;--bad:#A13A2C;--bad-bg:#F6E1DC;
--new:#2E5B87;--new-bg:#E0EAF4;--none:#6B706B;--none-bg:#E9EBE7}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--ground:#111412;--card:#191D1A;--ink:#E6E9E5;
--mut:#9AA29B;--line:#2A302B;--hair:#222723;--accent:#8DB596;--accent-bg:#1B2A1E;--tune:#D9A74E;--tune-bg:#2B2213;
--bad:#E08473;--bad-bg:#2E1814;--new:#8DB6DF;--new-bg:#16222F;--none:#9CA29C;--none-bg:#222723}}}}
:root[data-theme="dark"]{{--ground:#111412;--card:#191D1A;--ink:#E6E9E5;--mut:#9AA29B;--line:#2A302B;--hair:#222723;
--accent:#8DB596;--accent-bg:#1B2A1E;--tune:#D9A74E;--tune-bg:#2B2213;--bad:#E08473;--bad-bg:#2E1814;
--new:#8DB6DF;--new-bg:#16222F;--none:#9CA29C;--none-bg:#222723}}
*{{box-sizing:border-box}}
body{{background:var(--ground);color:var(--ink);font:16px/1.6 "IBM Plex Sans",system-ui,-apple-system,sans-serif;margin:0}}
.wrap{{max-width:900px;margin:0 auto;padding-inline:18px;padding-block:44px 80px}}
.eyebrow{{font:500 12px/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}}
h1,h2,h3{{font-family:Newsreader,Georgia,serif;font-weight:600;letter-spacing:-.01em;text-wrap:balance}}
h1{{font-size:clamp(34px,6vw,50px);line-height:1.05;margin:10px 0 12px}}
h2{{font-size:28px;margin:0 0 6px}}
h3{{font-size:20px;margin:0}}
.lede{{font-size:18px;color:var(--mut);max-width:62ch;margin:0}}
section{{margin-top:52px}}
.sub{{color:var(--mut);max-width:64ch;margin:0 0 18px}}
code{{font:13px "IBM Plex Mono",ui-monospace,monospace;background:var(--hair);padding:1px 5px;border-radius:3px}}
.chip{{font:500 10.5px/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;
padding:5px 7px;border-radius:3px;white-space:nowrap}}
.chip.ok{{color:var(--accent);background:var(--accent-bg)}} .chip.tune{{color:var(--tune);background:var(--tune-bg)}}
.chip.bad{{color:var(--bad);background:var(--bad-bg)}} .chip.new{{color:var(--new);background:var(--new-bg)}}
.chip.none{{color:var(--none);background:var(--none-bg)}}
/* the line */
.line{{list-style:none;margin:0;padding:0;display:grid;gap:0;border-left:2px solid var(--line);margin-left:6px}}
.st{{position:relative;padding:0 0 22px 22px}}
.st::before{{content:"";position:absolute;left:-7px;top:6px;width:12px;height:12px;border-radius:50%;
background:var(--card);border:2px solid var(--accent)}}
.st.tune::before{{border-color:var(--tune)}} .st.none::before{{border-color:var(--none);background:var(--ground)}}
.st.new::before{{border-color:var(--new)}} .st.broken::before{{border-color:var(--bad)}}
.stt{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}} .stt b{{font-size:17px}}
.when{{font:12px "IBM Plex Mono",ui-monospace,monospace;color:var(--mut);margin-top:2px}}
.st p{{margin:6px 0 4px;max-width:62ch}}
.how{{font:12.5px "IBM Plex Mono",ui-monospace,monospace;color:var(--mut)}}
/* week */
.tbl{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:6px}}
table{{border-collapse:collapse;width:100%;font-size:14.5px}}
th,td{{text-align:left;padding:10px 14px;border-bottom:1px solid var(--hair);white-space:nowrap}}
th{{font:500 11px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--mut)}}
tr:last-child td{{border-bottom:0}}
/* steps */
.steps{{display:grid;gap:12px}}
.step{{display:grid;grid-template-columns:52px 1fr;background:var(--card);border:1px solid var(--line);border-radius:6px}}
.step.broken{{border-color:var(--bad)}}
.sn{{font:500 15px "IBM Plex Mono",ui-monospace,monospace;color:var(--mut);padding:18px 0 0 16px}}
.sb{{padding:16px 18px 14px 0;min-width:0}}
.sh{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.model{{margin-left:auto;font:500 11.5px "IBM Plex Mono",ui-monospace,monospace;padding:4px 8px;border-radius:3px;border:1px solid var(--line);color:var(--mut)}}
.m-designs{{color:var(--ink);border-color:var(--ink)}}
.does{{margin:8px 0 10px;max-width:66ch}}
dl{{display:grid;grid-template-columns:78px 1fr;gap:6px 12px;margin:0 0 10px;font-size:14px}}
dt{{font:500 11px/1.9 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}}
dd{{margin:0;color:var(--mut)}} dd.knob{{color:var(--ink)}}
.step.broken dd.knob{{color:var(--bad)}}
details summary{{cursor:pointer;font-size:13.5px;color:var(--accent)}}
details pre{{margin:10px 0 0;max-height:360px;overflow:auto;background:var(--ground);border:1px solid var(--hair);
border-radius:4px;padding:14px;white-space:pre-wrap;word-wrap:break-word;font:12.5px/1.55 "IBM Plex Mono",ui-monospace,monospace;color:var(--ink)}}
/* knobs */
.knobs{{list-style:none;margin:0;padding:0;counter-reset:k;display:grid;gap:10px}}
.knobs li{{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:14px 18px 14px 52px;position:relative;counter-increment:k}}
.knobs li::before{{content:counter(k);position:absolute;left:18px;top:14px;font:500 15px "IBM Plex Mono",monospace;color:var(--mut)}}
.kt{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.knobs p{{margin:6px 0 0;color:var(--mut);max-width:64ch;font-size:15px}}
a{{color:var(--accent)}} :focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
footer{{margin-top:56px;padding-top:16px;border-top:1px solid var(--line);font:12.5px/1.8 "IBM Plex Mono",monospace;color:var(--mut)}}
@media(max-width:560px){{.step{{grid-template-columns:40px 1fr}}.sn{{padding-left:12px}}dl{{grid-template-columns:1fr}}.model{{margin-left:0}}}}
</style>
<div class="wrap">
<div class="eyebrow">Brand B · the email machine · 19 Sep 2026</div>
<h1>The Email Chain</h1>
<p class="lede">From the calendar to a draft sitting in Klaviyo: every station, how each one is triggered, the twelve writing steps with their prompts, and the knobs to turn — in order.</p>

<section>
<h2>The whole line</h2>
<p class="sub">Stage one is the planning — brand record through hand-off (components/marketing-calendar). Stage two is the writing and the pictures (tools/email-production). Then the price check, Klaviyo and the send time.</p>
<ol class="line">{line}</ol>
</section>

<section>
<h2>Next week, Brand B</h2>
<p class="sub">Every Brand B send on the rebuilt calendar, Sep 20–30. This pass writes the avatar-one ones — eight emails. Sep 23 was the test: written, pictured, drafted — and held for a wrong price.</p>
<div class="tbl"><table><thead><tr><th>Day</th><th>Send</th><th>Type</th><th>To (Core |)</th><th>Sells</th><th>Status</th></tr></thead>
<tbody>{week}</tbody></table></div>
</section>

<section>
<h2>The writing chain, step by step</h2>
<p class="sub">{n} steps, run in this order. Each one's output is handed to the steps after it — "Handed" is exactly what it receives. Open any prompt to read it word for word.</p>
<div class="steps">{stages}</div>
</section>

<section>
<h2>Knobs, in the order to turn them</h2>
<p class="sub">What to change before next week's emails go out, most urgent first.</p>
<ol class="knobs">{knobs}</ol>
</section>

<footer>
Code: tools/email-production — email.py (the twelve steps) · simple_email.py (pictures, layout, Klaviyo) · run_month.py (a whole month) · prompts/<br>
Look: brands/brand-b/email-sms/simple.json · Runs: runs/email-production/brand-b/ · Pictures: Shared Assets/runs/email-production/brand-b/<br>
This page: python3 chain_page.py — steps, models, inputs and prompts are read from the code.
</footer>
</div>
"""


def mirror():
    L = ["# The Email Chain", "",
         "Generated by `chain_page.py` — the page is `email-chain.html`.", "",
         "## The whole line", ""]
    L += [f"- **{n}** ({w}) — {d} *Triggered by:* {h}. **{STATE[s][0]}**" for n, w, d, h, s in LINE]
    L += ["", "## The writing chain", ""]
    for key, tier, sid, name in STAGES:
        does, makes, knob, st = STEP.get(key, ("", "", "", "ok"))
        pf = prompt_for(key)
        L.append(f"- **{sid} {name}** · {TIERS[tier]} · `{pf.name if pf else ''}` — {does}"
                 + (f" *Knob:* {knob}" if knob else ""))
    L += ["", "## Knobs, in order", ""]
    L += [f"{i}. **{t}** — {d}" for i, (t, d, s) in enumerate(KNOBS, 1)]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    (HERE / "email-chain.html").write_text(page())
    (HERE / "EMAIL-CHAIN.md").write_text(mirror())
    print(f"-> {HERE / 'email-chain.html'}  ({len(STAGES)} steps)")
