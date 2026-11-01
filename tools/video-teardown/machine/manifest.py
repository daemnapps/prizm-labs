"""MOVED to tools/video-writing/machine/ (2026-10-19, the owner: "make tools/video-writing with
the writing code and stages"). This forwarding copy keeps every old reader working: importing it gives
the real module, loading it by path copies the real module's names, and running it runs the real
command. Point new readers at the real file."""
import importlib.util as _u
import sys as _sys
from pathlib import Path as _P

_REAL = _P(__file__).resolve().parents[2] / "video-writing" / "machine" / _P(__file__).name

if __name__ == "__main__":
    import runpy as _rp
    _sys.argv[0] = str(_REAL)
    _rp.run_path(str(_REAL), run_name="__main__")
else:
    _s = _u.spec_from_file_location(__name__, _REAL)
    _m = _u.module_from_spec(_s)
    _s.loader.exec_module(_m)
    globals().update({k: v for k, v in vars(_m).items() if not (k.startswith("__") and k.endswith("__"))})
    _sys.modules[__name__] = _m
