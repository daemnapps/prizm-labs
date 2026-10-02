#!/usr/bin/env python3
"""image-sequence — a carousel or slideshow off one plate.

    python3 tools/image-edit/sequence.py <slide-one.png> --brand <brand> --deltas <06-brief.md | deltas.json>

Slide one is the plate — the draft already made and judged. Every later slide
is ONE delta off it (the AI sequence brief's own slide-deltas block), judged
against slide one for the thread — same person, product, palette, framing.
This writes one job per slide (`jobs.json`) and spends nothing; the session
makes them on Higgsfield and `edit.py --ingest <folder> --results …` brings
them back. `--dry-run` writes no jobs. Results land under
runs/image-edit/<brand>/<label>/slide-NN/.
"""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import image_edit as RE  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slide_one")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--deltas", required=True, help="the brief (its slide-deltas block is read) or a .json list")
    ap.add_argument("--keep", action="append", default=[])
    ap.add_argument("--product")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--region", help="left,top,right,bottom as percentages — the only part that may change")
    ap.add_argument("--model")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--label")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    req = {"brand": a.brand, "slide_one": a.slide_one, "deltas": a.deltas,
           "count": a.count, "dry_run": a.dry_run}
    for k in ("product", "label", "out", "model", "region"):
        if getattr(a, k):
            req[k] = getattr(a, k)
    if a.keep:
        req["keep"] = a.keep
    if a.ref:
        req["references"] = a.ref
    s = RE.sequence(req)
    print(f"{len(s['slides'])} slide(s) after slide one · {s['ready']} ready to make · {s['delivered']} delivered · "
          f"{s['rejected']} rejected · {s['refused']} refused")
    for sl in s["slides"]:
        mark = "✓" if sl["delivered"] else ("!" if sl["refused"] else "·")
        print(f"  {mark} slide {sl['slide']:02d}  {sl['state']}  — {sl['change'][:70]}"
              + (f"  {sl['refused']}" if sl["refused"] else ""))
    if s["ready"]:
        print(f"  jobs: {Path(s['out']) / 'jobs.json'}")
        print(f"  then: edit.py --ingest {s['out']} --results <results.json>")
    print(f"  record: {Path(s['out']) / 'sequence.json'}")


if __name__ == "__main__":
    main()
