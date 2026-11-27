#!/usr/bin/env python3
"""The Video Bench: a page on this machine where one clip is set up the way Seedance receives it, read, and made.

    python3 serve.py            # http://localhost:8896

owner never runs this; a launchd job keeps it up. Cases are frozen clips (capture.py): the same start picture and
the same voice read every time, so a test changes ONE input. The page shows the inputs numbered with their jobs, the
prompt (old, new, or edited), the size and the cost, and a button makes ONE clip through `machine/seedance.py`, the
same call every chain uses. The standard board makes every case with the old and the new prompt in one press.
Nothing spends without the cost box ticked. Clips file under runs/video-production/_bench/results/ and are copied to
the same path on the Shared Assets drive (never overwritten, never deleted). No brand or person is named here.
"""
import importlib.util
import json
import shutil
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
MACHINE = HERE.parent / "machine"
REPO = HERE.parents[2]


def _on_drive(q):
    """A finished file under runs/ handed to the Drive leaves a pointer: serve the Drive copy behind it
    (run-kit drive_hand.readable — inside runs/ as written, real place on a Drive home's runs/)."""
    rk = str(REPO / "components" / "run-kit")
    if rk not in sys.path:
        sys.path.append(rk)
    from run_kit import drive_hand
    return bool(q) and drive_hand.readable(q, REPO / "runs") is not None
BENCH = REPO / "runs" / "video-production" / "_bench"
DRIVE = Path.home() / "Library/CloudStorage/GoogleDrive-owner@company.com/Shared drives/Shared Assets"
PORT = int(__import__("os").environ.get("VIDEO_BENCH_PORT") or 8896)
JOBS, LOCK = {}, threading.Lock()
SERIAL = threading.Lock()                       # one paid call at a time (V37: one set at a time)


