#!/usr/bin/env python3
"""My Feeds — the one page over every feed.

    python3 desk.py [port]          # default 8820

What it is: type what you want to see → a dig runs → it becomes a standing
feed that the daily run keeps filling. Search runs across every post in every
feed. The page owns no data: it reads records/avatar-feeds/ and
records/desk/, and every button just starts one of the scripts
(dig.py · feed.py · sift.py) in the background.
"""
import collections, html, json, re, subprocess, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import desklib as D

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8820
WS = D.WS
MACHINE = WS / "tools/video-teardown/machine"


def _vt_workdir():
    """video-teardown's working-folder module, loaded by file (SI-56)."""
    m = sys.modules.get("vt_workdir")
    if m is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "vt_workdir", Path(__file__).resolve().parents[2] / "tools" / "video-teardown" / "machine" / "workdir.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["vt_workdir"] = m
        spec.loader.exec_module(m)
    return m

DAILY = D.HERE / "records" / "desk" / "daily.jsonl"


def spawn(*cmd):
    subprocess.Popen([sys.executable, *cmd], cwd=str(D.HERE),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def sounds_worker(job):
    D.job_write(job, kind="sounds", status="running", step="Pulling this week's trending sounds")
    for cmd, say in (("pull", "Tagging mood and energy"), ("tag", "Saving the audio"), ("audio", "Done")):
        r = subprocess.run([sys.executable, "sounds.py", cmd], cwd=str(D.HERE), capture_output=True, text=True)
        line = ((r.stdout or r.stderr).strip().splitlines() or [""])[-1]
        if r.returncode != 0:
            return D.job_write(job, status="failed", step=line[-200:])
        D.job_write(job, step=line)
        D.job_write(job, step=say)
    D.job_write(job, status="done")


def sweep_worker(feed, job):
    D.job_write(job, kind="pull", feed=feed, status="running", step=f"Pulling {feed} now")
    # His saves are not dug — they are projected from the saves catalog. A new
    # sweep of the saved folder needs his own logged-in Chrome, so the button
    # re-reads what the last sweep filed rather than pretending to scrape.
    if json.loads((D.FEEDS / feed / "sources.json").read_text()).get("pull") == "saves":
        r = subprocess.run([sys.executable, "saves_feed.py"], cwd=str(D.HERE),
                           capture_output=True, text=True)
        D.job_write(job, status="done" if r.returncode == 0 else "failed",
                    step=((r.stdout or r.stderr).strip().splitlines() or ["Rebuilt"])[-1][:160])
        return
    ok = True
    for say, cmd in (("Pulling", ["feed.py", "--avatar", feed]),
                     ("Sifting", ["sift.py", "--avatar", feed])):
        r = subprocess.run([sys.executable, *cmd], cwd=str(D.HERE), capture_output=True, text=True)
        D.job_write(job, step=f"{say} → {((r.stdout or r.stderr).strip().splitlines() or [''])[-1][:160]}")
        ok = ok and r.returncode == 0
    D.cache_covers(feed)
    if ok:
        # My Feeds, public (daemn.co/feeds/): re-export after every Pull. The
        # export only reads what this Pull just filed — it never pulls itself.
        spawn("feedsexport.py")
    D.job_write(job, status="done" if ok else "failed", step="Done" if ok else "Stopped")


ROUTES = ("creator", "ai", "founder")


def brief_worker(feed, item, job, route=None):
    """An avatar feed's card — briefs.py carries the avatar and awareness
    declarations, so it stays the path. This only wraps it in a job record, so
    the click is visible on the board and the run is one link away."""
    D.job_write(job, kind="teardown", feed=feed, item=item, status="running",
                step="Teardown running — the full chain to the brief")
    r = subprocess.run([sys.executable, "briefs.py", "--only", feed, "--item", item]
                       + (["--route", route] if route else []),
                       cwd=str(D.HERE), capture_output=True, text=True)
    out = (r.stdout or "").strip().splitlines()
    # briefs.py prints "  <label>: ready|failed" for the run it did
    hit = next((l for l in reversed(out) if re.match(r"^\s+\S+: (ready|failed)$", l)), None)
    label, state = (hit.strip().split(": ") if hit else (None, "failed"))
    D.job_write(job, label=label, status="done" if state == "ready" else "failed",
                step="The brief is ready — open the run" if state == "ready"
                else f"Stopped: {(r.stdout or r.stderr or '')[-200:]}")


def tear_worker(url, author, brand, job, route=None):
    """Same hand-off the feed board uses: download, then the real teardown machine."""
    label = re.sub(r"[^a-z0-9]+", "-", f"feed-{author}-{job[-6:]}".lower()).strip("-")[:40]
    D.job_write(job, kind="teardown", status="running", url=url, brand=brand, label=label,
                step="Downloading the video")
    media = D.HERE / "records" / "desk" / "media" / label
    media.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["yt-dlp", "-o", str(media / "video.%(ext)s"), "--no-playlist", url],
                       capture_output=True, timeout=300)
        vids = list(media.glob("video.*"))
        if not vids:
            raise RuntimeError("the video would not download")
        D.job_write(job, step=f"Teardown machine running — label {label}")
        with (media / "machine.log").open("w") as log:
            r = subprocess.run([sys.executable, str(MACHINE / "run.py"), str(vids[0]),
                                "--brand", brand, "--label", label]
                               + (["--route", route] if route else []),
                               stdout=log, stderr=subprocess.STDOUT, cwd=str(MACHINE), timeout=3 * 3600)
        D.job_write(job, status="done" if r.returncode == 0 else "failed",
                    step="Brief is on the teardowns board" if r.returncode == 0
                    else f"Machine stopped (exit {r.returncode})")
    except Exception as e:
        D.job_write(job, status="failed", step=f"Stopped: {str(e)[:160]}")


