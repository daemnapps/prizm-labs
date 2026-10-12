#!/usr/bin/env python3
"""Swipe Studio — the local app over the saves catalog.

Board of cards (thumbnail, copy, signal, lane, brand fit). Click a card →
**Tear down** (brand-neutral: strip the asset to structure, stages 1–2).
Once torn down, **Inject** it into any brand (stages 3 + 5 → the brief).
Brands are discovered from the brand cabinets on disk, so new brands just
appear — the owner's ruling 2026-08-31: teardown first, brand chosen after,
numerous brands coming.

    python3 app.py          # http://localhost:8765

Data in:  records/damon-saves/catalog.json (+ covers/)
Records:  records/teardowns/<code>/           stage1 + stage2 (neutral)
          records/teardowns/<code>/injections/<brand>/  stage3 + brief
Media:    records/teardowns/media/ — gitignored, words stay in git.
"""
import html, json, os, re, subprocess, threading
os.environ["PATH"] = os.environ.get("PATH", "") + ":/opt/homebrew/bin:/usr/local/bin"
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
for _r in HERE.parents:                # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
SAVES = HERE / "records/damon-saves"
VID = HERE / "records/swipe-videos"
TD = HERE / "records/teardowns"
import desklib as D  # noqa: E402  WS: run-kit's repo() (triage page 12)
WS = D.WS
CHAIN = WS / "new-workflow-design" / "builds" / "video-teardown" / "prompts"
S12 = ["stage1-teardown-v5-damon.md", "stage2-replication-v2-damon.md"]
S35 = ["stage3-injection-v3-damon.md", "stage5-brief-v8-damon.md"]
PORT = 8765
JOBS = {}  # "code" or "code:brand" -> {status, kind, brand?}
LOCK = threading.Lock()

BRANDS_DIR = (WS / "brands") if (WS / "brands").is_dir() else None

def brands():
    out = {}
    if not BRANDS_DIR:
        return out
    for d in sorted(BRANDS_DIR.iterdir()):
        if d.is_dir() and ((d / "core-avatars").is_dir() or (d / "avatars").is_dir()):
            out[d.name] = d
    return out

def code_of(u):
    m = re.search(r"/(p|reel|reels)/([A-Za-z0-9_-]+)", u)
    return m.group(2) if m else None

def rows():
    return json.loads((SAVES / "catalog.json").read_text())["rows"]

def claude_run(prompt):
    return subprocess.run(["claude", "-p", prompt, "--allowedTools", "Read", "Write", "Glob",
                           "Grep", "Bash(ffmpeg*)", "Bash(ffprobe*)"],
                          capture_output=True, text=True, timeout=1800,
                          cwd=str(WS))

def teardown_worker(row):
    code = code_of(row["url"])
    out = TD / code
    out.mkdir(parents=True, exist_ok=True)
    media = TD / "media" / code
    media.mkdir(parents=True, exist_ok=True)
    with LOCK:
        JOBS[code] = {"status": "running", "kind": "teardown"}
    try:
        subprocess.run(["yt-dlp", "-o", str(media / "video.%(ext)s"), "--no-playlist",
                        row["url"]], capture_output=True, timeout=300)
        vids = list(media.glob("video.*"))
        cover = SAVES / "covers" / (row.get("cover_file") or "")
        asset = {"url": row["url"], "author": row.get("author"), "caption": row.get("caption"),
                 "hashtags": row.get("hashtags"), "views": row.get("views"), "likes": row.get("likes"),
                 "category": row.get("category"), "lane": row.get("lane"),
                 "video_file": str(vids[0]) if vids else None,
                 "cover_file": str(cover) if cover.is_file() else None}
        (out / "asset.json").write_text(json.dumps(asset, indent=1))
        stage_list = "\n".join(f"  {i+1}. {CHAIN / s}" for i, s in enumerate(S12))
        prompt = f"""Run the BRAND-NEUTRAL half of the owner's teardown chain on one swiped asset — strip it to structure. No brand is chosen yet; do not inject or reference any of our brands.

The asset: {out / 'asset.json'}
Look at its cover image{' and, if useful, probe the downloaded video with ffmpeg (extract a few frames)' if vids else ''}. There is no transcript; work from caption + visuals and say so honestly wherever the chain expects a script.

The stage prompts, in order, exactly as written:
{stage_list}

Write stage 1 to {out / 'stage1-teardown.md'} and stage 2 to {out / 'stage2-spec.md'}. Clean Markdown. Do not modify any file outside {out}/."""
        r = claude_run(prompt)
        (out / "run.log").write_text((r.stdout or "") + "\n--- stderr ---\n" + (r.stderr or ""))
        with LOCK:
            JOBS[code]["status"] = "done" if (out / "stage2-spec.md").exists() else "failed"
    except Exception as e:
        (out / "run.log").write_text(f"worker error: {e}")
        with LOCK:
            JOBS[code]["status"] = "failed"

