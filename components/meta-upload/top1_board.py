#!/usr/bin/env python3
"""top1_board — The Top 1% Board: each brand's winning ads on one page, and where each one is in the
breakdown → learning → new copy road.

    top1_board.py      reads runs/media-buying/top1/board.json, writes lab/media-buying/top1-board.html
                       (+ TOP1-BOARD-damon.md)

the owner, 2 Oct 2026: "let's just do the top 1%. Let's build a board for them, and then we have to run the breakdown
process on them, learn from them, and do some innovative copywriting with our different formats going forward" —
"When you have stuff that works, you just double down on it … The underlying message is basically the same."
board.json is built from tiers.py's top-1% rows (warehouse, no Meta calls); each winner's `breakdown` fills in as
its breakdown runs.
"""
import html, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
SRC = WS / "runs/media-buying/top1/board.json"
OUT = WS / "lab/media-buying/top1-board.html"


def main():
    data = json.loads(SRC.read_text())
    OUT.write_text(TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    md = ["# The Top 1% Board", "", "Each brand's top 1% of ads (ranked by purchases, duplicates folded), and where each is in "
          "breakdown → learning → new copy. Source `top1-board.html`, built by `components/meta-upload/top1_board.py`.", ""]
    for b, d in data.items():
        md += [f"## {b.upper()} — {len(d['winners'])} ads = {d['share']}% of purchases ({d['window']['from']} → {d['window']['to']})", ""]
        for w in d["winners"]:
            bd = "breakdown done" if w.get("breakdown") else "breakdown not run"
            md.append(f"{w['rank']}. {w['ads'][0]['ad_name']} — {int(w['purchases'])} sales, ${w['spend']:,.0f}, CPA ${w['cpa']}, "
                      f"ROAS {w['roas']} · {len(w['ads'])} ads · {w['files_total']} files on Drive · {bd}")
        md.append("")
    (OUT.parent / "TOP1-BOARD-damon.md").write_text("\n".join(md) + "\n")
    print(f"wrote {OUT.relative_to(WS)}")


TEMPLATE = r'''<title>The Top 1% Board</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Figtree:wght@400;500;600&display=swap">
<style>
/* Layout: a gallery of winners — brand switch, the road (board → breakdown → learn → new copy → variations), then one wide card per winner: the creative left, its numbers, message and road status right */
:root{
  --bg:#f6f7f4; --panel:#ffffff; --ink:#15181c; --soft:#69717b; --line:#e4e6e0; --gold:#9a6b00; --gold-soft:#f7edd6;
  --top:#1d7a4c; --top-soft:#e1f1e7; --ask:#2f4fbf; --ask-soft:#e6ebfa; --grey:#a4aab2; --grey-soft:#eceee9;
  --display:"Bricolage Grotesque","Avenir Next","Segoe UI",sans-serif; --body:"Figtree","Helvetica Neue",Arial,sans-serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#111316; --panel:#181b1f; --ink:#e8eae6; --soft:#98a0aa; --line:#272b31; --gold:#e8b45a; --gold-soft:#3a2d12;
  --top:#6fd39b; --top-soft:#17301f; --ask:#93a9f6; --ask-soft:#1d2645; --grey:#5d646d; --grey-soft:#24282d; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#111316; --panel:#181b1f; --ink:#e8eae6; --soft:#98a0aa; --line:#272b31; --gold:#e8b45a; --gold-soft:#3a2d12;
  --top:#6fd39b; --top-soft:#17301f; --ask:#93a9f6; --ask-soft:#1d2645; --grey:#5d646d; --grey-soft:#24282d; color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:15px/1.5 var(--body)}
.w{max-width:1040px;margin:0 auto;padding-inline:16px;padding-block:28px 64px;display:grid;gap:16px}
h1{font:800 2.3rem/1.05 var(--display);margin:0;letter-spacing:-.02em}h2{font:600 1.1rem var(--display);margin:0}p{margin:0}.soft{color:var(--soft)}
.lab{font-size:.72rem;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--soft)}
.top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:end;gap:12px}
.seg{display:inline-flex;background:var(--grey-soft);border-radius:9px;padding:3px;gap:2px}
.seg button{font:600 .9rem var(--body);border:0;background:transparent;color:var(--soft);border-radius:7px;padding:7px 14px;cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--panel);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}
.road{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:.85rem}
.road span{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 10px}.road i{font-style:normal;color:var(--grey)}
.road .on{background:var(--gold-soft);border-color:transparent;color:var(--gold);font-weight:600}
.lead{font:600 1.05rem var(--display)}.lead b{color:var(--gold)}
.win{background:var(--panel);border:1px solid var(--line);border-radius:14px;display:grid;grid-template-columns:280px minmax(0,1fr);overflow:hidden}
.pic{background:#000;position:relative;min-height:420px}
.pic img{width:100%;height:100%;object-fit:contain;display:block;position:absolute;inset:0}
.pic .none{position:absolute;inset:0;display:grid;place-items:center;text-align:center;padding:12px;font-size:.85rem;color:#c9ced8;background:var(--grey-soft)}.pic .none a{color:var(--ask)}
.rk{position:absolute;left:10px;top:10px;background:var(--gold);color:var(--panel);font:800 1rem var(--display);border-radius:8px;padding:2px 9px}
.body{padding:16px 18px;display:grid;gap:10px;align-content:start;min-width:0}
.nm{font:600 1.05rem var(--display);overflow-wrap:anywhere}
.nums{display:grid;grid-template-columns:repeat(auto-fit,minmax(92px,1fr));gap:8px}
.n{background:var(--bg);border-radius:8px;padding:8px 10px;display:grid}.n b{font:800 1.15rem var(--display);font-variant-numeric:tabular-nums}.n span{font-size:.74rem;color:var(--soft)}
.msg{border-left:3px solid var(--gold);padding-left:12px;font-size:.92rem;white-space:pre-line;overflow-wrap:anywhere;max-height:9.5em;overflow:hidden;position:relative}
.msg.open{max-height:none}
.more{font:600 .82rem var(--body);background:none;border:0;color:var(--ask);cursor:pointer;padding:0;justify-self:start}
.hl{font-size:.85rem}.hl b{color:var(--soft);font-weight:600}
.status{display:flex;flex-wrap:wrap;gap:6px}
.st{font-size:.76rem;font-weight:600;border-radius:999px;padding:3px 10px;background:var(--grey-soft);color:var(--soft)}
.st.ok{background:var(--top-soft);color:var(--top)}.st.next{background:var(--ask-soft);color:var(--ask)}
.links{display:flex;flex-wrap:wrap;gap:14px;font-size:.85rem}.links a{color:var(--ask);text-decoration:none}.links a:hover{text-decoration:underline}
details summary{cursor:pointer;font-size:.85rem;color:var(--soft);font-weight:600}
details ul{margin:6px 0 0;padding-left:1.1em;font-size:.78rem;display:grid;gap:2px;overflow-wrap:anywhere;color:var(--soft)}
.bd{background:var(--top-soft);border-radius:10px;padding:12px;display:grid;gap:6px;font-size:.9rem}
@media (max-width:680px){.win{grid-template-columns:1fr}.pic{min-height:440px}}
button:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid var(--ask);outline-offset:2px}
</style>
<div class="w">
<div class="top"><div style="display:grid;gap:6px"><span class="lab">Double down on what works</span><h1>The Top 1% Board</h1></div>
<div class="seg" id="btabs"><button type="button" data-b="brand-a" aria-pressed="true">Brand A</button><button type="button" data-b="brand-b" aria-pressed="false">Brand B</button></div></div>
<p class="lead" id="lead"></p>
<div class="road"><span class="on">1 · The board</span><i>›</i><span>2 · Break each one down</span><i>›</i><span>3 · Why it works</span><i>›</i><span>4 · New copy in our formats</span><i>›</i><span>5 · Variations: same message, new format or angle</span></div>
<div id="core"></div>
<div id="list" style="display:grid;gap:14px"></div>
<p class="soft" style="font-size:.8rem" id="foot"></p>
</div>
<script>
(function(){
const D=__DATA__;
let brand="brand-a";
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const money=v=>v==null?"—":"$"+Math.round(v).toLocaleString();
const name=w=>w.ads[0].ad_name.split(" - ")[0];
function card(w,i){
  const kind={set:"flexible ad · "+((w.media||[]).length)+" videos/images",video:"video",image:"image",ad:"no media on file"}[w.kind]||w.kind;
  const msg=(w.primary||[])[0]||"";
  const bd=w.breakdown;
  return `<article class="win"><div class="pic">${w.pic?`<img src="${w.pic}" alt="">`:`<div class="none">No file found for this one<br>${w.ig?`<a href="${esc(w.ig)}" target="_blank" rel="noopener">Watch the ad ↗</a>`:""}</div>`}<span class="rk">#${w.rank}</span>${w.pic_from==="best guess from the Drive"?'<span style="position:absolute;left:10px;bottom:10px;font-size:.72rem;font-weight:600;background:rgba(0,0,0,.65);color:#fff;border-radius:5px;padding:2px 7px">best guess</span>':""}</div>
  <div class="body"><div class="nm">${esc(name(w))}</div>
  <div class="soft" style="font-size:.82rem">${esc(kind)} · ran in ${w.ads.length} ad${w.ads.length===1?"":"s"} · ${esc(w.first)} → ${esc(w.last)}</div>
  <div class="nums"><div class="n"><b>${Math.round(w.purchases).toLocaleString()}</b><span>sales</span></div><div class="n"><b>${money(w.spend)}</b><span>spend</span></div><div class="n"><b>${money(w.cpa)}</b><span>CPA</span></div><div class="n"><b>${w.roas==null?"—":w.roas.toFixed(2)+"×"}</b><span>ROAS</span></div></div>
  ${msg?`<div class="msg" id="m${i}">${esc(msg)}</div><button type="button" class="more" data-m="m${i}">Show the whole text</button>`:'<p class="soft">No words on file.</p>'}
  ${(w.headlines||[]).length?`<div class="hl"><b>Headlines</b> ${w.headlines.slice(0,4).map(esc).join(" · ")}</div>`:""}
  ${w.note?`<div class="soft" style="font-size:.82rem">${esc(w.note)}</div>`:""}
  ${bd?`<div class="bd"><div><b>The message</b> ${esc(bd.message||"")}</div>
    <div class="soft" style="font-size:.84rem"><b>Hook:</b> ${esc(bd.hook||"")}</div>
    <div class="soft" style="font-size:.84rem"><b>Format:</b> ${esc(bd.format||"")}</div>
    <details><summary>Why it works</summary><ul>${(bd.why_it_works||[]).map(x=>`<li>${esc(x)}</li>`).join("")}</ul></details>
    <details><summary>Keep · and three variations to make</summary><p style="font-size:.84rem;margin-top:6px"><b>Keep:</b> ${esc(bd.keep||"")}</p><ul>${(bd.vary||[]).map(x=>`<li>${esc(x)}</li>`).join("")}</ul></details>
    ${bd.flags&&String(bd.flags).toLowerCase()!=="none"?`<details><summary style="color:var(--gold)">Against today's brand rules</summary><ul>${(Array.isArray(bd.flags)?bd.flags:[bd.flags]).map(x=>`<li>${esc(x)}</li>`).join("")}</ul></details>`:""}</div>`:""}
  <div class="status"><span class="st ${w.files_total||w.ig?"ok":""}">${w.files_total?w.files_total+" files on the Drive":"file not found on the Drive"}</span><span class="st ${bd?"ok":"next"}">${bd?"Broken down":"Breakdown next"}</span><span class="st ${bd?"ok":""}">Why it works</span><span class="st">New copy</span><span class="st">Variations</span></div>
  <div class="links">${w.ig?`<a href="${esc(w.ig)}" target="_blank" rel="noopener">Watch the ad ↗</a>`:""}${w.preview?`<a href="${esc(w.preview)}" target="_blank" rel="noopener">Meta preview ↗</a>`:""}${w.landing?`<a href="${esc(w.landing)}" target="_blank" rel="noopener">Its landing page ↗</a>`:""}</div>
  ${w.files&&w.files.length?`<details><summary>Where the files are</summary><ul>${w.files.map(f=>`<li>${esc(f)}</li>`).join("")}${w.files_total>w.files.length?`<li>+${w.files_total-w.files.length} more</li>`:""}</ul></details>`:""}
  </div></article>`;
}
function render(){
  const d=D[brand];
  document.querySelectorAll("#btabs button").forEach(x=>x.setAttribute("aria-pressed",x.dataset.b===brand));
  $("lead").innerHTML=`The top 1% brought in <b>${d.share}%</b> of all ${brand==="brand-b"?"Brand B":"Brand A"} sales, out of ${d.assets.toLocaleString()} real assets. <b>${d.winners.length}</b> on the board${(d.removed||[]).length?` <span class="soft" style="font-weight:400">(taken off: ${d.removed.map(r=>esc(r.name)).join(", ")})</span>`:""}.`;
  const c=d.core_message;
  $("core").innerHTML=c?`<section style="background:var(--gold-soft);border-radius:14px;padding:18px 20px;display:grid;gap:10px"><span class="lab" style="color:var(--gold)">The message that works · in ${esc(c.seen_in)}</span>
    <p style="font:600 1.25rem/1.35 var(--display)">${esc(c.message)}</p>
    <div style="display:grid;gap:4px;font-size:.88rem"><b>The same message, told as:</b>${c.formats.map(f=>`<span>· ${esc(f)}</span>`).join("")}</div>
    <p style="font-size:.86rem">${esc(c.hook_note)}</p><p style="font-size:.86rem;color:var(--gold)">${esc(c.rules_note)}</p></section>`:"";
  $("list").innerHTML=d.winners.map(card).join("");
  $("foot").textContent=`Ranked by sales from our own copy of the ad account, ${d.window.from} to ${d.window.to}; each video, image or flexible-ad set counted once, every ad that ran it folded in.${brand==="brand-b"?" Brand B numbers start 1 Jan 2026 — older winners, like the years-long VSL before 2026, are only in Meta.":""}`;
}
document.addEventListener("click",e=>{
  const b=e.target.closest("#btabs button"); if(b){brand=b.dataset.b;render();return}
  const m=e.target.closest(".more"); if(m){const el=$(m.dataset.m);el.classList.toggle("open");m.textContent=el.classList.contains("open")?"Show less":"Show the whole text"}
});
render();
})();
</script>
'''


if __name__ == "__main__":
    main()
