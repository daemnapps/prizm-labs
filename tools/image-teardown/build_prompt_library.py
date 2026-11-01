#!/usr/bin/env python3
"""Render every image-teardown prompt into one page, in chain order.

    python3 build_prompt_library.py

Re-run after ANY prompt change. the owner reviews prompts as an artifact, never as
a file path — a rule he did not see is a rule he cannot correct.
"""
import html, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE / "prompts"
W = "../../image-writing/prompts/"      # steps 3 to 6: the writing station's prompts (2026-10-27)

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
    ("1k", "Culture read", "../../culture/prompts/stage1k-culture-v4-damon.md", "a",
     "What the people looking at the swipe recognize: references, formats, slang, the joke in its words, and since "
     "v5 (2026-10-29) the props that mark its moment and the words printed on things in the scene. The same read for "
     "video and pictures (components/culture).",
     "the teardown record + the post's talk", "out/01k-culture.md"),
    ("2", "Replication spec", "stage2-image-replication-v1-damon.md", "b",
     "The frame abstracted — brand stripped out, every element made "
     "injectable. Counts area and position, never seconds.",
     "the record", "a brand-free spec"),
    ("3C", "Controls reader", "../../creative-controls/prompts/read-controls-v1-damon.md", "b",
     "Reads the swipe on the creative controls before stage 3: its level on "
     "every dial its medium uses, its emotion, its techniques and the one "
     "thing the eye hits first. The same reader scores our finished ads and "
     "every swipe (components/creative-controls).",
     "the swipe picture + the dials", "the swipe's levels"),
    ("3", "Injection", "../../image-writing/prompts/stage3-image-injection-v6-damon.md", "b",
     "Substitution, not rewriting. Our brand in the slots, zone for zone. "
     "Not yet an ad. v4 added THE CREATIVE CONTROLS (every dial, swipe level to "
     "ours). v6 adds section 6, THE SWAPS RECORD: every swap as data with its kind "
     "(cast · product · library · drawn · words), whether the product is in the frame "
     "and where, and whether the words are set on top. Code reads it into "
     "out/swaps.json, and every picture maker works out what goes into the picture "
     "from that file alone.",
     "record + spec + brand + the dials", "the baseline injection"),
    ("3R", "Swaps reader", "../../image-writing/prompts/swaps-reader-v1-damon.md", "b",
     "Backfill only: reads a finished brand step and brief that pre-date the swaps "
     "record and writes the same record from what the text plainly says. A fast "
     "reading model, never a writer: a call the text does not settle comes back "
     "null and the run is listed, not guessed.",
     "the brand step + the brief's picture + the banks", "out/swaps.json"),
    ("4a", "Placement", "../../image-writing/prompts/stage4a-image-placement-v1-damon.md", "c",
     "Lane, headline zone, the ratios to build, awareness, the frame budget, "
     "the device check. No copy.",
     "baseline + record + spec", "the placement plan"),
    ("4b", "Headlines", "../../image-writing/prompts/stage4b-image-hook-v3-damon.md", "c",
     "v3 (2026-10-23): every line written FOR the swapped picture, naming what it shows, reading cold; the control keeps the swipe\'s job, never a word-for-word swap that reads as nonsense. One control plus five variations, each a line and an "
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
    ("5", "Variations", "../../image-writing/prompts/stage4e-image-variations-v3-damon.md", "c",
     "The brief's five variations, as data. The batch is six pictures: the approved one "
     "plus exactly five, each ONE change off it (2026-10-27). v3 writes them as "
     "THE VARIATIONS RECORD, a json block code reads into out/variations.json: id, label, "
     "the words (one per caption zone) and the one picture change, or a new person with "
     "who, age, look and wardrobe. tools/image-edit makes the five from that file "
     "(vary.py --from-brief).",
     "the brand step + its swap list + the headlines", "out/variations.json (5 rows)"),
    ("5G", "Generation spec", "stage5-image-generation-v2-damon.md", "d",
     "The maker is an image model, not a designer. Splits the ad into the "
     "plate the model paints and the type layer a compositor sets, decides "
     "per element which machine renders it, and emits a runnable job list.",
     "stage 4 outputs + brand", "plate prompts + type layer as JSON"),
    ("6", "The brief", "../../image-writing/prompts/stage6-image-brief-v10-damon.md", "d",
     "Everything before anyone builds: the ad in one line, the picture, the "
     "exact words, the offer and the variations. v11 (2026-10-27) lists the five rows "
     "of out/variations.json as one Variations section (the standard brief v2), in place "
     "of the separate headline and picture options. v10 carries the "
     "swaps record in Document Two, copied from stage 3 and never re-decided; the "
     "brief must agree with it (no product anywhere when it says none; words only "
     "in the words section when they are set on top). v9 (2026-10-23) "
     "carries the creative controls into the picture (every dial a visible "
     "direction, closed by a Dials line the picture review checks); v8 "
     "adds THE PICTURE SWAP (keep the swipe's picture, swap its key objects for ours) on top of the owner's look rules: the brand palette only, the product in the "
     "ad's own look, no long dashes on the ad, bodies that fit the line, "
     "native stays native.",
     "stages 1–5 + brand + palette", "the brief, three documents"),
    ("6T", "The standard brief (template)", "../../image-writing/templates/brief-standard-static-v2-damon.md", "d",
     "The one page every static brief fills, bound into step 6 as {brief_standard}. v3 (2026-10-29): section 3 opens "
     "with the concept and the moment's palette, then what the 3D set holds, every prop at its real size, the camera "
     "and the light as facts, the product from its own true-size build.",
     "the brief's facts", "Document One of the brief"),
    ("R", "Real review: words fixed", "../../image-writing/prompts/review-words-v1-damon.md", "e",
     "New 2026-10-27. When the swipe is a real customer review (the owner: \"this is the actual review ... we would not "
     "wanna make anything up\"), this rides on the end of steps 3 to 6 with the review's own words, zone by zone, as "
     "the teardown read them off the card. Step 6 is checked: a review line missing word for word is sent back once, "
     "then held at the copy gate.",
     "the teardown's verbatim words", "the same words, unchanged, on the brief"),
]

