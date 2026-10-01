#!/usr/bin/env python3
"""The briefs tool — localhost, no build step, writes as you work.

    serve.py [--port 8792]

    GET  /                 every brief, and how to start a run
    GET  /b/<id>           one brief, with its decisions open for answering
    GET  /state.json       the register as it stands right now
    POST /api/answer       {id, key, answer}   record a decision
    POST /api/clear        {id, key}           un-answer one
    POST /api/status       {id, status}        move it along the track

Damon, 2026-09-13: *"make this an actual local tool, like a local page tool
with logic that's hooked up, so that way we can actually interact with it."*

The static pages were a photograph of the register. This is the register.
Answering a decision here writes it into `briefs.json` immediately — there is
no save button and no build step, because a review surface you have to
remember to rebuild is one that is quietly out of date every time you open it.

**The gate lives here on purpose.** Nothing turns a brief into a production
spec on its own. A brief leaves `for review` only when a person moves it, and
it cannot be moved while a decision that belongs to Damon is still open.
"""
import argparse, json, re, sys
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "tools"))
import briefs as B
import brief_page as BP

BP.LINK = "/b/"

TRACK = ["for-review", "approved", "in-production", "shipped"]


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def open_decisions(rec, dec):
    """The ones still waiting on Damon, after what he has already answered."""
    answered = rec.get("decisions", {})
    return [d for d in dec
            if "damon" in d["who"].lower() and not d["settled"]
            and not answered.get(slugify(d["what"]), {}).get("answer")]


def panel(bid, rec):
    """The interactive half: the track, and every decision with a box."""
    run = HERE / "runs" / rec["run"]
    brief = (run / "out/06-brief.md").read_text()
    dec = BP.decisions(brief)
    answered = rec.get("decisions", {})
    waiting = open_decisions(rec, dec)

    rows = []
    for d in dec:
        key = slugify(d["what"])
        a = answered.get(key, {})
        mine = "damon" in d["who"].lower() and not d["settled"]
        state = ("settled in the brief" if d["settled"]
                 else f'answered {a["at"][:10]}' if a.get("answer")
                 else "open")
        box = ""
        if mine or a.get("answer"):
            val = BP.H.escape(a.get("answer", ""))
            box = (f'<div class="ans"><input id="i-{key}" value="{val}" '
                   f'placeholder="your call — it is written down as you typed it">'
                   f'<button onclick="answer(\'{key}\')">Save</button>'
                   + (f'<button class="ghost" onclick="clr(\'{key}\')">Clear</button>'
                      if a.get("answer") else "") + '</div>')
        rows.append(
            f'<tr class="{"mine" if mine else ""}"><td>{BP.H.escape(d["what"])}{box}</td>'
            f'<td>{BP.H.escape(d["who"])}</td><td>{state}</td></tr>')

    i = TRACK.index(rec["status"]) if rec["status"] in TRACK else 0
    steps = "".join(
        f'<button class="step {"on" if n == i else ""}" '
        f'onclick="setStatus(\'{s}\')"{" disabled" if n and waiting else ""}>'
        f'{s.replace("-", " ")}</button>'
        for n, s in enumerate(TRACK))
    miss = BP.readiness(bid, rec)
    note = ('<p class="hint ok">Ready for the designer. Anything the brief could '
            'not settle is listed below with how it was resolved — none of it '
            'blocks the work.</p>' if not miss else
            f'<p class="hint">Not ready: waiting on {BP.H.escape(", ".join(miss))}.</p>')

    return (f'<h2>Notes, and your overrides</h2><div class="body">'
            f'<div class="track">{steps}</div>{note}'
            f'<div class="scroll"><table><thead><tr><th>Decision</th>'
            f'<th>Who decides</th><th>State</th></tr></thead><tbody>'
            + "".join(rows) + '</tbody></table></div></div>'
            + SCRIPT.replace("__ID__", bid))


