#!/usr/bin/env python3
"""Every path the image lane uses. One file, so there is one place to look.

**Image teardown is a component** (`tools/image-teardown/`, moved out of
`tools/image-teardown/` on the owner's word, 2026-10-01: "move image teardown
to components"). It reads the workspace's own homes — `brands/`, the other
components — and nothing outside the repo: no `~/devel/daemn`, no integration
desk. The old lab folder keeps a README and two forwarding shims for one
release; working files a checkout still holds there are carried over on first
use (`carry_over()` below).

The one exception is Drive, and it is not an exception to the rule so much as
the other half of it: `lab/owner/README.md` says code in the repo, content on
Drive at the mirrored path. Pictures are content.

    from paths import LAB, LANE, SWIPE, DRIVE, brand
"""

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
    """The workspace root, by run-kit's one walk (SI-108 (teardown one locator)).
    run-kit is found beside the lane, appended, never ahead of it."""
    sys.path.append(str(LANE.parent / "run-kit"))
    from run_kit import paths as RK
    return RK.repo(start)


# The lane is the folder that holds chain.py and prompts/ — found, not counted.
LANE = _up(__file__, lambda d: (d / "chain.py").is_file() and (d / "prompts").is_dir(),
           "image-teardown lane")                 # tools/image-teardown
REPO = _repo(LANE)                                # the workspace root
# the owner's lab — still home to mirror.py and the lab pages. Not the lane's
# parent any more (the lane graduated to components/ on 2026-10-01), so it is
# named from the repo root rather than walked to.
LAB = REPO / "lab" / "owner"
OLD_LANE = LAB / "image-teardown"                 # the pre-2026-10-01 home; a shim now
TOOL = "image-teardown"                           # its name under runs/
RECORDS = REPO / "runs" / TOOL                    # runs/image-teardown/<brand>/<label>/
ELEMENTS = REPO / "components/elements"           # the element library
# image-production graduated out of lab/owner into components/ and three
# readers were left pointing at the old path, so every draft job failed
# with "can't open file" (2026-09-24). One constant now, not three paths.
IMAGE_PROD = REPO / "tools/image-production/static"
QUALITY = REPO / "components/marketing-chain-checks"      # the shared checks and hold()
RUN_KIT = REPO / "components/run-kit"             # tiers, numeric prompt versions

# The library split into paid and organic; "swipe" has not existed since.
# Three connection checks reported the whole swipe library missing.
SWIPE = REPO / "components" / "swipe-paid"        # the swipe library — a component since 2026-09-22 (was lab/owner/swipe-paid)
SWIPE_ORGANIC = REPO / "components" / "swipe-organic"   # likewise moved 2026-09-22
# Brand truth left the lab on 2026-09-02: the two homes were
# consolidated into the repo-root brands/. These paths pointed at the
# lab copy, so the packshot stopped existing and the product silently
# vanished from six finished ads.
BRANDS = REPO / "brands"                          # brand truth
sys.path.append(str(REPO / "components" / "brandpath"))  # appended, never ahead of this lane
import brandpath as BP                                 # noqa: E402  — brand folders by their plan name
import drive_index as DI                               # noqa: E402  — the shared Drive mount helper
# Same repo-root exception as BRANDS above: the marketing-doctrine component
# is the one home for Schwartz's frameworks (awareness, sophistication,
# desire, techniques), read by path, never restated in a prompt.
DOCTRINE = REPO / "components/marketing-doctrine/slices"
ADCOPY = REPO / "tools" / "copywriter"                          # the copy tool, incl. language.py

PROMPTS = LANE / "prompts"                        # the records' prompts: steps 1, 2, 2b (and the draft prompts)
TOOLS = LANE / "tools"
# THE WRITING STATION (split out 2026-10-27, the way video-writing left
# video-teardown): steps 3 to 6, their prompts, the swaps record and the brief
# template live in tools/image-writing. It writes into the run it is
# handed, so every run path here stays the same.
WRITING = REPO / "tools" / "image-writing"
WRITING_PROMPTS = WRITING / "prompts"
WRITING_TOOLS = WRITING / "tools"


def _newest(folder, stem):
    """The highest -vN- of a template (no number = 1), the same rule as the prompts."""
    import re
    hits = list(folder.glob(stem + "*-owner.md"))
    num = lambda f: int((re.search(r"-v(\d+)-", f.name) or [0, 1])[1])
    return max(hits, key=num) if hits else folder / (stem + "-owner.md")


