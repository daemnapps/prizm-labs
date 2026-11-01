#!/usr/bin/python3
"""Station 3 on the mini: the writing station's brief in, production v2 out (voice, stills, clips, handed
to the edit), passed on through Shared Assets.

    mini_v2.py --brand <b> --label <l> [--format <id>] --out <dir> [--dry-run]

<l> is the label the teardown and writing stations used. The writing run is this machine's own
(runs/video-teardown/_work/<l>/) or is fetched from Shared Assets runs/video-writing/<brand>/<l>/.
Two steps (video sync 2026-10-21, R1/P8): run_v2 start --yes runs the order itself — voice first (three reads a
line, one locked) → the storyboard → only the pictures it lists (one of each, 2026-10-24) → the clip plan —
then run_v2 clips --yes makes one take of every clip at 480p (another only if it fails, three at most), upscales the pick on this Mac, and hands
the clips to the edit (VIDEO-RULINGS V5–V7).
The production run is copied into --out and PUT on Shared Assets at runs/video-production/<brand>/<l>/
for the edit station (run_kit.station) — ONLY when every step finished and every clip the plan lists is made
(row 15, verify 2026-10-21): a failed step or a missing clip stops here, nothing is put on the drive, and the edit
door refuses the run. A finished run carries production-done.json (the clips made), which the edit door checks.
Exit 0 only when every step finished and the hand-off completed.

--dry-run runs production's own --dry-run on the brief (every gate, nothing spent); nothing is put on
the drive. Every run starts without CLAUDECODE in the environment, or production takes the
Higgsfield route.
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
TD = REPO / "tools" / "video-teardown" / "machine"
sys.path.insert(0, str(REPO / "components" / "run-kit"))


def finished(work):
    """A brief production may take: stage 5 done on run.json and the swipe match PASSED on the brief itself.
    (Review, 19 Oct: a reused label's old brief must never reach production.)"""
    try:
        st = json.loads((work / "run.json").read_text())
        brief = (work / "stages" / "5-brief.md").read_text()
    except (OSError, ValueError):
        return False
    return ((st.get("stages") or {}).get("stage5") or {}).get("status") == "done" and "swipe-match: PASSED" in brief[:400]


def rebuild_frames(work):
    """framemap/frames/ and framemap/elements/ stay on the machine that tore the swipe down (2026-10-20,
    worklist 7b option (i)), so a run fetched here has neither — and production would QUIETLY fall back:
    full_frame() to the shot still, swipe_frames() to no crops (cleanup proof, item 3). Rebuild both from
    source.mp4 + framemap.json the way `framemap.py <run> --frames-only` does: no model, nothing on the Drive."""
    fm = work / "framemap"
    if not (fm / "framemap.json").is_file() or not (work / "source.mp4").is_file():
        return
    sys.path.insert(0, str(TD))
    import json as _json
    if not (fm / "frames" / "index.json").is_file():
        import framemap as FM
        doc = _json.loads((fm / "framemap.json").read_text())
        rows = FM.extract_frames(work / "source.mp4", doc["shots"], fm, 4)
        print("source: frames/ rebuilt here from source.mp4 + framemap.json — %d frames "
              "(identical picks to the teardown's own: cleanup proof item 5)" % len(rows))
    # elements/ only when it is missing: a rebuild is deterministic today but NOT what an older
    # teardown made (cleanup proof item 5: 13 of 39 elements differed), so a copy that came with
    # the run is never overwritten
    if not (fm / "elements" / "index.json").is_file():
        import frame_elements as FE
        idx = FE.build(work)
        print("source: elements/ rebuilt here from the frames — %d elements (may differ from the "
              "teardown machine's own crops)" % len(idx["elements"]))


def writing_folder(brand, label):
    sys.path.insert(0, str(TD))
    import chain as C
    work = C.runs_root() / label                  # the runs tree, never a temp folder: paths stay valid after the job
    if not finished(work):
        # LD-53 (station-path runner): the writing run from the repo copy first (laid over a working
        # folder that has no finished brief), the teardown's repo copy filling gaps, then Shared Assets
        # for the media production reads — every source printed and kept on the work copy.
        from run_kit.station import resolve
        resolve("video-writing", brand, label, work, also=("video-teardown",),
                want=("source.mp4", "framemap/shots"), overwrite=(work / "run.json").is_file())
    rebuild_frames(work)
    if not finished(work):
        raise SystemExit("no finished brief for %r (%s) here or on Shared Assets runs/video-writing/%s/%s — stage 5 "
                         "must be done and its swipe match PASSED; run or approve the writing station first"
                         % (label, brand, brand, label))
    return work


def unmade_clips(run):
    """Every clip clips/plan.json lists that is not made (ledger 'done' + clips/<id>.mp4) — [] = complete. A run with
    no clip plan is unmade as a whole."""
    run = Path(run)
    try:
        plan = json.loads((run / "clips" / "plan.json").read_text())
    except (OSError, ValueError):
        return ["clips/plan.json"]
    try:
        _lf = run / "clips" / "ledger.json"          # (a run made before 2026-10-26 keeps clips/omni-ledger.json)
        led = json.loads((_lf if _lf.exists() else run / "clips" / "omni-ledger.json").read_text())
    except (OSError, ValueError):
        led = {}
    ids = [c.get("id") for c in plan.get("calls") or [] if c.get("id")]
    if not ids:
        return ["clips/plan.json lists no clips"]
    return [i for i in ids if (led.get(i) or {}).get("status") != "done" or not (run / "clips" / ("%s.mp4" % i)).is_file()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--format")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    a = ap.parse_args(argv)
    work = writing_folder(a.brand, a.label)
    brief = work / "stages" / "5-brief.md"
    st = json.loads((work / "run.json").read_text())
    fmt = a.format or (st.get("layers") or {}).get("format") or st.get("format_id") or "demonstration"
    root = REPO / "runs"
    run = root / "video-production" / a.brand / a.label
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    env["DISABLE_PROMPT_CACHING"] = "1"
    base = [sys.executable, str(HERE / "run_v2.py")]
    common = ["--brand", a.brand, "--format", fmt, "--label", a.label, "--runs-root", str(root)]
    if a.dry:
        return subprocess.run(base + ["start", str(brief)] + common + ["--dry-run"],
                              cwd=str(HERE.parent), env=env).returncode
    steps = [
        ("voice → storyboard → listed pictures → clip plan", base + ["start", str(brief)] + common + ["--yes"]),
        ("clips: three takes each, the best picked", base + ["clips", str(run), "--yes"]),
    ]
    failed = None
    for name, cmd in steps:
        print("== %s" % name, flush=True)
        if subprocess.run(cmd, cwd=str(HERE.parent), env=env).returncode != 0:
            failed = name
            break
    done = run / "production-done.json"
    if done.is_file():
        done.unlink()                           # an older run's mark never vouches for this one
    if not failed and run.is_dir():
        left = unmade_clips(run)
        if left:
            failed = "clips not all made (%d): %s" % (len(left), ", ".join(left)[:300])
    if failed:
        # NOTHING PARTIAL IS HANDED ON (row 15): the run stays on this machine for a look; the drive is not touched
        if run.is_dir():
            shutil.copytree(str(run), str(Path(a.out)), symlinks=False, dirs_exist_ok=True)
        print("production stopped at: %s — nothing handed on to the edit" % failed, file=sys.stderr)
        return 1
    if not run.is_dir():
        print("production made no run folder at %s — nothing handed on" % run, file=sys.stderr)
        return 1
    plan = json.loads((run / "clips" / "plan.json").read_text())
    done.write_text(json.dumps({"status": "done", "label": a.label, "brand": a.brand,
                                "clips": [c["id"] for c in plan.get("calls") or [] if c.get("id")]}, indent=1))
    shutil.copytree(str(run), str(Path(a.out)), symlinks=False, dirs_exist_ok=True)
    from run_kit.station import push
    res = push(run, "video-production", a.brand, a.label, copy_to=a.out)
    print("handed on: %d file(s) to %s%s" % (res["placed"], res["to"],
          "" if not res["notes"] else " · " + "; ".join(res["notes"])[:400]))
    if res["notes"]:
        print("the hand-off to Shared Assets did not complete — the edit station would read a partial run",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
