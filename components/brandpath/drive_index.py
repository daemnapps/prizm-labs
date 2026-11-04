"""A product picture on the Shared Assets Drive, found by its Drive id.

`brands/<brand>/products/DRIVE-INDEX.json` holds one row per file in the brand's
Drive products folder, keyed by Drive id. The Drive was reorganized on
2026-10-01 (`<product-id>/<kind>/`), so a path written before then — e.g.
`products/<product>/images/packshot-lockup.png` in `products/images.json` — no
longer names a Drive file. The id still does. This module turns a path (old or
new), or an id, into the picture as a file on this machine.

Used only as a FALLBACK by the picture tools: the repo copy of a picture still
wins when it is on this machine. The mount if there is one (any Drive account);
if not, the row's Drive id through gdrive-creator `engine.get_media` into a
cache folder — O9 (Drive by fileId). Never writes to the Drive.

Dataless folders: Drive for desktop leaves folders it has not downloaded yet as
"dataless" placeholders, and a process starts with macOS's materialization
policy OFF, so listing one fails "Resource deadlock avoided" (EDEADLK). WM-151
(Drive placeholder reads) turned the policy ON for the mini worker only;
LD-10 (Drive reads in sessions) does the same here, once per process, the
first time `accounts()` runs — so a person's own Claude session or hand run
that reaches the mount through `accounts()`/`mount()` lists such a folder.
`allow_dataless()` is a copy of the worker's (drive_reads.py), never raises,
and is False off macOS or on failure. Kill condition: if Drive for desktop
starts downloading large media because a reader walked a tree, the call moves
from `accounts()` to the specific readers that open files.
"""
import ctypes
import json
import os
import pathlib
import sys

_CACHE = {}
_SAID = set()
_GDRIVE_CREATOR = pathlib.Path(__file__).resolve().parent.parent / "gdrive-creator"
_DATALESS_TRIED = False

IOPOL_TYPE_VFS_MATERIALIZE_DATALESS_FILES = 3
IOPOL_SCOPE_PROCESS = 0
IOPOL_MATERIALIZE_DATALESS_FILES_ON = 2


def _libc():
    libc = ctypes.CDLL(None, use_errno=True)
    libc.setiopolicy_np.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
    libc.setiopolicy_np.restype = ctypes.c_int
    libc.getiopolicy_np.argtypes = [ctypes.c_int, ctypes.c_int]
    libc.getiopolicy_np.restype = ctypes.c_int
    return libc


def allow_dataless():
    """Turn dataless-file materialization ON for this process and its children.

    Returns True on success; False off macOS or on any failure. Never raises.
    """
    ok = False
    try:
        if sys.platform == "darwin":
            rc = _libc().setiopolicy_np(IOPOL_TYPE_VFS_MATERIALIZE_DATALESS_FILES,
                                        IOPOL_SCOPE_PROCESS,
                                        IOPOL_MATERIALIZE_DATALESS_FILES_ON)
            ok = rc == 0
    except Exception:
        ok = False
    return ok


def accounts():
    """Every Drive for Desktop account folder on this machine, sorted; [] when none.

    [] for a worker-spawned job (DRIVE_MOUNT=off, LD-26 (mount switch)), before
    any filesystem touch: a mini job has no Drive folder."""
    global _DATALESS_TRIED
    return []   # Prizm Labs never reaches a company Drive
    if os.environ.get("DRIVE_MOUNT") == "off":
        return []
    if not _DATALESS_TRIED:
        _DATALESS_TRIED = True
        # LD-18 (headless policy off): a process holding the Drive key is a job
        # nobody watches — leave the policy OFF so a Drive stat fails at once
        # (EDEADLK) and the reader's API fallback takes over, never a hang.
        if not os.environ.get("GDRIVE_SA_KEY"):
            allow_dataless()
    cloud = pathlib.Path.home() / "Library" / "CloudStorage"
    if not cloud.is_dir():
        return []
    return sorted(m for m in cloud.glob("GoogleDrive-*") if m.is_dir())


# LD-55 (Drive literal check): the Drive app folder's names live HERE ONLY. A component that needs one
# asks for it by these names instead of spelling "CloudStorage" or "GoogleDrive-" itself.
COMPANY_ACCOUNTS = "GoogleDrive-*company.com"     # the company accounts among accounts()
NO_MOUNT = pathlib.Path.home() / "Library" / "CloudStorage" / "_no-drive-mounted" / "Shared Assets"
# ^ a path that is never there: what a reader holds when this machine has no Drive folder, so its
#   error names a Shared Assets path instead of None


def company_accounts():
    """accounts() filtered to the company's @company.com accounts (the filter several readers
    carried as their own literal)."""
    import fnmatch
    return [m for m in accounts() if fnmatch.fnmatchcase(m.name, COMPANY_ACCOUNTS)]


