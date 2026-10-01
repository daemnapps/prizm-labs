#!/usr/bin/env python3
"""Every path the image lane uses. One file, so there is one place to look.

**The lane lives in the lab and reads nothing outside it** (Damon, 2026-08-28,
said three times before it stuck). No `~/devel/daemn`, no repo-root brand
folders, no integration desk. If the lane needs something, it lives under
`./` — and if it doesn't live there yet, that is the bug, not a reason
to reach across.

The one exception is Drive, and it is not an exception to the rule so much as
the other half of it: `README.md` says code in the repo, content on
Drive at the mirrored path. Pictures are content.

    from paths import LAB, LANE, SWIPE, DRIVE, brand
"""

import os
from pathlib import Path



def _up(start, test, what):
    """Walk up from `start` to the first folder that passes `test`.

    Paths are FOUND, never counted. `parents[N]` silently points one level
    too high or too low the day a folder moves, and nothing says so until a
    packshot stops existing (2026-09-02). Same walk as
    components/run-kit/run_kit/paths.py."""
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if test(d):
            return d
    raise FileNotFoundError(f"no {what} found upward of {here}")


def _repo(start):
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir() and (Path(env) / "components").is_dir():
        return Path(env)
    return _up(start, lambda d: (d / "components").is_dir() and (d / "brands").is_dir(),
               "workspace (a folder holding components/ and brands/)")


# The lane is the folder that holds chain.py and prompts/ — found, not counted.
LANE = _up(__file__, lambda d: (d / "chain.py").is_file() and (d / "prompts").is_dir(),
           "image-teardown lane")                 # image-teardown
LAB = LANE.parent                                 # lab/damon
REPO = _repo(LANE)                                # the workspace root
TOOL = "image-teardown"                           # its name under runs/
RECORDS = REPO / "runs" / TOOL                    # runs/image-teardown/<brand>/<label>/
ELEMENTS = REPO / "components/elements"           # the element library
QUALITY = REPO / "components/quality-checks"      # the shared checks and hold()
RUN_KIT = REPO / "components/run-kit"             # tiers, numeric prompt versions

# The library split into paid and organic; "swipe" has not existed since.
# Three connection checks reported the whole swipe library missing.
SWIPE = LAB / "swipe-paid"                        # the swipe library
SWIPE_ORGANIC = LAB / "swipe-organic"
# Brand truth left the lab on 2026-09-02: the two homes were
# consolidated into the repo-root brands/. These paths pointed at the
# lab copy, so the packshot stopped existing and the product silently
# vanished from six finished ads.
BRANDS = REPO / "brands"                          # brand truth
# Same repo-root exception as BRANDS above: the marketing-doctrine component
# is the one home for Schwartz's frameworks (awareness, sophistication,
# desire, techniques), read by path, never restated in a prompt.
DOCTRINE = REPO / "components/marketing-doctrine/slices"
ADCOPY = REPO / "components" / "copywriter"                          # the copy tool, incl. language.py

PROMPTS = LANE / "prompts"
TOOLS = LANE / "tools"
RUNS = LANE / "runs"
REFERENCE = LANE / "reference"                    # the visual lexicon

DRIVE = Path.home() / (
    "Library/CloudStorage/GoogleDrive-${DRIVE_ACCOUNT}/"
    "Shared drives/Shared Assets/lab/damon")

# runners
GEMINI_TEXT = TOOLS / "gemini_text.py"      # reads pictures, writes records
CLAUDE_TEXT = TOOLS / "claude_text.py"      # writes the brand-side work
GEMINI_IMAGE = TOOLS / "gemini_image.py"
COMPOSE = TOOLS / "compose.py"
# copy/machine/language.py, not copy/language.py. The wrong path failed as a
# non-zero exit, which the runner reported as "the prompt asks for something
# nothing supplies" — so a missing file read as a prompt-design problem, and
# every run since went out with no customer language in it at all.
LANGUAGE = ADCOPY / "machine/language.py"
FAL = TOOLS / "superseded/fal/fal_client.py"   # retired 2026-09-13, read-back only
LEXICON = REFERENCE / "visual-lexicon.md"


def brand(name):
    """Everything the chain reads about one brand, all under the lab.

    Returns paths whether or not they exist — the caller reports what is
    missing rather than silently falling back to somewhere else, which is how
    the lane ended up reading three different homes for one brand.
    """
    b = BRANDS / name
    # brand-identity/ is the v6 name for the look; identity/ the old one
    ident = next((b / n for n in ("brand-identity", "identity") if (b / n).is_dir()),
                 b / "brand-identity")
    return dict(
        root=b,
        avatars=b / "core-avatars",
        products=b / "products",
        offer=b / "offers/offer-bank.md",
        identity_dir=ident,
        identity=next((f for f in (b / "brand-identity/identity-anchors.md",
                                   b / "identity-anchors.md",
                                   ident / "anchors.md",
                                   ident / "palette.md") if f.is_file()),
                      b / "brand-identity/identity-anchors.md"),
        palette=ident / "palette.md",
        hook_ledger=b / "hook-ledger.md",
        # The roster moved under core-avatars/casting/; ai-cast/ has not
        # existed since, so every caller asking for `cast` got a dead path.
        cast=b / "core-avatars/casting",
    )


def avatar_profile(name, avatar):
    """The written profile for one core avatar — the file, not the folder.

    With no avatar named, and exactly one on file, use it: a brand with one
    avatar should not need the flag. With several, the caller must choose —
    picking one for them is how an ad gets aimed at the wrong person."""
    root = BRANDS / name / "core-avatars"
    if not avatar:
        found = sorted(d for d in root.glob("*/profile.md"))
        if len(found) == 1:
            return found[0]
        raise SystemExit(
            f"{name} has {len(found)} avatars — name one with --avatar: "
            + ", ".join(sorted(d.parent.name for d in found)))
    return root / avatar / "profile.md"


def product(name, slug):
    """One product's own file, whichever shape the brand keeps them in.

    Brands do not agree on this: one keeps `products/<slug>/product.md`,
    another keeps `products/<slug>.md`. Hard-coding the first shape meant the
    chain only ran for the brand it was built against, which is the
    brand-agnostic rule broken in practice rather than in principle."""
    b = BRANDS / name / "products"
    for cand in (b / slug / "product.md", b / f"{slug}.md"):
        if cand.is_file():
            return cand
    return b / slug / "product.md"      # report the canonical one as missing


def brand_of_run(run, named=None):
    """The brand a run belongs to: the one named with --brand, else the one
    the run itself recorded when it was opened (`vars/brand_name.md`). Never
    a default — a tool that cannot tell says so and stops, because a guessed
    brand puts one brand's logo and packshot on another brand's ad."""
    if named:
        return named
    f = Path(run) / "vars/brand_name.md"
    name = f.read_text().strip().lower() if f.is_file() else ""
    if name and (BRANDS / name).is_dir():
        return name
    raise SystemExit(f"which brand? {Path(run).name} does not record one "
                     f"(no vars/brand_name.md naming a folder under brands/) — "
                     f"pass --brand <folder under brands/>")
