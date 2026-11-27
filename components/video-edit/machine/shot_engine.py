"""shot_engine.py — a video as its shots, and a timeline of shots as a video. Free: ffmpeg on this machine, no model.

    shots(video, framemap=None)    [{id, start, end, seconds, what}] — the teardown's own frame map when there is one,
                                   else the cuts found here
    energy(video)                  {"cuts_per_s", "motion"} — how hard the picture works (a measured number, not taste)
    build(items, out, audio=None, fps=30, size=(1080, 1920), seconds=None)
                                   one video from items {file, in, seconds}: each laid at normal speed, never slowed and
                                   never frozen; a clip shorter than its slot is refused by name
    find(brand, seen, seconds, used, tries=40)   our own footage for a shot: long enough, no words burned in, never twice

The one engine under the Ad Multiplier (ad-variations/machine/multiply.py) and the swipe edit (swipe_edit.py). Words,
captions and cards are never drawn here: compose.py is the only thing that draws a word. Python 3.9, standard library.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_SHOT = 0.2


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("%s failed: %s" % (Path(cmd[0]).name, (r.stderr or r.stdout).strip()[-300:]))
    return r


def length(video):
    return float(_run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)]).stdout.strip())


def has_audio(video):
    return bool(_run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(video)]).stdout.strip())


def cut_times(video, thr=0.3):
    r = _run(["ffmpeg", "-v", "info", "-i", str(video), "-vf", "select='gt(scene,%s)',showinfo" % thr, "-an", "-f", "null", "-"])
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def plain(text):
    """A shot's words with the frame positions taken out: what is seen, never where in the frame."""
    t = re.sub(r"\([^)]*%[^)]*\)|\d+\s*[–-]\s*\d+\s*%[^,.;]*|\d+\s*%[^,.;]*", "", text)
    t = re.sub(r"\b(?:centered|center frame|top|bottom|left|right|upper|lower)(?: (?:half|third|edge|center|corner))?(?: of (?:the )?frame)?\b", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip(" ,.;")


def shots(video, framemap=None):
    total = length(video)
    if framemap:
        d = json.loads(Path(framemap).read_text())
        out = []
        for s in d["shots"]:
            m = s.get("map") or {}
            does = " ".join(str(x.get("does") or "") for x in m.get("moments") or [])
            says = any("speak" in str(x).lower() or "talk" in str(x).lower() for x in [does] + [x.get("what") for x in m.get("sound") or []])
            out.append({"id": s["id"], "start": float(s["start"]), "end": min(float(s["end"]), total), "what": plain(str(m.get("start_frame") or "")), "does": plain(does),
                        "camera": m.get("camera") or {}, "text": [t.get("text") for t in m.get("on_screen") or []], "talks": says})
    else:
        ts = [0.0] + [t for t in cut_times(video) if t > MIN_SHOT] + [total]
        out, a = [], ts[0]
        for b in ts[1:]:
            if b - a >= MIN_SHOT or b == total:
                out.append({"id": "K%02d" % (len(out) + 1), "start": a, "end": b, "what": "", "does": "", "camera": {}, "text": [], "talks": None})
                a = b
    for s in out:
        s["seconds"] = round(s["end"] - s["start"], 3)
    return [s for s in out if s["seconds"] > 0.04]


def energy(video):
    """Cuts a second, and how much the picture changes frame to frame (0 = a still), both measured."""
    total = length(video)
    r = _run(["ffmpeg", "-v", "info", "-i", str(video), "-vf", "fps=12,scale=160:-2,signalstats,metadata=print:key=lavfi.signalstats.YDIF", "-an", "-f", "null", "-"])
    y = [float(x) for x in re.findall(r"YDIF=([0-9.]+)", r.stderr)]
    return {"cuts_per_s": round(len(cut_times(video)) / total, 3), "motion": round(sum(y) / max(1, len(y)), 2), "seconds": round(total, 2)}


def build(items, out, audio=None, fps=30, size=(1080, 1920), seconds=None):
    for it in items:
        have = length(it["file"]) - float(it.get("in") or 0)
        if have + 0.05 < it["seconds"]:
            raise ValueError("%s: %.2f s of footage for a %.2f s shot — a clip is never slowed or frozen" % (it.get("id") or Path(it["file"]).name, have, it["seconds"]))
    w, h = size
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        parts, clock, frames = [], 0.0, 0
        for i, it in enumerate(items):
            clock += it["seconds"]
            n = max(1, round(clock * fps) - frames)                    # whole frames off one running clock: no drift
            frames += n
            p = Path(d) / ("%03d.mp4" % i)
            vf = "fps=%d,scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1,format=yuv420p" % (fps, w, h, w, h)
            _run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % float(it.get("in") or 0), "-i", str(it["file"]), "-vf", vf, "-frames:v", str(n), "-an",
                  "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", str(p)])
            parts.append(p)
        lst = Path(d) / "l.txt"
        lst.write_text("".join("file '%s'\n" % p for p in parts))
        pic = Path(d) / "pic.mp4"
        _run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(pic)])
        if audio:
            _run(["ffmpeg", "-v", "error", "-y", "-i", str(pic), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                  "-t", "%.3f" % (frames / fps), "-movflags", "+faststart", str(out)])
        else:
            _run(["ffmpeg", "-v", "error", "-y", "-i", str(pic), "-c", "copy", "-movflags", "+faststart", str(out)])
    return {"file": str(out), "seconds": round(length(out), 2), "shots": len(items)}


