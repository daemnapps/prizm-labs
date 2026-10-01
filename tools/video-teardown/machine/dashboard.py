#!/usr/bin/env python3
"""A live view of what the machine is doing right now.

    python3 dashboard.py            serve on 8787 and open it

The board (board.py) renders prompts beside outputs for tuning. This answers a
different question — which creators are briefed, which are running, what is
still waiting — and it has to be true THIS SECOND, so nothing here is baked at
build time. The page polls /state.json every two seconds and redraws; the
server reads the run folders on each request. A published copy of this would
be a photograph of a moving thing, which is what made the artifact version
useless (2026-08-27).
"""
import http.server, json, os, socketserver, sys, threading, webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library as L

PORT = int(os.environ.get("DASH_PORT", "8787"))
SELECTED = "creators/SELECTED-2026-08-27.json"
PICKING = "creators/PICKING.json"
# id prefix per creator handle — kept here so the dashboard can stand alone
def prefixes():
    """Creator id prefixes, read from the picking file rather than a second
    list kept here. The hardcoded copy went stale the moment two creators were
    added: their finished briefs showed as queued (2026-08-29)."""
    try:
        d = json.loads((L.root() / PICKING).read_text())
        return {c["prefix"]: h for h, c in d["creators"].items() if c.get("prefix")}
    except Exception:
        return {}


def runs_now():
    """Every run folder, keyed by the video id in its label."""
    out = {}
    root = HERE / "runs"
    if not root.exists():
        return out
    for d in root.iterdir():
        f = d / "run.json"
        if not f.is_file():
            continue
        try:
            j = json.loads(f.read_text())
        except Exception:
            continue
        lab = (j.get("label") or "").upper()
        vid = None
        for p in prefixes():
            if lab.startswith(p + "-"):
                vid = f"{p}-{lab[len(p)+1:].split('-')[0]}"
        st = j.get("stages") or {}
        order = [k for k in st]
        done = [k for k in order if st[k].get("status") in ("done", "skipped")]
        running = next((st[k].get("name") for k in order
                        if st[k].get("status") == "running"), None)
        out[vid or lab] = {
            "done": len(done), "total": len(st) or 14, "stage": running,
            "doc": j.get("gdoc_url"),
            "brief": (d / "brief-final.md").exists(),
            "at": f.stat().st_mtime,
        }
    return out


