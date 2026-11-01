#!/usr/bin/env python3
"""The review page — every email produced for a month, on one local page,
so the month can be read before anything goes near Klaviyo (the owner,
2026-09-02: "show me the emails in a local page so we can review; do not
send to Klaviyo right away").

    python3 build_review.py results/calendar-2026-09
        # -> runs/email-production/<brand>/review-2026-09/review-2026-09.html

One card per send, in calendar order: date, who it goes to, why it exists,
every subject line the chain wrote (none ranked — choosing is the owner's), and
the rendered email itself in the brand's skin. A send with several avatar
variants shows each variant side by side. A send not yet produced says so.
Written under runs/email-production/<brand>/review-<month>/ (email-production#19),
beside the chain runs it links to; generated, so ignored there.
"""
import html
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brief  # noqa: E402
from paths import run_home  # noqa: E402


def e(s):
    return html.escape(str(s if s is not None else ""))


def subjects(run_dir):
    f = run_dir / "stage5--subjects.md"
    if not f.is_file():
        return []
    txt = f.read_text()
    pairs = re.findall(r"\*\*Subject:?\*\*:?\s*(.+?)\n\s*-?\s*\*\*Preview(?: text)?:?\*\*:?\s*(.+?)(?:\n|$)",
                       txt, re.I)
    if not pairs:
        pairs = re.findall(r"Subject:\s*(.+?)\n\s*Preview:\s*(.+?)(?:\n|$)", txt, re.I)
    return [(s.strip().strip("“”\"*"), p.strip().strip("“”\"*")) for s, p in pairs]


def status(run_dir):
    r = run_dir / "run.json"
    if not r.is_file():
        return "not produced", 0
    st = json.loads(r.read_text()).get("stages", {})
    done = sum(1 for v in st.values() if v.get("status") == "done")
    if (run_dir / "email-final.html").is_file():
        return "rendered", done
    if (run_dir / "stage8--blocks.md").is_file():
        return "built, not rendered", done
    return f"running — stage {done}", done


def chain_run(brand, label, root=None):
    """email.py's home first; pre-move results/ read as history."""
    new = run_home(brand, label, root)
    return new if new.is_dir() or not (HERE / "results" / label).is_dir() else HERE / "results" / label


def variant_card(label, av, angle, brand, page_dir, root=None):
    d = chain_run(brand, label, root)
    href = e(os.path.relpath(d, Path(page_dir).resolve()).replace(os.sep, "/"))   # relative to the page
    stt, done = status(d)
    subs = subjects(d)
    who = av if av and av not in ("none", "mixed") else "everyone"
    body = [f'<div class="vh"><b>{e(who)}</b><span class="st s-{stt.split()[0]}">{e(stt)}</span></div>']
    if angle:
        body.append(f'<p class="angle">{e(angle)}</p>')
    if subs:
        body.append('<div class="subs"><div class="k">Subject lines — all ship, none ranked</div>'
                    + "".join(f'<div class="sub"><b>{e(s)}</b><i>{e(p)}</i></div>' for s, p in subs)
                    + "</div>")
    if (d / "email-final.html").is_file():
        body.append(f'<iframe class="mail" src="{href}/email-final.html" loading="lazy"></iframe>')
        fig = d / "figma-brief.json"
        figl = ""
        if fig.is_file():
            fj = json.loads(fig.read_text())
            figl = f' · <a href="{e(fj.get("url") or "#")}" target="_blank"><b>the brief in Figma</b></a>' if fj.get("url") else ""
        elif (d / "figma-brief.js").is_file():
            figl = " · Figma brief ready to push"
        body.append(f'<p class="k"><a href="{href}/email-final.html" target="_blank">open the email on its own</a>'
                    f' · <a href="{href}/stage9--brief.md" target="_blank">the brief</a>'
                    f' · <a href="{href}/" target="_blank">every stage</a>{figl}</p>')
    elif stt == "not produced":
        body.append('<p class="k">Not produced yet.</p>')
    return f'<div class="var">{"".join(body)}</div>'


