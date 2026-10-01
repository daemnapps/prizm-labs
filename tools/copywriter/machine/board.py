#!/usr/bin/env python3
"""Renders every copy run into one page: board.html.

Same shape as the video-teardown machine's board (
components/video-teardown/machine/board.py) and deliberately so — left, the
runs; click one and you get its five stages, and for each stage the prompt
that ran and the output it produced, side by side. That pairing is the whole
point: the prompt is the thing being tuned.

    python3 board.py

Reads results/<label>/run.json. Runs made before the runner wrote one are
reconstructed from the files on disk, with anything unknowable left blank
rather than guessed at.
"""

import html as H
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import md
from copy import STAGES, SPEC, fill, latest_prompt

import paths as P
from paths import HERE, WORKSPACE
RESULTS = HERE / "results"
OUT = HERE / "pages" / "board.html"


def read(p):
    p = Path(p)
    return p.read_text() if p.is_file() else ""


# The chain was rebuilt 2026-08-25 and the stage KEYS were reused for
# different jobs — old stage2 was "bank match", new stage2 is "spec". Render
# an old run against today's table and every stage gets a wrong name sitting
# over a real output, which is worse than showing nothing.
#
# A run's own filenames record what it actually ran (`stage2--bank-match.md`),
# so identity comes from the run, never from whatever the table says now.
SHAPE_V1 = [
    dict(key="stage1", id="1", name="Concept brief", group="READ THE SOURCE",
         label="concept-brief",
         blurb="The source's hook, beats, turn and proof, pulled into one block."),
    dict(key="stage0", id="1b", name="Context scout", group="READ THE SOURCE",
         label="context",
         blurb="Sifts what the brand knows and picks what this source needs."),
    dict(key="stage2", id="2", name="Bank match", group="CHECK WHAT'S RUNNING",
         label="bank-match",
         blurb="Existing copy judged against this source — reuse, re-angle, no match."),
    dict(key="stage3", id="3", name="Copy variations", group="WRITE IT",
         label="copy", blurb="Primary text and headlines, lane-labelled."),
    dict(key="stage4", id="4", name="Compliance", group="WRITE IT",
         label="checked",
         blurb="Banned words, unsupported claims, policy shapes, stale prices."),
    dict(key="stage5", id="5", name="Copy brief", group="WHAT SHIPS",
         label="copy-brief", blurb="The document a media buyer opens."),
]


def shape_of(d):
    """Which chain this run ran, decided by what is on its own disk."""
    labels = set()
    for f in d.iterdir():
        m = re.match(r"stage[0-9a-z]+--([a-z-]+)\.md$", f.name)
        if m:
            labels.add(m.group(1))
    v1 = len(labels & {s["label"] for s in SHAPE_V1})
    v2 = len(labels & {s["label"] for s in STAGES})
    return ("v1", SHAPE_V1) if v1 > v2 else ("v2", STAGES)


def legacy(d):
    """A run from before run.json existed. Everything here is read off disk or
    recomputed deterministically — no timings are invented, they stay null."""
    man = {}
    f = d / "run-manifest.json"
    if f.is_file():
        try:
            man = json.loads(f.read_text())
        except Exception:
            man = {}
    by_stage = {m["stage"]: m for m in man.get("stages", [])}
    stages = {}
    for spec in STAGES:
        k = spec["key"]
        out = d / f"{k}--{spec['label']}.md"
        if not out.is_file():
            continue
        m = by_stage.get(k, {})
        stages[k] = {
            "status": "done",
            "seconds": None,
            "chars_out": len(read(out).strip()),
            "model": m.get("model") or "claude-opus-5",
            "prompt_name": m.get("prompt") or "",
            "out": out.name,
            "sent": None,
        }
    return {
        "slug": d.name,
        "label": man.get("label") or d.name,
        "brand": man.get("brand") or "",
        "lane": "bank-matched" if man.get("existing_copy") else "net-new",
        "video_reference": man.get("video_brief") or "",
        "existing_copy": man.get("existing_copy"),
        "generated_at": man.get("generated_at") or "",
        "stages": stages,
    }


def shape_last(d):
    return shape_of(d)[1][-1]["key"]


