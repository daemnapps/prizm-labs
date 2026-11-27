#!/usr/bin/env python3
"""Moved to components/motion/motion_program.py (2026-11-12: the motion chain is its own component). This forward keeps
`import motion_program` and `python3 motion_program.py ...` working from here; new code reaches the motion chain through
components/motion/motion_chain.py."""
import importlib.util
import runpy
import sys
from pathlib import Path

_HOME = Path(__file__).resolve().parents[1] / "motion"
_FILE = _HOME / "motion_program.py"
if __name__ == "__main__":
    sys.path.insert(0, str(_HOME))
    sys.argv[0] = str(_FILE)
    runpy.run_path(str(_FILE), run_name="__main__")
else:
    if str(_HOME) not in sys.path:
        sys.path.insert(0, str(_HOME))
    _spec = importlib.util.spec_from_file_location(__name__, _FILE)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[__name__] = _mod          # whoever imports this gets the real module
    _spec.loader.exec_module(_mod)
