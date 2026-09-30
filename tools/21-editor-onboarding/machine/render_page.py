#!/usr/bin/env python3
"""Renders docs/onboarding.html — the public onboarding page — from the files
that are the truth: the two prompts and the SOP. Run it after any of them
change, so the page never drifts from the prompt an editor actually pastes.

    python3 render_page.py            # writes ../../../docs/onboarding.html
"""
from __future__ import annotations

import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
REPO = TOOL.parents[1]
OUT = REPO / "docs" / "onboarding.html"

VIDEO_ID = "1H5WVVLt5nbgXGjXxwsfVk2k9fzw9eQQh"      # Shared Assets/onboarding/walkthrough-editors-v1.mp4
VIDEO_FOLDER = "1V6s6D98PdelDKh8THm_RqJjGTPgfL-6Y"


def prompt_block(path: Path) -> str:
    m = re.search(r"```prompt\n(.*?)```", path.read_text(), re.S)
    if not m:
        raise SystemExit(f"{path.name}: no ```prompt block")
    return m.group(1).strip()


def chapters() -> list[dict]:
    import json
    spec = json.loads((TOOL / "walkthrough" / "cut-list.json").read_text())
    out, t = [], 0.0
    cs = spec.get("card_seconds", 3)
    t += cs + 1
    for ch in spec["chapters"]:
        out.append({"title": ch["card"].replace("\n", " "), "at": t})
        t += cs
        for a, b in ch["keep"]:
            def s(x):
                p = [float(v) for v in x.split(":")]
                return sum(v * 60 ** i for i, v in enumerate(reversed(p)))
            t += s(b) - s(a)
    return out


def mmss(t: float) -> str:
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


day_one = prompt_block(TOOL / "prompts" / "01-day-one-v2-damon.md")
pull = prompt_block(TOOL / "prompts" / "02-pull-briefs-v2-damon.md")
chaps = chapters()

chapter_html = "\n".join(
    f'<li><span class="t">{mmss(c["at"])}</span>{html.escape(c["title"])}</li>' for c in chaps)

page = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#EDE0DC">
<meta name="description" content="Onboarding for the editors and designers who make our ads: the walkthrough video, the way we work, and the two prompts you paste into Higgsfield Supercomputer.">
<title>Onboarding — PRIZM LABS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Jost:wght@200;300;400&family=Archivo:wght@400;500&family=IBM+Plex+Mono:wght@400&display=swap">
<link rel="stylesheet" href="studio.css">
<style>
.hero{{display:grid;grid-template-columns:.9fr 1.1fr;gap:50px;align-items:start;padding-top:120px}}
@media(max-width:900px){{.hero{{grid-template-columns:1fr;padding-top:110px}}}}
.player{{border:1px solid var(--line);border-radius:14px;overflow:hidden;
  background:color-mix(in srgb,var(--halo) 72%,transparent)}}
.player iframe{{display:block;width:100%;aspect-ratio:16/9;border:0;background:#000}}
.chapters{{list-style:none;margin:0;padding:10px 18px 14px;columns:2;column-gap:24px;
  font-family:var(--mono);font-size:11px;line-height:2;color:var(--ink2)}}
@media(max-width:600px){{.chapters{{columns:1}}}}
.chapters .t{{display:inline-block;width:46px;color:var(--ink3)}}
.need{{list-style:none;padding:0;margin:24px 0 0;border-top:1px solid var(--line)}}
.need li{{border-bottom:1px solid var(--line);padding:16px 0;display:grid;grid-template-columns:34px 1fr;gap:14px;font-size:14.5px;color:var(--ink2)}}
.need li .n{{font-family:var(--mono);font-size:10px;letter-spacing:.16em;color:var(--ink3);padding-top:5px}}
.need li b{{display:block;margin-bottom:3px}}
.steps{{display:grid;gap:1px;background:var(--line);border:1px solid var(--line);
  border-radius:14px;overflow:hidden;margin-top:30px}}
.step{{background:color-mix(in srgb,var(--halo) 72%,transparent);padding:22px 24px;
  display:grid;grid-template-columns:54px 1fr;gap:20px;align-items:start}}
.step .n{{font-family:var(--mono);font-size:10px;letter-spacing:.16em;color:var(--ink3);padding-top:4px}}
.step h3{{margin:0 0 6px}}
.step p{{font-size:13.5px;margin:0;max-width:64ch}}
.step p+p{{margin-top:6px}}
.step .you{{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink);margin-top:8px}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:56px}}
@media(max-width:860px){{.two{{grid-template-columns:1fr;gap:28px}}}}
.panel{{border:1px solid var(--line);border-radius:14px;padding:26px 26px 22px;
  background:color-mix(in srgb,var(--halo) 66%,transparent);margin-top:26px}}
