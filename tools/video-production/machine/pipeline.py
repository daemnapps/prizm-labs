#!/usr/bin/env python3
"""THE MASTER VIEW — the whole video road, in action, on one page.

    python3 pipeline.py            # build pipeline.html
    python3 pipeline.py --serve    # ...and serve it live on 8792

Four machines, one road:

    a swipe → TEARDOWN → a brief → PRODUCTION → an approved film
                                                      └→ VARIATION × every format

Each machine already owns its chain config; this reads all of them rather
than restating any, so a stage added anywhere appears here on the next
reload and this page can never drift from what actually runs.

It also reads live run state, so the page shows where real work sits right
now — which is the difference between a diagram and a view.
"""

import argparse
import html
import sys
import json
import re
import time
from pathlib import Path

WS = Path.home() / "Projects" / "ai-workspace"
TD = WS / "components/video-teardown/machine"
VP = WS / ""
SWIPE = WS / "swipe-organic/records/teardowns"
OUT = VP / "machine/pipeline.html"

STAGE_NAMES = {
    "stage1": "Teardown", "stage1b": "Audience read", "stage2": "Replication spec",
    "stage3": "Injection", "stage4a": "Hook — read", "stage4b": "Hook — hooks",
    "stage4c": "Hook — placement", "stage4d": "Hook — expansion",
    "stage4e": "Hook — close", "stage5": "The brief", "stage6": "Frames",
}


