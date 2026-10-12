#!/usr/bin/env python3
"""image-sequence — a carousel or slideshow off one plate.

    python3 tools/image-edit/sequence.py <slide-one.png> --brand <brand> --deltas <06-brief.md | deltas.json>

Slide one is the plate — the draft the machine already made and judged. Every
later slide is ONE delta off it (the AI sequence brief's own slide-deltas
block), judged against slide one for the thread — same person, product,
palette, framing — and finished to 9:16. `--dry-run` spends nothing.
Results land under runs/image-edit/<brand>/<label>/slide-NN/.

`--to-check` (with `--links`, and `--brief` or `--product`) finishes it: once every
slide has a delivered picture, the carousel — slide one, then each slide's first
delivered picture, in order — is filed as ONE card (format "carousel") in
Team Drive/meta/<brand>/1-check/carousel/<ad name>/ for the owner's approval
(components/meta-upload/feed_carousel.py, which also runs alone on an existing run).
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
    ap.add_argument("--purpose", default="ad")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--region", help="left,top,right,bottom as percentages — the only part that may change")
    ap.add_argument("--model")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--label")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--to-check", action="store_true",
                    help="finish: file the carousel into meta/<brand>/1-check/carousel/ for the owner's approval")
    ap.add_argument("--links", nargs="*", default=[], help="with --to-check: catalog link ids")
    ap.add_argument("--brief", help="with --to-check: the brief the carousel was made from")
    ap.add_argument("--batch", help="with --to-check: the batch (default: today's next free letter)")
    a = ap.parse_args()
    req = {"brand": a.brand, "slide_one": a.slide_one, "deltas": a.deltas, "purpose": a.purpose,
           "count": a.count, "dry_run": a.dry_run}
    for k in ("product", "label", "out", "model", "region"):
        if getattr(a, k):
            req[k] = getattr(a, k)
    if a.keep:
        req["keep"] = a.keep
    if a.ref:
        req["references"] = a.ref
    s = RE.sequence(req)
    print(f"{len(s['slides'])} slide(s) after slide one · {s['delivered']} delivered · "
          f"{s['rejected']} rejected · {s['refused']} refused")
    for sl in s["slides"]:
        mark = "✓" if sl["delivered"] else ("!" if sl["refused"] else "✗")
        print(f"  {mark} slide {sl['slide']:02d}  {sl['state']}  — {sl['change'][:70]}"
              + (f"  {sl['refused']}" if sl["refused"] else ""))
    print(f"  record: {Path(s['out']) / 'sequence.json'}")
    if a.to_check:
        to_check(s, a)


def to_check(s, a):
    """The finishing step: the whole carousel, in order, as one card in 1-check."""
    sys.path.append(str(Path(__file__).resolve().parents[2] / "components" / "meta-upload"))
    import feed_carousel as FC
    try:
        p, src = FC.feed(s["out"], a.brand, a.product, brief=a.brief, batch=a.batch, links=a.links,
                         dry_run=a.dry_run)
    except (FC.T.Refused, ValueError) as e:
        print(f"  to check: REFUSED  {e}")
        return
    print("  to check: " + FC.T.show(p).replace("\n", "\n  "))


if __name__ == "__main__":
    main()
