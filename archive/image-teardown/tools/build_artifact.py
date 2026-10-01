#!/usr/bin/env python3
"""Render one run of the image teardown into a single artifact page + md mirror.

    python3 build_artifact.py runs/<run-folder>

Re-run after any prompt or output change. Damon reviews in HTML; the team
reads the .md files this page is built from.
"""
import base64, html, re, sys
from pathlib import Path

# ---------------------------------------------------------------- markdown

def inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\*\w])\*([^\*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([A-Z][A-Z ]*?):", r"<span class='mark'>[\1:</span>", s)
    return s


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], cells[2:]
    out = ["<div class='scroll'><table><thead><tr>"]
    out += [f"<th>{inline(c)}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def md(text):
    lines = [l.rstrip() for l in text.split("\n")]
    out, i, n = [], 0, len(lines)
    listing = None  # 'ul' | 'ol' | None

    def close():
        nonlocal listing
        if listing:
            out.append(f"</{listing}>")
            listing = None

    while i < n:
        l = lines[i]
        s = l.strip()
        if not s:
            close(); i += 1; continue
        if s.startswith("<!--"):
            i += 1; continue
        if s.startswith("```"):
            close(); i += 1; buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append("<pre class='block'>" + html.escape("\n".join(buf)) + "</pre>")
            continue
        if s in ("***", "---", "___"):
            close(); out.append("<hr />"); i += 1; continue
        if s.startswith("|") and i + 1 < n and set(lines[i + 1].strip()) <= set("|:- "):
            close(); rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i]); i += 1
            out.append(table(rows)); continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            close()
            lvl = min(len(m.group(1)) + 2, 5)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>"); i += 1; continue
        m = re.match(r"^\*\*(.+?)\*\*:?$", s)
        if m and len(s) < 110:
            close(); out.append(f"<h4>{inline(m.group(1))}</h4>"); i += 1; continue
        m = re.match(r"^\s*[\*\-]\s+(.*)$", l)
        if m:
            if listing != "ul":
                close(); out.append("<ul>"); listing = "ul"
            out.append(f"<li>{inline(m.group(1))}</li>"); i += 1; continue
        m = re.match(r"^\s*\d+\.\s+(.*)$", l)
        if m:
            if listing != "ol":
                close(); out.append("<ol>"); listing = "ol"
            out.append(f"<li>{inline(m.group(1))}</li>"); i += 1; continue
        close()
        out.append(f"<p>{inline(s)}</p>"); i += 1
    close()
    return "\n".join(out)


def verbatim(text):
    """Prompts render as-is — they are the product, not prose about it."""
    t = html.escape(text.strip())
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
    t = re.sub(r"`([^`\n]+)`", r"<i>\1</i>", t)
    return t


def strip_header(t):
    return re.sub(r"^<!--.*?-->\s*", "", t, flags=re.S)


def provenance(t):
    m = re.match(r"^<!--(.*?)-->", t, flags=re.S)
    return m.group(1).strip() if m else ""

# ---------------------------------------------------------------- css

CSS = """
:root{
 --paper:#eef0f2; --surface:#f019;--surface:#f7f8f9; --sunk:#e2e6ea;
 --ink:#15202b; --muted:#5a6672; --line:#c9d1d9; --rule:#a9b4c0;
 --indigo:#2b4c7e; --turmeric:#c2760a; --jade:#5f8a72; --crimson:#9c3b2e;
 --code-bg:#141a21; --code-ink:#d8dee6; --code-key:#e8a33d; --code-var:#7fb3e8;
 --display:"Avenir Next Condensed","Futura","Helvetica Neue",Helvetica,sans-serif;
 --body:Charter,"Iowan Old Style",Georgia,"Times New Roman",serif;
 --data:"SF Mono",Menlo,ui-monospace,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --paper:#10161d; --surface:#161e26; --sunk:#1d2731;
 --ink:#e6ebf0; --muted:#93a1b0; --line:#2c3945; --rule:#3d4d5c;
 --indigo:#7ba7dd; --turmeric:#e5a23f; --jade:#8fc0a0; --crimson:#e08272;
 --code-bg:#0a0e13; --code-ink:#cdd6df;
}}
:root[data-theme="dark"]{
 --paper:#10161d; --surface:#161e26; --sunk:#1d2731;
 --ink:#e6ebf0; --muted:#93a1b0; --line:#2c3945; --rule:#3d4d5c;
 --indigo:#7ba7dd; --turmeric:#e5a23f; --jade:#8fc0a0; --crimson:#e08272;
 --code-bg:#0a0e13; --code-ink:#cdd6df;
}
*{box-sizing:border-box;}
body{background:var(--paper);color:var(--ink);font-family:var(--body);
 font-size:16.5px;line-height:1.62;margin:0;padding:0 1.1rem 6rem;
 -webkit-font-smoothing:antialiased;}
.wrap{max-width:62rem;margin:0 auto;}
h1,h2,h3,h4,h5,.disp{font-family:var(--display);text-wrap:balance;}
h1{font-size:clamp(2.4rem,6vw,3.9rem);font-weight:700;letter-spacing:.005em;
 line-height:.98;text-transform:uppercase;margin:.6rem 0 0;}
h2{font-size:clamp(1.5rem,3.2vw,2.1rem);font-weight:700;text-transform:uppercase;
 letter-spacing:.01em;line-height:1.05;margin:0;}
h3{font-size:1.18rem;font-weight:700;margin:2rem 0 .5rem;letter-spacing:.01em;}
h4{font-size:.74rem;font-weight:700;letter-spacing:.13em;text-transform:uppercase;
 color:var(--indigo);margin:1.7rem 0 .35rem;font-family:var(--display);}
h5{font-size:.95rem;font-weight:700;margin:1.2rem 0 .3rem;}
p{margin:0 0 .85rem;}
ul,ol{margin:.2rem 0 1rem;padding-left:1.3rem;}
li{margin:.25rem 0;}
hr{border:0;border-top:1px solid var(--line);margin:1.6rem 0;}
a{color:var(--indigo);}
code{font-family:var(--data);font-size:.82em;background:var(--sunk);
 padding:.1em .34em;border-radius:2px;}
.mark{font-family:var(--data);color:var(--crimson);font-size:.86em;}

header{padding-top:4rem;border-bottom:2px solid var(--ink);padding-bottom:1.6rem;}
.kicker{font-family:var(--data);font-size:.7rem;letter-spacing:.2em;
 text-transform:uppercase;color:var(--turmeric);}
.stand{font-size:1.12rem;color:var(--muted);max-width:38rem;margin-top:1.1rem;}
.facts{display:flex;flex-wrap:wrap;gap:0 2.2rem;margin-top:1.4rem;
 font-family:var(--data);font-size:.71rem;letter-spacing:.06em;
 text-transform:uppercase;color:var(--muted);}
.facts b{color:var(--ink);font-weight:600;}

nav{position:sticky;top:0;z-index:9;background:var(--paper);
 border-bottom:1px solid var(--line);padding:.55rem 0;margin-bottom:.5rem;
 display:flex;gap:.35rem;flex-wrap:wrap;}
nav a{font-family:var(--data);font-size:.67rem;letter-spacing:.09em;
 text-transform:uppercase;text-decoration:none;color:var(--muted);
 border:1px solid var(--line);padding:.28rem .5rem;background:var(--surface);}
nav a:hover,nav a:focus-visible{color:var(--ink);border-color:var(--rule);}

section{margin-top:3.6rem;scroll-margin-top:3.6rem;}
.head{display:flex;align-items:baseline;gap:1rem;flex-wrap:wrap;
 border-top:3px solid var(--indigo);padding-top:.7rem;}
.num{font-family:var(--data);font-size:.7rem;font-weight:700;letter-spacing:.16em;
 color:var(--turmeric);text-transform:uppercase;}
.note{font-size:1rem;color:var(--muted);margin:.7rem 0 0;max-width:40rem;}

.card{background:var(--surface);border:1px solid var(--line);
 padding:1.1rem 1.3rem;margin-top:1.2rem;}
.card>*:first-child{margin-top:0;}
.card>*:last-child{margin-bottom:0;}

.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-top:1.4rem;}
@media (max-width:760px){.gallery{grid-template-columns:1fr;}}
figure{margin:0;background:var(--surface);border:1px solid var(--line);}
figure img{display:block;width:100%;height:auto;}
figcaption{padding:.6rem .75rem .75rem;font-family:var(--data);font-size:.68rem;
 line-height:1.5;color:var(--muted);border-top:1px solid var(--line);}
figcaption b{display:block;color:var(--ink);font-size:.72rem;letter-spacing:.08em;
 text-transform:uppercase;margin-bottom:.25rem;}

.scroll{overflow-x:auto;margin:.9rem 0 1.2rem;border:1px solid var(--line);}
table{border-collapse:collapse;width:100%;font-family:var(--display);
 font-size:.84rem;font-variant-numeric:tabular-nums;background:var(--surface);}
th{text-align:left;background:var(--sunk);font-weight:700;font-size:.7rem;
 letter-spacing:.08em;text-transform:uppercase;padding:.5rem .7rem;
 border-bottom:1px solid var(--rule);white-space:nowrap;}
td{padding:.5rem .7rem;border-bottom:1px solid var(--line);vertical-align:top;}
tr:last-child td{border-bottom:0;}

pre{background:var(--code-bg);color:var(--code-ink);font-family:var(--data);
 font-size:.735rem;line-height:1.72;padding:1.1rem 1.25rem;overflow:auto;
 white-space:pre-wrap;word-break:break-word;border-left:3px solid var(--turmeric);
 margin:.9rem 0 0;max-height:34rem;}
pre b{color:var(--code-key);font-weight:600;}
pre i{color:var(--code-var);font-style:normal;}
pre.block{max-height:none;border-left-color:var(--rule);font-size:.72rem;}

details{border:1px solid var(--line);background:var(--surface);margin-top:.9rem;}
summary{font-family:var(--display);font-size:.8rem;font-weight:700;
 letter-spacing:.09em;text-transform:uppercase;padding:.65rem .9rem;cursor:pointer;
 color:var(--indigo);}
summary:hover{background:var(--sunk);}
details[open] summary{border-bottom:1px solid var(--line);}
.inner{padding:.4rem 1.3rem 1.3rem;}
.inner>*:first-child{margin-top:.8rem;}

.prov{font-family:var(--data);font-size:.63rem;color:var(--muted);
 letter-spacing:.04em;margin-top:.55rem;word-break:break-word;}

footer{margin-top:5rem;border-top:2px solid var(--ink);padding-top:1.1rem;
 font-family:var(--data);font-size:.68rem;line-height:1.8;color:var(--muted);
 letter-spacing:.04em;}
"""

# ---------------------------------------------------------------- page


def img_tag(p):
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"<img src='data:image/jpeg;base64,{b64}' alt='{html.escape(p.stem)}' />"


def main():
    run = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    out_dir, web, prompts = run / "out", run / "assets" / "web", run.parent.parent / "prompts"
    read = lambda p: Path(p).read_text()

    doctrine = read(out_dir / "00-video-doctrine.md")
    teardowns = [(t, read(out_dir / f"01-teardown-ad-{n}.md")) for n, t in
                 [("01", "Ad 01 — editorial, 1:1"),
                  ("02", "Ad 02 — direct response, 1:1"),
                  ("03", "Ad 03 — direct response, 9:16")]]
    deltas = read(run.parent.parent / "STAGE-DELTAS.md")

    figs = [
        ("ad-01_thai-secret-editorial-1x1.jpg", "Ad 01",
         "1080×1086 · 1:1 · editorial layout · cream ground · no offer block"),
        ("ad-02_it-works-too-well-dark-1x1.jpg", "Ad 02",
         "1078×1090 · 1:1 · direct response · black ground · offer + guarantee"),
        ("ad-03_it-works-too-well-dark-9x16.jpg", "Ad 03",
         "610×1088 · 9:16 · same execution as Ad 02, recut for story"),
    ]

    P = []
    A = P.append
    A("<title>Static Ad Teardown Lane</title>")
    A(f"<style>{CSS}</style>")
    A("<div class='wrap'>")

    A("<header>"
      "<div class='kicker'>content machine · image teardown · v1</div>"
      "<h1>Static ad<br />teardown lane</h1>"
      "<p class='stand'>The video chain, rebuilt for a single frame. One "
      "screencast of the ad account read for its doctrine, three live statics "
      "torn down against a new stage-1 prompt, and the map of what the rest of "
      "the chain has to change.</p>"
      "<div class='facts'>"
      "<span>Run <b>2026-08-19 · <brand>-thai-secret</b></span>"
      "<span>Model <b>gemini-3.1-pro-preview</b></span>"
      "<span>Assets <b>1 video · 3 statics</b></span>"
      "<span>Prompts <b>8</b></span>"
      "</div></header>")

    A("<nav>"
      "<a href='#doctrine'>01 Doctrine</a>"
      "<a href='#set'>02 The set</a>"
      "<a href='#teardowns'>03 Teardowns</a>"
      "<a href='#findings'>04 Findings</a>"
      "<a href='#run'>05 The chain run</a>"
      "<a href='#prompts'>06 Prompts</a>"
      "<a href='#chain'>07 Chain deltas</a>"
      "</nav>")

    # 1 — doctrine
    A("<section id='doctrine'>"
      "<div class='head'><span class='num'>01</span>"
      "<h2>What the video taught</h2></div>"
      "<p class='note'>Your screencast, read by Gemini for operating doctrine "
      "rather than as an ad — every rule quoted with the timestamp it was said "
      "at, and every number transcribed from the dashboard as displayed.</p>")
    A(f"<div class='card'>{md(strip_header(doctrine))}</div>")
    A(f"<p class='prov'>{html.escape(provenance(doctrine))}</p>")
    A("</section>")

    # 2 — the set
    A("<section id='set'>"
      "<div class='head'><span class='num'>02</span>"
      "<h2>The three statics</h2></div>"
      "<p class='note'>The assets fed to stage 1, exactly as supplied. Two are "
      "one execution cut for two placements; one is a separate execution of the "
      "same concept.</p>"
      "<div class='gallery'>")
    for fn, name, cap in figs:
        p = web / fn
        if p.exists():
            A(f"<figure>{img_tag(p)}<figcaption><b>{name}</b>{cap}</figcaption></figure>")
    A("</div></section>")

    # 3 — teardowns
    A("<section id='teardowns'>"
      "<div class='head'><span class='num'>03</span>"
      "<h2>Stage 1 · the teardowns</h2></div>"
      "<p class='note'>One reproduction spec per ad: frame spec, subject and "
      "setting, the zone table with every position as a percentage of frame, "
      "the reading path, the scroll-stop mechanism, the psychology, the index. "
      "Observation only — nothing here judges the ad.</p>")
    for title, body in teardowns:
        A(f"<details><summary>{html.escape(title)}</summary><div class='inner'>"
          f"{md(strip_header(body))}"
          f"<p class='prov'>{html.escape(provenance(body))}</p>"
          "</div></details>")
    A("</section>")

    # 5 — prompts
    A("<section id='prompts'>"
      "<div class='head'><span class='num'>06</span>"
      "<h2>The prompts, verbatim</h2></div>"
      "<p class='note'>Every prompt written this run, as it actually ran. Read "
      "them as rules you can strike or rewrite — a rule you did not see is a "
      "rule you cannot correct. For the full-width reading view, open the "
      "<a href='https://claude.ai/code/artifact/daa7603f-efcd-4f0c-a533-26492bf3ceab'>"
      "prompt library</a>.</p>")
    for label, fn in [
            ("Stage 1 · image teardown", "stage1-image-teardown-v1-damon.md"),
            ("Stage 1C · clone spec", "stage1c-image-clone-spec-v1-damon.md"),
            ("Stage 2 · replication spec", "stage2-image-replication-v1-damon.md"),
            ("Stage 3 · injection", "stage3-image-injection-v1-damon.md"),
            ("Stage 4a · placement", "stage4a-image-placement-v1-damon.md"),
            ("Stage 4b · headlines", "stage4b-image-hook-v1-damon.md"),
            ("Stage 4c · support copy", "stage4c-image-support-v1-damon.md"),
            ("Stage 4d · offer block", "stage4d-image-offer-v1-damon.md"),
            ("Stage 5 · generation spec", "stage5-image-generation-v2-damon.md"),
            ("Video doctrine extract", "video-doctrine-extract-v1.md")]:
        f = prompts / fn
        if not f.exists():
            continue
        A(f"<details><summary>{label} — {fn}</summary><div class='inner'>"
          f"<pre>{verbatim(f.read_text())}</pre></div></details>")
    A("</section>")

    # 6 — the chain run
    RUN_STAGES = [
        ("04-stage2-replication-spec.md", "Stage 2 · replication spec",
         "The frame abstracted — brand stripped out, every element made "
         "injectable, positions kept as percentages."),
        ("05-stage3-injection.md", "Stage 3 · injection",
         "<brand> substituted into the frame, zone for zone. Nothing rewritten, "
         "every missing fact left as a slot."),
        ("06-stage4a-placement.md", "Stage 4a · placement",
         "Lane, headline zone, ratios to build, awareness, the frame budget, "
         "and the device check against the objection bank."),
        ("07-stage4b-hooks.md", "Stage 4b · headlines",
         "Control plus five variations, each with its image concept and the "
         "verbatim it came from. All ship to test."),
        ("08-stage4c-support.md", "Stage 4c · support copy",
         "The four moves, each through the earns-its-way-in gate, priced in "
         "words against the frame budget."),
        ("09-stage4d-offer.md", "Stage 4d · offer block",
         "The objection line and the offer block, with the guarantee quoted "
         "exactly and the ratio check."),
        ("10-stage5-generation-spec.md", "Stage 5 · the generation spec",
         "The plate the image model paints, the type layer the compositor "
         "sets, and the runnable job list that produces every file."),
    ]
    live = [(fn, t, n) for fn, t, n in RUN_STAGES if (out_dir / fn).exists()]
    if live:
        A("<section id='run'>"
          "<div class='head'><span class='num'>05</span>"
          "<h2>The chain, run on <brand></h2></div>"
          "<p class='note'>Stage 1's teardown of Ad 02 carried through the "
          "whole chain against the live <brand> brand files — avatar, language "
          "bank, objection bank, product file, offer file, identity anchors. "
          "Every stage's raw output, nothing added.</p>")
        for fn, title, note in live:
            body = read(out_dir / fn)
            A(f"<details><summary>{html.escape(title)}</summary><div class='inner'>"
              f"<p class='note'>{note}</p>{md(strip_header(body))}"
              f"<p class='prov'>{html.escape(provenance(body))}</p>"
              "</div></details>")
        A("</section>")

    # 6 — chain deltas
    A("<section id='chain'>"
      "<div class='head'><span class='num'>07</span>"
      "<h2>What the rest of the chain changes</h2></div>")
    A(f"<div class='card'>{md(deltas)}</div>")
    A("</section>")

    # 7 — findings
    A("<section id='findings'>"
      "<div class='head'><span class='num'>04</span>"
      "<h2>Findings, and what v2 fixes</h2></div>"
      "<p class='note'>Three reads off the ads themselves, three defects in "
      "the prompts written this run, and the one rule that fired perfectly and "
      "should not be touched.</p>")
    A(f"<div class='card'>{md(strip_header(read(out_dir / '03-findings.md')))}</div>")
    A("</section>")

    A("<footer>"
      "Built by <code>build_artifact.py</code> from "
      "<code>content-machine/image-teardown/</code> · outputs and prompts are "
      "markdown files in the repo, this page is the read-through · "
      "run folder <code>runs/2026-08-19-<brand>-thai-secret/</code>"
      "</footer>")
    A("</div>")

    dest = run / "artifact.html"
    dest.write_text("\n".join(P))
    print(f"wrote {dest} — {format(dest.stat().st_size, ',')} bytes")


if __name__ == "__main__":
    main()
