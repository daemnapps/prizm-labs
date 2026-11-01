#!/usr/bin/env python3
"""A Shared Assets folder as a local folder: through the API first, the Drive folder second (the owner, 20 Oct 2026:
"there is a drive but it's connected directly via API, which our tools need to default to and use normal mounts").

    from gdrive_creator import shared as SH
    d = SH.folder("meta")                 # a local Path holding Shared Assets/meta
    ...read and write files under d as before...
    SH.save(d / "brand-a/1-check/image/x/card.json")   # a changed file goes back to the Drive

ROUTE (route()): GDRIVE_SA_KEY in the environment -> "api", even where a Drive folder exists; else the Drive for
Desktop folder (components/brandpath drive_index.mount()) -> "mount"; else NoDrive. DRIVE_ROUTE=mount pins the
folder for a caller that must see the folder itself (the Meta approve page, which moves card folders).

API: the folder is kept as a local copy under cache_home() (DRIVE_CACHE, else ~/.upright/cache/drive), refreshed at
most once every `ttl` seconds per process: a file is fetched when it is new or its modifiedTime changed, a folder
is made locally for every Drive folder, and a file the Drive no longer has is taken out of THIS LOCAL COPY ONLY
(it was moved or renamed on the Drive; the copy must not show it twice). `want(rel, size)` picks which files are
fetched at all (big videos can be left on the Drive). save() uploads a changed local file to the same place on the
Drive (same name = updated in place, its id and links kept).

MOUNT: folder() is the Drive folder path itself and save() does nothing (the file is already there).

ON THE DRIVE NOTHING IS EVER DELETED, MOVED OR RENAMED from here: the only calls are list, get_media and reach.put.
Stdlib only at import. Python 3.9.
"""
import json
import os
import tempfile
import time
from pathlib import Path

from . import reach

SYNC_FILE = ".drive-sync.json"
_SYNCED = {}                        # folder label -> time of the last refresh, this process


def cache_home():
    """Where API copies live: DRIVE_CACHE, else ~/.upright/cache/drive — one lasting cache per home, never a temp
    folder (LD-79 (Drive ref resolver)); laid out as Shared Assets is."""
    base = os.environ.get("DRIVE_CACHE") or (Path.home() / ".upright" / "cache" / "drive")
    return Path(base) / reach.SHARED_DRIVE


def route():
    """"api" | "mount", else reach.NoDrive."""
    if os.environ.get("DRIVE_ROUTE") == "mount" and reach.mount() is not None:
        return "mount"
    return reach.route()


def _parts(rel):
    return [p for p in str(rel).replace("\\", "/").split("/") if p and p not in (".", "..")]


def _tree(svc, fid, rel=""):
    """[(rel path, id, mimeType, modifiedTime, size)] for every file and folder under a Drive folder."""
    E = reach._engine()
    out, token = [], None
    while True:
        kw = dict(q=f"'{fid}' in parents and trashed = false",
                  fields="nextPageToken, files(id,name,mimeType,modifiedTime,size)", pageSize=200,
                  supportsAllDrives=True, includeItemsFromAllDrives=True)
        if token:
            kw["pageToken"] = token
        r = svc.files().list(**kw).execute()
        for f in r.get("files") or []:
            path = rel + f["name"]
            folder = f.get("mimeType") == E.FOLDER_MIME
            out.append((path, f["id"], f.get("mimeType"), f.get("modifiedTime"), int(f.get("size") or 0)))
            if folder:
                out += _tree(svc, f["id"], path + "/")
        token = r.get("nextPageToken")
        if not token:
            return out


def folder(rel, want=None, ttl=60, svc=None):
    """Shared Assets/<rel> as a local folder (see the module's note). Returns a Path; on the API it exists even when
    the Drive folder is empty. NoDrive when there is no route at all; None when the Drive folder isn't there."""
    parts = _parts(rel)
    how = route()
    if how == "mount":
        return Path(reach.mount()).joinpath(*parts)
    local = cache_home().joinpath(*parts)
    label = "/".join(parts)
    if label in _SYNCED and time.time() - _SYNCED[label] < ttl:
        return local
    E = reach._engine()
    svc = svc or E.service()
    fid = E.folder_by_path(reach._label(parts), svc=svc)
    if not fid:
        return None
    _sync(svc, fid, local, want)
    _SYNCED[label] = time.time()
    return local


def _fetch(svc, iid, dest):
    E = reach._engine()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(".fetch-" + dest.name)
    E.get_media(iid, tmp, svc=svc)
    os.replace(tmp, dest)                  # local copy only: a reader never sees half a file


def _drop(local, rel):
    """A file the Drive no longer has there (moved, renamed or trashed on the Drive): out of THIS LOCAL COPY only."""
    p = local / rel
    if p.is_file() and str(p.resolve()).startswith(str(cache_home().resolve())):
        os.remove(p)


