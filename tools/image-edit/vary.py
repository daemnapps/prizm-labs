#!/usr/bin/env python3
"""image-variation — N clean variations off one baseline draft.

    python3 tools/image-edit/vary.py <baseline> --brand <brand> \\
        --v headline:headline="Your new headline" \\
        --v person:who="a woman in her fifties" \\
        --v colour:from_colour=teal,to_colour=gold
    python3 tools/image-edit/vary.py --library                   # the rows, verbatim

Each variation is ONE delta off the baseline, judged against it. This writes
one job per row (`jobs.json` at the set's folder) and spends nothing; the
session makes them on Higgsfield and `edit.py --ingest <folder> --results …`
brings them back. `--dry-run` writes no jobs. Results land under
runs/image-edit/<brand>/<label>/<id>/.
"""
import argparse
import re
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
    # "It works, then it lasts." — and splitting on every comma made a
    # headline with one in it crash the run (found live 2026-09-23).
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
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--region", help="left,top,right,bottom as percentages — the only part that may change")
    ap.add_argument("--model", help="a different Higgsfield model for these edits")
    ap.add_argument("--ref", action="append", default=[], help="another reference picture on this machine")
    ap.add_argument("--label")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--library", action="store_true")
    a = ap.parse_args()

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
           "kind": a.kind, "count": a.count, "dry_run": a.dry_run}
    for k in ("product", "label", "out", "model", "region"):
        if getattr(a, k):
            req[k] = getattr(a, k)
    if a.ref:
        req["references"] = a.ref
    if a.keep:
        req["keep"] = a.keep
    s = RE.vary(req)
    print(f"{len(s['variations'])} variation(s) · {s['ready']} ready to make · {s['delivered']} delivered · "
          f"{s['rejected']} rejected · {s['refused']} refused")
    for v in s["variations"]:
        mark = "✓" if v["delivered"] else ("!" if v["refused"] else "·")
        print(f"  {mark} {v['id']:<11} {v['state']}" + (f"  {v['refused']}" if v["refused"] else ""))
    if s["ready"]:
        print(f"  jobs: {Path(s['out']) / 'jobs.json'}")
        print(f"  then: edit.py --ingest {s['out']} --results <results.json>")
    print(f"  record: {Path(s['out']) / 'variations.json'}")


if __name__ == "__main__":
    main()