def collect():
    runs = []
    # Current runs first, then anything parked in an archive folder. Archived
    # runs stay visible — they are real output and the record of how the tool
    # got here — but they never sit above the work in hand.
    # BOTH HOMES (2026-09-20): new runs file under runs/copy-machine/<brand>/,
    # older ones are still in results/ — paths.all_runs() reads the two.
    dirs = [(d, False) for d in P.all_runs()]
    for a in (sorted(P.RESULTS.glob("archive*")) if P.RESULTS.is_dir() else []):
        if a.is_dir():
            dirs += [(d, True) for d in sorted(a.iterdir()) if d.is_dir()]

    for d, archived in dirs:
        f = d / "run.json"
        if f.is_file():
            try:
                st = json.loads(f.read_text())
            except Exception:
                continue
        else:
            st = legacy(d)
            if not st["stages"]:
                continue

        # A run that finished before a stage existed has no record of it. That
        # is not "waiting" — nothing is coming. Saying waiting on a run that
        # ended yesterday is the page lying about its own state.
        # "Finished" means it reached the LAST stage — not "everything it
        # happens to have recorded is done", which is trivially true mid-run
        # and was labelling a run still in flight as predating the stages it
        # was about to execute.
        recorded = st.get("stages", {})
        finished = (recorded.get(shape_last(d)) or {}).get("status") == "done"

        chain_ver, shape = shape_of(d)
        st["chain"] = chain_ver
        stage_list = []
        for spec in shape:
            rec = dict(recorded.get(spec["key"]) or {})
            rec.setdefault("status", "absent" if finished else "waiting")
            rec.update(id=spec["id"], name=spec["name"], group=spec["group"],
                       blurb=spec["blurb"])

            # the prompt: whatever version actually ran, else the current head
            pname = rec.get("prompt_name") or ""
            # Runs made back in ai-workspace recorded this against that tree;
            # runs made here record it against the build. Try both.
            pf = None
            for base in (HERE, WORKSPACE):
                cand = (base / rec["prompt_file"]) if rec.get("prompt_file") else None
                if cand and cand.is_file():
                    pf = cand
                    break
            if not (pf and pf.is_file()):
                for base in (HERE / "prompts", HERE / "prompts" / "superseded"):
                    cand = base / pname if pname else None
                    if cand and cand.is_file():
                        pf = cand
                        break
            if not pf:
                try:
                    pf = latest_prompt(spec["key"])
                except SystemExit:
                    pf = None
            raw_prompt = read(pf) if pf else ""
            rec["prompt_name"] = pname or (pf.name if pf else "— none —")
            rec["prompt_text"] = raw_prompt
            rec["prompt_html"] = md.render(raw_prompt)

            o = d / rec["out"] if rec.get("out") else None
            raw_out = read(o) if o else ""
            rec["output_text"] = raw_out
            rec["output_html"] = md.render(raw_out) if raw_out else ""

            sp = d / rec["sent"] if rec.get("sent") else None
            raw_sent = read(sp) if sp else ""
            rec["sent_text"] = raw_sent
            rec["sent_html"] = md.render(raw_sent) if raw_sent else ""
            rec["wants"] = rec.get("wants") or []
            stage_list.append(rec)

        st["stage_list"] = stage_list
        st["archived"] = archived
        st["run_dir"] = str(d)          # where this run's files actually are
        st.setdefault("lane", "net-new")
        runs.append(st)
    return runs


def issues(runs):
    """What needs looking at, READ OFF THE RUNS — never a list typed by hand.

    A hand-kept list is the clock bug again: it is right the day it is
    written and quietly wrong after that. One of its entries had already
    decayed into announcing a fix as though it were pending. Everything here
    is derived, so a fixed thing disappears on the next build without anyone
    remembering to delete it.
    """
    found = []

    # stages a finished run never had — it is showing output from an older
    # shape of the chain, and its copy was written without that stage
    behind = {}
    for r in runs:
        for s in r["stage_list"]:
            if s.get("status") == "absent":
                behind.setdefault(s["name"], []).append(r["slug"])
    for name, slugs in behind.items():
        found.append(f"<b>{len(slugs)} run(s) predate the {name} stage</b> and "
                     f"never had it: {', '.join(slugs)}. Their copy was written "
                     f"without it — re-run the video to judge them on equal ground.")

    # a run whose prompt is no longer the head: the board is showing output
    # from wording that has since changed
    stale = []
    for r in runs:
        for s in r["stage_list"]:
            if s.get("status") != "done" or not s.get("prompt_name"):
                continue
            try:
                head = latest_prompt(next(x["key"] for x in STAGES
                                          if x["id"] == s["id"])).name
            except (SystemExit, StopIteration):
                continue
            if head != s["prompt_name"]:
                stale.append(f"{r['slug']} · {s['name']} ran {s['prompt_name']}, "
                             f"head is now {head}")
    if stale:
        found.append("<b>Output on this board came from prompt wording that has "
                     "since changed.</b> Re-run to see what the current prompts "
                     "do: " + "; ".join(stale))

    # anything the scout said was standing on contested ground
    for r in runs:
        s0 = next((s for s in r["stage_list"] if s["id"] == "1b"), None)
        if not s0 or s0.get("status") != "done":
            continue
        m = re.search(r"\*\*STANDING TO CARRY FORWARD:?\*\*(.+?)(?:\n\*\*|\Z)",
                      s0.get("output_text", ""), re.S)
        if not m:
            continue
        for line in m.group(1).strip().splitlines():
            line = line.strip(" -*")
            if len(line) > 40 and "nothing contested" not in line.lower():
                found.append(f"<b>{r['slug']} — contested ground:</b> {line}")
                break  # the first one; the stage output carries the rest

    if not found:
        found.append("Nothing flagged. Every run is on the current prompts and "
                     "no stage reported contested ground.")
    return found