def state():
    root = L.root()
    sel = json.loads((root / SELECTED).read_text())
    runs = runs_now()
    creators = []
    tot = ndone = nrun = 0
    for h, c in sel["creators"].items():
        vids = []
        for i in c["videos"]:
            R = runs.get(i["id"]) or {}
            tot += 1
            if R.get("brief") and R.get("done", 0) >= R.get("total", 99):
                s = "done"; ndone += 1
            elif R.get("done"):
                s = "running"; nrun += 1
            else:
                s = "queued"
            vids.append({"id": i["id"], "name": i["name"], "state": s,
                         "done": R.get("done", 0), "total": R.get("total", 14),
                         "stage": R.get("stage"), "doc": R.get("doc"),
                         "post": i.get("post")})
        creators.append({"handle": h, "name": c["creator"],
                         "owes": c["owes"], "videos": vids})
    creators.append({"handle": "katie", "name": "Katie", "owes": 5, "videos": [],
                     "blocked": "handle on the tracker returns nothing"})
    return {"totals": {"selected": tot, "done": ndone, "running": nrun,
                       "queued": tot - ndone - nrun}, "creators": creators}


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>Teardown runs</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--ground:#EDECE9;--panel:#F8F7F5;--panel2:#E3E1DD;--ink:#15181A;--body:#3B4145;
 --muted:#6E767B;--rule:#CFCDC8;--soft:#DFDDD8;--go:#1C6E68;--warn:#9A6B1E;--no:#A03D2C;
 --sans:system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;
 --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media(prefers-color-scheme:dark){:root{--ground:#111417;--panel:#191D20;--panel2:#222829;
 --ink:#ECEAE6;--body:#BEC4C8;--muted:#868D93;--rule:#2A3033;--soft:#232829;
 --go:#4FB5AC;--warn:#D8A44E;--no:#E0705C}}
*{box-sizing:border-box}body{background:var(--ground);color:var(--body);font-family:var(--sans);
 margin:0;padding:0 22px 70px;font-size:16px;line-height:1.55}
.wrap{max-width:1120px;margin:0 auto}
header{padding:34px 0 20px;border-bottom:2px solid var(--ink);display:flex;
 justify-content:space-between;align-items:flex-end;gap:20px;flex-wrap:wrap}
h1{margin:0;font-size:clamp(26px,4vw,40px);letter-spacing:-.02em;color:var(--ink)}
.live{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
 color:var(--go);display:flex;align-items:center;gap:7px}
.dot{width:8px;height:8px;border-radius:50%;background:var(--go);animation:p 1.6s infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.25}}
@media(prefers-reduced-motion:reduce){.dot{animation:none}}
.stats{display:flex;gap:36px;flex-wrap:wrap;padding:22px 0;border-bottom:1px solid var(--rule)}
.stats div{display:flex;flex-direction:column;gap:3px}
.stats .n{font-family:var(--mono);font-size:34px;color:var(--ink);line-height:1;
 font-variant-numeric:tabular-nums}
.stats .l{font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;
 text-transform:uppercase;color:var(--muted)}
.grid{display:grid;gap:1px;background:var(--soft);border:1px solid var(--soft);margin-top:26px;
 grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.card{background:var(--panel);padding:18px}
.card.done{border-left:3px solid var(--go)}
.card.running{border-left:3px solid var(--warn)}
.card.blocked{border-left:3px solid var(--no)}
.chead{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:6px}
.chead h2{margin:0;font-size:17px;color:var(--ink)}
.cnt{font-family:var(--mono);font-size:11px;color:var(--muted);white-space:nowrap}
.pbar{height:6px;background:var(--panel2);margin:10px 0 12px}
.pbar span{display:block;height:100%;background:var(--go);transition:width .4s}
.card.running .pbar span{background:var(--warn)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-family:var(--mono);font-size:10.5px;padding:3px 8px;border:1px solid var(--rule);
 color:var(--muted);text-decoration:none;display:inline-flex;gap:6px;align-items:center;
 background:var(--ground)}
.chip.done{border-color:var(--go);color:var(--go)}
.chip.running{border-color:var(--warn);color:var(--warn)}
a.chip:hover{border-color:var(--ink);color:var(--ink)}
.chip b{font-size:9px;letter-spacing:.06em;text-transform:uppercase}
.stage{margin-top:10px;font-family:var(--mono);font-size:11px;color:var(--warn)}
.blk{margin-top:8px;font-size:14px;color:var(--no)}
.tabs{display:flex;gap:2px;margin-top:20px;border-bottom:1px solid var(--rule);
 align-items:flex-end}
.tabs button,.tabs .tabl{font:inherit;font-size:14.5px;cursor:pointer;background:none;
 border:0;border-bottom:2px solid transparent;color:var(--muted);padding:9px 16px;
 margin-bottom:-1px;text-decoration:none}
.tabs button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--go);font-weight:600}
.tabs button:hover,.tabs .tabl:hover{color:var(--ink)}
.tabs .tabl{margin-left:auto;font-family:var(--mono);font-size:11.5px;
 letter-spacing:.08em;text-transform:uppercase}
.cr{margin-top:40px}
.crh{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;
 flex-wrap:wrap;padding-bottom:12px;border-bottom:1px solid var(--rule)}
.crh h2{margin:0;font-size:23px;color:var(--ink);letter-spacing:-.015em}
.crh .pfx{font-family:var(--mono);font-size:11px;color:var(--muted);
 border:1px solid var(--rule);padding:1px 6px;margin-left:8px;vertical-align:middle}
