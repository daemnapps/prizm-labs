"""Winner Rewrite Calls — the page where the owner rules on the structure holds.

Reads runs/media-buying/top1/structure-calls.json (one entry per held teardown,
parsed from each run's STRUCTURE-CHECK.md) and writes
lab/media-buying/rewrite-calls.html. His calls save to the page's db
(collection `calls`, one doc per <run>__<item>), and are read back to run
`--approve-structure` or re-run stage 3 with his note.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CALLS = ROOT / "runs/media-buying/top1/structure-calls.json"
RULINGS = ROOT / "runs/media-buying/top1/structure-rulings.json"
OUT = ROOT / "lab/media-buying/rewrite-calls.html"

THEMES = [
    ("lab", "A scientist or lab as the expert",
     {"brand-b": "Today's rule: the brand's own expert, not a lab.",
      "brand-a": "Today's rule: the brand's own expert, not a lab."}),
    ("origin", "Factory, warehouse or store shots",
     "Today's rule: no shots that claim where or how it's made."),
    ("offer", "Stacked deals and extra offers",
     "Today's rule: one price, one offer, one button."),
    ("age", "Looking younger / age gap",
     "Today's rule: never sell it as anti-aging or looking younger."),
    ("teller", "Who tells the story",
     "Your face is not cleared for AI yet, and the voice has to match who the ad is for."),
    ("click", "Where the click goes",
     "The swipe sends people off to a long page instead of straight to the product."),
    ("other", "One-offs",
     "Changes that only apply to one ad."),
]

# item -> theme, set by reading each item (keyword guessing put half of them wrong)
THEME_OF = {}   # "<brand>-NN": {"<item>": "<theme>"} — his per-item calls, a workspace record (empty here)

TEMPLATE = r"""<title>Winner Rewrite Calls</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Figtree:wght@400;500;600&display=swap">
<style>
/* Layout: one column — how it works, the recurring calls (decide a theme once, it fills every ad), then each winner with its picture and its own items; choices save to the page's database */
:root{--bg:#f6f7f4;--panel:#fff;--ink:#15181c;--soft:#69717b;--line:#e4e6e0;--go:#1d7a4c;--go-soft:#e1f1e7;--ch:#a85a00;--ch-soft:#fbeedc;--ask:#2f4fbf;--ask-soft:#e6ebfa;--grey-soft:#eceee9;
--display:"Bricolage Grotesque","Avenir Next","Segoe UI",sans-serif;--body:"Figtree","Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111316;--panel:#181b1f;--ink:#e8eae6;--soft:#98a0aa;--line:#272b31;--go:#6fd39b;--go-soft:#17301f;--ch:#f0b060;--ch-soft:#3a2a12;--ask:#93a9f6;--ask-soft:#1d2645;--grey-soft:#24282d;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#111316;--panel:#181b1f;--ink:#e8eae6;--soft:#98a0aa;--line:#272b31;--go:#6fd39b;--go-soft:#17301f;--ch:#f0b060;--ch-soft:#3a2a12;--ask:#93a9f6;--ask-soft:#1d2645;--grey-soft:#24282d;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:15px/1.5 var(--body)}.w{max-width:900px;margin:0 auto;padding-inline:16px;padding-block:28px 64px;display:grid;gap:16px}
h1{font:800 2.1rem/1.1 var(--display);margin:0}h2{font:600 1.15rem var(--display);margin:0}p{margin:0}.soft{color:var(--soft)}
.lab{font-size:.72rem;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--soft)}
.sec{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;display:grid;gap:12px;min-width:0}
.tabs{display:flex;gap:8px}.tabs button{font:600 1rem var(--display);border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:10px;padding:8px 16px;cursor:pointer}.tabs button[aria-selected="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}.tabs small{font:500 .75rem var(--body);opacity:.75;margin-left:6px}
.prog{display:flex;gap:12px;align-items:center;font-size:.9rem}.bar{flex:1;height:8px;background:var(--grey-soft);border-radius:99px;overflow:hidden}.bar i{display:block;height:8px;background:var(--go)}
.theme{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;padding:12px 0;border-top:1px solid var(--line)}.theme:first-of-type{border-top:0}
.theme b{font-family:var(--display);font-size:1rem}
.choice{display:flex;gap:6px;flex-wrap:wrap}.choice button{font:600 .85rem var(--body);border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:8px;padding:6px 12px;cursor:pointer}
.choice button[data-v="keep"][aria-pressed="true"]{background:var(--go);color:var(--panel);border-color:var(--go)}
.choice button[data-v="rule"][aria-pressed="true"]{background:var(--ch);color:var(--panel);border-color:var(--ch)}
.ad{display:grid;grid-template-columns:96px minmax(0,1fr);gap:14px}.ad img,.ph{width:96px;height:150px;object-fit:cover;border-radius:8px;background:var(--grey-soft);display:block}
.row{display:grid;gap:6px;padding:10px 0;border-top:1px solid var(--line)}.row:first-child{border-top:0}
.tag{display:inline-block;font-size:.7rem;font-weight:600;border-radius:999px;padding:1px 8px;background:var(--grey-soft);color:var(--soft);margin-right:6px}
.why{font-size:.84rem;color:var(--soft)}details summary{cursor:pointer;font-size:.82rem;color:var(--soft)}
input.note{width:100%;font:inherit;font-size:.86rem;border:1px solid var(--line);border-radius:8px;padding:6px 9px;background:var(--panel);color:var(--ink)}
.state{font-size:.8rem}.ok{color:var(--go)}.err{color:var(--ch)}
@media (max-width:560px){.ad{grid-template-columns:1fr}.theme{grid-template-columns:1fr}}
button:focus-visible,input:focus-visible{outline:2px solid var(--ask);outline-offset:2px}
</style>
<div class="w">
<header style="display:grid;gap:8px"><span class="lab">The top 1% teardowns · step 3 is waiting on you</span><h1>Winner Rewrite Calls</h1>
<p class="soft">To remake each winner with AI, the rewrite had to change parts of it — mostly where the old ad breaks a brand rule we have today. Nothing moves until you call each one. For each one: <b>keep it like the winner</b> (what made money), or <b>follow today's rule</b>. Decide a group once at the top and it fills every ad below; you can still flip single ones. A note is optional.</p></header>
<div class="tabs" role="tablist" id="tabs"></div>
<div class="prog"><span id="count"></span><div class="bar"><i id="fill" style="width:0"></i></div></div>
<section class="sec"><span class="lab">Decide these once — they fill every ad that hits them</span><div id="themes"></div></section>
<section class="sec" id="learned" hidden><span class="lab">What your calls taught the machine</span><div id="learnedBody"></div></section>
<div id="ads" style="display:grid;gap:12px"></div>
<p class="soft" style="font-size:.8rem" id="saveinfo"></p>
</div>
<script>
(function(){
const D=__DATA__;
let calls={}, db=null, uid="";
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const key=(it,r)=>it.run+"__"+r.n;
const ALL=[];D.items.forEach(it=>it.rows.forEach(r=>ALL.push([it,r])));
const NAMES={"brand-b":"Brand B","brand-a":"Brand A"};let brand="brand-b";try{brand=localStorage.getItem("rc-brand")||brand}catch(e){}
let all=[];
function choice(k,cur){return `<div class="choice" data-k="${esc(k)}"><button type="button" data-v="keep" aria-pressed="${cur==="keep"}">Keep it like the winner</button><button type="button" data-v="rule" aria-pressed="${cur==="rule"}">Follow today's rule</button></div>`}
function render(){
  all=ALL.filter(([it])=>it.brand===brand);
  $("tabs").innerHTML=Object.keys(NAMES).map(b=>{const xs=ALL.filter(([it])=>it.brand===b);const d=xs.filter(([it,r])=>(calls[key(it,r)]||{}).call).length;return `<button type="button" role="tab" data-b="${b}" aria-selected="${b===brand}">${NAMES[b]}<small>${d}/${xs.length}</small></button>`}).join("");
  const done=all.filter(([it,r])=>calls[key(it,r)]&&calls[key(it,r)].call).length;
  $("count").textContent=`${NAMES[brand]}: ${done} of ${all.length} called`; $("fill").style.width=(100*done/all.length)+"%";
  $("themes").innerHTML=D.themes.map(t=>{const xs=all.filter(([it,r])=>r.theme===t.key);if(!xs.length)return"";
    const vals=new Set(xs.map(([it,r])=>(calls[key(it,r)]||{}).call||""));const cur=vals.size===1?[...vals][0]:"";
    return `<div class="theme"><div><b>${esc(t.title)}</b> <span class="soft" style="font-size:.82rem">· ${xs.length} item${xs.length>1?"s":""} in ${(n=>n+(n>1?" ads":" ad"))(new Set(xs.map(([it])=>it.run)).size)}</span><div class="why">${esc(typeof t.rule==="object"?t.rule[brand]:t.rule)}</div></div>${choice("theme:"+t.key,cur)}</div>`}).join("");
  $("ads").innerHTML=D.items.filter(it=>it.brand===brand).map(it=>`<section class="sec"><div class="ad">${it.pic?`<img src="${it.pic}" alt="">`:'<div class="ph"></div>'}<div style="min-width:0;display:grid;gap:4px">
    <span class="lab">${it.brand==="brand-b"?"Brand B":"Brand A"} · #${it.rank} · ${it.sales.toLocaleString()} sales · $${it.spend.toLocaleString()}</span><h2>${esc(it.name)}</h2>
    <div>${it.rows.map(r=>{const c=calls[key(it,r)]||{};return `<div class="row"><div><span class="tag">${esc((D.themes.find(t=>t.key===r.theme)||{}).title||"")}</span></div>
      <div>${esc(r.element)}</div><div class="why">Right now the rewrite ${r.change==="Adapted"?"<b>followed today's rule</b>":"<b>kept it like the winner</b>"} and is waiting on you.</div><details><summary>Why it was flagged</summary><div class="why">${esc(r.why)}</div></details>
      ${choice(key(it,r),c.call||"")}${c.call?`<input class="note" data-k="${esc(key(it,r))}" placeholder="Note (optional) — e.g. use the barber, keep the deal but one click" value="${esc(c.note||"")}">`:""}
      <span class="state ${c.saved?"ok":""}">${c.saved?"Saved":""}</span></div>`}).join("")}</div></div></div></section>`).join("");
  const L=(D.learned||{})[brand];$("learned").hidden=!L;
  if(L)$("learnedBody").innerHTML=`<p><b>You kept the winner's way ${L.keep} of ${L.calls} times.</b> The rewrite had bent ${L.bent} place${L.bent===1?"":"s"} to a brand rule on its own; you sent ${L.bent_back} back.</p>
    <p class="why">From now on, every writer on a top-1% ${NAMES[brand]} run reads: keep the winner's structure, even against today's brand rules, and only change what you ruled.</p>
    ${L.rule.length?`<p style="margin-top:8px"><b>Where you followed today's rule:</b></p><ul>${L.rule.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:""}
    ${L.notes.length?`<p><b>Your notes:</b></p><ul>${L.notes.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:""}`;
  $("saveinfo").textContent=db?"Your calls save as you click.":"Open this page signed in to save your calls.";
}
async function save(k,body){calls[k]=Object.assign({},calls[k]||{},body);if(!db){render();return}
  const [run,n]=k.split("__");try{const doc=Object.assign({run,n,by:uid,at:new Date().toISOString()},calls[k]);delete doc.saved;await db.collection("calls").doc(k.replace(/[^A-Za-z0-9_\-.~:@+]/g,"_")).set(doc);calls[k].saved=true}catch(e){calls[k].saved=false}render()}
document.addEventListener("click",e=>{const tb=e.target.closest(".tabs button");if(tb){brand=tb.dataset.b;try{localStorage.setItem("rc-brand",brand)}catch(_){}render();return}
  const b=e.target.closest(".choice button");if(!b)return;const k=b.parentElement.dataset.k,v=b.dataset.v;
  if(k.startsWith("theme:")){const t=k.slice(6);all.filter(([it,r])=>r.theme===t).forEach(([it,r])=>save(key(it,r),{call:v}));return}
  save(k,{call:v})});
document.addEventListener("change",e=>{const i=e.target.closest("input.note");if(i)save(i.dataset.k,{note:i.value.trim()})});
render();
(async()=>{try{if(!window.claude)return;db=await window.claude.use("db");const u=await window.claude.use("user");if(u)uid=await u.id()}catch(e){db=null}
 if(!db)return;db.collection("calls").onSnapshot(s=>{s.docs.forEach(d=>{const x=d.data();calls[x.run+"__"+x.n]=Object.assign({},x,{saved:true})});render()},()=>{})})();
})();
</script>
"""


def build():
    items = json.loads(CALLS.read_text())
    for it in items:
        short = it["run"][5:].split("-")
        short = "-".join(short[:2])
        for r in it["rows"]:
            r["theme"] = THEME_OF.get(short, {}).get(r["n"], "other")
    learned = {}
    if RULINGS.exists():
        for run, r in json.loads(RULINGS.read_text())["runs"].items():
            L = learned.setdefault(r["brand"], {"calls": 0, "keep": 0, "rule": [], "bent": 0, "bent_back": 0, "notes": []})
            for x in r["rows"]:
                L["calls"] += 1
                if x["call"] == "keep":
                    L["keep"] += 1
                elif x["call"] == "rule":
                    L["rule"].append(f"#{r['rank']} {r['name']}: {x['element']}")
                if x["rewrite_did"] == "followed the rule":
                    L["bent"] += 1
                    L["bent_back"] += x["call"] == "keep"
                if x["note"]:
                    L["notes"].append(f"#{r['rank']} {r['name']}: \u201c{x['note']}\u201d")
    data = {"learned": learned, "items": items, "themes": [{"key": k, "title": t, "rule": d} for k, t, d in THEMES]}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    OUT.write_text(TEMPLATE.replace("__DATA__", blob))
    return OUT, sum(len(i["rows"]) for i in items), len(items)


if __name__ == "__main__":
    out, n, runs = build()
    print(f"{out} — {n} calls across {runs} winners")
