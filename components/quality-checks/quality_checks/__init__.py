"""Forwarder — the checks were renamed marketing-chain-checks on 2026-10-02
(the owner: "we need to name this thing something else … call it marketing chain
checks"). `import quality_checks` keeps working: it hands back
`marketing_chain_checks` and its submodules. New code imports
`marketing_chain_checks` directly."""
import importlib
import sys
from pathlib import Path

_here = str(Path(__file__).resolve().parents[1])     # the folder holding both packages
if _here not in sys.path:
    sys.path.insert(0, _here)
_m = importlib.import_module("marketing_chain_checks")
for _sub in ("review", "qc_log", "viewer"):
    try:
        sys.modules[f"{__name__}.{_sub}"] = importlib.import_module(f"marketing_chain_checks.{_sub}")
    except Exception:
        pass
sys.modules[__name__] = _m
