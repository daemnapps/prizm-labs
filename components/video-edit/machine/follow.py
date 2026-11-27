#!/usr/bin/env python3
"""follow.py — an annotation that FOLLOWS the person: an arrow, circle, underline or
highlight whose target is the face stays on it while it is up.

    follows(row) -> bool                    target "face" | "subject" | "person" | "presenter", or {"follow": "face"}
    track(sheet, start, end) -> (samples, by)   [(t, {x,y,w,h})] on the final clock, from faces.py's face_track,
                                              else production's subject_box (one box, or one per frame), else ([], None)
    keys(samples, kind, start, dur, size) -> (place, keyframes)
    apply(sheet) -> notes                   every follow annotation gets `place` (where it starts) and
                                              `follow: {by, keys: [{t, x_pct, y_pct}], ...}`; fixed targets are untouched

The face track is 5 frames a second and jittery, so the path is smoothed (a centred
moving average over three samples) and the size held at the median, so only the
position moves — compose.py tweens it between keyframes with an ease. A follow target
with no track and no subject_box is a WARN and falls back to a fixed anchor
(`fallback`, else `center`), never a red: the annotation still draws, just not on the face.
Boxes are % of the frame, top-left origin, like everything in placement.py.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
FOLLOW = ("face", "subject", "person", "presenter")
PLATES = ("card", "screen", "endcard", "split")
SMOOTH = 3


def follows(row: dict) -> bool:
    t = row.get("target")
    if isinstance(t, str):
        return t.strip().lower() in FOLLOW
    return isinstance(t, dict) and str(t.get("follow", "")).lower() in FOLLOW


def _biggest(boxes: list[dict]) -> dict:
    return max(boxes, key=lambda b: b["w"] * b["h"])


def track(sheet: dict, start: float, end: float) -> tuple[list[tuple[float, dict]], str | None]:
    """The person under [start, end]: tracked boxes first (the biggest face per moment), then production's subject_box."""
    on = [c for c in sheet.get("picture") or [] if c.get("kind") not in PLATES and not c.get("still")
          and c["start"] < end - 0.01 and start < c["start"] + c["duration"] - 0.01]
    on.sort(key=lambda c: 0 if c.get("roll") == "b" else 1)  # what is on top is what the eye sees
    by_t: dict[float, list] = {}
    for c in on:  # every part under it (a talking clip cut at its pauses is several parts), each only while it is on screen
        lo, hi = c["start"] - 0.25, c["start"] + c["duration"] + 0.25
        for b in c.get("face_track") or []:
            if start - 0.25 <= b["t"] <= end + 0.25 and lo <= b["t"] <= hi:
                by_t.setdefault(round(b["t"], 3), []).append(b)
    if by_t:
        return [(t, _biggest(bs)) for t, bs in sorted(by_t.items())], "face_track"
    for c in on:
        sb = c.get("subject_box")
        if isinstance(sb, dict) and {"x", "y", "w", "h"} <= set(sb):
            return [(start, sb), (end, sb)], "subject_box"
        if isinstance(sb, list):
            rows = [b for b in sb if isinstance(b, dict) and {"x", "y", "w", "h"} <= set(b)]
            timed = [b for b in rows if b.get("t") is not None]
            if timed:  # production's per-frame boxes: t on the clip's own clock
                off = c["start"] - c.get("source_start", 0)
                pts = [(round(b["t"] + off, 3), b) for b in timed if start - 0.25 <= b["t"] + off <= end + 0.25]
                if pts:
                    return pts, "subject_box"
            if rows:
                u = {"x": min(b["x"] for b in rows), "y": min(b["y"] for b in rows)}
                u.update(w=max(b["x"] + b["w"] for b in rows) - u["x"], h=max(b["y"] + b["h"] for b in rows) - u["y"])
                return [(start, u), (end, u)], "subject_box"
    return [], None


