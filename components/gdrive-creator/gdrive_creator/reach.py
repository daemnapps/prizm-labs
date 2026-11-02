#!/usr/bin/env python3
"""One shared Drive reach: route by key, get, put, fetch a folder, make any
Drive path readable (LD-14 (shared Drive reach), 2026-10-18).

WHY ONE HOME. Two copies of the same reach existed —
tools/image-production/image_production/drive_reach.py (SI-37 (image
Drive reach)) and tools/email-production/drive_reach.py (SI-38 (email
Drive reach)) — and every mini reader needed a third, because Full Disk
Access is not applied to the mini's launchd jobs: a `launchctl submit` probe
on 2026-10-18 could not list ~/Desktop, Google's Drive folder or the rclone
mount. A third copy is the cue to extract (O1 (third copy extracts)). Both
copies are now thin shims over this file, every public name kept.

THE SURFACE
  route()                       "api" | "mount", else NoDrive
  get(parts, name, dest_dir)    Shared Assets/<parts>/<name> as a local file, or None
  put(files, parts)             (how, placed, note) — folders made if missing,
                                same name = updated in place
  put_ids(files, parts)         put's answer plus folder, folder_id and one
                                {name, id, kind} row per placed file
                                (LD-64 (records Drive ids))
  drive_json(parts, folder_id, route, files)
                                the drive.json record a push leaves — the one
                                place its shape is defined; pure
  kind(name)                    "image" | "video" | "audio" | "text" | "other"
  fetch_folder(parts, dest_dir, recursive=False, max_bytes=MAX_BYTES)
                                a local folder holding that Drive folder's files
  readable(path)                a path that reads: the mount path itself when
                                it lists/opens, else an API copy
plus mount(), folder_id(), shared_assets_id(), NoDrive, KEY_ENV, NO_DRIVE,
DRIVE_JSON.

KEY PRESENCE DECIDES the route (route()): GDRIVE_SA_KEY in the environment,
non-empty -> "api", even where a mount exists; else a Shared Assets mount
(components/brandpath drive_index.mount()) -> "mount"; else NoDrive naming
both. Only the key's NAME is checked here; the engine reads its value.
`readable()` is the one exception, on purpose: it tries the path it was given
FIRST, and only a path that does not list or open goes to the API.

**NOTHING HERE DELETES, MOVES OR RENAMES A DRIVE FILE, ON THE MOUNT OR THE
API.** The mount copies a file in, or over the same name; the API goes
through the engine's `folder` (made if missing) and `upload_file` (same name =
updated in place). Reads write only under the caller's dest_dir or this
lasting cache folder (cache_root(), ~/.upright/cache/drive); nothing is removed
from either. A test asserts it, on the calls and on the source.

SEAMS. Every call takes `svc` (the engine's fake seam) and two finders a shim
may pass in: `find_mount` (a callable answering the Shared Assets mount or
None; default `mount`) and `find_engine` (a callable answering the engine
module; default this package's `engine`). A shim passes its own, which is how
each keeps its current behaviour exactly.

Stdlib only at import; the Google client is imported inside the engine's
functions, so a run on the mount never needs it. Python 3.9.

No brand, product, person or account is named in this file.
"""
import mimetypes
import os
import shutil
import sys
import tempfile
from pathlib import Path

KEY_ENV = "GDRIVE_SA_KEY"
DRIVE_JSON = "drive.json"           # the record a push leaves (LD-64 (records Drive ids))
SHARED_DRIVE = "Shared Assets"
NO_DRIVE = ("no Drive here: no Shared Assets mount on this machine and no "
            "GDRIVE_SA_KEY in the environment — nothing was read from or "
            "written to the Drive")
SKIP = "SKIP the rest of the Drive mirror — "
MAX_BYTES = 2 * 1024 ** 3           # fetch_folder's default stop: 2 GiB

_BRANDPATH = Path(__file__).resolve().parent.parent.parent / "brandpath"
_READABLE = {}                      # label -> the local API copy, this process only


class NoDrive(Exception):
    """No route to the Drive. The message says why."""


def mount():
    """`Shared Assets` on this machine's Drive mount, or None — the shared
    helper's answer (components/brandpath drive_index.mount())."""
    p = str(_BRANDPATH)
    if p not in sys.path:
        sys.path.append(p)                  # appended, never ahead of the caller
    import drive_index
    try:
        return drive_index.mount()
    except OSError:
        return None


def _engine():
    from . import engine
    return engine


def _finders(find_mount, find_engine):
    return find_mount or mount, find_engine or _engine