# The standard brief every static brief is filled into (the owner, 2026-10-02);
# the newest version is the one stage 6 fills and the copy gate holds it to.
BRIEF_STANDARD = _newest(WRITING / "templates", "brief-standard-static")


# Working files git does not track (runs/, the draft pictures, worksheet
# media, the board files) stay behind at the old lab path when a checkout
# pulls the move — git only moves what it tracks. On first use they are moved
# across, file by file, never over a file already here. The old lane still
# being a live checkout (its own tools/paths.py present) means nothing moved
# yet, so nothing is touched.
# REMOVE WITH THE SHIM (SI-36 (teardown lab mirror), 2026-10-07): delete carry_over() and its import-time call below in the same commit that deletes lab/owner/image-teardown/ — lab/owner/image-teardown/README.md says when; that deletion is the owner's call. tests/test_drive_link.py fails until both go.
_LEFTOVER_SKIP = {"README.md", "chain.py", "serve.py", "__pycache__", ".DS_Store"}


def carry_over(verbose=False):
    old = OLD_LANE
    if not old.is_dir() or (old / "tools" / "paths.py").is_file() or old.resolve() == LANE.resolve():
        return []
    moved = []
    for src in sorted(old.rglob("*")):
        rel = src.relative_to(old)
        if rel.parts[0] in _LEFTOVER_SKIP or "__pycache__" in rel.parts or not src.is_file():
            continue
        dst = LANE / rel
        if dst.exists():
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dst)
            moved.append(str(rel))
        except OSError:
            continue                              # another process got there first
    if verbose and moved:
        print(f"image-teardown: carried {len(moved)} working file(s) over from {old}")
    return moved


try:
    carry_over()
except Exception:                                 # never let tidying stop a run
    pass

# ONE HOME FOR A RUN (2026-10-28, components/naming/WHERE-EVERYTHING-GOES-owner.md
# item 4). A run's working files (out/, vars/, assets/, finals/, ...) used to sit
# in this lane's own runs/<label>/ while its record was filed to
# runs/image-teardown/<brand>/<label>/. They are one folder now: the run works
# in runs/image-teardown/<brand>/<label>/ directly and the record is filed
# beside its working files. RUNS is that root; a run is found with run_dir().
# OLD_RUNS is read for one release (a checkout that has not moved its working
# files yet) and an old path handed in is forwarded to the new home.
RUNS = RECORDS                                    # runs/image-teardown/ — <brand>/<label>/ under it
OLD_RUNS = LANE / "runs"                          # the pre-2026-10-28 working home; forwarding only
_OLD_PREFIX = "tools/image-teardown/runs/"


def _brand_folder(brand):
    """The brand's folder name under runs/image-teardown/ ("BRAND-A" → "brand-a")."""
    return str(brand).strip().lower()


def _is_run(d):
    """A working run, not a brand folder: it holds the run's working files."""
    return d.is_dir() and any((d / s).is_dir() for s in ("vars", "out", "assets", "finals"))


def run_dir(label, brand=None):
    """The folder a run works in: runs/image-teardown/<brand>/<label>/.

    `label` is a run label, or a path — an old tools/image-teardown/runs/<label>
    path (absolute or repo-relative) is forwarded to the new home. With `brand`
    the home is named outright (a new run is opened there); without it the
    brand folder that holds the label is found. A run only a not-yet-moved
    checkout still holds at the old home is read there (one release). A label
    found nowhere is placed by its brand prefix (`<brand>-...`), else under
    `_unfiled/` — a path that does not exist, so a reader's is_file() says no."""
    s = str(label)
    p = Path(s)
    if p.is_absolute():
        try:
            rel = p.relative_to(OLD_RUNS)
        except ValueError:
            return p
        return run_dir(rel.parts[0], brand).joinpath(*rel.parts[1:]) if rel.parts else RUNS
    if s.startswith(_OLD_PREFIX):
        rel = Path(s[len(_OLD_PREFIX):])
        return run_dir(rel.parts[0], brand).joinpath(*rel.parts[1:])
    if s.startswith("runs/image-teardown/"):
        return REPO / s
    name = p.name
    if brand:
        new = RUNS / _brand_folder(brand) / name
        if _is_run(new):
            return new
        found = run_dir(name)                     # working somewhere else (another folder, the old home)
        return found if _is_run(found) else new   # else: the run opens (or is filed) under its brand
    hits = [d for d in sorted(RUNS.glob(f"*/{name}")) if d.is_dir()] if RUNS.is_dir() else []
    hits.sort(key=lambda d: (not _is_run(d), d.parent.name.startswith(("_", "."))))
    if hits and _is_run(hits[0]):                 # where its working files are
        return hits[0]
    flat = RUNS / name                            # a flat layout (tests, a hand-made root)
    if _is_run(flat):
        return flat
    if (OLD_RUNS / name).is_dir():                # a checkout that has not moved its working files yet
        return OLD_RUNS / name
    if hits:                                      # filed only: the record folder is the run's home
        return hits[0]
    head = name.split("-", 1)[0].lower()
    if head and ((RUNS / head).is_dir() or (BRANDS / head).is_dir()):
        return RUNS / head / name
    return RUNS / "_unfiled" / name


