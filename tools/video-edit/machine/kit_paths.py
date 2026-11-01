#!/usr/bin/env python3
"""kit_paths.py — how a kit names its media so it reads the same on every Mac
(LD-2 (portable video kits); fixes video-edit-dry-1, where kit srcs were one
Mac's /Users/… paths).

    portable(path, kit_dir) -> str          the WRITE side (kit_from_run.py)
    resolve(src, kit_dir)   -> Path | None  the READ side (run.py gather)

A portable ref is, in this order of preference:
  kit-relative       the file is under the kit folder            media/S1.mp4
  repo-relative      the file is under the workspace             runs/video-production/<brand>/<label>/media/S1.mp4
  Shared Assets/…    the file is under the Drive mount           Shared Assets/banks/music/m1.mp3
  absolute           none of those — a last resort, printed as a WARN, because it reads only on this machine

`resolve` turns any of the four back into an absolute path when the file is on
this machine, and gives None when it is not, so the caller leaves the ref as
written and the gate names it. An old kit's absolute src is kept as it is.
The workspace is run-kit's `paths.repo()`; the mount is brandpath's
`drive_index.mount()` — both public surfaces, both found by walking up from here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

COMPONENTS = Path(__file__).resolve().parents[2]   # tools/video-edit/machine → components/
SHARED = "Shared Assets"


def repo() -> Path | None:
    """The workspace root (run-kit `paths.repo()`, which honours AI_WORKSPACE), or None."""
    p = str(COMPONENTS / "run-kit")
    if p not in sys.path:
        sys.path.insert(0, p)
    try:
        from run_kit import paths
        return paths.repo(__file__)
    except (ImportError, FileNotFoundError):
        return None


def mount() -> Path | None:
    """`Shared Assets` on this Mac's Drive mount (brandpath `drive_index.mount()`), or None."""
    p = str(COMPONENTS / "brandpath")
    if p not in sys.path:
        sys.path.insert(0, p)
    try:
        import drive_index
    except ImportError:
        return None
    return drive_index.mount()


def _forms(p: Path) -> list[Path]:
    """The path as written (made absolute) and with its links followed — a temp folder
    on macOS is both /var/… and /private/var/…."""
    a = Path(os.path.abspath(str(p)))
    r = a.resolve()
    return [a] if r == a else [a, r]


def _under(path: Path, base) -> str | None:
    if base is None:
        return None
    for f in _forms(path):
        for b in _forms(Path(base)):
            try:
                return f.relative_to(b).as_posix()
            except ValueError:
                continue
    return None


def portable(path, kit_dir) -> str:
    """The ref a kit stores for a file: kit-relative, repo-relative, `Shared Assets/<rest>`,
    else absolute with a WARN. `kit_dir` may be None when the kit folder is not known yet."""
    p = Path(str(path))
    rel = _under(p, kit_dir)
    if rel is not None:
        return rel
    rel = _under(p, repo())
    if rel is not None:
        return rel
    rel = _under(p, mount())
    if rel is not None:
        return f"{SHARED}/{rel}"
    # KEYS ONLY (2026-10-20, lead 088): a file the key fetched sits in gdrive-creator's API cache —
    # shared.cache_home() (<tmp>/upright-drive/Shared Assets/<rest>) or reach.cache_root()
    # (<tmp>/gdrive-reach-<pid>/<rest>). The kit stores its "Shared Assets/<rest>" label, never that
    # machine path; resolve() reads it back through reach.readable() (_api).
    rest = _after_shared(p.parts)
    if rest:
        return "/".join((SHARED,) + rest)
    try:
        rel = _under(p, R.cache_root())
    except Exception:
        rel = None
    if rel is not None:
        return f"{SHARED}/{rel}"
    a = _forms(p)[0]
    print(f"WARN  kit ref {a}: not under the kit, the workspace or {SHARED} — written absolute, it reads only on this machine")
    return str(a)


_GDRIVE = next((d / "gdrive-creator" for d in Path(__file__).resolve().parents
                if (d / "gdrive-creator" / "gdrive_creator").is_dir()), None)
if _GDRIVE is not None and str(_GDRIVE) not in sys.path:
    sys.path.append(str(_GDRIVE))
from gdrive_creator import reach as R      # noqa: E402

READABLE = R.readable    # the seam tests patch: a `Shared Assets/…` label → a path that reads (LD-15 (kit reads by API))


def _after_shared(parts) -> tuple:
    """The parts after the last `Shared Assets` part, or () when there is none."""
    if SHARED not in parts:
        return ()
    last = len(parts) - 1 - parts[::-1].index(SHARED)
    return tuple(parts[last + 1:])


def _api(p: Path) -> Path | None:
    """LD-15 (kit reads by API): the file a src with a `Shared Assets` part names, read through
    gdrive-creator `reach.readable()` on its `Shared Assets/<rest>` label — the mount when it
    reads, else a copy by the API in this process's cache. Not on the Drive, no key, or not a
    file: None, and the gate names the ref as written. Nothing is written into the kit."""
    rest = _after_shared(p.parts)
    if not rest:
        return None
    try:
        got = Path(str(READABLE("/".join((SHARED,) + rest))))
        return Path(os.path.abspath(str(got))) if got.is_file() else None
    except (R.NoDrive, SystemExit, OSError):
        return None


def _is_file(p: Path) -> bool:
    """`p.is_file()`, False when the stat itself raises (LD-24 (kit mount deadlock)): a Drive for
    desktop placeholder answers EDEADLK, which pathlib does not swallow — "not here", so the
    caller goes on to the next place and, last, the Drive API."""
    try:
        return p.is_file()
    except OSError:
        return False


def _foreign(p: Path) -> list[Path]:
    """Where an absolute path from another Mac may sit on this one (LD-13 (old kits remap)):
    the parts after its last `Shared Assets` on this mount, then the parts from its first
    repo top folder in this checkout."""
    places = []
    parts = p.parts
    rest = _after_shared(parts)
    if rest:
        m = mount()
        if m is not None:
            places.append(Path(m).joinpath(*rest))
    tops = ("runs", "components", "brands", "lab", "new-workflow-design")
    at = next((i for i, part in enumerate(parts) if part in tops), None)
    if at is not None:
        root = repo()
        if root is not None:
            places.append(Path(root).joinpath(*parts[at:]))
    return places


def resolve(src, kit_dir) -> Path | None:
    """The file a kit ref names, as an absolute path, or None when it is not on this machine.
    Absolute → kept when it is a file here, else mapped by its suffix (`_foreign`); else
    kit-relative, then repo-relative, then `Shared Assets/…` on the mount. Last, a src with a
    `Shared Assets` part is read through the Drive API (`_api`, LD-15 (kit reads by API))."""
    if not src:
        return None
    p = Path(str(src))
    if p.is_absolute():
        if _is_file(p):
            return p
        for c in _foreign(p):
            if _is_file(c):
                return Path(os.path.abspath(str(c)))
        return _api(p)
    places = []
    if kit_dir is not None:
        places.append(Path(kit_dir) / p)
    root = repo()
    if root is not None:
        places.append(root / p)
    if p.parts[:1] == (SHARED,):
        m = mount()
        if m is not None:
            places.append(m.joinpath(*p.parts[1:]))
    for c in places:
        if _is_file(c):
            return Path(os.path.abspath(str(c)))
    return _api(p)