def route(find_mount=None):
    """"api" or "mount", else NoDrive(NO_DRIVE). A GDRIVE_SA_KEY means the API even where a mount
    exists — found by the same lookup the engine uses (engine.has_key: the environment, a host's
    configured lookup, else the one key loader, so a person's ~/.upright-keys.env counts; LD-47
    (Drive sweep) step 1.6, 2026-10-20). An empty one is no key."""
    raise NoDrive("Prizm Labs does not reach company Drives")
    find_mount = find_mount or mount
    from . import engine as _keys          # the real lookup, not a test's stand-in engine: no network here
    if _keys.has_key(KEY_ENV):
        return "api"
    if find_mount() is not None:
        return "mount"
    raise NoDrive(NO_DRIVE)


def shared_assets_id(svc):
    """The id of the shared drive named Shared Assets (its root folder's id),
    or None when this key cannot see it."""
    from . import engine
    return engine.shared_drive_id(SHARED_DRIVE, svc)


def folder_id(parts, svc, make=False, find_engine=None, root=None):
    """The Drive id of Shared Assets/<parts...>, one step per name. make=True
    makes a missing step (the engine's `folder`: two looks before a create);
    make=False only looks and answers None at the first missing step —
    nothing is created. `root` starts the walk at a known id instead of the
    Shared Assets root. No shared drive: NoDrive when making, else None."""
    parent = root if root is not None else shared_assets_id(svc)
    if parent is None:
        if make:
            raise NoDrive(f"this key sees no shared drive named {SHARED_DRIVE!r}")
        return None
    E = (find_engine or _engine)()
    for part in parts:
        if make:
            parent = E.folder(part, parent, svc=svc)
            continue
        hit = E.find_file(svc, part, parent, mime=E.FOLDER_MIME)
        if not hit:
            return None
        parent = hit["id"]
    return parent


def put(files, parts, svc=None, find_mount=None, find_engine=None):
    """Files onto the Drive under Shared Assets/<parts...>, same names.
    Returns (how, placed, note).

    mount: the folder is made and each file copied over the same name;
    placed = the full mount paths. api: the folder chain is found or made by
    id and each file uploaded (updated in place when the name is there, which
    keeps its Drive id and every link already given); placed =
    "Shared Assets/<parts>/<name>". No route: ("none", [], SKIP + NoDrive).
    Any failure stops the rest and comes back as note = SKIP + "<ExcType>:
    <msg>"; what was placed before it stays placed. SystemExit (the engine's
    missing-package or missing-key refusal) is never caught."""
    r = put_ids(files, parts, svc=svc, find_mount=find_mount, find_engine=find_engine)
    return r["how"], r["placed"], r["note"]


IMAGE = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic", ".tif", ".tiff", ".bmp", ".svg")
VIDEO = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi")
AUDIO = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")
TEXT = (".json", ".jsonl", ".md", ".txt", ".csv", ".html", ".srt", ".vtt", ".log", ".yaml", ".yml")
KINDS = (("image", IMAGE), ("video", VIDEO), ("audio", AUDIO), ("text", TEXT))


def kind(name):
    """"image" | "video" | "audio" | "text" | "other" for a file name: the
    lower-cased suffix first, else mimetypes' major type when it is one of
    the four (LD-64 (records Drive ids))."""
    suffix = Path(str(name)).suffix.lower()
    for k, suffixes in KINDS:
        if suffix in suffixes:
            return k
    major = (mimetypes.guess_type(str(name))[0] or "").split("/")[0]
    return major if major in ("image", "video", "audio", "text") else "other"


