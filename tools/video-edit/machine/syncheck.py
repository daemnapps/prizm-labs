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
