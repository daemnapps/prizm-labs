#!/usr/bin/env python3
"""progress.py — the live progress page: every chain run in flight, step by step, with the hooks as soon as they land.

the owner, 2026-10-09: "show me the progress page for these as well, so I can always see them in real time. We're going to
move towards a model of actually having visibility into what we're doing."

    python3 progress.py            # writes progress.json every 5 s beside progress.html (served with the board, :8777)
    python3 progress.py --once     # write it once and stop

A run is IN FLIGHT when one of its steps started or finished in the last 12 hours. Reads each run's own
run.json (stage status, times) and, once the hooks step is done, its labelled hook slots (TAKE · LINE · CARD · SCROLL ·
THUMB, hooks v22). Writes nothing anywhere else. Brand-agnostic: the brand is whatever the run says.
"""
import json, re, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C  # noqa: E402

OUT = HERE / "progress.json"
WINDOW = timedelta(hours=12)
SLOTS = ("TAKE", "LINE", "CARD", "SCROLL", "THUMB")
HOLD_NOTES = ("HOOK-FORMAT.md", "AUDIT-HOLD.md", "STRUCTURE-CHECK.md", "SWIPE-MATCH.md", "CAST-MATCH.md")


def ts(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def slot(body, label):
    m = re.search(rf"^[\s>*`_-]*{re.escape(label)}\s*[*`_]*\s*:\s*[*`_]*\s*(.+?)\s*[*`_]*\s*$", body, re.M)
    return m.group(1).strip().strip("`*_ ") if m else None


def hooks(d, st):
    s = (st.get("stages") or {}).get("stage4b") or {}
    f = d / (s.get("out") or "stages/4b-hooks.md")
    if s.get("status") not in ("done", "held") or not f.is_file():
        return []
    body = f.read_text()
    rows = []
    for v in range(6):
        r = {sl.lower(): slot(body, f"{sl} V{v}") for sl in SLOTS}
        if any(r.values()):
            rows.append({"v": v, **r})
    return rows


def run_row(d, now):
    try:
        st = json.loads((d / "run.json").read_text())
    except Exception:
        return None
    stages = st.get("stages") or {}
    steps, latest = [], None
    for k, s in stages.items():
        stat = s.get("status") or "waiting"
        if stat == "skipped":
            continue
        fin, sta = ts(s.get("finished")), ts(s.get("started"))
        latest = max([x for x in (latest, fin, sta) if x], default=latest)
        steps.append({"key": k, "name": s.get("name") or k, "status": stat,
                      "started": s.get("started"), "finished": s.get("finished")})
    if not (latest and now - latest < WINDOW):      # a "running" step from days ago is a run that died, not one in flight
        return None
    brief = d / "stages" / "5-brief.md"
    title = None
    if brief.is_file():
        m = re.search(r"^# (.+)$", brief.read_text(), re.M)
        title = m.group(1).strip() if m else None
    holds = [n for n in HOLD_NOTES if (d / n).is_file()]
    return {"label": st.get("label") or d.name, "brand": st.get("brand"), "route": (st.get("route") or {}).get("lane")
            if isinstance(st.get("route"), dict) else st.get("route"), "opening_at": st.get("opening_at"),
            "title": title, "steps": steps, "holds": holds, "hooks": hooks(d, st),
            "updated": latest.isoformat() if latest else None}


def build():
    now = datetime.now(timezone.utc)
    rows = [r for d in sorted(C.runs_root().iterdir()) if d.is_dir() and (r := run_row(d, now))]
    rows.sort(key=lambda r: r["updated"] or "", reverse=True)
    OUT.write_text(json.dumps({"at": now.isoformat(), "runs": rows}, indent=1, ensure_ascii=False))
    return rows


if __name__ == "__main__":
    if "--once" in sys.argv:
        print(f"{len(build())} run(s) in flight → {OUT}")
    else:
        while True:
            try:
                build()
            except Exception as e:                      # never die on one bad run.json mid-write
                print("progress:", e, file=sys.stderr)
            time.sleep(5)
