#!/usr/bin/env python3
"""Shim — moved to components/email-production/adapter/sync.py (2026-10-22, team-outlier/ renamed to adapter/).

Run as a command, it forwards with the same arguments; imported by path (as
lab/owner/human-review/outlier_bridge.py does), it loads the real module and exposes its
names here. Kept for one release. See README.md."""
import runpy
import sys
from pathlib import Path

_target = Path(__file__).resolve().parent.parent / "adapter" / "sync.py"
if __name__ == "__main__":
    sys.argv[0] = str(_target)
    sys.path.insert(0, str(_target.parent))
    runpy.run_path(str(_target), run_name="__main__")
else:
    import importlib.util
    _spec = importlib.util.spec_from_file_location("email_adapter_sync", _target)
    _m = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
