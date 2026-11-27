#!/usr/bin/env python3
"""pace.py — a video's edit pace, measured (no model, no network): the numbers a format's edit spec is written from
and an edit is checked against.

    python3 pace.py <video> [--hook-end SECONDS] [--transcript transcript.json] [--json]

Prints, for the whole video and for the body after the hook: runtime, cuts per 10 s, median and lower-quartile shot
length (ffmpeg scene detection at 0.27, shots under 0.12 s ignored as flashes), and the spoken words per second when a
transcript with start/end times is given. Scene detection misses soft cuts and can split a fast pan, so a format's
published numbers are recounted by eye on its source swipes; for checking an edit against its format, this is enough.
"""
import argparse
import json
import re
import statistics as st
import subprocess
import sys


def cuts(video, threshold=0.27):
    out = subprocess.run(["ffmpeg", "-nostdin", "-i", video, "-vf", f"select='gt(scene,{threshold})',showinfo",
                          "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", out)]


def duration(video):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                                capture_output=True, text=True).stdout.strip())


def words_per_second(transcript, start):
    rows = json.load(open(transcript))
    rows = rows if isinstance(rows, list) else (rows.get("segments") or rows.get("words") or [])
    seg = [(float(r["start"]), float(r.get("end") or r["start"]), len(str(r.get("text") or r.get("word") or "").split()))
           for r in rows if isinstance(r, dict) and r.get("start") is not None and float(r["start"]) >= start]
    if not seg:
        return None
    return sum(n for _, _, n in seg) / max(0.1, max(e for _, e, _ in seg) - min(s for s, _, _ in seg))


def measure(video, hook_end=0.0, transcript=None):
    d, c = duration(video), cuts(video)

    def part(a, b):
        cs = [x for x in c if a <= x < b]
        pts = [a] + cs + [b]
        shots = sorted(y - x for x, y in zip(pts, pts[1:]) if y - x > 0.12)
        return {"seconds": round(b - a, 2), "cuts_per_10s": round(len(cs) / max(0.1, b - a) * 10, 2),
                "median_shot": round(st.median(shots), 2) if shots else None,
                "p25_shot": round(shots[len(shots) // 4], 2) if shots else None}

    out = {"video": video, "whole": part(0.0, d), "hook_end": hook_end, "body": part(hook_end, d)}
    if transcript:
        w = words_per_second(transcript, hook_end)
        out["body"]["words_per_second"] = round(w, 2) if w else None
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video")
    ap.add_argument("--hook-end", type=float, default=0.0)
    ap.add_argument("--transcript")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    m = measure(a.video, a.hook_end, a.transcript)
    if a.json:
        print(json.dumps(m, indent=1))
    else:
        for k in ("whole", "body"):
            p = m[k]
            print(f"{k:5s} {p['seconds']:6.1f}s  {p['cuts_per_10s']:4.1f} cuts/10s  median shot {p['median_shot']}s  "
                  f"p25 {p['p25_shot']}s" + (f"  {p.get('words_per_second')} words/s" if p.get("words_per_second") else ""))
    sys.exit(0)
