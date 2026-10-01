#!/usr/bin/env python3
"""
direct_openai.py — the machine hand's stills door: GPT Image 2, direct on the
OpenAI API (Damon's 2026-09-17 ruling). Every field value this module sends
(model id, quality, input_fidelity, moderation, size, output_format, and the
two endpoint URLs) comes from `providers.json`'s own `direct.openai` section
— nothing here names a model.

    python3 machine/direct_openai.py "<prompt>" [--ref <path> ...] --out <file> [--dry-run]

`generate(prompt, references, out, transport=None, key=None, dry_run=False)`:
a multipart POST to `images/edits` with every reference file sent as a
repeated `image[]` part, in the order given — OpenAI's own docs: "the first
image in the list preserves the finest detail," so callers pass the cast
sheet first, the packshot second. With no references, a plain JSON POST to
`images/generations`. Either way the response's `b64_json` is decoded
straight to `out`. Returns `{file, model, request_id, usage}` — `request_id`
read off the response headers when the transport supplies one (unverified
which header OpenAI actually sends this on; checked `x-request-id` and
`openai-request-id`), else `None`.

`key_of()`: `OPENAI_API_KEY`, env first, then the Keychain vault
(`daemn_keys`) — never a crash, only ever `None` when neither has it.
`generate()` itself raises `SystemExit` naming the key when a real (non
dry-run) call has none — never a silent skip.

`transport(method, url, headers, body_bytes) -> (status, headers, body_bytes)`
is the one seam every real call goes through; the default is a plain
urllib implementation. `--dry-run` (and `dry_run=True`) prints the request
— method, url, headers with the key redacted, and the body/fields — and
writes no file.

No brand, model or person name lives in this file as a literal.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


platform = _load("platform")


def cfg() -> dict:
    return platform.registry()["direct"]["openai"]


def key_of() -> str | None:
    """OPENAI_API_KEY: env first, then the Keychain vault — never a crash, a
    teammate's clone with neither simply has no key."""
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k
    try:
        import daemn_keys
        return daemn_keys.key("OPENAI_API_KEY") or None
    except Exception:
        return None


def _boundary() -> str:
    return f"----daemn-{uuid.uuid4().hex}"


def _multipart_body(fields: dict, files: list[tuple[str, Path]], boundary: str) -> bytes:
    """`fields`: name -> scalar value. `files`: repeated (field_name, path)
    pairs, emitted in the order given — order carries meaning upstream
    (the first image is the one OpenAI preserves detail from)."""
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f'{value}\r\n'.encode())
    for name, path in files:
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
            + path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts)


def http_transport(method: str, url: str, headers: dict, body: bytes | None):
    """The real network call — the default `transport`."""
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    # A 9:16 xhigh generation with references can take longer than three
    # minutes, and the network drops a socket now and then: the first paid
    # run (2026-09-19) died on one `Operation timed out` at frame 1 of 26.
    # A timed-out or reset call is retried twice before it counts; an HTTP
    # error is returned as the answer it is.
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=420) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers or {}), e.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = e
            import time as _t
            _t.sleep(5 * (attempt + 1))
    raise RuntimeError(f"OpenAI images: {last} after 3 attempts")


def _redacted(headers: dict) -> dict:
    return {k: ("Bearer <redacted>" if k.lower() == "authorization" else v)
            for k, v in headers.items()}


def generate(prompt: str, references: list[Path], out: Path, transport=None,
             key: str | None = None, dry_run: bool = False) -> dict:
    """Edit (references given) or generate (none) — see module docstring."""
    transport = transport or http_transport
    k = key if key is not None else key_of()
    if not dry_run and not k:
        raise SystemExit("no OPENAI_API_KEY — set it in the environment or the Keychain vault")

    c = cfg()
    model = c["model"]
    params = dict(c.get("params") or {})

    if references:
        boundary = _boundary()
        fields = {"model": model, "prompt": prompt, **{k2: str(v) for k2, v in params.items()}}
        files = [("image[]", Path(r)) for r in references]
        headers = {"Authorization": f"Bearer {k or ''}",
                   "Content-Type": f"multipart/form-data; boundary={boundary}"}
        url = c["images_edit"]
        if dry_run:
            print(json.dumps({"method": "POST", "url": url, "headers": _redacted(headers),
                              "fields": fields, "files": [str(p) for _, p in files]}, indent=1))
            return {"file": None, "model": model, "request_id": None, "usage": None}
        body = _multipart_body(fields, files, boundary)
        status, resp_headers, resp_body = transport("POST", url, headers, body)
        if status == 400 and b"invalid_input_fidelity_model" in resp_body and "input_fidelity" in fields:
            # Learned live 2026-09-18: the 2.5 models do not take input_fidelity
            # at all (it was a 2.x edits parameter). Send the same edit without
            # it rather than fail the frame; the registry notes it per model.
            print(f"  note: {model} does not take input_fidelity — sent without it", file=sys.stderr)
            fields.pop("input_fidelity")
            body = _multipart_body(fields, files, boundary)
            status, resp_headers, resp_body = transport("POST", url, headers, body)
    else:
        # input_fidelity only exists on the edits endpoint (it governs how the
        # reference images are honoured); generations rejects it as unknown
        body_obj = {"model": model, "prompt": prompt,
                    **{k2: v for k2, v in params.items() if k2 != "input_fidelity"}}
        headers = {"Authorization": f"Bearer {k or ''}", "Content-Type": "application/json"}
        url = c["images_generate"]
        if dry_run:
            print(json.dumps({"method": "POST", "url": url, "headers": _redacted(headers),
                              "body": body_obj}, indent=1))
            return {"file": None, "model": model, "request_id": None, "usage": None}
        status, resp_headers, resp_body = transport("POST", url, headers,
                                                      json.dumps(body_obj).encode())

    data = json.loads(resp_body.decode())
    if status is not None and status >= 400:
        raise RuntimeError(f"OpenAI images error {status}: {json.dumps(data)[:400]}")
    items = data.get("data") or []
    b64 = items[0].get("b64_json") if items else None
    if not b64:
        raise RuntimeError(f"no b64_json in response: {json.dumps(data)[:400]}")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(b64))
    # unverified: which header actually carries OpenAI's request id — no
    # confirmed field name in providers/research/gpt-image-2.md; both common
    # spellings are checked, else None rather than a guess.
    request_id = (resp_headers.get("x-request-id") or resp_headers.get("X-Request-Id")
                  or resp_headers.get("openai-request-id") or resp_headers.get("Openai-Request-Id"))
    return {"file": str(out), "model": model, "request_id": request_id, "usage": data.get("usage")}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt")
    ap.add_argument("--ref", action="append", default=[], dest="refs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        result = generate(a.prompt, [Path(r) for r in a.refs], Path(a.out), dry_run=a.dry_run)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    if not a.dry_run:
        print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
