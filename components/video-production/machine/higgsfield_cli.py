"""higgsfield_cli — the clip door through the signed-in Higgsfield account (2026-11-20).

The keyed HTTP door (higgsfield_api.py) spends from the API key's own credit pool; the signed-in account (the
`higgsfield` command line) spends from the account's subscription credits. They are two pools. The owner's standing
rule: tools are account-agnostic and fall through to the next account or door. This door has the same surface as
higgsfield_api.py, so seedance.py can send the same call through either:

    ready()                           -> (True, credits) or (False, why)      read-only
    balance()                         -> credits or None                      read-only
    upload(path)                      -> the local path (the command line uploads a path itself)
    submit(model_path, payload)       -> job id
    wait(job_id)                      -> {"status": ..., "result_url": ...}
    outputs(body)                     -> [video URLs]
    download(url, dest)               -> bytes written

The payload is higgsfield_api's (image_urls, video_urls, audio_urls, image_url, end_image_url, prompt, resolution,
aspect_ratio, duration, generate_audio); the files in it are local paths. Brand-agnostic; no key is read here — the
command line holds its own sign-in.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

AGENT = "upright-video-production/1"
TERMINAL = {"completed", "failed", "nsfw", "cancelled", "canceled", "error"}
PLACES = ("/opt/homebrew/bin/higgsfield", "/usr/local/bin/higgsfield", "~/.npm-global/bin/higgsfield",
          "~/.local/bin/higgsfield")
# A door model path (higgsfield_api's) → the command line's job type.
JOB = (("bytedance/seedance-2.5/", "seedance_2_5"), ("bytedance/seedance-2.0/", "seedance_2_0"),
       ("minimax/h3/", "minimax_h3"))


def which():
    env = os.environ.get("HIGGSFIELD_BIN")
    if env and Path(env).expanduser().is_file():
        return str(Path(env).expanduser())
    found = shutil.which("higgsfield")
    if found:
        return found
    for p in PLACES:
        if Path(p).expanduser().is_file():
            return str(Path(p).expanduser())
    return None


def _run(args, timeout=300):
    exe = which()
    if not exe:
        raise RuntimeError("the Higgsfield command line is not installed on this machine")
    r = subprocess.run([exe] + list(args), capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def ready():
    try:
        code, out, err = _run(["account", "status", "--json"], timeout=60)
        acct = json.loads(out)
        if code == 0 and "credits" in acct:
            return True, float(acct["credits"])
        return False, (out + err).strip()[:200] or "not signed in"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]


def balance():
    ok, v = ready()
    return v if ok else None


def upload(path) -> str:
    p = Path(path).resolve()
    if not p.is_file():
        raise RuntimeError(f"no file at {p}")
    return str(p)


def job_type(model_path: str) -> str:
    for prefix, jt in JOB:
        if model_path.strip("/").startswith(prefix.strip("/")):
            return jt
    raise RuntimeError(f"the command-line door has no job type for {model_path!r}")


_ACCEPTS = {}


def accepts(jt: str):
    """The settings this model takes, from the command line's own model sheet (`model get`), or None when it cannot
    be read (then every setting is sent as before). A setting a model does not take is never sent: MiniMax refuses
    --generate_audio and --mode (20 Nov 2026: every MiniMax clip through this door failed on them)."""
    if jt not in _ACCEPTS:
        try:
            out = subprocess.run([which(), "model", "get", jt, "--json"], capture_output=True, text=True, timeout=60).stdout
            got = json.loads(out)
            got = got.get("params") or got.get("parameters") if isinstance(got, dict) else got
            _ACCEPTS[jt] = {x["name"] for x in got if isinstance(x, dict) and x.get("name")} or None
        except Exception:   # noqa: BLE001 — no sheet: send as before
            _ACCEPTS[jt] = None
    return _ACCEPTS[jt]


def args_for(model_path: str, payload: dict) -> list:
    """The `generate create` arguments for one call (no spend here). Only settings the model takes are sent."""
    jt = job_type(model_path)
    ok = accepts(jt)
    takes = lambda name: ok is None or name in ok   # noqa: E731
    a = ["generate", "create", jt, "--prompt", payload["prompt"]]
    for k, flag in (("duration", "--duration"), ("resolution", "--resolution")):
        if payload.get(k) is not None:
            a += [flag, str(payload[k])]
    a += ["--aspect-ratio", str(payload.get("aspect_ratio") or "auto")]
    if takes("generate_audio"):
        a += ["--generate_audio", "true" if payload.get("generate_audio") else "false"]
    media = []
    for k, flag in (("image_urls", "--image-references"), ("video_urls", "--video-references"),
                    ("audio_urls", "--audio-references")):
        for f in payload.get(k) or []:
            media += [flag, str(f)]
    if payload.get("image_url"):
        media += ["--start-image", str(payload["image_url"])]
    if payload.get("end_image_url"):
        media += ["--end-image", str(payload["end_image_url"])]
    if media:
        a += (["--mode", "omni_reference"] if takes("mode") else []) + media
    return a + ["--json"]


def _job_id(text: str):
    try:
        got = json.loads(text)
    except ValueError:
        m = re.search(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text or "")
        return m.group(0) if m else None
    if isinstance(got, list) and got:
        got = got[0]
    if isinstance(got, dict):
        return got.get("id") or got.get("job_id") or got.get("request_id")
    if isinstance(got, str) and re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", got):
        return got                                                  # the command line answers with a plain list of ids
    return None


ENDED = {"failed", "nsfw", "cancelled", "canceled", "error"}


def recent(size: int = 100) -> list:
    code, out, err = _run(["generate", "list", "--video", "--size", str(size), "--json"], timeout=120)
    try:
        got = json.loads(out)
    except ValueError:
        return []
    return got if isinstance(got, list) else []


def find(model_path: str, payload: dict, jobs=None):
    """The account's own job for this exact request (same model, prompt and length), if one is already out or made —
    so a request is never paid for twice (2026-11-20: a send the door could not read back was sent again, twice).
    A finished one first, else the oldest still running; a failed or refused one never counts."""
    jt = job_type(model_path)
    same = [j for j in (recent() if jobs is None else jobs)
            if j.get("job_type") == jt and (j.get("params") or {}).get("prompt") == payload.get("prompt")
            and str((j.get("params") or {}).get("duration")) == str(payload.get("duration"))
            and str(j.get("status", "")).lower() not in ENDED]
    if not same:
        return None
    same.sort(key=lambda j: (str(j.get("status", "")).lower() != "completed", j.get("created_at") or ""))
    return same[0].get("id")


def _spend():
    """The house's size limit, checked before anything is sent (components/generative-model-house/spend.py)."""
    import importlib.util
    f = Path(__file__).resolve().parents[2] / "generative-model-house" / "spend.py"
    spec = importlib.util.spec_from_file_location("gmh_spend", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def submit(model_path: str, payload: dict) -> str:
    sp, jt = _spend(), job_type(model_path)
    sp.check(jt, payload)
    files = [payload[k] for k in ("image_url", "end_image_url") if payload.get(k)] + \
            [f for k in ("image_urls", "video_urls", "audio_urls") for f in payload.get(k) or []]
    sp.inputs(payload.get("prompt"), files)              # nothing missing from a paid clip (2026-11-25)
    fp = sp.once(jt, {k: v for k, v in payload.items() if not k.endswith(("_url", "_urls"))}, files)
    code, out, err = _run(args_for(model_path, payload), timeout=900)
    jid = _job_id(out) if code == 0 else None
    if jid:
        sp.record(jt, fp, jid, payload.get("image_url") or (files[0] if files else ""))
        return jid
    # Whatever the command said, the job may exist (it charged and answered with an error, 2026-11-20): read the
    # account's jobs before calling this a refusal.
    jid = find(model_path, payload)
    if jid:
        sp.record(jt, fp, jid, payload.get("image_url") or (files[0] if files else ""))   # charged though it errored
        return jid
    if code != 0:
        raise RuntimeError(f"submit refused — command line: {(out + err).strip()[:400]}")
    raise RuntimeError("UNCERTAIN: the command line accepted the call but named no job — check the account's "
                       "recent jobs before sending again: " + out.strip()[:300])


def get(job_id: str) -> dict:
    code, out, err = _run(["generate", "get", job_id, "--json"], timeout=120)
    try:
        got = json.loads(out)
    except ValueError:
        return {"status": "unknown", "detail": (out + err).strip()[:300]}
    if isinstance(got, list) and got:
        got = got[0]
    return got if isinstance(got, dict) else {"status": "unknown"}


def wait(job_id: str, every: float = 6, limit_s: float = 1800) -> dict:
    _run(["generate", "wait", job_id, "--timeout", f"{int(limit_s)}s", "--interval", f"{int(every)}s", "--quiet"],
         timeout=limit_s + 120)
    body = get(job_id)
    if str(body.get("status", "")).lower() not in TERMINAL:
        return {"status": "timeout", "request_id": job_id}
    return body


def outputs(body: dict) -> list:
    urls = [body["result_url"]] if isinstance(body.get("result_url"), str) else []
    for k in ("results", "videos", "outputs"):
        for it in body.get(k) or []:
            u = it.get("url") if isinstance(it, dict) else it
            if isinstance(u, str) and u not in urls:
                urls.append(u)
    return urls


def download(url: str, dest) -> int:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=600) as r:
        dest.write_bytes(r.read())
    return dest.stat().st_size


def spent_since(since_iso: str, pages: int = 10):
    """Credits the account spent since a moment (its own transaction list; a top-up or grant never counts), or None
    when the list cannot be read. A balance read misses spend behind a top-up (2026-11-20: a 3000-credit auto top-up
    hid a run's clips from the cap)."""
    total, cursor = 0.0, None
    for _ in range(pages):
        args = ["account", "transactions", "--size", "100", "--json"] + (["--cursor", cursor] if cursor else [])
        try:
            code, out, err = _run(args, timeout=120)
            d = json.loads(out)
        except Exception:  # noqa: BLE001
            return None
        items = d.get("items") or [] if isinstance(d, dict) else []
        for t in items:
            if str(t.get("created_at") or "") < since_iso:
                return round(total, 2)
            if t.get("action") == "spend":
                total += -float(t.get("credits") or 0)
        cursor = d.get("cursor") if isinstance(d, dict) else None
        if not cursor or not items:
            return round(total, 2)
    return round(total, 2)
