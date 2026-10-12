#!/usr/bin/env python3
"""The thin CLI over the library. A caller in Python imports the library
instead; this is for a person at a keyboard and for a chain that shells out.

    make.py --brand <brand> --purpose <purpose> --direction "<words>" \\
            --out <dir> [--aspect 9:16] [--count 2] [--product <key>] \\
            [--style <id>] [--format <id>] [--template <id>] \\
            [--from-image <png>] [--ref <png> ...] [--label <label>] \\
            [--people | --no-people] [--model <id>] [--dry-run]

    make.py --request <request.json> [--dry-run]     the same, as a file
    make.py purposes                                  what a picture can be for
    make.py route                                     the model table, read out

**--dry-run spends nothing**: it resolves the context, prints the prompt as it
would be sent, names the model and says where the files would land. No model
call, no judge call, no file written, nothing on Drive.

the owner never runs this. A session runs it on his behalf and hands him a link.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))      # APPEND, never insert at 0
import image_production as IP                              # noqa: E402


def build_parser():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="make",
                    choices=["make", "purposes", "route"])
    ap.add_argument("--request", help="a request.json holding the whole request")
    ap.add_argument("--brand")
    ap.add_argument("--purpose")
    ap.add_argument("--direction")
    ap.add_argument("--out")
    ap.add_argument("--aspect")
    ap.add_argument("--count", type=int)
    ap.add_argument("--product")
    ap.add_argument("--style")
    ap.add_argument("--format", dest="format")
    ap.add_argument("--template")
    ap.add_argument("--from-image", dest="from_image")
    ap.add_argument("--ref", action="append", dest="references", default=None)
    ap.add_argument("--label")
    ap.add_argument("--model")
    # Tri-state on purpose. The model route splits on whether a photoreal
    # person is in frame, and a purpose that says "maybe" has not decided —
    # so the caller says, or the inputs gate refuses. It is never read out of
    # the direction, because that is a guess.
    ap.add_argument("--people", dest="people", action="store_true", default=None,
                    help="a photoreal person IS in frame")
    ap.add_argument("--no-people", dest="people", action="store_false",
                    help="no person in frame")
    ap.add_argument("--check", action="append", dest="checks", default=None)
    ap.add_argument("--dry-run", "--dry", action="store_true", dest="dry_run")
    ap.add_argument("--gates", choices=["hold", "warn"], default="hold")
    ap.add_argument("--no-mirror", action="store_true",
                    help="do not copy the pictures to the Drive mirror")
    return ap


def request_from(a):
    if a.request:
        req = json.loads(Path(a.request).read_text())
    else:
        req = {}
    for field in ("brand", "purpose", "direction", "out", "aspect", "count", "product",
                  "style", "format", "template", "from_image", "references", "label",
                  "model", "people", "checks"):
        v = getattr(a, field, None)
        if v is not None and v != []:
            req[field] = v
    return req


def main(argv=None):
    a = build_parser().parse_args(argv)

    if a.command == "purposes":
        for pid, row in sorted(IP.purposes().items()):
            print(f"  {pid:<14} {row['aspect']:<6} {row['status']:<10} {row['what']}")
        return 0

    if a.command == "route":
        t = IP.route.table()
        print("  route, in order:")
        for row in t["route"]:
            when = ", ".join(f"{k}={v}" for k, v in (row.get("when") or {}).items()) or "(anything else)"
            print(f"    {when:<18} -> {row['model']:<20} {row['why']}")
        print("\n  models:")
        for name, e in t["models"].items():
            have = "key present" if IP.route.key_present(e) else "KEY MISSING"
            print(f"    {name:<20} {e['provider']:<8} {e['vendor_model']:<26} {e['key']} ({have})")
        j = t["judge"]
        print(f"    {'judge':<20} {j['provider']:<8} {j['vendor_model']:<26} {j['key']} "
              f"({'key present' if IP.route.key_present(j) else 'KEY MISSING'})")
        return 0

    req = request_from(a)
    if a.dry_run:
        ok, _ = IP.dry_run(req)
        return 0 if ok else 1

    try:
        result = IP.make(req, mirror=not a.no_mirror, mode=a.gates)
    except IP.BadRequest as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"\n{len(result['delivered'])} delivered · {len(result['held'])} held "
          f"— {result['model']} ({result['model_why']})")
    for p in result["delivered"]:
        print(f"  ✓ {p}")
    for h in result["held"]:
        print(f"  ✗ {h['name']} — {'; '.join(h['fails'])}")
    if result["drive"]["copied"]:
        print(f"  drive → {Path(result['drive']['copied'][0]).parent}")
    return 1 if result["held"] and not result["delivered"] else 0


if __name__ == "__main__":
    sys.exit(main())
