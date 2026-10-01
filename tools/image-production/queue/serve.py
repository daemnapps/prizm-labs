#!/usr/bin/env python3
"""The queue page — localhost, no build step, updates itself.

    serve.py [--port 8794]

GET /            the page          GET /state.json   the queue, computed now
GET /img/<path>  a picture         GET /api/job      {running, ok, log_tail}
POST /api/review {asset, verdict, why}   POST /api/job {step: plan|run|sync|kit}
"""
import json, subprocess, sys, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[3]
sys.path.insert(0, str(HERE)); import queue as Q
LOCK = threading.Lock(); JOB = {"running": False, "ok": None, "step": None}


def job(step):
    JOB.update(running=True, ok=None, step=step)
    try:
        {"plan": Q.plan, "run": Q.run, "sync": Q.sync, "kit": Q.kit}[step]()
        JOB["ok"] = True
    except Exception as e:
        Q.log(f"{step}: {e}"); JOB["ok"] = False
    finally:
        JOB["running"] = False


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=str(HERE), **k)
    def log_message(self, *a): pass
    def end_headers(self):
        self.send_header("Cache-Control", "no-store"); super().end_headers()
    def _json(self, d, code=200):
        b = json.dumps(d, ensure_ascii=False).encode(); self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"): self.path = "/page.html"; return super().do_GET()
        if p == "/state.json": return self._json(Q.state())
        if p == "/proof.json":
            import proof; return self._json(proof.rows())
        if p == "/proof": self.path = "/proof.html"; return super().do_GET()
        if p == "/api/job":
            tail = (HERE / "log.txt").read_text().splitlines()[-25:] if (HERE / "log.txt").is_file() else []
            return self._json({**JOB, "log_tail": tail})
        if p.startswith("/thumb/"):
            name = p[7:]; f = next((x for x in (WS / "image-production/runs").rglob(name + ".png")), None)
            if not f or not f.is_file(): return self._json({"error": "no"}, 404)
            th = HERE / ".thumbs" / (name + ".jpg"); th.parent.mkdir(exist_ok=True)
            if not th.is_file() or th.stat().st_mtime < f.stat().st_mtime:
                from PIL import Image
                im = Image.open(f).convert("RGB"); im.thumbnail((360, 640)); im.save(th, "JPEG", quality=82)
            b = th.read_bytes(); self.send_response(200); self.send_header("Content-Type", "image/jpeg"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if p.startswith("/tn/"):
            import hashlib
            rel = p[4:]; f = (WS / rel).resolve()
            if not str(f).startswith(str(WS / "image-production/runs")) or not f.is_file(): return self._json({"error": "no"}, 404)
            th = HERE / ".thumbs" / (hashlib.md5(rel.encode()).hexdigest() + ".jpg"); th.parent.mkdir(exist_ok=True)
            if not th.is_file() or th.stat().st_mtime < f.stat().st_mtime:
                from PIL import Image
                im = Image.open(f).convert("RGB"); im.thumbnail((420, 740)); im.save(th, "JPEG", quality=84)
            b = th.read_bytes(); self.send_response(200); self.send_header("Content-Type", "image/jpeg"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if p.startswith("/img/"):
            f = (WS / p[5:]).resolve()
            if not str(f).startswith(str(WS / "image-production/runs")) or not f.is_file(): return self._json({"error": "no"}, 404)
            b = f.read_bytes(); self.send_response(200); self.send_header("Content-Type", "image/png"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        return super().do_GET()
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/api/review":
            return self._json(Q.review(body["asset"], body["verdict"], body.get("why", "")))
        if self.path == "/api/job":
            with LOCK:
                if JOB["running"]: return self._json({"error": "a job is already running", **JOB}, 409)
                threading.Thread(target=job, args=(body["step"],), daemon=True).start()
            return self._json({"started": body["step"]})
        return self._json({"error": "unknown"}, 404)


if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8794
    print(f"queue page → http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
