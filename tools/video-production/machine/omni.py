#!/usr/bin/env python3
"""
omni.py — the talking beat on the controlled-Omni recipe, as one call.

the owner's 2026-09-18 ruling, after watching the same still + line through
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
vp_keys = _load("vp_keys")


def cfg() -> dict:
    return platform.registry()["direct"]["omni"]


def eleven_cfg() -> dict:
    return platform.registry()["direct"]["elevenlabs"]


def fal_key_of() -> str | None:
    return vp_keys.key("FAL_KEY")


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


# ---------------------------------------------------------- the Google door

# the voice swap's own output: ElevenLabs' best mp3 (2026-10-03: the default 128 kbps plus
# noise removal on an already-compressed input made the voices sound grainy)
STS_FORMAT = "mp3_44100_192"
# THE CRISP FINISH (the owner 2026-10-03, picked by ear: "version a actually sounds like the avatar
# looks"): the cast voices measured dull next to the clip model's own sound (-19 dB vs -12 in the
# 4-10 kHz band, -26 vs -17 above 10 kHz); this lifts them to match. Applied to every swapped voice.
CRISP = "highshelf=f=3500:g=9:t=s:width=0.6,highshelf=f=9000:g=4,loudnorm=I=-16:TP=-1.5:LRA=11"


def crisp(audio, out):
    run_cmd([ffmpeg_path(), "-y", "-i", str(audio), "-af", CRISP, "-ar", "44100", str(out)])
    return Path(out)

GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GOOGLE_MODEL = "gemini-omni-1.1-flash"
# Google's own price sheet, read 2026-10-03 (ai.google.dev/gemini-api/docs/pricing):
# output $17.50 / 1M tokens at 1931 (360p) · 5792 (720p) · 8688 (1080p) tokens a second;
# input $1.50 / 1M tokens, 1120 tokens an image
GOOGLE_TOKENS_PER_S = {"360p": 1931, "720p": 5792, "1080p": 8688, "4k": 17376}
GOOGLE_OUT_PER_M, GOOGLE_IN_PER_M, GOOGLE_IMAGE_TOKENS = 17.50, 1.50, 1120


def _find(o, pred):
    if isinstance(o, dict):
        if pred(o):
            return o
        for v in o.values():
            r = _find(v, pred)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = _find(v, pred)
            if r is not None:
                return r
    return None


def google_submit(prompt: str, still: Path, out: Path, resolution: str = "360p", aspect_ratio: str = "9:16",
                  end_still: Path | None = None, key: str | None = None, transport=None) -> dict:
    """Omni straight from Google (the Interactions API): the picture(s) + the words in, the
    clip back inline. Returns the clip, the seconds it took and its cost from Google's sheet."""
    import time, urllib.request
    k = key or _google_key()
    imgs = [still] + ([end_still] if end_still else [])
    body = {"model": GOOGLE_MODEL,
            "input": [{"type": "image", "data": base64.b64encode(Path(i).read_bytes()).decode(),
                       "mime_type": mimetypes.guess_type(str(i))[0] or "image/png"} for i in imgs]
            + [{"type": "text", "text": prompt}],
            "response_format": {"type": "video", "resolution": resolution, "aspect_ratio": aspect_ratio}}
    t = time.time()
    req = urllib.request.Request(f"{GOOGLE_URL}?key={k}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        res = json.loads(r.read())
    vid = _find(res, lambda d: d.get("type") == "video" or str(d.get("mime_type", "")).startswith("video/"))
    if not vid:
        raise SystemExit(f"Google Omni answered with no video: {json.dumps(res)[:400]}")
    out.parent.mkdir(parents=True, exist_ok=True)
    if vid.get("data"):
        out.write_bytes(base64.b64decode(vid["data"]))
    else:
        urllib.request.urlretrieve(vid.get("uri") or vid.get("url"), out)
    secs = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(out)], capture_output=True, text=True).stdout.strip() or 0)
    usage = res.get("usage") or _find(res, lambda d: "total_tokens" in d or "output_tokens" in d) or {}
    est = secs * GOOGLE_TOKENS_PER_S.get(resolution, 0) / 1e6 * GOOGLE_OUT_PER_M + \
        len(imgs) * GOOGLE_IMAGE_TOKENS / 1e6 * GOOGLE_IN_PER_M
    return {"model": GOOGLE_MODEL, "file": str(out), "request_id": res.get("id"), "took_s": round(time.time() - t, 1),
            "seconds": round(secs, 2), "usd": round(est, 4), "usage": usage}


