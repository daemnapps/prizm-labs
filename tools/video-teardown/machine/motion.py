#!/usr/bin/env python3
"""Does this source actually move?

    python3 motion.py <video>

A still posted as a reel is a real mp4 with an audio track, so triage — which
reads the file — calls it a video and the chain runs. Kerin's quote card got
thirteen stages of Opus that way on 2026-08-26, and KZN-07 (a split-screen
before/after photo) got five before a later stage caught it on the 27th.

This answers the cheap version of the question in about a second, with ffmpeg
rather than a model: sample frames across the clip and measure how much the
picture changes. It reports; it does not gate. Damon ruled the call is his.

WHAT IT CATCHES, HONESTLY. A frozen source scores near zero — KZN-07, a
split-screen before/after photo, came in at 0.15. A genuine performance runs
30-55. But a quote card over stock b-roll scores like a video, because the
b-roll really is moving: Kerin's sunset card measured 9.91. So this closes the
frozen-image half of the gap and not the other half. Catching "no person
performs in this" needs eyes on a frame, not a difference metric, and belongs
in triage where the model already looks at the video.
"""
import json, re, subprocess, sys
from pathlib import Path

SAMPLES = 8
# Mean per-pixel luma difference between consecutive samples. Camera noise and
# compression alone land under ~1.0; a locked-off shot of moving water was 6.4,
# a genuinely static card 0.2.
STILL_UNDER = 1.2


def duration(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def movement(video):
    """-> (mean difference, verdict). Higher means more actually happens."""
    dur = duration(video)
    if dur <= 0:
        return None, "unreadable"
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video),
         "-vf", (f"select='not(mod(n\\,{max(1, int(dur * 30 / SAMPLES))}))',"
                 "tblend=all_mode=difference,signalstats,"
                 "metadata=print:key=lavfi.signalstats.YAVG:file=-"),
         "-f", "null", "-"],
        capture_output=True, text=True)
    # metadata=print writes to its own file handle, not stderr — reading the
    # wrong stream silently measures nothing and calls everything unreadable.
    vals = [float(m) for m in re.findall(r"YAVG=([\d.]+)", r.stdout or "")]
    vals = [v for v in vals if v == v]
    if not vals:
        return None, "unreadable"
    mean = sum(vals) / len(vals)
    return mean, ("still" if mean < STILL_UNDER else "moves")


def check(video):
    mean, verdict = movement(video)
    return {"video": str(video), "movement": None if mean is None else round(mean, 2),
            "verdict": verdict,
            "note": {"still": "This source barely changes frame to frame — it is "
                              "very likely a still or a text card posted as a reel. "
                              "The chain will still run; the brief will be thin.",
                     "moves": "",
                     "unreadable": "Could not measure movement."}[verdict]}


if __name__ == "__main__":
    print(json.dumps(check(Path(sys.argv[1])), indent=2))
