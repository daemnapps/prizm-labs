#!/usr/bin/env python3
"""
omni.py — the talking beat on the controlled-Omni recipe, as one call.

Damon's 2026-09-18 ruling, after watching the same still + line through
three doors: "fal Omni came out the best for what I need and obviously it's
cheaper." The recipe he ruled the day before ("we should be able to control
this"), registered as `recipes.controlled_omni` in providers.json:

    1. Omni on fal, the approved still as the first frame, THE LINE WRITTEN
       INTO THE PROMPT in quotes — Omni performs it natively (it has no audio
       input at all; anything attached is silently dropped).
    2. line parity: transcribe the clip, ≥ threshold or FLAG.
    3. ElevenLabs speech-to-speech: the clip's own audio, re-voiced into the
       character's voice_id. Timing intact, so the lips still fit.
    4. ffmpeg: video stream copied untouched, the new audio muxed in.
    5. line parity again on the swapped clip — it must still say the line.

Every slug, URL, template and default comes from providers.json
(`direct.omni`, `direct.elevenlabs`); this file names none.

    python3 machine/omni.py talk "<line>" --still <png> --voice <voice_id> --out <mp4> [--seconds 6] [--dry-run]

`talk(line, still, voice_id, out, seconds, prompt_extra, ...)` returns
`{file, model, request_id, parity_native, parity_final, usage}`; on a FLAG
it still returns the clip (a ceiling ships FLAGGED, never re-rolled) with
the verdicts on the record for `record` to write.

Keys: FAL_KEY and ELEVENLABS_API_KEY — env first, then the Keychain vault.
`fal_transport(method, url, body_dict, headers) -> dict` and
`download(url, dest)` are the fal seams (providers_fal.py's shape);
`eleven_transport(method, url, headers, body_bytes) -> (status, headers, bytes)`
is the ElevenLabs seam (lineparity.py's shape); `run(cmd)` is ffmpeg's.
`--dry-run` prints every request (keys redacted, media elided) and writes
nothing.

No brand, model or person name lives in this file as a literal.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import mimetypes
import os
import shutil
import subprocess
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
lineparity = _load("lineparity")
providers_fal = _load("providers_fal")


def cfg() -> dict:
    return platform.registry()["direct"]["omni"]


def eleven_cfg() -> dict:
    return platform.registry()["direct"]["elevenlabs"]


def fal_key_of() -> str | None:
    k = os.environ.get("FAL_KEY")
    if k:
        return k
    try:
        import daemn_keys
        return daemn_keys.key("FAL_KEY") or None
    except Exception:
        return None


def ffmpeg_path() -> str:
    c = cfg()
    for cand in [c.get("ffmpeg"), shutil.which("ffmpeg"), "/opt/homebrew/bin/ffmpeg"]:
        if cand and Path(cand).is_file():
            return cand
    raise SystemExit("ffmpeg not found — the recipe's remux step needs it")


def run_cmd(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def data_url(path: Path) -> str:
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode() if path.is_file() else ""
    return f"data:{mime};base64,{b64}"


# ---------------------------------------------------------------- step 1

def omni_prompt(line: str, extra: str = "") -> str:
    """The registry's template with the line dropped in — the line is the
    only thing Omni is told to say."""
    tpl = cfg()["prompt_template"]
    text = tpl.replace("{line}", line.strip())
    if extra:
        text = text.rstrip() + " " + extra.strip()
    return text


def omni_submit(prompt: str, still: Path, seconds: int, out: Path, transport=None,
                download=None, key: str | None = None, dry_run: bool = False,
                resolution: str | None = None, aspect_ratio: str | None = None) -> dict:
    transport = transport or providers_fal.http_transport
    download = download or providers_fal.fetch
    c = cfg()
    lo, hi = c["seconds_range"]
    body = {"prompt": prompt, "image_url": data_url(still),
            "duration": int(min(max(seconds, lo), hi)),
            "aspect_ratio": aspect_ratio or c["defaults"]["aspect_ratio"],
            "resolution": resolution or c["defaults"]["resolution"]}
    slug = c["model"]
    if dry_run:
        shown = dict(body); shown["image_url"] = shown["image_url"][:30] + "…<elided>"
        print(json.dumps({"POST": f"{providers_fal.QUEUE}/{slug}", "body": shown}, indent=2))
        return {"model": slug, "file": None, "request_id": None}
    k = key if key is not None else fal_key_of()
    if not k:
        raise SystemExit("no FAL_KEY — set it in the environment or the Keychain vault")
    sub = providers_fal.submit(slug, body, k, transport)
    res = providers_fal.wait(sub["status_url"], sub["response_url"], k, transport, slug)
    urls = providers_fal.media_urls(res)
    if not urls:
        raise SystemExit(f"Omni answered with no media: {json.dumps(res)[:400]}")
    out.parent.mkdir(parents=True, exist_ok=True)
    download(urls[0], out)
    return {"model": slug, "file": str(out), "request_id": sub.get("request_id"), "url": urls[0]}


# ---------------------------------------------------------------- step 3

def _multipart(fields: dict, files: list[tuple[str, Path, str]], boundary: str) -> bytes:
    body = b""
    for k, v in fields.items():
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
    for k, p, mime in files:
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{p.name}\"\r\n"
                 f"Content-Type: {mime}\r\n\r\n").encode() + p.read_bytes() + b"\r\n"
    return body + f"--{boundary}--\r\n".encode()


def revoice(clip: Path, voice_id: str, out_audio: Path, transport=None, key: str | None = None,
            dry_run: bool = False) -> Path:
    """The clip's own audio → ElevenLabs speech-to-speech → the character's
    voice. Returns the new audio file."""
    transport = transport or lineparity.http_transport
    e = eleven_cfg()
    url = e["speech_to_speech"].format(voice_id=voice_id)
    model_id = e["sts_model_id"]
    src_audio = out_audio.with_name(out_audio.stem + "-omni-native.mp3")
    if dry_run:
        print(json.dumps({"ffmpeg": f"extract audio {clip.name} -> {src_audio.name}",
                          "POST": url, "fields": {"model_id": model_id}, "file": src_audio.name}, indent=2))
        return out_audio
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    run_cmd([ffmpeg_path(), "-y", "-i", str(clip), "-vn", "-acodec", "libmp3lame", "-q:a", "2", str(src_audio)])
    k = key if key is not None else lineparity.key_of()
    if not k:
        raise SystemExit("no ELEVENLABS_API_KEY — set it in the environment or the Keychain vault")
    boundary = lineparity._boundary()
    body = _multipart({"model_id": model_id, "remove_background_noise": "true"},
                      [("audio", src_audio, "audio/mpeg")], boundary)
    headers = {"xi-api-key": k, "Content-Type": f"multipart/form-data; boundary={boundary}",
               "Accept": "audio/mpeg"}
    status, _h, raw = transport("POST", url, headers, body)
    if status is None or status >= 400:
        raise SystemExit(f"ElevenLabs speech-to-speech error {status}: {raw[:300]!r}")
    out_audio.write_bytes(raw)
    return out_audio


# ---------------------------------------------------------------- step 4

def remux(clip: Path, audio: Path, out: Path, dry_run: bool = False) -> Path:
    if dry_run:
        print(json.dumps({"ffmpeg": f"remux {clip.name} + {audio.name} -> {out.name} (video copied)"}, indent=2))
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    run_cmd([ffmpeg_path(), "-y", "-i", str(clip), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)])
    return out


# ------------------------------------------------------------ silent motion

def motion(prompt: str, still: Path, out: Path, seconds: int | None = None,
           fal_transport=None, download=None, fal_key: str | None = None,
           dry_run: bool = False, resolution: str | None = None, aspect_ratio: str | None = None) -> dict:
    """A cutaway or a silent scene: the still animated on the same door, no
    line, and whatever sound Omni invents stripped — the cut carries the
    sound (Damon 2026-09-18: nothing in the chain needs the Higgsfield MCP
    any more). The registry's `silent_suffix` tells Omni nobody speaks."""
    still, out = Path(still), Path(out)
    c = cfg()
    seconds = seconds or c["defaults"]["seconds"]
    text = prompt.rstrip() + " " + (c.get("silent_suffix") or "")
    work = out.parent / f"{out.stem}-omni"
    native = work / f"{out.stem}-native.mp4"
    res = omni_submit(text, still, seconds, native, transport=fal_transport, download=download,
                      key=fal_key, dry_run=dry_run, resolution=resolution, aspect_ratio=aspect_ratio)
    result = {"model": res["model"], "request_id": res.get("request_id"), "recipe": "omni_silent",
              "native": str(native)}
    if dry_run:
        print(json.dumps({"ffmpeg": f"strip audio {native.name} -> {out.name} (video copied)"}, indent=2))
        result["file"] = None
        return result
    out.parent.mkdir(parents=True, exist_ok=True)
    run_cmd([ffmpeg_path(), "-y", "-i", str(native), "-an", "-c:v", "copy", str(out)])
    result["file"] = str(out)
    return result


