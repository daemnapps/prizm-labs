"""The brand's REAL assets on the Drive, indexed so a picture can be built from them.

the owner, 2026-09-21: "let's connect the [brand] asset folder directly and have it
indexable… so you can just build from what we really have and create truly
realistic content" and "the assets for video and image will be in google drive".

Until now every hero picture went out with an empty reference list: the picture
model got words and nothing else, so the result was competent stock rather than
this brand. The assets were already there — 16 cast, 5 environments, 11 product
shots — and nothing read them.

Brand-agnostic. The Drive is the source of record; this only reads it, and
caches the listing because the mount is slow. Nothing here is ever written to
the Drive, and nothing is deleted from it.
"""
import json
import os
import pathlib
import time

from . import drive_reach as DR
from . import paths as P

CACHE = pathlib.Path.home() / ".cache" / "daemn" / "asset-index"
PICTURE = {".png", ".jpg", ".jpeg", ".webp"}
# The folders a brand keeps its reusable picture material in, and what each is
# for. A folder that is not here is not indexed — a rushes folder is footage,
# a finals folder is output, and neither is a reference.
#
# Spelled in the v6 plan names (the Drive moved to them 2026-09-29); brandpath
# still answers the old folders on a mount that has not moved.
SHELVES = {
    "ai-elements/characters": "character",    # a person the brand casts — the
                                              # character pictures AND the AI cast
                                              # (casting/, per-person folders) sit
                                              # here since the move
    "ai-elements/environments": "environment",  # a place the brand shoots in
    "ai-elements/props": "prop",              # the product itself, and things in frame
    "products": "product",                    # per-product photography
    "content-creators": "creator",            # real people in real rooms — added
                                              # 2026-09-22, the cleanest read on the
                                              # avatars and the market's own language
}
STALE = 6 * 3600


def _drive_brand(brand):
    """`Team Drive/brands/<brand>` on the mount — None unless this run
    reaches the Drive through the mount (`drive_reach.route()`). The shelves
    and the logo search are folder listings, and gdrive-creator lists no
    folders yet, so an API run (or no Drive at all) reads none."""
    try:
        if DR.route() != "mount":
            return None
        return DR.mount() / "brands" / brand
    except DR.NoDrive:
        return None


