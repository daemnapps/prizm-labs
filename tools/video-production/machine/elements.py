#!/usr/bin/env python3
"""
elements.py — get the elements out of the cloud and into our own hands.

    python3 elements.py mirror <manifest.tsv>    download every source image
    python3 elements.py check  <brand>           what is mirrored, what is not

WHY THIS EXISTS. A Higgsfield element is a uuid pointing at an image on
someone else's CDN. It is not an asset we own; it is a bookmark. Lose the
account, change plan, or have Higgsfield change a URL and Nina is gone — and
with her the set, the roster and every product reference, none of which are
cheap to rebuild.

So the SOURCE IMAGE is the asset and the uuid is a pointer to it. This walks
every element, downloads the image that made it to the brand's Drive folder,
and writes a record in the repo beside it.

    Drive  brands/<brand>/elements/<category>/<name>.<ext>    the image
    repo   brands/<brand>/elements/<name>.md                  the record

What that buys, in order of how much it matters:

  · A new editor joining gets the folder and can re-bank every element into
    their own workspace from the real source, not from a description.
  · Moving off Higgsfield later costs nothing in assets. The images are ours;
    only the uuids are theirs, and uuids are the cheap part.
  · An element's record sits next to the product or cast member it belongs to,
    so the brand tree explains itself.

The uuid stays recorded because it is what a prompt references TODAY. It is
just no longer the only copy of anything.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[4]
def _drive_root() -> Path:
    """The Google Drive mount holding Shared Assets.

    Set DRIVE_ACCOUNT to the Google account the drive is mounted under.
    Unset, the first GoogleDrive-* mount found is used.
    """
    cs = Path.home() / "Library/CloudStorage"
    acct = os.environ.get("DRIVE_ACCOUNT")
    if acct:
        return cs / f"GoogleDrive-{acct}"
    return next(iter(sorted(cs.glob("GoogleDrive-*"))), cs / "GoogleDrive")


DRIVE = _drive_root() / "Shared drives/Shared Assets/brands"


def repo_dir(brand: str) -> Path:
    return WORKSPACE / "brands" / brand / "elements"


def drive_dir(brand: str, category: str) -> Path:
    return DRIVE / brand / "elements" / category


def mirror(manifest: Path) -> None:
    rows = [l.split("\t") for l in manifest.read_text().splitlines() if l.strip()]
    got = fail = skip = 0
    index: dict[str, list] = {}
    for brand, category, name, uid, url in rows:
        ext = url.rsplit(".", 1)[-1].split("?")[0][:5]
        dd = drive_dir(brand, category)
        dd.mkdir(parents=True, exist_ok=True)
        img = dd / f"{name}.{ext}"
        if img.exists() and img.stat().st_size > 1000:
            skip += 1
        else:
            try:
                urllib.request.urlretrieve(url, img)
                got += 1
            except Exception as e:
                print(f"  FAILED {name}: {e}")
                fail += 1
                continue
        rd = repo_dir(brand)
        rd.mkdir(parents=True, exist_ok=True)
        (rd / f"{name}.md").write_text(
            f"# {name}\n\n"
            f"**Higgsfield element** `{uid}` · category `{category}`\n\n"
            f"**Source image:** `Shared Assets/brands/{brand}/elements/"
            f"{category}/{img.name}` ({img.stat().st_size // 1024} KB)\n\n"
            f"That file is the asset. The uuid above is a pointer into one\n"
            f"Higgsfield workspace and is only good while that workspace is.\n"
            f"To use this element from another account, re-bank the source\n"
            f"image there and record the new uuid here.\n\n"
            f"Originally fetched from `{url}`\n")
        index.setdefault(brand, []).append(
            dict(name=name, category=category, element_id=uid,
                 source=f"elements/{category}/{img.name}"))
    for brand, items in index.items():
        rd = repo_dir(brand)
        (rd / "index.json").write_text(json.dumps(
            {"_what": "Every banked element for this brand, and the source "
                      "image each was built from. The image lives on Drive at "
                      "the path in `source`; the element_id is a pointer into "
                      "one Higgsfield workspace and is the disposable half.",
             "_rebank": "To bring these into another Higgsfield account: "
                        "upload each source image, create the element, and "
                        "record the new id here. Nothing is lost in the move "
                        "because the image is the asset.",
             "brand": brand, "count": len(items),
             "elements": sorted(items, key=lambda x: (x["category"], x["name"]))},
            indent=2))
        print(f"  {brand}: {len(items)} elements indexed")
    print(f"\n  downloaded {got} · already had {skip} · failed {fail}")


def check(brand: str) -> None:
    idx = repo_dir(brand) / "index.json"
    if not idx.exists():
        sys.exit(f"no index for {brand} — run mirror first")
    d = json.loads(idx.read_text())
    missing = [e for e in d["elements"]
               if not (DRIVE / brand / e["source"]).exists()]
    print(f"  {brand}: {d['count']} elements, {len(missing)} missing on Drive")
    for m in missing:
        print(f"    MISSING {m['name']}")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if sys.argv[1] == "mirror":
        mirror(Path(sys.argv[2]))
    elif sys.argv[1] == "check":
        check(sys.argv[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
