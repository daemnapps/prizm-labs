"""A person's ruling on a held problem, read back for the gate (HE-1 (fact
rulings), 2026-10-01).

the ops lead rules on a held problem once — `rule.py` files one `fact-rulings` record
per ruling on the records plane — and every gate that passes its problems as
items drops what a standing ruling clears. THE BRAND'S VERIFIED FACTS ARE A
READ OVER THESE RECORDS (standing true + fill), never a second store, and
never brands/: folding them into the brand files is the ops lead's own weekly act.

    wrong       the email is wrong — nothing clears; changed words are a new id
    true        the files are behind — clears the id for every email of the brand
    true-once   true for this email only, with a reason — clears that email only
    fill        the fact a hole needed — joins the verified facts, clears nothing
    not-ours    the brand does not have this — clears the id for every email

PRICES ARE OFFER-BANK-ONLY (Operator B, decision log 2026-10-01): a ruling never
adds or clears a price. A ruling on a price item is ignored here even when a
hand-written record exists; a wrong price is fixed in the offer bank.
"""
import json
import sys
from pathlib import Path

from . import prices_in

RECORDS_REL = "platform/data/records/fact-rulings"
KIND = "fact-rulings"
RULINGS = ("wrong", "true", "true-once", "fill", "not-ours")
# The step-8c findings take every ruling. An UNFILLED note is recorded (fill and
# not-ours feed the lists) but never dropped at the gate: the note is still in
# the email's text, so the writer must run again. Every other kind is refused.
RULABLE = {"fact": RULINGS, "chop": RULINGS, "typo": RULINGS,
           "unfilled": ("fill", "not-ours", "wrong")}
NEVER_CLEARED = {"unfilled"}
# what a standing ruling clears: the brand's every email, or the one it names
CLEARING = {"true": "brand", "not-ours": "brand", "true-once": "email"}


def load(root, brand):
    """Every readable fact-rulings record for this brand, oldest first. A file
    that cannot be read is skipped and named on stderr — never a crash."""
    d = Path(root) / RECORDS_REL
    out = []
    for f in sorted(d.glob("*.json")) if d.is_dir() else []:
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
            v = rec["verdict"]
            ok = (rec.get("kind") == KIND and isinstance(v, dict)
                  and v.get("ruling") in RULINGS and isinstance(v.get("problem_id"), str))
        except (OSError, ValueError, KeyError, TypeError):
            ok, rec, v = False, None, None
        if not ok:
            print(f"fact-rulings: skipped {f.name} — not a readable ruling", file=sys.stderr)
            continue
        if v.get("brand") != brand:
            continue
        out.append(dict(v, created=str(rec.get("created") or v.get("at") or ""), file=f.name))
    out.sort(key=lambda r: (r["created"], r["file"]))
    return out


def standing(root, brand):
    """problem id -> the latest brand-wide ruling on it (by `created`): a later
    ruling replaces an earlier one, so a later `wrong` revokes a `true`. A
    `true-once` is never here — it belongs to its email (HE-1b), see once()."""
    out = {}
    for r in load(root, brand):
        if CLEARING.get(r["ruling"]) != "email":
            out[r["problem_id"]] = r
    return out


def once(root, brand):
    """(problem id, email) -> the latest `true-once` for that email (HE-1b): a
    true-once on one email never replaces another email's, nor a brand ruling."""
    out = {}
    for r in load(root, brand):
        if CLEARING.get(r["ruling"]) == "email":
            out[(r["problem_id"], r.get("email"))] = r
    return out


def _order(r):
    return (r["created"], r["file"])            # the order load() sorts by


def split(items, brand, email, root):
    """(kept, cleared): the items still holding the email, and one row per item
    a standing ruling cleared. The deciding ruling is the later of the item's
    brand-wide ruling and this email's `true-once`, so a later `wrong` holds
    every email and a later `true-once` clears its own email only. Only the
    item's OWN kind decides what may clear it — a ruling on a price, an
    unfilled note or an unrulable kind clears nothing, whatever the record says."""
    rules, onces = standing(root, brand), once(root, brand)
    kept, cleared = [], []
    for it in items:
        found = [x for x in (rules.get(it["id"]), onces.get((it["id"], email))) if x]
        r = max(found, key=_order) if found else None
        scope = CLEARING.get(r["ruling"]) if r else None
        if (scope and it["kind"] in RULABLE and it["kind"] not in NEVER_CLEARED
                and r["ruling"] in RULABLE[it["kind"]]
                and (scope == "brand" or r.get("email") == email)):
            cleared.append({"id": it["id"], "kind": it["kind"], "ruling": r["ruling"],
                            "by": r.get("by"), "at": r.get("at")})
        else:
            kept.append(it)
    return kept, cleared


def _countable(r):
    return r.get("kind") in RULABLE and not prices_in(r.get("fact") or "")


def verified_facts(root, brand):
    """The brand's verified facts: standing true + fill rulings, never a price."""
    return [{"id": r["problem_id"], "fact": r.get("fact"), "ruling": r["ruling"],
             "email": r.get("email"), "by": r.get("by"), "at": r.get("at")}
            for r in standing(root, brand).values()
            if r["ruling"] in ("true", "fill") and _countable(r)]


def not_ours(root, brand):
    """What the brand does not have: standing not-ours rulings."""
    return [{"id": r["problem_id"], "quote": r.get("quote"), "email": r.get("email"),
             "by": r.get("by"), "at": r.get("at")}
            for r in standing(root, brand).values()
            if r["ruling"] == "not-ours" and r.get("kind") in RULABLE]