SCRIPT = """
<script>
const ID = "__ID__";
async function post(path, body){
  const r = await fetch(path, {method:"POST", headers:{"content-type":"application/json"},
                              body: JSON.stringify(body)});
  if(!r.ok){ alert(await r.text()); return; }
  location.reload();
}
const answer = k => post("/api/answer",
  {id: ID, key: k, answer: document.getElementById("i-"+k).value});
const clr = k => post("/api/clear", {id: ID, key: k});
const setStatus = s => post("/api/status", {id: ID, status: s});
</script>
"""

EXTRA_CSS = """
.track{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
.step{font:600 11px var(--mono);letter-spacing:.08em;text-transform:uppercase;
  padding:8px 14px;border-radius:999px;border:1px solid var(--line);background:var(--ground);
  color:var(--ink-2);cursor:pointer}
.step.on{background:var(--ink);color:var(--ground);border-color:var(--ink)}
.step:disabled{opacity:.35;cursor:not-allowed}
.hint{font-size:13.5px;color:var(--flag);margin:0 0 14px;font-weight:600}
.hint.ok{color:var(--ok)}
tr.mine td:first-child{color:var(--ink)}
.ans{display:flex;gap:7px;margin-top:9px}
.ans input{flex:1;min-width:0;font:400 13px var(--sans);padding:8px 11px;border-radius:7px;
  border:1px solid var(--line);background:var(--ground);color:var(--ink)}
.ans button{font:600 11px var(--mono);letter-spacing:.06em;padding:8px 13px;border-radius:7px;
  border:0;background:var(--ink);color:var(--ground);cursor:pointer}
.ans button.ghost{background:var(--ground);color:var(--ink-3);border:1px solid var(--line)}
"""


def fresh():
    """Pick up edits to the renderer without a restart.

    This file says "no build step", and it was not true: Python imports a
    module once, so the server went on serving the renderer as it was when it
    started. New drafts were filed, the page was reloaded, and nothing
    changed — because the running process still had the old code (2026-09-14).
    """
    import importlib
    importlib.reload(BP)
    BP.LINK = "/b/"
    BP.LINK2 = "/brand/"


