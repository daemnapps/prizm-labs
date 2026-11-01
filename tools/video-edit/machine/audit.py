#!/usr/bin/env python3
"""audit.py — every word and every shot of a finished cut, before anyone watches it (the owner, 2026-10-20: "The word
'then' is getting cut off. That was just one thing I found instantly … check every single frame for lip and sound").

    python3 audit.py <edit run dir> [--render renders/control.mp4]           every edit-map*.json version (E14)
    python3 audit.py <edit run dir> --sheet <cutsheet.json> --render <mp4>   a cut sheet (the kit route, E15)

The checks, each on EVERY item, never a sample:
  WORD CUT        a spoken word whose start or end falls outside the stretch of the clip the cut plays (a jump cut,
                  a trim or a clip edge landing inside the word) — the word is chopped
  LIPS STILL      a word heard from a clip while the shot on screen shows that person's mouth not moving
  WRONG SHOT      a word heard from a clip while a different shot of the person, mouth in frame, is on screen
  SYNC            every talking shot of 0.5 s or more measured against its source clip, frame by frame
                  (syncheck.picture_lag); more than 1.5 clip frames off
  WORDS ON FACE   a caption on a face or a mouth, read off EVERY FINISHED FRAME while the line is up (V13, E8: "you
  WORDS ON MOUTH  need awareness of the subject to ensure their mouths are never covered"; every frame since 10-21
                  row 9) — macOS Vision on the very frames a viewer sees, against where the caption sits
  WORDS ON WORDS  a caption over the headline or a badge already on screen (the edit map's words)
  JOIN CLICK      the finished sound jumps at a cut — a click where two pieces meet (E33, 2026-10-21: "choppy")
  MUFFLED         a talking take's voice in the finished file has lost its clarity against its own source clip — the
                  share of its sound above 3 kHz down by more than MUFFLE_DB (E33: "muffled")
  NO MUSIC        the swipe (or the brief) has music and the cut has none (V14, E26)
  NO SOUND FX     the swipe (or the brief) has sound effects and the cut lays none (V14, E26)
Writes <run>/audit[-<version>].json and prints one line per finding; exits 1 when anything is found. line.py runs it
after the render on every version and stops the line on a finding; run.py and v2.py hold a version with one (E13).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_map as RM  # noqa: E402
from mouths import moving, at  # noqa: E402
from edit_map import MOUTH_TOP  # noqa: E402

EDGE = 0.04          # a word may touch the cut edge by this much (its own breath) and still be whole
STILL = 0.03         # mouth movement below this while the word is said reads as lips not moving
SLIP_FRAMES = 1.5


def _call_dir(vm):
    """clips/calls/<call>/ — a run made before 2026-10-26 keeps clips/omni/<call>/ on disk."""
    c = Path(vm) / "clips"
    return c / "calls" if ((c / "calls").exists() or not (c / "omni").exists()) else c / "omni"


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def words_of(vm: Path, clip: str) -> list[dict]:
    w = _read(_call_dir(vm) / clip / "transcript-words.json", [])
    w = w.get("words", w) if isinstance(w, dict) else w
    return [x for x in w or [] if x.get("type", "word") == "word"]


def tracks_of(out: Path, clip: str) -> list[dict]:
    t = _read(out / "tracks" / f"{clip}.json", [])
    return t if isinstance(t, list) else (t or {}).get("rows", [])


def audit(out: Path, mp4: Path | None = None, map_file: str = "edit-map.json", final: Path | None = None) -> dict:
    """One edit-map version. `mp4` is the render the lips are measured on (renders/<v>.clean.mp4 — no words over the
    picture), `final` the finished file the words are checked on (renders/<v>.mp4, with its <v>.sheet.json beside it)."""
    m = _read(out / map_file)
    vm = Path(m["from_run"])
    jn0 = _read(final.with_suffix(".sheet.json"), {}) if final is not None else {}
    if (jn0 or {}).get("joined"):
        # a hook version joined onto the control (E35): only its own opening was made for it — the body is the control's
        # frames and sound, audited with the control — so only what starts before the join is checked here
        import render_map as _RM
        m = _RM._head_of(m, float(jn0["head_s"]))
    segs = RM.flatten(m)
    mutes = [(p["mute_a"], p["mute_b"]) for p in m.get("patches") or []]
    found = []
    for l in sorted(m["voice"], key=lambda x: x["a"]):
        if l["kind"] != "in clip":
            continue
        lo, hi = l["in"], l["in"] + l["len"]
        for w in words_of(vm, l["clip"]):
            if w["end"] <= lo or w["start"] >= hi:
                continue                                   # not part of this stretch
            t0 = l["a"] + (w["start"] - lo)
            if any(a <= t0 < b for a, b in mutes):
                continue                                   # replaced by a word fix
            if w["start"] < lo - EDGE or w["end"] > hi + EDGE:
                found.append({"check": "WORD CUT", "at": round(max(l["a"], t0), 2), "clip": l["clip"],
                              "word": w["text"], "word_s": [w["start"], w["end"]], "plays": [round(lo, 2), round(hi, 2)]})
            # the shot on screen while the word is said
            t = l["a"] + ((w["start"] + w["end"]) / 2 - lo)
            s = next((x for x in segs if x["a"] <= t < x["b"]), None)
            if not s or not s.get("clip") or s["kind"] not in ("clip", "insert"):
                continue
            src_t = s.get("in", 0) + (t - s["a"]) * float(s.get("speed") or 1)
            tr = tracks_of(out, s["clip"])
            r = at(tr, round(src_t, 1))
            if not r:
                continue
            x0, y0, x1, y1 = RM.crop_box(s)
            mouth_in = (r["y"] + r["h"] > y0 + 0.01 and r["y"] + MOUTH_TOP * r["h"] < y1 - 0.01
                        and x0 < r["x"] + r["w"] / 2 < x1)
            if not mouth_in:
                continue
            if s["clip"] != l["clip"]:
                found.append({"check": "WRONG SHOT", "at": round(t, 2), "clip": l["clip"], "word": w["text"],
                              "on_screen": s["clip"]})
                continue
            mv = moving(tr, src_t)
            if mv is not None and mv < STILL:
                found.append({"check": "LIPS STILL", "at": round(t, 2), "clip": l["clip"], "word": w["text"],
                              "move": round(mv, 3)})
    # SYNC, part 1 — THE PLAN: on every talking shot, the clip moment on screen against the clip moment heard. A shot
    # whose picture is set off its own voice (a nudge, a lead-in) shows lips out of time however well it renders.
    for s in segs:
        if s["kind"] != "clip" or not s.get("lip"):
            continue
        l = next((v for v in m["voice"] if v.get("clip") == s["clip"] and v["kind"] == "in clip"
                  and v["a"] <= s["a"] + 0.05 < v["b"]), None)
        if not l:
            continue
        cf = RM.src_fps(vm / "clips" / f"{s['clip']}.mp4")
        off = (s.get("in", 0) - (l["in"] + (s["a"] - l["a"]))) * cf
        if abs(off) > 1.0:
            found.append({"check": "SYNC PLAN", "at": round(s["a"], 2), "clip": s["clip"], "frames": round(off, 2),
                          "why": "the picture is set off its own voice"})
    # SYNC, part 2 — THE RENDER: every talking shot found in its source frame by frame, a reading every 0.15 s; a
    # 24 fps clip in a 30 fps cut reads on whole clip frames, so the MEAN is the slip, held at 1.5 clip frames
    if mp4 is not None and mp4.is_file():
        import syncheck as SC
        for s in segs:
            if s["kind"] != "clip" or not s.get("lip") or s["b"] - s["a"] < 0.5:
                continue
            src = vm / "clips" / f"{s['clip']}.mp4"
            cf = RM.src_fps(src)
            sp = float(s.get("speed") or 1)
            n = max(1, int((s["b"] - s["a"] - 0.35) / 0.15) + 1)
            looks = [SC.picture_lag(mp4, s["a"] + 0.05 + k * 0.15, src, s["in"] + (0.05 + k * 0.15) * sp,
                                    RM.crop_filter(s), seconds=0.3, fps=cf) for k in range(n)]
            looks = [x for x in looks if x is not None]
            if looks:
                lg = sum(looks) / len(looks)
                if abs(lg * cf) > SLIP_FRAMES:
                    found.append({"check": "SYNC", "at": round(s["a"], 2), "clip": s["clip"],
                                  "frames": round(lg * cf, 2), "looks": len(looks)})
    sheet = _read(final.with_suffix(".sheet.json")) if final is not None else None
    joined = bool(sheet and sheet.get("joined"))      # a hook version joined onto the control (E35): its own words are
    if joined:                                        # the opening's; the body is the control's frames, audited there
        sheet = _read(final.parent / sheet["head_sheet"])
    if final is not None and final.is_file() and sheet:
        found += words_off_faces(sheet, final, float(jn0["head_s"]) if (jn0 or {}).get("joined") else None)
    if final is not None and final.is_file():
        jn = _read(final.with_suffix(".sheet.json"), {}) or {}
        found += join_clicks(final, [x["a"] for x in segs] + [l["a"] for l in m["voice"] + m.get("sounds", [])]
                             + ([float(jn["head_s"])] if jn.get("joined") else []))
        found += clarity(final, [(l["a"], vm / "clips" / f"{l['clip']}.mp4", float(l["in"]), float(l["len"]), l["clip"])
                                 for l in m["voice"] if l.get("kind") == "in clip"])
    found += sound_called_for(m.get("music") or {}, m.get("sfx") or [], [], bool((m.get("music") or {}).get("made")))
    name = "control" if map_file == "edit-map.json" else map_file[len("edit-map-"):-5]
    rec = {"version": name, "found": found,
           "checked": {"words": True, "lips": True, "sync": bool(mp4), "faces": bool(final is not None and sheet), "sound": True,
                       "joins": bool(final is not None and final.is_file()), "clarity": bool(final is not None and final.is_file())}}
    (out / ("audit.json" if name == "control" else f"audit-{name}.json")).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


# ---------------------------------------------------------------- the finished frame: no words on a face or a mouth
FACE_TOL = 0.02     # share of the caption's box a face may graze (an ear at the edge) before it reads as covered


def caption_boxes(sheet: dict) -> list[dict]:
    """Every caption line as compose puts it on screen: its time and its box (% of the frame), the words' own width."""
    import compose as C
    import placement as P
    caps = sheet.get("captions") or {}
    if not caps.get("words"):
        return []
    L = C.look_of(sheet)
    quiet = [(c["start"], c["start"] + c["duration"]) for c in sheet.get("picture") or [] if c.get("kind") in C.TEXT_KINDS]
    quiet += [(o["start"], o["start"] + o["duration"]) for o in sheet.get("overlays") or [] if o.get("kind") == "hook"]
    zones = caps.get("zones") or {}
    out = []
    for ln in C.caption_lines(caps["words"], L.get("max_words", 4)):
        a, b = ln[0]["start"], ln[-1]["end"]
        mid = (a + b) / 2
        if any(x <= mid < y for x, y in quiet):
            continue
        on = sorted([c for c in sheet.get("picture") or [] if c["start"] <= mid < c["start"] + c["duration"]],
                    key=lambda c: 0 if c.get("roll") == "b" else 1)
        sc = (on[0].get("scene") or on[0]["id"]) if on else None
        zz = zones.get(sc) or {}
        bx = zz.get("box") or P.zones()[zz.get("zone") or L.get("zone") or "caption-band"]
        text = " ".join(w["text"] for w in ln)
        width = min(float(bx["w"]), len(text) * float(L.get("size_px", 60)) * 0.55 / 1080 * 100 + 4)
        x0 = float(bx["x"]) + (float(bx["w"]) - width) / 2
        out.append({"a": a, "b": b, "text": text, "box": (x0, float(bx["y"]), x0 + width, float(bx["y"]) + float(bx["h"]))})
    return out


