#!/usr/bin/env python3
"""Every path image teardown uses. One file, so there is one place to look.

Prizm Labs' public copy of the production tool (`tools/image-teardown/`). It
reads this repo's own homes — `brands/<brand>/` (laid out like
`brands/_TEMPLATE/`, whose `FOLDERS.json` names every folder, new and old),
the shared parts in `components/`, and the other tools in `tools/`. Nothing
outside the repo, except one folder for pictures you choose yourself
(`PRIZM_MEDIA`, below). Pictures are content; code and text are the repo.

    from paths import LANE, SWIPE, DRIVE, brand
"""

import json
import os
import sys
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
           "image-teardown lane")                 # tools/image-teardown
REPO = _repo(LANE)                                # the workspace root
LAB = LANE.parent                                 # tools/
TOOL = "image-teardown"                           # its name under runs/
RECORDS = REPO / "runs" / TOOL                    # runs/image-teardown/<brand>/<label>/
ELEMENTS = REPO / "components/elements"           # the element library
# One constant for image production, not three paths: three readers once
# pointed at an old folder and every draft job failed with "can't open file".
IMAGE_PROD = REPO / "tools/image-production"
QUALITY = REPO / "components/quality-checks"      # the shared checks and hold()
RUN_KIT = REPO / "components/run-kit"             # tiers, numeric prompt versions

# The swipe library: one folder per advertiser (paid) or account (organic).
SWIPE = REPO / "tools" / "my-feeds" / "paid"
SWIPE_ORGANIC = REPO / "tools" / "my-feeds" / "organic"
BRANDS = REPO / "brands"                          # brand truth — one folder per brand


def _folder_names():
    """new folder name -> old names, from brands/_TEMPLATE/FOLDERS.json."""
    f = BRANDS / "_TEMPLATE" / "FOLDERS.json"
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in d.items() if not k.startswith("_") and isinstance(v, list)}


class _BrandPath:
    """A brand file by its folder's name today, falling back to its old name
    (FOLDERS.json) so a brand folder that has not moved yet still works."""

    def brand_path(self, name, *keys, root=None):
        b = Path(root or BRANDS) / name
        rel = "/".join(keys)
        names = _folder_names()
        cands = [rel]
        for new, olds in sorted(names.items(), key=lambda kv: -len(kv[0])):
            if rel == new or rel.startswith(new + "/"):
                tail = rel[len(new):]
                cands += [o.rstrip("/") + tail for o in olds]
                break
        for c in cands:
            if (b / c).exists():
                return b / c
        return b / rel


BP = _BrandPath()
# Same repo-root exception as BRANDS above: the marketing-doctrine component
# is the one home for Schwartz's frameworks (awareness, sophistication,
# desire, techniques), read by path, never restated in a prompt.
DOCTRINE = REPO / "components/marketing-doctrine/slices"
ADCOPY = REPO / "tools" / "copywriter"                          # the copy tool, incl. language.py

PROMPTS = LANE / "prompts"
TOOLS = LANE / "tools"


RUNS = LANE / "runs"
REFERENCE = LANE / "reference"                    # the visual lexicon

# Where pictures live: any folder you choose, set once as PRIZM_MEDIA.
# Unset, it is a `media/` folder beside this tool (kept out of git).
DRIVE = Path(os.environ.get("PRIZM_MEDIA") or (LANE / "media"))

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
    """Everything the chain reads about one brand, all under brands/<brand>/.

    Returns paths whether or not they exist — the caller reports what is
    missing rather than silently falling back to somewhere else, which is how
    the lane ended up reading three different homes for one brand.
    """
    b = BRANDS / name
    bp = lambda *k: BP.brand_path(name, *k, root=BRANDS)   # noqa: E731  — today's folder for a plan name
    anchors = bp("brand-identity", "identity-anchors.md")   # today: brands/<brand>/identity-anchors.md
    return dict(
        root=b,
        avatars=bp("core-avatars"),
        products=bp("products"),
        offer=bp("products", "offer-bank.md"),
        identity=next((f for f in (anchors,
                                   bp("brand-identity", "anchors.md"),
                                   bp("brand-identity", "palette.md")) if f.is_file()),
                      anchors),
        palette=bp("brand-identity", "palette.md"),
        hook_ledger=bp("ads/hooks", "hook-ledger.md"),
        # The roster moved under ai-cast/casting/; ai-cast/ has not
        # existed since, so every caller asking for `cast` got a dead path.
        cast=bp("ai-elements/characters", "casting"),
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
