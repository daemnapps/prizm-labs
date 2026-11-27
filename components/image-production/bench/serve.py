#!/usr/bin/env python3
"""The Picture Bench: a page on this machine where one picture is set up, read, and made.

    python3 serve.py            # http://localhost:8895

owner never runs this; a launchd job keeps it up. The page shows the inputs the way the model gets them
(numbered images, each with its role, and the prompt in its five sections), and a button makes ONE picture
through `image_production.plain.make`, the same call every chain uses. Pictures file under
runs/image-production/<brand>/picture-bench/ and are copied to the same path on the Shared Assets drive
(never overwritten, never deleted). No brand, product or person is named here: the page reads them off the folders.
"""
import base64
import json
import shutil
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))
import image_production as IP                             # noqa: E402
from image_production import paths as P, plain          # noqa: E402

sys.path.append(str(HERE.parent.parent / "model-inputs"))     # the Prompt Bench (preflight) lives in components/model-inputs
import prompt_bench as PB                                    # noqa: E402
PB_HERE = HERE.parent.parent / "model-inputs"

PORT = 8895
REPO = P.repo()


def _readable(q):
    """The file a page asked for: inside the repo as written, its real place in the repo or on the Drive
    (a finished file handed to the Drive leaves a pointer here — run-kit drive_hand.readable)."""
    if not q:
        return None
    rk = str(REPO / "components" / "run-kit")
    if rk not in sys.path:
        sys.path.append(rk)
    from run_kit import drive_hand
    return drive_hand.readable(q, REPO)
JOBS, LOCK = {}, threading.Lock()


def brands():
    base = REPO / "runs" / "ai-elements"
    out = {}
    for b in sorted(p for p in base.iterdir() if (p / "products").is_dir()):
        out[b.name] = sorted(k.name for k in (b / "products").iterdir() if (k / "kit.json").is_file())
    return out


def swipes():
    # every picture run works in runs/image-teardown/<brand>/<run>/ since 2026-10-28; the old lane folder is read for one release
    found = []
    for pat in ("runs/image-teardown/*/*/assets/source.*", "components/image-teardown/runs/*/assets/source.*"):
        for f in REPO.glob(pat):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                found.append((f.stat().st_mtime, f))
    return [{"path": str(f), "name": f.parent.parent.name} for _, f in sorted(found, reverse=True)[:40]]


def refs_from(body):
    """The caller's reference pictures: an uploaded one is saved into the bench folder first."""
    refs = []
    for r in body.get("references") or []:
        if r.get("upload"):
            d = REPO / "runs" / "image-production" / "_bench-uploads"
            d.mkdir(parents=True, exist_ok=True)
            f = d / f"{int(time.time() * 1000)}-{Path(r.get('name') or 'ref.png').name}"
            f.write_bytes(base64.b64decode(r["upload"].split(",", 1)[-1]))
            refs.append(f)
        elif r.get("path") and Path(r["path"]).is_file():
            refs.append(Path(r["path"]))
    return refs


def roles_of(body):
    return [(r.get("role") or "").strip() for r in body.get("references") or []]


def model_line():
    """Which model makes the picture, read off the route table (never typed here)."""
    e = plain.R.table()["models"]["gpt-image-person"]
    p = e.get("params") or {}
    return {"model": e.get("vendor_model"), "name": "GPT Image 2.5", "door": e.get("provider"),
            "variant": p.get("variant"), "resolution": p.get("resolution"),
            "quality": p.get("quality"), "size": e.get("sizes", {}).get("9:16"),
            "max_images": plain.MAX_IMAGES, "qualities": list(plain.QUALITIES)}


def plan_of(body, refs):
    return plain.plan(body["brand"], body.get("text", ""), refs, [body["product"]] if body.get("product") else [],
                      people=_people(body), ref_roles=roles_of(body))


def shape(pl, size=None, quality=None):
    found = plain._rules().check(plain.MODEL, pl["prompt"], [{"path": str(p)} for p in pl["refs"]],
                                 size=size or plain.R.table()["models"]["gpt-image-person"]["sizes"]["9:16"],
                                 quality=quality or plain.R.table()["models"]["gpt-image-person"]["params"]["quality"])
    return {"checks": found, "prompt": pl["prompt"], "images": [{"n": i + 1, "role": r, "path": str(p)}
                                                for i, (p, r) in enumerate(zip(pl["refs"], pl["roles"]))]}



def _people(body):
    """The bench's people choice: "none" (or false) says no person is in the picture; anything else needs a 3D set print
    as the first reference (GATE-4, 2026-11-10)."""
    v = body.get("people")
    return False if v in (False, "none", "no") else (v or None)