.panel h3{{margin-bottom:4px}}
.panel .when{{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);margin-bottom:16px}}
.brandin{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 16px}}
.brandin label{{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3)}}
.brandin input{{background:var(--halo);border:1px solid var(--line);color:var(--ink);font-family:var(--mono);
  font-size:13px;padding:9px 12px;border-radius:8px;width:200px}}
pre.prompt{{font-family:var(--mono);font-size:12px;line-height:1.7;white-space:pre-wrap;word-break:break-word;
  background:var(--halo);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin:0 0 14px;
  max-height:420px;overflow:auto;color:var(--ink2)}}
pre.prompt mark{{background:color-mix(in srgb,#E9C7D6 70%,transparent);color:var(--ink);padding:0 3px;border-radius:3px}}
.copy{{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;background:var(--ink);
  color:var(--halo);border:1px solid var(--ink);border-radius:999px;padding:12px 22px;cursor:pointer}}
.copy:hover{{background:transparent;color:var(--ink)}}
.copy.done{{background:transparent;color:var(--ink)}}
.rules{{list-style:none;padding:0;margin:0}}
.rules li{{border-top:1px solid var(--line);padding:18px 0;color:var(--ink2);font-size:14.5px}}
.rules li b{{display:block;font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink3);margin-bottom:6px;font-weight:400}}
.qtab{{border-collapse:collapse;width:100%;margin-top:26px;font-size:13.5px}}
.qtab th{{text-align:left;font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--ink3);font-weight:400;padding:0 14px 12px 0;border-bottom:1px solid var(--line)}}
.qtab td{{padding:12px 14px 12px 0;border-bottom:1px solid var(--line);vertical-align:top;color:var(--ink2)}}
.qtab td:first-child{{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink);white-space:nowrap}}
.asks{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1px;background:var(--line);
  border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-top:30px}}
.ask{{background:color-mix(in srgb,var(--halo) 72%,transparent);padding:22px 22px 20px}}
.ask .k{{font-family:var(--mono);font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink);margin-bottom:8px}}
.ask p{{font-size:13.5px;margin:0}}
.ask .d{{font-family:var(--mono);font-size:10.5px;color:var(--ink3);margin-top:10px}}
</style>

<nav>
  <a class="mark" href="/">PRIZM LABS</a>
  <span class="sp"></span>
  <a class="link" href="/how-it-works.html">The tools</a>
  <a class="link" href="/swipes/">Swipe library</a>
  <a class="link" href="/onboarding.html" aria-current="page">Onboarding</a>
  <a class="link" href="https://github.com/daemnapps/prizm-labs" target="_blank" rel="noopener">Repo</a>
</nav>

