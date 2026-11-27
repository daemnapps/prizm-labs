"""The local face reader for covers (2026-11-12): where the faces and lips are on a picture, so the cover job can say
whether its headline sits on one.

It is the reader the video edit line already uses for its frames: macOS Vision, through the scene tool in
components/video-edit/machine/vision/scene.swift, built once with swiftc into that folder's .build/ (ignored by git).
Local and free; no key, no network. `reader()` is None on a machine that has neither the built tool nor swiftc, and
the cover job then says "faces not checked" and marks the cover not fit to file (models.json `gate.cover.faces`).

    read = reader()
    read("plate.png")  ->  [(l, t, r, b), ...]   pixels of that picture, one box per face and one per pair of lips
"""
import json
import shutil
import subprocess
from pathlib import Path

from . import paths as P


def source():
    return P.sibling("video-edit", "machine", "vision", "scene.swift")


def tool():
    """The built scene tool, built first when it is missing or older than its source. None when it cannot be."""
    src = source()
    if not src.is_file():
        return None
    built = src.parent / ".build" / "scene"
    if built.is_file() and built.stat().st_mtime >= src.stat().st_mtime:
        return built
    swiftc = shutil.which("swiftc")
    if not swiftc:
        return None
    built.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([swiftc, "-O", str(src), "-o", str(built)], capture_output=True, text=True)
    return built if r.returncode == 0 and built.is_file() else None


def boxes(row, size):
    """The scene tool's answer (shares of the picture, top-left origin) as pixel boxes: every face and every lips box."""
    w, h = size
    out = []
    for f in row.get("faces") or []:
        for b in (f.get("box"), f.get("lips")):
            if b:
                out.append(tuple(round(v, 1) for v in (b["x"] * w, b["y"] * h, (b["x"] + b["w"]) * w,
                                                       (b["y"] + b["h"]) * h)))
    return out


def read(picture, built=None):
    """Face and lips boxes on `picture`, in pixels. Raises RuntimeError when the reader cannot read it."""
    from PIL import Image
    built = built or tool()
    if built is None:
        raise RuntimeError("no face reader on this machine")
    with Image.open(picture) as im:
        size = im.size
    r = subprocess.run([str(built), str(picture)], capture_output=True, text=True)
    lines = [x for x in (r.stdout or "").splitlines() if x.strip()]
    if r.returncode or not lines:
        raise RuntimeError(f"the scene tool gave no answer: {(r.stderr or '').strip()[:200]}")
    row = json.loads(lines[0])
    if row.get("error"):
        raise RuntimeError(f"the scene tool could not read the picture: {row['error']}")
    return boxes(row, size)


def reader():
    """read(picture) -> [(l, t, r, b) px], or None when this machine has no face reader."""
    if not source().is_file() or not (shutil.which("swiftc") or (source().parent / ".build" / "scene").is_file()):
        return None

    def go(picture):
        return read(picture)
    return go
