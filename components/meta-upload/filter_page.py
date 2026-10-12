#!/usr/bin/env python3
"""filter_page — the Media Buying Desk page: every live ad's verdict, both brands, and the owner's calls on the ones that need him.

    filter_page.py      reads the latest runs/media-buying/<brand>/filter/<date>/verdicts.json per brand and writes
                        lab/media-buying/the-filter.html (+ THE-FILTER-damon.md), then it is republished to
                        the same artifact

The page keeps the owner's calls in its own database (capability `db`, collection `calls`, one doc per brand + ad:
`<brand>_<ad_id>` → {brand, ad_id, ad_name, verdict, why, call: kill|keep|more, reason, by, at, data_through}).
The machine reads them back (ArtifactData list `calls`) to retune the kill lines and signs of life
(standard.py) — every change shown to the owner first. Nothing on the page touches Meta.
"""
import html, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
OUT = WS / "lab/media-buying/the-filter.html"
BRANDS = (("brand-b", "Brand B"), ("brand-a", "Brand A"))


def latest(brand):
    runs = sorted((WS / "runs/media-buying" / brand / "filter").glob("*/verdicts.json"))
    return json.loads(runs[-1].read_text()) if runs else None


def media(ad_ids):
    """Each ad's picture (small JPEG as a data URI — the page can't load Meta's servers), its Instagram post and
    Meta preview link, from the warehouse's nightly meta_ads copy (fresh links)."""
    import base64, io, subprocess, sys, urllib.request
    sys.path.insert(0, str(WS / "tools/copywriter/library"))
    import meta_copy as MC
    if not ad_ids:
        return {}
    ids = ",".join(f"'{i}'" for i in ad_ids)
    rows = MC.db_query(f"""select coalesce(json_agg(x),'[]') from (select ad_id, image_url, thumbnail_url, video_id,
        instagram_permalink_url ig, preview_link from meta_ads where ad_id in ({ids})) x""")
    out = {}
    for r in rows:
        pic = None
        for u in (r.get("image_url"), r.get("thumbnail_url")):
            if not u:
                continue
            try:
                raw = urllib.request.urlopen(u, timeout=20).read()
                from PIL import Image
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                im.thumbnail((260, 460))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=72)
                pic = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
                break
            except Exception:
                continue
        out[r["ad_id"]] = {"pic": pic, "ig": r.get("ig"), "preview": r.get("preview_link"),
                           "kind": "video" if r.get("video_id") else "image"}
    return out


def main():
    data = {}
    for b, _ in BRANDS:
        d = latest(b)
        if d:
            std = json.loads((WS / "runs/media-buying" / b / "standard.json").read_text())
            g = {r["signal"]: r for r in std["judged"]}
            m = media([a["ad_id"] for a in d["ads"]])
            for a in d["ads"]:
                a.update(m.get(a["ad_id"], {}))
            bz = sorted((WS / "runs/media-buying" / b / "business").glob("*/business.json"))
            bz = json.loads(bz[-1].read_text()) if bz else None
            if bz:
                for a in d["ads"]:
                    x = bz["ads"].get(a["ad_id"]) or {}
                    a["brief"] = x.get("brief")
                    a["store_orders"], a["store_sales"] = x.get("store_orders"), x.get("store_sales")
            data[b] = {"business": ({k: bz[k] for k in ("store", "store_per_ad", "windows", "daily", "briefs", "since", "volume", "parts")} if bz else None),
                       "data_through": d["data_through"], "last_spend_day": d.get("last_spend_day"), "counts": d["counts"],
                       "good_cpa": g["cpa"]["good"], "made": d["made"],
                       "ads": [{k: a.get(k) for k in ("ad_id", "ad_name", "campaign", "adset", "pic", "ig", "preview", "kind", "spend", "purchases", "cpa", "roas",
                                                      "share", "atc", "ic", "ctr", "verdict", "why", "times_good_cpa", "brief", "store_orders", "store_sales", "leaning", "week", "lifetime_verdict", "lifetime_why",
                                                      "signs_of_life")} for a in d["ads"]]}
    page = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    OUT.write_text(page)
    md = ["# The Filter", "", "Page: see lab/context/artifacts.md (source `the-filter.html`, built by "
          "`components/meta-upload/filter_page.py`). Every live ad through the brand's standard; the owner's calls kept in the "
          "page's database (`calls`).", ""]
    for b, name in BRANDS:
        d = data.get(b)
        if not d:
            continue
        md += [f"## {name} — data through {d['data_through']}, last spend {d['last_spend_day']}", "",
               " · ".join(f"{k} {v}" for k, v in d["counts"].items()), ""]
        for a in d["ads"]:
            if a["verdict"] != "too early":
                md.append(f"- **{a['verdict']}** — {a['ad_name']}: {a['why']} (spent ${a['spend']:,.0f})")
        md.append("")
    (OUT.parent / "THE-FILTER-damon.md").write_text("\n".join(md) + "\n")
    print(f"wrote {OUT.relative_to(WS)}")