def inject_worker(code, brand):
    out = TD / code
    inj = out / "injections" / brand
    inj.mkdir(parents=True, exist_ok=True)
    key = f"{code}:{brand}"
    with LOCK:
        JOBS[key] = {"status": "running", "kind": "inject", "brand": brand}
    try:
        stage_list = "\n".join(f"  {i+1}. {CHAIN / s}" for i, s in enumerate(S35))
        bdir = brands()[brand]
        prompt = f"""Run the INJECTION half of the owner's teardown chain: take a finished brand-neutral teardown and inject the brand `{brand}` into it, ending in the brief.

Inputs, already written:
  the asset: {out / 'asset.json'}
  stage 1 (teardown): {out / 'stage1-teardown.md'}
  stage 2 (replication spec): {out / 'stage2-spec.md'}

Brand context: {bdir}/ — read its CLAUDE.md if present, the avatar profiles and language banks, as the stage prompts direct.

The stage prompts, in order, exactly as written:
{stage_list}

Write stage 3 to {inj / 'stage3-injection.md'} and the stage-5 brief to {inj / 'brief.md'} (the deliverable). Clean Markdown. Do not modify any file outside {inj}/."""
        r = claude_run(prompt)
        (inj / "run.log").write_text((r.stdout or "") + "\n--- stderr ---\n" + (r.stderr or ""))
        with LOCK:
            JOBS[key]["status"] = "done" if (inj / "brief.md").exists() else "failed"
    except Exception as e:
        (inj / "run.log").write_text(f"worker error: {e}")
        with LOCK:
            JOBS[key]["status"] = "failed"

def disk_state():
    """torn-down codes and finished injections, straight from disk."""
    state = {}
    if VID.exists():
        for d in VID.iterdir():
            if (d / "handoff.md").exists():
                state[d.name] = {"torn": False, "briefs": [], "sheet": True}
    if TD.exists():
        for d in TD.iterdir():
            if not d.is_dir() or d.name == "media":
                continue
            st = {"torn": (d / "stage2-spec.md").exists(), "briefs": [],
                  "sheet": state.get(d.name, {}).get("sheet", False)}
            ij = d / "injections"
            if ij.exists():
                st["briefs"] = [b.name for b in ij.iterdir() if (b / "brief.md").exists()]
            if st["torn"] or st["briefs"]:
                state[d.name] = st
    return state

CSS = """
.fmt.is-fam{border-left:4px solid #c58b00}
.tag.thin{background:#f6e0d8;color:#9a3a26;border-color:#e3bdb0}
.tag.ok{background:#dfe9dc;color:#3d5c3d;border-color:#c2d5be}
.tag.fam{background:#fdf0cf;color:#7a5c05;border-color:#e9d69a;cursor:help}
.tag.mech-tag{background:#eceaf5;color:#4b4470;border-color:#d5d0e6}
.tag.st-unreviewed{background:#eee;color:#666}
.tag.st-proposed{background:#e2ecf5;color:#2d5473;border-color:#c3d8e8}
.tag.st-active{background:#dfe9dc;color:#3d5c3d}

:root{--bg:#0c1315;--panel:#141d20;--panel2:#1b2629;--ink:#e6eef0;--mute:#8da4aa;
--line:#25353a;--go:#3ddc84;--wait:#e8a33d;--acc:#5db3e8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 -apple-system,'Segoe UI',sans-serif}
header{padding:20px 24px 6px;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
h1{font-size:22px;margin:0}.sub{color:var(--mute);font-size:13px}
.chips{padding:8px 24px 14px;display:flex;gap:8px;flex-wrap:wrap}
.chip{border:1px solid var(--line);border-radius:999px;background:none;color:var(--mute);
padding:5px 13px;font-size:13px;cursor:pointer}.chip.on{color:var(--ink);border-color:var(--ink)}
.gap{width:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;padding:0 24px 40px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;cursor:pointer;display:none}
.card.show{display:block}
.thumb{position:relative;aspect-ratio:4/5;background:var(--panel2)}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.pill{position:absolute;top:8px;font-size:10px;font-weight:700;letter-spacing:.05em;
padding:3px 7px;border-radius:4px;background:rgba(0,0,0,.55)}
.pl{left:8px}.pr{right:8px}
.st{position:absolute;bottom:8px;left:8px;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px}
.st.running{background:var(--wait);color:#000}.st.done{background:var(--go);color:#000}.st.failed{background:#d9534f;color:#fff}
.body{padding:10px 12px}.who{font-weight:600;font-size:13px}
.cap{color:var(--mute);font-size:12px;margin:4px 0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.meta{color:var(--mute);font-size:11.5px}
#drawer{position:fixed;top:0;right:-460px;width:440px;max-width:92vw;height:100%;background:var(--panel);
border-left:1px solid var(--line);transition:right .2s;overflow-y:auto;z-index:9}
#drawer.open{right:0}
.dwrap{padding:20px}
#drawer img{width:100%;border-radius:8px}
.dcap{font-size:14px;margin:12px 0;white-space:pre-wrap}
.dmeta{color:var(--mute);font-size:13px;margin-bottom:16px}
.btn{display:block;width:100%;margin:8px 0;padding:12px;border-radius:8px;border:none;
font-size:15px;font-weight:700;cursor:pointer}
.b-td{background:var(--go);color:#04140b}
.b-inj{background:var(--acc);color:#04121d}
.b-link{background:var(--panel2);color:var(--ink);border:1px solid var(--line)}
.x{position:absolute;top:12px;right:14px;background:none;border:none;color:var(--mute);font-size:22px;cursor:pointer}
a{color:var(--acc)}
"""

