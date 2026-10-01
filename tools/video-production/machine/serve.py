#!/usr/bin/env python3
"""Serves the production board, live — and runs its buttons.

The status of the process is always live — a published artifact is a
snapshot someone has to re-push; this reads the actual files (Damon's
2026-08-20 ruling). Every board load rebuilds board.html from runs/ and
prompts/, so disk state = screen state.

The board's controls call back here:

  POST /api/runs/<slug>/timeline   {timeline: {...}}   save the edit surface
  POST /api/runs/<slug>/job        {action, ids}        run sequence.py
  GET  /api/runs/<slug>/job                             poll the running job
  POST /api/fal-key                {key}                store the model key
                                   (written to machine/.env — local only,
                                   gitignored, never echoed back)

Actions map to sequence.py verbs; "picture" chains stills → clips for the
same ids (the invalidation rule: a new picture invalidates its clip). One
job at a time per run; per-shot failure isolation lives in sequence.py.

  python3 serve.py          # http://localhost:8791
"""

import json
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8791

ACTIONS = {"stills", "vo", "clips", "assemble", "picture"}
JOBS = {}  # slug -> {running, action, ids, log, ok}
LOCK = threading.Lock()


def run_job(slug, action, ids):
    job = JOBS[slug]

    def step(verb, vids):
        cmd = [sys.executable, str(HERE / "sequence.py"), slug, verb] + vids
        p = subprocess.Popen(cmd, cwd=str(HERE), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        for line in p.stdout:
            job["log"].append(line.rstrip())
        return p.wait() == 0

    try:
        if action == "picture":
            ok = step("stills", ids) and step("clips", ids)
        elif action == "vo":
            # words changed: new line, and the clip re-rolls only if it
            # exists (its length may change) — the 1¢-plus rule.
            ok = step("vo", ids)
            redo = [i for i in ids
                    if (RUNS / slug / "clips" / f"{i}.mp4").exists()]
            if ok and redo:
                job["log"].append(f"line changed — re-rolling clip for "
                                  f"{' '.join(redo)} (length follows the VO)")
                ok = step("clips", redo)
            if ok:
                ok = step("assemble", [])
        elif action in ("clips", "stills"):
            ok = step(action, ids)
            if ok:
                ok = step("assemble", [])
        else:
            ok = step(action, ids)
        job["ok"] = ok
    except Exception as e:
        job["log"].append(f"error: {e}")
        job["ok"] = False
    finally:
        job["running"] = False


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HERE), **kw)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    # ---- API ----

    def api_parts(self):
        p = self.path.split("?")[0].strip("/").split("/")
        # api / runs / <slug> / (timeline|job)
        if len(p) == 4 and p[0] == "api" and p[1] == "runs":
            return p[2], p[3]
        return None, None

    def do_GET(self):
        slug, what = self.api_parts()
        if what == "job":
            job = JOBS.get(slug)
            if not job:
                return self._json({"running": False, "ok": None, "log_tail": ""})
            return self._json({"running": job["running"], "ok": job["ok"],
                               "action": job["action"], "ids": job["ids"],
                               "log_tail": "\n".join(job["log"][-12:])})
        if what == "timeline":
            f = RUNS / slug / "timeline.json"
            if f.exists():
                return self._json(json.loads(f.read_text()))
            return self._json({"error": "no such run"}, 404)
        if self.path.split("?")[0] in ("/", "/board.html", "/index.html"):
            subprocess.run([sys.executable, str(HERE / "board.py")],
                           capture_output=True)
            self.path = "/board.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] == "/api/fal-key":
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            k = (body.get("key") or "").strip()
            if len(k) < 20 or any(c.isspace() for c in k):
                return self._json({"error": "that doesn't look like a key"}, 400)
            (HERE / ".env").write_text(f"FAL_KEY={k}\n")
            return self._json({"armed": True})
        slug, what = self.api_parts()
        if not slug:
            return self._json({"error": "unknown endpoint"}, 404)
        run_dir = RUNS / slug
        if not (run_dir / "timeline.json").exists():
            return self._json({"error": f"no run named {slug}"}, 404)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._json({"error": "bad json"}, 400)

        if what == "timeline":
            t = body.get("timeline")
            if not isinstance(t, dict) or "shots" not in t:
                return self._json({"error": "timeline missing shots"}, 400)
            f = run_dir / "timeline.json"
            f.write_text(json.dumps(t, indent=2))
            return self._json({"saved": True})

        if what == "job":
            action = body.get("action")
            ids = [i for i in (body.get("ids") or []) if isinstance(i, str)]
            if action not in ACTIONS:
                return self._json({"error": f"unknown action {action}"}, 400)
            with LOCK:
                if JOBS.get(slug, {}).get("running"):
                    return self._json({"error": "a job is already running "
                                       "for this run — let it finish"}, 409)
                JOBS[slug] = {"running": True, "action": action, "ids": ids,
                              "log": [], "ok": None}
                threading.Thread(target=run_job, args=(slug, action, ids),
                                 daemon=True).start()
            return self._json({"started": True})

        return self._json({"error": "unknown endpoint"}, 404)


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as s:
        print(f"board live at http://localhost:{PORT}")
        s.serve_forever()
