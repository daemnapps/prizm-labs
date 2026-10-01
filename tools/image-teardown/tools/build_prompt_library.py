#!/usr/bin/env python3
"""Render every image-teardown prompt into one page, in chain order.

    python3 build_prompt_library.py

Re-run after ANY prompt change. Damon reviews prompts as an artifact, never as
a file path — a rule he did not see is a rule he cannot correct.
"""
import html, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE / "prompts"

STAGES = [
    ("1", "Teardown", "stage1-image-teardown-v1-damon.md", "a",
     "One static in, one reproduction spec out. Frame spec, subject and "
     "setting, the zone table, the reading path, the psychology, the index. "
     "Observation only — abstraction happens at stage 2.",
     "one image", "the teardown record"),
    ("1C", "Clone spec", "stage1c-image-clone-spec-v1-damon.md", "a",
     "The teardown turned into the two machine-readable blocks that rebuild "
     "the ad exactly: the plate prompt with its accept tests, and the type "
     "layer as JSON. Abstracts nothing.",
     "the teardown record", "plate prompt + type layer"),
    ("2", "Replication spec", "stage2-image-replication-v1-damon.md", "b",
     "The frame abstracted — brand stripped out, every element made "
     "injectable. Counts area and position, never seconds.",
     "the record", "a brand-free spec"),
    ("3", "Injection", "stage3-image-injection-v1-damon.md", "b",
     "Substitution, not rewriting. Our brand in the slots, zone for zone. "
     "Not yet an ad.",
     "record + spec + brand", "the baseline injection"),
    ("4a", "Placement", "stage4a-image-placement-v1-damon.md", "c",
     "Lane, headline zone, the ratios to build, awareness, the frame budget, "
     "the device check. No copy.",
     "baseline + record + spec", "the placement plan"),
    ("4b", "Headlines", "stage4b-image-hook-v1-damon.md", "c",
     "One straight-swipe control plus five variations, each a line and an "
     "image concept, each cited to a verbatim. All ship to test.",
     "plan + banks + ledger", "6 headlines"),
    ("4c", "Support copy", "stage4c-image-support-v1-damon.md", "c",
     "Four moves, each behind the earns-its-way-in gate, priced in words "
     "against the frame budget rather than seconds against a runtime.",
     "plan + headlines + brand", "the frame through the product content"),
    ("4d", "Offer block", "stage4d-image-offer-v1-damon.md", "c",
     "The two pieces of copy no earlier pass writes: the line that answers "
     "the flinch, and the offer block carrying the offer file's exact "
     "guarantee wording. Then the ratio check.",
     "frame so far + banks", "the finished frame"),
    ("5", "Generation spec", "stage5-image-generation-v2-damon.md", "d",
     "The maker is an image model, not a designer. Splits the ad into the "
     "plate the model paints and the type layer a compositor sets, decides "
     "per element which machine renders it, and emits a runnable job list.",
     "stage 4 outputs + brand", "plate prompts + type layer as JSON"),
]

