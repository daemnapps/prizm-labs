#!/usr/bin/env python3
"""The offer bank, as rows the machine can actually query.

    python3 offers.py --brand brand-b                 # what may run, and what may not
    python3 offers.py --brand brand-b --on 2026-09-20 # what may run on a given day
    python3 offers.py --brand brand-b --write         # propose products/offers.json under runs/

RULED 2026-09-10 (the owner: "so there's an offer bank issue then…"). The bank is a
prose document with mixed section types — live offers, drafts, expired ones,
guarantees, standing rules, open gaps. Nothing could answer the one question
that matters, *what may this brand offer this reader today*, so:

- the planner invented plausible keys that do not exist (`named-sets`,
  `vitals-sub`) and the chain only found out at run time, twenty minutes in;
- a guard written against the document's headings accepted `rules` and `open`
  as offers;
- a **draft** offer with no price and an **expired** one stayed assignable;
- a dated offer had no end date, so a Labor Day price stayed "live" into late
  September.

The prose stays the human's source of truth. This reads its own structure —
the `## Live` / `## Draft` / `## Expired` headings the bank already keeps — and
turns it into rows. Nothing here knows a brand, a product or a price.

An offer is USABLE on a date when it is: under Live, not a draft, has no
window or has one containing that date, and its lane matches the avatar.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from paths import HERE, WORKSPACE
import facts_proposal

STATUS = [
    (re.compile(r"^##\s*live\b", re.I), "live"),
    (re.compile(r"^##\s*draft", re.I), "draft"),
]
# headings that hold no offers at all, whatever sits under them
NOT_OFFERS = re.compile(r"^##\s*(guarantees?|open|rules|.*—\s*context|[a-z-]+)\s*$", re.I)


def parse(brand):
    """The offers, read from the bank the generator writes.

    One shape, every brand (RULED 2026-09-13): each offer is a `## key — Name`
    block carrying its price, its subscribed price, its link, and the lines a
    human rules. Anything under the "Ruled by a human" divider is prose for
    people and is not parsed as an offer.
    """
    f = WORKSPACE / "brands" / brand / "products" / "offer-bank.md"
    if not f.is_file():
        return []
    text = f.read_text()
    MARK = "# Ruled by a human"
    if MARK in text:
        text = text.split(MARK, 1)[0]
    rows, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^##\s+([a-z0-9][a-z0-9-]*)\s+—\s+(.+)$", line.strip())
        if m:
            cur = {"key": m.group(1), "title": m.group(2).strip(), "status": "live",
                   "lane": None, "hero": None, "window": None, "url": None,
                   "points_at": m.group(1), "price": None, "subs": [],
                   "outcome_written": True, "states_prices": [], "notes": []}
            rows.append(cur)
            continue
        if cur is None:
            continue
        s = line.strip()
        for name, pat in (("lane", r"_lane:\s*([^_]+)_"), ("hero", r"_hero:\s*([^_]+)_"),
                          ("window", r"_window:\s*([^_]+)_")):
            mm = re.search(pat, s)
            if mm:
                v = mm.group(1).strip()
                cur[name] = None if v.startswith("[RULE") else v
        mm = re.match(r"- Price:\s*\*\*\$([0-9.,]+)\*\*", s)
        if mm:
            cur["price"] = mm.group(1).replace(",", "")
            cur["states_prices"].append(cur["price"])
        mm = re.match(r"- Subscribed:\s*\*\*\$([0-9.,]+)\*\*\s*every\s*(.+)$", s)
        if mm:
            cur["subs"].append({"price": mm.group(1).replace(",", ""),
                                "cadence": mm.group(2).strip()})
            cur["states_prices"].append(mm.group(1).replace(",", ""))
        mm = re.match(r"- Link:\s*(\S+)$", s)
        if mm:
            cur["url"] = mm.group(1)
        if re.search(r"Outcome:\s*\*\*OPEN", s):
            cur["outcome_written"] = False
    # A FREE THING IS NOT AN OFFER — the calendar's reader already says so
    # (brandrecord.render_offers, 2026-09-14) and this one did not, so the copy
    # side would accept a $0.00 sample the planner refuses. One rule, both
    # readers (2026-09-16).
    for r in rows:
        try:
            if r["price"] is not None and float(r["price"]) == 0:
                r["status"] = "free"
        except ValueError:
            pass
    return rows


def store(brand):
    f = WORKSPACE / "brands" / brand / "products" / "store.json"
    return json.loads(f.read_text()) if f.is_file() else None


def reconcile(brand):
    """Where the bank and the shop disagree ABOUT THE OFFER ITSELF.

    Stock is deliberately NOT checked (the owner, 2026-09-11: "do not worry about
    what's sold out and what's not, that doesn't matter right now — we are just
    focusing on the offer and its contents"). What is checked is what the offer
    claims: its price, its link, and whether it points at anything real.

    RULED 2026-09-10 (the owner: "a price change on the Shopify store would not be
    shown here in the repo… the WIDGET + Daily system isn't even live anymore").
    The bank is what a human ruled; the store is what a customer can buy. One
    does not overwrite the other — an offer pointing at a sold-out variant, or
    quoting a price the shop no longer charges, is reported and refused."""
    s = store(brand)
    if not s:
        return [{"level": "blocked", "why": "no store.json — run store.py --write first"}]
    prods = {p["handle"]: p for p in s["products"]}
    out = []
    for r in parse(brand):

        if not r.get("points_at"):
            out.append({"key": r["key"], "level": "unlinked",
                        "why": "names no product on the store, so nothing can check it "
                               "and no asset can link to it"})
            continue
        if r["points_at"] == "catalogue":
            continue
        p = prods.get(r["points_at"])
        if not p:
            out.append({"key": r["key"], "level": "gone",
                        "why": f"points at `{r['points_at']}`, which is not on the store at all"})
            continue
        # A DRAFT blocked for want of a price, where the shop now has one.
        if r["status"] == "draft" and p["available"] and p["price_from"]:
            out.append({"key": r["key"], "level": "draft, but priced",
                        "why": f"held as a draft because no source carried a price — "
                               f"{p['title']} now sells at ${p['price_from']} on the store. "
                               f"A human can promote it."})
        # THE PRICE THE BANK STATES vs THE PRICE THE SHOP CHARGES. This is the
        # check the owner asked for by name: "a price change on the Shopify store
        # would not be shown here in the repo".
        stated = r.get("states_prices") or []
        real = {v["price"] for v in p["variants"]} | {
            v["compare_at"] for v in p["variants"] if v["compare_at"]}
        # a subscription price is a real price too — it is what the customer is
        # charged on the cycle, and the bank quotes it in CTAs
        for v in p["variants"]:
            for sp in p.get("subscriptions") or []:
                try:
                    base = float(v["price"])
                    if sp["value_type"] == "fixed_amount":
                        real.add(f"{base - sp['value'] / 100:.2f}")
                    elif sp["value_type"] == "percentage":
                        real.add(f"{base * (100 - sp['value']) / 100:.2f}")
                except (TypeError, ValueError, KeyError):
                    pass
        ghosts = [x for x in stated if x not in real]
        if ghosts and stated:
            out.append({"key": r["key"], "level": "price drift",
                        "why": f"states ${', $'.join(ghosts)} — {p['title']} is sold at "
                               f"${', $'.join(sorted(real))}"})
    return out


def propose(brand):
    """The offers the STORE supports today, written out for a human to rule on.

    RULED 2026-09-11 (the owner: "let's focus on the store as the first place to
    create offers"). An offer starts as something a customer can actually buy:
    a product that is in stock, at a price the shop charges, at a link that
    resolves, with whatever subscription the shop itself publishes. The human
    then rules the parts a shop cannot know — which lane it speaks to, whether
    it is the paid hero, what window it runs in, and the outcome line in the
    customer's own words.

    This proposes; it never writes to the bank. Promotion is a human act."""
    s = store(brand)
    if not s:
        return []
    ruled = {r["key"]: r for r in parse(brand)}
    out = []
    for pr in s["products"]:
        if not pr["available"]:
            continue
        live = [v for v in pr["variants"] if v["available"]]
        base = min(live, key=lambda v: float(v["price"]))
        key = pr["handle"]
        existing = next((r for r in ruled.values() if r.get("points_at") == key), None)
        out.append({
            "key": (existing or {}).get("key") or key,
            "known": bool(existing),
            "title": pr["title"],
            "price": base["price"],
            "compare_at": base["compare_at"],
            "url": pr["url"],
            "sold_out_variants": [v["title"] for v in pr["variants"] if not v["available"]],
            "subscriptions": pr.get("subscriptions") or [],
            "lane": (existing or {}).get("lane"),
            "status": (existing or {}).get("status"),
        })
    return out


def usage(brand):
    """How many assets point at each offer, and which.

    RULED 2026-09-10 (the owner: "there is no clear way to track how many assets
    are using this specific offer"). Counted off the calendars and the built
    runs rather than declared — a count someone maintains by hand is a count
    that is wrong."""
    used = {r["key"]: {"slots": [], "runs": []} for r in parse(brand)}
    for cal in sorted(HERE.glob("results/calendar-*/slots.json")):
        month = cal.parent.name.replace("calendar-", "")
        rows = json.loads(cal.read_text())
        rows = rows if isinstance(rows, list) else rows.get("slots", [])
        for s in rows:
            o = s.get("offer")
            if o and o in used:
                used[o]["slots"].append(f"{month} {s['id']} ({s.get('date')})")
                for run in HERE.glob(f"results/{s['id']}*"):
                    if run.is_dir() and (run / "design.json").is_file():
                        used[o]["runs"].append(run.name)
    return used


def hero(brand, lane=None):
    """The one front-end offer a lane runs on.

    RULED 2026-09-10 (the owner: "we need to also build static ads from this same
    exact calendar tool… the ads on the front end will mostly be focused on a
    hero offer"). The paid surface and the email surface ask this bank two
    different questions. A static or a video ad points at the HERO — one per
    lane, the proven front-end construction. Email is the surface that varies:
    it may run any usable offer, or none, and most sends run none.

    A lane with no hero is not a gap to fill by picking one — it is a decision
    nobody has made, and it is returned as None so the caller says so."""
    for r in parse(brand):
        if r["status"] != "live" or not r.get("hero"):
            continue
        if lane and r["lane"] and r["lane"] != lane:
            continue
        return r
    return None


def usable(brand, avatar=None, on=None):
    """What may actually be offered — the only question the planner may ask."""
    out = []
    for r in parse(brand):
        if r["status"] != "live":
            continue
        if avatar and r["lane"] and r["lane"] != avatar:
            continue
        if on and r["window"] and not (r["window"][0] <= on <= r["window"][1]):
            continue
        out.append(r)
    return out


def refuse(brand, key, avatar=None, on=None):
    """Why this key may not be used — or None if it may."""
    rows = {r["key"]: r for r in parse(brand)}
    r = rows.get(key)
    if not r:
        near = sorted(rows, key=lambda k: -len(set(k.split("-")) & set(key.split("-"))))
        return (f"`{key}` is not in the offer bank. Real keys: "
                + ", ".join(f"`{k}`" for k in near[:4]))
    if r["status"] == "free":
        return f"`{key}` costs nothing — a free sample is not an offer a send can carry"
    if r["status"] == "draft":
        return f"`{key}` is a DRAFT in the bank — {'; '.join(r['notes']) or 'not usable'}"

    if avatar and r["lane"] and r["lane"] != avatar:
        return f"`{key}` belongs to lane `{r['lane']}`, not `{avatar}` — one lane per offer"
    if on and r["window"] and not (r["window"][0] <= on <= r["window"][1]):
        return (f"`{key}` runs {r['window'][0]} to {r['window'][1]} and this send is "
                f"{on} — its moment has passed")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help="brand folder name under brands/ — there is no default brand")
    ap.add_argument("--avatar", default=None)
    ap.add_argument("--on", default=None, help="a send date, ISO")
    ap.add_argument("--write", action="store_true",
                    help="propose products/offers.json under runs/email-production/<brand>/<label>/")
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    ap.add_argument("--propose", action="store_true",
                    help="what the store supports today, for a human to rule on")
    ap.add_argument("--usage", action="store_true",
                    help="how many assets point at each offer, and which")
    ap.add_argument("--check", action="store_true",
                    help="reconcile the bank against what the store actually sells today")
    ap.add_argument("--hero", action="store_true",
                    help="the front-end offer per lane — what a static or video ad points at")
    a = ap.parse_args()

    rows = parse(a.brand)
    if not rows:
        sys.exit(f"no offer bank for {a.brand}")

    if a.write:
        run = facts_proposal.run_dir(a.brand, a.label)
        f = facts_proposal.write(run, a.brand, "products/offers.json", json.dumps({
            "note": "Generated from offer-bank.md by tools/email-production/offers.py. "
                    "The prose bank is the human's source of truth; this is the queryable "
                    "form the machine reads. Regenerate after editing the bank.",
            "brand": a.brand, "offers": rows}, indent=1) + "\n")
        print(f"-> {f}  ({len(rows)} offers)")
        print(f"proposal -> {facts_proposal.note(run, a.brand)}")
        return

    if a.propose:
        for r in propose(a.brand):
            mark = f"in the bank as `{r['key']}` ({r['status']})" if r["known"] else "NOT IN THE BANK"
            cmp_ = f", was ${r['compare_at']}" if r["compare_at"] else ""
            print(f"  {r['title'][:36]:38} ${r['price']}{cmp_}")
            print(f"      {mark}" + (f" · lane {r['lane']}" if r["lane"] else ""))
            for s_ in r["subscriptions"]:
                print(f"      subscribe {s_['cadence']} — {s_['saves']}")
            print(f"      {r['url']}")
        return

    if a.usage:
        u = usage(a.brand)
        for k, v in sorted(u.items(), key=lambda kv: -len(kv[1]["runs"])):
            print(f"  {k:20} {len(v['runs']):3} asset(s) · {len(v['slots']):2} slot(s)")
            for s in v["slots"]:
                print(f"      {s}")
        return

    if a.check:
        s = store(a.brand)
        print(f"bank vs store — store read {s['read'] if s else 'NEVER'}\n")
        found = reconcile(a.brand)
        for f_ in found:
            print(f"  {f_['level'].upper():16} {f_.get('key', ''):20} {f_['why']}")
        print(f"\n{len(found)} disagreement(s)")
        return

    if a.hero:
        lanes = sorted({r["lane"] for r in rows if r["lane"]})
        for lane in lanes:
            h = hero(a.brand, lane)
            print(f"  {lane:14} " + (f"{h['key']:20} {h['title'][:50]}" if h else
                                     "NO HERO — nobody has named this lane's front-end offer"))
        return

    ok = usable(a.brand, a.avatar, a.on)
    print(f"USABLE" + (f" for {a.avatar}" if a.avatar else "")
          + (f" on {a.on}" if a.on else "") + f" — {len(ok)}")
    for r in ok:
        flag = "" if r["outcome_written"] else "   (price only — its outcome line is unwritten)"
        print(f"  {r['key']:20} {r['lane'] or 'any lane':14} {r['title'][:44]}{flag}")
    print()
    for r in rows:
        if r in ok:
            continue
        why = refuse(a.brand, r["key"], a.avatar, a.on) or "lane mismatch"
        print(f"  REFUSED  {r['key']:18} {why[:96]}")


if __name__ == "__main__":
    main()
