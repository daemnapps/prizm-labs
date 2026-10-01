#!/usr/bin/env python3
"""The chain's steps, declared once — `run.py` (up to the concept brief) and
`approve.py` (after Damon's approval) both read this list, and so can a page.

tier: reads = the answer is in the input · checks = applies rules that are
written down · designs = makes the calls nobody wrote down. The model behind
each tier is `components/run-kit` `model.TIERS` — no model id lives here.
"""
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import paths as P                                             # noqa: E402

sys.path.append(str(P.RUN_KIT))
sys.path.append(str(P.QUALITY))
from run_kit.stage import Chain                               # noqa: E402

STEPS = [
    {"key": "idea1", "name": "Round the idea out — what it really is, who it is for, what it promises, what to ask",
     "tier": "reads", "label": "round-out", "half": "brief"},
    {"key": "idea2", "name": "The awareness read — where the reader stands when they meet it",
     "tier": "checks", "label": "awareness", "depends": ["idea1"], "half": "brief"},
    {"key": "idea3", "name": "The concept brief — format-free",
     "tier": "designs", "label": "concept-brief", "depends": ["idea1", "idea2"], "half": "brief"},
    {"key": "idea4", "name": "Check the brief against the brand's files",
     "tier": "checks", "label": "check", "depends": ["idea3"], "half": "brief"},
    # ---- THE REVIEW STOP: nothing below runs without an approval on file ----
    {"key": "hand1", "name": "Pick the formats from the element library",
     "tier": "checks", "label": "formats", "depends": ["idea3"], "half": "hand-off"},
]
BRIEF_STEPS = [s["key"] for s in STEPS if s["half"] == "brief"]
HANDOFF_STEPS = [s["key"] for s in STEPS if s["half"] == "hand-off"]
KEPT = ("review", "roundout", "awareness", "concept", "formats", "handoffs", "state", "not_on_file")


def old_state(out):
    try:
        return json.loads((Path(out) / "run.json").read_text())
    except (OSError, ValueError):
        return {}


def chain(brand, label, out, assignment, dry, rerun_from, force_model, runner, echo, carry=None):
    """A Chain over STEPS. run-kit's record keeps only the steps from an
    earlier run; what THIS tool adds to run.json (the review above all) is
    carried across here so a second command never wipes an approval."""
    c = Chain(P.TOOL, brand, label, out, P.PROMPTS, STEPS, assignment=assignment, dry=dry,
              rerun_from=rerun_from, force_model=force_model, runner=runner, echo=echo)
    for k in KEPT:
        if carry and k in carry:
            c.record.state[k] = carry[k]
    return c
