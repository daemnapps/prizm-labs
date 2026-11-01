"""THE KLING DOOR — the backup clip, through the Higgsfield API (the owner, 2026-10-26).

Kling 4.0 is wired BEHIND Seedance: a clip comes here when Seedance fails its three takes, is refused or is down. It takes the
approved start picture and no audio (components/model-inputs/inputs/kling-4.0.json), so every clip it makes is SILENT. Both
calls refuse a picture of a person that has not passed the face gate, and check the call against the rulebook first.

    motion(prompt, still, out, seconds=None, ...)      a silent clip from the approved picture (image-to-video)

The request path and field names are the Higgsfield video list's pattern (providers.json clip_route.backup) and are read off the
first live call (a 422 names a wrong field). No brand, product or person is named here. Python 3.9.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "kling-4.0"
PATH = "kling-video/v4.0/image-to-video"          # unverified until the first live call (the list shows .../v4.0/text-to-video)
RES, ASPECT, LO, HI = "720p", "9:16", 3, 30       # Kling 4.0 has no 480p; the clip is upscaled on this Mac like every clip
USD_PER_S = 0.157                                 # Higgsfield list price, the high end of 'from 0.11 (list 0.157)'; not measured


def _load(name):
    sp = importlib.util.spec_from_file_location(f"vm_kl_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def span(seconds) -> int:
    return int(min(HI, max(LO, math.ceil(float(seconds or LO)))))


def usd_per_s(resolution=RES) -> float:
    return USD_PER_S


def motion(prompt, still, out, seconds=None, end_still=None, masters=None, no_people=False, resolution=RES,
           dry_run=False, hf=None, face_check=None) -> dict:
    still, out = Path(still), Path(out)
    CL = _load("clip_limits")
    CL.raise_on_errors(CL.check(MODEL, span(seconds), resolution, images=[still] + ([Path(end_still)] if end_still else [])), "kling")
    if not dry_run:
        _load("face_gate").require(still, masters, no_people=no_people, check=face_check)
    payload = {"prompt": prompt, "resolution": resolution, "duration": span(seconds), "aspect_ratio": ASPECT,
               "sound": "off", "mode": "image-to-video", "output_format": "mp4"}
    if dry_run:
        print(json.dumps({"POST": PATH, "image": str(still), "end_image": str(end_still or ""), **payload}, indent=1))
        return {"model": PATH, "file": None}
    S = _load("seedance")                          # one Higgsfield HTTP transport for both doors
    hf = hf or _load("higgsfield_api")
    payload["image_url"] = hf.upload(still)
    if end_still:
        payload["end_image_url"] = hf.upload(end_still)
    r = S._make(PATH, payload, out, hf)
    return {**r, "model": MODEL, "path": PATH, "seconds": payload["duration"]}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("prompt")
    ap.add_argument("--still", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--master", action="append", default=[])
    ap.add_argument("--no-people", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    r = motion(a.prompt, a.still, a.out, a.seconds, masters=a.master or None, no_people=a.no_people, dry_run=a.dry_run)
    print(json.dumps(r, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
