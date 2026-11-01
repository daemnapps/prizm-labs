"""TOMBSTONE — renamed to components/marketing-chain-checks (2026-10-02).
Forwards `quality_checks` and its submodules to `marketing_chain_checks` so
callers opened before the rename keep working. See ../README.md."""
import importlib, sys
from pathlib import Path

_new = Path(__file__).resolve().parents[2] / "marketing-chain-checks"
if str(_new) not in sys.path:
    sys.path.insert(0, str(_new))
_m = importlib.import_module("marketing_chain_checks")
for _sub in ("review", "qc_log", "viewer"):
    try:
        sys.modules[f"{__name__}.{_sub}"] = importlib.import_module(f"marketing_chain_checks.{_sub}")
    except Exception:
        pass
sys.modules[__name__] = _m