def embed_media(runs, budget=11_000_000):
    """Inline the media so the page carries it, for the published copy.

    Served locally the page just points at files. Published to claude.ai it is
    a standalone document on someone else's host: a src of
    `results/…/source.mp4` resolves to nothing there, which is why the video
    was invisible on the artifact while working perfectly on the board.

    Media is deduped by source path — five runs share one <person> video, and
    inlining it five times would blow the size cap for no gain. Returns a
    {id: dataURI} map; runs carry the id.
    """
    import base64, hashlib
    media, used, skipped = {}, 0, []

    def add(path, mime):
        nonlocal used
        p = Path(path)
        if not p.is_file():
            return None
        key = hashlib.sha256(str(p.resolve()).encode()).hexdigest()[:12]
        if key in media:
            return key                      # already carried, share it
        raw = p.read_bytes()
        if used + len(raw) * 1.37 > budget:
            skipped.append(f"{p.name} ({round(len(raw)/1048576,1)} MB)")
            return None
        media[key] = f"data:{mime};base64," + base64.b64encode(raw).decode()
        used += len(raw) * 1.37
        return key

    for r in runs:
        # Archived runs keep their poster (cheap, and the card looks right)
        # but not their video: five retired runs sharing one mp4 still cost a
        # copy each here, and two videos already put the page over the 16MB
        # publish cap. The live board still plays every one of them.
        d = Path(r["run_dir"]) if r.get("run_dir") else (
            (RESULTS / "archive-v1-chain" / r["slug"]) if r.get("archived") else (RESULTS / r["slug"]))
        if r.get("poster"):
            r["poster_id"] = add(d / r["poster"], "image/jpeg")
        if r.get("video") and not r.get("archived"):
            r["video_id"] = add(d / r["video"], "video/mp4")
    if skipped:
        print(f"  media over budget, left out: {', '.join(skipped)}")
    return media


def build(embed=False):
    (HERE / "pages").mkdir(exist_ok=True)      # generated, git-ignored — absent in a fresh checkout
    runs = collect()
    if embed:
        # The "filled in" view is every stage's prompt WITH the whole brand
        # context pasted into it — 11 MB across six runs, and the single
        # biggest thing on the page. It is a debugging view; the live board
        # keeps it. The published copy carries the prompts and the outputs,
        # which is what anyone reads away from the desk.
        for r in runs:
            for st in r["stage_list"]:
                st["sent_html"] = st["sent_text"] = ""
    media = embed_media(runs) if embed else {}
    data = json.dumps(runs).replace("</", "<\\/")
    stamp = time.strftime("%-I:%M:%S %p", time.localtime())
    # Written beside the page so the page can re-fetch its own data and redraw
    # without a reload — the same split the swipe machine uses. Served locally
    # this is what makes the board live; opened as a file or published as an
    # artifact the fetch just fails and the page stays a snapshot, which it
    # then says out loud instead of pretending.
    if not embed:
        (HERE / "pages" / "board.json").write_text(json.dumps(
            {"runs": runs, "issues": issues(runs), "built": time.time()}))
    page = (TEMPLATE
            .replace("__DATA__", data)
            .replace("__MEDIA__", json.dumps(media).replace("</", "<\\/"))
            .replace("__BUILT__", str(time.time()))
            .replace("__ISSUES__", json.dumps(issues(runs)).replace("</", "<\\/"))
            .replace("__STAMP__", stamp))
    out = (HERE / "pages" / "board-embedded.html") if embed else OUT
    out.write_text(page)
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Copy Machine</title>
<style>
:root{
  --paper:#ffffff; --ground:#f7f7f5; --rail:#fbfbfa; --line:#e8e6e1;
  --line2:#f0efec; --ink:#2c2a26; --body:#393732; --dim:#78746c;
  --dimmer:#a5a099; --go:#2e8b57; --run:#c07c1e; --stop:#c0392b;
  --wait:#dedbd5; --accent:#2f6db5; --hl:#fdf6e3;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,monospace;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{background:var(--ground);color:var(--body);
  font:16px/1.6 var(--sans);-webkit-font-smoothing:antialiased}
a{color:var(--accent)}

header{display:flex;align-items:baseline;gap:14px;padding:16px 26px;
  border-bottom:1px solid var(--line);background:var(--paper);
  position:sticky;top:0;z-index:20}
header h1{margin:0;font-size:17px;font-weight:650;color:var(--ink)}
header .sub{color:var(--dim);font-size:13px}
header .right{margin-left:auto;font-size:12px;color:var(--dimmer);
  display:flex;align-items:center;gap:12px}
.livetag{font:10px var(--mono);letter-spacing:.08em;text-transform:uppercase;
  padding:3px 8px;border-radius:12px}
.livetag.on{color:var(--go);background:#e4f2ea}
.livetag.on::before{content:"";display:inline-block;width:6px;height:6px;
  border-radius:50%;background:var(--go);margin-right:6px;
  animation:p 1.6s ease-in-out infinite;vertical-align:middle}
@keyframes p{0%,100%{opacity:1}50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.livetag.on::before{animation:none}}
.livetag.off{color:var(--dim);background:var(--line2);text-transform:none;
  letter-spacing:0}
#health a{font:11.5px var(--sans);color:var(--stop);text-decoration:none;
  background:#f8e4e1;border-radius:12px;padding:4px 10px;cursor:pointer}
#health a:hover{text-decoration:underline}
#healthbox{position:fixed;right:18px;top:52px;z-index:70;background:var(--paper);
  border:1px solid var(--stop);border-radius:8px;padding:14px 16px;max-width:440px;
  box-shadow:0 6px 24px rgba(0,0,0,.14);font-size:13px;line-height:1.5;display:none}
#healthbox h5{margin:0 0 8px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;
  color:var(--dimmer)}
#healthbox ul{margin:0;padding-left:18px}
#healthbox li{margin-bottom:7px}

