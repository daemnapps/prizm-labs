#!/usr/bin/env python3
"""The culture map, built bottom-up from the evidence — see
research_gatherer/culture_map.py for what goes in and how it is checked.

    python3 components/research-gatherer/culture_map.py --brand B --avatar A
    python3 components/research-gatherer/culture_map.py --brand B --all
    python3 components/research-gatherer/culture_map.py --brand B --avatar A --dry-run     # pack + the map it would write, nothing written
    python3 components/research-gatherer/culture_map.py --brand B --avatar A --pack-only   # the evidence pack alone, no model
    python3 components/research-gatherer/culture_map.py --brand B --avatar A --prompt-out P   # the filled prompt, no model
    python3 components/research-gatherer/culture_map.py --brand B --avatar A --answer F      # check + write a saved answer

Writes brands/<brand>/core-avatars/<avatar>/culture-map.md (the first time,
the hand-built map is kept once as culture-map.hand-2026-10-06.md) and a run
record at runs/research/<brand>/culture-map-<avatar>-<stamp>/.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_gatherer import culture_map as CM   # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", required=True)
    who = ap.add_mutually_exclusive_group(required=True)
    who.add_argument("--avatar")
    who.add_argument("--all", action="store_true", help="every roster avatar with a core-avatars folder")
    ap.add_argument("--dry-run", action="store_true", help="print the pack and the would-be map; write nothing")
    ap.add_argument("--pack-only", action="store_true", help="print the evidence pack; no model call")
    ap.add_argument("--model", help="Claude model (default: research.json ownvoice.model)")
    ap.add_argument("--prompt-out", help="write the filled prompt to this file and stop (one avatar)")
    ap.add_argument("--answer", help="check and assemble this saved model answer instead of calling the model (one avatar)")
    a = ap.parse_args(argv)
    if a.all and (a.prompt_out or a.answer):
        ap.error("--prompt-out / --answer take one --avatar")
    avatars = CM.all_avatars(a.brand) if a.all else [a.avatar]
    if not avatars:
        print(f"no avatars with a core-avatars folder for {a.brand}")
        return 1
    bad = 0
    for av in avatars:
        try:
            CM.run(a.brand, av, dry_run=a.dry_run, pack_only=a.pack_only, model=a.model,
                   prompt_out=a.prompt_out, answer=a.answer)
        except Exception as e:
            bad += 1
            print(f"{a.brand}/{av}: FAILED — {e}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
