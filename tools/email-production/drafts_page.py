#!/usr/bin/env python3
"""python3 drafts_page.py <calendar run> — every finished draft on one page, to read.

The words only. A picture is a DIRECTION at this stage, not an image: it is shown
as the direction it will be made from, so a wrong one is caught before it is paid for.
Writes drafts.html + DRAFTS.md under runs/email-production/<brand>/drafts-<calendar run>/."""
import base64, io, json, sys, html, datetime, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.append(str(HERE))
from paths import WORKSPACE, run_home                            # noqa: E402

run = pathlib.Path(sys.argv[1]).resolve()
slots = {s["id"]: s for s in json.loads((run / "slots.json").read_text())}
brand = json.loads((run / "run.json").read_text())["brand"]
RUNS = WORKSPACE / "runs" / "email-production" / brand

PLAIN = {"founder-note": "A note from you", "content-request": "Asking them for their story",
         "problem-explainer": "Explaining the problem", "bundle": "The set, not the one bottle",
         "myth-correction": "Correcting what they believe", "guarantee": "The guarantee",
         "moment": "Something happening this week", "subscription-invite": "Put it on standing order",
         "what-went-wrong": "What went wrong, and what changed",
         "affiliate-feature": "A partner's product, not ours"}

def slot_of(label):
    """Exact match only. An older run under a longer label (`sep-08--avatar-one`
    beside today's `sep-08`) is history, not a second draft of the same send."""
    return slots.get(label) or {}

found = []
for d in sorted(RUNS.glob("*/deliverable/email.json")):
    label = d.parent.parent.name
    if label.endswith("--before") or label.startswith("_"):
        continue
    s = slot_of(label)
    if not s or s.get("status") in ("past", "dropped"):
        continue
    found.append((s, label, json.loads(d.read_text()), d.parent))
found.sort(key=lambda x: x[0]["date"])