def run_job(jid, body, refs):
    j = JOBS[jid]
    try:
        out_dir = REPO / "runs" / "image-production" / body["brand"] / "picture-bench"
        out = out_dir / f"bench-{time.strftime('%Y%m%d-%H%M%S')}-{jid[-4:]}.png"
        raw = out_dir / "generated" / out.name        # the 4:5 content; the picture delivered is always the 9:16
        rec = plain.make(body["brand"], body.get("text", ""), raw, references=refs,
                         products=[body["product"]] if body.get("product") else [], aspect="9:16",
                         people=_people(body), quality=body.get("quality") or None, ref_roles=roles_of(body), size=body.get("size") or None, resolution=body.get("resolution") or None)
        plain.to_frame(raw, out)                      # made at 9:16 from the start; sized to 1080x1920, nothing painted
        j["file"], j["prompt"] = str(out), rec["prompt"]
        j["images"] = shape({"prompt": rec["prompt"], "refs": [Path(x) for x in rec["refs"]],
                             "roles": plain.plan(body["brand"], body.get("text", ""), refs,
                                                 [body["product"]] if body.get("product") else [], ref_roles=roles_of(body))["roles"]})["images"]
        out.with_suffix(".json").write_text(json.dumps({"request": {k: v for k, v in body.items() if k != "references"},
                                                          "quality": body.get("quality") or "high", "size": body.get("size") or "1152x2048", "frame": "9:16 native, safe zone in the prompt", "images": j["images"]}, indent=1))
        # the same path on the Shared Assets drive: copied in, never overwritten, never deleted
        try:
            rel = out_dir.relative_to(REPO)
            dest = P.drive_runs().parent / rel       # the mount is found, never typed: any teammate's account works
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "generated").mkdir(exist_ok=True)
            for f, d in ((out, dest), (raw, dest / "generated"), (raw.with_suffix(".prompt.txt"), dest), (out.with_suffix(".json"), dest)):
                if f.is_file() and not (d / f.name).exists():
                    shutil.copy2(f, d / f.name)
            j["drive"] = (dest / out.name).is_file()
        except Exception as e:                        # noqa: BLE001
            j["drive"] = False
            j["drive_why"] = str(e)[:120]
        j["state"] = "done"
    except (Exception, SystemExit) as e:                # noqa: BLE001
        j["state"], j["error"] = "failed", f"{type(e).__name__}: {str(e)[:300]}"