def _cover(c: tuple, b: tuple) -> float:
    w = min(c[2], b[2]) - max(c[0], b[0]); h = min(c[3], b[3]) - max(c[1], b[1])
    return 0.0 if w <= 0 or h <= 0 else w * h / ((c[2] - c[0]) * (c[3] - c[1]))


def words_off_faces(sheet: dict, final: Path, until: float | None = None, fps: float | None = None) -> list[dict]:
    """Each caption line read on EVERY finished frame it is on screen (verify 2026-10-21 row 9 — it used to read one
    frame, the line's middle, so a face that moved under the words later in the line went unseen): a face (brows to
    chin) or a mouth under the words. One finding per line, at the first frame it happens, with how many frames.
    `until`: a joined hook version's opening ends there — after it the frames are the control's, checked with it."""
    import subprocess
    import tempfile
    import thumbs as TH
    found = []
    boxes = [c for c in caption_boxes(sheet) if until is None or (c["a"] + c["b"]) / 2 < until]
    for c in boxes:              # two sets of words on top of each other (a caption under the headline)
        mid = (c["a"] + c["b"]) / 2
        for k in sheet.get("keep_clear") or []:
            if k.get("what") not in (None, "item") and k["start"] <= mid < k["end"] and _cover(c["box"], tuple(k["box"])) > 0.15:
                found.append({"check": "WORDS ON WORDS", "at": round(mid, 2), "words": c["text"], "under": k.get("what")})
    fps = float(fps or (sheet.get("meta") or {}).get("fps") or RM.FPS)
    pct = lambda b: (b["x"] * 100, b["y"] * 100, (b["x"] + b["w"]) * 100, (b["y"] + b["h"]) * 100)  # noqa: E731
    with tempfile.TemporaryDirectory() as td:
        for i, c in enumerate(boxes):
            d = Path(td) / f"c{i}"
            d.mkdir()
            n0, n1 = int(round(c["a"] * fps)), max(int(round(c["a"] * fps)) + 1, int(round(c["b"] * fps)))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{n0 / fps:.3f}", "-i", str(final), "-frames:v", str(n1 - n0),
                            "-vf", "scale=540:-2", str(d / "f%05d.jpg")], capture_output=True)
            frames = sorted(d.glob("f*.jpg"))
            if not frames:
                continue
            try:
                reads = TH.scenes(frames)
            except Exception:  # noqa: BLE001 — no Vision here: said so, never a silent pass
                return found + [{"check": "FACES NOT READ", "at": round(c["a"], 2),
                                 "why": "macOS Vision is not on this machine — words on faces unchecked"}]
            mouth, face = [], []
            for k, sc in enumerate(reads):
                t = round((n0 + k) / fps, 3)
                if any(_cover(c["box"], pct(b)) > 0 for b in sc.get("lips") or []):
                    mouth.append(t)
                elif any(_cover(c["box"], pct(b)) > FACE_TOL for b in sc.get("faces") or []):
                    face.append(t)
            box = [round(v, 1) for v in c["box"]]
            if mouth:
                found.append({"check": "WORDS ON MOUTH", "at": mouth[0], "words": c["text"], "box": box,
                              "frames": len(mouth), "of": len(frames)})
            elif face:
                found.append({"check": "WORDS ON FACE", "at": face[0], "words": c["text"], "box": box,
                              "frames": len(face), "of": len(frames)})
    return found