CSS = """
:root{--ground:#F4F2EE;--card:#fff;--ink:#17191C;--mut:#5E6469;--line:#DCD8D1;--hair:#ECE8E2;
--ok:#1D6B45;--ok-bg:#E0EFE6;--warn:#8A5A16;--warn-bg:#F7EBD8;--accent:#1F4E46;--pic:#4A4E7A;--pic-bg:#E7E7F4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ground:#101211;--card:#191C1C;--ink:#E7E9E7;
--mut:#9AA2A2;--line:#2A2F2E;--hair:#202525;--ok:#79C99A;--ok-bg:#142A1D;--warn:#E0B978;--warn-bg:#2C2312;
--accent:#8ACBBC;--pic:#A9ACE0;--pic-bg:#1C1D30}}
:root[data-theme="dark"]{--ground:#101211;--card:#191C1C;--ink:#E7E9E7;--mut:#9AA2A2;--line:#2A2F2E;--hair:#202525;
--ok:#79C99A;--ok-bg:#142A1D;--warn:#E0B978;--warn-bg:#2C2312;--accent:#8ACBBC;--pic:#A9ACE0;--pic-bg:#1C1D30}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font:16px/1.6 ui-sans-serif,system-ui,-apple-system,sans-serif}
.wrap{max-width:820px;margin:0 auto;padding-inline:16px;padding-block:36px 72px}
.eyebrow{font:600 11px/1 ui-monospace,monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--mut)}
h1{font-size:clamp(30px,6vw,46px);line-height:1.02;letter-spacing:-.02em;margin:10px 0 10px}
.lede{color:var(--mut);max-width:62ch;margin:0 0 24px;font-size:17px}
nav{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 30px}
nav a{font-size:13px;color:var(--accent);text-decoration:none;border:1px solid var(--line);
border-radius:99px;padding:4px 11px;background:var(--card)}
.mail{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 22px;margin:0 0 20px}
.hdr{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;border-bottom:1px solid var(--hair);
padding-bottom:12px;margin-bottom:14px}
.hdr b{font-size:19px;letter-spacing:-.01em}
.hdr .d{font:600 13px ui-monospace,monospace;color:var(--accent)}
.hdr .to{font-size:13px;color:var(--mut);flex-basis:100%}
.lab{font:600 11px ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);margin:16px 0 6px}
.subj{border:1px solid var(--hair);border-radius:8px;overflow:hidden}
.subj div{padding:8px 12px;border-bottom:1px solid var(--hair);font-size:15px}
.subj div:last-child{border-bottom:0}
.subj div:first-child{background:var(--ok-bg)}
.subj b{display:block}.subj span{color:var(--mut);font-size:13px}
.body{font-size:17px;line-height:1.65;border-left:3px solid var(--line);padding-left:16px}
.body p{margin:0 0 12px}
.hl{font-size:22px;font-weight:700;letter-spacing:-.01em;margin:0 0 12px}
.pic{background:var(--pic-bg);border-radius:8px;padding:11px 14px;margin:10px 0;font-size:14px;color:var(--ink)}
.pic b{display:block;font:600 11px ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--pic);margin-bottom:4px}
.btn{display:inline-block;background:var(--ink);color:var(--ground);border-radius:8px;padding:10px 18px;
font-weight:600;font-size:15px;margin:6px 0 4px}
.link{font-size:13px;color:var(--mut);word-break:break-all}
.offer{background:var(--warn-bg);border-radius:8px;padding:11px 14px;font-size:15px;margin:10px 0}
figure{margin:12px 0}
figure img{width:100%;height:auto;display:block;border-radius:10px;border:1px solid var(--line)}
figcaption{font:400 12px ui-monospace,monospace;color:var(--mut);margin-top:6px}
figcaption b{color:var(--ink);font-weight:600}
.chk{font-size:14px;margin-top:14px;padding-top:12px;border-top:1px solid var(--hair)}
.chk.pass{color:var(--ok)} .chk.held{color:var(--warn)}
.chk.held b{display:block;margin-top:6px;font-weight:600}
.tally{background:var(--warn-bg);border-radius:10px;padding:12px 16px;margin:0 0 24px;font-size:15px;max-width:66ch}
.tally b{color:var(--warn)}
footer{margin-top:44px;border-top:1px solid var(--line);padding-top:14px;font:12px/1.7 ui-monospace,monospace;color:var(--mut)}
"""

def picture(run_dir, kind):
    """The made picture, shrunk for the page. A picture is 2MB on disk and the
    page carries nine of them, so it is embedded at web size, not full size."""
    made = sorted((run_dir / "media" / "generated").glob(f"*{kind}*.png")) \
        if (run_dir / "media" / "generated").is_dir() else []
    if not made:
        return None, None
    try:
        from PIL import Image
        im = Image.open(made[0]).convert("RGB")
        im.thumbnail((820, 820))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=78, optimize=True)
        return ("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
                made[0].name)
    except Exception:
        return None, made[0].name


def held_pictures(run_dir):
    f = run_dir / "media" / "check.json"
    if not f.is_file():
        return []
    try:
        return ((json.loads(f.read_text()).get("media") or {}).get("problems") or [])
    except ValueError:
        return []


def para(body):
    if isinstance(body, str):
        body = [b for b in body.split("\n\n")]
    return "".join(f"<p>{html.escape(str(b))}</p>" for b in body if str(b).strip())

def shot(run_dir, kind, direction, title):
    """The picture if it has been made, the direction it would be made from if not."""
    src, name = picture(run_dir, kind)
    if src:
        return (f'<figure><img src="{src}" alt="{html.escape(direction[:120])}">'
                f'<figcaption><b>{title}</b> — {html.escape(name)}</figcaption></figure>')
    return f'<div class="pic"><b>{title} — not made yet</b>{html.escape(direction)}</div>'


