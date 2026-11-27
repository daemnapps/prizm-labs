"""Moved into the chain 2026-11-17: components/video-edit/maker/maker_pack.py in the workspace is the one copy.
The Studio only calls it (the chains run on their own; the Studio shows them). The Studio's last copy before the
move is _moved-to-chain/maker_pack.py."""
import importlib.util as _iu
import sys as _sys
from pathlib import Path as _P

import settings as _ST

_F = _P(_ST.WRITING).resolve().parents[2] / "components" / "video-edit" / "maker" / "maker_pack.py"
_K = "video_edit_maker_maker_pack"
if _K not in _sys.modules:
    _s = _iu.spec_from_file_location(_K, str(_F))
    _m = _iu.module_from_spec(_s)
    _sys.modules[_K] = _m
    _s.loader.exec_module(_m)
globals().update({k: v for k, v in vars(_sys.modules[_K]).items() if not k.startswith("__")})

if __name__ == "__main__":                       # the command still works from here; it runs the chain copy
    import runpy
    _sys.argv[0] = str(_F)
    runpy.run_path(str(_F), run_name="__main__")
