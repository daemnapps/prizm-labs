#!/usr/bin/env python3
"""shot_timing.py — how long a shot plays and where in its clip it starts. One home for every editing path: the
storyboard plan, the edit map, the edit line (the video editor's hand-off folder run) and the Video Studio all
read these rules from here (owner ruling 2026-11-16, V57 (swipe is the backbone): the swipe gives the idea and the order of scenes; the
edit is ours, frame by frame, clean cuts, clear product use, no awkward pauses).

THE RULES
  1. A shot runs on its action, not the swipe's lengths. A shot that no line is read over plays at most MAX_SHOT
     seconds (2.5 s); the end card at most END_CARD (3 s). A shot under a read plays its share of the read.
  2. Each shot starts on the busiest unbroken stretch of its clip, near where the chain matched it: the stretch of
     `need` seconds with the most movement that crosses none of the clip's own cuts. The cuts are the asset index's
     cut list, plus the cuts measured in the clip itself (the scene detector, cut_check.cuts), plus sudden motion
     jumps (a frame that moves far past the clip's usual motion is a cut the detector rated soft). Nothing may start
     within PAD (0.35 s) of a cut or whip: a cut is found to within a few frames, and a whip or blur runs on past it.
  3. A clip with no unbroken stretch long enough is swapped for the next-best clip that has one (`swap_for_fit`).
  MOMENTS FIRST: a clip the asset index's moments pass has read (components/asset-index/library/moments.py) is never
  read again at edit time: `placed` starts the shot on its clean moment. Only a clip with no moments yet is measured.

    python3 shot_timing.py <clip> <start> <need>     prints the start the rules pick (or "none: swap the clip")

Brand-agnostic: a clip is a file; the index's cuts come in as numbers (`known_cuts`).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

MAX_SHOT = 2.5      # a shot no line is read over plays its action and no more
END_CARD = 3.0      # the end card: the product, held long enough to read the card on it
PAD = 0.35          # no shot starts or ends within this of a cut or a whip
FLOOR = 0.5         # a matched span shorter than this still plays this long
JUMP_MIN = 30.0     # a frame's mean change (0..255) above this AND above JUMP_X times the clip's median is a cut
JUMP_X = 4.0
FPS = 10            # motion is read at this many frames a second, on a tiny grey copy


def _sibling(name):
    """A module beside this one, loaded by its file (never by the search path, so a caller's own module of the same
    name is never shadowed)."""
    import importlib.util
    key = "chain_video_edit_" + name
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, HERE / (name + ".py"))
        m = importlib.util.module_from_spec(spec)
        sys.modules[key] = m
        spec.loader.exec_module(m)
    return sys.modules[key]


def cap(kind: str | None = None) -> float:
    """The most a shot plays when no line is read over it: the end card END_CARD, every other shot MAX_SHOT."""
    return END_CARD if kind == "endcard" else MAX_SHOT


def shot_seconds(length: float | None, kind: str | None = None, floor: float = FLOOR) -> float:
    """The seconds a shot with no read over it plays: its matched length, at least `floor`, at most its cap."""
    try:
        length = float(length)
    except (TypeError, ValueError):
        length = cap(kind)
    return round(min(max(length, floor), cap(kind)), 3)


def unread_seconds(lengths, kind: str | None = None) -> list[float]:
    """Each shot of a stretch nobody speaks over, on its action: [shot_seconds(x)] for every matched length."""
    return [shot_seconds(x, kind) for x in lengths]


# ---------------------------------------------------------------- reading a clip
def motion(file, start: float, length: float, fps: int = FPS) -> list[float]:
    """How much moves in each frame of the clip from `start` for `length` seconds: the mean change from the frame
    before, on a 32x18 grey copy (0..255). [] when the clip cannot be read here."""
    if not file:
        return []
    w, h = 32, 18
    try:
        raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", "%.3f" % max(0.0, start), "-t", "%.3f" % length,
                              "-i", str(file), "-an", "-vf", "fps=%d,scale=%d:%d,format=gray" % (fps, w, h), "-f",
                              "rawvideo", "-"], capture_output=True, timeout=120).stdout
    except Exception:  # noqa: BLE001 - no ffmpeg or no file: nothing measurable
        return []
    n = w * h
    frames = [raw[i:i + n] for i in range(0, len(raw) - n + 1, n)]
    return [sum(abs(a - b) for a, b in zip(x, y)) / n for x, y in zip(frames, frames[1:])]


def measured_cuts(file, start: float, length: float) -> list[float]:
    """The shot changes actually in the clip between start and start+length (cut_check's scene detector on that window
    of the clip). The index's cut list can miss cuts in a fast edit. [] when not measurable here."""
    if not file:
        return []
    try:
        import tempfile
        CC = _sibling("cut_check")
        a = max(0.0, float(start))
        with tempfile.TemporaryDirectory() as d:
            w = str(Path(d) / "w.mp4")
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", "%.3f" % a, "-t", "%.3f" % length, "-i", str(file),
                            "-an", "-vf", "scale=360:-2", "-c:v", "libx264", "-preset", "ultrafast", w], check=True,
                           capture_output=True)
            return [a + c for c in CC.cuts(w)]
    except Exception:  # noqa: BLE001 - not measurable here: the index's list alone decides
        return []


