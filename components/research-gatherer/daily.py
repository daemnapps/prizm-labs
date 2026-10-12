#!/usr/bin/env python3
"""The daily language pull — every FREE source of our own customers' words,
into each brand's language bank, on a schedule.

Ruled 2026-09-29 (the owner): automate only what costs nothing. The 2026-09-23
"no automatic Apify spend" stands, so nothing here may reach Apify — the run
FAILS CLOSED if anything tries (no commit, exit 3).

    python3 components/research-gatherer/daily.py                 # every brand with a language-pulls.json
    python3 components/research-gatherer/daily.py --brand B        # one brand
    python3 components/research-gatherer/daily.py --dry-run        # pull and count; file, commit, push nothing
    python3 components/research-gatherer/daily.py --no-push        # file and commit in the throwaway checkout; keep it

Per brand, in order:
  1. ownvoice --no-scrape  warehouse ad comments + Gorgias tickets (never the top-ad scrape)
  2. surveys               new Google Form answers
  3. reviews               new store reviews (Junip / Judge.me)
  4. interviews            new transcripts in the brand's inbox
  5. feedback              new answers to the brand's own feedback forms (Klaviyo
                           "Submitted Feedback" events; only brands whose
                           language-pulls.json › feedback is enabled)
then the source registry (language-layer tools/map_sources.py — a proposal the
gatherer's `apply` step writes) and the bank page (tools/bank_page.py ->
runs/language-layer/_system/bank.html + BANK.md).

Where it writes: a THROWAWAY checkout off origin/main, never the main one
(other sessions are live there). Only the files the run produced are staged —
the avatar banks' `language/` folders, the source registry, and the run
records under runs/research/ and runs/language-layer/ — committed, and pushed
with rebase-retry (never force). A rebase that conflicts leaves the checkout
in place and says where; nothing is lost and the cursors did not move on
origin, so the next run pulls the same rows again.

The schedule: a launchd job on the owner's Mac (com.daemn.language-daily, 05:30
local) runs schedule/daemn-language-daily.sh, which reads THIS file from
origin/main so the newest code always runs. Log:
~/Library/Logs/daemn/language-daily.log.
"""
import argparse
import contextlib
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = Path.home() / "Library" / "Logs" / "daemn" / "language-daily.log"
MODES = ("ownvoice", "surveys", "reviews", "interviews", "feedback")
COMMIT_PATHS = (
    re.compile(r"^brands/[^/]+/core-avatars/[^/]+/language/.+\.json$"),
    re.compile(r"^brands/[^/]+/core-avatars/language-sources\.json$"),
    re.compile(r"^runs/research/[^/]+/.+"),
    re.compile(r"^runs/language-layer/.+"),
)
STRIP_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


def log(msg):
    line = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def git(repo, *args, check=True, capture=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=capture, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])}: {(r.stderr or r.stdout).strip()[:300]}")
    return (r.stdout or "").strip()


# ---------------------------------------------------------------- the Apify fence

REACHED = []


class ApifyBlocked(RuntimeError):
    pass


def fence_apify(engine=None):
    """Nothing in this process may reach Apify: its hosts do not resolve, and
    the engine's Apify layer raises. Every attempt is recorded; the run then
    fails closed."""
    import socket
    real = socket.getaddrinfo

    def gai(host, *a, **k):
        if host and "apify" in str(host).lower():
            REACHED.append(str(host))
            raise ApifyBlocked(f"Apify is off in the daily pull ({host})")
        return real(host, *a, **k)
    socket.getaddrinfo = gai
    if engine is not None:
        def blocked(*a, **k):
            REACHED.append("engine.apify_layer")
            raise ApifyBlocked("Apify is off in the daily pull (engine.apify_layer)")
        engine.apify_layer = blocked


# ---------------------------------------------------------------- inside the throwaway checkout

class Tee(io.TextIOBase):
    def __init__(self, *outs):
        self.outs = outs

    def write(self, s):
        for o in self.outs:
            o.write(s)
        return len(s)

    def flush(self):
        for o in self.outs:
            o.flush()


COUNT = re.compile(r"(\d+) pulled · (\d+) already in the bank · (\d+) new")
FILED = re.compile(r"filed (\d+) · dropped (\d+) · held (\d+)")


def brands(ws, named):
    if named:
        return named
    return sorted(p.parent.parent.name for p in (ws / "brands").glob("*/operations/language-pulls.json")
                  if not p.parent.parent.name.startswith("_"))


