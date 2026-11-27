"""Maker queue page: every video handed to one maker (default creator), live, with a Send back button that lands.

Reads runs/queue/*/video-ads/4-making/*.json (the queue's own records) and each hand-off's
delivery-state.json, so the page always shows today's state. Pictures and swipe frames are cut
once and cached under runs/maker-queue/. Send back calls delivery_contract.request_revision, the
same door the approval page uses, then re-reads the hand-off and shows the new state on the tile.

Run:   /usr/bin/python3 components/briefs/maker_queue.py [--port 8931] [--who creator]
Runs by: person. Writes only runs/maker-queue/ and, on Send back, the hand-off's revisions/ + delivery-state.json.
"""
import argparse, glob, html, json, os, re, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
RUNS = os.path.join(ROOT, "runs")
CACHE = os.path.join(RUNS, "maker-queue")
EXT = (".png", ".jpg", ".jpeg", ".webp")
SECTIONS = [("back", "Sent back", "bad"), ("need", "Needs you", "warn"), ("prod", "In production", "info"),
            ("rp", "Ready for production", "ok"), ("re", "Ready for editor", "ok")]


def jread(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def folder_of(rec):
    role = "video-editor"
    pk = rec.get("pack") or {}
    if pk.get("folder"):
        return os.path.join(ROOT, pk["folder"])
    b = rec["id"].split("_")[0]
    for r in ("video-editor", "video-producer"):
        p = os.path.join(RUNS, "handoffs", r, b, rec["id"])
        if os.path.isdir(p):
            return p
    return os.path.join(RUNS, "handoffs", role, b, rec["id"])


def items(who):
    out = []
    skip = ("gone", "removed", "not-on-queue", "renamed", "backlog")
    for p in sorted(glob.glob(os.path.join(RUNS, "queue", "*", "video-ads", "*", "*.json"))):
        if os.path.basename(os.path.dirname(p)) in skip:
            continue
        r = jread(p)
        if not r or r.get("stage") not in ("making", "brief-needs-you") or (r.get("who") or "").lower() != who.lower():
            continue
        r["_folder"] = folder_of(r)
        out.append(r)
    return out


def state_of(r):
    ds = jread(os.path.join(r["_folder"], "delivery-state.json"), {}) or {}
    at = r.get("at") or ""
    if ds.get("state") == "back-for-revision" or r.get("flag") == "sent-back":
        return "back", "Sent back" + (" · round %s" % ds["round"] if ds.get("round") else ""), ds
    if at.startswith("Approve"):
        return "need", at, ds
    if "in production" in at:
        return "prod", at, ds
    if at == "Ready for production":
        return "rp", at, ds
    return "re", at or "Ready for editor", ds


def brief_text(folder):
    for n in ("BRIEF.md",):
        p = os.path.join(folder, n)
        if os.path.isfile(p):
            return "\n".join(l for l in open(p, errors="ignore").read().split("\n") if not l.startswith("<!--"))
    return ""


def fld(t, k):
    m = re.search(r"^\*\*" + k + r":?\*\*:?\s*(.+)$", t, re.M)
    return m.group(1).strip() if m else ""


def clip(s, n):
    s = s.replace("`", "")
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def facts(r):
    t = brief_text(r["_folder"])
    idea = re.sub(r"\s*·\s*\*\*.*", "", fld(t, "Idea"))
    ask = re.sub(r"^.*?Ask:\*\*\s*", "", fld(t, "Ask"))
    rows = []
    if idea: rows.append(("The idea", clip(idea, 420)))
    if ask: rows.append(("Ad says", clip(ask, 160)))
    if fld(t, "Style"): rows.append(("Look", clip(fld(t, "Style"), 220)))
    sc = re.findall(r"^\*\*S\d+ ·", t, re.M)
    if sc: rows.append(("Scenes", "%d scenes" % len(sc)))
    if r.get("why"): rows.append(("Queue says", r["why"]))
    rows.append(("Handed off", (r.get("since") or "")[:10]))
    return rows


def pictures(r):
    f, key = r["_folder"], r["id"]
    b = key.split("_")[0]
    tiers = [sorted(glob.glob(os.path.join(RUNS, "video-production", b, key, "media", "S*-F1.*"))),
             sorted(glob.glob(os.path.join(f, "start-pictures", "*"))),
             sorted(glob.glob(os.path.join(f, "returned", "*"))),
             sorted(glob.glob(os.path.join(f, "refs", "*swipe*")) + glob.glob(os.path.join(f, "refs", "cast-*")) + glob.glob(os.path.join(f, "refs", "step-*"))),
             sorted(glob.glob(os.path.join(f, "refs", "*")))]
    for t in tiers:
        t = [x for x in t if x.lower().endswith(EXT) and os.path.getsize(x) > 5000]
        if t:
            k = min(4, len(t))
            idx = list(dict.fromkeys(round(i * (len(t) - 1) / max(k - 1, 1)) for i in range(k)))
            return [t[i] for i in idx]
    return []


def swipe_video(r):
    for p in (os.path.join(r["_folder"], "swipe", "swipe.mp4"), os.path.join(r["_folder"], "refs", "swipe.mp4")):
        if os.path.isfile(p):
            return p
    return None


def swipe_name(r):
    for p in glob.glob(os.path.join(r["_folder"], "*.md")) + glob.glob(os.path.join(r["_folder"], "*.json")):
        m = re.search(r"swipes/([a-z0-9][a-z0-9-]+)", open(p, errors="ignore").read())
        if m:
            return m.group(1)
    return None


def cached(key, tag, make):
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, "%s-%s.jpg" % (key, tag))
    if not os.path.isfile(out):
        make(out)
    return out if os.path.isfile(out) else None


