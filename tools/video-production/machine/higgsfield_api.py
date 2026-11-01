"""higgsfield_api — the machine's own Higgsfield door over HTTP (2026-10-20).

the owner, 2026-10-20: "we can run this all through higgsfield now." The MCP door only runs inside
a session; this one runs anywhere the keys are, so production can make its own swaps.

    upload(path)                      -> public URL   (POST /files/generate-upload-url, PUT the bytes)
    submit(model_path, payload)       -> request id   (POST /<model path>)
    wait(request_id)                  -> final status body
    outputs(body)                     -> [video/image URLs]

Keys by name only, through components/keys/loader.py: HIGGSFIELD_KEY_ID, HIGGSFIELD_KEY_SECRET.
Brand-agnostic.
"""
from __future__ import annotations

import hashlib
import subprocess
import importlib.util
import json
import mimetypes
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://api.higgsfield.ai"
AGENT = "upright-video-production/1"
TERMINAL = {"completed", "failed", "nsfw", "cancelled", "canceled", "error"}
_KEYS = Path(__file__).resolve().parents[2] / "keys" / "loader.py"


def _auth() -> str:
    spec = importlib.util.spec_from_file_location("hf_keys_loader", _KEYS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return f"Key {mod.key('HIGGSFIELD_KEY_ID')}:{mod.key('HIGGSFIELD_KEY_SECRET')}"


def _call(url: str, payload=None, method=None, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": _auth(), "Accept": "application/json", "User-Agent": AGENT}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method or ("POST" if data is not None else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except ValueError:
            return e.code, {"detail": body[:600]}


def upload(path) -> str:
    """Reuse identical uploaded assets; retry only the byte transfer, never a generation."""
    p = Path(path)
    ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    cache = Path(__file__).resolve().parents[3] / 'runs/ai-elements/higgsfield-uploads' / (sha + '.json')
    if cache.is_file():
        saved = json.loads(cache.read_text())
        if saved.get('content_type') == ctype and saved.get('public_url') and time.time() - saved.get('at', 0) < 86400:
            return saved['public_url']
    source_type, transfer_sha = ctype, sha
    # Keep the approved original. Large opaque PNG references get a reusable
    # full-resolution transfer JPEG; no crop, resize, retouching or generation.
    if p.suffix.lower() == '.png' and p.stat().st_size > 4 * 1024 * 1024:
        from PIL import Image
        with Image.open(p) as im:
            if im.mode == 'RGB':
                prepared = cache.parent / 'prepared' / (sha + '.jpg')
                if not prepared.is_file():
                    prepared.parent.mkdir(parents=True, exist_ok=True)
                    im.save(prepared, 'JPEG', quality=90, optimize=True, subsampling=0)
                    prepared.with_suffix('.source.json').write_text(json.dumps({'source': str(p),
                        'source_sha256': sha, 'dimensions': list(im.size), 'quality': 90, 'purpose': 'upload transfer only'}))
                p, ctype = prepared, 'image/jpeg'
                transfer_sha = hashlib.sha256(p.read_bytes()).hexdigest()
    code, body = _call(f"{BASE}/files/generate-upload-url", {"content_type": ctype})
    if code not in (200, 201) or not body.get("upload_url"):
        raise RuntimeError(f"upload URL refused — HTTP {code}")
    headers = dict(body.get("upload_headers") or {"Content-Type": ctype})
    # curl streams large files reliably on this host. Keep the signed URL out of
    # process arguments/logs; only upload retries are allowed here.
    config = 'url = ' + json.dumps(body['upload_url']) + '\n'
    config += ''.join('header = ' + json.dumps(k + ': ' + v) + '\n' for k, v in headers.items())
    response = subprocess.run(['curl', '--silent', '--show-error', '--fail', '--http1.1',
        '--connect-timeout', '20', '--max-time', '90', '--retry', '2', '--retry-all-errors', '--retry-delay', '2',
        '--header', 'Expect:', '--output', '/dev/null', '--write-out', '%{size_upload}', '--upload-file', str(p), '--config', '-'], input=config, text=True, capture_output=True, timeout=290)
    if response.returncode:
        # A lost PUT acknowledgement is not proof the storage write failed.
        # Verify exact bytes at its public URL before asking for another upload.
        verified = False
        try:
            with urllib.request.urlopen(body['public_url'], timeout=20) as remote:
                got = remote.read(p.stat().st_size + 1)
            verified = hashlib.sha256(got).hexdigest() == transfer_sha
        except (OSError, urllib.error.URLError):
            pass
        if not verified:
            transferred = response.stdout.strip() if response.stdout.strip().isdigit() else 'unknown'
            raise RuntimeError(f"Upload of {p.name} failed (curl {response.returncode}, bytes sent {transferred}); no generation submitted")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({'sha256': sha, 'content_type': source_type, 'transfer_sha256': transfer_sha, 'transfer_file': str(p), 'public_url': body['public_url'], 'at': time.time()}))
    return body['public_url']


def submit(model_path: str, payload: dict) -> str:
    code, body = _call(f"{BASE}/{model_path.strip('/')}", payload)
    rid = body.get("request_id") if isinstance(body, dict) else None
    if code not in (200, 201) or not rid:
        raise RuntimeError(f"submit refused — HTTP {code}: {json.dumps(body)[:400]}")
    return rid


def wait(request_id: str, every: float = 6, limit_s: float = 1800) -> dict:
    t0 = time.time()
    while time.time() - t0 < limit_s:
        time.sleep(every)
        code, body = _call(f"{BASE}/requests/{request_id}/status", timeout=60)
        if code == 200 and str(body.get("status", "")).lower() in TERMINAL:
            return body
    return {"status": "timeout", "request_id": request_id}


def outputs(body: dict) -> list:
    urls = []
    for k in ("videos", "images", "outputs", "results"):
        for it in body.get(k) or []:
            u = it.get("url") if isinstance(it, dict) else it
            if isinstance(u, str):
                urls.append(u)
    for k in ("video", "image"):
        v = body.get(k)
        if isinstance(v, dict) and v.get("url"):
            urls.append(v["url"])
    return urls


def download(url: str, dest) -> int:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=600) as r:
        dest.write_bytes(r.read())
    return dest.stat().st_size