def run_mode(mode, brand, avatar, dry):
    """One gatherer mode, in this process (so the Apify fence holds), its
    printout captured for the summary."""
    import importlib
    mod = importlib.import_module(f"research_gatherer.{mode}")
    argv = ["--brand", brand] + (["--dry-run"] if dry else [])
    if mode == "ownvoice":
        argv += ["--no-scrape"] + (["--avatar", avatar] if avatar else [])
    buf = io.StringIO()
    rc = None
    with contextlib.redirect_stdout(Tee(sys.stdout, buf)):
        try:
            rc = mod.main(argv)
        except ApifyBlocked as e:
            print(f"  BLOCKED — {e}")
            rc = 3
        except SystemExit as e:
            rc = e.code
        except Exception as e:
            print(f"  FAILED — {type(e).__name__}: {str(e)[:200]}")
            rc = 1
    out = buf.getvalue()
    c = COUNT.search(out)
    f = FILED.search(out)
    missing = [l.strip() for l in out.splitlines() if "MISSING" in l or "HELD" in l or "FAILED" in l or "BLOCKED" in l]
    return dict(mode=mode, rc=rc, pulled=int(c.group(1)) if c else 0, new=int(c.group(3)) if c else 0,
                filed=int(f.group(1)) if f else 0, dropped=int(f.group(2)) if f else 0, held=int(f.group(3)) if f else 0,
                missing=missing[:8], page=(re.search(r"page: (\S+)", out) or [None, None])[1])


def sub(ws, args, label):
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    env["AI_WORKSPACE"] = str(ws)
    r = subprocess.run([sys.executable, *args], cwd=str(ws), env=env, capture_output=True, text=True)
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-6:])
    log(f"  {label}: exit {r.returncode}" + (f"\n{tail}" if tail else ""))
    return r.returncode


def inside(a):
    ws = Path(os.environ.get("AI_WORKSPACE") or HERE.parents[1])
    sys.path.append(str(HERE))
    from research_gatherer import engine   # noqa: E402
    fence_apify(engine)
    from research_gatherer import voicepull as V   # noqa: E402
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d-%H%M")
    summary = dict(run=stamp, dry_run=a.dry_run, brands={})
    for b in brands(ws, a.brand):
        conf = V.brand_json(b)
        avatar = V.avatar_for(b, conf)
        log(f"{b} · avatar {avatar or '?'}")
        res = []
        for m in MODES:
            r = run_mode(m, b, avatar, a.dry_run)
            log(f"  {m}: pulled {r['pulled']} · new {r['new']} · filed {r['filed']} · dropped {r['dropped']} · held {r['held']}"
                + (f" · {' | '.join(r['missing'])}" if r["missing"] else ""))
            res.append(r)
        summary["brands"][b] = res
    if REACHED:
        log(f"FAIL CLOSED — something reached for Apify: {', '.join(sorted(set(REACHED)))}")
        return 3
    if not a.dry_run:
        ll = ws / "tools" / "language-layer" / "tools"
        for b in summary["brands"]:
            sub(ws, [str(ll / "map_sources.py"), "--brand", b], f"{b} source registry")
        mirror = None
        try:
            mirror = (re.search(r"Mirror of (https://\S+)", (ws / "runs/language-layer/_system/BANK.md").read_text()) or [None, None])[1]
        except Exception:
            pass
        page = [str(ll / "bank_page.py")] + sum((["--brand", b] for b in brands(ws, None)), [])
        page += ["--note", f"Daily language pull {stamp}: see runs/research/_system/daily/{stamp}.md"]
        if mirror:
            page += ["--mirror-of", mirror.rstrip(" ·")]
        sub(ws, page, "bank page")
        d = ws / "runs" / "research" / "_system" / "daily"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{stamp}.json").write_text(json.dumps(summary, indent=1) + "\n")
        (d / f"{stamp}.md").write_text(summary_md(summary))
    return 0


def summary_md(s):
    L = [f"# Daily language pull — {s['run']}", "",
         "Free sources only; Apify is fenced off (components/research-gatherer/daily.py).", ""]
    for b, res in s["brands"].items():
        L += [f"## {b}", "", "| Mode | Pulled | New | Filed | Dropped | Held | What could not be read |",
              "|---|---|---|---|---|---|---|"]
        for r in res:
            L.append(f"| {r['mode']} | {r['pulled']} | {r['new']} | {r['filed']} | {r['dropped']} | {r['held']} | "
                     + " / ".join(x.replace("|", "/") for x in r["missing"]) + " |")
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- outside: the throwaway checkout, commit, push

