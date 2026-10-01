#!/usr/bin/env python3
"""
footage.py — ask the library before you pay a model. A gate, not a button.

    python3 machine/footage.py <run>              # match every scene, write the ledger
    python3 machine/footage.py <run> --gate       # exit non-zero if unmatched scenes remain

**The brand owns 1,342 indexed clips.** On 2026-09-11 an entire ad was
generated — thirty-three clips, about 330 credits — without the index being
asked once. Twenty-six of those thirty-three had owned footage sitting in it.
The right number was seven.

The tool existed. The storyboard had a "Find footage" button on every card. It
was never pressed, because nothing in the chain required pressing it. So this
is a stage now: a scene is not generated until the library has been asked about
it, and the answer is written down where the next person can see it.

**Why owned footage beats generated footage even when both work.** It is real:
a real man's real neck, filmed. It costs nothing. It cannot drift from the
product, invent a wordmark, or put a tripod in the shop. And it is the brand's
own proof — the thing a competitor cannot copy.

Generate what the library cannot carry. That list is short, and it is worth
spending on.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

INDEX = "http://127.0.0.1:8420"


def query_for(s: dict) -> str:
    """One dense sentence — what the footage would actually show."""
    said = (s.get("say") or "").strip()
    seen = (s.get("happens") or s.get("product") or s.get("source") or "").strip()
    if seen:
        first = seen.split(". ")[0]
        return ((first + " " + said).strip() if len(first) < 220 else first)[:260]
    return said[:260]


# THE PRESENTER IS NEVER REPLACED BY THE LIBRARY.
#
# 2026-09-11: footage-first was applied to every scene, so eighteen of Nina's
# talking beats were swapped for other creators talking, and the ad stopped
# being hers. The saving was real and the ad was ruined.
#
# A type-A beat is the brand's own presenter saying the brand's own script in
# the brand's own voice. No clip in the library is that, however well it
# matches on words — matching on words is exactly how a different person ends
# up delivering the line.
#
# Footage-first is a rule about B-ROLL: inserts, demonstrations, reactions,
# product in a real hand. It is not a rule about who fronts the ad.
PRESENTER_TYPES = {"A"}


def ask(s: dict, per: int = 3) -> list[dict]:
    if s.get("type") in PRESENTER_TYPES:
        return []
    q = query_for(s)
    if not q:
        return []
    body = json.dumps({"beats": [{"n": s["n"], "beat": q,
                                  "timing": f'{s["start"]}-{s["end"]}'}],
                       "per_beat": per,
                       # browsing for candidates, not answering a brief
                       "min_cover": 0.18, "floor": 0.55}).encode()
    try:
        r = urllib.request.Request(INDEX + "/api/recommend", data=body,
                                   headers={"Content-Type": "application/json"})
        d = json.load(urllib.request.urlopen(r, timeout=25))
        return (d.get("beats") or [{}])[0].get("picks") or []
    except Exception:
        return []


def run(folder: Path, gate: bool = False) -> int:
    board = folder / "storyboard.json"
    if not board.exists():
        sys.exit(f"no storyboard in {folder}")
    b = json.loads(board.read_text())

    owned, need, presenter = [], [], []
    for s in b["scenes"]:
        if s.get("type") in PRESENTER_TYPES:
            s["owned_candidates"] = []
            s["source_plan"] = "presenter"
            s.pop("owned_file", None)
            presenter.append(s)
            continue
        picks = ask(s)
        s["owned_candidates"] = picks
        s["source_plan"] = "cut" if picks else "generate"
        (owned if picks else need).append(s)
    board.write_text(json.dumps(b, indent=1))

    print(f"{len(presenter)} scenes are THE PRESENTER — always her, never the library")
    print(f"{len(owned)} inserts can be CUT from footage we own")
    print(f"{len(need)} inserts need GENERATING\n")
    for s in need:
        print(f"  generate · scene {s['n']:2} {s['type']} · "
              f"{(s.get('say') or s.get('happens') or s.get('product') or '')[:64]}")

    # what it would have cost to generate the lot, against what it costs now
    saved = len(owned)
    print(f"\n{saved} clips not generated. At roughly 10 credits a clip that is "
          f"~{saved * 10} credits, and they are real footage rather than a model's "
          f"idea of it.")

    if gate and need and not all(s.get("takes") for s in need):
        print("\nGATE: scenes still need generating and have no take. "
              "Generate only those.", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path)
    ap.add_argument("--gate", action="store_true",
                    help="exit non-zero while unmatched scenes have no take")
    a = ap.parse_args()
    sys.exit(run(a.run.expanduser().resolve(), a.gate))


if __name__ == "__main__":
    main()
