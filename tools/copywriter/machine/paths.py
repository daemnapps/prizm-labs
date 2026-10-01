#!/usr/bin/env python3
"""Where this build is, and where the brand context it reads lives.

Graduated into the workspace 2026-08-26, so build and brand context now sit
in one tree — but they are still resolved separately on purpose. This tool
was written in daemn against a workspace it could not see, and keeping the
two named rather than derived is what let it move without breaking. Deriving
either by counting folders up from this file is what broke it the first time.

Override the brand tree with AI_WORKSPACE=/some/path, or --brand-root for a
one-off. Both still work from anywhere.

SHIM (BH-1, 2026-09-02). The LOCATOR — env override, else the named default —
moved to `components/brand-finder/` so rule-9's "where is brands/" has one
home; it had three, converging by copy-paste. This file is the same file it
always was: same names, same answers, same command. **The default below stays
HERE**, because it is this machine's own policy: it differs from
`email-production/paths.py`'s, and BH-1 forbids a shared locator
picking a winner between them. The component has no default of its own.
"""

import sys
from pathlib import Path

# The package root — machine/ code lives one level below it, and every
# station (bank, prompts, results, output, pages, library) hangs off it.
HERE = Path(__file__).resolve().parent.parent

_DEFAULT_WS = Path.home() / "Projects" / "ai-workspace"

_COMPONENT = next((d for d in Path(__file__).resolve().parents if (d / "components" / "brand-finder").is_dir()), Path(__file__).resolve().parents[2].parent) / "components" / "brand-finder"
if not _COMPONENT.is_dir():                  # a workspace mounted elsewhere
    _COMPONENT = _DEFAULT_WS / "components" / "brand-finder"
sys.path.append(str(_COMPONENT))        # appended, never ahead of this machine
import brand_finder as _finder               # noqa: E402


def workspace():
    """The tree brand context is read from. Named, never guessed."""
    return Path(_finder.workspace(_DEFAULT_WS))


WORKSPACE = workspace()


# ---------------------------------------------------------------- run folders
# WHERE A RUN LIVES (rollout, 2026-09-20). New runs file at the repo root —
# `runs/copy-machine/<brand>/<label>/` (runs/README.md; that folder name is the
# spoken one and is fixed). `results/<label>/` beside the code is HISTORY: it
# is still read everywhere a run is looked up, and never written to again.
# Every reader goes through the functions below, so no page can see only one.
TOOL = "copy-machine"
RESULTS = HERE / "results"


def repo():
    """The repo root runs/ hangs off — found by walking up, never counted."""
    for d in Path(__file__).resolve().parents:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    return WORKSPACE


RUNS = repo() / "runs" / TOOL


def run_dir(brand, label):
    """The home of a NEW run. Not created here — a dry run leaves no trace."""
    return RUNS / brand / label


def all_runs():
    """Every current run folder, from both homes. runs/ wins when a label is in
    both (a carried-over run continues in its new home). No archives."""
    seen, out = set(), []
    if RUNS.is_dir():
        for b in sorted(p for p in RUNS.iterdir()
                        if p.is_dir() and not p.name.startswith((".", "_"))):
            for d in sorted(p for p in b.iterdir() if p.is_dir()):
                if d.name not in seen:
                    seen.add(d.name)
                    out.append(d)
    if RESULTS.is_dir():
        for d in sorted(p for p in RESULTS.iterdir() if p.is_dir()):
            if not d.name.startswith("archive") and d.name not in seen:
                seen.add(d.name)
                out.append(d)
    return out


def find_run(label, brand=None):
    """One run by label: runs/copy-machine/<brand>/<label> first, then
    results/<label>. None when neither home has it."""
    if RUNS.is_dir():
        homes = [RUNS / brand] if brand else sorted(p for p in RUNS.iterdir() if p.is_dir())
        for b in homes:
            if (b / label).is_dir():
                return b / label
    if (RESULTS / label).is_dir():
        return RESULTS / label
    return None
