#!/usr/bin/env python3
"""Where the page machine is, where the workspace is, and where a run lives.

Found by walking up, never counted: `AI_WORKSPACE` first (a worktree or a
workspace mounted elsewhere), else the first folder upward holding both
`components/` and `brands/`.

WHERE A RUN LIVES (rollout, 2026-09-20). New runs file at the repo root —
`runs/page-machine/<brand>/<label>/` (that folder name is fixed). `runs/`
beside the code is the OLD home: it is still read everywhere a run is looked
up, and nothing new is written there. Every reader goes through `find_run` /
`all_runs`, so no page sees only one home.

Named page_paths, not paths: the copy machine's `context.py` does
`from paths import …`, and this folder is first on sys.path when run.py runs.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent            # the tool's own folder
TOOL = "page-machine"


def repo():
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env).expanduser() / "brands").is_dir():
        return Path(env).expanduser()
    for d in Path(__file__).resolve().parents:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    sys.exit("no workspace found: set AI_WORKSPACE to the folder holding brands/ and components/")


WORKSPACE = repo()


def identity_dir(brand):
    """The brand's look: brand-identity/ (the v6 folder name), else the old identity/."""
    b = WORKSPACE / "brands" / brand
    return next((b / n for n in ("brand-identity", "identity") if (b / n).is_dir()),
                b / "brand-identity")
RUNS = WORKSPACE / "runs" / TOOL                         # runs/page-machine/<brand>/<label>/
OLD_RUNS = HERE / "runs"                                 # read, never written to again


def run_dir(brand, label):
    """The home of a NEW run."""
    return RUNS / brand / label


def all_runs():
    """Every run folder, from both homes. The repo-root home wins when a label
    is in both."""
    seen, out = set(), []
    if RUNS.is_dir():
        for b in sorted(p for p in RUNS.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
            for d in sorted(p for p in b.iterdir() if p.is_dir()):
                if d.name not in seen and (d / "run.json").exists():
                    seen.add(d.name); out.append(d)
    if OLD_RUNS.is_dir():
        for d in sorted(p for p in OLD_RUNS.iterdir() if p.is_dir()):
            if d.name not in seen and (d / "run.json").exists():
                seen.add(d.name); out.append(d)
    return out


def find_run(label, brand=None):
    """One run by label: runs/page-machine/<brand>/<label> first, then the old
    home. None when neither has it."""
    if RUNS.is_dir():
        homes = [RUNS / brand] if brand else sorted(p for p in RUNS.iterdir() if p.is_dir())
        for b in homes:
            if (b / label).is_dir():
                return b / label
    if (OLD_RUNS / label).is_dir():
        return OLD_RUNS / label
    return None


def need_run(label, brand=None):
    """find_run, or a plain refusal naming both homes."""
    d = find_run(label, brand)
    if d is None:
        sys.exit(f"no run `{label}` — looked in {rel(RUNS)}/<brand>/ and {rel(OLD_RUNS)}/")
    return d


def rel(p):
    """A path as the workspace spells it, for anything a person reads."""
    try:
        return str(Path(p).relative_to(WORKSPACE))
    except ValueError:
        return str(p)
