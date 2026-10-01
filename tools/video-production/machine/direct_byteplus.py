#!/usr/bin/env python3
"""
direct_byteplus.py — the machine hand's Seedance door: motion and the talking
beat on BytePlus ModelArk, direct (Damon's 2026-09-18 ruling: "let's just
set up BytePlus so we just have what we need" — the Higgsfield API is the
same model at a higher price). Every field value (model id, host, roles,
the talking prefix) comes from `providers.json`'s own `direct.byteplus`
section — nothing here names a model.

    python3 machine/direct_byteplus.py motion "<prompt>" --first <png> [--last <png>] --out <mp4> [--seconds 6] [--dry-run]
    python3 machine/direct_byteplus.py talking "<prompt>" --still <png> --audio <wav|mp3> --out <mp4> [--dry-run]
    python3 machine/direct_byteplus.py poll <task id> --out <mp4>

`motion(prompt, first, last, out, seconds, ...)`: one task with the still
as `first_frame` (and `last_frame` when given), `generate_audio` false —
silent by design, the cut carries the sound.

`talking(prompt, still, audio, out, ...)`: one task with the still and the
ElevenLabs line, roles from the registry (`talking_roles`), the registry's
`talking_prefix` in front of the prompt so the model knows @Image1 is the
face and @Audio1 is the words. Duration = the audio's length, rounded up
to the model's floor. `generate_audio` true (the line rides the output).
Whether the result says the line is not this file's call — `record` runs
line parity on every talking clip, the same as every other door.

Media travel as base64 data URLs (documented on the create-task page:
`data:image/png;base64,…`, `data:audio/wav;base64,…`) so nothing has to be
public. The docs cap the request body at 64 MB and say "do not use Base64
for large files" — a still and a 30 s line are nowhere near that.

Task lifecycle: POST /contents/generations/tasks → {id}; GET …/tasks/{id}
until `succeeded` (video at content.video_url, downloaded to `out`) or
`failed`./`cancelled`./`expired` (SystemExit with the API's own message).

Key: `BYTEPLUS_API_KEY` (an Ark API key), env first, then the Keychain
vault (`daemn_keys`) — never a crash. A real call with no key is a
`SystemExit` naming it.

`transport(method, url, headers, body_bytes) -> (status, headers, body_bytes)`
is the one seam every network call goes through, matching direct_openai.py
and direct_google.py. `--dry-run` prints the request (key redacted, media
elided) and writes nothing.

No brand, model or person name lives in this file as a literal.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import math
import mimetypes
import os
import struct
import sys
import time
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

KEY_NAME = "BYTEPLUS_API_KEY"
TERMINAL_BAD = ("failed", "cancelled", "canceled", "expired")


def cfg() -> dict:
    return platform.registry()["direct"]["byteplus"]


def key_of() -> str | None:
    k = os.environ.get(KEY_NAME)
    if k:
        return k
    try:
        import daemn_keys
        return daemn_keys.key(KEY_NAME) or None
    except Exception:
        return None


def http_transport(method: str, url: str, headers: dict, body: bytes | None):
    """The real network call — the default `transport`."""
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def _redacted(headers: dict) -> dict:
    return {k: ("Bearer <redacted>" if k.lower() == "authorization" else v)
            for k, v in headers.items()}


def _headers(key: str | None) -> dict:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {key or ''}"}


# ------------------------------------------------------------------ media

def data_url(path: Path, kind: str) -> str:
    """`data:<mime>;base64,…` for a local file. The docs want the subtype
    lowercase (`data:audio/wav;base64,…`, `data:image/png;base64,…`)."""
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or {"image": "image/png", "audio": "audio/wav"}[kind]
    if kind == "audio" and mime == "audio/x-wav":
        mime = "audio/wav"
    if kind == "audio" and mime == "audio/mpeg":
        mime = "audio/mp3"
    b64 = base64.b64encode(path.read_bytes()).decode() if path.is_file() else ""
    return f"data:{mime.lower()};base64,{b64}"


def audio_seconds(path: Path) -> float | None:
    """Length of a WAV from its header, or of an MP3 by a rough
    frame count. None when unreadable — the caller falls back to the
    registry's default."""
    path = Path(path)
    if not path.is_file():
        return None
    data = path.read_bytes()
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        i = 12
        byte_rate = None
        while i + 8 <= len(data):
            cid, size = data[i:i + 4], struct.unpack("<I", data[i + 4:i + 8])[0]
            if cid == b"fmt " and i + 24 <= len(data):
                byte_rate = struct.unpack("<I", data[i + 16:i + 20])[0]
            elif cid == b"data" and byte_rate:
                return size / byte_rate
            i += 8 + size + (size & 1)
        return None
    if path.suffix.lower() == ".mp3":
        # count MPEG-1 Layer III frames (CBR estimate; good enough to pick a
        # duration the line fits inside — the model rounds to whole seconds)
        i, frames, secs = 0, 0, 0.0
        if data[:3] == b"ID3":
            sz = data[6:10]
            i = 10 + ((sz[0] << 21) | (sz[1] << 14) | (sz[2] << 7) | sz[3])
        bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
        rates = [44100, 48000, 32000]
        while i + 4 <= len(data):
            if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
                br = bitrates[(data[i + 2] >> 4) & 0x0F] * 1000
                sr_i = (data[i + 2] >> 2) & 0x03
                if br and sr_i < 3:
                    sr = rates[sr_i]
                    pad = (data[i + 2] >> 1) & 0x01
                    flen = int(144 * br / sr) + pad
                    frames += 1
                    secs += 1152 / sr
                    i += max(flen, 4)
                    continue
            i += 1
        return secs if frames else None
    return None


