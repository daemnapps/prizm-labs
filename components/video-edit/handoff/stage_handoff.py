#!/usr/bin/env python3
"""Stage hand-offs: the shared library under check.py, pull.py and pack.py.

A chain (chains/<chain>.json) names its stages, the ROLE that holds each one, how the stage is switched on, and what a
hand-off INTO the stage must carry. Who holds a role is roles.json. A hand-off is one folder:

    runs/handoffs/<role>/<brand>/<brief key>/      (the same path under Shared Assets/ on the Drive)

Public surface: chain(), roles(), stage(), stage_of_role(), holders(), roles_of(), folder(), handoffs(), number(),
files(), manifest(), drive_files(), mirror(). Reads only, except mirror(), which copies a folder to the Drive.
"""
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# the definitions (chains/<chain>.json, roles.json) are data, kept in components/stage-handoff/ (folded 2026-11-19)
DATA = HERE.parents[1] / "stage-handoff"
sys.path.insert(0, str(HERE.parents[1] / "run-kit"))
from run_kit import paths as P  # noqa: E402

HANDOFFS = Path("runs") / "handoffs"
DRIVE_ROOT = "Shared Assets"
SCHEMA = "stage-handoff/1"


def repo():
    return P.repo()


def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def chain(name="video"):
    c = _json(DATA / "chains" / ("%s.json" % name))
    if not c:
        raise SystemExit("No chain called %r (components/stage-handoff/chains/)" % name)
    return c


def roles():
    return (_json(DATA / "roles.json") or {}).get("roles") or {}


def stage(name, chain_name="video"):
    for s in chain(chain_name)["stages"]:
        if s["id"] == name:
            return s
    raise SystemExit("No stage %r in the %s chain" % (name, chain_name))


def stage_of_role(role, chain_name="video"):
    """The stage a role receives hand-offs for: the LIVE one when a role holds several."""
    hits = [s for s in chain(chain_name)["stages"] if s["role"] == role]
    live = [s for s in hits if s.get("state") == "live"]
    return (live or hits or [None])[0]


def holders(role):
    return list((roles().get(role) or {}).get("holders") or [])


def roles_of(who):
    who = str(who).lower()
    return sorted(r for r, v in roles().items() if who in [h.lower() for h in v.get("holders") or []])


def folder(role, brand, key, root=None):
    return Path(root or repo()) / HANDOFFS / role / brand / key


def number(key):
    m = re.search(r"brief-(\d+)", str(key))
    return m.group(1) if m else str(key)


def handoffs(role, brand=None, root=None):
    """Every numbered hand-off folder for a role: set-aside folders (_superseded, _closed) are never work."""
    base = Path(root or repo()) / HANDOFFS / role
    if not base.is_dir():
        return
    for b in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        if brand and b.name != brand:
            continue
        for k in sorted(p for p in b.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
            if re.search(r"brief-\d+", k.name) or (k / "HANDOFF.json").is_file():
                yield k


def find(num, role, brand=None, root=None):
    want = str(num).lstrip("#")
    hits = [k for k in handoffs(role, brand, root) if k.name == want or number(k.name).lstrip("0") == want.lstrip("0")]
    return hits[-1] if hits else None


def files(root):
    """{relative posix path: bytes} for every file in a folder, hidden and temp files left out."""
    out = {}
    root = Path(root)
    for dp, dn, fn in os.walk(str(root)):
        dn[:] = [d for d in dn if d != "__pycache__" and not d.startswith(".")]
        for f in fn:
            if f.startswith(".") or f.endswith(".tmp"):
                continue
            p = Path(dp) / f
            out[p.relative_to(root).as_posix()] = p.stat().st_size
    return out


def manifest(f):
    return _json(Path(f) / "HANDOFF.json")


def returned(f):
    d = Path(f) / "returned"
    return sorted(p.name for p in d.iterdir() if p.is_file() and not p.name.startswith(".")) if d.is_dir() else []


def label_of(f, root=None):
    """The Drive label of a hand-off folder: Shared Assets/runs/handoffs/<role>/<brand>/<key>."""
    rel = Path(f).resolve().relative_to(Path(root or repo()).resolve())
    return "%s/%s" % (DRIVE_ROOT, rel.as_posix())


# ── the Drive: through gdrive-creator with the person's own key (builder card rule 4) ──

def _link_share(dest, svc, E):
    """The hand-off folder open to anyone with the link, its returned/ taking uploads (owner, 2026-11-27: every hand-off
    Drive folder shared by link so editors scale): the one sharing rule, image-edit's handoff.link_share. Best effort: a
    share that fails is recorded, never stops the hand-off."""
    try:
        ie = str(repo() / "components" / "image-edit")
        if ie not in sys.path:
            sys.path.append(ie)
        from image_edit import handoff as IH  # noqa: E402
        return IH.link_share(dest, svc, E)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200]}


def _engine():
    gc = str(repo() / "components" / "gdrive-creator")
    if gc not in sys.path:
        sys.path.append(gc)
    from gdrive_creator import engine
    return engine


