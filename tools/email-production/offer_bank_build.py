#!/usr/bin/env python3
"""Build a brand's offer bank.

    python3 offer_bank_build.py --brand brand-a
    python3 offer_bank_build.py --brand brand-a --write   # propose products/offer-bank.md under runs/

RULED 2026-09-13 (the owner): "we're just trying to get the offer bank together, and
then you link to whatever hosts that offer… stop overcomplicating these things."

An offer bank is one shape for every brand: the offers, what each costs, what it
costs subscribed, and the link to wherever it is sold. Where that link points —
Shopify, 29 Next, anything else — is a detail of the link, not a section of the
document. An earlier version branched the whole template on platform and
produced two different documents for two brands; it does not do that now.

Prices are read live from whatever the brand sells on. Everything a machine
cannot know — the lane an offer speaks to, whether it is the paid hero, the
outcome line in the customer's own words — is left as `[RULE THIS]`.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".daemn"))
import daemn_keys                                                  # noqa: E402
from paths import WORKSPACE                                        # noqa: E402
import facts_proposal                                              # noqa: E402
import store as STORE                                              # noqa: E402


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")[:32]


def money(x):
    try:
        return f"${float(x):,.2f}"
    except (TypeError, ValueError):
        return None


def from_shopify(brand):
    """Offers as the storefront sells them."""
    shop = STORE.pull(brand)
    out = []
    for p in shop.get("products", []):
        if not p.get("available"):
            continue
        live = [v for v in p["variants"] if v["available"]]
        if not live:
            continue
        base = min(live, key=lambda v: float(v["price"]))
        subs = []
        for s in (p.get("subscriptions") or []):
            price = None
            try:
                b = float(base["price"])
                price = (b - s["value"] / 100 if s["value_type"] == "fixed_amount"
                         else b * (100 - s["value"]) / 100)
            except (TypeError, ValueError, KeyError):
                pass
            subs.append({"cadence": (s.get("cadence") or "").replace("Deliver every ", ""),
                         "price": money(price)})
        out.append({
            "key": p["handle"], "name": p["title"],
            "price": money(base["price"]),
            "was": money(base["compare_at"]) if base.get("compare_at") else None,
            "subs": subs,
            "sizes": [f"{money(v['price'])} ({v['title']})" for v in live[:4]]
                     if len(live) > 1 else [],
            "handle": p["handle"], "url": p["url"],
        })
    return out


def from_next(brand):
    """Offers as the funnel sells them."""
    s = daemn_keys.key(f"{brand.upper()}_NEXTCOMMERCE_STORE")
    tok = daemn_keys.key(f"{brand.upper()}_NEXTCOMMERCE_ACCESS_TOKEN")
    if not s or not tok:
        return []
    base = f"https://{s}.29next.store/api/admin/"

    def get(p):
        r = subprocess.run(["curl", "-sS", "--max-time", "40",
                            "-H", f"Authorization: Bearer {tok}",
                            "-H", "Accept: application/json", base + p],
                           capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except ValueError:
            return None

    listing = get("products/?limit=100") or {}
    out = []
    for row in (listing.get("results") if isinstance(listing, dict) else listing) or []:
        d = get(f"products/{row.get('id')}/") or {}
        prices = []
        for v in (d.get("variants") or []):
            for pr in (v.get("prices") or []):
                if (pr.get("currency") or "").upper() == "USD" and pr.get("price"):
                    prices.append((float(pr["price"]), pr.get("subscription"),
                                   v.get("title") or v.get("sku")))
                    break
        if not prices:
            continue
        prices.sort()
        low = prices[0]
        subs = []
        if low[1]:
            counts = d.get("interval_counts") or []
            cad = ("/".join(str(c) for c in counts) + f" {d.get('interval')}s"
                   if counts else "on")
            subs.append({"cadence": cad, "price": money(low[1])})
        out.append({
            "key": slug(d.get("title")), "name": d.get("title"),
            "price": money(low[0]), "was": None, "subs": subs,
            "sizes": [f"{money(p)} ({t})" for p, _, t in prices[:4]] if len(prices) > 1 else [],
            "handle": d.get("slug"),
            # 29 Next serves a product at /catalogue/<slug>_<id>/ on the store's
            # own domain; /products/<slug> is a 404 (every Brand A link was, 1 Oct).
            "url": f"{store_domain(brand) or f'https://{s}.29next.store'}/catalogue/{d.get('slug')}_{d.get('id')}/",
        })
    return out


def store_domain(brand):
    """The store's public domain, from the catalog tool's brand config."""
    f = WORKSPACE / "lab" / "catalog" / "tool" / "config" / f"{brand}.json"
    try:
        stores = json.loads(f.read_text()).get("stores") or []
    except (OSError, ValueError):
        return None
    return next((st["domain"].rstrip("/") for st in stores if st.get("domain")), None)


def apply_links(brand, offers):
    """The link an offer carries is the one the brand's own rule names
    (brands/<brand>/products/heroes.json, `sellable[].url` — e.g. Brand A's
    recipe.brand-a.example CPK funnel), never the bare store when a rule exists;
    an offer the rule lists under `never` carries no link at all (1 Oct 2026:
    every email had been linking a dead 29next.store page off this file)."""
    f = WORKSPACE / "brands" / brand / "products" / "heroes.json"
    try:
        h = json.loads(f.read_text())
    except (OSError, ValueError):
        return offers
    sell = {r["handle"]: r.get("url") for r in h.get("sellable") or [] if r.get("handle")}
    never = set((h.get("never") or {}).get("handles") or [])
    ids = catalog_ids(brand)
    for o in offers:
        k = o.get("handle") or o["key"]
        if k in sell and sell[k]:
            o["url"] = sell[k]
        elif k in never:
            o["url"] = None
        o["link_id"] = ids.get(_norm(o["url"])) if o["url"] else None
    return offers


def _norm(u):
    u = re.sub(r"^https?://(www\.)?", "", str(u or "").strip().lower()).rstrip("/")
    return re.sub(r"\.html$", "", u)                 # /landing.html and /landing/ are one page


def catalog_ids(brand):
    """URL -> catalog id, from the catalog tool's brand config (`live_pages`)."""
    f = WORKSPACE / "lab" / "catalog" / "tool" / "config" / f"{brand}.json"
    try:
        pages = json.loads(f.read_text()).get("live_pages") or {}
    except (OSError, ValueError):
        return {}
    return {_norm(u): i for i, u in pages.items() if u}


