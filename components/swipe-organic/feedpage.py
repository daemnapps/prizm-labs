#!/usr/bin/env python3
"""Render an avatar feed's page from its store. The page is a WINDOW:
it reads the backend, computes what's rising, and shows it — it holds
no data of its own and takes no input that feeds the learning loop
(the owner's ruling 2026-08-30: no human in the loop).

    python3 feedpage.py --avatar brand-b--avatar-two

feed.py calls this after every sweep, so the page rebuilds itself
whenever the data moves. Output: <feed folder>/feed.html (committed —
a page is code, not a document).
"""
import argparse, html, json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

def iso(s):
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def build(avatar):
    root = HERE / "records/avatar-feeds" / avatar
    items = json.loads((root / "items.json").read_text())["items"]
    obs = {}
    for line in (root / "observations.jsonl").read_text().splitlines():
        o = json.loads(line)
        obs.setdefault(o["item"], []).append(o)
    sweeps = [json.loads(l) for l in (root / "sweeps.jsonl").read_text().splitlines()]
    now = datetime.now(timezone.utc)

    cards = []
    for key, it in items.items():
        rows = [o for o in obs.get(key, []) if o.get("views")]
        views = rows[-1]["views"] if rows else None
        likes = next((o["likes"] for o in reversed(obs.get(key, [])) if o.get("likes")), None)
        rise = None  # % growth per day between first and last sighting
        if len(rows) >= 2 and rows[0]["views"]:
            t0, t1 = iso(rows[0]["at"]), iso(rows[-1]["at"])
            days = max((t1 - t0).total_seconds() / 86400, 0.25) if t0 and t1 else None
            # small posts swing wildly in % terms — rising means moving AND real
            if days and rows[-1]["views"] >= 10_000:
                rise = (rows[-1]["views"] / rows[0]["views"] - 1) / days * 100
        posted = iso(it["posted"]) if it.get("posted") else None
        age = (now - posted).days if posted else None
        cards.append({
            "platform": it["platform"], "url": it["url"], "author": it.get("author") or "",
            "caption": (it.get("caption") or "")[:160], "cover": it.get("cover"),
            "posted": posted.strftime("%b %d") if posted else None, "age": age,
            "views": views, "likes": likes, "rise": rise, "source": it.get("source", ""),
            "lane": it.get("lane"), "bf": it.get("brand_fit"), "cat": it.get("category"),
        })
    # default order: rising first (by growth), then newest, then biggest
    cards.sort(key=lambda c: (-(c["rise"] or -1), c["age"] if c["age"] is not None else 9999,
                              -(c["views"] or 0)))

    def fmt(n):
        if n is None: return ""
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1_000: return f"{n/1_000:.0f}K"
        return str(n)

    P = {"tiktok": ("TT", "#69C9D0"), "instagram": ("IG", "#E1306C"), "youtube": ("YT", "#FF0000")}
    cells = []
    for c in cards:
        badge, color = P.get(c["platform"], ("?", "#999"))
        risehtml = (f'<span class="rise">▲ {c["rise"]:.0f}%/day</span>'
                    if c["rise"] is not None and c["rise"] >= 5 else "")
        extra = " · ".join(x for x in [c.get("cat") or "", (c.get("lane") or "").upper(),
                                        c.get("bf") or ""] if x)
        meta = " · ".join(x for x in [
            f'{fmt(c["views"])} views' if c["views"] else "",
            f'{fmt(c["likes"])} likes' if c["likes"] else "",
            c["posted"] or "", f'{c["age"]}d ago' if c["age"] is not None else "", extra] if x)
        cover = (f'<img loading="lazy" referrerpolicy="no-referrer" src="{html.escape(c["cover"])}" onerror="this.style.display=\'none\'">'
                 if c["cover"] else "")
        rise_attr = f'{c["rise"]:.1f}' if c["rise"] is not None else ""
        cells.append(f'''<a class="card" data-p="{c["platform"]}" data-ln="{c.get("lane") or ""}" data-bf="{c.get("bf") or ""}" data-age="{c["age"] if c["age"] is not None else ""}" data-v="{c["views"] or 0}" data-r="{rise_attr}" href="{html.escape(c["url"])}" target="_blank">
<div class="thumb">{cover}<span class="pb" style="background:{color}">{badge}</span>{risehtml}</div>
<div class="body"><div class="author">{html.escape(c["author"])}</div>
<div class="cap">{html.escape(c["caption"])}</div><div class="meta">{meta}</div></div></a>''')

    last = sweeps[-1] if sweeps else {}
    head = (f'{len(cards)} posts · last sweep {last.get("at","—")[:16].replace("T"," ")} UTC · '
            f'{last.get("new",0)} new that run · {len(sweeps)} sweeps recorded')
    has_saves = any(c.get("lane") for c in cards)
    lanes = sorted({c["lane"] for c in cards if c.get("lane")})
    bfs = sorted({c["bf"] for c in cards if c.get("bf")})
    extrachips = ""
    if has_saves:
        extrachips = ('<span class="gap"></span>'
            + '<button class="chip ln on" data-ln="all">Both lanes</button>'
            + "".join(f'<button class="chip ln" data-ln="{x}">{x.title()}s</button>' for x in lanes)
            + '<span class="gap"></span>'
            + '<button class="chip bf on" data-bf="all">All fits</button>'
            + "".join(f'<button class="chip bf" data-bf="{x}">{x.title()}</button>' for x in bfs))
    twdef = "all" if has_saves else "90"
    doc = f'''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Feed — {avatar}</title><style>
:root{{color-scheme:dark}}body{{margin:0;background:#0d1117;color:#e6edf3;font:15px/1.45 -apple-system,Segoe UI,sans-serif}}
header{{padding:22px 24px 10px}}h1{{margin:0;font-size:21px}}h1 small{{color:#8b949e;font-weight:400}}
.sub{{color:#8b949e;font-size:13px;margin-top:4px}}
.chips{{padding:8px 24px 16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.gap{{width:14px}}
.chip{{border:1px solid #30363d;border-radius:999px;padding:4px 14px;font-size:13px;cursor:pointer;color:#8b949e;background:none}}
.chip.on{{color:#e6edf3;border-color:#e6edf3}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;padding:0 24px 24px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:10px;overflow:hidden;text-decoration:none;color:inherit;display:none}}
.card.show{{display:block}}
.thumb{{position:relative;aspect-ratio:9/12;background:#21262d}}
.thumb img{{width:100%;height:100%;object-fit:cover;display:block}}
.pb{{position:absolute;top:8px;left:8px;color:#fff;font-size:11px;font-weight:700;padding:2px 7px;border-radius:5px}}
.rise{{position:absolute;top:8px;right:8px;background:#238636;color:#fff;font-size:11px;font-weight:700;padding:2px 7px;border-radius:5px}}
.body{{padding:10px 12px 12px}}.author{{font-weight:600;font-size:13px}}
.cap{{color:#8b949e;font-size:12px;margin:4px 0;min-height:2.4em;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.meta{{color:#8b949e;font-size:12px}}
.more{{display:block;margin:0 auto 32px;padding:9px 26px;border-radius:999px;border:1px solid #30363d;background:#161b22;color:#e6edf3;font-size:14px;cursor:pointer}}
</style></head><body>
<header><h1>What the avatar is watching <small>— {avatar.replace("--"," · ")}</small></h1>
<div class="sub">{head} · organic only · <span class="count"></span></div></header>
<div class="chips"><button class="chip on" data-f="all">All</button>
<button class="chip" data-f="tiktok">TikTok</button>
<button class="chip" data-f="instagram">Instagram</button>
<button class="chip" data-f="youtube">YouTube</button>
<span class="gap"></span>
<button class="chip s on" data-s="rise">Rising</button>
<button class="chip s" data-s="new">Newest</button>
<button class="chip s" data-s="views">Most viewed</button>
<span class="gap"></span>
<button class="chip t" data-t="30">30d</button>
<button class="chip t{' on' if twdef=='90' else ''}" data-t="90">90d</button>
<button class="chip t{' on' if twdef=='all' else ''}" data-t="all">All time</button>{extrachips}</div>
<div class="grid">{"".join(cells)}</div>
<button class="more">Show more</button>
<script>
let f="all",s="rise",tw="{twdef}",ln="all",bf="all",n=24;
const grid=document.querySelector(".grid"),cards=[...document.querySelectorAll(".card")];
const age=c=>c.dataset.age===""?null:+c.dataset.age;
function fits(c){{if(f!=="all"&&c.dataset.p!==f)return false;
 if(ln!=="all"&&c.dataset.ln!==ln)return false;
 if(bf!=="all"&&c.dataset.bf!==bf)return false;
 if(tw!=="all"){{const a=age(c);if(a===null||a>+tw)return false;}}return true;}}
function key(c){{if(s==="views")return -(+c.dataset.v);
 if(s==="new"){{const a=age(c);return a===null?9e9:a;}}
 return -(c.dataset.r===""?-1:+c.dataset.r);}}
function paint(){{const list=cards.filter(fits).sort((a,b)=>key(a)-key(b));
 cards.forEach(c=>c.classList.remove("show"));
 list.forEach((c,i)=>{{grid.appendChild(c);if(i<n)c.classList.add("show");}});
 document.querySelector(".more").style.display=list.length>n?"block":"none";
 document.querySelector(".count").textContent=list.length+" posts in view";}}
document.querySelectorAll(".chip").forEach(b=>b.onclick=()=>{{n=24;
 if(b.dataset.f){{f=b.dataset.f;pick("f",b);}}
 else if(b.dataset.s){{s=b.dataset.s;pick("s",b);}}
 else if(b.dataset.t){{tw=b.dataset.t;pick("t",b);}}
 if(b.dataset.ln){{ln=b.dataset.ln;pick("ln",b);}}
 if(b.dataset.bf){{bf=b.dataset.bf;pick("bf",b);}}
 paint();}});
function pick(kind,b){{document.querySelectorAll(".chip").forEach(x=>{{
 if(x.dataset[kind]!==undefined)x.classList.toggle("on",x===b);}});}}
document.querySelector(".more").onclick=()=>{{n+=24;paint();}};paint();
</script></body></html>'''
    out = root / "feed.html"
    out.write_text(doc)
    print(f"{out.relative_to(HERE)} · {len(cards)} cards")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--avatar", required=True)
    build(ap.parse_args().avatar)
