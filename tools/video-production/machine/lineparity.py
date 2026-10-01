#!/usr/bin/env python3
"""
lineparity.py — every talking clip is transcribed and checked against the
line it was supposed to say. Damon, 2026-09-18: a talking clip from one door
lip-synced perfectly to the WRONG words — the model ignored the attached
audio and invented speech. Transcribing the clip and comparing it to the
line caught it (Higgsfield Seedance 2.5 and fal OmniHuman: 100% match; fal
Google Omni Flash: 10%). "Let's get optics on that" — this module is that
check, run before a clip can ship.

    python3 machine/lineparity.py --run <run-dir> <item-id> --clip <path> [--dry-run]

Looks the item up in `<run>/batches/*.json` (via `preflight.other_batches`),
joins the text of every line id in its own `lines` list (read from
`<run>/lines.json` — a value there may be a plain string or a dict carrying
`text`), transcribes the clip on the direct ElevenLabs API
(`speech-to-text`, model `scribe_v1`), and compares the two texts
(lowercased, punctuation stripped, split into words,
`difflib.SequenceMatcher.ratio()`). At or above the threshold (default
0.85, or `providers.json`'s own `gates.line_parity.threshold`) the verdict
is PASS; below it, FLAG — written into `<run>/verdicts.json[item]["parity"]`
through `preflight.py`'s own `verdict()`, so a FLAG accumulates the same
history every other layer does.

`key_of()`: `ELEVENLABS_API_KEY`, env first, then the Keychain vault
(`daemn_keys`) — never a crash, only ever `None` when neither has it. A real
(non dry-run) call with no key is a `SystemExit` naming it.

`transport(method, url, headers, body_bytes) -> (status, headers, body_bytes)`
is the one seam a real call goes through — the same shape every other direct
door in this machine uses (`direct_openai.py`, `direct_google.py`). The
multipart body (`model_id` field + the clip as `file`) is built by hand, the
same way `direct_openai.py` builds its `image[]` parts. `--dry-run` prints
the request — method, url, headers with the key redacted, the field, the
clip path — and writes nothing: no network call, no verdict.

No brand, model or person name lives in this file as a literal.
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

ELEVEN_STT = "https://api.elevenlabs.io/v1/speech-to-text"
STT_MODEL_ID = "scribe_v1"
DEFAULT_THRESHOLD = 0.85


def _load(name: str):
    """Load a sibling module by path, never by import — the same trick every
    other module here uses (platform.py shadows a stdlib name; the rest just
    follow suit so every module runs the same regardless of sys.path)."""
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


platform = _load("platform")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text())


def key_of() -> str | None:
    """ELEVENLABS_API_KEY: env first, then the Keychain vault — never a
    crash, a teammate's clone with neither simply has no key."""
    k = os.environ.get("ELEVENLABS_API_KEY")
    if k:
        return k
    try:
        import daemn_keys
        return daemn_keys.key("ELEVENLABS_API_KEY") or None
    except Exception:
        return None


def threshold_of() -> float:
    reg = platform.registry()
    gate = ((reg.get("gates") or {}).get("line_parity") or {})
    return gate.get("threshold", DEFAULT_THRESHOLD)


# --------------------------------------------------------------- the words

def normalize(text: str) -> list[str]:
    text = (text or "").lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def compare(heard: str, line: str) -> float:
    return difflib.SequenceMatcher(None, normalize(heard), normalize(line)).ratio()


def line_text_of(run: Path, item: dict) -> str:
    """Every line id the item's own `lines` claims, joined with a space. A
    `lines.json` entry may be a plain string or a dict carrying `text` (both
    shapes are on record in this repo's own fixtures) — either way, the
    words are what get compared."""
    lids = item.get("lines") or []
    if not lids:
        return ""
    lines = read_json(run / "lines.json", {}) or {}
    texts = []
    for lid in lids:
        val = lines.get(str(lid), "")
        if isinstance(val, dict):
            val = val.get("text", "")
        if val:
            texts.append(str(val))
    return " ".join(texts)


# ------------------------------------------------------------- the request

def _boundary() -> str:
    return f"----daemn-{uuid.uuid4().hex}"


def _multipart_body(fields: dict, files: list[tuple[str, Path]], boundary: str) -> bytes:
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
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def _redacted(headers: dict) -> dict:
    return {k: ("<redacted>" if k.lower() == "xi-api-key" else v) for k, v in headers.items()}


def check(clip: Path, line: str, transport=None, key: str | None = None,
          dry_run: bool = False) -> dict | None:
    """Transcribe `clip` on the direct ElevenLabs API and compare it to
    `line`. Returns `{"heard", "match", "verdict", "at"}`, or `None` on a
    dry run (which prints the request and calls nothing)."""
    transport = transport or http_transport
    k = key if key is not None else key_of()
    if not dry_run and not k:
        raise SystemExit("no ELEVENLABS_API_KEY — set it in the environment or the Keychain vault")

    clip = Path(clip)
    boundary = _boundary()
    fields = {"model_id": STT_MODEL_ID}
    files = [("file", clip)]
    headers = {"xi-api-key": k or "", "Content-Type": f"multipart/form-data; boundary={boundary}"}

    if dry_run:
        print(json.dumps({"method": "POST", "url": ELEVEN_STT, "headers": _redacted(headers),
                          "fields": fields, "file": str(clip)}, indent=1))
        return None

    body = _multipart_body(fields, files, boundary)
    status, _resp_headers, resp_body = transport("POST", ELEVEN_STT, headers, body)
    data = json.loads(resp_body.decode()) if resp_body else {}
    if status is not None and status >= 400:
        raise RuntimeError(f"ElevenLabs speech-to-text error {status}: {json.dumps(data)[:400]}")

    heard = data.get("text") or ""
    match = round(compare(heard, line), 4)
    threshold = threshold_of()
    verdict = "PASS" if match >= threshold else "FLAG"
    return {"heard": heard, "match": match, "verdict": verdict, "at": now()}


# ------------------------------------------------------------------ CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("item")
    ap.add_argument("--run", required=True)
    ap.add_argument("--clip", required=True)
    ap.add_argument("--dry-run", action="store_true")
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    run = Path(a.run).resolve()
    preflight = _load("preflight")

    items = preflight.other_batches(run)
    by_id = {str(it.get("id")): it for it in items}
    item = by_id.get(str(a.item))
    if item is None:
        print(f"no item {a.item!r} in {run / 'batches'}/*.json", file=sys.stderr)
        return 3

    line = line_text_of(run, item)
    if not line:
        print(f"item {a.item!r} carries no lines to check", file=sys.stderr)
        return 3

    clip = Path(a.clip)
    if not a.dry_run and not clip.is_file():
        print(f"no such clip: {clip}", file=sys.stderr)
        return 3

    try:
        result = check(clip, line, dry_run=a.dry_run)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2

    if a.dry_run:
        return 0

    preflight.verdict(run, a.item, "parity", result)
    print(f"heard: {result['heard']!r}")
    print(f"match: {result['match']}")
    print(f"verdict: {result['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