_STUDIO = None


def studio_md():
    """The machine's own markdown renderer, so a brief reads here the way it
    reads on the machine's board."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_vt_md", MACHINE / "md.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def studio():
    """Swipe Studio's page builders — the format bank and the rebuild sheet.
    Its board is gone (2026-09-22, his call: everything lives on My Feeds);
    these two pages were the only things it held that this board didn't, so
    app.py stays as a library and this board serves them."""
    global _STUDIO
    if _STUDIO is None:
        import app as _app
        _STUDIO = _app
    return _STUDIO


def run_page(label):
    """One run: what it is, what it made, and the brief — which is the thing he
    opens it for, so the brief is the page and everything else is a line above
    it. The machine's own board (127.0.0.1:8777) holds every run ever."""
    d = _vt_workdir().run_dir(label, WS)
    head = ('<p class="back"><a href="/">&larr; the board</a></p>'
            f'<h1>{html.escape(label)}</h1>')
    if not (d / "run.json").exists():
        return RUN_CSS + head + ('<p class="note">This run has not opened yet — the video '
                                 'is still downloading. Reload in a minute.</p>')
    st = json.loads((d / "run.json").read_text())
    stages = st.get("stages") or {}
    vals = [(v or {}).get("status") for v in stages.values() if isinstance(v, dict)]
    done, total = sum(1 for v in vals if v == "done"), len(vals)
    live = next((k for k, v in stages.items()
                 if isinstance(v, dict) and v.get("status") == "running"), None)
    state = ("running" if live else "failed"
             if any(v in ("failed", "error") for v in vals) else "done")

    aud = st.get("audience") or {}
    facts = [("brand", st.get("brand")), ("creator", st.get("creator")),
             ("avatar", aud.get("_avatar")), ("sub-avatar", aud.get("_sub_avatar")),
             ("framework", (st.get("doctrine") or {}).get("framework")),
             ("came from", {"ALREADY AN AD": "a paid ad", "ORGANIC": "an organic post"}
              .get(st.get("triage_lane"), st.get("triage_lane"))),
             ("route", st.get("production_route")), ("started", (st.get("opened") or "")[:16].replace("T", " "))]
    dl = "".join(f"<div><dt>{html.escape(k)}</dt><dd>{html.escape(str(v))}</dd></div>"
                 for k, v in facts if v)

    # Which model drew the frames — recorded per frame since 2026-09-22; older
    # runs say what the manifest knows, which for them is nothing.
    man = d / "frames" / "frames" / "manifest.json"
    drew = ""
    if man.exists():
        try:
            rows = json.loads(man.read_text())
            names = [r.get("model") for r in rows if r.get("model")]
            made = sum(1 for r in rows if str(r.get("kind", "")).startswith("generated"))
            tally = ", ".join(f"{n}&times;{html.escape(m)}" for m, n in
                              sorted(collections.Counter(names).items(), key=lambda x: -x[1]))
            drew = (f'<p class="drew"><b>{made}</b> frames drawn by {tally}</p>' if tally
                    else f'<p class="drew"><b>{made}</b> frames &mdash; this run predates the '
                         'per-frame record; the default then was Nano Banana Pro '
                         '(<code>gemini-3-pro-image</code>) at 9:16, falling back to '
                         'Nano Banana 2 when Pro was busy.</p>')
        except Exception:
            drew = ""

    stage_rows = "".join(
        f'<li class="{("done" if (v or {}).get("status") == "done" else "run" if (v or {}).get("status") == "running" else "bad")}">'
        f'{html.escape(k)}</li>' for k, v in stages.items() if isinstance(v, dict))

    brief_f = d / "brief-final.md"
    body = ""
    if brief_f.exists():
        try:
            body = studio_md().render(brief_f.read_text())
        except Exception:
            body = f"<pre>{html.escape(brief_f.read_text())}</pre>"
        body = re.sub(r'(<img[^>]+src=")(?!https?:|/)', rf'\1/run/{label}/', body)
        # a frame is a reference beside its scene, not a poster: thumb it, and
        # make it open full size for anyone who wants to look properly
        body = re.sub(r'<img([^>]*?)src="([^"]+)"([^>]*)>',
                      r'<a class="frame" href="\2" target="_blank">'
                      r'<img\1src="\2"\3></a>', body)

    gdoc = st.get("gdoc_url")
    links = " ".join(filter(None, [
        f'<a href="http://127.0.0.1:8777/runs/{label}/source.mp4" target="_blank">the source video</a>',
        f'<a href="http://127.0.0.1:8777/runs/{label}/" target="_blank">every prompt as sent</a>',
        f'<a href="{html.escape(gdoc)}" target="_blank">the brief as a Doc</a>' if gdoc else "",
        '<a href="http://127.0.0.1:8777/board.html" target="_blank">every run</a>']))

    return RUN_CSS + f"""{head}
<div class="state {state}">{"stage " + html.escape(live) + " running" if live
 else "finished" if state == "done" else "stopped"} &middot; {done} of {total} stages
<details><summary>stages</summary><ul class="stages">{stage_rows}</ul></details></div>
<dl class="facts">{dl}</dl>
{drew}
<p class="links">{links}</p>
{f'<article class="brief">{body}</article>' if body
 else '<p class="note">The brief is not written yet — the chain is still running. '
      'Reload to see it.</p>'}
"""


