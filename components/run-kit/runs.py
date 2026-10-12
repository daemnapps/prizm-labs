#!/usr/bin/env python3
"""What is in runs/ — every run, every brief, and what is not filed right.

    python3 components/run-kit/runs.py health          how each machine files
    python3 components/run-kit/runs.py briefs [--brand <b>] [--machine <m>]
    python3 components/run-kit/runs.py runs   [--brand <b>] [--machine <m>]

It reads `runs/` and nothing else — no registry, no declaration. A machine that
files to the standard appears here by doing nothing.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from run_kit import index  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("health", "briefs", "runs"))
    ap.add_argument("--brand")
    ap.add_argument("--machine")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.what == "health":
        h = index.health()
        if a.json:
            print(json.dumps(h, indent=1)); return
        tot = sum(d["runs"] for d in h.values())
        filed = sum(d["with_brief"] for d in h.values())
        mis = sum(d["misfiled"] for d in h.values())
        print(f"  {'machine':<22}{'runs':>5}{'filed':>7}{'misfiled':>10}{'no run.json':>13}")
        for m, d in sorted(h.items(), key=lambda kv: -kv[1]["runs"]):
            flag = "  <- briefs nobody else can find" if d["misfiled"] else ""
            print(f"  {m:<22}{d['runs']:>5}{d['with_brief']:>7}{d['misfiled']:>10}{d['no_record']:>13}{flag}")
        print(f"\n  {tot} runs · {filed} briefs filed to the standard · {mis} runs with a brief somewhere else")
        return

    rows = index.briefs(a.brand, a.machine) if a.what == "briefs" else [
        r for r in index.scan()
        if (not a.brand or r["brand"] == a.brand) and (not a.machine or r["machine"] == a.machine)]
    if a.json:
        print(json.dumps(rows, indent=1)); return
    for r in rows:
        if a.what == "briefs":
            mark = " " if r["filed"] else "!"
            print(f"  {mark} {r['machine']:<18} {r['brand']:<9} {r['changed']}  {r['brief']}")
        else:
            print(f"    {r['machine']:<18} {r['brand']:<9} {r['changed']}  {r['label']}"
                  + (f"  [{len(r['briefs'])} brief]" if r["briefs"] else ""))
    if a.what == "briefs":
        bad = sum(1 for r in rows if not r["filed"])
        print(f"\n  {len(rows)} briefs · {bad} marked ! are not in deliverable/ — findable only by reading that machine's code")


if __name__ == "__main__":
    main()
