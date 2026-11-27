#!/usr/bin/env python3
"""spend.py — where the Higgsfield credits go, and a stop on a call bigger than its ruled size.

    python3 components/generative-model-house/spend.py [--days 30] [--json]     the meter: read-only, spends nothing

The meter reads the signed-in account's own transactions through the `higgsfield` command line: credits by tool (after
refunds), single charges over the flag, and what the total costs at the rate in spend_limits.json.

Called by a door before it sends a paid call, each raising Refused with nothing spent:
`check(job_type, params)`     a resolution above spend_limits.json
`inputs(prompt, files)`       a file that is not there, a picture number the call does not carry, or words that leave
                              the product out ("laid on at the edit", "grip left open for")
`once(job_type, params, files)`  the same request (same words, same settings, same file bytes) already paid for; a remake
                              changes an input. Returns the request's fingerprint for `record`.
`record(...)`                 after the call: one line in runs/generative-model-house/_system/spend/<month>.jsonl with the
                              job, the fingerprint and the file it made, so every paid call is tied to its ad.
A person's yes lets one run through: UPRIGHT_SPEND_OK="<who said yes, and to what>". Nothing here changes a call or picks
a model. Python 3.9, standard library, no key: the command line is signed in.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIZES = ("360p", "480p", "540p", "720p", "768p", "1080p", "2k", "4k")


class Refused(RuntimeError):
    pass


def limits():
    return json.loads((HERE / "spend_limits.json").read_text())


def _size(name):
    name = str(name or "").strip().lower()
    return SIZES.index(name) if name in SIZES else None


def check(job_type, params):
    """Refuse a call above its ruled size. Unknown job or unnamed resolution: nothing to check."""
    rule = limits()["jobs"].get(job_type)
    if not rule:
        return
    asked, most = _size(params.get("resolution")), _size(rule["max_resolution"])
    if asked is None or most is None or asked <= most:
        return
    if os.environ.get("UPRIGHT_SPEND_OK", "").strip():
        return
    raise Refused("REFUSED before sending, nothing spent: {} at {} is above its limit of {} ({}). A person's yes lets "
                  "one run through: UPRIGHT_SPEND_OK=\"<who said yes>\".".format(
                      job_type, params.get("resolution"), rule["max_resolution"], rule["why"]))


def _yes():
    return bool(os.environ.get("UPRIGHT_SPEND_OK", "").strip())


def inputs(prompt, images=(), others=()):
    """Nothing may be missing from a paid call (2026-11-25). `images` in the order the prompt numbers them, or None when
    the caller's numbering is not known here; `others` = voice and video files."""
    bad = ["the file is not there: " + Path(str(f)).name for f in list(images or []) + list(others or [])
           if not str(f).startswith("http") and not re.fullmatch(r"[0-9a-f-]{36}", str(f)) and not Path(str(f)).is_file()]
    words = re.compile("|".join(limits()["words_that_leave_the_product_out"]), re.I).search(prompt or "")
    if words:
        bad.append("the words leave the product out: " + words.group(0))
    if bad and not _yes():
        raise Refused("REFUSED before sending, nothing spent: " + "; ".join(bad))


def _ledger():
    if os.environ.get("UPRIGHT_SPEND_LEDGER"):
        return Path(os.environ["UPRIGHT_SPEND_LEDGER"])
    sys.path.insert(0, str(HERE.parent / "run-kit"))
    try:
        from run_kit import paths
    finally:
        sys.path.pop(0)
    return paths.repo(str(HERE)) / "runs" / "generative-model-house" / "_system" / "spend"


def fingerprint(job_type, params, files=()):
    h = hashlib.sha256(json.dumps([job_type, params], sort_keys=True, default=str).encode())
    for f in files or []:
        h.update(Path(str(f)).read_bytes() if Path(str(f)).is_file() else str(f).encode())
    return h.hexdigest()


def paid(fp):
    """The ledger row of the same request already paid for, or None."""
    for f in sorted(_ledger().glob("*.jsonl"), reverse=True)[:2]:
        for line in f.read_text().splitlines():
            if fp in line:
                return json.loads(line)
    return None


