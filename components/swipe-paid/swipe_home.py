"""THE SWIPE HOME — where both swipe pools live on the Shared Assets Drive.

    import swipe_home
    swipe_home.root("paid")                 <Shared Assets>/swipe/paid
    swipe_home.path("organic", "sounds")    <Shared Assets>/swipe/organic/sounds
    swipe_home.label("paid", brand)         "Shared Assets/swipe/paid/<brand>"
    swipe_home.resolve(stored)              any stored form, old or new -> today's path

Every swipe reader and writer finds the pools through this one file (SI-47
(swipe switch), ruled triage page 8, switched at midnight BKK 2026-10-07).
The mount comes from components/brandpath's `drive_index.mount()` — the first
GoogleDrive-*company.com account on this machine — so no caller names
a person's Drive account.

THE REVERT. `USE_LAB = True` puts every caller back on the lab folders, which
stay untouched until the rename. One line.

Records and links already handed out keep the path they were written with;
`resolve()` reads every form they use, so they keep working after the switch.
"""
from __future__ import annotations

import sys
from pathlib import Path

POOLS = ("paid", "organic")
USE_LAB = False   # the revert: True puts every caller back on the lab folders
HOME_REL = {"paid": "swipe/paid", "organic": "swipe/organic"}
LAB_REL = {"paid": "lab/owner/swipe-paid", "organic": "lab/owner/swipe-organic"}


def _brandpath() -> Path | None:
    for p in Path(__file__).resolve().parents:
        if (p / "components" / "brandpath" / "drive_index.py").is_file():
            return p / "components" / "brandpath"
    return None


_BP = _brandpath()
if _BP is not None and str(_BP) not in sys.path:
    sys.path.append(str(_BP))
import drive_index  # noqa: E402  components/brandpath — imported, never edited
NO_MOUNT = drive_index.NO_MOUNT  # LD-55 (Drive literal check): named in drive_index only

MOUNT = drive_index.mount        # the seam: tests replace this attribute

# Stored forms, newest first; the first prefix that matches wins.
_FORMS = (
    ("swipe/paid", "paid"),
    ("swipe/organic", "organic"),
    ("lab/owner/swipe-paid", "paid"),
    ("lab/owner/swipe-organic", "organic"),
    ("lab/owner/swipe", "paid"),          # the retired paid form
    ("swipe-paid", "paid"),
    ("swipe-organic", "organic"),
)


def rel(pool) -> str:
    """The pool's folder under Shared Assets."""
    table = LAB_REL if USE_LAB else HOME_REL
    if pool not in table:
        raise ValueError(f"unknown swipe pool {pool!r}; pools are {', '.join(POOLS)}")
    return table[pool]


def label(pool, *parts) -> str:
    """The Drive label a person reads or a record stores: "Shared Assets/…"."""
    return "Shared Assets/" + "/".join([rel(pool), *parts])


def _drive_api():
    """The API-first Shared Assets layer (components/gdrive-creator shared.py), or None on the Drive folder route."""
    for p in Path(__file__).resolve().parents:
        if (p / "components" / "gdrive-creator").is_dir():
            if str(p / "components" / "gdrive-creator") not in sys.path:
                sys.path.append(str(p / "components" / "gdrive-creator"))
            break
    from gdrive_creator import shared
    # LD-47 (Drive sweep) step 1.6: the door decides — a key in the environment OR a person's key file
    # means the API (shared.route()); DRIVE_ROUTE=mount still pins the Drive folder.
    try:
        api = shared.route() == "api"
    except shared.reach.NoDrive:
        api = False
    return shared if api else None


def shared_assets() -> Path:
    """`Shared Assets`: the API copy's root when the Drive is reached through the API (the default, the owner
    20 Oct 2026), else this machine's Drive folder, or NO_MOUNT (which never exists, so a caller's
    is_dir()/exists() check still reports "not mounted")."""
    SH = _drive_api()
    if SH is not None:
        return SH.cache_home()
    m = MOUNT()
    return Path(m) if m else NO_MOUNT


def root(pool) -> Path:
    return shared_assets() / rel(pool)


def path(pool, *parts) -> Path:
    """A piece of a pool. Through the API the piece asked for (one creative's folder, one file) is fetched
    then — the pools are gigabytes, so nothing comes down that no tool asked for."""
    SH = _drive_api()
    if SH is not None and parts:
        cap = 300 * 1024 * 1024
        whole = len(parts) >= 2            # one brand's whole folder is gigabytes: its layout only, files on asking
        SH.ensure("/".join([rel(pool), *[str(x) for x in parts]]),
                  want=(lambda r, size: size < cap) if whole else (lambda r, size: False))
    return root(pool).joinpath(*parts)


def resolve(ref) -> Path | None:
    """Any stored form of a swipe path -> today's path, or None when it does
    not name a swipe pool."""
    if not ref:
        return None
    s = str(ref).replace("\\", "/")
    if "Shared Assets/" in s:
        s = s.split("Shared Assets/", 1)[1]
    s = s.lstrip("/")
    for prefix, pool in _FORMS:
        if s == prefix:
            return root(pool)
        if s.startswith(prefix + "/"):
            rest = s[len(prefix) + 1:]
            return path(pool, rest) if rest else root(pool)
    return None