.crh .why{margin:7px 0 0;font-size:14.5px;max-width:72ch}
.crh .cnt2{font-family:var(--mono);font-size:13px;color:var(--ink);white-space:nowrap}
.pg{display:grid;gap:12px;margin-top:18px;
 grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.pc{background:var(--panel);border:1px solid var(--soft);padding:7px;display:flex;
 flex-direction:column;gap:6px}
.pc.on{border-color:var(--go);border-width:2px;padding:6px}
.pc.off{opacity:.45}.pc.off:hover{opacity:1}
.pc img{width:100%;display:block;background:var(--panel2)}
.pc .sh{position:relative;line-height:0}
.pc .r1{display:flex;justify-content:space-between;align-items:center;gap:6px}
.pc .id{font-family:var(--mono);font-size:10.5px;font-weight:600;color:var(--ink);
 background:var(--panel2);padding:2px 6px;user-select:all}
.pc button{font:inherit;font-family:var(--mono);font-size:10px;letter-spacing:.08em;
 text-transform:uppercase;cursor:pointer;border:1px solid var(--rule);
 background:var(--panel2);color:var(--muted);padding:3px 8px}
.pc.on button{background:var(--go);border-color:var(--go);color:#fff}
.pc h4{margin:0;font-size:13.5px;color:var(--ink);line-height:1.3}
.pc h4 a{color:inherit;text-decoration:none}.pc h4 a:hover{text-decoration:underline}
.pc .v{font-family:var(--mono);font-size:10.5px;color:var(--muted)}
.pc .nt{margin:0;font-size:12px;line-height:1.45}
.deep{margin-top:22px;padding-top:16px;border-top:1px dashed var(--rule)}
.deep h3{margin:0 0 4px;font-size:15px;color:var(--ink)}
</style></head><body><div class="wrap">
<header><h1>The swipe machine</h1>
<div class="live"><span class="dot"></span><span id="tick">connecting…</span></div></header>
<div class="tabs" role="tablist">
  <button role="tab" data-pane="runs" aria-selected="true">Runs</button>
  <button role="tab" data-pane="pick" aria-selected="false">Picking</button>
  <a class="tabl" href="/board" target="_blank" rel="noopener">The work &#8599;</a>
</div>
<div id="pane-runs">
  <div class="stats" id="stats"></div>
  <div class="grid" id="grid"></div>
</div>
<div id="pane-pick" hidden><div id="picking"></div></div>
</div><script>
function esc(s){return (s==null?'':String(s)).replace(/[&<>"]/g,function(c){
 return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function draw(d){
 var t=d.totals;
 document.getElementById('stats').innerHTML=
  [['done','briefs done'],['running','running'],['queued','waiting'],['selected','selected']]
  .map(function(p){return '<div><span class="n">'+t[p[0]]+'</span><span class="l">'+p[1]+'</span></div>';}).join('');
 document.getElementById('grid').innerHTML=d.creators.map(function(c){
  if(c.blocked) return '<div class="card blocked"><div class="chead"><h2>'+esc(c.name)+
    '</h2><span class="cnt">0 of '+c.owes+'</span></div><div class="blk">'+esc(c.blocked)+'</div></div>';
  var nd=c.videos.filter(function(v){return v.state==='done';}).length;
  var nr=c.videos.filter(function(v){return v.state==='running';}).length;
  var cls=nd===c.videos.length?'done':(nr?'running':'');
  var pct=Math.round(100*nd/Math.max(c.videos.length,1));
  var run=c.videos.filter(function(v){return v.state==='running';})[0];
  return '<div class="card '+cls+'"><div class="chead"><h2>'+esc(c.name)+
   '</h2><span class="cnt">'+nd+' of '+c.videos.length+' briefed</span></div>'+
   '<div class="pbar"><span style="width:'+pct+'%"></span></div>'+
   '<div class="chips">'+c.videos.map(function(v){
     var inner=esc(v.id)+(v.state==='running'?' <b>'+v.done+'/'+v.total+'</b>':'')+
               (v.doc?' <b>doc</b>':'');
     return v.doc? '<a class="chip '+v.state+'" href="'+esc(v.doc)+'" target="_blank" title="'+esc(v.name)+'">'+inner+'</a>'
                 : '<span class="chip '+v.state+'" title="'+esc(v.name)+'">'+inner+'</span>';
   }).join('')+'</div>'+
   (run&&run.stage?'<div class="stage">running: '+esc(run.stage)+'</div>':'')+'</div>';
 }).join('');
}
function poll(){
 fetch('/state.json?t='+Date.now()).then(function(r){return r.json();}).then(function(d){
  draw(d);
  document.getElementById('tick').textContent='live · '+new Date().toLocaleTimeString();
 }).catch(function(){ document.getElementById('tick').textContent='server stopped'; });
}
poll(); setInterval(poll, 2000);

// ---- picking -------------------------------------------------------------
var PICK=null;
function card(h,p,sel){
 var on=sel.indexOf(p.rank)>=0;
 return '<div class="pc '+(on?'on':'off')+'" data-h="'+h+'" data-id="'+esc(p.id)+
  '" data-rank="'+esc(p.rank)+'">'+
  '<a class="sh" href="'+esc(p.post)+'" target="_blank" rel="noopener">'+
   '<img loading="lazy" src="'+esc(p.thumb)+'" alt=""></a>'+
  '<div class="r1"><span class="id">'+esc(p.id)+'</span>'+
   '<button type="button">'+(on?'✓ picked':'pick')+'</button></div>'+
  (p.name?'<h4><a href="'+esc(p.post)+'" target="_blank" rel="noopener">'+esc(p.name)+'</a></h4>':'')+
  '<div class="v">'+Number(p.views).toLocaleString()+' views</div>'+
  (p.note?'<p class="nt">'+esc(p.note)+'</p>':'')+'</div>';
}
function drawPick(){
 if(!PICK) return;
 var hs=Object.keys(PICK.creators).sort(function(a,b){
   var mx=function(k){return Math.max.apply(null,PICK.creators[k].posts.map(function(p){return p.views||0;}));};
   return mx(b)-mx(a);});
 document.getElementById('picking').innerHTML=hs.map(function(h){
  var c=PICK.creators[h], sel=c.selected||[];
  var n=sel.length;
  return '<div class="cr" id="c-'+h+'"><div class="crh"><div>'+
   '<h2>'+esc(c.name)+'<span class="pfx">'+esc(c.prefix)+'</span></h2>'+
   (c.why?'<p class="why">'+esc(c.why)+'</p>':'')+'</div>'+
   '<div class="cnt2">'+n+' / '+c.owes+' picked</div></div>'+
   '<div class="pg">'+c.posts.map(function(p){return card(h,p,sel);}).join('')+'</div>'+
   (c.deeper.length?'<div class="deep"><h3>Deeper in her page</h3><div class="pg">'+
     c.deeper.map(function(p){return card(h,p,sel);}).join('')+'</div></div>':'')+
   '</div>';
 }).join('');
}
fetch('/picking.json').then(function(r){return r.json();}).then(function(d){PICK=d;drawPick();});

document.addEventListener('click',function(e){
 var b=e.target.closest('.pc button'); if(!b) return;
 var c=b.closest('.pc'), h=c.dataset.h, id=c.dataset.id, rank=c.dataset.rank;
 var on=!c.classList.contains('on');
 fetch('/select',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({handle:h,id:id,on:on})})
  .then(function(r){return r.json();})
  .then(function(res){ PICK.creators[h].selected=res.selected; drawPick(); });
});

var tabs=[].slice.call(document.querySelectorAll('.tabs button'));
tabs.forEach(function(t){ t.addEventListener('click',function(){
  tabs.forEach(function(x){x.setAttribute('aria-selected', x===t?'true':'false');});
  document.getElementById('pane-runs').hidden = t.dataset.pane!=='runs';
  document.getElementById('pane-pick').hidden = t.dataset.pane!=='pick';
});});
</script></body></html>"""


def thumb_path(handle, rank):
    """A still, off the Drive. `rank` is either a post folder number or an
    N-id from the deeper pass."""
    root = L.root() / "creators" / handle
    if str(rank).upper().startswith("N"):
        f = root / "deeper" / f"{str(rank).upper()}.jpg"
        return f if f.is_file() else None
    for d in (root / "posts").glob(f"{rank}-*"):
        f = d / "thumbnail.jpg"
        if f.is_file():
            return f
    return None


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        """Selection is saved to the Drive, not to one browser. A pick made
        here is the same pick anyone else sees."""
        if not self.path.startswith("/select"):
            self.send_error(404); return
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            self.send_error(400); return
        f = L.root() / PICKING
        d = json.loads(f.read_text())
        h, vid, on = body.get("handle"), body.get("id"), bool(body.get("on"))
        c = d["creators"].get(h)
        if not c:
            self.send_error(404); return
        sid = vid.split("-", 1)[1] if "-" in vid else vid
        cur = set(c["selected"])
        cur.add(sid) if on else cur.discard(sid)
        c["selected"] = sorted(cur)
        f.write_text(json.dumps(d, indent=2))
        out = json.dumps({"ok": True, "selected": c["selected"]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers(); self.wfile.write(out)

    def do_GET(self):
        if self.path.startswith("/thumb/"):
            parts = self.path.split("?")[0].strip("/").split("/")
            f = thumb_path(parts[1], parts[2]) if len(parts) >= 3 else None
            if not f:
                self.send_error(404); return
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "max-age=3600")
            self.end_headers(); self.wfile.write(data); return

        if self.path.startswith("/board"):
            # the machine's own stage-by-stage view: every prompt beside the
            # output it produced. Built by board.py; served here so the whole
            # thing is one place.
            f = HERE / "board.html"
            if not f.is_file():
                self.send_error(404, "run board.py first"); return
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(data); return

        if self.path.startswith("/state.json"):
            body = json.dumps(state()).encode()
            ctype = "application/json"
        elif self.path.startswith("/picking.json"):
            body = (L.root() / PICKING).read_bytes()
            ctype = "application/json"
        else:
            body = PAGE.encode()
            ctype = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), H) as srv:
        url = f"http://127.0.0.1:{PORT}/"
        print(f"live at {url}  (ctrl-c to stop)", flush=True)
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
        srv.serve_forever()
