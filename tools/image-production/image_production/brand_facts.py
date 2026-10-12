"""What is TRUE of a brand's product — read from the brand, never typed here.

Lifted from `tools/image-production/static/tools/brand_facts.py`, unchanged in
logic. The judge used to carry one brand's product geometry as a constant, so
every other brand's picture was judged against the first brand's device
(2026-09-20).

Product truth lives with the brand, in `brands/<brand>/ai-elements/element-facts.json`:
one entry per banked element, keyed by its id, with `facts` (what is true of
the object) and `forbids` (what it never does). The judge's product tests are
built from those lines:

  - the product elements the picture's own prompt references (`<<<id>>>`), else
  - the product element the request NAMES (matched by name or key), else
  - the brand's `canonical` product element(s), else
  - nothing brand-specific: one plain test, and a note saying the brand has no
    product facts on file, so the check is only as good as that.
"""
import json
import re

from . import paths as P

ELEMENT = re.compile(r"<<<([0-9a-fA-F-]{36})>>>")

# Brand-free. Used when a brand has written no facts about its product yet.
PLAIN_PRODUCT_CHECK = (
    "The product in frame is one coherent, recognisable product and the same "
    "object everywhere it appears. FAIL only if it reads as a different or "
    "invented product: parts that change between appearances, a label that is "
    "another brand's, or an object no customer could identify.")


def facts_file(brand):
    P.need_brand(brand, "the judge's product tests")
    return P.brand(brand)["element_facts"]


def book(brand):
    try:
        return json.loads(facts_file(brand).read_text()).get("elements", {})
    except (OSError, ValueError):
        return {}


def _row(b, uid):
    r = b.get(uid) or {}
    if r.get("same_as"):
        r = b.get(r["same_as"], r)
    return r


def product_rows(brand, prompt_text="", product=None):
    """The product elements to judge against: the ones the prompt names, else
    the one the request named, else the brand's canonical ones. Blocked
    elements are never the standard."""
    b = book(brand)

    named = []
    for uid in ELEMENT.findall(prompt_text or ""):
        r = _row(b, uid)
        if r.get("kind") == "product" and not r.get("blocked") and r not in named:
            named.append(r)
    if named:
        return named

    if product:
        want = str(product).replace("_", "-").lower()
        live = [r for r in b.values()
                if r.get("kind") == "product" and not r.get("blocked")]
        hit = [r for r in live
               if want and (want in str(r.get("name") or "").replace("_", "-").lower()
                            or str(r.get("name") or "").replace("_", "-").lower() in want)]
        if hit:
            return hit

        # A SET IS ITS MEMBERS. The named product may be a set with no element
        # row of its own — the brand keeps rows for the three things inside it.
        # Judging that picture against the brand's CANONICAL product's geometry
        # is how a set of three bottles got failed for not being a teardrop pod
        # (2026-09-21), so the canonical is never the fallback for a product
        # that was named: a wrong test is worse than a plain one.
        members = _set_members(brand, product, live)
        if members:
            return members
        return []

    return [r for r in b.values()
            if r.get("kind") == "product" and r.get("canonical") and not r.get("blocked")]


def _set_members(brand, product, live):
    """The element rows for the products a named set is made of, read from the
    set's own file in the brand — never a list typed here."""
    f = P.brand(brand)["root"] / "products" / f"{str(product).replace('_', '-')}.md"
    if not f.is_file():
        return []
    text = f.read_text().lower()
    out = []
    for r in live:
        stem = str(r.get("name") or "").split("-")[0].strip().lower()
        if len(stem) > 2 and stem in text and r not in out:
            out.append(r)
    return out


def product_checks(brand, prompt_text="", product=None):
    """The judge's product tests for this brand — (tests, note).

    One test per product element: what is true of it, and what it never does.
    FAIL only when it would read as a different product — the narrowing ruled
    2026-09-05 stands; only the source of the geometry changed."""
    rows = [r for r in product_rows(brand, prompt_text, product)
            if r.get("facts") or r.get("forbids")]
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


def facts_for_prompt(brand, product=None):
    """The same truth, said forwards rather than as a test — what the PROMPT
    is told about the product. The judge and the prompt read one file, so a
    picture is never asked for one thing and judged against another (the rule
    `prompt.py`/`judge.py` already share for the result budget)."""
    rows = [r for r in product_rows(brand, "", product) if r.get("facts")]
    if not rows:
        return ""
    out = []
    for r in rows:
        line = " ".join(r.get("facts") or [])
        if r.get("forbids"):
            line += " It never: " + " ".join(r["forbids"])
        out.append(line)
    return " ".join(out)
