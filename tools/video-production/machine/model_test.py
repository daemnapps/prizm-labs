#!/usr/bin/env python3
"""model_test.py — the same clip on more than one model, with everything else held equal (the owner, 2026-10-29:
"run through the chain properly … so we can isolate variance clearly").

One call is built ONCE by the chain's own prompt builder (seedance_prompt.build) from a run's scene, its approved start
picture and its locked read (vo/<scene>.mp3, the singer's slice of the song for a sung scene). Every model gets that same
prompt, picture and audio through the same door (seedance.py). The model's own sound is thrown away: the SAME read is laid
over each result, so the pictures are the only thing that differs. Writes <run>/model-tests/<label>/: prompt.txt,
inputs.json, one <model>.mp4 per model (the model's own file), one <model>-same-audio.mp4 each, and side-by-side.mp4.

    python3 machine/model_test.py <run> --scene L1 --picture media/singer.png --models seedance-2.5,seedance-2.0
        [--label L1] [--line "…"] [--acting "…"] [--movement <bank id>] [--dry-run]

No model is ruled by this; it only measures. --movement adds one real-person reference from the movement bank
(tools/video-production/movement-bank.json) to EVERY model, or none (the default). Spends only without --dry-run.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    sp = importlib.util.spec_from_file_location(f"mt_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _secs(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def build_call(run, scene, line, acting, movement=None):
    """The one call every model gets: built by seedance_prompt.build, the chain's own writer."""
    SP = _load("seedance_prompt")
    read = Path(run) / "vo" / f"{scene}.mp3"
    secs = max(4, int(-(-(_secs(read) + 0.6) // 1)))
    style = ""
    try:
        rows = json.loads((HERE.parents[1] / "components/elements/library/style.video.json").read_text())
        rows = rows if isinstance(rows, list) else rows.get("rows") or rows.get("items") or []
        sid = (json.loads((Path(run) / "plan.json").read_text()).get("style_id")) or "family-3d"
        style = next((r.get("what") for r in rows if isinstance(r, dict) and r.get("id") == sid), "") or ""
    except (OSError, ValueError):
        pass
    call = {"id": f"TEST-{scene}", "talking": True, "sung": True, "people": ["SINGER"], "scenes": [scene], "duration": secs,
            "seconds": secs, "lines": [{"speaker": "SINGER", "on_camera": True, "scene": scene, "line": line}],
            "voice_parts": [{"scene": scene, "line": line}], "refs": []}
    scenes = {scene: {"id": scene, "happens": acting, "camera_move": "hold"}}
    people = {"SINGER": {"noun": "singer", "poss": "his", "gestures": []}}
    out = SP.build(call, scenes, people, {}, style)
    if movement:
        MV = _load("movement")
        call["refs"] = MV.for_call(call, acting, entry_id=movement)
        MV.make(Path(run), call["refs"][0], "ffmpeg")
        out = SP.build(call, scenes, people, {}, style)
    return call, out, read, secs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--picture", required=True, help="the approved start picture, relative to the run or absolute")
    ap.add_argument("--models", default="seedance-2.5,seedance-2.0")
    ap.add_argument("--label")
    ap.add_argument("--line")
    ap.add_argument("--acting", default="sings the line to the phone like a music video, mouth on every sung word, a confident hand gesture, head moving with the beat")
    ap.add_argument("--movement")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    run = Path(a.run).resolve()
    pic = Path(a.picture) if Path(a.picture).is_absolute() else run / a.picture
    lock = (json.loads((run / "vo" / "locks.json").read_text()) if (run / "vo" / "locks.json").is_file() else {}).get(a.scene) or {}
    line = a.line or " ".join(lock.get("lines") or [])
    if not line:
        raise SystemExit(f"{a.scene}: no line — pass --line or cut the sung reads first (song.py sung_reads)")
    call, built, read, secs = build_call(run, a.scene, line, a.acting, a.movement)
    prompt = built["prompt"] if isinstance(built, dict) else str(built)
    d = run / "model-tests" / (a.label or a.scene)
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.txt").write_text(prompt)
    models = [m.strip() for m in a.models.split(",") if m.strip()]
    (d / "inputs.json").write_text(json.dumps({"scene": a.scene, "picture": str(pic), "audio": str(read), "seconds": secs,
                                               "line": line, "movement": a.movement, "models": models,
                                               "resolution": "480p"}, indent=1))
    SD = _load("seedance")
    print(f"prompt (same for every model):\n{prompt}\n")
    outs = []
    for m in models:
        out = d / f"{m}.mp4"
        r = SD.talk(line, pic, read, out, seconds=secs, masters=[pic], prompt=prompt,
                    videos=[run / x["file"] for x in call["refs"]], model=m, dry_run=a.dry_run)
        print(f"{m}: {'dry run' if a.dry_run else r.get('file')}")
        outs.append((m, out))
    if a.dry_run:
        return 0
    ff = ["ffmpeg", "-y", "-loglevel", "error"]
    same = []
    for m, out in outs:       # the same read under every picture: the model's own sound is not kept
        s = d / f"{m}-same-audio.mp4"
        subprocess.run(ff + ["-i", str(out), "-i", str(read), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                             "-shortest", str(s)], check=True)
        same.append(s)
    if len(same) == 2:
        # 2.5 on the left, 2.0 on the right (the order of --models); no on-screen text, so it needs no font
        subprocess.run(ff + ["-i", str(same[0]), "-i", str(same[1]), "-filter_complex",
                             "[0:v]scale=-2:854[a];[1:v]scale=-2:854[b];[a][b]hstack=inputs=2[v]", "-map", "[v]", "-map", "0:a",
                             "-c:v", "libx264", "-c:a", "aac", "-shortest", str(d / "side-by-side.mp4")], check=True)
    print(f"written under {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
