#!/usr/bin/env python3
"""How much room each Apify account has. Reads only, spends nothing, prints no key.

    python3 components/apify/status.py
"""
import json
import urllib.request

import apify

NAMES = ["APIFY_TOKEN", "APIFY_TOKEN_PERSONAL"] + ["APIFY_TOKEN_%d" % n for n in range(2, 10)]


def limits(tok):
    req = urllib.request.Request(apify.API + "/users/me/limits", headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["data"]


def main():
    seen = set()
    for name in NAMES:
        tok = apify._vault(name)
        if not tok or tok in seen:
            continue
        seen.add(tok)
        d = limits(tok)
        cap = d["limits"]["maxMonthlyUsageUsd"]
        used = d["current"]["monthlyUsageUsd"]
        end = d["monthlyUsageCycle"]["endAt"][:10]
        print("%-22s used $%.2f of $%.2f, $%.2f left, cycle ends %s" % (name, used, cap, max(cap - used, 0), end))


if __name__ == "__main__":
    main()
