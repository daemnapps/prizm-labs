#!/usr/bin/env python3
"""Make two synthetic Prizm deliveries and four pending jobs. No network or credentials."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

import prizm_connector as C


def build(out):
    out = Path(out).resolve()
    if out.exists():
        raise C.Refused("Choose a new demo output directory; existing work is never replaced")
    binary = shutil.which("ffmpeg")
    if not binary:
        raise C.Refused("The demo needs ffmpeg to create its free local fixture video")
    out.mkdir(mode=0o700, parents=True)
    video = out / "fixture.mp4"
    result = subprocess.run([binary, "-v", "error", "-f", "lavfi", "-i", "color=c=navy:s=180x320:d=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)], capture_output=True, timeout=30)
    if result.returncode:
        raise C.Refused("Local demo video generation failed")
    C.probe_video(video)
    store = C.Connector(out / "connector.db")
    summaries = []
    try:
        at = (C.dt.datetime.now(C.UTC) + C.dt.timedelta(minutes=5)).isoformat(timespec="seconds")
        for brand, platforms in (("brand-a", C.PLATFORMS), ("brand-b", ("instagram",))):
            folder = out / brand
            folder.mkdir(mode=0o700)
            unit = f"{brand}_product-a_brief-0001_batch-2026-10-19-a"
            media = unit + "_asset-01.mp4"
            shutil.copyfile(video, folder / media)
            card = {"schema": "meta-card/1", "brand": brand, "product": "product-a",
                "brief_id": "brief-0001", "ad_name": unit, "media": [media], "checks": {},
                "approval": None, "made_by": {"tool": "video-edit", "run": f"runs/video-edit/{brand}/demo"}}
            card_path = folder / "card.json"
            C.private_write(card_path, json.dumps(card, indent=2) + "\n")
            targets = []
            for platform in platforms:
                account = "demo-" + platform
                store.register("demo-workspace", brand, account, platform,
                    f"demo-{brand}-{platform}-identity", f"demo-{brand}-{platform}-device")
                targets.append({"account_id": account, "caption": "Synthetic connector demonstration. Not for publishing.",
                    "title": "Connector demonstration", "schedule_at": at, "ai_disclosure": False})
            C.private_write(folder / "targets.json", json.dumps(targets, indent=2) + "\n")
            plan = store.plan(card_path, media, targets, "demo-workspace")
            first = store.intake(plan)
            replay = store.intake(plan)
            assert first["created"] and not replay["created"]
            C.private_write(folder / "plan.json", json.dumps({k: v for k, v in plan.items() if k != "media"}, indent=2) + "\n")
            C.report(store, "demo-workspace", brand, folder / "receipt.html")
            receipts = store.receipts("demo-workspace", brand)
            C.private_write(folder / "results.jsonl", "".join(C.canonical(r) + "\n" for r in receipts))
            summaries.append({"brand": brand, "jobs": len(receipts), "replay_created_more_jobs": replay["created"], "state": "awaiting_approval"})
        C.private_write(out / "summary.json", json.dumps(summaries, indent=2) + "\n")
    finally:
        store.close()
    return {"demo": str(out), "brands": summaries, "network_calls": 0, "posts_published": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    try:
        print(json.dumps(build(a.out), indent=2))
        return 0
    except (C.Refused, OSError, subprocess.SubprocessError) as e:
        print(str(e) if isinstance(e, C.Refused) else "Local demo setup failed")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