# what changed since the version before, shown old next to new (a person reads every prompt change here)
CHANGED_FROM = {W + "stage4e-image-variations-v8-damon.md": W + "stage4e-image-variations-v7-damon.md",   # 2026-10-28: sale ads stay the sale; written off the approved picture
                W + "stage3-image-injection-v15-damon.md": W + "stage3-image-injection-v14-damon.md",
                W + "stage4b-image-hook-v7-damon.md": W + "stage4b-image-hook-v6-damon.md",
                "stage2-image-replication-v2-damon.md": "stage2-image-replication-v1-damon.md",
                W + "stage6-image-brief-v11-damon.md": W + "stage6-image-brief-v10-damon.md",
                W + "review-words-v1-damon.md": None,          # a new prompt: nothing before it
                # 2026-10-29: the creativity tools catch up with the 3D-set picture chain (3D set, print, words on top)
                W + "stage4b-image-hook-v8-damon.md": W + "stage4b-image-hook-v7-damon.md",
                W + "stage4e-image-variations-v9-damon.md": W + "stage4e-image-variations-v8-damon.md",
                W + "stage6-image-brief-v12-damon.md": W + "stage6-image-brief-v11-damon.md",
                "../../culture/prompts/stage1k-culture-v5-damon.md": "../../culture/prompts/stage1k-culture-v4-damon.md",
                "../../image-writing/templates/brief-standard-static-v3-damon.md":
                    "../../image-writing/templates/brief-standard-static-v2-damon.md"}

