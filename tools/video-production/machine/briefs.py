#!/usr/bin/env python3
"""Every brief, and how far each one has got. The view across runs.

    briefs.py [port]          default 8458

The cinema board and the storyboard each show ONE ad. Nothing showed the shelf:
which briefs exist, which are half-built, which are waiting on a person. Damon,
2026-09-14: "I need some sort of visual to let me know where things are at per
generation of briefs."

Reads the runs folder live on every request and holds no state of its own. A
stage is DONE because its files are on disk, never because something said so —
a board that lies about its own state is worse than no board.

Brand-agnostic: no brand, person or product is named here. The run's name
carries all of it, and the name is parsed with components/naming.
"""
from __future__ import annotations
import json, os, re, subprocess, sys, tempfile, time
from datetime import datetime
from html import escape as e
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"
WS = Path(os.environ.get("AI_WORKSPACE", Path.home() / "Projects/ai-workspace"))
sys.path.insert(0, str(WS / "components" / "naming"))
try:
    import names as NAMES
except Exception:
    NAMES = None

STAGES = ["brief", "plan", "frames", "clips", "voice", "cut"]
CINEMA_PORT = 8459          # one address, always the run last opened
_cinema = {"run": None, "proc": None}
_thumbs: dict = {}


def thumb(f: Path, h: int = 184) -> bytes:
    """A 92pt-tall strip has no business shipping a 6MB master."""
    k = (str(f), f.stat().st_mtime_ns)
    if k in _thumbs:
        return _thumbs[k]
    out = Path(tempfile.gettempdir()) / f"briefs-{abs(hash(k))}.jpg"
    subprocess.run(["sips", "-Z", str(h), "-s", "format", "jpeg",
                    "-s", "formatOptions", "70", str(f), "--out", str(out)],
                   capture_output=True)
    b = out.read_bytes() if out.exists() else f.read_bytes()
    _thumbs.clear(); _thumbs[k] = b
    return b


