"""Where the Video Studio keeps its data and finds its neighbours — settings, never machine paths in the code.

- VIDEO_STUDIO_DATA   the folder holding `briefs/` and `sources/` (default: `runs/video-studio/` in this repo)
- VIDEO_STUDIO_DRIVE  a synced `Shared Assets` folder to read library clips from (default: none; clips are pulled by link)
- VIDEO_STUDIO_BOARD  the storyboard board's address (default http://127.0.0.1:8914)
- VIDEO_STUDIO_APPROVE the approval page's address (default http://127.0.0.1:8795)
- VIDEO_STUDIO_WRITING the writing runs, each with its production brief (default runs/video-teardown/_work)
- VIDEO_STUDIO_LEDGER  the Queue, the one ledger every tool reads stages from (default http://127.0.0.1:8880)
Keys are read through `components/keys/loader.py`, never from a file here.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]                                   # the workspace this component sits in
DATA = Path(os.environ.get("VIDEO_STUDIO_DATA") or REPO / "runs" / "video-studio")
BRIEFS = DATA / "briefs"
SOURCES = DATA / "sources"
DRIVE_ROOTS = [p for p in [os.environ.get("VIDEO_STUDIO_DRIVE")] if p]
BOARD = os.environ.get("VIDEO_STUDIO_BOARD") or "http://127.0.0.1:8914"
APPROVE = os.environ.get("VIDEO_STUDIO_APPROVE") or "http://127.0.0.1:8795"
WRITING = Path(os.environ.get("VIDEO_STUDIO_WRITING") or REPO / "runs" / "video-teardown" / "_work")   # the writing runs (their production briefs)
LEDGER = os.environ.get("VIDEO_STUDIO_LEDGER") or "http://127.0.0.1:8880"     # the Queue: the one ledger of where every piece is


def part(name, root=None):
    """A neighbour by name, wherever this workspace keeps it: `components/<name>` or `tools/<name>`."""
    root = Path(root or REPO)
    for shelf in ("components", "tools"):
        if (root / shelf / name).is_dir():
            return root / shelf / name
    return root / "components" / name


def key(name):
    """A key by name: the environment, then the workspace key loader."""
    if os.environ.get(name):
        return os.environ[name]
    loader = part("keys")
    if (loader / "loader.py").is_file():
        sys.path.append(str(loader))
        try:
            import loader as L
            return L.key(name) if hasattr(L, "key") else L.get(name)
        except Exception:
            return None
    return None
