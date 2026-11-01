#!/usr/bin/env python3
"""The shared work list — every ad waiting for the chain, which machine has it, and what came out.

    python3 tools/work_list.py add <run> --brand brand-a --preset native-unaware --level unaware [--product flex]
    python3 tools/work_list.py list --brand brand-a
    python3 tools/work_list.py next --brand brand-a --who <machine or person>      claim the next open ad
    python3 tools/work_list.py done <run> --brand brand-a --state delivered|held [--why "..."]
    python3 tools/work_list.py open <run> --brand brand-a                           put it back on the list

the owner, 2026-10-23: "if they start something, I can pick it right up. If I start
something, they can pick it right up ... as long as there is a technically alive
computer session running with those login credentials, then we can just leave it
on all the time." One list per brand at runs/image-teardown/<brand>/queue.json;
`tools/worker.py` is the always-on reader. Unaware and problem-aware ads are
claimed first (the owner, same day: "let's just crush top of funnel and problem
aware all day long"). A claim older than CLAIM_HOURS is taken back, so a machine
that goes to sleep mid-ad never strands it.
"""
import argparse, json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P  # noqa: E402

ORDER = ["unaware", "problem-aware", "solution-aware", "product-aware", "black-friday", "cyber-monday", "most-aware"]
CLAIM_HOURS = 3


def path(brand):
    return P.REPO / "runs" / "image-teardown" / brand / "queue.json"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load(brand):
    f = path(brand)
    return json.loads(f.read_text()) if f.is_file() else {"brand": brand, "items": []}


def save(q):
    f = path(q["brand"])
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(q, indent=1) + "\n")


def find(q, run):
    return next((x for x in q["items"] if x["run"] == run), None)


def stale(item):
    t = item.get("claimed_at")
    return bool(t) and datetime.fromisoformat(t) < datetime.now(timezone.utc) - timedelta(hours=CLAIM_HOURS)


def add(brand, run, preset, level, product="flex"):
    q = load(brand)
    if find(q, run):
        return find(q, run)
    item = {"run": run, "preset": preset, "level": level, "product": product, "state": "open",
            "attempts": 0, "added": now()}
    q["items"].append(item)
    save(q)
    return item


def claim(brand, who):
    """The next open ad (top of funnel first) for `who`, marked as theirs; None when the list is empty."""
    q = load(brand)
    for x in q["items"]:
        if x["state"] == "working" and stale(x):
            x["state"] = "open"
    rank = lambda x: (ORDER.index(x["level"]) if x["level"] in ORDER else 99, x.get("attempts", 0), x.get("added", ""))
    free = sorted((x for x in q["items"] if x["state"] == "open"), key=rank)
    if not free:
        save(q)
        return None
    x = free[0]
    x.update(state="working", who=who, claimed_at=now(), attempts=x.get("attempts", 0) + 1)
    save(q)
    return x


def finish(brand, run, state, why=""):
    q = load(brand)
    x = find(q, run)
    if not x:
        sys.exit(f"{run} is not on the {brand} list")
    x.update(state=state, why=why, finished_at=now())
    save(q)
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "list", "next", "done", "open"])
    ap.add_argument("run", nargs="?")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--preset"); ap.add_argument("--level"); ap.add_argument("--product", default="flex")
    ap.add_argument("--who"); ap.add_argument("--state"); ap.add_argument("--why", default="")
    a = ap.parse_args()
    if a.cmd == "add":
        print(json.dumps(add(a.brand, a.run, a.preset, a.level, a.product)))
    elif a.cmd == "list":
        for x in load(a.brand)["items"]:
            print(f"{x['state']:<10} {x['level']:<15} {x['run']}  {x.get('who', '')} {x.get('why', '')}".rstrip())
    elif a.cmd == "next":
        x = claim(a.brand, a.who or "someone")
        print(json.dumps(x) if x else "")
    elif a.cmd == "done":
        print(json.dumps(finish(a.brand, a.run, a.state or "delivered", a.why)))
    elif a.cmd == "open":
        print(json.dumps(finish(a.brand, a.run, "open", a.why)))


if __name__ == "__main__":
    main()
