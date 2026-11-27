#!/usr/bin/env python3
"""One product record, the same way for every brand: the one door from any product name to everything the workspace
holds about that product.

    python3 components/naming/products.py record <brand> <any product name>    the record, as JSON
    python3 components/naming/products.py check [<brand>]                      every product, and what it is missing

`record(brand, any_name)` resolves the name to the ONE catalog id (`names.product_id`: store handles, kit aliases and
old names are aliases), then reads, for that id only:

- `name`   the product's name: the store feed's title for any of its names, else the bank page's first heading
- `bank`   the product's bank page in the brand folder, by any of its names: `brands/<b>/products/<name>.md`, or
           `brands/<b>/products/<name>/product.md` (or its README.md)
- `kit`    the product kit `runs/ai-elements/<b>/products/<id>/` (kit.json: what it is, its kind, its measured size;
           `refs`: the reference pictures and the real packshot cut-out in `model/`)
- `drive`  its packshots on the Shared Assets Drive, from `brands/<b>/products/DRIVE-INDEX.json` (id + label):
           the named picks (`<brand>_<id>_…`) at the top of `packshot/`, else the top of `packshot/`; at most six
- `words`  the plain words a script uses for it (its short name, its aliases, the noun of what it is)
- `missing` the parts above the workspace does not hold for it

Every path is repo-relative and every Drive file is an id plus its "Shared Assets/…" label (builder card rule 4).
Nothing is invented: a part not held is left out and named in `missing`. Reads only; writes nothing.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import names  # noqa: E402

PARTS = ("name", "bank", "kit", "drive")
MAX_DRIVE = 6


def _root(root=None):
    if root:
        return Path(root)
    for d in [HERE] + list(HERE.parents):
        if (d / "brands").is_dir() and (d / "components" / "naming").is_dir():
            return d
    return HERE.parents[1]


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def record(brand, any_name, root=None):
    """The product's record (see the module docstring), or None when the name is no product of this brand."""
    repo = _root(root)
    try:
        pid = names.product_id(brand, any_name)
    except Exception:
        pid = None
    try:
        known = set(names.product_ids(brand))
    except Exception:
        known = set()
    if not pid or pid not in known:                      # a name that is no product of this brand is no product
        return None
    try:
        aliases = list(names.product_aliases(brand, pid))
    except Exception:
        aliases = []
    pdir = repo / "brands" / brand / "products"
    kitdir = repo / "runs" / "ai-elements" / brand / "products" / pid
    kit = _json(kitdir / "kit.json") or {}
    called = list(dict.fromkeys([pid] + aliases + list(kit.get("aliases") or []) + [any_name]))
    out = {"brand": brand, "id": pid}
    store = _json(pdir / "store.json") or {}
    title = next((x.get("title") for x in store.get("products") or [] if x.get("handle") in called), None)
    for n in called:
        for cand in (pdir / (n + ".md"), pdir / n / "product.md", pdir / n / "README.md"):
            if cand.is_file():
                out["bank"] = str(cand.relative_to(repo))
                break
        if "bank" in out:
            break
    if not title and out.get("bank"):
        m = re.search(r"^#\s+(.+)$", (repo / out["bank"]).read_text(), re.M)
        title = re.split(r"\s+[—–-]\s+", m.group(1).strip())[0] if m else None
    if title:
        out["name"] = title
    if kit:
        out["kit"] = str(kitdir.relative_to(repo))
        for k in ("what", "kind", "size_reads"):
            if kit.get(k):
                out[k] = kit[k]
        refs = [kitdir / "model" / f for f in ("product-sheet.png", "sheet/current/front.png", "sheet/current/three-quarter.png")]
        out["refs"] = [str(r.relative_to(repo)) for r in refs if r.is_file()]
    idx = _json(pdir / "DRIVE-INDEX.json") or {}
    files = idx.get("files") or {}
    rows = [r for r in (files.values() if isinstance(files, dict) else files) if isinstance(r, dict)]
    top = [r for r in rows if r.get("folder") == pid and r.get("kind") == "packshot" and r.get("drive_id")
           and str(r.get("drive_path", "")).rsplit("/", 2)[-2:-1] == ["packshot"]]
    picked = [r for r in top if str(r.get("name", "")).startswith("%s_%s_" % (brand, pid))]
    drive = [{"drive_id": r["drive_id"], "label": "Shared Assets/" + r["drive_path"], "kind": "packshot"}
             for r in (picked or top)[:MAX_DRIVE]]
    if drive:
        out["drive"] = drive
    words = set(a.lower() for a in aliases + list(kit.get("aliases") or []) if a)
    if title:
        words.add(re.sub(r"[^\w]", "", title.split()[0]).lower())
    if kit.get("what"):
        words.add(str(kit["what"]).split()[-1].lower())
    out["words"] = sorted(w for w in words if len(w) > 2)
    out["missing"] = [p for p in PARTS if not out.get(p)]
    return out


def brands(root=None):
    repo = _root(root)
    return sorted(p.name for p in (repo / "brands").iterdir()
                  if p.is_dir() and not p.name.startswith(("_", ".")) and (p / "CLAUDE.md").is_file())


def check(brand=None, root=None):
    """[(brand, product id, missing parts)] for every product of every brand (or one brand); a brand naming no
    product is one row with product None."""
    out = []
    for b in [brand] if brand else brands(root):
        try:
            ids = names.product_ids(b)
        except Exception:
            ids = []
        if not ids:
            out.append((b, None, list(PARTS)))
        for pid in ids:
            r = record(b, pid, root) or {"missing": list(PARTS)}
            out.append((b, pid, r["missing"]))
    return out


def main(argv):
    if len(argv) >= 3 and argv[0] == "record":
        r = record(argv[1], argv[2])
        print(json.dumps(r, indent=1, ensure_ascii=False) if r else "no product %r in %s" % (argv[2], argv[1]))
        return 0 if r else 1
    if argv and argv[0] == "check":
        rows = check(argv[1] if len(argv) > 1 else None)
        for b, pid, miss in rows:
            print("%-10s %-28s %s" % (b, pid or "(no products)", "complete" if not miss else "missing: " + ", ".join(miss)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
