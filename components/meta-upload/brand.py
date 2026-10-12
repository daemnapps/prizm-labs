#!/usr/bin/env python3
"""Which brand a drop belongs to, and every brand-specific fact it needs.

Nothing in this folder names a brand. Workspace rule 7: brand context enters
only from `brands/<brand>/`, never from the tool. So every tool here takes
`--brand <name>` and reads one file:

    brands/<brand>/meta/account.json

That file holds the brand's Meta facts (which ad account, Page, pixel, IG
account) and points at the four inputs the builder reads. Adding a second
brand is writing that file, not editing any code here.

    from brand import Brand
    b = Brand("<brand>")
    b.account_id, b.page_id, b.pixel_id
    b.pictures, b.copy, b.pages, b.roster     # resolved, absolute
    b.pretty("forty-year-shaver")             # the brand's own spelling

Paths in the file are relative to the repo root, so they can point inside
`brands/<brand>/` or into a lab folder while the production line still lives
there. A missing optional input is `None`, not a crash — brands are at
different stages and the builder says what it could not find.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BRANDS = REPO / "brands"

# What every account.json must carry. A brand whose file is missing one of
# these is caught here, with the key named, rather than three steps later as
# a KeyError inside the builder.
# Every brand goes in by bulk import, and the sheet needs only the Page (its
# `Link Object ID` column) plus the naming and the inputs. `account_id` and
# `pixel_id` are still wanted — the first to open the right Ads Manager, the
# second to set on the ad sets in one bulk edit — but a brand is usable
# before they are known, so they are checked rather than demanded.
REQUIRED = ("page_id", "campaign", "inputs")
WANTED = ("account_id", "pixel_id")

# Optional inputs, and whether the builder can proceed without them.
INPUTS = {
    "pictures": True,     # required — there is no drop without pictures
    "copy":     True,     # required — a picture never ships with borrowed words
    "pages":    True,     # required — an ad needs somewhere to go
    "roster":   False,    # optional — maps a person to their sub-avatar
    "adsets":   False,    # optional — per-sub-avatar notes and age bands
    "offers":   False,    # optional — the expired-offer gate
}


def available():
    """Every brand with a Meta account file. `_TEMPLATE` is not a brand."""
    return sorted(p.parent.parent.name for p in BRANDS.glob("*/meta/account.json")
                  if not p.parent.parent.name.startswith("_"))


class Brand:
    def __init__(self, name):
        self.name = name
        self.file = BRANDS / name / "meta" / "account.json"
        if not self.file.is_file():
            have = ", ".join(available()) or "none yet"
            raise SystemExit(
                f"no Meta account file for '{name}' — expected {self.file}\n"
                f"brands set up for Meta: {have}\n"
                f"Copy an existing one and change the ids; see RUNBOOK.md "
                f"'Adding a brand'.")
        self.d = json.loads(self.file.read_text())
        missing = [k for k in REQUIRED if not self.d.get(k)]
        if missing:
            raise SystemExit(f"{self.file} is missing: {', '.join(missing)}")
        self.thin = [k for k in WANTED if not self.d.get(k)]

    # -- the account ------------------------------------------------------
    @property
    def account_id(self): return str(self.d.get("account_id") or "")
    @property
    def page_id(self): return str(self.d["page_id"])
    @property
    def pixel_id(self): return str(self.d.get("pixel_id") or "")
    @property
    def instagram_id(self):
        v = self.d.get("instagram_id")
        return str(v) if v else None
    @property
    def token_key(self): return self.d.get("token_key", "PRIZM_META_TOKEN")

    # -- how the drop is shaped -------------------------------------------
    @property
    def campaign(self): return self.d["campaign"]      # market / product / funnel
    @property
    def display_link(self): return self.d.get("display_link", "")
    @property
    def cta(self): return self.d.get("call_to_action", "SHOP_NOW")
    @property
    def creative_type(self): return self.d.get("creative_type", "Link Page Post Ad")
    @property
    def objective(self): return self.d.get("objective", "Outcome Sales")
    @property
    def optimization_goal(self): return self.d.get("optimization_goal", "OFFSITE_CONVERSIONS")
    @property
    def conversion_event(self): return self.d.get("conversion_event", "PURCHASE")
    @property
    def daily_budget(self): return self.d.get("daily_budget", 100)
    @property
    def countries(self): return self.d.get("countries", ["US"])
    @property
    def age(self): return self.d.get("age", [18, 65])
    @property
    def platforms(self): return self.d.get("publisher_platforms", ["facebook", "instagram"])

    # -- where its inputs live --------------------------------------------
    def path(self, key):
        """An input path, resolved from the repo root. None if not declared."""
        rel = (self.d.get("inputs") or {}).get(key)
        if not rel:
            if INPUTS.get(key):
                raise SystemExit(
                    f"{self.file}: inputs.{key} is required and not set")
            return None
        p = REPO / rel
        if not p.exists() and INPUTS.get(key):
            raise SystemExit(f"{self.file}: inputs.{key} points at {p}, which does not exist")
        return p

    @property
    def pictures(self): return self.path("pictures")
    @property
    def copy(self): return self.path("copy")
    @property
    def pages(self): return self.path("pages")
    @property
    def roster(self): return self.path("roster")
    @property
    def adsets(self): return self.path("adsets")
    @property
    def offers(self): return self.path("offers")

    # -- how this brand names things --------------------------------------
    @property
    def naming(self):
        """The brand's own name templates, defaulting to naming.DEFAULT.

        Read off the live account, never imposed. Two real shapes so far:
        `US | WIDGET™ | ICON | Avatar One` and `cbo_us_purchase_body-scrub`.
        """
        import naming as _n
        d = dict(_n.DEFAULT)
        d.update(self.d.get("naming") or {})
        return d

    # -- how this brand spells its own slugs ------------------------------
    def pretty(self, slug):
        """Title Case for Ads Manager, using the brand's own spellings.

        Slugs are kebab-case everywhere they are stored and Title Case
        everywhere the owner reads them. A brand overrides only the ones a naive
        capitalise gets wrong — `el-jefe` -> `El Jefe`, `avatarone` ->
        `Avatar One`.
        """
        spelling = self.d.get("spelling") or {}
        return spelling.get(slug) or " ".join(
            w.capitalize() for w in str(slug).split("-"))

    def __repr__(self):
        return f"<Brand {self.name} · act_{self.account_id}>"


if __name__ == "__main__":
    import sys
    names = sys.argv[1:] or available()
    if not names:
        print("no brand has a Meta account file yet")
    for n in names:
        b = Brand(n)
        print(f"{b}\n   page {b.page_id} · pixel {b.pixel_id} · ig {b.instagram_id}")
        print(f"   campaign {b.campaign} · {b.cta} · ${b.daily_budget}/day")
        for k in INPUTS:
            try:
                p = b.path(k)
            except SystemExit as e:
                print(f"   TODO {k:9} {e}")
                continue
            mark = "ok  " if p and p.exists() else ("--  " if p is None else "GONE")
            print(f"   {mark} {k:9} {p.relative_to(REPO) if p else 'not set'}")
        for k in b.thin:
            print(f"   TODO {k} not set — needed to open Ads Manager / set the pixel")
        for line in b.d.get("_todo") or []:
            print(f"   TODO {line}")
