#!/usr/bin/env python3
"""Where things live. One file, so no tool guesses a path.

Paths are FOUND by walking up (or taken from `AI_WORKSPACE` — a worktree, a
test), never counted with parents[N]. Nothing here names a brand: a brand is a
folder under `brands/`, named at run time by `--brand`.
"""
import os
from pathlib import Path

MACHINE = Path(__file__).resolve().parent.parent      # this tool's own folder
TOOL = "page-teardown"                                # the name we say out loud


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
RECORDS = REPO / "runs" / TOOL                         # runs/page-teardown/<brand>/<label>/
PROMPTS = MACHINE / "prompts"
RUN_KIT = REPO / "components" / "run-kit"
QUALITY = REPO / "components" / "quality-checks"
ELEMENTS = REPO / "components" / "elements"
CLASSIFIER = REPO / "components" / "naming" / "classify_pages.py"   # called, never edited


def record_dir(brand, label):
    """Where a teardown run files: runs/page-teardown/<brand>/<label>/ at the
    repo root. Named here, made by the runner — never by a dry run."""
    return RECORDS / brand / label


def known_brands():
    if not BRANDS.is_dir():
        return []
    return sorted(p.name for p in BRANDS.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))


def rel(path):
    try:
        return str(Path(path).resolve().relative_to(REPO.resolve()))
    except ValueError:
        return str(path)
