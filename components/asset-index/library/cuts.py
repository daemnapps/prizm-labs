#!/usr/bin/env python3
"""cuts.py — the real shot changes in every clip, found on its local proxy (ffmpeg scene detection; free).

    python3 cuts.py --brand <brand> [--workers 8]

Writes runs/asset-index/<brand>/library/cuts.json: {clip id: [seconds of each shot change]}. Resumable: a clip
already measured is skipped. library.py build reads it and snaps each scene's in and out to a shot change
within SNAP_S of the labelled second, so the times an editor gets land on the cut, not on a rounded second.
Nothing is cut or copied; only times are written.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library as LIB  # noqa: E402

THRESHOLD = 0.25          # ffmpeg scene score that counts as a shot change
TIME = re.compile(r"pts_time:([0-9.]+)")


def shot_changes(proxy: Path) -> list[float]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(proxy), "-vf", f"select='gt(scene,{THRESHOLD})',showinfo",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    return sorted({round(float(t), 3) for t in TIME.findall(r.stderr or "")})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    rows = LIB.rows_of(a.brand)
    f = LIB.libdir(a.brand) / "cuts.json"
    have = json.loads(f.read_text()) if f.is_file() else {}
    todo = {}
    for r in rows:
        if r.get("kind") == "picture" or r["clip"] in have or r["clip"] in todo:
            continue
        fa = LIB._abs(r)
        if fa and (fa.parent / "proxy.mp4").is_file():
            todo[r["clip"]] = fa.parent / "proxy.mp4"
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for cid, cuts in zip(todo, ex.map(shot_changes, todo.values())):
            have[cid] = cuts
    f.write_text(json.dumps(have, separators=(",", ":")) + "\n")
    print(json.dumps({"measured_now": len(todo), "clips_with_cuts": len(have),
                      "shot_changes": sum(len(v) for v in have.values())}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
