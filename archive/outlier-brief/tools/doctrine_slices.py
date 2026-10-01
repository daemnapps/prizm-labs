#!/usr/bin/env python3
"""The marketing doctrine, as its own rendered slices.

Awareness, sophistication, mass desire and the ad frameworks are NEVER typed
into a prompt in this folder. A prompt binds the slice the doctrine component
renders (`components/marketing-doctrine/slices/<name>.md`) and the words
arrive at run time — one doctrine, not two that drift.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import paths as P                                             # noqa: E402

# the variable a prompt asks for → the slice that fills it (names fixed by the
# doctrine component's README, the same in every chain)
SLICES = {
    "desire_dimensions": "desire.md",
    "awareness_levels": "awareness.md",
    "sophistication_stages": "sophistication.md",
    "ad_frameworks": "ad-frameworks.md",
}


def path(var):
    return P.DOCTRINE / "slices" / SLICES[var]


def missing():
    return [f"the doctrine slice for {{{v}}} is not on file: {P.rel(path(v))}" for v in SLICES if not path(v).is_file()]


def text(var):
    return path(var).read_text().strip()
