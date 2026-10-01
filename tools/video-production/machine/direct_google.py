#!/usr/bin/env python3
"""
direct_google.py — the machine hand's two Gemini doors: Nano Banana Pro for
discrete edits, Lyria for the song (Damon's 2026-09-17 ruling). Every field
value (model id, imageConfig, safety categories, song model ids) comes from
`providers.json`'s own `direct.google` section — nothing here names a model.

    python3 machine/direct_google.py edit "<prompt>" --image <path> [--image <path> ...] --out <file> [--dry-run]
    python3 machine/direct_google.py song "<prompt>" --out-wav <file> --timing-out <file> [--model full|clip] [--dry-run]

`edit_image(prompt, images, out, transport=None, key=None, dry_run=False)`:
one `generateContent` call on the edit model, `inline_data` parts (base64)
for every image followed by a `text` part for the prompt,
`generationConfig.imageConfig` from the registry, `safetySettings` built
per-category at the registry's threshold. The first inline-data part in the
response is decoded straight to `out`.

`song(prompt, out_wav, timing_out, model="full", transport=None, key=None,
dry_run=False)`: one `generateContent` call on the named Lyria model
(`full` -> `lyria-3-pro-preview`, `clip` -> `lyria-3-clip-preview`),
no requested audio format (the API rejects `responseFormat.audio.mimeType`
values and answered MP3 on the first live run, 2026-09-18). Writes
the response's audio part to `out_wav` and its text part verbatim to
`timing_out`. Returns `{wav, timing, timed}` — `timed` is `True` only when
the text part carries an `[m:ss]`-style marker, because a timed lyric sheet
is *observed behaviour on this API, not a documented contract*
(`providers/research/lyria.md`) — check it every run, never assume it.

Key: `GEMINI_API_KEY`, env first, then the Keychain vault (`daemn_keys`) —
never a crash. Both calls raise `SystemExit` naming the key when a real
(non dry-run) call has none.

`transport(method, url, headers, body_bytes) -> (status, headers, body_bytes)`
is the one seam every real call goes through, matching direct_openai.py's
shape. `--dry-run` prints the request (key redacted) and writes nothing.

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
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


platform = _load("platform")

TIME_MARKER = re.compile(r"\[\d{1,3}:\d{2}(?:\.\d+)?\]")
BLOCK_LEVEL = re.compile(r"BLOCK_[A-Z_]+")
DEFAULT_THRESHOLD = "BLOCK_ONLY_HIGH"


def cfg() -> dict:
    return platform.registry()["direct"]["google"]


def key_of() -> str | None:
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k
    try:
        import daemn_keys
        return daemn_keys.key("GEMINI_API_KEY") or None
    except Exception:
        return None


def http_transport(method: str, url: str, headers: dict, body: bytes | None):
    """The real network call — the default `transport`."""
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def _redacted(headers: dict) -> dict:
    return {k: ("<redacted>" if k.lower() == "x-goog-api-key" else v) for k, v in headers.items()}


def safety_settings(c: dict) -> list[dict]:
    threshold_match = BLOCK_LEVEL.search(c.get("safety") or "")
    threshold = threshold_match.group(0) if threshold_match else DEFAULT_THRESHOLD
    categories = c.get("safety_categories") or []
    return [{"category": cat, "threshold": threshold} for cat in categories]


def _url_for(model: str, c: dict) -> str:
    return c["generate_content"].format(model=model)


def _parts_of(data: dict) -> list[dict]:
    candidates = data.get("candidates") or []
    if not candidates:
        return []
    content = candidates[0].get("content") or {}
    return content.get("parts") or []


def _inline_data(part: dict) -> dict | None:
    # the REST API renders proto field names as camelCase; check both since
    # the request side is documented as snake_case (providers/research/lyria.md)
    return part.get("inlineData") or part.get("inline_data")


def edit_image(prompt: str, images: list[Path], out: Path, transport=None,
                key: str | None = None, dry_run: bool = False) -> dict:
    transport = transport or http_transport
    k = key if key is not None else key_of()
    if not dry_run and not k:
        raise SystemExit("no GEMINI_API_KEY — set it in the environment or the Keychain vault")

    c = cfg()
    model = c["image_model"]
    parts = []
    for img in images:
        img = Path(img)
        mime = mimetypes.guess_type(img.name)[0] or "image/png"
        data_b64 = base64.b64encode(img.read_bytes()).decode() if img.is_file() else ""
        parts.append({"inline_data": {"mime_type": mime, "data": data_b64}})
    parts.append({"text": prompt})

    body_obj = {
        "contents": [{"parts": parts}],
        "generationConfig": {"imageConfig": c.get("image_config") or {}},
        "safetySettings": safety_settings(c),
    }
    url = _url_for(model, c)
    headers = {"x-goog-api-key": k or "", "Content-Type": "application/json"}
    if dry_run:
        dry_body = dict(body_obj)
        dry_body["contents"] = [{"parts": [
            {"inline_data": {"mime_type": p["inline_data"]["mime_type"], "data": "<base64 omitted>"}}
            if "inline_data" in p else p for p in parts]}]
        print(json.dumps({"method": "POST", "url": url, "headers": _redacted(headers),
                          "body": dry_body}, indent=1))
        return {"file": None, "model": model, "request_id": None, "usage": None}

    status, resp_headers, resp_body = transport("POST", url, headers, json.dumps(body_obj).encode())
    data = json.loads(resp_body.decode())
    if status is not None and status >= 400:
        raise RuntimeError(f"Gemini edit error {status}: {json.dumps(data)[:400]}")
    for part in _parts_of(data):
        inline = _inline_data(part)
        if inline and inline.get("data"):
            out = Path(out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(base64.b64decode(inline["data"]))
            request_id = resp_headers.get("x-request-id") or resp_headers.get("X-Request-Id")
            return {"file": str(out), "model": model, "request_id": request_id, "usage": data.get("usageMetadata")}
    raise RuntimeError(f"no inline image data in response: {json.dumps(data)[:400]}")


def song(prompt: str, out_wav: Path, timing_out: Path, model: str = "full",
         transport=None, key: str | None = None, dry_run: bool = False) -> dict:
    transport = transport or http_transport
    k = key if key is not None else key_of()
    if not dry_run and not k:
        raise SystemExit("no GEMINI_API_KEY — set it in the environment or the Keychain vault")

    c = cfg()
    song_models = c.get("song_models") or {}
    model_id = song_models.get(model)
    if not model_id:
        raise SystemExit(f"providers.json direct.google.song_models has no entry for {model!r}")

    body_obj = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {},
    }
    url = _url_for(model_id, c)
    headers = {"x-goog-api-key": k or "", "Content-Type": "application/json"}
    if dry_run:
        print(json.dumps({"method": "POST", "url": url, "headers": _redacted(headers),
                          "body": body_obj}, indent=1))
        return {"wav": None, "timing": None, "model": model_id, "timed": None}

    status, resp_headers, resp_body = transport("POST", url, headers, json.dumps(body_obj).encode())
    data = json.loads(resp_body.decode())
    if status is not None and status >= 400:
        raise RuntimeError(f"Gemini song error {status}: {json.dumps(data)[:400]}")

    out_wav, timing_out = Path(out_wav), Path(timing_out)
    audio_written = text_written = False
    text_seen = ""
    # docs warn ordering is not guaranteed ("you should not assume the
    # lyrics are always the first part") — walk every part rather than
    # assuming positions.
    for part in _parts_of(data):
        inline = _inline_data(part)
        if inline and inline.get("data") and not audio_written:
            # the API decides the container (it answered audio/mpeg on the
            # first live run, 2026-09-18, and rejects a requested mime type);
            # name the file by what actually came back
            mime = (inline.get("mime_type") or inline.get("mimeType") or "").lower()
            ext = {"audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/wav": ".wav",
                   "audio/x-wav": ".wav", "audio/ogg": ".ogg"}.get(mime)
            if ext and out_wav.suffix.lower() != ext:
                out_wav = out_wav.with_suffix(ext)
            out_wav.parent.mkdir(parents=True, exist_ok=True)
            out_wav.write_bytes(base64.b64decode(inline["data"]))
            audio_written = True
        elif part.get("text") and not text_written:
            text_seen = part["text"]
            timing_out.parent.mkdir(parents=True, exist_ok=True)
            timing_out.write_text(text_seen)
            text_written = True
    if not audio_written:
        raise RuntimeError(f"no inline audio data in response: {json.dumps(data)[:400]}")
    if not text_written:
        # a song with no text part at all still has no timing sheet to
        # write — record that plainly rather than leaving a stale file.
        timing_out.parent.mkdir(parents=True, exist_ok=True)
        timing_out.write_text("")
    timed = bool(TIME_MARKER.search(text_seen))
    return {"wav": str(out_wav), "timing": str(timing_out), "model": model_id, "timed": timed}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)

    e = sub.add_parser("edit")
    e.add_argument("prompt")
    e.add_argument("--image", action="append", default=[], dest="images")
    e.add_argument("--out", required=True)
    e.add_argument("--dry-run", action="store_true")

    s = sub.add_parser("song")
    s.add_argument("prompt")
    s.add_argument("--out-wav", required=True)
    s.add_argument("--timing-out", required=True)
    s.add_argument("--model", choices=["full", "clip"], default="full")
    s.add_argument("--dry-run", action="store_true")

    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        if a.verb == "edit":
            result = edit_image(a.prompt, [Path(p) for p in a.images], Path(a.out), dry_run=a.dry_run)
        else:
            result = song(a.prompt, Path(a.out_wav), Path(a.timing_out), model=a.model, dry_run=a.dry_run)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    if not a.dry_run:
        print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
