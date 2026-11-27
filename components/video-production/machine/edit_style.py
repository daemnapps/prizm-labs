#!/usr/bin/env python3
"""edit_style.py — a swipe's edit, read cut by cut: the score an edit copies (no model, no network).

    python3 edit_style.py <swipe video> [--transcript transcript.json] [--hook-end SECONDS] [--out DIR]

An average pace says how fast; it does not say WHERE the cuts fall, and an edit built from an average feels off. This
reads the swipe's own rhythm and writes it as a score:

  shots      every shot's start, length and the cut that opened it (ffmpeg scene detection, flashes under 0.12 s dropped)
  placement  for each cut: the phrase it lands in, how far into that phrase (seconds and fraction), or "gap" when it
             falls between phrases — so a copy cuts where the swipe cuts relative to the words, not on a clock
  beats      how many cuts each phrase carries (one shot per phrase, two, a held phrase) and the phrase's length
  pattern    the shot lengths in order, short/medium/long, so the swipe's run of quick cuts and its held shots survive
  sections   the same numbers for the hook and the body when --hook-end is given

Writes edit-style.json and EDIT-STYLE.md. `score_for(style, phrases)` lays the swipe's score on a new narration:
it returns the cut times for our phrases that copy the swipe's cuts-per-phrase and where in the phrase they fall.
Scene detection misses soft cuts and can split a fast pan; recount the numbers by eye on the swipe before they are law.
Brand-agnostic: reads only a video and its transcript.
"""
import argparse
import json
import re
import statistics
import subprocess
from pathlib import Path

FLASH = 0.12


def duration(video):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                                capture_output=True, text=True).stdout.strip())


def cuts(video, threshold=0.27):
    out = subprocess.run(["ffmpeg", "-nostdin", "-i", video, "-vf", f"select='gt(scene,{threshold})',showinfo",
                          "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    times, last = [], 0.0
    for x in (float(v) for v in re.findall(r"pts_time:([0-9.]+)", out)):
        if x - last >= FLASH:
            times.append(round(x, 3))
            last = x
    return times


def kind(d):
    return "quick" if d < 1.0 else "medium" if d < 1.8 else "held"


def read(video, phrases=None, hook_end=None):
    total = duration(video)
    cs = cuts(video)
    edges = [0.0] + cs + [total]
    shots = [{"n": i + 1, "start": edges[i], "end": edges[i + 1], "len": round(edges[i + 1] - edges[i], 3),
              "kind": kind(edges[i + 1] - edges[i])} for i in range(len(edges) - 1)]
    placement = []
    for c in cs:
        where = {"cut": c, "phrase": None, "into_s": None, "into_frac": None}
        for p in phrases or []:
            if p["start"] - 0.05 <= c <= p["end"] + 0.05:
                span = max(p["end"] - p["start"], 0.01)
                where.update(phrase=p.get("id"), into_s=round(c - p["start"], 3),
                             into_frac=round((c - p["start"]) / span, 2))
                break
        placement.append(where)
    beats = []
    for p in phrases or []:
        inside = [c for c in cs if p["start"] - 0.05 <= c <= p["end"] + 0.05]
        beats.append({"phrase": p.get("id"), "text": p.get("text", ""), "start": p["start"], "end": p["end"],
                      "len": round(p["end"] - p["start"], 2), "cuts": len(inside)})

    def stats(sub):
        lens = [s["len"] for s in sub]
        if not lens:
            return {}
        span = sub[-1]["end"] - sub[0]["start"]
        lens_sorted = sorted(lens)
        return {"seconds": round(span, 2), "shots": len(lens), "cuts_per_10s": round((len(lens) - 1) / span * 10, 2),
                "median": round(statistics.median(lens), 2), "p25": round(lens_sorted[len(lens) // 4], 2),
                "shortest": round(min(lens), 2), "longest": round(max(lens), 2)}

    out = {"video": str(video), "seconds": round(total, 2), "all": stats(shots), "shots": shots,
           "placement": placement, "beats": beats, "pattern": [s["kind"] for s in shots]}
    if hook_end:
        out["hook"] = stats([s for s in shots if s["end"] <= hook_end + 0.3])
        out["body"] = stats([s for s in shots if s["start"] >= hook_end - 0.3])
    return out


def score_for(style, phrases):
    """Cut times for a new narration: each phrase gets as many cuts as the swipe's phrase of the same rank carried,
    placed at the same fractions of the phrase. Phrases map in order, the swipe's beats cycling if ours are longer."""
    src = [b for b in style["beats"] if b["len"] > 0]
    if not src:
        return []
    times = []
    plc = {}
    for w in style["placement"]:
        if w["phrase"] is not None:
            plc.setdefault(w["phrase"], []).append(w["into_frac"])
    for i, p in enumerate(phrases):
        b = src[i % len(src)]
        times.append(round(p["start"], 3))
        for f in plc.get(b["phrase"], []):
            times.append(round(p["start"] + f * (p["end"] - p["start"]), 3))
    return sorted(set(times))


def md(style):
    a = style["all"]
    lines = ["# Edit style, read from the swipe", "",
             f"`{style['video']}` · {style['seconds']} s · {a['shots']} shots · {a['cuts_per_10s']} cuts per 10 s · "
             f"median {a['median']} s · shortest {a['shortest']} s · longest {a['longest']} s", ""]
    for k in ("hook", "body"):
        if style.get(k):
            s = style[k]
            lines.append(f"- **{k}:** {s['shots']} shots, {s['cuts_per_10s']} cuts per 10 s, median {s['median']} s")
    lines += ["", "## The cut score, in order", "", "| # | start | length | kind |", "|---|---|---|---|"]
    lines += [f"| {s['n']} | {s['start']:.2f} | {s['len']:.2f} | {s['kind']} |" for s in style["shots"]]
    if style["beats"]:
        lines += ["", "## Cuts per phrase", "", "| phrase | start | length | cuts inside | words |", "|---|---|---|---|---|"]
        lines += [f"| {b['phrase']} | {b['start']:.2f} | {b['len']} | {b['cuts']} | {b['text'][:60]} |" for b in style["beats"]]
        lines += ["", "## Where each cut lands in its phrase", "", "| cut | phrase | into (s) | fraction |", "|---|---|---|---|"]
        lines += [f"| {w['cut']:.2f} | {w['phrase'] or 'gap'} | {w['into_s'] if w['into_s'] is not None else ''} | "
                  f"{w['into_frac'] if w['into_frac'] is not None else ''} |" for w in style["placement"]]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--transcript")
    ap.add_argument("--hook-end", type=float)
    ap.add_argument("--out", default=".")
    a = ap.parse_args()
    phrases = json.load(open(a.transcript)) if a.transcript else None
    style = read(a.video, phrases, a.hook_end)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "edit-style.json").write_text(json.dumps(style, indent=1))
    (out / "EDIT-STYLE.md").write_text(md(style))
    print(md(style))


if __name__ == "__main__":
    main()
