#!/usr/bin/env python3
"""Download every known result that is not yet filed, and file it."""
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import queue as Q
res = json.loads((HERE / "inbox/results.json").read_text())
q = json.loads((HERE / "queue.json").read_text())["items"]
(HERE / "inbox/gen").mkdir(exist_ok=True)
byid = {i["id"]: i for i in q}
for iid, url in res.items():
    it = byid.get(iid)
    if not it or it["status"] in ("done",) or it.get("filed") == url: continue
    out = HERE / "inbox/gen" / f"{it['id']}.png"
    subprocess.run(["curl", "-s", "-L", "-o", str(out), url], check=True)
    try:
        Q.intake(it["id"], out)
    except SystemExit as e:
        Q.log(f"intake {it['id']}: {e}")
    q2 = json.loads((HERE / "queue.json").read_text())
    for i in q2["items"]:
        if i["id"] == iid: i["filed"] = url
    (HERE / "queue.json").write_text(json.dumps(q2, indent=1, ensure_ascii=False) + "\n")
Q.log("intake_jobs: pass complete")