def put_ids(files, parts, svc=None, find_mount=None, find_engine=None):
    """put(), keeping what the Drive gave back (LD-64 (records Drive ids)).
    Returns {"how", "placed", "note"} — exactly put's three — plus "folder"
    (the "Shared Assets/…" label), "folder_id" and "files": one
    {name, id, kind} row per PLACED file, in order.

    api: folder_id is the leaf folder's id and each id is upload_file's.
    mount: folder_id and every id are None — Drive for Desktop assigns an
    id only after its asynchronous sync, so none is read here. No route:
    files []. A failure part-way keeps the rows placed before it and note
    is put's SKIP text. SystemExit is never caught. No Drive call is added:
    the ids are the answers put already received."""
    find_mount, find_engine = _finders(find_mount, find_engine)
    out = {"how": "none", "placed": [], "note": None, "folder": _label(parts),
           "folder_id": None, "files": []}
    placed, rows = out["placed"], out["files"]
    try:
        how = route(find_mount)
    except NoDrive as e:
        out["note"] = f"{SKIP}NoDrive: {e}"
        return out
    out["how"] = how
    try:
        if how == "mount":
            sa = find_mount()
            if sa is None:
                raise NoDrive(NO_DRIVE)
            dest = Path(sa).joinpath(*parts)
            dest.mkdir(parents=True, exist_ok=True)
            for f in files:
                name = Path(f).name
                shutil.copy2(str(f), str(dest / name))
                placed.append(str(dest / name))
                rows.append({"name": name, "id": None, "kind": kind(name)})
        else:
            E = find_engine()
            svc = svc or E.service()
            fid = folder_id(parts, svc, make=True, find_engine=lambda: E)
            out["folder_id"] = fid
            for f in files:
                name = Path(f).name
                got = E.upload_file(f, name, fid, svc=svc)
                placed.append("/".join([SHARED_DRIVE] + list(parts) + [name]))
                rows.append({"name": name,
                             "id": got[0] if isinstance(got, (tuple, list)) else got,
                             "kind": kind(name)})
    except Exception as e:
        out["note"] = f"{SKIP}{type(e).__name__}: {e}"
    return out


def drive_json(parts, folder_id, route, files):
    """The drive.json record of one push (LD-64 (records Drive ids)) — the one
    place its shape is defined:
    {"schema": 1, "folder": "Shared Assets/<parts>", "folder_id", "route":
    "api" | "mount" | "none", "files": [{"path", "id", "kind"}]}. Each row's
    "path" is run-relative posix; a row with no kind gets kind(path). Rows
    are sorted by path. Pure: no I/O."""
    rows = [{"path": r["path"], "id": r.get("id"), "kind": r.get("kind") or kind(r["path"])}
            for r in files]
    return {"schema": 1, "folder": _label(parts), "folder_id": folder_id,
            "route": route, "files": sorted(rows, key=lambda r: r["path"])}


def _api_get(parts, name, dest_dir, svc, E):
    fid = folder_id(parts, svc, make=False, find_engine=lambda: E)
    if fid is None:
        return None
    hit = E.find_file(svc, name, fid)
    if not hit:
        return None
    return Path(E.get_media(hit["id"], Path(dest_dir) / name, svc=svc))


def get(parts, name, dest_dir, svc=None, find_mount=None, find_engine=None):
    """Shared Assets/<parts...>/<name>, as a local file, or None.

    mount: the file on the mount itself, no copy. api: found by name under the
    folder chain, read by id into <dest_dir>/<name>. A read never creates a
    Drive folder. NoDrive and API exceptions propagate."""
    find_mount, find_engine = _finders(find_mount, find_engine)
    how = route(find_mount)
    if how == "mount":
        try:
            sa = find_mount()
            p = Path(sa).joinpath(*parts, name) if sa is not None else None
            return p if p is not None and p.is_file() else None
        except OSError:
            return None
    E = find_engine()
    return _api_get(parts, name, dest_dir, svc or E.service(), E)


def _subfolders(svc, folder_id):
    """Every non-trashed child FOLDER of a folder, [{id, name}], every page —
    the half `list_files` leaves out. Parent-scoped, supportsAllDrives."""
    from . import engine
    q = (f"'{folder_id}' in parents and trashed = false "
         f"and mimeType = '{engine.FOLDER_MIME}'")
    out, token = [], None
    while True:
        kw = dict(q=q, fields="nextPageToken, files(id,name)", pageSize=100,
                  supportsAllDrives=True, includeItemsFromAllDrives=True)
        if token:
            kw["pageToken"] = token
        r = svc.files().list(**kw).execute()
        out.extend({"id": f.get("id"), "name": f.get("name")}
                   for f in r.get("files") or [])
        token = r.get("nextPageToken")
        if not token:
            return out


def subfolders(folder_id, svc=None, find_engine=None):
    """Every non-trashed child FOLDER of the folder with this Drive id, [{id, name}] in name order. READ-ONLY, one
    listing: a caller walking a few known levels (QB-9 (the team statics) reads hand-off folders this way) lists only
    the folders it needs, where list_tree would list every file under them."""
    svc = svc or (find_engine or _engine)().service()
    return sorted(_subfolders(svc, folder_id), key=lambda s: s["name"] or "")


MAX_ITEMS = 5000                    # list_tree's default stop: names, not bytes


