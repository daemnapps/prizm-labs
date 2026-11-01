"""THE SEEDANCE DOOR — every clip on Seedance 2.5 through the Higgsfield API (the owner, 2026-10-23).

    "audio is not being generated with video at the same time, which if you really do think about it in life, it's
    always generated at the same time … we always need to use the frontier models for generative work … use the 720P
    version of seed dance … seed dance is the best video in the world."
    (components/generative-model-house/MODEL-HOUSE.md, Clips; models.json clips.ruled_2026_10_23)

    talk(still, voice, line, out, …)     a TALKING clip: the approved start picture AND the line's own voice read go in
                                         the same call (bytedance/seedance-2.5/reference-to-video) — the mouth is built to
                                         the real words; nothing is re-voiced after
    motion(still, prompt, out, …)        a silent clip from the approved picture (bytedance/seedance-2.5/image-to-video)

Both refuse a picture of a person that has not passed the face gate (machine/face_gate.py) before anything is sent.
480p unless told otherwise (the owner, 2026-10-26: every clip is made at 480p and upscaled on this Mac); 4–30 s a call. Keys by name through higgsfield_api.py (HIGGSFIELD_KEY_ID/SECRET).
Brand-agnostic: the words come from the caller.

    python3 machine/seedance.py talk "<line>" --still S.png --voice line.mp3 --out clip.mp4 --master M.png [--seconds N]
    python3 machine/seedance.py motion "<what moves>" --still S.png --out clip.mp4 --no-people [--seconds N]
"""
from __future__ import annotations

import hashlib
import argparse
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TALK = "bytedance/seedance-2.5/reference-to-video"
MOTION = "bytedance/seedance-2.5/image-to-video"
# One door, more than one Seedance (2026-10-29): a model is named by its registry id and checked against its own sheet,
# components/model-inputs/inputs/<id>.json. The default is the house's clips.seedance (2.5); a format's playbook names
# another (a song ad: seedance-2.0, the house's clips.song_ad).
PATHS = {"seedance-2.5": (TALK, MOTION),
         "seedance-2.0": ("bytedance/seedance-2.0/reference-to-video", "bytedance/seedance-2.0/image-to-video")}
DEFAULT_MODEL = "seedance-2.5"


def paths(model=None):
    m = model or DEFAULT_MODEL
    if m not in PATHS:
        raise SystemExit(f"no Seedance model {m!r} on this door — the models are: {', '.join(sorted(PATHS))}")
    return PATHS[m]
RES, ASPECT, LO, HI = "480p", "9:16", 4, 30
# What a second costs. 720p MEASURED 2026-09-18 (job 57755a28: 6 s = 39 credits = 6.5 cr/s); a credit is $0.0435.
# 480p, the size every clip is made at since 2026-10-26, is an ESTIMATE by pixel count until the first real call prices it.
CREDIT_USD = 0.0435
CREDITS_PER_S = {"720p": 6.5, "480p": 6.5 * (854 * 480) / (1280 * 720), "1080p": 6.5 * 2.25}
MEASURED = ("720p",)


def usd_per_s(resolution=RES) -> float:
    return round(CREDITS_PER_S.get(resolution, CREDITS_PER_S[RES]) * CREDIT_USD, 4)


def _load(name):
    sp = importlib.util.spec_from_file_location(f"vm_sd_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def seconds_of(f) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def check_inputs(secs, resolution, images, videos=(), audios=(), aspect=9 / 16, model=None) -> list:
    """The call against the rulebook (components/model-inputs/inputs/seedance-2.5.json), before anything is sent: an error
    stops the call, a warning is returned for the page. The same numbers the video chain's field list reads."""
    CL = _load("clip_limits")
    return CL.raise_on_errors(CL.check(model or DEFAULT_MODEL, secs, resolution, images=images, videos=videos, audios=audios,
                                        aspect=aspect), "seedance")


def span(seconds) -> int:
    return int(min(HI, max(LO, math.ceil(float(seconds or LO)))))


def talk_prompt(line: str, acting: str = "") -> str:
    """The hand-made prompt (a person typing one line at the door). The chain never uses it: `seedance_prompt.build`
    writes the chain's, in the guide's blocks. Same shape here, shortest form; the line is in the audio, never typed."""
    return ("Image 1 is the first frame and shows the speaker: keep this exact person, face, clothing, props, room and light.\n"
            "Audio 1 is the speaker's voice: they speak Audio 1 word for word, lips matching every word.\n\n"
            + ((acting.strip().rstrip(".") + ".") if acting.strip() else "The speaker talks straight to the camera.")
            + "\n\nConstant throughout: one continuous take, the same person, clothing, props, room and light as Image 1. "
              "No subtitles. No background music.")


def motion_prompt(prompt: str) -> str:
    return ("Image 1 is the first frame: keep this exact person, face, clothing, props, room and light.\n\n"
            + prompt.strip().rstrip(".") + ".\n\nConstant throughout: one continuous take, the same people, props, room and "
            "light as Image 1. Nobody speaks; mouths stay closed unless an action says otherwise. "
            "No subtitles. No background music.")


def _make(path, payload, out, hf):
    out = Path(out)
    checkpoint = out.with_suffix('.request.json')
    fingerprint = hashlib.sha256(json.dumps([path, payload], sort_keys=True).encode()).hexdigest()
    saved = json.loads(checkpoint.read_text()) if checkpoint.is_file() else {}
    if saved.get('request_id') and saved.get('state') not in ('failed', 'nsfw', 'cancelled', 'canceled', 'error'):
        if saved.get('fingerprint') != fingerprint:
            raise RuntimeError('An existing generation has different inputs; resolve its saved request before a new submission.')
        rid = saved['request_id']
        if saved.get('state') == 'completed' and out.is_file():
            return {'model': path, 'request_id': rid, 'file': str(out), 'url': saved.get('url')}
    else:
        rid = hf.submit(path, payload)
        out.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({'request_id': rid, 'fingerprint': fingerprint, 'state': 'submitted'}))
    body = hf.wait(rid)
    state = str(body.get('status', '')).lower()
    checkpoint.write_text(json.dumps({'request_id': rid, 'fingerprint': fingerprint, 'state': state}))
    if state != 'completed':
        raise RuntimeError(f"{out.name}: Seedance ended '{state}' (request saved for recovery)")
    urls = hf.outputs(body)
    if not urls:
        raise RuntimeError(f"{out.name}: Seedance answered with no video")
    hf.download(urls[0], out)
    checkpoint.write_text(json.dumps({'request_id': rid, 'fingerprint': fingerprint, 'state': state, 'url': urls[0]}))
    return {'model': path, 'request_id': rid, 'file': str(out), 'url': urls[0]}