RUN_CSS = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>the run</title><style>
:root{--bg:#09090b;--panel:#111113;--line:#27272a;--ink:#fafafa;--body:#d4d4d8;--mut:#8b8b94;
--blue:#60a5fa;--go:#4ade80;--bad:#f87171;--hot:#fbbf24;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;--mono:ui-monospace,Menlo,monospace}
@media(prefers-color-scheme:light){:root:not([data-theme=dark]){--bg:#fafafa;--panel:#fff;--line:#e4e4e7;
--ink:#09090b;--body:#27272a;--mut:#71717a;--blue:#2563eb;--go:#16a34a;--bad:#dc2626;--hot:#b45309}}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--body);font:16px/1.65 var(--sans);margin:0;
padding:28px 20px 80px;max-width:820px;margin-inline:auto;-webkit-font-smoothing:antialiased}
a{color:var(--blue)}
.back{font-size:13.5px;margin:0 0 14px}
h1{color:var(--ink);font:600 21px/1.25 var(--mono);letter-spacing:-.01em;margin:0 0 12px;word-break:break-word}
.state{font-size:13.5px;color:var(--mut);border:1px solid var(--line);border-radius:8px;
padding:9px 13px;background:var(--panel)}
.state.done{border-left:3px solid var(--go)}.state.running{border-left:3px solid var(--hot)}
.state.failed{border-left:3px solid var(--bad)}
.state summary{cursor:pointer;display:inline;margin-left:8px;color:var(--blue)}
.stages{list-style:none;display:flex;flex-wrap:wrap;gap:5px;padding:10px 0 2px;margin:0}
.stages li{font:11.5px/1 var(--mono);padding:4px 7px;border-radius:5px;background:var(--bg);
border:1px solid var(--line)}
.stages li.done{color:var(--go)}.stages li.run{color:var(--hot)}.stages li.bad{color:var(--bad)}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px 18px;
margin:18px 0;padding:0}
.facts div{display:flex;flex-direction:column;gap:1px}
.facts dt{font:500 10.5px/1 var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--mut)}
.facts dd{margin:0;color:var(--ink);font-size:14.5px}
.drew{font-size:13.5px;color:var(--mut);border-top:1px solid var(--line);padding-top:12px;margin:0}
.drew code{font:12.5px var(--mono)}
.links{font-size:13.5px;display:flex;gap:14px;flex-wrap:wrap;margin:12px 0 0;
border-bottom:1px solid var(--line);padding-bottom:22px}
.note{color:var(--mut);margin-top:22px}
/* the brief — this is what the page is for, so it gets the reading measure */
.brief{margin-top:30px;font-size:16px}
.brief h1{font:600 26px/1.2 var(--sans);letter-spacing:-.02em;margin:0 0 6px}
.brief h2{color:var(--ink);font:600 13px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;
margin:38px 0 10px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.brief h3{color:var(--ink);font:600 17px/1.3 var(--sans);margin:26px 0 6px}
.brief p{margin:0 0 12px;max-width:66ch}
.brief strong{color:var(--ink);font-weight:600}
.brief ul,.brief ol{max-width:66ch;padding-left:20px}
.brief li{margin-bottom:5px}
.brief table{border-collapse:collapse;width:100%;margin:10px 0 18px;font-size:14px;display:block;overflow-x:auto}
.brief th,.brief td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
.brief th{background:var(--panel);color:var(--mut);font:500 11px/1.4 var(--mono);
letter-spacing:.06em;text-transform:uppercase}
.brief pre,pre{white-space:pre-wrap;background:var(--panel);border:1px solid var(--line);
border-radius:8px;padding:13px;font:12.5px/1.55 var(--mono);overflow-x:auto}
/* a frame is a reference next to its scene, not a poster down the page */
a.frame{display:inline-block;width:200px;max-width:100%;margin:6px 8px 16px 0;line-height:0}
a.frame img{width:100%;border-radius:8px;border:1px solid var(--line);display:block}
a.frame:hover img{border-color:var(--blue)}
.brief p:has(> a.frame){max-width:none;display:flex;flex-wrap:wrap;gap:0;margin:2px 0 6px}
</style>"""


def reference_page(code, d):
    """A swipe with no written sheet yet — its video and its six beats."""
    meta = json.loads((d / "meta.json").read_text()) if (d / "meta.json").exists() else {}
    if not (d / "video.mp4").exists():
        return (f"<!doctype html><meta charset=utf-8><title>{code}</title>"
                "<body style='font:15px/1.6 -apple-system;max-width:720px;margin:60px auto;padding:0 20px'>"
                f"<p><a href='/'>← the board</a></p><h1>{code}</h1>"
                "<p>No reference pulled for this one yet — it is an image post, or the "
                "video would not download. Open it on Instagram from the card.</p>")
    stills = "".join(
        f"<img src='/still/{code}/{s.name}' style='width:calc(33.3% - 8px);border-radius:8px'>"
        for s in sorted((d / "strip").glob("*.jpg"))) if (d / "strip").exists() else ""
    secs = meta.get("duration")
    return f"""<!doctype html><meta charset=utf-8><title>{code} — the reference</title>
<body style="font:15px/1.6 -apple-system,sans-serif;background:#09090b;color:#d4d4d8;max-width:980px;margin:0 auto;padding:26px 22px 60px">
<p><a href="/" style="color:#60a5fa">← the board</a></p>
<h1 style="color:#fafafa;font-size:22px;margin:0 0 4px">The reference</h1>
<p style="color:#8b8b94;margin:0 0 18px">{code}{f" · {secs}s" if secs else ""}
{f" · {meta.get('w')}×{meta.get('h')}" if meta.get("w") else ""} —
no written sheet for this swipe yet; this is the footage and its six beats.</p>
<video src="/video/{code}" controls style="width:340px;max-width:100%;border-radius:10px;background:#000"></video>
<div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:18px">{stills}</div>
</body>"""


QUEUE = D.HERE / "records" / "desk" / "briefs"


def briefs():
    out = []
    for f in sorted(QUEUE.glob("*.json")) if QUEUE.exists() else []:
        r = json.loads(f.read_text())
        run = _vt_workdir().run_dir(r["label"], WS)
        if (run / "run.json").exists():
            j = json.loads((run / "run.json").read_text())
            aud, doc = j.get("audience") or {}, j.get("doctrine") or {}
            r["machine"] = {"avatar": aud.get("_avatar"), "sub": aud.get("_sub_avatar"),
                            "funnel": aud.get("_funnel"),
                            "awareness": (j.get("market_state") or {}).get("awareness"), "framework": doc.get("framework"),
                            "triage": j.get("triage_lane"), "gdoc": j.get("gdoc_url"),
                            "stages": {k: v.get("status") for k, v in (j.get("stages") or {}).items()}}
        b = run / "brief-final.md"
        r["brief"] = b.read_text() if b.exists() else None
        out.append(r)
    return sorted(out, key=lambda r: r.get("queued", ""), reverse=True)


def state():
    fs = D.feeds()
    cards = [c for f in fs for c in D.cards(f["id"])]
    used, cap = D.apify_spend()
    daily = [json.loads(l) for l in DAILY.read_text().splitlines()][-7:] if DAILY.exists() else []
    if str(WS / "components" / "brandpath") not in sys.path:
        sys.path.append(str(WS / "components" / "brandpath"))
    import brandpath as BP  # anything under brands/<brand>/ (SI-111 (organic one locator))
    brands = sorted(p.name for p in BP.brands_dir(WS / "brands").iterdir()
                    if p.is_dir() and not p.name.startswith("_"))
    return {"feeds": fs, "cards": cards, "jobs": D.jobs(), "spend": {"used": used, "cap": cap},
            "daily": daily, "brands": brands, "briefs": briefs(),
            "prompts": {**{p.name: p.read_text() for p in sorted(D.PROMPTS.glob("feed-*.md"))},
                        # the teardown machine's audience stage — shown here because the feeds
                        # declare its audience (v9, 2026-09-20)
                        **{p.name: p.read_text() for p in [
                            *sorted((WS / "tools/copywriter/prompts/video/stage-1b-audience").glob("*-v10-*.md")),
                            # the hook stage's unaware entry (v15, 2026-09-20)
                            *sorted((WS / "tools/copywriter/prompts/video/stage-4-loop/4b-hook").glob("*-v15-*.md"))]}}}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json", code=200):
        if not isinstance(body, bytes):
            body = (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if "json" in ctype or "html" in ctype else "max-age=86400")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            return self.send((D.HERE / "desk.html").read_text(), "text/html; charset=utf-8")
        if self.path == "/api/state":
            return self.send(state())
        m = re.match(r"^/api/chain/([A-Za-z0-9_-]+)$", self.path)
        if m and (D.FEEDS / m.group(1) / "sources.json").exists():
            return self.send(D.chain(m.group(1)))
        if self.path == "/api/jobs":
            return self.send({"jobs": D.jobs()})
        m = re.match(r"^/cover/([A-Za-z0-9_-]+)/([A-Za-z0-9_-]+\.jpg)$", self.path)
        if m:
            f = D.FEEDS / m.group(1) / "covers" / m.group(2)
            if f.exists():
                return self.send(f.read_bytes(), "image/jpeg")
        # --- the pages Swipe Studio used to serve (it was retired 2026-09-22;
        # everything lives on this board now). app.py is kept as the library
        # that builds them — the format bank, and the rebuild sheet a maker gets.
        # --- trending sounds (sounds.py, 2026-09-23): this week's TikTok sounds, keep/skip
        if self.path == "/sounds":
            return self.send((D.HERE / "sounds.html").read_text(), "text/html; charset=utf-8")
        if self.path == "/api/sounds":
            import sounds
            used, cap = D.apify_spend()
            return self.send({**sounds.rows_for_page(), "spend": {"used": used, "cap": cap},
                              "cost": sounds.pull_cost(list(sounds.LANES), 30, sounds.tier()),
                              "job": next((j for j in D.jobs() if j.get("kind") == "sounds"), None)})
        m = re.match(r"^/sound-audio/(snd-[0-9A-Za-z_-]+)\.mp3$", self.path)
        if m:
            import sounds
            f = sounds.LOCAL / f"{m.group(1)}.mp3"
            if f.exists():
                return self.send(f.read_bytes(), "audio/mpeg")
        if self.path == "/formats":
            return self.send(studio().formats_page(), "text/html; charset=utf-8")
        m = re.match(r"^/format/([a-z0-9-]+)$", self.path)
        if m:
            return self.send(studio().format_page(m.group(1)), "text/html; charset=utf-8")
        m = re.match(r"^/handoff/([A-Za-z0-9_-]+)$", self.path)
        if m:
            code = m.group(1)
            d = D.HERE / "records/swipe-videos" / code
            if (d / "handoff.md").exists():
                return self.send(studio().handoff_page(code), "text/html; charset=utf-8")
            # No written sheet for this one — show what the swipe actually has:
            # the reference video and the six stills across its runtime. That is
            # the rebuild material; the written sheet is a later pass.
            return self.send(reference_page(code, d), "text/html; charset=utf-8")
        m = re.match(r"^/run/([A-Za-z0-9_.-]+)$", self.path)
        if m:
            return self.send(run_page(m.group(1)), "text/html; charset=utf-8")
        # a run's own files (the brief's frames, its poster), by relative path
        m = re.match(r"^/run/([A-Za-z0-9_.-]+)/([A-Za-z0-9_./-]+)$", self.path)
        if m and ".." not in m.group(2):
            f = _vt_workdir().run_dir(m.group(1), WS) / m.group(2)
            kind = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".mp4": "video/mp4", ".webp": "image/webp"}.get(f.suffix.lower())
            if f.is_file() and kind:
                return self.send(f.read_bytes(), kind)
        m = re.match(r"^/still/([A-Za-z0-9_-]+)/([0-9]+\.jpg)$", self.path)
        if m:
            f = D.HERE / "records/swipe-videos" / m.group(1) / "strip" / m.group(2)
            if f.exists():
                return self.send(f.read_bytes(), "image/jpeg")
        m = re.match(r"^/sheet/([A-Za-z0-9_-]+)$", self.path)
        if m:
            f = D.HERE / "records/swipe-videos" / m.group(1) / "sheet.jpg"
            if f.exists():
                return self.send(f.read_bytes(), "image/jpeg")
        m = re.match(r"^/video/([A-Za-z0-9_-]+)$", self.path)
        if m:
            f = D.HERE / "records/swipe-videos" / m.group(1) / "video.mp4"
            if f.exists():
                return self.send(f.read_bytes(), "video/mp4")
        m = re.match(r"^/covers/([A-Za-z0-9_.-]+)$", self.path)
        if m:
            f = D.HERE / "records/damon-saves/covers" / m.group(1)
            if f.exists():
                return self.send(f.read_bytes(), "image/jpeg")
        self.send({"error": "not found"}, code=404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self.send({"error": "bad request"}, code=400)
        job = time.strftime("%Y%m%d-%H%M%S")
        if self.path == "/api/dig":
            ask = (body.get("ask") or "").strip()
            if len(ask) < 8:
                return self.send({"error": "say a little more about what you want to see"}, code=400)
            D.job_write(f"dig-{job}", kind="dig", ask=ask, status="running", step="Queued")
            spawn("dig.py", ask, "--job", f"dig-{job}")
            return self.send({"job": f"dig-{job}"})
        if self.path == "/api/sounds-pull":
            # on his button only — no schedule (the owner, 2026-09-23). Pull the chart,
            # tag it, save the audio; the page shows the cost before he presses.
            import sounds
            used, cap = D.apify_spend()
            if used is not None and cap - used < 0.5:
                return self.send({"error": f"Apify is at ${used} of its ${cap} monthly limit — raise the limit first"}, code=400)
            threading.Thread(target=sounds_worker, args=(f"sounds-{job}",), daemon=True).start()
            return self.send({"job": f"sounds-{job}"})
        if self.path == "/api/sound-verdict":
            import sounds
            if not sounds.verdict(str(body.get("id") or ""), body.get("pick")):
                return self.send({"error": "no such sound"}, code=400)
            return self.send({"ok": True})
        if self.path == "/api/verdict":
            f = QUEUE / (re.sub(r"[^a-z0-9-]", "", body.get("label") or "") + ".json")
            if not f.exists() or body.get("verdict") not in ("yes", "no", None):
                return self.send({"error": "no such brief"}, code=400)
            r = json.loads(f.read_text())
            r.update(verdict=body.get("verdict"), verdict_at=D.now(), note=(body.get("note") or "")[:500])
            f.write_text(json.dumps(r, indent=1))
            return self.send({"ok": True})
        if self.path == "/api/pull":
            feed = body.get("feed") or ""
            if not (D.FEEDS / feed / "sources.json").exists():
                return self.send({"error": "no such feed"}, code=400)
            threading.Thread(target=sweep_worker, args=(feed, f"pull-{job}"), daemon=True).start()
            return self.send({"job": f"pull-{job}"})
        if self.path == "/api/tear":
            feed, item = body.get("feed") or "", body.get("item") or ""
            # the route he picked on the card; none = teardown only (the route lock)
            route = (body.get("route") or "").strip().lower()
            route = route if route in ROUTES else None
            if not (D.FEEDS / feed / "sources.json").exists() or not item:
                return self.send({"error": "needs a post from a feed"}, code=400)
            if json.loads((D.FEEDS / feed / "sources.json").read_text()).get("core"):
                threading.Thread(target=brief_worker, args=(feed, item, f"tear-{job}", route),
                                 daemon=True).start()
                return self.send({"job": f"tear-{job}"})
            # A feed with no avatar of its own — his saves, the meme scroll. The
            # brand comes from the card instead (Swipe Studio's pick-a-brand flow,
            # brought onto this board 2026-09-22).
            brand = re.sub(r"[^a-z0-9-]", "", (body.get("brand") or "").lower())
            if str(WS / "components" / "brandpath") not in sys.path:
                sys.path.append(str(WS / "components" / "brandpath"))
            import brandpath as BP  # anything under brands/<brand>/ (SI-111 (organic one locator))
            if not brand or not BP.brand_root(brand, root=WS / "brands").is_dir():
                return self.send({"error": "pick a brand for this one"}, code=400)
            card = next((c for c in D.cards(feed) if c["key"] == item), None)
            if not card:
                return self.send({"error": "no such post in that feed"}, code=400)
            threading.Thread(target=tear_worker,
                             args=(card["url"], card["author"], brand, f"tear-{job}", route),
                             daemon=True).start()
            return self.send({"job": f"tear-{job}"})
        self.send({"error": "not found"}, code=404)


if __name__ == "__main__":
    print(f"My Feeds → http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
