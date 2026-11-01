#!/usr/bin/env python3
"""Where this tool is, and where everything it reads lives.

**Nothing here counts folders upward from this file**, and that is the point.
This tool moved from the email machine's folder into `components/` and back
into `lab/` inside one day, and every `parents[3]` in the tree broke on each
move — silently, because a wrong path just means a file "isn't there". So the
workspace is FOUND — run-kit's `paths.repo()`, the first folder upward holding
`components/` and `brands/`, or `AI_WORKSPACE` when that names a tree with a
`brands/` — and brand folders are read through `brandpath` (SI-109 (calendar
one locator)). There is no named default in anyone's home folder. The folder
can move again for free.

Everything the tool reads or writes hangs off `WORKSPACE`:

    brands/<brand>/     brand content, read-only (rule-9, brand home)
    components/         shared engines this one borrows (language-layer)
    platform/data/      where finished results are filed
    runs/marketing-calendar/<brand>/<YYYY-MM>/
                        THE home of a planned month (SI-22 (calendar months
                        home), 2026-10-07) — one home, no second copy; the
                        board, the front page and email production read it
                        here. `_system/` holds the page covering every brand.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # machine/
COMPONENT = HERE.parent                             # the tool's own folder
PROMPTS = COMPONENT / "prompts"
DEFINITIONS = COMPONENT / "definitions"

# run-kit and brandpath are this tool's siblings under components/
sys.path.append(str(COMPONENT.parent / "run-kit"))     # appended, never ahead of this tool
sys.path.append(str(COMPONENT.parent / "brandpath"))
from run_kit import paths as _kit                   # noqa: E402
import brandpath as BP                              # noqa: E402


def workspace():
    """The tree brand content is read from — run-kit's one locator."""
    return _kit.repo(HERE)


WORKSPACE = workspace()
COMPONENTS = WORKSPACE / "components"
PLATFORM = WORKSPACE / "platform"
RUNS = WORKSPACE / "runs" / "marketing-calendar"
SYSTEM = RUNS / "_system"
MONTH_RE = re.compile(r"\d{4}-\d{2}")


def _slug(s):
    """The brand's shelf name — gates._safe's rule, so the two never disagree."""
    return re.sub(r"[^a-z0-9-]+", "-", str(s or "").lower()).strip("-")


def month_dir(brand, month):
    """Where one brand's month lives: runs/marketing-calendar/<brand>/<YYYY-MM>/."""
    return RUNS / _slug(brand) / month


def months(root=None):
    """Every planned month on the shelf — <root>/<brand>/<YYYY-MM>/ holding a
    slots.json, sorted. `_system` and `moments-*` proposals are not months."""
    root = Path(root) if root else RUNS
    if not root.is_dir():
        return []
    found = []
    for b in sorted(root.iterdir()):
        if not b.is_dir() or b.name.startswith("_"):
            continue
        for d in sorted(b.iterdir()):
            if d.is_dir() and MONTH_RE.fullmatch(d.name) and (d / "slots.json").is_file():
                found.append(d)
    return found


def brand_root(brand):
    return BP.brand_root(brand, root=WORKSPACE / "brands")


def rel(p):
    """A path written the way a person can follow it — relative to the
    workspace when it is inside one, absolute when it is not."""
    p = Path(p)
    try:
        return str(p.relative_to(WORKSPACE))
    except ValueError:
        return str(p)
