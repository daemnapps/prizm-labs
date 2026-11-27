#!/usr/bin/env python3
"""Freeze clips of a finished plan into bench cases: the start picture, the locked voice read, the line, the people's
masters, and the prompt the chain used to send and the one it sends now.

    python3 capture.py <run folder> <call id,call id,...> [--name NAME]

A case lives at runs/video-production/_bench/cases/<name>/<call id>/ and never changes, so every test of an input
(a prompt, a size, a reference) is made from the same picture and the same voice. Brand-agnostic.
"""
import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MACHINE = HERE.parent / "machine"
REPO = HERE.parents[2]


def _load(name):
    sp = importlib.util.spec_from_file_location(f"bc_{name}", MACHINE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sys.modules[sp.name] = m
    sp.loader.exec_module(m)
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run")
    ap.add_argument("calls")
    ap.add_argument("--name")
    a = ap.parse_args(argv)
    run = Path(a.run).resolve()
    oc, sd, fg = _load("clips_run"), _load("seedance"), _load("face_gate")
    ck = oc._load("clip_kit")
    plan = json.loads((run / "clips" / "plan.json").read_text())
    name = a.name or run.name
    made = []
    for cid in [x.strip() for x in a.calls.split(",") if x.strip()]:
        c = next((x for x in plan["calls"] if x["id"] == cid), None)
        if not c or not c.get("talking") or not c.get("seedance"):
            print(f"{cid}: not a talking call with a Seedance prompt (re-plan the run first)", file=sys.stderr)
            continue
        d = REPO / "runs" / "video-production" / "_bench" / "cases" / name / cid
        d.mkdir(parents=True, exist_ok=True)
        start = oc.cp.picture_file(run, c["start_frame"])
        sent = oc.to_aspect(start, d / "start.png", (9, 16))
        take, a_from, a_to = oc.locked_read(run, c, d, ck)
        read = d / "read.wav"
        cmd = [ck.ffmpeg_path(), "-y"] + (["-ss", f"{a_from}"] if a_from else []) + (["-to", f"{a_to}"] if a_to else []) \
            + ["-i", str(take), "-ac", "1", "-ar", "44100", str(read)]
        ck.run_cmd(cmd)
        line = " ".join(p["line"] for p in c.get("voice_parts") or [])
        masters = fg.masters_for(run, c.get("people") or [])
        (d / "case.json").write_text(json.dumps({
            "id": cid, "case": name, "source_run": run.name, "line": line, "seconds": sd.span(sd.seconds_of(read) + 0.6),
            "people": c.get("people") or [], "masters": masters, "start": "start.png", "read": "read.wav",
            "prompts": {"old": sd.talk_prompt(line, c["params"].get("prompt", "")), "new": c["seedance"]["prompt"]},
        }, indent=1))
        made.append(cid)
        print("captured", d)
    return 0 if made else 2


if __name__ == "__main__":
    sys.exit(main())
