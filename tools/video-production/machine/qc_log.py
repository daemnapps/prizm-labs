"""THE QC LOG — shim. The log every tool shares lives in
components/quality-checks/marketing_chain_checks/qc_log.py (2026-10-02: the creative QC
loop installed for every tool and every stage). This file keeps
`machine/qc_log.py add|fix|show` and every caller here unchanged."""
import importlib.util, sys
from pathlib import Path

_p = Path(__file__).resolve().parents[2].parent / "components" / "quality-checks" / "marketing_chain_checks" / "qc_log.py"
_s = importlib.util.spec_from_file_location("qc_log_shared", _p)
_m = importlib.util.module_from_spec(_s); _s.loader.exec_module(_m)
HEAD, add, fix, rounds, tally, main = _m.HEAD, _m.add, _m.fix, _m.rounds, _m.tally, _m.main

if __name__ == "__main__":
    sys.exit(main())