# ---------------------------------------------------------------- the sound itself: clicks at the joins, clarity (E33)
CLICK_JUMP = 0.12   # a sample-to-sample jump (full scale = 1) at a cut this big, and CLICK_RATIO × the sound around it
CLICK_RATIO = 4.0
MUFFLE_DB = 6.0     # the voice's share above 3 kHz may fall this far below its source's before it reads as muffled


def _pcm(path: Path, t0: float, dur: float, rate: int = 48000) -> list[float]:
    import array
    import subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t0):.4f}", "-t", f"{dur:.4f}", "-i", str(path), "-vn",
                          "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"], capture_output=True).stdout
    a = array.array("h"); a.frombytes(raw[: len(raw) // 2 * 2])
    return [x / 32768.0 for x in a]


def join_clicks(final: Path, cuts: list[float]) -> list[dict]:
    """Every cut in the finished sound: the biggest sample jump within 3 ms of it, against the sound around it."""
    found = []
    for t in sorted({round(c, 3) for c in cuts if c > 0.05}):
        x = _pcm(final, t - 0.02, 0.04)
        if len(x) < 100:
            continue
        d = [abs(b - a) for a, b in zip(x, x[1:])]
        mid, k = len(d) // 2, int(0.003 * 48000)
        at = max(d[max(0, mid - k): mid + k] or [0])
        rest = sorted(d[: max(0, mid - k)] + d[mid + k:])
        base = rest[int(len(rest) * 0.95)] if rest else 0.0
        if at > CLICK_JUMP and at > CLICK_RATIO * max(base, 1e-4):
            found.append({"check": "JOIN CLICK", "at": t, "jump": round(at, 3), "around": round(base, 3)})
    return found


def _bright(path: Path, t0: float, dur: float) -> float | None:
    """dB of the sound above 3 kHz, relative to the whole — how clear (not muffled) a stretch of voice is."""
    import re as _re
    import subprocess

    def mean(af):
        e = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{max(0.0, t0):.3f}", "-t", f"{dur:.3f}", "-i", str(path), "-vn",
                            "-af", af, "-f", "null", "-"], capture_output=True, text=True).stderr
        m = _re.findall(r"mean_volume:\s*(-?[\d.]+) dB", e)
        return float(m[-1]) if m else None
    full, hi = mean("volumedetect"), mean("highpass=f=3000:poles=2,volumedetect")
    return None if full is None or hi is None or full < -60 else hi - full


