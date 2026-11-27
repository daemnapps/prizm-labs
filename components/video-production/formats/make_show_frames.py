#!/usr/bin/env python3
"""One key frame per show format, same cast member in every one, through the image door.
    python3 formats/make_show_frames.py --cast <frame.png>"""
import argparse, json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
import direct_openai as door
_cfg = door.cfg
door.cfg = lambda: {**_cfg(), "params": {**(_cfg().get("params") or {}), "quality": "medium"}}
LOCK = ("The woman in the reference image is the cast member: keep her face, hair and age exactly. Do NOT copy the reference's background, pose or clothes. "
        "New picture, vertical 9:16, photoreal television still: {p}. No readable text, no logos, no real people.")
ap = argparse.ArgumentParser(); ap.add_argument("--cast", required=True); a = ap.parse_args()
for s in json.loads((HERE / "show-formats.json").read_text())["shows"]:
    out = HERE / s["frame"]
    if out.exists(): print(s["id"], "kept"); continue
    try:
        png = out.with_suffix(".png"); r = door.generate(LOCK.format(p=s["frame_prompt"]), [Path(a.cast)], png)
        if not r.get("file"): print(s["id"], "FAILED"); continue
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(png),"-vf","scale=512:-1","-q:v","4",str(out)],check=True); png.unlink(); print(s["id"], "made", flush=True)
    except BaseException as e: print(s["id"], "FAILED", str(e)[:140], flush=True)
