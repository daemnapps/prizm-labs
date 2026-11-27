#!/usr/bin/env python3
"""Carry this Mac's old working runs into runs/video-teardown/_work/ — once.

    python3 move_runs.py               dry run: says what it would move, moves nothing
    python3 move_runs.py --go          moves them
    python3 move_runs.py --go --force  also moves a run touched in the last 10 minutes

SI-56 (teardown working home), 2026-10-08: the working folder left the
component (the old `runs/` beside this file) for `<workspace>/runs/video-teardown/_work/`
(workdir.py). Nothing in the old folder is tracked, so git cannot move it;
each Mac runs this once, by hand.

Every entry (run folders AND loose files) is renamed across whole. It never
overwrites and never merges: a name already in _work/ is SKIPPED and both
copies stay as they are. A run whose run.json changed in the last 10 minutes
is in flight and is SKIPPED unless --force. The old folder is removed only
when it ends up empty (rmdir, never a recursive delete). Exit 2 when --go
skipped anything, so a person reads what is left; a dry run exits 0.
"""

import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workdir  # noqa: E402

IN_FLIGHT_S = 600


def _touched(entry):
    rj = entry / "run.json"
    return (rj if rj.is_file() else entry).stat().st_mtime


def main(argv=None, src=None, dest=None, now=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    go, force = "--go" in argv, "--force" in argv
    src = Path(src) if src is not None else workdir.legacy()
    dest = Path(dest) if dest is not None else workdir.root()
    now = time.time() if now is None else now
    if not src.is_dir():
        print("nothing to move")
        return 0
    skipped = False
    for entry in sorted(src.iterdir(), key=lambda p: p.name):
        name = entry.name
        target = dest / name
        why = None
        if os.path.lexists(target):
            why = f"already in {dest}"
        elif entry.is_dir() and not force and now - _touched(entry) < IN_FLIGHT_S:
            why = "in flight"
        if not go:
            # a dry run moves and skips nothing; it says what --go would do
            print(f"would skip {name} — {why}" if why else f"would move {name}")
            continue
        if why:
            print(f"SKIPPED {name} — {why}")
            skipped = True
            continue
        dest.mkdir(parents=True, exist_ok=True)
        try:
            os.rename(entry, target)
        except OSError:
            shutil.move(str(entry), str(target))
        print(f"moved {name}")
    if go:
        try:
            os.rmdir(src)
        except OSError:
            pass
    if not go:
        print(f"dry run — nothing moved; `python3 move_runs.py --go` moves into {dest}")
    return 2 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
