#!/usr/bin/env python3
"""brand-finder — "where is brands/" answered in ONE place (BH-1).

rule-9 (brand home) says brand content comes from `brands/<brand>/` and
nowhere else. Three implementations were answering "where is that", and
converging by copy-paste: `lab/copy/machine/paths.py`,
`lab/email-production/paths.py`, and `components/chain-runner/runner/
brandhome.py`. This module is the UNION of their MECHANISMS and nothing else
— no policy, no default, no brand.

Two questions, because the three callers genuinely ask two:

    workspace(default)   the NAMED tree brand context is read from — an env
                         override, else the caller's own default. The lab
                         machines' question, asked once at import.
    checkout_of(path)    the working tree a path sits in, found by probing
                         upward for `.git`; `home_of(path)` is that
                         checkout's `brands/`. chain-runner's question, asked
                         of paths a run declares.

**THIS MODULE HAS NO DEFAULT OF ITS OWN, and that is structural rather than
an oversight**: `workspace()` takes the caller's default positionally and
there is nowhere to put a fallback. The two lab machines name DIFFERENT
default trees — the repo root (copy) and `lab` (email-production) — and
BH-1's kill says a shared locator must never flatten a real difference by
picking a winner. So the mechanism moves here and each caller's default stays
on its own line, where it already lived. The divergence itself is written
down for the 09-03 the owner batch: see this folder's CLAUDE.md.

No brand name is written down here, and none can be: `HOME` is a directory
name, not a brand (workspace rule 7).
"""

import os

# The one home, relative to whatever tree contains it. A directory name.
HOME = "brands"


def workspace(default, env="AI_WORKSPACE"):
    """The tree brand context is read from. Named, never guessed.

    `default` is REQUIRED — see the module docstring. It is handed back
    unchanged, so a caller that has always got a `Path` still does, and a
    caller passing a str gets a str. The env value goes through
    `expanduser` and nothing else: it is not resolved, not made absolute and
    not checked for a `brands/` inside it, because every one of those would
    be this module deciding something a caller already decided.
    """
    named = os.environ.get(env)
    if named:
        return os.path.expanduser(named)
    return default


def checkout_of(path):
    """The working tree `path` sits in, or None.

    The path NEED NOT EXIST — a root naming a directory nobody created yet is
    still a declaration, and it is the declaration rule-9 reads. A `.git`
    that is a FILE counts: that is a linked worktree, and a worktree is a
    checkout.
    """
    cursor = os.path.normpath(os.path.abspath(str(path)))
    while True:
        if os.path.exists(os.path.join(cursor, ".git")):
            return cursor
        parent = os.path.dirname(cursor)
        if parent == cursor:
            return None
        cursor = parent


def home_of(path):
    """The one home — `<checkout>/brands` — for whatever checkout `path` sits
    in, or None when it sits in none.

    A caller that also needs the checkout itself (chain-runner does, to read a
    path's segments relative to it) calls `checkout_of` and joins `HOME`,
    rather than this doing the walk twice.
    """
    checkout = checkout_of(path)
    if checkout is None:
        return None
    return os.path.join(checkout, HOME)