def where():
    """Where every piece of a brief lives, and why two brands cannot collide.

    Damon, 2026-09-14, before standing up a second brand: *"I need to make
    sure both brands have clear respective briefs, drafts, and generation
    pipelines that do not conflict with each other."*
    """
    import json as _j
    reg = B.load()
    brands = sorted({r["brand"] for r in reg["briefs"].values() if r.get("run")})
    rows = []
    for br in brands:
        ids = sorted(b for b, r in reg["briefs"].items()
                     if r.get("run") and r["brand"] == br)
        runs = sorted((HERE / "runs").glob(f"{br}-*"))
        d = HERE / "drafts" / br
        vs = sorted((x.name for x in d.glob("v*") if x.is_dir()), reverse=True)
        pics = len(list((d / vs[0]).glob("*.png"))) if vs else 0
        drive = next((r["drive"]["folder"] for r in reg["briefs"].values()
                      if r.get("brand") == br and r.get("drive")), None)
        rows.append((br, ids, runs, vs, pics, drive,
                     (d / "baseline.json").is_file()))

    def esc(x): return BP.H.escape(str(x))
    cards = ""
    for br, ids, runs, vs, pics, drive, has_base in rows:
        cards += (
            f'<div class="card"><h4>{esc(br)}</h4>'
            f'<table><tbody>'
            f'<tr><td>briefs</td><td>{", ".join(ids) or "&mdash;"}</td></tr>'
            f'<tr><td>run folders</td><td><code>runs/{esc(br)}-&lt;swipe&gt;-&lt;block&gt;/</code>'
            f' &middot; {len(runs)}</td></tr>'
            f'<tr><td>baseline</td><td><code>drafts/{esc(br)}/baseline.json</code>'
            f' &middot; {"set" if has_base else "not set"}</td></tr>'
            f'<tr><td>pictures</td><td><code>drafts/{esc(br)}/{esc(vs[0]) if vs else "v1"}/</code>'
            f' &middot; {pics} &middot; not in git</td></tr>'
            f'<tr><td>on Drive</td><td>'
            + (f'<a href="{drive}" target="_blank" rel="noopener">'
               f'image-teardown/{esc(br)}/&lt;brief&gt;/</a>' if drive else "not delivered yet")
            + '</td></tr></tbody></table></div>')

    return ('<meta charset="utf-8"><title>Where things live</title>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Archivo:wght@400;600;800&family=Newsreader:opsz,wght@6..72,400&'
        'family=JetBrains+Mono:wght@400;600&display=swap">'
        f'<style>{BP.CSS}{EXTRA_CSS}'
        '.card table{width:100%;font-size:13.5px}'
        '.card td{padding:7px 10px 7px 0;border-bottom:1px solid var(--line);vertical-align:top}'
        '.card td:first-child{width:112px;color:var(--ink-3);font:600 10.5px var(--mono);'
        'letter-spacing:.08em;text-transform:uppercase;padding-top:10px}'
        '.card h4{font:800 17px var(--sans);margin:0 0 10px;letter-spacing:-.01em;color:var(--ink)}'
        '.four{display:grid;gap:14px;grid-template-columns:1fr}'
        '@media(min-width:760px){.four{grid-template-columns:1fr 1fr}}'
        '</style>'
        '<div class="wrap"><p class="id"><a href="/">&larr; all briefs</a></p>'
        '<header><h1>Where things live</h1>'
        '<p class="lede">The static ad machine keeps one brief in four places. '
        'Every one of them is keyed by brand, so two brands never touch.</p></header>'

        '<h2>The four places</h2><div class="body">'
        '<div class="scroll"><table><thead><tr><th>Place</th><th>What it holds</th>'
        '<th>Keyed by</th></tr></thead><tbody>'
        '<tr><td>image-teardown</td><td>the swipe it came from, all six stages, the brief, '
        'the register, the slot files and the draft pictures</td>'
        '<td>brand, in the run folder name and in <code>drafts/&lt;brand&gt;/</code></td></tr>'
        '<tr><td>image-production</td><td>the batch spec, the plates, the judge&rsquo;s verdicts, '
        'the finished ads and the report</td>'
        '<td>brand, in <code>runs/&lt;brand&gt;/&lt;batch&gt;/</code></td></tr>'
        '<tr><td>Google Drive</td><td>the source ad, the draft and the brief, per brief &mdash; '
        'the only copy that is not on this laptop</td>'
        '<td>brand, in <code>image-teardown/&lt;brand&gt;/&lt;brief id&gt;/</code></td></tr>'
        '<tr><td>brands/&lt;brand&gt;</td><td>the things the chain reads and never writes: '
        'avatars, roster, products, offers, palette, angle bank</td>'
        '<td>the folder is the brand</td></tr>'
        '</tbody></table></div></div>'

        '<h2>What each brand actually has right now</h2>'
        f'<div class="four">{cards}</div>'

        '<h2>Why they cannot collide</h2><div class="body">'
        '<ul class="rules">'
        '<li><b>Brief ids come out of separate blocks.</b> One brand starts at p001, the next '
        'at p140, and a new brand is given the next free hundred on its first brief. Two brands '
        'can never be handed the same id.</li>'
        '<li><b>Run folders lead with the brand.</b> They used to be named after the swipe alone, '
        'so two brands tearing down the same competitor ad wrote to the same folder and the '
        'second overwrote the first. Found on 2026-09-14 when a test brand ate a finished run; '
        'the six existing runs were renamed to match.</li>'
        '<li><b>Baselines are per brand.</b> One cast and one product each, pinned. Changing '
        'one brand&rsquo;s man cannot touch another&rsquo;s.</li>'
        '<li><b>Drive folders are per brand, then per brief.</b> Re-delivering updates the same '
        'file rather than making a new one, so a link you have handed out keeps working.</li>'
        '<li><b>The brand folder is read-only to the chain.</b> It takes avatars, roster, '
        'products, offers and angles out; the only thing it ever writes back is a proposed '
        'angle, and that lands at status <code>proposed</code> for you to sign.</li>'
        '</ul></div>'

        '<h2>The one word that joins it all</h2><div class="body">'
        '<p>The brief id. <code>p005</code> is the folder on Drive, the row in the register, '
        'and the <code>brief</code> field inside every Meta ad name the batch produces &mdash; '
        'so spend in a report leads back to the brief that made it, and the competitor ad that '
        'started it.</p></div>'
        '<footer>Static ad machine &middot; image-teardown + image-production &middot; '
        'this page is generated from the register, so it cannot drift from the truth</footer>'
        '</div>')


