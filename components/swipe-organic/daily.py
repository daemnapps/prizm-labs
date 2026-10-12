#!/usr/bin/env python3
"""The daily run — every feed pulls, sifts, follows its winners, saves thumbnails.

    python3 daily.py [--dry-run] [--floor 12]

Runs from launchd each morning (com.daemn.feeds-daily). One line per run lands
in records/desk/daily.jsonl, which is what the page's "daily run" drawer reads.

Money guard: scraping is the only thing here that costs. One morning spends at
most --cap dollars, stalest feeds first. If the Apify account
has less than --floor dollars left in the cycle, the run pulls nothing and
says so — the feeds never eat the budget the other machines need.
"""
import argparse, json, re, subprocess, sys
import desklib as D

DAILY = D.HERE / "records" / "desk" / "daily.jsonl"


def step(*cmd):
    r = subprocess.run([sys.executable, *cmd], cwd=str(D.HERE), capture_output=True, text=True,
                       timeout=6 * 3600)
    return r.returncode == 0, ((r.stdout or r.stderr).strip().splitlines() or [""])[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--floor", type=float, default=3.0)
    ap.add_argument("--cap", type=float, default=40.0, help="most scraping dollars one morning may spend")
    a = ap.parse_args()
    before, cap = D.apify_spend()
    fs = D.feeds()
    print(f"{len(fs)} feeds · scraping ${before} of ${cap} used")
    if a.dry_run:
        for f in fs:
            print(f"  would pull {f['id']} ({f['sources']} sources)")
        return
    rec = {"at": D.now(), "feeds": []}
    if before is not None and cap - before < a.floor:
        rec["feeds"] = [{"feed": "—", "errors": [f"skipped: only ${cap - before:.2f} of scraping left this month"]}]
    else:
        # stalest feed first; stop if the night's money is spent
        fs.sort(key=lambda f: (f["last"] or {}).get("at", ""))
        held = []

        def one(f):
            spent_now, _ = D.apify_spend()
            if before is not None and spent_now is not None and spent_now - before >= a.cap:
                held.append(f["id"])
                return None
            row = {"feed": f["id"], "errors": []}
            ok, line = step("feed.py", "--avatar", f["id"])
            m = re.search(r"new (\d+)", line)
            row["new"] = int(m.group(1)) if m else 0
            if not ok or "errors" in line:
                row["errors"].append(line[-140:])
            if f.get("ask"):
                ok, line = step("sift.py", "--avatar", f["id"])
                m = re.search(r"kept (\d+)", line)
                row["kept"] = int(m.group(1)) if m else 0
            ok, line = step("hops.py", "--avatar", f["id"], "--max", "4")
            if not ok:
                row["errors"].append("follow: " + line[-100:])
            row["covers"] = D.cache_covers(f["id"])
            print(f"  {f['id']}: {row}", flush=True)
            return row

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as pool:      # three feeds at a time
            rec["feeds"] = [r for r in pool.map(one, fs) if r]
        if held:
            rec["held"] = held
            print(f"  night cap ${a.cap} reached — {len(held)} feeds wait for tomorrow")
    # then the brief line: each avatar feed's best untouched post → the teardown chain
    ok, line = step("briefs.py")
    rec["briefs"] = line
    print(f"  briefs: {line}")
    after, _ = D.apify_spend()
    rec["spend"] = round(after - before, 2) if before is not None and after is not None else None
    DAILY.parent.mkdir(parents=True, exist_ok=True)
    with DAILY.open("a") as L:
        L.write(json.dumps(rec) + "\n")
    print(f"done · ${rec['spend']} of scraping")


if __name__ == "__main__":
    main()