def board_html():
    R = sorted(rows(), key=lambda r: (r.get("views") or 0) + (r.get("likes") or 0) * 10, reverse=True)
    B = list(brands().keys())
    cards = []
    for r in R:
        c = code_of(r["url"])
        if not c:
            continue
        img = f'<img loading="lazy" src="/covers/{r["cover_file"]}">' if r.get("cover_file") else ""
        payload = json.dumps({"code": c, "url": r["url"], "author": r.get("author"),
                              "caption": (r.get("caption") or "")[:600], "views": r.get("views"),
                              "likes": r.get("likes"), "category": r.get("category"),
                              "lane": r.get("lane"), "brand_fit": r.get("brand_fit"),
                              "cover": r.get("cover_file")})
        cards.append(
            f'<div class="card" data-b="{r.get("brand_fit","")}" data-l="{r.get("lane","")}" data-code="{c}" '
            f"onclick='openCard({html.escape(json.dumps(payload))})'>"
            f'<div class="thumb">{img}<span class="pill pl" style="color:var(--go)">{(r.get("lane") or "?").upper()}</span>'
            f'<span class="pill pr" style="color:var(--mute)">{html.escape(r.get("brand_fit",""))}</span>'
            f'<span class="st" id="st-{c}"></span></div>'
            f'<div class="body"><div class="who">{html.escape(r.get("author") or "?")}</div>'
            f'<div class="cap">{html.escape((r.get("caption") or "")[:140])}</div>'
            f'<div class="meta">{(r.get("views") or 0):,} views · {(r.get("likes") or 0):,} likes · {html.escape(r.get("category") or "")}</div></div></div>')
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Swipe Studio</title>
<style>{CSS}</style></head><body>
<header><h1>Swipe Studio</h1><span class="sub">{len(cards)} saves · click a card → Tear down → Inject into any brand</span>
<span class="sub" style="margin-left:auto"><a href="/formats"><b>Format library</b></a> · Feeds:
<a href="/feed/damon--saves">My saves feed</a> ·
<a href="/feed/brand-b--avatar-two">Avatar-two feed</a></span></header>
<div class="chips">
<button class="chip on" data-b="all">All fits</button><button class="chip" data-b="brand-b">Brand B</button>
<button class="chip" data-b="brand-a">Brand A</button><button class="chip" data-b="general">General</button>
<span class="gap"></span>
<button class="chip on" data-l="all">Both lanes</button><button class="chip" data-l="swipe">Swipes</button>
<button class="chip" data-l="organic">Organic</button></div>
<div class="grid">{''.join(cards)}</div>
<div id="drawer"><div class="dwrap" id="dbody"></div></div>
<script>
const BRANDS={json.dumps(B)};
let b="all",l="all",state={{}};
const cards=[...document.querySelectorAll(".card")];
function paint(){{cards.forEach(c=>c.classList.toggle("show",(b==="all"||c.dataset.b===b)&&(l==="all"||c.dataset.l===l)));}}
document.querySelectorAll(".chip").forEach(c=>c.onclick=()=>{{
if(c.dataset.b){{b=c.dataset.b;document.querySelectorAll("[data-b]").forEach(x=>x.classList.toggle("on",x===c));}}
else{{l=c.dataset.l;document.querySelectorAll("[data-l]").forEach(x=>x.classList.toggle("on",x===c));}}paint();}});
paint();
let cur=null;
function openCard(js){{cur=JSON.parse(js);renderDrawer();document.getElementById("drawer").classList.add("open");}}
function renderDrawer(){{if(!cur)return;const r=cur,s=state[r.code]||{{}};
let act="";
if(s.status==="running")act=`<div style="color:var(--wait);font-weight:700">${{s.kind==="inject"?"Injecting "+s.brand+"…":"Tearing down…"}} runs a few minutes.</div>`;
else if(!s.torn)act=`<button class="btn b-td" onclick="tear()">Tear down</button>`;
if(s.sheet)act+=`<a class="btn b-td" style="text-align:center;text-decoration:none" href="/handoff/${{r.code}}">Rebuild sheet — format + Higgsfield ↗</a>`;
if(s.torn){{act+=`<a class="btn b-link" style="text-align:center;text-decoration:none" href="/out/${{r.code}}">Open the teardown ↗</a>`;
act+=BRANDS.map(br=>s.briefs&&s.briefs.includes(br)
?`<a class="btn b-link" style="text-align:center;text-decoration:none" href="/out/${{r.code}}/${{br}}">Brief · ${{br.toUpperCase()}} ↗</a>`
:`<button class="btn b-inj" onclick="inject('${{br}}')">Inject → ${{br.toUpperCase()}}</button>`).join("");}}
document.getElementById("dbody").innerHTML=`<button class="x" onclick="document.getElementById('drawer').classList.remove('open')">×</button>
<h2 style="margin:0 0 10px;font-size:17px">${{r.author||"?"}}</h2>
${{r.cover?`<img src="/covers/${{r.cover}}">`:""}}
<div class="dmeta">${{(r.views||0).toLocaleString()}} views · ${{(r.likes||0).toLocaleString()}} likes · ${{r.category||""}} · ${{r.lane}}</div>
<div class="dcap">${{r.caption||""}}</div>
<a href="${{r.url}}" target="_blank">Open the post ↗</a>
<div style="margin-top:18px">${{act}}</div>`;}}
async function tear(){{await fetch("/tear",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{code:cur.code}})}});poll();}}
async function inject(brand){{await fetch("/inject",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{code:cur.code,brand}})}});poll();}}
async function poll(){{state=await(await fetch("/status")).json();
for(const[c,s]of Object.entries(state)){{const el=document.getElementById("st-"+c);if(!el)continue;
if(s.status==="running"){{el.className="st running";el.textContent=(s.kind==="inject"?"INJECTING":"TEARING DOWN");}}
else if(s.briefs&&s.briefs.length){{el.className="st done";el.textContent="BRIEF: "+s.briefs.join(", ").toUpperCase();}}
else if(s.torn){{el.className="st done";el.textContent="TORN DOWN";}}
else if(s.sheet){{el.className="st done";el.textContent="REBUILD SHEET";
 el.onclick=e=>{{e.stopPropagation();location="/handoff/"+c;}};}}
else if(s.status==="failed"){{el.className="st failed";el.textContent="FAILED";}}}}
renderDrawer();
if(Object.values(state).some(s=>s.status==="running"))setTimeout(poll,5000);}}
poll();
</script></body></html>"""

def out_page(code, brand=None):
    base = TD / code
    files = ([("injections/" + brand + "/brief.md", "The brief — " + brand.upper()),
              ("injections/" + brand + "/stage3-injection.md", "Stage 3 — injection")] if brand else []) + \
            [("stage2-spec.md", "Stage 2 — replication spec"), ("stage1-teardown.md", "Stage 1 — teardown")]
    parts = []
    for name, title in files:
        f = base / name
        if f.exists():
            parts.append(f"<h2>{title}</h2><pre style='white-space:pre-wrap;font:13px/1.55 -apple-system,sans-serif;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px'>{html.escape(f.read_text())}</pre>")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{code}</title><style>{CSS}</style></head>"
            f"<body><div style='max-width:860px;margin:0 auto;padding:30px 22px'><a href='/'>← back to the board</a>"
            f"<h1 style='margin:14px 0'>{code}{' · ' + brand.upper() if brand else ''}</h1>{''.join(parts) or '<p>Nothing written yet.</p>'}</div></body></html>")

def md(t):
    """Just enough Markdown for a handoff sheet."""
    # pipe tables first — the beat table is the most-read thing on the page
    lines, tbl, buf = [], False, []
    for ln in t.split("\n") + [""]:
        if ln.startswith("|"):
            tbl = True
            buf.append(ln)
            continue
        if tbl:
            rows = [r for r in buf if not re.match(r"^\|[\s:|-]+\|$", r)]
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            if cells:
                head = "".join(f"<th>{html.escape(c)}</th>" for c in cells[0])
                body = "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>"
                               for r in cells[1:])
                lines.append(f"<div class='tw'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")
            tbl, buf = False, []
        lines.append(ln)
    t = "\n".join(lines)
    out, fence = [], False
    for ln in t.split("\n"):
        if ln.startswith("<div class='tw'>"):
            out.append(ln)
            continue
        if ln.startswith("```"):
            fence = not fence
            out.append("<pre class='pp'>" if fence else "</pre>")
            continue
        if fence:
            out.append(html.escape(ln))
            continue
        e = html.escape(ln)
        e = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e)
        e = re.sub(r"`(.+?)`", r"<code>\1</code>", e)
        if ln.startswith("### "): out.append(f"<h3>{e[4:]}</h3>")
        elif ln.startswith("## "): out.append(f"<h2>{e[3:]}</h2>")
        elif ln.startswith("# "): out.append(f"<h1>{e[2:]}</h1>")
        elif ln.startswith(("- ", "* ")): out.append(f"<li>{e[2:]}</li>")
        elif not ln.strip(): out.append("<div class='sp'></div>")
        else: out.append(f"<p>{e}</p>")
    return "\n".join(out)

DRIVE = " ▸ ".join(swipe_home.label("organic", "records", "swipe-videos",
                                    "{code}", "video.mp4").split("/"))

def format_page(fid):
    """One format, its examples, and the pack you send a maker."""
    lib = json.loads((HERE / "formats.json").read_text())
    f = next((x for x in lib["formats"] if x["id"] == fid), None)
    if not f:
        return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div style='padding:30px'><a href='/formats'>← the library</a><p>No format {html.escape(fid)}.</p></div></body></html>"
    cat = {code_of(r["url"]): r for r in rows() if code_of(r["url"])}
    mine = []
    for d in (VID.iterdir() if VID.exists() else []):
        p = d / "format.json"
        if not p.is_file():
            continue
        try:
            if json.loads(p.read_text()).get("format_id") == fid:
                mine.append(d.name)
        except Exception:
            pass
    mine.sort(key=lambda c: (cat.get(c, {}).get("views") or 0), reverse=True)
    ev = f["evidence"][0]
    tiles = []
    for c in mine:
        r = cat.get(c, {})
        img = f'<img src="/covers/{r["cover_file"]}">' if r.get("cover_file") else '<img src="/sheet/' + c + '">'
        tiles.append(f'''<a class="tile" href="/handoff/{c}">{img}
<div class="tb"><b>{html.escape(r.get("author") or c)}</b>
<span>{(r.get("views") or 0):,} views</span></div></a>''')
    refs = "\n".join(f"  {i+1}. https://www.instagram.com/p/{c}/  ({(cat.get(c,{}).get('views') or 0):,} views)"
                     for i, c in enumerate(mine[:3]))
    pack = f"""FORMAT: {f['name']}

