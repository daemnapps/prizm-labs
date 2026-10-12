"""Winner Briefs — every top-1% winner remade as an AI brief, on one page, split by brand.

Reads the finished teardown runs (runs/video-teardown/<brand>/top1-*/hand/5-brief.md), the winners' numbers and
pictures (runs/media-buying/top1/board.json), and the open questions (runs/media-buying/top1/facts-for-damon.json).
Writes lab/media-buying/winner-briefs.html and the Markdown copy WINNER-BRIEFS-damon.md.
the owner's answers save to the page's db (collection `answers`, one doc per <run>__<n>).
"""
import json
import re
import sys
from pathlib import Path


def _vt_workdir():
    """video-teardown's working-folder module, loaded by file (SI-56)."""
    m = sys.modules.get("vt_workdir")
    if m is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "vt_workdir", ROOT / "tools" / "video-teardown" / "machine" / "workdir.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["vt_workdir"] = m
        spec.loader.exec_module(m)
    return m


ROOT = Path(__file__).resolve().parents[2]
TOP1 = ROOT / "runs/media-buying/top1"
OUT = ROOT / "lab/media-buying/winner-briefs.html"
MD = ROOT / "lab/media-buying/WINNER-BRIEFS-damon.md"
MACHINE = _vt_workdir().root(ROOT)     # the teardown's live runs, runs/video-teardown/_work/ (SI-56)
SKIP = set()          # run ids taken off the page (a workspace record — empty here)
NAMES = {"brand-b": "Brand B", "brand-a": "Brand A"}


def brief_json(text):
    for body in reversed(re.findall(r"```json\n(.*?)\n```", text, re.S)):
        try:
            return json.loads(body)
        except Exception:
            continue
    return {}


