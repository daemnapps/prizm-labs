#!/usr/bin/env python3
"""job-meter: runs the scheduled jobs in a job list, holds each to its money cap, and keeps one ledger of every run.

    meter.py run  --jobs FILE [--only ID[,ID]] [--dry-run]    run every job due today, in list order
    meter.py show --jobs FILE [--days 30] [--json]            per job: runs, ok, model, money, minutes, last result

The job list is private (it names brands and folders) and lives outside this repo. Its shape is in README.md.
One ledger line per job per brand: when, how long, how it ended, the model it uses, what it spent, the cap.

Money guard: a job with `cap_usd` names a `meter` (apify, adplexity). Before it runs, the meter is read. A meter that
cannot be read means the job does not run (never spend blind). If the month's room left is under the cap plus the
floor, it does not run. After it runs, the meter is read again and the difference is the spend on its ledger line.
A job never calls an ad platform for numbers here: those come from the warehouse, inside the job itself.

Exit codes a job may use: 0 done, 3 skipped on purpose (nothing to do, or a guard said no). Anything else is failed.
Python 3.9, standard library only.
"""
import argparse, datetime as dt, json, os, sqlite3, subprocess, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TODAY = dt.date.today()


# ------------------------------------------------------------------ meters: what a paid service says is used this month
def meter_apify(cfg):
    """(used_usd, limit_usd) this billing cycle, from the account's own limits page, or (None, None)."""
    tok = os.environ.get(cfg.get("token_env", "APIFY_TOKEN"))
    if not tok:
        return None, None
    try:
        req = urllib.request.Request("https://api.apify.com/v2/users/me/limits", headers={"Authorization": "Bearer " + tok})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)["data"]
        return round(d["current"]["monthlyUsageUsd"], 2), round(d["limits"]["maxMonthlyUsageUsd"], 2)
    except Exception:
        return None, None


def meter_adplexity(cfg):
    """(used_usd, limit_usd) this calendar month, from the sweep client's own call log (credits priced per plan)."""
    db = cfg.get("db")
    if not db or not Path(db).is_file():
        return None, None
    try:
        con = sqlite3.connect(db)
        usd = con.execute("select coalesce(sum(cost_usd),0) from scan_runs where source like 'adplexity%' and ran_at >= ?",
                          (TODAY.replace(day=1).isoformat(),)).fetchone()[0]
        return round(usd, 2), float(cfg.get("month_usd", 99.0))
    except Exception:
        return None, None


METERS = {"apify": meter_apify, "adplexity": meter_adplexity}


def read_meter(job):
    m = job.get("meter")
    if not m:
        return None, None
    return METERS[m["kind"]](m)


# ------------------------------------------------------------------ the list
def load(path):
    doc = json.loads(Path(path).read_text())
    for j in doc.get("jobs", []):
        if j.get("meter") and j["meter"].get("kind") not in METERS:
            raise SystemExit("job %s: meter %r is not one this tool reads (%s)" % (j["id"], j["meter"].get("kind"), ", ".join(METERS)))
    return doc


def due(job):
    every = str(job.get("every", "daily"))
    if every == "daily":
        return True
    kind, _, arg = every.partition(":")
    if kind == "weekly":
        return TODAY.strftime("%a").lower().startswith(arg.lower()[:3])
    if kind == "monthly":
        return TODAY.day == int(arg or 1)
    return False


def fill(parts, brand, job):
    v = {"today": TODAY.isoformat(), "yesterday": (TODAY - dt.timedelta(days=1)).isoformat(),
         "brand": brand or "", "cap": str(job.get("cap_usd", "")), "python": sys.executable}
    out = []
    for p in parts:
        s = str(p)
        for k, x in v.items():
            s = s.replace("{%s}" % k, x)
        while "{days_ago:" in s:
            a = s.index("{days_ago:"); b = s.index("}", a)
            s = s[:a] + (TODAY - dt.timedelta(days=int(s[a + 10:b]))).isoformat() + s[b + 1:]
        out.append(s)
    return out


def ledger_path(doc, jobs_file):
    p = Path(os.path.expanduser(doc.get("ledger") or "ledger.jsonl"))
    return p if p.is_absolute() else Path(jobs_file).resolve().parent / p


def write(ledger, row):
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as f:
        f.write(json.dumps(row) + "\n")


