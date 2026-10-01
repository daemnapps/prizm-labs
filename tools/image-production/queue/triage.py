#!/usr/bin/env python3
"""Turn every failed check into a work item. Nothing is left held.

Damon, 2026-09-10: "we want to get out the ads we made and if there are
issues then we need to solve them not just hold back."

A headline mismatch is not a verdict, it is one of three things, and this
decides which and writes it down:

  FIX    the picture really does contradict its words -> a kill carrying the
         fix, so plan()/run() re-make it image-to-image
  CLEAR  the check was wrong -> written into meta-upload/held.json so the
         sheet ships it and the next run does not re-flag it
  ASK    neither is obvious -> listed for Damon, the only state that waits

    python3 triage.py            # show the split, change nothing
    python3 triage.py --apply    # write the kills and the clearings
"""
import argparse, datetime, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs/<brand>"
HELD = HERE.parent.parent / "meta-upload/held.json"
AUDIT = HERE / "headline-audit.json"
REVIEW = HERE / "review.json"

# A still photograph cannot show these, so a mismatch resting on one is the
# judge's error, not the picture's. Each pattern is a thing we have actually
# been wrong about — add to it only from a real case.
CANNOT_SHOW = [
    (r"motion|moving|rotat|high[- ]speed|rpm|static object|motionless",
     "no still photograph shows motion or speed; a spec over a clean product shot is the format working"),
    (r"return policy|guarantee|refund|warranty|\bpolicy\b",
     "a guarantee is a promise in words; the picture carries the product, which is the risk-reversal format"),
    (r"column header|merges two|two opposing|incorrectly merges",
     "the judge was handed two separate lines read as one phrase — it judged a headline the picture never carried"),
]

# The one defect class that is always real: the headline names a visible
# problem and the picture does not show it.
IS_REAL = re.compile(
    r"no visible|lacks the|without visible|clear (skin|neck|face)|not (recently )?shav|"
    r"grown[- ]out beard|full,? (grey|gray|white)? ?beard|has a beard|facial hair|"
    r"front[- ]facing|does not (show|depict)|nowhere in the picture", re.I)


def ocr_headline(name):
    """What the picture actually says, off the pixels — so a mis-read headline
    is caught before it is called a defect."""
    ocr = json.loads((RUNS / "_ocr.json").read_text()) if (RUNS / "_ocr.json").is_file() else {}
    row = ocr.get(name + ".png") or {}
    return (row.get("headline") or "").replace("\n", " ").strip()


def classify(name, v):
    why = (v.get("why") or "") + " " + (v.get("seen") or "")
    for pat, reason in CANNOT_SHOW:
        if re.search(pat, why, re.I):
            return "CLEAR", reason
    seen_head = ocr_headline(name)
    if seen_head and v.get("headline") and seen_head.lower() != v["headline"].lower():
        return "CLEAR", ("the judge was given a headline the picture never carried "
                         f"— it reads \"{seen_head[:60]}\"")
    if IS_REAL.search(why):
        return "FIX", (v.get("why") or "").strip()
    return "ASK", (v.get("why") or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    audit = json.loads(AUDIT.read_text())
    review = json.loads(REVIEW.read_text()) if REVIEW.is_file() else {}
    now = datetime.datetime.now().isoformat(timespec="seconds")

    out = {"FIX": [], "CLEAR": [], "ASK": []}
    for name, v in audit.items():
        if v.get("verdict") != "MISMATCH":
            continue
        if review.get(name, {}).get("verdict") == "kill":
            continue                              # already a work item
        out[classify(name, v)[0]].append((name, v, classify(name, v)[1]))

    for road in ("FIX", "CLEAR", "ASK"):
        if not out[road]:
            continue
        print(f"\n{road} — {len(out[road])}")
        for name, v, reason in out[road]:
            print(f"   {name[-44:]}  {reason[:88]}")

    if not a.apply:
        print("\nnothing written — run with --apply")
        return 0

    for name, v, reason in out["FIX"]:
        review[name] = {"verdict": "kill", "why": reason, "at": now,
                        "by": "triage — the picture does not show what the headline claims"}
    REVIEW.write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n")

    held = json.loads(HELD.read_text()) if HELD.is_file() else {"calls": {}}
    for name, v, reason in out["CLEAR"]:
        held["calls"][name] = {"call": "bad-call", "why": reason, "at": now}
    HELD.write_text(json.dumps(held, indent=1, ensure_ascii=False) + "\n")

    print(f"\nwrote {len(out['FIX'])} kills and {len(out['CLEAR'])} clearings")
    if out["ASK"]:
        print(f"{len(out['ASK'])} need Damon — nothing else is waiting")
    print("next: queue.py plan && queue.py run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
