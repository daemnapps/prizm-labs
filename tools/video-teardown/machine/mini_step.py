#!/usr/bin/python3
"""Station 1 on the mini: a swipe in, the v2 teardown (stages 0 → 2) out, handed on through Shared Assets.

    mini_step.py --brand <b> --label <l> (--url <post link> | --video <repo or Shared Assets path>)
                 --route ai|creator [--lane paid|organic] [--product <p>] --out <dir> [--dry-run]

The lab door (lab_door.json beside this) calls it; a person can too. It runs the teardown v2 chain
to the end of stage 2 (the audience read included, so writing can start on the route), copies the
run folder into --out, and PUTS it on Shared Assets at runs/video-teardown/<brand>/<label>/ so the
writing station's job finds it by the same label (run_kit.station). Exit 0 only when stage 2 is done.

--dry-run resolves the whole plan and spends nothing (the teardown's own --dry-run); nothing is
put on the drive.
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
YES = {"yes", "true", "1"}


def get_video(a, tmp):
    if a.url:
        out = Path(tmp) / "swipe.mp4"
        subprocess.run(["yt-dlp", "-q", "-f", "mp4/best", "-o", str(out), a.url], check=True,
                       stdout=subprocess.DEVNULL, timeout=600)
        return out
    p = Path(a.video)
    for cand in (p, REPO / p):
        if cand.is_file():
            return cand.resolve()
    from run_kit.station import _reach
    parts = list(p.parent.parts)
    if parts and parts[0].lower() == "shared assets":   # "Shared Assets/swipe/…" names the drive root itself
        parts = parts[1:]
    got = _reach().get(parts, p.name, tmp)
    if got:
        return Path(got)
    raise SystemExit("no swipe at %s (not in this checkout, not on Shared Assets)" % a.video)


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


def work_dir(label, C=None):
    """The teardown's working folder for this door label. run.py names it chain.run_slug(label) —
    label--<operator> for anyone but the owner — so look there first; when that folder holds no
    run.json, the bare label folder (the behaviour before LD-68 (teardown door finds run))."""
    if C is None:
        sys.path.insert(0, str(HERE))
        import chain as C
    root = C.runs_root(create=False)
    mine = root / C.run_slug(label)
    if (mine / "run.json").is_file():
        return mine
    return root / label


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--url")
    ap.add_argument("--video")
    ap.add_argument("--route", required=True, choices=["ai", "creator", "founder"])
    ap.add_argument("--lane", default="paid", choices=["paid", "organic"])
    ap.add_argument("--product")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    a = ap.parse_args(argv)
    fetch_calls()
    if bool(a.url) == bool(a.video):
        raise SystemExit("give exactly one of --url or --video")
    dry = a.dry
    with tempfile.TemporaryDirectory() as tmp:
        video = get_video(a, tmp)
        print("source: swipe video from %s" % (a.url or a.video))    # LD-53 (station-path runner): every run says where it came from
        cmd = [sys.executable, str(HERE / "run.py"), str(video), "--brand", a.brand, "--label", a.label,
               "--v2", "--route", a.route, "--lane", a.lane, "--to", "2", "--again"]
        if a.product:
            cmd += ["--product", a.product]
        if a.url:
            cmd += ["--post-url", a.url]
        if dry:
            cmd += ["--dry-run"]
        env = dict(os.environ, VT_CHAIN="v2", DISABLE_PROMPT_CACHING="1")
        r = subprocess.run(cmd, cwd=str(HERE), env=env)
        if dry:
            return r.returncode
        sys.path.insert(0, str(HERE))
        import chain as C
        work = work_dir(a.label, C)
        st = json.loads((work / "run.json").read_text()) if (work / "run.json").is_file() else {}
        done = (st.get("stages") or {}).get("stage2", {}).get("status") == "done"
        out = Path(a.out)
        if work.is_dir():
            shutil.copytree(str(work), str(out), symlinks=False, dirs_exist_ok=True)
            from run_kit.station import push
            res = push(work, "video-teardown", a.brand, a.label, skip=C.NOT_ON_DRIVE, copy_to=out)   # 7b option (i)
            print("handed on: %d file(s) to %s%s" % (res["placed"], res["to"],
                  "" if not res["notes"] else " · " + "; ".join(res["notes"])[:400]))
            if res["notes"]:                    # a partial hand-off is a failed one (review, 19 Oct)
                return 1
        if not done:
            print("teardown stopped before stage 2 was done — %s" % (st.get("stopped_at") or "see the log"),
                  file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(main())
