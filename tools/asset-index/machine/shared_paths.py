#!/usr/bin/env python3
"""
shared_paths.py — where each indexed clip lives NOW, on the company Shared Assets drive.

    python3 machine/shared_paths.py --brand <brand>            # walk once, map, report
    python3 machine/shared_paths.py --brand <brand> --rewalk   # walk the drive again

The index records (work/<collection>/<clip_id>/clip.json) were made while the
footage sat on a personal drive. the owner moved it to the Shared Assets drive
(5 Oct 2026). A record's old path is useless now, so every clip is matched to
its copy on Shared Assets by FILENAME, and confirmed by SIZE when the name is
shared by more than one file (then by the old folder's words, as a last tie-break).

The drive is slow, so it is walked ONCE and cached (gitignored, under work/_maps/):

    work/_maps/walk-<brand>.json         every video/still under brands/<brand>/ with its size
    work/_maps/<collection>.json         clip_id -> {"path", "how"} | {"path": null, "why"}

Never returns a personal-drive path: only a path under the Shared Assets root
that exists in the walk. Brand-agnostic — the brand is an argument (rule 7).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
WORK = COMPONENT / "work"
MAPS = WORK / "_maps"
REPO = COMPONENT.parent.parent
RUNS = REPO / "runs" / "asset-index"
# The old lab folder the records were first written to — read-only, last (root CLAUDE.md rule 9).
LAB_WORK = REPO / "lab" / "damon" / "asset-index" / "work"

sys.path.append(str(COMPONENT.parent / "brandpath"))
import drive_index as DI  # noqa: E402

# The company drive: SHARED_ASSETS_ROOT, else this machine's mount through the one shared helper (O9 (Drive by fileId)).
SHARED_ROOT = (Path(os.environ["SHARED_ASSETS_ROOT"]) if os.environ.get("SHARED_ASSETS_ROOT")
               else DI.mount())
_WARNED = False

MEDIA_EXT = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv",
             ".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"}
SKIP_DIRS = {".git", "__pycache__"}


def shared_root(root: Path | None = None) -> Path:
    base = root or SHARED_ROOT
    if base is None:
        raise SystemExit("Shared Assets is not reachable on this machine: no Google Drive with "
                         "Shared drives/Shared Assets is mounted (components/brandpath/drive_index.py "
                         "mount()) and SHARED_ASSETS_ROOT is not set")
    return Path(base)


def brand_root(brand: str, root: Path | None = None) -> Path:
    return shared_root(root) / "brands" / brand


def on_shared(path: str | None, root: Path | None = None) -> bool:
    global _WARNED
    if not path:
        return False
    base = root or SHARED_ROOT
    if base is None:
        if not _WARNED:
            _WARNED = True
            print("shared_paths: Shared Assets is not reachable — SHARED_ASSETS_ROOT is not set and no "
                  "Drive mount was found (components/brandpath/drive_index.py mount()); "
                  "no path counts as on Shared Assets", file=sys.stderr)
        return False
    try:
        Path(path).resolve().relative_to(Path(base).resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- the walk

def _list_retry(svc, fid, tok, tries=6):
    """One folder page through the key, retried with backoff on Drive's transient 5xx / rate-limit
    answers (a 500 'Unknown Error' ended a full walk on 2026-10-20); any other error is raised."""
    import time as _t
    for i in range(tries):
        try:
            return svc.files().list(q="'%s' in parents and trashed=false" % fid, pageToken=tok, pageSize=1000,
                                    fields="nextPageToken, files(id,name,size,md5Checksum,mimeType,createdTime,"
                                           "modifiedTime,imageMediaMetadata(width,height),"
                                           "videoMediaMetadata(width,height,durationMillis))",
                                    supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        except Exception as e:  # noqa: BLE001
            code = getattr(getattr(e, "resp", None), "status", None)
            if i == tries - 1 or code not in (403, 429, 500, 502, 503, 504):
                raise
            _t.sleep(2 ** i)


def key_walk(brand: str, max_items: int = 400000) -> list[dict]:
    """Every media file under Shared Assets/brands/<brand>/ THROUGH THE KEY (LD-56 (footage index in git),
    the team 2026-10-20: "search should also use key"): one listing per folder, names, sizes and md5 only —
    nothing is downloaded. -> [{path: "Shared Assets/…" label, name, bytes, drive_id, md5, mime, created, modified,
    width, height, duration_s}] — the last five from the Drive's own media metadata (LD-59 (image records)), None
    when the Drive has not read the file's media."""
    gdc = str(COMPONENT.parent / "gdrive-creator")
    if gdc not in sys.path:
        sys.path.append(gdc)
    from gdrive_creator import engine as E
    svc = E.service()
    top = E.folder_by_path("Shared Assets/brands/" + brand, svc=svc)
    if not top:
        raise SystemExit("Shared Assets/brands/%s is not reachable through the key" % brand)
    out, todo = [], [(top, "Shared Assets/brands/" + brand)]
    while todo and len(out) < max_items:
        fid, label = todo.pop(0)
        tok = None
        while True:
            r = _list_retry(svc, fid, tok)
            for f in r.get("files", []):
                if f.get("mimeType") == "application/vnd.google-apps.folder":
                    if f["name"] not in SKIP_DIRS and not f["name"].startswith("."):
                        todo.append((f["id"], label + "/" + f["name"]))
                elif Path(f["name"]).suffix.lower() in MEDIA_EXT and not f["name"].startswith("."):
                    mm = f.get("videoMediaMetadata") or f.get("imageMediaMetadata") or {}
                    ms = (f.get("videoMediaMetadata") or {}).get("durationMillis")
                    out.append({"path": label + "/" + f["name"], "name": f["name"],
                                "bytes": int(f["size"]) if f.get("size") else None,
                                "drive_id": f["id"], "md5": f.get("md5Checksum"), "mime": f.get("mimeType"),
                                "created": f.get("createdTime"), "modified": f.get("modifiedTime"),
                                "width": mm.get("width"), "height": mm.get("height"),
                                "duration_s": round(int(ms) / 1000.0, 2) if ms else None})
            tok = r.get("nextPageToken")
            if not tok:
                break
    if todo:
        print("shared_paths: key walk stopped at %d files (max_items) — %d folders not listed"
              % (len(out), len(todo)), file=sys.stderr)
    return out


