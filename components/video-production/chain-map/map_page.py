#!/usr/bin/env python3
"""The chain map page: every piece of a chain's components and every hand-off between them, drawn from its map file.

    python3 components/video-production/chain-map/map_page.py [video]      -> runs/stage-handoff/<chain>/map.html

Reads chains/<chain>-map.json (the one source; refine the workflows there and re-draw). Writes only the page.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = REPO / "components" / "stage-handoff"          # the chain data stays there (folded 2026-11-19)
sys.path.insert(0, str(HERE))

chain = sys.argv[1] if len(sys.argv) > 1 else "video"
src = DATA / "chains" / ("%s-map.json" % chain)
out = REPO / "runs" / "stage-handoff" / chain / "map.html"
out.parent.mkdir(parents=True, exist_ok=True)
d = json.loads(src.read_text(encoding="utf-8"))
data = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
html = r'''<title>Video Chain Map</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* layout: four component bands top to bottom, a handshake band between each; tap any piece for its contract */
:root{--bg:#fafafa;--card:#fff;--line:#e4e4e7;--fg:#18181b;--mute:#71717a;--chip:#f4f4f5;
--stage:#2563eb;--gate:#d97706;--repair:#7c3aed;--sub:#0891b2;--stop:#db2777;--file:#52525b;--pack:#16a34a;--no:#dc2626;--ok:#16a34a;
--sans:"Inter",system-ui,sans-serif;--mono:"JetBrains Mono",ui-monospace,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#09090b;--card:#18181b;--line:#27272a;--fg:#fafafa;--mute:#a1a1aa;--chip:#27272a;--stage:#60a5fa;--gate:#fbbf24;--repair:#a78bfa;--sub:#22d3ee;--stop:#f472b6;--file:#a1a1aa;--pack:#4ade80;--no:#f87171;--ok:#4ade80;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#09090b;--card:#18181b;--line:#27272a;--fg:#fafafa;--mute:#a1a1aa;--chip:#27272a;--stage:#60a5fa;--gate:#fbbf24;--repair:#a78bfa;--sub:#22d3ee;--stop:#f472b6;--file:#a1a1aa;--pack:#4ade80;--no:#f87171;--ok:#4ade80;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--sans)}
.wrap{max-width:1180px;margin:0 auto;padding-block:24px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:18px}
h1{font-size:22px;margin:0;text-wrap:balance}
.lbl{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);font-weight:600}
.top{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px;display:grid;gap:6px;min-width:0}
.big{font-size:17px;font-weight:600}.sub{font-size:12px;color:var(--mute)}
.legend{display:flex;flex-wrap:wrap;gap:6px}
.lg{font-size:12px;border:1px solid var(--line);border-radius:999px;padding:3px 10px;cursor:pointer;background:var(--card);color:var(--fg);display:flex;gap:6px;align-items:center}
.lg[aria-pressed="false"]{opacity:.35}
.dot{width:9px;height:9px;border-radius:2px;flex:none}
.comp{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;display:grid;gap:10px}
.chead{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:baseline}
.cname{font-size:18px;font-weight:700}
.chip{font-size:12px;background:var(--chip);border-radius:6px;padding:2px 7px}
.door{font-family:var(--mono);font-size:11.5px;color:var(--mute);overflow-wrap:anywhere}
.lane{display:grid;gap:6px}
.lanename{font-size:12px;font-weight:600;color:var(--mute)}
.flow{display:flex;flex-wrap:wrap;gap:6px;align-items:stretch}
.p{appearance:none;border:1px solid var(--line);border-left:4px solid var(--k);background:var(--bg);color:var(--fg);border-radius:6px;padding:6px 8px;min-width:118px;max-width:190px;text-align:left;cursor:pointer;display:grid;gap:3px;font:inherit}
.p:hover,.p:focus-visible{outline:2px solid var(--k);outline-offset:1px}
.p .pn{font-size:12.5px;font-weight:600;line-height:1.25}
.p .pk{font-size:10.5px;color:var(--mute);display:flex;gap:4px;flex-wrap:wrap}
.tag{font-size:10px;border-radius:4px;padding:0 4px;background:var(--chip)}
.tag.sk{color:var(--stop)}
.p.hid{display:none}
.seam{border:1px dashed var(--line);border-radius:10px;padding:12px 14px;display:grid;grid-template-columns:1fr 1fr;gap:10px 18px;background:transparent}
.seam .st{grid-column:1/-1;display:flex;gap:8px;align-items:center;font-weight:700;font-size:14px}
.seam .arrow{color:var(--mute)}
.seam p{margin:0;font-size:12.5px;line-height:1.45;min-width:0;overflow-wrap:anywhere}
.gaps{grid-column:1/-1;display:grid;gap:4px;margin:0;padding:0;list-style:none}
.gaps li{font-size:12.5px;display:flex;gap:8px;line-height:1.4}
.m{font-weight:700;flex:none;width:14px}.no{color:var(--no)}.ok{color:var(--ok)}
.panel{position:fixed;right:max(12px,env(safe-area-inset-right,0px));bottom:max(12px,env(safe-area-inset-bottom,0px));width:min(440px,calc(100vw - 24px));max-height:70vh;overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.18);padding:14px;display:grid;gap:8px;z-index:20}
.panel[hidden]{display:none}.panel h3{margin:0;font-size:15px}
.panel dl{margin:0;display:grid;grid-template-columns:72px minmax(0,1fr);gap:5px 10px;font-size:12.5px}
.panel dt{color:var(--mute)}.panel dd{margin:0;overflow-wrap:anywhere}
.panel code{font-family:var(--mono);font-size:11.5px}
.x{justify-self:end;border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:6px;padding:2px 8px;cursor:pointer}
.across li{font-size:13px}
@media (max-width:700px){.top{grid-template-columns:1fr}.seam{grid-template-columns:1fr}.p{max-width:none;flex:1 1 140px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<div class="wrap">
  <div style="display:grid;gap:4px"><span class="lbl">Video chain · as the code runs it · 17 Nov</span><h1>Every piece of the four components, and every hand-off between them</h1></div>
  <div class="top" id="top"></div>
  <div class="legend" id="legend" aria-label="Show or hide kinds"></div>
  <div id="map" style="display:grid;gap:14px"></div>
  <div class="box"><span class="lbl">Across the whole chain</span><ul class="gaps across" id="across"></ul></div>
  <span class="sub">Source: components/stage-handoff/chains/video-map.json — read from the code, file:line on every piece. Tap a piece for what it reads, writes and what holds it.</span>
</div>
<div class="panel" id="panel" hidden></div>
<script>
const D = __DATA__;
const K = {stage:["Model step","--stage"],gate:["Check that can hold","--gate"],repair:["Repair / retry","--repair"],"sub-process":["Calls another tool","--sub"],"owner-stop":["Waits for a person","--stop"],filing:["Files / stores","--file"],pack:["Hand-off pack","--pack"],station:["Station","--stage"],step:["Step","--stage"]};
const kindOf = k => (k||"").split("+")[0];
const color = k => "var(" + ((K[kindOf(k)]||K.step)[1]) + ")";
const shown = new Set(Object.keys(K));
const esc = s => String(s==null?"":s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let all = [], gaps = 0;
D.seams.forEach(s => gaps += (s.gaps||[]).length);
function lanes(c){ if (c.pieces && c.pieces.length) return [{name:"", pieces:c.pieces}]; return (c.lines||c.roads||[]).map(l => ({name:l.name, pieces:l.pieces})); }
D.components.forEach(c => lanes(c).forEach(l => l.pieces.forEach(p => all.push(p))));
const stops = all.filter(p => kindOf(p.kind)==="owner-stop").length, holds = all.filter(p => kindOf(p.kind)==="gate").length;
document.getElementById("top").innerHTML =
 `<div class="box"><span class="lbl">Mapped</span><span class="big">${all.length} pieces · 4 components</span><span class="sub">${holds} checks · ${stops} person stops</span></div>
  <div class="box"><span class="lbl">Hand-offs that don't meet</span><span class="big"><span class="no">✗</span> ${gaps} gaps on 4 seams</span><span class="sub">Red marks between the components below</span></div>
  <div class="box"><span class="lbl">Biggest one</span><span class="big"><span class="no">✗</span> Production → edit</span><span class="sub">No builder makes the folder the edit line's own door accepts</span></div>`;
const lg = document.getElementById("legend");
Object.entries(K).filter(([k]) => !["station","step"].includes(k)).forEach(([k,[name,v]]) => {
  const b = document.createElement("button"); b.className="lg"; b.setAttribute("aria-pressed","true");
  b.innerHTML = `<span class="dot" style="background:var(${v})"></span>${name}`;
  b.onclick = () => { const on = b.getAttribute("aria-pressed")==="true"; b.setAttribute("aria-pressed", on?"false":"true");
    on ? shown.delete(k) : shown.add(k); if (k==="stage"){ on? (shown.delete("station"),shown.delete("step")) : (shown.add("station"),shown.add("step")); } filter(); };
  lg.appendChild(b);
});
function filter(){ document.querySelectorAll(".p").forEach(el => el.classList.toggle("hid", !shown.has(el.dataset.k))); }
const map = document.getElementById("map"); let idx = 0; const byId = {};
D.components.forEach((c, ci) => {
  const sec = document.createElement("section"); sec.className="comp";
  let h = `<div class="chead"><span class="cname">${esc(c.id)}</span><span class="chip">skill: ${esc(c.skill)}</span></div><div class="door">${esc(c.door)}</div>`;
  lanes(c).forEach(l => {
    h += `<div class="lane">${l.name?`<span class="lanename">${esc(l.name)}</span>`:""}<div class="flow">`;
    l.pieces.forEach(p => { const id = "p"+(idx++); byId[id] = Object.assign({comp:c.id, lane:l.name}, p);
      const extra = [p.model?`<span class="tag">${esc(String(p.model).split(" ")[0])}</span>`:"", p.skill?`<span class="tag sk">${esc(p.skill)}</span>`:"", (p.subs&&p.subs.length)?`<span class="tag">+${p.subs.length} calls</span>`:"", p.holds&&p.holds!=="never"?`<span class="tag" style="color:var(--gate)">holds</span>`:""].join("");
      h += `<button class="p" data-id="${id}" data-k="${kindOf(p.kind)}" style="--k:${color(p.kind)}"><span class="pn">${esc(p.name)}</span><span class="pk"><span>${esc(p.kind)}</span>${extra}</span></button>`; });
    h += `</div></div>`;
  });
  sec.innerHTML = h; map.appendChild(sec);
  const s = D.seams.find(x => x.from === c.id);
  if (s) { const el = document.createElement("div"); el.className="seam";
    el.innerHTML = `<div class="st"><span>${esc(s.from)}</span><span class="arrow">→</span><span>${esc(s.to)}</span><span class="sub" style="font-weight:400">${s.hand_off?"· hand-off: "+esc(s.hand_off):""}</span></div>
      <p><span class="lbl">Hands over</span><br>${esc(s.handed)}</p><p><span class="lbl">Next door reads</span><br>${esc(s.door_reads)}</p>
      <ul class="gaps">${(s.gaps||[]).map(g => `<li><span class="m no">✗</span><span>${esc(g)}</span></li>`).join("") || `<li><span class="m ok">✓</span>Meets cleanly</li>`}</ul>`;
    map.appendChild(el); }
});
document.getElementById("across").innerHTML = D.across.map(a => `<li><span class="m no">✗</span><span>${esc(a)}</span></li>`).join("");
const panel = document.getElementById("panel");
const row = (k, v) => v && (!Array.isArray(v) || v.length) ? `<dt>${k}</dt><dd>${Array.isArray(v)? v.map(esc).join("<br>") : `<code>${esc(v)}</code>`}</dd>` : "";
map.addEventListener("click", e => { const b = e.target.closest(".p"); if (!b) return; const p = byId[b.dataset.id];
  panel.innerHTML = `<button class="x" aria-label="Close">Close</button><span class="lbl">${esc(p.comp)}${p.lane?" · "+esc(p.lane):""} · ${esc(p.kind)}</span><h3>${esc(p.name)}</h3>
   <dl>${row("Runs",p.runs)}${row("Prompt",p.prompt)}${row("Model",p.model)}${row("Skill",p.skill)}${row("Reads",p.reads)}${row("Writes",p.writes)}${row("Calls",p.subs)}${row("Holds",p.holds)}${row("Repair",p.repair)}${row("When",p.when)}</dl>`;
  panel.hidden = false; panel.querySelector(".x").onclick = () => panel.hidden = true; });
document.addEventListener("keydown", e => { if (e.key === "Escape") panel.hidden = true; });
</script>
'''
out.write_text(html.replace("__DATA__", data), encoding="utf-8")
print(out)
