#!/usr/bin/env python3
"""
colour_match.py — hold the edit to the frame it came from.

A LAST FRAME is an edit of its scene's FIRST FRAME, and an edit door returns
its own idea of the exposure, the white balance and sometimes the pixel
size. Two stills that disagree about any of those read as two different
shots the moment a clip runs from one to the other — which is exactly what a
first-frame/last-frame pair must never do.

So after every edit, mechanically, before the still is verified:

  1. resize the edit to the reference's exact size;
  2. match it per channel to the reference by histogram — for each of R, G
     and B, map every level to the level whose cumulative share of the
     reference matches its own.

Measured live 2026-09-18. Pure PIL, no numpy — the machine has no numpy, and
this runs on every edit in every run, so it has to work with what is here.

    python3 machine/colour_match.py <edit.png> <first-frame.png> [--out f]

`colour_match(src, ref) -> Image` is the helper everything else calls;
`match_file(src_path, ref_path, out_path=None) -> bool` does it on disk and
returns False (never raises) when PIL is missing or either file cannot be
read, because a colour pass must never lose a frame that was generated.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:                                    # PIL is the one dependency, and it is optional
    from PIL import Image               # noqa: F401
    HAVE_PIL = True
except Exception:                       # pragma: no cover — a clone without PIL
    HAVE_PIL = False


def _cdf(hist: list[int]) -> list[float]:
    total = sum(hist) or 1
    out, run = [], 0
    for n in hist:
        run += n
        out.append(run / total)
    return out


def _lut(src_hist: list[int], ref_hist: list[int]) -> list[int]:
    """The 256-entry map that lands the source's distribution on the
    reference's: for each source level, the reference level whose cumulative
    share first reaches the source's own."""
    src_cdf, ref_cdf = _cdf(src_hist), _cdf(ref_hist)
    lut, j = [], 0
    for level in range(256):
        want = src_cdf[level]
        while j < 255 and ref_cdf[j] < want:
            j += 1
        lut.append(j)
    return lut


def colour_match(src, ref):
    """The edit, resized to the reference and matched to it per channel.
    Returns a new RGB image; neither input is modified."""
    from PIL import Image
    src = src.convert("RGB")
    ref = ref.convert("RGB")
    if src.size != ref.size:
        src = src.resize(ref.size, Image.LANCZOS)
    bands_out = []
    for s_band, r_band in zip(src.split(), ref.split()):
        bands_out.append(s_band.point(_lut(s_band.histogram(), r_band.histogram())))
    return Image.merge("RGB", bands_out)


def match_file(src_path, ref_path, out_path=None) -> bool:
    """Match `src_path` to `ref_path`, in place unless `out_path` is given.
    False means nothing was done — never an exception, because losing a
    generated frame to a colour pass would be the worse failure."""
    if not HAVE_PIL:
        return False
    try:
        from PIL import Image
        src_path, ref_path = Path(src_path), Path(ref_path)
        if not (src_path.is_file() and ref_path.is_file()):
            return False
        with Image.open(src_path) as s, Image.open(ref_path) as r:
            out = colour_match(s, r)
        dest = Path(out_path) if out_path else src_path
        out.save(dest)
        return True
    except Exception:
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edit")
    ap.add_argument("reference")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if not HAVE_PIL:
        print("no PIL on this machine — nothing matched", file=sys.stderr)
        return 2
    ok = match_file(a.edit, a.reference, a.out)
    print(f"{'matched' if ok else 'could not match'} {a.edit} to {a.reference}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
