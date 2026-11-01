#!/usr/bin/env python3
"""CLI entry point for the research-gatherer engine — see
research_gatherer/engine.py.

    python3 components/research-gatherer/gather.py --brand B --avatar A --sub S
    python3 components/research-gatherer/gather.py --brand B --all
    python3 components/research-gatherer/gather.py --pick-thinnest --cap 150
    python3 components/research-gatherer/gather.py --brand B --avatar A --sub S --dry-run
    python3 components/research-gatherer/gather.py voiceprint --brand B --creator H
    python3 components/research-gatherer/gather.py voiceprint --brand B --all
    python3 components/research-gatherer/gather.py ownvoice --brand B [--dry-run] [--since D]
    python3 components/research-gatherer/gather.py comments --brand B [--sub S] --url <post> [--dry-run]
    python3 components/research-gatherer/gather.py surveys --brand B [--dry-run]
    python3 components/research-gatherer/gather.py reviews --brand B [--dry-run]
    python3 components/research-gatherer/gather.py interviews --brand B [--dry-run]
    python3 components/research-gatherer/gather.py feedback --brand B [--dry-run] [--include-tests]
    python3 components/research-gatherer/gather.py feedcomments --feed <brand>--<x> [--top 15] [--max-comments 200] [--apply]
    python3 components/research-gatherer/gather.py feedcomments --all [--brand B] [--apply]
    python3 components/research-gatherer/gather.py digcomments --dig <brand>/<avatar>/<sub> | --all [--apply]
    python3 components/research-gatherer/gather.py retag --culture --brand B [--avatar A] [--limit N] [--apply]
    python3 components/research-gatherer/gather.py apply --proposal runs/language-layer/B/<run>/proposal.json [--dry-run]

Chain-agnostic — deep mode only. `inputs(st, chain_profile)` is a library
call: it needs a chain's own stage map (which language STAGE_USE keys to
query, where a run's own folder lives), so a chain's shim
(`components/video-teardown/machine/research.py`, and any sibling chain
that adopts this component) exposes it as its own `run` subcommand instead.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_gatherer.engine import main   # noqa: E402

if __name__ == "__main__":
    # `voiceprint` is its own module (research_gatherer/voiceprint.py): the
    # spoken profile of a brand's creators, measured off their own audio.
    # `ownvoice` is its own module (research_gatherer/ownvoice.py): our own
    # audience — ad comments and support emails — into the avatar's bank.
    # `apply` is its own module (research_gatherer/bank_apply.py): the one
    # write path for a language-bank proposal the language layer's bank tools
    # wrote under runs/ — checked against its gates, then written.
    if sys.argv[1:2] == ["apply"]:
        from research_gatherer.bank_apply import main as ap_main   # noqa: E402
        sys.exit(ap_main(sys.argv[2:]))
    # `feedcomments` / `digcomments` (2026-10-06, the bottom-up culture build):
    # comments under the posts an avatar's feed found, and the comments a culture
    # dig captured, as prospect rows — free (yt-dlp), proposed, then applied.
    # `retag --culture`: the seven culture tags added to rows already in the bank.
    if sys.argv[1:2] in (["feedcomments"], ["digcomments"]):
        from research_gatherer.culturecomments import main as cc_main   # noqa: E402
        sys.exit(cc_main(sys.argv[2:], mode=sys.argv[1]))
    if sys.argv[1:2] == ["retag"]:
        from research_gatherer.retag import main as rt_main   # noqa: E402
        sys.exit(rt_main(sys.argv[2:]))
    if sys.argv[1:2] == ["comments"]:
        from research_gatherer.comments import main as cm_main   # noqa: E402
        sys.exit(cm_main(sys.argv[2:]))
    if sys.argv[1:2] == ["ownvoice"]:
        from research_gatherer.ownvoice import main as ov_main   # noqa: E402
        sys.exit(ov_main(sys.argv[2:]))
    # `surveys`, `reviews`, `interviews` (2026-09-29): the free internal
    # sources — form answers, store reviews, transcripts in the brand's inbox —
    # filed through the same read as ownvoice (research_gatherer/voicepull.py).
    # `daily.py` beside this file runs them on a schedule.
    # `feedback` (2026-09-29): the brand's own feedback forms
    # (components/feedback-forms) — Klaviyo "Submitted Feedback" events, read back.
    if sys.argv[1:2] in (["surveys"], ["reviews"], ["interviews"], ["feedback"]):
        import importlib   # noqa: E402
        mod = importlib.import_module(f"research_gatherer.{sys.argv[1]}")
        sys.exit(mod.main(sys.argv[2:]))
    if sys.argv[1:2] == ["voiceprint"]:
        from research_gatherer.voiceprint import main as vp_main   # noqa: E402
        sys.exit(vp_main(sys.argv[2:]))
    sys.exit(main())