# ------------------------------------------------------------------ calls

def _post_task(body: dict, transport, key: str | None, dry_run: bool) -> dict:
    c = cfg()
    url = c["create_task"]
    headers = _headers(key)
    if dry_run:
        shown = json.loads(json.dumps(body))
        for part in shown.get("content", []):
            for k in ("image_url", "audio_url", "video_url"):
                if k in part and isinstance(part[k], dict):
                    part[k]["url"] = part[k]["url"][:40] + "…<elided>"
        print(json.dumps({"POST": url, "headers": _redacted(headers), "body": shown}, indent=2))
        return {}
    status, _h, raw = transport("POST", url, headers, json.dumps(body).encode())
    try:
        data = json.loads(raw.decode() or "{}")
    except ValueError:
        data = {"raw": raw[:400].decode(errors="replace")}
    if status not in (200, 201) or not data.get("id"):
        raise SystemExit(f"BytePlus refused the task — HTTP {status}: {json.dumps(data)[:600]}")
    return data


def poll(task_id: str, transport=None, key: str | None = None,
         every: float = 5.0, timeout: float = 1800.0) -> dict:
    """GET the task until it settles. Returns the final task body."""
    transport = transport or http_transport
    c = cfg()
    url = c["get_task"].format(id=task_id)
    headers = _headers(key if key is not None else key_of())
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        status, _h, raw = transport("GET", url, headers, None)
        try:
            last = json.loads(raw.decode() or "{}")
        except ValueError:
            last = {"raw": raw[:400].decode(errors="replace")}
        state = str(last.get("status", "")).lower()
        if state == "succeeded":
            return last
        if state in TERMINAL_BAD:
            err = last.get("error") or last
            raise SystemExit(f"BytePlus task {task_id} ended {state}: {json.dumps(err)[:600]}")
        time.sleep(every)
    raise SystemExit(f"BytePlus task {task_id} still {last.get('status')!r} after {int(timeout)}s")


def download(url: str, out: Path, transport=None) -> Path:
    transport = transport or http_transport
    status, _h, raw = transport("GET", url, {}, None)
    if status != 200:
        raise SystemExit(f"could not download the clip — HTTP {status} from {url[:80]}")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    return out


def _finish(task: dict, out: Path, transport, key, dry_run) -> dict:
    if dry_run:
        return {"model": cfg()["model"], "file": None, "task_id": None, "usage": None}
    done = poll(task["id"], transport=transport, key=key)
    url = (done.get("content") or {}).get("video_url")
    if not url:
        raise SystemExit(f"BytePlus task {task['id']} succeeded with no video_url: {json.dumps(done)[:400]}")
    file_ = download(url, out, transport=transport)
    return {"model": done.get("model") or cfg()["model"], "file": str(file_),
            "task_id": task["id"], "usage": done.get("usage"),
            "seed": done.get("seed"), "video_url": url}


def _common(c: dict, seconds: int, resolution: str | None, ratio: str | None) -> dict:
    d = c["defaults"]
    return {
        "resolution": resolution or d["resolution"],
        "ratio": ratio or d["ratio"],
        "duration": int(seconds),
        "watermark": False,
        "output_format": d.get("output_format", "mp4"),
    }


