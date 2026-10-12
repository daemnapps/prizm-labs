#!/usr/bin/env python3
"""Create the core campaign segments.

    python3 calendar/make_segments.py --brand brand-b [--dry-run]

Campaign segments are NOT the language segments (the owner, 2026-08-28). The
language banks split by journey position because that is what flows need.
Campaigns run on core commercial segments, and this writes them.

Klaviyo's shape, read off the brand's own existing rules: condition_groups are
ANDed together, conditions inside one group are ORed. "3x Purchase OR 3x Order
Value" is one group with two conditions; "2 Orders AND $__ Spent" is two
groups with one each.

Live writes. --dry-run prints what would be created and sends nothing.
"""
import argparse
import json
import sys
import time
import urllib.error

import derive as D

# Metric ids are per-ACCOUNT, so they are resolved per brand at run time —
# never literals (de-branded 2026-08-31: these were one brand's ids, which
# would have silently built wrong segments for the next brand).
METRIC_NAMES = {"order": ["Placed Order", "Ordered Product"],
                "sub": ["Started Subscription", "Subscription Started"],
                "opened": ["Opened Email"],
                "clicked": ["Clicked Email"]}


def resolve_metrics(brand, key):
    """name -> id, from the brand's own account. accounts.json may pin one
    (a brand with two Placed Order metrics must say which is real)."""
    acct = D.BRANDS.get(brand, {})
    found, cur, page = {}, None, 0
    while True:
        r = D.get("metrics", key, **({"page[cursor]": cur} if cur else {}))
        for m in r.get("data", []):
            found[m["attributes"]["name"]] = m["id"]
        nxt = r.get("links", {}).get("next")
        page += 1
        if not nxt or page > 20:
            break
        import urllib.parse as U
        cur = U.parse_qs(U.urlparse(nxt).query).get("page[cursor]", [None])[0]
        if not cur:
            break
    out = {}
    for key_name, candidates in METRIC_NAMES.items():
        pinned = acct.get(f"{key_name}_metric") or (acct.get("placed_order")
                                                    if key_name == "order" else None)
        if pinned:
            out[key_name] = pinned
            continue
        hit = next((found[c] for c in candidates if c in found), None)
        out[key_name] = hit          # None is legal: that segment is skipped
    return out


def metric(mid, measurement, op, value, days=None):
    tf = {"type": "date", "operator": "alltime"} if not days else \
         {"type": "date", "operator": "in-the-last", "unit": "day", "quantity": days}
    return {"type": "profile-metric", "metric_id": mid, "measurement": measurement,
            "measurement_filter": {"type": "numeric", "operator": op, "value": value},
            "timeframe_filter": tf, "metric_filters": None}


CONSENT = {"type": "profile-marketing-consent",
           "consent": {"channel": "email", "can_receive_marketing": True,
                       "consent_status": {"subscription": "any", "filters": None}}}


def g(*conds):
    return {"conditions": list(conds)}


# name, plain-English rule, condition_groups (ANDed) — built per brand
def segment_defs(M):
    ORDER, SUB, OPENED, CLICKED = M['order'], M['sub'], M['opened'], M['clicked']
    defs = [
 ("Core | Lead", "No order ever, and can receive email.",
  [g(metric(ORDER, "count", "equals", 0)), g(CONSENT)]),
 ("Core | One-Time Customer", "Exactly 1 order.",
  [g(metric(ORDER, "count", "equals", 1))]),
 ("Core | Returning Customer", "Exactly 2 orders.",
  [g(metric(ORDER, "count", "equals", 2))]),
 ("Core | Loyal Customer", "3 or 4 orders.",
  [g(metric(ORDER, "count", "greater-than-or-equal", 3)),
   g(metric(ORDER, "count", "less-than", 5))]),
 ("Core | VIP Customer", "5 orders or more.",
  [g(metric(ORDER, "count", "greater-than-or-equal", 5))]),
 ("Core | Subscriber", "Has started a subscription.",
  [g(metric(SUB, "count", "greater-than-or-equal", 1))]),
 ("Core | Churned", "Has bought before, but not in the last 180 days.",
  [g(metric(ORDER, "count", "greater-than-or-equal", 1)),
   g(metric(ORDER, "count", "equals", 0, days=180))]),
 ("Core | Unengaged", "No open and no click in the last 120 days.",
  [g(metric(OPENED, "count", "equals", 0, days=120)),
   g(metric(CLICKED, "count", "equals", 0, days=120))]),
    ]
    need = {"Core | Subscriber": SUB, "Core | Unengaged": OPENED and CLICKED,
            "Core | Lead": ORDER, "Core | One-Time Customer": ORDER,
            "Core | Returning Customer": ORDER, "Core | Loyal Customer": ORDER,
            "Core | VIP Customer": ORDER, "Core | Churned": ORDER}
    return [d for d in defs if need.get(d[0], True)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    key = D.key_for(args.brand)
    M = resolve_metrics(args.brand, key)
    missing = [k for k, v in M.items() if not v]
    if missing:
        print(f'  NOTE: no metric found for {missing} in this account — '
              'the segments that need them are skipped, not guessed')

    existing = {}
    cur, page = None, 0
    import urllib.parse as U
    while True:
        p = {"page[cursor]": cur} if cur else {}
        r = D.get("segments", key, **p)
        for x in r.get("data", []):
            existing[x["attributes"]["name"]] = x["id"]
        nxt = r.get("links", {}).get("next")
        page += 1
        if not nxt or page > 30:
            break
        cur = U.parse_qs(U.urlparse(nxt).query).get("page[cursor]", [None])[0]
        if not cur:
            break

    made = []
    for name, rule, groups in segment_defs(M):
        if name in existing:
            print(f"  SKIP    {name:30} already exists ({existing[name]})")
            continue
        if args.dry_run:
            print(f"  WOULD   {name:30} {rule}")
            continue
        body = {"data": {"type": "segment", "attributes": {
            "name": name, "definition": {"condition_groups": groups}}}}
        for a in range(5):
            try:
                r = D.post("segments", key, body)
                sid = r["data"]["id"]
                print(f"  CREATED {name:30} {sid}   {rule}")
                made.append((name, sid, rule))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(2 ** a)
                    continue
                print(f"  FAILED  {name:30} HTTP {e.code} {e.read()[:220]}")
                break
        time.sleep(1.5)

    if made:
        print(f"\n{len(made)} created. Sizes take a few minutes to populate.")


if __name__ == "__main__":
    main()
