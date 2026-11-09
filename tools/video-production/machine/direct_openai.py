#!/usr/bin/env python3
"""
direct_openai.py — the machine hand's stills door: GPT Image 2, direct on the
OpenAI API (the owner's 2026-09-17 ruling). Every field value this module sends
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

`key_of()`: `OPENAI_API_KEY`, read through the shared key
loader (components/keys, via vp_keys) — never a crash, only ever `None` when neither has it.
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
import re
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


platform = _load("provider_platform")
vp_keys = _load("vp_keys")


def cfg() -> dict:
    """The picture door's settings; the MODEL is the Generative Model House's (pictures.generate — the same model
    edits, pictures.edit), read there and never from providers.json (VIDEO-RULINGS V2, P23)."""
    c = dict(platform.registry()["direct"]["openai"])
    h = _house()
    c["model"] = (h.picture_safety_net() if hasattr(h, "picture_safety_net") else "") or h.picture_model("generate")   # the OpenAI call needs OpenAI's own id
    c.pop("overflow", None)                                   # the fal overflow door is retired (2026-10-26)
    return c


def _house():
    """machine/house.py — the Generative Model House as this machine reads it. A house that cannot be read is a STOP
    naming it, never a model written here (verify 2026-10-21 row 17, VIDEO-RULINGS V2)."""
    import importlib.util as _u
    try:
        sp = _u.spec_from_file_location("vm_do_house", HERE / "house.py")
        h = _u.module_from_spec(sp); sp.loader.exec_module(h)
        return h
    except (Exception, SystemExit) as e:                # noqa: BLE001
        raise SystemExit(f"the picture model comes from the Generative Model House and it could not be read: {e}") from None


def key_of() -> str | None:
    """OPENAI_API_KEY through the shared key loader (vp_keys) — never a
    crash, a clone with no key simply has none."""
    return vp_keys.key("OPENAI_API_KEY")


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


def backup_model() -> str:
    """The Model House's picture backup (pictures.backup, VIDEO-RULINGS V21 — Seedream on fal)."""
    return _house().picture_backup()


def _door() -> str:
    """The door the House gives pictures.generate: 'higgsfield' (the command line) once switched, 'openai' before."""
    if os.environ.get("IMAGE_DOOR_TEST_FORCE_OPENAI"):        # the legacy OpenAI-path unit tests only; never set in a run
        return "openai"
    try:
        return _house().picture_door("generate")
    except Exception:  # noqa: BLE001 — an old house without the helper: the OpenAI path below
        return "openai"


def _via_image_engine(prompt, references, out, dry_run=False, mask=None, aspect="9:16") -> dict:
    """A picture through the image engine's ladder (tools/image-production): GPT Image 2.5 on the Higgsfield command
    line, one more try, Seedream 5 Pro when GPT refuses, Nano Banana Pro, then OpenAI direct as the last rung. Replaces this
    file's own OpenAI call, its fal overflow and its fal Seedream backup (2026-10-26). The record says which rung made it."""
    root = str(Path(__file__).resolve().parents[2] / "image-production")
    if root not in sys.path:
        sys.path.append(root)
    from image_production import providers as PR, route as R
    t = R.table()
    name = "gpt-image-edit" if references else "gpt-image-person"
    entry = t["models"][name]
    refs = [Path(r) for r in references or []]
    if mask:
        print("  note: the Higgsfield door has no mask; this is made as an ordinary edit "
              "(name what must not change in the prompt)", file=sys.stderr)
    if dry_run:                                        # a dry run needs no Higgsfield login: the quote is shown when it can be had
        credits, why = None, None
        if entry.get("provider") == "higgsfield":
            try:
                credits = PR.higgsfield_cost(entry, prompt, refs, aspect)
            except PR.ProviderError as ex:
                why = str(ex)[:160]
        print(json.dumps({"door": entry.get("provider"), "model": entry.get("vendor_model"), "params": entry.get("params"),
                          "references": [str(r) for r in refs], "credits": credits, "quote_unavailable": why}, indent=1))
        return {"file": None, "model": entry.get("vendor_model"), "request_id": None, "usage": None}
    rungs = R.rungs(name, entry, t)
    try:
        rec = PR.generate_ladder(rungs, prompt, refs, Path(out), aspect)
    except PR.ProviderError:
        # A SWIPE FRAME THE FILTER REFUSES (2026-10-09): the sharp frame is a composition guide only; ask once more without it
        kept = [r for r in refs if "/framemap/frames/" not in str(r)]
        if len(kept) == len(refs):
            raise
        print("  note: every model refused this picture with the swipe frame — sent once more without it", file=sys.stderr)
        rec = PR.generate_ladder(rungs, prompt, kept, Path(out), aspect)
    if rec.get("made_by") != rungs[0]["name"]:
        print(f"  note: made on the {rec['made_by']} rung ({rec.get('model')})", file=sys.stderr)
    return {"file": rec["file"], "model": rec.get("model"), "request_id": rec.get("request_id"), "usage": rec.get("usage"),
            "door": rec.get("provider"), "made_by": rec["made_by"], "ladder": rec["ladder"]}