def clarity(final: Path, pieces: list[tuple]) -> list[dict]:
    """(at on the cut, source file, source second, seconds, name) per talking piece: its voice in the finished file
    against its own clip. Lost brightness = muffled (a lip-fit, a re-encode, a filter)."""
    found = []
    for at, src, s0, dur, name in pieces:
        dur = min(float(dur), 1.5)
        if dur < 0.6 or not Path(src).is_file() or not final.is_file():
            continue
        a, b = _bright(final, at + 0.1, dur - 0.2), _bright(Path(src), s0 + 0.1, dur - 0.2)
        if a is not None and b is not None and b - a > MUFFLE_DB:
            found.append({"check": "MUFFLED", "at": round(at, 2), "clip": name, "lost_db": round(b - a, 1)})
    return found


# ---------------------------------------------------------------- the sound the swipe has
def sound_called_for(music: dict, cues: list, sfx_laid: list, music_laid: bool, wanted: dict | None = None) -> list[dict]:
    """The swipe or the brief has music / sound effects and the cut has none: a finding, never a note (V14, E26)."""
    found = []
    w = wanted or {}
    has_music = bool(str(music.get("what") or "").strip() and str(music.get("what")).strip().lower() not in ("none", "no music")) \
        or bool(str(w.get("music") or "").strip() and str(w.get("music")).strip().lower() != "none")
    if has_music and not music_laid:
        found.append({"check": "NO MUSIC", "at": 0.0, "why": f"the swipe/brief has music ({music.get('what') or w.get('music')}) and the cut has none"})
    named = [x for x in cues or [] if str(x.get("what") or x.get("cue") or "").strip()]
    has_fx = bool(named) or bool(str(w.get("effects") or "").strip() and str(w.get("effects")).strip().lower() != "none")
    made = [x for x in cues or [] if x.get("made")] + list(sfx_laid or [])
    if has_fx and not made:
        found.append({"check": "NO SOUND FX", "at": 0.0, "why": f"the swipe/brief has {len(named) or 'its'} sound effect(s) and the cut lays none"})
    return found


