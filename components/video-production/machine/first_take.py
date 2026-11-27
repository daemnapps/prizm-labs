#!/usr/bin/env python3
"""How many shots landed on the first take, and why the rest did not.

Reads each run's clip ledger and writes nothing to it. A shot is one call and its retakes
(G01-C1, G01-C1-t2, G01-C1-bk). It passed first time when only one take exists, or the take
picked is the first. Reasons come from the chain's own checks on each take; takes rejected
by eye carry no reason here.

    python3 first_take.py <run folder> [more run folders] [--json] [--out file]
"""
import collections
import json
import re
import sys
from pathlib import Path

GOOD_LINE = {"PASS", "CLEAN", "OK", "CLOSE"}


def shots(ledger):
    grouped = collections.defaultdict(list)
    for cid, row in ledger.items():
        if isinstance(row, dict):
            grouped[re.sub(r"-(t\d+|bk\d*)$", "", cid)].append((cid, row))
    return grouped


KINDS = (
    ("hands", ("hand", "finger", "grip", "tap")),
    ("object appeared or changed", ("appears", "vanish", "clips through", "label", "magically", "opposite")),
    ("words", ("words:",)),
    ("direction not played", ("missing", "static", "does not", "instead of")),
)


def kind(check):
    low = check.lower()
    return next((name for name, marks in KINDS if any(m in low for m in marks)), "other")


def judged(row):
    """The kept take's failed checks, each sentence counted as one kind of fault."""
    got = []
    for check in row.get("failed_checks") or []:
        for part in re.split(r";\s*|(?<=\.)\s+", check.replace("clip judge:", "")):
            if part.strip():
                got.append(kind(part if not check.startswith("words:") else check))
    return got


def reasons(row):
    got = judged(row)
    line = row.get("line_check") or {}
    verdict = str(line.get("verdict") or "").upper()
    if verdict and verdict not in GOOD_LINE:
        got.append("words: " + verdict.lower().replace("_", " "))
    if (row.get("face_lock") or {}).get("ok") is False:
        got.append("face changed")
    if row.get("status") not in (None, "done"):
        got.append("take failed: " + str(row.get("status")))
    return got


def report(run):
    run = Path(run)
    path = run / "clips" / "ledger.json"
    ledger = json.loads(path.read_text())
    out = {"run": run.name, "shots": 0, "first_time": 0, "takes": 0, "seconds": 0.0, "reasons": collections.Counter()}
    for base, takes in shots(ledger).items():
        picked = next((r.get("picked") for _, r in takes if r.get("picked") is not None), None)
        out["shots"] += 1
        out["takes"] += len(takes)
        out["seconds"] += sum(float(r.get("seconds") or 0) for _, r in takes)
        if len(takes) == 1 or str(picked) == "1":
            out["first_time"] += 1
        for _, row in takes:
            out["reasons"].update(reasons(row))
    out["reasons"] = dict(out["reasons"].most_common())
    out["seconds"] = round(out["seconds"], 1)
    return out


def main(argv):
    argv = list(argv)
    out = None
    if "--out" in argv:
        at = argv.index("--out")
        out = Path(argv[at + 1])
        del argv[at:at + 2]
    as_json = "--json" in argv
    rows = [report(a) for a in argv if a != "--json"]
    if out:
        out.write_text(json.dumps(rows[0] if len(rows) == 1 else rows, indent=1) + "\n")
        return
    if as_json:
        print(json.dumps(rows, indent=1))
        return
    for r in rows:
        print(f"{r['run']}: {r['first_time']}/{r['shots']} shots first time · {r['takes']} takes · {r['seconds']}s made")
        for why, n in r["reasons"].items():
            print(f"  {n} × {why}")


if __name__ == "__main__":
    main(sys.argv[1:])
