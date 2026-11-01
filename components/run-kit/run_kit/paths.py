"""Paths are FOUND by walking up, never counted with parents[N].
Lifted from tools/email-production/paths.py — written after a folder
move made parents[3] silently point one level too high."""
import os
from pathlib import Path


def repo(start=None):
    """The workspace root: the first folder upward holding components/ and brands/."""
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    here = Path(start or __file__).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError("no workspace found upward of " + str(here))


def venv(component, requirements):
    """Where a component's venv lives OUTSIDE the repo, so a fresh worktree (a mini run) finds it
    (LD-52 (venvs outside repo)): $UPRIGHT_VENVS, default ~/.upright/venvs, then
    `<component>-<first 8 hex of sha256 of the requirements file>`. A changed requirements file
    names a different folder, so nothing runs on stale packages. The path may not exist yet."""
    import hashlib
    root = Path(os.environ.get("UPRIGHT_VENVS") or Path.home() / ".upright" / "venvs").expanduser()
    sha = hashlib.sha256(Path(requirements).read_bytes()).hexdigest()[:8]
    return root / f"{component}-{sha}"


def models(component):
    """Where a component's model weights live OUTSIDE the repo (LD-52, extended to models):
    $UPRIGHT_MODELS, default ~/.upright/models, then `<component>/` — the same layout as the
    component's own models/ folder. The path may not exist yet."""
    root = Path(os.environ.get("UPRIGHT_MODELS") or Path.home() / ".upright" / "models").expanduser()
    return root / component


def component(*parts, start=None):
    return repo(start).joinpath("components", *parts)


def lab(*parts, start=None):
    return repo(start).joinpath("lab", "damon", *parts)


def brand(name, *parts, start=None):
    return repo(start).joinpath("brands", name, *parts)


def _repo_paths():
    """components/naming/repo_paths.py, loaded by file once (builder card rule 4 (stored data
    references)): the one place a stored path is made portable."""
    import importlib.util
    import sys
    m = sys.modules.get("naming_repo_paths")
    if m is None or not hasattr(m, "to_portable"):
        # the sibling component beside this one (engine code), not AI_WORKSPACE's tree
        f = Path(__file__).resolve().parents[2] / "naming" / "repo_paths.py"
        spec = importlib.util.spec_from_file_location("naming_repo_paths", str(f))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        sys.modules["naming_repo_paths"] = m
    return m


def portable(s):
    """What a record stores for a path (or any text holding paths): this checkout's or anyone's
    clone -> repo-relative, a Drive mount of Shared Assets -> "Shared Assets/…". Anything else
    comes back unchanged. Use it on what you write into run.json, a card, a brief or an index."""
    return _repo_paths().to_portable(s)


def local(obj, labels=None):
    """The reader's half: a record read back (dict/list/str) with its repo-relative paths made
    absolute in this checkout; "Shared Assets/…" labels through labels(label) when given."""
    return _repo_paths().to_local(obj, labels=labels)