.wrap{display:grid;grid-template-columns:262px 1fr;height:calc(100% - 57px)}
.rail{border-right:1px solid var(--line);overflow-y:auto;padding:14px;
  background:var(--rail)}
#q{width:100%;padding:8px 10px;margin-bottom:12px;border:1px solid var(--line);
  border-radius:7px;font:13px var(--sans);background:var(--paper);color:var(--ink)}
#q:focus{outline:none;border-color:var(--accent)}
#count{font:11px var(--mono);color:var(--dimmer);margin-top:10px}
.lanehead{font:600 10px/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;
  color:var(--dimmer);margin:14px 0 7px;display:flex;align-items:center;gap:7px}
.lanehead:first-child{margin-top:0}
.lanehead b{background:var(--line2);border-radius:20px;padding:2px 7px;
  font-family:var(--mono);font-weight:600;color:var(--dim)}
.card{background:var(--paper);border:1px solid var(--line);border-radius:8px;
  padding:10px;margin-bottom:9px;cursor:pointer}
.card:hover{border-color:#d3cfc7}
.card.on{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.card .t{font-size:13px;font-weight:600;color:var(--ink);line-height:1.3;
  word-break:break-word}
.card .cat{font-size:10.5px;color:var(--dimmer);margin-top:3px;line-height:1.35}
.tag{display:inline-block;font:9.5px/1 var(--mono);padding:3px 5px;border-radius:3px;
  background:var(--line2);color:var(--dim);margin-right:4px}
.tag.bank{background:#e4f2ea;color:var(--go)}
.tag.old{background:var(--line2);color:var(--dimmer)}
.chainbadge{font:9.5px var(--mono);letter-spacing:.06em;text-transform:uppercase;
  background:#e4f2ea;color:var(--go);border-radius:10px;padding:2px 7px}
.chainbadge.old{background:var(--line2);color:var(--dimmer)}
.done-pct{font:10px var(--mono);color:var(--dimmer);float:right}
.dots{display:flex;gap:3px;margin-top:8px}
.dot{flex:1;height:4px;border-radius:2px;background:var(--wait)}
.dot.done{background:var(--go)} .dot.running{background:var(--run)}
.dot.error{background:var(--stop)}

main{overflow-y:auto;background:var(--ground)}
.inner{max-width:1180px;margin:0 auto;padding:24px 28px 120px}

.runhead{display:flex;gap:18px;align-items:flex-start;margin-bottom:8px}
.runhead .vidwrap{width:190px;flex:none}
.runhead .vidwrap video{width:190px;max-height:340px;border-radius:9px;
  background:#000;display:block;border:1px solid var(--line)}
.runhead .vcap{font:10.5px var(--mono);color:var(--dimmer);margin-top:6px;
  text-align:center;word-break:break-all}
.runhead .vlabel{font:9.5px var(--mono);letter-spacing:.09em;text-transform:uppercase;
  color:var(--dimmer);margin-bottom:6px;text-align:center}
.runhead .vwarn{font-size:11px;line-height:1.45;color:var(--run);background:#fbf0dc;
  border-radius:5px;padding:7px 9px;margin-top:8px}
.runhead .vidcard{width:190px;flex:none;border:1px solid var(--line);
  border-radius:9px;background:var(--paper);padding:14px;text-align:center}
.runhead .vnone{font-size:11px;color:var(--dimmer);margin-top:8px;line-height:1.4}
.runhead .vidcard .vlabel{font:10px var(--mono);color:var(--dimmer);
  letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px}
.runhead .vidcard .vref{font-size:12px;color:var(--ink);word-break:break-word;
  line-height:1.4}
.runhead h2{margin:0 0 5px;font-size:21px;color:var(--ink);font-weight:650}
.meta{color:var(--dim);font-size:13px}
.meta b{color:var(--ink);font-weight:600}

.grp{font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--dimmer);font-weight:600;margin:30px 0 10px}

.stage{border:1px solid var(--line);border-radius:9px;margin-bottom:10px;
  overflow:hidden;background:var(--paper)}
.stage>summary{list-style:none;cursor:pointer;padding:13px 16px;
  display:flex;align-items:center;gap:12px}
.stage>summary::-webkit-details-marker{display:none}
.stage>summary:hover{background:var(--line2)}
.stage[open]>summary{border-bottom:1px solid var(--line);background:var(--line2)}
.pill{font:600 11px/1 var(--mono);padding:6px 8px;border-radius:5px;
  background:var(--wait);color:var(--dim);min-width:30px;text-align:center}
.pill.done{background:#e4f2ea;color:var(--go)}
.pill.running{background:#fbf0dc;color:var(--run)}
.pill.error{background:#f8e4e1;color:var(--stop)}
/* a stage this run never had — hatched, not blank, so it reads as "no such
   thing here" rather than "not yet" */
.pill.absent,.pill.skipped{background:var(--line2);color:var(--dimmer)}
.dot.skipped{background:repeating-linear-gradient(45deg,var(--wait),var(--wait) 2px,var(--line2) 2px,var(--line2) 4px)}
.skipnote{padding:16px 20px;color:var(--dim);font-size:13.5px;line-height:1.6}
.skipnote b{color:var(--ink);font-weight:640}
.stage.absent{opacity:.62}
.dot.absent{background:repeating-linear-gradient(45deg,var(--wait),var(--wait) 2px,var(--line2) 2px,var(--line2) 4px)}
.sname{font-weight:650;font-size:15px;color:var(--ink)}
.sblurb{color:var(--dim);font-size:13px;margin-top:2px;max-width:82ch}
.stats{margin-left:auto;text-align:right;color:var(--dimmer);
  font:11px/1.5 var(--mono);flex:none}
.flagtag{display:block;font:9.5px/1 var(--mono);color:var(--run);
  background:#fbf0dc;border-radius:3px;padding:3px 5px;margin-bottom:4px}

.panes{display:grid;grid-template-columns:minmax(0,38%) minmax(0,62%);
  gap:1px;background:var(--line)}
@media(max-width:1000px){.panes{grid-template-columns:1fr}}
.pane{background:var(--paper);min-width:0;display:flex;flex-direction:column}
.pane.prompt{background:#fcfcfb}
.pane h4{margin:0;padding:10px 18px;font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--dimmer);font-weight:600;
  border-bottom:1px solid var(--line2);display:flex;align-items:center;gap:10px}
.pane h4 .fname{font-family:var(--mono);text-transform:none;letter-spacing:0;
  color:var(--dim);font-size:11px;font-weight:400}
.pane h4 .btns{margin-left:auto;display:flex;gap:5px}
.pane h4 button{font:11px var(--sans);background:var(--paper);
  border:1px solid var(--line);color:var(--dim);border-radius:5px;
  padding:3px 9px;cursor:pointer}
.pane h4 button:hover{color:var(--ink);border-color:#cfcbc3}
.pane h4 button.on{color:#fff;background:var(--accent);border-color:var(--accent)}

.doc{padding:20px 26px 34px;overflow:auto;max-height:68vh;
  font-size:15.5px;line-height:1.68;color:var(--body)}
.pane.prompt .doc{font-size:14.5px;line-height:1.62}
.doc>*:first-child{margin-top:0}
.doc h2{font-size:20px;font-weight:650;color:var(--ink);
  margin:30px 0 10px;line-height:1.3}
.doc h3{font-size:16.5px;font-weight:650;color:var(--ink);margin:26px 0 8px}
.doc h4,.doc h5,.doc h6{font-size:14px;font-weight:650;color:var(--ink);
  margin:22px 0 6px;letter-spacing:.01em}
.doc p{margin:0 0 13px;max-width:74ch}
.doc strong{color:var(--ink);font-weight:650}
.doc ul,.doc ol{margin:0 0 14px;padding-left:22px}
.doc li{margin-bottom:6px;max-width:72ch}
.doc blockquote{margin:0 0 15px;padding:2px 0 2px 16px;
  border-left:3px solid var(--wait);color:var(--dim)}
.doc blockquote p{margin-bottom:6px}
.doc hr{border:0;border-top:1px solid var(--line);margin:24px 0}
.doc code{font:.87em var(--mono);background:var(--line2);
  border:1px solid var(--line);border-radius:4px;padding:1px 5px;color:var(--ink)}
.doc pre.block{font:12.5px/1.6 var(--mono);background:#faf9f7;
  border:1px solid var(--line);border-radius:6px;padding:13px 15px;
  overflow-x:auto;white-space:pre;margin:0 0 15px}
.doc .tw{overflow-x:auto;margin:0 0 18px;border:1px solid var(--line);
  border-radius:7px}
.doc table{border-collapse:collapse;width:100%;font-size:14px}
.doc th{background:#faf9f7;text-align:left;font-weight:650;color:var(--ink);
  padding:9px 13px;border-bottom:1px solid var(--line);white-space:nowrap}
.doc td{padding:9px 13px;border-bottom:1px solid var(--line2);
  vertical-align:top;line-height:1.55}
.doc tr:last-child td{border-bottom:0}
.doc .none{color:var(--dimmer)}
.raw{padding:18px 24px;font:12.5px/1.65 var(--mono);white-space:pre-wrap;
  word-break:break-word;overflow:auto;max-height:68vh;color:#4a4740;margin:0}
.wants{padding:8px 18px;border-bottom:1px solid var(--line2);
  font:11px var(--sans);color:var(--dimmer)}
.wants span{display:inline-block;background:var(--line2);
  border:1px solid var(--line);border-radius:4px;padding:2px 7px;
  margin:2px 4px 2px 0;color:var(--dim);font-family:var(--mono)}
.empty{color:var(--dim);max-width:60ch;margin-top:40px}
.bar{height:3px;background:var(--line2);position:relative;overflow:hidden}
.bar i{position:absolute;inset:0 auto 0 0;width:0;background:var(--run);display:block}
.bar.done i{background:var(--go);width:100%}
.bar.idle{display:none}

@media (max-width: 760px){
  html,body{height:auto}
  header{padding:12px 14px;gap:8px;flex-wrap:wrap}
  header h1{font-size:16px} header .sub{display:none}
  .wrap{display:block;height:auto}
  .rail{border-right:0;border-bottom:1px solid var(--line);padding:10px 12px;
    position:sticky;top:49px;z-index:15;background:var(--rail)}
  #rail{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none}
  #rail::-webkit-scrollbar{display:none}
  .card{flex:0 0 150px;margin:0;padding:7px}
  .card .cat{display:none}
  main{overflow:visible}
  .inner{padding:16px 12px 80px}
  .runhead{gap:12px} .runhead .vidcard{width:120px;padding:10px}
  .runhead h2{font-size:17px}
  .panes{grid-template-columns:1fr}
  .pane.out{order:1}
  .pane.prompt{order:2;border-top:1px solid var(--line)}
  .doc{max-height:none;padding:16px 14px 26px;font-size:15px}
  .pane.prompt .doc{max-height:340px;font-size:13.5px}
  .raw{max-height:340px}
  .doc table{font-size:13px} .doc th,.doc td{padding:7px 9px}
  .stage>summary{padding:14px 13px;gap:10px}
  .pill{padding:8px 9px;font-size:12px}
  .pane h4{padding:11px 14px;flex-wrap:wrap;gap:7px}
  .pane h4 button{padding:6px 11px;font-size:12px}
}
</style></head><body>

<header>
  <h1>The Copy Machine</h1>
  <span class="sub">video's brief in &rarr; ad copy out</span>
  <div class="right"><span id="health"></span><span id="live"></span><span id="clock">__STAMP__</span></div>
</header>

<div class="wrap">
  <nav class="rail">
    <input id="q" type="search" placeholder="Search runs, brand, lane…"
           autocomplete="off" oninput="rail()">
    <div id="rail"></div>
    <div id="count"></div>
  </nav>
  <main id="main"><div class="inner" id="inner"></div></main>
</div>

<script>
const RUNS = __DATA__;
const MEDIA = __MEDIA__;
// A build that carries its own media is a snapshot by definition: polling
// would fetch pathed data and throw the embedded media away mid-render.
const EMBEDDED = Object.keys(MEDIA).length > 0;
const esc = s => (s||"").replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));

/* When a run actually happened, said relative to now — "yesterday" is the
   thing he needs to see at a glance, not an ISO string he has to decode. */
function when(stamp){
  if(!stamp) return "date not recorded";
  const t = Date.parse(stamp);
  if(isNaN(t)) return stamp;
  const days = Math.floor((Date.now() - t) / 86400000);
  const clock = new Date(t).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"});
  if(days <= 0) return `today, ${clock}`;
  if(days === 1) return `yesterday, ${clock}`;
  if(days < 7) return `${days} days ago`;
  return new Date(t).toLocaleDateString([], {day:"numeric", month:"short"});
}
let cur = 0;

/* Things a person should look at before this copy runs anywhere. Each one is
   read off a real stage output — nothing here is decorative. */
let ISSUES = __ISSUES__;

const KEEP = "copy-machine-place";
function remember(){
  const open = [...document.querySelectorAll("details.stage[open]")].map(d=>d.dataset.uid);
  sessionStorage.setItem(KEEP, JSON.stringify(
    {cur, open, y: document.getElementById("main").scrollTop}));
}
function restore(){
  let p; try { p = JSON.parse(sessionStorage.getItem(KEEP)); } catch(e){}
  if(!p) return;
  if(typeof p.cur === "number" && RUNS[p.cur]) cur = p.cur;
  rail(); render();
  (p.open||[]).forEach(uid => {
    const d = document.querySelector(`details.stage[data-uid="${uid}"]`);
    if(d) d.open = true;
  });
  if(p.y) document.getElementById("main").scrollTop = p.y;
}
addEventListener("beforeunload", remember);

function rail(){
  const q = (document.getElementById("q")?.value || "").toLowerCase().trim();
  const hay = r => [r.label, r.brand, r.lane, r.video_reference].join(" ").toLowerCase();
  const shown = RUNS.map((r,i)=>({r,i})).filter(({r}) => !q || hay(r).includes(q));

  const groups = {};
  shown.forEach(({r,i}) => {
    const k = r.archived ? "ARCHIVE · FIRST CHAIN" : (r.lane || "unread").toUpperCase();
    (groups[k] = groups[k] || []).push({r,i});
  });
  const order = ["ORGANIC","ALREADY AN AD","UNREAD","BANK-MATCHED","NET-NEW"];
  // the archive always sits last, whatever it is called
  const isArc = k => k.startsWith("ARCHIVE");
  const keys = Object.keys(groups).sort((a,b)=>{
    if(isArc(a) !== isArc(b)) return isArc(a) ? 1 : -1;
    const x = order.indexOf(a), y = order.indexOf(b);
    return (x<0?98:x)-(y<0?98:y);
  });

  document.getElementById("rail").innerHTML = keys.map(k => `
    <div class="lanehead">${esc(k)} <b>${groups[k].length}</b></div>
    ${groups[k].map(({r,i})=>{
      const done = r.stage_list.filter(s=>s.status==="done").length;
      const opts = (r.stage_list.find(s=>s.id==="3")||{}).chars_out;
      return `<div class="card ${i===cur?'on':''}" onclick="pick(${i})">
        <div class="t">${esc(r.label)}<span class="done-pct">${done}/${r.stage_list.length}</span></div>
        <div class="cat">${esc(r.brand||"—")}${r.chain==="v1"?' · <span class="tag old">old chain</span>':''}</div>
        <div class="cat">
          <span class="tag ${r.existing_copy?'bank':''}">${r.existing_copy?"copy bank":"no bank"}</span>
          ${opts?`<span class="tag">${(opts/1000).toFixed(1)}k chars</span>`:""}
        </div>
        <div class="dots">${r.stage_list.map(s=>`<div class="dot ${s.status}" title="${s.id} ${esc(s.name)}"></div>`).join("")}</div>
      </div>`;
    }).join("")}`).join("") || '<div class="empty">No match.</div>';

  document.getElementById("count").textContent =
    `${shown.length} of ${RUNS.length} run${RUNS.length===1?"":"s"}`;
}
function pick(i){ cur=i; rail(); render();
  document.getElementById("main").scrollTop=0; remember(); }

function show(uid, which, e){
  if(e){ e.preventDefault(); e.stopPropagation(); }
  ["doc","filled","raw"].forEach(k=>{
    const el = document.getElementById(k+"-"+uid);
    if(el) el.style.display = (k===which) ? "" : "none";
    const b = document.getElementById("b"+k+"-"+uid);
    if(b) b.classList.toggle("on", k===which);
  });
}

function toggleHealth(e){
  e.preventDefault();
  const b = document.getElementById("healthbox");
  b.style.display = b.style.display === "block" ? "none" : "block";
}

function stageBlock(r,s){
  const done = s.status==="done", uid = r.slug+"-"+s.id;
  const stats = done
    ? `${s.seconds!=null?s.seconds+"s &middot; ":""}${(s.chars_out||0).toLocaleString()} chars<br>${esc(s.model||"")}`
    : (s.status==="running" ? "running&hellip;"
      : (s.status==="error" ? "stopped"
      : (s.status==="absent" ? "not in this run" : "waiting")));
  const body = done
    ? `<div class="doc">${s.output_html||""}</div>`
    : s.status==="skipped"
    ? `<div class="skipnote"><b>Skipped on purpose.</b><br>${esc(s.why||"")}</div>`
    : s.status==="absent"
    ? `<div class="doc"><p class="none">This run finished before this stage
        existed, so it never ran here. Nothing is pending &mdash; re-run the
        video if you want this stage's output for it.</p></div>`
    : `<div class="doc"><p class="none">Nothing here yet &mdash; this stage has not run.</p></div>`;
  return `
  <details class="stage ${(s.status==="absent"||s.status==="skipped")?"absent":""}" id="stage-wrap-${uid}" data-uid="${uid}" ontoggle="remember()">
    <summary>
      <span class="pill ${s.status}">${s.id}</span>
      <span><span class="sname">${esc(s.name)}</span><div class="sblurb">${esc(s.blurb)}</div></span>
      <span class="stats">${stats}</span>
    </summary>
    <div class="bar ${done?'done':'idle'}"><i></i></div>
    <div class="panes">
      <div class="pane prompt">
        <h4>The prompt <span class="fname">${esc(s.prompt_name)}</span>
          <span class="btns">
            <button id="bdoc-${uid}" class="on" onclick="show('${uid}','doc',event)">prompt</button>
            ${s.sent_html?`<button id="bfilled-${uid}" onclick="show('${uid}','filled',event)">filled in</button>`:""}
            <button id="braw-${uid}" onclick="show('${uid}','raw',event)">raw</button>
          </span>
        </h4>
        ${s.wants && s.wants.length?`<div class="wants">feeds on ${s.wants.map(w=>`<span>${esc(w)}</span>`).join("")}</div>`:""}
        <div class="doc" id="doc-${uid}">${s.prompt_html||""}</div>
        <div class="doc" id="filled-${uid}" style="display:none">${s.sent_html||""}</div>
        <pre class="raw" id="raw-${uid}" style="display:none">${esc(s.prompt_text)}</pre>
      </div>
      <div class="pane out">
        <h4>What came back</h4>
        ${body}
      </div>
    </div>
  </details>`;
}

function render(){
  const r = RUNS[cur], m = document.getElementById("inner");
  if(!r){ m.innerHTML = `<div class="empty"><h2>No runs yet.</h2></div>`; return; }
  const done = r.stage_list.filter(s=>s.status==="done").length;
  // What this video actually IS matters more than showing it. It is the
  // SOURCE that was torn down — the creator's own existing post, whose
  // FORMAT the new ad replicates. It is not the ad this copy runs against;
  // that ad has not been shot yet. Labelling it "pairs with" (which this
  // board did until 2026-08-25) invites a buyer to play it, hear a subject
  // the copy never mentions, and conclude the copy is wrong.
  // Carried inline when the page was built for publishing; a file path when
  // it is being served locally. A path is meaningless on claude.ai, which is
  // why the video was missing there and fine on the board.
  const vsrc = MEDIA[r.video_id]
    || (r.video ? `results/${encodeURIComponent(r.slug)}/${encodeURIComponent(r.video)}` : null);
  const vpos = MEDIA[r.poster_id]
    || (r.poster ? `results/${encodeURIComponent(r.slug)}/${encodeURIComponent(r.poster)}` : null);
  let out = `<div class="runhead">
    ${vsrc
      ? `<div class="vidwrap">
           <div class="vlabel">source · the format being replicated</div>
           <video src="${vsrc}" ${vpos?`poster="${vpos}"`:""} controls preload="metadata"
                  playsinline></video>
           <div class="vcap">${esc(r.video_reference||"")}</div>
           <div class="vwarn">Not the ad. This is the creator's existing post,
             torn down for its structure. The ad this copy runs against is
             still to be shot from the brief.</div>
         </div>`
      : `<div class="vidcard">
           <div class="vlabel">source</div>
           <div class="vref">${esc(r.video_reference||"—")}</div>
           <div class="vnone">no video linked &mdash; re-run with <code>--video</code></div>
         </div>`}
    <div><h2>${esc(r.label)}</h2>
      <div class="meta"><b>${done}</b> of ${r.stage_list.length} stages done
      &middot; brand <b>${esc(r.brand||"—")}</b> &middot; <b>${esc(r.lane)}</b> lane</div>
      <div class="meta" style="margin-top:4px">${r.existing_copy
        ? `checked against <b>${esc(r.existing_copy.split("/").pop())}</b>`
        : `no existing copy supplied &mdash; every option written net-new`}</div>
      <div class="meta" style="margin-top:4px">ran <b data-ran="${esc(r.generated_at||"")}">${esc(when(r.generated_at))}</b>
        ${r.chain==="v1"
          ? ` &middot; <span class="chainbadge old">first shape &middot; retired 25 Aug</span>`
          : ` &middot; <span class="chainbadge">current chain</span>`}</div>
      ${r.chain==="v2" ? `<div class="meta" style="margin-top:4px">
        lane <b>${esc(r.lane||"unread")}</b> &middot; format <b>${esc(r.format||"unread")}</b></div>` : ""}
    </div></div>`;
  out += `<div id="stages">`;
  let g = "";
  for(const s of r.stage_list){
    if(s.group !== g){ g = s.group; out += `<div class="grp">${esc(g)}</div>`; }
    out += stageBlock(r,s);
  }
  out += `</div>`;
  m.innerHTML = out;
}

function health(){
  const el = document.getElementById("health");
  el.innerHTML = ISSUES.length
    ? `<a onclick="toggleHealth(event)">${ISSUES.length} issue${ISSUES.length>1?"s":""}</a>` : "";
  let box = document.getElementById("healthbox");
  if(!box){ box = document.createElement("div"); box.id="healthbox"; document.body.appendChild(box); }
  box.innerHTML = `<h5>Needs looking at</h5><ul>` +
    ISSUES.map(x=>`<li>${esc(x)}</li>`).join("") + `</ul>`;
}

rail(); render(); restore(); health();

/* ---- keeping the page honest about its own age -------------------------
   The clock used to be a string baked in at build time. It never moved, so
   a board opened at nine in the morning still read whatever time it was
   built — which is exactly how a working tool comes to look broken. Two
   loops now: one ticks the clock every second, one re-fetches the runs and
   redraws when they change.                                              */
const BUILT = __BUILT__ * 1000;
let LIVE = null;          // null until we know; true served, false snapshot
let LASTSIG = null;

function ago(ms){
  const s = Math.max(0, Math.round((Date.now() - ms) / 1000));
  if(s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if(m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return h < 24 ? `${h}h ago` : `${Math.floor(h/24)}d ago`;
}

function tick(){
  document.getElementById("clock").textContent =
    new Date().toLocaleTimeString([], {hour:"numeric", minute:"2-digit", second:"2-digit"});
  const el = document.getElementById("live");
  if(LIVE === true){
    el.className = "livetag on";
    el.textContent = "live";
  } else if(LIVE === false){
    // A snapshot is fine — it just must never pass itself off as live.
    el.className = "livetag off";
    el.textContent = `snapshot · built ${ago(BUILT)}`;
  } else {
    el.className = "livetag"; el.textContent = "";
  }
  // relative run ages drift too — "today, 12:59" becomes "yesterday" at midnight
  document.querySelectorAll("[data-ran]").forEach(n => {
    n.textContent = when(n.dataset.ran);
  });
}

async function poll(){
  try{
    const res = await fetch("board.json?t=" + Date.now(), {cache:"no-store"});
    if(!res.ok) throw new Error(res.status);
    const j = await res.json();
    LIVE = true;
    const sig = JSON.stringify([j.runs.map(r =>
      [r.slug, ...r.stage_list.map(s => `${s.id}:${s.status}:${s.chars_out||0}`)]),
      j.issues]);
    if(sig === LASTSIG) return;
    LASTSIG = sig;
    // the issues badge is derived from the runs, so it has to move with them
    // — leaving it baked at build time is the same staleness bug one level up
    if(j.issues){ ISSUES.length = 0; j.issues.forEach(i => ISSUES.push(i)); health(); }
    // keep his place: which run, which stages open, where he had scrolled
    const open = [...document.querySelectorAll("details.stage[open]")].map(d => d.dataset.uid);
    const y = document.getElementById("main").scrollTop;
    const slug = RUNS[cur] && RUNS[cur].slug;
    RUNS.length = 0; j.runs.forEach(r => RUNS.push(r));
    const i = RUNS.findIndex(r => r.slug === slug);
    cur = i >= 0 ? i : 0;
    rail(); render();
    open.forEach(uid => {
      const d = document.querySelector(`details.stage[data-uid="${uid}"]`);
      if(d) d.open = true;
    });
    document.getElementById("main").scrollTop = y;
  }catch(e){
    // opened as a file, or published as a static artifact — no data to poll
    if(LIVE === null) LIVE = false;
  }
}

setInterval(tick, 1000);
if(!EMBEDDED){ setInterval(poll, 3000); poll(); }
else { LIVE = false; }
tick();
</script></body></html>
"""

if __name__ == "__main__":
    print(build())
