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
mount-only act here: callers that need one say so.

A THIN SHIM since LD-14 (shared Drive reach), 2026-10-18: the two copies this
file's SI-38 note promised to fold are folded into components/gdrive-creator's
`reach` (O1 (third copy extracts)), which also lists and fetches a folder
through the API (`fetch_folder`, `readable`). Every public name here stays and
behaves as before; `mount` and `_engine` stay this file's own, so a test or a
caller that patches them still steers every call.

Stdlib only at module level; the Google client is gdrive-creator's business.
"""
import sys

from paths import component

_GC = str(component("gdrive-creator"))
if _GC not in sys.path:
    sys.path.append(_GC)                    # appended, never ahead of the caller
from gdrive_creator import reach as R      # noqa: E402

KEY_ENV = R.KEY_ENV
SHARED_DRIVE = R.SHARED_DRIVE
NO_DRIVE = R.NO_DRIVE
NoDrive = R.NoDrive


def mount():
    """`Shared Assets` on this machine's Drive mount, or None — the shared
    helper's answer (components/brandpath drive_index.mount())."""
    return R.mount()


def route():
    """"api" or "mount", else NoDrive.

    (1) GDRIVE_SA_KEY in the environment, non-empty -> "api", even when a
    mount exists; (2) a Shared Assets mount -> "mount"; (3) NoDrive(NO_DRIVE).
    Only the key's NAME is checked; nothing here loads a vault into the
    environment."""
    return R.route(find_mount=mount)


def _engine():
    """gdrive-creator's engine. Imported at call time, never at import."""
    from gdrive_creator import engine
    return engine


def shared_assets_id(svc):
    """The id of the shared drive named Shared Assets (its root folder's id),
    or None when this key cannot see it."""
    return R.shared_assets_id(svc)


def folder_id(parts, svc, make=False):
    """The Drive id of Shared Assets/<parts...>. make=False finds each step by
    name and answers None at the first one missing; make=True makes a missing
    step (gdrive-creator's folder(): two looks before a create)."""
    return R.folder_id(parts, svc, make=make, find_engine=_engine)


def put(files, parts, svc=None):
    """Files onto the Drive under Shared Assets/<parts...>, same names.
    Returns (how, placed, note).

    mount: the folder is made and each file copied over the same name;
    placed = the full mount paths. api: the folder chain is found or made by
    id and each file uploaded (updated in place when the name is there);
    placed = "Shared Assets/<parts>/<name>". Any failure stops the rest and
    comes back as note = "SKIP the rest of the Drive mirror — <ExcType>: <msg>";
    SystemExit (gdrive-creator's missing-package refusal) is never caught."""
    return R.put(files, parts, svc, find_mount=mount, find_engine=_engine)


def get(parts, name, dest_dir, svc=None):
    """Shared Assets/<parts...>/<name>, as a local file, or None.

    mount: the file on the mount itself, no copy. api: found by name under the
    folder chain, read by id into <dest_dir>/<name>. A read never creates a
    folder. NoDrive and API exceptions propagate."""
    return R.get(parts, name, dest_dir, svc, find_mount=mount, find_engine=_engine)
