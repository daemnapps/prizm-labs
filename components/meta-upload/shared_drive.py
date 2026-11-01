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

NO_MOUNT = DI.NO_MOUNT  # LD-55 (Drive literal check): named in drive_index only
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


# ---- API first (the owner, 20 Oct 2026: the Drive is reached "directly via API, which our tools need to default to") ---
# With GDRIVE_SA_KEY in the environment, Shared Assets/meta is a local copy kept in step through the API
# (components/gdrive-creator shared.py); a changed card goes back with save(). CARDS_ROUTE=mount pins the Drive folder
# itself: the Meta approve page (approve.py, the owner's Mac only) moves card folders between states, which only the
# folder can do. META_CARDS_ROOT stays the override for tests and trials.
def _sh():
    p = str(REPO / "components/gdrive-creator")
    if p not in sys.path:
        sys.path.append(p)
    from gdrive_creator import shared
    return shared


def api():
    import os
    return (not os.environ.get("META_CARDS_ROOT") and os.environ.get("CARDS_ROUTE") != "mount"
            and bool(os.environ.get("GDRIVE_SA_KEY")))


def _want(rel, size):
    """Which files the local copy fetches: every card.json and the top-level logs; the media of cards waiting in
    1-check (what people look at) up to 300 MB a file. Cards past 1-check keep their media on the Drive."""
    bits = rel.split("/")
    if bits[-1] == "card.json" or len(bits) <= 3 or bits[0] == "learnings":
        return True
    return len(bits) >= 4 and bits[1] == "1-check" and size < 300 * 1024 * 1024


def meta():
    """Shared Assets/meta: the API copy, else the mount's (or NO_MOUNT/meta, which does not exist)."""
    if api():
        got = _sh().folder("meta", want=_want)
        if got is not None:
            return got
    return shared_assets() / "meta"


def save(path):
    """A card file changed in the API copy goes back to the Drive; on the mount it is already there."""
    if api():
        _sh().save(path)


def save_tree(path):
    if api():
        _sh().save_tree(path)
