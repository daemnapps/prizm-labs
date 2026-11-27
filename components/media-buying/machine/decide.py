#!/usr/bin/env python3
"""decide.py — owner's call on a flag, with his reason, kept forever.

    python3 decide.py brand_b F2 down --why "CPK is new, give it the week"      # latest report
    python3 decide.py brand_b F4 double --why "..." --asof 2026-10-03
    python3 decide.py brand_b --log                                            # every call so far, and how often he agreed
    python3 decide.py <brand> --summary                                        # the same calls as calls.py reads them: every disagreement with its reason

Calls: off · keep · watch · up · down · hold · double · skip (any word he uses is kept as said in `said`).
One line per call in runs/media-buying/<brand>/decisions.jsonl, carrying the flag exactly as it was
shown (numbers, the machine's suggestion), so the lines in desk.json can be retuned from where he
disagreed — always shown to him first, never changed on their own. Recording a call changes nothing
in Meta; act.py does that, only on his go.
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze as A
import calls as CL

CALLS = {"off": "off", "kill": "off", "pause": "off", "keep": "keep", "watch": "watch", "up": "budget_up",
         "down": "budget_down", "hold": "budget_hold", "double": "double_down", "skip": "skip"}


def latest(brand):
    runs = sorted(p for p in A.desk_dir(brand).iterdir() if p.is_dir() and (p / "report.json").exists())
    if not runs:
        raise SystemExit("no report yet — run analyze.py first")
    return runs[-1]


def record(brand, flag, call, why, asof=None, by="owner"):
    run = A.desk_dir(brand) / asof if asof else latest(brand)
    rep = json.loads((run / "report.json").read_text())
    f = next((x for x in rep["flags"] if x["flag"].lower() == flag.lower()), None)
    if not f:
        raise SystemExit(f"{flag} is not in the {rep['asof']} report")
    if not (why or "").strip():
        raise SystemExit("a call needs its reason — that is what the desk learns from")
    line = {"at": datetime.now().isoformat(timespec="seconds"), "by": by, "asof": rep["asof"], "flag": f["flag"],
            "kind": f["kind"], "id": f["id"], "name": f["name"], "suggested": f["action"],
            "call": CALLS.get(call.lower(), call.lower()), "said": call, "why": why.strip(), "agreed": CALLS.get(call.lower()) == ("keep" if f["action"] == "prospect" else f["action"]),
            "numbers": {k: f.get(k) for k in ("spend", "purchases", "cpa", "cpa7", "cpa3", "spend7", "break_even", "share7", "link_rate", "checkouts",
                                              "windows", "freq7", "account_share7") if k in f},
            "lines": rep["rule"] if rep.get("rule") else rep["lines"]}
    with open(A.desk_dir(brand) / "decisions.jsonl", "a") as fh:
        fh.write(json.dumps(line) + "\n")
    return line


def log(brand):
    p = A.desk_dir(brand) / "decisions.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
    by = {}
    for r in rows:
        b = by.setdefault(r["suggested"], {"calls": 0, "agreed": 0, "overruled_to": {}})
        b["calls"] += 1
        b["agreed"] += r["agreed"]
        if not r["agreed"]:
            b["overruled_to"][r["call"]] = b["overruled_to"].get(r["call"], 0) + 1
    return {"calls": len(rows), "by_suggestion": by, "last": rows[-10:]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("brand"); ap.add_argument("flag", nargs="?"); ap.add_argument("call", nargs="?")
    ap.add_argument("--why", default=""); ap.add_argument("--asof"); ap.add_argument("--log", action="store_true")
    ap.add_argument("--summary", action="store_true", help="what the calls say, every disagreement kept (calls.py)")
    a = ap.parse_args(argv)
    if a.summary:
        print(json.dumps(CL.summary(CL.read(A.desk_dir(a.brand) / "decisions.jsonl")), indent=1)); return
    if a.log or not a.flag:
        print(json.dumps(log(a.brand), indent=1)); return
    print(json.dumps(record(a.brand, a.flag, a.call, a.why, a.asof), indent=1))


if __name__ == "__main__":
    main()
