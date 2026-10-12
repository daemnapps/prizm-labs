#!/usr/bin/env python3
"""How the email line reaches the Shared Assets Drive — one helper, three ways.

SI-38 (email Drive reach), 2026-10-07. This replaces the three `_drive_mount()`
copies (simple_email.py, build_dashboard.py, pull/build_email_folders.py), each
of which globbed every Drive account's mount and, with no mount, fell back to a
path that did not exist — so a machine with no mount built a fake local Drive tree
without a word.

KEY PRESENCE DECIDES (route()):
  1 `GDRIVE_SA_KEY` in the environment -> "api": gdrive-creator by id, even
    when a mount exists (a mini job holding a grant, or a person who chose it)
  2 a Shared Assets mount               -> "mount": components/brandpath
    drive_index.mount(), called as it is
  3 neither                             -> NoDrive, naming both

Only the key's NAME is checked; nothing here loads a vault into the
environment, and nothing on these paths may before route() runs.

Never deletes, moves, renames or lists a Drive file. A folder listing is a
mount-only act (gdrive-creator has no list function): callers that need one
say so. Same names and shapes as image-production's drive_reach.py (SI-37
(image Drive reach)), so the clean-up phase can fold the two into one.

Stdlib only at module level; the Google client is gdrive-creator's business.
"""
import os
import shutil
import sys
from pathlib import Path

from paths import component

KEY_ENV = "GDRIVE_SA_KEY"
SHARED_DRIVE = "Shared Assets"
NO_DRIVE = ("no Drive here: no Shared Assets mount on this machine and no "
            "GDRIVE_SA_KEY in the environment — nothing was read from or "
            "written to the Drive")


class NoDrive(Exception):
    pass


def mount():
    """`Shared Assets` on this machine's Drive mount, or None — the shared
    helper's answer (components/brandpath drive_index.mount())."""
    p = str(component("brandpath"))
    if p not in sys.path:
        sys.path.append(p)                  # appended, never ahead of the caller
    import drive_index
    try:
        return drive_index.mount()
    except OSError:
        return None


def route():
    """"api" or "mount", else NoDrive.

    (1) GDRIVE_SA_KEY in the environment, non-empty -> "api", even when a
    mount exists; (2) a Shared Assets mount -> "mount"; (3) NoDrive(NO_DRIVE).
    Only the key's NAME is checked; nothing here loads a vault into the
    environment."""
    if os.environ.get(KEY_ENV):
        return "api"
    if mount() is not None:
        return "mount"
    raise NoDrive(NO_DRIVE)


def _engine():
    """gdrive-creator's engine. Imported at call time, never at import."""
    p = str(component("gdrive-creator"))
    if p not in sys.path:
        sys.path.append(p)
    from gdrive_creator import engine
    return engine


def shared_assets_id(svc):
    """The id of the shared drive named Shared Assets (its root folder's id),
    or None when this key cannot see it."""
    resp = svc.drives().list(pageSize=100, fields="drives(id,name)").execute()
    for d in resp.get("drives", []) or []:
        if d.get("name") == SHARED_DRIVE:
            return d["id"]
    return None


def folder_id(parts, svc, make=False):
    """The Drive id of Shared Assets/<parts...>. make=False finds each step by
    name and answers None at the first one missing; make=True makes a missing
    step (gdrive-creator's folder(): two looks before a create)."""
    parent = shared_assets_id(svc)
    if parent is None:
        if make:
            raise NoDrive(f"this key sees no shared drive named {SHARED_DRIVE!r}")
        return None
    E = _engine()
    for part in parts:
        if make:
            parent = E.folder(part, parent, svc=svc)
            continue
        hit = E.find_file(svc, part, parent, mime=E.FOLDER_MIME)
        if not hit:
            return None
        parent = hit["id"]
    return parent


def put(files, parts, svc=None):
    """Files onto the Drive under Shared Assets/<parts...>, same names.
    Returns (how, placed, note).

    mount: the folder is made and each file copied over the same name;
    placed = the full mount paths. api: the folder chain is found or made by
    id and each file uploaded (updated in place when the name is there);
    placed = "Shared Assets/<parts>/<name>". Any failure stops the rest and
    comes back as note = "SKIP the rest of the Drive mirror — <ExcType>: <msg>";
    SystemExit (gdrive-creator's missing-package refusal) is never caught."""
    placed = []
    try:
        how = route()
    except NoDrive as e:
        return "none", placed, f"SKIP the rest of the Drive mirror — NoDrive: {e}"
    try:
        if how == "mount":
            sa = mount()
            if sa is None:
                raise NoDrive(NO_DRIVE)
            dest = sa.joinpath(*parts)
            dest.mkdir(parents=True, exist_ok=True)
            for f in files:
                shutil.copy2(str(f), str(dest / Path(f).name))
                placed.append(str(dest / Path(f).name))
        else:
            E = _engine()
            svc = svc or E.service()
            fid = folder_id(parts, svc, make=True)
            for f in files:
                E.upload_file(f, Path(f).name, fid, svc=svc)
                placed.append("/".join([SHARED_DRIVE, *parts, Path(f).name]))
    except Exception as e:
        return how, placed, f"SKIP the rest of the Drive mirror — {type(e).__name__}: {e}"
    return how, placed, None


def get(parts, name, dest_dir, svc=None):
    """Shared Assets/<parts...>/<name>, as a local file, or None.

    mount: the file on the mount itself, no copy. api: found by name under the
    folder chain, read by id into <dest_dir>/<name>. A read never creates a
    folder. NoDrive and API exceptions propagate."""
    how = route()
    if how == "mount":
        try:
            sa = mount()
            p = sa.joinpath(*parts, name) if sa is not None else None
            return p if p is not None and p.is_file() else None
        except OSError:
            return None
    E = _engine()
    svc = svc or E.service()
    fid = folder_id(parts, svc, make=False)
    if fid is None:
        return None
    hit = E.find_file(svc, name, fid)
    if not hit:
        return None
    return Path(E.get_media(hit["id"], Path(dest_dir) / name, svc=svc))
