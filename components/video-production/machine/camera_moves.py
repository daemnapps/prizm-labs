"""Camera moves: punch-ins timed to the words, cut into a finished take with no regeneration.

A move is a lens zoom toward a point in the frame while a word is said, then back out:
    {"on": "45,", "nth": 1, "until": "and", "to": [0.31, 0.66], "zoom": 1.6}
`on` / `until` are words from the take's own transcript (transcript-words.json), `nth` picks
which time the word is said (1 = first); `from` / `to_t` in seconds may be given instead.
`to` is the point to push toward, as a share of the frame's width and height. The moves for a
run live in its `camera-moves.json`, one list per scene id; the chain writes them from the
brief's gestures, never by hand in the edit.

    python3 camera_moves.py <run dir> <scene id> [take]     # writes clips/calls/<call>/moves/<take>.mp4
"""
import json
import re
import math
import subprocess
import sys
from pathlib import Path

LEAD = 0.55       # the glide starts this long before the word, so it settles as the word lands
MERGE = 1.2       # two moves closer than this never pull out between them: the camera pans across
GLIDE = 6.5       # spring stiffness (1/s); lower = slower, softer glide. Two springs in a row, so it eases in AND out
DRIFT = 0.03      # the camera never stops dead at rest: a slow breath in and back out over the take, full frame at both ends
SETTLE = 1.3      # seconds the camera needs to be back on the full frame before the cut
CREEP = 0.05      # during a hold the lens keeps pushing in this much more
REST = (0.5, 0.5)   # the full frame: where every scene starts and ends


def _words(path):
    return [w for w in json.loads(Path(path).read_text()) if w.get("type", "word") == "word" and w.get("text", "").strip()]


def _norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _find(words, text, nth=1, after=0.0):
    hits = [w for w in words if _norm(w["text"]) == _norm(text) and w["start"] >= after]
    if len(hits) < nth:
        raise SystemExit(f"camera move: the word {text!r} (time {nth}) is not in the take")
    return hits[nth - 1]


def timed(moves, words, length):
    """Each move with its start and end in seconds, from its words."""
    out = []
    for m in moves:
        if "from" in m:
            a, b = float(m["from"]), float(m["to_t"])
        else:
            w = _find(words, m["on"], m.get("nth", 1))
            a = w["start"] - LEAD
            b = _find(words, m["until"], 1, w["end"])["start"] if m.get("until") else w["end"] + 0.4
        out.append({"a": max(0.0, a), "b": min(length, b), "x": m["to"][0], "y": m["to"][1], "z": float(m.get("zoom", 1.5))})
    out.sort(key=lambda m: m["a"])
    for p, n in zip(out, out[1:]):      # close gaps: glide straight from one point to the next
        if n["a"] - p["b"] < MERGE:
            p["b"] = n["a"]
    # EVERY SCENE IS A LOOP (2026-10-28): it starts and ends on the full frame, so the next scene starts from the
    # same place; the last move lets go in time for the pull-out to settle before the cut
    for m in out:
        m["b"] = min(m["b"], length - SETTLE)
        m["a"] = min(m["a"], m["b"])
    return [m for m in out if m["b"] - m["a"] > 0.2]


AIM_Y = 0.33      # a pushed-in point in the upper half (a face) sits this high, above the caption band
AIM_LOW = 0.62    # a pushed-in point in the lower half (hands, a counter) sits this low, so the face stays in frame


def _box(z, cx, cy):
    """A framing (log zoom, left, top) as shares of the frame, kept inside the picture. The point pushed toward lands at
    AIM_Y of the frame's height, never in the caption band (2026-10-28: a centred push put her face under the captions)."""
    s = 1.0 / z
    aim = AIM_Y if cy <= 0.55 else AIM_LOW                  # a face stays above the captions; hands keep the face in frame
    return (math.log(z), min(max(cx - s / 2, 0.0), 1 - s), min(max(cy - s * aim, 0.0), 1 - s))


def _aim(timed_moves, t, length):
    for m in timed_moves:
        if m["a"] <= t <= m["b"]:   # while it holds, it keeps creeping in, so it never sits parked
            return _box(m["z"] * (1 + CREEP * (t - m["a"]) / max(m["b"] - m["a"], 0.1)), m["x"], m["y"])
    return _box(1 + DRIFT * math.sin(math.pi * min(max(t / max(length, 0.1), 0.0), 1.0)), *REST)


