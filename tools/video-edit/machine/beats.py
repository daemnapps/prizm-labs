#!/usr/bin/env python3
"""beats.py — the music's beats on the final clock, and cuts / graphic hits snapped to them.

    attach(sheet, root, controls=None) -> sheet   music.beats (final clock) + snaps within the tolerance dial
    snap(sheet, beats, tolerance)       -> [moves] the pure snap (tested)
    python3 machine/beats.py detect <audio>       (runs in the helpers venv: librosa beat_track → JSON)

What may move, and why only these: a B-roll clip laid over talking A-roll (the A-roll
underneath keeps the sound and the lips, so the cover can slide a few frames), and the
start of a graphic layer (icons, annotations, platform UI, lower thirds). A talking cut,
a voice cut, a plate and a scene hand-off NEVER move — they carry the words.
Every move is recorded in sheet["beat_snaps"] with where it came from.

librosa (ISC) runs in the helpers venv; without it the beats fall back to the bank
row's tempo grid (tempo_bpm, first beat at the track's start) and the sheet says so.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
sys.path.insert(0, str(HERE))
SNAP_LAYERS = ("icons", "annotations", "platform_ui", "lower_thirds")


def tolerance(controls: dict | None) -> tuple[float, bool]:
    c = (controls or {}).get("beats") or {}
    d = json.loads((TOOL / "looks/retention.json").read_text()).get("beats") or {}
    return float(c.get("snap_tolerance_s", d.get("snap_tolerance_s", 0.12))), bool(c.get("snap", True))


def detect_here(audio: str) -> dict:
    """Run inside the venv: librosa's beat tracker on the whole track (source seconds)."""
    import librosa
    y, sr = librosa.load(audio, sr=22050, mono=True)
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    times = librosa.frames_to_time(frames, sr=sr)
    t = float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo)
    return {"tempo_bpm": round(t, 2), "beats": [round(float(x), 3) for x in times], "by": f"librosa {librosa.__version__} beat_track"}


def detect(audio: Path, bpm: float | None = None, seconds: float | None = None) -> dict:
    import helpers
    try:
        return helpers.call("beats.py", "detect", str(audio), timeout=300)
    except Exception as e:
        if not bpm:
            return {"tempo_bpm": None, "beats": [], "by": f"none — {e}"}
        step = 60.0 / float(bpm)
        n = int((seconds or 600) / step) + 1
        return {"tempo_bpm": bpm, "beats": [round(i * step, 3) for i in range(n)], "by": f"tempo grid from the bank row ({bpm} BPM) — librosa not reachable: {e}"}


def to_final(music: dict, src_beats: list[float], end: float) -> list[float]:
    ss, st = music.get("source_start", 0) or 0, music.get("start", 0) or 0
    return [round(b - ss + st, 3) for b in src_beats if 0 <= b - ss + st <= end + 1e-6]


def _covered(spans: list[tuple[float, float]], a: float, b: float) -> bool:
    cur = a
    for s, e in sorted(spans):
        if s <= cur + 0.02 and e > cur:
            cur = e
        if cur >= b - 0.02:
            return True
    return cur >= b - 0.02


def nearest(beats: list[float], t: float, tol: float) -> float | None:
    best = min(beats, key=lambda b: abs(b - t), default=None)
    return best if best is not None and abs(best - t) <= tol + 1e-9 else None


def snap(sheet: dict, beats: list[float], tol: float) -> list[dict]:
    pics = sheet.get("picture") or []
    end = max((c["start"] + c["duration"] for c in pics), default=0.0)
    a_roll = [(c["start"], c["start"] + c["duration"]) for c in pics if c.get("roll") == "a" and c.get("talks")]
    moves = []
    for c in pics:
        if c.get("roll") != "b" or c.get("kind") not in (None, "broll"):
            continue
        b = nearest(beats, c["start"], tol)
        if b is None or abs(b - c["start"]) < 0.005:
            continue
        d = b - c["start"]
        s1, e1 = c["start"] + d, c["start"] + c["duration"] + d
        if s1 < 0 or e1 > end + 1e-6 or not _covered(a_roll, s1, e1):
            continue  # only a cover over talking A-roll slides; anything else would open a hole
        moves.append({"what": "b-roll", "id": c["id"], "from": round(c["start"], 3), "to": round(s1, 3), "beat": b})
        for x in sheet.get("sfx") or []:  # its sound effect travels with it
            if x.get("for") in (c["id"], c.get("scene")) and x.get("at") is not None and abs(x["at"] - c["start"]) < 0.05:
                x["at"] = round(x["at"] + d, 3)
        c["start"] = round(s1, 3)
    L = sheet.get("layers") or {}
    span: dict = {}
    for c in pics:
        sc = c.get("scene") or c["id"]
        lo, hi = span.get(sc, (c["start"], c["start"] + c["duration"]))
        span[sc] = (min(lo, c["start"]), max(hi, c["start"] + c["duration"]))
    for k in SNAP_LAYERS:
        for r in L.get(k) or []:
            if r.get("start") is None:
                continue
            b = nearest(beats, r["start"], tol)
            if b is None or abs(b - r["start"]) < 0.005 or b < 0 or b + r["duration"] > end + 0.05:
                continue
            lo, hi = span.get(r.get("scene"), (0.0, end))
            if b < lo - 0.005 or b >= hi:
                continue  # a graphic never lands before its own scene's cut, or after it
            moves.append({"what": k, "id": r.get("id"), "from": round(r["start"], 3), "to": b, "beat": b})
            r["start"] = b
    return moves


def attach(sheet: dict, root: Path, controls: dict | None = None) -> dict:
    music = sheet.get("music")
    if not music or not music.get("src"):
        return sheet
    src = Path(music["src"]) if Path(music["src"]).is_absolute() else Path(root) / music["src"]
    end = max((c["start"] + c["duration"] for c in sheet.get("picture") or []), default=0.0)
    got = detect(src, music.get("tempo_bpm"), (music.get("source_start") or 0) + end + 5)
    music["beats"] = to_final(music, got["beats"], end)
    music["beats_by"] = got["by"]
    if got.get("tempo_bpm"):
        music["tempo_detected_bpm"] = got["tempo_bpm"]
    tol, on = tolerance(controls or sheet.get("controls"))
    sheet["beat_snaps"] = snap(sheet, music["beats"], tol) if on and music["beats"] else []
    sheet["beat_snap_tolerance_s"] = tol
    return sheet


if __name__ == "__main__":
    if sys.argv[1:2] == ["detect"]:
        print(json.dumps(detect_here(sys.argv[2])))
    else:
        print(__doc__)
