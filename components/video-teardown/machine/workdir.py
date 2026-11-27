#!/usr/bin/env python3
"""Where video-teardown's working runs live — named once, here (SI-56, 2026-10-08).

A run's working folder (source video, frames, every stage, run.json) used to
be `runs/<slug>/` inside this machine folder. It is now
`<workspace>/runs/video-teardown/_work/<slug>/` (gitignored whole; run-kit's
index skips the `_work` slot, so it is never listed as a filed run). The
machine's own no-brand files — creators.json, the generated briefs and
prompts pages — sit in `<workspace>/runs/video-teardown/_system/`.

Every reader of a live or in-flight run gets the folder from this module:
inside the machine by `import workdir`, outside it by loading this one file by
path. Finished text is read from the filed shelves through run_kit.index.

Stdlib only; imports nothing from this repo; creates nothing at import or on a
lookup. `move_runs.py` carries the old folder (legacy()) across, once per Mac.
"""

import os
from pathlib import Path

PARTS = ("runs", "video-teardown", "_work")
SYSTEM_PARTS = ("runs", "video-teardown", "_system")
MACHINE = Path(__file__).resolve().parent


def workspace(env=None):
    """The workspace root — the same rule as chain.workspace(): the
    AI_WORKSPACE variable when it names a folder holding brands/; else the
    first folder upward of this file holding both components/ and brands/;
    else the repo this file sits in."""
    env = os.environ.get("AI_WORKSPACE") if env is None else env
    if env:
        p = Path(env).expanduser()
        if (p / "brands").is_dir():
            return p.resolve()
    for d in [MACHINE, *MACHINE.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    return MACHINE.parents[2]


def root(ws=None):
    """The working folder: <workspace>/runs/video-teardown/_work/."""
    return Path(ws or workspace()).joinpath(*PARTS)


def run_dir(slug, ws=None):
    """One working run: <workspace>/runs/video-teardown/_work/<slug>/."""
    return root(ws) / slug


def system(ws=None):
    """The machine's own no-brand files: <workspace>/runs/video-teardown/_system/."""
    return Path(ws or workspace()).joinpath(*SYSTEM_PARTS)


def legacy():
    """The old working folder, inside the component."""
    return MACHINE / "runs"


def legacy_entries():
    """What still sits in the old folder — [] when it is gone."""
    d = legacy()
    if not d.is_dir():
        return []
    return sorted(d.iterdir())
