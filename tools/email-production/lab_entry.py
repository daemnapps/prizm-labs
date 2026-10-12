#!/usr/bin/python3
"""The mini's door into run_month.py — a lab-run turns a request into this call.

    lab-run → lab_entry.py --month M [--only sep-01,sep-02] [--dry_run yes]

Why it exists (ready.md G1, 2026-09-29): lab-run passes only `--name value`
pairs, but run_month.py wants a month folder as a positional path; run_month.py
writes its runs under WORKSPACE/runs/email-production/, which on the mini is
not this checkout unless AI_WORKSPACE says so, and the worktree dies after the
run, so what the run made is copied into $OUT here; and the shebang above is
absolute, so the mini runs 3.9.6, not whichever python3 is first on PATH.

Words and layout only (the email lead, "pictures on the brand editor's mac", 2026-09-29): the
build always gets --no-images and no OPENAI_API_KEY reaches the child. The
month is read from git (EP-2 (month in the repo), "save the month in the
repo"): runs/marketing-calendar/<brand>/<YYYY-MM>/ with its slots.json,
run.json and review.json (SI-22 (calendar months home)); --month is YYYY-MM or
the legacy calendar-YYYY-MM[-<brand>] label the mini still sends. Prompt dumps (`*--sent.md`) carry brand context and never go to
$OUT (the copywriter S1 lesson). Never --push.

$BRAND and $OUT come from lab-run. Brand context is read from this checkout,
not a clone elsewhere on the machine.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]                   # tools/email-production → repo root
YES = {"yes", "true", "1"}
MONTH_FILES = ("slots.json", "run.json", "review.json")
MINI_CONCURRENCY = 2                     # SI-163 (mini emails two at once): the mini's plan is shared


LEGACY = re.compile(r"calendar-(\d{4}-\d{2})(?:-(.+))?")


def month_dir(repo, month, brand):
    """runs/marketing-calendar/<brand>/<YYYY-MM>/. `month` is "YYYY-MM", or the
    legacy "calendar-YYYY-MM[-<brand>]" label every lab-run record so far sends.
    A legacy label naming another brand than `brand` is a ValueError (main
    returns 2)."""
    m = LEGACY.fullmatch(month)
    if m:
        if m.group(2) and m.group(2) != brand:
            raise ValueError(f"--month {month} names brand {m.group(2)!r}, but $BRAND is {brand!r}")
        month = m.group(1)
    return Path(repo) / "runs" / "marketing-calendar" / brand / month


def month_argv(args, month_path):
    return ([str(HERE / "run_month.py"), str(month_path), "--no-images",
             "--concurrency", str(MINI_CONCURRENCY)]
            + (["--only", args.only] if args.only else []))


def child_env(env, repo):
    env = dict(env)
    env["AI_WORKSPACE"] = str(repo)      # runs land in this checkout, not $AI_WORKSPACE
    env.pop("OPENAI_API_KEY", None)      # no pictures on the mini
    return env


def snapshot(root):
    if not root.is_dir():
        return {}
    return {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}


def main(argv=None, env=None, run=subprocess.call):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--dry_run", default="no")
    args = ap.parse_args(argv)
    brand, out = env.get("BRAND"), env.get("OUT")
    if not brand or not out:
        sys.exit("lab_entry: $BRAND and $OUT are set by lab-run; run run_month.py directly by hand")
    out = Path(out)
    try:
        month = month_dir(REPO, args.month, brand)
    except ValueError as e:
        print(f"lab_entry: {e}")
        return 2
    missing = [n for n in MONTH_FILES if not (month / n).is_file()]
    if missing:
        print(f"lab_entry: {month} lacks {', '.join(missing)} — commit the reviewed month first")
        return 2
    cmd = [sys.executable] + month_argv(args, month)
    if str(args.dry_run).strip().lower() in YES:
        print("dry run — would run: " + " ".join(cmd))
        for n in MONTH_FILES:
            print(f"  found {month / n}")
        return 0
    runs = REPO / "runs" / "email-production" / brand
    before = snapshot(runs)
    rc = run(cmd, env=child_env(env, REPO))
    for path, mtime in sorted(snapshot(runs).items()):
        if before.get(path) == mtime or path.name.endswith("--sent.md"):
            continue                     # untouched, or a prompt dump
        dest = out / path.relative_to(runs)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(path), str(dest))
    return rc


if __name__ == "__main__":
    sys.exit(main())