<div class="wrap">
  <div class="hero">
    <div>
      <p class="eyebrow">Onboarding · editors and designers</p>
      <h1>Start<br>here.</h1>
      <p class="lede">You never install anything. You work inside <b>Higgsfield Supercomputer</b>,
        which reads the brand folder on Google Drive and our tools from GitHub. Briefs come to
        you there; finished work goes back to Drive from there.</p>
      <p class="lede">Watch the walkthrough once. Then the two prompts below are the whole job.</p>
      <ul class="need">
        <li><span class="n">01</span><div><b>The brand folder link</b>one Google Drive link from the owner — it opens for anyone with it, no invitation</div></li>
        <li><span class="n">02</span><div><b>A Higgsfield account</b>your own is enough; the owner's workspace only matters for its credits</div></li>
        <li><span class="n">03</span><div><b>This page</b>the video, the steps, the prompts — bookmark it</div></li>
      </ul>
      <div class="btns">
        <a class="btn" href="#setup">Set up — ten minutes</a>
        <a class="btn ghost" href="#prompts">The prompts</a>
      </div>
      <div class="note">The video plays for anyone the walkthrough folder is shared with</div>
    </div>
    <div class="player">
      <iframe src="https://drive.google.com/file/d/{VIDEO_ID}/preview" allow="autoplay; fullscreen" allowfullscreen title="Editor onboarding — the walkthrough"></iframe>
      <ul class="chapters">
        {chapter_html}
      </ul>
    </div>
  </div>

  <section id="setup">
    <p class="eyebrow">01 — once</p>
    <h2>Set up,<br>ten minutes</h2>
    <p class="lede">Everything happens in Higgsfield Supercomputer. Supercomputer can only see what
      is in your own Google Drive, so step 3 matters.</p>
    <div class="steps">
      <div class="step"><span class="n">01</span><div><h3>Get the brand folder link</h3>
        <p>One Google Drive link from the owner. No invitation and nothing to be added to — the folder opens for anyone with the link. Keep it; the Day-one prompt takes it.</p></div></div>
      <div class="step"><span class="n">02</span><div><h3>Connect Drive and GitHub</h3>
        <p>In Supercomputer: <b>Connectors → Explore</b> → connect <b>Google Drive</b>, then <b>GitHub</b>. Sign in to each when asked.</p><p class="you">Video · chapter 1</p></div></div>
      <div class="step"><span class="n">03</span><div><h3>Put the brand folder in your own Drive</h3>
        <p>Open the link, then in Google Drive right-click the folder → <b>Organize → Add shortcut</b> → into a folder you make in <i>My Drive</i>. Supercomputer only sees your own Drive.</p><p class="you">Video · chapter 2</p></div></div>
      <div class="step"><span class="n">04</span><div><h3>New chat → + → Connectors</h3>
        <p>Check Google Drive and GitHub are both ticked for that chat.</p><p class="you">Video · chapter 3</p></div></div>
      <div class="step"><span class="n">05</span><div><h3>Paste the Day-one prompt</h3>
        <p>With the brand's name and the folder link filled in. It clones the tools, opens the folder, reads the queue and tells you what is open. When it ends with <i>"Set up for &lt;brand&gt; — N briefs open"</i>, you are done.</p><p class="you">Video · chapters 4–5 · the prompt is below</p></div></div>
    </div>
  </section>

  <section id="loop">
    <p class="eyebrow">02 — every session</p>
    <h2>The loop</h2>
    <p class="lede">One prompt, pasted at the start of every session. It stops and shows you at every
      decision — you decide, it does the work.</p>
    <div class="steps">
      <div class="step"><span class="n">01</span><div><h3>Sync</h3><p>It pulls the tools for updates and reads the live queue from Drive. Never skipped: a brief made from yesterday's tools is the one that gets sent back.</p></div></div>
      <div class="step"><span class="n">02</span><div><h3>Pick</h3><p>The brief you name, or the newest open one. It claims it in <code>briefs/claims/</code> so nobody else takes it.</p></div></div>
      <div class="step"><span class="n">03</span><div><h3>Lay it out</h3><p>Downloads the package and shows you everything: the scenes with their clips and voices (or the image drafts), the intended cut, what is locked, the known issues, the loop.</p><p class="you">Video · chapters 6 and 9</p></div></div>
      <div class="step"><span class="n">04</span><div><h3>Review</h3><p>Same person, same wardrobe, same product, slop, sound, words, anything odd — one table: KEEP / FIX AT CUT / REROLL. Then three to five ideas inside the brief's own loop.</p><p class="you">You decide what gets rerolled · video · chapter 7</p></div></div>
      <div class="step"><span class="n">05</span><div><h3>The asks</h3><p>The extras the brief wants — scroll stoppers, headlines, variations, extra scenes, formats, styles — made in Higgsfield from the same cast and product references.</p><p class="you">You approve each one</p></div></div>
      <div class="step"><span class="n">06</span><div><h3>The edit</h3><p>Video: everything packed into <code>&lt;brief&gt;--edit</code> with a cut sheet; you take it into Premiere or CapCut. Statics: the finals into <code>&lt;brief&gt;--finals</code>.</p></div></div>
      <div class="step"><span class="n">07</span><div><h3>Deliver</h3><p>Finished files to <code>briefs/delivered/&lt;brief&gt;/</code> on Drive, named <code>&lt;brief&gt;--&lt;what&gt;--v1</code>, with a short <code>DELIVERED.md</code>. The queue updates itself within the hour.</p></div></div>
    </div>
  </section>

  <section id="prompts">
    <p class="eyebrow">03 — the prompts</p>
    <h2>Two prompts,<br>that's the job</h2>
    <p class="lede">Type the brand's folder name and paste its Drive link once; the prompts fill them in. Copy, paste into a new
      Supercomputer chat, go.</p>
    <div class="brandin"><label for="brand">Brand folder name</label><input id="brand" placeholder="e.g. the folder's name" autocomplete="off">
      <label for="folder">Brand folder link</label><input id="folder" placeholder="https://drive.google.com/drive/folders/…" autocomplete="off" style="width:min(420px,100%)"></div>

    <div class="panel">
      <h3>Day one</h3>
      <div class="when">Paste once · after Drive and GitHub are connected</div>
      <pre class="prompt" data-src="dayone">{html.escape(day_one)}</pre>
      <button class="copy" data-for="dayone">Copy the Day-one prompt</button>
    </div>

    <div class="panel">
      <h3>Pull briefs</h3>
      <div class="when">Paste at the start of every session · name a brief or leave "newest open"</div>
      <pre class="prompt" data-src="pull">{html.escape(pull)}</pre>
      <button class="copy" data-for="pull">Copy the Pull-briefs prompt</button>
    </div>
    <div class="note">These are the same files the tools ship: <code>tools/21-editor-onboarding/prompts/</code>. When they change there, they change here.</div>
  </section>

  <section id="queue">
    <p class="eyebrow">04 — the queue</p>
    <h2>What is waiting</h2>
    <p class="lede"><code>briefs/QUEUE.md</code> in each brand folder on Drive. One row per brief: type, status,
      who, bounty, due, package. Rebuilt every hour from the folder — nobody edits it by hand.</p>
    <table class="qtab">
      <tr><th>Status</th><th>It means</th><th>Because</th></tr>
      <tr><td>open</td><td>Nobody has it</td><td>The package is in the folder</td></tr>
      <tr><td>claimed</td><td>Someone is on it</td><td>A file named <code>&lt;brief&gt; — &lt;name&gt;</code> is in <code>briefs/claims/</code></td></tr>
      <tr><td>delivered</td><td>Finished, waiting on the owner</td><td>Files are in <code>briefs/delivered/&lt;brief&gt;/</code></td></tr>
      <tr><td>approved · paid</td><td>The owner's call</td><td>Set by the owner, never by the folder</td></tr>
    </table>
    <div class="note">Bounty and due dates are the owner's. The queue shows them; the folder does not set them.</div>
  </section>

  <section id="asks">
    <p class="eyebrow">05 — the asks</p>
    <h2>Beyond the base cut</h2>
    <p class="lede">Every brief ends with <b>THE ASKS</b> — six lines, each specified or refused with a reason.
      Older briefs without the section get this default menu. Every ask keeps the same cast references,
      product references and wardrobe locks as the base set. No new claims, ever. One ratio: 9:16, with everything that matters inside the 4:5 crop.</p>
    <div class="asks">
      <div class="ask"><div class="k">Scroll stoppers</div><p>Alternative first three seconds, one per hook the brief did not use as the opener.</p><div class="d">default · 3</div></div>
      <div class="ask"><div class="k">Headlines</div><p>Opener-card lines under eight words, from the brief's own hooks, loop and offer.</p><div class="d">default · 5</div></div>
      <div class="ask"><div class="k">Variations</div><p>Alternate takes, same line, different framing: the opening and the offer scene.</p><div class="d">default · 1 each</div></div>
      <div class="ask"><div class="k">Extra scenes</div><p>Inserts for any beat the post list or known issues leave uncovered.</p><div class="d">default · one per uncovered beat</div></div>
      <div class="ask"><div class="k">Formats</div><p>9:16 only — nothing at 4:5 or 1:1. A 15-second cutdown map, and every face, product and word inside the centred 4:5 crop.</p><div class="d">default · one ratio</div></div>
      <div class="ask"><div class="k">Styles</div><p>A visual restyle of the same film — only when the brief names one.</p><div class="d">default · none</div></div>
    </div>
  </section>

  <section id="rules">
    <div class="two">
      <div>
        <p class="eyebrow">06 — the rules that never move</p>
        <ul class="rules">
          <li><b>Nothing invented</b>Not a product detail, not a claim, not a person. If the brief does not say it, the answer is "not in the brief" — ask.</li>
          <li><b>Every face and product carries its reference</b>A person or product generated without their reference is a reroll, not a delivery.</li>
          <li><b>Never write into the source package</b>Deliveries go to <code>delivered/</code>. The package stays as it arrived.</li>
          <li><b>Sync first, every session</b>Stale tools or a stale queue are how a brief gets sent back.</li>
          <li><b>When a door fails, say which one</b>Drive, GitHub, Higgsfield — one line. Never a silent workaround.</li>
        </ul>
      </div>
      <div>
        <p class="eyebrow">07 — when it goes wrong</p>
        <ul class="rules">
          <li><b>"Something went wrong" opening the brand folder</b>Supercomputer picked the wrong folder or cached an old one. Paste the folder's Drive link directly into the chat.</li>
          <li><b>No credits · "no chats"</b>You are in the wrong Higgsfield workspace. Switch to the shared one (top-left) and refresh.</li>
          <li><b>It found the wrong briefs folder</b>Two folders share the name. Give it the path or the link — it must not guess.</li>
          <li><b>A delivered brief still shows open</b>The files are not in <code>delivered/&lt;brief&gt;/</code> under the exact brief name from the queue.</li>
          <li><b>"No updates" but the way of working changed</b>The clone is stale. Say: <i>clone https://github.com/daemnapps/prizm-labs again, fresh</i>.</li>
        </ul>
      </div>
    </div>
  </section>

  <footer>
    <span>PRIZM LABS</span>
    <span><a href="/onboarding-desk.html">Onboarding someone? The desk</a> · <a href="/how-it-works.html">The tools</a> · <a href="https://github.com/daemnapps/prizm-labs" target="_blank" rel="noopener">Repo</a></span>
  </footer>
