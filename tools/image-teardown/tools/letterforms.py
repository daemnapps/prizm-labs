#!/usr/bin/env python3
"""Every letterform the teardowns have used, and every one they had to name.

    letterforms.py                  the bank, and what every run actually used
    letterforms.py --proposed       only the rows waiting for Damon
    letterforms.py --brand <brand>  one brand's runs

Damon, 2026-09-25: *"when we redo teardown, if something doesn't exist in the
bank just yet — just like we have with format and stuff — give it a name so we
can keep things moving forward."*

That rule only works if the names come back. A run that meets a letterform the
bank does not hold writes `none-fits` and proposes a named row, and **carries
on** — nothing waits on a signature. This is the other half: the proposals,
gathered, so a row that was invented once is signed into the bank rather than
re-invented under a different name next week.

**Nothing here writes to the bank.** A row becomes real when Damon puts it in
`tools/image-production/letterform-bank.json` and the element
library is rebuilt — the same gate every other list runs.
"""
import argparse, json, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P
import elements_label as EL


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand")
    ap.add_argument("--proposed", action="store_true", help="only what is not in the bank")
    a = ap.parse_args()

    bank = {r["id"]: r for r in EL.library().rows(*EL.LETTERFORM)}
    used, proposed = Counter(), []
    for f in sorted(P.RUNS.glob("*/out/letterforms.json")):
        run = f.parent.parent.name
        if a.brand and a.brand not in run:
            continue
        try:
            d = json.loads(f.read_text())
        except ValueError:
            continue
        for u in d.get("used") or []:
            used[u["id"]] += 1
        for x in d.get("proposed") or []:
            proposed.append((run, x))

    if not a.proposed:
        print(f"THE BANK — {len(bank)} rows, "
              f"{sum(1 for r in bank.values() if r.get('approved'))} signed\n")
        for i, r in bank.items():
            n = used.get(i, 0)
            mark = "signed  " if r.get("approved") else "draft   "
            print(f"  {mark} {i:22} {r.get('name','')[:26]:26} used on {n} element(s)")
        stray = sorted(set(used) - set(bank) - {"none-fits"})
        if stray:
            print(f"\n  ! ids no row holds: {', '.join(stray)}")
        print(f"\n  none-fits answered {used.get('none-fits', 0)} time(s)")

    print(f"\nPROPOSED — {len(proposed)} row(s) named by a teardown, waiting for Damon")
    if not proposed:
        print("  none. Every text element so far matched a row in the bank.")
        return
    seen = {}
    for run, x in proposed:
        seen.setdefault(x.split("—")[0].strip().lower(), []).append((run, x))
    for k, rows in sorted(seen.items()):
        print(f"\n  {rows[0][1]}")
        print(f"      seen on {len(rows)} run(s): {', '.join(r for r, _ in rows[:4])}")
    print("\n  To make one real: add it to "
          "tools/image-production/letterform-bank.json with "
          '"status": "draft", then rebuild the element library.')


if __name__ == "__main__":
    main()