def walk(brand: str, root: Path | None = None) -> list[dict]:
    """Every media file under brands/<brand>/ on Shared Assets: path + size. With no root it walks THROUGH
    THE KEY (key_walk: labels, Drive ids, md5); a root given (a test's folder, or SHARED_ASSETS_ROOT) is
    walked on disk."""
    if root is None and not os.environ.get("SHARED_ASSETS_ROOT"):
        return key_walk(brand)
    base = brand_root(brand, root)
    if not base.is_dir():
        raise SystemExit(f"Shared Assets is not reachable at {base}")
    out = []
    for d, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
        for f in files:
            if Path(f).suffix.lower() in MEDIA_EXT and not f.startswith("."):
                p = Path(d) / f
                try:
                    size = p.stat().st_size
                except OSError:
                    size = None
                out.append({"path": str(p), "name": f, "bytes": size})
    return out


def cached_walk(brand: str, rewalk: bool = False, root: Path | None = None,
                maps: Path | None = None) -> list[dict]:
    maps = Path(maps or MAPS)
    f = maps / f"walk-{brand}.json"
    if f.is_file() and not rewalk:
        return json.loads(f.read_text())["files"]
    files = walk(brand, root)
    maps.mkdir(parents=True, exist_ok=True)
    where = str(brand_root(brand, root)) if (root or os.environ.get("SHARED_ASSETS_ROOT")) else \
        "Shared Assets/brands/" + brand + " (through the key)"
    f.write_text(json.dumps({"brand": brand, "root": where, "files": files}, indent=0))
    return files


# ---------------------------------------------------------------- matching

def _norm(name: str) -> str:
    """A filename as a key: case-folded, Drive's ' (1)' / ' copy' suffixes dropped."""
    stem, ext = os.path.splitext(name)
    stem = re.sub(r"(\s*\(\d+\))+$", "", stem)
    stem = re.sub(r"\s+copy(\s*\d+)?$", "", stem, flags=re.I)
    return (stem.strip() + ext).lower()


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2}


def _size_ok(rec_mb, nbytes, tol=0.06) -> bool:
    if rec_mb is None or nbytes is None:
        return False
    return abs(nbytes / 1048576 - float(rec_mb)) <= max(tol, 0.01 * float(rec_mb))


