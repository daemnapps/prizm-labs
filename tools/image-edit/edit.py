#!/usr/bin/env python3
"""image-edit — fix one thing on a finished picture.

    python3 tools/image-edit/edit.py <picture> --brand <brand> --change "the tube is in her left hand"
    python3 tools/image-edit/edit.py <picture> --brand <brand> --fix logo
    python3 tools/image-edit/edit.py <picture> --brand <brand> --fix text --arg was=SAALE --arg now=SALE
    python3 tools/image-edit/edit.py <picture> --brand <brand> --fix product --product <slug>
    python3 tools/image-edit/edit.py --fixes                       # the library, verbatim

`--dry-run` resolves everything, prints the instruction as it would be sent,
and spends nothing. The original picture is never written to; the result is a
new version under runs/image-edit/<brand>/<label>/.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import image_edit as RE  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("picture", nargs="?")
    ap.add_argument("--brand")
    ap.add_argument("--change", help="the ONE thing to change, in words")
    ap.add_argument("--fix", help="a row in the fixes library")
    ap.add_argument("--arg", action="append", default=[], help="key=value a fix needs")
    ap.add_argument("--kind", default="picture", help="picture · slide · frame-A · frame-B · frame-C")
    ap.add_argument("--keep", action="append", default=[], help="one more thing that must not move")
    ap.add_argument("--element", action="append", default=[], help="an element id the change is about")
    ap.add_argument("--product")
    ap.add_argument("--purpose", default="ad")
    ap.add_argument("--aspect")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--region", help="left,top,right,bottom as percentages — the only part that may change")
    ap.add_argument("--model", help="force one image model (a declared row)")
    ap.add_argument("--ref", action="append", default=[], help="another reference picture on this machine")
    ap.add_argument("--label")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fixes", action="store_true", help="print the fixes library and stop")
    a = ap.parse_args()

    if a.fixes:
        table, path = RE.fixes()
        print(f"# fixes — {path.name}\n")
        for r in table.values():
            print(f"{r['id']:<11} {r['name']}  [{r['status']}]\n  {r['what']}\n  delta: {r['delta']}"
                  + (f"\n  needs: {', '.join(r['needs'])}" if r.get('needs') else "") + "\n")
        return
    if not a.picture or not a.brand:
        raise SystemExit("a picture and --brand are required")

    req = {"brand": a.brand, "picture": a.picture, "kind": a.kind, "purpose": a.purpose,
           "count": a.count, "dry_run": a.dry_run}
    if a.change:
        req["change"] = a.change
    if a.fix:
        req["fix"] = a.fix
        req["args"] = dict(kv.split("=", 1) for kv in a.arg)
    for k in ("keep", "element"):
        if getattr(a, k):
            req["elements" if k == "element" else k] = getattr(a, k)
    for k in ("product", "aspect", "label", "out", "model", "region"):
        if getattr(a, k):
            req[k] = getattr(a, k)
    if a.ref:
        req["references"] = a.ref

    r = RE.edit(req)
    print(f"{r['state'].upper()}  {r['chars']} chars · {r['changes']} change(s) · v{r['version']}")
    print(f"  reference: {r['picture']}")
    print(f"  {r['instruction']}")
    if r.get("refused"):
        print(f"  ! {r['refused']}")
    for d in r.get("delivered", []):
        print(f"  ✓ {d['file']}")
    for d in r.get("rejected", []):
        print(f"  ✗ {d['file']}  — {'; '.join(d['fails'])}")
    if r.get("drive", {}).get("note"):
        print(f"  {r['drive']['note']}")
    print(f"  record: {Path(r['out']) / 'edit.json'}")


if __name__ == "__main__":
    main()
