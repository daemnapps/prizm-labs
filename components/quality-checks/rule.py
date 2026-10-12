#!/usr/bin/env python3
"""Rule on a held problem — one command, one fact-rulings record (HE-1 (fact
rulings), 2026-10-01).

    python3 rule.py <email run folder> <id> true "the fact, as the brand would say it"
    python3 rule.py <email run folder> <id> true-once --reason "why, for this email only"
    python3 rule.py <email run folder> <id> wrong
    python3 rule.py <email run folder> <id> fill "the missing fact"
    python3 rule.py <email run folder> <id> not-ours
    python3 rule.py --list <brand>          # the verified facts, then the not-ours list

The ids are in the email's deliverable/check.json (`delivery.items`). The
record is filed through dispatch_card.write_record under
platform/data/records/fact-rulings/ in the workspace (AI_WORKSPACE, else this
checkout) and its path printed. NOTHING IS COMMITTED and nothing is written
under brands/ — folding the verified facts into the brand files stays the ops lead's
own hand. A price is never ruled: a wrong price is fixed in the offer bank.
"""
import argparse
import datetime
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = next(d for d in HERE.parents if (d / "components" / "brand-finder").is_dir())
DISPATCH_REL = "platform/tools/dispatch_card.py"
sys.path.insert(0, str(HERE))
sys.path.append(str(REPO / "components" / "brand-finder"))
import marketing_chain_checks as Q                       # noqa: E402
from marketing_chain_checks import rulings as R          # noqa: E402
import brand_finder                              # noqa: E402


class Refused(Exception):
    pass


def workspace():
    """The tree brand context, runs and rulings live in — one knob."""
    return Path(brand_finder.workspace(REPO))


def _dispatch():
    """dispatch_card.py, imported by path from THIS checkout — the one writer."""
    spec = importlib.util.spec_from_file_location("_he1_dispatch_card", REPO / DISPATCH_REL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def record_for(run, pid, ruling, fact="", reason="", by=None, root=None):
    """The record a ruling files, or Refused naming the fix. Writes nothing."""
    run = Path(run).resolve()
    try:
        brand = json.loads((run / "run.json").read_text()).get("brand")
    except (OSError, ValueError):
        brand = None
    if not brand:
        raise Refused(f"{run / 'run.json'} names no brand — a ruling belongs to one brand, "
                      "and the brand is never guessed from a folder name")
    try:
        delivery = json.loads((run / "deliverable" / "check.json").read_text()).get("delivery") or {}
    except (OSError, ValueError):
        delivery = {}
    if "items" not in delivery:
        raise Refused(f"{run.name}'s check.json carries no problem ids — re-check it first: "
                      f"simple_email.py {run} --brand {brand} --no-images")
    it = next((i for i in delivery["items"] if i.get("id") == pid), None)
    if not it:
        have = ", ".join(f"{i.get('id')} ({i.get('kind')})" for i in delivery["items"]) or "none"
        raise Refused(f"`{pid}` is not a problem on {run.name} — its ids: {have}")
    if ruling not in R.RULINGS:
        raise Refused(f"`{ruling}` is not a ruling — one of: {', '.join(R.RULINGS)}")
    kind = it.get("kind")
    if kind == "price" and ruling != "wrong":
        raise Refused(f"a wrong price is fixed in brands/{brand}/products/offer-bank.md "
                      "(the ops lead's fold) — a ruling never clears a price")
    if kind not in R.RULABLE:
        raise Refused(f"a `{kind}` problem is not rulable — fix the email, not rulable")
    if ruling not in R.RULABLE[kind]:
        raise Refused(f"a `{kind}` problem takes {' | '.join(R.RULABLE[kind])}, not `{ruling}`")
    fact, reason = (fact or "").strip(), (reason or "").strip()
    if ruling in ("true", "fill") and not fact:
        raise Refused(f"`{ruling}` needs the fact text — "
                      f"rule.py {run} {pid} {ruling} \"the fact\"")
    if ruling in ("true", "fill") and Q.prices_in(fact):
        raise Refused("the fact text names a price — a wrong price is fixed in "
                      f"brands/{brand}/products/offer-bank.md (the ops lead's fold) — a ruling never clears a price")
    if ruling == "true-once" and not reason:
        raise Refused(f"`true-once` needs --reason — why it is true for {run.name} only")
    root = Path(root or workspace())
    if not by:
        D = _dispatch()
        try:
            by = D.runner_id(root)
        except D.Refused as e:
            raise Refused(f"no person to file as ({e}) — pass --by <person>")
    at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"schema": 1, "kind": R.KIND, "reviewer": by, "item": pid,
            "verdict": {"brand": brand, "problem_id": pid, "email": run.name, "kind": kind,
                        "quote": it.get("quote"), "files_say": it.get("files_say"),
                        "ruling": ruling, "fact": fact if ruling in ("true", "fill") else "",
                        "reason": reason, "by": by, "at": at},
            "notes": "", "created": at, "via": "marketing-chain-checks/rule.py"}


def listing(brand, root=None):
    root = Path(root or workspace())
    facts, gone = R.verified_facts(root, brand), R.not_ours(root, brand)
    lines = [f"verified facts — {brand} ({len(facts)}):"]
    lines += [f"  {f['fact']}   [{f['ruling']} · {f['by']} · {f['at']} · {f['email']} · {f['id']}]"
              for f in facts] or ["  (none)"]
    lines += ["", f"not ours — {brand} ({len(gone)}):"]
    lines += [f"  “{g['quote']}”   [{g['by']} · {g['at']} · {g['email']} · {g['id']}]"
              for g in gone] or ["  (none)"]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run", nargs="?", help="the email's run folder (holds run.json and deliverable/check.json)")
    ap.add_argument("id", nargs="?", help="the problem id, from check.json's delivery.items")
    ap.add_argument("ruling", nargs="?", help=" | ".join(R.RULINGS))
    ap.add_argument("fact", nargs="?", default="", help="the fact text (true, fill)")
    ap.add_argument("--reason", default="", help="why — required for true-once")
    ap.add_argument("--by", default=None, help="who rules (default: this checkout's git identity)")
    ap.add_argument("--list", metavar="BRAND", help="print the brand's verified facts and not-ours list")
    a = ap.parse_args(argv)
    if a.list:
        print(listing(a.list))
        return 0
    if not (a.run and a.id and a.ruling):
        ap.print_usage(sys.stderr)
        return 2
    try:
        rec = record_for(a.run, a.id, a.ruling, a.fact, a.reason, a.by)
    except Refused as e:
        print(f"REFUSED — {e}. Nothing filed.", file=sys.stderr)
        return 1
    root = workspace()
    path = _dispatch().write_record(rec, root, R.RECORDS_REL)
    print(f"filed {a.ruling} on {a.id} ({rec['verdict']['kind']}) for {rec['verdict']['email']}: "
          f"{root / path}\n(not committed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
