"""How this engine reaches the Team Drive Drive: the mount, or the API by id.

O9 (Drive by fileId), as narrowed for this phase: a person's run may use the
Drive for desktop mount; a job nobody watches goes through the API by file id.
KEY PRESENCE decides (SI-37, image Drive reach, 2026-10-07). The mini HAS a
mount, and reading through it from a session's shell failed (EDEADLK on 356 of
356 stats), so a key wins even where a mount exists.

**NOTHING IS EVER DELETED ON THE DRIVE, MOUNT OR API.** The mount copies a
file in, or over the same name; the API goes through gdrive-creator's
`folder` (made if missing) and `upload_file` (same name = updated in place).
Nothing here deletes, moves, renames or lists a Drive file.

Stdlib only at import. gdrive-creator is imported on the API route alone, so a
person's run on the mount never needs the Google packages.

No brand, product, person or account is named in this file.
"""
import os
import shutil
import sys
from pathlib import Path

from . import paths as P

KEY_ENV = "GDRIVE_SA_KEY"
SHARED_DRIVE = "Team Drive"
NO_DRIVE = ("no Drive here: no Team Drive mount on this machine and no "
            "GDRIVE_SA_KEY in the environment — nothing was read from or "
            "written to the Drive")


class NoDrive(Exception):
    """No route to the Drive. The message says why."""


def mount():
    """`Team Drive` on this machine's Drive for desktop mount, or None."""
    try:
        return P.drive_runs().parent
    except P.MountError:
        return None


def route():
    """How this run reaches Team Drive. A GDRIVE_SA_KEY in the environment
    means the API through gdrive-creator by file id — a mini job holding a
    grant, or a person who chose it — even where a mount exists. No key: this
    machine's Drive for desktop mount (components/brandpath drive_index.mount()).
    Neither: NoDrive, naming both. Only the key's NAME is checked here;
    gdrive-creator reads its value. Nothing here loads a vault into the
    environment."""
    if os.environ.get(KEY_ENV):
        return "api"
    if mount() is not None:
        return "mount"
    raise NoDrive(NO_DRIVE)


def _engine():
    """components/gdrive-creator's engine, found upward from this file."""
    here = Path(__file__).resolve()
    home = next((d / "components" / "gdrive-creator" for d in here.parents
                 if (d / "components" / "gdrive-creator" / "gdrive_creator").is_dir()), None)
    if home is not None and str(home) not in sys.path:
        sys.path.append(str(home))
    from gdrive_creator import engine
    return engine


def shared_assets_id(svc):
    """The id of the shared drive named Team Drive — a shared drive's id is
    its root folder id."""
    r = svc.drives().list(pageSize=100, fields="drives(id,name)").execute()
    for d in r.get("drives") or []:
        if d.get("name") == SHARED_DRIVE:
            return d["id"]
    raise NoDrive(f"this key cannot see a shared drive named '{SHARED_DRIVE}'")


def folder_id(parts, svc, make=False):
    """The folder Team Drive/<parts...> by id, one step per name. make=True
    makes a missing step (gdrive-creator `folder`); make=False only looks, and
    answers None at the first missing step — nothing is created."""
    E = _engine()
    parent = shared_assets_id(svc)
    for name in parts:
        if make:
            parent = E.folder(name, parent, svc)
        else:
            got = E.find_file(svc, name, parent, mime=E.FOLDER_MIME)
            if not got:
                return None
            parent = got["id"]
    return parent


def put(files, parts, svc=None):
    """Put files into Team Drive/<parts...>. Returns (how, placed, note).

    `how` is route() — NoDrive goes to the caller. A file already there is
    REPLACED IN PLACE (same name), which keeps its Drive id and every link
    already given. `note` is None, or SKIP and the first failure; what was
    placed before it stays placed."""
    how = route()
    srcs = [Path(f) for f in files if Path(f).is_file()]
    placed = []
    if how == "mount":
        try:
            dest = mount().joinpath(*parts)
            dest.mkdir(parents=True, exist_ok=True)
            for src in srcs:
                shutil.copy2(src, dest / src.name)
                placed.append(str(dest / src.name))
        except OSError as e:
            return how, placed, f"SKIP the rest of the Drive mirror — {type(e).__name__}: {e}"
        return how, placed, None
    where = "Team Drive/" + "/".join(parts) + "/"
    try:
        E = _engine()
        svc = svc or E.service()
        fid = folder_id(parts, svc, make=True)
        for src in srcs:
            E.upload_file(src, src.name, fid, svc=svc)
            placed.append(where + src.name)
    except Exception as e:                # SystemExit is not an Exception: it stays loud
        return how, placed, f"SKIP the rest of the Drive mirror — {type(e).__name__}: {e}"
    return how, placed, None
