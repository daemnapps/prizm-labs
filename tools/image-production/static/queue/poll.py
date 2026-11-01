#!/usr/bin/env python3
"""Poll Higgsfield for each job, download what's ready, hand it to intake."""
import json, subprocess, sys, time, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import queue as Q
CDN = "https://d8j0ntlcm91z4.cloudfront.net/user_36c0fo7ubzgkpamMa7xUa1gvZKf/"
jobs = json.loads((HERE / "inbox/jobs2.json").read_text())
done = json.loads((HERE / "inbox/done2.json").read_text()) if (HERE / "inbox/done2.json").is_file() else {}
(HERE / "inbox/gen").mkdir(exist_ok=True)
# the CDN filename is hf_<yyyymmdd>_<hhmmss>_<job>.png — we do not know the stamp,
# so ask the widget API through the same session the MCP uses: fall back to a
# HEAD sweep over plausible stamps is silly. Instead: the caller supplies urls.
urls = json.loads((HERE / "inbox/results2.json").read_text()) if (HERE / "inbox/results2.json").is_file() else {}
for iid, url in urls.items():
    if done.get(iid) == url: continue
    out = HERE / "inbox/gen" / f"{iid}.png"
    try:
        subprocess.run(["curl", "-sfL", "-o", str(out), url], check=True)
        Q.intake(iid, out)
        done[iid] = url
        (HERE / "inbox/done2.json").write_text(json.dumps(done, indent=1))
    except Exception as e:
        Q.log(f"poll {iid}: {e}")
Q.log(f"poll: {len(done)}/{len(jobs)} filed")
