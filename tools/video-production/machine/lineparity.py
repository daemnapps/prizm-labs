#!/usr/bin/env python3
"""
lineparity.py — every talking clip is transcribed and checked against the
line it was supposed to say. the owner, 2026-09-18: a talking clip from one door
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
is PASS; below it, FLAG; and a clip whose line's last words are not heard
at its end is CUT_OFF whatever its match (the owner, 2026-09-23: a clip that
stops mid-line is made again, never edited around) — written into `<run>/verdicts.json[item]["parity"]`
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
vp_keys = _load("vp_keys")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text())


def key_of() -> str | None:
    """ELEVENLABS_API_KEY: env first, then the Keychain vault — never a
    crash, a teammate's clone with neither simply has no key."""
    return vp_keys.key("ELEVENLABS_API_KEY")


def threshold_of() -> float:
    reg = platform.registry()
    gate = ((reg.get("gates") or {}).get("line_parity") or {})
    return gate.get("threshold", DEFAULT_THRESHOLD)


# --------------------------------------------------------------- the words

def normalize(text: str) -> list[str]:
    # the transcriber tags sounds in brackets ([singing], [laughs], [outro music]) —
    # they are not words, and must never count against a line's ending
    text = re.sub(r"\[[^\]]*\]", " ", text or "").lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def spoken(line: str) -> str:
    """Only the words a person says: a speaker label (`NOVA:`) and a stage
    direction in brackets are not heard, so they are not compared."""
    line = re.sub(r"\([^)]*\)", " ", line or "")
    line = re.sub(r"(^|[\s\"“])[A-Z][A-Z0-9 .'-]{1,30}:\s", " ", line)
    return line


_spoken_numbers = None


def say_numbers(text: str) -> str:
    """Every figure in words, by the one table (spoken_numbers.py /
    spoken-rules.json). A text with no figures comes back unchanged."""
    global _spoken_numbers
    if _spoken_numbers is None:
        _spoken_numbers = _load("spoken_numbers")
    return _spoken_numbers.say(text or "")


def compare(heard: str, line: str) -> float:
    return difflib.SequenceMatcher(None, normalize(heard), normalize(spoken(line))).ratio()


ENDING_WORDS = 3   # the last words of the line that must be heard, in order
ENDING_REACH = 4   # how far from the end of what was heard they may sit


def ending_heard(heard: str, line: str, n: int = ENDING_WORDS, reach: int = ENDING_REACH) -> bool:
    """Did the clip get to the END of its line? the owner, 2026-09-23: a clip that
    stops mid-line is an error — it is made again, never edited around. The
    overall match cannot see it: a sixteen-word line can lose "is a cop out"
    and still score over 0.85. So the line's last words must be heard, in
    order, at the end of what the clip says (a word may be misheard a little)."""
    want = normalize(spoken(line))[-n:]
    got = normalize(heard)
    if not want:
        return True
    tail = got[-(len(want) + reach):]
    i = 0
    for w in tail:
        if i < len(want) and difflib.SequenceMatcher(None, w, want[i]).ratio() >= 0.75:
            i += 1
    return i == len(want)


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
    # figures are compared as the words they are said as (spoken_numbers,
    # 2026-09-23): the line may say "$29" and the transcriber "twenty-nine
    # dollars", or the other way round — the same rules turn both into words
    h_cmp, l_cmp = say_numbers(heard), spoken(say_numbers(line))
    match = round(compare(h_cmp, l_cmp), 4)
    threshold = threshold_of()
    ending = ending_heard(h_cmp, l_cmp)
    # CUT_OFF outranks a good match: the line did not finish, so the clip is
    # made again (the remake step) — it is never a ceiling that ships flagged.
    # Wrong words altogether stay a FLAG; CUT_OFF is the right words that
    # stop short — what was heard matches the START of the line.
    got, want = normalize(h_cmp), normalize(l_cmp)
    starts_right = bool(got) and difflib.SequenceMatcher(None, got, want[:len(got) + 2]).ratio() >= 0.75
    if not ending and starts_right:
        verdict = "CUT_OFF"
    else:
        verdict = "PASS" if (match >= threshold and ending) else "FLAG"
    return {"heard": heard, "match": match, "ending_heard": ending, "verdict": verdict, "at": now()}


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
