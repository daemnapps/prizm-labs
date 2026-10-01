#!/usr/bin/env python3
"""Every path stage two uses. One file, one place to look.

**Production reads the brief and writes the ads.** Teardown owns everything up
to the brief — the swipe, the record, the format, the copy. Production owns
everything after it: the plates, the judging, the compositing, the finished
files. Split 2026-08-31 on Damon's call, because they are two different jobs
and were tangled in one folder.

A run exists in both places under the same name: its words in teardown, its
pictures here. The brief is the seam.
"""
import json
import os
from pathlib import Path


def _up(start, test, what):
    """Walk up from `start` to the first folder that passes `test`.

    Paths are FOUND, never counted. `parents[N]` silently points one level too
    high or too low the day a folder moves, and nothing says so until a
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


# The tool's folder is the one holding machine.py and templates/ — found.
PROD = _up(__file__, lambda d: (d / "machine.py").is_file() and (d / "templates").is_dir(),
           "image-production folder")             # image-production
LAB = PROD.parent                                  # lab/damon
REPO = _repo(PROD)                                 # the workspace root
TOOL = "image-production"                          # its name under runs/
RECORDS = REPO / "runs" / TOOL                     # runs/image-production/<brand>/<batch>/
TEARDOWN = LAB / "image-teardown"                  # where briefs come from

# Brand truth left the lab on 2026-09-02: the two homes were
# consolidated into the repo-root brands/. These paths pointed at the
# lab copy, so the packshot stopped existing and the product silently
# vanished from six finished ads.
# The naming standard graduated out of the lab to components/naming on
# 2026-09; naming/ has not existed since.
COMPONENTS = REPO / "components"
NAMING = COMPONENTS / "naming"
ELEMENTS = COMPONENTS / "elements"                 # the element library
QUALITY = COMPONENTS / "quality-checks"            # the shared checks and hold()
GDRIVE = COMPONENTS / "gdrive-creator"             # delivery, through the Drive API

BRANDS = REPO / "brands"
TOOLS = PROD / "tools"
RUNS = PROD / "runs"
TEMPLATES = PROD / "templates"
STYLE_PACKS = PROD / "style-packs.json"
FORMAT_BANK = PROD / "format-bank.json"


class MountError(Exception):
    """The Shared Assets drive cannot be found on this machine."""


def drive():
    """Shared Assets/lab/damon on the mounted Drive — DISCOVERED, never typed.

    The account in the mount's name belongs to whoever is signed in, so it is
    not written here. Same discovery, and the same three loud failures, as
    components/run-kit/run_kit/filing.py `drive_runs()`."""
    cloud = Path.home() / "Library" / "CloudStorage"
    mounts = sorted(cloud.glob("GoogleDrive-*<brand>.com")) if cloud.is_dir() else []
    if not mounts:
        raise MountError("no <brand> Google Drive is mounted on this machine")
    if len(mounts) > 1:
        raise MountError("more than one <brand> Drive is mounted: "
                         + ", ".join(m.name for m in mounts))
    shared = mounts[0] / "Shared drives" / "Shared Assets"
    if not shared.is_dir():
        raise MountError(f"the Shared Assets drive is not visible under {mounts[0].name}")
    return shared / "lab" / "damon"


def _drive_or_absent():
    """`DRIVE` for the callers that test it with `.is_dir()`. With no mount it
    is a path that does not exist, so they say "is Drive mounted?" as before;
    `drive()` is the loud one."""
    try:
        return drive()
    except MountError:
        return Path.home() / "Library/CloudStorage/_no-drive-mounted/Shared Assets/lab/damon"


DRIVE = _drive_or_absent()

GEMINI_IMAGE = TOOLS / "gemini_image.py"           # the judge's eyes
COMPOSE = TOOLS / "compose.py"
# Retired 2026-09-11 — Higgsfield only. Kept so an old run can be read back.
FAL = TOOLS / "superseded/fal/fal_client.py"
PROMPTS = TEARDOWN / "prompts"                     # only for reference


def brief_for(run_name):
    """The brief this run was built from. Production never invents one."""
    return TEARDOWN / "runs" / run_name / "out/06-brief.md"


def source_for(run_name):
    """The swiped ad, for use as the layout reference."""
    d = TEARDOWN / "runs" / run_name / "assets"
    if not d.is_dir():
        return None
    return next((p for p in d.iterdir()
                 if p.stem == "source" and p.suffix.lower() in (".jpg", ".png")), None)


def identity_dir(b):
    """The brand's look: brand-identity/ (the v6 name), else the old identity/."""
    b = Path(b)
    return next((b / n for n in ("brand-identity", "identity") if (b / n).is_dir()),
                b / "brand-identity")


