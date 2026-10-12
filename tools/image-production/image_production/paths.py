"""Every path this engine uses, FOUND by walking up — never counted.

`parents[N]` silently points one level too high or too low the day a folder
moves, and nothing says so until a packshot stops existing (2026-09-02).
Lifted from `tools/image-production/static/tools/paths.py` (`_up`, `_repo`,
`drive()`) and `components/run-kit/run_kit/paths.py` (the AI_WORKSPACE
override, and the three loud Drive failures in `filing.py`).

No brand, product, person or model is named in this file.
"""
import os
import sys
from pathlib import Path

# The name the team says out loud — runs/<tool>/<brand>/<label>/ on both
# planes (runs/README.md, the developer 2026-09-17). Never a folder, never a person.
TOOL = "image-production"


def _up(start, test, what):
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if test(d):
            return d
    raise FileNotFoundError(f"no {what} found upward of {here}")


def repo(start=None):
    """The workspace root: the first folder upward holding components/ and
    brands/. `AI_WORKSPACE` wins when it names such a folder — a worktree
    would otherwise read and write the main checkout by accident."""
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir() and (Path(env) / "components").is_dir():
        return Path(env)
    return _up(start or __file__,
               lambda d: (d / "components").is_dir() and (d / "brands").is_dir(),
               "workspace (a folder holding components/ and brands/)")


def home():
    """This component's own folder — the one holding models.json and this
    package. Found, so the folder can be moved without editing a constant."""
    return _up(__file__,
               lambda d: (d / "models.json").is_file() and (d / "image_production").is_dir(),
               "image-production component folder")


def component(*parts, start=None):
    return repo(start).joinpath("components", *parts)


def sibling(*parts):
    """Another component, found BESIDE this one rather than through the
    workspace root.

    Engine code and brand content answer to different things: `AI_WORKSPACE`
    points at the tree whose BRANDS are being read, and a caller may legally
    point it at a worktree or a fixture. The shared engines this one calls —
    marketing-chain-checks, elements — are its neighbours in `components/`, wherever
    that is, and must not move when the brands tree does."""
    return home().parents[1].joinpath("components", *parts)   # tools/<this> -> components/<that>


def prompts_dir():
    return home() / "prompts"


def brands_dir(start=None):
    return repo(start) / "brands"


class BrandRequired(SystemExit):
    """A brand-bound read was asked for with no brand. Never a default.

    Defaulting to one brand meant every other brand's picture got the first
    brand's logo, colours and packshot (tools/image-production/static)."""


def need_brand(name, what, start=None):
    root = brands_dir(start)
    if not name:
        raise BrandRequired(
            f"which brand? {what} is read from brands/<brand>/ — name one "
            f"(a folder under brands/)")
    if not (root / name).is_dir():
        have = ", ".join(sorted(p.name for p in root.iterdir()
                                if p.is_dir() and not p.name.startswith(("_", "."))))
        raise BrandRequired(f"no brand folder brands/{name} — have: {have}")
    return name


def brandpath(start=None):
    """components/brandpath — one door into a brand's folders (plan names in,
    today's folders out). The module is CODE, so it is found beside this
    component (upward from this file), and only then from the workspace the
    brand data sits in — a test's sandbox workspace holds brands, not code."""
    here = Path(__file__).resolve()
    homes = [d / "components" / "brandpath" for d in [here, *here.parents]]
    try:
        homes.append(repo(start) / "components" / "brandpath")
    except FileNotFoundError:
        pass
    home = next((h for h in homes if (h / "brandpath.py").is_file()), None)
    if home is not None and str(home) not in sys.path:
        sys.path.append(str(home))
    import brandpath as BP
    return BP


def brand(name, start=None):
    """Where each part of a brand's own truth lives. Nothing is read here;
    this only says where to look. Folders resolve via brandpath, so the
    brand folders can be renamed to the plan without touching this."""
    root = brands_dir(start)
    b = root / name
    BP = brandpath(start)
    return {
        "root": b,
        "identity": BP.brand_path(name, "brand-identity", root=root),
        "products": BP.brand_path(name, "products", root=root),
        "product_images": BP.brand_path(name, "products", "images.json", root=root),
        "element_facts": b / "ai-elements" / "element-facts.json",
        "elements": BP.brand_path(name, "ai-elements", root=root),
        "offers": BP.brand_path(name, "offers", root=root),
    }


def _drive_index(start=None):
    brandpath(start)                      # puts components/brandpath on the path
    import drive_index
    return drive_index


def drive_picture(brand_name, ref, start=None):
    """A product picture on the Drive by its Drive id — `ref` is a path from
    products/images.json (old or new) or an id. None when it is not there.
    The Drive was reorganized 2026-10-01; products/DRIVE-INDEX.json keeps the ids."""
    try:
        return _drive_index(start).local(brand_name, ref, brands_dir(start))
    except Exception:
        return None


def drive_product_pictures(brand_name, product, start=None):
    """The product's packshots on the Drive (products/<product>/packshot/…)."""
    try:
        return _drive_index(start).product_pictures(brand_name, product, brands_dir(start))
    except Exception:
        return []


class MountError(Exception):
    """The Team Drive drive cannot be found on this machine."""


def drive_runs():
    """`Team Drive/runs` on the mounted Drive — found through the shared
    mount helper (components/brandpath `drive_index.mount()`), so one mount is
    discovered in one place and no account is typed here. How a run REACHES
    the Drive — this mount or the API — is `drive_reach.route()`'s call."""
    try:
        shared = _drive_index().mount()
    except OSError as e:
        raise MountError(f"the Drive mount could not be read: {type(e).__name__}: {e}")
    if shared is None:
        raise MountError("no Team Drive Drive mount on this machine "
                         "(components/brandpath drive_index.mount() found none)")
    return shared / "runs"


def rel(p, start=None):
    """A path as the repo says it, for printing. Never fails."""
    try:
        return str(Path(p).resolve().relative_to(repo(start)))
    except (ValueError, OSError, FileNotFoundError):
        return str(p)