def build(brand, force=False):
    """{shelf: [{name, kind, path, bytes, stem}]} — read once, cached."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{brand}.json"
    if f.is_file() and not force and time.time() - f.stat().st_mtime < STALE:
        return json.loads(f.read_text())

    root = _drive_brand(brand)
    out = {"brand": brand, "root": str(root) if root else None,
           "built": time.strftime("%Y-%m-%dT%H:%M"), "shelves": {}}
    if root is None:
        out["missing"] = ("the asset shelves are read off a Drive mount only, and this "
                          "run reaches the Drive through the API or not at all; "
                          "gdrive-creator lists no folders yet")
        f.write_text(json.dumps(out, indent=1))
        return out
    if not root.is_dir():
        out["missing"] = f"no asset folder on the Drive for `{brand}`"
        f.write_text(json.dumps(out, indent=1))
        return out

    BP = P.brandpath()
    for rel, kind in SHELVES.items():
        # the shelf by today's name, through brandpath — the same folder today,
        # the renamed one once the folder plan lands on the Drive too
        folder = BP.resolve_rel(brand, rel, root=root.parent)
        if not folder.is_dir():
            continue
        rows = []
        for p in sorted(folder.rglob("*")):
            if p.suffix.lower() not in PICTURE or p.name.startswith("."):
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if "/archive/" in str(p).lower():
                continue          # archive is search-only, never a reference
            rows.append({"name": p.stem, "kind": kind, "path": str(p),
                         "bytes": size,
                         "under": str(p.parent.relative_to(folder)) if p.parent != folder else ""})
        if rows:
            out["shelves"][kind] = rows
    out["count"] = sum(len(v) for v in out["shelves"].values())
    f.write_text(json.dumps(out, indent=1))
    return out


def all_rows(brand, force=False):
    idx = build(brand, force)
    return [r for rows in idx.get("shelves", {}).values() for r in rows]


# ------------------------------------------------------------------ choosing

# WHAT IS IN THE ASSET, NOT WHAT IT IS CALLED. the owner, 2026-09-21: "you need to
# identify the context" and "we've already did a footage index run on [a brand] as
# well". `tools/asset-index` reads a clip or a still and writes a record of
# what is actually in it — subject, setting, action, products visible. Matching
# a direction against THAT is the difference between finding the right asset and
# finding one whose filename happened to share a word.
#
# The records are read through asset-index's OWN reader (SI-99 (asset-index
# readers)): runs/asset-index/<brand>/*, then its work/, then the old lab folder,
# read-only and last — never a folder list kept here.
def _asset_index():
    """asset-index's shared_paths, loaded by file and cached in sys.modules
    (the footage.py pattern), so no other `shared_paths` can stand in for it."""
    import importlib.util
    import sys
    if "shared_paths" in sys.modules:
        return sys.modules["shared_paths"]
    path = pathlib.Path(__file__).resolve().parents[2] / "asset-index" / "machine" / "shared_paths.py"
    spec = importlib.util.spec_from_file_location("shared_paths", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["shared_paths"] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop("shared_paths", None)
        raise
    return mod


def _index_work(brand):
    try:
        return _asset_index().collections(brand)
    except Exception:
        return []


def _frames_of(record_dir):
    try:
        return _asset_index().record_frames(record_dir)
    except Exception:
        return []


def described(brand, force=False):
    """Every asset the index has READ, as {path, name, kind, said, frames} —
    `said` being everything the record says is in it, for matching against."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{brand}-described.v2.json"
    if f.is_file() and not force and time.time() - f.stat().st_mtime < STALE:
        return json.loads(f.read_text())

    rows = []
    for coll in _index_work(brand):
        for d in coll.iterdir():
            bd, cl = d / "breakdown.json", d / "clip.json"
            if not (bd.is_file() and cl.is_file()):
                continue
            try:
                b, c = json.loads(bd.read_text()), json.loads(cl.read_text())
            except ValueError:
                continue
            said = [str(b.get("subject") or ""), str(b.get("setting") or "")]
            said += [str(x) for x in (b.get("products_visible") or [])]
            said += [str(x) for x in (b.get("usable_for") or [])]
            said += [str(x) for x in (b.get("shot") or [])]
            for sc in (b.get("scenes") or []):
                said.append(str(sc.get("visuals") or ""))
            said.append(str(b.get("action") or ""))
            rows.append({"path": c.get("path"), "name": c.get("filename") or d.name,
                         "kind": "footage" if str(c.get("path", "")).lower().endswith(
                             (".mp4", ".mov", ".m4v")) else "still",
                         "collection": coll.name, "said": " · ".join(x for x in said if x),
                         "record": str(d), "frames": _frames_of(d)})
    f.write_text(json.dumps(rows, indent=1))
    return rows


def _words(text):
    return {w for w in "".join(c if c.isalnum() else " " for c in (text or "").lower()).split()
            if len(w) > 2}


def pick(brand, direction, product=None, want_people=None, limit=4, force=False):
    """The assets a direction is actually about — (rows, why).

    Matched on the WORDS of the direction against each asset's own name, plus
    the product when one is named. A picture model is handed few references or
    it averages them, so the best-scoring handful wins and the rest are left.
    """
    rows, why = all_rows(brand, force), []
    if not rows:
        return [], ["no assets indexed for this brand"]
    want = _words(direction)
    if product:
        want |= _words(str(product).replace("-", " "))

    # An asset the index has READ is matched on what it contains; one it has not
    # is matched on its filename, which is all there is. The first is worth far
    # more, so a described asset that matches wins over a filename that matches.
    try:
        for r in described(brand, force):
            if r.get("kind") == "still" and r.get("path"):
                rows = rows + [{"name": r["name"], "kind": "read", "path": r["path"],
                                "bytes": 0, "said": r["said"], "record": r["record"]}]
    except Exception:
        pass

    scored = []
    for r in rows:
        name = _words(r["name"].replace("-", " ").replace("_", " "))
        if r.get("said"):
            hit = (name | _words(r["said"])) & want
        else:
            hit = name & want
        if not hit:
            continue
        # a product shot matched by the product's own name is the strongest
        score = len(hit) * {"read": 5, "product": 3, "prop": 3}.get(r["kind"], 2)
        if want_people is False and r["kind"] == "character":
            continue                         # a picture with nobody in it gets no cast
        scored.append((score, r, sorted(hit)))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    seen, kept = set(), []
    for sc, r, hit in scored:                    # one copy of a file kept in two folders
        key = (r["name"].lower().replace(" copy", ""), r["bytes"])
        if key in seen:
            continue
        seen.add(key)
        kept.append((sc, r, hit))
        if len(kept) >= limit:
            break
    chosen = [r for _, r, _ in kept]
    for sc, r, hit in kept:
        why.append(f"{r['name']} ({r['kind']}) — the direction says {', '.join(hit)}")
    if not chosen:
        why.append("nothing in the brand's assets matches the words of this direction")
    return chosen, why
