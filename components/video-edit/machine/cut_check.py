#!/usr/bin/env python3
"""cut_check.py — the edit's own checks on a made video, measured on the file, never claimed. One home for every
editing path: the edit line's final checks (run.py, the video editor's hand-off folder run), the sound pass
(listen.py) and the Video Studio's swipe check all read them from here (owner ruling 2026-11-16, V57 (swipe is the backbone)).

  clean_cuts   every cut in a made scene is one we placed (within 3 frames of a shot boundary): no stray cut from
               inside one of our clips, and no shot under 3 frames. How long each shot runs is never graded.
  no_flash     no shot in the finished cut is shorter than 3 frames.
  words_heard  the cut's speech matches the script (WORDS_BAR or more). An ad with no spoken script (a song, a
               music-only cut) has nothing to hear: the check passes and says so.
  differs      a shot that differs from the swipe's is NOTED, never failed: the swipe gives the idea, the edit is ours.

    python3 cut_check.py <video> <cut at> [<cut at> ...]     clean_cuts + no_flash of a video against the cuts we placed
"""
from __future__ import annotations

import difflib
import re
import subprocess
import sys

FRAME = 1001 / 24000         # one frame at 23.976 fps: the shortest shot allowed is three of them
SLACK = 0.05                 # a measured cut is ours when it is within 3 frames plus this of one we placed
WORDS_BAR = 0.95


def cuts(video, thr: float = 0.27) -> list[float]:
    """Every picture change in the video (ffmpeg's scene score above thr), in seconds."""
    err = subprocess.run(["ffmpeg", "-nostdin", "-i", str(video), "-vf", f"select='gt(scene,{thr})',showinfo", "-an", "-f",
                          "null", "-"], capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", err)]


def dur(video) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                                capture_output=True, text=True).stdout)


def stray(found, placed, frame: float = FRAME) -> list[float]:
    """The measured cuts that are none of ours: further than 3 frames (+SLACK) from every cut we placed."""
    return [round(x, 2) for x in found if not any(abs(x - b) <= 3 * frame + SLACK for b in placed)]


def flashes(found, length: float, frame: float = FRAME) -> list[float]:
    """Where a shot under 3 frames starts, from the measured cuts of a video `length` seconds long."""
    edges = [0.0] + sorted(found) + [length]
    return [round(edges[i], 2) for i in range(len(edges) - 1) if edges[i + 1] - edges[i] < 3 * frame]


def scene_fault(name: str, found, length: float, placed) -> str | None:
    """One scene's clean-cut fault, in words, or None when every cut is ours and no shot is a flash."""
    s, f = stray(found, placed), flashes(found, length)
    if not s and not f:
        return None
    return "%s:%s%s" % (name, " a cut inside a shot at %s s" % s if s else "", " a flash under 3 frames at %s s" % f if f else "")


def clean_cuts(faults) -> dict:
    """The clean_cuts row from every scene's fault (scene_fault, or "<scene>: not made")."""
    bad = [x for x in faults if x]
    return {"check": "clean_cuts", "pass": not bad,
            "detail": "every cut is one we placed, no flash frames" if not bad else "; ".join(bad)}


def no_flash(found, length: float) -> dict:
    short = flashes(found, length)
    return {"check": "no_flash", "pass": not short, "detail": "no shot under 3 frames" if not short else "short at %s" % short}


def placed_of(sheet: dict) -> list[float]:
    """The cuts a cut sheet places: every picture row's start and end, the video's own start and end left out."""
    rows = [r for r in (sheet or {}).get("picture") or [] if r.get("duration")]
    if not rows:
        return []
    end = max(float(r["start"]) + float(r["duration"]) for r in rows)
    at = {round(float(r["start"]), 3) for r in rows} | {round(float(r["start"]) + float(r["duration"]), 3) for r in rows}
    return sorted(x for x in at if 0.05 < x < end - 0.05)


TRANSITION_S = 0.6           # a drawn transition the sheet places (a whip, a wipe) reads as cuts this far either side


