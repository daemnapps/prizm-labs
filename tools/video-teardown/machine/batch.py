#!/usr/bin/env python3
"""Run every selected video that has not been briefed yet.

    python3 batch.py --dry-run          what would run, and roughly how long
    python3 batch.py                     three at a time
    python3 batch.py --workers 4         more, if the image API can take it
    python3 batch.py --creator <person>

Runs are independent — own folder, own outputs, own Doc — so they parallelise
cleanly. What is NOT independent is the shared timing file (now locked) and the
image API, which is the real ceiling: frames already fires six concurrent
requests inside a single run, so four runs is twenty-four in flight. Frames
falls back on its own (pro, then flash, then a still from the video), so
pushing the count trades picture quality for wall clock rather than breaking.

One video failing never stops the batch. It is recorded, named at the end with
the stage it died on, and every other video carries on.
"""
import argparse, json, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C, library as L

SELECTED = "creators/SELECTED-2026-08-27.json"
lock = threading.Lock()


def briefed(vid):
    """Has this id already produced a brief?"""
    for d in C.runs_root().iterdir():
        f = d / "run.json"
        if not f.is_file():
            continue
        try:
            lab = (json.loads(f.read_text()).get("label") or "").upper()
        except Exception:
            continue
        if lab.startswith(vid.upper() + "-") and (d / "brief-final.md").is_file():
            return d.name
    return None


def slug_for(vid, name):
    clean = "".join(ch if ch.isalnum() or ch == " " else "" for ch in (name or ""))
    return f"{vid}-{'-'.join(clean.lower().split())[:40]}".strip("-")


def todo(brand, only_creator=None):
    """What the picking board says to brief.

    Reads PICKING.json — the file the live board writes when someone ticks a
    video. It used to read a separate selections file, so a pick made on the
    board never reached the runner and the two could disagree without saying
    so (2026-08-29). One file, one truth."""
    root = L.root()
    pick = json.loads((root / "creators/PICKING.json").read_text())
    out = []
    for h, c in pick["creators"].items():
        if only_creator and h != only_creator:
            continue
        # Deeper-pass finds live in their own list, and their ranks are the
        # N-ids. Reading only `posts` silently dropped every N pick — Janci's
        # whole set is N-ids, so she would have briefed nothing.
        by = {p["rank"]: p for p in
              list(c.get("posts", [])) + list(c.get("deeper", []))}
        vids = []
        for sid in c.get("selected", []):
            p = by.get(sid)
            if not p:
                continue
            # An N pick was downloaded into the posts folder numbered 11+.
            want = sid if not sid.startswith("N") else f"{int(sid[1:]) + 10:02d}"
            d = next((x for x in (root / "creators" / h / "posts").iterdir()
                      if x.is_dir() and x.name.startswith(want + "-")), None)
            vids.append({"id": p["id"], "name": p.get("name", ""),
                         "video": str((d / "video.mp4").relative_to(root)) if d else None})
        c = {"creator": c["name"], "owes": c.get("owes", 5), "videos": vids}
        for i in c.get("videos", []):
            if briefed(i["id"]):
                continue
            v = root / i["video"]
            if not v.is_file():
                out.append({**i, "handle": h, "creator": c["creator"],
                            "owes": c["owes"], "video": None})
                continue
            out.append({**i, "handle": h, "creator": c["creator"],
                        "owes": c["owes"], "video": v})
    return out


def one(job, brand):
    if not job["video"]:
        return job["id"], "no video on the Drive", None
    cmd = ["python3", str(HERE / "run.py"), str(job["video"]),
           "--brand", brand, "--creator", job["handle"],
           "--label", slug_for(job["id"], job["name"]),
           "--video-count", str(job["owes"])]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERE))
    mins = (time.time() - t0) / 60
    tail = (r.stdout or "") + (r.stderr or "")
    if "through to the end" in tail:
        url = ""
        for line in tail.splitlines():
            if "Doc " in line and "http" in line:
                url = line.split("http", 1)[1]
                url = "http" + url.strip()
        with lock:
            print(f"  ✔ {job['id']:<9} {job['creator']:<8} {mins:4.1f} min"
                  f"{'  ' + url if url else ''}", flush=True)
        return job["id"], None, url
    stage = ""
    for line in tail.splitlines():
        if "stopped at" in line:
            stage = line.strip()
    with lock:
        print(f"  ✖ {job['id']:<9} {job['creator']:<8} {mins:4.1f} min  "
              f"{stage or 'failed'}", flush=True)
    return job["id"], stage or "failed", None


def main():
    ap = argparse.ArgumentParser(description="Brief every selected video.")
    ap.add_argument("--brand", required=True,
                    help="which brand's picks to brief. Named every time — a "
                         "default here would quietly run one brand's videos "
                         "as another's (rule 4).")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--creator")
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    a = ap.parse_args()

    jobs = todo(a.brand, a.creator)
    if not jobs:
        print("  nothing left to brief")
        return 0

    per = 25  # minutes, measured across <person>'s three
    print(f"\n  {len(jobs)} video(s) to brief, {a.workers} at a time")
    print(f"  roughly {len(jobs) * per / a.workers / 60:.1f} hours "
          f"(one at a time it would be {len(jobs) * per / 60:.1f})")
    missing = [j["id"] for j in jobs if not j["video"]]
    if missing:
        print(f"  {len(missing)} have no video on the Drive: {', '.join(missing[:6])}")
    by = {}
    for j in jobs:
        by.setdefault(j["creator"], []).append(j["id"])
    for k, v in by.items():
        print(f"     {k:<9} {', '.join(v)}")
    if a.dry:
        print("\n  dry run — nothing started")
        return 0

    print()
    fails = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for vid, err, _ in ex.map(lambda j: one(j, a.brand), jobs):
            if err:
                fails.append((vid, err))
    print(f"\n  {len(jobs) - len(fails)} briefed, {len(fails)} stopped short")
    for vid, err in fails:
        print(f"     {vid}: {err}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
