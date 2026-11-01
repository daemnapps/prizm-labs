#!/usr/bin/env python3
"""rule-9 (brand home) — a COMPILE FINDING, not a note somebody makes in review.

components/CLAUDE.md rule 9 (the team, 2026-09-01): an engine stays brand-agnostic
and takes brand CONTENT only from `brands/<brand>/` — the real brands tree, the
one home. This module is the mechanical half of that rule and the ONLY file in
`runner/` that knows the word: it reads the PATHS a run declares as roots and
says which of them take brand content from somewhere else. Nothing here
executes, resolves or substitutes anything, and `spec.py`'s data model and the
engine never call it — they stay brand-blind, which is the other half of the
ruling (PLAN rider (2), the team GO).

DETECTION IS BY PATH SHAPE, NEVER BY CONTENT. Classifying arbitrary files as
"brand content" is a judgement, and a judgement in a compile check is a check
people learn to override. So:

  PASSES   a root resolving under its own checkout's `brands/`.
  FINDING  a root resolving elsewhere whose path SAYS it is a brand tree —
           either (1) it walks through a `brands` directory that is not the
           home one (`lab/<person>/brands/<x>`, a copy at `scratch/brands/<x>`),
           or (2) one of its segments IS a brand that exists in the home (an
           ad-hoc copy at `lab/<person>/copy/<brand>/`).
  NOTHING  anything else — a path under no checkout at all, a path outside its
           checkout, a directory named nothing in particular.

The third case is the important one. FALSE POSITIVES ARE WORSE THAN MISSES
here: prose review still covers what a path cannot say, while a finding that
fires on legitimate roots gets routed around and takes the real findings with
it. When the shape is ambiguous this module is silent on purpose.

No brand name is written down anywhere in this file. The names in case (2) are
read out of the home tree at check time, because a brand name in this code is
the exact hard-coding workspace rule 7 forbids.

WHERE a checkout's home IS is no longer decided here (BH-1, 2026-09-02): the
LOCATOR — probe upward for `.git`, the home is `<checkout>/brands` — moved to
`components/brand-finder/`, which the two lab machines' `paths.py` now share.
It had three implementations converging by copy-paste. What stayed is this
file's whole job: deciding which declared roots take brand content from
somewhere OTHER than the home. Finding logic here, location there.
"""

from __future__ import annotations

import os
import sys

_COMPONENT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "brand-finder")
if _COMPONENT not in sys.path:
    sys.path.append(_COMPONENT)

# `HOME` — the one home's directory name — and the checkout probe are the
# component's, re-exported under the names this module has always used.
from brand_finder import HOME, checkout_of as _checkout   # noqa: E402


class Finding(object):
    """One declared root that takes brand content from outside the home."""

    def __init__(self, name, declared, path, origin, reason):
        self.name = name
        self.declared = declared        # as written, before resolution
        self.path = path                # absolute, resolved
        self.origin = origin            # "chain" or "--root"
        self.reason = reason

    @property
    def message(self):
        return ("rule-9 (brand home): root {0!r} ({1} {2!r}) resolves to {3}, "
                "which {4}. Brand content comes from {5}/<brand>/ and nowhere "
                "else — point the root at the home tree, or drop it."
                .format(self.name, self.origin, self.declared, self.path,
                        self.reason, HOME))


def findings(roots):
    """[Finding] over declared roots.

    `roots` is a list of dicts — `name`, `declared`, `path` (ABSOLUTE, already
    resolved by the caller against whatever base that kind of root uses) and
    `origin`. The list may be empty, and usually is: a chain declaring no roots
    can never trip this rule.
    """
    out = []
    for root in roots:
        path = os.path.normpath(os.path.abspath(str(root.get("path"))))
        checkout = _checkout(path)
        if checkout is None:
            # Under no working tree at all. There is no home to be outside of,
            # so there is nothing this rule can say.
            continue
        home = os.path.join(checkout, HOME)
        if path == home or path.startswith(home + os.sep):
            continue                    # the one home — this is the pass
        segments = _segments(checkout, path)
        if segments is None:
            continue                    # outside its own checkout: ambiguous
        reason = None
        if HOME in segments:
            reason = ("is a second {0}/ tree, outside the home one at {1}"
                      .format(HOME, home))
        else:
            named = sorted(set(segments) & _brands_at(home))
            if named:
                reason = ("is named after {0}, which has a home at {1}"
                          .format(", ".join(named),
                                  os.path.join(home, named[0])))
        if reason is None:
            continue                    # nothing in the shape says brand
        out.append(Finding(root.get("name"), root.get("declared"), path,
                           root.get("origin"), reason))
    return out


def _segments(checkout, path):
    """`path`'s segments relative to `checkout`, or None if it is not under it."""
    if path == checkout:
        return []
    if not path.startswith(checkout + os.sep):
        return None
    return path[len(checkout) + 1:].split(os.sep)


def _brands_at(home):
    """The brands that actually exist in the home — read here, never written
    down, so this file names no brand and workspace rule 7 holds."""
    try:
        return set(name for name in os.listdir(home)
                   if not name.startswith(".")
                   and os.path.isdir(os.path.join(home, name)))
    except OSError:
        return set()
