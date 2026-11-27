#!/usr/bin/env python3
"""index_new.py — keep a brand's footage library current as new files land on the Shared Assets drive.

    python3 index_new.py --brand <brand> [--budget 2.00] [--dry-run] [--key-env NAME]

One pass, in order, each step resumable and skipped when there is nothing new:

1. map     machine/map_all.py — a free record for every new file the key reaches (nothing downloaded).
2. describe machine/describe.py — new VIDEOS in footage folders get their scene labels (paid, inside the budget).
3. check   library/check.py — described clips not yet checked get the check pass (paid, inside what is left).
4. cuts    library/cuts.py — the real shot changes of new clips, so in and out land on the cut (free).
5. build   library/library.py build — the brand's library and coverage are rebuilt (free).
5b. cast   library/cast.py — people (count, gender, age, skin tone, face, couple, person id) and what happens (action,
           product in use, competitor, room, framing, camera, emotion, letterbox) per scene (paid, inside what is
           left); then written onto the rows, and the story-coverage map rebuilt (free).
6. moments library/moments.py run — new scenes split at their real cuts, each stretch's busiest window judged once
           (paid, inside what is left), so editing is a lookup on the index, never a measurement.

The budget is one cap for the whole pass, in USD; a step starts only while money is left. With --dry-run
nothing is written or sent: it reports what each step would do and cost. A key that is out of credit stops
the paid steps for that pass and the free steps still run. Writes only runs/asset-index/<brand>/.
Footage folders are the ones listed in FOOTAGE (the first folder under brands/<brand>/ and, for intake and
archive, the second); pictures are a later card.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MACHINE = HERE.parent / "machine"
REPO = HERE.parents[2]
RUNS = Path(os.environ.get("ASSET_INDEX_RUNS") or (REPO / "runs" / "asset-index"))
FOOTAGE_DEFAULT = ["content-creators", "intake/organic", "intake/references", "intake/before-after", "archive/creators-curated",
           "ai-elements", "brand-assets"]     # a brand's own list: footage_folders in brands/<brand>/footage-library.json
FOOTAGE = list(FOOTAGE_DEFAULT)
PY = sys.executable
sys.path.insert(0, str(HERE))
import library as LIB  # noqa: E402  (brand_config)


def _run(args: list, env=None) -> tuple[int, str]:
    r = subprocess.run([PY, *args], capture_output=True, text=True, env=env, cwd=str(REPO))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def new_videos(brand: str) -> list[str]:
    """Labels prefixes of footage folders that hold video records not yet described."""
    out = {}
    for m in sorted((RUNS / brand).glob("*/map.json")):
        try:
            mp = json.loads(m.read_text())
        except ValueError:
            continue
        for fid, e in mp.items():
            rec = m.parent / fid
            lab = str(e.get("label") or "")
            rel = lab.split(f"brands/{brand}/", 1)[-1]
            if not any(rel.startswith(f + "/") for f in FOOTAGE):
                continue
            if (rec / "breakdown.json").is_file():
                continue
            try:
                clip = json.loads((rec / "clip.json").read_text())
            except (OSError, ValueError):
                continue
            if clip.get("kind") == "video" or (clip.get("meta") or {}).get("duration_s"):
                out[fid] = FOOTAGE.index(next(f for f in FOOTAGE if rel.startswith(f + "/")))
    return sorted(out, key=lambda f: (out[f], f))     # creators' raw footage first: casting reads it


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--budget", type=float, default=2.0)
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    ap.add_argument("--key-env", default="", help="model key from this environment variable (default: the shared loader)")
    a = ap.parse_args(argv)
    env = dict(os.environ)
    if a.key_env and env.get(a.key_env):
        env["GEMINI_API_KEY"] = env[a.key_env]      # describe reads GEMINI_API_KEY through the shared loader
    log = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "brand": a.brand, "budget": a.budget,
           "dry": a.dry, "steps": {}}
    left = a.budget

    for attempt in (1, 2):                          # the Drive walk can time out on a slow line; one retry
        code, out = _run([str(MACHINE / "map_all.py"), "--brand", a.brand, *(["--dry-run"] if a.dry else [])], env)
        if code == 0:
            break
    log["steps"]["map"] = {"exit": code, "attempts": attempt, "tail": out.strip()[-400:]}

    FOOTAGE[:] = LIB.brand_config(a.brand).get("footage_folders") or FOOTAGE_DEFAULT
    ids = new_videos(a.brand)
    step = {"new_videos": len(ids)}
    if ids and left > 0:
        code, out = _run([str(MACHINE / "describe.py"), "--brand", a.brand, "--ids", ",".join(ids),
                          "--budget", f"{left:.2f}", "--reason", "new footage on the drive (index_new)",
                          *(["--dry-run"] if a.dry else [])], env)
        step["exit"] = code
        try:
            res = json.loads(out[out.index("{"):])
            step.update({k: res.get(k) for k in ("described", "spent_usd", "stopped", "would_describe", "est_usd")})
            if not a.dry:
                left -= float(res.get("spent_usd") or 0)
        except ValueError:
            step["tail"] = out.strip()[-400:]
    log["steps"]["describe"] = step

    # the library must know the newly described clips before they can be checked
    if not a.dry:
        _run([str(HERE / "library.py"), "build", "--brand", a.brand], env)
    if left > 0:
        code, out = _run([str(HERE / "check.py"), "--brand", a.brand, "--budget", f"{left:.2f}",
                          *(["--key-env", a.key_env] if a.key_env else []), *(["--dry-run"] if a.dry else [])], env)
        log["steps"]["check"] = {"exit": code, "tail": out.strip()[-400:]}
    else:
        log["steps"]["check"] = {"skipped": "budget spent"}

    if not a.dry:
        code, out = _run([str(HERE / "cuts.py"), "--brand", a.brand], env)       # free: shot changes for the editor's times
        log["steps"]["cuts"] = {"exit": code, "tail": out.strip()[-200:]}
        code, out = _run([str(HERE / "library.py"), "build", "--brand", a.brand], env)
        log["steps"]["build"] = {"exit": code, "tail": out.strip()[-300:]}
    # the cast pass: who is on screen and what happens, per scene (paid, inside what is left), then onto the rows
    if left > 0:
        code, out = _run([str(HERE / "cast.py"), "run", "--brand", a.brand, "--budget", f"{left:.2f}",
                          *(["--key-env", a.key_env] if a.key_env else []), *(["--dry-run"] if a.dry else [])], env)
        step = {"exit": code, "tail": out.strip()[-300:]}
        try:
            res = json.loads(out.strip().splitlines()[-1])
            if not a.dry:
                left -= float(res.get("spent_usd_run") or 0)
        except (ValueError, IndexError):
            pass
        log["steps"]["cast"] = step
    else:
        log["steps"]["cast"] = {"skipped": "budget spent"}
    if not a.dry:     # free: the cast fields onto library.json, and the story-coverage map
        code, out = _run([str(HERE / "cast.py"), "apply", "--brand", a.brand], env)
        log["steps"]["cast_apply"] = {"exit": code, "tail": out.strip()[-200:]}
        code, out = _run([str(HERE / "cast.py"), "coverage", "--brand", a.brand], env)
        log["steps"]["coverage"] = {"exit": code}
    if left > 0:      # the moments pass: needs the built library; with --dry-run it counts and prices only
        code, out = _run([str(HERE / "moments.py"), "run", "--brand", a.brand, "--budget", f"{left:.2f}",
                          *(["--dry-run"] if a.dry else [])], env)
        log["steps"]["moments"] = {"exit": code, "tail": out.strip()[-400:]}
    else:
        log["steps"]["moments"] = {"skipped": "budget spent"}
    if not a.dry:
        f = RUNS / a.brand / "library" / "index-new.json"
        hist = json.loads(f.read_text()) if f.is_file() else []
        hist.append(log)
        f.write_text(json.dumps(hist[-60:], indent=1) + "\n")
    print(json.dumps(log, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
