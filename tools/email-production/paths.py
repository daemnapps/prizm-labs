#!/usr/bin/env python3
"""Where the email system is, and where the brand context it reads lives.

The tool lives in daemn — the owner's repo, where he builds and tests. The brand
context it reads lives in the shared workspace, read-only, the same way
his chain-variables map points into it. Those are two different trees, so
neither path may be derived by counting folders up from this file: that is
why this is named rather than derived by counting folders up from this file.

Override the brand tree with AI_WORKSPACE=/some/path when it moves, or pass
--brand-root to the runner for a one-off.

SHIM (BH-1, 2026-09-02). The LOCATOR — env override, else the named default —
moved to `components/brand-finder/` so rule-9's "where is brands/" has one
home; it had three, and this file's copy came from copy.py's. This file is the
same file it always was: same names, same answers, same command. **The default
below stays HERE**, because it is this machine's own policy. RULED 2026-09-09
(the owner, "it lives in the repo and everything's reflective"): the repo root,
the same as `lab/copy/machine/paths.py` — the BH-1 divergence is closed. That divergence is written
down for the 09-03 the owner batch in
`new-workflow-design/builds/brand-home/DIVERGENCE.md`; nothing here decided it.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The tree that CONTAINS brands/ — the lab, not the repo root. Both this
# runner and copy's context.py resolve <root>/brands/<brand>, so they must be
# handed the same root or the scout indexes a different tree than the one
# the runner reads (which is exactly what broke the first Brand B attempt).
_DEFAULT_WS = next((d for d in Path(__file__).resolve().parents if (d / "brands").is_dir()), Path("."))      # brands/ at the repo root (the owner, 2026-09-09)

# FOUND, never counted: this folder moved lab/email-production ->
# tools/email-production on 2026-09-19, and parents[3] silently pointed one
# level too high the moment it did.
_REPO = next((d for d in Path(__file__).resolve().parents if (d / "components" / "brand-finder").is_dir()), None)
_COMPONENT = (_REPO / "components" / "brand-finder") if _REPO else None
if not _COMPONENT:                           # a workspace mounted elsewhere
    _COMPONENT = _DEFAULT_WS / "components" / "brand-finder"
sys.path.append(str(_COMPONENT))        # appended, never ahead of this machine
import brand_finder as _finder               # noqa: E402


def workspace():
    """The tree brand context is read from. Named, never guessed."""
    return Path(_finder.workspace(_DEFAULT_WS))


WORKSPACE = workspace()


def calendar_tool(sub=""):
    """The marketing-calendar tool's folder, FOUND rather than counted.

    That tool moved from this folder into `components/` and back into `lab/`
    inside one day, and every `parents[N]` pointing at it broke on each move —
    silently, because a wrong path only means a file "isn't there". So look for
    it instead: up the tree, in the places it actually lives. Returns None when
    it genuinely is not there, which is a real answer and not a crash.
    """
    here = Path(__file__).resolve()
    for d in [here.parent, *here.parents]:
        for cand in (d / "marketing-calendar",
                     d / "lab" / "marketing-calendar",
                     d / "components" / "marketing-calendar"):
            if (cand / (sub or "machine")).exists():
                return cand / sub if sub else cand
    return None


def component(*parts):
    """A sibling component, found by walking up — never counted."""
    parts = (_PUBLIC_NAME.get(parts[0], parts[0]),) + tuple(parts[1:]) if parts else parts
    for d in Path(__file__).resolve().parents:
        for home in ("components", "tools"):       # public layout: chains sit in tools/
            cand = d.joinpath(home, *parts)
            if cand.exists():
                return cand
    return WORKSPACE.joinpath("components", *parts)


# Public layout: the private marketing-chain-checks component ships as components/quality-checks.
_PUBLIC_NAME = {"marketing-chain-checks": "quality-checks"}


def lab_tool(*parts):
    """Another of the owner's machines, still in lab/ — found by walking up,
    so this component can move again without every reach breaking."""
    for d in Path(__file__).resolve().parents:
        cand = d.joinpath("lab", *parts)
        if cand.exists():
            return cand
    return WORKSPACE.joinpath("lab", *parts)


# K2 (brands write wall), SI-21 2026-10-07. No script in this component writes
# under brands/: a brand fact it makes goes to a PROPOSAL under runs/
# (facts_proposal.py) and a person copies it in. Every write path a writer
# takes from outside — an --out, a run folder — passes through here first.
# Resolved, so `..` and symlinks cannot walk around it; only the workspace's
# own brands/ folder is walled, never a folder that is merely NAMED brands
# (pull/derive.py's pull/brands/ stays inside the component).
def refuse_brand_write(path, root=None):
    p = Path(path).expanduser().resolve()
    walls = [(Path(root) if root else workspace()).resolve() / "brands"]
    if _REPO is not None:
        walls.append(_REPO / "brands")
    for wall in walls:
        if p == wall or wall in p.parents:
            raise SystemExit("REFUSED (K2 brands write wall): %s is under brands/ — "
                             "write a proposal under runs/ instead" % p)
    return p


# SI-53 (email outputs home), email-production#19, 2026-10-07 (triage page 9).
# Every run this component writes lands beside the chain's own runs
# (email.py), under runs/email-production/<brand>/<label>/ — never beside the
# code. One plain folder name per part, then the brands wall above.
def _plain(what, value):
    v = str(value or "")
    if (not v or v in (".", "..") or "/" in v or "\\" in v
            or Path(v).is_absolute()):
        raise SystemExit(f"REFUSED: {what} {value!r} is not one plain folder name — "
                         "email-production writes only under "
                         "runs/email-production/<brand>/<label>/")
    return v


def brand_runs(brand, root=None):
    """runs/email-production/<brand>/ at the workspace root."""
    base = Path(root) if root else workspace()
    return refuse_brand_write(base / "runs" / "email-production" / _plain("brand", brand), root)


def run_home(brand, label, root=None):
    """runs/email-production/<brand>/<label>/ — where every run this component
    writes lands (email-production#19, triage page 9). Never made here."""
    return refuse_brand_write(brand_runs(brand, root) / _plain("label", label), root)