def _shape(kind: str, cx: float, cy: float, fw: float, fh: float, fx0: float, fy1: float, size: dict) -> dict:
    """The annotation's box around one face: a circle rings it, a highlight covers it, an
    underline sits under the chin, an arrow's tip touches its left edge."""
    if kind == "circle":
        return {"x_pct": cx, "y_pct": cy, "w_pct": fw * 1.55, "h_pct": fh * 1.4}
    if kind == "highlight":
        return {"x_pct": cx, "y_pct": cy, "w_pct": fw * 1.1, "h_pct": fh * 1.1}
    if kind == "underline":
        h = max(2.0, fh * 0.35)
        return {"x_pct": cx, "y_pct": fy1 - 0.4 * h, "w_pct": fw * 1.2, "h_pct": h}
    w, h = size.get("w_pct", 30), size.get("h_pct", 14)  # arrow: the tip is drawn at (10%, 55%) of its box
    tip_x, tip_y = fx0 - 0.8, cy
    return {"x_pct": tip_x + 0.4 * w, "y_pct": tip_y - 0.05 * h, "w_pct": w, "h_pct": h}


def keys(samples: list[tuple[float, dict]], kind: str, start: float, dur: float, size: dict | None = None) -> tuple[dict, list[dict]]:
    """Smoothed keyframes on the final clock, clipped to the annotation's life; size held at the median."""
    end = start + dur
    pts = sorted(samples, key=lambda p: p[0])
    cx = [b["x"] + b["w"] / 2 for _, b in pts]
    cy = [b["y"] + b["h"] / 2 for _, b in pts]
    half = SMOOTH // 2
    sx = [statistics.fmean(cx[max(0, i - half): i + half + 1]) for i in range(len(pts))]
    sy = [statistics.fmean(cy[max(0, i - half): i + half + 1]) for i in range(len(pts))]
    fw = statistics.median(b["w"] for _, b in pts)
    fh = statistics.median(b["h"] for _, b in pts)
    raw = [(t, _shape(kind, x, y, fw, fh, x - fw / 2, y + fh / 2, size or {})) for (t, _), x, y in zip(pts, sx, sy)]

    def at(t: float) -> dict:  # held before the first sample and after the last, eased in between
        if t <= raw[0][0]:
            return raw[0][1]
        if t >= raw[-1][0]:
            return raw[-1][1]
        for (t0, a), (t1, b) in zip(raw, raw[1:]):
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0) if t1 > t0 else 0
                return {k: a[k] + (b[k] - a[k]) * f for k in a}
        return raw[-1][1]
    times = [start] + [t for t, _ in raw if start < t < end] + [end]
    ks = [{"t": round(t, 3), **{k: round(v, 2) for k, v in at(t).items() if k in ("x_pct", "y_pct")}} for t in times]
    first = at(start)
    place = {k: round(first[k], 2) for k in ("x_pct", "y_pct", "w_pct", "h_pct")}
    return place, ks


def apply(sheet: dict) -> list[str]:
    """Lay every follow annotation on the person; the ones that cannot follow fall back to a fixed anchor, and say so."""
    anchors = json.loads((TOOL / "looks/layers.json").read_text())["annotation"]["anchors"]
    notes = []
    for r in (sheet.get("layers") or {}).get("annotations") or []:
        if not follows(r) or r.get("start") is None:
            continue
        samples, by = track(sheet, r["start"], r["start"] + r["duration"])
        size = anchors.get(r.get("fallback") or "center") if r.get("kind") != "arrow" else {"w_pct": 30, "h_pct": 14}
        if not samples:
            fb = r.get("fallback") if r.get("fallback") in anchors else "center"
            r["place"] = dict(anchors[fb])
            r["follow"] = {"by": None, "fell_back_to": fb,
                           "why": "no face track and no subject_box under it — drawn fixed at the anchor, not on the person"}
            notes.append(f"annotation {r.get('id')} ({r.get('kind')} on the {r.get('target')}): nothing tracks the person here — fixed at `{fb}` instead")
            continue
        place, ks = keys(samples, r.get("kind", "circle"), r["start"], r["duration"], size)
        r["place"] = place
        r["follow"] = {"by": by, "keys": ks, "samples": len(samples), "smoothed": f"centred moving average of {SMOOTH}; size held at the median"}
        notes.append(f"annotation {r.get('id')} ({r.get('kind')}) follows the {r.get('target')} by {by} — {len(ks)} keyframes over {r['duration']:.2f}s")
    return notes