def build(run_dir):
    slots = json.loads((run_dir / "slots.json").read_text())
    run = json.loads((run_dir / "run.json").read_text())
    brand, month = run["brand"], run["month"]
    page_dir = run_home(brand, f"review-{month}")   # email-production#19
    cards, n_done, n_total = [], 0, 0
    for s in sorted(slots, key=lambda x: (x["date"], x["id"])):
        d = date.fromisoformat(s["date"])
        segs = s.get("segments") or [s["segment"]]
        vars_ = brief.variant_runs(s, brand)
        vcards = []
        for av, angle, label in vars_:
            n_total += 1
            if (chain_run(brand, label) / "email-final.html").is_file():
                n_done += 1
            vcards.append(variant_card(label, av, angle, brand, page_dir))
        links = []
        if s.get("follows"):
            links.append(f"follows {s['follows']}")
        if s.get("then"):
            links.append(f"then {s['then']}")
        cards.append(f'''<section class="send" id="{e(s["id"])}">
<div class="sh">
 <span class="d"><b>{d.day}</b><i>{d:%a}</i></span>
 <div class="meta">
  <div class="t"><code>{e(s["id"])}</code> <b>{e(s["type"])}</b> <em class="cat">{e(s["category"])}</em>
   {'<em class="anc">anchored</em>' if s.get("anchored") else ''}</div>
  <div class="occ">{e(s.get("occasion"))}</div>
  <div class="to">To: {e(" · ".join(x.replace("Core | ", "") for x in segs))}
   {f' · offer <code>{e(s["offer"])}</code>' if s.get("offer") not in (None, "none") else ''}
   {f' · product <code>{e(s["product"])}</code>' if s.get("product") not in (None, "none") else ''}
   {(' · ' + ' · '.join(links)) if links else ''}</div>
 </div>
</div>
<details class="why"><summary>Why this send exists</summary><p>{e(s.get("why"))}</p></details>
<div class="vars n{len(vcards)}">{"".join(vcards)}</div>
</section>''')
    doc = f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review — {e(brand)} {e(month)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,640&family=Instrument+Sans:wght@400;500;600&family=Spline+Sans+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#F1F0EA;--card:#fff;--ink:#191B1D;--mut:#676C73;--line:#DBD9D2;--acc:#2E5D50;--acc-bg:#DFEBE6;--warn:#8A5A10}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0E1012;--card:#16191C;--ink:#E6E8EA;--mut:#8E959D;--line:#272B30;--acc:#74B4A2;--acc-bg:#12251F}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "Instrument Sans",system-ui,sans-serif}}
.wrap{{max-width:1400px;margin:0 auto;padding:28px 24px 80px}}
h1{{font:640 34px/1.1 Fraunces,Georgia,serif;margin:0 0 6px}} .lede{{color:var(--mut);margin:0 0 26px}}
.send{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:0 0 16px}}
.sh{{display:flex;gap:14px;align-items:flex-start}}
.d{{display:flex;flex-direction:column;align-items:center;min-width:44px;font-family:Fraunces,serif}} .d b{{font-size:26px;line-height:1}} .d i{{font-style:normal;font-size:11px;color:var(--mut);text-transform:uppercase}}
.t b{{font-size:17px}} .t code,.to code{{font:500 12px "Spline Sans Mono",monospace;background:var(--acc-bg);color:var(--acc);padding:1px 6px;border-radius:5px}}
em.cat,em.anc{{font-style:normal;font-size:11px;padding:2px 8px;border-radius:99px;border:1px solid var(--line);margin-left:6px}} em.anc{{background:var(--acc-bg);color:var(--acc);border-color:var(--acc)}}
.occ{{font-weight:600;margin-top:2px}} .to{{color:var(--mut);font-size:13.5px}}
details.why{{margin:10px 0 6px;font-size:13.5px;color:var(--mut)}} details.why summary{{cursor:pointer;color:var(--acc)}}
.vars{{display:grid;gap:14px;margin-top:12px}} .vars.n2{{grid-template-columns:1fr 1fr}} .vars.n3{{grid-template-columns:repeat(3,1fr)}}
@media (max-width:1000px){{.vars.n2,.vars.n3{{grid-template-columns:1fr}}}}
.var{{border:1px solid var(--line);border-radius:10px;padding:12px;background:var(--bg)}}
.vh{{display:flex;justify-content:space-between;align-items:center}} .vh b{{font-size:14px}}
.st{{font-size:11px;padding:2px 8px;border-radius:99px;border:1px solid var(--line);color:var(--mut)}} .s-rendered{{color:var(--acc);border-color:var(--acc)}} .s-running{{color:var(--warn);border-color:var(--warn)}}
.angle{{font-size:13px;color:var(--mut);margin:6px 0 8px}}
.subs .k,.k{{font-size:12px;color:var(--mut);margin:6px 0 4px}} .sub{{padding:5px 0;border-top:1px dashed var(--line)}} .sub b{{display:block;font-size:14px}} .sub i{{font-style:normal;font-size:12.5px;color:var(--mut)}}
iframe.mail{{width:100%;height:760px;border:1px solid var(--line);border-radius:8px;background:#fff;margin-top:10px}}
a{{color:var(--acc)}}
.prog{{display:inline-block;padding:4px 12px;border-radius:99px;background:var(--acc-bg);color:var(--acc);font-weight:600;font-size:13px}}
</style>
<div class="wrap">
<h1>{e(brand.upper())} — {date.fromisoformat(month + "-01"):%B %Y}, for review</h1>
<p class="lede"><span class="prog">{n_done} of {n_total} emails rendered</span> &nbsp; {len(slots)} sends on the calendar.
Every subject line the machine wrote is here, none ranked — choosing is yours. Nothing on this page has been sent to Klaviyo.</p>
{"".join(cards)}
</div>'''
    page_dir.mkdir(parents=True, exist_ok=True)
    out = page_dir / f"review-{month}.html"
    out.write_text(doc)
    print(f"{out}  ({n_done}/{n_total} rendered)")


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results/calendar-2026-09"
    build(d if d.is_absolute() else HERE / d)
