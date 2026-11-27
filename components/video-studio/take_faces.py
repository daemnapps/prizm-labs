"""THE TAKE'S FACE DOORS (2026-11-13): a continuous take (take.py) keeps the people on their character sheets.

Why: hook takes were made from a start picture nobody face-checked, and the motion chain's first frame was fed in its
place; the woman and the first man came out as other people, and every cover copied from the take failed the face
gate. take.py sent pictures to the video model with no face gate at all (seedance.py's own doors have one).

  picture  before anything is bought: the start picture against the sheets of the people in it (take.json
           `in_picture`, a list of cast names; default every cast member with a sheet). Every one must come back SAME
           (video-production face_gate.require). A miss refuses the take and names the person; nothing is sent.
  take     after the take is made: one frame in the middle of every beat of the script, against the sheets of the
           people that beat names (`faces` and `moves`). A beat whose person comes back DIFFERENT is drift: the take is
           kept beside as <out>.drift.mp4, never placed at `out`, and the take stops with the beat and the person.
           The record is <out>.faces.json.

SWITCH: take-faces.json beside this file (`on`, parts `picture`, `take`), or TAKE_FACES_OFF=1 / =<part> on one
machine. Row TAKE-FACES in team/rollbacks.md.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

CONF = HERE / "take-faces.json"


def _conf():
    try:
        return json.loads(CONF.read_text())
    except (OSError, ValueError):
        return {}


def _off():
    return {x.strip() for x in os.environ.get("TAKE_FACES_OFF", "").split(",") if x.strip()}


def on(part) -> bool:
    off = _off()
    c = _conf()
    return not (off & {"1", "all"}) and part not in off and c.get("on", True) is not False and c.get(part, True) is not False


def _gate():
    import settings as ST
    p = ST.part("video-production") / "machine" / "face_gate.py"
    spec = importlib.util.spec_from_file_location("take_faces_gate", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sheet(c):
    """The picture a person's face is checked against: their face master (cast `master`, a portrait) when the take names
    one, else their character sheet. A full-body turnaround leaves the face too small for the reader to confirm."""
    return (c.get("master") or c.get("sheet")) if isinstance(c, dict) else c


def sheets_for(take, names):
    cast = take.get("cast") or {}
    return [str(sheet(cast[n])) for n in names if n in cast and sheet(cast[n]) and Path(str(sheet(cast[n]))).is_file()]


def picture_masters(take):
    names = take.get("in_picture") or list((take.get("cast") or {}).keys())
    return sheets_for(take, names)


def gate_picture(take, gate=None):
    """Refuse (SystemExit) a start picture whose people are not their sheets; returns the record, or None when off or
    the take has no sheets."""
    if not on("picture"):
        return None
    masters = picture_masters(take)
    if not masters:
        return None
    g = gate or _gate()
    return g.require(str(take["picture"]), masters)


def beat_people(line):
    return list(dict.fromkeys(list((line.get("faces") or {}).keys()) + list((line.get("moves") or {}).keys())))


def _seconds(clip):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def _frame(clip, t, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t, "-i", str(clip), "-frames:v", "1", str(out)], check=True)
    return out


def check_take(take, clip, gate=None, frame=_frame, seconds=_seconds):
    """Every beat's people against their sheets, on a frame in the middle of the beat (beats share the take's length
    evenly). Returns {"pass", "beats": [...]}; writes <clip>.faces.json."""
    g = gate or _gate()
    script = take.get("script") or []
    total = seconds(clip)
    n = max(len(script), 1)
    beats = []
    work = Path(str(clip) + ".faces")
    work.mkdir(exist_ok=True)
    for k, line in enumerate(script):
        masters = sheets_for(take, beat_people(line))
        if not masters:
            continue
        t = total * (k + 0.5) / n
        pic = frame(clip, t, work / ("beat-%d.png" % (k + 1)))
        rec = g.stamp(str(pic), masters)
        bad = [(Path(p.get("master", "")).name, p.get("verdict")) for p in rec.get("people") or []
               if p.get("verdict") not in ("SAME", "GROUP")]
        beats.append({"beat": k + 1, "at": round(t, 2), "people": beat_people(line), "pass": bool(rec.get("pass")),
                      "misses": bad})
    res = {"clip": str(clip), "pass": all(b["pass"] for b in beats), "beats": beats}
    Path(str(clip) + ".faces.json").write_text(json.dumps(res, indent=1))
    return res


def hold_drift(take, out, gate=None, **kw):
    """After the take is made: check it; a drifted take moves to <out>.drift.mp4 and stops the run (SystemExit)."""
    if not on("take") or not (take.get("cast") or {}):
        return None
    res = check_take(take, out, gate=gate, **kw)
    if not res["pass"]:
        drift = Path(out).with_suffix(".drift.mp4")
        Path(out).rename(drift)
        miss = next(b for b in res["beats"] if not b["pass"])
        raise SystemExit("the take drifted from its cast: beat %d at %.1f s, %s; kept as %s, not used"
                         % (miss["beat"], miss["at"], "; ".join("%s %s" % m for m in miss["misses"]) or "no face confirmed",
                            drift.name))
    return res
