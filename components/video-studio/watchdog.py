#!/usr/bin/env python3
"""Production watchdog (owner, 20 Nov 2026: "We cannot let these creatives get stuck in production for no real good
reason ever again. We need to scale.").

Runs every 5 minutes. For every Studio production with a Next step job that is not done:
  - the job's process died            -> the job is marked stopped and started again
  - the process is alive but idle      -> no CPU used by it or its children and no file written in its production for
    STUCK_MIN minutes: the process tree is stopped, the job marked "stuck", and started again
Each production gets MAX_RETRIES restarts per stage. After that it is listed in STUCK.json beside the briefs (with the
step and its last words) for the driving session to fix at the cause; it is never retried blindly for ever.

Every action is written to watchdog.log beside the briefs. Stdlib only.
"""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

STUDIO = os.environ.get("VIDEO_STUDIO_URL", "http://127.0.0.1:8922")
BRIEFS = Path(os.environ.get("VIDEO_STUDIO_DATA", str(Path.home() / "devel/daemn/board/scene-canvas"))) / "briefs"
STUCK_MIN = float(os.environ.get("WATCHDOG_STUCK_MIN", "20"))
MAX_RETRIES = int(os.environ.get("WATCHDOG_RETRIES", "2"))
STATE = BRIEFS.parent / "watchdog-state.json"
LOG = BRIEFS.parent / "watchdog.log"
STUCK = BRIEFS.parent / "STUCK.json"


def log(msg):
    with open(LOG, "a") as f:
        f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))


def load(p, default):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def tree(pid):
    """The pid and every descendant."""
    out, todo = [], [pid]
    while todo:
        p = todo.pop()
        out.append(p)
        try:
            kids = subprocess.run(["pgrep", "-P", str(p)], capture_output=True, text=True, timeout=10).stdout.split()
        except (OSError, subprocess.SubprocessError):
            kids = []
        todo += [int(k) for k in kids if k.isdigit()]
    return out


def cpu_seconds(pids):
    """Total CPU time used so far by these processes."""
    if not pids:
        return 0.0
    try:
        rows = subprocess.run(["ps", "-o", "time=", "-p", ",".join(map(str, pids))],
                              capture_output=True, text=True, timeout=10).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return 0.0
    total = 0.0
    for r in rows:                      # [[dd-]hh:]mm:ss.cc
        days = 0
        if "-" in r:
            d, r = r.split("-", 1)
            days = int(d)
        parts = [float(x) for x in r.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0.0)
        total += days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]
    return total


def newest_write(folder):
    newest = 0.0
    for root, _dirs, files in os.walk(folder):
        for f in files:
            try:
                newest = max(newest, os.path.getmtime(os.path.join(root, f)))
            except OSError:
                pass
    return newest


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def restart(n):
    req = urllib.request.Request(STUDIO + "/api/next/" + n, data=b"{}", headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read() or b"{}")
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:200]}


