#!/usr/bin/env python3
"""Renders every run into one page: board.html.

Left, the videos. Click one and you get its nine stages, and for each stage
the prompt that ran and the output it produced, side by side. That pairing is
the whole point — the prompt is the thing being tuned.
"""

import html, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import re
import chain as C
import md

RUNS = C.runs_root()
OUT = C.MACHINE / "board.html"


def collect():
    runs = []
    if not RUNS.exists():
        return runs
    for d in sorted(RUNS.iterdir()):
        f = d / "run.json"
        if not f.exists():
            continue
        try:
            st = json.loads(f.read_text())
        except Exception:
            continue
        brand = st.get("brand") or ""
        try:
            # the lane decides which stages this run HAS (chain.LANE_ONLY) —
            # a FRAMEWORK run carries 2f, a swipe run never sees it
            plan = C.stages(brand, lane=st.get("triage_lane") or "")
        except Exception:
            plan = []
        stages = []
        for spec in plan:
            rec = dict(st.get("stages", {}).get(spec["key"]) or {})
            rec.setdefault("status", "waiting")
            rec["id"] = spec["id"]
            rec["name"] = spec["name"]
            rec["group"] = spec["group"]
            rec["blurb"] = spec["blurb"]
            rec["engine"] = rec.get("engine") or spec["engine"]
            rec["version"] = rec.get("version", spec["version"])
            rec["wants"] = sorted(spec["vars"].keys())
            # A stage that ran before its lane rule existed. Saying "skipped"
            # would be false — it ran, and downstream consumed it.
            route = C.route_for(st.get("triage_lane"))
            if rec.get("status") == "done" and spec["key"] in (route["skip"] or []):
                rec["off_route"] = route["why"]

            pf = rec.get("prompt_file") or spec["prompt"]
            rec["prompt_name"] = Path(pf).name if pf else "— none —"
            raw_prompt = Path(pf).read_text() if pf and Path(pf).exists() else ""
            rec["prompt_text"] = raw_prompt
            rec["prompt_html"] = md.render(raw_prompt)

            o = d / rec["out"] if rec.get("out") else None
            raw_out = o.read_text() if o and o.exists() else ""
            rec["output_text"] = raw_out
            html_out = md.render(raw_out) if raw_out else ""
            html_out = html_out.replace('<img src="frames/',
                                        f'<img src="runs/{d.name}/frames/')
            rec["output_html"] = html_out

            sp = d / rec["sent"] if rec.get("sent") else None
            raw_sent = sp.read_text() if sp and sp.exists() else ""
            rec["sent_text"] = raw_sent
            rec["sent_html"] = md.render(raw_sent) if raw_sent else ""
            stages.append(rec)
        # what stage 0 saw — the rail groups and searches on this
        tri = next((x for x in stages if x["id"] == "0"), None)
        text = (tri or {}).get("output_text") or ""
        def field(name):
            m = re.search(rf"^{name}:\s*(.+)$", text, re.M)
            return m.group(1).strip() if m else ""
        st["triage"] = dict(
            lane=field("LANE") or "unclassified",
            category=field("CATEGORY"),
            runtime=field("RUNTIME"),
            ai=("AI" if "LIKELY AI" in text else
                ("maybe AI" if "POSSIBLY AI" in text else
                 ("human" if "LIKELY HUMAN" in text else ""))),
            summary=field("ONE LINE"))
        # every earlier breakdown of this video, newest first
        vdir = d / "versions"
        vers = []
        if vdir.exists():
            for vd in sorted(vdir.iterdir(), reverse=True):
                vf = vd / "version.json"
                if not vf.exists():
                    continue
                try:
                    vj = json.loads(vf.read_text())
                except Exception:
                    continue
                vlist = []
                for spec in plan:
                    k = spec["key"]
                    rec = dict((vj.get("stages") or {}).get(k) or {})
                    rec.setdefault("status", "waiting")
                    rec.update(id=spec["id"], name=spec["name"], group=spec["group"],
                               blurb=spec["blurb"], wants=sorted(spec["vars"].keys()))
                    pr = (vj.get("prompts") or {}).get(k) or {}
                    rec["prompt_name"] = pr.get("name") or ""
                    rec["version"] = pr.get("version")
                    of = vd / rec["out"] if rec.get("out") else None
                    raw = of.read_text() if of and of.exists() else ""
                    html = md.render(raw) if raw else ""
                    rec["output_html"] = html.replace(
                        '<img src="frames/',
                        f'<img src="runs/{d.name}/versions/{vd.name}/frames/')
                    rec["output_text"] = raw
                    rec["prompt_html"] = rec["sent_html"] = ""
                    rec["prompt_text"] = ""
                    vlist.append(rec)
                (vd / "rendered.json").write_text(json.dumps({"stage_list": vlist}))
                vers.append(dict(stamp=vj.get("stamp") or vd.name,
                                 note=vj.get("note") or "",
                                 rerun_from=vj.get("rerun_from") or "",
                                 lane=vj.get("lane"),
                                 prompts=vj.get("prompts") or {},
                                 path=f"runs/{d.name}/versions/{vd.name}/rendered.json"))
        st["versions"] = vers
        st["stage_list"] = stages
        st["lane"] = st.get("lane", "creator")
        st["dir"] = str(d)
        runs.append(st)
    return runs