def _sync(svc, fid, local, want):
    """The first time: the whole folder, listed and fetched. After that: only what Drive's change feed says moved
    since the last refresh (one call when nothing did), so a page that reads every minute stays quick."""
    E = reach._engine()
    local.mkdir(parents=True, exist_ok=True)
    mf = local / SYNC_FILE
    try:
        m = json.loads(mf.read_text())
    except (OSError, ValueError):
        m = {}
    if m.get("root") == fid and m.get("token") and isinstance(m.get("files"), dict):
        _changes(svc, fid, local, want, m)
    else:
        drive = reach.shared_assets_id(svc)
        token = svc.changes().getStartPageToken(driveId=drive, supportsAllDrives=True).execute().get("startPageToken")
        files, folders = {}, {fid: ""}
        for path, iid, mime, mtime, size in _tree(svc, fid):
            if mime == E.FOLDER_MIME:
                folders[iid] = path + "/"
                (local / path).mkdir(parents=True, exist_ok=True)
                continue
            if want and not want(path, size):
                continue
            files[path] = [iid, mtime]
            if (m.get("files") or {}).get(path) == [iid, mtime] and (local / path).is_file():
                continue
            _fetch(svc, iid, local / path)
        for path in set(m.get("files") or {}) - set(files):
            _drop(local, path)
        m = {"root": fid, "drive": drive, "token": token, "files": files, "folders": folders}
    mf.write_text(json.dumps(m))


def _changes(svc, fid, local, want, m):
    E = reach._engine()
    files, folders = m["files"], m["folders"]
    by_id = {v[0]: k for k, v in files.items()}
    token = m["token"]
    while token:
        r = svc.changes().list(pageToken=token, driveId=m.get("drive"), supportsAllDrives=True,
                               includeItemsFromAllDrives=True, pageSize=500,
                               fields="nextPageToken,newStartPageToken,changes(fileId,removed,"
                                      "file(name,parents,mimeType,modifiedTime,size,trashed))").execute()
        for ch in r.get("changes") or []:
            iid, f = ch.get("fileId"), ch.get("file") or {}
            gone = ch.get("removed") or f.get("trashed")
            parent = (f.get("parents") or [None])[0]
            if iid in folders and iid != fid:          # a folder of ours moved, renamed or gone: re-list it all next time
                if gone or parent not in folders or folders[parent] + f.get("name", "") + "/" != folders[iid]:
                    (local / SYNC_FILE).write_text(json.dumps({"files": files}))   # no token: a full re-list,
                    return _sync(svc, fid, local, want)                            # files already here kept
                continue
            old = by_id.get(iid)
            if gone or parent not in folders:          # gone, or moved out of this folder
                if old:
                    _drop(local, old)
                    files.pop(old, None)
                continue
            rel = folders[parent] + f.get("name", "")
            if f.get("mimeType") == E.FOLDER_MIME:
                folders[iid] = rel + "/"
                (local / rel).mkdir(parents=True, exist_ok=True)
                continue
            if old and old != rel:                     # renamed or moved inside this folder
                _drop(local, old)
                files.pop(old, None)
            if want and not want(rel, int(f.get("size") or 0)):
                continue
            if files.get(rel) == [iid, f.get("modifiedTime")] and (local / rel).is_file():
                continue
            _fetch(svc, iid, local / rel)
            files[rel] = [iid, f.get("modifiedTime")]
            by_id[iid] = rel
        token = r.get("nextPageToken")
        if not token:
            m["token"] = r.get("newStartPageToken") or m["token"]


def ensure(rel, want=None, svc=None):
    """Shared Assets/<rel> present locally, whatever it is: a folder is kept in step (folder()); a single file is
    fetched by name when the local copy lacks it. Returns the local Path (on the mount: the mount path), or None
    when the Drive has nothing there. For big pools where only the piece a tool asks for should come down."""
    parts = _parts(rel)
    if route() == "mount":
        return Path(reach.mount()).joinpath(*parts)
    E = reach._engine()
    svc = svc or E.service()
    if E.folder_by_path(reach._label(parts), svc=svc):
        return folder(rel, want=want, svc=svc)
    local = cache_home().joinpath(*parts)
    if local.is_file():
        return local
    parent = E.folder_by_path(reach._label(parts[:-1]), svc=svc) if parts else None
    hit = E.find_file(svc, parts[-1], parent) if parent else None
    if not hit:
        return None
    _fetch(svc, hit["id"], local)
    return local


def is_copy(path):
    """True when a path sits in the API copy (so a write to it must be saved back)."""
    try:
        Path(path).resolve().relative_to(cache_home().resolve())
        return True
    except ValueError:
        return False


def save(path):
    """A file changed in the API copy goes back to the same place on the Drive. On the Drive folder itself, nothing
    to do. Returns (how, note): note is None when it landed."""
    p = Path(path)
    if not is_copy(p):
        return "mount", None
    rel = p.resolve().relative_to(cache_home().resolve())
    how, placed, note = reach.put([p], list(rel.parts[:-1]))
    return how, note


def save_tree(path):
    """Every file under a folder in the API copy, back to the Drive (a new card, a returned master). (how, note)."""
    p = Path(path)
    if not is_copy(p):
        return "mount", None
    note = None
    for sub in sorted(x for x in p.rglob("*") if x.is_file() and not x.name.startswith(".")):
        how, n = save(sub)
        note = note or n
    return "api", note
