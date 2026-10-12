#!/usr/bin/env python3
"""One profile per product, built from the brand's own live catalogue.

    python3 calendar/products.py --brand brand-b [--refresh]

A PRODUCT and an OFFER are different things (the owner, 2026-08-27). The product is
what the thing IS — mechanism, ingredients, features, benefits, specs. The
offer is the commercial construction around it. This writes the product half.

Source is the storefront's own product feed, which is the only place the real
ingredient lists and specifications exist. Everything written is from that
feed; nothing is inferred. What the feed does not say is left OPEN, because a
plausible ingredient claim is the most expensive thing this system can produce.

    --refresh   re-pull the feed. Otherwise the cached copy is used, so a
                rebuild is reproducible and does not depend on the site.

Proposes products/<handle>.md, products/README.md (and a refreshed
email-sms/catalogue.json) under runs/email-production/<brand>/facts-<YYYY-MM-DD>/
(K2 (brands write wall)); a products/*.md this build no longer makes is listed
as a removal. A person folds the proposal into brands/.
"""
import argparse
import html as H
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import WORKSPACE  # noqa: E402
import facts_proposal  # noqa: E402
BRAND_ROOT = WORKSPACE / "brands"

HERE = Path(__file__).resolve().parent


def feed_for(brand):
    """The store's public product feed, from brands/<brand>/email-sms/machine.json
    ("store_feed"). None when the brand has no public feed — the catalogue
    is then built from products/<slug>/product.md files instead."""
    f = BRAND_ROOT / brand / "email-sms" / "machine.json"
    if f.is_file():
        try:
            return json.loads(f.read_text()).get("store_feed")
        except Exception:
            return None
    return None

# Ingredient and active terms to surface as a list. Matched against the
# description, never invented — a term not in the feed does not appear.
KNOWN = ["Gold", "Organic Charcoal", "Charcoal", "Aloe Vera", "Peppermint",
         "Vitamin C", "Vitamin E", "Witch Hazel", "Willow Bark", "Salicylic",
         "Niacinamide", "Hyaluronic", "Tea Tree", "MAKTREK", "CFU",
         "Microfiber", "Glycolic", "Retinol", "Shea", "Jojoba"]

SKIP = {"gift-card"}


def text(h):
    h = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr)>", "\n", h or "")
    h = re.sub(r"<[^>]+>", " ", h)
    h = H.unescape(h)
    h = re.sub(r"[ \t\xa0]+", " ", h)
    return "\n".join(l.strip() for l in h.splitlines() if l.strip())