# ------------------------------------------------------------------ run
def run_one(job, brand, ledger, dry):
    row = {"job": job["id"], "brand": brand, "started": dt.datetime.now().isoformat(timespec="seconds"),
           "model": job.get("model", "none"), "cap_usd": job.get("cap_usd")}
    before, limit = read_meter(job)
    if job.get("cap_usd") is not None:
        if before is None:
            row.update(status="skipped", why="the %s meter could not be read, so nothing was spent" % job["meter"]["kind"])
            return row if dry else (write(ledger, row) or row)
        room = limit - before
        if room < job["cap_usd"] + float(job.get("floor_usd", 0)):
            row.update(status="skipped", why="only $%.2f of $%.2f left this month" % (room, limit))
            return row if dry else (write(ledger, row) or row)
    cmd = fill(job["cmd"], brand, job)
    if dry:
        row.update(status="would run", cmd=" ".join(cmd))
        return row
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=os.path.expanduser(job.get("cwd", ".")), capture_output=True, text=True,
                           timeout=int(job.get("timeout_min", 60)) * 60, stdin=subprocess.DEVNULL)
        code, text = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        code, text = 124, "stopped at its %s-minute limit" % job.get("timeout_min", 60)
    lines = [x for x in text.strip().splitlines() if x.strip()]
    row.update(minutes=round((time.time() - t0) / 60, 1), exit=code,
               status="done" if code == 0 else "skipped" if code == 3 else "failed", last=(lines[-1] if lines else "")[:300])
    if job.get("meter"):
        after, _ = read_meter(job)
        if before is not None and after is not None:
            row["spent_usd"] = round(after - before, 2)
            if job.get("cap_usd") is not None and row["spent_usd"] > job["cap_usd"]:
                row["over_cap"] = True
    write(ledger, row)
    return row


def cmd_run(a):
    doc = load(a.jobs)
    ledger = ledger_path(doc, a.jobs)
    only = set(a.only.split(",")) if a.only else None
    env = doc.get("env") or {}
    os.environ.update({k: os.path.expanduser(str(v)) for k, v in env.items()})
    bad = 0
    for job in doc.get("jobs", []):
        if job.get("off") or (only and job["id"] not in only) or (not only and not due(job)):
            continue
        for brand in job.get("brands") or [None]:
            row = run_one(job, brand, ledger, a.dry_run)
            bad += row["status"] == "failed"
            print("%-18s %-10s %-9s %s" % (job["id"], brand or "", row["status"],
                  row.get("why") or row.get("cmd") or "%s min · %s" % (row.get("minutes"), row.get("last", ""))[:160]))
    return 1 if bad else 0


# ------------------------------------------------------------------ show
def summary(doc, ledger, days):
    since = (TODAY - dt.timedelta(days=days)).isoformat()
    rows = []
    if ledger.is_file():
        for line in ledger.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("started", "") >= since:
                rows.append(r)
    out = []
    for job in doc.get("jobs", []):
        mine = [r for r in rows if r["job"] == job["id"]]
        last = mine[-1] if mine else {}
        out.append({"job": job["id"], "what": job.get("what", ""), "every": job.get("every", "daily"),
                    "at": doc.get("at", ""), "where": doc.get("where", ""), "off": bool(job.get("off")),
                    "model": job.get("model", "none"), "cap_usd": job.get("cap_usd"),
                    "runs": len(mine), "done": sum(r["status"] == "done" for r in mine),
                    "failed": sum(r["status"] == "failed" for r in mine),
                    "skipped": sum(r["status"] == "skipped" for r in mine),
                    "spent_usd": round(sum(r.get("spent_usd") or 0 for r in mine), 2),
                    "minutes": round(sum(r.get("minutes") or 0 for r in mine), 1),
                    "last_status": last.get("status"), "last_at": last.get("started"),
                    "last": last.get("why") or last.get("last")})
    return {"days": days, "from": since, "to": TODAY.isoformat(), "jobs": out,
            "spent_usd": round(sum(j["spent_usd"] for j in out), 2), "minutes": round(sum(j["minutes"] for j in out), 1)}


def cmd_show(a):
    doc = load(a.jobs)
    s = summary(doc, ledger_path(doc, a.jobs), a.days)
    if a.json:
        print(json.dumps(s, indent=1))
        return 0
    print("last %d days · $%.2f · %.1f min" % (a.days, s["spent_usd"], s["minutes"]))
    for j in s["jobs"]:
        print("%-18s %-14s runs %-3d ok %-3d fail %-3d $%-7.2f %6.1f min  %s" % (
            j["job"], j["model"], j["runs"], j["done"], j["failed"], j["spent_usd"], j["minutes"], j["last_status"] or "never run"))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="do", required=True)
    r = sub.add_parser("run"); r.add_argument("--jobs", required=True); r.add_argument("--only"); r.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("show"); s.add_argument("--jobs", required=True); s.add_argument("--days", type=int, default=30); s.add_argument("--json", action="store_true")
    a = ap.parse_args()
    return cmd_run(a) if a.do == "run" else cmd_show(a)


if __name__ == "__main__":
    sys.exit(main())
