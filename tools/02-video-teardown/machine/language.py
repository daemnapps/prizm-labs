#!/usr/bin/env python3
"""Query the language layer instead of reading it.

    python3 language.py --brand <brand> --stage hooks
    python3 language.py --brand <brand> --avatars

SHIM (LL-1, 2026-09-01). The engine moved to `components/language-layer/` so
the query over the banks has ONE home — this file and the copy lab's copy had
drifted 103 lines apart, and the header here said that drift was the signal to
give it one home rather than to patch both. This file is the same command it
always was: it re-exports the component's engine and hands it this machine's
own settings — its workspace root, its stage map, its widening ladder — so
nothing about a run here changes. The docstring above the engine is the
doctrine; read it there.

STAGE_USE below stays HERE because it is this chain's definition, not the
engine's: what a stage is looking for differs legitimately between chains, and
the engine that ships one chain's map is that chain's engine.
"""

import sys
from pathlib import Path

try:
    from paths import WORKSPACE
except ImportError:                      # the video machine has no paths.py
    from pathlib import Path as _P
    WORKSPACE = _P.home() / "Projects" / "ai-workspace"

_COMPONENT = Path(__file__).resolve().parents[2] / "language-layer"
sys.path.append(str(_COMPONENT))        # appended, never ahead of this machine
from language_layer import engine as _engine     # noqa: E402

# What each stage is actually looking for. Ordered: earlier tags are the
# stage's bread and butter, later ones fill in when the good rows are thin.
# The rare purpose-built tags (`hook`, `caption-hook`) exist but are only a
# handful of rows, so a stage never relies on them alone.
STAGE_USE = {
    "injection":   ["problem-language", "self-descriptor", "identity",
                    "tried-and-failed", "alternative-solution", "cope"],
    # A hook opens where its awareness level may begin, and a funny hook is
    # filled from the room's own reactions — so the result and reaction rows
    # ride along after the problem rows (2026-09-28: a solution-aware joke hook
    # was handed only problem-language and had to go outside the bank).
    "hooks":       ["hook", "hook-headline", "caption-hook", "one-liner",
                    "problem-language", "competitor-annoyance", "self-descriptor",
                    "transformation-reaction", "result-language", "taste", "in-word"],
    # The same hook pass, for an opening that enters at the RESULT — a
    # solution-, product- or most-aware opening, where the problem is not where
    # the ad may begin. The room's reactions and result words lead.
    "hooks-result": ["transformation-reaction", "result-language", "taste", "in-word",
                     "hook", "hook-headline", "caption-hook", "one-liner", "self-descriptor"],
    "placement":   ["buying-criteria", "buy-trigger", "why-interested"],
    "expansion":   ["why-bought", "buying-criteria", "competitor-annoyance",
                    "alternative-solution", "why-interested"],
    "close":       ["objection", "refund-reason", "expectation-gap",
                    "comment-objection", "objection-answer", "churn-risk"],
    "proof":       ["why-bought", "post-use-feeling", "what-they-like",
                    "result-language", "transformation-reaction", "comment-proof"],
    # Schwartz's depth pass (schwartz-part2.md tables (a)/(b); C2, 2026-09-18)
    # — 4d-expansion leads with mechanism once the market is stage-3+
    # sophisticated, chains the smallest accepted fact toward the real claim
    # (gradualization), and answers the failed-solutions concentration beat.
    # Existing tags do most of the work; the three new ones make an avatar's
    # own accepted beliefs and claimed roles available to it rather than
    # guessed (brands/language-schema.md, "New tags — the Schwartz depth
    # pass").
    "depth":       ["self-descriptor", "identity", "tried-and-failed",
                    "alternative-solution", "why-bought", "objection",
                    "buying-criteria", "mechanism", "accepted-belief",
                    "role-claimed"],
    # The 4g creative pass (voice, lookalike character, styling, mood) needs
    # a subculture's own register to sound real rather than written —
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
    # 2f-compose — the second door (Damon's ruling 2026-09-18). It writes a
    # whole construct from a chosen framework rather than abstracting one off
    # a swipe, so it needs the whole ladder in one query: the problem in their
    # words, the belief a gradualization chain can start from, the mechanism a
    # stage-3 market demands, the roles an identification beat attaches, and
    # the register a camouflage beat has to sound like. Built from the `depth`
    # and `spice` tags above — the same rows those two stages read, ordered
    # for a stage that opens on the problem and closes on the offer. No new
    # tag: a compose stage that needed its own vocabulary would be writing an
    # ad the rest of the chain could not.
    "compose":     ["problem-language", "self-descriptor", "identity",
                    "accepted-belief", "role-claimed", "mechanism",
                    "tried-and-failed", "alternative-solution", "objection",
                    "why-bought", "result-language", "transformation-reaction",
                    "subculture", "in-word"],
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

_engine.configure(workspace=WORKSPACE, stage_use=STAGE_USE, widen="ladder",
                  title="Language for this stage")

# The public surface this file has always had, unchanged.
WORKSPACE = _engine.WORKSPACE
TIER_RANK = _engine.TIER_RANK
_ROOTS = _engine._ROOTS
bank_dir = _engine.bank_dir
brand_dir = _engine.brand_dir
avatars = _engine.avatars
load = _engine.load
_uses = _engine._uses
query = _engine.query
render = _engine.render
for_stage = _engine.for_stage
topics_of = _engine.topics_of
load_used = _engine.load_used     # the used lane (2026-09-28)
used_ids = _engine.used_ids
main = _engine.main

if __name__ == "__main__":
    main()