def brand(name):
    b = BRANDS / name
    ident = identity_dir(b)
    return dict(root=b, identity=ident,
                logo_white=ident / "logo-white.png",
                logo_dark=ident / "logo-dark.png",
                products=b / "products",
                offer=b / "offers/offer-bank.md")


def product(name, slug):
    """One product's own file, whichever shape the brand keeps them in
    (`products/<slug>/product.md` or `products/<slug>.md`)."""
    b = BRANDS / name / "products"
    for cand in (b / slug / "product.md", b / f"{slug}.md"):
        if cand.is_file():
            return cand
    return b / slug / "product.md"      # report the canonical one as missing


class BrandRequired(SystemExit):
    """A brand-bound read was asked for with no brand. Never a default."""


def need_brand(name, what):
    """The brand, or a stop that says so. Defaulting to one brand meant every
    other brand's ad got the first brand's logo, colours and packshot."""
    if not name:
        raise BrandRequired(
            f"which brand? {what} is read from brands/<brand>/ — pass --brand "
            f"<folder under brands/> (or a batch.json that names `brand`)")
    if not (BRANDS / name).is_dir():
        have = ", ".join(sorted(p.name for p in BRANDS.iterdir()
                                if p.is_dir() and not p.name.startswith(("_", "."))))
        raise BrandRequired(f"no brand folder brands/{name} — have: {have}")
    return name


def brand_of_run(run_name, named=None):
    """The brand a swipe run belongs to: the one named with --brand, else the
    one teardown recorded when it opened the run (`vars/brand_name.md`).
    Never a default."""
    if named:
        return need_brand(named, "the brand")
    f = TEARDOWN / "runs" / Path(run_name).name / "vars/brand_name.md"
    name = f.read_text().strip().lower() if f.is_file() else ""
    if name and (BRANDS / name).is_dir():
        return name
    return need_brand(None, f"{Path(run_name).name} records no brand, and its packshot, logo and colours")


def product_images(brand_name):
    """`brands/<brand>/products/images.json` → {product: {hero, cutout, all}}."""
    f = BRANDS / brand_name / "products/images.json"
    try:
        return json.loads(f.read_text()).get("products", {})
    except (OSError, ValueError):
        return {}


def product_cutout(brand_name=None, product_slug=None):
    """The real packshot, background removed — composited, never generated.

    A generated tube is a different product wearing our name. The judge
    correctly failed one on 2026-08-31.

    **Read from the brand, for the product named.** Until 2026-09-20 this
    returned one brand's one product unconditionally, so a second brand's ad
    was built with the first brand's tube on it. Now: the `cutout` the brand
    declares for that product in `products/images.json`; failing that, a
    cutout / packshot / hero PNG in the product's own images folder. With no
    product named and exactly one cutout on file, that one; with several, the
    caller must choose.

    Returns the path whether or not the file is on this machine (media is not
    in git) — the caller reports it missing. Returns None when the brand has
    no local cutout for that product at all."""
    need_brand(brand_name, "the packshot")
    root = BRANDS / brand_name
    imgs = product_images(brand_name)

    def local(v):
        return v and not str(v).startswith(("http://", "https://"))

    if not product_slug:
        have = sorted(k for k, v in imgs.items() if local(v.get("cutout")))
        if len(have) == 1:
            product_slug = have[0]
        elif have:
            raise BrandRequired(
                f"{brand_name} has {len(have)} products with a packshot — name one "
                f"with --product: {', '.join(have)}")
        else:
            return None
    declared = (imgs.get(product_slug) or {}).get("cutout")
    if local(declared):
        return root / declared
    folder = root / "products" / product_slug / "images"
    cands = sorted(folder.glob("*.png")) if folder.is_dir() else []
    for word in ("cutout", "packshot", "hero"):
        hit = next((p for p in cands if word in p.name.lower()), None)
        if hit:
            return hit
    return None
