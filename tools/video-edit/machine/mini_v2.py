#!/usr/bin/python3
"""Station 4 on the mini: the production station's run in, the finished, audited edit out, handed on through
Shared Assets.

    mini_v2.py --brand <b> --label <l> --out <dir> [--dry-run]

<l> is the label every station of this swipe used. The production run is this machine's own
(runs/video-production/<brand>/<l>/) or is fetched from Shared Assets runs/video-production/<brand>/<l>/.
One step (video sync 2026-10-21, R4/R5): line.py <production run>, the one edit path — the edit map, the
mouths, the render, compose.py's words, the audit on every version, the scan, thumbnails, the copy, the card
in 1-check. Every check stops the line. Hook versions and thumbnails follow the owner's final OK on the control cut
(line.approved()). The edit run is copied into --out and PUT on Shared Assets at runs/video-edit/<brand>/<l>/
(run_kit.station). Exit 0 only when the card is filed and waiting for Approve; nothing goes live on Meta here.

The production run is taken only when it is FINISHED (row 15, verify 2026-10-21): production-done.json from the
production door, and every clip clips/plan.json lists made (ledger 'done' + the mp4). A partial run is refused
before anything is planned, rendered or put on the drive. The edit run is handed on only when the line exits 0.

--dry-run runs the plan step only (edit_map.py: the edit map, free, no voice, no lips, no render) and reports what
it found; nothing is put on the drive.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "components" / "run-kit"))


def production_folder(brand, label):
    """The production run in this checkout's runs tree (fetched there when missing), never a temp folder:
    the edit kit records its clip paths, and the final render reads them later (review, 19 Oct)."""
    local = REPO / "runs" / "video-production" / brand / label
    # LD-53 (station-path runner): the repo copy is this folder itself (its text in git, its media
    # git-ignored); what it lacks — the clips and voice — comes from Shared Assets, every source
    # printed and kept on run.json.
    from run_kit.station import resolve
    resolve("video-production", brand, label, local, need=("media", "clips", "production-done.json"), want=("vo",),
            repo=REPO)
    return local


def unfinished(prod):
    """Why this production run is not finished — [] = take it. The mark production writes only on a clean finish,
    then every clip the plan lists made (status 'done' in the ledger and the mp4 here)."""
    prod = Path(prod)
    try:
        mark = json.loads((prod / "production-done.json").read_text())
    except (OSError, ValueError):
        return ["no production-done.json — production did not finish this run"]
    if mark.get("status") != "done":
        return ["production-done.json says %r, not done" % mark.get("status")]
    try:
        plan = json.loads((prod / "clips" / "plan.json").read_text())
    except (OSError, ValueError):
        return ["no clips/plan.json"]
    try:
        _lf = prod / "clips" / "ledger.json"           # (a run made before 2026-10-26 keeps clips/omni-ledger.json)
        led = json.loads((_lf if _lf.exists() else prod / "clips" / "omni-ledger.json").read_text())
    except (OSError, ValueError):
        led = {}
    ids = [c.get("id") for c in plan.get("calls") or [] if c.get("id")]
    if not ids:
        return ["clips/plan.json lists no clips"]
    return ["clip %s not made" % i for i in ids
            if (led.get(i) or {}).get("status") != "done" or not (prod / "clips" / ("%s.mp4" % i)).is_file()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    a = ap.parse_args(argv)
    prod = production_folder(a.brand, a.label)
    why = unfinished(prod)
    if why:
        print("the production run %s is not finished — the edit does not start on it:\n  %s"
              % (a.label, "\n  ".join(why[:20])), file=sys.stderr)
        return 1
    root = REPO / "runs" / "video-edit"
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    env["DISABLE_PROMPT_CACHING"] = "1"
    run = root / a.brand / a.label
    if a.dry:
        # the plan step alone: no word fixes (they read lines aloud), no lips, no render — free (row 22)
        r = subprocess.run([sys.executable, str(HERE / "edit_map.py"), str(prod), "--out", str(run), "--hooks"],
                           cwd=str(HERE), env=env)
        return r.returncode
    r = subprocess.run([sys.executable, str(HERE / "line.py"), str(prod), "--out", str(run)], cwd=str(HERE), env=env)
    if r.returncode != 0:
        # nothing partial is handed on (row 15): the edit run stays here for a look, the drive is not touched
        if run.is_dir():
            shutil.copytree(str(run), str(Path(a.out)), symlinks=False, dirs_exist_ok=True)
        print("the edit line stopped at a red check — see line.json in the edit run; nothing handed on", file=sys.stderr)
        return 1
    if run.is_dir():
        shutil.copytree(str(run), str(Path(a.out)), symlinks=False, dirs_exist_ok=True)
        from run_kit.station import push
        res = push(run, "video-edit", a.brand, a.label, copy_to=a.out)
        print("handed on: %d file(s) to %s%s" % (res["placed"], res["to"],
              "" if not res["notes"] else " · " + "; ".join(res["notes"])[:400]))
        if res["notes"]:
            print("the hand-off to Shared Assets did not complete", file=sys.stderr)
            return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
