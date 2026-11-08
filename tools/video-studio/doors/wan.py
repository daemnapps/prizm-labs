"""THE WAN DOOR — Wan 3.0 as a person's pick for a clip, on the Higgsfield plan's credits (ruled 2026-11-08).

Not the house default: Seedance 2.5 stays the default (components/generative-model-house/MODEL-HOUSE.md, Clips). A person
picks Wan for a shot, usually one Seedance refuses or one where the cost per take matters. The call goes through the
Higgsfield CLI (`higgsfield generate create wan3_0`) under the signed-in account, so it spends the plan's credits and no key.
Rulebook: components/model-inputs/inputs/wan-3.0.json. Registry: components/models/models.json `wan-3.0`.

    motion(prompt, still, out, seconds=None, ...)      a silent clip from the approved picture (image-to-video)

Like the other clip doors it refuses a picture of a person that has not passed the face gate and checks the call against
the rulebook first. A start picture cannot travel with reference media on this door, so a Wan clip carries no voice read.
No brand, product or person is named here. Python 3.9.

    python3 machine/wan.py "<what moves>" --still S.png --out clip.mp4 --master M.png [--seconds N] [--dry-run]
"""
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "wan-3.0"
JOB = "wan3_0"                                   # the Higgsfield model id (registry doors.higgsfield.vendor_id)
RES, ASPECT, LO, HI = "480p", "9:16", 2, 30
CREDITS_PER_S = {"480p": 1.0, "720p": 1.75, "1080p": 3.5}   # `higgsfield generate cost wan3_0`, read 2026-11-08, sound off
# The first take pushed in from full body to waist-up unasked (2026-11-08); every prompt now holds the framing.
HOLD = "The camera keeps the first frame's framing and distance the whole time: no zoom, no push-in, no cut."
TERMINAL = {"completed", "failed", "nsfw", "cancelled", "canceled", "error"}


def _load(name):
    sp = importlib.util.spec_from_file_location(f"vm_wan_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def span(seconds) -> int:
    return int(min(HI, max(LO, math.ceil(float(seconds or 5)))))


def credits(resolution=RES, seconds=5) -> float:
    return round(CREDITS_PER_S.get(resolution, CREDITS_PER_S[RES]) * span(seconds), 2)


def cli() -> str:
    exe = shutil.which("higgsfield") or shutil.which("higgs")
    if not exe:
        raise SystemExit("the Wan door needs the Higgsfield CLI (`higgsfield`), signed in to the account whose credits it spends")
    return exe


def motion_prompt(prompt: str) -> str:
    """The house clip prompt (the same wording the Seedance door sends) plus the framing line."""
    base = _load("seedance").motion_prompt(prompt)
    return base.replace("\n\nConstant throughout:", " " + HOLD + "\n\nConstant throughout:", 1)


def _run(args, timeout=1800):
    r = subprocess.run([cli(), "--json"] + args, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"higgsfield {' '.join(args[:2])} failed: {(r.stderr or r.stdout).strip()[:400]}")
    return json.loads(r.stdout or "null")


def _make(args, out):
    out = Path(out)
    checkpoint = out.with_suffix(".request.json")
    fingerprint = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()
    saved = json.loads(checkpoint.read_text()) if checkpoint.is_file() else {}
    if saved.get("job_id") and saved.get("state") not in TERMINAL - {"completed"}:
        if saved.get("fingerprint") != fingerprint:
            raise RuntimeError("An existing generation has different inputs; resolve its saved request before a new submission.")
        job = saved["job_id"]
        if saved.get("state") == "completed" and out.is_file():
            return {"model": MODEL, "request_id": job, "file": str(out), "url": saved.get("url")}
    else:
        ids = _run(["generate", "create", JOB] + args, timeout=600)
        job = ids[0] if isinstance(ids, list) else (ids or {}).get("id")
        if not job:
            raise RuntimeError(f"{out.name}: Wan answered with no job id: {str(ids)[:200]}")
        out.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({"job_id": job, "fingerprint": fingerprint, "state": "submitted"}))
    body = _run(["generate", "wait", job])
    state = str(body.get("status", "")).lower()
    url = body.get("result_url")
    checkpoint.write_text(json.dumps({"job_id": job, "fingerprint": fingerprint, "state": state, "url": url}))
    if state != "completed" or not url:
        raise RuntimeError(f"{out.name}: Wan ended '{state}' (job {job} saved for recovery)")
    with urllib.request.urlopen(url, timeout=300) as r, open(out, "wb") as f:
        shutil.copyfileobj(r, f)
    return {"model": MODEL, "request_id": job, "file": str(out), "url": url}


def motion(prompt, still, out, seconds=None, end_still=None, masters=None, no_people=False, resolution=RES,
           dry_run=False, face_check=None, whole=False, **_) -> dict:
    still, out = Path(still), Path(out)
    if (HERE.parents[1] / "model-inputs" / "inputs" / f"{MODEL}.json").is_file():
        CL = _load("clip_limits")
        CL.raise_on_errors(CL.check(MODEL, span(seconds), resolution,
                                    images=[still] + ([Path(end_still)] if end_still else []), measure=False), "wan")
    elif resolution not in CREDITS_PER_S or not LO <= float(seconds or 5) <= HI:
        # a copy of the team tools that does not carry the rulebook yet: the door's own limits still hold
        raise SystemExit(f"wan: {resolution} / {seconds} s is outside what {MODEL} makes ({', '.join(CREDITS_PER_S)}; {LO} to {HI} s)")
    if not dry_run:
        _load("face_gate").require(still, masters, no_people=no_people, check=face_check)
    text = prompt if whole else motion_prompt(prompt)
    args = ["--prompt", text, "--start-image", str(still), "--resolution", resolution, "--duration", str(span(seconds)),
            "--aspect_ratio", ASPECT, "--generate_audio", "false"]
    if end_still:
        args += ["--end-image", str(end_still)]
    if dry_run:
        print(json.dumps({"job_type": JOB, "args": args, "credits": credits(resolution, seconds)}, indent=1))
        return {"model": MODEL, "file": None, "prompt": text}
    r = _make(args, out)
    return {**r, "seconds": span(seconds), "prompt": text, "credits": credits(resolution, seconds)}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt")
    ap.add_argument("--still", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--end-still")
    ap.add_argument("--resolution", default=RES)
    ap.add_argument("--master", action="append", default=[])
    ap.add_argument("--no-people", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    r = motion(a.prompt, a.still, a.out, a.seconds, end_still=a.end_still, masters=a.master or None,
               no_people=a.no_people, resolution=a.resolution, dry_run=a.dry_run)
    print(json.dumps(r, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
