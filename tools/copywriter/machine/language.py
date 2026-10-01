#!/usr/bin/env python3
"""Query the language layer instead of reading it.

    python3 language.py --brand <brand> --stage hooks
    python3 language.py --brand <brand> --avatars

SHIM (LL-1, 2026-09-01). The engine moved to `components/language-layer/` so
the query over the banks has ONE home — this file and the video machine's copy
had drifted 103 lines apart, and the render fix of 2026-08-31 lived only here.
This file is the same command it always was: it re-exports the component's
engine and hands it this machine's own settings — its workspace root and its
stage map — so nothing about a run here changes. This copy was ruled the base
of the convergence (it was the most recent; the drift was staleness), so the
engine's behaviour on this side is the behaviour of this file. The docstring
above the engine is the doctrine; read it there.

STAGE_USE below stays HERE because it is this chain's definition, not the
engine's: the `render` entry exists because this chain has a render stage and
the video chain does not, and the engine that ships one chain's map is that
chain's engine.
"""

import sys
from pathlib import Path

from paths import WORKSPACE

_COMPONENT = next((d for d in Path(__file__).resolve().parents if (d / "components" / "language-layer").is_dir()), Path(__file__).resolve().parents[2].parent) / "components" / "language-layer"
if not _COMPONENT.is_dir():                  # a workspace mounted elsewhere
    _COMPONENT = Path(WORKSPACE) / "components" / "language-layer"
sys.path.append(str(_COMPONENT))        # appended, never ahead of this machine
from language_layer import engine as _engine     # noqa: E402

# What each stage is actually looking for. Ordered: earlier tags are the
# stage's bread and butter, later ones fill in when the good rows are thin.
# The rare purpose-built tags (`hook`, `caption-hook`) exist but are only a
# handful of rows, so a stage never relies on them alone.
STAGE_USE = {
    "injection":   ["problem-language", "self-descriptor", "identity",
                    "tried-and-failed", "alternative-solution", "cope"],
    "hooks":       ["hook", "hook-headline", "caption-hook", "one-liner",
                    "problem-language", "competitor-annoyance", "self-descriptor"],
    "placement":   ["buying-criteria", "buy-trigger", "why-interested"],
    "expansion":   ["why-bought", "buying-criteria", "competitor-annoyance",
                    "alternative-solution", "why-interested"],
    "close":       ["objection", "refund-reason", "expectation-gap",
                    "comment-objection", "objection-answer", "churn-risk"],
    "proof":       ["why-bought", "post-use-feeling", "what-they-like",
                    "result-language", "transformation-reaction", "comment-proof"],
    # The stage that WRITES the finished piece needs both halves: the proof
    # rows for the middle, and the self-descriptor / problem rows for the
    # opening. It used to borrow "proof" alone, so the stage responsible for
    # the first line never saw a single self-label — its own opening check
    # reported "there was no such row available" while `old lady hands` sat
    # in prospects.json (Damon, 2026-08-31). A stage cannot reach for
    # language it was never handed.
    "render":      ["self-descriptor", "problem-language", "identity",
                    "why-bought", "post-use-feeling", "what-they-like",
                    "result-language", "transformation-reaction", "comment-proof"],
    # Schwartz's depth pass (schwartz-part2.md tables (a)/(b); C2, 2026-09-18)
    # — the expansion stage leads with mechanism once the market is stage-3+
    # sophisticated, chains the smallest accepted fact toward the real claim
    # (gradualization), and answers the failed-solutions concentration beat.
    # Existing tags do most of the work; the three new ones make an avatar's
    # own accepted beliefs and claimed roles available to it rather than
    # guessed (brands/language-schema.md, "New tags — the Schwartz depth
    # pass"). Kept identical to the video machine's copy on purpose (LL-1).
    "depth":       ["self-descriptor", "identity", "tried-and-failed",
                    "alternative-solution", "why-bought", "objection",
                    "buying-criteria", "mechanism", "accepted-belief",
                    "role-claimed"],
    # The creative pass (voice, lookalike character, styling, mood) needs a
    # subculture's own register to sound real rather than written —
    # subculture/in-word carry the room's own words; role-claimed and
    # mechanism repeat here because a badge moment and a demonstration both
    # need the same real language the depth pass found.
    # Taste and delivery (2026-09-18): `taste` and `cringe` carry what the
    # room laughs at and what it cringes at, which is where the humor level,
    # the reference world and the avoid list come from — chosen from their
    # world, never from the writer's. `trust-language` and `community-voice`
    # carry who the room believes, which is where the delivery style comes
    # from. See components/marketing-doctrine/delivery.json.
    "spice":       ["subculture", "in-word", "taste", "cringe",
                    "trust-language", "community-voice",
                    "role-claimed", "mechanism",
                    "post-use-feeling", "result-language",
                    "transformation-reaction"],
    # The spoken pass (2026-09-19, Damon: "humans don't use em dashes when
    # speaking — trigger deeper research on actual English-speaking human
    # speech patterns and round up levels of colloquialisms that we can use
    # per sub-avatar"). RQ-22..24 in components/marketing-doctrine/
    # frameworks.json ask how the room phrases things out loud, what it calls
    # things, and how it reacts; the rows land under these tags and the
    # spoken script (4g) and the brief's voice paragraphs (5) read them. A
    # colloquialism level of 3 or above is spoken ONLY in words these rows
    # carry — see components/marketing-doctrine/spoken.json.
    "spoken":      ["in-word", "subculture", "community-voice", "taste"],
}

_engine.configure(workspace=WORKSPACE, stage_use=STAGE_USE, widen="once",
                  title="Customer language for this stage")

# The public surface this file has always had, unchanged.
WORKSPACE = _engine.WORKSPACE
TIER_RANK = _engine.TIER_RANK
brand_dir = _engine.brand_dir
avatar_root = _engine.avatar_root
avatars = _engine.avatars
load = _engine.load
_uses = _engine._uses
query = _engine.query
render = _engine.render
for_stage = _engine.for_stage
topics_of = _engine.topics_of
main = _engine.main

# Also available now, because the video machine needed them and one home means
# one surface: `bank_dir(candidate_tree)` — the bank folder under a candidate
# tree, whichever of the two layouts is in use.
bank_dir = _engine.bank_dir

if __name__ == "__main__":
    main()