def resolve_one(clip: dict, by_name: dict, by_norm: dict, root: Path | None = None,
                by_tail: dict | None = None) -> dict:
    """-> {"path": <shared path>, "how": "..."} or {"path": None, "why": "..."}.

    Every file that could be this clip is pooled — the exact name, the name
    without Drive's copy suffix, and the name after an old-folder prefix the
    move added — then the SIZE decides. A generic name ("4.mov") is shared by
    many creators' files, so a lone name match whose size is off is refused
    rather than trusted."""
    old = clip.get("path") or ""
    if on_shared(old, root) and Path(old).exists():
        return {"path": old, "how": "already on Shared Assets"}
    name = clip.get("filename") or Path(old).name
    meta = clip.get("meta") or {}
    mb = meta.get("size_mb")
    if mb is None and meta.get("bytes"):
        mb = meta["bytes"] / 1048576
    fw = _words(clip.get("folder") or "")
    pool: list[tuple[dict, str]] = []
    seen: set[str] = set()

    def add(cs, how):
        for c in cs or []:
            if c["path"] not in seen:
                seen.add(c["path"])
                pool.append((c, how))

    add(by_name.get(name), "filename")
    add(by_norm.get(_norm(name)), "filename (Drive copy suffix ignored)")
    if by_tail:
        # renamed with its old folder as a prefix: the prefix must be the old folder's words
        add([c for c in by_tail.get(_norm(name)) or []
             if (_words(c["name"]) - _words(name)) <= (fw | _words(str(Path(c["path"]).parent)))],
            "filename after its old folder's prefix")
    if not pool:
        return {"path": None, "why": "no file of this name on Shared Assets"}
    sized = [(c, h) for c, h in pool if _size_ok(mb, c.get("bytes"))]
    if mb is None or not any(c.get("bytes") is not None for c, _ in pool):
        # nothing to weigh by: only an unambiguous name is trusted
        if len(pool) == 1:
            return {"path": pool[0][0]["path"], "how": pool[0][1]}
        return {"path": None, "why": f"{len(pool)} files of this name and no size to tell them apart"}
    if not sized:
        if len(pool) == 1:
            c = pool[0][0]
            return {"path": None, "why": f"one file of this name, but its size differs "
                                         f"({(c.get('bytes') or 0) / 1048576:.1f} MB vs {mb} MB)"}
        return {"path": None, "why": f"{len(pool)} files of this name, none the indexed size ({mb} MB)"}
    if len(sized) == 1:
        c, how = sized[0]
        return {"path": c["path"], "how": how + (" + size" if len(pool) > 1 else "")}
    # same-size copies are the same footage: the old folder's words, then the shortest path
    sized.sort(key=lambda ch: (-len(fw & _words(ch[0]["path"])), len(ch[0]["path"]), ch[0]["path"]))
    c, how = sized[0]
    return {"path": c["path"], "how": how + f" + size ({len(sized)} identical copies)"}


def index_files(files: list[dict]) -> tuple[dict, dict, dict]:
    """Three lookups over the walk: exact name, normalised name, and the name
    after a folder-slug prefix — the move renamed `Peanut Butter/IMG_3470.MOV`
    to `raw/peanut-butter_IMG_3470.MOV`, so every tail after an underscore is a key."""
    by_name: dict[str, list] = {}
    by_norm: dict[str, list] = {}
    by_tail: dict[str, list] = {}
    for f in files:
        by_name.setdefault(f["name"], []).append(f)
        by_norm.setdefault(_norm(f["name"]), []).append(f)
        parts = f["name"].split("_")
        for i in range(1, len(parts)):
            by_tail.setdefault(_norm("_".join(parts[i:])), []).append(f)
    return by_name, by_norm, by_tail


def collections_of(brand: str, work: Path | None = None) -> list[Path]:
    work = Path(work or WORK)
    return sorted(p for p in work.glob(f"{brand}-*") if p.is_dir())