def render(brand, offers, with_defaults=True):
    L = [f"# Offer bank — {brand}", "",
         "Every offer the brand sells, what it costs, and the link to where it is sold.",
         "Prices are read live; nothing here is typed by hand.", "",
         f"Generated {datetime.date.today().isoformat()} by "
         f"`offer_bank_build.py --brand {brand}`.", "",
         "| Offer | Price | Subscribed | Link |", "|---|---|---|---|"]
    for o in offers:
        sub = " · ".join(f"{s['price']} every {s['cadence']}" for s in o["subs"] if s["price"]) or "—"
        L.append(f"| {o['name']} | {o['price']}"
                 + (f" <sub>was {o['was']}</sub>" if o["was"] else "")
                 + f" | {sub} | " + (f"[link]({o['url']})" if o["url"] else "— not offered") + " |")
    L += ["", "---", ""]
    for o in offers:
        L += [f"## {o['key']} — {o['name']}",
              "_lane: [RULE THIS]_  ·  _hero: [RULE THIS]_", ""]
        L.append(f"- Price: **{o['price']}**" + (f", was {o['was']}" if o["was"] else ""))
        for s in o["subs"]:
            L.append(f"- Subscribed: **{s['price']}** every {s['cadence']}")
        if not o["subs"]:
            L.append("- Subscribed: none")
        if o["sizes"]:
            L.append("- Sizes: " + " · ".join(o["sizes"]))
        L += [f"- Link: {o['url']}" + (f" (catalog `{o['link_id']}`)" if o.get("link_id") else "") if o["url"] else "- Link: none — not offered today (heroes.json `never`)",
              "- Outcome: **OPEN** — no line yet in the customer's own words", ""]
    if not with_defaults:
        return "\n".join(L) + "\n"
    L += ["## Rules", "",
          "- **The hero offer is the front end.** One per lane. A static or video ad points",
          "  at the hero; email may run any offer, or none.",
          "- **One lane per offer.**",
          "- **A dated run carries a window** and is refused outside it.",
          "- **Promos are founder-set.** The machine never invents an offer or a discount.",
          "- **No efficacy timeframes in offer copy** — a guarantee is a refund promise.", "",
          "## Open", "",
          "- Every lane is unruled, and no hero is marked.",
          "- Every outcome is OPEN.", ""]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--write", action="store_true",
                    help="propose products/offer-bank.md under runs/email-production/<brand>/<label>/")
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    a = ap.parse_args()
    offers = apply_links(a.brand, from_shopify(a.brand) or from_next(a.brand))
    if not offers:
        sys.exit(f"no offers found for {a.brand} — no storefront feed and no funnel credentials")
    f = WORKSPACE / "brands" / a.brand / "products" / "offer-bank.md"
    MARK = "# Ruled by a human — carried forward, not generated"
    tail = ""
    if a.write and f.is_file():
        prev = f.read_text()
        if MARK in prev:
            tail = MARK + "\n\n" + prev.split(MARK, 1)[1].lstrip("\n")
    doc = render(a.brand, offers, with_defaults=not tail)
    if a.write:
        if tail:
            doc = doc.rstrip() + "\n\n---\n\n" + tail
        run = facts_proposal.run_dir(a.brand, a.label)
        out = facts_proposal.write(run, a.brand, "products/offer-bank.md", doc)
        print(f"-> {out}  ({len(offers)} offers"
              + (", ruled tail preserved" if tail else "") + ")")
        print(f"proposal -> {facts_proposal.note(run, a.brand)}")
        return
    print(doc)


if __name__ == "__main__":
    main()
