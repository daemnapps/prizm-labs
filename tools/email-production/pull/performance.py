#!/usr/bin/env python3
"""What every send actually did, joined to what it was.

    python3 calendar/performance.py --brand brand-b [--months 12]

The classification says what each email WAS. This says what it DID. Joined,
they answer the question the calendar exists to settle: what earns, by
category, by type, by segment, by day, by hour.

Metrics are pulled per campaign from the platform's own reporting, so nothing
is estimated. Open rate is reported but carries a caveat everywhere it appears:
Apple Mail privacy auto-opens inflate it, and a segment selected FOR engagement
inflates it again. Click and revenue per recipient are the honest columns.

Proposes email-sms/performance.json under
runs/email-production/<brand>/facts-<YYYY-MM-DD>/ (K2 (brands write wall)).

Reads only.
"""
import argparse
import json
import sys
import time
import urllib.error
from collections import defaultdict
from pathlib import Path

import derive as D

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import WORKSPACE  # noqa: E402
import facts_proposal  # noqa: E402
BRAND_ROOT = WORKSPACE / "brands"

HERE = Path(__file__).resolve().parent

STATS = ["recipients", "delivered", "opens_unique", "clicks_unique",
         "conversions", "conversion_value", "unsubscribes", "spam_complaints",
         "bounced", "revenue_per_recipient"]


def report(key, conversion_metric, timeframe_days):
    body = {"data": {"type": "campaign-values-report", "attributes": {
        "statistics": STATS,
        "timeframe": {"key": timeframe_days},
        "conversion_metric_id": conversion_metric,
        "filter": "equals(send_channel,'email')",
    }}}
    return D.post("campaign-values-reports", key, body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--timeframe", default="last_12_months")
    ap.add_argument("--conversion", default=None,
                    help="the Placed Order metric; defaults to the brand's row in accounts.json")
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    args = ap.parse_args()
    if args.conversion is None:
        # never another brand's metric — the default was brand-b' id for every brand
        if args.brand not in D.BRANDS:
            sys.exit(f"{args.brand} has no row in pull/accounts.json — add one, or pass --conversion")
        args.conversion = D.BRANDS[args.brand]["placed_order"]
    key = D.key_for(args.brand)

    for a in range(6):
        try:
            r = report(key, args.conversion, args.timeframe)
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** a)
                continue
            sys.exit(f"HTTP {e.code}: {e.read()[:400]}")
    else:
        sys.exit("rate limited out")

    rows = r["data"]["attributes"]["results"]
    run = facts_proposal.run_dir(args.brand, args.label)
    out = facts_proposal.write(run, args.brand, "email-sms/performance.json", json.dumps(rows, indent=1) + "\n")
    print(f"{len(rows)} campaign rows -> {out.name}")

    # join to what each email WAS
    cls = {}
    cf = BRAND_ROOT / args.brand / "email-sms" / "classified.json"
    idx = BRAND_ROOT / args.brand / "email-sms" / "sends" / "index.json"
    if cf.is_file() and idx.is_file():
        byfile = {x["file"]: x for x in json.loads(cf.read_text())}
        for x in json.loads(idx.read_text()):
            c = byfile.get(x["file"])
            if c:
                cls[x.get("id") or x["file"]] = c
    print(f"classified emails available to join: {len(cls)}")
    print(f"proposal -> {facts_proposal.note(run, args.brand)}")
    return rows, cls


if __name__ == "__main__":
    main()
