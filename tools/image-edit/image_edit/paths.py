"""Every path, found by walking up — never counted (image-production's rule)."""
import importlib.util
import os
from pathlib import Path

TOOL = "image-edit"          # runs/image-edit/<brand>/<label>/


def _up(start, test, what):
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if test(d):
            return d
    raise FileNotFoundError(f"no {what} found upward of {here}")


def home():
    """tools/image-edit — the folder holding splits.json and image_edit/."""
    return _up(__file__, lambda d: (d / "splits.json").is_file() and (d / "image_edit").is_dir(),
               "image-edit folder")


def repo():
    """The repo root: the folder holding components/ and brands/. AI_WORKSPACE
    outranks the walk, the same as tools/image-production/tools/paths.py — a
    worktree, or a test's temp folder, must not read the main checkout."""
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir() and (Path(env) / "components").is_dir():
        return Path(env)
    return _up(__file__, lambda d: (d / "components").is_dir() and (d / "brands").is_dir(),
               "repo (a folder holding components/ and brands/)")


def brands():
    return repo() / "brands"


def sibling(*parts):
    """Another tool found BESIDE this one (tools/<name>)."""
    return home().parent.joinpath(*parts)


def _load(name, path):
    """A module from image-production's own tools/ folder, under its own name.
    Loaded by file, never put on sys.path — its `paths.py` would shadow ours."""
    if not path.is_file():
        raise FileNotFoundError(f"{path} is not here — image-edit runs beside tools/image-production")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def production():
    """tools/image-production/tools/paths.py — where a brand's logo and product
    photo live. Its brands root is pointed at ours, so a test's temp brands
    and a worktree's are the ones read."""
    mod = _load("image_production_paths", sibling("image-production", "tools", "paths.py"))
    mod.BRANDS = brands()
    return mod


def gemini():
    """tools/image-production/tools/gemini_image.py — the judge's key, read
    the same way image-production's own judge reads it."""
    return _load("image_production_gemini", sibling("image-production", "tools", "gemini_image.py"))


def runs(brand, label):
    return repo() / "runs" / TOOL / brand / label