def swipe_page(name, picks=None):
    """Every post in a swipe library, grouped by creator, hottest first.

    Damon, 2026-09-14: *"pull up the top posts by each creator so we can
    select the ones we want to swipe."* Data only — engagement, type, date,
    the caption as posted. No subject filter and no recommendation: a post
    about something other than the product is still a format, and for an
    unaware audience it is often the format that works.
    """
    import base64, io, json as _j
    sys.path.insert(0, str(HERE / "tools"))
    import paths as _P
    idx = None
    for root in (_P.SWIPE_ORGANIC, _P.SWIPE):
        f = root / name / "posts.json"
        g = root / name / "blocks.json"
        if f.is_file():
            idx = _j.loads(f.read_text()); break
    if not idx:
        return f"<p>no swipe library called {BP.H.escape(name)}</p>"

    # Never the Drive mount. Reading it from inside the server deadlocked the
    # whole process — Errno 11, Resource deadlock avoided — and took the
    # briefs tool down with it (2026-09-14). A local cache, built once by
    # tools/cache_swipe.py, is what this page reads.
    cache = HERE / ".swipe-cache" / name
    def thumb(slug, fname):
        q = cache / f"{slug}.jpg"
        if not q.is_file():
            return ""
        try:
            return "data:image/jpeg;base64," + base64.b64encode(q.read_bytes()).decode()
        except OSError:
            return ""

    chosen = None
    if picks:
        chosen = {int(x) for x in re.findall(r"\d+", picks)}
    posts_all = [p for p in idx["posts"]
                 if not chosen or p["rank"] in chosen]
    by = {}
    for p in posts_all:
        by.setdefault(p["creator"], []).append(p)
    order = sorted(by, key=lambda c: -max(x["engagement"] for x in by[c]))

    caps, comments = {}, {}
    for f in sorted((_P.SWIPE_ORGANIC / name / "posts").glob("*.md")):
        tx = f.read_text()
        m = re.search(r"## Caption \(verbatim, as posted\)\n\n((?:> .*\n?)+)", tx)
        caps[f.stem] = re.sub(r"^> ?", "", m.group(1).strip(), flags=re.M) if m else ""
        comments[f.stem] = [
            (u, int(lk), (tx_ or "").strip()) for u, lk, tx_ in
            re.findall(r"^- \*\*@([^*]+)\*\* · (\d+) likes[^\n]*\n\s{2}(.+)$", tx, re.M)]

    blocks = ""
    for c in order:
        posts = sorted(by[c], key=lambda x: -x["engagement"])
        cards = ""
        for p in posts:
            src = thumb(p["slug"], p["file"])
            img = (f'<img src="{src}" alt="">' if src else
                   '<div class="noimg">no still on Drive</div>')
            raw = caps.get(p["slug"], "") or ""
            cap = BP.H.escape(raw if chosen else raw[:180])
            body = ""
            if chosen:
                cm = comments.get(p["slug"], [])
                rows = "".join(
                    f'<li><b>@{BP.H.escape(u)}</b> <span>{lk}</span>'
                    f'<p>{BP.H.escape(tx)}</p></li>' for u, lk, tx in cm)
                body = (f'<details class="cm"><summary>{len(cm)} comments</summary>'
                        f'<ol>{rows}</ol></details>') if cm else ""
            cards += (
                f'<figure class="sw"><a href="{p.get("drive") or p.get("url")}" '
                f'target="_blank" rel="noopener">{img}</a><figcaption>'
                f'<p class="eng">{p["engagement"]:,}</p>'
                f'<p class="det">{p["likes"]:,} likes &middot; {p["comments"]:,} comments'
                f'<br>{p.get("posted","")} &middot; rank {p["rank"]} of {idx["count"]}</p>'
                f'<p class="cap">{cap}</p>'
                f'<p class="det"><code>{p["slug"]}</code></p>'
                + body + '</figcaption></figure>')
        tot = sum(x["engagement"] for x in posts)
        blocks += (f'<h3 class="cr">{BP.H.escape(c)} '
                   f'<span>{len(posts)} post{"s" if len(posts)!=1 else ""} &middot; '
                   f'{tot:,} total engagement</span></h3>'
                   f'<div class="grid">{cards}</div>')

    return ('<meta charset="utf-8"><title>' + BP.H.escape(name) + ' swipe</title>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Archivo:wght@400;600;800&family=Newsreader:opsz,wght@6..72,400&'
        'family=JetBrains+Mono:wght@400;600&display=swap">'
        f'<style>{BP.CSS}{EXTRA_CSS}'
        '.cr{font:800 19px var(--sans);margin:36px 0 12px;letter-spacing:-.01em;'
        'border-top:2px solid var(--ink);padding-top:12px}'
        '.cr span{font:400 11px var(--mono);color:var(--ink-3);letter-spacing:.06em;'
        'text-transform:uppercase;margin-left:8px}'
        '.sw{margin:0;background:var(--card);border:1px solid var(--line);'
        'border-radius:10px;overflow:hidden}'
        '.sw img{width:100%;display:block}'
        '.noimg{padding:40px 12px;text-align:center;font:400 11px var(--mono);'
        'color:var(--ink-3);background:var(--ground)}'
        '.sw figcaption{padding:11px 13px}'
        '.eng{margin:0;font:800 20px var(--sans);letter-spacing:-.02em}'
        '.det{margin:3px 0 0;font:400 11px var(--mono);color:var(--ink-3);line-height:1.6}'
        '.cap{margin:8px 0 0;font-size:12.5px;color:var(--ink-2);line-height:1.5;white-space:pre-wrap}'
'.cm{margin:10px 0 0;padding:0 12px;background:var(--ground);border:1px solid var(--line);border-radius:8px}'
'.cm summary{padding:9px 0;font:600 11px var(--mono);letter-spacing:.06em;color:var(--ink-3);cursor:pointer;list-style:none}'
'.cm ol{margin:0;padding:0 0 10px 0;list-style:none;max-height:420px;overflow-y:auto}'
'.cm li{padding:8px 0;border-top:1px solid var(--line)}'
'.cm li b{font:600 11.5px var(--mono)} .cm li span{float:right;font:400 10.5px var(--mono);color:var(--ink-3)}'
'.cm li p{margin:3px 0 0;font-size:12.5px;color:var(--ink-2);line-height:1.45}'
        '</style>'
        '<div class="wrap"><p class="id"><a href="/">&larr; all briefs</a></p>'
        f'<header><h1>{BP.H.escape(name)} &mdash; the feed</h1>'
        f'<p class="lede">{idx["count"]} posts from '
        f'{len(order)} creators, ranked by engagement within each. '
        f'{BP.H.escape(idx.get("note",""))}</p></header>'
        + blocks +
        '<footer>swipe-organic/' + BP.H.escape(name) + '/posts/ &middot; '
        'stills on Drive at the mirrored path &middot; '
        'pulled ' + BP.H.escape(idx.get("pulled","")) + '</footer></div>')