# ------------------------------------------------------------ the recipe

def talk(line: str, still: Path, voice_id: str, out: Path, seconds: int | None = None,
         prompt_extra: str = "", fal_transport=None, download=None, eleven_transport=None,
         fal_key: str | None = None, eleven_key: str | None = None, dry_run: bool = False,
         skip_parity: bool = False, resolution: str | None = None, aspect_ratio: str | None = None) -> dict:
    still, out = Path(still), Path(out)
    c = cfg()
    seconds = seconds or c["defaults"]["seconds"]
    work = out.parent / f"{out.stem}-omni"
    native = work / f"{out.stem}-native.mp4"

    prompt = omni_prompt(line, prompt_extra)
    res = omni_submit(prompt, still, seconds, native, transport=fal_transport, download=download,
                      key=fal_key, dry_run=dry_run, resolution=resolution, aspect_ratio=aspect_ratio)
    result = {"model": res["model"], "request_id": res.get("request_id"), "recipe": "controlled_omni",
              "native": str(native), "parity_native": None, "parity_final": None}
    if dry_run:
        revoice(native, voice_id, work / f"{out.stem}-voiced.mp3", transport=eleven_transport,
                key=eleven_key, dry_run=True)
        remux(native, work / f"{out.stem}-voiced.mp3", out, dry_run=True)
        result["file"] = None
        return result

    if not skip_parity:
        result["parity_native"] = lineparity.check(native, line, transport=eleven_transport, key=eleven_key)
    voiced = revoice(native, voice_id, work / f"{out.stem}-voiced.mp3", transport=eleven_transport,
                     key=eleven_key)
    remux(native, voiced, out)
    if not skip_parity:
        result["parity_final"] = lineparity.check(out, line, transport=eleven_transport, key=eleven_key)
    result["file"] = str(out)
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="the talking beat on the controlled-Omni recipe")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("talk")
    t.add_argument("line")
    t.add_argument("--still", required=True)
    t.add_argument("--voice", required=True, help="the character's ElevenLabs voice_id")
    t.add_argument("--out", required=True)
    t.add_argument("--seconds", type=int)
    t.add_argument("--extra", default="", help="performance notes appended to the prompt")
    t.add_argument("--dry-run", action="store_true")
    t.add_argument("--no-parity", action="store_true")
    m = sub.add_parser("motion")
    m.add_argument("prompt")
    m.add_argument("--still", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--seconds", type=int)
    m.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "motion":
        print(json.dumps(motion(a.prompt, Path(a.still), Path(a.out), seconds=a.seconds, dry_run=a.dry_run), indent=2))
        return 0
    res = talk(a.line, Path(a.still), a.voice, Path(a.out), seconds=a.seconds, prompt_extra=a.extra,
               dry_run=a.dry_run, skip_parity=a.no_parity)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