def talk(line, still, voice, out, seconds=None, acting="", masters=None, no_people=False, refs=(),
         resolution=RES, aspect=ASPECT, dry_run=False, hf=None, face_check=None, prompt=None, videos=(), model=None) -> dict:
    talk_path = paths(model)[0]
    still, voice, out = Path(still), Path(voice), Path(out)
    if not voice.is_file() and not dry_run:
        raise SystemExit(f"{out.name}: no voice read at {voice} — the line is read first, then the clip is made to it")
    if not dry_run:
        _load("face_gate").require(still, masters, no_people=no_people, check=face_check)
    secs = span(seconds or (seconds_of(voice) + 0.6 if voice.is_file() else LO))
    check_inputs(secs, resolution, [still] + [Path(r) for r in refs], videos=videos, audios=[voice], model=model)
    payload = {"prompt": prompt or talk_prompt(line, acting), "resolution": resolution, "aspect_ratio": aspect,
               "duration": secs, "generate_audio": True, "output_format": "mp4"}
    if dry_run:
        print(json.dumps({"POST": talk_path, "images": [str(still)] + [str(r) for r in refs], "videos": [str(v) for v in videos],
                          "audio": [str(voice)], **payload}, indent=1))
        return {"model": talk_path, "file": None}
    hf = hf or _load("higgsfield_api")
    payload["image_urls"] = [hf.upload(still)] + [hf.upload(r) for r in refs]
    if videos:
        # motion references (the swipe's own shot, blurred): the field name is read off the first live call (a 422 names it)
        payload["video_urls"] = [hf.upload(v) for v in videos]
    payload["audio_urls"] = [hf.upload(voice)]
    return {**_make(talk_path, payload, out, hf), "seconds": secs, "line": line}


def motion(prompt, still, out, seconds=None, end_still=None, masters=None, no_people=False,
           resolution=RES, dry_run=False, hf=None, face_check=None, whole=False, videos=(), model=None) -> dict:
    talk_path, motion_path = paths(model)
    still, out = Path(still), Path(out)
    if not dry_run:
        _load("face_gate").require(still, masters, no_people=no_people, check=face_check)
    check_inputs(span(seconds), resolution, [still] + ([Path(end_still)] if end_still else []), videos=videos, model=model)
    payload = {"prompt": prompt if whole else motion_prompt(prompt), "resolution": resolution, "duration": span(seconds),
               "generate_audio": False, "output_format": "mp4"}
    # a silent clip WITH a motion reference is reference mode (picture + video), like a talking clip; without one it is
    # image-to-video and may carry a last frame (the two modes cannot be mixed on this door)
    path = talk_path if videos else motion_path
    if dry_run:
        print(json.dumps({"POST": path, "image": str(still), "end_image": str(end_still or ""),
                          "videos": [str(v) for v in videos], **payload}, indent=1))
        return {"model": path, "file": None}
    hf = hf or _load("higgsfield_api")
    if videos:
        payload.update({"image_urls": [hf.upload(still)], "video_urls": [hf.upload(v) for v in videos], "aspect_ratio": ASPECT})
    else:
        payload["image_url"] = hf.upload(still)
        if end_still:
            payload["end_image_url"] = hf.upload(end_still)
    return _make(path, payload, out, hf)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("talk"); t.add_argument("line"); t.add_argument("--voice", required=True)
    m = sub.add_parser("motion"); m.add_argument("prompt"); m.add_argument("--end-still")
    for p in (t, m):
        p.add_argument("--still", required=True); p.add_argument("--out", required=True)
        p.add_argument("--seconds", type=float); p.add_argument("--resolution", default=RES)
        p.add_argument("--master", action="append", default=[]); p.add_argument("--no-people", action="store_true")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--model", choices=sorted(PATHS), help="which Seedance (registry id); default the house's")
    t.add_argument("--acting", default=""); t.add_argument("--ref", action="append", default=[])
    a = ap.parse_args(argv)
    if a.cmd == "talk":
        r = talk(a.line, a.still, a.voice, a.out, a.seconds, a.acting, a.master or None, a.no_people, a.ref,
                 a.resolution, dry_run=a.dry_run, model=a.model)
    else:
        r = motion(a.prompt, a.still, a.out, a.seconds, a.end_still, a.master or None, a.no_people, a.resolution,
                   dry_run=a.dry_run, model=a.model)
    print(json.dumps(r, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