def thumbs_for(r):
    key, urls = r["id"], []
    for j, src in enumerate(pictures(r)):
        o = cached(key, "p%d" % j, lambda out, s=src: subprocess.run(
            ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "60", "--resampleWidth", "300", s, "--out", out], capture_output=True))
        if o: urls.append("/img/" + os.path.basename(o))
    return urls


def swipe_frames(r):
    v = swipe_video(r)
    if not v:
        return [], None
    try:
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout.strip() or 8)
    except Exception:
        d = 8.0
    urls = []
    for j in (1, 2, 3):
        o = cached(r["id"], "s%d" % j, lambda out, t=round(d * j / 4, 1): subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", v, "-frames:v", "1", "-vf", "scale=240:-2", "-q:v", "7", out], capture_output=True))
        if o: urls.append("/img/" + os.path.basename(o))
    return urls, round(d)


def tile(r):
    sec, label, ds = state_of(r)
    key = r["id"]
    brand = "brand_a" if r["brand"] == "brand_a" else r["brand"].title()
    num = key.rsplit("brief-", 1)[-1]
    th = thumbs_for(r)
    rows = "".join('<div class="r"><b>%s</b><span>%s</span></div>' % (html.escape(k), html.escape(v)) for k, v in facts(r))
    if sec == "back":
        req = jread(os.path.join(r["_folder"], ds.get("request", "")), {}) if ds.get("request") else {}
        if req.get("note"):
            rows = '<div class="r"><b>Sent back</b><span>%s</span></div>' % html.escape(clip(req["note"], 500)) + rows
    sw, dur = swipe_frames(r)
    nm = swipe_name(r)
    swhtml = ('<div class="sl">Swipe it came from · %s · %ss</div><div class="strip sws">%s</div>' % (
        html.escape(nm or "name not recorded"), dur, "".join('<img alt="" src="%s">' % u for u in sw))) if sw else '<div class="sl">Swipe it came from · none on file</div>'
    cover = '<img class="cv" alt="" src="%s">' % th[0] if th else '<div class="cv"></div>'
    strip = '<div class="strip">%s</div>' % "".join('<img alt="" src="%s">' % u for u in th) if th else ""
    send = ""
    if sec != "back":
        send = ('<div class="send"><textarea id="n-%s" placeholder="What to fix (optional)"></textarea>'
                '<button onclick="sendBack(\'%s\')">Send back for revision</button><div class="msg" id="m-%s"></div></div>') % (num + r["brand"], key, key)
    else:
        send = '<div class="msg ok">Already sent back. Waiting on the redo.</div>'
    return sec, ('<details class="t s-%s" id="%s"><summary>%s<span class="n">%s</span><span class="bn">%s · Brief %s</span><span class="m">%s</span></summary>'
                 '<div class="body">%s%s%s%s</div></details>') % (sec, html.escape(key), cover, html.escape(r["title"]), brand, num,
                                                                  html.escape(label), strip, rows, swhtml, send)


PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>%(who)s's queue</title><style>
:root{--bg:#f6f6f3;--fg:#1c1d1f;--mut:#6c6f73;--card:#fff;--line:#e2e2dd;--ok:#1f8a4c;--warn:#b7791f;--bad:#c0392b;--info:#2b6cb0}
@media(prefers-color-scheme:dark){:root{--bg:#151618;--fg:#ececea;--mut:#9a9da1;--card:#1f2023;--line:#33353a;--ok:#4cc27f;--warn:#e0a94a;--bad:#ef6f60;--info:#6aa8ee;color-scheme:dark}}
body{background:var(--bg);color:var(--fg);font:15px/1.4 -apple-system,Inter,system-ui,sans-serif;margin:0 auto;max-width:980px;padding:20px max(16px,env(safe-area-inset-right)) 40px max(16px,env(safe-area-inset-left))}
h1{font-size:22px;margin:0}.sub{color:var(--mut);font-size:13px;margin:4px 0 16px}
.top{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:8px}
.big{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}.big b{font-size:28px;display:block;line-height:1}.big span{font-size:12px;color:var(--mut)}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);margin:22px 0 8px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}
.t{background:var(--card);border:1px solid var(--line);border-radius:10px;min-width:0}
.t[open]{grid-column:1/-1}.t summary{list-style:none;cursor:pointer;padding:10px;display:flex;flex-direction:column;gap:6px}.t summary::-webkit-details-marker{display:none}
.t summary:after{content:"Tap to open";font-size:11px;color:var(--info)}.t[open] summary:after{content:"Close"}
.cv{width:100%%;aspect-ratio:9/12;object-fit:cover;border-radius:6px;background:var(--line)}.t[open] .cv{display:none}
.n{font-weight:600;overflow-wrap:anywhere}.bn{font-size:12px;font-weight:700;color:var(--info)}.m{font-size:12px;color:var(--mut)}
.s-back{border-left:4px solid var(--bad)}.s-need{border-left:4px solid var(--warn)}.s-prod{border-left:4px solid var(--info)}.s-rp,.s-re{border-left:4px solid var(--ok)}
.body{padding:10px 12px 12px;display:grid;gap:8px;border-top:1px solid var(--line)}
.r{display:grid;grid-template-columns:90px 1fr;gap:10px;font-size:14px}.r b{color:var(--mut);font-size:12px;text-transform:uppercase}.r span{min-width:0;overflow-wrap:anywhere}
@media(max-width:480px){.r{grid-template-columns:1fr;gap:2px}}
.strip{display:flex;gap:8px;overflow-x:auto}.strip img{height:220px;width:auto;border-radius:6px;flex:none}.sws img{height:170px}
.sl{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em;margin-top:6px;overflow-wrap:anywhere}
.send{display:grid;gap:8px;border-top:1px solid var(--line);padding-top:10px}
textarea{width:100%%;box-sizing:border-box;min-height:64px;border:1px solid var(--line);border-radius:8px;padding:8px;font:inherit;background:var(--bg);color:var(--fg)}
button{background:var(--bad);color:#fff;border:0;border-radius:8px;padding:12px;font:600 15px inherit;cursor:pointer}button:disabled{opacity:.5}
.msg{font-size:14px}.msg.ok{color:var(--ok)}.msg.err{color:var(--bad)}
</style>
<h1>%(who)s's queue</h1><div class=sub>Live from the queue · %(total)d videos · tap one to open it · %(when)s</div>
<div class=top>%(top)s</div>%(body)s
<script>
async function sendBack(key){
  var d=document.getElementById(key), ta=d.querySelector('textarea'), btn=d.querySelector('button'), msg=d.querySelector('.msg');
  btn.disabled=true; msg.className='msg'; msg.textContent='Sending…';
  try{
    var r=await fetch('/sendback',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({key:key,note:ta.value})});
    var j=await r.json();
    if(j.ok){ msg.className='msg ok'; msg.textContent='Sent back · '+j.revision+' · now shows under Sent back. Reloading…'; setTimeout(function(){location.reload()},1500); }
    else { msg.className='msg err'; msg.textContent='Not sent: '+j.error; btn.disabled=false; }
  }catch(e){ msg.className='msg err'; msg.textContent='Not sent: could not reach the page. Nothing changed.'; btn.disabled=false; }
}
</script>"""


def page(who):
    secs = {k: [] for k, _, _ in SECTIONS}
    for r in items(who):
        s, h = tile(r)
        secs[s].append(h)
    top = "".join('<div class=big><b>%d</b><span>%s</span></div>' % (len(secs[k]), l) for k, l, _ in SECTIONS)
    body = "".join('<h2>%s · %d</h2><div class=grid>%s</div>' % (l, len(secs[k]), "".join(secs[k])) for k, l, _ in SECTIONS if secs[k])
    return PAGE % dict(who=html.escape(who), total=sum(len(v) for v in secs.values()), top=top, body=body, when=time.strftime("%b %d %H:%M"))


def send_back(key, note):
    import delivery_contract as DC
    for r in items(ARGS.who):
        if r["id"] == key:
            by = "owner"
            note = (note or "").strip() or "Sent back for revision by owner. See the brief and the delivery checklist, then return the full set."
            try:
                req = DC.request_revision(r["_folder"], note, by, "page:%s:%d" % (key, int(time.time())))
            except Exception as e:
                return {"ok": False, "error": str(e)}
            st = jread(os.path.join(r["_folder"], "delivery-state.json"), {}) or {}
            if st.get("state") != "back-for-revision":
                return {"ok": False, "error": "the hand-off did not record it"}
            return {"ok": True, "revision": req["revision_id"]}
    return {"ok": False, "error": "that video is not in this queue"}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, body, ctype):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header("content-type", ctype); self.send_header("content-length", str(len(b))); self.send_header("cache-control", "no-store"); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            who = parse_qs(u.query).get("who", [ARGS.who])[0]
            return self._send(200, page(who), "text/html; charset=utf-8")
        if u.path.startswith("/img/"):
            p = os.path.join(CACHE, os.path.basename(unquote(u.path)))
            if os.path.isfile(p):
                return self._send(200, open(p, "rb").read(), "image/jpeg")
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path != "/sendback":
            return self._send(404, "not found", "text/plain")
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
            out = send_back(d.get("key", ""), d.get("note", ""))
        except Exception as e:
            out = {"ok": False, "error": str(e)}
        self._send(200, json.dumps(out), "application/json")


ARGS = None
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8931)
    ap.add_argument("--who", default="creator")
    ap.add_argument("--host", default="127.0.0.1")
    ARGS = ap.parse_args()
    print("maker queue for %s on http://%s:%d/" % (ARGS.who, ARGS.host, ARGS.port))
    ThreadingHTTPServer((ARGS.host, ARGS.port), H).serve_forever()