def once(job_type, params, files=()):
    """The same request is never paid for twice: a remake changes an input (the words, a picture, a setting)."""
    fp = fingerprint(job_type, params, files)
    row = paid(fp)
    if row and not _yes():
        raise Refused("REFUSED before sending, nothing spent: this exact request was already paid for on {} (job {}, {}). "
                      "Change the input that was wrong, then make it again.".format(row["at"], row["job"], row["out"]))
    return fp


def record(job_type, fp, job, out):
    """One paid call, tied to what it made. Never stops the work: the call is already paid for."""
    try:
        now = datetime.now(timezone.utc)
        led = _ledger()
        led.mkdir(parents=True, exist_ok=True)
        parts = Path(str(out)).parts
        here = "/".join(parts[parts.index("runs"):]) if "runs" in parts else Path(str(out)).name
        with (led / (now.strftime("%Y-%m") + ".jsonl")).open("a") as f:
            f.write(json.dumps({"at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "job_type": job_type, "job": job, "out": here,
                                "fp": fp, "yes": os.environ.get("UPRIGHT_SPEND_OK") or None}) + "\n")
    except (OSError, ValueError):
        pass


def _page(offset):
    exe = shutil.which("higgsfield")
    if not exe:
        raise RuntimeError("the higgsfield command line is not installed on this machine")
    argv = [exe, "account", "transactions", "--size", "100", "--json"] + (["--cursor", str(offset)] if offset else [])
    r = subprocess.run(argv, capture_output=True, text=True, timeout=90)
    try:
        got = json.loads(r.stdout)
    except ValueError:
        raise RuntimeError("could not read the account's transactions: " + (r.stderr or r.stdout).strip()[:200])
    return got if isinstance(got, list) else got.get("items") or []


def read(since, page=_page, most_pages=400):
    """Every transaction since an ISO time, newest first."""
    rows, n = [], 0
    while n < most_pages:
        got = page(n * 100)
        rows += [r for r in got if r["created_at"] >= since]
        if len(got) < 100 or got[-1]["created_at"] < since:
            return rows
        n += 1
    raise RuntimeError("stopped at {} pages: the period is longer than the meter reads".format(most_pages))


def report(rows, lim=None):
    lim = lim or limits()
    tool, count, day, back, big = (collections.Counter() for _ in range(5))
    bought = 0.0
    for r in rows:
        c, name = float(r["credits"]), r["display_name"]
        if r["action"] == "spend":
            tool[name] -= c
            count[name] += 1
            day[r["created_at"][:10]] -= c
            if -c > lim["flag_one_charge_over"]:
                big[(r["created_at"][:10], name, -c)] += 1
        elif r["action"] == "refund":
            tool[name] -= c
            back[name] += c
            day[r["created_at"][:10]] -= c
        elif r["action"] == "grant" and "top-up" in name.lower():
            bought += c
    total = sum(tool.values())
    return {"credits": round(total, 2), "usd": round(total * lim["credit_usd"]["value"], 2), "refill_credits": bought,
            "tools": [{"tool": k, "credits": round(v, 2), "share": round(100 * v / total, 1) if total else 0,
                       "calls": count[k], "refunded": round(back[k], 2)} for k, v in tool.most_common()],
            "days": {k: round(v, 2) for k, v in sorted(day.items())},
            "big": [{"day": d, "tool": t, "credits": c, "times": n} for (d, t, c), n in sorted(big.items())]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    since = (datetime.now(timezone.utc) - timedelta(days=a.days)).strftime("%Y-%m-%dT%H:%M:%S")
    rep = report(read(since))
    if a.json:
        print(json.dumps(rep, indent=1))
        return 0
    print("{:,.0f} credits in {} days (${:,.0f} at the refill rate; {:,.0f} bought as refills)".format(
        rep["credits"], a.days, rep["usd"], rep["refill_credits"]))
    for t in rep["tools"][:12]:
        print("  {:34s} {:9,.0f}  {:5.1f}%  {:5d} calls".format(t["tool"], t["credits"], t["share"], t["calls"]))
    for b in rep["big"]:
        print("  one charge over the flag: {} {} {:g} credits x{}".format(b["day"], b["tool"], b["credits"], b["times"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