def _subfolders(E, svc, parent):
    q = "'%s' in parents and trashed = false and mimeType = '%s'" % (parent, E.FOLDER_MIME)
    out, token = [], None
    while True:
        kw = dict(q=q, fields="nextPageToken, files(id,name)", pageSize=200, supportsAllDrives=True,
                  includeItemsFromAllDrives=True)
        if token:
            kw["pageToken"] = token
        r = svc.files().list(**kw).execute()
        out += r.get("files") or []
        token = r.get("nextPageToken")
        if not token:
            return out


def drive_files(label):
    """{relative path: Drive file id} under a Drive label, or None when the folder is not there.
    Raises RuntimeError when the Drive cannot be reached (no key, no network)."""
    try:
        E = _engine()
        svc = E.service()
        top = E.folder_by_path(label, svc=svc)
    except (Exception, SystemExit) as e:  # noqa: BLE001 — what failed is the caller's to say
        raise RuntimeError(str(e)[:200])
    if not top:
        return None
    out = {}

    def walk(fid, pre):
        for f in E.list_files(fid, svc=svc):
            out[pre + f["name"]] = f["id"]
        for d in _subfolders(E, svc, fid):
            out[pre + d["name"] + "/"] = d["id"]
            walk(d["id"], pre + d["name"] + "/")
    walk(top, "")
    return out


def drive_handoffs(role, brand=None):
    """[(brand, key, folder id)] for every numbered hand-off of a role on the Drive."""
    E = _engine()
    svc = E.service()
    top = E.folder_by_path("%s/%s/%s" % (DRIVE_ROOT, HANDOFFS.as_posix(), role), svc=svc)
    out = []
    if not top:
        return out
    for b in _subfolders(E, svc, top):
        if b["name"].startswith(("_", ".")) or (brand and b["name"] != brand):
            continue
        for k in _subfolders(E, svc, b["id"]):
            if not k["name"].startswith(("_", ".")):
                out.append((b["name"], k["name"], k["id"]))
    return out


METADATA_FILES = ("HANDOFF.json", "START.md", "delivery-state.json", "REVISION.md", "DELIVERY-CHECKLIST.md", "DELIVERY-REQUIREMENTS.json")


def fetch(folder_id, dest, only=None, refresh_metadata=False):
    """Bring a Drive hand-off folder down to `dest` (missing files only; `only` = names to fetch, top level)."""
    if refresh_metadata and (not only or not set(only).issubset(METADATA_FILES)):
        raise ValueError("Only handoff metadata may be refreshed; working files are preserved")
    E = _engine()
    svc = E.service()
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    got = 0
    for f in E.list_files(folder_id, svc=svc):
        if only and f["name"] not in only:
            continue
        if Path(f["name"]).name != f["name"] or f["name"] in (".", ".."):
            raise ValueError("Unsafe Drive file name")
        if refresh_metadata or not (dest / f["name"]).exists():
            if refresh_metadata:
                import tempfile
                with tempfile.TemporaryDirectory(dir=str(dest)) as tmp:
                    incoming = Path(tmp) / f["name"]
                    E.get_media(f["id"], str(incoming), svc=svc)
                    if f["name"] == "HANDOFF.json":
                        candidate = json.loads(incoming.read_text())
                        if not isinstance(candidate, dict):raise ValueError("Invalid handoff metadata")
                    incoming.replace(dest / f["name"])
            else:
                E.get_media(f["id"], str(dest / f["name"]), svc=svc)
            got += 1
    if not only:
        for d in _subfolders(E, svc, folder_id):
            name = d["name"]
            child = dest / name
            if Path(name).name != name or name in (".", "..") or "\\" in name or child.resolve().parent != dest.resolve():
                raise ValueError("Unsafe Drive folder name")
            got += fetch(d["id"], child)
    return got


def _fill(E, svc, f, top, label):
    """Upload only the files the Drive copy lacks, so a big folder cut off part-way carries on where it stopped."""
    have = drive_files(label) or {}
    folders, sent = {"": top}, []

    def folder_for(rel):
        if rel not in folders:
            parent, _, name = rel.rpartition("/")
            folders[rel] = E.folder(name, folder_for(parent), svc)
        return folders[rel]

    for p in sorted(x for x in f.rglob("*") if x.is_file() and x.name != ".DS_Store"):
        rel = p.relative_to(f).as_posix()
        if rel in have:
            continue
        E.upload_file(str(p), p.name, folder_for(rel.rpartition("/")[0]), svc=svc)
        sent.append(rel)
    return sent


def mirror(f, root=None, missing_only=False):
    """Copy a hand-off folder to the same path under Shared Assets/. Copies and updates; never deletes."""
    E = _engine()
    svc = E.service()
    parts = label_of(f, root).split("/")
    cur = E.folder_by_path("/".join(parts[:3]), svc=svc)           # Shared Assets/runs/handoffs
    if not cur:
        raise SystemExit("Shared Assets/runs/handoffs is not reachable with this key")
    for name in parts[3:]:
        cur = E.folder(name, cur, svc)
    if missing_only:
        return cur, _fill(E, svc, Path(f), cur, label_of(f, root))
    ids = E.mirror_tree(str(f), cur, svc)
    for sub in ("returned",):                                       # an empty folder is still where work comes back
        if (Path(f) / sub).is_dir():
            E.folder(sub, cur, svc)
    _link_share(cur, svc, E)                                        # open by link, returned/ takes uploads (2026-11-27)
    return cur, ids
