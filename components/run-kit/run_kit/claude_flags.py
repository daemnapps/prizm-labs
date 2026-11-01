"""The flags every chain's `claude -p` passes the same way (LD-73 (explicit effort)).

A mini run's `claude -p` does not load the account's user settings, so it ran
at the CLI's default effort while a person's own Mac run inherited their
effortLevel. Every call site now passes its effort explicitly, from here:

    from run_kit.claude_flags import effort_args
    argv = ["claude", "-p", "--model", m, *effort_args(), ...]

The level is fixed at "medium" — the owner's own default, the effort the chains
were tuned at (the team, 2026-10-21: "set to medium for mini for now. Don't add
more variables"). No environment knob: change EFFORT here. email-production
keeps its own effort (LD-62 (lean model calls), lean_call.py). Stdlib only.

The model is named the same way (LD-100 (chain model explicit)): a call that
names no model ran on whatever the machine's settings said — Sonnet on the
mini from 2026-10-11, against the 10-01 Opus 5.5 ruling. MODEL is the
registry's entry `claude-opus-5-5` (components/models/models.json, "Claude
Opus 5.5"). CHAIN_MODEL may name another model, honoured only when the
registry lists its id; anything else falls back to MODEL.
"""
import json
import os
from pathlib import Path

EFFORT = "medium"
MODEL = "claude-opus-5-5"   # models.json entry claude-opus-5-5; the 10-01 Opus 5.5 ruling (d1105b91c5)
REGISTRY = Path(__file__).resolve().parents[2] / "models" / "models.json"


def effort() -> str:
    return EFFORT


def effort_args() -> list:
    return ["--effort", EFFORT]


def _registry_ids() -> set:
    try:
        return {m["id"] for m in json.loads(REGISTRY.read_text())["models"] if m.get("id")}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def model() -> str:
    """The chains' model, read at call time: CHAIN_MODEL when the registry lists it, else MODEL."""
    asked = os.environ.get("CHAIN_MODEL", "").strip()
    return asked if asked and asked in _registry_ids() else MODEL


def model_args() -> list:
    return ["--model", model()]