def _google_key():
    return vp_keys.key("GEMINI_API_KEY")


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
    url = e["speech_to_speech"].format(voice_id=voice_id) + "?output_format=" + STS_FORMAT
    model_id = e["sts_model_id"]
    src_audio = out_audio.with_name(out_audio.stem + "-omni-native.wav")
    if dry_run:
        print(json.dumps({"ffmpeg": f"extract audio {clip.name} -> {src_audio.name}",
                          "POST": url, "fields": {"model_id": model_id}, "file": src_audio.name}, indent=2))
        return out_audio
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    run_cmd([ffmpeg_path(), "-y", "-i", str(clip), "-vn", "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(src_audio)])
    k = key if key is not None else lineparity.key_of()
    if not k:
        raise SystemExit("no ELEVENLABS_API_KEY — set it in the environment or the Keychain vault")
    boundary = lineparity._boundary()
    body = _multipart({"model_id": model_id, "remove_background_noise": "false"},
                      [("audio", src_audio, "audio/wav")], boundary)
    headers = {"xi-api-key": k, "Content-Type": f"multipart/form-data; boundary={boundary}",
               "Accept": "audio/mpeg"}
    status, _h, raw = transport("POST", url, headers, body)
    if status is None or status >= 400:
        raise SystemExit(f"ElevenLabs speech-to-speech error {status}: {raw[:300]!r}")
    raw_out = out_audio.with_name(out_audio.stem + "-uncrisp" + out_audio.suffix)
    raw_out.write_bytes(raw)
    crisp(raw_out, out_audio)
    return out_audio


def revoice_lines(clip: Path, parts: list[dict], out_audio: Path, key: str | None = None) -> Path:
    """More than one person talks in the clip (the owner 2026-10-03: the doctor's scenes have
    talking): Omni says every line in its own voices; each line's stretch of the audio is
    found by the transcript's word timings and swapped into THAT person's voice
    (ElevenLabs speech-to-speech), then laid back at the same times. `parts` in order:
    [{"line": ..., "voice": voice_id}, ...]."""
    import tempfile
    k = key or lineparity.key_of()
    clip, out_audio = Path(clip), Path(out_audio)
    work = Path(tempfile.mkdtemp())
    src = work / "native.wav"
    run_cmd([ffmpeg_path(), "-y", "-i", str(clip), "-vn", "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(src)])
    boundary = lineparity._boundary()
    body = lineparity._multipart_body({"model_id": lineparity.STT_MODEL_ID, "timestamps_granularity": "word"},
                                      [("file", src)], boundary)
    st, _h, raw = lineparity.http_transport("POST", lineparity.ELEVEN_STT,
                                            {"xi-api-key": k, "Content-Type": f"multipart/form-data; boundary={boundary}"}, body)
    words = [w for w in json.loads(raw.decode()).get("words", []) if w.get("type") == "word"]
    # each line takes as many heard words as it has words; its stretch starts at its first one
    starts, i = [], 0
    for p_ in parts:
        starts.append(words[i]["start"] if i < len(words) else (words[-1]["end"] if words else 0.0))
        i += len(lineparity.normalize(lineparity.spoken(p_["line"])))
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                                 capture_output=True, text=True).stdout.strip() or 0)
    segs = []
    for n, p_ in enumerate(parts):
        a = 0.0 if n == 0 else max(0.0, starts[n] - 0.08)
        z = total if n == len(parts) - 1 else max(a, starts[n + 1] - 0.08)
        seg = work / f"seg{n}.wav"
        run_cmd([ffmpeg_path(), "-y", "-ss", f"{a:.3f}", "-t", f"{z - a:.3f}", "-i", str(src), "-c:a", "pcm_s16le", str(seg)])
        voiced = revoice_file(seg, p_["voice"], work / f"seg{n}-v.mp3", key=k)
        segs.append((a, voiced))
    ins, flt = [], []
    for n, (a, f) in enumerate(segs):
        ins += ["-i", str(f)]
        flt.append(f"[{n}:a]adelay={int(a * 1000)}|{int(a * 1000)}[d{n}]")
    fc = ";".join(flt) + ";" + "".join(f"[d{n}]" for n in range(len(segs))) + f"amix=inputs={len(segs)}:normalize=0[o]"
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    mixed = work / "mixed.wav"
    run_cmd([ffmpeg_path(), "-y", *ins, "-filter_complex", fc, "-map", "[o]", "-t", f"{total:.3f}", str(mixed)])
    crisp(mixed, out_audio)
    return out_audio


def revoice_file(audio: Path, voice_id: str, out: Path, key: str | None = None) -> Path:
    """One audio file → ElevenLabs speech-to-speech → that voice."""
    e = eleven_cfg(); k = key or lineparity.key_of()
    boundary = lineparity._boundary()
    body = _multipart({"model_id": e["sts_model_id"], "remove_background_noise": "false"},
                      [("audio", Path(audio), "audio/wav" if str(audio).endswith(".wav") else "audio/mpeg")], boundary)
    st, _h, raw = lineparity.http_transport("POST", e["speech_to_speech"].format(voice_id=voice_id) + "?output_format=" + STS_FORMAT,
                                            {"xi-api-key": k, "Content-Type": f"multipart/form-data; boundary={boundary}",
                                             "Accept": "audio/mpeg"}, body)
    if st is None or st >= 400:
        raise SystemExit(f"ElevenLabs speech-to-speech error {st}: {raw[:300]!r}")
    Path(out).write_bytes(raw)
    return Path(out)


# ---------------------------------------------------------------- step 4

def remux(clip: Path, audio: Path, out: Path, dry_run: bool = False) -> Path:
    if dry_run:
        print(json.dumps({"ffmpeg": f"remux {clip.name} + {audio.name} -> {out.name} (video copied)"}, indent=2))
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    run_cmd([ffmpeg_path(), "-y", "-i", str(clip), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", str(out)])
    return out


# ------------------------------------------------------------ silent motion

def motion(prompt: str, still: Path, out: Path, seconds: int | None = None,
           fal_transport=None, download=None, fal_key: str | None = None,
           dry_run: bool = False, resolution: str | None = None, aspect_ratio: str | None = None) -> dict:
    """A cutaway or a silent scene: the still animated on the same door, no
    line, and whatever sound Omni invents stripped — the cut carries the
    sound (the owner 2026-09-18: nothing in the chain needs the Higgsfield MCP
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
         skip_parity: bool = False, resolution: str | None = None, aspect_ratio: str | None = None,
         door: str = "fal") -> dict:
    still, out = Path(still), Path(out)
    c = cfg()
    seconds = seconds or c["defaults"]["seconds"]
    work = out.parent / f"{out.stem}-omni"
    native = work / f"{out.stem}-native.mp4"

    prompt = omni_prompt(line, prompt_extra)
    if door == "google" and not dry_run:
        res = google_submit(prompt, still, native, resolution or "360p", aspect_ratio or c["defaults"]["aspect_ratio"])
    else:
        res = omni_submit(prompt, still, seconds, native, transport=fal_transport, download=download,
                          key=fal_key, dry_run=dry_run, resolution=resolution, aspect_ratio=aspect_ratio)
    result = {"model": res["model"], "door": door, "request_id": res.get("request_id"), "recipe": "controlled_omni",
              "native": str(native), "parity_native": None, "parity_final": None,
              **{k: res[k] for k in ("took_s", "seconds", "usd", "usage") if k in res}}
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
    t.add_argument("--door", default="fal", choices=["fal", "google"], help="where Omni runs: fal, or Google directly")
    t.add_argument("--resolution", help="360p · 720p · 1080p — absent, the door's default (low and upscaled locally is the cheap route)")
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
               dry_run=a.dry_run, skip_parity=a.no_parity, resolution=a.resolution, door=a.door)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