WHAT IT IS
{f['mechanic']}

WHY IT WORKS
{f['why_it_works']}

THE BEATS, IN ORDER
""" + "\n".join(f"  {i+1}. {b}" for i, b in enumerate(f["beats"])) + f"""

ON-SCREEN TEXT
{f.get('text_behaviour','—')}

CAMERA
{f.get('camera','—')}

HIGGSFIELD — IMAGE
{f['higgsfield']['image']}

HIGGSFIELD — MOTION
{f['higgsfield']['motion']}

REFERENCE VIDEOS (watch before you shoot)
{refs}
Reference files also on the shared drive at:
  {DRIVE.format(code='<post code>')}

RULES
  - Rebuild the STRUCTURE, not the content. Different product, same shape.
  - Nothing invented: if the brief does not state a wardrobe, a room or how
    the product looks, ask before you generate it.
  - No on-screen text beyond the pattern above."""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(f['name'])}</title><style>{CSS}
.wrap{{max-width:940px;margin:0 auto;padding:26px 22px 60px}}
.mech{{margin:8px 0}}.why{{color:var(--mute);margin:8px 0}}
.beats{{display:grid;gap:6px;margin:14px 0}}
.beat{{background:var(--panel2);border-left:2px solid var(--go);padding:8px 12px;border-radius:0 6px 6px 0;font-size:13.5px}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin:12px 0 22px}}
.tile{{background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden;text-decoration:none;color:inherit}}
.tile img{{width:100%;aspect-ratio:4/5;object-fit:cover;display:block;background:var(--panel2)}}
.tb{{padding:7px 9px;font-size:12px}}.tb b{{display:block;font-size:12.5px}}.tb span{{color:var(--mute)}}
.klabel{{font-size:11px;font-weight:700;color:var(--mute);letter-spacing:.05em;margin:16px 0 5px}}
.pp{{background:#0a1012;border:1px solid var(--line);border-radius:8px;padding:14px;white-space:pre-wrap;
font:12.5px/1.6 ui-monospace,Menlo,monospace;margin:0}}
.cw{{position:relative}}.copy{{position:absolute;top:10px;right:10px;background:var(--go);color:#04140b;
border:none;border-radius:6px;padding:6px 13px;font-size:12px;font-weight:700;cursor:pointer}}
.tag{{font-size:11px;font-weight:700;background:var(--panel2);color:var(--mute);padding:4px 9px;border-radius:5px}}
</style></head><body><div class="wrap">
<a href="/formats">← the library</a> · <a href="/">the board</a>
<h1 style="margin:14px 0 6px">{html.escape(f['name'])}</h1>
<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
{f'<span class="tag">{ev["views"]:,} views proved it</span>' if ev.get("views") is not None else ''}<span class="tag">{len(mine)} of your swipes</span></div>
<p class="mech">{html.escape(f['mechanic'])}</p>
<p class="why"><b>Why it works.</b> {html.escape(f['why_it_works'])}</p>
<div class="beats">{''.join(f'<div class="beat">{html.escape(b)}</div>' for b in f['beats'])}</div>
<h2 style="font-size:17px;margin:22px 0 4px">Your swipes in this format</h2>
<p style="color:var(--mute);font-size:13.5px;margin:0">Click any one for its rebuild sheet — beats, timestamps, prompts and the reference video.</p>
<div class="tiles">{''.join(tiles) or '<p style="color:var(--mute)">None yet.</p>'}</div>
<h2 style="font-size:17px;margin:0 0 4px">The pack you send a maker</h2>
<p style="color:var(--mute);font-size:13.5px;margin:0 0 8px">Everything they need in one paste — structure, prompts, references, rules.</p>
<div class="cw"><pre class="pp" id="pack">{html.escape(pack)}</pre>
<button class="copy" onclick="cp()">Copy the pack</button></div></div>
<script>function cp(){{navigator.clipboard.writeText(document.getElementById("pack").innerText);
event.target.textContent="Copied";setTimeout(()=>event.target.textContent="Copy the pack",1400);}}</script>
</body></html>"""

