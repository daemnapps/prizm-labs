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
    python3 machine/colour_match.py <clip.mp4> <first-frame.png>     # a clip

A CLIP is matched the same way (2026-09-23, ELEMENTS.md §5): its first frame
against the piece's first frame, the map applied to every frame by ffmpeg,
the original archived — `match_clip(clip, ref)`.

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


# ------------------------------------------------------------------ clips
#
# ELEMENTS.md §5 (2026-09-23): "every clip is matched to the piece's first
# frame." A clip door returns its own exposure and white balance just as an
# edit door does, and a piece whose clips disagree reads as footage from five
# shoots. So after a clip lands — a post step, never a generation — its first
# frame is measured against the piece's first frame, the per-channel map that
# lands one on the other is written as a 1D LUT, and ffmpeg applies it to the
# whole clip. The sound is copied untouched. The original is ARCHIVED first
# (`<clip>-precolour.<ext>` in the archive folder) and never overwritten, and
# a clip already archived that way is not matched twice.

def have_ffmpeg() -> bool:
    import shutil
    return bool(shutil.which("ffmpeg"))


def _first_frame(clip: Path, out_png: Path) -> bool:
    import subprocess
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-frames:v", "1",
                        str(out_png)], capture_output=True)
    return r.returncode == 0 and out_png.is_file()


def write_cube(luts, path) -> Path:
    """Three 256-entry per-channel maps as a 1D .cube ffmpeg's lut1d reads."""
    path = Path(path)
    rows = ["TITLE \"colour_match to the piece's first frame\"", "LUT_1D_SIZE 256",
            "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
    for i in range(256):
        rows.append(" ".join(f"{luts[c][i] / 255:.6f}" for c in range(3)))
    path.write_text("\n".join(rows) + "\n")
    return path


def clip_luts(clip, ref):
    """The per-channel maps that land the clip's FIRST FRAME on `ref`."""
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "first.png"
        if not _first_frame(Path(clip), png):
            return None
        with Image.open(png) as f, Image.open(ref) as r:
            src = f.convert("RGB").split()
            dst = r.convert("RGB").split()
            return [_lut(s.histogram(), d.histogram()) for s, d in zip(src, dst)]


def match_clip(clip, ref, archive_dir=None, stem=None) -> dict:
    """Match `clip` to the still `ref`, in place, with the original archived.
    Returns {matched, why, archived}. Never raises: a colour pass must never
    lose a clip that was paid for."""
    import shutil
    import subprocess
    import tempfile
    clip, ref = Path(clip), Path(ref)
    arch = Path(archive_dir) if archive_dir else clip.parent / "versions"
    kept = arch / f"{stem or clip.stem}-precolour{clip.suffix}"
    if kept.exists():
        return {"matched": False, "why": f"already matched — the original is {kept}",
                "archived": str(kept)}
    if not (clip.is_file() and ref.is_file()):
        return {"matched": False, "why": "the clip or the first frame is not on disk",
                "archived": None}
    if not (HAVE_PIL and have_ffmpeg()):
        return {"matched": False, "why": "no ffmpeg or no PIL on this machine", "archived": None}
    try:
        luts = clip_luts(clip, ref)
        if luts is None:
            return {"matched": False, "why": "ffmpeg could not read the clip's first frame",
                    "archived": None}
        with tempfile.TemporaryDirectory() as tmp:
            cube = write_cube(luts, Path(tmp) / "match.cube")
            out = Path(tmp) / f"matched{clip.suffix}"
            r = subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", str(clip),
                 "-vf", f"lut1d=file={cube}", "-map", "0:v:0", "-map", "0:a?",
                 "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                 "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)],
                capture_output=True, text=True)
            if r.returncode != 0 or not out.is_file():
                return {"matched": False, "why": f"ffmpeg refused: {r.stderr.strip()[-200:]}",
                        "archived": None}
            arch.mkdir(parents=True, exist_ok=True)
            shutil.copy2(clip, kept)
            shutil.move(str(out), str(clip))
        return {"matched": True, "why": f"matched to {ref.name}", "archived": str(kept)}
    except Exception as e:                      # never lose a clip to this pass
        return {"matched": False, "why": f"{type(e).__name__}: {e}", "archived": None}


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
    if Path(a.edit).suffix.lower() in (".mp4", ".mov", ".webm", ".m4v"):
        res = match_clip(a.edit, a.reference)
        print(f"{'matched' if res['matched'] else 'not matched'} {a.edit}: {res['why']}")
        return 0 if res["matched"] else 2
    ok = match_file(a.edit, a.reference, a.out)
    print(f"{'matched' if ok else 'could not match'} {a.edit} to {a.reference}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