def chains():
    vp = json.loads((VP / "chain_config.json").read_text())
    # THE TEARDOWN CHAIN COMES FROM THE MACHINE ITSELF, not from its config
    # file. chain_config.json is only half of it — chain.py also folds in
    # extra-stages.json (audit, inject, profile) and the triage stage, so
    # reading the config alone under-reported 15 real stages as 11
    # (caught by Damon, 2026-09-02).
    import importlib.util
    spec = importlib.util.spec_from_file_location("vt_chain", TD / "chain.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TD))
    spec.loader.exec_module(mod)
    tear = [{"stage": st.get("key") or st.get("stage"),
             "name": st.get("name") or STAGE_NAMES.get(st.get("key", ""), "?"),
             "kind": "prompt" if st.get("prompt") else "machine",
             "why": st.get("why", "")} for st in mod.stages()]
    prod = [{"stage": s["stage"], "name": s.get("name", s["stage"]),
             "kind": "prompt" if s.get("prompt") else "machine",
             "why": s.get("why", "")} for s in vp["stages"]]
    var = [{"stage": s["stage"], "name": s.get("name", s["stage"]),
            "kind": ("human" if s.get("runner") == "human"
                     else "prompt" if s.get("prompt") else "machine"),
            "why": s.get("why", "")} for s in vp["variation_stages"]]
    return tear, prod, var


def drive_brands():
    """The Drive mirror of the brand tree, if this machine has it mounted."""
    base = Path.home() / "Library/CloudStorage"
    if not base.is_dir():
        return None
    for m in sorted(base.glob("GoogleDrive-*")):
        d = m / "Shared drives/Shared Assets/brands"
        if d.is_dir():
            return d
    return None


def pools():
    """THE THREE SWIPE POOLS (Damon, 2026-09-02). Everything the road can
    start from, and they are not the same kind of thing:

      WINNERS    — our own ads that already performed. The only pool that
                   arrives with proof attached.
      COMPETITORS— other brands' paid creative, swept and torn down.
      ORGANIC    — what the avatar actually watches. No ad intent at all.
    """
    out = []

    # winners — our own running creative
    # actual creative only — a copy bank is notes about ads, not ads
    MEDIA = (".mp4", ".mov", ".jpg", ".jpeg", ".png", ".webp")
    # intake/ads is the v6 name; existing-content/ads the old one, read too
    INTAKE = ("*/intake/ads", "*/existing-content/ads")
    ads = [p for pat in INTAKE for b in (WS / "brands").glob(pat)
           for p in b.rglob("*")
           if p.is_file() and p.suffix.lower() in MEDIA]
    try:
        ads += [p for pat in INTAKE for b in (drive_brands() or []).glob(pat)
                for p in b.rglob("*")
                if p.is_file() and p.suffix.lower() in MEDIA]
    except Exception:
        pass
    out.append({"key": "winners", "name": "Our winners",
                "what": "our own ads that already performed — the only pool "
                        "that comes with proof of what worked",
                "n": len(ads), "unit": "banked",
                "state": "live" if ads else "empty",
                "note": "the Meta accounts are connected and queryable; "
                        "nothing has been banked here yet"})

    # competitors — swipe-paid brands
    sp = WS / "swipe-paid"
    brands, creatives = 0, 0
    rm = sp / "README.md"
    if rm.is_file():
        for line in rm.read_text().splitlines():
            if line.startswith("| ["):
                cells = [c.strip() for c in line.strip("|").split("|")]
                brands += 1
                try:
                    creatives += int(cells[3].replace(",", ""))
                except Exception:
                    pass
    out.append({"key": "competitors", "name": "Competitors",
                "what": "other brands' paid creative, swept and torn down "
                        "brand by brand",
                "n": creatives, "unit": f"creatives · {brands} brands",
                "state": "live" if creatives else "empty",
                "note": "swipe-paid"})

    # organic — the avatar's feed
    n = 0
    f = WS / "swipe-organic/records/avatar-feeds/damon--saves/items.json"
    if f.is_file():
        try:
            d = json.loads(f.read_text())
            items = d.get("items", d)
            n = len(items)
        except Exception:
            n = 0
    out.append({"key": "organic", "name": "Organic",
                "what": "what the avatar actually watches — no ad intent, "
                        "which is why the formats are different",
                "n": n, "unit": "posts",
                "state": "live" if n else "empty",
                "note": "the feed board, with a Tear down button on every card"})
    return out


def live_run():
    """The run in flight right now, if there is one — so the road below is a
    LIVE view and not a diagram. Newest teardown run wins; a run whose
    run.json has not been touched in an hour is finished, not running."""
    root = TD / "runs"
    if not root.is_dir():
        return None
    best = None
    for d in root.iterdir():
        rj = d / "run.json"
        if not rj.is_file():
            continue
        if best is None or rj.stat().st_mtime > best[0]:
            best = (rj.stat().st_mtime, d)
    if not best:
        return None
    age = time.time() - best[0]
    try:
        st = json.loads((best[1] / "run.json").read_text())
    except Exception:
        return None
    stages = st.get("stages") or {}
    running = [k for k, v in stages.items() if v.get("status") == "running"]
    return {"slug": best[1].name,
            "label": st.get("label") or best[1].name,
            "brand": st.get("brand") or "", "route": st.get("production_route") or "",
            "lane": st.get("triage_lane") or "",
            "stages": {k: v.get("status") for k, v in stages.items()},
            "now": running[0] if running else None,
            "live": age < 3600 and bool(running),
            "age": int(age)}


def counts():
    n_tear = len(list((TD / "runs").glob("*/run.json"))) if (TD / "runs").is_dir() else 0
    n_brief = len(list((TD / "runs").glob("*/brief-final.md"))) if (TD / "runs").is_dir() else 0
    ident = list((WS / "brands").glob("*/*/*/lora.json")) + \
            list((WS / "brands").glob("*/*/lora.json"))
    voices = list((WS / "brands").glob("*/ai-elements/characters/*/voice.json")) + \
             list((WS / "brands").glob("*/ai-cast/*/voice.json"))
    fmts = len(list((VP / "formats").glob("*.md"))) - 1  # README
    return {"runs": n_tear, "briefs": n_brief, "identities": len(ident),
            "voices": len(voices), "formats": max(fmts, 0)}


CSS = """
:root{--paper:#F4F2ED;--sheet:#FBFAF7;--ink:#191C24;--ink-soft:#4C5261;--ink-faint:#828A9B;
--rule:#D8D4CB;--rule-soft:#E7E4DC;--a:#B23A2F;--a-bg:#F6E9E6;--b:#3D5674;--b-bg:#EAEEF3;
--c:#2E6B4F;--c-bg:#E6F0EA;--d:#8A6D1F;--d-bg:#F7F0DC;--code:#F1EEE7;}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#0F1218;--sheet:#161A22;
--ink:#E8E6E1;--ink-soft:#A6AEBF;--ink-faint:#6E7789;--rule:#2A303C;--rule-soft:#222833;
--a:#E2705F;--a-bg:#2A1B18;--b:#8FB0D4;--b-bg:#1A222E;--c:#5FBF8F;--c-bg:#12241B;
--d:#D9B44A;--d-bg:#2A2312;--code:#12161D;}}
:root[data-theme="dark"]{--paper:#0F1218;--sheet:#161A22;--ink:#E8E6E1;--ink-soft:#A6AEBF;
--ink-faint:#6E7789;--rule:#2A303C;--rule-soft:#222833;--a:#E2705F;--a-bg:#2A1B18;
--b:#8FB0D4;--b-bg:#1A222E;--c:#5FBF8F;--c-bg:#12241B;--d:#D9B44A;--d-bg:#2A2312;--code:#12161D;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font:400 17px/1.6 Karla,ui-sans-serif,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1000px;margin:0 auto;padding:0 24px}
h1,h2,h3{text-wrap:balance;margin:0}
.mast{padding:60px 0 34px;border-bottom:1px solid var(--rule)}
.slate{font:500 12px/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.13em;
text-transform:uppercase;color:var(--ink-faint);margin-bottom:20px}
h1{font-family:"Instrument Serif",Georgia,serif;font-weight:400;
font-size:clamp(38px,7vw,64px);line-height:1.04}
h1 em{font-style:italic;color:var(--b)}
.standfirst{margin-top:18px;font-size:19px;color:var(--ink-soft);max-width:64ch}
.tally{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:2px;
background:var(--rule);border:1px solid var(--rule);border-radius:3px;overflow:hidden;margin:30px 0 0}
.t{background:var(--sheet);padding:16px 18px}
.t b{display:block;font:400 27px/1 "Instrument Serif",Georgia,serif;color:var(--b);margin-bottom:5px}
.t span{font-size:13.5px;color:var(--ink-soft)}
.road{padding:44px 0;border-bottom:1px solid var(--rule-soft)}
.leg{margin-bottom:34px}
.leg:last-child{margin-bottom:0}
.legh{display:flex;align-items:baseline;gap:12px;margin-bottom:6px;flex-wrap:wrap}
.legh h2{font-family:"Instrument Serif",Georgia,serif;font-size:clamp(23px,3.6vw,30px)}
.pill{font:600 10.5px/1 "IBM Plex Mono",monospace;letter-spacing:.09em;padding:5px 8px;border-radius:2px}
.p-a{background:var(--a-bg);color:var(--a)}.p-b{background:var(--b-bg);color:var(--b)}
.p-c{background:var(--c-bg);color:var(--c)}.p-d{background:var(--d-bg);color:var(--d)}
.legsub{color:var(--ink-soft);font-size:16px;margin:0 0 14px;max-width:68ch}
.stages{display:flex;flex-wrap:wrap;gap:5px}
.st{font:500 12px/1.35 "IBM Plex Mono",monospace;padding:8px 10px;border-radius:2px;
border:1px solid var(--rule);background:var(--sheet);color:var(--ink-soft);position:relative}
.st b{color:var(--ink);font-weight:600}
.st.m{border-style:dashed;color:var(--ink-faint)}
.st.h{border-color:var(--d);color:var(--d)}
.pools{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:2px;
background:var(--rule);border:1px solid var(--rule);border-radius:3px;overflow:hidden}
.pool{background:var(--sheet);padding:20px 22px}
.pool.empty{background:var(--paper)}
.pn{font:600 12px/1 "IBM Plex Mono",monospace;letter-spacing:.09em;text-transform:uppercase;
color:var(--a);margin-bottom:12px}
.pool.empty .pn{color:var(--ink-faint)}
.pq{font:400 34px/1 "Instrument Serif",Georgia,serif;color:var(--ink);margin-bottom:3px}
.pool.empty .pq{color:var(--ink-faint)}
.pu{font:500 11.5px/1 "IBM Plex Mono",monospace;color:var(--ink-faint);margin-bottom:12px}
.pool p{font-size:14.5px;line-height:1.5;color:var(--ink-soft);margin:0 0 10px}
.pnote{font-size:12.5px;color:var(--ink-faint);font-style:italic}
.live{margin:26px 0 0;padding:16px 20px;border-radius:3px;border:1px solid var(--rule);
background:var(--sheet);display:flex;justify-content:space-between;align-items:center;
flex-wrap:wrap;gap:10px}
.live.live{border-color:var(--c)}
.live .lh{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.live b{font-size:16px}
.lmeta{font:500 11.5px/1 "IBM Plex Mono",monospace;color:var(--ink-faint)}
.lnow{font:600 12px/1 "IBM Plex Mono",monospace;color:var(--c);letter-spacing:.06em}
.live.idle .lnow{color:var(--ink-faint)}
.dotm{width:9px;height:9px;border-radius:50%;background:var(--c);flex:none}
.live.idle .dotm{background:var(--ink-faint)}
.live.live .dotm{animation:pulse 1.4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.live.live .dotm{animation:none}}
.st.done{border-color:var(--c);color:var(--c);background:var(--c-bg)}
.st.done b{color:var(--c)}
.st.now{border-color:var(--d);background:var(--d-bg);color:var(--d)}
.st.now b{color:var(--d)}
.st.skip{opacity:.45;text-decoration:line-through}
.arrow{text-align:center;color:var(--ink-faint);font-size:20px;margin:14px 0;letter-spacing:.3em}
a{color:var(--b)}
.note{padding:44px 0}
.note p{max-width:66ch;margin:0 0 13px}
.mono{font-family:"IBM Plex Mono",monospace;font-size:13.5px}
footer{padding:34px 0 66px;color:var(--ink-faint);font-size:14px;border-top:1px solid var(--rule-soft)}
@media(max-width:640px){body{font-size:16px}.st{font-size:11px}}
"""


def render():
    tear, prod, var = chains()
    c = counts()
    pl = pools()
    run = live_run()

    pool_cards = '<div class="pools">'
    for x in pl:
        empty = " empty" if x["state"] == "empty" else ""
        n = f'{x["n"]:,}' if x["n"] else "—"
        pool_cards += (
            f'<div class="pool{empty}"><div class="pn">{html.escape(x["name"])}</div>'
            f'<div class="pq">{n}</div>'
            f'<div class="pu">{html.escape(x["unit"])}</div>'
            f'<p>{html.escape(x["what"])}</p>'
            f'<div class="pnote">{html.escape(x["note"])}</div></div>')
    pool_cards += "</div>"

    banner = ""
    if run:
        dot = "live" if run["live"] else "idle"
        nm = run.get("now") or ("finished" if not run["live"] else "…")
        when = (f"{run['age']}s ago" if run["age"] < 120
                else f"{run['age'] // 60}m ago")
        banner = (
            f'<div class="live {dot}"><div class="lh">'
            f'<span class="dotm"></span>'
            f'<b>{html.escape(run["label"][:48])}</b>'
            f'<span class="lmeta">{html.escape(run["brand"])}'
            f'{" · " + html.escape(run["route"]) if run["route"] else ""}'
            f'{" · " + html.escape(run["lane"]) if run["lane"] else ""}</span></div>'
            f'<div class="lnow">{"running " + html.escape(nm) if run["live"] else "last run — " + when}</div>'
            f'</div>')

    def strip(stages, state=None):
        out = []
        for s in stages:
            k = {"machine": " m", "human": " h"}.get(s["kind"], "")
            if state:
                got = state.get(s["stage"])
                if got == "done":
                    k += " done"
                elif got == "running":
                    k += " now"
                elif got == "skipped":
                    k += " skip"
            out.append(f'<span class="st{k}" title="{html.escape(s["why"])}">'
                       f'<b>{html.escape(s["stage"])}</b> {html.escape(s["name"])}</span>')
        return f'<div class="stages">{"".join(out)}</div>'

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>The Video Road</title>
<meta http-equiv="refresh" content="15">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Karla:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{CSS}</style></head><body><div class="wrap">

<header class="mast">
<div class="slate">Master view · live from the chain configs · {time.strftime('%b %d, %H:%M')}</div>
<h1>A swipe goes in.<br><em>Finished ads</em> come out.</h1>
<p class="standfirst">Four machines, one continuous road. Each one owns its own chain, and this
page reads all of them rather than restating any — so a stage added anywhere shows up here, and
this view can never drift from what actually runs.</p>
<div class="tally">
<div class="t"><b>{c['runs']}</b><span>teardown runs</span></div>
<div class="t"><b>{c['briefs']}</b><span>briefs written</span></div>
<div class="t"><b>{c['identities']}</b><span>trained identities</span></div>
<div class="t"><b>{c['voices']}</b><span>bound voices</span></div>
<div class="t"><b>{c['formats']}</b><span>format profiles</span></div>
</div>
</header>

{banner}
<section class="road">
<div class="leg">
<div class="legh"><h2>Swipe</h2><span class="pill p-a">3 pools</span></div>
<p class="legsub">Three pools feed the same road, and they are not the same kind of thing. Every
one of them ends the same way: pick something, hit Tear down.</p>
{pool_cards}
</div>
<div class="arrow">↓</div>

<div class="leg">
<div class="legh"><h2>Teardown</h2><span class="pill p-b">{len(tear)} stages</span>
<span class="pill p-b">makes the brief</span></div>
<p class="legsub">Strips someone else's ad to its structure, reads who it speaks to, injects our
brand, runs the hook loop, and writes the brief. Ends with frames.</p>
{strip(tear, run["stages"] if run else None)}
</div>
<div class="arrow">↓</div>

<div class="leg">
<div class="legh"><h2>Production</h2><span class="pill p-c">{len(prod)} stages</span>
<span class="pill p-c">makes the film</span></div>
<p class="legsub">Takes the brief and carries it to a cut-ready scene set: every fact decided
once, identities trained, ledgers checked against each other, one prompt per scene, QC on every
frame. Motion runs last — only on a set that cleared QC.</p>
{strip(prod)}
</div>
<div class="arrow">↓</div>

<div class="leg">
<div class="legh"><h2>Variation</h2><span class="pill p-d">{len(var)} stages</span>
<span class="pill p-d">× every format</span></div>
<p class="legsub">The multiplier. One approved film, restyled into any visual format — screenplay,
blocking and dialogue frozen, only the rendering swapped. The restyle step is mechanical by
design, because a model asked to restyle re-plans the film.</p>
{strip(var)}
</div>
</section>



<section class="note">
<h2 style="font-family:'Instrument Serif',Georgia,serif;font-size:30px;margin-bottom:12px">
Two axes, not one</h2>
<p><b>A variation changes how the film looks.</b> That is the cheap, unlimited axis — the
expensive work of deciding and proving the film is already paid for.</p>
<p><b>Changing the avatar, the problem or the angle changes what the film says.</b> That is a new
production, back through the brief with different inputs. Both scale; conflating them is how a
variation quietly becomes a remake.</p>
</section>

<footer>Solid outline = a written stage · dashed = machine work · gold = a human decision.
Hover any stage for what it is for. Built from
<span class="mono">components/video-teardown/machine/chain_config.json</span> and
<span class="mono">chain_config.json</span>.</footer>
</div></body></html>"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8792)
    a = ap.parse_args()
    OUT.write_text(render())
    print(f"wrote {OUT}")
    if a.serve:
        import functools
        import http.server
        import socketserver

        class H(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                # rebuilt per request, so the page is never a stale snapshot
                body = render().encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

        print(f"the road, live → http://localhost:{a.port}")
        socketserver.TCPServer(("127.0.0.1", a.port), H).serve_forever()
