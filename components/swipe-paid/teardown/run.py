#!/usr/bin/env python3
"""Hand a swiped creative to the video-teardown machine.

    run.py <brand> <ad_id> [--only 4b] [--from 5] [--stages]

This owns none of the teardown. The machine sequences its own stages, holds
its own prompts, and mirrors its own output to Drive. All this does is
resolve an ad the swipe already has, find its file in the Drive mirror, and
hand that file over with the swipe's findings attached.

Deliberately no `--creator`: without one the machine treats a run as swipe
research — the brief is written unassigned and no frames are made, which is
exactly what a competitor's ad should produce.

    --stages   show the machine's current chain and exit
"""
import argparse, json, os, sqlite3, subprocess, sys
from datetime import date
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SWIPE = os.path.dirname(HERE)
LAB = os.path.dirname(SWIPE)                      # the team notes
DB = os.path.join(SWIPE, "swipe.db")
for _r in Path(HERE).parents:          # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
DRIVE = str(swipe_home.root("paid"))

# The chain GRADUATED out of lab 2026-08-25 (the developer ruling) — it lives at the
# repo root now. The copy under new-workflow-design stays outdated and retired.
sys.path.append(os.path.join(os.path.dirname(SWIPE), "run-kit"))   # appended, never ahead of this tool
from run_kit.paths import repo  # noqa: E402  the one workspace locator (triage page 12)
WS = str(repo(HERE))
MACHINE = os.path.join(WS, "tools", "video-teardown", "machine", "run.py")


def lookup(brand, ad_id):
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    ad = con.execute("SELECT * FROM ads WHERE brand=? AND ad_id=?",
                     (brand, str(ad_id))).fetchone()
    if not ad:
        sys.exit(f"no ad {ad_id} for {brand} in swipe.db")
    block = con.execute("SELECT * FROM blocks WHERE brand=? AND slug=?", (brand, ad["block_slug"])).fetchone()
    con.close()
    return dict(ad), dict(block) if block else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brand", nargs="?")
    ap.add_argument("ad_id", nargs="?")
    ap.add_argument("--only")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="stop")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--stages", action="store_true")
    a = ap.parse_args()

    if not os.path.isfile(MACHINE):
        sys.exit(f"machine not found at {MACHINE}")
    if a.stages or not (a.brand and a.ad_id):
        subprocess.run([sys.executable, MACHINE, "--stages"])
        return

    ad, angle = lookup(a.brand, a.ad_id)
    rel = ad["drive_file"].split("/swipe/")[-1]    # the retired form, the fallback
    media = str(swipe_home.resolve(ad["drive_file"]) or swipe_home.path("paid", rel))
    if not os.path.isfile(media):
        sys.exit(f"media not on Drive yet: {rel}\n  run: build.py harvest {a.brand}")

    if ad["media_type"] != "video":
        print(f"[skip] {a.ad_id} is a static — the image chain is not built yet.")
        return

    label = f"swipe-{a.brand}-{a.ad_id}"

    # What the swipe already knows about this creative, written beside the
    # media so the run has the angle and its funnel position to hand.
    ctx = os.path.join(os.path.dirname(media), f"{a.ad_id}.swipe.json")
    json.dump({"brand": a.brand, "ad_id": ad["ad_id"], "variants": ad["variants"],
               "angle": angle.get("headline"), "stage": angle.get("stage"),
               "seasonal": angle.get("seasonal"),
               "primary_text": angle.get("primary_text"),
               "landing_page": angle.get("landing_page"),
               "swiped": date.today().isoformat(), "label": label},
              open(ctx, "w"), indent=1)

    cmd = [sys.executable, MACHINE, media, "--brand", a.brand, "--label", label]
    for flag, val in (("--only", a.only), ("--from", a.start), ("--to", a.stop)):
        if val:
            cmd += [flag, val]
    if a.redo:
        cmd.append("--redo")

    print(f"→ {angle.get('headline','')[:60]}  ({ad['variants']}x variants, "
          f"{angle.get('stage','?')})")
    print(f"  {' '.join(os.path.basename(c) if c == media else c for c in cmd)}\n")
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
