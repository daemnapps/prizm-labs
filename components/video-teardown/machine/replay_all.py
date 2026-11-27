#!/usr/bin/env python3
"""Replay every filed brief through today's chain — spends nothing.

    python3 replay_all.py [--jobs 8] [--out results.json]

Each brief under runs/video-writing/ is played back on the route it was
written for, every model answer taken from what that run really wrote
(test_chain_replay.py does the playing). A brief that stops says where and
why — usually a record written before a check existed.
"""
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C                                            # noqa: E402

ONE = r'''
import sys, json, io, unittest
sys.argv=["x"]
sys.path.insert(0, %r)
import test_chain_replay as T
t = T.Replay("test_each_route_moves_from_step_to_step")
try:
    ok, log, st, answered, missing, filed, _ = t.replay(%r, %r, %r, relax_teardown=%r)
    stages = st.get("stages") or {}
    done = [r.get("name") or k for k, r in stages.items() if r.get("status") == "done"]
    stop = {k: (r.get("why") or r.get("error") or r.get("status")) for k, r in stages.items()
            if r.get("status") not in ("done", "skipped")}
    tail = [l.strip() for l in log.splitlines() if "STOPPED" in l or "no stage" in l][-1:]
    print(json.dumps({"ok": bool(ok) and not stop, "done": done, "stop": stop, "why": tail, "missing": missing}))
except unittest.SkipTest as e:
    print(json.dumps({"ok": None, "skip": str(e)}))
'''


def one(brand, slug, route, relax):
    p = subprocess.run([sys.executable, "-c", ONE % (str(HERE), brand, slug, route, relax)],
                       capture_output=True, text=True, cwd=str(HERE), timeout=900)
    last = [l for l in p.stdout.splitlines() if l.startswith("{")]
    res = json.loads(last[-1]) if last else {"ok": False, "why": [(p.stderr or p.stdout)[-300:]]}
    return {"brief": f"{brand}/{slug}", "route": route, "kind": "brief" if route else "teardown only", **res}


def teardown_bar(brand, slug):
    """Does the filed teardown meet today's detail bar? (None = no record)"""
    import run as R
    f = C.workspace() / "runs" / "video-teardown" / brand / slug / "stages" / "1-teardown.md"
    if not f.is_file():
        return None
    b = f.read_text()
    thin, bad = R.thin_visuals(b), R.off_doctrine_sections(b)
    return "meets it" if not thin and not bad else (
        f"below: {thin} words a shot" if thin else "below: sections not the doctrine's")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--out", default="replay-results.json")
    a = ap.parse_args()
    runs = C.workspace() / "runs" / "video-writing"
    todo = []
    for d in sorted(runs.glob("*/*")):
        st = json.loads((d / "run.json").read_text()) if (d / "run.json").is_file() else {}
        is_brief = (d / "stages" / "5-brief.md").is_file()
        # a brief replays through writing on its own route, over its teardown
        # even when that teardown predates today's bar; a teardown that never
        # reached writing replays as what it is — a teardown, no route
        todo.append((d.parent.name, d.name,
                     (st.get("production_route") or "creator") if is_brief else None, is_brief))
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda t: one(*t), todo))
    for r in res:
        r["teardown_bar"] = teardown_bar(*r["brief"].split("/"))
    Path(a.out).write_text(json.dumps(res, indent=1))
    for kind in ("brief", "teardown only"):
        rs = [r for r in res if r["kind"] == kind]
        print(f"{kind}: {sum(1 for r in rs if r.get('ok'))} of {len(rs)} moved step to step to the end")


if __name__ == "__main__":
    main()