def transition_windows(sheet: dict) -> list[tuple[float, float]]:
    """Where the sheet lays a drawn transition: TRANSITION_S either side of the end of the scene it follows. A cut the
    detector reads inside one is that transition, placed by us."""
    tr = ((sheet or {}).get("layers") or {}).get("transitions") or (sheet or {}).get("transitions") or []
    rows = [r for r in (sheet or {}).get("picture") or [] if r.get("duration")]
    out = []
    for t in tr:
        ends = [float(r["start"]) + float(r["duration"]) for r in rows if r.get("scene") == t.get("after_scene")]
        if ends and str(t.get("kind") or "cut") != "cut":
            out.append((max(ends) - TRANSITION_S, max(ends) + TRANSITION_S))
    return out


def on_sheet(video, sheet: dict, found=None, length=None) -> list[dict]:
    """The edit line's rows for a finished video against its cut sheet: clean_cuts (every cut one the sheet places,
    no flash) and no_flash. A drawn transition the sheet lays is ours (transition_windows). `found` / `length` are
    measured from the video when not given."""
    found = cuts(video) if found is None else found
    length = dur(video) if length is None else length
    wins = transition_windows(sheet)
    found = [x for x in found if not any(a <= x <= b for a, b in wins)]
    return [clean_cuts([scene_fault("the cut", found, length, placed_of(sheet))]), no_flash(found, length)]


# ---------------------------------------------------------------- words heard
_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
_SAID = {"gonna": "going to", "wanna": "want to", "gotta": "got to", "mmm": "mm", "mmmm": "mm", "hmm": "mm"}


def _num(n: int) -> str:
    """A whole number as it is spoken (to the millions): 12000 -> twelve thousand."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else " " + _ONES[n % 10])
    for size, word in ((1000000, "million"), (1000, "thousand"), (100, "hundred")):
        if n >= size:
            return _num(n // size) + " " + word + ("" if n % size == 0 else " " + _num(n % size))


def canon(words) -> list[str]:
    """Words compared the way they are spoken, the same on both sides: numbers in words (10 -> ten), an acronym letter by
    letter (rpm -> r p m), spoken forms (gonna -> going to, mmm -> mm), curly apostrophes straightened. A transcript's
    spelling never counts as a missed word."""
    out = []
    for w in words:
        w = re.sub(r"(?<=\d),(?=\d)", "", w.replace("’", "'").lower())     # 200,000 is one number
        for t in re.findall(r"[a-z0-9']+", w):
            if t.isdigit():
                out += _num(int(t)).split()
            elif t in ("rpm",):
                out += list(t)
            else:
                out += _SAID.get(t, t).split()
    return out


def has_script(script_words) -> bool:
    """Is anything scripted to be said? A song ad or a music-only cut has no spoken script."""
    return any(str(w).strip() for w in script_words or ())


def words_heard(script_words, heard_words, bar: float = WORDS_BAR) -> dict:
    """The words_heard row: the script (words) against what the cut's speech was heard as (words). No spoken script:
    nothing to hear, the check passes and says so."""
    want = canon(script_words or [])
    if not want:
        return {"check": "words_heard", "pass": True, "detail": "no spoken script in this ad"}
    m = difflib.SequenceMatcher(None, want, canon(heard_words or [])).ratio()
    return {"check": "words_heard", "pass": m >= bar, "detail": "%.3f of the script heard" % m}


# ---------------------------------------------------------------- against the swipe
def differs(rows, check: str = "shots_copy") -> dict | None:
    """A shot that differs from the swipe's is noted, never failed (V57 (swipe is the backbone)). rows: [(shot id, how it differs)]. None when
    nothing differs."""
    rows = [r for r in rows or [] if r]
    if not rows:
        return None
    return {"check": check, "pass": True, "note": True,
            "detail": "ours, not the swipe's (noted): " + "; ".join("%s %s" % (a, b) for a, b in rows)}


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 1:
        sys.exit(__doc__)
    found, length = cuts(a[0]), dur(a[0])
    rows = [clean_cuts([scene_fault("the cut", found, length, [float(x) for x in a[1:]])]), no_flash(found, length)]
    for r in rows:
        print("%s %-11s %s" % ("✓" if r["pass"] else "✗", r["check"], r["detail"]))
    sys.exit(0 if all(r["pass"] for r in rows) else 1)
