#!/usr/bin/env python3
"""File a planned month onto the platform's records plane.

    python3 records.py ../../runs/marketing-calendar/<brand>/2026-09
    python3 records.py --all                       # every month in runs/marketing-calendar/

Components rule 3: outputs land as records, so runs are visible and judgeable
on the platform rather than only inside one person's folder. Pointers only —
the month itself stays in its run folder and the record names where that is.
Counts, not content: no slot, no angle, no line of copy passes through here.

Two facts are kept apart on purpose. A month that PLANNED cleanly and a month
a human has finished REVIEWING are different things, and a dashboard that
collapses them will show a month as ready when nobody has read it.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

import paths
from paths import PLATFORM, RUNS, rel
import board as B
import chain as CH
import review as R

KIND = "calendar-run"
PLANE = PLATFORM / "data" / "records" / KIND


def utc(ts=None):
    d = (datetime.datetime.fromisoformat(ts) if ts
         else datetime.datetime.now(datetime.timezone.utc))
    if d.tzinfo is None:
        d = d.astimezone()
    return d.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def summarise(run_dir):
    run_dir = Path(run_dir)
    slots, state, checks = B.read_run(run_dir)
    breaks, warns = B.split_checks(checks)
    rev = R.load(run_dir)

    counts = {"pending": 0, "approved": 0, "needs_work": 0, "cut": 0,
              "edited": 0, "noted": 0}
    for s in slots:
        r = rev["slots"].get(s["id"], {})
        counts[r.get("status", "pending").replace("-", "_")] += 1
        if r.get("edits"):
            counts["edited"] += 1
        if (r.get("note") or "").strip():
            counts["noted"] += 1

    copy = {}
    for v in rev["copy"].values():
        st = v.get("state", "queued")
        copy[st] = copy.get(st, 0) + 1

    # Through the chain, so the record lists all nine layers in order whether
    # they ran, were carried, or left a named hole — a stage missing from the
    # record and a stage that did not run must never look the same.
    stages = {}
    for s in CH.ordered(state):
        r = s["run"] or {}
        row = {"n": s["n"], "by": s["by"], "status": s["status"],
               "produced": r.get("produced"), "seconds": r.get("seconds")}
        if r.get("prompt_name"):
            row["prompt"] = r["prompt_name"]
            row["prompt_sha256_12"] = r.get("prompt_sha256_12")
        stages[s["key"]] = row

    label = state.get("label") or f"{run_dir.parent.name}-{run_dir.name}"
    status = "ok" if slots and not breaks else ("breaks" if slots else "failed")
    unrecorded = [k for k, v in stages.items() if v["status"] == "unrecorded"]
    verdict = {
        "event": "plan",
        "status": status,
        "brand": state.get("brand"),
        "month": B.month_of(slots, state),
        "slots": len(slots),
        "breaks": len(breaks),
        "warnings": len(warns),
        "stages": stages,
        "unrecorded_stages": unrecorded or None,
        "at": utc(state.get("generated_at")),
        "run_dir": rel(run_dir),
        "board": "board.html" if (run_dir / "board.html").is_file() else None,
    }
    if any(counts.values()):
        verdict["review"] = counts
    if copy:
        verdict["copy"] = copy
    return label, verdict


def file_record(run_dir, reviewer="marketing-calendar"):
    label, verdict = summarise(run_dir)
    PLANE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = PLANE / f"{stamp}--{reviewer}--{label}.json"
    out.write_text(json.dumps(
        {"schema": 1, "kind": KIND, "reviewer": reviewer,
         "item": label, "verdict": verdict}, indent=2) + "\n")
    print(f"  -> {rel(out)}  "
          f"({verdict['slots']} sends · {verdict['breaks']} breaks)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all:
        found = paths.months()
        if not found:
            sys.exit(f"no planned months in {RUNS}")
        for d in found:
            file_record(d)
        return
    if not a.run_dir:
        ap.error("give a run folder, or --all")
    file_record(a.run_dir)


if __name__ == "__main__":
    main()
