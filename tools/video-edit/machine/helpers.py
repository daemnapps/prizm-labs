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
VENV = TOOL / ".venv"
REQ = TOOL / "requirements-helpers.txt"


def python() -> Path | None:
    p = VENV / "bin" / "python"
    return p if p.exists() else None


class HelperMissing(RuntimeError):
    pass


def call(script: str, *args: str, timeout: int = 900):
    py = python()
    if not py:
        raise HelperMissing("the helpers venv is not built — python3 machine/helpers.py setup")
    r = subprocess.run([str(py), str(HERE / script), *map(str, args)], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{script} failed: {(r.stderr or r.stdout).strip()[-600:]}")
    out = r.stdout.strip()
    return json.loads(out[out.index("{") if out.lstrip().startswith("{") else out.index("["):])


def setup() -> int:
    py312 = next((p for p in ("/opt/homebrew/bin/python3.12", "/usr/local/bin/python3.12") if Path(p).exists()), None)
    if not python():
        subprocess.run([py312 or "python3.12", "-m", "venv", str(VENV)], check=True)
        (VENV / ".gitignore").write_text("*\n")
    return subprocess.run([str(python()), "-m", "pip", "install", "-r", str(REQ)]).returncode


if __name__ == "__main__":
    if sys.argv[1:2] == ["setup"]:
        sys.exit(setup())
    print(f"helpers venv: {python() or 'not built — python3 machine/helpers.py setup'}")