</div>

<script>
(function(){{
  var input=document.getElementById('brand');
  var folder=document.getElementById('folder');
  var pres=[].slice.call(document.querySelectorAll('pre.prompt'));
  var raw={{}};
  pres.forEach(function(p){{ raw[p.dataset.src]=p.textContent; }});
  function esc(s){{ return s.replace(/[&<>]/g,function(c){{return {{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c];}}); }}
  function fill(t,asHtml){{
    var b=(input.value||'').trim(), f=(folder.value||'').trim();
    var wrap=function(v,ph){{ return asHtml?('<mark>'+esc(v||ph)+'</mark>'):(v||ph); }};
    t=asHtml?esc(t):t;
    return t.replace(/\\{{BRAND\\}}/g, wrap(b,'{{BRAND}}')).replace(/\\{{FOLDER LINK\\}}/g, wrap(f,'{{FOLDER LINK}}'));
  }}
  function paint(){{ pres.forEach(function(p){{ p.innerHTML=fill(raw[p.dataset.src],true); }}); }}
  function text(key){{ return fill(raw[key],false); }}
  try{{ input.value=localStorage.getItem('onboarding-brand')||''; folder.value=localStorage.getItem('onboarding-folder')||''; }}catch(e){{}}
  input.addEventListener('input',function(){{ paint(); try{{localStorage.setItem('onboarding-brand',input.value);}}catch(e){{}} }});
  folder.addEventListener('input',function(){{ paint(); try{{localStorage.setItem('onboarding-folder',folder.value);}}catch(e){{}} }});
  paint();
  [].slice.call(document.querySelectorAll('.copy')).forEach(function(btn){{
    btn.addEventListener('click',function(){{
      var t=text(btn.dataset.for);
      var done=function(){{ var was=btn.textContent; btn.textContent='Copied'; btn.classList.add('done'); setTimeout(function(){{btn.textContent=was;btn.classList.remove('done');}},1800); }};
      if(navigator.clipboard&&navigator.clipboard.writeText){{ navigator.clipboard.writeText(t).then(done,function(){{fallback(t);done();}}); }}
      else {{ fallback(t); done(); }}
    }});
  }});
  function fallback(t){{ var ta=document.createElement('textarea'); ta.value=t; document.body.appendChild(ta); ta.select(); try{{document.execCommand('copy');}}catch(e){{}} document.body.removeChild(ta); }}
}})();
</script>
</html>
"""

OUT.write_text(page)
print(f"wrote {OUT.relative_to(REPO)} — {len(page):,} bytes, {len(chaps)} chapters")

# ── the desk: the onboarder's page, from DESK.md ─────────────────────────
desk_src = (TOOL / "DESK.md").read_text()
msg = re.search(r"```message\n(.*?)```", desk_src, re.S).group(1).strip()

desk = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#EDE0DC">
<meta name="description" content="For whoever brings editors in: open the folders by link once per brand, send one message per editor, and what to check in their first session and first delivery.">
<title>Onboarding desk — PRIZM LABS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Jost:wght@200;300;400&family=Archivo:wght@400;500&family=IBM+Plex+Mono:wght@400&display=swap">
<link rel="stylesheet" href="studio.css">
<style>
.hero{{padding-top:120px;max-width:760px}}
.steps{{display:grid;gap:1px;background:var(--line);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-top:30px}}
.step{{background:color-mix(in srgb,var(--halo) 72%,transparent);padding:22px 24px;display:grid;grid-template-columns:54px 1fr;gap:20px;align-items:start}}
.step .n{{font-family:var(--mono);font-size:10px;letter-spacing:.16em;color:var(--ink3);padding-top:4px}}
.step h3{{margin:0 0 6px}}
.step p{{font-size:13.5px;margin:0;max-width:64ch}}
.qtab{{border-collapse:collapse;width:100%;margin-top:26px;font-size:13.5px}}
.qtab th{{text-align:left;font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink3);font-weight:400;padding:0 14px 12px 0;border-bottom:1px solid var(--line)}}
.qtab td{{padding:12px 14px 12px 0;border-bottom:1px solid var(--line);vertical-align:top;color:var(--ink2)}}
.qtab td:first-child{{color:var(--ink);white-space:nowrap}}
.qtab td b{{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;font-weight:400}}
.panel{{border:1px solid var(--line);border-radius:14px;padding:26px 26px 22px;background:color-mix(in srgb,var(--halo) 66%,transparent);margin-top:26px}}
.fill{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:0 0 16px}}
.fill label{{display:block;font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);margin-bottom:6px}}
.fill input{{width:100%;background:var(--halo);border:1px solid var(--line);color:var(--ink);font-family:var(--mono);font-size:13px;padding:9px 12px;border-radius:8px}}
pre.msg{{font-family:var(--mono);font-size:12.5px;line-height:1.7;white-space:pre-wrap;word-break:break-word;background:var(--halo);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin:0 0 14px;color:var(--ink2)}}
pre.msg mark{{background:color-mix(in srgb,#E9C7D6 70%,transparent);color:var(--ink);padding:0 3px;border-radius:3px}}
.copy{{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;background:var(--ink);color:var(--halo);border:1px solid var(--ink);border-radius:999px;padding:12px 22px;cursor:pointer}}
.copy:hover,.copy.done{{background:transparent;color:var(--ink)}}
.rules{{list-style:none;padding:0;margin:0}}
.rules li{{border-top:1px solid var(--line);padding:16px 0;color:var(--ink2);font-size:14.5px}}
.rules li b{{display:block;font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);margin-bottom:6px;font-weight:400}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:56px}}
@media(max-width:860px){{.two{{grid-template-columns:1fr;gap:28px}}}}
</style>

<nav>
  <a class="mark" href="/">PRIZM LABS</a>
  <span class="sp"></span>
  <a class="link" href="/how-it-works.html">The tools</a>
  <a class="link" href="/swipes/">Swipe library</a>
  <a class="link" href="/onboarding.html">Onboarding</a>
  <a class="link" href="/onboarding-desk.html" aria-current="page">Desk</a>
  <a class="link" href="https://github.com/daemnapps/prizm-labs" target="_blank" rel="noopener">Repo</a>
</nav>

<div class="wrap">
  <div class="hero">
    <p class="eyebrow">The onboarding desk · for whoever brings editors in</p>
    <h1>Ten minutes<br>per editor.</h1>
    <p class="lede">The editor's side is <a href="/onboarding.html">the onboarding page</a>. This is yours: open the folders by link once per brand, send one message per editor, then watch two things — their first session and their first delivery.</p>
  </div>

  <section id="brand">
    <p class="eyebrow">01 — once per brand</p>
    <h2>Open the folders<br>by link</h2>
    <p class="lede">No invitations. The folder opens for anyone with the link, so an editor never waits on an account being added.</p>
    <table class="qtab">
      <tr><th>Folder</th><th>Share → General access</th><th>Why</th></tr>
      <tr><td>The brand folder</td><td><b>Anyone with the link · Viewer</b></td><td>They read products, cast, briefs</td></tr>
      <tr><td>Its <code>briefs/</code> folder</td><td><b>Anyone with the link · Editor</b></td><td>They claim in <code>claims/</code> and deliver into <code>delivered/</code></td></tr>
      <tr><td><code>Shared Assets / onboarding</code></td><td><b>Anyone with the link · Viewer</b></td><td>The walkthrough video plays on the page</td></tr>
    </table>
    <div class="note">Greyed out? The shared drive needs "allow sharing with non-members" on first — Manage shared drive → Settings. Keep the brand folder link handy; every editor gets it.</div>
  </section>

  <section id="message">
    <p class="eyebrow">02 — per editor</p>
    <h2>One message</h2>
    <p class="lede">Fill the three boxes, copy, send. That is the whole onboarding — the page does the rest.</p>
    <div class="panel">
      <div class="fill">
        <div><label for="name">Their name</label><input id="name" autocomplete="off"></div>
        <div><label for="brand">Brand</label><input id="brand" autocomplete="off"></div>
        <div><label for="folder">Brand folder link</label><input id="folder" placeholder="https://drive.google.com/drive/folders/…" autocomplete="off"></div>
      </div>
      <pre class="msg" id="msg">{html.escape(msg)}</pre>
      <button class="copy" id="copy">Copy the message</button>
    </div>
  </section>

  <section id="watch">
    <div class="two">
      <div>
        <p class="eyebrow">03 — their first session</p>
        <ul class="rules">
          <li><b>They connected both</b>Google Drive and GitHub, in Supercomputer's Connectors. The Day-one prompt stops at step 1 if either is missing.</li>
          <li><b>The shortcut is in their own Drive</b>Supercomputer only sees My Drive; the link alone is not enough — step 3 on the page.</li>
          <li><b>The queue showed</b>"Set up for &lt;brand&gt; — N briefs open" is the finish line. Wrong folder? Check they filled the second box — the link goes straight into the prompt.</li>
          <li><b>A claim file appeared</b><code>briefs/claims/&lt;brief&gt; — &lt;their name&gt;</code> in the brand folder. The queue flips to <i>claimed</i> on the hour.</li>
        </ul>
      </div>
      <div>
        <p class="eyebrow">04 — their first delivery</p>
        <ul class="rules">
          <li><b>Files in the right place</b><code>briefs/delivered/&lt;brief&gt;/</code>, named <code>&lt;brief&gt;--&lt;what&gt;--v1</code>.</li>
          <li><b>A DELIVERED.md beside them</b>What was made, what was rerolled, what is still open for the owner.</li>
          <li><b>One ratio</b>Everything at 9:16, faces and product and words inside the 4:5 crop. Nothing at 4:5 or 1:1.</li>
          <li><b>The asks present</b>Stoppers, headlines, variations, the cutdown map — or a line saying which were refused and why.</li>
        </ul>
      </div>
    </div>
  </section>

  <section id="where">
    <p class="eyebrow">05 — where to look</p>
    <table class="qtab">
      <tr><th>For</th><th>Where</th></tr>
      <tr><td>What is open, claimed, delivered</td><td><code>briefs/QUEUE.md</code> in the brand folder — rebuilt hourly</td></tr>
      <tr><td>What they delivered</td><td><code>briefs/delivered/&lt;brief&gt;/</code></td></tr>
      <tr><td>Bounties and due dates</td><td>You don't edit the queue. Tell the owner "&lt;brief&gt; $&lt;amount&gt; by &lt;date&gt;" — it shows within the hour.</td></tr>
      <tr><td>What they are stuck on</td><td>Ask for the last line Supercomputer said — it names the door that failed.</td></tr>
      <tr><td>The way we work, verbatim</td><td><a href="https://github.com/daemnapps/prizm-labs/tree/main/tools/21-editor-onboarding" target="_blank" rel="noopener">tools/21-editor-onboarding</a> — SOP.md and the prompts</td></tr>
    </table>
  </section>

  <footer>
    <span>PRIZM LABS</span>
    <span><a href="/onboarding.html">Onboarding</a> · <a href="https://github.com/daemnapps/prizm-labs" target="_blank" rel="noopener">Repo</a></span>
  </footer>
</div>

<script>
(function(){{
  var raw=document.getElementById('msg').textContent, pre=document.getElementById('msg');
  var f={{NAME:document.getElementById('name'),BRAND:document.getElementById('brand'),'FOLDER LINK':document.getElementById('folder')}};
  function esc(s){{ return s.replace(/[&<>]/g,function(c){{return {{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c];}}); }}
  function fill(asHtml){{
    var t=asHtml?esc(raw):raw;
    Object.keys(f).forEach(function(k){{
      var v=(f[k].value||'').trim(), ph='{{'+k+'}}';
      t=t.split(ph).join(asHtml?('<mark>'+esc(v||ph)+'</mark>'):(v||ph));
    }});
    return t;
  }}
  function paint(){{ pre.innerHTML=fill(true); }}
  Object.keys(f).forEach(function(k){{
    try{{ f[k].value=localStorage.getItem('desk-'+k)||''; }}catch(e){{}}
    f[k].addEventListener('input',function(){{ paint(); try{{localStorage.setItem('desk-'+k,f[k].value);}}catch(e){{}} }});
  }});
  paint();
  var btn=document.getElementById('copy');
  btn.addEventListener('click',function(){{
    var t=fill(false);
    var done=function(){{ btn.textContent='Copied'; btn.classList.add('done'); setTimeout(function(){{btn.textContent='Copy the message';btn.classList.remove('done');}},1800); }};
    if(navigator.clipboard&&navigator.clipboard.writeText){{ navigator.clipboard.writeText(t).then(done,function(){{fb(t);done();}}); }} else {{ fb(t); done(); }}
  }});
  function fb(t){{ var ta=document.createElement('textarea'); ta.value=t; document.body.appendChild(ta); ta.select(); try{{document.execCommand('copy');}}catch(e){{}} document.body.removeChild(ta); }}
}})();
</script>
</html>
"""
(REPO / "docs" / "onboarding-desk.html").write_text(desk)
print(f"wrote docs/onboarding-desk.html — {len(desk):,} bytes")