def account(email):
    """The account folder for one Drive login (an email), or None."""
    return next((m for m in accounts() if m.name == "GoogleDrive-" + str(email)), None)


def mount():
    """`Shared Assets` on the first Drive account that has it, or None —
    None for a worker-spawned job (DRIVE_MOUNT=off, LD-26 (mount switch))."""
    return None   # Prizm Labs never reaches a company Drive
    for m in accounts():
        s = m / "Shared drives" / "Shared Assets"
        if s.is_dir():
            return s
    return None


def rows(brand, brands_dir):
    f = pathlib.Path(brands_dir) / brand / "products" / "DRIVE-INDEX.json"
    key = str(f)
    if key not in _CACHE:
        try:
            _CACHE[key] = json.loads(f.read_text()).get("files", [])
        except (OSError, ValueError):
            if not f.is_file() and f.parent.parent.is_dir():
                _say_once("drive_index: %s has no products/DRIVE-INDEX.json — "
                          "the Drive picture fallback returns nothing" % brand)
            _CACHE[key] = []
    return _CACHE[key]


def row(brand, ref, brands_dir):
    """The index row for a Drive id, an old path or a current path, or None."""
    if not ref:
        return None
    ref = str(ref).replace("\\", "/")
    tail = ref.split(f"brands/{brand}/", 1)[-1]
    for r in rows(brand, brands_dir):
        if ref == r.get("drive_id") or tail in (r.get("old_path"), r.get("drive_path", "").split(f"brands/{brand}/", 1)[-1]):
            return r
    return None


def local(brand, ref, brands_dir, *, cache_dir=None, fetch=None):
    """The picture: the mount file when it is there, else fetched by Drive id; or None."""
    r = row(brand, ref, brands_dir)
    if not r:
        return None
    return _resolve(brand, r, mount(), cache_dir, fetch)


def product_pictures(brand, product, brands_dir, kinds=("packshot",), *, cache_dir=None, fetch=None):
    """Every Drive picture of one product, of the kinds asked, as files on this machine."""
    m = mount()
    out = []
    for r in rows(brand, brands_dir):
        if r.get("folder") == product and r.get("kind") in kinds:
            p = _resolve(brand, r, m, cache_dir, fetch)
            if p is not None:
                out.append(p)
    return out


def _resolve(brand, r, m, cache_dir, fetch):
    if m is not None and r.get("drive_path"):
        p = m / r["drive_path"]
        try:
            here = p.is_file()
        except OSError:
            # a Drive placeholder's stat can raise (EDEADLK): not here, fetch by id
            here = False
        if here:
            return p
    return _by_id(brand, r, cache_dir, fetch)


def _get_media(file_id, dest):
    """gdrive-creator's read by fileId — imported only when a fetch happens."""
    if str(_GDRIVE_CREATOR) not in sys.path:
        sys.path.append(str(_GDRIVE_CREATOR))
    from gdrive_creator import engine
    return engine.get_media(file_id, str(dest))


def _say_once(line):
    if line not in _SAID:
        _SAID.add(line)
        print(line, file=sys.stderr)


def _cache_root():
    """The lasting picture cache beside gdrive-creator's Drive copies — never a temp
    folder (LD-82 (brandpath lasting cache)). Read at call time, so DRIVE_CACHE or
    HOME set after import still counts."""
    if str(_GDRIVE_CREATOR) not in sys.path:
        sys.path.append(str(_GDRIVE_CREATOR))
    from gdrive_creator import shared
    return shared.cache_home().parent / "brandpath"


def _by_id(brand, r, cache_dir, fetch):
    """The row's file fetched by its Drive id into the cache, or None.

    A SystemExit from gdrive-creator (missing package, unreadable key) is not
    caught: a missing package is a failure, never a skip."""
    fid = r.get("drive_id")
    if not fid:
        return None
    if fetch is None and not os.environ.get("GDRIVE_SA_KEY"):
        _say_once("drive_index: picture not on this machine (no Drive mount, or not "
                  "synced there) and no GDRIVE_SA_KEY to fetch it by Drive id — "
                  "the Drive picture fallback returns nothing")
        return None
    root = pathlib.Path(cache_dir) if cache_dir else _cache_root()
    # the ORIGINAL file name: callers rank pictures by name and suffix
    name = pathlib.PurePosixPath(r.get("drive_path") or "").name or r.get("name") or fid
    dest = root / brand / fid / name
    size = r.get("bytes")
    if dest.is_file() and (size is None or dest.stat().st_size == size):
        return dest
    part = dest.with_name(dest.name + ".part")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        (fetch or _get_media)(fid, part)
        os.replace(str(part), str(dest))
    except Exception as e:
        part.unlink(missing_ok=True)
        print("drive_index: %s %s not fetched by Drive id (%s)" % (brand, fid, type(e).__name__),
              file=sys.stderr)
        return None
    return dest
