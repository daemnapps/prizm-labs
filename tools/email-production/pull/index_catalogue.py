#!/usr/bin/env python3
"""Index a brand's type catalogue with the detail a calendar needs to be
built deterministically. (the owner, 2026-08-31: "index the catalogue with
detail — to deterministically create the calendar with detail.")

    python3 pull/index_catalogue.py --brand <brand> [--dry-run]

The catalogue already says what each type IS. This adds what each type
NEEDS AROUND IT, so code — not a model — can assemble a promotional arc:

  carries_offer   does this type require an offer to exist at all
  warm_up         types that can legitimately precede it (earns/sets-up)
  cool_down       types that can legitimately follow it (recovers/closes)
  arc_required    True when this type must never ship alone

Every value is DERIVED from what the catalogue already declares — the
type's own `then`, its `needs`, its role and its well. Nothing is invented,
and a brand that has edited its catalogue gets an index of its own edits.
Re-runnable: it rewrites the `arc` block and touches nothing else — as a
proposal of email-sms/email-types.json under
runs/email-production/<brand>/facts-<YYYY-MM-DD>/ (K2 (brands write wall)).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from paths import WORKSPACE  # noqa: E402
import facts_proposal  # noqa: E402


def build_index(cat):
    types = {t["key"]: t for t in cat["types"]}
    recovery = [k for k, t in types.items() if t["role"] == "recovers"]
    closes = [k for k, t in types.items() if t["role"] == "closes"]
    # affiliate types earn attention for a PARTNER's offer, not ours — they
    # never warm up or close an arc built around our own promotional ask.
    earners = [k for k, t in types.items()
               if t["role"] in ("earns", "sets-up") and t.get("well") != "affiliate"]

    for k, t in types.items():
        needs_offer = "offer_file" in (t.get("needs") or [])
        declared_then = list(t.get("then") or [])

        # COOL-DOWN: what the type itself names, narrowed to real recoveries
        # and closes; where it names none, the general recoveries stand.
        cool = [x for x in declared_then if types.get(x, {}).get("role")
                in ("recovers", "closes")]
        if not cool and t["role"] == "asks":
            # an ask with no declared recovery still needs one: prefer a
            # recovery that shares its needs (offer-based asks -> offer-based
            # recoveries), else any recovery.
            same = [r for r in recovery
                    if needs_offer == ("offer_file" in (types[r].get("needs") or []))]
            cool = same or recovery

        # WARM-UP: anything whose declared `then` points AT this type is the
        # brand's own statement that it warms this one. Otherwise, earners
        # that share a material need (same product/offer dependency) qualify.
        warm = [a for a, x in types.items()
                if k in (x.get("then") or []) and x["role"] in ("earns", "sets-up")]
        if not warm and t["role"] == "asks":
            need = set(t.get("needs") or [])
            warm = [a for a in earners
                    if need & set(types[a].get("needs") or [])] or earners

        t["arc"] = {
            "carries_offer": needs_offer,
            "arc_required": bool(t["role"] == "asks" and needs_offer),
            "warm_up": sorted(set(warm))[:8],
            "cool_down": sorted(set(cool))[:6],
            "declared_then": declared_then,
        }
    return cat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    a = ap.parse_args()
    f = WORKSPACE / "brands" / a.brand / "email-sms" / "email-types.json"
    if not f.is_file():
        sys.exit(f"{a.brand} has no email/email-types.json — copy the seed first")
    cat = build_index(json.loads(f.read_text()))
    need_arc = [t for t in cat["types"] if t["arc"]["arc_required"]]
    print(f"{len(cat['types'])} types indexed · {len(need_arc)} require a full arc")
    for t in need_arc:
        print(f"  {t['key']:20} warm: {', '.join(t['arc']['warm_up'][:4]) or '—'}")
        print(f"  {'':20} cool: {', '.join(t['arc']['cool_down'][:4]) or '—'}")
    if a.dry_run:
        print("\n(dry run — nothing written)")
        return
    run = facts_proposal.run_dir(a.brand, a.label)
    facts_proposal.write(run, a.brand, "email-sms/email-types.json", json.dumps(cat, indent=1) + "\n")
    print(f"\nproposal -> {facts_proposal.note(run, a.brand)}")


if __name__ == "__main__":
    main()
