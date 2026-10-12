#!/usr/bin/env python3
"""syncheck.py — are the lips in time? Measures how far the finished video's
sound has slipped against the talking clip it came from, for one span.

    lag(final, final_at, source, source_at, seconds) -> seconds (+ = sound late) | None

The picture in that span IS the source clip from `source_at`; if the sound in
the final lines up with the source's own sound, the lips line up. Loudness
envelopes at 200 Hz, best match within ±0.3 s. Pure Python + ffmpeg.
"""
from __future__ import annotations
import struct, subprocess
from pathlib import Path

RATE, HOP = 8000, 40  # 8 kHz, 5 ms hops


def envelope(path: Path, at: float, seconds: float) -> list[float]:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, at):.3f}", "-t", f"{seconds:.3f}", "-i", str(path), "-vn", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
                         capture_output=True).stdout
    n = len(raw) // 2
    pcm = struct.unpack(f"<{n}h", raw[:n * 2])
    env = [sum(abs(x) for x in pcm[i:i + HOP]) / HOP for i in range(0, n - HOP, HOP)]
    m = sum(env) / len(env) if env else 0
    return [e - m for e in env]


def lag(final: Path, final_at: float, source: Path, source_at: float, seconds: float, reach: float = 0.3) -> float | None:
    pad = reach
    a = envelope(final, final_at - pad if final_at >= pad else 0, seconds + (pad if final_at >= pad else final_at) + pad)
    lead = pad if final_at >= pad else final_at
    b = envelope(source, source_at, seconds)
    if len(b) < 20 or len(a) < len(b):
        return None
    step = HOP / RATE
    best, best_k = None, 0
    for k in range(0, len(a) - len(b) + 1):
        s = sum(x * y for x, y in zip(a[k:k + len(b)], b))
        if best is None or s > best:
            best, best_k = s, k
    return round(best_k * step - lead, 3)


# ---- the picture side (4 Oct 2026): the sound can be right and the PICTURE late — overlapping pieces once
# slid the picture ~0.4 s behind the voice by the end of an ad. Find where the finished frames sit in the source.

GW, GH = 48, 85  # tiny grey frames: enough to tell one frame of a talking clip from the next


def frames(path: Path, at: float, seconds: float, vf: str = "", fps: int = 30) -> list[bytes]:
    chain = (vf + "," if vf else "") + f"fps={fps},scale={GW}:{GH},format=gray"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, at):.3f}", "-i", str(path), "-t", f"{seconds:.3f}",
                          "-vf", chain, "-f", "rawvideo", "-"], capture_output=True).stdout
    n = GW * GH
    return [raw[i:i + n] for i in range(0, len(raw) - n + 1, n)]


def picture_lag(final: Path, final_at: float, source: Path, source_at: float, vf: str = "",
                seconds: float = 0.5, reach: float = 0.6, fps: int = 30) -> float | None:
    """Seconds the finished PICTURE sits behind (+) or ahead (−) of where the map put it: the frames of `final` from
    `final_at` matched against the source clip around `source_at` (through `vf`, the same crop the render used)."""
    a = frames(final, final_at, seconds, fps=fps)
    lo = max(0.0, source_at - reach)
    b = frames(source, lo, seconds + (source_at - lo) + reach, vf, fps)
    if len(a) < 5 or len(b) < len(a):
        return None
    sad = lambda x, y: sum(abs(p - q) for p, q in zip(x, y))
    scores = [sum(sad(x, y) for x, y in zip(a, b[k:k + len(a)])) for k in range(len(b) - len(a) + 1)]
    best = min(range(len(scores)), key=scores.__getitem__)
    # NO CLEAR MATCH IS NO READING (2026-10-08, the athlete): on a shot that barely moves every offset scores alike and the
    # minimum drifts to the edge of the search, which read as "slipped 18 frames" on clips that were in time. A best
    # match at the very edge of the reach, or one no better than the typical offset, is unmeasurable here → None.
    srt = sorted(scores)
    typical = srt[len(srt) // 2] or 1
    if best in (0, len(scores) - 1) and lo > 0 or scores[best] > 0.9 * typical:
        return None
    return round((source_at - lo) - best / fps, 3)
