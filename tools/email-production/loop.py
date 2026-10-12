#!/usr/bin/env python3
"""Loop subscriptions — what is actually running on the storefront.

    python3 loop.py --brand <brand>                 # the picture: status, cadence, value, cycles
    python3 loop.py --brand <brand> --write         # propose products/loop.json under runs/email-production/<brand>/facts-<YYYY-MM-DD>/
    python3 loop.py --brand <brand> --pages 20      # read deeper (2 requests per 3 seconds)

The storefront's subscription CONTRACTS, which no public feed carries: who is
subscribed, on what cadence, at what price, how many cycles they have survived,
and who cancelled. This is the retention half of the picture — the funnel half
lives in Next Commerce.

Auth: `LOOP_<BRAND>_KEY` from the machine's Keychain via `daemn_keys`. The key is
never printed, never written to disk, never passed in a URL.
"""
import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".daemn"))
import daemn_keys                                          # noqa: E402
from paths import WORKSPACE                                # noqa: E402
import facts_proposal                                      # noqa: E402

BASE = "https://api.loopsubscriptions.com/admin/2026-04"


def get(path, token, params=""):
    """Shell out to curl: this folder's `email.py` shadows the stdlib `email`
    package, so anything importing urllib here dies on http.client."""
    url = f"{BASE}{path}{params}"
    r = subprocess.run(["curl", "-fsSL", "--max-time", "30",
                        "-H", f"X-Loop-Token: {token}",
                        "-H", "Accept: application/json", url],
                       capture_output=True, text=True)
    if r.returncode:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def key_name(brand):
    """The Keychain name of this brand's Loop key: `loop_key` in the brand's
    email/machine.json when it names one, else LOOP_<BRAND>_KEY."""
    try:
        d = json.loads((WORKSPACE / "brands" / brand / "email-sms" / "machine.json").read_text())
    except (OSError, ValueError):
        d = {}
    return d.get("loop_key") or f"LOOP_{brand.upper()}_KEY"


def pull(brand, pages=10, size=50):
    token = daemn_keys.key(key_name(brand), required=True)
    rows, cursor = [], None
    for _ in range(pages):
        q = f"?pageSize={size}" + (f"&afterCursor={cursor}" if cursor else "")
        d = get("/subscription", token, q)
        if not d or not d.get("data"):
            break
        rows += d["data"]
        pi = d.get("pageInfo") or {}
        cursor = pi.get("nextCursor") if pi.get("hasNextPage") else None
        if not cursor:
            break
        time.sleep(1.6)                                     # 2 requests / 3 seconds
    return rows


def summarise(rows):
    out = {"contracts_read": len(rows)}
    out["status"] = dict(Counter(r.get("status") for r in rows).most_common())
    cad = Counter()
    for r in rows:
        b = r.get("billingPolicy") or {}
        if b.get("interval"):
            cad[f"every {b.get('intervalCount')} {str(b.get('interval')).lower()}"] += 1
    out["cadence"] = dict(cad.most_common())
    cycles = [r.get("completedOrdersCount") or 0 for r in rows]
    out["cycles"] = {
        "never billed (0)": sum(1 for c in cycles if c == 0),
        "one order": sum(1 for c in cycles if c == 1),
        "2 to 3": sum(1 for c in cycles if 2 <= c <= 3),
        "4 or more": sum(1 for c in cycles if c >= 4),
        "most cycles seen": max(cycles) if cycles else 0,
    }
    live = [r for r in rows if r.get("status") == "ACTIVE"]
    vals = [float(r.get("totalLineItemDiscountedPrice") or 0) for r in live]
    out["active"] = {
        "count": len(live),
        "cycle value total": round(sum(vals), 2),
        "cycle value average": round(sum(vals) / len(vals), 2) if vals else 0,
    }
    why = Counter(r.get("cancellationReason") for r in rows if r.get("cancellationReason"))
    out["cancellation reasons"] = dict(why.most_common(8))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help="brand folder name under brands/ — there is no default brand")
    ap.add_argument("--pages", type=int, default=10)
    ap.add_argument("--write", action="store_true",
                    help="propose products/loop.json under runs/email-production/<brand>/<label>/")
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    a = ap.parse_args()
    rows = pull(a.brand, a.pages)
    if not rows:
        sys.exit("Loop returned nothing — check the key and the token's scopes")
    s = summarise(rows)
    if a.write:
        run = facts_proposal.run_dir(a.brand, a.label)
        f = facts_proposal.write(run, a.brand, "products/loop.json",
                                 json.dumps({"read": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                             "summary": s}, indent=1) + "\n")
        print(f"-> {f}")
        print(f"proposal -> {facts_proposal.note(run, a.brand)}")
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
