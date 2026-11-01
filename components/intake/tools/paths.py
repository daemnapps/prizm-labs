"""Where things are — FOUND by walking up, never counted with parents[N].

Two roots, and they are usually the same folder:

    code_repo()   the repo this file sits in — the shared CODE is imported from
                  here (components/marketing-chain-checks, components/elements/machine)
    workspace()   where the DATA is — the two swipe pools, brands/, runs/ and
                  the built element library. `AI_WORKSPACE` overrides it, which
                  is how a worktree reads the live pools and how the tests run
                  against a tiny fake workspace.
"""
import os
import sys
from pathlib import Path

TOOL = "intake"                                   # the name we say out loud: runs/<TOOL>/...
# Both pools graduated out of the lab to components/ on 2026-09-22 (the owner:
# "swipe paid, swipe organic, intake all need to move to components now").
# The DRIVE mirror deliberately did not move — the media stays where every
# link already handed out points at it.
PAID_POOL = ("components", "swipe-paid")          # where paid + own swipes LIVE
ORGANIC_POOL = ("components", "swipe-organic")    # where organic swipes LIVE


def _walk_up(start):
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError("no workspace found upward of " + str(here))


def code_repo():
    return _walk_up(__file__)


def workspace():
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    return code_repo()


def paid_pool():
    return workspace().joinpath(*PAID_POOL)


def organic_pool():
    return workspace().joinpath(*ORGANIC_POOL)


def brands():
    """Every real brand — read from the folders, never typed."""
    d = workspace() / "brands"
    return sorted(p.name for p in d.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))


def run_dir(brand, label, make=True):
    """runs/intake/<brand>/<label>/ at the workspace root (lab/damon/CLAUDE.md §1).
    A brand or label that is not one plain folder name, or a label that resolves
    outside runs/intake/<brand>/, raises ValueError (intake#1, K2 (brands write wall))."""
    for what, value in (("brand", brand), ("label", label)):
        if (not value or value in (".", "..") or "/" in value or "\\" in value
                or "\x00" in value or os.path.isabs(value)):
            raise ValueError(f"refused: {what} {value!r} is not one plain folder name — "
                             f"an intake run files only under runs/intake/<brand>/<label>/")
    base = workspace() / "runs" / TOOL / brand
    d = base / label
    if base.resolve() not in d.resolve().parents:
        raise ValueError(f"refused: label {label!r} resolves outside runs/intake/{brand}/")
    if make:
        d.mkdir(parents=True, exist_ok=True)
    return d


def shared(*parts):
    """Put one shared code folder on the import path — APPENDED, never
    inserted at 0, so nothing here can shadow the standard library."""
    p = str(code_repo().joinpath("components", *parts))
    if p not in sys.path:
        sys.path.append(p)
    return p
