#!/usr/bin/env python3
"""File a run's WORDS to the repo's one home for run records.

    python3 file_run.py                  every finished run on this machine
    python3 file_run.py <run-label>      one run

    runs/video-teardown/<brand>/<slug>/
        run.json  doctrine.json  elements.json  stages/*.md  prompts/*.md

`runs/README.md` (Dayu, 2026-09-16): a machine's record must not live beside
its code, because code moves. This machine's working copy stays exactly where
it has always been — `machine/runs/<slug>/`, read by the board, mirrored to the
Drive — and NOTHING is moved. This is one more copy, of the text only.

TEXT ONLY, ALWAYS: never the source video, a poster, a frame, the Doc's HTML,
or anything over 1 MB. Media lives on the Drive (workspace rule 3).

It never deletes and never fails a run: run.py wraps it like every other
end-of-run step, so a problem here prints SKIPPED and the run is still whole.

Switch it off: `VT_NO_REPO_FILING=1` in the environment.
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
sys.path.insert(0, str(MACHINE))
import chain as C                                            # noqa: E402

TOOL = "video-teardown"
OFF_ENV = "VT_NO_REPO_FILING"
MAX_BYTES = 1_000_000
TOP_FILES = ("run.json", "doctrine.json", "elements.json")
TEXT_FOLDERS = ("stages", "prompts")
TEXT_SUFFIX = ".md"


def _safe(s):
    return re.sub(r"[^a-z0-9-]+", "-", str(s or "").lower()).strip("-")


def home(brand, slug, repo=None):
    """<repo>/runs/video-teardown/<brand>/<slug>/ — the repo FOUND by walking
    up (chain.workspace), never counted."""
    repo = Path(repo) if repo else C.workspace()
    return repo / "runs" / TOOL / _safe(brand) / _safe(slug)


def _wanted(run_dir):
    run_dir = Path(run_dir)
    for name in TOP_FILES:
        f = run_dir / name
        if f.is_file():
            yield f, Path(name)
    for folder in TEXT_FOLDERS:
        d = run_dir / folder
        if d.is_dir():
            for f in sorted(d.glob("*" + TEXT_SUFFIX)):
                if f.is_file():
                    yield f, Path(folder) / f.name


def file_run(run_dir, repo=None):
    """Copy one run's text to the repo-root runs/ home.
    -> (dest, copied, left_out). Raises on a run with no brand — the brand IS
    the filing key, and a guessed one would file the record under the wrong
    shelf."""
    run_dir = Path(run_dir)
    st = json.loads((run_dir / "run.json").read_text())
    brand = _safe(st.get("brand"))
    if not brand:
        raise ValueError(f"{run_dir.name}: run.json names no brand, so there "
                         "is no shelf to file it on")
    dest = home(brand, st.get("slug") or run_dir.name, repo)
    copied, left_out = [], []
    for src, rel in _wanted(run_dir):
        if src.stat().st_size > MAX_BYTES:
            left_out.append(f"{rel} (over 1 MB)")
            continue
        try:
            src.read_text(encoding="utf-8")          # text, or it does not go
        except (UnicodeDecodeError, OSError):
            left_out.append(f"{rel} (not text)")
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.is_file() or out.read_bytes() != src.read_bytes():
            shutil.copyfile(src, out)
        copied.append(str(rel))
    return dest, copied, left_out


def file_after_run(run_dir, repo=None):
    """The end-of-run call. -> a one-line note, or None when switched off."""
    if os.environ.get(OFF_ENV):
        return None
    # Only a run in the machine's REAL runs folder reaches the repo's record.
    # Tests and scratch runs point the runs root at a temp folder; they must
    # never be able to write into runs/video-teardown/ (2026-09-18: a test
    # that touched live runs cost a real one, four times).
    if repo is None and \
            Path(run_dir).resolve().parent != (MACHINE / "runs").resolve():
        return None
    dest, copied, left_out = file_run(run_dir, repo)
    try:
        shown = dest.relative_to(Path(repo) if repo else C.workspace())
    except ValueError:
        shown = dest
    return (f"{len(copied)} text file(s) → {shown}"
            + (f" · left out: {', '.join(left_out)}" if left_out else ""))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = C.runs_root()
    if argv:
        dirs = [root / C.run_slug(_safe(argv[0]))]
        if not dirs[0].is_dir():
            dirs = [root / argv[0]]
    else:
        dirs = sorted(p for p in root.iterdir()
                      if p.is_dir() and (p / "run.json").is_file())
    n = 0
    for d in dirs:
        try:
            dest, copied, left_out = file_run(d)
            print(f"  {d.name}: {len(copied)} file(s) → {dest}"
                  + (f" · left out: {', '.join(left_out)}" if left_out else ""))
            n += 1
        except Exception as e:
            print(f"  {d.name}: SKIPPED — {e}")
    print(f"{n} run(s) filed under runs/{TOOL}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
