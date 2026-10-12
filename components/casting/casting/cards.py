"""cards.py — the talent-card schema and its check.

One schema for every brand's `casting/cards-v6.json` (Naming Standard, "Talent
card fields", v6 2026-09-29). Every list value on a card must be in its list;
a card with a value outside a list is REFUSED, not corrected — the record is
brand truth and a person fixes it. The Talent Cards page builder calls
`validate_file` before it draws anything, so a bad card can never reach a page.

    from casting.cards import validate, validate_file, LISTS
    python3 components/casting/casting/cards.py            # checks every brand, exit 1 on any error

Stdlib only; runs on /usr/bin/python3 (3.9).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LISTS = {
    "kind": ["real-creator", "ai-character"],
    "role": ["ugc", "authority", "customer", "founder", "interviewer"],
    "gender": ["female", "male"],
    "ethnic-appearance": ["black", "white", "latino", "east-asian", "southeast-asian", "south-asian", "middle-eastern", "mixed"],
    "ethnic-appearance-source": ["stated", "drive-folder", "estimated from photos", "estimated from video frames", "index"],
    "age-band": ["18-24", "25-34", "35-44", "45-54", "55-64", "65-plus"],
    "age-band-source": ["stated", "estimated from photos", "estimated from video frames", "index"],
    "casting-sheet": ["yes", "no"],
    "status": ["current", "not current — no casting sheet"],
}
# fields that may be blank (null) — a blank is a blank, never a guess
BLANKABLE = {"gender", "ethnic-appearance", "ethnic-appearance-source", "age-band", "age-band-source", "name", "handle", "reads"}
REQUIRED = ["id", "name", "handle", "kind", "role", "gender", "ethnic-appearance", "ethnic-appearance-source",
            "age-band", "age-band-source", "avatars-fit", "sub-avatars-fit", "source", "notes", "missing"]
LISTY = ["avatars-fit", "sub-avatars-fit", "notes", "missing", "old-ids"]
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate(card: dict, brand: str = "") -> list[str]:
    """Every problem on one card, in words. Empty list = the card is good."""
    where = f"{brand}/{card.get('id', '?')}" if brand else str(card.get("id", "?"))
    out = []
    for f in REQUIRED:
        if f not in card:
            out.append(f"{where}: missing field '{f}'")
    cid = card.get("id")
    if not isinstance(cid, str) or not ID_RE.match(cid):
        out.append(f"{where}: id must be lowercase words joined by hyphens, got {cid!r}")
    for f, allowed in LISTS.items():
        if f not in card:
            continue
        v = card[f]
        if v is None and f in BLANKABLE:
            continue
        if v not in allowed:
            out.append(f"{where}: {f} = {v!r} is not in its list ({' | '.join(allowed)})")
    for f in LISTY:
        if f in card and not isinstance(card[f], list):
            out.append(f"{where}: {f} must be a list")
    kind = card.get("kind")
    if kind == "ai-character":
        for f in ("casting-sheet", "status"):
            if f not in card:
                out.append(f"{where}: an ai-character needs '{f}'")
        if card.get("casting-sheet") == "yes" and card.get("status") != "current":
            out.append(f"{where}: casting-sheet yes but status is {card.get('status')!r}")
        if card.get("casting-sheet") == "no" and card.get("status") == "current":
            out.append(f"{where}: no casting sheet, so status cannot be 'current'")
    if card.get("role") == "authority" and not card.get("credential"):
        out.append(f"{where}: an authority needs a 'credential'")
    if card.get("role") != "authority" and card.get("credential"):
        out.append(f"{where}: 'credential' only belongs on an authority")
    if card.get("ethnic-appearance") and not card.get("ethnic-appearance-source"):
        out.append(f"{where}: ethnic-appearance is set but ethnic-appearance-source is blank")
    if card.get("age-band") and not card.get("age-band-source"):
        out.append(f"{where}: age-band is set but age-band-source is blank")
    if card.get("name") is None and "first name unknown" not in (card.get("missing") or []) and "name" not in (card.get("missing") or []):
        out.append(f"{where}: name is blank but missing does not say so")
    return out


def validate_cards(cards: list, brand: str = "") -> list[str]:
    out = []
    seen = {}
    for c in cards:
        out += validate(c, brand)
        cid = c.get("id")
        if cid in seen:
            out.append(f"{brand}/{cid}: id used twice (cards {seen[cid]} and {cards.index(c)})")
        seen.setdefault(cid, cards.index(c))
    return out


def validate_file(path: Path) -> list[str]:
    d = json.loads(Path(path).read_text())
    brand = Path(path).resolve().parts[-5] if "brands" in Path(path).resolve().parts else Path(path).stem
    return validate_cards(d["cards"], brand)


def card_files(repo: Path) -> list[Path]:
    return sorted((repo / "brands").glob("*/ai-elements/characters/casting/cards-v6.json"))


def main(argv=None) -> int:
    repo = Path(__file__).resolve().parents[3]
    files = [Path(a) for a in (argv or sys.argv[1:])] or card_files(repo)
    problems = []
    for f in files:
        errs = validate_file(f)
        problems += errs
        n = len(json.loads(f.read_text())["cards"])
        print(f"{f.relative_to(repo) if f.is_relative_to(repo) else f}: {n} cards, {len(errs)} problems")
    for p in problems:
        print("  ", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
