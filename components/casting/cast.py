#!/usr/bin/env python3
"""cast.py — the thin command line over the casting component.

    who plays this role?
        python3 components/casting/cast.py who --brand <b> --role "barber"

    what could be the baseline?
        python3 components/casting/cast.py find --brand <b> --like "barber, apron"

    who plays it in the ad's style? (a banked person in another style is a variant to make, never a gap)
        python3 components/casting/cast.py who --brand <b> --role "barber" --style <style-id>

    the banked person in another style: have it, or make it (3D print, then the sheets in the style)
        python3 components/casting/cast.py variant --brand <b> --person <id> --style <style-id> [--look F] [--dry-run]

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
    w.add_argument("--style", help="the ad's style id (style_chain.py style): the answer says whether the person is "
                                   "banked in it, or the variant to make")

    vr = sub.add_parser("variant", help="the banked person in another style: have it, or make it")
    vr.add_argument("--brand", required=True)
    vr.add_argument("--person", required=True, help="the casting element id")
    vr.add_argument("--style", required=True)
    vr.add_argument("--look", help="a face-free swipe frame for the look (default: the swipe's own, else the swatch)")
    vr.add_argument("--run", help="the writing or teardown run (its face-free frames carry the look)")
    vr.add_argument("--dry-run", "--dry", dest="dry_run", action="store_true")

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


def style_chain():
    """The ad's style, read down the chain (components/video-production/styles/style_chain.py)."""
    import importlib.util
    f = Path(__file__).resolve().parents[1] / "video-production" / "styles" / "style_chain.py"
    spec = importlib.util.spec_from_file_location("vp_style_chain", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def in_style(brand, person_id, style):
    """A banked person in the ad's style: master, have, make (the variant to make) or no-master."""
    return style_chain().resolve(brand, "person", person_id, style)


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

    if a.what == "variant":
        out = style_chain().ensure_one(a.brand, "person", a.person, a.style, run=a.run, look=a.look,
                                       dry_run=a.dry_run)
        print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
        return 0 if out.get("state") in ("master", "have", "queued", "make") else 1

    if a.what == "who":
        if a.json:
            ans = C.cast(brand=a.brand, role=a.role)
            if a.style and ans.get("person"):
                ans["in_style"] = in_style(a.brand, ans["person"].get("id"), a.style)
            print(json.dumps(ans, indent=1, default=str))
            return 0
        r, answer = C.dry_who(a.brand, a.role)
        if a.style and (answer or {}).get("person"):
            st = in_style(a.brand, answer["person"].get("id"), a.style)
            print("\n  in the ad's style (%s): %s" % (a.style, st["state"]))
            if st.get("next"):
                print("    a variant to make, not a gap: " + st["next"])
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
    if a.style:
        # the role is banked in another style: a variant to make, never a new face and never a different look
        ans = C.cast(brand=a.brand, role=a.role)
        if ans.get("covered") and ans.get("person"):
            st = in_style(a.brand, ans["person"]["id"], a.style)
            if st["state"] != "no-master":
                print("%s is banked; in %s: %s" % (ans["person"]["id"], a.style, st["state"]))
                if st["state"] == "make":
                    out = style_chain().ensure_one(a.brand, "person", ans["person"]["id"], a.style,
                                                   dry_run=a.dry_run)
                    print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
                return 0
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
