#!/usr/bin/env python3
"""realism.py — the editing rows of the realism index, picked for one piece (V9, video system sync 2026-10-21, E29).

    pick(fmt, vm=None, run=None, kit=None) -> {"rows": [...], "filming": <format>|None, "level": n, "why": "..."}

The index lives in tools/video-production/spice/realism-index.json (read, never copied — the owner curates it). Its
rows whose `stage` is "editing" are the edit's to add: phone-grain · crooked-hold · digital-micro-shake ·
reframe-nudge · exposure-shift · imperfect-zoom · app-native-captions. Which of them a piece gets:

  1. the brief picked them — the piece's `realism` list (row ids; the writing stage reads the same index, W23)
  2. else the piece's FILMING format (selfie-talk, counter-demo, …: `piece.filming` / `piece.realism_format`) and its
     level (`piece.realism_level`, default 1): every editing row made for that filming format at or under the level
  3. else nothing is known about how it was filmed: only the rows made for EVERY filming format at level 1 (the
     finish every phone video has — the grain, the app's own captions)

compose.py draws them (`sheet["realism"]`); app-native-captions is the caption look itself (looks.pick_caption).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = HERE.parents[1] / "video-production" / "spice" / "realism-index.json"
DRAWN = ("phone-grain", "crooked-hold", "digital-micro-shake", "reframe-nudge", "exposure-shift", "imperfect-zoom",
         "app-native-captions")


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def editing_rows() -> list[dict]:
    idx = _read(INDEX, {}) or {}
    return [r for r in idx.get("rows") or [] if r.get("stage") == "editing" and r.get("status") != "deprecated"]


def _piece(vm: Path | None, run: dict | None, kit: dict | None) -> dict:
    p = {}
    if vm is not None:
        p.update((_read(Path(vm) / "plan.json", {}) or {}).get("piece") or {})
    p.update((run or {}).get("piece") or {})
    p.update((kit or {}).get("piece") or {})
    for k in ("realism", "filming", "realism_format", "realism_level"):
        if (kit or {}).get(k) is not None:
            p[k] = kit[k]
    return p


def pick(fmt: str | None = None, vm: Path | None = None, run: dict | None = None, kit: dict | None = None) -> dict:
    rows = editing_rows()
    if not rows:
        return {"rows": [], "filming": None, "level": 0, "why": f"no realism index at {INDEX} — nothing added"}
    p = _piece(vm, run, kit)
    every = set().union(*(set(r.get("formats") or []) for r in rows))
    named = [str(x) for x in p.get("realism") or []]
    if named:
        got = [r for r in rows if r["id"] in named]
        return {"rows": [r["id"] for r in got], "filming": p.get("filming") or p.get("realism_format"),
                "level": None, "why": "the brief picked them (piece.realism)"}
    filming = p.get("filming") or p.get("realism_format")
    level = int(p.get("realism_level") or 1)
    if filming:
        got = [r for r in rows if filming in (r.get("formats") or []) and int(r.get("level") or 1) <= level]
        why = f"made for {filming} at level {level} or under"
    else:
        got = [r for r in rows if set(r.get("formats") or []) >= every and int(r.get("level") or 1) <= 1]
        why = "how it was filmed is not on the brief — only the finish every phone video has"
    return {"rows": [r["id"] for r in got if r["id"] in DRAWN], "filming": filming, "level": level, "why": why}


STILL_SHARE = 0.4   # more still frames than this share of a stretch: the clip came out too still (a phone never is)


def still(src: Path, at: float, seconds: float) -> bool:
    """Does this stretch of the source sit still? (more than STILL_SHARE of its frames barely change) — the swipe is a
    handheld phone: 11% of its frames are still, ours were 18% before a shake or a push was added."""
    txt = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{at:.3f}", "-t", f"{seconds:.3f}", "-i", str(src), "-vf",
                          "scale=135:240,signalstats,metadata=print:key=lavfi.signalstats.YDIF", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    yd = [float(x) for x in re.findall(r"YDIF=([\d.]+)", txt)]
    return bool(yd) and sum(y < 0.6 for y in yd) / len(yd) > STILL_SHARE


DRIFT_OFF = 12.0    # % of the frame a face's centre may sit off the middle before the hand corrects toward it


def mark(sheet: dict, root: Path) -> None:
    """The finish this sheet's picture needs, only for the rows picked: a video clip that came out too still is marked
    for the hand's shake (digital-micro-shake); a clip whose subject sits off centre gets a small quick correction
    toward it (reframe-nudge, from the faces read on the picture — faces.py). Stills drift instead (compose.py)."""
    rows = (sheet.get("realism") or {}).get("rows") or []
    if "reframe-nudge" in rows:
        for c in sheet.get("picture") or []:
            fs = [b for b in c.get("face_track") or []] + [f for r in c.get("scene_read") or [] for f in r.get("faces") or []]
            if not fs:
                continue
            cx = sum(f["x"] + f["w"] / 2 for f in fs) / len(fs)
            if abs(cx - 50) > DRIFT_OFF:
                c["reframe_dx"] = round(max(-4.0, min(4.0, (50 - cx) * 0.3)), 2)
    if "digital-micro-shake" not in rows:
        return
    for c in sheet.get("picture") or []:
        src = Path(str(c.get("src") or ""))
        src = src if src.is_absolute() else Path(root) / src
        if c.get("still") or c.get("kind") in ("card", "screen", "endcard", "split") or src.suffix.lower() not in (".mp4", ".mov", ".webm"):
            continue
        if src.is_file() and float(c.get("duration") or 0) >= 1.0:
            c["too_still"] = still(src, float(c.get("source_start") or 0), float(c["duration"]))