def expected():
    f = C.MACHINE / "stage-times.json"
    try:
        d = json.loads(f.read_text()) if f.exists() else {}
    except Exception:
        return {}
    return {k: round(sorted(v)[len(v) // 2], 1) for k, v in d.items() if v}


def build():
    runs = collect()
    data = json.dumps(runs).replace("</", "<\\/")
    # Written beside the page so the page can re-fetch its own data and redraw
    # itself. Updating individual fields by hand kept leaving one behind —
    # a stale badge, a frozen timer, a running label on a finished stage.
    stamp = time.strftime("%-I:%M:%S %p", time.localtime())
    (C.MACHINE / "board.json").write_text(json.dumps(
        {"runs": runs, "expected": expected(), "stamp": stamp}))
    # A tiny file to poll. The full one carries every prompt and every output —
    # eighteen megabytes — which is fine to fetch when something changed and
    # absurd to fetch every two seconds.
    (C.MACHINE / "status.json").write_text(json.dumps({
        "stamp": stamp,
        "sig": [[r["slug"]] + [f"{s['id']}:{s.get('status')}:{s.get('seconds') or 0}"
                               for s in r["stage_list"]] for r in runs],
    }))
    live = any(s.get("status") == "running" for r in runs for s in r["stage_list"])
    OUT.write_text(TEMPLATE
                   .replace("__DATA__", data)
                   .replace("__EXPECTED__", json.dumps(expected()))
                   .replace("__STAMP__", time.strftime("%-I:%M:%S %p", time.localtime()))
                   .replace("__LIVE__", "true" if live else "false"))
    return OUT


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Swipe Machine</title>
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
.pulse{width:8px;height:8px;border-radius:50%;background:var(--run);
  animation:p 1.1s infinite;display:inline-block}
@keyframes p{0%,100%{opacity:1}50%{opacity:.25}}

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
.card .cat{font-size:10.5px;color:var(--dimmer);margin-top:3px;line-height:1.35}
.tag{display:inline-block;font:9.5px/1 var(--mono);padding:3px 5px;border-radius:3px;
  background:var(--line2);color:var(--dim);margin-right:4px}
.tag.ai{background:#fbf0dc;color:var(--run)}
.done-pct{font:10px var(--mono);color:var(--dimmer);float:right}
.vertabs{display:flex;gap:4px;margin-top:10px;flex-wrap:wrap}
.vt{font:11.5px var(--sans);background:var(--paper);border:1px solid var(--line);
  color:var(--dim);border-radius:15px;padding:4px 11px;cursor:pointer}
.vt:hover{color:var(--ink);border-color:#cfcbc3}
.vt.on{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.card.working{border-color:var(--run);box-shadow:0 0 0 1px var(--run)}
.working-now{display:flex;align-items:center;gap:6px;font:600 10.5px var(--sans);
  color:var(--run);margin-bottom:6px;letter-spacing:.02em}
.card{background:var(--paper);border:1px solid var(--line);border-radius:8px;
  padding:10px;margin-bottom:9px;cursor:pointer}
.card:hover{border-color:#d3cfc7}
.card.on{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.card .t{font-size:13px;font-weight:600;color:var(--ink);line-height:1.3;
  word-break:break-word}
.card .m{font-size:11px;color:var(--dimmer);margin-top:2px}
.card img{width:100%;height:84px;object-fit:cover;object-position:center 22%;
  border-radius:5px;margin-bottom:8px;display:block;background:#eee}
.dots{display:flex;gap:3px;margin-top:8px}
.dot{flex:1;height:4px;border-radius:2px;background:var(--wait)}
.dot.done{background:var(--go)} .dot.running{background:var(--run)}
.dot.error{background:var(--stop)}

main{overflow-y:auto;background:var(--ground)}
.inner{max-width:1180px;margin:0 auto;padding:24px 28px 120px}

.runhead{display:flex;gap:18px;align-items:flex-start;margin-bottom:8px}
.runhead video{width:168px;border-radius:9px;background:#000;flex:none;
  border:1px solid var(--line)}
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
.pill.skipped{background:var(--line2);color:var(--dimmer)}
.dot.skipped{background:repeating-linear-gradient(45deg,var(--wait),var(--wait)2px,var(--line2)2px,var(--line2)4px)}
.stage.skipped{opacity:.72}
.skipnote{padding:14px 18px;color:var(--dim);font-size:13.5px;line-height:1.55}
.skipnote b{color:var(--ink);font-weight:600}
.skipnote.offroute{background:#fdf8ec;border-bottom:1px solid var(--line)}
.offroute-tag{display:block;font:9.5px/1 var(--mono);color:var(--run);
  background:#fbf0dc;border-radius:3px;padding:3px 5px;margin-bottom:4px}
.sname{font-weight:650;font-size:15px;color:var(--ink)}
.sblurb{color:var(--dim);font-size:13px;margin-top:2px;max-width:82ch}
.stats{margin-left:auto;text-align:right;color:var(--dimmer);
  font:11px/1.5 var(--mono);flex:none}

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

/* the readable part — this is what he actually reads */
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
.doc img{display:block;max-width:300px;width:100%;height:auto;border-radius:8px;
  border:1px solid var(--line);margin:4px 0 20px}
.raw{padding:18px 24px;font:12.5px/1.65 var(--mono);white-space:pre-wrap;
  word-break:break-word;overflow:auto;max-height:68vh;color:#4a4740;margin:0}
.wants{padding:8px 18px;border-bottom:1px solid var(--line2);
  font:11px var(--sans);color:var(--dimmer)}
.wants span{display:inline-block;background:var(--line2);
  border:1px solid var(--line);border-radius:4px;padding:2px 7px;
  margin:2px 4px 2px 0;color:var(--dim);font-family:var(--mono)}
.err{padding:18px 24px;color:var(--stop);font:13px/1.6 var(--mono);
  white-space:pre-wrap}
.empty{color:var(--dim);max-width:60ch;margin-top:40px}
#newout{position:fixed;right:20px;bottom:20px;z-index:60;cursor:pointer;
  background:var(--run);color:#fff;border:0;border-radius:20px;
  padding:10px 18px;font:600 13px var(--sans);box-shadow:0 3px 14px rgba(0,0,0,.18)}

/* ---------- phone ---------- */
@media (max-width: 760px){
  html,body{height:auto}
  header{padding:12px 14px;gap:8px;flex-wrap:wrap}
  header h1{font-size:16px}
  header .sub{display:none}
  .wrap{display:block;height:auto}
  .rail{border-right:0;border-bottom:1px solid var(--line);padding:10px 12px;
    position:sticky;top:49px;z-index:15;background:var(--rail)}
  .rail h2{display:none}
  #rail{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;
    -webkit-overflow-scrolling:touch}
  #rail::-webkit-scrollbar{display:none}
  .card{flex:0 0 132px;margin:0;padding:7px}
  .card img{height:58px}
  .card .t{font-size:11.5px}
  .card .m{display:none}
  main{overflow:visible}
  .inner{padding:16px 12px 80px}
  .runhead{gap:12px}
  .runhead video{width:104px}
  .runhead h2{font-size:17px}
  .panes{grid-template-columns:1fr}
  .pane.out{order:1}
  .pane.prompt{order:2;border-top:1px solid var(--line)}
  .doc{max-height:none;padding:16px 14px 26px;font-size:15px}
  .pane.prompt .doc{max-height:340px;font-size:13.5px}
  .raw{max-height:340px}
  .doc img{max-width:100%}
  .doc table{font-size:13px}
  .doc th,.doc td{padding:7px 9px}
  .stage>summary{padding:14px 13px;gap:10px}
  .pill{padding:8px 9px;font-size:12px}
  .pane h4{padding:11px 14px;flex-wrap:wrap;gap:7px}
  .pane h4 button{padding:6px 11px;font-size:12px}
}

/* live progress */
.bar{height:3px;background:var(--line2);position:relative;overflow:hidden}
.bar i{position:absolute;inset:0 auto 0 0;width:0;background:var(--run);
  transition:width .9s linear;display:block}
.bar.done i{background:var(--go);width:100%}
.bar.over i{background:var(--stop)}
.bar.idle{display:none}
.tick{font:11px/1.5 var(--mono);color:var(--run)}
.tick b{font-weight:600}
.eta{color:var(--dimmer)}
.stage.now{border-color:var(--run);box-shadow:0 0 0 1px rgba(192,124,30,.25)}
.livebadge{display:inline-flex;align-items:center;gap:6px;font:11px var(--sans);
  color:var(--dim)}
#health a{font:11.5px var(--sans);color:var(--stop);text-decoration:none;
  background:#f8e4e1;border-radius:12px;padding:4px 10px}
#health a:hover{text-decoration:underline}
#healthbox{position:fixed;right:18px;top:52px;z-index:70;background:var(--paper);
  border:1px solid var(--stop);border-radius:8px;padding:14px 16px;max-width:420px;
  box-shadow:0 6px 24px rgba(0,0,0,.14);font-size:13px;line-height:1.5;display:none}
#healthbox h5{margin:0 0 8px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;
  color:var(--dimmer)}
#healthbox li{margin-bottom:5px}
</style></head><body>

<header>
  <h1>The Swipe Machine</h1>
  <span class="sub">video in &rarr; brief out</span>
  <div class="right"><span id="health"></span><span id="livedot"></span><span class="livebadge"><span id="clock">__STAMP__</span></span></div>
</header>

<div class="wrap">
  <nav class="rail">
    <input id="q" type="search" placeholder="Search videos, category, lane…"
           autocomplete="off" oninput="rail()">
    <div id="rail"></div>
    <div id="count"></div>
  </nav>
  <main id="main"><div class="inner" id="inner"></div></main>
</div>

<script>
const RUNS = __DATA__, LIVE = __LIVE__;
const esc = s => (s||"").replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
let cur = 0;
let LIVEDATA = {};   // declared before rail() can read it
let LASTSIG = null;
let VIEWING = null;   // a past breakdown being read instead of the current one
let PENDING = false;

const KEEP = "swipe-machine-place";
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

function liveStage(r){
  const live = LIVEDATA[r.slug] || {};
  for (const k in live) if (live[k] && live[k].status === "running") return live[k];
  return null;
}

function rail(){
  const q = (document.getElementById("q")?.value || "").toLowerCase().trim();
  const hay = r => [r.label, r.brand, r.lane, r.triage?.lane, r.triage?.category,
                    r.triage?.summary].join(" ").toLowerCase();
  const shown = RUNS.map((r,i)=>({r,i})).filter(({r}) => !q || hay(r).includes(q));

  // grouped by what stage 0 decided it was
  const groups = {};
  shown.forEach(({r,i}) => {
    const k = (r.triage?.lane) || "unclassified";
    (groups[k] = groups[k] || []).push({r,i});
  });
  const order = ["ALREADY AN AD","ORGANIC","STATIC","SEQUENTIAL","unclassified"];
  const keys = Object.keys(groups).sort((a,b)=>{
    const x = order.indexOf(a), y = order.indexOf(b);
    return (x<0?99:x)-(y<0?99:y);
  });

  document.getElementById("rail").innerHTML = keys.map(k => `
    <div class="lanehead">${esc(k)} <b>${groups[k].length}</b></div>
    ${groups[k].map(({r,i})=>{
      const liveMap = LIVEDATA[r.slug] || {};
      const done = Object.keys(liveMap).length
        ? Object.values(liveMap).filter(v=>v.status==="done").length
        : r.stage_list.filter(s=>s.status==="done").length;
      const t = r.triage || {};
      const now = liveStage(r);
      return `<div class="card ${i===cur?'on':''} ${now?'working':''}" onclick="pick(${i})">
        ${now?`<div class="working-now"><span class="pulse"></span>${esc(now.name)}</div>`:""}
        ${r.poster?`<img src="runs/${r.slug}/${r.poster}" alt="">`:""}
        <div class="t">${esc(r.label)}<span class="done-pct">${done}/${r.stage_list.length}</span></div>
        <div class="cat">${t.category?esc(t.category):esc(r.brand)}</div>
        <div class="cat">${t.runtime?`<span class="tag">${esc(t.runtime)}</span>`:""}${t.ai?`<span class="tag ${t.ai!=="human"?"ai":""}">${esc(t.ai)}</span>`:""}${r.creator?`<span class="tag">${esc(r.creator)}</span>`:""}</div>
        <div class="dots">${r.stage_list.map(s=>`<div class="dot ${s.status}" title="${s.id} ${esc(s.name)}"></div>`).join("")}</div>
      </div>`;
    }).join("")}`).join("") || '<div class="empty">No match.</div>';

  document.getElementById("count").textContent =
    `${shown.length} of ${RUNS.length} video${RUNS.length===1?"":"s"}`;
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

function stageBlock(r,s){
  const done = s.status==="done", uid = r.slug+"-"+s.id;
  const stats = done
    ? `${s.seconds}s &middot; ${(s.chars_out||0).toLocaleString()} chars<br>${esc(s.model||s.engine)}`
    : (s.status==="running" ? "running&hellip;"
      : (s.status==="error" ? "stopped"
      : (s.status==="skipped" ? "skipped" : "waiting")));
  const flag = s.off_route ? '<span class="offroute-tag">off route</span>' : "";
  const body = s.status==="error"
    ? `<div class="err">${esc(s.error||"no detail")}</div>`
    : s.status==="skipped"
    ? `<div class="skipnote"><b>Skipped on purpose.</b><br>${esc(s.why||"")}</div>`
    : s.off_route
    ? `<div class="skipnote offroute"><b>This ran before the lane rule existed.</b><br>
        Under the current routing it would be skipped &mdash; ${esc(s.off_route)}.
        It did run, and the stages after it used what it produced, so the brief you
        are reading was built with it. Re-run this video to bring it in line.</div>
       <div class="doc">${s.output_html||""}</div>`
    : (done ? `<div class="doc">${s.output_html||""}</div>`
            : `<div class="doc"><p class="none">Nothing here yet &mdash; this stage has not run.</p></div>`);
  return `
  <details class="stage ${s.status==="skipped"?"skipped":""}" id="stage-wrap-${uid}" data-uid="${uid}" ontoggle="remember()">
    <summary>
      <span class="pill ${s.status}" id="pill-${uid}">${s.id}</span>
      <span><span class="sname">${esc(s.name)}</span><div class="sblurb">${esc(s.blurb)}</div></span>
      <span class="stats" id="st-${uid}">${flag}${stats}</span>
    </summary>
    <div class="bar ${s.status==='done'?'done':(s.status==='running'?'':'idle')}"
         id="bar-${uid}"><i></i></div>
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

function toggleHealth(e){
  e.preventDefault();
  const b = document.getElementById("healthbox");
  b.style.display = b.style.display === "block" ? "none" : "block";
}

function pretty(stamp){
  const m = String(stamp).match(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})/);
  return m ? `${m[3]}/${m[2]} ${m[4]}:${m[5]}` : stamp;
}

async function showVersion(path, btn){
  document.querySelectorAll(".vt").forEach(b => b.classList.remove("on"));
  btn.classList.add("on");
  const main = document.getElementById("inner");
  const body = main.querySelector("#stages");
  if(!path){ VIEWING = null; render(); return; }
  const res = await fetch(path + "?t=" + Date.now(), {cache:"no-store"});
  if(!res.ok){ return; }
  const j = await res.json();
  VIEWING = j.stage_list;
  render(true);
  document.querySelectorAll(".vt").forEach(b => b.classList.remove("on"));
  [...document.querySelectorAll(".vt")].find(b => b.textContent === btn.textContent)
    ?.classList.add("on");
}

function render(keepVersion){
  const r = RUNS[cur], m = document.getElementById("inner");
  if(!r){ m.innerHTML = `<div class="empty"><h2>No runs yet.</h2></div>`; return; }
  const done = r.stage_list.filter(s=>s.status==="done").length;
  const vers = r.versions || [];
  const tabs = vers.length ? `<div class="vertabs">
      <button class="vt on" onclick="showVersion(null,this)">Current</button>
      ${vers.map((v,n)=>`<button class="vt" title="${esc(v.note||v.rerun_from)}"
        onclick="showVersion('${v.path}',this)">${esc(pretty(v.stamp))}</button>`).join("")}
    </div>` : "";
  let out = `<div class="runhead">
    <video src="runs/${r.slug}/${r.source||''}" controls preload="metadata"
           ${r.poster?`poster="runs/${r.slug}/${r.poster}"`:""}></video>
    <div><h2>${esc(r.label)}</h2>
      <div class="meta"><b>${done}</b> of ${r.stage_list.length} stages done
      &middot; brand <b>${esc(r.brand)}</b> &middot; <b>${esc(r.lane)}</b> lane</div>
      ${tabs}</div></div>`;
  const list = (keepVersion && VIEWING) ? VIEWING : r.stage_list;
  if(!keepVersion) VIEWING = null;
  out += `<div id="stages">`;
  let g = "";
  for(const s of list){
    if(s.group !== g){ g = s.group; out += `<div class="grp">${esc(g)}</div>`; }
    out += stageBlock(r,s);
  }
  out += `</div>`;
  m.innerHTML = out;
}

rail(); render(); restore();

/* ---- live: poll the run files, tick every second, never reload the page ----
   A full reload threw away his scroll position and every open stage. This
   updates only the numbers, so he can keep reading while a stage runs.      */
const EXPECTED = __EXPECTED__;
// The label matches run order (4a..4f). The internal key matches Dayu's
// shared config, which "4a"/"4b" refer to in his own file — see chain.py.
const KEYMAP = {"0":"stage0","1":"stage1","2":"stage2","3":"stage3",
  "4a":"stage4r","4b":"stage4b","4c":"stage4a","4d":"stage4c","4e":"stage4d",
  "4f":"stage4e","5":"stage5","6":"stage6","7":"stage7","7b":"stage7b"};

function fmt(s){
  s = Math.max(0, Math.round(s));
  const m = Math.floor(s/60);
  return m ? `${m}m ${String(s%60).padStart(2,"0")}s` : `${s}s`;
}

function tick(){
  const r = RUNS[cur]; if(!r) return;
  let anyRunning = false;
  for(const s of r.stage_list){
    const uid = r.slug+"-"+s.id;
    const live = (LIVEDATA[r.slug]||{})[KEYMAP[s.id]] || {};
    const status = live.status || s.status;
    const bar = document.getElementById("bar-"+uid);
    const st = document.getElementById("st-"+uid);
    const pill = document.getElementById("pill-"+uid);
    if(!bar || !st) continue;
    // The badge is the thing he reads first. It used to keep whatever it said
    // when the page loaded, so a stage that finished while he watched still
    // read "waiting".
    if(pill && !pill.classList.contains(status)){
      pill.className = "pill " + status;
    }

    if(status === "running"){
      anyRunning = true;
      const started = Date.parse((live.started||"").replace(" ","T")) || Date.now();
      const el = (Date.now() - started)/1000;
      const exp = EXPECTED[KEYMAP[s.id]] || 180;
      const pct = Math.min(95, (el/exp)*100);
      bar.className = "bar" + (el > exp*1.5 ? " over" : "");
      bar.firstElementChild.style.width = pct.toFixed(1)+"%";
      st.innerHTML = `<span class="tick"><b>${fmt(el)}</b></span><br>` +
        `<span class="eta">${el > exp ? "longer than usual" : "usually "+fmt(exp)}</span>`;
      document.getElementById("stage-wrap-"+uid)?.classList.add("now");
    } else {
      // it was added when the stage started and never taken off, so every
      // stage that had ever run kept the highlight — three at once, all lying
      document.getElementById("stage-wrap-"+uid)?.classList.remove("now");
    }
    if(status === "done"){
      bar.className = "bar done";
      bar.firstElementChild.style.width = "100%";
      // Always rewrite it. This used to need a duration from the poll, and when
      // that was missing the amber "longer than usual" line from while it was
      // running just stayed on a finished stage.
      const secs  = live.seconds  ?? s.seconds;
      const chars = live.chars_out ?? s.chars_out;
      const model = live.model || s.model || s.engine || "";
      st.innerHTML = secs
        ? `${Math.round(secs)}s &middot; ${(chars||0).toLocaleString()} chars<br>${model}`
        : `done<br>${model}`;
    } else if(status === "error"){
      bar.className = "bar over"; bar.firstElementChild.style.width = "100%";
    }
  }
  const dot = document.getElementById("livedot");
  dot.innerHTML = anyRunning ? '<span class="pulse"></span>' : "";
  document.getElementById("clock").textContent =
    new Date().toLocaleTimeString([], {hour:"numeric", minute:"2-digit", second:"2-digit"});
}

async function poll(){
  try{
    // Poll the small file; pull the big one only when it says something moved.
    const sres = await fetch("status.json?t="+Date.now(), {cache:"no-store"});
    if(!sres.ok) return;
    const st = await sres.json();
    document.getElementById("clock").textContent = st.stamp;
    fetch("health.json?t="+Date.now(),{cache:"no-store"}).then(r=>r.ok&&r.json()).then(h=>{
      if(!h) return;
      const el = document.getElementById("health");
      const n = (h.found||[]).length;
      el.innerHTML = n ? `<a href="#" onclick="toggleHealth(event)">${n} issue${n>1?"s":""}</a>` : "";
      let box = document.getElementById("healthbox");
      if(!box){ box = document.createElement("div"); box.id="healthbox"; document.body.appendChild(box); }
      box.innerHTML = `<h5>Needs looking at</h5><ul>` +
        (h.found||[]).map(x=>`<li>${esc(x)}</li>`).join("") + `</ul>` +
        ((h.fixed||[]).length ? `<h5 style="margin-top:12px">Fixed on its own</h5><ul>` +
          h.fixed.map(x=>`<li>${esc(x)}</li>`).join("") + `</ul>` : "");
    }).catch(()=>{});
    const sig = JSON.stringify(st.sig);
    if(sig === LASTSIG) return;
    LASTSIG = sig;

    const res = await fetch("board.json?t="+Date.now(), {cache:"no-store"});
    if(res.ok){
      const j = await res.json();
      {
        const open = [...document.querySelectorAll("details.stage[open]")]
          .map(d => d.dataset.uid);
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
      }
      RUNS.forEach(r => { LIVEDATA[r.slug] = (r.stage_list||[]).reduce((a,s)=>{
        a[KEYMAP[s.id]] = s; return a; }, {}); });
    }

  }catch(e){ /* file:// blocks fetch — the 1s tick still runs */ }
}



setInterval(tick, 1000);
setInterval(poll, 2000);
poll(); tick();
</script></body></html>
"""

if __name__ == "__main__":
    print(build())