# the definitions bound into the prompts, old next to new: (title, the copy taken before the change, the live file)
DEFS_BEFORE = "runs/image-teardown/_system/before-2026-10-29"
DEFS = [("Creative controls, bound as {creative_controls}", "creative-controls-slice.md",
         "components/creative-controls/slices/controls.md"),
        ("Picture dials: how each dial reaches a picture", "picture-dials.json",
         "components/model-inputs/picture-dials.json"),
        ("The creative glossary", "creative-glossary.md", "components/creative-controls/GLOSSARY.md")]
# the audit that went with that change, shown at the top of the page
AUDIT = "tools/image-writing/context/creativity-tools-audit-2026-10-29-damon.md"

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

.chg{margin:1rem 0 0;border:1px solid var(--line);background:var(--surface);}
.chg h3{font-family:var(--display);font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;margin:0;padding:.55rem .8rem;border-bottom:1px solid var(--line);}
.chg .row{display:grid;grid-template-columns:1fr 1fr;border-bottom:1px solid var(--line);}
.chg .row:last-child{border-bottom:0;}
@media (max-width:620px){.chg .row{grid-template-columns:1fr;}}
.chg .old,.chg .new{padding:.6rem .8rem;font-family:var(--data);font-size:.74rem;line-height:1.7;white-space:pre-wrap;word-break:break-word;}
.chg .old{background:color-mix(in srgb,#c0392b 10%,var(--surface));}
.chg .new{background:color-mix(in srgb,#1f8a5b 12%,var(--surface));}
.chg .tag{display:block;font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:.2rem;}
.audit h2{margin:.2rem 0 .6rem;font-size:clamp(1.2rem,2.6vw,1.6rem);}
.audit h3{font-family:var(--display);text-transform:uppercase;font-size:.95rem;margin:1.4rem 0 .4rem;}
.audit li{margin:.3rem 0 .3rem 1.1rem;font-size:.95rem;}
.tbl{overflow-x:auto;margin:.8rem 0;}
.tbl table{border-collapse:collapse;font-size:.84rem;line-height:1.45;min-width:46rem;}
.tbl th,.tbl td{border:1px solid var(--line);padding:.45rem .55rem;vertical-align:top;text-align:left;}
.tbl th{background:var(--sunk);font-family:var(--display);text-transform:uppercase;font-size:.7rem;letter-spacing:.08em;}
.tbl td:first-child{font-weight:600;white-space:nowrap;}
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


def changes(new_fn):
    """Old next to new for one prompt: every changed block against the version before it. '' when nothing to compare."""
    import difflib
    if new_fn in CHANGED_FROM and CHANGED_FROM[new_fn] is None:
        return ("<div class='chg'><h3>New prompt: nothing before it</h3><div class='row'>"
                "<div class='old'><span class='tag'>before</span>(no prompt: a review's words were rewritten like any swipe's)</div>"
                f"<div class='new'><span class='tag'>{Path(new_fn).name[:-9]}</span>{render((P / new_fn).read_text().strip())}</div></div></div>")
    old_fn = CHANGED_FROM.get(new_fn)
    if not old_fn or not (P / old_fn).exists():
        return ""
    a, b = (P / old_fn).read_text().splitlines(), (P / new_fn).read_text().splitlines()
    rows = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        old, new = "\n".join(a[i1:i2]).strip(), "\n".join(b[j1:j2]).strip()
        rows.append("<div class='row'>"
                    f"<div class='old'><span class='tag'>{Path(old_fn).name[:-9] if old else 'nothing before'}</span>{render(old) if old else ''}</div>"
                    f"<div class='new'><span class='tag'>{Path(new_fn).name[:-9] if new else 'removed'}</span>{render(new) if new else ''}</div></div>")
    if not rows:
        return ""
    return f"<div class='chg'><h3>What changed from {html.escape(old_fn)}: old next to new</h3>{''.join(rows)}</div>"


def diff_rows(a_txt, b_txt, a_tag, b_tag):
    import difflib
    a, b = a_txt.splitlines(), b_txt.splitlines()
    rows = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        old, new = "\n".join(a[i1:i2]).strip(), "\n".join(b[j1:j2]).strip()
        rows.append("<div class='row'>"
                    f"<div class='old'><span class='tag'>{a_tag if old else 'nothing before'}</span>{render(old) if old else ''}</div>"
                    f"<div class='new'><span class='tag'>{b_tag if new else 'removed'}</span>{render(new) if new else ''}</div></div>")
    return rows


def md_page(md):
    """A small Markdown page (headings, one table, bullets, paragraphs) as HTML, for the audit at the top."""
    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return re.sub(r"(https://\S+)", r"<a href='\1'>\1</a>", s)
    out, para, rows = [], [], []
    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()
        if rows:
            head, body = rows[0], [r for r in rows[2:]]
            out.append("<div class='tbl'><table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
                       + "</table></div>")
            rows.clear()
    for line in md.splitlines():
        if line.startswith("|"):
            if para:
                flush()
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif line.startswith("#"):
            flush()
            n = len(line) - len(line.lstrip("#"))
            out.append(f"<h{n + 1}>{inline(line.lstrip('# ').strip())}</h{n + 1}>")
        elif line.startswith("- "):
            flush()
            out.append("<li>" + inline(line[2:]) + "</li>")
        elif line.startswith("  ") and out and out[-1].startswith("<li>"):
            out[-1] = out[-1][:-5] + " " + inline(line.strip()) + "</li>"
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
    flush()
    return "\n".join(out)


def latest(fn):
    """The highest -vN version of a prompt: the page shows what runs, so a stale version number in the list never hides it."""
    stem = re.sub(r"-v\d+-damon\.md$", "", fn)
    base = P / Path(fn).parent
    hits = sorted(base.glob(Path(stem).name + "-v*-damon.md"), key=lambda f: int(re.search(r"-v(\d+)-", f.name).group(1)))
    return str(Path(fn).parent / hits[-1].name) if hits else fn


def main():
    STAGES[:] = [(s[0], s[1], latest(s[2]), *s[3:]) for s in STAGES]
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
    import sys; sys.path.insert(0, str(HERE / "tools")); import paths as PT
    audit = PT.REPO / AUDIT
    if audit.is_file():
        out += ["<section class='ke audit' id='saudit'>", md_page(audit.read_text()), "</section>"]

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
                changes(fn), f"<pre>{render(body)}</pre>", "</section>"]

    for title, before, now in DEFS:
        a, b = PT.REPO / DEFS_BEFORE / before, PT.REPO / now
        if not (a.is_file() and b.is_file()):
            continue
        rows = diff_rows(a.read_text(), b.read_text(), "before 2026-10-29", "now")
        if rows:
            out += ["<section class='ke'>", f"<div class='top'><span class='badge'>Definition</span><h2>{html.escape(title)}</h2>",
                    f"<span class='file'>{now}</span></div>",
                    "<p class='job'>Bound into the prompts above word for word. Only what changed is shown.</p>",
                    f"<div class='chg'><h3>What changed: old next to new</h3>{''.join(rows)}</div>", "</section>"]

    out += [f"<footer>{len(live)} prompts · {total} lines · "
            "<code>tools/image-teardown/prompts/</code> (steps 1, 2, 2b) and <code>tools/image-writing/prompts/</code> (steps 3 to 6) · "
            "variables documented in <code>image-teardown/VARIABLES.md</code> · "
            "rebuilt by <code>build_prompt_library.py</code> after every "
            "prompt change</footer></div>"]

    # output under runs/, never inside the component (O4)
    dest = PT.REPO / "runs" / "image-teardown" / "_system" / "prompt-library.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out))
    print(f"wrote {dest} — {len(live)} prompts, {total} lines, "
          f"{format(dest.stat().st_size, ',')} bytes")


if __name__ == "__main__":
    main()
