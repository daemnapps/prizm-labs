"""THE TEXT READER — every line of words macOS Vision reads on a picture, with its height (2026-11-21).

The reader the clip gate already uses for its words checks: macOS Vision, through the readtext tool in
components/video-production/machine/vision/readtext.swift, built once with swiftc into that folder's .build/ (ignored by
git). Local and free; no key, no network. `lines()` is None on a machine with neither the built tool nor swiftc, and
the caller says the words were not read.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import paths as P


def source():
    return P.sibling("video-production", "machine", "vision", "readtext.swift")


def tool():
    """The built readtext tool, built first when it is missing or older than its source. None when it cannot be."""
    src = source()
    if not src.is_file():
        return None
    built = src.parent / ".build" / "readtext"
    if built.is_file() and built.stat().st_mtime >= src.stat().st_mtime:
        return built
    swiftc = shutil.which("swiftc")
    if not swiftc:
        return None
    built.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([swiftc, "-O", str(src), "-o", str(built)], capture_output=True, text=True)
    return built if r.returncode == 0 and built.is_file() else None


def lines(picture):
    """[(height as a share of the frame, text)] for every line Vision reads, or None when the reader cannot run."""
    t = tool()
    if t is None:
        return None
    try:
        out = subprocess.run([str(t), str(picture), "--boxes"], capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    rows = []
    for ln in out.splitlines():
        parts = ln.split("\t", 2)
        if len(parts) == 3:
            try:
                rows.append((float(parts[0]), parts[2].strip()))
            except ValueError:
                pass
    return rows