def build_map(collection: Path, files: list[dict], root: Path | None = None,
              maps: Path | None = None) -> dict:
    by_name, by_norm, by_tail = index_files(files)
    out = {}
    for cj in sorted(collection.glob("*/clip.json")):
        try:
            clip = json.loads(cj.read_text())
        except Exception:
            continue
        cid = clip.get("clip_id") or cj.parent.name
        r = resolve_one(clip, by_name, by_norm, root, by_tail)
        r["folder"] = clip.get("folder") or ""
        r["filename"] = clip.get("filename") or ""
        out[cid] = r
    maps = Path(maps or MAPS)
    maps.mkdir(parents=True, exist_ok=True)
    (maps / f"{collection.name}.json").write_text(json.dumps(out, indent=0))
    return out


def load_map(collection: Path, maps: Path | None = None) -> dict:
    """{clip id: {label, …}}. A collection in runs/asset-index/ (LD-56 (footage index in git)) carries its
    own map.json keyed by Drive file id — each entry a "Shared Assets/…" label, md5 and size; an old
    work/ collection's map comes from work/_maps/<name>.json, keyed by the old sha1 id with a mount path."""
    own = Path(collection) / "map.json"
    if own.is_file():
        return json.loads(own.read_text())
    f = Path(maps or MAPS) / f"{Path(collection).name}.json"
    return json.loads(f.read_text()) if f.is_file() else {}


def label_of(path: str | None) -> str | None:
    """A mount path or a label → its "Shared Assets/…" label, else None (never a personal-drive path)."""
    s = str(path or "")
    return "Shared Assets/" + s.split("Shared Assets/", 1)[1] if "Shared Assets/" in s else None


def shared_path(collection: Path, clip_id: str, maps: Path | None = None) -> str | None:
    """The clip's "Shared Assets/…" LABEL, or None — KEYS ONLY (the team, 2026-10-20: "everything component wise
    should work with keys"): a stored reference is a label, read through the key with local(), never a test
    against this machine's mount. Never a personal-drive path."""
    e = load_map(collection, maps).get(clip_id) or {}
    return e.get("label") or label_of(e.get("path"))


def local(ref: str | None) -> str | None:
    """A footage reference as a file this process can open: a "Shared Assets/…" label (or an old mount path)
    through gdrive-creator reach.readable() — the key's API copy — else the path itself when it is a local
    file. None when it is neither."""
    if not ref:
        return None
    lab = label_of(ref)
    if lab:
        gdc = str(COMPONENT.parent / "gdrive-creator")
        if gdc not in sys.path:
            sys.path.append(gdc)
        from gdrive_creator import reach
        try:
            return str(reach.readable(lab))
        except Exception as e:  # noqa: BLE001
            print("shared_paths: %s not read through the key (%s: %s)" % (lab, type(e).__name__, e), file=sys.stderr)
            return None
    return str(ref) if Path(ref).is_file() else None


def runs_root() -> Path:
    """runs/asset-index/ — where extract.py writes <brand>/<label>/<clip-id>/clip.json."""
    return RUNS


def _dirs(root: Path) -> list[Path]:
    try:
        return sorted(p for p in Path(root).iterdir() if p.is_dir())
    except OSError:
        return []


def collections(brand: str, work: Path | None = None, runs: Path | None = None,
                lab: Path | None = None) -> list[Path]:
    """The ONE reader of a brand's clip-record collections, newest home first:
    runs/asset-index/<brand>/*, then work/<brand>-*, then the old lab folder
    (any name containing the brand — the way image-production matched it).
    A name already seen in a newer home is skipped. Missing folders give nothing."""
    found = [p for p in _dirs(Path(runs or runs_root()) / brand) if not p.name.startswith((".", "_"))]
    found += collections_of(brand, work)
    found += [p for p in _dirs(Path(lab or LAB_WORK)) if brand.lower() in p.name.lower()]
    out, seen = [], set()
    for p in found:
        if p.name not in seen:
            seen.add(p.name)
            out.append(p)
    return out


def _media_request(file_id):
    """gdrive-creator's (url, header) for a ranged read by id — the seam tests replace."""
    gdc = str(COMPONENT.parent / "gdrive-creator")
    if gdc not in sys.path:
        sys.path.append(gdc)
    from gdrive_creator import engine
    return engine.media_request(file_id)


def _run(cmd):
    """The ffmpeg seam (tests replace it)."""
    import subprocess
    return subprocess.run(cmd, capture_output=True)