TEMPLATE = r'''<title>Media Buying Desk</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Figtree:wght@400;500;600&display=swap">
<style>
/* Layout: an ad-manager list — slim header with brand + view switches, one verdict bar, then folding campaign → ad set groups of single-line ad rows (thumb · name · verdict · CPA · return · share · spent); a row opens to the why, the links and the call buttons */
:root{
  --bg:#f6f7f4; --panel:#ffffff; --ink:#15181c; --soft:#69717b; --line:#e4e6e0; --hover:#f1f3ee;
  --top:#1d7a4c; --top-soft:#e1f1e7; --watch:#a86f00; --watch-soft:#fbf0d9; --cut:#b2462e; --cut-soft:#f7e3dc; --ask:#2f4fbf; --ask-soft:#e6ebfa; --grey:#a4aab2; --grey-soft:#eceee9;
  --display:"Bricolage Grotesque","Avenir Next","Segoe UI",sans-serif; --body:"Figtree","Helvetica Neue",Arial,sans-serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#111316; --panel:#181b1f; --ink:#e8eae6; --soft:#98a0aa; --line:#272b31; --hover:#1f2328;
  --top:#6fd39b; --top-soft:#17301f; --watch:#e8b45a; --watch-soft:#3a2d12; --cut:#f0907a; --cut-soft:#3a1d16; --ask:#93a9f6; --ask-soft:#1d2645; --grey:#5d646d; --grey-soft:#24282d; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#111316; --panel:#181b1f; --ink:#e8eae6; --soft:#98a0aa; --line:#272b31; --hover:#1f2328;
  --top:#6fd39b; --top-soft:#17301f; --watch:#e8b45a; --watch-soft:#3a2d12; --cut:#f0907a; --cut-soft:#3a1d16; --ask:#93a9f6; --ask-soft:#1d2645; --grey:#5d646d; --grey-soft:#24282d; color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:14px/1.45 var(--body)}
.w{max-width:1000px;margin:0 auto;padding-inline:16px;padding-block:24px 64px;display:grid;gap:14px}
h1{font:800 1.9rem/1.1 var(--display);margin:0;letter-spacing:-.01em}
.soft{color:var(--soft)}
.top{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:end;justify-content:space-between}
.seg{display:inline-flex;background:var(--grey-soft);border-radius:9px;padding:3px;gap:2px}
.seg button{font:600 .85rem var(--body);border:0;background:transparent;color:var(--soft);border-radius:7px;padding:6px 12px;cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--panel);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}
.vbar{display:flex;height:8px;border-radius:99px;overflow:hidden;background:var(--grey-soft)}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.82rem;color:var(--soft)}
.legend span{display:inline-flex;align-items:center;gap:6px}.legend b{color:var(--ink);font-variant-numeric:tabular-nums}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:none}
.list{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.ghead,.shead{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;cursor:pointer;list-style:none}
.ghead::-webkit-details-marker,.shead::-webkit-details-marker{display:none}
.ghead{padding:12px 16px;background:var(--panel);border-top:1px solid var(--line)}
details.g:first-child>.ghead{border-top:0}
.ghead .t{font:600 1rem var(--display);overflow-wrap:anywhere}
.shead{padding:8px 16px 8px 28px;border-top:1px solid var(--line);background:var(--bg)}
.shead .t{font-size:.86rem;font-weight:600;color:var(--soft);overflow-wrap:anywhere}
.tot{font-size:.8rem;color:var(--soft);font-variant-numeric:tabular-nums;white-space:nowrap;text-align:right}
.chev{display:inline-block;transition:transform .15s;color:var(--grey);margin-right:6px}
details[open]>summary .chev{transform:rotate(90deg)}
.cols,.row{display:grid;grid-template-columns:44px minmax(0,1fr) 92px 72px 64px 64px 76px;gap:12px;align-items:center;padding:8px 16px 8px 28px}
.cols{font-size:.7rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--soft);padding-top:6px;padding-bottom:6px;border-top:1px solid var(--line)}
.cols span:nth-child(n+4),.row .num{text-align:right}
.row{border-top:1px solid var(--line);cursor:pointer;font-variant-numeric:tabular-nums}
.row:hover{background:var(--hover)}
.row .th{width:44px;height:55px;border-radius:6px;background:var(--grey-soft);overflow:hidden}
.row .th img{width:100%;height:100%;object-fit:cover;display:block}
.row .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.row .sub{font-size:.78rem;color:var(--soft);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tag{display:inline-flex;align-items:center;gap:6px;font-size:.78rem;font-weight:600;white-space:nowrap}
.open{display:grid;grid-template-columns:120px minmax(0,1fr);gap:16px;padding:12px 16px 16px 28px;background:var(--bg);border-top:1px solid var(--line)}
.open img{width:120px;border-radius:8px;display:block}
.open .why{font-size:.95rem}
.facts{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:.84rem;color:var(--soft);font-variant-numeric:tabular-nums;margin-top:6px}
.links{display:flex;gap:14px;font-size:.85rem;margin-top:8px}.links a{color:var(--ask);text-decoration:none}.links a:hover{text-decoration:underline}
.calls{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:10px}
.calls button{font:600 .82rem var(--body);border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:7px;padding:5px 11px;cursor:pointer}
.calls button[aria-pressed="true"]{background:var(--ink);color:var(--panel);border-color:var(--ink)}
.calls input{flex:1;min-width:180px;font:inherit;font-size:.84rem;border:1px solid var(--line);border-radius:7px;padding:5px 9px;background:var(--panel);color:var(--ink)}
.saved{font-size:.8rem;color:var(--top)}.err{font-size:.8rem;color:var(--cut)}
.early{padding:8px 16px 10px 28px;border-top:1px solid var(--line);font-size:.82rem;color:var(--soft);cursor:pointer}
.empty{padding:20px;color:var(--soft)}
@media (max-width:700px){.cols{display:none}.row{grid-template-columns:44px minmax(0,1fr) auto;padding-left:16px}.row .num{display:none}.shead,.open,.early{padding-left:16px}.open{grid-template-columns:1fr}.open img{width:100px}}
button:focus-visible,input:focus-visible,a:focus-visible,summary:focus-visible,.row:focus-visible{outline:2px solid var(--ask);outline-offset:-2px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;display:grid;gap:2px}
.kpi b{font:800 1.6rem var(--display);font-variant-numeric:tabular-nums}.kpi span{font-size:.8rem;color:var(--soft)}.kpi small{font-size:.78rem;color:var(--soft)}
.card2{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;display:grid;gap:10px;min-width:0}
.card2 h2{font:600 1.05rem var(--display);margin:0}
.chart{overflow-x:auto}.chart svg{display:block;min-width:560px;width:100%}
.ax{font:11px var(--body);fill:var(--soft)}
table.t{border-collapse:collapse;width:100%;font-size:.86rem;font-variant-numeric:tabular-nums}
table.t th{text-align:left;font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--soft);font-weight:600;padding:6px 8px;border-bottom:1px solid var(--line)}
table.t td{padding:7px 8px;border-bottom:1px solid var(--line)}table.t td.n,table.t th.n{text-align:right}
.bchip{display:inline-block;font-size:.72rem;font-weight:600;border-radius:5px;padding:1px 6px;background:var(--ask-soft);color:var(--ask);margin-right:6px}
.bchip.none{background:var(--grey-soft);color:var(--soft)}
.acols{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.acts{margin:0;padding-left:1.1em;display:grid;gap:8px;font-size:.86rem}.acts b{overflow-wrap:anywhere}
.note{font-size:.84rem;color:var(--soft);background:var(--panel);border:1px dashed var(--line);border-radius:10px;padding:10px 12px}
</style>
<div class="w">
<div class="top">
  <div style="display:grid;gap:4px"><h1>Media Buying Desk</h1><span class="soft" id="asof"></span></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap"><div class="seg" id="btabs"><button type="button" data-b="brand-a" aria-pressed="true">Brand A</button><button type="button" data-b="brand-b" aria-pressed="false">Brand B</button></div>
  <div class="seg" id="ttabs"><button type="button" data-t="trouble" aria-pressed="true">Troubleshoot</button><button type="button" data-t="ads" aria-pressed="false">Ads</button><button type="button" data-t="business" aria-pressed="false">Business</button></div></div>
</div>
<div id="adsTop" style="display:grid;gap:8px"><div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:center"><div class="legend" id="legend"></div><div class="seg" id="vtabs"><button type="button" data-v="camp" aria-pressed="true">By campaign</button><button type="button" data-v="verdict" aria-pressed="false">By verdict</button></div></div><div class="vbar" id="vbar"></div></div>
<div class="list" id="view"></div>
<div id="panel" style="display:grid;gap:14px" hidden></div>
<details class="card2" id="words"><summary style="font-weight:600;cursor:pointer">The words on this page</summary><table class="t">
<tr><td><b>Ad spend</b></td><td>what Meta spent</td></tr>
<tr><td><b>Meta CPA</b></td><td>ad spend ÷ the sales Meta reports</td></tr>
<tr><td><b>Meta ROAS</b></td><td>the sales value Meta reports ÷ ad spend</td></tr>
<tr><td><b>Share of spend</b></td><td>of everything an ad's campaign spent while it ran, how much went to that ad</td></tr>
<tr><td><b>Store revenue</b></td><td>what the store took in, after tax and refunds (Brand B: brand-b.example; Brand A: its funnels)</td></tr>
<tr><td><b>Store orders</b></td><td>every store order, from an ad or not</td></tr>
<tr><td><b>MER</b></td><td>store revenue ÷ ad spend — what each ad dollar returned across the whole business</td></tr>
<tr><td><b>Blended CPA</b></td><td>ad spend ÷ store orders — what each order cost across the whole business</td></tr>
<tr><td><b>Tracked orders</b></td><td>store orders that record the ad that sold them (Brand A only; Brand B orders don't)</td></tr>
<tr><td><b>Tracked CPA · tracked ROAS</b></td><td>an ad's or brief's spend against only its tracked orders</td></tr>
<tr><td><b>Verdicts</b></td><td>the brand's standard on The Top 1% Plan: judged from 2× good CPA, decision at 5×, scale check at 10×</td></tr>
</table></details>
<p class="soft" style="font-size:.78rem">From our own copy of the ad and store numbers; nothing here changes Meta. Your calls on ads are kept to retune the lines, and you see every change first.</p>
</div>
<script>
(function(){
const D=__DATA__;
const ORDER=["pull up","kill","cut","scale","good","watch","too early"];
const LABEL={"pull up":"Your call","kill":"Kill","cut":"Cut","scale":"Scale","good":"Good","watch":"Watch","too early":"Too early"};
const COL={"pull up":"var(--ask)","kill":"var(--cut)","cut":"var(--cut)","scale":"var(--top)","good":"var(--top)","watch":"var(--watch)","too early":"var(--grey)"};
const CALLS=[["kill","Kill"],["keep","Keep"],["more","Give it more"]];
let brand="brand-a", view="camp", tab="trouble", part="angle", win="30", openId=null, db=null, uid=null, calls={};
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const money=v=>v==null?"—":"$"+Math.round(v).toLocaleString();
const needs=v=>v==="pull up"||v==="kill"||v==="cut";
const rank=a=>ORDER.indexOf(a.verdict);
const tag=v=>`<span class="tag" style="color:${COL[v]}"><i class="dot" style="background:${COL[v]}"></i>${LABEL[v]}</span>`;
const cols='<div class="cols"><span></span><span>Ad</span><span>Verdict</span><span>CPA</span><span>Return</span><span>Share</span><span>Spent</span></div>';
function row(a){
  const key=brand+"_"+a.ad_id, c=calls[key];
  return `<div class="row" tabindex="0" data-id="${esc(a.ad_id)}"><div class="th">${a.pic?`<img src="${a.pic}" alt="" loading="lazy">`:""}</div>
  <div style="min-width:0"><div class="nm" title="${esc(a.ad_name)}">${esc(a.ad_name)}</div><div class="sub">${a.brief?`<span class="bchip">${esc(a.brief.brief)}</span>`:'<span class="bchip none">before briefs</span>'}${c?"Your call: "+esc(LABEL[c.call]||c.call)+" · ":""}${esc(a.why)}</div></div>
  <div>${tag(a.verdict)}${a.leaning?'<div style="font-size:.72rem;color:var(--cut);font-weight:600">leaning cut</div>':""}</div><div class="num">${money(a.cpa)}</div><div class="num">${a.roas==null?"—":a.roas.toFixed(2)+"×"}</div><div class="num">${a.share==null?"—":a.share+"%"}</div><div class="num">${money(a.spend)}</div></div>
  ${openId===a.ad_id?detail(a):""}`;
}
function detail(a){
  const key=brand+"_"+a.ad_id, c=calls[key]||{};
  return `<div class="open">${a.pic?`<img src="${a.pic}" alt="">`:"<div></div>"}<div style="min-width:0"><div class="why">${esc(a.why)}</div>
  <div class="facts">${a.week?`<span>This week: ${money(a.week.spend)} · ${Math.round(a.week.purchases)} sales · CPA ${money(a.week.cpa)}</span>`:""}${a.lifetime_verdict?`<span>Lifetime: ${esc(a.lifetime_why)}</span>`:""}${a.brief?`<span>Brief ${esc(a.brief.brief)}${a.brief.product?" · "+esc(a.brief.product):""}${a.brief.angle?" · "+esc(a.brief.angle):""}</span>`:"<span>Made before briefs</span>"}${a.store_orders!=null&&D[brand].business&&D[brand].business.store_per_ad?`<span>${a.store_orders} store orders · ${money(a.store_sales)} store sales (90 days)</span>`:""}<span>${Math.round(a.purchases)} sales (Meta)</span><span>${Math.round(a.atc||0)} carts</span><span>${Math.round(a.ic||0)} checkouts</span><span>Click rate ${a.ctr==null?"—":a.ctr+"%"}</span><span>${a.times_good_cpa}× good CPA spent</span><span>${esc(a.kind||"")}</span></div>
  <div class="links">${a.ig?`<a href="${esc(a.ig)}" target="_blank" rel="noopener">Watch the ad ↗</a>`:""}${a.preview?`<a href="${esc(a.preview)}" target="_blank" rel="noopener">Meta preview ↗</a>`:""}</div>
  ${needs(a.verdict)?`<div class="calls" data-key="${esc(key)}">${CALLS.map(([v,l])=>`<button type="button" data-call="${v}" aria-pressed="${c.call===v}">${l}</button>`).join("")}<input type="text" placeholder="Why (one line)" value="${esc(c.reason||"")}" aria-label="Reason for your call"><button type="button" data-save>Save</button><span class="saved">${c.call?"Saved: "+esc(LABEL[c.call]||c.call):""}</span></div>`:""}</div></div>`;
}
function tot(xs){const s=xs.reduce((t,a)=>t+(a.spend||0),0),p=xs.reduce((t,a)=>t+(a.purchases||0),0);return `${xs.length} ad${xs.length===1?"":"s"} · ${money(s)} · CPA ${p?money(s/p):"—"}`}
function dots(xs){const c={};xs.forEach(a=>c[a.verdict]=(c[a.verdict]||0)+1);return ORDER.filter(v=>c[v]&&v!=="too early").map(v=>`<span class="tag" style="color:${COL[v]};margin-left:10px"><i class="dot" style="background:${COL[v]}"></i>${c[v]}</span>`).join("")}
function rowsFor(xs){
  const shown=xs.filter(a=>a.verdict!=="too early").sort((a,b)=>rank(a)-rank(b)||b.spend-a.spend), early=xs.filter(a=>a.verdict==="too early").sort((a,b)=>b.spend-a.spend);
  return (shown.length?cols+shown.map(row).join(""):"")+(early.length?`<details><summary class="early">${early.length} too early to judge (under ${money(2*D[brand].good_cpa)} spent)</summary>${cols}${early.map(row).join("")}</details>`:"");
}
function byCampaign(d){
  const camps={};d.ads.forEach(a=>{const c=a.campaign||"(no campaign)",s=a.adset||"(no ad set)";(camps[c]=camps[c]||{})[s]=(camps[c][s]||[]).concat([a])});
  const sum=xs=>xs.reduce((t,a)=>t+a.spend,0);
  return Object.entries(camps).map(([c,sets])=>({c,sets,all:Object.values(sets).flat()}))
   .sort((x,y)=>Math.min(...x.all.map(rank))-Math.min(...y.all.map(rank))||sum(y.all)-sum(x.all))
   .map(({c,sets,all})=>`<details class="g" open><summary class="ghead"><span class="t"><span class="chev">›</span>${esc(c)}</span><span class="tot">${tot(all)}${dots(all)}</span></summary>
   ${Object.entries(sets).sort((x,y)=>Math.min(...x[1].map(rank))-Math.min(...y[1].map(rank))||sum(y[1])-sum(x[1])).map(([s,xs])=>`<details open><summary class="shead"><span class="t"><span class="chev">›</span>${esc(s)}</span><span class="tot">${tot(xs)}</span></summary>${rowsFor(xs)}</details>`).join("")}</details>`).join("");
}
function byVerdict(d){
  return ORDER.map(v=>{const xs=d.ads.filter(a=>a.verdict===v).sort((a,b)=>b.spend-a.spend);if(!xs.length)return "";
   return `<details class="g" ${v==="too early"?"":"open"}><summary class="ghead"><span class="t"><span class="chev">›</span>${tag(v)}</span><span class="tot">${tot(xs)}</span></summary>${cols}${xs.map(row).join("")}</details>`}).join("");
}

const pct=v=>v==null?"—":v+"%";
const x2=v=>v==null?"—":v.toFixed(2)+"×";
function winBtns(){return `<div class="seg" id="wtabs">${["7","30","90"].map(w=>`<button type="button" data-w="${w}" aria-pressed="${win===w}">Last ${w} days</button>`).join("")}</div>`}
function chart(daily,bars,line,barLabel,lineLabel,lineFmt){
  const W=760,H=240,L=54,R=54,T=14,B=30, n=daily.length; if(!n) return "";
  const bw=(W-L-R)/n, bmax=Math.max(1,...daily.map(d=>d[bars]||0));
  const lv=daily.map(line), lmax=Math.max(1,...lv.filter(v=>v!=null));
  const X=i=>L+i*bw+bw/2, YB=v=>T+(1-v/bmax)*(H-T-B), YL=v=>T+(1-v/lmax)*(H-T-B);
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${barLabel} and ${lineLabel} by day">`;
  [0,.5,1].forEach(f=>{const y=T+(1-f)*(H-T-B);s+=`<line x1="${L}" x2="${W-R}" y1="${y}" y2="${y}" stroke="var(--line)"/><text class="ax" x="${L-6}" y="${y+4}" text-anchor="end">${money(bmax*f)}</text><text class="ax" x="${W-R+6}" y="${y+4}">${lineFmt(lmax*f)}</text>`});
  daily.forEach((d,i)=>{const v=d[bars]||0;s+=`<rect x="${L+i*bw+1}" y="${YB(v)}" width="${Math.max(1,bw-2)}" height="${H-B-YB(v)}" fill="var(--ask-soft)" stroke="var(--ask)" stroke-width=".5"><title>${d.date}: ${money(v)}</title></rect>`});
  const pts=lv.map((v,i)=>v==null?null:`${X(i)},${YL(v)}`).filter(Boolean);
  if(pts.length>1) s+=`<polyline points="${pts.join(" ")}" fill="none" stroke="var(--top)" stroke-width="2"/>`;
  [0,Math.floor(n/2),n-1].forEach(i=>{s+=`<text class="ax" x="${X(i)}" y="${H-10}" text-anchor="middle">${daily[i].date.slice(5)}</text>`});
  return s+`</svg><div class="legend"><span><i class="dot" style="background:var(--ask)"></i>${barLabel} (left)</span><span><i class="dot" style="background:var(--top)"></i>${lineLabel} (right)</span></div>`;
}
function roll(daily,num,den,k=7){return daily.map((_,i)=>{const xs=daily.slice(Math.max(0,i-k+1),i+1);const a=xs.reduce((t,d)=>t+(num(d)||0),0),b=xs.reduce((t,d)=>t+(den(d)||0),0);return b?a/b:null})}
const VB={"working":["Working","var(--top)"],"watch":["Watch","var(--watch)"],"not working":["Not working","var(--cut)"],"too early":["Too early","var(--grey)"]};
const vtag=v=>v?`<span class="tag" style="color:${VB[v][1]}"><i class="dot" style="background:${VB[v][1]}"></i>${VB[v][0]}</span>`:'<span class="soft">—</span>';
function kpis(list){return `<div class="kpis">${list.map(k=>`<div class="kpi"><span>${k[0]}</span><b>${k[1]}</b><small>${esc(k[2]||"")}</small></div>`).join("")}</div>`}
function trouble(d){
  const bz=d.business; if(!bz) return '<div class="note">No numbers built yet for this brand.</div>';
  const w=bz.windows[win], ads=d.ads||[];
  const pick=(f,n=6)=>ads.filter(f).sort((a,b)=>b.spend-a.spend).slice(0,n);
  const li=(a)=>`<li><b>${esc(a.ad_name)}</b><div class="soft" style="font-size:.8rem">${a.brief?esc(a.brief.brief)+" · ":""}${esc(a.why)}</div></li>`;
  const wb=bz.briefs.filter(b=>b.verdict==="working");
  const col=(title,color,items,empty)=>`<div class="card2" style="border-top:3px solid ${color};border-radius:0 0 12px 12px"><h2>${title}</h2>${items.length?`<ul class="acts">${items.join("")}</ul>`:`<p class="soft" style="font-size:.85rem">${empty}</p>`}</div>`;
  const v=bz.volume, judgedPct=v.launched_30d?Math.round(100*v.reached_a_verdict/v.launched_30d):0;
  const parts={angle:"Angle",avatar:"Avatar",format:"Format",media:"Media"};
  const prow=bz.parts[part]||[];
  return `${winBtns()}
  ${kpis([["Ad spend",money(w.spend),""],["Meta CPA",money(w.meta_cpa),"ad spend ÷ Meta-reported sales"],["Blended CPA",money(w.store_cpa),"ad spend ÷ every store order"],["MER",x2(w.mer),"store revenue ÷ ad spend"]])}
  <div class="acols">
    ${col("Scale","var(--top)",pick(a=>a.verdict==="scale").map(li),"No ad has earned scale yet: good CPA and return plus a real share of its campaign.")}
    ${col("Make variations","var(--ask)",wb.map(b=>`<li><b>${esc(b.brief)}</b> ${esc(b.product||"")}<div class="soft" style="font-size:.8rem">${esc([b.angle,b.avatar].filter(Boolean).join(" · "))} — ${esc(b.why)}</div></li>`),"No brief is working yet. Briefs need about "+money(2*d.good_cpa)+" each before they can be judged.")}
    ${col("Kill or cut","var(--cut)",pick(a=>a.verdict==="kill"||a.verdict==="cut").map(li).concat(pick(a=>a.leaning==="cut").map(a=>li(a).replace("<li>",'<li><span class="pill" style="background:var(--cut-soft);color:var(--cut)">Leaning cut</span> '))),"Nothing to kill or cut today.")}
    ${col("Your call","var(--ask)",pick(a=>a.verdict==="pull up").map(li),"Nothing is waiting on you.")}
  </div>
  <div class="card2"><h2>Volume vs intent · new ads, last 30 days</h2>
    <div class="kpis">${[["New ads launched",v.launched_30d,""],["Got enough spend to judge",v.reached_a_verdict,judgedPct+"% of them · judged from "+money(v.judged_from)],["Spend on new ads",money(v.spend_30d_new),"of "+money(bz.windows["30"].spend)+" total"],["Spend still too thin to judge",money(v.spend_on_unjudged),"spread across "+(v.launched_30d-v.reached_a_verdict)+" ads"]].map(k=>`<div class="kpi"><span>${k[0]}</span><b>${k[1]}</b><small>${esc(k[2])}</small></div>`).join("")}</div>
    <div class="vbar"><i style="width:${judgedPct}%;background:var(--top)"></i><i style="width:${100-judgedPct}%;background:var(--grey)"></i></div>
    <p class="soft" style="font-size:.84rem">Each new ad needs about ${money(v.judged_from)} before the standard can call it. Fewer ads with real budget each get a verdict; many small ones don't.</p></div>
  <div class="card2"><h2>Briefs · last 90 days</h2><div class="chart"><table class="t">
    <tr><th>Verdict</th><th>Brief</th><th>Angle · avatar</th><th class="n">Ads</th><th class="n">Spend</th><th class="n">Meta CPA</th><th class="n">Meta ROAS</th>${bz.store_per_ad?'<th class="n">Tracked orders</th><th class="n">Tracked CPA</th>':""}<th>Why it works or doesn't</th></tr>
    ${bz.briefs.map(b=>`<tr><td>${b.brief==="made before briefs"?'<span class="soft">—</span>':vtag(b.verdict)}</td><td>${b.brief==="made before briefs"?'<span class="bchip none">made before briefs</span>':`<span class="bchip">${esc(b.brief)}</span>${esc(b.product||"")}`}</td><td class="soft">${esc([b.angle,b.avatar].filter(Boolean).join(" · ")||"—")}</td><td class="n">${b.ads}</td><td class="n">${money(b.spend)}</td><td class="n">${money(b.meta_cpa)}</td><td class="n">${x2(b.meta_roas)}</td>${bz.store_per_ad?`<td class="n">${b.store_orders}</td><td class="n">${money(b.store_cpa)}</td>`:""}<td class="soft">${b.brief==="made before briefs"?"older ads — the Drive clean-up gives them briefs":b.verdict==="too early"?"too early to read":"not read yet"}</td></tr>`).join("")}
  </table></div></div>
  <div class="card2"><div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:center"><h2>What's working, by part</h2><div class="seg" id="ptabs">${Object.entries(parts).map(([k,l])=>`<button type="button" data-p="${k}" aria-pressed="${part===k}">${l}</button>`).join("")}</div></div>
    ${prow.length?`<div class="chart"><table class="t"><tr><th>${parts[part]}</th><th class="n">Briefs</th><th class="n">Spend</th><th class="n">Meta CPA</th><th class="n">Meta ROAS</th><th>Verdicts</th></tr>${prow.map(x=>`<tr><td>${esc(x.value)}</td><td class="n">${x.briefs}</td><td class="n">${money(x.spend)}</td><td class="n">${money(x.meta_cpa)}</td><td class="n">${x2(x.meta_roas)}</td><td>${Object.entries(x.verdicts).map(([k,n])=>`${n} ${VB[k]?VB[k][0].toLowerCase():k}`).join(" · ")}</td></tr>`).join("")}</table></div>`:'<p class="soft">No briefed ads in this window.</p>'}
    <p class="soft" style="font-size:.8rem">From the briefs behind each ad. "not set" means the brief doesn't record it yet.</p></div>`;
}
function business(d){
  const bz=d.business; if(!bz) return '<div class="note">No numbers built yet for this brand.</div>';
  const w=bz.windows[win];
  const kp=[["Store revenue",money(w.sales),bz.store],["Store orders",Math.round(w.orders).toLocaleString(),"every order, from an ad or not"],["MER",x2(w.mer),"store revenue ÷ ad spend"],["Blended CPA",money(w.store_cpa),"ad spend ÷ store orders"]];
  if(bz.store_per_ad) kp.push(["Tracked orders",Math.round(w.ad_orders).toLocaleString(),pct(w.ad_share_of_orders)+" of store orders record the ad that sold them"]);
  const daily=bz.daily.filter(x=>x.date>=new Date(Date.now()-win*864e5).toISOString().slice(0,10));
  return `${winBtns()}${kpis(kp)}
  <div class="card2"><h2>Store revenue against ad spend, by day</h2><div class="chart">${chart(daily.map(x=>Object.assign({},x)),"sales",x=>x.spend,"Store revenue","Ad spend",money)}</div></div>
  ${bz.store_per_ad?"":'<p class="note">Brand B store orders don’t record the ad that sold them, so its store numbers are for the whole business, not per ad or brief.</p>'}`;
}
function render(){
  const d=D[brand];
  document.querySelectorAll("#btabs button").forEach(x=>x.setAttribute("aria-pressed",x.dataset.b===brand));
  document.querySelectorAll("#vtabs button").forEach(x=>x.setAttribute("aria-pressed",x.dataset.v===view));
  document.querySelectorAll("#ttabs button").forEach(x=>x.setAttribute("aria-pressed",x.dataset.t===tab));
  const onAds=tab==="ads"; $("adsTop").hidden=!onAds; $("view").hidden=!onAds; $("panel").hidden=onAds;
  if(!onAds&&d){$("asof").textContent=`Data through ${d.data_through} · last spend ${d.last_spend_day||"—"} · checked ${d.made}`;$("panel").innerHTML=tab==="trouble"?trouble(d):business(d);return}
  if(!d){$("asof").textContent="";$("vbar").innerHTML="";$("legend").innerHTML="";$("view").innerHTML='<div class="empty">No filter run yet for this brand.</div>';return}
  $("asof").textContent=`Data through ${d.data_through} · last spend ${d.last_spend_day||"—"} · checked ${d.made}`;
  const n=d.ads.length||1;
  $("vbar").innerHTML=ORDER.map(v=>d.counts[v]?`<i style="width:${100*d.counts[v]/n}%;background:${COL[v]}" title="${LABEL[v]} ${d.counts[v]}"></i>`:"").join("");
  $("legend").innerHTML=ORDER.map(v=>`<span><i class="dot" style="background:${COL[v]}"></i>${LABEL[v]} <b>${d.counts[v]||0}</b></span>`).join("");
  if(!d.ads.length){$("view").innerHTML=`<div class="empty">No ${brand==="brand-b"?"Brand B":"Brand A"} ad has spent since ${d.last_spend_day}. Nothing live to judge.</div>`;return}
  const keep=[...document.querySelectorAll("#view details")].map(x=>x.open);
  $("view").innerHTML=view==="camp"?byCampaign(d):byVerdict(d);
  if(!db) document.querySelectorAll(".calls").forEach(el=>{el.querySelectorAll("button,input").forEach(x=>x.disabled=true);el.insertAdjacentHTML("beforeend",'<span class="err">Open this page signed in to save calls.</span>')});
}
document.addEventListener("click",async e=>{
  const bt=e.target.closest("#btabs button"); if(bt){brand=bt.dataset.b;openId=null;render();return}
  const vt=e.target.closest("#vtabs button"); if(vt){view=vt.dataset.v;openId=null;render();return}
  const tt=e.target.closest("#ttabs button"); if(tt){tab=tt.dataset.t;render();return}
  const wt=e.target.closest("#wtabs button"); if(wt){win=wt.dataset.w;render();return}
  const pt=e.target.closest("#ptabs button"); if(pt){part=pt.dataset.p;render();return}
  const r=e.target.closest(".row"); if(r){openId=openId===r.dataset.id?null:r.dataset.id;const det=[...document.querySelectorAll("#view details")].map(x=>x.open);render();[...document.querySelectorAll("#view details")].forEach((x,i)=>{if(det[i]!==undefined)x.open=det[i]});return}
  const box=e.target.closest(".calls"); if(!box) return;
  const b=e.target.closest("button"); if(!b) return;
  if(b.dataset.call){box.querySelectorAll("[data-call]").forEach(x=>x.setAttribute("aria-pressed",x===b));return}
  if(b.hasAttribute("data-save")){
    const key=box.dataset.key, sel=box.querySelector('[data-call][aria-pressed="true"]'), msg=box.querySelector(".saved,.err");
    if(!sel){msg.className="err";msg.textContent="Pick kill, keep or give it more first.";return}
    const reason=box.querySelector("input").value.trim();
    if(!reason){msg.className="err";msg.textContent="Add one line on why.";return}
    const a=D[brand].ads.find(x=>brand+"_"+x.ad_id===key);
    const body={brand,ad_id:a.ad_id,ad_name:a.ad_name,campaign:a.campaign||"",adset:a.adset||"",verdict:a.verdict,why:a.why,call:sel.dataset.call,reason,by:uid||"",at:new Date().toISOString(),data_through:D[brand].data_through,
      numbers:{spend:a.spend,purchases:a.purchases,cpa:a.cpa,roas:a.roas,share:a.share,atc:a.atc,ic:a.ic,ctr:a.ctr}};
    b.disabled=true;
    try{await db.collection("calls").doc(key).set(body);calls[key]=body;msg.className="saved";msg.textContent="Saved: "+LABEL[body.call]}
    catch(err){msg.className="err";msg.textContent="Couldn't save: "+(err&&err.code||"try again")}
    b.disabled=false;
  }
});
document.addEventListener("keydown",e=>{const r=e.target.closest&&e.target.closest(".row");if(r&&(e.key==="Enter"||e.key===" ")){e.preventDefault();r.click()}});
render();
(async()=>{
  try{if(!window.claude)return;db=await window.claude.use("db");const user=await window.claude.use("user");if(user)uid=await user.id()}catch(e){db=null}
  if(!db) return;
  db.collection("calls").onSnapshot(s=>{calls={};s.docs.forEach(x=>{calls[x.id]=x.data()});const det=[...document.querySelectorAll("#view details")].map(x=>x.open);render();[...document.querySelectorAll("#view details")].forEach((x,i)=>{if(det[i]!==undefined)x.open=det[i]})},()=>{});
})();
})();
</script>
'''


if __name__ == "__main__":
    main()
