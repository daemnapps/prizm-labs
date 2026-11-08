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
import tempfile
import time

from . import drive_reach as DR
from . import paths as P

CACHE = pathlib.Path(tempfile.gettempdir()) / "daemn" / "asset-index"
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
STALE_API = 24 * 3600


def _drive_brand(brand):
    """`Shared Assets/brands/<brand>` on the mount — None unless this run
    reaches the Drive through the mount (`drive_reach.route()`). The shelves
    and the logo search are folder listings, and gdrive-creator lists no
    folders yet, so an API run (or no Drive at all) reads none."""
    try:
        if DR.route() != "mount":
            return None
        return DR.mount() / "brands" / brand
    except DR.NoDrive as e:
        DR.loud(f"brand shelves for {brand}", e)
        return None


def build(brand, force=False):
    """{shelf: [{name, kind, path, bytes, stem}]} — read once, cached."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{brand}.json"
    if f.is_file() and not force:
        kept = json.loads(f.read_text())
        # a listing through the key walks every shelf folder (minutes); the shelves change rarely, so it keeps a day
        if time.time() - f.stat().st_mtime < (STALE_API if kept.get("route") == "api" else STALE):
            return kept

    root = _drive_brand(brand)
    out = {"brand": brand, "root": str(root) if root else None,
           "built": time.strftime("%Y-%m-%dT%H:%M"), "shelves": {}}
    if root is None and _api_route():
        # machine inputs go through the Drive API (the 2026-09-17 ruling): the shelves are listed by the key and a
        # picked file is fetched by its id (local_file), so any machine with the key reads the same assets
        try:
            out["shelves"] = _shelves_by_api(brand)
            out["route"] = "api"
            out["count"] = sum(len(v) for v in out["shelves"].values())
            f.write_text(json.dumps(out, indent=1))
            return out
        except Exception as e:                                     # a slow or absent Drive never stops a run
            DR.loud(f"brand shelves for {brand} through the API", e)
    if root is None:
        # no Drive on this machine: the brand's own folder in this repo carries the same shelves (a lab brand
        # keeps its real material there), read the same way
        try:
            local = pathlib.Path(P.brand(brand)["root"])
        except Exception:
            local = None
        if local is not None and local.is_dir() and any((local / rel).is_dir() for rel in SHELVES):
            root = local
            out["root"], out["route"] = str(local), "brand-folder"
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


def _api_route():
    try:
        return DR.route() == "api"
    except Exception:
        return False


FOLDER = "application/vnd.google-apps.folder"


def _walk_api(svc, folder_id, label, depth=0, limit=8):
    """Every picture under a Drive folder, by the key: [{id, name, label}] (archive folders skipped)."""
    out, token = [], None
    while True:
        kw = dict(q=f"'{folder_id}' in parents and trashed = false", pageSize=200,
                  fields="nextPageToken, files(id,name,mimeType,size)",
                  supportsAllDrives=True, includeItemsFromAllDrives=True)
        if token:
            kw["pageToken"] = token
        r = svc.files().list(**kw).execute()
        for x in r.get("files") or []:
            name = x.get("name") or ""
            if x.get("mimeType") == FOLDER:
                if depth < limit and "archive" not in name.lower() and not name.startswith((".", "_old")):
                    out += _walk_api(svc, x["id"], f"{label}/{name}", depth + 1, limit)
            elif pathlib.Path(name).suffix.lower() in PICTURE and not name.startswith("."):
                out.append({"id": x["id"], "name": name, "label": f"{label}/{name}", "bytes": int(x.get("size") or 0)})
        token = r.get("nextPageToken")
        if not token:
            return out


def _shelves_by_api(brand):
    E = DR._engine()
    svc = E.service()
    shelves = {}
    for rel, kind in SHELVES.items():
        label = f"Shared Assets/brands/{brand}/{rel}"
        fid = E.folder_by_path(label, svc)
        if not fid:
            continue
        rows = [{"name": pathlib.Path(x["name"]).stem, "kind": kind, "path": "drive:" + x["id"], "label": x["label"],
                 "bytes": x["bytes"], "under": x["label"][len(label) + 1:].rsplit("/", 1)[0] if "/" in x["label"][len(label) + 1:] else ""}
                for x in _walk_api(svc, fid, label)]
        if rows:
            shelves[kind] = rows
    return shelves


def fetch(drive_id, name=""):
    """A Drive file by its id, through the key, into this machine's cache — the path, or None."""
    if not drive_id:
        return None
    dest = CACHE / "files" / (drive_id + (pathlib.Path(name).suffix.lower() or ".jpg"))
    if dest.is_file() and dest.stat().st_size:
        return dest
    try:
        DR._engine().get_media(drive_id, dest)
        return dest if dest.is_file() and dest.stat().st_size else None
    except Exception as e:
        DR.loud(f"asset {name or drive_id}", e)
        return None


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


