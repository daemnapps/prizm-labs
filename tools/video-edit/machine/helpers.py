#!/usr/bin/env python3
"""helpers.py — the door to the AI helpers that need more than the standard library
(MediaPipe face tracking, librosa beats, BiRefNet cut-outs). They live in their own
Python 3.12 venv beside this folder (`tools/video-edit/.venv`, versions pinned in
requirements-helpers.txt) and are called as a subprocess that prints JSON — so the
machine itself stays standard-library and runs anywhere. No venv → the caller falls
back (tempo grid for beats, subject_box / face-blind for faces) and says so.

    python()          -> Path | None      the venv's interpreter, if built
    call(script, *args, timeout=600) -> dict | list    run machine/<script> under it, parse its JSON
    setup()           builds the venv from requirements-helpers.txt (the install is approved)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
LOCAL_VENV = TOOL / ".venv"          # beside the component — the owner's Mac, before LD-52
REQ = TOOL / "requirements-helpers.txt"


def shared_venv() -> Path:
    """The venv outside the repo, named by requirements-helpers.txt (LD-52 (venvs outside repo)),
    so a mini run in a fresh worktree finds it. run-kit `paths.venv()`."""
    p = str(TOOL.parent / "run-kit")
    if p not in sys.path:
        sys.path.insert(0, p)
    from run_kit import paths
    return paths.venv("video-edit", REQ)


def python() -> Path | None:
    """The helpers' interpreter: the shared venv first, then the one beside the component."""
    for v in (shared_venv(), LOCAL_VENV):
        p = v / "bin" / "python"
        if p.exists():
            return p
    return None


class HelperMissing(RuntimeError):
    pass


def call(script: str, *args: str, timeout: int = 900):
    py = python()
    if not py:
        raise HelperMissing(f"the helpers venv is not built — looked in {shared_venv()} and {LOCAL_VENV}; "
                            "build it with: python3 machine/helpers.py setup")
    r = subprocess.run([str(py), str(HERE / script), *map(str, args)], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{script} failed: {(r.stderr or r.stdout).strip()[-600:]}")
    out = r.stdout.strip()
    return json.loads(out[out.index("{") if out.lstrip().startswith("{") else out.index("["):])


def setup() -> int:
    py312 = next((p for p in ("/opt/homebrew/bin/python3.12", "/usr/local/bin/python3.12") if Path(p).exists()), None)
    venv = shared_venv()
    if not (venv / "bin" / "python").exists():
        venv.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([py312 or "python3.12", "-m", "venv", str(venv)], check=True)
    return subprocess.run([str(venv / "bin" / "python"), "-m", "pip", "install", "-r", str(REQ)]).returncode


if __name__ == "__main__":
    if sys.argv[1:2] == ["setup"]:
        sys.exit(setup())
    print(f"helpers venv: {python() or f'not built — looked in {shared_venv()} and {LOCAL_VENV}; python3 machine/helpers.py setup'}")