def jump_cuts(mv: list[float], lo: float, fps: int = FPS) -> set[float]:
    """Frames that jump far past the clip's usual motion (above JUMP_MIN and JUMP_X times the median): cuts the
    detector rated soft, busy-looking but a cut all the same. Seconds on the clip's clock."""
    if not mv:
        return set()
    med = sorted(mv)[len(mv) // 2]
    return {round(lo + (i + 1) / fps, 2) for i, m in enumerate(mv) if m > max(JUMP_MIN, JUMP_X * med)}


def crosses(s: float, need: float, cuts, pad: float = PAD) -> bool:
    """Does a shot from s for `need` seconds come within `pad` of one of the cuts?"""
    return any(s - pad < c < s + need + pad for c in cuts)


def best_start(mv: list[float], cuts, lo: float, need: float, fps: int = FPS, pad: float = PAD):
    """The start (from `lo`, in 1/fps steps) of the `need` seconds with the most movement that cross no cut. With no
    motion read, the only candidate is `lo` itself, scored 0. None when every candidate crosses a cut."""
    k = max(1, int(round(need * fps)))
    best = None
    for i in range(0, max(1, len(mv) - k + 1)):
        s = lo + i / fps
        if crosses(s, need, cuts, pad):
            continue
        score = sum(mv[i:i + k]) / k if mv else 0.0
        if best is None or score > best[0]:
            best = (score, round(s, 3))
    return best[1] if best else None


def one_shot_in(start: float, need: float, cuts, reach: float = 6.0, pad: float = PAD):
    """Where to start a pick so it plays `need` seconds without one of the clip's own cuts: the start as placed when it
    already fits, else the nearest unbroken stretch long enough within `reach` seconds of it. None when there is no
    unbroken stretch long enough: the caller swaps the clip."""
    start = float(start or 0)
    cuts = sorted(cuts)
    if not cuts or not crosses(start, need, cuts, pad):
        return start
    edges = [0.0] + cuts + [cuts[-1] + 60.0]
    segs = [(a, b) for a, b in zip(edges, edges[1:]) if abs(a - start) <= reach or a <= start < b]
    fit = [(abs(a + pad - start), a + pad) for a, b in segs if b - a - 2 * pad >= need]
    if fit:
        return round(min(fit)[1], 3)
    return None


def busiest_in(file, start, need: float, before: float = 1.0, after: float = 5.0, fps: int = FPS, known_cuts=(),
               reach_cuts=None, read_motion=motion, read_cuts=measured_cuts):
    """THE START RULE: the start, near where the chain matched the shot (`start`), of the `need` seconds with the most
    going on (the product in use, not a person standing still) that cross none of the clip's own cuts. The cuts are
    `known_cuts` (the asset index's list), the cuts measured in the window, and sudden motion jumps. When nothing
    could be measured and the window's start is blocked, the unbroken-stretch rule alone (`one_shot_in`; its cuts are
    `reach_cuts(start)` when given, else the known ones). None: this clip cannot play the shot unbroken, swap it."""
    lo = max(0.0, float(start or 0) - before)
    span = before + after + need
    cuts = set(float(c) for c in known_cuts or ()) | set(round(c, 2) for c in read_cuts(file, lo, span))
    mv = read_motion(file, lo, span, fps)
    cuts |= jump_cuts(mv, lo, fps)
    at = best_start(mv, sorted(cuts), lo, need, fps)
    if at is None and not mv:
        wide = reach_cuts(float(start or 0)) if reach_cuts else sorted(float(c) for c in known_cuts or ())
        return one_shot_in(start, need, wide)
    return at


# ---------------------------------------------------------------- moments first (owner, 17 Nov: editing leverages the index)
def _moments():
    """The asset index's moments (components/asset-index/library/moments.py), loaded by its file once; None where the
    index is not installed. The moments pass measured every clip once when it entered the index."""
    key = "chain_asset_index_moments"
    if key not in sys.modules:
        f = HERE.parents[1] / "asset-index" / "library" / "moments.py"
        if not f.is_file():
            return None
        import importlib.util
        spec = importlib.util.spec_from_file_location(key, f)
        m = importlib.util.module_from_spec(spec)
        sys.modules[key] = m
        try:
            spec.loader.exec_module(m)
        except Exception:  # noqa: BLE001 - a broken index: every clip is measured live, as before
            sys.modules.pop(key, None)
            return None
    return sys.modules[key]


def placed(brand: str, clip, start, need: float, product: str | None = None, reach: float = 6.0, avoid=()):
    """MOMENTS FIRST: where a shot starts in a clip the moments pass has read, with no read of the clip: the clean
    moment (no text over the video, no blur or transition, not dead, the right product in use when `product` is a
    product key) nearest `start` whose unbroken stretch holds `need` seconds. -> (True, start) / (True, None) = read,
    no clean moment can play it, swap the clip / (False, None) = not read yet: measure it live (busiest_in).
    avoid: (in, out) sections of this clip that other shots already play (one clip section per shot)."""
    MO = _moments()
    if MO is None or not brand:
        return False, None
    try:
        if not MO.known(brand, clip):
            return False, None
        got = MO.place(brand, clip, float(start or 0), need, product, reach, avoid=avoid)
    except Exception:  # noqa: BLE001 - the index could not answer: live, as before
        return False, None
    return True, (got[0] if got else None)


def swap_for_fit(alternates, need: float, fits, used=()):
    """THE SWAP RULE: the next-best clip (in the footage pass's order) that can play the shot unbroken. alternates:
    [{"path", "in", "shows"}]; fits(path, start, need) -> start or None (busiest_in). Returns (alternate, start) or
    None. A clip already used for another shot is passed over."""
    for alt in alternates or []:
        if not alt.get("path") or alt["path"] in used:
            continue
        at = fits(alt["path"], alt.get("in") or 0, need)
        if at is not None:
            return alt, at
    return None


def rules_md() -> list[str]:
    """The rules as the video editor reads them in the hand-off's edit notes (editor_handoff.edit_notes_md)."""
    return ["## How to cut", "",
            f"- **Shots run on their action, not the swipe's lengths.** A shot with no line read over it plays at most "
            f"{MAX_SHOT:g} s; the end card at most {END_CARD:g} s. A shot under a line plays its share of the line.",
            "- **Start each shot on the busiest unbroken stretch of its clip**: the product in use, not a person standing "
            f"still. Never start or end within {PAD:g} s of a cut or a whip inside the clip.",
            "- **A clip with no unbroken stretch long enough is swapped** for the next-best clip that has one.",
            "- **Look at the frames of every shot**: the product in view and being used, no text laid over the video, "
            "no blur or transition inside the shot, something happening, and it shows what the shot is meant to show. "
            "A shot that misses takes the next-best clip that passes.",
            "- **Clean cuts**: every cut in the finished video is one you placed. No cut from inside a clip, no shot "
            "under 3 frames.",
            "- The swipe gives the idea and the order of the scenes. Where our shot differs from the swipe's, that is "
            "fine: it is noted, never a fault.", ""]


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) != 3:
        sys.exit(__doc__)
    got = busiest_in(a[0], float(a[1]), float(a[2]))
    print("none: swap the clip" if got is None else got)
