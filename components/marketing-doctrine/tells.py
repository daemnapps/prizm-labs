#!/usr/bin/env python3
"""The machine half of the tells layer (tells.json): every `hard` tell's
patterns, run over a piece of text. No model, no network.

    from tells import check_text
    check_text(text, swipe="the source's own transcript")
        -> [{"id": "W2", "name": ..., "match": "game changer", "line": 3, "fix": ...}]

    python3 components/marketing-doctrine/tells.py <file> [--swipe <file>]

A phrase the swipe itself says is the swipe's and is never flagged: a tell is
something WE added (tells.json `hold_rule`).
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TELLS_PATH = HERE / "tells.json"


def hard_tells():
    """-> [(tell row, [compiled pattern])] for every `hard` tell."""
    rows = json.loads(TELLS_PATH.read_text())["tells"]
    return [(t, [re.compile(p, re.I) for p in t.get("patterns") or []])
            for t in rows if t.get("check") == "hard"]


def check_text(text, swipe=""):
    """Every hard-tell match in `text`, one finding per match, in line order.
    A match whose words also appear in `swipe` is the swipe's and is skipped."""
    swipe_l = (swipe or "").lower()
    found = []
    tells = hard_tells()
    for n, line in enumerate((text or "").splitlines(), 1):
        for t, pats in tells:
            seen = set()
            for p in pats:
                for m in p.finditer(line):
                    hit = m.group(0)
                    if hit.strip() and hit.lower() in swipe_l:
                        continue
                    if any(a <= m.start() < b or m.start() <= a < m.end() for a, b in seen):
                        continue
                    seen.add((m.start(), m.end()))
                    found.append({"id": t["id"], "name": t["name"], "match": hit,
                                  "line": n, "fix": t["fix"]})
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description="find the hard tells in a text")
    ap.add_argument("file")
    ap.add_argument("--swipe", help="the source's own words; a phrase it says is not flagged")
    a = ap.parse_args(argv)
    swipe = Path(a.swipe).read_text() if a.swipe else ""
    found = check_text(Path(a.file).read_text(), swipe)
    for f in found:
        print("%s line %d: %s — \"%s\" — %s" % (f["id"], f["line"], f["name"], f["match"], f["fix"]))
    print("%d tell%s" % (len(found), "" if len(found) == 1 else "s"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
