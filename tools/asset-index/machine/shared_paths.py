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
# An older home for records, read last; none in this checkout unless you set one.
LAB_WORK = Path(os.environ["ASSET_INDEX_OLD_WORK"]) if os.environ.get("ASSET_INDEX_OLD_WORK") else WORK / "_none"


def _mount():
    """The shared drive's root on this machine, where a workspace has a helper for it."""
    try:
        sys.path.append(str(REPO / "components" / "brandpath"))
        import drive_index as DI  # noqa: E402
        return DI.mount()
    except Exception:
        return None


# The company drive everyone can open: SHARED_ASSETS_ROOT (a folder holding brands/<brand>/…),
# else this machine's mount where a helper finds one.
SHARED_ROOT = (Path(os.environ["SHARED_ASSETS_ROOT"]) if os.environ.get("SHARED_ASSETS_ROOT")
               else _mount())
_WARNED = False

MEDIA_EXT = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv",
             ".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"}
SKIP_DIRS = {".git", "__pycache__"}


def shared_root(root: Path | None = None) -> Path:
    base = root or SHARED_ROOT
    if base is None:
        raise SystemExit("Shared Assets is not reachable on this machine: SHARED_ASSETS_ROOT is not set "
                         "and no shared-drive mount was found")
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
                  "shared-drive mount was found; no path counts as on Shared Assets", file=sys.stderr)
        return False
    try:
        Path(path).resolve().relative_to(Path(base).resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- the walk

def walk(brand: str, root: Path | None = None) -> list[dict]:
    """Every media file under brands/<brand>/ on Shared Assets: path + size."""
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
    f.write_text(json.dumps({"brand": brand, "root": str(brand_root(brand, root)),
                             "files": files}, indent=0))
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
    f = Path(maps or MAPS) / f"{Path(collection).name}.json"
    return json.loads(f.read_text()) if f.is_file() else {}


def shared_path(collection: Path, clip_id: str, maps: Path | None = None) -> str | None:
    """The clip's Shared Assets path, or None. Never a personal-drive path."""
    p = (load_map(collection, maps).get(clip_id) or {}).get("path")
    return p if p and on_shared(p) else None


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


def record_frames(record_dir) -> list[str]:
    """A record's frame files as absolute paths: clip.json's frames[].file that
    exist, in order; else f_*.jpg; else the older frame_*.jpg. [] for no folder."""
    d = Path(record_dir).absolute() if record_dir else None
    if not d or not d.is_dir():
        return []
    try:
        frames = json.loads((d / "clip.json").read_text()).get("frames") or []
        named = [d / str(f["file"]) for f in frames if isinstance(f, dict) and f.get("file")]
        named = [str(p) for p in named if p.is_file()]
    except (OSError, ValueError, AttributeError, TypeError):
        named = []
    return (named or [str(p) for p in sorted(d.glob("f_*.jpg"))]
            or [str(p) for p in sorted(d.glob("frame_*.jpg"))])


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