def path(timed_moves, length, fps, frames):
    """One framing per frame. The aim jumps between framings; the camera follows it through two
    critically damped springs in a row, so every move starts slowly, glides, and settles with no jolt."""
    sub = 8
    dt = 1.0 / fps / sub
    k = GLIDE
    a = list(_aim(timed_moves, 0.0, length))
    b, va, vb = a[:], [0.0] * 3, [0.0] * 3
    out = []
    for n in range(frames):
        for s in range(sub):
            t = (n * sub + s) * dt
            g = _aim(timed_moves, t, length)
            for i in range(3):
                va[i] += (k * k * (g[i] - a[i]) - 2 * k * va[i]) * dt
                a[i] += va[i] * dt
                vb[i] += (k * k * (a[i] - b[i]) - 2 * k * vb[i]) * dt
                b[i] += vb[i] * dt
        out.append(tuple(b))
    # the last frames land exactly on the full frame, eased, so the next scene starts where this one ends
    tail = max(1, int(0.4 * fps))
    for i in range(max(0, frames - tail), frames):
        e = (i - (frames - tail) + 1) / tail
        e = e * e * (3 - 2 * e)
        out[i] = tuple(v * (1 - e) for v in out[i])
    return out


def window(frame, w, h):
    """The crop box (left, top, right, bottom) in pixels for one framing."""
    s = 1.0 / math.exp(frame[0])
    x = min(max(frame[1], 0.0), 1 - s) * w
    y = min(max(frame[2], 0.0), 1 - s) * h
    return (x, y, x + s * w, y + s * h)


def _probe(clip):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(clip)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    return s["width"], s["height"], float(j["format"]["duration"]), s["r_frame_rate"]


def apply(clip, words_file, moves, out):
    from PIL import Image
    w, h, length, fps = _probe(clip)
    tm = timed(moves, _words(words_file), length)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(clip), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                            "-r", fps, "-i", "-", "-i", str(clip), "-map", "0:v", "-map", "1:a?",
                            "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p",
                            "-c:a", "copy", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    num, den = (fps.split("/") + ["1"])[:2]
    rate, n, size = float(num) / float(den), 0, w * h * 3
    frames = path(tm, length, rate, int(length * rate) + 2)
    while True:
        buf = dec.stdout.read(size)
        if len(buf) < size:
            break
        im = Image.frombytes("RGB", (w, h), buf)
        im = im.resize((w, h), Image.LANCZOS, box=window(frames[min(n, len(frames) - 1)], w, h))
        enc.stdin.write(im.tobytes())
        n += 1
    enc.stdin.close()
    if enc.wait() or dec.wait():
        raise SystemExit("camera move: ffmpeg failed")
    Path(out).with_name(Path(out).stem + "-moves.json").write_text(json.dumps({"from": str(Path(clip).name), "moves": tm}, indent=1))
    return out


def for_scene(run, gid, take=None):
    """Apply the run's moves for one scene to its chosen take (default: the newest take that passed)."""
    run = Path(run)
    moves = json.loads((run / "camera-moves.json").read_text()).get(gid)
    if not moves:
        raise SystemExit(f"no camera moves for {gid} in camera-moves.json")
    led = json.loads((run / "clips" / "ledger.json").read_text()) if (run / "clips" / "ledger.json").is_file() else {}
    takes = sorted((run / "clips" / "calls").glob(f"{gid}-*/takes/*.mp4"), key=lambda f: -f.stat().st_mtime)
    if take:
        takes = [t for t in takes if t.stem == take]
    else:
        takes = [t for t in takes if ((led.get(t.stem) or {}).get("qc") or {}).get("ok")] or takes
    if not takes:
        raise SystemExit(f"no take for {gid}")
    t = takes[0]
    words = t.parent.parent.parent / t.stem / "transcript-words.json"
    return apply(t, words, moves, t.parent.parent / "moves" / f"{t.stem}.mp4")


PLAN_ASK = """You are a camera operator planning punch-ins for one continuous talking take. The picture is the take's first
frame. Below are the beats, in order: what the person does, and the words it happens over.

Pick the beats where the viewer should SEE a detail up close: a hand touching, pointing at, tapping, pouring, scooping,
spreading or holding up something, or a product shown to the lens. Never a beat that is only a look, a nod, a breath,
a hold or a smile. At most one push-in per {per} seconds of take; leave the rest on the full frame.

For each beat you pick, say where the detail is in THIS picture (where the hand will be, on the object it works on),
as a share of the picture's width (x, 0 left to 1 right) and height (y, 0 top to 1 bottom), and how far to push in
(zoom 1.3 to 1.6; 1.45 is normal).

Beats:
{beats}

Answer as JSON: {{"moves": [{{"beat": <number>, "x": <0-1>, "y": <0-1>, "zoom": <1.3-1.6>, "why": "<a few words>"}}]}}"""