def motion(prompt: str, first: Path, last: Path | None, out: Path, seconds: int = 5,
           resolution: str | None = None, ratio: str | None = None,
           transport=None, key: str | None = None, dry_run: bool = False) -> dict:
    """Silent motion from a still (and optionally a last frame)."""
    transport = transport or http_transport
    k = key if key is not None else key_of()
    if not dry_run and not k:
        raise SystemExit(f"no {KEY_NAME} — set it in the environment or the Keychain vault")
    c = cfg()
    roles = c["motion_roles"]
    content = [{"type": "text", "text": prompt},
               {"type": "image_url", "image_url": {"url": data_url(first, "image")}, "role": roles["first"]}]
    if last:
        content.append({"type": "image_url", "image_url": {"url": data_url(last, "image")}, "role": roles["last"]})
    lo, hi = c["seconds_range"]
    body = {"model": c["model"], "content": content, "generate_audio": False,
            **_common(c, min(max(int(seconds), lo), hi), resolution, ratio)}
    task = _post_task(body, transport, k, dry_run)
    return _finish(task, out, transport, k, dry_run)


def talking(prompt: str, still: Path, audio: Path, out: Path, seconds: int | None = None,
            resolution: str | None = None, ratio: str | None = None,
            transport=None, key: str | None = None, dry_run: bool = False) -> dict:
    """The talking beat: the still is the face, the audio is the words."""
    transport = transport or http_transport
    k = key if key is not None else key_of()
    if not dry_run and not k:
        raise SystemExit(f"no {KEY_NAME} — set it in the environment or the Keychain vault")
    c = cfg()
    roles = c["talking_roles"]
    lo, hi = c["seconds_range"]
    if seconds is None:
        length = audio_seconds(audio)
        seconds = math.ceil(length) if length else c["defaults"]["talking_seconds"]
    seconds = min(max(int(seconds), lo), hi)
    text = (c.get("talking_prefix") or "").rstrip() + (" " if c.get("talking_prefix") else "") + prompt
    content = [{"type": "text", "text": text},
               {"type": "image_url", "image_url": {"url": data_url(still, "image")}, "role": roles["image"]},
               {"type": "audio_url", "audio_url": {"url": data_url(audio, "audio")}, "role": roles["audio"]}]
    body = {"model": c["model"], "content": content, "generate_audio": True,
            **_common(c, seconds, resolution, ratio)}
    if c.get("talking_task_type"):
        body["omni_reference_task_type"] = c["talking_task_type"]
    task = _post_task(body, transport, k, dry_run)
    return _finish(task, out, transport, k, dry_run)


# -------------------------------------------------------------------- cli

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Seedance direct on BytePlus ModelArk — the machine hand's motion door")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("motion")
    m.add_argument("prompt")
    m.add_argument("--first", required=True)
    m.add_argument("--last")
    m.add_argument("--out", required=True)
    m.add_argument("--seconds", type=int, default=5)
    m.add_argument("--resolution")
    m.add_argument("--ratio")
    m.add_argument("--dry-run", action="store_true")

    t = sub.add_parser("talking")
    t.add_argument("prompt")
    t.add_argument("--still", required=True)
    t.add_argument("--audio", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--seconds", type=int)
    t.add_argument("--resolution")
    t.add_argument("--ratio")
    t.add_argument("--dry-run", action="store_true")

    q = sub.add_parser("poll")
    q.add_argument("task_id")
    q.add_argument("--out", required=True)

    a = p.parse_args(argv)
    if a.cmd == "motion":
        res = motion(a.prompt, Path(a.first), Path(a.last) if a.last else None, Path(a.out),
                     seconds=a.seconds, resolution=a.resolution, ratio=a.ratio, dry_run=a.dry_run)
    elif a.cmd == "talking":
        res = talking(a.prompt, Path(a.still), Path(a.audio), Path(a.out), seconds=a.seconds,
                      resolution=a.resolution, ratio=a.ratio, dry_run=a.dry_run)
    else:
        done = poll(a.task_id)
        url = (done.get("content") or {}).get("video_url")
        res = {"file": str(download(url, Path(a.out))) if url else None, "task_id": a.task_id,
               "usage": done.get("usage")}
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
