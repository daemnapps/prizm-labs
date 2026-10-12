#!/usr/bin/env python3
"""Pull down every swiped video and cut its contact strip.

The reference video is what a maker actually watches, and the contact
strip (6 stills across the runtime) is what makes the FORMAT readable —
to a person and to a model — without opening the file.

    python3 videos.py [--lane swipe] [--limit 50] [--redo]

Per post, in records/swipe-videos/<code>/:
    video.mp4     the reference (media — gitignored, mirrored to Drive)
    strip/01..06.jpg   stills at 8/24/40/56/72/88% of runtime
    meta.json     duration, size, resolution, the beats' timestamps

Signal order (views + 10x likes) so the ones worth having land first.
Runs are resumable: an existing meta.json is skipped unless --redo.
"""
import argparse, json, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAVES = HERE / "records/damon-saves"
OUT = HERE / "records/swipe-videos"
MARKS = [0.08, 0.24, 0.40, 0.56, 0.72, 0.88]

def code_of(u):
    m = re.search(r"/(p|reel|reels)/([A-Za-z0-9_-]+)", u)
    return m.group(2) if m else None

def probe(f):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                        "-show_format", "-show_streams", str(f)],
                       capture_output=True, text=True, timeout=60)
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"duration": round(float(d.get("format", {}).get("duration", 0)), 2),
            "size": int(d.get("format", {}).get("size", 0)),
            "w": v.get("width"), "h": v.get("height")}

def one(row, redo=False):
    code = code_of(row["url"])
    if not code:
        return "nocode"
    d = OUT / code
    if (d / "meta.json").exists() and not redo:
        return "have"
    d.mkdir(parents=True, exist_ok=True)
    vid = d / "video.mp4"
    if not vid.exists() or redo:
        r = subprocess.run(["yt-dlp", "-q", "--no-warnings", "-f", "mp4/best",
                            "-o", str(vid), "--no-playlist", row["url"]],
                           capture_output=True, text=True, timeout=420)
        if not vid.exists():
            (d / "failed.txt").write_text((r.stderr or "")[-400:])
            return "fail"
    meta = probe(vid)
    strip = d / "strip"
    strip.mkdir(exist_ok=True)
    beats = []
    for i, frac in enumerate(MARKS, 1):
        t = round(meta["duration"] * frac, 2)
        subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-ss", str(t), "-i", str(vid),
                        "-frames:v", "1", "-vf", "scale=480:-1", str(strip / f"{i:02d}.jpg")],
                       capture_output=True, timeout=120)
        beats.append(t)
    meta.update({"code": code, "url": row["url"], "author": row.get("author"),
                 "beats": beats, "pulled": time.strftime("%Y-%m-%d")})
    (d / "meta.json").write_text(json.dumps(meta, indent=1))
    return "got"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", default=None, help="swipe | organic (default: both)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args()
    rows = json.loads((SAVES / "catalog.json").read_text())["rows"]
    if a.lane:
        rows = [r for r in rows if r.get("lane") == a.lane]
    rows = [r for r in rows if r.get("views")]           # video posts
    rows.sort(key=lambda r: (r.get("views") or 0) + (r.get("likes") or 0) * 10, reverse=True)
    if a.limit:
        rows = rows[:a.limit]
    tally = {}
    for i, r in enumerate(rows, 1):
        s = one(r, a.redo)
        tally[s] = tally.get(s, 0) + 1
        print(f"[{i}/{len(rows)}] {code_of(r['url'])} {s}", flush=True)
        if s == "got":
            time.sleep(2)                                # be a polite guest
    print("done:", tally, flush=True)

if __name__ == "__main__":
    main()