def _first_word(over):
    w = re.findall(r"[A-Za-z0-9']+", str(over or ""))
    return w[0] if w else ""


def plan_scene(run, gid, seconds=10.0, ask=None):
    """The camera moves for one section, planned by the chain from the brief: its scenes' beats (`do` over `over`),
    a cheap vision read of the section's start picture for which beats to push in on and where. A move runs from its
    beat's first word to the next beat's first word. Returns the moves (not written)."""
    run = Path(run)
    sb = json.loads((run / "storyboard.json").read_text())
    scenes = {s["id"]: s for s in json.loads((run / "plan.json").read_text()).get("scenes") or []}
    sec = next(g for g in sb["sections"] if g["id"] == gid)
    beats = [b for sid in sec.get("scenes") or [] for b in (scenes.get(sid) or {}).get("beats") or []
             if isinstance(b, dict) and b.get("do")]
    spoken = [b for b in beats if re.search(r"[A-Za-z0-9]", str(b.get("over") or "")) and not
              re.search(r"(?i)^(the )?(stop|breath|pause)|no words", str(b.get("over") or "").strip())]
    if not spoken:
        return []
    pic = run / "media" / f"{sec['scenes'][0]}-F1.png"
    listing = "\n".join(f"{i + 1}. {b['do']}  — over: \"{b['over']}\"" for i, b in enumerate(spoken))
    if ask is None:
        import importlib.util as _u
        sp = _u.spec_from_file_location("cm_v2checks", Path(__file__).resolve().parent / "v2_checks.py")
        vc = _u.module_from_spec(sp)
        sp.loader.exec_module(vc)
        ask = lambda prompt, images: vc.ask(run, "camera-moves", prompt, images)[0]
    got = json.loads(ask(PLAN_ASK.format(per=3, beats=listing), [pic]) or "{}")
    out, count = [], {}
    for m in got.get("moves") or []:
        i = int(m.get("beat", 0)) - 1
        if not 0 <= i < len(spoken):
            continue
        on = _first_word(spoken[i]["over"])
        nxt = _first_word(spoken[i + 1]["over"]) if i + 1 < len(spoken) else ""
        count[on.lower()] = count.get(on.lower(), 0) + 1
        out.append({"on": on, "nth": 1, "until": nxt or None, "to": [round(float(m["x"]), 3), round(float(m["y"]), 3)],
                    "zoom": round(min(max(float(m.get("zoom", 1.45)), 1.3), 1.6), 2), "why": m.get("why") or spoken[i]["do"],
                    "beat": spoken[i]["do"]})
    return out


def plan_run(run, overwrite=False):
    """Write every lip-sync section's moves into the run's camera-moves.json (a section already there is kept)."""
    run = Path(run)
    f = run / "camera-moves.json"
    have = json.loads(f.read_text()) if f.is_file() else {}
    sb = json.loads((run / "storyboard.json").read_text())
    for g in sb["sections"]:
        if g.get("maker") != "lip-sync" or (g["id"] in have and not overwrite):
            continue
        have[g["id"]] = plan_scene(run, g["id"], g.get("seconds") or 10)
    f.write_text(json.dumps(have, indent=1, ensure_ascii=False))
    return have


def on_kept(run, call_id):
    """The camera moves cut into a call's KEPT clip (clips/<call>.mp4), the one the edit takes: the section's moves whose
    words this call says, timed on the kept take's own words. The clip as kept stays beside it as <call>-nomoves.mp4.
    Run once per keep; a call with no moves of its own is left alone."""
    run = Path(run)
    gid = call_id.split("-")[0]
    moves = (json.loads((run / "camera-moves.json").read_text()) if (run / "camera-moves.json").is_file() else {}).get(gid) or []
    final = run / "clips" / f"{call_id}.mp4"
    plain = final.with_name(f"{call_id}-nomoves.mp4")
    words_f = run / "clips" / "calls" / call_id / "transcript-words.json"
    if not moves or not final.is_file() or not words_f.is_file():
        return None
    if not plain.is_file():
        final.rename(plain)
    said = {_norm(w["text"]) for w in _words(words_f)}
    mine = [m for m in moves if "from" in m or (_norm(m["on"]) in said and (not m.get("until") or _norm(m["until"]) in said))]
    if not mine:
        plain.rename(final)
        return None
    return apply(plain, words_f, mine, final)


if __name__ == "__main__":
    if sys.argv[1:2] == ["kept"]:
        print(on_kept(sys.argv[2], sys.argv[3]))
    elif sys.argv[1:2] == ["plan"]:
        print(json.dumps(plan_run(sys.argv[2]), indent=1))
    else:
        print(for_scene(*sys.argv[1:4]))
