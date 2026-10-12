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
`the team notes`'s, and BH-1 forbids a shared locator
picking a winner between them. The component has no default of its own.
"""

import sys
from pathlib import Path

# The package root — machine/ code lives one level below it, and every
# station (bank, prompts, results, output, pages, library) hangs off it.
HERE = Path(__file__).resolve().parent.parent

# The checkout this file sits in (<ws>/tools/copywriter/machine/) — found
# by walking up to the folder that holds both components/ and brands/, never
# a home-folder guess. AI_WORKSPACE still wins (brand-finder's rule).
_DEFAULT_WS = next((d for d in Path(__file__).resolve().parents
                    if (d / "components").is_dir() and (d / "brands").is_dir()),
                   Path(__file__).resolve().parents[3])

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
# `runs/copywriter/<brand>/<label>/` (runs/README.md; that folder name is the
# spoken one — the owner ruled `copywriter` 2026-09-21, replacing `copy-machine`). `results/<label>/` beside the code is HISTORY: it
# is still read everywhere a run is looked up, and never written to again.
# Every reader goes through the functions below, so no page can see only one.
TOOL = "copywriter"
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


def find_archived(slug):
    """A parked run by slug, from whichever archive container holds it."""
    for a in archive_dirs():
        d = a / slug
        if d.is_dir():
            return d
    return RESULTS / "archive-v1-chain" / slug      # the old shape, for a caller that expects a path


def archive_dirs():
    """Every `archive*` container holding parked runs, in BOTH homes.

    Archived runs used to sit only in `results/archive-v1-chain/`. The 2026-09-22
    sweep moved them to `runs/copywriter/<brand>/`, so a reader that globs only
    RESULTS now finds nothing — silently, because an empty glob is not an error.
    Go through here instead of either constant.
    """
    out = []
    if RESULTS.is_dir():
        out += [a for a in sorted(RESULTS.glob("archive*")) if a.is_dir()]
    if RUNS.is_dir():
        for brand in sorted(b for b in RUNS.iterdir() if b.is_dir()):
            out += [a for a in sorted(brand.glob("archive*")) if a.is_dir()]
    return out


OUTPUT = HERE / "output"            # HISTORY: published per source before 2026-09-21


def all_deliverables():
    """Every published deliverable, from BOTH homes, newest home first.

    Since 2026-09-21 (the owner: "finished copy goes in runs") publish.py writes
    `<run>/deliverable/`. `output/<source-slug>/` holds everything published
    before that and is still read, never written — the same arrangement
    `results/` has with `runs/`. Readers go through here so no page can see
    only one home and quietly go stale.

    Yields (name, folder) where folder holds copy.md / v*.md / source.md.
    """
    seen, out = set(), []
    for run in all_runs():
        d = run / "deliverable"
        if (d / "copy.md").is_file():
            seen.add(run.name)
            out.append((run.name, d))
    if OUTPUT.is_dir():
        for d in sorted(p for p in OUTPUT.iterdir() if p.is_dir()):
            if d.name not in seen and (d / "copy.md").is_file():
                seen.add(d.name)
                out.append((d.name, d))
    return out


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
    """One run by label: runs/copywriter/<brand>/<label> first, then
    results/<label>. None when neither home has it."""
    if RUNS.is_dir():
        homes = [RUNS / brand] if brand else sorted(p for p in RUNS.iterdir() if p.is_dir())
        for b in homes:
            if (b / label).is_dir():
                return b / label
    if (RESULTS / label).is_dir():
        return RESULTS / label
    return None
