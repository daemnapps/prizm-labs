#!/usr/bin/env python3
"""What the store actually sells today — pulled live, not remembered.

    python3 store.py --brand brand-b            # read the store, show it
    python3 store.py --brand brand-b --write    # propose products/store.json under runs/

RULED 2026-09-10 (the owner): "there is very little dynamism here — for example a
price change on the Shopify store would not be shown here in the repo… look at
the Shopify store for brand-b, that would show you what's actually live."

The offer bank is a human's rulings. This is the shop's own truth: every
product, every variant, its price, its compare-at, whether it is in stock, and
**its link** — because a campaign, an email or an ad cannot be built without
one. The two are reconciled by `offers.py`; neither overwrites the other, and
where they disagree the disagreement is the finding.

No key, no auth, no connector: a Shopify storefront publishes `products.json`.
Nothing here is brand-specific — the feed URL comes from the brand's own
`email-sms/machine.json`.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

from paths import WORKSPACE
import facts_proposal


def feed_url(brand):
    f = WORKSPACE / "brands" / brand / "email-sms" / "machine.json"
    if f.is_file():
        d = json.loads(f.read_text())
        if d.get("store_feed"):
            return d["store_feed"], d.get("site")
    return None, None


def plans(site, handle):
    """The subscription terms the shop itself publishes.

    A subscription IS an offer — price, cadence and discount — and it was being
    carried in prose from memory: the bank said "$__ today + $__ every 60
    days" when the shop says WIDGET subscribes at $__ off every 75 days. Read it,
    do not remember it."""
    r = subprocess.run(["curl", "-fsSL", "--max-time", "20", f"{site}/products/{handle}.js"],
                       capture_output=True, text=True)
    if r.returncode:
        return []
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return []
    out = []
    for g in d.get("selling_plan_groups") or []:
        for sp in g.get("selling_plans", []):
            adj = (sp.get("price_adjustments") or [{}])[0]
            kind, val = adj.get("value_type"), adj.get("value")
            if kind == "fixed_amount" and val is not None:
                saves = f"${val / 100:.2f} off"
            elif kind == "percentage" and val is not None:
                saves = f"{val}% off"
            else:
                saves = "no stated discount"
            out.append({"group": g.get("name"), "cadence": sp.get("name"), "saves": saves,
                        "value_type": kind, "value": val})
    return out


def pull(brand):
    url, site = feed_url(brand)
    if not url:
        # Not every brand is on Shopify. Brand A runs on 29 Next, which publishes
        # no products.json — that is a different platform, not a missing file.
        return {"brand": brand, "read": None, "source": None, "site": site,
                "products": [], "note": "no Shopify storefront feed for this brand"}
    site = site or re.sub(r"/products\.json.*$", "", url)
    # NOT urllib: this folder contains `email.py`, which shadows the stdlib
    # `email` package, and urllib imports it by way of http.client. Any tool
    # here that touches the network hits the same wall — shell out instead.
    r = subprocess.run(["curl", "-fsSL", "--max-time", "30", url],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"could not read {url} — {r.stderr.strip()[:200]}")
    raw = json.loads(r.stdout)
    out = []
    for p in raw.get("products", []):
        variants = []
        for v in p.get("variants", []):
            variants.append({
                "id": v.get("id"), "title": v.get("title"),
                "sku": v.get("sku") or None,
                "price": v.get("price"),
                "compare_at": v.get("compare_at_price"),
                "available": bool(v.get("available")),
            })
        any_live = any(v["available"] for v in variants)
        out.append({
            "handle": p.get("handle"),
            "title": p.get("title"),
            "url": f"{site}/products/{p.get('handle')}",
            "available": any_live,
            "price_from": min((v["price"] for v in variants if v["available"]), default=None),
            "variants": variants,
            "subscriptions": plans(site, p.get("handle")),
        })
    return {"brand": brand, "read": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": url, "site": site, "products": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help="brand folder name under brands/ — there is no default brand")
    ap.add_argument("--write", action="store_true",
                    help="propose products/store.json under runs/email-production/<brand>/<label>/")
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    ap.add_argument("--subs", action="store_true",
                    help="the subscription picture: every plan, cadence and discount, "
                         "and where they disagree with each other")
    a = ap.parse_args()
    d = pull(a.brand)
    if a.write:
        run = facts_proposal.run_dir(a.brand, a.label)
        f = facts_proposal.write(run, a.brand, "products/store.json", json.dumps(d, indent=1) + "\n")
        print(f"-> {f}  ({len(d['products'])} products, read {d['read']})")
        print(f"proposal -> {facts_proposal.note(run, a.brand)}")
        return
    if a.subs:
        rows = []
        for p_ in d["products"]:
            live = [v for v in p_["variants"] if v["available"]]
            base = min(live, key=lambda v: float(v["price"])) if live else None
            for s in (p_.get("subscriptions") or [None]):
                eff = None
                if s and base:
                    try:
                        b = float(base["price"])
                        eff = (b - s["value"] / 100 if s["value_type"] == "fixed_amount"
                               else b * (100 - s["value"]) / 100)
                    except (TypeError, KeyError, ValueError):
                        eff = None
                rows.append((p_["handle"], base["price"] if base else None, s, eff))
        print(f"subscriptions on {d['site']}   read {d['read']}\n")
        print(f"  {'product':22} {'one-time':>9} {'plan group':<20} "
              f"{'cadence':<22} {'saves':<12} {'cycle price':>11}")
        for h, price, s, eff in rows:
            if not s:
                print(f"  {h:22} {'$'+str(price) if price else '—':>9} "
                      f"{'— no subscription —':<20}")
                continue
            print(f"  {h:22} {'$'+str(price) if price else '—':>9} {s['group']:<20} "
                  f"{s['cadence']:<22} {s['saves']:<12} "
                  f"{('$%.2f' % eff) if eff is not None else '—':>11}")
        groups = sorted({s["group"] for _, _, s, _ in rows if s})
        cads = sorted({s["cadence"] for _, _, s, _ in rows if s})
        shapes = sorted({s["value_type"] for _, _, s, _ in rows if s})
        zero = [h for h, _, s, _ in rows if s and not s.get("value")]
        none_ = [h for h, _, s, _ in rows if not s]
        print(f"\n  {len(groups)} plan group(s): {', '.join(groups)}")
        print(f"  {len(cads)} cadence(s): {', '.join(cads)}")
        print(f"  {len(shapes)} discount shape(s): {', '.join(shapes)}")
        if zero:
            print(f"  saves NOTHING: {', '.join(zero)}")
        if none_:
            print(f"  no subscription: {', '.join(none_)}")
        return

    print(f"{len(d['products'])} products on {d['site']}   read {d['read']}\n")
    for p in d["products"]:
        sold = sum(1 for v in p["variants"] if not v["available"])
        flag = "" if p["available"] else "   ENTIRELY SOLD OUT"
        part = f"   {sold}/{len(p['variants'])} variants sold out" if sold and p["available"] else ""
        print(f"  {p['handle']:22} {(p['title'] or '')[:34]:36} "
              f"from ${p['price_from'] or '—':<8}{flag}{part}")
        for s in p.get("subscriptions") or []:
            print(f"      subscribe: {s['cadence']} — {s['saves']}")
        print(f"      {p['url']}")


if __name__ == "__main__":
    main()
