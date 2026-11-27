#!/usr/bin/env python3
"""The thin CLI over the library. A caller in Python imports the library
instead; this is for a person at a keyboard and for a chain that shells out.

    make.py --brand <brand> --purpose <purpose> --direction "<words>" \\
            --out <dir> [--aspect 9:16] [--count 2] [--product <key>] \\
            [--style <id>] [--format <id>] [--template <id>] \\
            [--from-image <png>] [--ref <png> ...] [--label <label>] \\
            [--people | --no-people] [--model <id>] [--dry-run]
            [--no-product-3d] [--product-place '{"x":0.5,"y":0.75,"height":0.3}']

    make.py --request <request.json> [--dry-run]     the same, as a file
    make.py purposes                                  what a picture can be for
    make.py route                                     the model table, read out

    make.py covers --job <job.json> [--only <version> ...] [--dry-run]
                                                      every version's cover for one video ad, in one type
                                                      (image_production/covers.py says what the job holds)
    make.py --purpose cover --brand <brand> --set <set> --out <dir> [--direction "<words>"] \\
            --version <id> --headline "<words>" --frame <png> --video <mp4> --frame-at <seconds> --swipe <id> \\
            --ad <id> [--type <type.json>] \\
            [--people | --no-people] [--product <key>] [--product-place '{...}'] [--ref <cast sheet> ...]
                                                      one version's cover
                                                      (exits 1 when the cover is delivered but not `ok`)

**--dry-run spends nothing**: it resolves the context, prints the prompt as it
would be sent, names the model and says where the files would land. No model
call, no judge call, no file written, nothing on Drive.

The owner never runs this. A session runs it on the owner's behalf and hands over a link.
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
                    choices=["make", "purposes", "route", "covers"])
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
    # The product from its 3D model (2026-10-14): ON by itself for a product
    # whose kit has a 3D model — the image model then never draws the product.
    ap.add_argument("--no-product-3d", dest="product_3d", action="store_false", default=None,
                    help="let the image model draw the product (off: not recommended)")
    ap.add_argument("--product-3d", dest="product_3d", action="store_true",
                    help="require the 3D product; refused if the kit has no model")
    ap.add_argument("--product-place", dest="product_place", type=json.loads, default=None,
                    help='where the 3D product goes, JSON: {"pose","x","y","height","camera","light"}')
    ap.add_argument("--product-after", dest="product_after", action="store_true", default=None,
                    help="the real product is laid over the drawn one afterwards: don't judge the drawn product's look")
    ap.add_argument("--set", dest="set", help="the filed 3D set (picture_sets.py) this picture is made from; required "
                                              "for a people picture of an ad or video still (its kept print is the base)")
    # A cover (purpose `cover`): one request per version of a video ad. The frame of the version's own video is the
    # composition, the filed set is still required, the headline is set by the tool's words step.
    ap.add_argument("--ad", help="cover: the ad this version belongs to")
    ap.add_argument("--version", help="cover: the version this cover is for (control, a hook id)")
    ap.add_argument("--headline", help="cover: the version's headline; the words on the cover, set by the tool")
    ap.add_argument("--frame", help="cover: the strongest frame of the version's own video (a picture file)")
    ap.add_argument("--video", help="cover: the version's own video the frame is from")
    ap.add_argument("--frame-at", dest="t", type=float, help="cover: the frame's second in that video")
    ap.add_argument("--swipe", help="cover: the id of the real cover this one follows, from the swipe index")
    ap.add_argument("--type", dest="type", help="cover: the ad's type record (a JSON file); default cover-type.json")
    ap.add_argument("--job", help="covers: the job file holding one ad's versions")
    ap.add_argument("--only", action="append", default=None,
                    help="covers: make just this version again, in the ad's filed type (repeatable)")
    ap.add_argument("--dry-run", "--dry", action="store_true", dest="dry_run")
    ap.add_argument("--gates", choices=["hold", "warn"], default="hold")
    ap.add_argument("--recipe", help="a JSON file holding the picture's variable sheet (every variable filled, or "
                                      "{\"na\": reason}); a new ad picture without one is refused")
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
                  "model", "people", "checks", "product_3d", "product_place", "product_after", "set"):
        v = getattr(a, field, None)
        if v is not None and v != []:
            req[field] = v
    if getattr(a, "recipe", None):
        req["recipe"] = json.loads(Path(a.recipe).read_text())
    cover = {k: getattr(a, k, None) for k in ("ad", "version", "headline", "frame", "video", "t", "swipe", "type")}
    cover = {k: v for k, v in cover.items() if v is not None}
    if cover:
        req["cover"] = {**(req.get("cover") or {}), **cover}
    return req


def covers(a):
    """`make.py covers --job <job.json>`: every version's cover for one ad, in one type."""
    if not a.job:
        print("covers needs --job <job.json> (image_production/covers.py says what it holds)", file=sys.stderr)
        return 2
    job = json.loads(Path(a.job).read_text())
    try:
        got = IP.covers.make_ad(job, only=a.only, dry_run=a.dry_run,
                                **({} if a.dry_run else {"mirror": not a.no_mirror, "mode": a.gates}))
    except IP.covers.CoverRefused as e:
        print(str(e), file=sys.stderr)
        return 2
    if a.dry_run:
        print(f"{len(got['requests'])} cover(s) would be made for {got['ad']}, one type: "
              f"{(got['type'] or {}).get('face')} {(got['type'] or {}).get('weight', '')} at "
              f"{(got['type'] or {}).get('size_px', 0):g} px. Nothing was generated, written or spent.")
        return 0
    for row in got["covers"]:
        mark = "✓" if row.get("ok") else "~"
        print(f"  {mark} {row['version']}: {row.get('file')}" + ("" if row.get("ok") else " — " + "; ".join(row.get("problems") or got["problems"])))
    for f in got["failed"]:
        print(f"  ✗ {f['version']}: {f['why']}")
    for p in got["problems"]:
        print(f"  ! {p}")
    print(f"  record → {got['record']}")
    return 0 if got["ok"] else 1


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
            if e.get("provider") == "higgsfield":       # the command line signs in through a browser: no key
                print(f"    {name:<24} {e['provider']:<10} {e['vendor_model']:<20} {e.get('credential')}")
                continue
            have = "key present" if IP.route.key_present(e) else "KEY MISSING"
            print(f"    {name:<24} {e['provider']:<10} {e['vendor_model']:<26} {e['key']} ({have})")
        j = t["judge"]
        print(f"    {'judge':<20} {j['provider']:<8} {j['vendor_model']:<26} {j['key']} "
              f"({'key present' if IP.route.key_present(j) else 'KEY MISSING'})")
        return 0

    if a.command == "covers":
        return covers(a)

    req = request_from(a)
    if a.dry_run:
        ok, _ = IP.dry_run(req)
        return 0 if ok else 1

    try:
        result = IP.make(req, mirror=not a.no_mirror, mode=a.gates)
    except IP.BadRequest as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"\n{len(result['delivered'])} delivered · {len(result.get('below_criteria') or [])} below criteria "
          f"— {result['model']} ({result['model_why']})")
    for p in result["delivered"]:
        print(f"  ✓ {p}")
    for row in result["pictures"]:
        if row.get("product3d"):
            pr = row["product3d"]
            print(f"  3D product: {pr.get('source') or pr.get('error')} — empty scene {pr['scene']}")
    for h in result.get("below_criteria") or []:           # delivered and flagged: outputs never hold the chain
        print(f"  ~ {h['name']} is below criteria — {'; '.join(h['failed_checks']) or 'did not pass the judge'}")
    if result["drive"]["copied"]:
        print(f"  drive → {Path(result['drive']['copied'][0]).parent}")
    cover = result.get("cover")
    if cover is not None and not cover.get("ok") and IP.covers.on("unfit_exit"):
        # a cover that is not fit to file stops its caller here: the video line files nothing on a non-zero exit
        print(f"  ✗ the cover is not fit to file — {'; '.join(cover.get('problems') or ['its record does not say ok'])}. "
              f"Make it again; never file it.", file=sys.stderr)
        return 1
    return 0 if result["delivered"] else 1


if __name__ == "__main__":
    sys.exit(main())
