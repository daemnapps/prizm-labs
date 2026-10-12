"""Every path, found by walking up — never counted (image-production's rule)."""
import os
import sys
from pathlib import Path

TOOL = "image-edit"          # runs/image-edit/<brand>/<label>/
# THE NAME SAID OUT LOUD. Runs filed under "reference-edit" until 2026-09-23
# — back when that was this component's own folder name too — the owner, reading
# a finished drop: "why did this go into reference edit? … image edit
# instead, since it's a final run for this chain." The component folder
# itself caught up on 2026-09-30 ("we're not calling it reference edit, it's
# just going to be image edit"), so folder and output now agree.


def _up(start, test, what):
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if test(d):
            return d
    raise FileNotFoundError(f"no {what} found upward of {here}")


def home():
    return _up(__file__, lambda d: (d / "splits.json").is_file() and (d / "image_edit").is_dir(),
               "image-edit component folder")


def repo():
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir() and (Path(env) / "components").is_dir():
        return Path(env)
    return _up(__file__, lambda d: (d / "components").is_dir() and (d / "brands").is_dir(),
               "workspace (a folder holding components/ and brands/)")


def sibling(*parts):
    """Another component found BESIDE this one — the engines this one calls
    must not move when the brands tree does."""
    return home().parent.joinpath(*parts)


def image_production():
    """The shared image engine, imported once from beside this component.
    `sys.path.append`, never insert at 0 — a folder at position 0 shadows the
    stdlib."""
    folder = sibling("image-production")
    if str(folder) not in sys.path:
        sys.path.append(str(folder))
    import image_production  # noqa: E402
    from image_production import providers, route, judge, context  # noqa: F401
    return image_production


def runs(brand, label):
    return repo() / "runs" / TOOL / brand / label
