#!/usr/bin/env python3
"""The Creator lane at Produce (owner, 16 Nov 2026): a creator films this idea. The swipe's own teardown is reused, the
creator brief is written from it, and the brief joins the brand's creator hub as a draft, open to every creator (briefs
are decentralised: any creator on any of the brand's payout programs can pick one up). Nothing is sent: a draft shows
to creators only after the owner's yes in the hub.

    python3 creator_lane.py <writing run label>        branch, write, add to the hub; prints one JSON line

Steps:
1. branch(run): a sibling working run `<run>-creator` with the teardown stages (0 to 2) and their files only, so the
   AI lane's storyboard (its stage 5) is never touched and nothing already read is paid for again.
2. write(label, brand): the teardown machine's creator line from stage 3 (`line.py creator --label`), which files
   `runs/video-writing/<brand>/<label>/brief--video--creator.md` (components/briefs/creator-brief/README.md).
3. to_hub(brand, page, label): `hub.py --add` as a draft, open to all programs (no --open-to = every program).
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

WS = Path(os.environ.get("VIDEO_STUDIO_WRITING") or ST.WRITING).resolve().parents[2]   # the workspace whose runs these are
WORK = WS / "runs" / "video-teardown" / "_work"
KEEP_STAGES = ("stage0", "stage1", "stage1b", "stage1c", "stage1k", "stage2")
KEEP_RUN = ("brand", "product", "source", "video", "opened", "poster", "format_id", "style_id", "doctrine", "elements",
            "audience", "venue", "market_state", "triage_lane", "library", "layers", "_order")
WRITTEN = re.compile(r"^(?:[3-8][a-z0-9-]*|5-brief.*|7b.*)\.(?:md|json)$")
SKIP_TOP = {"revalidation", "section-fit", "section-fit-revalidation", "writing-result.json", "viewer-panel.json",
            "manifest.json", "manifest-reviews", "hook-matrix.json", "RULINGS.md", "deliverable", "stamps"}


def branch(run):
    """The creator sibling of a writing run: teardown only. Returns its label (made once; kept if it exists)."""
    src = WORK / run
    if not (src / "run.json").is_file():
        raise SystemExit("no writing run %s" % run)
    label = run + "-creator"                 # one dash: the chain's own slug for a label
    dst = WORK / label
    if (dst / "run.json").is_file():
        return label
    dst.mkdir(parents=True)
    for p in src.iterdir():
        if p.name in SKIP_TOP or (p.name.startswith(("HOOK-", "SWIPE-", "STRUCTURE-", "AUDIT-", "storyboard-footage"))
                                  and not p.name.endswith("-approved.md")):   # the owner's approvals of this swipe carry over
            continue
        if p.name == "stages":
            (dst / "stages").mkdir()
            for f in p.iterdir():
                if f.is_file() and not WRITTEN.match(f.name) and not f.name.startswith("storyboard-footage"):
                    shutil.copy2(f, dst / "stages" / f.name)
            continue
        if p.name == "run.json":
            continue
        (shutil.copytree if p.is_dir() else shutil.copy2)(p, dst / p.name)
    st = json.loads((src / "run.json").read_text())
    keep = {k: st[k] for k in KEEP_RUN if k in st}
    keep["stages"] = {k: v for k, v in (st.get("stages") or {}).items() if k in KEEP_STAGES}
    keep["label"] = keep["slug"] = label
    keep["branched_from"] = run
    (dst / "run.json").write_text(json.dumps(keep, indent=1, ensure_ascii=False))
    return label


def write(label, brand):
    """The creator line from stage 3; returns the filed brief's repo-relative path, or raises with its tail."""
    machine = WS / "components" / "video-teardown" / "machine"      # the workspace's own chain, where its runs live
    r = subprocess.run([sys.executable, str(machine / "line.py"), "creator", "--label", label, "--brand", brand],
                       cwd=str(machine), capture_output=True, text=True, timeout=3600, env=dict(os.environ))
    page = WS / "runs" / "video-writing" / brand / label / "brief--video--creator.md"
    if not page.is_file():
        here = WORK / label / "brief--video--creator.md"
        if here.is_file():
            return str(here.relative_to(WS))
        raise RuntimeError("the creator brief was not written: " + ((r.stderr or r.stdout or "")[-300:]).strip())
    return str(page.relative_to(WS))


def to_hub(brand, page, label):
    """Add the brief to the brand's creator hub as a draft open to every program; returns the hub's answer line."""
    hub = WS / "lab" / "owner" / "creator-machine" / "machine" / "hub.py"
    r = subprocess.run([sys.executable, str(hub), "--brand", brand, "--add", page, "--id", label,
                        "--made-by", "studio · creator lane", "--preview"],
                       cwd=str(hub.parent), capture_output=True, text=True, timeout=300, env=dict(os.environ))
    if r.returncode:
        raise RuntimeError("the creator hub refused it: " + (r.stderr or r.stdout or "")[-300:])
    return (r.stdout or "").strip().splitlines()[0] if r.stdout else "added"


def main(run):
    brand = json.loads((WORK / run / "run.json").read_text()).get("brand")
    label = branch(run)
    page = write(label, brand)
    said = to_hub(brand, page, label)
    print(json.dumps({"label": label, "page": page, "hub": said}))


if __name__ == "__main__":
    main(sys.argv[1])
