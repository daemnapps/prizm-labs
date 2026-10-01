#!/usr/bin/env python3
"""Where things live. One file, so no tool guesses a path.

The workspace root is `AI_WORKSPACE` when it is set (a worktree, a test),
otherwise found by walking up — never counted with parents[N].
"""
import os
from pathlib import Path

MACHINE = Path(__file__).resolve().parent.parent      # copy-teardown
TOOL = "copy-teardown"                                 # the name we say out loud


def _repo():
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    for d in MACHINE.parents:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError("no workspace found upward of " + str(MACHINE))


REPO = _repo()
BRANDS = REPO / "brands"
RECORDS = REPO / "runs" / TOOL                         # runs/copy-teardown/<brand>/<label>/
PROMPTS = MACHINE / "prompts"
RUN_KIT = REPO / "components" / "run-kit"
QUALITY = REPO / "components" / "quality-checks"
ELEMENTS = REPO / "components" / "elements"


def record_dir(brand, label):
    """Where a teardown run files: runs/copy-teardown/<brand>/<label>/ at the
    repo root. Named here, made by the runner — never by a dry run."""
    return RECORDS / brand / label


def known_brands():
    if not BRANDS.is_dir():
        return []
    return sorted(p.name for p in BRANDS.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))
