#!/usr/bin/env python3
"""The offer bank, as rows the machine can actually query.

    python3 offers.py --brand brand_a                 # what may run, and what may not
    python3 offers.py --brand brand_a --on 2026-09-20 # what may run on a given day
    python3 offers.py --brand brand_a --write         # propose products/offers.json under runs/

RULED 2026-09-10 (owner: "so there's an offer bank issue then…"). The bank is a
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

from paths import HERE, WORKSPACE, calendar_tool
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
    human rules. Under the "Ruled by a human" divider the prose is for people —
    except a section the marketing calendar's reader counts as an offer (a
    priced `### key — Name`: a funnel offer, a dated promotion, 2026-11-03).
    Those are read through that reader (marketing-calendar library surface,
    `brandrecord.render_offers`), so the calendar that assigns an offer and
    this writer that carries it can never disagree about what is one.
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
    have = {r["key"] for r in rows}
    full = f.read_text()
    for key in ruled_offers(brand):
        if key in have:
            continue
        body = re.search(rf"^###\s+{re.escape(key)}\b(.*?)(?=^#{{1,3}}\s|\Z)", full, re.M | re.S)
        sect = body.group(1) if body else ""
        title = sect.splitlines()[0].strip(" —-") if sect else key
        rows.append({"key": key, "title": title, "status": "live", "lane": None, "hero": None,
                     "window": None, "url": None, "points_at": None, "price": None, "subs": [],
                     "outcome_written": True, "ruled": True,
                     "states_prices": sorted(set(re.findall(r"\$([0-9]+(?:\.[0-9]{2})?)", sect))),
                     "notes": ["ruled by a human, below the divider"]})
    return rows


def guarantee_lines(text):
    """The bank's guarantee wording, word for word: every quoted line (`> …`) in a section whose key or parent
    section names a guarantee. -> [(what it covers, the line)]."""
    out, parent, on, label = [], "", False, ""
    for ln in text.splitlines():
        if ln.startswith("# "):
            on = False
        elif ln.startswith("## "):
            parent, on, label = ln[3:].strip().lower(), "guarantee" in ln.lower().split("—")[0], ln[3:].strip()
        elif ln.startswith("### "):
            head = ln[4:].strip()
            on = "guarantee" in head.lower().split("—")[0] or "guarantee" in parent.split("—")[0]
            label = head
        elif on and ln.startswith(">"):
            line = ln.lstrip("> ").strip()
            if out and out[-1][0] == label and not out[-1][1].endswith(('."', '.', '"')):
                out[-1] = (label, out[-1][1] + " " + line)
            else:
                out.append((label, line))
    return out


def writer_rules(brand, offer, also=(), kind=None, deadline=None, order_by=None):
    """What every writing step is held to, from the record, so the mistake is never written (2026-11-04):
    the guarantee word for word, the only deadline the plan gives, the send's own type, and no code where the bank
    says there is none. Handed to every stage inside {offer_rule}."""
    f = WORKSPACE / "brands" / brand / "products" / "offer-bank.md"
    text = f.read_text() if f.is_file() else ""
    out = []
    lines = guarantee_lines(text)
    if lines:
        out.append("**The guarantee, if it appears, is one of these lines, word for word:**\n"
                   + "\n".join(f"- ({label.split('—')[-1].strip()}) {line}" for label, line in lines)
                   + "\nNothing else stands in for it: no \"zero risk\", no \"risk-free\", no \"no risk\", no other "
                     "length of time and no other promise.")
    if offer and offer != "none" and deadline:
        s = f"**The only deadline this send may state is {deadline}**, the last day in the plan."
        if order_by:
            s += f" Order by {order_by} to arrive in time; that is the brand's own date."
        out.append(s + " No clock time (midnight, tonight at …), no \"hours left\", no countdown, and no other date: "
                       "the record gives a day, so the send gives a day.")
    else:
        out.append("**This send states no deadline.** The plan gives it none, so it names no last day, no clock time "
                   "and no countdown.")
    if kind:
        what = ""
        try:
            types = json.loads((WORKSPACE / "brands" / brand / "email-sms" / "email-types.json").read_text())["types"]
            what = next((t.get("what") or "" for t in types if t.get("key") == kind), "")
        except (OSError, ValueError, KeyError):
            pass
        out.append(f"**This send is a `{kind}`**" + (f" ({what.rstrip('.')})" if what else "") + ", and it stays one. The "
                   "source email gives it a shape, never a subject: whatever the source sold (a subscription, another "
                   "product, another offer) does not travel. A subscription is named only when the offer above is one.")
    sections = [_section(text, k) for k in ([offer] if offer and offer != "none" else []) + list(also or [])]
    if re.search(r"\bno code\b", "\n".join(sections), re.I) or re.search(r"\bno code necessary\b", text, re.I):
        out.append("**There is no code.** Never mention one, in a subject line or anywhere else, and never a discount "
                   "that is the reader's: not waiting, saved, unused or on an account. The price is simply on the page.")
    for sec in sections:
        cond = saving_condition(sec)
        if cond:
            line = re.search(r"^- Saving:\s*(.*)$", sec, re.M).group(1).replace("**", "")
            out.append(f"**{offer_name(sec)}: a saving is stated only with its condition.** {line} Any line that states "
                       f"this saving, or the subscribed price, says it's {cond} in that same sentence.")
    if sections:
        out.append("**Prices and was-prices come only from the offer above.** A product file can carry an older was-price; "
                   "it is never written.")
    out.append(NO_INVENTION)
    return "\n\n".join(out)


# LD-104 (no invented facts), 2026-11-04: in the Nov 3-4 run 10 of 13 emails were held or fixed for specifics no
# file holds — a repeat rate turned into "N of our M customers bought again", a review count rounded up, a dose, a
# span of hours, a store credit, a product version, a stock state (runs/email-production/notes/
# 2026-11-04-november-email-audit.md, fact 3). The same words for every brand: what is true comes from the files.
NO_INVENTION = (
    "**Nothing is invented.** Every number, timeframe, guarantee term and named quote in this send is one the brand's "
    "files handed to this step hold (the product file, the offer bank, the brand's story, its customer language and "
    "reviews, the week's sources). Anything not in the brand's files is not written, however likely it sounds.\n"
    "- A number is any count, amount, percentage, dose or size, in digits or written in words (\"three pumps\" is a "
    "number). A count of customers, reviews, buyers or years is stated exactly as the file states it: never rounded "
    "up, never worked out from a rate (a repeat rate never becomes \"N of our M customers\"), never a new one.\n"
    "- A timeframe is any span or moment of time (\"in two weeks\", \"the twelve hours after\", \"for 30 days\"), "
    "other than the deadline this send is given above.\n"
    "- A guarantee term is any refund, return, store credit, warranty or promise. It appears only word for word from "
    "the guarantee lines in this section; with none listed, the send promises none.\n"
    "- A named quote is any words put in a person's mouth (a customer, the founder, an expert, \"a verified buyer\"). "
    "It is quoted word for word from a file and credited as that file credits it: a forum post or a video comment is "
    "never a customer or a verified buyer, and no line goes under a real customer's name or picture that they did not "
    "say.\n"
    "- The same holds for a product's name, version or stock: only as the catalogue gives it.\n"
    "If a line needs a fact the files do not hold, write the sentence without it: a true general line beats an "
    "invented specific. Only when the email cannot stand without it, write [UNFILLED: what is missing] so a person "
    "fills it. Never guess.")


def offer_name(section):
    m = re.match(r"#+\s+\S+\s+—\s+(.+)", section or "")
    return re.sub(r"[™®]", "", m.group(1)).strip() if m else ""


def saving_condition(section):
    """The condition the bank puts on stating an offer's saving (`- Saving: … Copy stating the saving says it's <condition>.`),
    or None when the bank marks none."""
    m = re.search(r"^- Saving:.*?copy stating the saving says it's ([^.\n]+)\.", section or "", re.M | re.I)
    return m.group(1).strip() if m else None


def saving_problems(text, section, alone=True):
    """Every sentence of `text` that states this offer's saving, or its subscribed price, without the bank's condition.
    `alone`: the send carries only this offer, so a saving that names no product is this one's. -> [problems]"""
    cond = saving_condition(section)
    if not cond:
        return []
    amounts = lambda pat: {a for ln in re.findall(pat, section, re.M) for a in re.findall(r"\$([0-9]+(?:\.[0-9]{1,2})?)", ln)}
    gated = (amounts(r"^- Subscribed:.*$") | amounts(r"^- Saving:.*$")) - amounts(r"^- Price:.*$")
    word = cond.split()[-1][:6].lower()                   # "with the subscription" reads as any form of subscribe
    name = offer_name(section).lower().replace("the ", "", 1)
    out = []
    for s in re.split(r"(?<=[.!?])\s+|\n+", text or ""):
        low = s.lower()
        states = re.search(r"\b(you save|savings?|save (big|on|more)|sav(e|es|ing)\b.*[$%]|[$%]\S*\s*\bsav(e|es|ing)\b|\d%? off\b)", low)
        price = gated & set(re.findall(r"\$([0-9]+(?:\.[0-9]{1,2})?)", s))
        if word not in low and (price or (states and (alone or (name and name in low)))):
            out.append(f"states a saving or subscribed price without “{cond}”, as the bank requires: “{s.strip()}”")
    return out


def bundle_as_product(brand, key):
    """What the writer knows of a product with no product file yet (a bundle sold before its file exists, 2026-11-04):
    its own bank section, then the product file of each thing its `Holds:` line names, matched on a product folder's
    or file's own name. None when the bank has no section for it: nothing is invented."""
    products = WORKSPACE / "brands" / brand / "products"
    bank = products / "offer-bank.md"
    sec = _section(bank.read_text(), key).strip() if bank.is_file() else ""
    if not sec:
        return None
    holds = next((ln.split(":", 1)[1] for ln in sec.splitlines() if re.match(r"\s*-\s*Holds:", ln)), "")
    said = re.sub(r"[™®]", "", holds).lower()
    parts = [sec]
    for d in sorted(products.iterdir()):
        f = d / "product.md" if d.is_dir() else d
        name = (d.name if d.is_dir() else d.stem).replace("-", " ").lower()
        if f.is_file() and f.suffix == ".md" and name in said:
            parts.append(f"## What it holds: {name}\n\n" + f.read_text().strip())
    return "\n\n".join(parts)


def _section(text, key):
    m = re.search(rf"^#{{2,3}}\s+{re.escape(key)}\b.*?(?=^#{{1,3}}\s|\Z)", text, re.M | re.S)
    return m.group(0) if m else ""


def ruled_offers(brand):
    """The keys the calendar's reader counts as offers in the bank's human-ruled half."""
    cal = calendar_tool("machine")
    if not cal:
        return []
    if str(cal) not in sys.path:
        sys.path.append(str(cal))                     # appended, never ahead of this folder
    import brandrecord
    root = WORKSPACE / "brands" / brand
    roster = []
    try:
        roster = [a["key"] for a in brandrecord.L.avatars(brand, WORKSPACE)] if brandrecord.L else []
    except Exception:                                 # noqa: BLE001  no roster is a brand, not an error
        roster = []
    text = (root / "products" / "offer-bank.md").read_text()
    if brandrecord.bank_is_per_avatar(text, roster):
        return []                                     # a per-avatar bank keeps no ruled half
    MARK = "# Ruled by a human"
    ruled = text.split(MARK, 1)[1] if MARK in text else ""
    heads = {ln[4:].strip().split(" ")[0].strip("`") for ln in ruled.splitlines() if ln.startswith("### ")}
    return [ln.split("`")[1] for ln in brandrecord.render_offers(root, roster).splitlines()
            if ln.startswith("- OFFER `") and ln.split("`")[1] in heads]


def store(brand):
    f = WORKSPACE / "brands" / brand / "products" / "store.json"
    return json.loads(f.read_text()) if f.is_file() else None


def reconcile(brand):
    """Where the bank and the shop disagree ABOUT THE OFFER ITSELF.

    Stock is deliberately NOT checked (owner, 2026-09-11: "do not worry about
    what's sold out and what's not, that doesn't matter right now — we are just
    focusing on the offer and its contents"). What is checked is what the offer
    claims: its price, its link, and whether it points at anything real.

    RULED 2026-09-10 (owner: "a price change on the Shopify store would not be
    shown here in the repo… the FLEX + Vitals system isn't even live anymore").
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
        # check owner asked for by name: "a price change on the Shopify store
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

    RULED 2026-09-11 (owner: "let's focus on the store as the first place to
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

    RULED 2026-09-10 (owner: "there is no clear way to track how many assets
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

    RULED 2026-09-10 (owner: "we need to also build static ads from this same
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
            "note": "Generated from offer-bank.md by components/email-production/offers.py. "
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