def formats_page():
    lib = json.loads((HERE / "formats.json").read_text())
    seen = {}
    for d in (VID.iterdir() if VID.exists() else []):
        f = d / "format.json"
        if f.is_file():
            try:
                seen.setdefault(json.loads(f.read_text()).get("format_id"), []).append(d.name)
            except Exception:
                pass
    fams = lib.get("families", {})
    cards = []
    # strongest evidence first — the review has to start somewhere honest
    order = sorted(lib["formats"],
                   key=lambda x: (-(x.get("proof", {}).get("posts") or len(x.get("evidence") or [])),
                                  -(x.get("proof", {}).get("best_views") or 0)))
    for f in order:
        mine = seen.get(f["id"], [])
        ev = f["evidence"][0]
        links = " · ".join(f'<a href="/handoff/{c}">{c}</a>' for c in mine[:8])

        # two evidence shapes live in this file: a swiped post (code/author/views)
        # and a clip from our own delivered footage (clip/creator/note). Assuming
        # the first is what blanked this whole page — render whichever it is.
        if "code" in ev:
            evidence_line = (f'Proved by <a href="https://www.instagram.com/p/{ev["code"]}/"'
                             f' target="_blank">@{html.escape(ev["author"])}</a>'
                             f' — “{html.escape(ev.get("line",""))}”')
        else:
            who = html.escape(str(ev.get("creator") or "our own footage"))
            note = html.escape(str(ev.get("note") or ev.get("clip") or ""))
            evidence_line = f'From our own delivered footage — {who}{" — " + note if note else ""}'

        proof = f.get("proof") or {}
        n = proof.get("posts", len(f.get("evidence") or []))
        best = proof.get("best_views") or 0
        # the denominator, on the card — a shape seen once is a shape seen once
        proven = (f'<span class="tag thin">{n} post — seen once, not proven</span>'
                  if n < 2 else f'<span class="tag ok">{n} posts behind it</span>')
        views = f'<span class="tag">{best:,} views at best</span>' if best else ''

        st = f.get("state") or f.get("status", "unreviewed")   # rule 6: the review word lives in `state` (triage page 15)
        stpill = f'<span class="tag st-{st}">{st}</span>'

        fam = f.get("family")
        fampill = ''
        if fam:
            mech = html.escape(fams.get(fam, {}).get("mechanic", ""))
            others = len(fams.get(fam, {}).get("members", [])) - 1
            fampill = (f'<span class="tag fam" title="{mech}">shares a text mechanic with {others} other'
                       f'{"s" if others != 1 else ""} — differs by {html.escape(f.get("differs_by",""))}</span>')

        tm = f.get("text_mechanic")
        tmpill = f'<span class="tag mech-tag">{html.escape(tm)}</span>' if tm else ''

        cards.append(f"""<div class="fmt{' is-fam' if fam else ''}"><h2><a href="/format/{f['id']}" style="text-decoration:none">{html.escape(f['name'])}</a></h2>
<div class="pillrow">{stpill}{proven}{views}{fampill}{tmpill}
<a class="tag" href="/format/{f['id']}" style="text-decoration:none">{len(mine)} of your swipes use it →</a></div>
<p class="mech">{html.escape(f['mechanic'])}</p>
<p class="why"><b>Why it works.</b> {html.escape(f['why_it_works'])}</p>
<div class="beats">{''.join(f'<div class="beat">{html.escape(b)}</div>' for b in f['beats'])}</div>
<div class="kit"><div class="klabel">Higgsfield — image</div><pre class="pp">{html.escape(f['higgsfield']['image'])}</pre>
<div class="klabel">Higgsfield — motion</div><pre class="pp">{html.escape(f['higgsfield']['motion'])}</pre></div>
<div class="ev">{evidence_line}{'<br>Yours: ' + links if links else ''}</div></div>""")
    # formats the machine proposed that aren't in the library yet — the discovery surface
    prop = {}
    for dd in (VID.iterdir() if VID.exists() else []):
        f = dd / "format.json"
        if not f.is_file():
            continue
        try:
            j = json.loads(f.read_text())
        except Exception:
            continue
        fid = j.get("format_id", "")
        if fid.startswith("new:"):
            p = prop.setdefault(fid, {"codes": [], "why": j.get("why", ""),
                                      "carries": j.get("carries_the_value", "")})
            p["codes"].append(dd.name)
    pr = []
    for k, v in sorted(prop.items(), key=lambda kv: -len(kv[1]["codes"])):
        name = html.escape(k[4:].replace("-", " "))
        line = html.escape(v["carries"] or v["why"])
        links = " · ".join(f'<a href="/handoff/{c}">{c}</a>' for c in v["codes"][:10])
        n = len(v["codes"])
        pr.append(f'<div class="prop"><div class="ph"><b>{name}</b>'
                  f'<span class="tag">{n} swipe{"s" if n > 1 else ""}</span></div>'
                  f'<p class="mech">{line}</p><div class="ev">{links}</div></div>')
    emerging = ('<h2 style="margin:34px 0 6px;font-size:19px">Emerging — proposed from your swipes</h2>'
                '<p style="color:var(--mute);margin:0 0 14px;font-size:14px">Structures the machine found '
                'that were not in the library. They earn a card above once they repeat and a human reads '
                'them.</p>' + "".join(pr)) if pr else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Formats</title><style>{CSS}