def list_tree(parts, svc=None, find_engine=None, max_items=MAX_ITEMS):
    """Every FILE under Shared Assets/<parts...>, recursive, as [(relative
    path, file id)] — "a.jpg", "sub/b.jpg" — through the API by name (the
    engine's `folder_by_path` and `list_files`, plus `_subfolders`). Names
    only: NOTHING IS DOWNLOADED (no get_media), so a tree of any size costs
    one listing per folder; the caller fetches the one file it uses
    (`readable()`). Each folder's files in name order, then its subfolders
    in name order (fetch_folder's order). None when the Drive folder is not
    there (LD-16 (email design by API)).

    Once max_items files are listed nothing more is listed, and the stop is
    SAID on stderr, naming where it stopped. A read never creates a Drive
    folder."""
    E = (find_engine or _engine)()
    svc = svc or E.service()
    fid = E.folder_by_path(_label(parts), svc=svc)
    if not fid:
        return None
    out, stop = [], []
    _walk(E, svc, fid, max_items, out, stop)
    if stop:
        print("reach.list_tree: STOPPED at max_items=%d — %d files listed "
              "under %s; not listed: %s and everything after it" % (
                  max_items, len(out), _label(parts), stop[0]),
              file=sys.stderr)
    return out


def _walk(E, svc, fid, max_items, out, stop, rel=""):
    for f in sorted(E.list_files(fid, svc=svc), key=lambda f: f["name"] or ""):
        if max_items is not None and len(out) >= max_items:
            stop.append(rel + f["name"])
            return
        out.append((rel + f["name"], f["id"]))
    for sub in sorted(_subfolders(svc, fid), key=lambda s: s["name"] or ""):
        if stop:
            return
        if max_items is not None and len(out) >= max_items:
            stop.append(rel + sub["name"] + "/")
            return
        _walk(E, svc, sub["id"], max_items, out, stop, rel + sub["name"] + "/")


def _label(parts):
    return "/".join([SHARED_DRIVE] + [p for p in parts if p])


def fetch_folder(parts, dest_dir, recursive=False, max_bytes=MAX_BYTES,
                 svc=None, find_engine=None):
    """Shared Assets/<parts...> as a local folder at dest_dir, through the API
    by id — always the API: a folder that reads on the mount is local already
    (`readable()` prefers it). Returns dest_dir as a Path, or None when the
    Drive folder is not there (nothing is written then).

    Its files are read by id, in name order. Its subfolders are CREATED,
    and filled only when recursive=True. The bytes are counted as they land:
    once max_bytes is reached nothing more is fetched — the file that crossed
    it is kept whole — and the stop is SAID on stderr, naming what was left.
    A read never creates a Drive folder."""
    E = (find_engine or _engine)()
    svc = svc or E.service()
    fid = E.folder_by_path(_label(parts), svc=svc)
    if not fid:
        return None
    dest = Path(dest_dir)
    state = {"bytes": 0, "files": 0, "left": []}
    _fill(E, svc, fid, dest, recursive, max_bytes, state)
    if state["left"]:
        more = len(state["left"]) - 5
        print("reach.fetch_folder: STOPPED at max_bytes=%d — %d bytes in %d "
              "files fetched from %s; not fetched: %s%s" % (
                  max_bytes, state["bytes"], state["files"], _label(parts),
                  ", ".join(state["left"][:5]),
                  " (and %d more)" % more if more > 0 else ""),
              file=sys.stderr)
    return dest


def _fill(E, svc, fid, dest, recursive, max_bytes, state, rel=""):
    dest.mkdir(parents=True, exist_ok=True)
    for f in sorted(E.list_files(fid, svc=svc), key=lambda f: f["name"] or ""):
        if max_bytes is not None and state["bytes"] >= max_bytes:
            state["left"].append(rel + f["name"])
            continue
        got = Path(E.get_media(f["id"], dest / f["name"], svc=svc))
        state["bytes"] += got.stat().st_size
        state["files"] += 1
    for sub in sorted(_subfolders(svc, fid), key=lambda s: s["name"] or ""):
        (dest / sub["name"]).mkdir(parents=True, exist_ok=True)
        if recursive:
            _fill(E, svc, sub["id"], dest / sub["name"], recursive, max_bytes,
                  state, rel + sub["name"] + "/")


def _reads(p):
    """True when a path lists (a folder) or opens (a file) on this machine."""
    try:
        os.listdir(str(p))
        return True
    except NotADirectoryError:
        pass
    except OSError:
        return False
    try:
        with open(str(p), "rb"):
            return True
    except OSError:
        return False