def generate(prompt: str, references: list[Path], out: Path, transport=None,
             key: str | None = None, dry_run: bool = False, mask: Path | None = None,
             overrides: dict | None = None, format_id: str | None = None, backup_transport=None) -> dict:
    """Edit (references given) or generate (none) — see module docstring. A picture GPT Image still refuses
    (moderation_blocked) is made on the house backup (`_backup`)."""
    if transport is None and _door() == "higgsfield":
        # Carry the caller's frame size through the routed provider door.
        size = (overrides or {}).get("size")
        aspect = "9:16"
        if size:
            from math import gcd
            match = re.fullmatch(r"(\d+)x(\d+)", str(size))
            if not match:
                raise ValueError(f"invalid image size: {size!r}")
            width, height = map(int, match.groups())
            if not width or not height:
                raise ValueError("image dimensions must be positive")
            divisor = gcd(width, height)
            aspect = f"{width // divisor}:{height // divisor}"
        return _via_image_engine(prompt, references, out, dry_run=dry_run, mask=mask, aspect=aspect)
    transport = transport or http_transport
    k = key if key is not None else key_of()
    if not dry_run and not k:
        raise SystemExit("no OPENAI_API_KEY — set it in the environment or the Keychain vault")

    c = cfg()
    model = c["model"]
    params = dict(c.get("params") or {})
    # THE FORMAT PLAYBOOK (the owner, 2026-10-10: one specialised workflow per kind of ad) sets the picture SIZE only;
    # the model is always the Model House's and a playbook never lowers the quality (V17, P56, 2026-10-21). A caller's
    # explicit `overrides` may set the SIZE only — the house quality always wins (P64, VIDEO-RULINGS V17).
    ov = {}
    if format_id:
        try:
            ov.update(_load("playbook").picture_overrides(format_id))
        except Exception:
            ov = {}
    ov.update({k2: v for k2, v in (overrides or {}).items() if v is not None})
    if ov.get("quality") and ov["quality"] != params.get("quality"):
        print(f"  note: a caller asked for quality {ov['quality']!r} — the house quality "
              f"{params.get('quality')!r} is sent (V17)", file=sys.stderr)
    if ov.get("size"):
        params["size"] = ov["size"]

    if references:
        boundary = _boundary()
        fields = {"model": model, "prompt": prompt, **{k2: str(v) for k2, v in params.items()}}
        files = [("image[]", Path(r)) for r in references]
        if mask:
            # transparent pixels of the mask are what the edit may change; opaque ones are kept (applies to image 1)
            files.append(("mask", Path(mask)))
        headers = {"Authorization": f"Bearer {k or ''}",
                   "Content-Type": f"multipart/form-data; boundary={boundary}"}
        url = c["images_edit"]
        if dry_run:
            print(json.dumps({"method": "POST", "url": url, "headers": _redacted(headers),
                              "fields": fields, "files": [str(p) for _, p in files]}, indent=1))
            return {"file": None, "model": model, "request_id": None, "usage": None}
        body = _multipart_body(fields, files, boundary)
        status, resp_headers, resp_body = transport("POST", url, headers, body)
        # THE PER-MINUTE LIMIT (found 2026-09-23 building the cast: 5 input
        # images a minute on this org). A 429 waits and asks again — a run of
        # thirty frames must not die halfway on a rate limit.
        # THE OVERFLOW DOOR (2026-10-10, the owner: "trigger image creation on a few
        # different platforms at one time to distribute the work"): the same model,
        # sold by fal, takes the picture the moment OpenAI says slow down — no wait.
        for _ in range(15):
            if status != 429:
                break
            import time as _t
            _t.sleep(20)
            status, resp_headers, resp_body = transport("POST", url, headers, body)
        if status == 400 and b"invalid_input_fidelity_model" in resp_body and "input_fidelity" in fields:
            # Learned live 2026-09-18: the 2.5 models do not take input_fidelity
            # at all (it was a 2.x edits parameter). Send the same edit without
            # it rather than fail the frame; the registry notes it per model.
            print(f"  note: {model} does not take input_fidelity — sent without it", file=sys.stderr)
            fields.pop("input_fidelity")
            body = _multipart_body(fields, files, boundary)
            status, resp_headers, resp_body = transport("POST", url, headers, body)
        if status == 400 and b"moderation_blocked" in resp_body and any("/framemap/frames/" in str(p) for _, p in files):
            # A SWIPE FRAME THE FILTER REFUSES (2026-10-09, a BRAND-A shirtless mirror selfie refused three times):
            # the sharp swipe frame is a composition guide only, and a real stranger's bare body in it can trip the
            # output filter whatever the prompt says. Ask once more without it; our cast, looks and sets still lead.
            files = [(n, p) for n, p in files if "/framemap/frames/" not in str(p)]
            print("  note: the safety filter refused this picture with the swipe frame — sent once more without it",
                  file=sys.stderr)
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

    if status == 400 and b"moderation_blocked" in (resp_body or b""):
        # still refused: this legacy OpenAI path has no backup of its own; the picture ladder (tools/image-production:
        # GPT Image on Higgsfield, Seedream, Nano Banana Pro, then OpenAI) is what makes a refused picture
        raise RuntimeError("OpenAI refused this picture (moderation_blocked); the picture ladder in tools/image-production "
                           "is the path that moves to the next model")
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
    ap.add_argument("--format", dest="format_id", help="read quality/size/model from this format's playbook")
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        result = generate(a.prompt, [Path(r) for r in a.refs], Path(a.out), dry_run=a.dry_run,
                          format_id=a.format_id)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    if not a.dry_run:
        print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
