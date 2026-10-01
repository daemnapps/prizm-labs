#!/usr/bin/env python3
"""The designer's walkthrough of the Brief Board — one page, dumb simple.

    walkthrough.py --brand <brand> --out walkthrough-<brand>.html

Damon, 2026-09-18: "a dumb simple hand off walkthrough artifact for this
brief board, what it is, how it works, each component, any direct prompts
the designer should use."

Built off the live files, never retyped: the brief counts per product, the
settings and Elements off a real work order, the swipe-and-draft pair off a
real brief, the pack links off the register. The prompts she uses are the
ones on the board itself — this page says where they are, it does not copy
them (a second copy is a copy that drifts).
"""
import argparse, html, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P
import briefs as B
import deliver as DV
import designer_page as DP

ROOT = HERE.parent

CSS = """
:root{--paper:#E9EAE6;--card:#F4F5F2;--card2:#FBFBF9;--ink:#15181A;--ink2:#5B6163;--ink3:#878D8C;
  --rule:#CDD0CA;--rule2:#DEE0DA;--oxide:#A33217;--oxide-bg:#F6E4DE;--go:#3B6B2E;--go-bg:#E3ECDC;
  --ask:#1F4F63;--ask-bg:#DDE9EE;
  --sans:'Instrument Sans',ui-sans-serif,system-ui,-apple-system,'Helvetica Neue',sans-serif;
  --disp:'Bricolage Grotesque','Instrument Sans',ui-sans-serif,system-ui,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#121414;--card:#1A1D1D;--card2:#202423;--ink:#E7E9E5;--ink2:#A2A8A6;--ink3:#7A807E;
  --rule:#2E3332;--rule2:#262B2A;--oxide:#E0785A;--oxide-bg:#2A1A15;--go:#8FBF7A;--go-bg:#1A2417;
  --ask:#7FB3C8;--ask-bg:#15242B}}
:root[data-theme="dark"]{
  --paper:#121414;--card:#1A1D1D;--card2:#202423;--ink:#E7E9E5;--ink2:#A2A8A6;--ink3:#7A807E;
  --rule:#2E3332;--rule2:#262B2A;--oxide:#E0785A;--oxide-bg:#2A1A15;--go:#8FBF7A;--go-bg:#1A2417;
  --ask:#7FB3C8;--ask-bg:#15242B}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.6}
.wrap{max-width:860px;margin:0 auto;padding-block:40px 80px;padding-inline:20px}
.eyebrow{font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink3);display:flex;gap:16px;align-items:center;margin:0 0 14px}
.eyebrow::after{content:"";flex:1;height:1px;background:var(--rule)}
h1{font-family:var(--disp);font-weight:800;font-size:44px;letter-spacing:-.025em;line-height:1.02;margin:0 0 18px;text-wrap:balance}
h2{font-family:var(--disp);font-weight:700;font-size:26px;letter-spacing:-.015em;margin:56px 0 10px;text-wrap:balance}
h3{font-family:var(--disp);font-weight:700;font-size:17px;margin:0 0 4px}
p{margin:0 0 14px;max-width:66ch}
.stand{font-size:19px;line-height:1.55;color:var(--ink2)}
.stand b{color:var(--ink);font-weight:600}
a{color:var(--ask)}
.btn{display:inline-flex;align-items:center;gap:10px;text-decoration:none;background:var(--ink);color:var(--paper);
  border-radius:3px;padding:12px 18px;font-weight:600;font-size:15px;margin:6px 8px 6px 0}
.btn:hover{background:var(--oxide)}
.btn small{font-family:var(--mono);font-size:11px;font-weight:400;letter-spacing:.06em;opacity:.75}
.map{counter-reset:c;display:grid;gap:10px;margin:18px 0 0;padding:0;list-style:none}
.map li{counter-increment:c;display:grid;grid-template-columns:40px 1fr;gap:14px;align-items:start;
  background:var(--card);border:1px solid var(--rule);border-radius:3px;padding:14px 16px}
.map li::before{content:counter(c);font-family:var(--mono);font-weight:600;font-size:13px;color:var(--oxide);
  width:30px;height:30px;border:1px solid var(--rule);border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--card2)}
.map p{margin:0;font-size:14.5px;color:var(--ink2)}
.map b.you{color:var(--go)}
.frames{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:16px 0}
figure{margin:0}figure img{display:block;width:100%;border-radius:2px;background:var(--rule2)}
figcaption{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);
  display:flex;justify-content:space-between;margin-top:8px}
figcaption b{color:var(--ink)}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14.5px}
th{text-align:left;font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);
  padding:8px 10px 8px 0;border-bottom:1px solid var(--rule)}
td{padding:10px 10px 10px 0;border-bottom:1px solid var(--rule2);vertical-align:top;color:var(--ink2)}
td.k{font-family:var(--mono);font-size:12.5px;color:var(--ink);white-space:nowrap}
code{font-family:var(--mono);font-size:.9em;background:var(--card2);border:1px solid var(--rule2);border-radius:2px;padding:1px 5px}
ol.steps{padding-left:0;list-style:none;counter-reset:s;margin:14px 0 0}
ol.steps li{counter-increment:s;position:relative;padding:0 0 18px 48px}
ol.steps li::before{content:counter(s);position:absolute;left:0;top:2px;width:30px;height:30px;border-radius:50%;
  background:var(--ink);color:var(--paper);font-family:var(--mono);font-weight:600;font-size:13px;display:flex;align-items:center;justify-content:center}
ol.steps p{margin:0;font-size:15px;color:var(--ink2)}
.rule{border-left:3px solid var(--oxide);background:var(--oxide-bg);padding:16px 20px;border-radius:0 3px 3px 0;margin:22px 0}
.rule b{color:var(--oxide)}
.note{border-left:2px solid var(--go);background:var(--go-bg);padding:14px 18px;border-radius:0 3px 3px 0;margin:18px 0;font-size:15px}
.note b{color:var(--go)}
.us{border:1px dashed var(--rule);border-radius:3px;padding:14px 18px;font-size:14px;color:var(--ink3);margin:18px 0}
footer{margin:70px 0 0;padding-top:20px;border-top:1px solid var(--rule);font-family:var(--mono);font-size:11px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px}
@media (max-width:620px){.frames{grid-template-columns:1fr}h1{font-size:34px}}
"""