def produced(wt):
    """(files the run produced, anything else it changed) in the throwaway checkout."""
    r = subprocess.run(["git", "-C", str(wt), "status", "--porcelain", "-z", "-uall"], capture_output=True, text=True)
    ok, other = [], []
    for item in r.stdout.split("\0"):
        if len(item) < 4:
            continue
        p = item[3:]   # "XY path" — never strip: the status column can start with a space
        (ok if any(rx.match(p) for rx in COMMIT_PATHS) else other).append(p)
    return ok, other


def push(wt, tries=5):
    for i in range(tries):
        r = subprocess.run(["git", "-C", str(wt), "push", "-q", "origin", "HEAD:main"], capture_output=True, text=True)
        if r.returncode == 0:
            return True, None
        log(f"  push refused (try {i + 1}): {r.stderr.strip()[:160]}")
        git(wt, "fetch", "-q", "origin")
        rb = subprocess.run(["git", "-C", str(wt), "rebase", "--autostash", "origin/main"], capture_output=True, text=True)
        if rb.returncode != 0:
            subprocess.run(["git", "-C", str(wt), "rebase", "--abort"], capture_output=True)
            return False, f"rebase onto origin/main conflicts: {(rb.stdout + rb.stderr).strip()[:200]}"
        time.sleep(3 * (i + 1))
    return False, "push kept being refused"


def outside(a):
    repo = Path(a.repo).expanduser() if a.repo else HERE.parents[1]
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = Path.home() / "Library" / "Caches" / "daemn" / "language-daily"
    base.mkdir(parents=True, exist_ok=True)
    wt = base / f"wt-{stamp}"
    log(f"start{' (DRY RUN)' if a.dry_run else ''} · repo {repo}")
    try:
        git(repo, "fetch", "-q", "origin")
        git(repo, "worktree", "add", "-q", "--detach", str(wt), "origin/main")
    except Exception as e:
        log(f"FAILED — could not make the throwaway checkout: {e}")
        return 1
    head = git(wt, "rev-parse", "--short", "HEAD")
    log(f"throwaway checkout {wt} at origin/main {head}")
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    env["AI_WORKSPACE"] = str(wt)
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    cmd = [sys.executable, str(wt / "components" / "research-gatherer" / "daily.py"), "--inside"]
    cmd += sum((["--brand", b] for b in a.brand or []), []) + (["--dry-run"] if a.dry_run else [])
    rc = subprocess.run(cmd, cwd=str(wt), env=env).returncode
    if rc == 3:
        log(f"FAIL CLOSED — nothing committed; the checkout is kept at {wt}")
        return 3
    if rc != 0:
        log(f"inner run exited {rc} — nothing committed; the checkout is kept at {wt}")
        return rc
    if a.dry_run:
        git(repo, "worktree", "remove", "--force", str(wt), check=False)
        log("dry run — nothing filed, nothing committed")
        return 0
    files, other = produced(wt)
    if other:
        log(f"  not staged (outside what this run may commit): {', '.join(other[:12])}")
    if not files:
        log("no new rows — nothing to commit")
        git(repo, "worktree", "remove", "--force", str(wt), check=False)
        return 0
    try:
        summary = json.loads(sorted((wt / "runs/research/_system/daily").glob("*.json"))[-1].read_text())
    except Exception:
        summary = {"brands": {}}
    lines = []
    for b, res in summary.get("brands", {}).items():
        lines.append(f"{b}: " + ", ".join(f"{r['mode']} {r['filed']} filed" for r in res))
    msg = (f"language(daily): {dt.date.today().isoformat()} — free sources into the banks ({len(files)} file(s))\n\n"
           + "\n".join(lines) + "\n\nRun by components/research-gatherer/daily.py (launchd com.daemn.language-daily); "
           "Apify fenced off. Log: ~/Library/Logs/daemn/language-daily.log\n\n"
           "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    for i in range(0, len(files), 200):
        git(wt, "add", "--", *files[i:i + 200])
    git(wt, "commit", "-q", "-m", msg)
    sha = git(wt, "rev-parse", "--short", "HEAD")
    log(f"committed {len(files)} file(s): {sha}")
    if a.no_push:
        log(f"--no-push: the commit stays in {wt}")
        return 0
    ok, why = push(wt)
    if not ok:
        log(f"PUSH FAILED — {why}; the commit is kept in {wt}")
        return 1
    log(f"pushed {git(wt, 'rev-parse', '--short', 'HEAD')}")
    git(repo, "worktree", "remove", "--force", str(wt), check=False)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="daily.py")
    ap.add_argument("--brand", action="append", help="one brand (repeatable); default every brand with operations/language-pulls.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--repo", help="the checkout to branch the throwaway checkout from (default: the one this file sits in)")
    ap.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    return inside(a) if a.inside else outside(a)


if __name__ == "__main__":
    sys.exit(main())