def all_runs(brand=None, prefix=""):
    """Every working run, sorted by label: runs/image-teardown/<brand>/<label>/
    that hold working files, plus any the old home still holds that the new one
    does not. `brand` narrows to one brand folder; `prefix` to labels starting so."""
    seen, out = set(), []
    roots = []
    if RUNS.is_dir():
        roots = [RUNS / _brand_folder(brand)] if brand else sorted(d for d in RUNS.iterdir() if d.is_dir())
    for root in roots:
        if not root.is_dir():
            continue
        if _is_run(root):                         # a flat layout: the root itself holds runs
            continue
        for d in sorted(root.iterdir()):
            if d.name.startswith(prefix) and d.name not in seen and _is_run(d):
                seen.add(d.name)
                out.append(d)
    if RUNS.is_dir():                             # a flat layout (tests, a hand-made root)
        for d in sorted(RUNS.iterdir()):
            if d.name.startswith(prefix) and d.name not in seen and _is_run(d) \
               and (not brand or d.name.startswith(_brand_folder(brand) + "-")):
                seen.add(d.name)
                out.append(d)
    if OLD_RUNS.is_dir():
        for d in sorted(OLD_RUNS.iterdir()):
            if d.is_dir() and d.name.startswith(prefix) and d.name not in seen \
               and (not brand or d.name.startswith(_brand_folder(brand) + "-")):
                seen.add(d.name)
                out.append(d)
    return sorted(out, key=lambda d: d.name)


REFERENCE = LANE / "reference"                    # the visual lexicon

# Shared Assets is found through the shared mount helper, not typed with one
# person's account (SI-39 (teardown mount helper), 2026-10-07). With no mount
# it is a named path that does not exist, so every reader's is_dir()/is_file()
# answers no — same as tools/image-production/static/tools/paths.py.
NO_MOUNT = DI.NO_MOUNT  # LD-55 (Drive literal check): named in drive_index only
NO_MOUNT_NOTE = ("no Shared Assets Drive mount on this machine (components/brandpath "
                 "drive_index.mount() found none) — the swipe stills and brand "
                 "elements on the Drive cannot be read here")


def _shared_assets():
    """Shared Assets on this machine's Drive mount, else NO_MOUNT (a path that
    does not exist). An OSError from the mount is NO_MOUNT too."""
    try:
        return DI.mount() or NO_MOUNT
    except OSError:
        return NO_MOUNT


SHARED_ASSETS = _shared_assets()
DRIVE_MOUNTED = SHARED_ASSETS != NO_MOUNT
DRIVE = SHARED_ASSETS / "lab" / "owner"

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


def sub_avatar(name, avatar, sub):
    """The sub-avatar's two files: its card (`sub-avatars/<sub>.md`) and its
    newest profile (`sub-avatars/<sub>/profile.md`, written over each time the
    profile prompt runs; the history is in git). the owner, 2026-10-02: briefs are
    always written off the most up-to-date avatar, so a run names its sub and
    reads these fresh at every stage, never a copy taken when the run opened."""
    d = BRANDS / name / "core-avatars" / avatar / "sub-avatars"
    return d / f"{sub}.md", d / sub / "profile.md"


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


def portable(s):
    """What a record stores for a path, or for JSON text holding paths — repo-relative or a
    "Shared Assets/…" label, never a machine path (builder card rule 4 (stored data references));
    run-kit's paths.portable."""
    from run_kit import paths as RK
    return RK.portable(s)
