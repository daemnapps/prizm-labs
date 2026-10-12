#!/usr/bin/env python3
"""cast.py — the thin command line over the casting component.

    who plays this role?
        python3 components/casting/cast.py who --brand <b> --role "barber"

    what could be the baseline?
        python3 components/casting/cast.py find --brand <b> --like "barber, apron"

    the nine steps, for a role the bank does not cover
        python3 components/casting/cast.py build --brand <b> --role "barber" \\
            --id <id> --kind authority --noun man \\
            --who "…" --wardrobe "…" --world "…" [--detail "hands and forearms"] \\
            [--baseline <frame.jpg>] [--dry-run]

`who` and `find` spend nothing, always. `build --dry-run` spends nothing and
writes nothing. Every path goes through the same request contract; this file
only turns flags into that request.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))     # APPEND — never insert at 0
import casting as C                                        # noqa: E402


def build_parser():
    ap = argparse.ArgumentParser(
        prog="cast.py", description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    # At the top level `--dry-run` answers "what would this do?" with no
    # request at all: the nine steps and the contract, printed, spending
    # nothing. A dry run that needs a full request first is a dry run nobody
    # can use to find out how to write one.
    ap.add_argument("--dry-run", "--dry", dest="top_dry", action="store_true",
                    help="print the nine steps and the request contract; spend nothing")
    sub = ap.add_subparsers(dest="what")

    w = sub.add_parser("who", help="who plays this role?")
    w.add_argument("--brand", required=True)
    w.add_argument("--role", required=True)
    w.add_argument("--json", action="store_true")

    v = sub.add_parser("avatar", help="who do we have for this core avatar?")
    v.add_argument("--brand", required=True)
    v.add_argument("--name", help="a core avatar id; omit to list them all")

    f = sub.add_parser("find", help="baseline candidates in the owned footage")
    f.add_argument("--brand", required=True)
    f.add_argument("--like", required=True, help="words that describe the role")
    f.add_argument("--collection", help="only this footage collection")
    f.add_argument("--top", type=int, default=8)

    b = sub.add_parser("build", help="the nine steps, for a gap")
    for field in ("brand", "role"):
        b.add_argument("--" + field, required=True)
    for field in ("id", "kind", "who", "wardrobe", "world", "noun", "detail",
                  "baseline", "like", "collection", "name", "out", "label",
                  "style", "format", "lane", "fronts", "problem", "reads",
                  "hair", "setting", "register", "note"):
        b.add_argument("--" + field)
    b.add_argument("--check", action="append", dest="checks",
                   help="an extra judge test for this character")
    b.add_argument("--rule", action="append", dest="rules",
                   help="an extra standing rule for this character")
    b.add_argument("--gates", choices=C.gates.MODES, default="hold")
    b.add_argument("--no-mirror", action="store_true",
                   help="do not copy the sheets to Drive")
    b.add_argument("--dry-run", "--dry", dest="dry_run", action="store_true")
    return ap


def request_from(a):
    req = {}
    for field in sorted(C.FIELDS):
        v = getattr(a, field, None)
        if v not in (None, ""):
            req[field] = v
    return req


def main(argv=None):
    a = build_parser().parse_args(argv)
    if not a.what:
        if getattr(a, "top_dry", False):
            print("casting — who plays this role?\n")
            print("  the nine steps")
            for s in C.STEPS:
                print("    %d %-9s %-9s %s" % (s["n"], s["key"], s["kind"], s["what"]))
            print("\n  the question, and what it takes")
            print("    cast(brand, role) -> the person already banked, or the gap")
            print("\n  a build's request contract")
            print("    required: %s" % ", ".join(sorted(C.REQUIRED)))
            print("    required to build: %s" % ", ".join(C.BUILD_REQUIRED))
            print("    optional: %s" % ", ".join(
                sorted(set(C.FIELDS) - set(C.REQUIRED)
                       - set(C.BUILD_REQUIRED))))
            print("\n  nothing was generated, judged, written or spent.")
            return 0
        build_parser().print_help()
        return 2

    if a.what == "avatar":
        from casting import bank
        if not a.name:
            found = bank.avatars(a.brand)
            print(f"\n  {a.brand} · the core avatars its cast serves\n")
            for name, c in sorted(found.items(), key=lambda x: -(x[1]["authority"] + x[1]["roster"])):
                flag = "OK      " if c["authority"] else "--      "
                print(f"    {flag} {name:<20} {c['authority']} authority · {c['roster']} to play them"
                      + ("" if c["authority"] else "   <- no authority figure"))
            if not found:
                print("    none — no cast row names a core avatar")
            print()
            return 0
        r = bank.for_avatar(a.brand, a.name)
        print(f"\n  {a.brand} · {a.name}\n\n    {r['why']}\n")
        for label, rows in (("authority", r["authority"]), ("plays them", r["roster"]),
                            ("also plays them", r["also"])):
            for p in rows:
                row = p.get("row") or {}
                what = row.get("role") or row.get("note") or ""
                print(f"    {label:<16} {p['name']} (`{p['id']}`)" + (f" — {what[:70]}" if what else ""))
        print()
        return 0

    if a.what == "who":
        if a.json:
            print(json.dumps(C.cast(brand=a.brand, role=a.role), indent=1,
                             default=str))
            return 0
        r, _answer = C.dry_who(a.brand, a.role)
        return 1 if r.missing else 0

    if a.what == "find":
        rows, why = C.search.baselines(a.brand, a.like, a.collection, limit=a.top)
        print("%d baseline candidate(s) for %r in %s\n" % (len(rows), a.like, a.brand))
        for row in rows:
            print("  [%s] %s" % (row["points"], row["why"]))
            print("        %s" % (str(row["said"])[:120]))
            if row["baseline"]:
                print("        baseline candidate: %s" % row["baseline"])
            print()
        for w in why:
            print("  -- %s" % w)
        if rows:
            print("\nPick one frame, then: cast.py build --baseline <frame> …")
        return 0 if rows else 1

    req = request_from(a)
    if a.dry_run:
        r, _resolved = C.dry_run(req)
        return 1 if (r.missing or r.problems) else 0
    out = C.build(req, mirror=not a.no_mirror, mode=a.gates)
    print("\nrun    %s" % out["out"])
    for step in out["steps"]:
        print("  %-9s %s %s" % (step["key"], step["status"],
                                str(step.get("what") or step.get("why") or "")[:90]))
    if out["filed"]:
        print("\nfiled  %s" % C.paths.rel(Path(list(out["filed"].values())[0]).parent))
    print("\nPROPOSED, NOT REGISTERED — a person registers the row:")
    print("  %s" % (Path(out["out"]) / "register" / "REGISTER.md"))
    print("\nSTILL OPEN:")
    for s in out["still_open"]:
        print("  · %s" % s)
    return 1 if out["held"] else 0


if __name__ == "__main__":
    sys.exit(main())
