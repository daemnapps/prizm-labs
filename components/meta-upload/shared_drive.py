#!/usr/bin/env python3
"""Shared Assets on this machine's Drive mount, found by the shared mount helper.

    import shared_drive as SD
    DRIVE = SD.shared_assets()      # the mount's Shared Assets, else SD.NO_MOUNT
    SD.mounted(DRIVE)               # False with no mount

components/brandpath drive_index.mount() looks for it (any GoogleDrive-*
account), so no file here types one person's account. With no mount the answer
is NO_MOUNT, a named path that does not exist (the precedent:
tools/image-production/static/tools/paths.py, _drive_or_absent): a reader's
`.is_dir()` says no, and a writer refuses with NOTE. `META_CARDS_ROOT` and
`--root` stay the overrides; they are read where they always were. Mount only:
meta-upload runs on a person's own Mac. Never writes anything.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.append(str(REPO / "components/brandpath"))  # appended, never ahead of this folder
import drive_index as DI  # noqa: E402

NO_MOUNT = Path.home() / "Library/CloudStorage/_no-drive-mounted/Shared Assets"
NOTE = ("no Shared Assets Drive mount on this machine (components/brandpath drive_index.mount() "
        "found none) — set META_CARDS_ROOT or pass --root")


def shared_assets():
    """Shared Assets on the mount, else NO_MOUNT. Never None."""
    try:
        m = DI.mount()
    except OSError:                 # a mount that will not list reads as none
        m = None
    return Path(m) if m else NO_MOUNT


def mounted(path):
    """True unless `path` is the no-mount stand-in."""
    return Path(path) != NO_MOUNT
