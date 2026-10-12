"""Core Message — the one thing each brand's biggest-spending ads are saying, under every format and angle.

Reads each brand's brands/<brand>/brand-identity/core-message/ (top-spenders.json, the 20 biggest spenders;
core-message.json (Step 2 of lab/media-buying/prompts/core-message-damon.md), and the prompt itself, shown verbatim.
Writes lab/media-buying/core-message.html and the Markdown copy CORE-MESSAGE-damon.md.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRANDS = ROOT / "brands"   # each brand's core message lives at brands/<brand>/brand-identity/core-message/ (the owner, 5 Oct)
PROMPT = ROOT / "lab/media-buying/prompts/core-message-damon.md"
OUT = ROOT / "lab/media-buying/core-message.html"
MD = ROOT / "lab/media-buying/CORE-MESSAGE-damon.md"
NAMES = {"brand-b": "Brand B", "brand-a": "Brand A"}


def build():
    brands = {}
    for b in NAMES:
        home = BRANDS / b / "brand-identity/core-message"
        f = home / "core-message.json"
        if not f.exists():
            continue
        c = json.loads(f.read_text())
        if c.get("second_message") and not c["second_message"].get("spend_share"):
            c["second_message"] = None          # "none" written as an object with 0% share
        top = {b: json.loads((home / "top-spenders.json").read_text())}
        ads = {a["n"]: a for a in top[b]["ads"]}
        per = {p["n"]: p for p in c.get("per_ad", [])}
        rows = [{"n": n, "name": a["ad_name"][:70], "spend": a["spend"], "sales": a["purchases"], "cpa": a["cpa"],
                 "message": (per.get(n) or {}).get("message", ""), "messenger": (per.get(n) or {}).get("messenger", ""),
                 "partial": (per.get(n) or {}).get("partial", False)} for n, a in sorted(ads.items())]
        brands[b] = {**c, "ads": rows, "total_spend": top[b]["total_spend"], "top20_share": top[b]["top20_spend_share"],
                     "window": top[b]["window"], "left_out": top[b].get("left_out_by_damon") or []}
    v = ROOT / "tools/video-teardown/prompts/stage-1-teardown/stage1-teardown-v15-damon.md"
    wired = v.read_text().split("**6. THE CORE MESSAGE**", 1)[1].split("Give me a really clean output", 1)[0] if v.exists() else ""
    data = {"brands": brands, "prompt": PROMPT.read_text(),
            "wired": ("THE CORE MESSAGE" + wired).strip() if wired else ""}
    OUT.write_text(TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    write_md(brands)
    return brands


def write_md(brands):
    L = ["# Core Message — the owner", "", "The one thing each brand's 20 biggest-spending ads say, under every format and angle. "
         "Prompt: `lab/media-buying/prompts/core-message-damon.md`.", ""]
    for b, B in brands.items():
        L += [f"# {NAMES[b]}", "", f"**The core message:** {B['core']}", "",
              f"Carried by {B['core_spend_share']}% of the top-20 spend (the top 20 = {B['top20_share']}% of all ${B['total_spend']:,}).", ""]
        if B.get("second_message"):
            s = B["second_message"]
            L += [f"**Second message ({s['spend_share']}%):** {s['text']}", ""]
        L += ["## The beliefs under it", ""] + [f"- **{x['belief']}** — {x['spend_share']}% · \"{x['best_line']}\" (ad {x['from_ad']})" for x in B.get("beliefs", [])] + [""]
        L += ["## The delivery", ""] + [f"- **{x['what']}:** {x['detail']} — {x['spend_share']}%" for x in B.get("delivery", [])] + [""]
        L += ["## Free to change (angle, not message)", ""] + [f"- **{x['kind']}:** " + " · ".join(x["items"]) for x in B.get("angle", [])] + [""]
        if B.get("breaks"):
            L += ["## Where it breaks", ""] + [f"- Ad {x['ad']}: {x['message']} — CPA ${x['cpa']} vs ${x['vs_core_cpa']}" for x in B["breaks"]] + [""]
        L += ["## The 20 ads", "", "| # | Ad | Spend | CPA | Its message |", "|---|---|---|---|---|"]
        L += [f"| {a['n']} | {a['name']} | ${a['spend']:,} | ${a['cpa']} | {a['message']}{' *(partial)*' if a['partial'] else ''} |" for a in B["ads"]] + [""]
    MD.write_text("\n".join(L) + "\n")


TEMPLATE = r"""<title>Core Message</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800&family=Figtree:wght@400;500;600&display=swap">
<style>
:root{--bg:#f5f4f0;--panel:#fff;--ink:#17191c;--soft:#6a6f76;--line:#e3e1da;--accent:#9a5b12;--accent-soft:#f6ead9;--go:#1d7a4c;--stop:#a3302a;--bar:#e9e6de;
--display:"Fraunces",Georgia,serif;--body:"Figtree","Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121315;--panel:#1a1c1f;--ink:#ecebe6;--soft:#9aa0a8;--line:#2a2d31;--accent:#e2a65c;--accent-soft:#3a2b17;--go:#6fd39b;--stop:#f08a80;--bar:#2a2d31;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#121315;--panel:#1a1c1f;--ink:#ecebe6;--soft:#9aa0a8;--line:#2a2d31;--accent:#e2a65c;--accent-soft:#3a2b17;--go:#6fd39b;--stop:#f08a80;--bar:#2a2d31;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:15px/1.55 var(--body)}
.w{max-width:960px;margin:0 auto;padding-inline:16px;padding-block:28px 64px;display:grid;gap:18px}
h1{font:800 2.3rem/1.05 var(--display);margin:0}h2{font:600 1.15rem/1.3 var(--display);margin:0}p{margin:0}
.soft{color:var(--soft)}.lab{font-size:.72rem;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--soft)}
.tabs{display:flex;gap:8px;flex-wrap:wrap}.tabs button{font:600 1rem var(--body);border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:10px;padding:8px 16px;cursor:pointer}
.tabs button[aria-selected="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.hero{background:var(--accent-soft);border-radius:14px;padding:22px;display:grid;gap:12px}
.hero blockquote{margin:0;font:600 1.6rem/1.3 var(--display);text-wrap:balance}
.meter{display:grid;gap:4px}.track{height:10px;background:var(--bar);border-radius:99px;overflow:hidden;display:flex}.track i{display:block;height:10px}
.sec{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;display:grid;gap:10px;min-width:0}
.row{display:grid;grid-template-columns:minmax(0,1fr) 120px;gap:12px;align-items:start;padding:10px 0;border-top:1px solid var(--line)}.row:first-of-type{border-top:0}
.row b{font-weight:600}.row q{display:block;color:var(--soft);font-size:.9rem;margin-top:2px}
.pct{font-variant-numeric:tabular-nums;font-weight:600;text-align:right}.pct .track{margin-top:4px;height:6px}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chips span{background:var(--bar);border-radius:999px;padding:3px 10px;font-size:.84rem}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.86rem}th,td{text-align:left;padding:7px 8px;border-top:1px solid var(--line);vertical-align:top}
th{font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--soft);font-weight:600}td.n{font-variant-numeric:tabular-nums;white-space:nowrap}
.part{font-size:.7rem;color:var(--accent);font-weight:600}
.brk{color:var(--stop);font-weight:600}
pre{white-space:pre-wrap;font:13px/1.5 ui-monospace,Menlo,monospace;background:var(--bg);border-radius:8px;padding:12px;margin:0;max-height:520px;overflow:auto}
details summary{cursor:pointer;font-weight:600}
@media (max-width:560px){.row{grid-template-columns:1fr}.pct{text-align:left}.hero blockquote{font-size:1.3rem}}
button:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
</style>
<div class="w">
<header style="display:grid;gap:8px"><span class="lab">The backbone of every campaign</span><h1>Core Message</h1>
<p class="soft">What each brand's 20 biggest-spending ads are really saying, once you take away the format, the angle and the named problem. Any new ad, in any format, should say this.</p></header>
<div class="tabs" role="tablist" id="tabs"></div>
<div id="page" style="display:grid;gap:18px"></div>
<section class="sec" id="wiredSec"><h2>Now part of every breakdown and every brief</h2>
<p class="soft" style="font-size:.88rem">Every video and image breakdown now ends with this step, word for word. Every brief, for video and image and for both AI and creator, now opens with the ad's <b>Core message:</b> line, and any scene or slide that doesn't carry it gets flagged for you.</p>
<pre id="wired"></pre></section>
<details class="sec"><summary>The prompt that made this page (word for word)</summary><pre id="prompt"></pre></details>
</div>
<script>
(function(){
const D=__DATA__;const NAMES={"brand-b":"Brand B","brand-a":"Brand A"};
const keys=Object.keys(D.brands);let brand=keys[0];try{const s=localStorage.getItem("cm-brand");if(s&&D.brands[s])brand=s}catch(e){}
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const money=n=>"$"+Math.round(n).toLocaleString();
const bar=(p,c)=>`<div class="track"><i style="width:${Math.max(0,Math.min(100,p))}%;background:${c||"var(--accent)"}"></i></div>`;
function render(){
  $("tabs").innerHTML=Object.keys(NAMES).map(b=>D.brands[b]?`<button type="button" role="tab" data-b="${b}" aria-selected="${b===brand}">${NAMES[b]}</button>`:`<button type="button" disabled title="still being analysed">${NAMES[b]} · in progress</button>`).join("");
  const B=D.brands[brand];const s2=B.second_message;const other=Math.max(0,100-B.core_spend_share-(s2?s2.spend_share:0));
  $("page").innerHTML=`
  <section class="hero"><span class="lab">${NAMES[brand]} · the core message</span><blockquote>${esc(B.core)}</blockquote>
    <div class="meter">${`<div class="track"><i style="width:${B.core_spend_share}%;background:var(--accent)"></i>${s2?`<i style="width:${s2.spend_share}%;background:var(--soft)"></i>`:""}</div>`}
    <span class="soft" style="font-size:.85rem"><b style="color:var(--ink)">${B.core_spend_share}%</b> of the top-20 spend says this${s2?` · ${s2.spend_share}% says something else (below)`:""}${other>0.5?` · ${other.toFixed(1)}% couldn't be placed`:""}. The top 20 are ${B.top20_share}% of all ${money(B.total_spend)} spent${B.left_out.length?` (left out, as you asked: ${B.left_out.map(esc).join(", ")})`:""}.</span></div>
    ${s2?`<p style="font-size:.92rem"><b>The other message:</b> ${esc(s2.text)} <span class="soft">— ads ${s2.ads.join(", ")} · ${s2.spend_share}%</span></p>`:""}
  </section>
  <section class="sec"><h2>The beliefs it rests on</h2><p class="soft" style="font-size:.85rem">What the viewer has to accept on the way. Every ad that works lands most of these.</p>
    ${B.beliefs.map(x=>`<div class="row"><div><b>${esc(x.belief)}</b><q>“${esc(x.best_line)}” — ad ${x.from_ad}</q></div><div class="pct">${x.spend_share}% · ${x.ads.length} ads${bar(x.spend_share)}</div></div>`).join("")}</section>
  <section class="sec"><h2>How it's delivered</h2>
    ${B.delivery.map(x=>`<div class="row"><div><b>${esc(x.what)}</b> — ${esc(x.detail)}</div><div class="pct">${x.spend_share}% · ${x.ads.length} ads${bar(x.spend_share,"var(--go)")}</div></div>`).join("")}</section>
  <section class="sec"><h2>Free to change</h2><p class="soft" style="font-size:.85rem">These varied across the winners while the message held. A new ad can pick any of them.</p>
    ${B.angle.map(x=>`<div><span class="lab">${esc(x.kind)}</span><div class="chips" style="margin-top:6px">${x.items.map(i=>`<span>${esc(i)}</span>`).join("")}</div></div>`).join("")}</section>
  ${B.breaks&&B.breaks.length?`<section class="sec"><h2>Where it breaks</h2>${B.breaks.map(x=>`<div class="row"><div>Ad ${x.ad}: ${esc(x.message)}</div><div class="pct">CPA $${x.cpa}<br><span class="soft" style="font-weight:400">core ads $${x.vs_core_cpa}</span></div></div>`).join("")}</section>`:""}
  <section class="sec"><h2>The 20 ads</h2><div class="tbl"><table><thead><tr><th>#</th><th>Ad</th><th>Spend</th><th>CPA</th><th>Its message</th></tr></thead><tbody>
    ${B.ads.map(a=>`<tr><td class="n">${a.n}</td><td>${esc(a.name)}</td><td class="n">${money(a.spend)}</td><td class="n">$${a.cpa}</td><td>${esc(a.message)}${a.partial?` <span class="part">captions only</span>`:""}</td></tr>`).join("")}</tbody></table></div></section>`;
}
$("prompt").textContent=D.prompt;$("wired").textContent=D.wired;if(!D.wired)$("wiredSec").hidden=true;
document.addEventListener("click",e=>{const t=e.target.closest(".tabs button[data-b]");if(!t)return;brand=t.dataset.b;try{localStorage.setItem("cm-brand",brand)}catch(_){}render()});
render();
})();
</script>
"""

if __name__ == "__main__":
    for b, B in build().items():
        print(b, B["core_spend_share"], B["core"][:90])
