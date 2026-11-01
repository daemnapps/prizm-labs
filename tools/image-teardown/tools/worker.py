#!/usr/bin/env python3
"""The always-on worker — takes the next ad off the shared list and runs it on this machine's login.

    python3 tools/worker.py --brand brand-a                 keep going until the list is empty, then wait
    python3 tools/worker.py --brand brand-a --once          one ad, then stop
    python3 tools/worker.py --brand brand-a --sync          pull the list before a claim, push it after

the owner, 2026-10-23: "as long as there is a technically alive computer session
running with those login credentials, then we can just leave it on all the
time." Any machine, any person: the model calls go through run-kit's
claude_door, which uses whatever login this machine holds (every Claude login,
then Codex). Per ad: stages 3 → 6 (the brand step with the creative controls,
headlines, picture variations, the brief), then the pictures
(`tools/pictures.py`, which refuses a brief under the never-sterile floor).
A sterile or failed ad goes back on the list for another machine; after
MAX_TRIES it stays held with the reason. The list is
runs/image-teardown/<brand>/queue.json (`tools/work_list.py`); with --sync it moves
between machines through git (pull before a claim, commit + push the list file
alone after).
"""
import argparse, json, socket, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import paths as P  # noqa: E402
import work_list as Q  # noqa: E402

MAX_TRIES = 3
IDLE_SECONDS = 300


def git(*args):
    return subprocess.run(["git", "-C", str(P.REPO), *args], capture_output=True, text=True)


def sync_pull():
    git("pull", "--ff-only", "--quiet")


def sync_push(brand, msg):
    f = Q.path(brand).relative_to(P.REPO)
    git("add", str(f))
    if git("diff", "--cached", "--quiet", "--", str(f)).returncode:
        git("commit", "-q", "-m", msg, "--", str(f))
        git("push", "--quiet")


def product_of(item, run):
    """The ad's product: the work item's, else the brief register's row for the run. Never a typed default (no brand or
    product is named in code)."""
    if item.get("product"):
        return item["product"]
    import json
    try:
        reg = json.loads((ROOT / "briefs.json").read_text())["briefs"]
        return next((r.get("product") for r in reg.values() if r.get("run") == run and r.get("product")), None)
    except (OSError, ValueError, KeyError):
        return None


def run_one(item, brand, log):
    run = item["run"]
    product = product_of(item, run)
    if not product:
        return "failed", "no product for this ad (work item or brief register)"
    log.write(f"\n== {run} ({item['level']}, {item['preset']}) on {socket.gethostname()}\n")
    log.flush()
    r = subprocess.run([sys.executable, str(HERE / "run.py"), run, "3,4,5,6", "--brand", brand,
                        "--product", product, "--controls", item["preset"], "--gates", "warn"],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode:
        return "failed", "the chain stopped (see the worker log)"
    p = subprocess.run([sys.executable, str(HERE / "pictures.py"), run, "--brand", brand,
                        "--product", product, "--count", "1"],
                       cwd=ROOT, capture_output=True, text=True)
    log.write(p.stdout + p.stderr)
    out = p.stdout + p.stderr
    if "never-sterile floor" in out:
        return "sterile", out.strip().splitlines()[-1][-200:]
    if p.returncode:
        return "failed", (out.strip().splitlines() or ["pictures failed"])[-1][-200:]
    # EVERY HANDOFF CHECKED (the owner, 2026-10-25): the piece goes through stage-check, which verifies each step
    # (record filed, brief numbered, pictures matched to the swipe, card, Queue) and acts on what it can fix.
    sc = subprocess.run([sys.executable, str(HERE.parent.parent / "stage-check" / "stage_check.py"), run, "--brand", brand,
                         "--product", product, "--fix", "--want", "1"],
                        cwd=ROOT, capture_output=True, text=True)
    log.write(sc.stdout + sc.stderr)
    return ("delivered" if "delivered" in out and " 0 delivered" not in out else "held"), out.strip().splitlines()[-1][-200:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--who", default=socket.gethostname())
    a = ap.parse_args()
    logf = P.REPO / "runs" / "image-teardown" / a.brand / "worker-logs" / f"{a.who}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    while True:
        if a.sync:
            sync_pull()
        item = Q.claim(a.brand, a.who)
        if a.sync and item:
            sync_push(a.brand, f"queue: {a.who} takes {item['run']}")
        if not item:
            if a.once:
                print("the list is empty")
                return
            time.sleep(IDLE_SECONDS)
            continue
        print(f"{a.who} takes {item['run']} ({item['level']})", flush=True)
        with open(logf, "a") as log:
            state, why = run_one(item, a.brand, log)
        if state in ("sterile", "failed") and item.get("attempts", 0) < MAX_TRIES:
            Q.finish(a.brand, item["run"], "open", f"try {item['attempts']}: {why}")
        else:
            Q.finish(a.brand, item["run"], state, why)
        if a.sync:
            sync_pull()
            sync_push(a.brand, f"queue: {item['run']} {state} ({a.who})")
        print(f"  {state}: {why}", flush=True)
        if a.once:
            return


if __name__ == "__main__":
    main()