def _asset_search():
    sys.path.append(str(HERE.parents[1] / "asset-index" / "machine"))
    import search
    return search


def _mount():
    try:
        sys.path.append(str(HERE.parents[1] / "brandpath"))
        import drive_index
        return Path(drive_index.mount())
    except Exception:  # noqa: BLE001  no drive on this machine: the preview copies are what there is
        return None


def full(hit, root=None):
    """(the clip's full file, "full"), else (its preview copy, "preview")."""
    root = root or _mount()
    sp = re.sub(r"^Shared Assets/", "", str(hit.get("shared_path") or ""))
    for f in ([root / sp, root / "Shared Assets" / sp] if root and sp else []):
        if f.is_file():
            return f, "full"
    return Path(hit.get("proxy") or ""), "preview"


_LOADED = {}


def _by_path(rel, name):
    if name not in _LOADED:
        import importlib.util
        f = HERE.parents[1] / rel
        spec = importlib.util.spec_from_file_location(name, str(f))
        m = importlib.util.module_from_spec(spec)
        sys.path.append(str(f.parent))
        spec.loader.exec_module(m)
        _LOADED[name] = m
    return _LOADED[name]


def words_in(file, a, seconds):
    """Every line of text this machine reads on three frames of the piece (macOS Vision, free). None: no reader here."""
    try:
        CG = _by_path("video-production/machine/clip_gate.py", "se_clip_gate")
        out = []
        with tempfile.TemporaryDirectory() as d:
            for i, k in enumerate((0.1, 0.5, 0.9)):
                f = Path(d) / ("%d.png" % i)
                _run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % (a + seconds * k), "-i", str(file), "-frames:v", "1", str(f)])
                if f.is_file():
                    out += [(h, t) for h, t in CG.text_boxes(f)]
        return out
    except Exception:  # noqa: BLE001  no reader on this machine
        return None


def burned(rows):
    """The text a viewer reads as words on the video: a line three letters or longer, big enough to read on a phone. A
    product's own small label passes."""
    return [t for h, t in rows or [] if h >= 0.016 and len(re.findall(r"[A-Za-z]", t)) >= 3]


def sheet(rows, out):
    """One picture to look at before anything is used: each row a [first, middle, last] frame of (file, in, seconds)."""
    with tempfile.TemporaryDirectory() as d:
        strips = []
        for n, (f, a, sec) in enumerate(rows):
            fr = []
            for i, k in enumerate((0.1, 0.5, 0.9)):
                p = Path(d) / ("%d_%d.png" % (n, i))
                _run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % (a + sec * k), "-i", str(f), "-frames:v", "1",
                      "-vf", "scale=180:320:force_original_aspect_ratio=increase,crop=180:320", str(p)])
                fr += ["-i", str(p)]
            s = Path(d) / ("s%d.png" % n)
            _run(["ffmpeg", "-v", "error", "-y"] + fr + ["-filter_complex", "hstack=inputs=3", str(s)])
            strips += ["-i", str(s)]
        n = len(rows)
        _run(["ffmpeg", "-v", "error", "-y"] + strips + (["-filter_complex", "vstack=inputs=%d" % n] if n > 1 else []) + [str(out)])
    return str(out)


def find(brand, seen, seconds, used, tries=60, floor=0.45, where=None, does=""):
    """The best piece of our own footage for this shot, or None. `used` holds every clip already laid."""
    hits = _asset_search().search(seen, "", brand=brand, core=does, per=tries, exclude_talking=True, scenes_per_clip=2, where=where)
    try:
        hits = _by_path("asset-index/library/library.py", "se_library").enrich(hits, brand)     # each clip's own text marks
    except Exception:  # noqa: BLE001  no built library for this brand: the words are read off the frames below
        pass
    for h in hits:
        marks = h.get("text_marks")
        clean = list(marks) == ["clean"] if marks is not None else True
        if h["score"] < floor or not clean or any(c in (h["clip_id"], str(h.get("shows"))) for c, _ in used):
            continue
        f, copy = full(h)
        if not f.is_file():
            continue
        a = float(h.get("in") or 0)
        try:
            if length(f) - a < seconds + 0.05:
                continue
            words = words_in(f, a, seconds)
        except (RuntimeError, ValueError):
            continue
        if burned(words) or (words is None and marks is None):           # words on it, or nobody could check
            continue
        used.add((h["clip_id"], a))
        used.add((str(h.get("shows")), a))           # the same footage filed twice under two ids is one clip
        return {"file": str(f), "in": a, "seconds": seconds, "shared_path": h.get("shared_path"), "shows": h.get("shows"), "score": h["score"],
                "copy": copy, "rights": (h.get("rights") or {}).get("state")}
    return None
