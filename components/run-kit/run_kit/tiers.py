"""tiers — the one model table: which model each kind of job runs on, for every chain (tiers.json beside this file).

    from run_kit import tiers
    tiers.shared()                    {"reads": ..., "checks": ..., "designs": ...}
    tiers.for_chain("copywriter")     shared, with that chain's pinned jobs on top ("default" resolved)
    tiers.model("session-teardown", "checks")
    tiers.lean("email-production")    True / False (LD-62 (lean model calls))

A chain the table doesn't name gets shared. "default" in a chain's entry means the chains' one model,
claude_flags.model() (LD-100 (chain model explicit)), read at call time so CHAIN_MODEL still works.
Built 2026-11-26 with every chain pinned to what it asked for that day (Creative Workflow Standard 1.8.2).
Stdlib only, Python 3.9.
"""
import json
from pathlib import Path

from . import claude_flags

TABLE = Path(__file__).resolve().parent / "tiers.json"
JOBS = ("reads", "checks", "designs")
_cache = {}


def table():
    """The whole table, read once per process."""
    if "t" not in _cache:
        _cache["t"] = json.loads(TABLE.read_text(encoding="utf-8"))
    return _cache["t"]


def _resolve(m):
    return claude_flags.model() if m == "default" else m


def shared():
    return {j: _resolve(table()["shared"][j]) for j in JOBS}


def entry(chain):
    return (table().get("chains") or {}).get(chain) or {}


def for_chain(chain):
    """Every job's model for one chain: shared, with the chain's pinned jobs on top."""
    pins = entry(chain).get("tiers") or {}
    return {j: _resolve(pins.get(j, table()["shared"][j])) for j in JOBS}


def model(chain, job):
    return for_chain(chain)[job]


def lean(chain):
    return bool(entry(chain).get("lean", False))


def chains():
    return sorted((table().get("chains") or {}))