def build(brand, out):
    reg = B.load()
    ids = [b for b, r in sorted(reg["briefs"].items())
           if r.get("brand") == brand and r.get("run")
           and (P.RUNS / r["run"] / "out/06-brief.md").is_file()
           and (ROOT / "worksheets" / brand / b / "work-order.md").is_file()]
    by_product = {}
    for b in ids:
        by_product.setdefault(reg["briefs"][b].get("product") or "—", []).append(b)
    packs = {k: v for k, v in (reg.get("packs") or {}).items()
             if (v.get("brand") or k.split("--")[0]) == brand}
    arts = (ROOT / "context/artifacts.md").read_text()
    m = re.search(r"\| The Brief Board[^|]*\| (https://\S+) \|", arts)
    board_url = m.group(1) if m else "#"

    # the example pair and the settings, off a real brief — the first that has a draft
    # a brief with a person in it, so the pair shows the standard on a face
    reads = json.loads((ROOT / "drafts" / brand / "swipe-subjects.json").read_text()) \
        if (ROOT / "drafts" / brand / "swipe-subjects.json").is_file() else {}
    ex = next((b for b in ids if DV.newest_draft(brand, b) and reads.get(b, {}).get("person")),
              next((b for b in ids if DV.newest_draft(brand, b)), ids[0]))
    erec = reg["briefs"][ex]
    src = P.RUNS / erec["run"] / "assets/source.jpg"
    drf = DV.newest_draft(brand, ex)
    wo = (ROOT / "worksheets" / brand / ex / "work-order.md").read_text()
    settings = re.search(r"## The settings.*?\n(\|.*?)(?=\n###|\n## )", wo, re.S)
    settings_html = DP.table(settings.group(1).strip().split("\n")) if settings else ""
    n_prompts = sum(len(list((ROOT / "worksheets" / brand / b / "prompts").glob("*.txt"))) for b in ids)

    # the Elements per product, off each product's first work order
    el_rows = []
    for prod, bids in by_product.items():
        w = (ROOT / "worksheets" / brand / bids[0] / "work-order.md").read_text()
        rows = re.findall(r"^\| (the \w+) \| (.+?) \| (.+?) \|$", w, re.M)
        for who, what, reads in rows:
            el_rows.append((prod.replace("-", " "), who, what, reads))

    pack_btns = "".join(
        f'<a class="btn" href="{html.escape(v["url"])}" target="_blank" rel="noopener">'
        f'Download the {html.escape((v.get("product") or "").replace("-", " "))} pack '
        f'<small>{len(v.get("briefs", []))} briefs</small></a>'
        for _, v in sorted(packs.items()))
    prod_list = " and ".join(f"{len(v)} for the {k.replace('-', ' ')}" for k, v in by_product.items())

    page = f"""<title>Working the Brief Board</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Instrument+Sans:ital,wght@0,400;0,500;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<div class="eyebrow"><span>{html.escape(brand)}</span><span>For the graphic designer</span></div>
<h1>Working the Brief Board</h1>
<p class="stand"><b>The Brief Board is the whole job on one page.</b> Every ad we want made,
with the real photo it copies, our first attempt at it, and the exact prompts to paste into
Higgsfield. You pick a brief, run its prompts, keep the frames that look most like the real
photo, and move to the next. Nothing on it needs writing, rewriting or interpreting.</p>
<p><a class="btn" href="{html.escape(board_url)}" target="_blank" rel="noopener">Open the Brief Board <small>{len(ids)} briefs · {n_prompts} prompts</small></a>{pack_btns}</p>

<h2>What is on it, top to bottom</h2>
<p>Numbered in the order you meet them scrolling down. The ones marked <b style="color:var(--go)">you</b> are the ones you use; the rest are ours.</p>
<ol class="map">
  <li><div><h3>The pack buttons <b class="you">· you</b></h3><p>One zip per product. Inside: a folder per brief with the swipe, our draft, the work order, the brief and the prompts, plus a README with the batch and the settings to set once. Download it if you'd rather work from folders than from the page — same files either way.</p></div></li>
  <li><div><h3>Where these live</h3><p>The paths on GitHub and Google Drive. For us. You never need them.</p></div></li>
  <li><div><h3>How these drafts are made</h3><p>Collapsed. The rules and prompts <i>our machine</i> uses to make the draft pictures. Not your prompts — yours are inside each brief (step 8). Open it only if you're curious.</p></div></li>
  <li><div><h3>The product tabs <b class="you">· you</b></h3><p>Right now: {html.escape(prod_list)}. The board opens on the first product. Click a tab to switch; "all" shows everything.</p></div></li>
  <li><div><h3>The grid of briefs <b class="you">· you</b></h3><p>One card per brief: a thumbnail of our draft, the brief number (<code>{html.escape(ex)}</code> and so on) and one line on what it is. <b>Click a card and the brief opens below.</b> The number is how everything downstream finds your work, so it stays on the files.</p></div></li>
  <li><div><h3>The brief's header <b class="you">· you</b></h3><p>The number, what it is for, and <b>Open the folder →</b> — the brief's own folder on the shared drive. That is where your finished frames go.</p></div></li>
  <li><div><h3>The swipe and ours <b class="you">· you</b></h3><p>Left: the real post this ad copies. Right: our draft. The swipe is the target; the draft is a reference for composition, not something to match. If ours is flagged, a red note says what our machine got wrong — you don't need to fix it, just don't copy it.</p></div></li>
  <li><div><h3>The brief</h3><p>The reasoning behind the ad, as written. Read it if you want the why. You do not need it to work.</p></div></li>
  <li><div><h3>Its prompts <b class="you">· you</b></h3><p><b>These are your prompts.</b> One tab per picture — <code>00-control</code> and up to three variations — each with a <b>Copy</b> button. Paste exactly as copied, with the brief's <code>refs/</code> images attached. Each variation is the control plus one line that moves one thing.</p></div></li>
</ol>

<h2>The standard, in one picture</h2>
<div class="frames">
  <figure><img src="{DP.thumb(src, 700, 60)}" alt="The swiped original."><figcaption><span>source.jpg</span><b>The swipe</b></figcaption></figure>
  <figure><img src="{DP.thumb(drf, 700, 60) if drf else ''}" alt="Our draft."><figcaption><span>draft.png</span><b>Ours</b></figcaption></figure>
</div>
<p>Left is a real post by a real person. Right is ours. They should be hard to tell apart — same light, same softness, same accidental framing. <b>Ours is not meant to be the better photograph.</b></p>

<h2>In Higgsfield, click by click</h2>
<p>Same every brief. Set up once, then it's paste → generate → keep one, per prompt file.</p>
<ol class="steps">
  <li><h3>Higgsfield → Image</h3><p>Model: <b>Nano Banana Pro</b> — the one that takes several reference images. Aspect ratio: the one the work order says (usually <b>9:16</b>). Resolution 2K. Number of images: <b>4</b>.</p></li>
  <li><h3>Attach the references, in order</h3><p>Add image → every file in the brief's <code>refs/</code> folder (in the pack, or on the brief's Drive folder), lowest number first. <code>1-swipe.jpg</code> is always first — the prompt calls it IMAGE 1. The rest are our product from a few angles. <b>No Elements, no styles, no presets.</b> The prompt carries everything.</p></li>
  <li><h3>Paste the control, generate 4</h3><p><b>Copy</b> on the <code>00-control</code> tab → paste into the prompt box → generate. Change nothing in the text.</p></li>
  <li><h3>Keep one</h3><p>The frame that looks most like the swipe <i>and</i> survives the crop check (below). Re-roll two or three times if it won't land; then a one-line note and move on.</p></li>
  <li><h3>Next tab, same everything</h3><p>Same references, same settings, paste the next prompt file. Each variation is the control plus one line that moves one thing — a body part, a room, a person. Four tabs, four keepers.</p></li>
  <li><h3>Drop the keepers in the brief's Drive folder</h3><p><b>Open the folder →</b> in the brief's header. A <code>finals/</code> folder inside it, named after the prompt: <code>00-control.png</code>, <code>01-…png</code>. Problems in <code>finals/notes.txt</code>.</p></li>
</ol>
<div class="tw">{settings_html}</div>
<p style="margin-top:12px;font-size:14px;color:var(--ink3)">Her prompts are our machine's prompts, word for word, with the same reference pictures — so what she makes and what we made can only differ by the roll. If a prompt is wrong for how Higgsfield behaves, that's a note back to us, never a quiet edit.</p>
<div class="note"><b>9:16 everywhere, 4:5 for anything that matters.</b> Every picture is 9:16 so one file runs in every placement. The feed crops it to the centred 4:5, so the face, hands, product and words all sit in that middle — and the top and bottom 15% are still real picture, never a bar. Judge every frame twice: at 9:16, and with the top and bottom covered.</div>

<div class="rule"><b>The one rule that gets broken every time: match the swipe, do not improve on it.</b> If your picture is sharper, cleaner, better lit or better composed than the swipe, it is wrong — it reads as an advertisement, and the whole reason this format works is that it doesn't. No phone or camera in frame, ever. If the swipe has words, ours has the same words in the same place at the same weight.</div>

<div class="us"><b>What we'd like back after the first few:</b> is the page enough to start from · are the prompts usable as-is for how Higgsfield behaves · is four pictures a brief the right batch · where does it get annoying at twenty a week · what's missing.</div>

<footer><span>{html.escape(brand)} · {len(ids)} briefs</span><span>Built off the live board — the board is the truth</span></footer>
</div>
"""
    Path(out).write_text(page)
    return len(ids), len(page)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n, size = build(a.brand, a.out)
    print(f"{a.out}  ·  {n} briefs  ·  {size/1000:.0f} KB")