def money(v):
    try:
        return f"${float(v):,.2f}".replace(".00", "")
    except (TypeError, ValueError):
        return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    args = ap.parse_args()
    run = facts_proposal.run_dir(args.brand, args.label)

    cache = BRAND_ROOT / args.brand / "email-sms" / "catalogue.json"
    if args.refresh or not cache.is_file():
        url = feed_for(args.brand)
        if not url:
            sys.exit(f"no catalogue feed known for {args.brand}")
        r = subprocess.run(["curl", "-sS", "-A", "Mozilla/5.0", url],
                           capture_output=True, text=True)
        if r.returncode or not r.stdout.strip().startswith("{"):
            sys.exit(f"could not pull the catalogue: {r.stderr[:200]}")
        facts_proposal.write(run, args.brand, "email-sms/catalogue.json", r.stdout)
        print(f"pulled {url}")
        feed = json.loads(r.stdout)["products"]
    else:
        feed = json.loads(cache.read_text())["products"]

    # every profile in brands/ today: one this build does not make again is
    # proposed for removal, never deleted here
    had = sorted(f.name for f in (BRAND_ROOT / args.brand / "products").glob("*.md"))

    written = []
    for p in feed:
        if p["handle"] in SKIP:
            continue
        body = text(p.get("body_html"))
        lines = [l for l in body.splitlines() if l]
        headline = lines[0] if lines else ""
        # the feed's shape: a headline, then prose, then a bullet run
        prose, bullets = [], []
        for l in lines[1:]:
            (bullets if (len(l) < 90 and not l.endswith(".")) else prose).append(l)
        found = [k for k in KNOWN if re.search(re.escape(k), body, re.I)]
        # drop terms wholly contained in a longer one already matched:
        # "Organic Charcoal" and "Charcoal" are one ingredient, not two
        found = [k for k in found
                 if not any(k != o and k.lower() in o.lower() for o in found)]
        vs = p.get("variants", [])
        opts = [o["name"] for o in p.get("options", []) if o.get("name") != "Title"]
        warn = next((l for l in lines if l.lower().startswith("warning")), "")
        if warn:
            bullets = [b for b in bullets if b != warn]
            prose = [x for x in prose if x != warn]

        L = [f"# {p['title']}", "",
             f"`{p['handle']}` · live on the storefront"
             + (f" · {p['product_type']}" if p.get("product_type") else ""), "",
             "**Built from the brand's own product feed.** Every line below is from",
             "that feed. What it does not say is left OPEN — nothing here is inferred.",
             "", "## What it is", ""]
        L += [f"**{headline}**", ""] if headline else []
        L += prose or ["> OPEN — the feed carries no description for this."]
        L += ["", "## What it does", ""]
        L += [f"- {b}" for b in bullets] or ["> OPEN — no feature or benefit lines in the feed."]
        L += ["", "## Ingredients and components", ""]
        if found:
            L += [f"- {k}" for k in found]
            L += ["", "> Extracted from the description above — this is what the feed",
                  "> names, not a full INCI list. The complete formulation is OPEN."]
        else:
            L += ["> OPEN — the feed names no ingredients for this product.",
                  "> For a device or accessory that is expected; for a formulation it is a gap."]
        if warn:
            L += ["", "## Safety", "", warn]
        L += ["", "## How it is sold", "",
              "The commercial terms are the OFFER's business, not the product's. These",
              "are only the sizes and prices the storefront lists.", ""]
        L += [f"- {v.get('title', '—')} — {money(v.get('price'))}"
              + (f" (was {money(v.get('compare_at_price'))})" if v.get("compare_at_price") else "")
              for v in vs] or ["- OPEN"]
        if opts:
            L += ["", f"Sold by: {', '.join(opts)}."]
        L += ["", "## Open", "",
              "- The mechanism in plain terms — *why* the formulation does what it claims",
              "- The full ingredient list, and which of them may be claimed about",
              "- Who it is for, and who it is not for",
              "- What it replaces in someone's routine", ""]
        facts_proposal.write(run, args.brand, f"products/{p['handle']}.md", "\n".join(L))
        written.append((p["handle"], p["title"], len(found), len(bullets), len(vs)))

    live = {p["handle"] for p in feed}
    gone = ["FADE™", "MEND™", "VAULT™", "The Revival Set"]
    idx = ["# Products", "",
           "One profile per product, built from the storefront's own feed.", "",
           "**A product is not an offer.** The product is what the thing is —",
           "mechanism, ingredients, features, specs. The offer is the commercial",
           "construction around it. One product carries many offers.", "",
           "| Product | Ingredients named | Feature lines | Sizes |", "|---|---|---|---|"]
    for h, t, f, b, v in written:
        idx.append(f"| [{t}]({h}.md) | {f} | {b} | {v} |")
    idx += ["", "## Named elsewhere, not in the live catalogue", "",
            "These appear in the offer bank or in sent emails but are **not on the",
            "storefront**. Either retired or unlisted — worth knowing before an email",
            "points at one.", ""]
    idx += [f"- {g}" for g in gone]
    facts_proposal.write(run, args.brand, "products/README.md", "\n".join(idx) + "\n")
    made = {f"{h}.md" for h, *_ in written} | {"README.md"}
    for name in had:
        if name not in made:
            facts_proposal.remove(run, args.brand, f"products/{name}")

    for h, t, f, b, v in written:
        print(f"  {t[:38]:40} {f:2} ingredients · {b:2} features · {v} sizes")
    print(f"\n{len(written)} profiles proposed")
    print(f"proposal -> {facts_proposal.note(run, args.brand)}")


if __name__ == "__main__":
    main()
