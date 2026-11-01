"""How this engine reaches the Shared Assets Drive: the mount, or the API by id.

O9 (Drive by fileId), as narrowed for this phase: a person's run may use the
Drive for desktop mount; a job nobody watches goes through the API by file id.
KEY PRESENCE decides (SI-37, image Drive reach, 2026-10-07). The mini HAS a
mount, and reading through it from a session's shell failed (EDEADLK on 356 of
356 stats), so a key wins even where a mount exists.

**NOTHING IS EVER DELETED ON THE DRIVE, MOUNT OR API.** The mount copies a
file in, or over the same name; the API goes through gdrive-creator's
`folder` (made if missing) and `upload_file` (same name = updated in place).
Nothing here deletes, moves, renames or lists a Drive file.

A THIN SHIM since LD-14 (shared Drive reach), 2026-10-18: the substance is
components/gdrive-creator's `reach` (O1 (third copy extracts)). Every public
name stays and behaves as before; what is this copy's own stays here — the
mount found through this engine's `paths`, NoDrive raised by route() and
put() rather than skipped, only files that exist put, and a shared drive this
key cannot see is a NoDrive.

Stdlib only at import (`reach` and gdrive-creator's engine import no Google
package); the Google client is reached on the API route alone, so a person's
run on the mount never needs the Google packages.

No brand, product, person or account is named in this file.
"""
import sys
from pathlib import Path

from . import paths as P

_HOME = next((d / "gdrive-creator" for d in Path(__file__).resolve().parents
              if (d / "gdrive-creator" / "gdrive_creator").is_dir()), None)
if _HOME is not None and str(_HOME) not in sys.path:
    sys.path.append(str(_HOME))
from gdrive_creator import reach as R      # noqa: E402

KEY_ENV = R.KEY_ENV
SHARED_DRIVE = R.SHARED_DRIVE
NO_DRIVE = R.NO_DRIVE
NoDrive = R.NoDrive


def loud(what, err):
    """Say OUT LOUD that a Drive read did not happen (LD-47 (Drive sweep), step 1). These places used
    to answer empty in silence, so a mini run read "nothing there"; the caller still carries on."""
    print(f"DRIVE NOT REACHED — {what}: {type(err).__name__}: {err} "
          "(no Drive folder on this machine? reach it through gdrive-creator)", file=sys.stderr)


def mount():
    """`Shared Assets` on this machine's Drive for desktop mount, or None."""
    # A probe, not a read: route() asks it and raises NoDrive, naming both doors, when neither is
    # here — so None stays quiet (LD-47 step 1 reviewed this site; a line here would print on every
    # API-route run).
    try:
        return P.drive_runs().parent
    except P.MountError:
        return None


def route():
    """How this run reaches Shared Assets. A GDRIVE_SA_KEY in the environment
    means the API through gdrive-creator by file id — a mini job holding a
    grant, or a person who chose it — even where a mount exists. No key: this
    machine's Drive for desktop mount (components/brandpath drive_index.mount()).
    Neither: NoDrive, naming both. Only the key's NAME is checked here;
    gdrive-creator reads its value. Nothing here loads a vault into the
    environment."""
    return R.route(find_mount=mount)


def _engine():
    """components/gdrive-creator's engine, found upward from this file."""
    from gdrive_creator import engine
    return engine


def shared_assets_id(svc):
    """The id of the shared drive named Shared Assets — a shared drive's id is
    its root folder id."""
    got = R.shared_assets_id(svc)
    if got is None:
        raise NoDrive(f"this key cannot see a shared drive named '{SHARED_DRIVE}'")
    return got


def folder_id(parts, svc, make=False):
    """The folder Shared Assets/<parts...> by id, one step per name. make=True
    makes a missing step (gdrive-creator `folder`); make=False only looks, and
    answers None at the first missing step — nothing is created."""
    E = _engine()
    return R.folder_id(parts, svc, make=make, find_engine=lambda: E,
                       root=shared_assets_id(svc))


def put(files, parts, svc=None):
    """Put files into Shared Assets/<parts...>. Returns (how, placed, note).

    `how` is route() — NoDrive goes to the caller. A file already there is
    REPLACED IN PLACE (same name), which keeps its Drive id and every link
    already given. `note` is None, or SKIP and the first failure; what was
    placed before it stays placed."""
    route()
    srcs = [Path(f) for f in files if Path(f).is_file()]
    return R.put(srcs, parts, svc, find_mount=mount, find_engine=_engine)


def put_ids(files, parts, svc=None):
    """put(), keeping the Drive ids (LD-64 (records Drive ids)): gdrive-creator's
    reach.put_ids answer — how, placed, note, folder, folder_id and one
    {name, id, kind} row per placed file. NoDrive goes to the caller."""
    route()
    srcs = [Path(f) for f in files if Path(f).is_file()]
    return R.put_ids(srcs, parts, svc, find_mount=mount, find_engine=_engine)


drive_json = R.drive_json
DRIVE_JSON = R.DRIVE_JSON
