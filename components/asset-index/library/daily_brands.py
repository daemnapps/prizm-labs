#!/usr/bin/env python3
"""daily_brands.py — the brands whose footage library runs on a schedule, read from each brand's own settings.

    python3 daily_brands.py            # one line per brand: "<brand> <daily cap USD>"

A brand is listed when brands/<brand>/footage-library.json has "daily": {"on": true, "usd": <cap>}. Adding a brand to
the schedule is adding that file; no code or scheduler change. run-daily.sh and the machine's scheduler read this.
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BRANDS = Path(os.environ.get("ASSET_INDEX_BRANDS") or (REPO / "brands"))


def daily() -> list:
    out = []
    for f in sorted(BRANDS.glob("*/footage-library.json")):
        if f.parent.name.startswith("_"):
            continue
        try:
            d = (json.loads(f.read_text()).get("daily") or {})
        except ValueError:
            continue
        if d.get("on"):
            out.append((f.parent.name, float(d.get("usd") or 2.0)))
    return out


if __name__ == "__main__":
    for b, usd in daily():
        print(f"{b} {usd:.2f}")
    sys.exit(0)
