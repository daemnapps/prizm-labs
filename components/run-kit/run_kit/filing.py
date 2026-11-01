"""Where a run lives: runs/<tool>/<brand>/<label>/ in the repo, and the same
path under Shared Assets/runs/ on Drive for media (runs/README.md, ruled
2026-09-17). The Drive mount is found through the one shared helper,
components/brandpath/drive_index.py mount() (O9 (Drive by fileId)); a missing
mount is a loud MountError. Layout lifted from video-teardown chain.py:51-97."""
import sys
from pathlib import Path

from . import paths

_BRANDPATH = Path(__file__).resolve().parents[2] / "brandpath"


class MountError(Exception):
    pass


def run_dir(tool, brand, label, start=None):
    d = paths.repo(start) / "runs" / tool / brand / label
    d.mkdir(parents=True, exist_ok=True)
    return d


def drive_runs():
    if str(_BRANDPATH) not in sys.path:
        sys.path.append(str(_BRANDPATH))
    import drive_index
    m = drive_index.mount()
    if m is None:
        raise MountError("no Google Drive with Shared drives/Shared Assets is mounted on this machine "
                         "(looked through components/brandpath/drive_index.py mount())")
    return m / "runs"


def media_dir(tool, brand, label):
    d = drive_runs() / tool / brand / label
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- deliverable

def deliver(run_dir, files, name=None):
    """Put the thing a person traffics where the standard says it goes.

    `runs/README.md` has said since 2026-09-17 that the deliverable lives in
    `runs/<machine>/<brand>/<label>/deliverable/`. On 2026-09-23 an index over
    every run found 189 runs and THREE briefs actually filed there — 110 were
    somewhere inside their run that only that machine's own code knows about.
    That is how the Clipper Kit came to read its briefs out of a cloned lane's
    private runs folder, and how deleting that lane took six briefs with it.

    A machine calls this once, at the end, with whatever it hands on. The copy
    is a copy: the working record keeps its own file where it always was, so
    nothing upstream has to change to start being findable.

    Returns the list of paths written.
    """
    import shutil
    run_dir = Path(run_dir)
    out = run_dir / "deliverable"
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for i, f in enumerate(files if isinstance(files, (list, tuple)) else [files]):
        f = Path(f)
        if not f.is_file():
            continue
        dest = out / (name if name and i == 0 else f.name)
        if dest.resolve() == f.resolve():
            written.append(dest)
            continue
        shutil.copy2(f, dest)
        written.append(dest)
    return written