def open_board(run: str) -> int:
    """Put this run on CINEMA_PORT, replacing whoever holds it."""
    if _cinema["run"] == run and _cinema["proc"] and _cinema["proc"].poll() is None:
        return CINEMA_PORT
    if _cinema["proc"] and _cinema["proc"].poll() is None:
        _cinema["proc"].terminate()
        try:
            _cinema["proc"].wait(timeout=5)
        except Exception:
            _cinema["proc"].kill()
    _cinema["proc"] = subprocess.Popen(
        [sys.executable, str(HERE / "board.py"), f"runs/{run}"],
        cwd=str(HERE.parent),
        env=dict(os.environ, BOARD_PORT=str(CINEMA_PORT)),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _cinema["run"] = run
    time.sleep(1.2)
    return CINEMA_PORT


def survey(d: Path) -> dict:
    brief = (d / "stages" / "5-brief.md")
    plan_f = (d / "out" / "plan.json")
    plan = json.loads(plan_f.read_text()) if plan_f.is_file() else {}
    rows = (plan.get("scenes") or []) + (plan.get("cutaways") or [])
    want = len(rows)
    broll = d / "rushes" / "broll"
    clips = d / "rushes" / "clips"
    stills = len(list(broll.glob("*.png"))) + len(list((d / "rushes" / "anchored").glob("*.png"))) if broll.exists() or (d/"rushes"/"anchored").exists() else 0
    mp4 = len(list(broll.glob("*.mp4"))) + (len(list(clips.glob("*.mp4"))) if clips.exists() else 0)
    cut = (d / "cinema" / "CUT.mp4").is_file()
    parsed = NAMES.parse(d.name) if NAMES else None
    return {
        "run": d.name, "parsed": parsed, "want": want,
        "stills": stills, "clips": mp4, "cut": cut,
        "seconds": round(sum(float(r.get("seconds") or 0) for r in rows), 1),
        "when": datetime.fromtimestamp(d.stat().st_mtime).strftime("%d %b %H:%M"),
        "state": {
            "brief": brief.is_file(),
            "plan": bool(want),
            "frames": stills >= want > 0,
            "clips": mp4 >= want > 0,
            "voice": (d / "rushes" / "voice").is_dir(),
            "cut": cut,
        },
        "thumbs": sorted([p for p in broll.glob("*.png")] +
                         [p for p in (d / "rushes" / "anchored").glob("*.png")])[:6],
    }


def bar(s: dict) -> str:
    out = []
    for k in STAGES:
        on = s["state"].get(k)
        part = "part" if (not on and k == "frames" and 0 < s["stills"] < s["want"]) else ""
        out.append(f'<span class="st {"on" if on else part}">{k}</span>')
    return "".join(out)


def card(s: dict) -> str:
    p = s["parsed"] or {}
    chips = "".join(
        f'<span class="chip"><b>{e(k)}</b>{e(str(v))}</span>'
        for k, v in p.items() if k in ("brand", "product", "avatar", "angle", "concept", "format"))
    thumbs = "".join(
        f'<img src="/t/{e(s["run"])}/{e(t.name)}" alt="">' for t in s["thumbs"])
    done = f'{s["stills"]}/{s["want"]} frames · {s["clips"]}/{s["want"]} clips'
    return f"""<article class="run">
      <header>
        <div>
          <code class="name">{e(s['run'])}</code>
          <div class="meta">{e(done)} · {s['seconds']}s · touched {e(s['when'])}</div>
        </div>
        <div class="bar">{bar(s)}<a class="open" href="/open/{e(s['run'])}">Open board &rsaquo;</a></div>
      </header>
      <div class="chips">{chips or '<span class="chip warn">name does not parse</span>'}</div>
      <div class="strip">{thumbs or '<div class="none">no frames yet</div>'}</div>
    </article>"""


def page() -> str:
    runs = sorted([d for d in RUNS.iterdir() if d.is_dir()],
                  key=lambda d: d.stat().st_mtime, reverse=True)
    ss = [survey(d) for d in runs]
    tot = sum(x["want"] for x in ss)
    made = sum(x["stills"] for x in ss)
    return f"""<!doctype html><meta charset=utf-8><title>Briefs</title>
<style>
:root{{--bg:#16181A;--card:#1E2226;--ink:#E6E8EA;--soft:#9AA0A6;--rule:rgba(154,160,166,.2);
 --on:#7FA8D0;--part:#C9A227;--warn:#D07F7F}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:34px 22px 80px}}
h1{{font-size:22px;margin:0 0 4px;letter-spacing:-.01em}}
.sub{{color:var(--soft);margin:0 0 26px}}
.run{{background:var(--card);border:1px solid var(--rule);border-radius:7px;padding:16px 18px;margin-bottom:12px}}
.run header{{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;flex-wrap:wrap}}
.name{{font:12px/1.4 ui-monospace,Menlo,monospace;word-break:break-all;color:var(--ink)}}
.meta{{color:var(--soft);font-size:12.5px;margin-top:5px}}
.bar{{display:flex;gap:4px;flex-shrink:0}}
.st{{font:10px/1 ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;
 padding:5px 7px;border-radius:3px;border:1px solid var(--rule);color:var(--soft)}}
.st.on{{border-color:var(--on);color:var(--on)}}
.st.part{{border-color:var(--part);color:var(--part)}}
.open{{font:10px/1 ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;
 padding:5px 8px;border-radius:3px;border:1px solid var(--on);color:var(--on);
 text-decoration:none;margin-left:6px}}
.open:hover{{background:var(--on);color:var(--bg)}}
.chips{{display:flex;flex-wrap:wrap;gap:5px;margin:11px 0 0}}
.chip{{font:11px/1 ui-monospace,monospace;border:1px solid var(--rule);border-radius:3px;
 padding:4px 6px;color:var(--soft)}}
.chip b{{color:var(--ink);font-weight:500;margin-right:5px;opacity:.65}}
.chip.warn{{border-color:var(--warn);color:var(--warn)}}
.strip{{display:flex;gap:5px;margin-top:12px;overflow-x:auto}}
.strip img{{height:92px;border-radius:4px;flex-shrink:0}}
.none{{color:var(--soft);font-size:12.5px;padding:8px 0}}
</style>
<div class="wrap">
<h1>Briefs</h1>
<p class="sub">{len(ss)} runs · {made}/{tot} frames made · a stage is lit because its files are on disk, never because something said so. Open board puts that run on one fixed address, so there is never a second board showing an older one.</p>
{''.join(card(s) for s in ss)}
</div>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/open/"):
            run = unquote(self.path.split("/", 2)[2]).strip("/")
            port = open_board(run)
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{port}/")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); return
        if self.path.startswith("/t/"):
            _, _, run, name = self.path.split("/", 3)
            for sub in ("broll", "anchored"):
                f = RUNS / run / "rushes" / sub / name
                if f.is_file():
                    return self._img(thumb(f))
            self.send_response(404); self.end_headers(); return
        b = page().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _img(self, b):
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8458
    print(f"briefs · http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
