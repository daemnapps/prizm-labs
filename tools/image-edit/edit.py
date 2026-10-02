#!/usr/bin/env python3
"""image-edit — fix one thing on a finished picture.

    python3 tools/image-edit/edit.py <picture> --brand <brand> --change "the tube is in her left hand"
    python3 tools/image-edit/edit.py <picture> --brand <brand> --fix logo
    python3 tools/image-edit/edit.py <picture> --brand <brand> --fix layout --arg element="the badge" --arg where="top right"
    python3 tools/image-edit/edit.py <picture> --brand <brand> --fix product --product <slug>
    python3 tools/image-edit/edit.py --fixes                          # the library, verbatim
    python3 tools/image-edit/edit.py --ingest <run folder> --results results.json

The first form writes `job.json` beside the record — the instruction exactly
as it is sent, the model, the frame, the references in order — and spends
nothing. The session generates the job on Higgsfield, writes
`{slug: picture}` into a results file, and `--ingest` judges each picture
against the reference and files it: a new version, or held under rejected/.
`--ingest` takes a vary or sequence folder too.

`--dry-run` resolves everything and prints the instruction; no job is
written. The original picture is never written to.
"""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import image_edit as RE  # noqa: E402


def show_ingest(s):
    for d in s["ingested"]:
        mark = "✓" if d["delivered"] else "✗"
        print(f"  {mark} {d['slug']}  {d['state']}")
        for f in d["delivered"]:
            print(f"      {f}")
        for f in d["rejected"]:
            print(f"      held: {f}")
    for w in s["waiting"]:
        print(f"  … {w}  still waiting for its picture")


def show_ready(r):
    j = r.get("job") or {}
    print(f"  job: {Path(r['out']) / 'job.json'}")
    print(f"  make it on Higgsfield: {j.get('model')} at {j.get('aspect_ratio')}, "
          f"{len(j.get('references', []))} reference(s), the reference first")
    if j.get("finish"):
        print(f"  then finish to 9:16 with skills/{j['finish']}.md")
    print(f"  then: edit.py --ingest {r['out']} --results <results.json>")


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
    ap.add_argument("--aspect")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--region", help="left,top,right,bottom as percentages — the only part that may change")
    ap.add_argument("--model", help="a different Higgsfield model for this edit")
    ap.add_argument("--ref", action="append", default=[], help="another reference picture on this machine")
    ap.add_argument("--label")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fixes", action="store_true", help="print the fixes library and stop")
    ap.add_argument("--ingest", metavar="FOLDER", help="bring a run's pictures back and judge them")
    ap.add_argument("--results", help="with --ingest: {slug: picture} as json")
    a = ap.parse_args()

    if a.fixes:
        table, path = RE.fixes()
        print(f"# fixes — {path.name}\n")
        for r in table.values():
            print(f"{r['id']:<11} {r['name']}  [{r['status']}]\n  {r['what']}\n  delta: {r['delta']}"
                  + (f"\n  needs: {', '.join(r['needs'])}" if r.get('needs') else "") + "\n")
        return
    if a.ingest:
        if not a.results:
            raise SystemExit("--ingest needs --results <results.json>")
        show_ingest(RE.ingest(a.ingest, a.results))
        return
    if not a.picture or not a.brand:
        raise SystemExit("a picture and --brand are required")

    req = {"brand": a.brand, "picture": a.picture, "kind": a.kind,
           "count": a.count, "dry_run": a.dry_run}
    if a.change:
        req["change"] = a.change
    if a.fix:
        req["fix"] = a.fix
        req["args"] = dict(kv.split("=", 1) for kv in a.arg)
    if a.keep:
        req["keep"] = a.keep
    if a.element:
        req["elements"] = a.element
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
    if r["state"] == "ready":
        show_ready(r)
    print(f"  record: {Path(r['out']) / 'edit.json'}")


if __name__ == "__main__":
    main()
