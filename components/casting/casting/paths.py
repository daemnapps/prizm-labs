"""Every path this engine uses, FOUND by walking up — never counted.

`parents[N]` silently points one level too high or too low the day a folder
moves, and nothing says so until a registry stops existing. Lifted from
`tools/image-production/image_production/paths.py` (`_up`, `repo`,
`home`, `sibling`, `need_brand`, `drive_runs`, `rel` — unchanged but for the
two constants and the brand map, which are this component's own).

No brand, product, person or model is named in this file.
"""
import os
import sys
from pathlib import Path

# The name the team says out loud — runs/<tool>/<brand>/<label>/ on both
# planes (runs/README.md, ruled 2026-09-17). Never a folder, never a person.
TOOL = "casting"

# Where a built character lives inside a brand, and where the brand's cast
# RECORDS live. Both are the brand's, and both are read exactly as they are on
# disk — `the team notes/avatar-builder/build.py` files into the first and
# `the team notes/casting/build_cast.py` reads the second.
CAST_FOLDER = ("ai-cast",)

# THE REGISTRY IS BEING MOVED, AND THIS COMPONENT ONLY READS IT (2026-09-22).
# On the Drive the folder went from `core-avatars/casting` to
# `ai-cast/casting` today; in the repo the committed path is still the first
# and a working tree beside this one already holds the second. So BOTH are
# looked for, in this order, and the first one on disk wins. Reading two
# candidate paths costs nothing and means a brand's cast keeps answering
# whichever way the move lands; finding BOTH is reported as a problem, because
# two registries for one brand is the one outcome that silently splits a cast.
# Nothing here writes to either: registration is a person's act.
REGISTRY_FOLDERS = (("core-avatars", "casting"), ("ai-cast", "casting"))
REGISTRY_FOLDER = REGISTRY_FOLDERS[0]            # the declared one, for printing


def _up(start, test, what):
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if test(d):
            return d
    raise FileNotFoundError("no %s found upward of %s" % (what, here))


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
    """This component's own folder — the one holding this package and its
    prompts. Found, so the folder can be moved without editing a constant."""
    return _up(__file__,
               lambda d: (d / "casting").is_dir() and (d / "prompts").is_dir(),
               "casting component folder")


def sibling(*parts):
    """Another component, found BESIDE this one rather than through the
    workspace root.

    Engine code and brand content answer to different things: `AI_WORKSPACE`
    points at the tree whose BRANDS are being read, and a caller may legally
    point it at a worktree or a fixture. The shared engines this one calls —
    image-production, marketing-chain-checks, elements, run-kit — are its neighbours
    in `components/`, wherever that is, and must not move when the brands tree
    does. (image-production's own `paths.sibling`, same reasoning.)"""
    return home().parent.joinpath(*parts)


def prompts_dir():
    return home() / "prompts"


def brands_dir(start=None):
    return repo(start) / "brands"


class BrandRequired(SystemExit):
    """A brand-bound read was asked for with no brand. Never a default."""


def need_brand(name, what, start=None):
    root = brands_dir(start)
    if not name:
        raise BrandRequired(
            "which brand? %s is read from brands/<brand>/ — name one "
            "(a folder under brands/)" % what)
    if not (root / name).is_dir():
        have = ", ".join(sorted(p.name for p in root.iterdir()
                                if p.is_dir() and not p.name.startswith(("_", "."))))
        raise BrandRequired("no brand folder brands/%s — have: %s" % (name, have))
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


# The registry folders and the cast folder by their PLAN names (brandpath):
# `ai-cast/casting` is `ai-elements/characters/casting`, `ai-cast/` is
# `ai-elements/characters`. Today they still resolve to the folders above.
REGISTRY_KEYS = (("core-avatars", "casting"), ("ai-elements/characters", "casting"))
CAST_KEY = ("ai-elements/characters",)


def registries(name, start=None):
    """Every registry folder for this brand that is actually on disk, in the
    declared order. Empty when the brand keeps no registry at all."""
    root = brands_dir(start)
    BP = brandpath(start)
    found = [BP.brand_path(name, *keys, root=root) for keys in REGISTRY_KEYS]
    return [p for p in found if p.is_dir()]


def brand(name, start=None):
    """Where each part of a brand's cast lives. Nothing is read here; this
    only says where to look."""
    root = brands_dir(start)
    b = root / name
    BP = brandpath(start)
    found = registries(name, start)
    reg = found[0] if found else BP.brand_path(name, *REGISTRY_KEYS[0], root=root)
    return {
        "root": b,
        "cast": BP.brand_path(name, *CAST_KEY, root=root),
        "registry": reg,
        "registries": found,
        "roster": reg / "roster.json",
        "authority": reg / "authority.json",
        "identities": reg / "identities.json",
        "lineage": reg / "lineage.json",
    }


def character(brand_name, cid, start=None):
    """One built character's folder inside the brand — the shape
    `the team notes/avatar-builder/build.py` already files into, unchanged."""
    d = brand(brand_name, start)["cast"] / cid
    return {"root": d, "boards": d / "boards",
            "master": d / "master-sheet.png",
            "anchor": d / "boards" / "character-sheet.png",
            "bible": d / "character.md"}


class MountError(Exception):
    """The Team Drive drive cannot be found on this machine."""


def drive_runs():
    """`Team Drive/runs` on the mounted Drive — DISCOVERED, never typed.
    The account in the mount's name belongs to whoever is signed in, so it is
    not written here. Same three loud failures as
    `components/run-kit/run_kit/filing.py` `drive_runs()`."""
    cloud = Path.home() / "Library" / "CloudStorage"
    mounts = sorted(cloud.glob("GoogleDrive-*" + os.environ.get("DRIVE_ACCOUNT_HINT", ""))) if cloud.is_dir() else []
    if not mounts:
        raise MountError("no team Google Drive is mounted on this machine")
    if len(mounts) > 1:
        raise MountError("more than one team Drive is mounted: "
                         + ", ".join(m.name for m in mounts))
    shared = mounts[0] / "Shared drives" / os.environ.get("SHARED_DRIVE_NAME", "Team Drive")
    if not shared.is_dir():
        raise MountError("the Team Drive drive is not visible under %s" % mounts[0].name)
    return shared / "runs"


def drive_character(brand_name, cid):
    """`Team Drive/brands/<brand>/ai-cast/<id>/` — the mirror
    `build.py` step 9 writes, with the mount DISCOVERED instead of typed.

    NOTE (2026-09-22): on the Drive the brand's `core-avatars/casting` folder
    was moved to `ai-cast/casting`, so the Drive and the repo now disagree
    about where the cast RECORDS live. The repo is unchanged and is what this
    component reads; this path is the character's PICTURES, which never moved.
    """
    return brandpath().brand_path(brand_name, *CAST_KEY, cid,
                                  root=drive_runs().parent / "brands")


def rel(p, start=None):
    """A path as the repo says it, for printing. Never fails."""
    try:
        return str(Path(p).resolve().relative_to(repo(start)))
    except (ValueError, OSError, FileNotFoundError):
        return str(p)
