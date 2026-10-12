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
import sys
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
           "image-production folder")             # tools/image-production/static
LAB = PROD.parent                                  # tools/image-production
REPO = _repo(PROD)                                 # the workspace root
TOOL = "image-production"                          # its name under runs/
RECORDS = REPO / "runs" / TOOL                     # runs/image-production/<brand>/<batch>/
# Where briefs come from. Image teardown graduated to components/ on
# 2026-10-01; `LAB / "image-teardown"` had pointed inside this component since
# image-production itself moved, so it named a folder that never existed.
TEARDOWN = next((d for d in (REPO / "tools" / "image-teardown",)
                 if (d / "chain.py").is_file() and (d / "prompts").is_dir()),
                REPO / "tools" / "image-teardown")

# Brand truth left the lab on 2026-09-02: the two homes were
# consolidated into the repo-root brands/. These paths pointed at the
# lab copy, so the packshot stopped existing and the product silently
# vanished from six finished ads.
# The naming standard graduated out of the lab to components/naming on
# 2026-09; the team notes/naming/ has not existed since.
COMPONENTS = REPO / "components"
NAMING = COMPONENTS / "naming"
ELEMENTS = COMPONENTS / "elements"                 # the element library
QUALITY = COMPONENTS / "quality-checks"            # the shared checks and hold()
GDRIVE = COMPONENTS / "gdrive-creator"             # delivery, through the Drive API

BRANDS = REPO / "brands"
sys.path.append(str(REPO / "components" / "brandpath"))  # appended, never ahead of this tool
import brandpath as BP                                 # noqa: E402  — brand folders by their plan name
import drive_index as DI                               # noqa: E402  — product pictures on the Drive, by id
TOOLS = PROD / "tools"
RUNS = PROD / "runs"
BATCHES = RECORDS   # a batch's working folder IS its record folder: runs/image-production/<brand>/<batch>/ (image-production#12)
TEMPLATES = PROD / "templates"
STYLE_PACKS = PROD / "style-packs.json"
FORMAT_BANK = PROD / "format-bank.json"


def run_dir(arg, *, strict=True):
    """The batch folder a run.py argument names, under BATCHES.

    `runs/<brand>/<batch>` (the documented form), `<brand>/<batch>` and
    `runs/image-production/<brand>/<batch>` all name the same record home; an
    absolute path, or a relative one that exists from here, is taken as given.
    A batch folder inside this tool's own `runs/` is refused when `strict` —
    batches made before 2026-10-07 stay there, frozen (image-production#12).
    Never creates a folder."""
    p = Path(arg).expanduser()
    if p.is_absolute():
        cand = p
    elif (Path.cwd() / p).is_dir():
        cand = Path.cwd() / p
    elif p.parts[:2] == ("runs", TOOL):
        cand = REPO / p
    elif p.parts[:1] == ("runs",):
        cand = BATCHES.joinpath(*p.parts[1:])
    else:
        cand = BATCHES / p
    cand = cand.resolve()
    legacy = RUNS.resolve()
    if strict and (cand == legacy or legacy in cand.parents):
        print(f"refused: {cand} is inside this tool's own runs/ folder — a batch lives at "
              "runs/image-production/<brand>/<batch>/ since 2026-10-07 (image-production#12); "
              "move the folder there and run again", file=sys.stderr)
        raise SystemExit(2)
    return cand


DRIVE_SUBDIR = tuple(p for p in os.environ.get("PRIZM_DRIVE_SUBDIR", "prizm").split("/") if p)


class MountError(Exception):
    """The Team Drive drive cannot be found on this machine."""


def drive():
    """Team Drive/the team notes on the mounted Drive — DISCOVERED, never typed.

    The account in the mount's name belongs to whoever is signed in, so it is
    not written here. Same discovery, and the same three loud failures, as
    components/run-kit/run_kit/filing.py `drive_runs()`."""
    cloud = Path.home() / "Library" / "CloudStorage"
    mounts = sorted(cloud.glob("GoogleDrive-*" + os.environ.get("DRIVE_ACCOUNT_HINT", ""))) if cloud.is_dir() else []
    if not mounts:
        raise MountError("no team Google Drive is mounted on this machine")
    if len(mounts) > 1:
        raise MountError("more than one team Drive is mounted: "
                         + ", ".join(m.name for m in mounts))
    shared = mounts[0] / "Shared drives" / os.environ.get("SHARED_DRIVE_NAME", "Team Drive")
    if not shared.is_dir():
        raise MountError(f"the Team Drive drive is not visible under {mounts[0].name}")
    return shared.joinpath(*DRIVE_SUBDIR)   # PRIZM_DRIVE_SUBDIR: the folder on the shared drive this repo mirrors to


def _drive_or_absent():
    """`DRIVE` for the callers that test it with `.is_dir()`. With no mount it
    is a path that does not exist, so they say "is Drive mounted?" as before;
    `drive()` is the loud one."""
    try:
        return drive()
    except MountError:
        return Path.home() / "Library/CloudStorage/_no-drive-mounted/Team Drive/the team notes"


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


def brand(name):
    b = BRANDS / name
    bp = lambda *k: BP.brand_path(name, *k, root=BRANDS)   # noqa: E731  — today's folder for a plan name
    return dict(root=b, identity=bp("brand-identity"),
                logo_white=bp("brand-identity", "logo-white.png"),
                logo_dark=bp("brand-identity", "logo-dark.png"),
                products=bp("products"),
                offer=bp("products", "offer-bank.md"))


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
        if (root / declared).is_file():
            return root / declared
        # not in this repo copy: the same picture on the Drive, by its Drive id
        # (the Drive was reorganized 2026-10-01 — products/DRIVE-INDEX.json)
        on_drive = DI.local(brand_name, declared, BRANDS)
        return on_drive or root / declared
    folder = root / "products" / product_slug / "images"
    cands = sorted(folder.glob("*.png")) if folder.is_dir() else []
    cands += [p for p in DI.product_pictures(brand_name, product_slug, BRANDS) if p.suffix.lower() == ".png"]
    for word in ("cutout", "packshot", "hero"):
        hit = next((p for p in cands if word in p.name.lower()), None)
        if hit:
            return hit
    return None
