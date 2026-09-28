#!/usr/bin/env python3
"""Renders the board — the one page Damon reads for this subject: the flow,
the page, the video, both prompts verbatim, the asks, both queues, what is
open. Same sources as the public page, plus the live queues on Drive.

    python3 render_board.py <out.html>          # the artifact file
    python3 render_board.py <out.html> --md <out.md>   # and the Markdown mirror
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
sys.path.insert(0, str(HERE))
import queue as Q  # noqa: E402
sys.path.insert(0, str(TOOL.parent / "22-swipe-library" / "machine"))
import library as LIB  # noqa: E402

ASKS = TOOL.parents[0] / "05-ai-video-production" / "ASKS-SPEC.md"
HANDOFF = TOOL.parents[0] / "05-ai-video-production" / "prompts" / "stage-6-handoff" / "stage6-handoff-v5-damon.md"
VIDEO = "https://drive.google.com/file/d/1H5WVVLt5nbgXGjXxwsfVk2k9fzw9eQQh/view"
FOLDER = "https://drive.google.com/drive/folders/1V6s6D98PdelDKh8THm_RqJjGTPgfL-6Y"
PAGE = "https://daemn.co/onboarding.html"


E = html.escape


def block(path: Path, fence="prompt") -> str:
    m = re.search(rf"```{fence}\n(.*?)```", path.read_text(), re.S)
    return m.group(1).strip() if m else path.read_text()


def asks_section() -> str:
    s = HANDOFF.read_text()
    m = re.search(r"(## THE ASKS\n.*?)(?=\n## THE RECEIPT)", s, re.S)
    return m.group(1).strip()


def queues() -> dict[str, list[dict]]:
    out = {}
    root = Q.brands_root()
    if root.is_dir():
        for p in sorted(root.iterdir()):
            if p.is_dir() and not p.name.startswith(".") and Q.briefs_folder(p.name):
                out[p.name] = Q.build(p.name, write=False)
    return out


day_one = block(TOOL / "prompts" / "01-day-one-v2-damon.md")
swipe_prompt = block(TOOL / "prompts" / "03-swipe-library-v1-damon.md")
LF, LV, LFE, LSW = LIB.formats(), LIB.videos(), LIB.feeds(), LIB.sweeps()
ltorn = [v for v in LV if v["torn"]]
feed_rows = "".join(f'<tr><td class="b">{E(f["feed"])}</td><td>{E(f["brand"])}</td><td>{f["kept"]}</td>'
                    f'<td>{f["lanes"].get("entertainment", 0)}</td><td>{f["lanes"].get("educational", 0)}</td><td>{E(f["updated"])}</td></tr>' for f in LFE)
sweep_rows = "".join(f'<tr><td class="b">{i}</td><td>{s["angles"]}</td><td>{s["ads"]:,}</td><td>{s["concentration"]}%</td><td>{"yes" if s["on_drive"] else "not yet"}</td></tr>' for i, s in enumerate(LSW, 1))
pull = block(TOOL / "prompts" / "02-pull-briefs-v2-damon.md")
asks_v4 = asks_section()
qs = queues()
built = datetime.now().strftime("%-d %b %Y, %H:%M")


def qtable(brand: str, rows: list[dict]) -> str:
    if not rows:
        return f'<p class="muted">{E(brand)} — nothing in the briefs folder.</p>'
    tr = "".join(
        f'<tr><td class="b">{E(r["brief"])}</td><td>{E(r["type"])}</td>'
        f'<td><span class="pill {E(r["status"])}">{E(r["status"])}</span></td>'
        f'<td>{E(r["who"] or "—")}</td><td>{E(r["bounty"] or "—")}</td><td>{E(r["due"] or "—")}</td>'
        f'<td class="mono">{E(r["package"])}</td><td>{E(r["note"])}</td></tr>' for r in rows)
    return (f'<div class="tw"><table><thead><tr><th>Brief</th><th>Type</th><th>Status</th><th>Who</th>'
            f'<th>Bounty</th><th>Due</th><th>Package</th><th>Note</th></tr></thead><tbody>{tr}</tbody></table></div>')


queue_html = "".join(f'<h3>{E(b)} <span class="count">{len(r)} brief{"s" if len(r) != 1 else ""}</span></h3>{qtable(b, r)}'
                     for b, r in qs.items())

page = f"""<title>Editor Onboarding</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Jost:wght@200;300;400&family=Archivo:wght@400;500&family=IBM+Plex+Mono:wght@400&display=swap">
<style>
:root{{
  --ground:#F5EEE9;--panel:#FBF6F2;--panel2:#EFE4DD;--line:rgba(76,61,55,.16);
  --ink:#1B1512;--ink2:#4C3D37;--ink3:rgba(76,61,55,.6);
  --accent:#8C2F1E;--ok:#3E7D4A;--warn:#9A6A1E;--claim:#4B5FA8;
  --display:Jost,"Century Gothic",Futura,ui-sans-serif,sans-serif;
  --body:Archivo,"Helvetica Neue",Inter,system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
}}
@media (prefers-color-scheme: dark){{ :root:not([data-theme="light"]){{
  --ground:#0B0D10;--panel:#12161C;--panel2:#1A2028;--line:#242A33;
  --ink:#FFFFFF;--ink2:rgba(255,255,255,.84);--ink3:rgba(255,255,255,.56);
  --accent:#EBFF00;--ok:#6FD27F;--warn:#E3B04B;--claim:#8FA3F0; }} }}
:root[data-theme="dark"]{{
  --ground:#0B0D10;--panel:#12161C;--panel2:#1A2028;--line:#242A33;
  --ink:#FFFFFF;--ink2:rgba(255,255,255,.84);--ink3:rgba(255,255,255,.56);
  --accent:#EBFF00;--ok:#6FD27F;--warn:#E3B04B;--claim:#8FA3F0; }}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.6}}
.wrap{{max-width:1040px;margin:0 auto;padding-block:36px 80px;padding-inline:clamp(16px,4vw,40px)}}
h1{{font-family:var(--display);font-weight:200;text-transform:uppercase;letter-spacing:.03em;font-size:clamp(34px,6vw,64px);line-height:.95;margin:0 0 10px;text-wrap:balance}}
h2{{font-family:var(--display);font-weight:200;text-transform:uppercase;letter-spacing:.05em;font-size:clamp(22px,3vw,32px);margin:0 0 14px;text-wrap:balance}}
h3{{font-family:var(--display);font-weight:300;text-transform:uppercase;letter-spacing:.06em;font-size:17px;margin:26px 0 8px}}
p{{color:var(--ink2);max-width:66ch;margin:0 0 12px}}
.eyebrow{{font-family:var(--mono);font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--ink3);margin:0 0 12px}}
.muted{{color:var(--ink3)}}
.mono{{font-family:var(--mono);font-size:12px}}
a{{color:var(--ink)}}
section{{padding-top:56px;border-top:1px solid var(--line);margin-top:56px}}
section:first-of-type{{border-top:0;margin-top:0;padding-top:20px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0}}
.chips a{{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;text-decoration:none;color:var(--ink2);border:1px solid var(--line);border-radius:999px;padding:7px 12px}}
.chips a:hover{{border-color:var(--ink)}}
.flow{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:22px}}
@media(max-width:760px){{.flow{{grid-template-columns:1fr 1fr}}}}
@media(max-width:430px){{.flow{{grid-template-columns:1fr}}}}
.node{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 16px 14px;position:relative}}
.node .w{{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink3);margin-bottom:8px}}
.node b{{display:block;font-weight:500;margin-bottom:4px}}
.node span{{font-size:13px;color:var(--ink2)}}
.node.hot{{border-color:var(--accent)}}
.links{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;margin-top:18px}}
.link{{display:block;text-decoration:none;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.link:hover{{border-color:var(--ink)}}
.link .k{{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink3);margin-bottom:6px}}
.link b{{display:block;font-weight:500}}
.link span{{font-size:13px;color:var(--ink2)}}
.chap{{list-style:none;padding:0;margin:14px 0 0;columns:2;column-gap:28px;font-family:var(--mono);font-size:11.5px;line-height:2;color:var(--ink2)}}
@media(max-width:600px){{.chap{{columns:1}}}}
.chap .t{{display:inline-block;width:48px;color:var(--ink3)}}
.steps{{display:grid;gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-top:18px}}
.step{{background:var(--panel);padding:16px 18px;display:grid;grid-template-columns:44px 1fr;gap:14px}}
.step .n{{font-family:var(--mono);font-size:10px;letter-spacing:.16em;color:var(--ink3);padding-top:4px}}
.step b{{display:block;font-weight:500;margin-bottom:3px}}
.step span{{font-size:13.5px;color:var(--ink2)}}
.step .you{{display:inline-block;margin-top:6px;font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}}
pre{{font-family:var(--mono);font-size:12px;line-height:1.7;white-space:pre-wrap;word-break:break-word;background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:10px;padding:18px 20px;margin:12px 0 0;color:var(--ink2)}}
.prompt-head{{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-top:24px}}
.prompt-head .file{{font-family:var(--mono);font-size:11px;color:var(--ink3)}}
.asks{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-top:18px}}
.ask{{background:var(--panel);padding:16px 18px}}
.ask .k{{font-family:var(--mono);font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink);margin-bottom:6px}}
.ask span{{font-size:13px;color:var(--ink2)}}
.ask .d{{display:block;font-family:var(--mono);font-size:10.5px;color:var(--ink3);margin-top:8px}}
.count{{font-family:var(--mono);font-size:11px;letter-spacing:.1em;color:var(--ink3);text-transform:none;margin-left:8px}}
.tw{{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel)}}
table{{border-collapse:collapse;width:100%;font-size:13.5px}}
th{{text-align:left;font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:400;padding:12px 14px;border-bottom:1px solid var(--line);white-space:nowrap}}
td{{padding:11px 14px;border-bottom:1px solid var(--line);vertical-align:top;color:var(--ink2)}}
tr:last-child td{{border-bottom:0}}
td.b{{color:var(--ink);font-weight:500}}
.pill{{display:inline-block;font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;padding:3px 9px;border-radius:999px;border:1px solid var(--line);color:var(--ink2)}}
.pill.open{{border-color:var(--ok);color:var(--ok)}}
.pill.claimed{{border-color:var(--claim);color:var(--claim)}}
.pill.delivered{{border-color:var(--warn);color:var(--warn)}}
.pill.approved,.pill.paid{{border-color:var(--ink);color:var(--ink)}}
.open-list{{list-style:none;padding:0;margin:14px 0 0}}
.open-list li{{border-top:1px solid var(--line);padding:14px 0;display:grid;grid-template-columns:110px 1fr;gap:14px;font-size:14px;color:var(--ink2)}}
.open-list li .who{{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);padding-top:4px}}
.open-list li b{{color:var(--ink);font-weight:500}}
.foot{{margin-top:60px;font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;color:var(--ink3)}}
@media(prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style>

<div class="wrap">
<p class="eyebrow">Editors and designers · Higgsfield first · built {E(built)}</p>
<h1>Editor<br>onboarding</h1>
<p>Editors and designers work inside Higgsfield Supercomputer. It reads the brand folder on Drive and the tools from GitHub; briefs go to them there, finished work comes back to Drive, the queue rebuilds itself every hour.</p>
<div class="chips">
  <a href="#flow">The flow</a><a href="#page">The page</a><a href="#video">The video</a><a href="#loop">The loop</a>
  <a href="#prompts">The prompts</a><a href="#asks">The asks</a><a href="#queue">The queues</a><a href="#library">The swipe library</a><a href="#sync">Sync</a><a href="#open">Open</a>
</div>

<section id="flow">
<p class="eyebrow">01 · the flow</p>
<h2>Five places, one direction</h2>
<div class="flow">
  <div class="node"><div class="w">You · Claude Code</div><b>The brief is made</b><span>Teardown → AI production → handoff pack, ending in THE ASKS.</span></div>
  <div class="node"><div class="w">Google Drive</div><b>Drops in <span class="mono">briefs/</span></b><span>The package lands in the brand folder. The queue sees it within the hour.</span></div>
  <div class="node hot"><div class="w">Higgsfield</div><b>The editor pulls it</b><span>One prompt: sync, claim, lay out, review, the asks, the edit. The brand folder opens by link — no invitation.</span></div>
  <div class="node"><div class="w">Premiere · CapCut</div><b>The cut</b><span>From the cut sheet the prompt packs. AI editing lands here later.</span></div>
  <div class="node"><div class="w">Google Drive</div><b>Back in <span class="mono">delivered/</span></b><span>Named to the brief. The queue flips to delivered; you approve, you pay.</span></div>
</div>
</section>

<section id="page">
<p class="eyebrow">02 · the page they get</p>
<h2>One link for every new editor</h2>
<p>The walkthrough, the setup, the loop, both prompts with copy buttons, the queue rules, the asks, the rules, and what to do when it breaks. Generic on purpose — it works for anyone who clones the tools; the brand comes from Drive.</p>
<div class="links">
  <a class="link" href="{PAGE}" target="_blank" rel="noopener"><div class="k">Public page</div><b>daemn.co/onboarding.html</b><span>live once the repo is pushed (GitHub Pages)</span></a>
  <a class="link" href="https://github.com/daemnapps/prizm-labs/blob/main/tools/21-editor-onboarding/DESK.md" target="_blank" rel="noopener"><div class="k">For the onboarder</div><b>tools/21-editor-onboarding/DESK.md</b><span>the onboarder's side: folders by link once per brand, one message per editor, what to check</span></a>
  <a class="link" href="{FOLDER}" target="_blank" rel="noopener"><div class="k">Drive folder</div><b>Shared Assets / onboarding</b><span>the edited video + the full transcript — share this with editors</span></a>
  <a class="link" href="https://github.com/daemnapps/prizm-labs/tree/main/tools/21-editor-onboarding" target="_blank" rel="noopener"><div class="k">The tool</div><b>tools/21-editor-onboarding</b><span>SOP, prompts, the queue, the cut list</span></a>
</div>
</section>

<section id="video">
<p class="eyebrow">03 · the walkthrough</p>
<h2>67 minutes cut to 17</h2>
<p>The recorded call with Ahmed, cut to the ten steps that teach, with a title card in front of each. Rendered at full 1080p; wherever a screen is being shared the cut zooms to that screen so the buttons are readable. The cut is a text file in the tools (<span class="mono">walkthrough/cut-list.json</span>) — change a timestamp, run it again, new video. The full transcript sits beside it on Drive.</p>
<div class="links">
  <a class="link" href="{VIDEO}" target="_blank" rel="noopener"><div class="k">Watch</div><b>walkthrough-editors-v1.mp4</b><span>17 min · 1080p, cropped to the shared screen</span></a>
</div>
<ul class="chap">
  <li><span class="t">00:04</span>1 · Connect Drive and GitHub inside Supercomputer</li>
  <li><span class="t">03:03</span>2 · Put the shared brand folders in your own Drive</li>
  <li><span class="t">06:21</span>3 · Test it — new chat, + → Connectors</li>
  <li><span class="t">07:30</span>4 · Clone the tools repo</li>
  <li><span class="t">09:20</span>5 · "Pull my GitHub repository and look for updates"</li>
  <li><span class="t">11:25</span>6 · Where the briefs live</li>
  <li><span class="t">13:37</span>7 · The workflow — review, remove slop, reroll, sequence, edit</li>
  <li><span class="t">14:50</span>8 · Turn the pull into a skill</li>
  <li><span class="t">15:35</span>9 · Execute a brief — pull up its clips</li>
  <li><span class="t">16:34</span>10 · Pull in the AI video production workflows</li>
</ul>
</section>

<section id="loop">
<p class="eyebrow">04 · every session</p>
<h2>The loop the prompt runs</h2>
<div class="steps">
  <div class="step"><span class="n">01</span><div><b>Sync</b><span>Pull the tools; read the live queue from Drive. Never skipped.</span></div></div>
  <div class="step"><span class="n">02</span><div><b>Pick</b><span>The brief they name or the newest open one. A claim file goes in <span class="mono">briefs/claims/</span>.</span></div></div>
  <div class="step"><span class="n">03</span><div><b>Lay it out</b><span>Scenes with clips, voices and first frames — or the image drafts. The intended cut, the locks, the known issues, the loop, verbatim.</span></div></div>
  <div class="step"><span class="n">04</span><div><b>Review</b><span>Same person · same wardrobe · same product · slop · sound · words · odd. A KEEP / FIX AT CUT / REROLL table, then three to five ideas inside the loop.</span><br><span class="you">stops — the editor decides</span></div></div>
  <div class="step"><span class="n">05</span><div><b>The asks</b><span>Scroll stoppers, headlines, variations, extra scenes, formats, styles — from the handoff, or the default menu. Made in Higgsfield from the same references.</span><br><span class="you">stops — the editor approves each</span></div></div>
  <div class="step"><span class="n">06</span><div><b>The edit</b><span>Video → <span class="mono">&lt;brief&gt;--edit</span> with a cut sheet, into Premiere or CapCut. Static → <span class="mono">&lt;brief&gt;--finals</span>.</span></div></div>
  <div class="step"><span class="n">07</span><div><b>Deliver</b><span><span class="mono">briefs/delivered/&lt;brief&gt;/</span> + a DELIVERED.md. The queue flips itself.</span></div></div>
</div>
</section>

<section id="prompts">
<p class="eyebrow">05 · the prompts, verbatim</p>
<h2>Two prompts, that's the job</h2>
<p>These are the exact files the editor pastes. <span class="mono">{{BRAND}}</span> is the only thing they fill in. Change the file and the public page re-renders from it.</p>
<div class="prompt-head"><h3 style="margin:0">Day one · v1</h3><span class="file">prompts/01-day-one-v2-damon.md · pasted once</span></div>
<pre>{E(day_one)}</pre>
<div class="prompt-head"><h3 style="margin:0">Pull briefs · v1</h3><span class="file">prompts/02-pull-briefs-v2-damon.md · pasted every session</span></div>
<pre>{E(pull)}</pre>
</section>

<section id="asks">
<p class="eyebrow">06 · built into the brief</p>
<h2>The asks</h2>
<p>Every handoff now ends with THE ASKS — six lines, each specified or refused with a reason. The editor makes them after the base cut. Older briefs without the section get the default menu.</p>
<div class="asks">
  <div class="ask"><div class="k">Scroll stoppers</div><span>Alternative first three seconds, one per unused hook.</span><span class="d">default · 3</span></div>
  <div class="ask"><div class="k">Headlines</div><span>Opener-card lines under eight words, from the brief's own words.</span><span class="d">default · 5</span></div>
  <div class="ask"><div class="k">Variations</div><span>Alternate takes of the opening and the offer, same line, new framing.</span><span class="d">default · 1 each</span></div>
  <div class="ask"><div class="k">Extra scenes</div><span>Inserts for beats POST or KNOWN ISSUES leave uncovered.</span><span class="d">default · one per gap</span></div>
  <div class="ask"><div class="k">Formats</div><span>9:16 only — nothing at 4:5 or 1:1. A 15 s cutdown map, and every face, product and word inside the centred 4:5 crop.</span><span class="d">default · one ratio</span></div>
  <div class="ask"><div class="k">Styles</div><span>A restyle of the same film — only when the brief names one.</span><span class="d">default · none</span></div>
</div>
<div class="prompt-head"><h3 style="margin:0">Stage 6 handoff · v4 — the new section</h3><span class="file">tools/05-ai-video-production/prompts/stage-6-handoff/stage6-handoff-v5-damon.md · spec: ASKS-SPEC.md</span></div>
<pre>{E(asks_v4)}</pre>
</section>

<section id="queue">
<p class="eyebrow">07 · the queues · as of {E(built)}</p>
<h2>What is waiting</h2>
<p>Read from each brand's <span class="mono">briefs/</span> folder on Drive. Open = the package is there. Claimed = a claim file. Delivered = files in <span class="mono">delivered/&lt;brief&gt;/</span>. Bounty and due are yours to set; nothing else is typed by hand.</p>
{queue_html}
</section>

<section id="library">
<p class="eyebrow">08 · the swipe library · as of {E(built)}</p>
<h2>Everything swiped, one door</h2>
<p>Tools public, assets private. The formats and the angle shapes are on the site for anyone; the videos, the feeds and the competitor sweeps are on Drive, indexed in <span class="mono">SWIPE LIBRARY.md</span> at the root of the shared drive, read through Higgsfield with the prompt below. Sweeps are numbered here because this board is shareable; the index on Drive names them.</p>
<div class="flow">
  <div class="node"><div class="w">Public · site</div><b>{len([k for k in set(v["format"] for v in ltorn) if not k.startswith("one-off")])} formats</b><span>+ one-offs · {len(ltorn)} posts taken apart, text only. Rebuilt today.</span></div>
  <div class="node"><div class="w">Drive</div><b>{len(LV)} swipe videos</b><span>{len(ltorn)} torn down, {len(LV) - len(ltorn)} waiting · video, sheet, beat strip per folder.</span></div>
  <div class="node hot"><div class="w">Drive</div><b>{len(LFE)} feeds</b><span>{sum(f["kept"] for f in LFE):,} posts kept of {sum(f["total"] for f in LFE):,} seen · a FEED.md each, every row linked.</span></div>
  <div class="node"><div class="w">Drive + site</div><b>{len(LSW)} sweeps · {sum(s["ads"] for s in LSW):,} ads</b><span>{sum(s["angles"] for s in LSW)} angles with media on Drive; the recurring shapes on the site, brands unnamed.</span></div>
  <div class="node"><div class="w">You · this Mac</div><b>My Feeds</b><span>The live board — Pull now, Tear down. These files are its export.</span></div>
</div>
<div class="links">
  <a class="link" href="https://daemn.co/swipes/" target="_blank" rel="noopener"><div class="k">Public page</div><b>daemn.co/swipes/</b><span>formats + angle shapes, straight from the repo</span></a>
  <a class="link" href="https://drive.google.com/drive/folders/1V6s6D98PdelDKh8THm_RqJjGTPgfL-6Y" target="_blank" rel="noopener"><div class="k">Drive</div><b>Shared Assets</b><span>SWIPE LIBRARY.md sits at the root, beside the brands folder</span></a>
</div>
<h3>The feeds</h3>
<div class="tw"><table><thead><tr><th>Feed</th><th>Brand</th><th>Kept</th><th>Entertainment</th><th>Educational</th><th>Newest</th></tr></thead><tbody>{feed_rows}</tbody></table></div>
<h3>The paid sweeps</h3>
<div class="tw"><table><thead><tr><th>#</th><th>Angles</th><th>Live ads</th><th>Top-3 share</th><th>Media on Drive</th></tr></thead><tbody>{sweep_rows}</tbody></table></div>
<div class="prompt-head"><h3 style="margin:0">Swipe library · v1</h3><span class="file">prompts/03-swipe-library-v1-damon.md · pasted when they want something to rebuild</span></div>
<pre>{E(swipe_prompt)}</pre>
</section>

<section id="sync">
<p class="eyebrow">09 · always in step</p>
<h2>How Drive and the tools stay synced</h2>
<p><b>Two homes, on purpose.</b> The tools live in the public repo (Prizm Labs). The briefs — runs, packs, brand material — live in the private workspace (ai-workspace) and on Drive, and never touch the public repo. The bridge between them is one verb, run for you every hour.</p>
<div class="steps">
  <div class="step"><span class="n">→</span><div><b>Workspace → Drive</b><span>Every finished run in ai-workspace (its pack cleared the gates) is zipped and dropped into the brand's <span class="mono">briefs/</span> on Drive, once — never twice, never over something an editor has claimed. <span class="mono">queue.py ship --auto</span>, hourly.</span></div></div>
  <div class="step"><span class="n">→</span><div><b>Tools → editors</b><span>The Pull-briefs prompt pulls the repo before anything else, every session. Whatever is committed reaches every editor next time they sit down.</span></div></div>
  <div class="step"><span class="n">→</span><div><b>Drive → queue</b><span>An hourly job on your Mac rebuilds every brand's QUEUE.md from the briefs folder. Log: <span class="mono">~/Library/Logs/daemn/brief-queue.log</span>.</span></div></div>
  <div class="step"><span class="n">→</span><div><b>Prompts → page</b><span>The public page is rendered from the prompt files. Edit a prompt, re-render, push — the page and the pasted text can't drift.</span></div></div>
</div>
</section>

<section id="open">
<p class="eyebrow">10 · open</p>
<h2>What only you can do</h2>
<ul class="open-list">
  <li><span class="who">Damon</span><div><b>Open the folders by link — no invitations.</b> In Drive, for each brand: the brand folder → Share → General access → <b>Anyone with the link · Viewer</b>; its <span class="mono">briefs</span> folder → <b>Anyone with the link · Editor</b> (they deliver into it). Same for <span class="mono">Shared Assets / onboarding</span> (Viewer) so the video plays. If Drive greys the option out, the shared drive's settings need "allow sharing with non-members" turned on first (Manage shared drive → Settings). Sharing changes are the one thing I'm not allowed to make.</div></li>
  <li><span class="who">Damon</span><div><b>Set bounties and due dates</b> — tell me per brief ("kzn03 $150 by Friday") and I set them; the queue shows them within the hour.</div></li>
  <li><span class="who">Damon</span><div><b>DOUXDS briefs folder</b> — it is sitting at <span class="mono">brands/douxds/archive/empty-folders/briefs/</span>, not <span class="mono">brands/douxds/briefs/</span>. The queue finds it either way; moving it back is one drag in Drive, and I was not allowed to move it for you.</div></li>
  <li><span class="who">Damon</span><div><b>Push the repo</b> so daemn.co/onboarding.html goes live — say the word and I commit and push.</div></li>
  <li><span class="who">next</span><div><b>AI editing</b> — the cut from the cut sheet without a timeline. Until then the edit is the editor's, in Premiere or CapCut.</div></li>
</ul>
</section>

<p class="foot">Mirrors in the repo: tools/21-editor-onboarding/SOP.md · prompts/ · tools/05-ai-video-production/ASKS-SPEC.md · context/artifacts.md</p>
</div>
"""

out = Path(sys.argv[1])
out.write_text(page)
print(f"wrote {out} — {len(page):,} bytes; queues: " + ", ".join(f"{b} {len(r)}" for b, r in qs.items()))

if "--md" in sys.argv:
    md = Path(sys.argv[sys.argv.index("--md") + 1])
    lines = [f"# Editor onboarding — the board (mirror)", "", f"Built {built}. The artifact is the page; this is its Markdown mirror.", "",
             f"- Public page: {PAGE}", f"- Walkthrough video: {VIDEO}", f"- Drive folder: {FOLDER}", "",
             "## The queues", ""]
    for b, rows in qs.items():
        lines += [f"### {b}", "", "| Brief | Type | Status | Who | Bounty | Due | Package |", "|---|---|---|---|---|---|---|"]
        lines += [f"| {r['brief']} | {r['type']} | {r['status']} | {r['who'] or '—'} | {r['bounty'] or '—'} | {r['due'] or '—'} | `{r['package']}` |" for r in rows] or ["| — | | | | | | |"]
        lines.append("")
    lines += ["## The prompts", "", "Verbatim in `prompts/01-day-one-v2-damon.md` and `prompts/02-pull-briefs-v2-damon.md`.", "",
              "## The asks", "", "`../05-ai-video-production/ASKS-SPEC.md`; the handoff section in `stage-6-handoff/stage6-handoff-v5-damon.md`.", ""]
    md.write_text("\n".join(lines))
    print(f"wrote {md}")