held_n = 0
cards, nav, md = [], [], [f"# The drafts — {brand}, rest of September 2026\n"]
for s, label, e, deliv in found:
    anchor = label.replace("--", "-")
    nav.append(f'<a href="#{anchor}">{datetime.date.fromisoformat(s["date"]).strftime("%-d %b")}</a>')
    subs = e.get("subjects") or []
    subj = "".join(f'<div><b>{html.escape(x.get("subject",""))}</b>'
                   f'<span>{html.escape(x.get("preview",""))}</span></div>' for x in subs)
    hero = e.get("hero") or {}
    off = e.get("offer") or {}
    btn = e.get("button") or {}
    chk = deliv / "check.json"
    if chk.is_file():
        st = json.loads(chk.read_text()).get("delivery", {})
        bad = st.get("problems") or []
        held_n += 1 if bad else 0
        chkhtml = (('<div class="chk held">held — the check found ' + str(len(bad)) + ' thing(s):'
                    + "".join(f"<b>{html.escape(x)}</b>" for x in bad) + '</div>') if bad
                   else '<div class="chk pass">checked — prices, product facts, no holes</div>')
    else:
        chkhtml = '<div class="chk">not checked yet — the pictures step runs the check</div>'
    offhtml = (f'<div class="offer">{html.escape(off.get("line",""))}</div>' if off.get("line") else "")
    if (off.get("image") or {}).get("prompt"):
        offhtml += shot(deliv.parent, "offer", off["image"]["prompt"], "the offer picture")
    cards.append(f"""<section class="mail" id="{anchor}">
<div class="hdr"><span class="d">{html.escape(datetime.date.fromisoformat(s['date']).strftime('%a %-d %b'))}</span>
<b>{html.escape(PLAIN.get(s['type'], s['type']))}</b>
<span class="to">to {html.escape(', '.join(s['segments']))}</span></div>
<div class="lab">subject lines — the first one is the one it sends with</div><div class="subj">{subj}</div>
<div class="lab">the email</div>
<div class="hl">{html.escape(e.get('headline',''))}</div>
{shot(deliv.parent, "hero", hero.get("prompt", ""), "picture at the top")}
<div class="body">{para(e.get('body') or [])}</div>
{offhtml}
<div class="btn">{html.escape(btn.get('label','') or 'button')}</div>
<div class="link">{html.escape(btn.get('link',''))}</div>
{chkhtml}</section>""")
    md.append(f"\n## {s['date']} — {PLAIN.get(s['type'], s['type'])} → {', '.join(s['segments'])}\n")
    md.append(f"**{subs[0]['subject'] if subs else ''}** — {subs[0].get('preview','') if subs else ''}\n")
    md.append(f"### {e.get('headline','')}\n")
    md.append("\n".join(str(b) for b in (e.get("body") or [])) if not isinstance(e.get("body"), str)
              else e["body"])

page = f"""<meta charset="utf-8">
<title>The Drafts</title>
<style>{CSS}</style>
<div class="wrap">
<div class="eyebrow">{html.escape(brand)} · written by the chain, not typed · {datetime.date.today()}</div>
<h1>The drafts</h1>
<p class="lede">{len(found)} emails, as they would read, with the picture each one sends with. A picture
still to be made shows the direction it would be made from instead, so a wrong one is caught before it
is paid for.</p>
<p class="tally">{held_n} of {len(found)} are <b>held</b> — the check found something in them and none of them
can reach Klaviyo until it is settled. Each one says what, at the bottom of its card.</p>
<nav>{''.join(nav)}</nav>
{''.join(cards)}
<footer>rebuilt by tools/email-production/drafts_page.py · mirror DRAFTS.md</footer>
</div>"""
page_dir = run_home(brand, f"drafts-{run.name}")      # email-production#19: out of the code folder
page_dir.mkdir(parents=True, exist_ok=True)
(page_dir / "drafts.html").write_text(page)
(page_dir / "DRAFTS.md").write_text("\n".join(md) + "\n")
print(f"{len(found)} drafts -> {page_dir / 'drafts.html'}")
