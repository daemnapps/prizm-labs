#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import queue as Q, finish
plan = {x["id"]: x for x in json.loads((HERE / "inbox/posters.json").read_text())}
res = json.loads((HERE / "inbox/posters_results.json").read_text())
done = json.loads((HERE / "inbox/posters_done.json").read_text()) if (HERE / "inbox/posters_done.json").is_file() else {}
(HERE / "inbox/gen").mkdir(exist_ok=True)
for iid, url in res.items():
    if done.get(iid) == url: continue
    it = plan[iid]; out = HERE / "inbox/gen" / f"{iid}.png"
    subprocess.run(["curl", "-sfL", "-o", str(out), url], check=True)
    ok, r = finish.add_asset(Q.RUNS_ROOT / it["run"], it["slug"], out, it["target"],
                             "device replaced with the FLEX Element (8fad5612) — Damon 2026-09-09", it["source_name"])
    Q.log(f"poster: {iid} -> {'ok ' + r if ok else 'REJECT ' + '; '.join(r)[:100]}")
    if ok: Q.refresh_ocr(Q.RUNS_ROOT / it["run"] / "ads" / it["slug"], r + ".png")
    done[iid] = url; (HERE / "inbox/posters_done.json").write_text(json.dumps(done, indent=1))
Q.log(f"poster intake: {len(done)}/18")