def main():
    state = load(STATE, {})
    stuck = load(STUCK, {})
    now = time.time()
    for f in sorted(BRIEFS.glob("*/next-job.json")):
        n = f.parent.name
        job = load(f, {})
        died = job.get("done") and any(("process ended before it finished" in (s.get("said") or ""))
                                        or ("RemoteDisconnected" in (s.get("said") or ""))      # the Studio restarted under it
                                        or ("Connection refused" in (s.get("said") or ""))
                                        or ("cancelled_parent_exited" in (s.get("said") or ""))
                                        for s in job.get("steps", []))
        if died and (state.get(n) or {}).get("died_job") != job.get("id") and now - f.stat().st_mtime < 6 * 3600:
            r = restart(n)       # the Studio marked it stopped when its process died: start it again, once per job
            state[n] = {"stage": job.get("stage"), "retries": 1, "job": r.get("job"), "since": time.time(),
                        "died_job": job.get("id")}
            log("%s %s died mid-step -> restarted: %s" % (n, job.get("stage"), r))
            continue
        if not job or job.get("done"):
            if not died:
                state.pop(n, None)
            continue
        stage = job.get("stage") or "?"
        pid = int(job.get("pid") or 0)
        rec = state.get(n) or {}
        if rec.get("stage") != stage or rec.get("job") != job.get("id"):
            rec = {"stage": stage, "job": job.get("id"), "retries": rec.get("retries", 0) if rec.get("stage") == stage else 0}
        pids = tree(pid) if pid and alive(pid) else []
        cpu, wrote = cpu_seconds(pids), newest_write(f.parent)
        if pids and (rec.get("cpu") is None or cpu > rec["cpu"] + 0.5 or wrote > rec.get("wrote", 0)):
            rec.update(cpu=cpu, wrote=wrote, since=now)          # it moved: the clock starts again
            state[n] = rec
            continue
        idle_min = (now - rec.get("since", now)) / 60
        if pids and idle_min < STUCK_MIN:
            rec.setdefault("since", now)
            rec.setdefault("cpu", cpu)
            rec.setdefault("wrote", wrote)
            state[n] = rec
            continue
        step = next((s for s in job.get("steps", []) if s.get("state") in ("doing", "waiting")), {})
        why = ("idle %d min (no CPU, no file written)" % idle_min) if pids else "its process ended"
        if rec.get("retries", 0) >= MAX_RETRIES:
            stuck[n] = {"stage": stage, "step": step.get("id"), "said": step.get("said"), "why": why,
                        "retries": rec["retries"], "at": time.strftime("%Y-%m-%d %H:%M")}
            log("%s %s/%s STILL STUCK after %d restarts (%s): listed in STUCK.json" % (n, stage, step.get("id"), rec["retries"], why))
            for p in reversed(pids):
                try:
                    os.kill(p, signal.SIGTERM)
                except OSError:
                    pass
            for s in job.get("steps", []):
                if s.get("state") in ("doing", "waiting"):
                    s["state"], s["said"] = "stopped", "Stuck: %s. Restarted %d times; needs a fix at the cause." % (why, rec["retries"])
            job["done"] = True
            f.write_text(json.dumps(job, indent=1))
            state.pop(n, None)
            continue
        for p in reversed(pids):
            try:
                os.kill(p, signal.SIGTERM)
            except OSError:
                pass
        time.sleep(2)
        for p in pids:
            if alive(p):
                try:
                    os.kill(p, signal.SIGKILL)
                except OSError:
                    pass
        for s in job.get("steps", []):
            if s.get("state") in ("doing", "waiting"):
                s["state"], s["said"] = "stopped", "Watchdog: %s; started again." % why
        job["done"] = True
        f.write_text(json.dumps(job, indent=1))
        r = restart(n)
        rec = {"stage": stage, "retries": rec.get("retries", 0) + 1, "job": r.get("job"), "since": time.time()}
        state[n] = rec
        stuck.pop(n, None)
        log("%s %s/%s %s -> restarted (try %d): %s" % (n, stage, step.get("id"), why, rec["retries"], r))
    advance_idle(state, stuck)
    STATE.write_text(json.dumps(state, indent=1))
    STUCK.write_text(json.dumps(stuck, indent=1))


# RUN TO COMPLETION (owner, 20 Nov: "we need to stop having idle sessions for no reason. everything needs to run to
# completion"). A production worked on in the last ADVANCE_HOURS whose last job finished cleanly IDLE_MIN ago, with a
# free stage due and nothing running, gets that stage started here. Paid stages (AI pictures and clips) and the
# hand-off to the editor are never started by a machine: they wait for a person.
FREE_STAGES = {"songcheck", "songcut", "shots", "cut", "check", "render", "edit"}
IDLE_MIN = float(os.environ.get("WATCHDOG_IDLE_MIN", "10"))
ADVANCE_HOURS = float(os.environ.get("WATCHDOG_ADVANCE_HOURS", "12"))


def due(n):
    try:
        return json.loads(urllib.request.urlopen(STUDIO + "/api/next/" + n, timeout=60).read() or b"{}")
    except Exception:  # noqa: BLE001
        return {}


def advance_idle(state, stuck):
    now = time.time()
    for f in sorted(BRIEFS.glob("*/next-job.json")):
        n = f.parent.name
        job = load(f, {})
        age = (now - f.stat().st_mtime) / 60
        if not job.get("done") or n in stuck or age < IDLE_MIN or age > ADVANCE_HOURS * 60:
            continue
        if any(s.get("state") == "stopped" for s in job.get("steps", [])):
            continue                     # a step that stopped needs its fix first, not a blind next step
        d = due(n)
        stage = d.get("due")
        if d.get("running") or stage not in FREE_STAGES:
            continue
        adv = state.setdefault("_advanced", {}).setdefault(n, {})
        if list(adv) != [stage]:
            adv.clear()                  # a new stage is due: the count is for the same stage over and over only
        if adv.get(stage, 0) >= 2:
            if n not in stuck:           # started twice and still due: it loops, a person fixes the cause
                stuck[n] = {"stage": stage, "why": "due again after 2 automatic starts", "at": time.strftime("%Y-%m-%d %H:%M")}
                log("%s %s still due after 2 automatic starts: listed in STUCK.json" % (n, stage))
            continue
        r = restart(n)
        adv[stage] = adv.get(stage, 0) + 1
        log("%s idle %d min with %s due -> started (%d): %s" % (n, age, stage, adv[stage], r))


if __name__ == "__main__":
    sys.exit(main())