# ---------------------------------------------------------------- a cut sheet (the kit route) — E15
def audit_sheet(sheet: dict, root: Path, final: Path, kit: dict | None = None) -> dict:
    """The same audit on a cut sheet: words chopped at a piece's edge, each talking piece's lips against its own
    clip, words off every face and mouth on the finished frames, the sound the swipe has."""
    import syncheck as SC
    found = []
    words = (sheet.get("captions") or {}).get("words") or []
    pics = sorted([c for c in sheet.get("picture") or [] if c.get("talks")], key=lambda c: c["start"])
    for x, y in zip(pics, pics[1:] + [None]):
        end = x["start"] + x["duration"]
        joined = y is not None and y.get("src") == x.get("src") and abs(y["start"] - end) < 0.02 \
            and abs(float(y.get("source_start", 0)) - (float(x.get("source_start", 0)) + x["duration"])) < 0.02
        if joined:
            continue                                   # the same take carries straight on: no edge here
        for w in words:
            if w["start"] + EDGE < end < w["end"] - EDGE:
                found.append({"check": "WORD CUT", "at": round(end, 2), "clip": x["id"], "word": w["text"],
                              "word_s": [w["start"], w["end"]]})
    for c in pics:
        if c["duration"] < 0.5 or not Path(str(c.get("src"))).is_file() or not final.is_file():
            continue
        lg = SC.lag(final, c["start"], Path(c["src"]), float(c.get("source_start", 0)), min(c["duration"], 4.0))
        if lg is not None and abs(lg) > 0.045:
            found.append({"check": "SYNC", "at": round(c["start"], 2), "clip": c["id"], "ms": round(lg * 1000)})
    if final.is_file():
        found += words_off_faces(sheet, final)
        cuts = [c["start"] for c in sheet.get("picture") or []] + [v["start"] for v in sheet.get("voice_cuts") or []]
        found += join_clicks(final, cuts)
        found += clarity(final, [(c["start"], c["src"], float(c.get("source_start", 0)), c["duration"], c["id"]) for c in pics])
    k = kit or {}
    found += sound_called_for({}, [], sheet.get("sfx") or [], bool(sheet.get("music")), k.get("wanted"))
    return {"found": found, "checked": {"words": True, "sync": final.is_file(), "faces": final.is_file(), "sound": True,
                                        "joins": final.is_file(), "clarity": final.is_file()}}