def summary(text):
    m = re.search(r"^# .+?\n\n(.+?)\n\n", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def machine_record(run_dir):
    # a label ending in "-" was filed without the dash on our side; the dashed folder is the live record
    for rj in (MACHINE / (run_dir.name + "-") / "run.json", MACHINE / run_dir.name / "run.json"):
        if rj.exists():
            return json.loads(rj.read_text())
    for rj in MACHINE.glob(run_dir.name + "*/run.json"):
        return json.loads(rj.read_text())
    # not live on this Mac: the filed shelves, through run-kit's index
    kit = str(ROOT / "components" / "run-kit")
    if kit not in sys.path:
        sys.path.append(kit)
    from run_kit import index as RKI
    for row in RKI.scan():
        if row["machine"] in ("video-teardown", "video-writing") and \
                (row["label"] == run_dir.name or row["label"].startswith(run_dir.name)):
            rj = ROOT / row["path"] / "run.json"
            if rj.is_file():
                return json.loads(rj.read_text())
    return {}


def scene_line(s):
    if s.get("held"):
        return {"id": s["id"], "kind": "held", "say": "", "note": "Winner's own clip, cut as filmed"}
    say = (s.get("voice") or "").strip()
    if s.get("kind") == "card":
        words = " / ".join(x for x in (s.get("lines") or []) if isinstance(x, str))
        return {"id": s["id"], "kind": "card", "say": say, "note": f"Card: {words}" if words else "Card"}
    return {"id": s["id"], "kind": s.get("kind") or "", "say": say, "note": "" if say else (s.get("happens") or "")[:120]}


def open_facts(f):
    """Questions not settled by a brand file (an answer with confidence 'found' settles one)."""
    a = f.get("answers") or {}
    return [q for i, q in enumerate(f.get("facts") or []) if (a.get(str(i)) or {}).get("confidence") != "found"]


def build():
    board = json.loads((TOP1 / "board.json").read_text())
    facts = json.loads((TOP1 / "facts-for-damon.json").read_text()) if (TOP1 / "facts-for-damon.json").exists() else {}
    rulings = json.loads((TOP1 / "structure-rulings.json").read_text())["runs"] if (TOP1 / "structure-rulings.json").exists() else {}
    brands = {}
    for brand in NAMES:
        winners = {int(w["rank"]): w for w in board[brand]["winners"]}
        cm = board[brand].get("core_message") or {}
        rows = []
        for d in sorted((ROOT / "runs/video-teardown" / brand).glob(f"top1-{brand}-*")):
            if d.name in SKIP or not d.is_dir():
                continue
            rank = int(re.match(rf"top1-{brand}-(\d+)", d.name).group(1))
            w = winners.get(rank, {})
            bf = d / "hand/5-brief.md"
            text = bf.read_text() if bf.exists() else ""
            b = brief_json(text) if text else {}
            rec = machine_record(d)
            open_ = ((rec.get("production_contract") or {}).get("open")) or []
            done = bool(b) and (rec.get("stages", {}).get("stage5") or {}).get("status") == "done" and not open_
            f = facts.get(d.name) or next((v for k, v in facts.items() if d.name.startswith(k.rstrip("-")) or k.startswith(d.name)), {})
            scenes = [scene_line(s) for s in (b.get("scenes") or [])]
            held = sum(1 for s in scenes if s["kind"] == "held")
            r = rulings.get(d.name) or {}
            changed = ([f"followed today's rule on: {x['element'][:90]}" for x in r.get("rows", []) if x.get("call") == "rule"]
                       + [f"your note: \u201c{x['note']}\u201d" for x in r.get("rows", []) if x.get("note")])
            rows.append({
                "run": d.name, "rank": rank,
                "name": (w.get("ads") or [{}])[0].get("ad_name", d.name).split(" - ")[0][:60],
                "sales": int(float(w.get("purchases") or 0)), "spend": round(float(w.get("spend") or 0)),
                "cpa": w.get("cpa"), "pic": w.get("pic") or "",
                "title": (b.get("piece") or {}).get("title") or "",
                "summary": summary(text),
                "hooks": [h.get("text", "") for h in (b.get("hooks") or [])][:6],
                "scenes": scenes, "n_scenes": len(scenes), "n_held": held,
                "status": "ready" if done and not open_facts(f) else ("answers" if done else "stuck"),
                "facts": [{"q": q, **((f.get("answers") or {}).get(str(i)) or {})} for i, q in enumerate(f.get("facts") or [])], "note": f.get("note") or f.get("machine_note") or "",
                "changed": changed,
                "aspect": (b.get("piece") or {}).get("aspect_ratio") or "",
            })
        brands[brand] = {"core": cm.get("message") or "", "formats": cm.get("formats") or [], "winners": rows}
    data = {"brands": brands}
    OUT.write_text(TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    write_md(brands)
    return brands


def write_md(brands):
    L = ["# Winner Briefs — the owner", "", "Every top-1% winner, remade as an AI brief that keeps the winner's own structure "
         "(the owner's calls, 4 Oct). Live page: see `lab/context/artifacts.md` → Winner Briefs.", ""]
    for brand, B in brands.items():
        L += [f"# {NAMES[brand]}", "", f"**Core message:** {B['core']}", ""]
        for w in B["winners"]:
            st = {"ready": "Ready", "answers": "Ready — needs your answers", "stuck": "Not finished"}[w["status"]]
            L += [f"## #{w['rank']} {w['title'] or w['name']} — {st}", "",
                  f"{w['sales']:,} sales · ${w['spend']:,} · {w['n_scenes']} scenes ({w['n_held']} cut from the winner as filmed)", ""]
            if w["summary"]:
                L += [w["summary"], ""]
            if w["hooks"]:
                L += ["**Openings:**"] + [f"- {h}" for h in w["hooks"]] + [""]
            if w["facts"]:
                L += ["**Questions:**"] + [f"- {f['q']}" + (f" — *{'answered' if f.get('confidence')=='found' else 'brand files say'}:* {f['answer']} ({f['source']})" if f.get('answer') else "") for f in w["facts"]] + [""]
            if w["note"]:
                L += [f"*{w['note']}*", ""]
            say = [s for s in w["scenes"] if s["say"]]
            if say:
                L += ["<details><summary>Script</summary>", ""] + [f"- **{s['id']}** {s['say']}" for s in say] + ["", "</details>", ""]
    MD.write_text("\n".join(L) + "\n")


TEMPLATE = r"""<title>Winner Briefs</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Figtree:wght@400;500;600&display=swap">
<style>
:root{--bg:#f6f7f4;--panel:#fff;--ink:#15181c;--soft:#69717b;--line:#e4e6e0;--go:#1d7a4c;--go-soft:#e1f1e7;--ask:#a85a00;--ask-soft:#fbeedc;--stop:#a3302a;--stop-soft:#f8e3e1;--grey:#eceee9;
--display:"Bricolage Grotesque","Avenir Next","Segoe UI",sans-serif;--body:"Figtree","Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111316;--panel:#181b1f;--ink:#e8eae6;--soft:#98a0aa;--line:#272b31;--go:#6fd39b;--go-soft:#17301f;--ask:#f0b060;--ask-soft:#3a2a12;--stop:#f08a80;--stop-soft:#3a1a18;--grey:#24282d;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#111316;--panel:#181b1f;--ink:#e8eae6;--soft:#98a0aa;--line:#272b31;--go:#6fd39b;--go-soft:#17301f;--ask:#f0b060;--ask-soft:#3a2a12;--stop:#f08a80;--stop-soft:#3a1a18;--grey:#24282d;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:15px/1.5 var(--body)}
.w{max-width:960px;margin:0 auto;padding-inline:16px;padding-block:28px 64px;display:grid;gap:16px}
h1{font:800 2.2rem/1.1 var(--display);margin:0;text-wrap:balance}h2{font:700 1.2rem/1.25 var(--display);margin:0;text-wrap:balance}p{margin:0}
.soft{color:var(--soft)}.lab{font-size:.72rem;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--soft)}
.tabs{display:flex;gap:8px;flex-wrap:wrap}.tabs button{font:600 1rem var(--display);border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:10px;padding:8px 16px;cursor:pointer}
.tabs button[aria-selected="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}.tabs small{font:500 .75rem var(--body);opacity:.75;margin-left:6px}
.core{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;display:grid;gap:8px}
.core q{font:600 1.15rem/1.4 var(--display);quotes:"\201C" "\201D"}
.key{display:flex;gap:14px;flex-wrap:wrap;font-size:.85rem}.key span{display:inline-flex;gap:6px;align-items:center}
.chip{display:inline-block;font-size:.72rem;font-weight:600;border-radius:999px;padding:2px 9px}
.ready{background:var(--go-soft);color:var(--go)}.answers{background:var(--ask-soft);color:var(--ask)}.stuck{background:var(--stop-soft);color:var(--stop)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;display:grid;grid-template-columns:110px minmax(0,1fr);gap:16px}
.card img,.ph{width:110px;height:170px;object-fit:cover;border-radius:8px;background:var(--grey);display:block}
.body{display:grid;gap:8px;min-width:0}.nums{font-size:.82rem;color:var(--soft);font-variant-numeric:tabular-nums}
details{border-top:1px solid var(--line);padding-top:8px}summary{cursor:pointer;font-weight:600;font-size:.9rem}
ol.script{margin:8px 0 0;padding-left:0;list-style:none;display:grid;gap:4px;font-size:.9rem;max-height:420px;overflow:auto}
ol.script li{display:grid;grid-template-columns:44px minmax(0,1fr);gap:8px}ol.script b{color:var(--soft);font-weight:600;font-variant-numeric:tabular-nums}
ol.script .held{color:var(--soft);font-style:italic}
ul{margin:4px 0 0;padding-left:18px}
.ask{background:var(--ask-soft);border-radius:10px;padding:10px 12px;display:grid;gap:8px}
.ask label{display:grid;gap:4px;font-size:.88rem}.ask input{font:inherit;font-size:.88rem;border:1px solid var(--line);border-radius:8px;padding:6px 9px;background:var(--panel);color:var(--ink)}
.found{font-size:.82rem;background:var(--panel);border-radius:6px;padding:6px 8px}.found.ok{border-left:3px solid var(--go)}
.saved{font-size:.75rem;color:var(--go)}
@media (max-width:560px){.card{grid-template-columns:1fr}.card img,.ph{width:100%;height:auto;aspect-ratio:9/16;max-height:360px}}
button:focus-visible,input:focus-visible,summary:focus-visible{outline:2px solid var(--ask);outline-offset:2px}
</style>
<div class="w">
<header style="display:grid;gap:8px"><span class="lab">The top 1% · remade with AI, kept like the winner</span><h1>Winner Briefs</h1>
<p class="soft">Each winner rebuilt as an AI brief, following your 37 calls. Every brief keeps the winner's own structure. Answer the questions inline and they save here.</p></header>
<div class="tabs" role="tablist" id="tabs"></div>
<section class="core" id="core"></section>
<div class="key"><span><i class="chip ready">Ready</i> brief done, nothing needed</span><span><i class="chip answers">Needs your answers</i> brief done, a few scenes wait on a fact</span><span><i class="chip stuck">Not finished</i> stopped before the brief</span></div>
<div id="list" style="display:grid;gap:12px"></div>
</div>
<script>
(function(){
const D=__DATA__;const NAMES={"brand-b":"Brand B","brand-a":"Brand A"};
let brand="brand-b";try{brand=localStorage.getItem("wb-brand")||brand}catch(e){}
let answers={},db=null,uid="";
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const LABEL={ready:"Ready",answers:"Needs your answers",stuck:"Not finished"};
function render(){
  $("tabs").innerHTML=Object.keys(NAMES).map(b=>{const W=D.brands[b].winners;const r=W.filter(w=>w.status!=="stuck").length;
    return `<button type="button" role="tab" data-b="${b}" aria-selected="${b===brand}">${NAMES[b]}<small>${r}/${W.length} briefs</small></button>`}).join("");
  const B=D.brands[brand];const W=B.winners;
  const c={ready:0,answers:0,stuck:0};W.forEach(w=>c[w.status]++);
  $("core").innerHTML=`<span class="lab">${NAMES[brand]} · the core message all its winners carry</span><q>${esc(B.core)}</q>
    <p class="soft" style="font-size:.85rem">${W.length} winners · ${c.ready} ready · ${c.answers} need your answers · ${c.stuck} not finished</p>`;
  $("list").innerHTML=W.map(w=>{
    const say=w.scenes;
    return `<article class="card">${w.pic?`<img src="${w.pic}" alt="">`:'<div class="ph"></div>'}<div class="body">
      <div><span class="chip ${w.status}">${LABEL[w.status]}</span></div>
      <span class="lab">${NAMES[brand]} #${w.rank} · ${esc(w.name)}</span>
      <h2>${esc(w.title||w.name)}</h2>
      <div class="nums">${w.sales.toLocaleString()} sales · $${w.spend.toLocaleString()} spent${w.n_scenes?` · ${w.n_scenes} scenes, ${w.n_held} cut from the winner as filmed`:""}${w.aspect?` · ${esc(w.aspect)}`:""}</div>
      ${w.summary?`<p>${esc(w.summary)}</p>`:""}
      ${w.changed.length?`<p style="font-size:.85rem"><b>Your calls on this one:</b> ${w.changed.map(esc).join(" · ")}</p>`:""}
      ${w.facts.length?`<div class="ask"><b style="font-size:.88rem">Questions on this one</b>${w.facts.map((f,i)=>{const k=w.run+"__"+i;const a=answers[k]||{};
        const got=f.confidence==="found";
        return `<label>${esc(f.q)}${f.answer?`<span class="found ${got?"ok":""}">${got?"Answered from the brand files":"Brand files say"}: ${esc(f.answer)} <span class="soft">(${esc(f.source)})</span></span>`:""}${got?"":`<input data-k="${esc(k)}" data-q="${esc(f.q)}" value="${esc(a.answer||"")}" placeholder="Your answer"><span class="saved">${a.saved?"Saved":""}</span>`}</label>`}).join("")}</div>`:""}
      ${w.note?`<p class="soft" style="font-size:.85rem">${esc(w.note)}</p>`:""}
      ${w.hooks.length?`<details><summary>Openings (${w.hooks.length})</summary><ul>${w.hooks.map(h=>`<li>${esc(h)}</li>`).join("")}</ul></details>`:""}
      ${say.length?`<details><summary>Script, scene by scene (${say.length})</summary><ol class="script">${say.map(s=>`<li><b>${esc(s.id)}</b><span class="${s.kind==="held"?"held":""}">${esc(s.say||s.note)}${s.say&&s.note?` <span class="soft">· ${esc(s.note)}</span>`:""}</span></li>`).join("")}</ol></details>`:""}
    </div></article>`}).join("");
}
document.addEventListener("click",e=>{const t=e.target.closest(".tabs button");if(!t)return;brand=t.dataset.b;try{localStorage.setItem("wb-brand",brand)}catch(_){}render()});
document.addEventListener("change",async e=>{const i=e.target.closest(".ask input");if(!i)return;const k=i.dataset.k;
  answers[k]={answer:i.value.trim(),question:i.dataset.q};if(!db){return}
  try{await db.collection("answers").doc(k.replace(/[^A-Za-z0-9_\-.~:@+]/g,"_")).set({run:k.split("__")[0],question:i.dataset.q,answer:i.value.trim(),by:uid,at:new Date().toISOString()});answers[k].saved=true}catch(_){answers[k].saved=false}
  const s=i.parentElement.querySelector(".saved");if(s)s.textContent=answers[k].saved?"Saved":"Not saved"});
render();
(async()=>{try{if(!window.claude)return;db=await window.claude.use("db");const u=await window.claude.use("user");if(u)uid=await u.id()}catch(e){db=null}
 if(!db)return;db.collection("answers").onSnapshot(s=>{s.docs.forEach(d=>{const x=d.data();const k=d.id;answers[k]=Object.assign({},x,{saved:true})});
   if(!document.activeElement||!document.activeElement.matches(".ask input"))render()},()=>{})})();
})();
</script>
"""

if __name__ == "__main__":
    out = build()
    for b, B in out.items():
        print(b, [(w["rank"], w["status"], w["n_scenes"]) for w in B["winners"]])
