#!/usr/bin/env python3
"""image-variation — N clean variations off one baseline draft.

    python3 tools/image-edit/vary.py <baseline> --brand <brand> \\
        --v headline:headline="Stop the itch tonight" \\
        --v person:who="a woman in her fifties" \\
        --v colour:from_colour=teal,to_colour=gold
    python3 tools/image-edit/vary.py --library                   # the rows, verbatim
    python3 tools/image-edit/vary.py <approved.png> --brand <brand> --from-brief <variations.json> [--only h1,p2] [--dry-run]

`--from-brief` is the picture path (2026-10-27): the approved picture's own recipe plus each of its brief's variations,
ONE change each, built, checked and made by components/model-inputs exactly as the approved picture was, its words set
on top, then judged against it here. The file is the brief's variation list as data (`variations`: id, label, words,
picture, swap, stays_drop, people).

On a run with a kept 3D set, a picture change is that set changed: its `set-request.json` is written (the change, the
print's words, the credits), and once its print is filed the next run takes the print as the picture.

Each variation is ONE delta off the baseline, judged against it. `--dry-run`
spends nothing. Results land under runs/image-edit/<brand>/<label>/<id>/.
"""
import argparse, re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import image_edit as RE  # noqa: E402


def parse_v(spec):
    """`id:key=value,key=value` → {"id":…, "args":{…}}."""
    if ":" not in spec:
        return {"id": spec, "args": {}}
    vid, rest = spec.split(":", 1)
    args = {}
    # Split only on a comma that STARTS the next key=value. A value is copy —
    # "It clears your skin, then stains it." — and splitting on every comma
    # made a headline with one in it crash the run (found live 2026-09-23).
    for kv in filter(None, re.split(r",(?=\s*[A-Za-z_][A-Za-z0-9_]*\s*=)", rest)):
        if "=" not in kv:
            raise SystemExit(f"--v {spec}: '{kv.strip()}' is not key=value")
        k, v = kv.split("=", 1)
        args[k.strip()] = v.strip().strip('"')
    return {"id": vid, "args": args}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("baseline", nargs="?")
    ap.add_argument("--brand")
    ap.add_argument("--v", action="append", default=[], help="id:key=value,…")
    ap.add_argument("--kind", default="picture")
    ap.add_argument("--keep", action="append", default=[], help="one more thing that must not move")
    ap.add_argument("--product")
    ap.add_argument("--purpose", default="ad")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--region", help="left,top,right,bottom as percentages — the only part that may change")
    ap.add_argument("--model", help="force one image model (a declared row)")
    ap.add_argument("--ref", action="append", default=[], help="another reference picture on this machine")
    ap.add_argument("--label")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--library", action="store_true")
    ap.add_argument("--from-brief", help="the brief's variation list as data: made on the picture path")
    ap.add_argument("--only", help="comma-separated variation ids to run from --from-brief")
    a = ap.parse_args()

    if a.from_brief:
        import json
        if not a.baseline or not a.brand:
            raise SystemExit("an approved picture and --brand are required")
        doc = json.loads(Path(a.from_brief).read_text())
        vs = doc.get("variations") or []
        if a.only:
            want = {x.strip() for x in a.only.split(",") if x.strip()}
            vs = [v for v in vs if v.get("id") in want]
        req = {"brand": a.brand, "baseline": a.baseline, "variations": vs, "dry_run": a.dry_run}
        for k in ("label", "out"):
            if getattr(a, k):
                req[k] = getattr(a, k)
        s = RE.vary_recipe(req)
        print(f"{len(s['variations'])} variation(s) · {s['delivered']} delivered · "
              f"{s['rejected']} held · {s['refused']} refused · "
              f"{s['waiting_for_set']} waiting for a set · {s['print_credits']} credits of prints to make")
        for v in s["variations"]:
            mark = "✓" if v["delivered"] else ("!" if v["refused"] else "·" if v["state"] in ("dry", "waiting-for-set") else "✗")
            print(f"  {mark} {v['id']:<4} {v['state']:<8} {v.get('route') or '':<5} {v['name']}" + (f"  {v['refused']}" if v["refused"] else ""))
            for f in v["delivered"] + v["rejected"]:
                print(f"      {f}")
        print(f"  record: {Path(s['out']) / 'variations.json'}")
        return

    if a.library:
        table, path = RE.variations()
        print(f"# variations — {path.name}\n")
        for r in table.values():
            print(f"{r['id']:<11} {r['name']}  [{r['status']}]\n  {r['what']}\n  delta: {r['delta']}"
                  + (f"\n  needs: {', '.join(r['needs'])}" if r.get('needs') else "") + "\n")
        return
    if not a.baseline or not a.brand or not a.v:
        raise SystemExit("a baseline, --brand and at least one --v are required")

    req = {"brand": a.brand, "baseline": a.baseline, "variations": [parse_v(s) for s in a.v],
           "kind": a.kind, "purpose": a.purpose, "count": a.count, "dry_run": a.dry_run}
    for k in ("product", "label", "out", "model", "region"):
        if getattr(a, k):
            req[k] = getattr(a, k)
    if a.ref:
        req["references"] = a.ref
    if a.keep:
        req["keep"] = a.keep
    s = RE.vary(req)
    print(f"{len(s['variations'])} variation(s) · {s['delivered']} delivered · "
          f"{s['rejected']} rejected · {s['refused']} refused")
    for v in s["variations"]:
        mark = "✓" if v["delivered"] else ("!" if v["refused"] else "✗")
        print(f"  {mark} {v['id']:<11} {v['state']}" + (f"  {v['refused']}" if v["refused"] else ""))
        for f in v["delivered"]:
            print(f"      {f}")
    print(f"  record: {Path(s['out']) / 'variations.json'}")


if __name__ == "__main__":
    main()
