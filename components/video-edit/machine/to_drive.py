#!/usr/bin/env python3
"""to_drive — the finished videos of one edit run go to the Shared Drive; this Mac keeps a pointer only.

    to_drive.py <edit run> [<edit run> …]      hand an already-finished run's videos over by hand

owner, 2026-11-17, after finished renders filled the Mac: finished exports save straight to the Drive
folder (`Shared Assets/runs/video-edit/<brand>/<label>/…`, the same path as here) and no lasting copy
stays on the Mac. Every road calls `hand(run)` as its LAST act, after the audit, the checks, the
versions, the card and the filing have read the files:

    run.py start        work/final.mp4 (and the deliverable/ copies)
    line.py / beat_cut  renders/<version>.mp4 and deliverable/<ad name>/*.mp4
    v2.py ad            deliverable/<label>_<version>.mp4
    handoff_run         the master copy the run keeps

Which files count as FINISHED is `finals()` below — never a rough cut, a captions draft, a preview, a
working clip or a kit. The move itself is run-kit's `drive_hand` (copy in place on the Drive, pointer
left here, the Mac copy dropped once Drive has uploaded it; a no-op with no Drive mount, on the mini,
with RUNS_TO_DRIVE=off, and for any file git tracks).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_RK = HERE.parent.parent / "run-kit"
if str(_RK) not in sys.path:
    sys.path.append(str(_RK))
from run_kit import drive_hand as DH  # noqa: E402

SKIP_DIRS = {"preview", "qc-frames", "kit", "kits", "work", "clips", "cut"}
# working copies that sit beside the finals in renders/: no words, a proxy for the watcher, half-made
DRAFTS = {"draft", "rough", "captioned", "board", "preview"}   # looked-at drafts, never the finished file
SKIP_MARKS = (".clean.", ".watch-proxy.", ".raw.", ".head.", ".master.", ".part", ".level.")


def finals(run):
    """The finished videos of one edit run, as they sit in it."""
    run = Path(run)
    seen = []
    f = run / "work" / "final.mp4"
    if f.exists() or f.is_symlink():
        seen.append(f)
    for folder in (run / "renders", run / "deliverable"):
        if not folder.is_dir():
            continue
        for p in sorted(folder.rglob("*.mp4")):
            rel = p.relative_to(folder).parts[:-1]
            if (any(part in SKIP_DIRS for part in rel) or any(m in p.name for m in SKIP_MARKS)
                    or p.stem.split("-")[0] in DRAFTS):
                continue
            seen.append(p)
    return seen


def hand(run, quiet=False):
    """Hand every finished video of `run` to the Drive. Never raises, never stops a run."""
    try:
        rows = DH.hand_all(finals(run))
    except Exception as e:                   # filing never stops a delivery
        if not quiet:
            print(f"  Drive: kept on this Mac ({type(e).__name__}: {e})")
        return []
    if not quiet:
        moved = [r for r in rows if r[1]]
        if moved:
            print(f"  Drive: {len(moved)} finished video(s) at Shared Assets/runs/… — the Mac copy drops once uploaded")
        elif rows:
            print(f"  Drive: not moved — {rows[0][2]}")
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__.splitlines()[2]); sys.exit(2)
    for r in sys.argv[1:]:
        for f, d, note in hand(Path(r).resolve() if not Path(r).is_symlink() else Path(r), quiet=True):
            print(f"{f}  ->  {d or '(stayed)'}  ({note})")
