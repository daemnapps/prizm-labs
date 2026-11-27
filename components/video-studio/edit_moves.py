"""Moved to components/video-edit/machine/studio/edit_moves.py (2026-11-21): the edit is Video Edit's work and the Studio is
its view. This name forwards there, as a module and as a command, so every reader keeps working; it goes once readers
call Video Edit directly."""
import importlib.util
import os
import runpy
import sys

_REAL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "video-edit", "machine",
                                      "studio", "edit_moves.py"))
if __name__ == "__main__":
    sys.argv[0] = _REAL
    runpy.run_path(_REAL, run_name="__main__")
else:
    _spec = importlib.util.spec_from_file_location(__name__, _REAL)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[__name__] = _mod
    _spec.loader.exec_module(_mod)
