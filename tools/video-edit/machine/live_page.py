#!/usr/bin/env python3
"""live_page.py — the live timeline: the video and every element of the edit on
one clock, in sync. the owner, 2026-09-23: "an interactive local artifact that aligns
with the timeline so I can see activation of each element as I push the video
forward or backward or hit play or pause so we can dial these timelines in. This
is the sauce."

    write(run, sheet, video, checks=None, out=None) -> Path     (run/timeline.html by default)
    python3 machine/live_page.py <run-folder> [--publish-dir <dir>]

Every lane is read straight off the cut sheet, so what lights up IS what renders.
A playhead runs across every lane; a bar lights while its element is on; clicking
or dragging anywhere on the timeline moves the video there; arrow keys step one
frame; the panel on the right says, for this exact frame, the section, the words
being said and every element that is live. The Pauses lane (T-3, 23 Sep) marks every
mid-clip pause the trim cut (red dot at the join) or kept (green span) — clicking one
jumps just before it and plays, so the pauses are reviewed here, with no separate stop. `--publish-dir` writes a folder
(index.html + the video beside it) that publishes as an artifact.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
E = html.escape

SECTION_COLOURS = ["#3AA7C9", "#E0A04A", "#9C8AE0", "#4FBF84", "#E0705E", "#8C99A6", "#D77AB0", "#A6C95A"]


def _section_names() -> dict:
    for p in [HERE, *HERE.parents]:
        f = p / "components" / "marketing-doctrine" / "frameworks.json"
        if f.exists():
            return {r["id"]: r.get("name", r["id"]) for r in json.loads(f.read_text()).get("sections") or [] if isinstance(r, dict) and r.get("id")}
    return {}


def _safe_overlay() -> dict:
    """The safe-zone overlay's data: the app buttons of the feeds this edit runs on,
    the 4:5 content band, and the named text zones — the same numbers placement uses."""
    try:
        dfl = json.loads((HERE / "defaults.json").read_text())
        sz = dfl.get("safe_zones") or {}
        use = (dfl.get("platform_surfaces") or {}).get("value") or list((sz.get("surfaces") or {}).keys())
        return {"surfaces": {k: v for k, v in (sz.get("surfaces") or {}).items() if k in use},
                "content": sz.get("content_4x5"),
                "zones": [{k: z.get(k) for k in ("id", "x", "y", "w", "h")} for z in json.loads((HERE.parent / "looks" / "placement.json").read_text()).get("zones") or []]}
    except Exception:
        return {}


def tracks_of(sheet: dict) -> tuple[list[dict], float]:
    """Every lane of the edit, as {name, note, kind, items:[{s, e, label, detail, colour?, point?}]}."""
    pics = sheet.get("picture") or []
    end = max((c["start"] + c["duration"] for c in pics), default=0.0)
    names = _section_names()
    T: list[dict] = []

    def lane(name, kind, items, note=""):
        items = [i for i in items if i["e"] > i["s"] or i.get("point")]
        if items:
            T.append({"name": name, "kind": kind, "note": note, "items": items})

    # sections — the swap unit
    secmap = sheet.get("sections")
    if secmap is None:
        import assemble as A
        secmap = A.section_map(sheet)
    col = {}
    for r in secmap:
        col.setdefault(r["section"], SECTION_COLOURS[len(col) % len(SECTION_COLOURS)])
    lane("Sections", "section", [{"s": r["start"], "e": r["end"], "label": names.get(r["section"], r["section"]), "detail": r.get("words", ""),
                                  "colour": col[r["section"]]} for r in secmap], sheet.get("framework") or "the doctrine's sections")

    # text layers
    lane("Hook / headline", "text", [{"s": o["start"], "e": o["start"] + o["duration"], "label": o.get("text", o.get("kind", "")), "detail": f'{o.get("kind", "overlay")} · on frame one' if o["start"] < .05 else o.get("kind", "overlay")}
                                      for o in sheet.get("overlays") or []])
    words = (sheet.get("captions") or {}).get("words") or []
    if words:
        import compose as C
        try:
            look = C.look_of(sheet)
            lines = C.caption_lines(words, look["max_words"])
        except Exception:
            lines = [[w] for w in words]
        lane("Captions", "text", [{"s": l[0]["start"], "e": l[-1]["end"], "label": " ".join(w["text"] for w in l),
                                   "detail": "caption" + "".join(f' · "{w["text"]}" in the script\'s spelling (heard "{w["heard"]}")' for w in l if w.get("heard"))
                                   + "".join(f' · "{w["text"]}" is not in the script — shown as heard' for w in l if w.get("unaligned"))} for l in lines],
             (sheet.get("captions") or {}).get("look") or "")
    L = sheet.get("layers") or {}
    lane("Lower thirds", "text", [{"s": x["start"], "e": x["start"] + x["duration"], "label": f'{x.get("name", "")} · {x.get("title", "")}', "detail": "name tag"} for x in L.get("lower_thirds") or [] if "start" in x])
    def ann_detail(x):
        f = x.get("follow") or {}
        if not f:
            return "drawn on its words, fixed"
        if f.get("by"):
            return f'drawn on its words · follows the {x.get("target")} ({f["by"]}, {len(f.get("keys") or [])} keyframes, smoothed)'
        return f'should follow the {x.get("target")} but nothing tracks the person here — fixed at {f.get("fell_back_to")}'
    lane("Annotations", "text", [{"s": x["start"], "e": x["start"] + x["duration"], "label": f'{x.get("kind")} · "{x.get("at_words", "")}"' + (" · follows" if (x.get("follow") or {}).get("by") else ""),
                                  "detail": ann_detail(x)} for x in L.get("annotations") or [] if x.get("start") is not None])
    lane("Platform UI", "text", [{"s": x["start"], "e": x["start"] + x["duration"], "label": f'{x.get("kind")} {x.get("handle", "")}', "detail": x.get("text") or ""} for x in L.get("platform_ui") or [] if "start" in x])
    lane("Disclaimers", "text", [{"s": x["start"], "e": x["start"] + x["duration"], "label": x.get("text") or x.get("claim", "disclaimer"), "detail": f'claim: {x.get("claim", "")}'} for x in L.get("disclaimers") or [] if "start" in x])

    # picture
    def pic_label(c):
        k = c.get("kind")
        return f'{c["id"]}' + (f' · {k}' if k and k not in ("talking", "broll") else "")
    lane("B-roll & inserts", "picture", [{"s": c["start"], "e": c["start"] + c["duration"], "label": pic_label(c), "detail": c.get("why", "")} for c in pics if c.get("roll") == "b"])
    lane("A-roll", "picture", [{"s": c["start"], "e": c["start"] + c["duration"], "label": pic_label(c) + (" · punch-in" if c.get("punch", 1) != 1 else ""), "detail": c.get("why", "")} for c in pics if c.get("roll") == "a"])
    scene_end = {}
    for c in pics:
        sc = c.get("scene") or c["id"]
        scene_end[sc] = max(scene_end.get(sc, 0), c["start"] + c["duration"])
    pz = sheet.get("pauses") or []  # T-3 (23 Sep): every pause the trim cut or kept, reviewed here — no separate stop
    lane("Pauses", "pause", [({"s": p["at"] - .12, "e": p["at"] + .12, "point": True, "jump": max(0.0, p["at"] - 1.2), "colour": "#E0705E",
                              "label": f'{p["length"]:.2f}s cut', "detail": f'{p["clip"]}: "{p.get("after", "")} … {p.get("before", "")}" — {p["length"]:.2f}s of silence, {p["removed"]:.2f}s taken out at the join (a breath left each side) · {p.get("what", "")} · click to hear the join'}
                             if p["action"] == "cut" else
                             {"s": p["start"], "e": p["end"], "jump": max(0.0, p["start"] - 1.0), "colour": "#4FBF84",
                              "label": f'{p["length"]:.2f}s kept', "detail": f'{p["clip"]}: "{p.get("after", "")} … {p.get("before", "")}" — {p["length"]:.2f}s left in (the pace dial allows {p.get("pace_max")}s) · click to hear it'})
                            for p in pz],
         f'{sum(p["action"] == "cut" for p in pz)} cut ({sum(p.get("removed", 0) for p in pz if p["action"] == "cut"):.1f}s out) · {sum(p["action"] == "kept" for p in pz)} kept — click one to hear it')
    lane("Transitions", "picture", [{"s": scene_end[t["after_scene"]] - .12, "e": scene_end[t["after_scene"]] + .12, "label": t.get("kind", "cut"), "detail": f'after {t["after_scene"]}', "point": True}
                                    for t in L.get("transitions") or [] if t.get("after_scene") in scene_end and t.get("kind", "cut") != "cut"])

    # sound
    voice = []
    if sheet.get("voice"):
        v = sheet["voice"]
        voice.append({"s": v.get("start", 0), "e": v.get("start", 0) + (v.get("duration") or end), "label": "voice read", "detail": f'{v.get("volume_db", 0)} dB'})
    voice += [{"s": c["start"], "e": c["start"] + c["duration"], "label": "own sound", "detail": f'{c["id"]} — the talking clip keeps its own sound'} for c in pics if c.get("talks")]
    voice += [{"s": v["start"], "e": v["start"] + v["duration"], "label": "voice read", "detail": v["id"]} for v in sheet.get("voice_cuts") or []]
    lane("Voice", "sound", voice, "words tick along the bottom")
    if sheet.get("music"):
        m = sheet["music"]
        lane("Music", "sound", [{"s": m.get("start", 0), "e": m.get("start", 0) + (m.get("duration") or end), "label": m.get("bank_id") or "music bed",
                                 "detail": f'{m.get("volume_db", -18)} dB · ducked under the voice' + (f' · {m["tempo_bpm"]} BPM' if m.get("tempo_bpm") else "")}])
    lane("Sound effects", "sound", [{"s": s["at"] - .1, "e": s["at"] + .35, "label": s.get("cue") or s["id"], "detail": f'for {s.get("for", "")} · lands 2 frames early', "point": True} for s in sheet.get("sfx") or []])
    lane("Room tone", "sound", [{"s": r["start"], "e": r["start"] + r["duration"], "label": "room tone", "detail": "fills a trimmed gap"} for r in sheet.get("room_tone") or []])
    return T, round(end, 3)


PAGE = r"""<meta charset="utf-8">
<title>__TITLE__</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
:root{color-scheme:dark;--bg:#0E1013;--panel:#161A1F;--panel2:#1C2128;--line:#262C35;--ink:#E7EBF0;--soft:#8A94A1;--head:#FF4D3D;
--text:#B98BE0;--picture:#3AA7C9;--sound:#4FBF84;--on:#FFFFFF;--sans:"Inter Tight",-apple-system,Arial,sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,monospace}
*{box-sizing:border-box}
html,body{background:var(--bg);color:var(--ink);margin:0;font:14px/1.45 var(--sans)}
body{padding-inline:16px;padding-block:18px 40px}
.top{display:grid;grid-template-columns:minmax(220px,340px) 1fr;gap:18px;max-width:1500px;margin:0 auto}
@media(max-width:820px){.top{grid-template-columns:1fr}}
.vid{background:#000;border:1px solid var(--line);border-radius:6px;overflow:hidden;align-self:start;position:sticky;top:env(safe-area-inset-top,0px)}
video{display:block;width:100%;aspect-ratio:9/16;background:#000}
.now{display:flex;flex-direction:column;gap:12px;min-width:0}
.hdr{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.hdr h1{font:700 1.5rem/1.1 var(--sans);margin:0;letter-spacing:-.01em}
.hdr .meta{color:var(--soft);font:400 .8rem/1 var(--mono)}
.tc{font:600 2.2rem/1 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:.02em}
.tc small{font-size:.9rem;color:var(--soft)}
.controls{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
button,select{font:600 .8rem/1 var(--mono);background:var(--panel2);color:var(--ink);border:1px solid var(--line);border-radius:5px;padding:8px 10px;cursor:pointer}
button:hover{border-color:var(--soft)} button:focus-visible,select:focus-visible{outline:2px solid var(--head);outline-offset:1px}
button.play{background:var(--head);border-color:var(--head);color:#fff;min-width:74px}
.sec{border-left:4px solid var(--c,#555);padding:8px 12px;background:var(--panel)}
.sec b{font:700 1.15rem/1.2 var(--sans)} .sec div{color:var(--soft);font-size:.85rem;margin-top:3px}
.said{font:500 1.15rem/1.5 var(--sans);min-height:1.6em;background:var(--panel);padding:10px 12px}
.said span{color:var(--soft)} .said span.w{color:var(--ink)} .said span.cur{color:#FFD84A}
.live{display:flex;flex-wrap:wrap;gap:6px;min-height:30px}
.chip{font:500 .78rem/1 var(--sans);padding:6px 8px;border-radius:4px;background:var(--panel2);border:1px solid var(--line)}
.chip i{font-style:normal;color:var(--soft);margin-right:5px;font-family:var(--mono);font-size:.7rem}
.help{color:var(--soft);font-size:.78rem}
.tlwrap{max-width:1500px;margin:18px auto 0;border:1px solid var(--line);border-radius:6px;background:var(--panel);overflow-x:auto;position:relative}
.tl{position:relative;min-width:100%;user-select:none;-webkit-user-select:none}
.row{display:grid;grid-template-columns:150px 1fr;border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:0}
.lab{position:sticky;left:0;z-index:3;background:var(--panel);padding:7px 10px;border-right:1px solid var(--line);font-weight:600;font-size:.8rem}
.lab small{display:block;font-weight:400;color:var(--soft);font-size:.68rem;font-family:var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lane{position:relative;height:38px;cursor:crosshair}
.ruler .lane{height:26px}
.tick{position:absolute;top:0;bottom:0;border-left:1px solid var(--line);font:400 10px/26px var(--mono);color:var(--soft);padding-left:3px}
.bar{position:absolute;top:6px;height:26px;border-radius:3px;background:var(--k);opacity:.38;overflow:hidden;font:500 .7rem/26px var(--sans);color:#fff;padding:0 6px;white-space:nowrap;text-overflow:ellipsis;transition:opacity .08s,box-shadow .08s;border:1px solid rgba(255,255,255,.08)}
.bar.point{border-radius:13px;text-align:center;padding:0 4px}
.bar.on{opacity:1;box-shadow:0 0 0 2px var(--on),0 0 14px color-mix(in srgb,var(--k) 70%,transparent)}
.k-text{--k:var(--text)} .k-picture{--k:var(--picture)} .k-sound{--k:var(--sound)} .k-retention{--k:#FF4D3D;opacity:.55} .k-pause{--k:#E0A04A}
.beat{position:absolute;top:4px;width:1px;height:8px;background:#FFD84A;opacity:.75}
.rt{background:var(--panel);padding:10px 12px;border-left:4px solid #FF4D3D}
.rt .sc{font:600 1.4rem/1 var(--mono)} .rt .sc small{font-size:.8rem;color:var(--soft)}
.rt ul{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:4px}
.rt li{font-size:.8rem;display:flex;gap:8px;align-items:baseline}
.rt li b{font:600 .66rem/1 var(--mono);padding:3px 5px;border-radius:3px;min-width:38px;text-align:center}
.rt li b.pass{background:#1f4d33;color:#8fe0b0} .rt li b.warn{background:#5a1f1a;color:#ffb3a8} .rt li b.info{background:#23303d;color:#9fc3e6} .rt li b.nm{background:#2a2f36;color:var(--soft)}
.rt li span{color:var(--soft)}
.word{position:absolute;bottom:2px;width:2px;height:6px;background:var(--soft);opacity:.6}
.word.on{background:#FFD84A;opacity:1;height:9px}
.head{position:absolute;top:0;bottom:0;width:2px;background:var(--head);z-index:4;pointer-events:none;box-shadow:0 0 8px var(--head)}
.head::before{content:"";position:absolute;top:0;left:-5px;border:6px solid transparent;border-top-color:var(--head)}
.vid{position:relative}
.sz{position:absolute;inset:0;pointer-events:none;font:600 9px/1.1 var(--sans);color:#fff}
.sz .ui{position:absolute;background:rgba(255,40,40,.32);border:1px dashed rgba(255,120,120,.9)}
.sz .ui span{position:absolute;left:3px;top:2px;text-shadow:0 1px 2px #000}
.sz .c45{position:absolute;left:0;right:0;border-top:1px dashed #FFD84A;border-bottom:1px dashed #FFD84A}
.sz .c45 span{position:absolute;right:3px;top:2px;color:#FFD84A;text-shadow:0 1px 2px #000}
.sz .zn{position:absolute;border:1px solid rgba(90,200,255,.9);background:rgba(90,200,255,.08)}
.sz .zn span{position:absolute;left:2px;top:1px;color:#9fe0ff;text-shadow:0 1px 2px #000}
.legend{max-width:1500px;margin:14px auto 0;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.legend b{font:600 .72rem/1 var(--mono);color:var(--soft);letter-spacing:.08em;text-transform:uppercase;margin-right:6px}
.legend span{font:500 .78rem/1 var(--sans);padding:6px 9px;border-radius:4px;border:1px solid var(--line);color:var(--soft);opacity:.55}
.legend span.used{opacity:1;color:#fff;border-color:transparent;background:var(--c)}
.legend span.cur{box-shadow:0 0 0 2px #fff}
.zoom{display:flex;align-items:center;gap:8px;color:var(--soft);font:400 .75rem/1 var(--mono)}
input[type=range]{accent-color:var(--head)}
@media (prefers-reduced-motion:reduce){.bar{transition:none}}
</style>
<div class="top">
  <div class="vid"><video id="v" src="__VIDEO__" playsinline preload="auto"></video><div class="sz" id="sz" hidden></div></div>
  <div class="now">
    <div class="hdr"><h1>__TITLE__</h1><span class="meta">__META__</span></div>
    <div class="tc" id="tc">00:00<small>:00</small></div>
    <div class="controls">
      <button class="play" id="play" type="button">▶ Play</button>
      <button type="button" data-step="-1">−1s</button><button type="button" data-frame="-1">−1f</button>
      <button type="button" data-frame="1">+1f</button><button type="button" data-step="1">+1s</button>
      <select id="rate" aria-label="Speed"><option value="0.25">0.25×</option><option value="0.5">0.5×</option><option value="1" selected>1×</option></select>
      <button type="button" id="loop" aria-pressed="false">Loop section: off</button>
      <button type="button" id="szb" aria-pressed="false">Safe zones: off</button>
    </div>
    <div class="sec" id="sec"><b>—</b><div></div></div>
    <div class="said" id="said"></div>
    <div><div class="help" style="margin-bottom:6px">Live on this frame</div><div class="live" id="live"></div></div>
    <div class="rt" id="rt" hidden></div>
    <div class="help">Space play/pause · ← → one frame · Shift+← → one second · click or drag anywhere on the timeline to jump · click a bar to jump to its start</div>
  </div>
</div>
<div class="tlwrap" id="wrap"><div class="tl" id="tl"></div></div>
<div class="legend" id="legend"></div>
<div style="max-width:1500px;margin:8px auto 0" class="zoom">Zoom <input id="zoom" type="range" min="1" max="8" step="0.5" value="1"> <span id="zv">1×</span></div>
<script>
const DATA=__DATA__;
const v=document.getElementById("v"),tl=document.getElementById("tl"),wrap=document.getElementById("wrap");
const END=DATA.end, FPS=DATA.fps||30;
let loopSec=false;
function fmt(t){t=Math.max(0,t);const m=Math.floor(t/60),s=Math.floor(t%60),f=Math.floor((t%1)*FPS);return `${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}<small>:${String(f).padStart(2,"0")}</small>`}
function pct(t){return (t/END*100).toFixed(4)+"%"}
// build lanes
const ruler=document.createElement("div");ruler.className="row ruler";ruler.innerHTML='<div class="lab">Time</div><div class="lane"></div>';tl.appendChild(ruler);
const step=END>40?5:END>15?2:1;
for(let t=0;t<=END;t+=step){const i=document.createElement("i");i.className="tick";i.style.left=pct(t);i.textContent=t+"s";ruler.lastChild.appendChild(i)}
const bars=[];
for(const tr of DATA.tracks){
  const row=document.createElement("div");row.className="row";
  row.innerHTML=`<div class="lab">${tr.name}<small title="${tr.note||""}">${tr.note||""}</small></div><div class="lane"></div>`;
  const ln=row.lastChild;
  for(const it of tr.items){
    const b=document.createElement("div");b.className=`bar k-${tr.kind}`+(it.point?" point":"");
    b.style.left=pct(it.s);b.style.width=`max(${pct(it.e-it.s)}, ${it.point?"22px":"3px"})`;
    if(it.colour)b.style.setProperty("--k",it.colour);
    b.textContent=it.label;b.title=`${it.label}${it.detail?" — "+it.detail:""}  (${it.s.toFixed(2)}–${it.e.toFixed(2)}s)`;
    b.addEventListener("click",ev=>{ev.stopPropagation();seek((it.jump??it.s)+0.001);if(tr.kind==="pause")v.play()});
    ln.appendChild(b);bars.push({el:b,it,tr});
  }
  if(tr.name==="Music")for(const b of DATA.beats||[]){const m=document.createElement("i");m.className="beat";m.style.left=pct(b);m.title=`beat ${b.toFixed(2)}s`;ln.appendChild(m)}
  if(tr.name==="Voice")for(const w of DATA.words){const m=document.createElement("i");m.className="word";m.style.left=pct(w.start);ln.appendChild(m);w.el=m}
  tl.appendChild(row);
}
const head=document.createElement("div");head.className="head";tl.appendChild(head);
// retention: the score and every rule (warnings and info — nothing here blocks the export)
if(DATA.retention){const R=DATA.retention,el=document.getElementById("rt");el.hidden=false;
  const tag={pass:"OK",warn:"WARN",info:"INFO","not measured":"—"};
  el.innerHTML=`<div class="help" style="margin-bottom:4px">Retention — warnings and a score; never blocks the export</div><div class="sc">${R.score==null?"—":R.score}<small>/100 · ${R.warnings} warning(s) · ${R.placement}</small></div><ul>`+
    R.rules.map(x=>`<li><b class="${x.status==="not measured"?"nm":x.status}">${tag[x.status]||x.status}</b><div>${x.name.replace(/</g,"&lt;")} <span>— ${x.detail.replace(/</g,"&lt;")}</span></div></li>`).join("")+"</ul>";}
// sync
function seek(t){v.currentTime=Math.min(Math.max(t,0),END-0.001);paint()}
function secAt(t){return DATA.sections.find(s=>t>=s.s&&t<s.e)}
let lastLive="";
let paint=function(){
  const t=v.currentTime;
  head.style.left=`calc(150px + (100% - 150px) * ${t/END})`;
  document.getElementById("tc").innerHTML=fmt(t);
  const live=[];
  for(const b of bars){const on=t>=b.it.s&&t<b.it.e;b.el.classList.toggle("on",on);if(on&&b.tr.name!=="Sections")live.push(`<span class="chip"><i>${b.tr.name}</i>${b.it.label.replace(/</g,"&lt;")}</span>`)}
  const lv=live.join("")||'<span class="help">nothing but the picture</span>';if(lv!==lastLive){document.getElementById("live").innerHTML=lv;lastLive=lv}
  const s=secAt(t),sec=document.getElementById("sec");
  if(s){sec.style.setProperty("--c",s.colour);sec.querySelector("b").textContent=s.label;sec.querySelector("div").textContent=`${s.s.toFixed(2)}s – ${s.e.toFixed(2)}s · the swap unit`}
  // the words being said
  let html="";for(const w of DATA.words){if(w.el)w.el.classList.toggle("on",t>=w.start&&t<w.end)}
  const near=DATA.words.filter(w=>w.start<=t+1.2&&w.end>=t-1.2);
  html=near.map(w=>`<span class="${t>=w.start&&t<w.end?"cur":t>=w.end?"w":""}">${w.text.replace(/</g,"&lt;")}</span>`).join(" ");
  document.getElementById("said").innerHTML=html||'<span>—</span>';
  if(loopSec&&s&&!v.paused&&t>=s.e-0.03){v.currentTime=s.s}
}
function tick(){paint();if(!v.paused)requestAnimationFrame(tick)}
v.addEventListener("play",()=>{document.getElementById("play").textContent="❚❚ Pause";requestAnimationFrame(tick)});
v.addEventListener("pause",()=>{document.getElementById("play").textContent="▶ Play";paint()});
v.addEventListener("seeked",()=>paint());v.addEventListener("loadedmetadata",()=>paint());
document.getElementById("play").onclick=()=>v.paused?v.play():v.pause();
document.querySelectorAll("[data-step]").forEach(b=>b.onclick=()=>{v.pause();seek(v.currentTime+ +b.dataset.step)});
document.querySelectorAll("[data-frame]").forEach(b=>b.onclick=()=>{v.pause();seek(v.currentTime+ (+b.dataset.frame)/FPS)});
document.getElementById("rate").onchange=e=>v.playbackRate=+e.target.value;
document.getElementById("loop").onclick=e=>{loopSec=!loopSec;e.target.textContent="Loop section: "+(loopSec?"on":"off");e.target.setAttribute("aria-pressed",loopSec)};
// scrub: click or drag on the timeline
function tAt(x){const r=tl.getBoundingClientRect();const lane0=r.left+150;return Math.min(END,Math.max(0,(x-lane0)/(r.width-150)*END))}
let drag=false;
tl.addEventListener("pointerdown",e=>{if(e.target.closest(".lab"))return;drag=true;v.pause();tl.setPointerCapture(e.pointerId);seek(tAt(e.clientX))});
tl.addEventListener("pointermove",e=>{if(drag)seek(tAt(e.clientX))});
tl.addEventListener("pointerup",()=>drag=false);
document.addEventListener("keydown",e=>{if(e.target.tagName==="SELECT")return;
  if(e.code==="Space"){e.preventDefault();v.paused?v.play():v.pause()}
  else if(e.key==="ArrowRight"){e.preventDefault();v.pause();seek(v.currentTime+(e.shiftKey?1:1/FPS))}
  else if(e.key==="ArrowLeft"){e.preventDefault();v.pause();seek(v.currentTime-(e.shiftKey?1:1/FPS))}});
const z=document.getElementById("zoom");z.oninput=()=>{tl.style.width=(z.value*100)+"%";document.getElementById("zv").textContent=z.value+"×";paint()};
const lg=document.getElementById("legend");lg.innerHTML="<b>All 15 sections</b>"+DATA.vocab.map(x=>{const u=DATA.sections.find(s=>s.label===x.name);return `<span data-n="${x.name}" class="${u?"used":""}" style="--c:${u?u.colour:"transparent"}" title="${x.what.replace(/"/g,"&quot;")}">${x.name}</span>`}).join("");
(function(){const z=DATA.safe||{};const el=document.getElementById("sz");let h="";
 for(const [name,m] of Object.entries(z.surfaces||{})){
  h+=`<div class="ui" style="left:0;right:0;top:0;height:${m.top_pct}%"><span>${name} top bar</span></div>`;
  h+=`<div class="ui" style="left:0;right:0;bottom:0;height:${m.bottom_pct}%"><span>${name} caption &amp; buttons</span></div>`;
  h+=`<div class="ui" style="right:0;top:${m.top_pct}%;bottom:${m.bottom_pct}%;width:${m.right_pct}%"><span>${name} icons</span></div>`;}
 if(z.content){h+=`<div class="c45" style="top:${z.content.top_pct}%;bottom:${z.content.bottom_pct}%"><span>4:5 content zone</span></div>`}
 for(const q of (z.zones||[])){h+=`<div class="zn" style="left:${q.x}%;top:${q.y}%;width:${q.w}%;height:${q.h}%"><span>${q.id}</span></div>`}
 el.innerHTML=h;
 const b=document.getElementById("szb");b.onclick=()=>{el.hidden=!el.hidden;b.textContent="Safe zones: "+(el.hidden?"off":"on");b.setAttribute("aria-pressed",String(!el.hidden))};})();
const _paint=paint;paint=function(){_paint();const s=secAt(v.currentTime);lg.querySelectorAll("span").forEach(e=>e.classList.toggle("cur",!!s&&e.dataset.n===s.label))};
paint();
</script>
"""


def retention_lane(rep: dict | None) -> dict | None:
    """The Retention lane: every WARN rule's flags at their seconds (a static hold is a red span)."""
    if not rep:
        return None
    items = [{"s": f["s"], "e": f["e"] if f["e"] > f["s"] else f["s"] + .01, "label": x["name"], "detail": f["detail"], "point": bool(f.get("point"))}
             for x in rep["rules"] if x["status"] == "warn" for f in x["flags"]]
    return {"name": "Retention", "kind": "retention", "note": f'score {rep["score"]}/100 · warnings only', "items": items} if items else None


def write(run: Path, sheet: dict, video: Path | None, checks: list | None = None, out: Path | None = None, video_href: str | None = None,
          retention: dict | None = None) -> Path:
    tracks, end = tracks_of(sheet)
    if retention is None:
        try:
            import retention as RT
            retention = RT.check(sheet, video if video and Path(video).is_file() else None)
        except Exception:
            retention = None
    rl = retention_lane(retention)
    if rl:
        tracks.insert(1, rl)
    words = [{"text": w["text"], "start": w["start"], "end": w["end"]} for w in (sheet.get("captions") or {}).get("words") or []]
    secs = [{"s": i["s"], "e": i["e"], "label": i["label"], "colour": i.get("colour")} for tr in tracks if tr["kind"] == "section" for i in tr["items"]]
    meta = sheet.get("meta") or {}
    out = out or (run / "timeline.html")
    href = video_href or (str(video.relative_to(out.parent)) if video and video.is_relative_to(out.parent) else (str(video) if video else ""))
    fails = [c for c in checks or [] if not c.get("pass")]
    meta_line = f'{meta.get("brand", "")} · {end:.1f}s · {meta.get("fps", 30)} fps · cut by {sheet.get("cut_by", "?")}' + (f' · {len(fails)} check(s) held' if fails else (" · checks pass" if checks else ""))
    vocab = []
    for pth in [HERE, *HERE.parents]:
        f = pth / "components" / "marketing-doctrine" / "frameworks.json"
        if f.exists():
            vocab = [{"id": r["id"], "name": r.get("name", r["id"]), "what": r.get("what", "")} for r in json.loads(f.read_text()).get("sections") or [] if isinstance(r, dict) and r.get("id")]
            break
    data = {"end": end, "fps": meta.get("fps", 30), "tracks": tracks, "words": words, "sections": secs, "vocab": vocab,
            "beats": (sheet.get("music") or {}).get("beats") or [], "retention": retention, "safe": _safe_overlay()}
    page = (PAGE.replace("__TITLE__", E(f'{meta.get("label", run.name)} — timeline'))
                .replace("__META__", E(meta_line)).replace("__VIDEO__", E(href))
                .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run"); ap.add_argument("--publish-dir")
    a = ap.parse_args(argv)
    run = Path(a.run).resolve()
    import run as R
    sheet_path = run / "deliverable" / "cutsheet.json"
    if not sheet_path.exists():
        sheet_path = R.latest_sheet(run)
    sheet = json.loads(Path(sheet_path).read_text())
    video = next((p for p in (run / "work" / "final.mp4", run / "work" / "captioned.mp4", run / "work" / "rough-cut.mp4") if p.exists()), None)
    checks = json.loads((run / "deliverable" / "checks.json").read_text()) if (run / "deliverable" / "checks.json").exists() else None
    rt = json.loads((run / "deliverable" / "retention.json").read_text()) if (run / "deliverable" / "retention.json").exists() else None
    if a.publish_dir:
        d = Path(a.publish_dir); d.mkdir(parents=True, exist_ok=True)
        if video:
            shutil.copy2(video, d / "video.mp4")
        print(write(run, sheet, video, checks, out=d / "index.html", video_href="video.mp4" if video else "", retention=rt))
    else:
        print(write(run, sheet, video, checks, retention=rt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
