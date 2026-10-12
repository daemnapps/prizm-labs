#!/usr/bin/env python3
"""
(retired — editing is the editor's) — lay the cutaways over the spine and write the finished ad.

    python3 (retired — editing is the editor's) <run> [out.mp4]

The spine is the revoiced A-roll, in order. Her voice runs the whole way and
is NEVER cut — only the picture changes. So this takes the video from the
cutaway for its few seconds and the audio from the spine throughout, which is
what "B-roll sits on top of A-roll" actually means in an edit.

Positions come from each cutaway's own `over` and `at` in plan.json, resolved
against the REAL durations on disk rather than the durations the brief asked
for — Cinema Studio picks its own length, so the two are never quite equal and
using the asked-for number slides every cut later than intended.

Two rules it enforces, both learned the hard way:

  · A cutaway must finish at least 0.4s before its take does, or the join
    lands on the cut and reads as a mistake.
  · Two cutaways less than 1.5s apart are run together into one block. A
    one-second flash of her face between two inserts is a hiccup, not a beat.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

VF = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
      "fps=30,setsar=1")
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
       "-pix_fmt", "yuv420p"]
TAIL_GUARD = 0.4        # a cutaway must end this far before its take does
MERGE_GAP = 1.5         # closer than this and two cutaways become one block


def dur(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def seg(src: Path, ss: float, length: float, out: Path, audio: bool) -> Path:
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.3f}", "-i", str(src),
           "-t", f"{length:.3f}", "-vf", VF] + ENC
    cmd += (["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
            if audio else ["-an"])
    r = subprocess.run(cmd + [str(out)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg failed on {out.name}: {r.stderr[-400:]}")
    return out


def main():
    run = Path(sys.argv[1]).expanduser().resolve()
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else run / "cinema" / "CUT.mp4"
    d = json.loads((run / "cinema" / "plan.json").read_text())
    cin = run / "cinema"
    work = cin / "work"
    work.mkdir(parents=True, exist_ok=True)

    # ---- the spine, from what is actually on disk
    spine_parts, offs, t = [], {}, 0.0
    for s in d["scenes"]:
        f = cin / "voiced" / f"{s['id']}.mp4"
        if not f.exists():
            sys.exit(f"{s['id']} is not revoiced yet — nothing to cut")
        offs[s["id"]] = t
        spine_parts.append(seg(f, 0, dur(f), work / f"sp-{s['id']}.mp4", True))
        t += dur(spine_parts[-1])
    total = t
    lst = work / "spine.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in spine_parts))
    spine = cin / "work" / "spine.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(spine)], check=True)
    total = dur(spine)

    # ---- place the cutaways
    cuts = []
    for c in d.get("cutaways", []):
        f = cin / "broll" / f"{c['id']}.mp4"
        if not f.exists():
            print(f"  {c['id']}  not generated — skipped")
            continue
        take = next(s for s in d["scenes"] if s["id"] == c["over"])
        tl = dur(cin / "voiced" / f"{take['id']}.mp4")
        length = min(dur(f), c["seconds"])
        at = float(c["at"])
        if at + length > tl - TAIL_GUARD:
            at = max(0.3, tl - TAIL_GUARD - length)
            print(f"  {c['id']}  pulled back to {at:.1f}s to clear {take['id']}'s tail")
        cuts.append({"id": c["id"], "src": f, "abs": offs[c["over"]] + at,
                     "len": length, "over": c["over"], "at": at})
    cuts.sort(key=lambda c: c["abs"])
    for a, b in zip(cuts, cuts[1:]):
        gap = b["abs"] - (a["abs"] + a["len"])
        if 0 < gap < MERGE_GAP:
            b["abs"] = a["abs"] + a["len"]
            print(f"  {a['id']}+{b['id']}  run together — {gap:.2f}s gap was a hiccup")

    # ---- build the picture: spine, punched through by each cutaway
    parts, t, n = [], 0.0, 0
    for c in cuts:
        if c["abs"] - t > 0.05:
            n += 1
            parts.append(seg(spine, t, c["abs"] - t, work / f"v{n:02}-A.mp4", False))
        n += 1
        parts.append(seg(c["src"], 0, c["len"], work / f"v{n:02}-{c['id']}.mp4", False))
        t = c["abs"] + c["len"]
    if total - t > 0.05:
        n += 1
        parts.append(seg(spine, t, total - t, work / f"v{n:02}-A.mp4", False))

    vl = work / "video.txt"
    vl.write_text("".join(f"file '{p}'\n" for p in parts))
    vid = work / "video.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(vl), "-c", "copy", str(vid)], check=True)

    # hold the last frame so rounding cannot clip the final words, then take
    # the spine's audio whole and cut to its exact length
    pad = work / "video-pad.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(vid), "-vf",
                    "tpad=stop_mode=clone:stop_duration=1,fps=30"] + ENC +
                   ["-an", str(pad)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pad), "-i", str(spine),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.6f}",
                    "-movflags", "+faststart", str(out)], check=True)

    cov = sum(c["len"] for c in cuts)
    print(f"\n  {out}")
    print(f"  {total:.2f}s · {len(d['scenes'])} takes · {len(cuts)} cutaways")
    print(f"  B-roll {cov:.1f}s ({cov / total * 100:.0f}%) · "
          f"her face {100 - cov / total * 100:.0f}%")


if __name__ == "__main__":
    main()
