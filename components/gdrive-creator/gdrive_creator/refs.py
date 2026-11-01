#!/usr/bin/env python3
"""Stored references: the one public surface for writing a file reference into a record and reading it
back on any machine (LD-79 (Drive ref resolver), 2026-10-22; builder-card rule 4: "any file reference
written into a record, layout, card, brief or run file is a repo-relative git-tracked path or
{drive_id, label}, never an absolute machine path").

    from gdrive_creator import refs
    ref = refs.put(local_png, "Shared Assets/runs/<machine>/<brand>/<label>")
                                   # -> {"drive_id", "label": "Shared Assets/…/<name>", "bytes"}
    path = refs.local(ref)         # -> a file that reads, in the lasting cache

THE SURFACE
  put(local, label)    one file onto the Drive folder `label` (reach.put_ids: folders made if missing,
                       same name = updated in place) -> {"drive_id", "label", "bytes"}. drive_id is None
                       on the mount route (Drive for Desktop assigns ids asynchronously; the label alone
                       then resolves). Nothing placed: reach.NoDrive, put_ids' note in the message.
  local(ref)           a Path that reads:
                         {drive_id, label, bytes}  the cached file at cache_home()/<label after
                                                   "Shared Assets/"> when its size == bytes (no Drive
                                                   call), else engine.get_media(drive_id) into that place
                         {label} (no drive_id)     reach.readable(label), copied into that same place
                         "repo/relative/path"      that file under the repo; FileNotFoundError naming it
                         "/an/absolute/path"       LEGACY: the path itself when it exists (read-only,
                                                   never written back), else Unportable naming it
  is_ref(x)            True for a dict carrying "label" or a repo-relative string
  Unportable           an absolute machine path that does not exist here

ONE LASTING CACHE: shared.cache_home() (DRIVE_CACHE, else ~/.upright/cache/drive/Shared Assets), so a
file fetched once is a hit in every later process. Nothing here deletes, moves or renames, on the
Drive or on disk. Stdlib only at import. Python 3.9.

No brand, product, person or account is named in this file.
"""
import os
import shutil
from pathlib import Path

from . import reach

_HERE = Path(__file__).resolve()


class Unportable(Exception):
    """A stored absolute machine path that does not exist on this machine."""

    def __init__(self, path):
        self.path = str(path)
        super().__init__("%s: stored as a machine path; store a {drive_id, label} ref "
                         "(builder-card rule 4)" % self.path)


def _rest(label):
    """The parts of a "Shared Assets/…" label after the drive's name; ValueError when it names
    nothing on that drive or would step outside it."""
    parts = reach._drive_parts(label) if label else None
    if not parts or any(p in ("", ".", "..") for p in parts):
        raise ValueError("%r: not a \"%s/…\" file label" % (label, reach.SHARED_DRIVE))
    return parts


def _repo():
    """The workspace root: the nearest folder above this file holding .git (a folder, or a
    worktree's .git file)."""
    for d in _HERE.parents:
        if (d / ".git").exists():
            return d
    raise FileNotFoundError("no .git above %s: the workspace root is not found" % _HERE)


def _cached(label):
    from . import shared
    return shared.cache_home().joinpath(*_rest(label))


def is_ref(x):
    """True for a stored reference: a dict carrying "label", or a repo-relative path string."""
    if isinstance(x, dict):
        return bool(x.get("label"))
    return isinstance(x, str) and bool(x) and not os.path.isabs(x)


def put(local, label, svc=None, find_mount=None, find_engine=None):
    """`local` onto the Drive folder `label` ("Shared Assets/…"), same name. Returns
    {"drive_id", "label": "<label>/<name>", "bytes"}; drive_id None on the mount route."""
    src = Path(str(local))
    parts = _rest(label)
    r = reach.put_ids([src], parts, svc=svc, find_mount=find_mount, find_engine=find_engine)
    if not r["files"]:
        raise reach.NoDrive("%s: not placed in %s — %s" % (src, reach._label(parts), r["note"]))
    row = r["files"][0]
    return {"drive_id": row["id"], "label": "/".join([r["folder"], row["name"]]),
            "bytes": src.stat().st_size}


def local(ref, svc=None, find_mount=None, find_engine=None, repo=None):
    """A Path that reads for a stored reference (see the module's note)."""
    if isinstance(ref, dict):
        label = ref.get("label")
        dest = _cached(label)
        if ref.get("drive_id"):
            want = ref.get("bytes")
            if dest.is_file() and (want is None or dest.stat().st_size == int(want)):
                return dest
            E = (find_engine or reach._engine)()
            return Path(E.get_media(ref["drive_id"], dest, svc=svc))
        got = Path(reach.readable(label, svc=svc, find_mount=find_mount, find_engine=find_engine))
        if got.resolve() != dest.resolve():
            dest.parent.mkdir(parents=True, exist_ok=True)
            if got.is_dir():
                shutil.copytree(str(got), str(dest), dirs_exist_ok=True)
            else:
                shutil.copy2(str(got), str(dest))
        return dest
    s = os.fspath(ref)
    if os.path.isabs(s):
        if os.path.exists(s):
            return Path(s)
        raise Unportable(s)
    p = Path(repo or _repo()) / s
    if not p.exists():
        raise FileNotFoundError("%s: not in the repo at %s" % (s, p))
    return p