def _drive_parts(path):
    """The parts under Shared Assets a mount path or a "Shared Assets/…"
    label names, or None when it names nothing on that drive."""
    bits = Path(str(path)).parts
    if SHARED_DRIVE not in bits:
        return None
    return list(bits[bits.index(SHARED_DRIVE) + 1:])


def drive_id(path, svc=None, find_engine=None):
    """The Drive id of a file or folder under Shared Assets — a mount path or a "Shared Assets/…"
    label — or None. With a key (route() "api") it is looked up by name through the API (the folder
    itself, else the file in its parent folder); with no key it is the drivefs extended attribute the
    mount stamps on a synced item (LD-47 (Drive sweep) step 2: the one place every component's
    "xattr -p com.google.drivefs.item-id#S" goes). Never creates anything; a path not under Shared
    Assets is None."""
    parts = _drive_parts(path)
    if not parts:
        return None
    try:
        api = route(find_mount=lambda: None) == "api"
    except NoDrive:
        api = False
    if api:
        E = (find_engine or _engine)()
        svc = svc or E.service()
        fid = E.folder_by_path(_label(parts), svc=svc)
        if fid:
            return fid
        parent = E.folder_by_path(_label(parts[:-1]), svc=svc) if len(parts) > 1 else shared_assets_id(svc)
        hit = E.find_file(svc, parts[-1], parent) if parent else None
        return (hit or {}).get("id") or None
    import subprocess
    try:
        out = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", str(path)],
                             capture_output=True, text=True, timeout=10)
        v = out.stdout.strip()
        return v if out.returncode == 0 and len(v) > 10 else None
    except Exception:
        return None


def cache_root():
    """The lasting folder for API copies: DRIVE_CACHE, else ~/.upright/cache/drive — the same base
    shared.cache_home() sits under, never a per-process temp folder (LD-79 (Drive ref resolver)).
    Not imported from shared: shared imports this module."""
    return Path(os.environ.get("DRIVE_CACHE") or (Path.home() / ".upright" / "cache" / "drive"))


def readable(path, svc=None, find_mount=None, find_engine=None,
             recursive=False, max_bytes=MAX_BYTES):
    """A path that reads, for a mount path or a "Shared Assets/…" label.

    0 KEY FIRST (LD-47 (Drive sweep) step 1.5; the team, 2026-10-20: "the goal is really just all of
      the components use the key"): when route() says "api" — a GDRIVE_SA_KEY in the environment —
      the mount is not read at all and step 2 runs, so the read is the key's, on every machine;
    1 the mount path itself (a label is put under mount()) when it lists or
      opens — no copy, no API call (route() "mount", no key);
    2 else the API copy, in the lasting cache (cache_root(), LD-79 (Drive
      ref resolver)), laid out as the label is so every name is the same: a
      folder by fetch_folder (recursive / max_bytes passed on), a file by
      name under its folder, read by id. Refreshed once per label per
      process (it overwrites); only the location lasts.
    A path that names nothing under Shared Assets comes back unchanged, so
    wrapping a local path is harmless. Not on the Drive either: NoDrive,
    naming the path. A missing key on the API leg is the engine's SystemExit."""
    find_mount, find_engine = _finders(find_mount, find_engine)
    s = str(path)
    parts = _drive_parts(path)
    if parts is None:
        return Path(s)
    try:
        key_first = route(find_mount=lambda: None) == "api"
    except NoDrive:
        key_first = False
    if key_first:
        candidate = None
    elif Path(s).is_absolute():
        candidate = Path(s)
    else:
        sa = find_mount()
        candidate = Path(sa).joinpath(*parts) if sa is not None else None
    if candidate is not None and _reads(candidate):
        return candidate
    label = _label(parts)
    if label in _READABLE:
        return _READABLE[label]
    E = find_engine()
    svc = svc or E.service()
    local = cache_root().joinpath(*parts)
    got = None
    if E.folder_by_path(label, svc=svc):
        got = fetch_folder(parts, local, recursive=recursive,
                           max_bytes=max_bytes, svc=svc,
                           find_engine=lambda: E)
    elif parts:
        parent = E.folder_by_path(_label(parts[:-1]), svc=svc)
        hit = E.find_file(svc, parts[-1], parent) if parent else None
        if hit:
            got = Path(E.get_media(hit["id"], local, svc=svc))
    if got is None:
        raise NoDrive(f"{s}: does not read here and {label} is not on the "
                      f"Drive through the API either")
    _READABLE[label] = got
    return got
