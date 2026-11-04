"""VIDEO PRODUCTION v2 — the picture/voice check door (2026-10-18).

v1 opened a whole `claude -p` session for every check (~160 per video, each
writing ~38k tokens of prompt cache that the next check never read). v2 makes
ONE direct API call per check — the picture and the question, nothing else, no
prompt cache written — and remembers every answer by a fingerprint of the
picture (or voice take) plus the question. A picture or take that has not
changed is never checked again.

Every paid call lands in the run's ledger.json with its dollars, including the
checks, the voice and the repairs (v1 left those out).

Config: machine/v2.json `checks`. Used by machine/run_v2.py; v1 never loads it.
"""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "v2.json").read_text())
LOCK = threading.RLock()
MAX_SIDE = 1024


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _key():
    import importlib.util
    sp = importlib.util.spec_from_file_location("v2_vp_keys", HERE / "vp_keys.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    k = (m.key("GEMINI_API_KEY") or "").strip()
    if not k:
        raise SystemExit("no GEMINI_API_KEY in this repo's .env — v2's checks need it")
    return k


def fingerprint(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        if isinstance(p, Path) or (isinstance(p, str) and len(p) < 400 and Path(p).is_file()):
            h.update(Path(p).read_bytes())
        else:
            h.update(str(p).encode())
        h.update(b"\0")
    return h.hexdigest()[:24]


# ------------------------------------------------------------- the ledger

def ledger(run: Path, model: str, job: str, usd: float | None, note: str = "", **extra) -> None:
    """One row per paid call, in the same shape v1's rows have."""
    row = {"model": model, "job": job, "seconds": extra.pop("seconds", 0.0), "tier": None,
           "resolution": extra.pop("resolution", None), "status": "done", "credits": None,
           "usd": None if usd is None else round(usd, 5), "at": now(), "shot": job.split("-v2")[0],
           "machine": "video-production-v2"}
    if note:
        row["note"] = note
    row.update(extra)
    with LOCK:
        p = Path(run) / "ledger.json"
        rows = json.loads(p.read_text()) if p.is_file() else []
        rows.append(row)
        p.write_text(json.dumps(rows, indent=1) + "\n")


# ------------------------------------------------------------- memory

def _mem_path(run: Path) -> Path:
    return Path(run) / "v2-checks.json"


def remembered(run: Path, fp: str):
    with LOCK:
        p = _mem_path(run)
        return (json.loads(p.read_text()) if p.is_file() else {}).get(fp)


def remember(run: Path, fp: str, answer) -> None:
    with LOCK:
        p = _mem_path(run)
        d = json.loads(p.read_text()) if p.is_file() else {}
        d[fp] = answer
        p.write_text(json.dumps(d, indent=1) + "\n")


STATS = {"asked": 0, "remembered": 0, "usd": 0.0}


# ------------------------------------------------------------- one call

def _inline(p: Path) -> dict:
    p = Path(p)
    data, mime = p.read_bytes(), mimetypes.guess_type(str(p))[0] or "image/png"
    try:
        from PIL import Image
        import io
        with Image.open(p) as im:
            if max(im.size) > MAX_SIDE:
                im = im.convert("RGB"); im.thumbnail((MAX_SIDE, MAX_SIDE))
                b = io.BytesIO(); im.save(b, "JPEG", quality=88)
                data, mime = b.getvalue(), "image/jpeg"
    except Exception:                                   # noqa: BLE001
        pass
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}


def model_of(name: str | None) -> str:
    """A model named in v2.json: "house:<job>" is read from the Generative Model House (VIDEO-RULINGS V2, P26) —
    "house:behind.judge" is the house judge, Gemini 3.1 Pro; any other value is a model id as written."""
    name = str(name or "")
    if name.startswith("house:"):
        import importlib.util as _u
        sp = _u.spec_from_file_location("vm_v2c_house", HERE / "house.py")
        h = _u.module_from_spec(sp)
        sp.loader.exec_module(h)
        return str(h.model(name.split(":", 1)[1]))
    return name


def ask(run: Path, job: str, prompt: str, images, model: str | None = None, want_json: bool = True):
    """One direct Gemini call. Returns (text, info). Remembered by fingerprint."""
    model = model_of(model or CFG["checks"]["zone_model"])
    images = [Path(i) for i in images if i and Path(i).is_file()]
    fp = fingerprint(model, prompt, *images)
    got = remembered(run, fp) if run else None
    if got is not None:
        STATS["remembered"] += 1
        return got["text"], {**got.get("info", {}), "remembered": True}
    parts = [{"text": prompt}] + [_inline(i) for i in images]
    gc = {"temperature": 0}
    if want_json:
        gc["responseMimeType"] = "application/json"
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={_key()}",
        data=json.dumps({"contents": [{"parts": parts}], "generationConfig": gc}).encode(),
        headers={"Content-Type": "application/json"})
    t = time.time()
    for n in range(3):
        try:
            with urllib.request.urlopen(req, timeout=int(CFG["checks"]["timeout_s"])) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and n < 2:
                time.sleep(5 * (n + 1)); continue
            raise RuntimeError(f"check door HTTP {e.code}: {e.read()[:200]!r}") from None
        except (TimeoutError, OSError, urllib.error.URLError) as e:   # a slow answer is the network: ask again
            if n < 2:
                time.sleep(5 * (n + 1)); continue
            raise RuntimeError(f"check door did not answer: {e}") from None
    text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    u = data.get("usageMetadata") or {}
    rate = CFG["checks"]["usd_per_m"].get(model, {"in": 0, "out": 0})
    tin = u.get("promptTokenCount") or 0
    tout = (u.get("candidatesTokenCount") or 0) + (u.get("thoughtsTokenCount") or 0)
    usd = tin / 1e6 * rate["in"] + tout / 1e6 * rate["out"]
    info = {"model": model, "seconds": round(time.time() - t, 1), "usd": round(usd, 5),
            "tokens": {"in": tin, "out": tout}}
    STATS["asked"] += 1
    STATS["usd"] += usd
    if run:
        ledger(run, model, job, usd, note="v2 check (direct, no cache)", tokens=info["tokens"],
               seconds=info["seconds"])
        remember(run, fp, {"text": text, "info": info})
    return text, info


def json_of(text: str):
    import re
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except Exception:                                   # noqa: BLE001
        return None


def zone_caller(run: Path, iid: str):
    """A safezone.check() caller on the v2 door: same prompt, same parsing."""
    class _A(str):
        backend = "v2-direct"
        model = CFG["checks"]["zone_model"]
        def by(self):
            return f"v2-direct ({self.model})"

    def call(prompt, img, entry):
        text, info = ask(run, f"{iid}-v2-zone", prompt, [img])
        return _A(text)
    return call


def memo_file_check(run_of, fn, kind: str):
    """Wrap a check of a FILE (a voice take, a clip) so an unchanged file with
    the same question is answered from memory. `run_of(args)` names the run."""
    def wrapped(f, *a, **kw):
        if kw.get("dry_run"):
            return fn(f, *a, **kw)
        run = run_of(f)
        fp = fingerprint(kind, Path(f), *[str(x) for x in a])
        got = remembered(run, fp) if run else None
        if got is not None:
            STATS["remembered"] += 1
            return got
        res = fn(f, *a, **kw)
        if run and res is not None:
            remember(run, fp, res)
        return res
    return wrapped
