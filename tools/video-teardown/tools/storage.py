#!/usr/bin/env python3
"""Where dossiers and archived media live.

DECIDED 2026-08-14 (the developer): Google Drive — the "Team Drive" shared
drive, brand-scoped. Drive is an ARCHIVE, never an analysis input
(Gemini cannot read Drive; see CONTEXT.md finding 1).

Layout:

    Shared drives/Team Drive/<brand>/creator-teardowns/
        <platform>-<handle>/
            profile.json, dossier.md, posts/…

Sync happens through Google Drive for Desktop — we write to a normal
local path and Drive uploads it. No API credentials, no OAuth, and the
folder is already shared with the team.

The brand is a RUN-TIME argument, never hardcoded (workspace rule 7):
this component stays brand-agnostic; the caller says which brand a
creator belongs to.

Standalone check:  python3 storage.py            (where would things go?)
                   python3 storage.py <brand>
"""

import os, sys
from pathlib import Path

SHARED_DRIVE = os.environ.get("SHARED_DRIVE_NAME", "Shared drives/Team Drive")
SUBFOLDER = "creator-teardowns"


def drive_root():
    """The mounted 'Team Drive' shared drive, or None if unavailable.

    Prefers the team account when several Google accounts are mounted.
    """
    base = Path.home() / "Library/CloudStorage"
    if not base.exists():
        return None
    mounts = sorted(base.glob("GoogleDrive-*"),
                    key=lambda p: (os.environ.get("DRIVE_ACCOUNT_HINT", "") not in p.name.lower(),
                                   p.name))
    for m in mounts:
        candidate = m / SHARED_DRIVE
        if candidate.is_dir():
            return candidate
    return None


def resolve_out(explicit_out=None, brand=None):
    """Pick the output root. Returns (path, description).

    --out wins when given. Otherwise a brand routes to Drive. With
    neither, fall back to a local folder and say so — a silent local
    write is how two people end up with two private piles.
    """
    if explicit_out:
        return Path(explicit_out).expanduser(), "explicit --out"

    if brand:
        root = drive_root()
        if root is None:
            sys.exit(
                "--brand given but the 'Team Drive' shared drive isn't "
                "mounted.\nInstall/sign in to Google Drive for Desktop with "
                "the team account, or pass --out to write locally.")
        target = root / brand / SUBFOLDER
        if not (root / brand).is_dir():
            existing = sorted(p.name for p in root.iterdir()
                              if p.is_dir() and not p.name.startswith("."))
            sys.exit(f"no brand folder '{brand}' in {root}.\n"
                     f"Brands present: {', '.join(existing) or '(none)'}")
        return target, f"Google Drive → {brand}/{SUBFOLDER}"

    return (Path.home() / "ugc-dossiers",
            "LOCAL ONLY (no --brand given — nothing syncs to the team)")


if __name__ == "__main__":
    brand = sys.argv[1] if len(sys.argv) > 1 else None
    root = drive_root()
    print(f"Team Drive mount: {root or 'NOT MOUNTED'}")
    if root:
        brands = sorted(p.name for p in root.iterdir()
                        if p.is_dir() and not p.name.startswith("."))
        print(f"brands available: {', '.join(brands) or '(none)'}")
    path, why = resolve_out(brand=brand)
    print(f"output root ({why}):\n  {path}")
