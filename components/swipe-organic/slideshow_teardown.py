#!/usr/bin/env python3
"""Tear down every slideshow in a pool, slide by slide, with the image chain's own slideshow prompt.

    python3 slideshow_teardown.py --pool <pool> --brand <brand> [--top 20] [--workers 6]

the owner, 2026-10-24, on the clipping campaign: "run teardown on all of the assets ... so that way we can build a
variation matrix". Each slideshow in `<pool>/posts.json` whose slides are in the library
(`records/swipe-videos/<id>/slides/slide-NN.jpg`) goes through
`tools/image-teardown/prompts/stage1-sequence-teardown-v*` (the newest), on the image chain's own Gemini
door, with every slide attached in order. Biggest first (views from the pool row, or from a Content Rewards
snapshot beside it). Writes runs/swipe-organic/<brand>/<pool>-teardowns/<id>.md; a teardown already written is
kept. Nothing here is brand-specific: the brand only names where the run is filed.
"""
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))
from run_kit.paths import repo  # noqa: E402

IT = repo() / "tools" / "image-teardown"
GEMINI = IT / "tools" / "gemini_image.py"
DOCTRINE = repo() / "components" / "marketing-doctrine" / "slices"
LIB = HERE / "records" / "swipe-videos"


def prompt():
    return sorted((IT / "prompts").glob("stage1-sequence-teardown-v*-owner.md"),
                  key=lambda p: int(p.name.split("-v")[1].split("-")[0]))[-1]


def views_of(brand, pool):
    """Views per post id from the newest Content Rewards snapshot, when there is one."""
    snaps = sorted((repo() / "runs" / "content-rewards" / brand / pool).glob("*/clips.json"))
    if not snaps:
        return {}
    out = {}
    for c in json.loads(snaps[-1].read_text()).get("clips", []):
        pid = (c.get("postUrl") or "").rstrip("/").rsplit("/", 1)[-1]
        out[pid] = int(float(c.get("lifetimeViews") or 0))
    return out


def one(code, out):
    dest = out / f"{code}.md"
    if dest.exists() and dest.stat().st_size > 500:
        return code, "kept"
    slides = sorted((LIB / code / "slides").glob("slide-*.jpg"))
    if not slides:
        return code, "no slides"
    cmd = [sys.executable, str(GEMINI), "--prompt-file", str(prompt())]
    for s in slides:
        cmd += ["--image", str(s)]
    for k, f in (("awareness_levels", "awareness.md"), ("sophistication_stages", "sophistication.md"), ("desire_dimensions", "desire.md")):
        cmd += ["--var", f"{k}={DOCTRINE / f}"]
    cmd += ["--out", str(dest)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return code, "done" if r.returncode == 0 and dest.exists() else f"failed: {(r.stderr or r.stdout)[-200:]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True); ap.add_argument("--brand", required=True)
    ap.add_argument("--top", type=int, default=0); ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    rows = json.loads((HERE / a.pool / "posts.json").read_text())["posts"]
    views = views_of(a.brand, a.pool)
    codes = sorted({r["id"] for r in rows}, key=lambda c: -views.get(c, 0))
    if a.top:
        codes = codes[:a.top]
    out = repo() / "runs" / "swipe-organic" / a.brand / f"{a.pool}-teardowns"
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.workers) as ex:
        for code, state in ex.map(lambda c: one(c, out), codes):
            print(f"  {code} ({views.get(code, 0):,} views): {state}", flush=True)
    print(f"teardowns in {out}")


if __name__ == "__main__":
    main()
