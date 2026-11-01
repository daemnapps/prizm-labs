#!/usr/bin/python3
"""Station 2 on the mini: the teardown's run in, the v2 writing (stages 3 → 5) and its brief checks out,
handed on through Shared Assets.

    mini_step.py --brand <b> --label <l> --out <dir> [--route ai|creator|founder] [--dry-run]

<l> is the label the teardown station used; the run folder is fetched from Shared Assets
runs/video-teardown/<brand>/<l>/ unless this machine already holds it. Writing runs on it (writing_v2,
then the swipe match when the brief has no PASSED stamp yet), the folder is copied into --out and PUT
on Shared Assets at runs/video-writing/<brand>/<l>/ for the production station (run_kit.station).
Exit 0 only when 5-brief.md is written and its swipe match PASSED; a brief held for the owner's call
exits 1 and says so.

--dry-run fetches the teardown and checks that every writing pass resolves (every {slot} bound,
the teardown's stages done) and spends nothing; nothing is put on the drive.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TD = REPO / "tools" / "video-teardown" / "machine"
sys.path.insert(0, str(REPO / "components" / "run-kit"))
NEEDED = ("stage0", "stage1", "stage1b", "stage1c", "stage2")


def teardown_folder(brand, label):
    sys.path.insert(0, str(TD))
    import chain as C
    work = C.runs_root() / label
    # LD-53 (station-path runner): the working folder, then the repo copy, then Shared Assets for the
    # swipe video — every source printed and kept on the work copy. A run taken from the repo or the
    # Drive keeps only the teardown's stages (0–2), so writing starts clean; the repo file is untouched.
    from run_kit.station import resolve
    resolve("video-teardown", brand, label, work, want=("source.mp4",),
            keep_stage=lambda k: bool(re.match(r"stage[012](?![0-9])", k)))
    # Stage 1b (audience) is a teardown stage whose file the shelves file under video-writing
    # (found 2026-10-20 on batchtest-skin): bring that ONE file, and its prompt, from the writing
    # shelf when the run says 1b is done and the work copy lacks it. Never the writing shelf's other
    # files — a stale 5-brief.md must never look like this run's brief.
    import shutil
    st = json.loads((work / "run.json").read_text())
    out = ((st.get("stages") or {}).get("stage1b") or {}).get("out") or "stages/1b-audience.md"
    shelf = REPO / "runs" / "video-writing" / brand / label
    for rel in (out, "prompts/" + Path(out).name):
        if not (work / rel).is_file() and (shelf / rel).is_file():
            (work / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(shelf / rel), str(work / rel))
            print("source: repo runs/video-writing/%s/%s/%s (the stage-1b file)" % (brand, label, rel))
    return work


def dry(work, brand):
    st = json.loads((work / "run.json").read_text())
    S = st.get("stages") or {}
    bad = [k for k in NEEDED if (S.get(k) or {}).get("status") != "done"]
    route = (st.get("production_route") or "").lower()
    sys.path.insert(0, str(HERE))
    import writing_v2 as W
    unbound = []
    for p in W.plan(brand, route or "ai", st.get("triage_lane") or ""):
        asks = set(re.findall(r"\{([a-z0-9_]+)\}", Path(p["prompt"]).read_text()))
        unbound += ["%s {%s}" % (p["key"], a) for a in sorted(asks - set(p["vars"]))]
    print("teardown stages not done: %s" % (", ".join(bad) or "none"))
    print("route: %s%s" % (route or "(none)", "" if route == "ai" else " — writes on v1 (v2 has only the AI brief)"))
    print("writing slots unbound: %s" % (", ".join(unbound) or "none"))
    ok = not bad and bool(route) and not unbound
    print("dry run: %s — 0 model calls made" % ("everything resolves" if ok else "NOT ready"))
    return 0 if ok else 1


def fetch_calls():
    """the owner's format calls from Shared Assets runs/video-teardown/format-calls.json (Outlier copies
    them there), so a call he made on his Mac releases a held run here too (2026-10-19)."""
    import tempfile as _t
    try:
        from run_kit.station import get_shared
        with _t.TemporaryDirectory() as tmp:
            got = get_shared("format-calls.json", "video-teardown", tmp)
            if not got:
                return
            theirs = json.loads(Path(got).read_text())
        mine_p = REPO / "runs" / "video-teardown" / "format-calls.json"
        mine = json.loads(mine_p.read_text()) if mine_p.is_file() else {}
        merged = dict(theirs, **mine)          # merged, never lost: a call on this machine wins
        if merged != mine:
            mine_p.parent.mkdir(parents=True, exist_ok=True)
            mine_p.write_text(json.dumps(merged, indent=1))
    except Exception as e:  # noqa: BLE001
        print("format calls not fetched from Shared Assets: %s" % e, file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--route", choices=["ai", "creator", "founder"],
                    help="the route to write on; default the run's own production_route. Set on the WORK copy only")
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    a = ap.parse_args(argv)
    fetch_calls()
    work = teardown_folder(a.brand, a.label)
    if a.route:
        # LD-53 (station-path runner): the repo copy's route is the one it was torn down on; a later
        # run may write on another (the team, 2026-10-20: the AI run off the owner's creator baseline). The
        # WORK copy changes, never the repo file, and the source lines say so.
        st = json.loads((work / "run.json").read_text())
        was = st.get("production_route") or "(none)"
        if was != a.route:
            st["production_route"] = a.route
            st.setdefault("sources", []).append("route set by the door: %s (the copy had %s)" % (a.route, was))
            (work / "run.json").write_text(json.dumps(st, indent=2))
        print("source: route set by the door: %s (the copy had %s)" % (a.route, was))
    if a.dry:
        return dry(work, a.brand)
    env = dict(os.environ, VT_CHAIN="v2", DISABLE_PROMPT_CACHING="1")
    st = json.loads((work / "run.json").read_text())
    route = (st.get("production_route") or "ai").lower()
    if route == "ai":
        r = subprocess.run([sys.executable, str(HERE / "run.py"), str(work)], cwd=str(HERE), env=env)
    else:
        # creator / founder: v2 has only the AI brief, so these write on v1 — the teardown's own stage loop,
        # stages 3 → 5 on this run (review, 19 Oct: they used to stop here on the mini)
        video = st.get("video") if st.get("video") and Path(st["video"]).is_file() else str(work / "source.mp4")
        cmd = [sys.executable, str(TD / "run.py"), video, "--label", a.label, "--brand", a.brand, "--route", route,
               "--v2", "--from", "3", "--to", "5"]
        if st.get("product"):
            cmd += ["--product", str(st["product"])]
        r = subprocess.run(cmd, cwd=str(TD), env=env)
    brief = work / "stages" / "5-brief.md"
    if brief.is_file() and "swipe-match: PASSED" not in brief.read_text()[:400]:
        subprocess.run([sys.executable, str(HERE / "swipe_match.py"), str(work)], cwd=str(TD), env=env)
    passed = brief.is_file() and "swipe-match: PASSED" in brief.read_text()[:400]
    shutil.copytree(str(work), str(Path(a.out)), symlinks=False, dirs_exist_ok=True)
    from run_kit.station import push
    res = push(work, "video-writing", a.brand, a.label, copy_to=a.out)
    print("handed on: %d file(s) to %s%s" % (res["placed"], res["to"],
          "" if not res["notes"] else " · " + "; ".join(res["notes"])[:400]))
    if res["notes"]:
        print("the hand-off to Shared Assets did not complete — production would read a partial run", file=sys.stderr)
        return 1
    if r.returncode != 0 or not passed:
        print("writing did not finish a brief that passed its swipe match — "
              + ("no brief" if not brief.is_file() else "held for the owner's call (SWIPE-MATCH.md / AUDIT-HOLD.md)"),
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
