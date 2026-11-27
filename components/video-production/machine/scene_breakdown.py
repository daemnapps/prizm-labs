"""SCENE BREAKDOWN — each scene of the swipe read to its smallest elements (2026-10-28).

One cheap read per scene of the swipe's own footage (prompts/v2/scene-breakdown-v1-owner.md): the camera's hand drift,
where the person looks, every prop's state and lift, where each ingredient goes and its texture, what each action lands
on, the sound effects, the atmosphere, the explainer graphic's style and the captions' look and place. Saved per scene in
the run's `scene-breakdown.json`; the clip prompt states the elements (`prompt_lines`) and the clip judge checks them
(`judge_lines`), and the board shows them on the scene.

    python3 scene_breakdown.py <video-production run> [G01 G02 ...]
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPT = HERE.parent / "prompts" / "v2" / "scene-breakdown-v2-owner.md"
FILE = "scene-breakdown.json"
FIELDS = ("camera", "gaze", "props", "continuity", "actions", "sound", "atmosphere", "explainer", "captions", "pace", "manner")
# what the clip itself carries, in words that fit OUR objects (the edit lays sound, captions and explainers; pace is the
# voice's; the swipe's props, continuity and actions name ITS objects, so they stay on the board as reference, and the
# clip's own timeline and the physical-sense line cover ours)
FOR_CLIP = ("camera", "gaze", "manner", "atmosphere")


def _load(name):
    spec = importlib.util.spec_from_file_location(f"vm_sb_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load(run: Path) -> dict:
    p = Path(run) / FILE
    try:
        return json.loads(p.read_text()) if p.is_file() else {}
    except ValueError:
        return {}


def spans(run: Path) -> dict:
    sb = json.loads((Path(run) / "storyboard.json").read_text())
    return {g["id"]: (g.get("swipe") or {}).get("span") for g in sb.get("sections") or [] if (g.get("swipe") or {}).get("span")}


def _gray(f: Path, w: int = 192, fps: int = 6) -> tuple:
    h = int(w * 16 / 9)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-vf", f"fps={fps},scale={w}:{h},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    n = w * h
    return [raw[i:i + n] for i in range(0, len(raw) - n + 1, n)], w, h


def _shift(a: bytes, b: bytes, w: int, h: int, r: int = 5) -> tuple:
    """How far frame b sits from frame a, read on the frame's two outer quarters (the room, not the person)."""
    xs = list(range(r + 1, w // 4)) + list(range(w - w // 4, w - r - 1))
    best = None
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            s = 0
            for y in range(r + 1, h - r - 1, 2):
                ra, rb = y * w, (y + dy) * w + dx
                for x in xs:
                    s += abs(a[ra + x] - b[rb + x])
            if best is None or s < best[0]:
                best = (s, dx, dy)
    return best[1], best[2]


def camera_drift(f: Path) -> dict:
    """MEASURED, never read (a model watching at one frame a
    second calls a held phone "propped still"): the room's shift frame by frame, 6 a second. A phone held by a hand
    drifts by a pixel or two often; a propped phone does not move at all."""
    fr, w, h = _gray(f)
    path = [(0, 0)] + [_shift(fr[0], fr[i], w, h) for i in range(1, len(fr))]
    most = max((max(abs(x), abs(y)) for x, y in path), default=0)
    changes = sum(1 for i in range(1, len(path)) if path[i] != path[i - 1])
    held = most >= 1 and changes >= 4
    pct = round(100.0 * most / w, 1)
    line = (f"Held by a hand, not propped: a very subtle, constant drift (up to {pct}% of the frame), the small sway of "
            "someone holding the phone; never a zoom or a cut." if held else "Propped still: the frame does not move.")
    return {"held": held, "most_pct": pct, "changes": changes, "frames": len(fr), "line": line}


def read(run: Path, gid: str, ask=None) -> dict:
    """One scene's breakdown, read from the swipe's own footage for that scene (with its sound). Saved and returned."""
    run = Path(run).resolve()
    span = spans(run).get(gid)
    if not span:
        raise ValueError(f"{gid}: the scene has no swipe span")
    src = _load("effects").teardown_of(run) / "source.mp4"
    seg = run / "scene-breakdown" / f"{gid}-swipe.mp4"
    seg.parent.mkdir(parents=True, exist_ok=True)
    if not seg.is_file():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{float(span[0]):.2f}", "-to", f"{float(span[1]):.2f}",
                        "-i", str(src), "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-c:a", "aac", str(seg)],
                       check=True)
    V = _load("v2_checks")
    text, info = (ask or V.ask)(run, f"{gid}-scene-breakdown", PROMPT.read_text(), [seg])
    got = V.json_of(text) or {}
    rec = {k: [str(x) for x in got.get(k) or [] if str(x).strip()] for k in FIELDS + ("must_match",)}
    drift = camera_drift(seg)
    # the measured camera wins over the read: its line goes first, and a read that calls a held phone still is dropped
    rec["camera"] = [drift["line"]] + [x for x in rec["camera"]
                                       if not (drift["held"] and re.search(r"\b(still|static|propped|no movement)\b", x, re.I))]
    rec.update(span=span, swipe=str(seg.relative_to(run)), by=info.get("model"), prompt=PROMPT.name, drift=drift)
    allr = load(run)
    allr[gid] = rec
    (run / FILE).write_text(json.dumps(allr, indent=1) + "\n")
    return rec


def of_call(run: Path, call: dict) -> dict:
    """The breakdown of the scene a clip call belongs to (`G02-C1` → `G02`); {} when it was not read."""
    gid = str(call.get("take_of") or call.get("id") or "").split("-")[0]
    return load(run).get(gid) or {}


def prompt_lines(rec: dict) -> str:
    """The swipe's elements as the clip prompt states them: how the camera is held, where the eyes go, how each prop is
    handled, where each ingredient goes, what each action lands on, and the atmosphere."""
    if not rec:
        return ""
    names = {"camera": "Camera, as the swipe", "gaze": "Where the eyes go", "manner": "How things are handled, as the swipe",
             "atmosphere": "Atmosphere"}
    return "\n".join(f"{names[k]}: " + " ".join(x.rstrip(".") + "." for x in rec[k]) for k in FOR_CLIP if rec.get(k))


NOT_THE_CLIPS = re.compile(r"\b(captions?|text|words on|animated|animation|graphics?|cut-?away|transparent|see-through|"
                           r"explainer|overlay)\b", re.I)
STILL_WORDS = re.compile(r"\b(static|still|propped|locked|no movement)\b", re.I)


def judge_lines(rec: dict) -> str:
    """The elements the clip judge holds the take to (check 14): what the clip itself must carry. Captions and the
    explainer are laid by the edit and the effect step, so they are not asked of the clip; the measured camera replaces
    a read that calls a held phone still."""
    held = (rec.get("drift") or {}).get("held")
    must = [x for x in rec.get("must_match") or [] if not NOT_THE_CLIPS.search(x)
            and not (held and STILL_WORDS.search(x) and re.search(r"camera|shot|framing", x, re.I))]
    if held:
        must.insert(0, rec["drift"]["line"])
    return "\n".join(f"- {x}" for x in must)


def main(argv=None) -> int:
    a = list(argv if argv is not None else sys.argv[1:])
    if not a:
        print(__doc__)
        return 2
    run = Path(a[0])
    for gid in a[1:] or sorted(spans(run)):
        rec = read(run, gid)
        print(f"{gid}: " + "; ".join(f"{k} {len(rec[k])}" for k in FIELDS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