CSS = """
:root{
 --paper:#eef0f2; --surface:#f7f8f9; --sunk:#e2e6ea;
 --ink:#15202b; --muted:#5a6672; --line:#c9d1d9; --rule:#a9b4c0;
 --a:#2b4c7e; --b:#1f6f63; --c:#9c5a12; --d:#7a3b6d; --e:#54607a;
 --code-bg:#141a21; --code-ink:#dbe2ea; --code-key:#f0b45a; --code-var:#84baf0;
 --code-tag:#e88b7a;
 --display:"Avenir Next Condensed","Futura","Helvetica Neue",Helvetica,sans-serif;
 --body:Charter,"Iowan Old Style",Georgia,"Times New Roman",serif;
 --data:"SF Mono",Menlo,ui-monospace,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --paper:#10161d; --surface:#161e26; --sunk:#1d2731;
 --ink:#e6ebf0; --muted:#93a1b0; --line:#2c3945; --rule:#3d4d5c;
 --a:#7ba7dd; --b:#5fb9aa; --c:#e0a44e; --d:#c98ab8; --e:#93a1b0;
 --code-bg:#0a0e13; --code-ink:#d3dbe4;
}}
:root[data-theme="dark"]{
 --paper:#10161d; --surface:#161e26; --sunk:#1d2731;
 --ink:#e6ebf0; --muted:#93a1b0; --line:#2c3945; --rule:#3d4d5c;
 --a:#7ba7dd; --b:#5fb9aa; --c:#e0a44e; --d:#c98ab8; --e:#93a1b0;
 --code-bg:#0a0e13; --code-ink:#d3dbe4;
}
*{box-sizing:border-box;}
body{background:var(--paper);color:var(--ink);font-family:var(--body);
 font-size:16.5px;line-height:1.6;margin:0;padding:0 1.1rem 6rem;
 -webkit-font-smoothing:antialiased;}
.wrap{max-width:64rem;margin:0 auto;}
h1,h2{font-family:var(--display);text-wrap:balance;}
h1{font-size:clamp(2.3rem,5.5vw,3.6rem);font-weight:700;line-height:1;
 text-transform:uppercase;margin:.5rem 0 0;}
h2{font-size:clamp(1.35rem,3vw,1.85rem);font-weight:700;text-transform:uppercase;
 line-height:1.05;margin:0;}
p{margin:0 0 .8rem;}
a{color:var(--a);}
code{font-family:var(--data);font-size:.84em;background:var(--sunk);
 padding:.1em .34em;border-radius:2px;}

header{padding-top:4rem;border-bottom:2px solid var(--ink);padding-bottom:1.5rem;}
.kicker{font-family:var(--data);font-size:.7rem;letter-spacing:.2em;
 text-transform:uppercase;color:var(--c);}
.stand{font-size:1.1rem;color:var(--muted);max-width:37rem;margin-top:1rem;}

.chain{display:flex;flex-wrap:wrap;gap:.3rem;align-items:stretch;margin-top:1.5rem;}
.chain a{flex:1 1 5.4rem;text-decoration:none;background:var(--surface);
 border:1px solid var(--line);border-top:3px solid var(--k);padding:.5rem .55rem;
 display:flex;flex-direction:column;gap:.15rem;min-width:5.4rem;}
.chain a:hover,.chain a:focus-visible{background:var(--sunk);}
.chain .s{font-family:var(--data);font-size:.68rem;font-weight:700;
 letter-spacing:.1em;color:var(--k);}
.chain .n{font-family:var(--display);font-size:.82rem;font-weight:700;
 text-transform:uppercase;color:var(--ink);line-height:1.15;}
.ka{--k:var(--a);}.kb{--k:var(--b);}.kc{--k:var(--c);}.kd{--k:var(--d);}.ke{--k:var(--e);}

section{margin-top:3.2rem;scroll-margin-top:1.5rem;border-top:3px solid var(--k);
 padding-top:.8rem;}
.top{display:flex;align-items:baseline;gap:.9rem;flex-wrap:wrap;}
.badge{font-family:var(--data);font-size:.72rem;font-weight:700;letter-spacing:.14em;
 text-transform:uppercase;color:var(--k);}
.file{margin-left:auto;font-family:var(--data);font-size:.68rem;color:var(--muted);
 word-break:break-all;}
.job{font-size:1rem;color:var(--muted);margin:.65rem 0 0;max-width:42rem;}
.io{display:grid;grid-template-columns:1fr 1fr;gap:.4rem;margin-top:.8rem;}
@media (max-width:620px){.io{grid-template-columns:1fr;}}
.io div{background:var(--surface);border:1px solid var(--line);padding:.45rem .75rem;
 font-size:.9rem;color:var(--muted);}
.io b{display:block;font-family:var(--display);font-size:.64rem;letter-spacing:.12em;
 text-transform:uppercase;color:var(--ink);margin-bottom:.1rem;}

pre{background:var(--code-bg);color:var(--code-ink);font-family:var(--data);
 font-size:.775rem;line-height:1.85;padding:1.4rem 1.5rem;overflow-x:auto;
 white-space:pre-wrap;word-break:break-word;border-left:3px solid var(--k);
 margin:1rem 0 0;}
pre b{color:var(--code-key);font-weight:600;}
pre i{color:var(--code-var);font-style:normal;}
pre u{color:var(--code-tag);text-decoration:none;}

footer{margin-top:5rem;border-top:2px solid var(--ink);padding-top:1rem;
 font-family:var(--data);font-size:.68rem;line-height:1.9;color:var(--muted);}
"""


def render(txt):
    t = html.escape(txt.strip())
    t = re.sub(r"\{([a-z0-9_]+)\}", r"<i>{\1}</i>", t)
    t = re.sub(r"\[([A-Z][A-Z0-9 _…:.-]*?)\]", r"<u>[\1]</u>", t)
    t = re.sub(r"`([^`\n]+)`", r"<u>\1</u>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
    return t


def main():
    live = [s for s in STAGES if (P / s[2]).exists()]
    total = sum(len((P / s[2]).read_text().splitlines()) for s in live)

    out = ["<title>Image Lane Prompt Library</title>",
           f"<style>{CSS}</style>", "<div class='wrap'>",
           "<header><div class='kicker'>content machine · image teardown · v1</div>",
           "<h1>Prompt library</h1>",
           "<p class='stand'>Every prompt in the static-ad chain, in the order "
           "it runs, exactly as it runs. Nothing summarised — a rule you did "
           "not see is a rule you cannot correct.</p>",
           "<div class='chain'>"]
    for sid, name, fn, k, *_ in live:
        anchor = sid.replace("—", "doc").lower()
        out.append(f"<a class='k{k}' href='#s{anchor}'>"
                   f"<span class='s'>{html.escape(sid)}</span>"
                   f"<span class='n'>{html.escape(name)}</span></a>")
    out.append("</div></header>")

    for sid, name, fn, k, job, vin, vout in live:
        f = P / fn
        body = f.read_text()
        lines = len(body.splitlines())
        anchor = sid.replace("—", "doc").lower()
        out += [f"<section class='k{k}' id='s{anchor}'>",
                f"<div class='top'><span class='badge'>Stage {html.escape(sid)}</span>",
                f"<h2>{html.escape(name)}</h2>",
                f"<span class='file'>{fn} · {lines} lines</span></div>",
                f"<p class='job'>{job}</p>",
                f"<div class='io'><div><b>Takes in</b>{vin}</div>"
                f"<div><b>Gives out</b>{vout}</div></div>",
                f"<pre>{render(body)}</pre>", "</section>"]

    out += [f"<footer>{len(live)} prompts · {total} lines · "
            "<code>content-machine/image-teardown/prompts/</code> · "
            "variables documented in <code>image-teardown/VARIABLES.md</code> · "
            "rebuilt by <code>build_prompt_library.py</code> after every "
            "prompt change</footer></div>"]

    dest = HERE / "prompt-library.html"
    dest.write_text("\n".join(out))
    print(f"wrote {dest} — {len(live)} prompts, {total} lines, "
          f"{format(dest.stat().st_size, ',')} bytes")


if __name__ == "__main__":
    main()