class App(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, code=200, ctype="text/html; charset=utf-8"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(b)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        fresh()
        reg = B.load()
        path = self.path.split("?")[0]
        if path == "/":
            return self.send(BP.brands(reg).replace("</style>", EXTRA_CSS + "</style>"))
        if path.startswith("/brand/"):
            br = path[len("/brand/"):]
            html = BP.index(reg, br).replace("</style>", EXTRA_CSS + "</style>")
            return self.send(html.replace('href="index.html"', 'href="/"'))
        if path == "/state.json":
            return self.send(json.dumps(reg, indent=1),
                             ctype="application/json; charset=utf-8")
        if path.startswith("/swipe/"):
            rest = path[len("/swipe/"):]
            if "/" in rest:
                nm, _, picks = rest.partition("/")
                return self.send(swipe_page(nm, picks))
            return self.send(swipe_page(rest))
        if path == "/where":
            return self.send(where())
        if path.startswith("/b/"):
            bid = path[3:]
            rec = reg["briefs"].get(bid)
            if not rec or not rec.get("run"):
                return self.send(f"no brief {bid}", 404, "text/plain; charset=utf-8")
            html = BP.render(bid, rec, reg, extra=panel(bid, rec))
            html = html.replace("</style>", EXTRA_CSS + "</style>")
            html = html.replace('<div class="wrap">',
                                '<div class="wrap"><p class="id">'
                                '<a href="/">&larr; all briefs</a></p>', 1)
            return self.send(html)
        return self.send("not here", 404, "text/plain; charset=utf-8")

    def do_POST(self):
        n = int(self.headers.get("content-length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self.send("bad json", 400, "text/plain; charset=utf-8")
        reg = B.load()
        rec = reg["briefs"].get(body.get("id"))
        if not rec:
            return self.send("no such brief", 404, "text/plain; charset=utf-8")

        if self.path == "/api/answer":
            key, ans = body.get("key"), (body.get("answer") or "").strip()
            if not key:
                return self.send("no key", 400, "text/plain; charset=utf-8")
            rec.setdefault("decisions", {})
            if ans:
                rec["decisions"][key] = {"answer": ans,
                                         "at": datetime.now().isoformat(timespec="seconds")}
            else:
                rec["decisions"].pop(key, None)
            # An answered angle is a signed angle — the one decision that
            # changes what the ad can be named.
            # The key is a slug of the decision's own title, so it reads
            # "unsigned-angle" as often as "angle" — match the word anywhere.
            if re.search(r"\bangle\b", key) and ans:
                rec.setdefault("declares", {})["angle"] = slugify(ans).replace("-", "")

        elif self.path == "/api/clear":
            key = body.get("key")
            rec.get("decisions", {}).pop(key, None)
            # Un-answering the angle has to un-sign it. Left alone, clearing
            # the decision removed the record of who signed while the signed
            # angle stayed in `declares` — and the ad name would then carry an
            # angle nobody had approved.
            if key and re.search(r"\bangle\b", key):
                _, _, declared = B.read_run(HERE / "runs" / rec["run"])
                rec.setdefault("declares", {})["angle"] = declared.get("angle", "unsigned")

        elif self.path == "/api/status":
            s = body.get("status")
            if s not in TRACK:
                return self.send(f"status must be one of {TRACK}", 400,
                                 "text/plain; charset=utf-8")
            # No gate. Damon, 2026-09-14: "the system needs to run without
            # me." A brief that stops until someone answers a question is a
            # brief that does not ship, and the questions this chain raised
            # were answerable from the repo every time.
            rec["status"] = s
        else:
            return self.send("not here", 404, "text/plain; charset=utf-8")

        B.save(reg)
        return self.send("ok", 200, "text/plain; charset=utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8792)
    o = ap.parse_args()
    print(f"briefs  ->  http://127.0.0.1:{o.port}")
    ThreadingHTTPServer(("127.0.0.1", o.port), App).serve_forever()
