#!/usr/bin/env python3
"""File a brand's swipe library into the Drive structure.

    python3 sync_to_drive.py <brand-slug> [--dry-run]

Words stay in git; media goes to Drive. Target shape is the one already in
use in the paid swipe home, found through `swipe_home` (see its README):

    swipe-paid/<brand>/
      teardown.html
      angles/NN_<angle-slug>/
        _ANGLE.md
        video/     <ad_id>.mp4  +  <ad_id>_poster.jpg
        photos/    <ad_id>.jpg
      _pages/<page-slug>/
        _PAGE.md · page.png · page.html · page.txt

Local `by-angle/NN/image/` maps to Drive `angles/NN/photos/`; local
`pages/by-type/<type>/<slug>/` flattens into `_pages/<slug>/`, since the type
already lives in the page's own _PAGE.md and the repo's index tables.

Copies are skip-if-same-size, so a re-run after a partial upload is cheap.
"""
import os, shutil, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
# The DRIVE mirror is the paid swipe home, found through swipe_home — one
# definition for both pools (SI-47 (swipe switch)). Links already handed out
# keep the path they were written with.
for _r in Path(HERE).parents:
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402

DRIVE = str(swipe_home.root("paid"))

def copy(src, dst, dry):
    if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
        return 0
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    return 1

def main(brand, dry=False):
    if not os.path.isdir(DRIVE):
        sys.exit(f"Drive not mounted at {DRIVE}")
    local = os.path.join(HERE, "assets", brand)
    root = os.path.join(DRIVE, brand)
    n = mb = 0

    src = os.path.join(local, "by-angle")
    for angle in sorted(os.listdir(src)) if os.path.isdir(src) else []:
        a = os.path.join(src, angle)
        if not os.path.isdir(a):
            continue
        for sub, dest_sub in (("video", "video"), ("image", "photos"), (".", ".")):
            sd = os.path.join(a, sub)
            if not os.path.isdir(sd):
                continue
            for f in sorted(os.listdir(sd)):
                p = os.path.join(sd, f)
                if not os.path.isfile(p):
                    continue
                dst = os.path.join(root, "angles", angle,
                                   *( [] if dest_sub == "." else [dest_sub] ), f)
                if copy(p, dst, dry):
                    n += 1; mb += os.path.getsize(p) / 1e6

    bt = os.path.join(local, "pages", "by-type")
    for typ in sorted(os.listdir(bt)) if os.path.isdir(bt) else []:
        td = os.path.join(bt, typ)
        if not os.path.isdir(td):
            continue
        for slug in sorted(os.listdir(td)):
            sd = os.path.join(td, slug)
            if not os.path.isdir(sd):
                continue
            for f in sorted(os.listdir(sd)):
                p = os.path.join(sd, f)
                if os.path.isfile(p) and copy(p, os.path.join(root, "_pages", slug, f), dry):
                    n += 1; mb += os.path.getsize(p) / 1e6

    for f in os.listdir(HERE):
        if f.startswith(f"{brand}-teardown") and f.endswith((".html", ".md")):
            ext = f.rsplit(".", 1)[1]
            if copy(os.path.join(HERE, f), os.path.join(root, f"teardown.{ext}"), dry):
                n += 1

    print(f"{'would copy' if dry else 'copied'} {n} files · {mb:,.0f} MB")
    if not dry:
        print()
        import drive_links
        drive_links.report(brand)

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    main(sys.argv[1], "--dry-run" in sys.argv)
