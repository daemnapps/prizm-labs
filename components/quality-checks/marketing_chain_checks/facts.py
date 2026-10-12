"""What a brand's files and a person's rulings say is true — ONE read, for every
checker (HE-3 (shared brand facts), 2026-10-02).

    from marketing_chain_checks.facts import brand_facts
    brand_facts(brand, root=None) -> {"product_facts": str, "products": [title, ...],
                                      "verified_facts": [...], "not_ours": [...]}

A fact the ops lead cleared once (HE-1 (fact rulings)) was known to the email
writer's gate and to no other check, so the next checker flagged it again at
the source. Every checker now reads the same four things from here:

    product_facts   every LIVE product's file, then the brand's position, story,
                    operations and offer bank — the text email-production's
                    stage 8c has read since 2026-09-21, byte for byte
    products        the live product titles (products/heroes.json `sellable`)
    verified_facts  rulings.verified_facts — standing true + fill, never a price
    not_ours        rulings.not_ours — what the brand does not have

PRICES ARE OFFER-BANK-ONLY (Operator B, 2026-10-01, "1 for prices"): nothing
here adds, clears or changes a price. A ruling whose fact carries one is
dropped by `rulings.verified_facts`, and a wrong price is fixed in the offer
bank.

`root` is the workspace (default: brandpath's `repo()`); the brand's files
resolve through brandpath, so a folder rename moves no code. No brand is named
in this file (workspace rule 7).
"""
import json
import sys
from pathlib import Path

from . import rulings as R


def _component(name):
    """A sibling component, found by walking up from this file — never counted."""
    for d in Path(__file__).resolve().parents:
        cand = d / "components" / name
        if cand.is_dir():
            return cand
    raise ImportError(f"components/{name} not found upward of {__file__}")


if "brandpath" not in sys.modules:
    _BP_HOME = str(_component("brandpath"))
    if _BP_HOME not in sys.path:
        sys.path.append(_BP_HOME)            # appended, never ahead of the caller's own modules
import brandpath as BP                       # noqa: E402

# The brand's own files that state what is true beyond one product's file, in
# the order stage 8c is handed them: (folder key, file, the label it carries).
# THE MECHANISM IS RULED IN position.md, NOT IN A PRODUCT FILE (2026-09-21):
# four sends were held for lines the position file states as ruled.
BRAND_FILES = (("brand-identity", "position.md", "The brand's ruled position and mechanism"),
               ("brand-identity", "story.md", "The brand's story, and who tells it"),
               ("operations", "operations.md", "How this brand ships and stocks"),
               ("products", "offer-bank.md", "What may be sold, and the guarantee"))
NO_FILES = "(no product files on file for this brand)"


def _json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def _sellable(brand, brands):
    """The live catalogue rows. A product that is not live is never read — the
    catalogue decides what is read, so a draft's file is never opened."""
    return _json(BP.brand_file(brand, "products", "heroes.json", root=brands), {}).get("sellable", [])


def product_facts(brand, root=None):
    """The facts of every live product, then the brand files — one text."""
    brands = Path(root if root is not None else BP.repo()) / "brands"
    out = []
    for s in _sellable(brand, brands):
        # both product shapes: products/<slug>.md and products/<slug>/product.md
        f = BP.brand_path(brand, "products", f"{s['handle']}.md", root=brands)
        if not f.is_file():
            f = BP.brand_path(brand, "products", s["handle"], "product.md", root=brands)
        if f.is_file():
            out.append(f"----- {s['title']} (`{s['handle']}`) -----\n" + f.read_text().strip())
    for key, name, title in BRAND_FILES:
        f = BP.brand_file(brand, key, name, root=brands)
        if f.is_file():
            out.append(f"----- {title} -----\n" + f.read_text().strip())
    return "\n\n".join(out) if out else NO_FILES


def brand_facts(brand, root=None):
    """{product_facts, products, verified_facts, not_ours} for one brand, read
    from `root` (the workspace) — the brand's files and that root's rulings."""
    ws = Path(root) if root is not None else BP.repo()
    titles = [str(s.get("title") or "").strip() for s in _sellable(brand, ws / "brands")
              if isinstance(s, dict)]
    return {"product_facts": product_facts(brand, ws),
            "products": [t for t in titles if t],
            "verified_facts": R.verified_facts(ws, brand),
            "not_ours": R.not_ours(ws, brand)}