.prop{{background:var(--panel);border:1px solid var(--line);border-left:2px solid var(--wait);
border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:10px}}
.ph{{display:flex;gap:10px;align-items:center;margin-bottom:4px}}.ph b{{font-size:15px}}
.wrap{{max-width:900px;margin:0 auto;padding:26px 22px 60px}}
.fmt{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px 22px;margin-bottom:18px}}
.fmt h2{{margin:0 0 8px;font-size:20px}}
.pillrow{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}}
.tag{{font-size:11px;font-weight:700;letter-spacing:.04em;background:var(--panel2);color:var(--mute);padding:4px 9px;border-radius:5px}}
.mech{{margin:8px 0}}.why{{color:var(--mute);margin:8px 0}}
.beats{{display:grid;gap:6px;margin:12px 0}}
.beat{{background:var(--panel2);border-left:2px solid var(--go);padding:7px 11px;border-radius:0 6px 6px 0;font-size:13.5px}}
.kit{{margin-top:12px}}.klabel{{font-size:11px;font-weight:700;color:var(--mute);letter-spacing:.05em;margin:10px 0 4px}}
.pp{{background:#0a1012;border:1px solid var(--line);border-radius:8px;padding:12px;white-space:pre-wrap;
font:12.5px/1.5 ui-monospace,Menlo,monospace;color:var(--ink);margin:0}}
.ev{{color:var(--mute);font-size:12.5px;margin-top:12px;border-top:1px solid var(--line);padding-top:10px}}
</style></head><body><div class="wrap">
<a href="/">← the board</a>
<h1 style="margin:14px 0 4px">The format library <span style="font-size:16px;opacity:.55;font-weight:400">&mdash; organic video only</span></h1>
<p style="color:var(--mute);margin:0 0 22px">The structures behind your ORGANIC VIDEO swipes, reverse-engineered from the frames. Not paid swipes, not proven brand assets, not page, email or copy formats — each of those is its own bank. Brand-free on purpose; the brand goes in at injection.</p>
{''.join(cards)}{emerging}</div></body></html>"""

def handoff_page(code):
    d = VID / code
    hf = d / "handoff.md"
    if not hf.is_file():
        return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div style='padding:30px'><a href='/'>← the board</a><p>No handoff written for {html.escape(code)} yet.</p></div></body></html>"
    fj = {}
    if (d / "format.json").is_file():
        try:
            fj = json.loads((d / "format.json").read_text())
        except Exception:
            pass
    prompts = ""
    hg = fj.get("higgsfield") or {}
    if hg:
        prompts = "".join(
            f'<div class="klabel">{k.replace("_"," ").title()}</div>'
            f'<div class="cw"><pre class="pp" id="p{i}">{html.escape(v)}</pre>'
            f'<button class="copy" onclick="cp(\'p{i}\')">Copy</button></div>'
            for i, (k, v) in enumerate(hg.items()) if v)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(code)} — rebuild sheet</title><style>{CSS}
.wrap{{max-width:1080px;margin:0 auto;padding:26px 22px 60px;display:grid;grid-template-columns:340px 1fr;gap:26px;align-items:start}}
@media(max-width:820px){{.wrap{{grid-template-columns:1fr}}}}
.side video{{width:100%;border-radius:10px;background:#000}}
.side img{{width:100%;border-radius:8px;margin-top:12px}}
.doc h1{{font-size:22px;margin:0 0 10px}}.doc h2{{font-size:16px;margin:20px 0 6px}}
.doc p{{margin:6px 0}}.doc li{{margin:3px 0 3px 18px}}.sp{{height:8px}}
.tw{{overflow-x:auto;margin:10px 0}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th{{text-align:left;color:var(--mute);font-size:11px;letter-spacing:.05em;text-transform:uppercase;
padding:6px 10px;border-bottom:1px solid var(--line)}}
td{{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
td:first-child{{white-space:nowrap;color:var(--go);font:12px ui-monospace,Menlo,monospace}}
.pp{{background:#0a1012;border:1px solid var(--line);border-radius:8px;padding:12px;white-space:pre-wrap;
font:12.5px/1.5 ui-monospace,Menlo,monospace;margin:0}}
.klabel{{font-size:11px;font-weight:700;color:var(--mute);letter-spacing:.05em;margin:14px 0 4px}}
.cw{{position:relative}}.copy{{position:absolute;top:8px;right:8px;background:var(--acc);color:#04121d;
border:none;border-radius:6px;padding:5px 11px;font-size:12px;font-weight:700;cursor:pointer}}
code{{background:var(--panel2);padding:1px 5px;border-radius:4px;font-size:12.5px}}
</style></head><body><div class="wrap">
<div class="side"><a href="/">← the board</a> · <a href="/formats">formats</a>
<video controls playsinline src="/video/{code}"></video>
<img src="/sheet/{code}" alt="beats">
{prompts}</div>
<div class="doc">{md(hf.read_text())}</div></div>
<script>function cp(id){{navigator.clipboard.writeText(document.getElementById(id).innerText);
event.target.textContent="Copied";setTimeout(()=>event.target.textContent="Copy",1200);}}</script>
</body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, body, ctype="text/html; charset=utf-8", status=200):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            return self._send(board_html())
        if self.path.startswith("/covers/"):
            f = SAVES / "covers" / Path(self.path).name
            return self._send(f.read_bytes(), "image/jpeg") if f.is_file() else self._send("", status=404)
        m = re.match(r"^/feed/([a-z-]+--[a-z-]+)$", self.path)
        if m:
            f = HERE / "records/avatar-feeds" / m.group(1) / "feed.html"
            if f.is_file():
                # the page is built for the repo; in the app, covers are served locally
                body = f.read_text().replace("../../damon-saves/covers/", "/covers/")
                return self._send(body)
            return self._send("no such feed", status=404)
        if self.path == "/formats":
            return self._send(formats_page())
        m = re.match(r"^/format/([a-z0-9-]+)$", self.path)
        if m:
            return self._send(format_page(m.group(1)))
        m = re.match(r"^/handoff/([A-Za-z0-9_-]+)$", self.path)
        if m:
            return self._send(handoff_page(m.group(1)))
        m = re.match(r"^/video/([A-Za-z0-9_-]+)$", self.path)
        if m:
            f = VID / m.group(1) / "video.mp4"
            if not f.is_file():
                return self._send("", status=404)
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        m = re.match(r"^/sheet/([A-Za-z0-9_-]+)$", self.path)
        if m:
            f = VID / m.group(1) / "sheet.jpg"
            return self._send(f.read_bytes(), "image/jpeg") if f.is_file() else self._send("", status=404)
        if self.path == "/status":
            with LOCK:
                merged = {}
                for c, st in disk_state().items():
                    merged[c] = {"torn": st["torn"], "briefs": st["briefs"],
                                 "sheet": st.get("sheet", False), "status": "idle"}
                for k, j in JOBS.items():
                    c = k.split(":")[0]
                    merged.setdefault(c, {"torn": False, "briefs": [], "sheet": False, "status": "idle"})
                    if j["status"] == "running":
                        merged[c].update(status="running", kind=j["kind"], brand=j.get("brand"))
                    elif j["status"] == "failed" and merged[c]["status"] != "running":
                        merged[c]["status"] = "failed"
                return self._send(json.dumps(merged), "application/json")
        m = re.match(r"^/out/([A-Za-z0-9_-]+)(?:/(\w+))?$", self.path)
        if m:
            return self._send(out_page(m.group(1), m.group(2)))
        return self._send("not found", status=404)
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n) or "{}")
        if self.path == "/tear":
            row = next((r for r in rows() if code_of(r["url"]) == req.get("code")), None)
            if not row:
                return self._send('{"ok":false}', "application/json", 400)
            threading.Thread(target=teardown_worker, args=(row,), daemon=True).start()
            return self._send('{"ok":true}', "application/json")
        if self.path == "/inject":
            if req.get("brand") not in brands() or not (TD / req.get("code", "") / "stage2-spec.md").exists():
                return self._send('{"ok":false,"why":"tear down first"}', "application/json", 400)
            threading.Thread(target=inject_worker, args=(req["code"], req["brand"]), daemon=True).start()
            return self._send('{"ok":true}', "application/json")
        return self._send("not found", status=404)

if __name__ == "__main__":
    # RETIRED 2026-09-22, his call: "remove swipe studio, everything needs to
    # live in my feeds". The board is gone; the file stays as the library that
    # builds the format bank and the rebuild sheet, which My Feeds now serves
    # at /formats and /handoff/<code>. Nothing was deleted — to bring the old
    # board back for an hour, call serve() below.
    import sys
    sys.exit("Swipe Studio was retired on 2026-09-22 — open My Feeds instead:\n"
             "    http://localhost:8820\n"
             "The saves are the 'damon · my saves' feed there; the format library\n"
             "is the link in its header, and every card has its rebuild sheet.")


def serve():
    TD.mkdir(exist_ok=True)
    print(f"Swipe Studio → http://localhost:{PORT} · brands: {', '.join(brands())}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
