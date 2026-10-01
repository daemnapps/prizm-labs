#!/usr/bin/env python3
"""What is TRUE of a brand's product — read from the brand, never typed here.

    brand_facts.py <brand>                      the judge's product tests for that brand
    brand_facts.py <brand> --prompt <file>      ...for the product a prompt references

The judge used to carry one brand's product geometry as a constant, so every
other brand's ad was judged against the first brand's device (2026-09-20).

Product truth lives with the brand, in `brands/<brand>/element-facts.json` —
the same file `ai-video-production/machine/prompt.py` reads: one
entry per banked element, keyed by its id, with `facts` (what is true of the
object) and `forbids` (what it never does). The judge's product tests are
built from those lines:

  - the product elements the ad's own prompt references (`<<<id>>>`), else
  - the brand's `canonical` product element(s), else
  - nothing brand-specific: one plain test, and a note saying the brand has
    no product facts on file, so the check is only as good as that.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

ELEMENT = re.compile(r"<<<([0-9a-fA-F-]{36})>>>")

# Brand-free. Used when a brand has written no facts about its product yet.
PLAIN_PRODUCT_CHECK = (
    "The product in frame is one coherent, recognisable product and the same "
    "object everywhere it appears. FAIL only if it reads as a different or "
    "invented product: parts that change between appearances, a label that is "
    "another brand's, or an object no customer could identify.")


def facts_file(brand):
    P.need_brand(brand, "the judge's product tests")
    return P.BRANDS / brand / "element-facts.json"


def book(brand):
    try:
        return json.loads(facts_file(brand).read_text()).get("elements", {})
    except (OSError, ValueError):
        return {}


def product_rows(brand, prompt_text=""):
    """The product elements to judge against: the ones the prompt names, else
    the brand's canonical ones. Blocked elements are never the standard."""
    b = book(brand)

    def row(uid):
        r = b.get(uid) or {}
        if r.get("same_as"):
            r = b.get(r["same_as"], r)
        return r

    named = []
    for uid in ELEMENT.findall(prompt_text or ""):
        r = row(uid)
        if r.get("kind") == "product" and not r.get("blocked") and r not in named:
            named.append(r)
    if named:
        return named
    return [r for r in b.values()
            if r.get("kind") == "product" and r.get("canonical") and not r.get("blocked")]


def product_checks(brand, prompt_text=""):
    """The judge's product tests for this brand — (tests, note).

    One test per product element: what is true of it, and what it never does.
    FAIL only when it would read as a different product — the narrowing ruled
    2026-09-05 stands; only the source of the geometry changed."""
    rows = [r for r in product_rows(brand, prompt_text) if r.get("facts") or r.get("forbids")]
    if not rows:
        return [PLAIN_PRODUCT_CHECK], (
            f"{brand} has no product facts in element-facts.json — the product "
            f"test is the plain one")
    tests = []
    for r in rows:
        t = ("The product is recognisably ours. What is true of it: "
             + " ".join(r.get("facts") or []))
        if r.get("forbids"):
            t += " What it never does: " + " ".join(r["forbids"])
        t += (" FAIL only if it would read as a different product, or if the "
              "picture shows something listed under what it never does. A "
              "partly hidden or foreshortened product PASSES.")
        tests.append(t)
    return tests, None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    text = ""
    if "--prompt" in sys.argv:
        text = Path(sys.argv[sys.argv.index("--prompt") + 1]).read_text()
    tests, note = product_checks(sys.argv[1], text)
    for i, t in enumerate(tests, 1):
        print(f"{i}. {t}\n")
    if note:
        print(f"! {note}")
