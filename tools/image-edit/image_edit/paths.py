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


def picture_builder():
    """components/model-inputs' prompt builder (preview.py), loaded from beside this component, so a variation is
    built, checked and made on the same path as the picture it varies."""
    folder = sibling("model-inputs")
    if str(folder) not in sys.path:
        sys.path.append(str(folder))
    import importlib.util
    spec = importlib.util.spec_from_file_location("image_edit_model_inputs_preview", folder / "preview.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def runs(brand, label):
    return repo() / "runs" / TOOL / brand / label


def _kit_paths():
    """run-kit's paths, the sibling component (appended to sys.path, never ahead of the caller)."""
    kit = str(sibling("run-kit"))
    if kit not in sys.path:
        sys.path.append(kit)
    from run_kit import paths as kit_paths
    return kit_paths


def portable(s):
    """What a record stores for a path, or for JSON text holding paths — repo-relative or a
    "Shared Assets/…" label, never a machine path (builder card rule 4 (stored data references))."""
    return _kit_paths().portable(s)


def local(obj):
    """A record read back: its stored repo-relative paths made absolute in this checkout."""
    return _kit_paths().local(obj)