def versions(out: Path) -> dict:
    """{version: map file} — the control and every hook version (E14: every version, never the control alone)."""
    v = {"control": "edit-map.json"} if (out / "edit-map.json").exists() else {}
    for f in sorted(out.glob("edit-map-*.json")):
        v[f.stem[len("edit-map-"):]] = f.name
    return v


def show(name: str, rec: dict) -> None:
    for f in rec["found"]:
        print(f"{name:<8} {f['check']:<14} {f['at']:7.2f}s  {f.get('clip', '')}  " + json.dumps(
            {k: v for k, v in f.items() if k not in ('check', 'at', 'clip')}, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--render", help="one version's render (default: renders/<version>.clean.mp4 for each)")
    ap.add_argument("--only", help="versions to audit, comma-separated (default: every version)")
    ap.add_argument("--sheet", help="audit a cut sheet instead (the kit route): its json; --render is the finished file")
    a = ap.parse_args(argv)
    out = Path(a.run)
    if a.sheet:
        rec = audit_sheet(_read(Path(a.sheet)), out, Path(a.render or out / "work" / "final.mp4"))
        show("sheet", rec)
        print(f"audit: {len(rec['found'])} finding(s)")
        return 1 if rec["found"] else 0
    want = set(a.only.split(",")) if a.only else None
    total = 0
    for name, mf in versions(out).items():
        if want and name not in want:
            continue
        r = out / "renders"
        clean = Path(a.render) if a.render else (r / f"{name}.clean.mp4" if (r / f"{name}.clean.mp4").exists() else r / f"{name}.mp4")
        rec = audit(out, out / clean if not clean.is_absolute() else clean, mf, r / f"{name}.mp4")
        show(name, rec)
        total += len(rec["found"])
    print(f"audit: {total} finding(s)")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
