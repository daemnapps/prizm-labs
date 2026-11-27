#!/usr/bin/env python3
"""Small local thumbnails for a swipe library, so pages never read Drive.

    cache_swipe.py --swipe <name> --from <folder of originals>

The briefs tool tried to read stills straight off the Google Drive mount and
deadlocked the whole server — `OSError: [Errno 11] Resource deadlock avoided`
— taking every page down with it (2026-09-14). The mount is for delivery,
through the API, not for a web server to stat forty-five files on.

So: one pass, one small jpeg per post, into `.swipe-cache/<swipe>/`, which is
git-ignored because it is derived and it is media. The originals stay on
Drive; this is only what a page needs to show you a grid.
"""
import argparse, json, sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import paths as P

ap = argparse.ArgumentParser()
ap.add_argument("--swipe", required=True)
ap.add_argument("--from", dest="src", required=True,
                help="a folder holding the original stills")
a = ap.parse_args()

idx = None
for root in (P.SWIPE_ORGANIC, P.SWIPE):
    f = root / a.swipe / "posts.json"
    if f.is_file():
        idx = json.loads(f.read_text()); break
if not idx:
    sys.exit(f"no posts.json for {a.swipe!r}")

out = HERE / ".swipe-cache" / a.swipe
out.mkdir(parents=True, exist_ok=True)
src = Path(a.src)
n, miss = 0, 0
for p in idx["posts"]:
    q = src / p["file"]
    if not q.is_file():
        miss += 1; continue
    im = Image.open(q).convert("RGB")
    im.thumbnail((420, 840), Image.LANCZOS)
    im.save(out / f"{p['slug']}.jpg", "JPEG", quality=72, optimize=True)
    n += 1
print(f"{n} cached → {out.relative_to(HERE)}" + (f", {miss} originals missing" if miss else ""))