def _sd():
    sp = importlib.util.spec_from_file_location("vb_seedance", MACHINE / "seedance.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


SD = _sd()
STANDARD = ["G03-C1-1", "G04-C2", "G04-C1-2"]   # the standard board: short, one picture each, a whole read


def cases():
    out = []
    for f in sorted((BENCH / "cases").glob("*/*/case.json")):
        c = json.loads(f.read_text())
        c["dir"] = str(f.parent)
        c["standard"] = c["id"] in STANDARD
        out.append(c)
    return out


def case_of(cid, name=None):
    for c in cases():
        if c["id"] == cid and (not name or c["case"] == name):
            return c
    raise KeyError(cid)


def usd(res, secs):
    return round(SD.usd_per_s(res) * secs, 2)


IMG_ROLES = {
    "face": "Image {n} is the same person's face reference: use it for the face only.",
    "product": "Image {n} is the real product: its shape, size, label and colour exactly as shown, and nothing else from it.",
    "set": "Image {n} is the room: use its place, props and light only, no person from it.",
    "style": "Image {n} is the look reference: use its colour, light and grain only, no person or object from it.",
}
LIMITS = {"images": "1 to 8 subjects is the stable range", "video": "2 to 15 s each, 5 to 10 s works best, 3 at most on some doors",
          "audio": "2 to 15 s, one voice per person"}


def save_extra(x):
    """An uploaded reference (a data URL from the page) saved under the bench; returns (path, role, kind)."""
    import base64
    d = BENCH / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{int(time.time() * 1000)}-{Path(x.get('name') or 'ref').name}"
    f.write_bytes(base64.b64decode(x["upload"].split(",", 1)[-1]))
    return f, x.get("role") or "face", "video" if f.suffix.lower() in (".mp4", ".mov", ".webm") else "image"


def extras_of(body, c):
    """Every extra input as [(path, role, kind)]: the case's own face master when asked, then the caller's uploads."""
    out = []
    if body.get("master") and c.get("masters"):
        out.append((Path(c["masters"][0]), "face", "image"))
    for x in body.get("extras") or []:
        if x.get("upload"):
            out.append(save_extra(x))
        elif x.get("path") and Path(x["path"]).is_file():
            out.append((Path(x["path"]), x.get("role") or "face", "video" if Path(x["path"]).suffix.lower() in (".mp4", ".mov") else "image"))
    return out


def compose(prompt, extras):
    """The assets block grows by one bound line per extra, images numbered after Image 1, videos from Video 1."""
    sp = importlib.util.spec_from_file_location("vb_sp", MACHINE / "seedance_prompt.py")
    SPM = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(SPM)
    lines, ni, nv = [], 2, 1
    for _, role, kind in extras:
        if kind == "video":
            lines.append(SPM.VIDEO_LINE.format(n=nv)); nv += 1
        else:
            lines.append(IMG_ROLES.get(role, IMG_ROLES["face"]).format(n=ni)); ni += 1
    if not lines or lines[0] in prompt:
        return prompt
    head = prompt.split("\n")
    return "\n".join(head[:1] + lines + head[1:])


def shape(c, prompt, res, extras):
    prompt = compose(prompt, extras)
    d = Path(c["dir"])
    imgs = [{"n": 1, "role": "the first frame", "path": str(d / c["start"])}]
    ni, nv = 2, 1
    vids = []
    for p, role, kind in extras:
        if kind == "video":
            vids.append({"n": nv, "role": "motion and camera only", "path": str(p)}); nv += 1
        else:
            imgs.append({"n": ni, "role": {"face": "the face, for the face only", "product": "the real product", "set": "the room",
                                           "style": "the look"}.get(role, role), "path": str(p)}); ni += 1
    return {"videos": vids, "limits": LIMITS, "prompt": prompt, "images": imgs, "audio": {"n": 1, "role": "the voice read of the line", "path": str(d / c["read"])},
            "seconds": c["seconds"], "resolution": res, "aspect": "9:16", "usd": usd(res, c["seconds"]),
            "estimate": res not in SD.MEASURED}


def run_job(jid, c, label, prompt, res, extras):
    j = JOBS[jid]
    with SERIAL:
        try:
            j["state"] = "running"
            d = Path(c["dir"])
            out_dir = BENCH / "results"
            out = out_dir / f"{c['id']}-{label}-{res}-{time.strftime('%Y%m%d-%H%M%S')}.mp4"
            r = SD.talk(c["line"], d / c["start"], d / c["read"], out, seconds=None, masters=c.get("masters") or None,
                        no_people=not c.get("people"), refs=[p for p, _, k in extras if k == "image"],
                        videos=[p for p, _, k in extras if k == "video"], resolution=res, prompt=compose(prompt, extras))
            out.with_suffix(".json").write_text(json.dumps({"case": c["case"], "id": c["id"], "label": label, "resolution": res,
                                                            "extras": [{"file": str(p), "role": r} for p, r, _ in extras], "prompt": compose(prompt, extras),
                                                            "model": r.get("model"), "request_id": r.get("request_id"),
                                                            "seconds": r.get("seconds"), "usd": usd(res, r.get("seconds") or c["seconds"])}, indent=1))
            j["file"] = str(out)
            try:
                rel = out_dir.relative_to(REPO)
                dest = DRIVE / rel
                dest.mkdir(parents=True, exist_ok=True)
                for f in (out, out.with_suffix(".json")):
                    if not (dest / f.name).exists():
                        shutil.copy2(f, dest / f.name)
                j["drive"] = (dest / out.name).is_file()
            except Exception as e:                      # noqa: BLE001
                j["drive"], j["drive_why"] = False, str(e)[:120]
            j["state"] = "done"
        except (Exception, SystemExit) as e:            # noqa: BLE001
            j["state"], j["error"] = "failed", f"{type(e).__name__}: {str(e)[:300]}"


def start(c, label, prompt, res, extras, group=None):
    jid = f"j{int(time.time() * 1000)}{len(JOBS)}"
    with LOCK:
        JOBS[jid] = {"state": "waiting", "case": c["id"], "label": label, "res": res, "group": group}
    threading.Thread(target=run_job, args=(jid, c, label, prompt, res, extras), daemon=True).start()
    return jid


def results():
    out = []
    for f in sorted((BENCH / "results").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)[:60]:
        meta = json.loads(f.with_suffix(".json").read_text()) if f.with_suffix(".json").is_file() else {}
        out.append({"path": str(f), "name": f.name, **{k: meta.get(k) for k in ("id", "label", "resolution", "usd", "extras")}})
    return out


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, data, ctype="application/json"):
        b = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self.send(200, (HERE / "page.html").read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/options":
            return self.send(200, {"cases": cases(), "results": results(), "resolutions": {r: SD.usd_per_s(r) for r in ("480p", "720p")},
                                   "measured": list(SD.MEASURED)})
        if u.path == "/api/job":
            return self.send(200, JOBS.get(parse_qs(u.query).get("id", [""])[0], {"state": "unknown"}))
        if u.path == "/api/jobs":
            return self.send(200, JOBS)
        if u.path == "/file":
            q = parse_qs(u.query).get("path", [""])[0]
            f = Path(q).resolve()
            ctype = {".png": "image/png", ".jpg": "image/jpeg", ".wav": "audio/wav", ".mp3": "audio/mpeg", ".mp4": "video/mp4"}.get(f.suffix.lower())
            if not (f.is_file() and ctype and (BENCH in f.parents or (REPO / "runs") in f.parents or _on_drive(q))):
                return self.send(404, {"error": "not found"})
            return self.send(200, f.read_bytes(), ctype)
        return self.send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        res = body.get("resolution") or "480p"
        try:
            if self.path == "/api/preview":
                c = case_of(body["id"], body.get("case"))
                prompt = body.get("prompt") or c["prompts"][body.get("which", "new")]
                return self.send(200, shape(c, prompt, res, extras_of(body, c)))
            if self.path == "/api/generate":
                if not body.get("ok"):
                    return self.send(400, {"error": "tick the cost box first"})
                c = case_of(body["id"], body.get("case"))
                prompt = body.get("prompt") or c["prompts"][body.get("which", "new")]
                return self.send(200, {"id": start(c, body.get("label") or body.get("which", "custom"), prompt, res, extras_of(body, c))})
            if self.path == "/api/board":
                if not body.get("ok"):
                    return self.send(400, {"error": "tick the cost box first"})
                ids = []
                for c in [x for x in cases() if x["standard"]]:
                    for which in ("old", "new"):
                        ids.append(start(c, which, c["prompts"][which], res, [], group="board"))
                return self.send(200, {"ids": ids, "usd": round(sum(usd(res, c["seconds"]) * 2 for c in cases() if c["standard"]), 2)})
        except KeyError as e:
            return self.send(400, {"error": f"no such case: {e}"})
        except Exception as e:                          # noqa: BLE001
            return self.send(400, {"error": str(e)[:300]})
        return self.send(404, {"error": "not found"})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