def _rebuild_frames(d: Path) -> list[str]:
    """LD-58 (record frames on demand): a record whose frame pictures are not on this machine (they are
    git-ignored; only the owner's Mac had them) gets them back from its clip, fetched by its Drive label through
    the key (local() → reach.readable) — ffmpeg at each frames[].at_s, 480 px tall like index_run.py — written
    into the record folder once, so the next call fetches nothing. A still record: the picture itself,
    scaled once. No model. [] when the record names no label or the clip cannot be read."""
    try:
        clip = json.loads((d / "clip.json").read_text())
    except (OSError, ValueError):
        return []
    frames = [f for f in (clip.get("frames") or []) if isinstance(f, dict) and f.get("file")]
    label = clip.get("label") or label_of(clip.get("path"))
    if not frames or not label:
        return []
    still = not ((clip.get("meta") or {}).get("duration_s") if isinstance(clip.get("meta"), dict) else None)
    # THE FULL-DOWNLOAD GUARD (2026-10-21, thread post 139): a clip whose Drive id the record knows is never
    # read whole to make one frame — ffmpeg seeks on the Drive URL with the key's header (index_run's way),
    # so only the bytes around each frame are read. A still is its own picture, read whole once.
    fid = clip.get("drive_id") or (d.name if (d.parent / "map.json").is_file() else None)
    hdr = None
    if fid and not still:
        try:
            src, hdr = _media_request(fid)
        except (Exception, SystemExit) as e:  # noqa: BLE001
            print("shared_paths: no ranged read for %s (%s) — no frame" % (fid, type(e).__name__), file=sys.stderr)
            return []
    else:
        src = local(label)
    if not src:
        return []
    out = []
    for f in frames:
        dest = d / str(f["file"])
        if not dest.is_file():
            head = ["-headers", hdr] if hdr else []
            cmd = (["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "scale=-2:480", "-frames:v", "1", str(dest)] if still else
                   ["ffmpeg", "-v", "error", "-y", *head, "-ss", str(float(f.get("at_s") or 0)), "-i", src, "-frames:v", "1",
                    "-vf", "scale=-2:480", str(dest)])
            _run(cmd)
            if not dest.is_file() and hdr:
                _run(cmd)                 # one retry: a first ranged read can miss (seen 2026-10-21, 1 of 3)
        if dest.is_file():
            out.append(str(dest))
        if still:
            break
    return out


def record_frames(record_dir, fetch: bool = True) -> list[str]:
    """A record's frame files as absolute paths: clip.json's frames[].file that
    exist, in order; else f_*.jpg; else the older frame_*.jpg; else, when fetch, the frames rebuilt from
    the clip through the key (_rebuild_frames, LD-58 (record frames on demand)). [] for no folder."""
    d = Path(record_dir).absolute() if record_dir else None
    if not d or not d.is_dir():
        return []
    try:
        frames = json.loads((d / "clip.json").read_text()).get("frames") or []
        named = [d / str(f["file"]) for f in frames if isinstance(f, dict) and f.get("file")]
        named = [str(p) for p in named if p.is_file()]
    except (OSError, ValueError, AttributeError, TypeError):
        named = []
    have = (named or [str(p) for p in sorted(d.glob("f_*.jpg"))]
            or [str(p) for p in sorted(d.glob("frame_*.jpg"))])
    return have or (_rebuild_frames(d) if fetch else [])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--collection", help="one collection folder name under work/ (default: every <brand>-*)")
    ap.add_argument("--rewalk", action="store_true", help="walk the drive again instead of the cache")
    a = ap.parse_args(argv)
    files = cached_walk(a.brand, rewalk=a.rewalk)
    cols = [WORK / a.collection] if a.collection else collections_of(a.brand)
    print(f"Shared Assets: {len(files)} media files under brands/{a.brand}/")
    for col in cols:
        m = build_map(col, files)
        ok = [v for v in m.values() if v.get("path")]
        miss = [v for v in m.values() if not v.get("path")]
        print(f"\n{col.name}: {len(ok)} of {len(m)} clips found on Shared Assets, {len(miss)} not")
        folders: dict[str, int] = {}
        for v in miss:
            folders[v["folder"]] = folders.get(v["folder"], 0) + 1
        for fo, n in sorted(folders.items(), key=lambda x: -x[1]):
            print(f"  not found · {n:4} · {fo or '(no folder)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