def _frames_of(record_dir, fetch=False):
    """A record's frame pictures that are ON THIS MACHINE. Listing never fetches (the full-download guard,
    2026-10-21: rebuilding every record's frames while listing pulled whole clips); frames_now() fetches one."""
    try:
        return _asset_index().record_frames(record_dir, fetch=fetch)
    except Exception:
        return []


def frames_now(row):
    """One row's frames, fetched now when they are not here: asset-index rebuilds them through the key (a
    ranged seek for a clip with a Drive id, the picture itself for a still). For the few rows a caller keeps."""
    return (row or {}).get("frames") or (_frames_of(row.get("record"), fetch=True) if (row or {}).get("record") else [])


def described(brand, force=False):
    """Every asset the index has a record of, as {path, name, kind, said, frames, described} — `said` being
    everything the record says is in it, for matching against. A mapping-only record (described false,
    LD-59 (image records)) says its folder and file-name words plus any pointer text. `frames` lists only
    pictures already here; frames_now(row) fetches them for a row a caller keeps."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{brand}-described.v2.json"   # name kept (test_assets_index_reader); a cache ages out in STALE
    if f.is_file() and not force and time.time() - f.stat().st_mtime < STALE:
        return json.loads(f.read_text())

    rows = []
    for coll in _index_work(brand):
        for d in coll.iterdir():
            bd, cl = d / "breakdown.json", d / "clip.json"
            if not cl.is_file():
                continue
            if not bd.is_file():
                try:
                    c = json.loads(cl.read_text())
                except ValueError:
                    continue
                if c.get("described") is not False:
                    continue
                said = list(c.get("words") or []) + ([str(c["text"])] if c.get("text") else [])
                rows.append({"path": c.get("label") or c.get("path"), "drive_id": c.get("drive_id"),
                             "name": c.get("filename") or d.name,
                             "kind": "footage" if c.get("kind") == "video" else "still",
                             "collection": coll.name, "said": " · ".join(x for x in said if x),
                             "record": str(d), "frames": _frames_of(d), "described": False})
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
            rows.append({"path": c.get("path"), "label": c.get("label") or "", "drive_id": c.get("drive_id"),
                         "name": c.get("filename") or d.name,
                         "kind": "footage" if str(c.get("path") or c.get("label") or "").lower().endswith(
                             (".mp4", ".mov", ".m4v")) else "still",
                         "collection": coll.name, "said": " · ".join(x for x in said if x),
                         "record": str(d), "frames": _frames_of(d), "described": True})
    f.write_text(json.dumps(rows, indent=1))
    return rows


# words that say nothing about what is in a picture never match an asset (2026-11-08: "the" matched a skin set)
FILLER = {"the", "and", "for", "with", "his", "her", "its", "are", "was", "into", "from", "that", "this", "out",
          "about", "over", "under", "one", "two", "who", "what", "when", "where", "while", "has", "have", "him",
          "she", "they", "them", "their", "our", "your", "you", "not", "but", "all", "any", "very", "just", "like",
          "same", "real", "photo", "picture", "shot", "image", "frame", "ad", "new", "set"}


def _words(text):
    return {w for w in "".join(c if c.isalnum() else " " for c in (text or "").lower()).split()
            if len(w) > 2 and w not in FILLER}


def pick(brand, direction, product=None, want_people=None, limit=4, force=False):
    """The assets a direction is actually about — (rows, why).

    Matched on the WORDS of the direction against each asset's own name, plus
    the product when one is named. A picture model is handed few references or
    it averages them, so the best-scoring handful wins and the rest are left.
    """
    rows, why = all_rows(brand, force), []
    if not rows:
        got, wide = nearest(brand, [], _words(direction) | (_words(str(product).replace("-", " ")) if product else set()),
                            want_people, limit, force)
        return got, ["no asset shelves indexed for this brand"] + wide
    want = _words(direction)
    if product:
        want |= _words(str(product).replace("-", " "))

    # An asset the index has READ is matched on what it contains; one it has not
    # is matched on its filename, which is all there is. The first is worth far
    # more, so a described asset that matches wins over a filename that matches.
    try:
        for r in described(brand, force):
            if r.get("kind") == "still" and r.get("path"):
                rows = rows + [{"name": r["name"], "kind": "read", "path": r["path"], "label": r.get("label") or "",
                                "drive_id": r.get("drive_id"), "bytes": 0, "said": r["said"], "record": r["record"],
                                "frames": r.get("frames") or []}]
            elif r.get("kind") == "footage" and r.get("described") and r.get("frames"):
                # footage the index has READ competes on what is in it, through its own frame (2026-11-08)
                rows = rows + [{"name": r["name"], "kind": "read", "path": r["frames"][0], "label": r.get("label") or "",
                                "bytes": 0, "said": r["said"], "record": r["record"], "frames": r["frames"][:1]}]
    except Exception:
        pass

    rows = [r for r in rows if real_source(r.get("path") or r.get("name"))
            and real_source(r.get("label") or "")]                              # real material only (2026-11-08)
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
        if want_people and not product and (r["kind"] in ("product", "prop")
                                            or "/products/" in str(r.get("label") or r.get("path") or "").lower()):
            continue                         # a picture of people gets people and places; the product only when named
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
    chosen = [r for r in chosen if not _made_by_us(r.get("path") or r.get("file"))]     # never AI from AI
    here = []
    for r in chosen:                                  # a match is only worth something as a file on this machine
        f = local_file(r)
        if f is not None:
            here.append(dict(r, path=str(f)))
    chosen = here
    if not chosen:
        # The referencing process (2026-11-08): a picture starts from something real, so when no asset shares
        # a word with the direction the index is searched wider instead of handing the model words alone.
        chosen, wide = nearest(brand, rows, want, want_people, limit, force)
        why += ["nothing in the brand's assets matches the words of this direction"] + wide
    return chosen, why


# The kinds of real asset a picture falls back to when no word matches, in order: a picture with people
# gets real people first; one without gets real places and the product.
NEAREST_KINDS = {True: ("creator", "read", "footage-frame", "character", "environment"),
                 False: ("environment", "product", "prop", "read"),
                 None: ("creator", "read", "environment", "footage-frame", "product")}


def _stem(w):
    """A plain root: "dating" and "date" -> "dat", "nights" -> "night", "cleaned" -> "clean"."""
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[:-len(suf)]
            break
    if w.endswith("e") and len(w) > 3:
        w = w[:-1]
    return w


def _stems(words):
    return {_stem(w) for w in words}


# Where a brand's REAL material lives, and what is never pulled in on its own (2026-11-08). A reference is a real
# frame or photo: creator footage, product photography and true 3D renders, brand shoots, before/after proof, the
# cast. Old AI tests, the archive, raw intake, finished ads and email outputs are never handed to the model unasked.
NOT_REAL = ("/archive/", "/_old", "/intake/", "/ads/", "/email-sms/", "/deliverables/", "/existing-content/",
            "/runs/image-production/", "/sample-", "/ai-elements/", "/set/", "/core-avatars/")      # ai-elements and set: generated cast,
                                                                                # rooms and props — passed by hand only
AI_NAMES = ("chatgpt image", "dall-e", "dall·e", "midjourney", "gemini_generated", "firefly", "ai-test", "generated")


def real_source(path):
    """True when an asset is real material a picture may start from (see NOT_REAL / AI_NAMES)."""
    s = "/" + str(path or "").lower().replace("\\", "/")
    name = s.rsplit("/", 1)[-1]
    return not any(x in s for x in NOT_REAL) and not any(x in name for x in AI_NAMES) and not _made_by_us(path)


def local_file(r):
    """The asset as a file on this machine: its path, else its Drive label under the mount, else the index's own
    frame of it — None when none is here."""
    path = str(r.get("path") or "")
    if path and not path.startswith("drive:") and pathlib.Path(path).is_file():
        return pathlib.Path(path)
    for fr in r.get("frames") or []:                    # the index's own frame of it, already on this machine
        if pathlib.Path(str(fr)).is_file():
            return pathlib.Path(str(fr))
    did = path[6:] if path.startswith("drive:") else r.get("drive_id")
    if did and _api_route():                             # through the key, by id (the 2026-09-17 ruling)
        return fetch(did, r.get("name") or r.get("label") or "")
    return None


def _made_by_us(path):
    """A picture this component made carries its recipe beside it; it is never a reference (2026-11-08)."""
    if not path:
        return False
    p = pathlib.Path(str(path))
    if not p.name:
        return False
    return p.with_suffix(".recipe.json").is_file() or "/runs/image-production/" in str(p)


def nearest(brand, rows, want, want_people=None, limit=4, force=False):
    """The nearest REAL assets when no word of the direction matched — (rows, why). First by word roots
    ("dating" finds "date night"), then by kind (NEAREST_KINDS). Footage the index has read offers its own
    frames. Only files on this machine, never a picture we made."""
    pool = [r for r in rows if r.get("path")]
    try:
        for r in described(brand, force):
            if r.get("kind") == "still":
                pool.append({"name": r["name"], "kind": "read", "path": r.get("path"), "label": r.get("label") or "",
                             "drive_id": r.get("drive_id"), "bytes": 0, "said": r["said"], "frames": r.get("frames") or []})
            if r.get("kind") == "footage":
                for fr in (r.get("frames") or [])[:1]:          # one frame per clip, so three picks are three clips
                    pool.append({"name": r["name"], "kind": "footage-frame", "path": fr, "bytes": 0, "said": r["said"],
                                 "label": r.get("label") or r.get("path") or ""})
    except Exception:
        pass
    pool = [r for r in pool if real_source(r.get("path")) and real_source(r.get("label") or "")]
    if not pool:
        return [], ["no real asset of this brand is indexed to start from"]

    def resolved(cands):
        """The first `limit` candidates that are files here (fetched by the key when they are on the Drive)."""
        out = []
        for c in cands:
            f = local_file(c)
            if f is not None:
                out.append(dict(c, path=str(f)))
            if len(out) >= limit:
                break
        return out
    stems = _stems(want)
    scored = []
    for r in pool:
        have = _stems(_words(r["name"].replace("-", " ").replace("_", " ")) | _words(r.get("said") or ""))
        hit = stems & have
        if hit and not (want_people is False and r["kind"] == "character"):
            scored.append((len(hit), r, sorted(hit)))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    if scored:
        out = resolved([r for _, r, _ in scored[:limit * 4]])
        if out:
            return out, [f"{r['name']} ({r['kind']}) — nearest by word roots" for r in out]
    order = NEAREST_KINDS.get(want_people, NEAREST_KINDS[None])
    cands = [r for kind in order for r in sorted((x for x in pool if x["kind"] == kind), key=lambda x: x["name"])]
    out = resolved(cands[:limit * 4])
    return out, [f"{r['name']} ({r['kind']}) — the nearest real {r['kind']} asset; no word matched" for r in out]
