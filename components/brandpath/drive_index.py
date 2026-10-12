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
"""
import json
import os
import pathlib
import sys
import tempfile

_CACHE = {}
_SAID = set()
_GDRIVE_CREATOR = pathlib.Path(__file__).resolve().parent.parent / "gdrive-creator"


def accounts():
    """Every Drive for Desktop account folder on this machine, sorted; [] when none."""
    cloud = pathlib.Path.home() / "Library" / "CloudStorage"
    if not cloud.is_dir():
        return []
    return sorted(m for m in cloud.glob("GoogleDrive-*") if m.is_dir())


def mount():
    """`Shared Assets` on the first Drive account that has it, or None."""
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
        if p.is_file():
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
    root = pathlib.Path(cache_dir) if cache_dir else pathlib.Path(tempfile.gettempdir()) / "brandpath-drive-cache"
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