def history():
    out = []
    for f in (REPO / "runs" / "image-production").glob("*/picture-bench/bench-*.png"):
        out.append((f.stat().st_mtime, f))
    return [{"path": str(f), "name": f.name, "brand": f.parent.parent.name} for _, f in sorted(out, reverse=True)[:24]]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, data, ctype="application/json"):
        b = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")           # a reload always shows the current page
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self.send(200, (HERE / "page.html").read_bytes().replace(b"__STAMP__", time.strftime("%b %d, %H:%M", time.localtime((HERE / "page.html").stat().st_mtime)).encode()), "text/html; charset=utf-8")
        if u.path in ("/prompt", "/prompt/"):
            return self.send(200, (PB_HERE / "prompt_bench.html").read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/prompt-options":
            return self.send(200, PB.options())
        if u.path == "/media":                               # the Prompt Bench's clips and voice reads, from the repo only
            f = _readable(parse_qs(u.query).get("path", [""])[0])   # in the repo, or a finished file's pointer to the Drive
            types = {".mp4": "video/mp4", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav"}
            if not (f and f.is_file() and f.suffix.lower() in types):
                return self.send(404, {"error": "not found"})
            return self.send(200, f.read_bytes(), types[f.suffix.lower()])
        if u.path == "/api/prompt-job":
            return self.send(200, PB.job(parse_qs(u.query).get("id", [""])[0]))
        if u.path == "/api/prompt-recipes":
            qs = parse_qs(u.query)
            return self.send(200, {"recipes": PB.recipes(qs.get("brand", [""])[0], qs.get("run", [None])[0])})
        if u.path == "/api/prompt-made":
            return self.send(200, {"made": PB.made()})
        if u.path == "/api/prompt-batch":
            return self.send(200, PB.batch(parse_qs(u.query).get("run", [""])[0]))
        if u.path == "/api/prompt-shots":                      # a video's shots: one start picture each + its effects
            try:
                return self.send(200, PB.shots(parse_qs(u.query).get("run", [""])[0]))
            except (ValueError, OSError) as e:
                return self.send(400, {"error": str(e)[:300]})
        if u.path == "/api/prompt-handoff":
            q = parse_qs(u.query)
            return self.send(200, PB.handoff_state(q.get("run", [""])[0], q.get("kind", [None])[0]))
        if u.path == "/api/options":
            return self.send(200, {"brands": brands(), "swipes": swipes(), "history": history(), "model": model_line()})
        if u.path == "/api/job":
            return self.send(200, JOBS.get(parse_qs(u.query).get("id", [""])[0], {"state": "unknown"}))
        if u.path == "/file":
            f = _readable(parse_qs(u.query).get("path", [""])[0])
            ok = bool(f) and f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
            if not ok:
                return self.send(404, {"error": "not found"})
            return self.send(200, f.read_bytes(), {".png": "image/png", ".webp": "image/webp"}.get(f.suffix.lower(), "image/jpeg"))
        return self.send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path == "/api/prompt-preview":
            return self.send(*PB.preview(body))
        if self.path == "/api/prompt-make":
            return self.send(*PB.make(body))
        if self.path == "/api/prompt-upload":
            return self.send(*PB.upload(body))
        if self.path == "/api/prompt-recipe":
            return self.send(*PB.save_recipe(body))
        if self.path == "/api/prompt-good":
            return self.send(*PB.looks_good(body))
        if self.path == "/api/prompt-batch-write":
            return self.send(*PB.batch_write(body))
        if self.path == "/api/prompt-batch-make":
            return self.send(*PB.batch_make(body))
        if self.path == "/api/prompt-batch-card":
            return self.send(*PB.batch_card(body))
        if self.path == "/api/prompt-shot-open":
            return self.send(*PB.shot_open(body))
        if self.path == "/api/prompt-hook-action":
            return self.send(*PB.hook_action(body))
        if self.path == "/api/prompt-hook-update":
            return self.send(*PB.hook_update(body))
        if self.path == "/api/prompt-shot-approve":
            return self.send(*PB.shot_approve(body))
        if self.path == "/api/prompt-shot-change":
            return self.send(*PB.shot_change(body))
        if self.path == "/api/prompt-edit-make":
            return self.send(*PB.edit_make(body))
        if self.path == "/api/prompt-effect-make":
            return self.send(*PB.effect_make(body))
        if self.path == "/api/prompt-shot-keep":
            return self.send(*PB.shot_keep(body))
        if self.path == "/api/prompt-handoff":
            return self.send(*PB.handoff(body))
        if self.path == "/api/prompt-delivery":
            return self.send(*PB.delivery_check(body))
        if self.path == "/api/prompt-delivery-card":
            return self.send(*PB.delivery_card(body))
        if not body.get("brand"):
            return self.send(400, {"error": "pick a brand"})
        refs = refs_from(body)
        if self.path == "/api/preview":
            try:
                return self.send(200, {**shape(plan_of(body, refs), body.get("size") or None, body.get("quality") or None), "model": model_line()})
            except Exception as e:                      # noqa: BLE001
                return self.send(400, {"error": str(e)[:300]})
        if self.path == "/api/cost":
            # what this picture would cost on the Higgsfield door: asked of Higgsfield, spends nothing
            try:
                pl = plan_of(body, refs)
                e = plain.R.table()["models"]["gpt-image-person"]
                if e.get("provider") != "higgsfield":
                    return self.send(200, {"credits": None, "say": "This picture goes through OpenAI directly, which prices in dollars on the bill, not credits."})
                prm = dict(e.get("params") or {})
                if body.get("quality"):
                    prm["quality"] = body["quality"]
                if body.get("resolution"):
                    prm["resolution"] = body["resolution"]
                c = plain.PR.higgsfield_cost({**e, "params": prm}, pl["prompt"], [], "9:16")
                return self.send(200, {"credits": c, "say": f"{c:g} credits"})
            except Exception as ex:                    # noqa: BLE001
                return self.send(400, {"error": str(ex)[:300]})
        if self.path == "/api/generate":
            if plain.R.recipe_required():                  # every picture passes the variable sheet: made from the Prompt Bench
                return self.send(400, {"error": "Pictures are made from the Prompt Bench (the Prompt link at the top): it fills in "
                                                "every variable of the sheet first, so nothing blank reaches the picture maker."})
            if not (body.get("text") or "").strip():
                return self.send(400, {"error": "write what the picture shows first"})
            jid = f"j{int(time.time() * 1000)}"
            with LOCK:
                JOBS[jid] = {"state": "running"}
            threading.Thread(target=run_job, args=(jid, body, refs), daemon=True).start()
            return self.send(200, {"id": jid})
        return self.send(404, {"error": "not found"})


def _loaded_code():
    """Every source file this server has loaded from components/, this file included."""
    files = [getattr(m, "__file__", None) for m in list(sys.modules.values())]
    return {Path(f) for f in files if f and f.endswith(".py") and f.startswith(str(REPO / "components"))} | {Path(__file__).resolve()}


def _newest_code():
    return max((f.stat().st_mtime for f in _loaded_code() if f.is_file()), default=0)


def keep_current(every=15):
    """The board always runs the code on disk: once a loaded file changes and has sat still for one pass, and every
    loaded file compiles, the server replaces itself. Jobs run in their own processes (board_job.py), so none stops."""
    import os
    seen = _newest_code()
    while True:
        time.sleep(every)
        now = _newest_code()
        if now <= seen:
            continue
        time.sleep(every)
        if _newest_code() != now:
            continue
        try:
            for f in _loaded_code():
                compile(f.read_text(), str(f), "exec")
        except (SyntaxError, ValueError, OSError) as e:
            print(f"keeping the running board: {e}", flush=True)
            seen = now
            continue
        print("code changed: restarting the board", flush=True)
        os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve())])


if __name__ == "__main__":
    threading.Thread(target=keep_current, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
