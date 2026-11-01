#!/usr/bin/env python3
"""
rights.py — may this footage be used? Read from the brand's creator usage-rights register.

    python3 machine/rights.py --brand <brand> "Shared Assets/brands/<brand>/content-creators/…/<person>/raw/clip.mp4"

The register is `brands/<brand>/content-creators/usage-rights.json` (curated by people, read-only here):
one row per creator with `drive_folder` (the person's folder name under
content-creators/<gender>/<look>/<age>/), `paid_ads`, `website` and `until`.
Footage is matched to its row by that folder name, any case.

A verdict, per use ("ads", "website" or "email"):
    allowed    the row says yes (or says nothing against it) and the window is open
    refused    the row says no for this use (the team, 2026-10-30: a NO-ADS creator must
               never come back from a search)
    expired    the row's `until` date has passed
    unknown    creator footage with no row in the register — returned, but marked
    n/a        not creator footage (products, identity, …): the register does not speak to it

EMAIL is stricter (LD-101 (Brand-B house look), the team's ruling 2026-10-30): `allowed` only when the row says
`email: true` ("treat them as no until their row says `email: true`"), or the creator has no row and her folder is
on the register's `pre_registry.drive_folders` (content that arrived before the registry); a row with `email`
missing or false is `refused`. A row always wins over the list, and the list speaks to email only: a pre-registry
folder is still `unknown` for ads and the website.

Brand-agnostic: the brand comes from the caller; a brand with no register gives `unknown` for every
creator clip and refuses nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent.parent / "brandpath"))
import brandpath  # noqa: E402

CREATORS = "content-creators"
USES = ("ads", "website", "email")
FIELD = {"ads": "paid_ads", "website": "website", "email": "email"}


def register_path(brand: str) -> Path:
    return brandpath.brand_root(brand) / CREATORS / "usage-rights.json"


def load(brand: str = "", path: Path | None = None, register: dict | None = None) -> dict:
    """{folder name lowercased: row}. A missing or unreadable register is an empty one. A pre-registry folder with
    no row of its own gets a stand-in row that speaks to email only (`_pre_registry`). `register` = the parsed
    file itself (tests)."""
    if register is None:
        p = Path(path) if path else register_path(brand)
        try:
            register = json.loads(p.read_text())
        except (OSError, ValueError):
            return {}
    rows = {str(r["drive_folder"]).lower(): r for r in register.get("creators") or [] if r.get("drive_folder")}
    pre = register.get("pre_registry") or {}
    for folder in pre.get("drive_folders") or []:
        rows.setdefault(str(folder).lower(), {"creator": folder, "drive_folder": folder, "email": pre.get("email") is True,
                                              "until": None, "_pre_registry": True})
    return rows


def creator_folder(label: str) -> str | None:
    """The person's folder in a content-creators label: …/content-creators/<gender>/<look>/<age>/<person>/…"""
    parts = (label or "").split("/")
    if CREATORS not in parts:
        return None
    rest = parts[parts.index(CREATORS) + 1:]
    return rest[3] if len(rest) > 4 else None


def verdict(label: str, register: dict, use: str = "ads", today: date | None = None) -> dict:
    """{"state": allowed|refused|expired|unknown|n/a, "use", "creator", "until"} for one clip's label."""
    folder = creator_folder(label)
    if folder is None:
        return {"state": "n/a", "use": use, "creator": None, "until": None}
    row = register.get(folder.lower())
    if row is None:
        return {"state": "unknown", "use": use, "creator": folder, "until": None}
    if row.get("_pre_registry") and use != "email":
        return {"state": "unknown", "use": use, "creator": folder, "until": None}
    out = {"use": use, "creator": row.get("creator") or folder, "until": row.get("until")}
    said = row.get(FIELD.get(use, use))
    if said is False or (use == "email" and said is not True):
        return dict(out, state="refused")
    until = row.get("until")
    try:
        ends = date.fromisoformat(str(until)) if until else None
    except ValueError:
        ends = None                    # "see note": the window's start is not on record — not refused here
    if ends and ends < (today or date.today()):
        return dict(out, state="expired")
    return dict(out, state="allowed")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("label")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--use", default="ads", choices=USES)
    a = ap.parse_args(argv)
    print(json.dumps(verdict(a.label, load(a.brand), a.use)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
