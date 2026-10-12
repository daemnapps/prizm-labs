#!/usr/bin/env python3
"""4:5 in, 9:16 out — the content taped down, the strips above and below PAINTED.

    pad.py <in.png> [<out.png>]        finish one picture to 9:16
    pad.py --check <png>               0 if it is a finished 9:16, 1 if not

the owner, 2026-09-22: every asset is 9:16, only the content is 4:5, and no flat
band — the scene continues. So this file no longer pads. It hands the picture
to the one image engine's finish (`tools/image-production`,
`providers.finish_9x16`): the 4:5 content is placed in the middle of the tall
frame, a mask exposes only the strips, the edit model paints the backdrop
continuing, and the original content is pasted back over the answer so it
cannot have moved. The name `pad` and the calls stay so nothing upstream
changes; the solid ink band of 2026-09-09 is retired.

In place (no <out>): the 4:5 content is kept beside the file as
`<stem>--4x5.png` before the 9:16 is written over the name — the content is
never lost. A picture already 9:16 is re-finished from its centre 4:5.
"""
import shutil
import sys
from pathlib import Path
from PIL import Image


def _engine():
    here = Path(__file__).resolve()
    for d in here.parents:
        if (d / "tools" / "image-production" / "models.json").is_file():
            p = str(d / "tools" / "image-production")
            if p not in sys.path:
                sys.path.append(p)
            import image_production as IP
            return IP
    raise SystemExit("tools/image-production is not beside this workspace")


W, H = 1080, 1920                                    # what a finished asset measures


def content_4x5(im):
    """The 4:5 picture inside whatever we were handed (kept for callers)."""
    return _engine().providers.content_4x5(im)


def pad(src, dst=None):
    src = Path(src)
    IP = _engine()
    if dst is None:
        keep = src.with_name(f"{src.stem}--4x5{src.suffix}")
        if not keep.is_file():
            shutil.copy2(src, keep)
        tmp = src.with_name(f"{src.stem}--9x16-tmp.png")
        IP.finish(keep, tmp, fit="content")   # a padded 9:16 re-finishes from its centre 4:5
        shutil.move(str(tmp), str(src))
        return src
    IP.finish(src, dst, fit="content")
    return dst


def solid(png, tol=None):
    """Kept for callers: True when the picture is a finished 9:16 asset."""
    with Image.open(png) as im:
        w, h = im.size
    return abs(h / w - 16 / 9) < 0.01


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--check":
        ok = solid(a[1]); print("finished 9:16" if ok else "NOT a 9:16 asset"); sys.exit(0 if ok else 1)
    print(pad(a[0], a[1] if len(a) > 1 else None))
