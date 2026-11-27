#!/usr/bin/env python3
"""The motion chain: the one way an AI clip gets its movement, every time, before any paid take. It runs on its own:
nobody approves anything. A scene's motion passes on the chain's own checks or is held with the reason.

    python3 motion_chain.py run <scene dir> [--take take.json] [--brand B] [--framemap framemap.json] [--source swipe.mp4]
                         [--span 0-15.08 ...] [--clip real.mp4] [--only find,track,read,rehearse,preview]
    python3 motion_chain.py decide <scene dir>                  passed, or held with the reasons (exit 1 when held)
    python3 motion_chain.py who <scene dir> A1=NAME B1=extra [--by <name>]   correct who is who; rehearses, previews and decides again
    python3 motion_chain.py frame-words <scene dir>                  the rehearsal's first frame in words, for the start picture's prompt
    python3 motion_chain.py print-words <scene dir>                  the 3D set print's words for the start picture (place, frame, cast)
    python3 motion_chain.py start-check <scene dir> [<picture>]      the start picture against the rehearsal's first frame
                                                                     (exit 1 when it fails: do not pay for a take from it)
    python3 motion_chain.py check <scene dir> [<clip>] [--name take]   a finished take set against the reference (✓/✗ rows)
    python3 motion_chain.py ours <scene dir> [--model opus]          the rehearsal programmed from our beats on the
                                                                     reference's timing and camera (run does this itself
                                                                     when the reference does not show our moves)
    python3 motion_chain.py approve <scene dir> --by <name>     an override, recorded: passes motion its checks held
    python3 motion_chain.py status <scene dir>                         every stage: done or not, and what it found
    python3 motion_chain.py rows <production dir>                      every scene's rows, in the Checks panel's shape

A scene is a folder holding take.json (what happens, who, why). Everything is written to <scene>/motion/.

Stages, in order (each one's result is kept as files and as a row in chain.json, so a board can show it):
  find       finder.py     real footage of the same action: own footage, then the swipe's seconds, then a web search
                           list (a web clip is downloaded only on a named yes). `--span` (seconds of `--source`) or
                           `--clip` names it outright; otherwise the finder's pick is used
  track      motion.py     the reference's skeletons (body, hands, face, and each body's own 3D pose) and its camera
  read       read.py       who is who, then the motion read: the moment as body mechanics per beat
  rehearse   retarget.py   3D stand-ins moved by the real skeletons, filmed by the real camera's path
  preview    here          reference | skeleton | 3D rehearsal side by side; the rehearsal measured against the
                           reference (match.py) and looked at (watch.py), all before a credit is spent
  ours       here          when the read says the reference does not show one of OUR beats' moves (`missing`), the rehearsal is programmed from our beats
                           instead (motion_program.py), on the reference's own beat timing and filmed by its tracked
                           camera: the reference gives the timing and the camera only, never a body move we did not
                           write. The reference's own rehearsal is kept in rehearsal-reference/
  decide     here          passed or held, from those checks alone (`decide`). Held motion gets one more read and
                           rehearsal on its own; if it is still held it stays held, with the reasons, and no take is made
  check      match.py      after a take: the take against the reference, beat by beat

For a take (take.py and gen_ref.py call this, and only this):
  for_take(take)           the take with its scene's motion once that motion has passed its own checks; a refusal with
                           the reason when the checks held it or it never went through them. The motion read's beats
                           ride along as `mechanics`. When the motion carries a tracked camera, the take's written shot
                           sizes are taken out and the camera is described only as the track measured it (written
                           sizes made models invent push-ins).
  ready(scene_dir)         for the moment a take is made: the motion decided, the start picture made from the
                           rehearsal's first frame and checked against it (made again when it does not match)
  prepare(scene_dir, ...)  run the stages for a scene from code; returns the status

A scene longer than one generation (15 s of motion) is split into parts at the reference's cuts and beat ends
(segments.json); a take names its part with `motion: {"scene": ..., "segment": k}` and gets that part's seconds of the
rehearsal, its beats and its camera, on the part's own clock. Each later part starts from the last frame of the take
before it.

The verbs (motion_program.py) stay as the fallback when no real footage of the action exists yet.
No brand, product or person is named here; the brand comes from the caller.
"""
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import home as ST  # noqa: E402
import measure as ME  # noqa: E402

STAGES = ("find", "track", "read", "rehearse", "preview")
NAMES = {"segments": "Long scene in parts", "watch": "Preview watched", "build": "Stand-ins built to the cast", "picture": "Start picture", "find": "Real reference found", "track": "Skeleton + camera tracked", "read": "Motion read",
         "rehearse": "3D rehearsal from the real skeleton", "camera": "Camera from the track", "preview": "Preview",
         "approve": "Motion checks"}


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _say(d, stage, ok, short, detail="", **more):
    """One stage's result into chain.json: what a board draws."""
    f = Path(d) / "chain.json"
    rec = _load(f, {"stages": {}})
    rec["stages"][stage] = dict({"name": NAMES.get(stage, stage), "ok": ok, "short": short, "detail": detail,
                                 "at": time.strftime("%Y-%m-%dT%H:%M:%S")}, **more)
    f.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec["stages"][stage]


BEAT_FIELDS = ("who", "action", "prop", "target", "where")


def _has(words, part):
    return str(part).lower().split("'")[0].strip() in str(words).lower()


def beat_action(ln):
    """One beat's action in words, built from its own fields when it has them (2026-11-15: who, action, prop, target
    and where are carried apart from the writing into the take, never as one sentence): "A lifts it to her
    eye, holding the lens, to B's jaw (first in the line)". A line written before the fields existed keeps its `do`."""
    if not ln.get("action"):
        return str(ln.get("do") or "").strip()
    act = str(ln["action"]).strip().rstrip(".")
    who = ln.get("who") or ln.get("speaker") or ""
    out = ("%s %s" % (who, act)).strip() if who and not act.startswith(who) else act
    if ln.get("prop") and not _has(act, ln["prop"]):
        out += ", holding the %s" % ln["prop"]
    if ln.get("target") and not _has(act, ln["target"]):
        out += ", to %s" % ln["target"]
    if ln.get("where"):
        out += " (%s)" % ln["where"]
    return out


def actions_of(take):
    """What the bodies do, as search phrases: every beat's action (its fields, else its `do`), else the staging."""
    out = [beat_action(ln) for ln in take.get("script") or [] if ln.get("action") or ln.get("do")]
    if not out:
        out = [beat_action(b) for b in take.get("beats") or [] if isinstance(b, dict) and (b.get("action") or b.get("do"))]
    return out or ([take["staging"]] if take.get("staging") else [])


TAIL = 0.07            # seconds trimmed off the end of every named span (a frame and a half of a 24 fps source)


def build_ref(d, spans, source, cuts=None):
    """The reference clip: the named seconds of the source, joined in order. Cuts are where spans meet, plus the
    source's own cuts inside them (from a frame map)."""
    d = Path(d)
    parts, at, joins, used = [], 0.0, [], []
    for k, (a, b) in enumerate(spans):
        p = d / ("ref-%d.mp4" % k)
        b = max(a + 0.2, b - TAIL)                 # a span's last frame is often the next shot's first: left out
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % a, "-t", "%.3f" % (b - a), "-i", str(source), "-an",
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24", str(p)], check=True)
        for c in cuts or []:
            if a + 0.05 < c < b - 0.05:
                joins.append(round(at + c - a, 3))
        parts.append(p)
        used.append({"from": a, "to": b, "at": round(at, 3)})
        at += b - a
        if k < len(spans) - 1:
            joins.append(round(at, 3))
    ref = d / "ref.mp4"
    if len(parts) == 1:
        shutil.move(str(parts[0]), str(ref))
    else:
        lst = d / "ref.txt"
        lst.write_text("".join("file '%s'\n" % p.name for p in parts))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(ref)], check=True, cwd=str(d))
        for p in parts:
            p.unlink()
        lst.unlink()
    rec = {"source": str(source), "spans": used, "cuts": sorted(joins), "seconds": round(at, 3)}
    (d / "ref.json").write_text(json.dumps(rec, indent=1))
    return rec


def framemap_cuts(framemap):
    fm = _load(framemap) or {}
    return [float(c) for c in fm.get("cuts") or []]


def prepare(scene_dir, take=None, brand=None, framemap=None, source=None, spans=None, clip=None, only=None, kind=None,
            watch=True, retry=True, camera_only=False):
    """Run the stages for one scene, then decide: the motion passes on its own checks or is held with the reasons
    (`decide`); held motion gets one more read and rehearsal on its own before it stays held. `watch`: also have the
    preview looked at (watch.py). `camera_only`: nobody is in the shot, so the tracked camera is the whole motion.
    Returns chain.json's stages."""
    import finder as FI
    import motion as MO
    scene_dir = Path(scene_dir)
    d = scene_dir / "motion"
    d.mkdir(parents=True, exist_ok=True)
    take = take or _load(scene_dir / "take.json") or {}
    only = [s for s in STAGES if not only or s in only]
    cuts = framemap_cuts(framemap) if framemap else []
    if "find" in only:
        acts = actions_of(take)
        had = _load(d / "ref.json") or {}                          # a reference already named and tracked for this scene
        named_spans = spans or [(x["from"], x["to"]) for x in had.get("spans") or []] or None
        cand = FI.find(scene_dir, acts, brand, framemap, source, also_web=(_load(d / "motion-read.json") or {}).get("missing"),
                       used=named_spans) if acts else {"candidates": [], "pick": None}
        named = bool(spans or clip)
        pick = next((c for c in cand["candidates"] if c["n"] == cand.get("pick")), None)
        if not named and pick and pick["from_where"] == "swipe":
            spans, source = [(float(pick["from"]), float(pick["to"]))], pick["source"]
        got = sum(1 for c in cand["candidates"] if not c["needs_download"])
        wait = len(cand.get("waiting_for_yes") or [])
        short = ("a clip given" if clip else "the swipe's own seconds" if (spans or had.get("spans")) else
                 "our own footage" if pick and pick["from_where"] == "own" else "a clip given" if had.get("source") else "nothing found")
        _say(d, "find", bool(named or pick or had.get("source")), short,
             "%d found in what we have (own footage first, then the swipe); %d web results wait for a yes before any download.%s" % (
                 got, wait, (" Web list because: " + cand["why_web"]) if cand.get("why_web") else ""),
             candidates=len(cand["candidates"]), waiting=wait, file="candidates.json")
    if "track" in only:
        if clip:
            shutil.copyfile(str(clip), str(d / "ref.mp4"))
            ref = {"source": str(clip), "spans": [], "cuts": [], "seconds": MO.seconds_of(clip)}
            (d / "ref.json").write_text(json.dumps(ref, indent=1))
        elif spans and source:
            ref = build_ref(d, spans, source, cuts)
        else:
            _say(d, "track", False, "no reference", "No real footage of this action is named yet: pick a candidate (finder.py yes), or give --span / --clip.")
            return _load(d / "chain.json")["stages"]
        rec = MO.track(d / "ref.mp4", d, kind=kind or ("swipe" if spans else "clip"))
        rec["chain"] = True
        rec["camera_only"] = bool(camera_only)
        rec["take_motion"]["approved"] = False
        (d / "motion.json").write_text(json.dumps(rec, indent=1))
        _say(d, "track", rec.get("frames_with_people", 0) > 0, "%d people, %.1f s" % (rec.get("people_max", 0), ref["seconds"]),
             "Bodies, hands and faces read on %d of %d frames; camera: %s. Free, %.0f s on this machine." % (
                 rec.get("frames_with_people", 0), rec.get("frames", 0), rec.get("camera"), rec.get("seconds_to_read", 0)),
             file="overlay.mp4")
        if "rehearse" not in only and camera_only:   # no bodies to rehearse: the reference's own camera is the motion
            words = camera_words(d)
            rec["take_motion"]["camera"] = {"from_track": True, "words": words}
            (d / "motion.json").write_text(json.dumps(rec, indent=1))
            _say(d, "camera", True, "from the track", words)
    ref = _load(d / "ref.json") or {}
    if "read" in only:
        import read as RD
        r = RD.read(d, take, ref.get("cuts"))
        _say(d, "read", bool(r["beats"]), "%d beats" % len(r["beats"]), r.get("moment", ""),
             beats=len(r["beats"]), missing=r.get("missing"), model=r.get("model"), file="motion-read.json")
    if "rehearse" in only:
        import retarget as RT
        # each stand-in built to its cast member's body (build.py: measured off the cast sheet, else from the words)
        import build as BU
        builds = {}
        if take.get("cast"):
            try:
                builds = BU.for_scene(scene_dir, take)
            except (OSError, ValueError, KeyError, SystemExit) as e:
                _say(d, "build", None, "plain stand-ins", "The cast's builds could not be read (%s); the stand-ins keep the plain torso." % str(e)[:160])
        m = RT.rehearse(d, cast={n: {"build": BU.to_standin(b["widths"])} for n, b in builds.items()})
        names = m.get("people_names") or []
        want = [p["ours"] for p in ME.read_of(d).get("people") or []]
        _say(d, "rehearse", bool(names), "%d of %d people from real skeletons" % (len(names), len(want)),
             "The stand-ins move as the tracked people did. " + " ".join(m.get("notes") or []), file="rehearsal/blocking.mp4",
             fallback=[n for n in want if n not in names])
        cams = ME.camera_read(_load(d / "camera.json") or {}, [(s["from"], s["to"]) for s in ME.tracks(_load(d / "pose.json"), ref.get("cuts"), _load(d / "camera.json"))])
        words = camera_words(d)
        _say(d, "camera", True, "from the track", words, punch=sum(len(c["punch"]) for c in cams) + sum(1 for c in cams if c.get("edit_zoom")))
        # the scene's motion for a take: the stand-ins' clip (none of the reference's people in it), decided below by the
        # chain's own checks (decide)
        rec = _load(d / "motion.json") or {}
        for k in ("override", "decided", "approved_by", "approved_at"):     # new motion: decided afresh
            rec.pop(k, None)
        rec.update({"kind": "real-skeleton", "status": "tracked"})
        rec["take_motion"] = {"source": str(d / "rehearsal" / "blocking.mp4"), "from": 0.0, "to": m.get("to"), "approved": False,
                              "pose": str(d / "rehearsal" / "skeleton.mp4"), "camera": {"from_track": True, "words": words}}
        parts = segments(d)
        if len(parts) > 1:                           # longer than one generation: made as several takes, part by part
            rec["take_motion"]["segments"] = parts
            _say(d, "segments", True, "%d takes of at most %.0f s" % (len(parts), TAKE_MAX),
                 "Longer than one generation, so it is made in parts, split at the reference's cuts and beat ends: " +
                 ", ".join("%.1f-%.1f s" % (p["from"], p["to"]) for p in parts) + ". Each part's take starts from the last frame of the one before.",
                 file="segments.json")
        (d / "motion.json").write_text(json.dumps(rec, indent=1))
        if not camera_only and gaps(d):
            # the reference does not show what our beats do: its skeletons would act the wrong moment. Our beats are
            # programmed into the rehearsal instead, on the reference's timing and camera.
            ours(scene_dir, take)
    if "preview" in only and (_load(d / "motion.json") or {}).get("kind") == "programmed":
        only = [s for s in only if s != "preview"]     # nothing real to measure our own blocking against
        decide(scene_dir)
    if "preview" in only:
        import match as MA
        p = preview(d)
        rec = MA.match(d, d / "rehearsal" / "blocking.mp4", "rehearsal", ref.get("cuts"), exact_dir=d / "rehearsal")
        _stamped(d / "match-rehearsal.json", d)
        if (d / "build.json").exists():                # the stand-ins' bodies against the cast's: rendered and measured
            import build as BU
            try:
                bc = BU.check(scene_dir)
                _stamped(d / "match-build.json", d)
                _say(d, "build", bc["failed"] == 0, "%d of %d as the cast" % (bc["passed"], len(bc["rows"])),
                     " · ".join("%s: %s" % (r["name"], r["short"]) for r in bc["rows"]), file="build-lineup.png")
            except SystemExit as e:
                _say(d, "build", None, "not checked", str(e)[:200])
        beats = [r for r in rec["rows"] if r["beat"] and "timing" not in r["name"] and r["ok"] is not None]
        held = sum(1 for r in beats if r["ok"])
        _say(d, "preview", not rec.get("held_by"), "%d ✓  %d ✗ against the reference" % (rec["passed"], rec["failed"]),
             "The 3D rehearsal measured against the real footage, beat by beat, before any take is paid for.",
             file=Path(p).name, match="match-rehearsal.json", beats_held=held, beats=len(beats))
        if watch:                                    # looked at as well as measured: what neither track holds
            import watch as WA
            try:
                v = WA.watch(d)
                _stamped(d / "verdict.json", d)
                _say(d, "watch", v["verdict"] != "not yet", v["verdict"], v.get("summary", ""), file="verdict.json", faults=len(v.get("faults") or []))
            except (SystemExit, ValueError, KeyError, TypeError, AttributeError) as e:   # it could not look: said, and the rows decide alone
                _say(d, "watch", None, "not watched", str(e)[:200])
        won = decide(scene_dir)
        if not won["passed"] and retry:
            # held: one more go on its own before it is left held. A second read can map the people right where the
            # first did not, and everything after the read is made again from it.
            first = list(won["held"])
            prepare(scene_dir, take, brand, framemap, source, only=["read", "rehearse", "preview"], kind=kind, watch=watch, retry=False)
            again = (_load(d / "motion.json") or {}).get("decided") or {}
            rec = _load(d / "chain.json")
            rec["stages"]["approve"]["tried_again"] = {"first_held": first, "now_ok": bool(again.get("passed"))}
            (d / "chain.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    elif camera_only and "track" in only:               # nobody in the shot: the camera's own path is the motion, nothing to rehearse
        rec = _load(d / "motion.json") or {}
        rec["camera_only"] = True
        (d / "motion.json").write_text(json.dumps(rec, indent=1))
        decide(scene_dir)
    return _load(d / "chain.json")["stages"]


def camera_words(d, a=None, b=None):
    """The camera for a take, from the track only: how it is held (the read) and what it measured doing per shot.
    No shot sizes, and no push the reference does not make. `a`, `b`: only that span of the reference (a long scene
    made as several takes), its seconds counted from the span's start."""
    d = Path(d)
    read = _load(d / "motion-read.json") or {}
    ref = _load(d / "ref.json") or {}
    pose, cam = _load(d / "pose.json"), _load(d / "camera.json") or {}
    cams = ME.camera_read(cam, [(s["from"], s["to"]) for s in ME.tracks(pose, ref.get("cuts"), cam)], int(pose.get("fps") or 16))
    cuts = ref.get("cuts") or []
    off = 0.0
    if a is not None and b is not None:
        cams = [dict(c, **{"from": max(c["from"], a) - a, "to": min(c["to"], b) - a}) for c in cams if c["to"] > a + 0.05 and c["from"] < b - 0.05]
        cuts, off = [c - a for c in cuts if a + 0.05 < c < b - 0.05], a
    held = ((read.get("camera") or {}).get("held_by") or "a phone held by a person").rstrip(".")
    by_shot = read.get("held") or {}
    if len(set(by_shot.values())) > 1:                # held differently from shot to shot: said per shot
        held = "; ".join("shot %s, %s" % (k, str(v).rstrip(".")) for k, v in sorted(by_shot.items()))
    bits = []
    for c in cams:
        w = ", ".join(x for x in c["words"].split(", ") if not x.startswith(("edit punch-in", "edit zoom")))
        bits.append(("%.1f-%.1f s: %s" % (c["from"], c["to"], w)) if len(cams) > 1 else w)
    still = all(abs(c["push"]) <= 0.04 for c in cams)
    return ("The camera: %s. It moves only as in the motion reference: %s.%s%s" % (
        held, "; ".join(bits), " It never pushes in or zooms; the framing is held." if still else " No zoom beyond that.",
        (" It cuts only where the motion reference cuts (at %s s), to the reference's own framings." % ", ".join("%.1f" % c for c in cuts)) if cuts
        else " One continuous take, no cuts."))


TAKE_MAX = 15.0        # seconds of motion one generation carries (the take doors' own ceiling)


def segments(d, limit=TAKE_MAX):
    """A scene longer than one generation, split into takes of about the same length: at the reference's own cuts
    first, then at the ends of the read's beats, never in the middle of a move; each part at most `limit` seconds. Written to segments.json
    ([{"k", "from", "to", "seconds", "starts_at": "a cut" | "a beat's end" | "an even split"}]); a scene that fits one
    generation has one part. Each later part's take starts from the last frame of the take before it."""
    d = Path(d)
    ref, read = _load(d / "ref.json") or {}, _load(d / "motion-read.json") or {}
    total = float(ref.get("seconds") or read.get("seconds") or 0)
    if not total:
        return []
    marks = {round(float(c), 2): "a cut" for c in ref.get("cuts") or []}
    for bt in read.get("beats") or []:
        marks.setdefault(round(float(bt["to"]), 2), "a beat's end")
    marks = {t: w for t, w in marks.items() if 0.3 < t < total - 0.3}
    parts, at, why = [], 0.0, "the start"
    while total - at > limit + 0.5:                   # half a second over is trimmed by the take itself, not split off
        left = total - at
        want = at + left / math.ceil(left / limit)    # parts of about the same length: no two-second stub at the end
        inside = [t for t in marks if at + 2.0 <= t <= at + limit and total - t >= 2.0]
        cuts = [t for t in inside if marks[t] == "a cut" and abs(t - want) <= 0.35 * limit]
        # the cut nearest an even split; else the nearest beat's end; else the even split itself
        nxt = min(cuts, key=lambda t: abs(t - want)) if cuts else (min(inside, key=lambda t: abs(t - want)) if inside else want)
        parts.append({"from": round(at, 2), "to": round(nxt, 2), "starts_at": why})
        at, why = nxt, marks.get(round(nxt, 2), "an even split")
    parts.append({"from": round(at, 2), "to": round(total, 2), "starts_at": why})
    for k, p in enumerate(parts, 1):
        p.update({"k": k, "seconds": round(p["to"] - p["from"], 2)})
    (d / "segments.json").write_text(json.dumps(parts, indent=1))
    return parts


def mechanics(read):
    """The motion read as lines a take is given: per beat, when, what, who moves first, who answers and how late, and
    the one move the track measured (its size and when it is half done). The read's finer notes on each body (weight,
    hands, eyes) are the model's words and stay on the page for a person to read; a take is told only what was
    measured, so its words never argue with its motion video."""
    words = {"lean": "leans %s about %s degrees", "head": "%s the head about %s degrees", "knees": "%s the knees about %s degrees",
             "hips": "%s about %s of a torso length", "hand_l": "the left hand %s about %s of the way from hip to shoulder",
             "hand_r": "the right hand %s about %s of the way from hip to shoulder", "turn": "turns %s about %s degrees", "near": "the heads %s by about %s head heights"}
    verb = {"lean": ("in", "back"), "head": ("ducks", "lifts"), "knees": ("bends", "straightens"), "hips": ("drops", "rises"),
            "hand_l": ("rises", "lowers"), "hand_r": ("rises", "lowers"), "turn": ("away from the lens", "toward the lens"), "near": ("move apart", "close in")}
    out = []
    for b in read.get("beats") or []:
        bits = ["%.1f-%.1f s: %s." % (b["from"], b["to"], str(b.get("what", "")).rstrip("."))]
        if b.get("starts"):
            ans = b.get("answers")
            bits.append("%s moves first%s." % (b["starts"], (", %s answers %.1f s later" % (ans, float(b.get("answer_lag") or 0.3))) if ans and ans != "none" else ""))
        ck = b.get("check")
        if ck and ck.get("from_track") and ck.get("measure") in words:
            v = verb[ck["measure"]][0 if ck.get("moves") != "down" else 1]
            by = ("%.1f" if ck["measure"] in ("hips", "hand_l", "hand_r", "near") else "%.0f") % float(ck.get("by") or 0)
            bits.append("Measured off the real footage: %s %s, half done at %.1f s." % (ck["who"], words[ck["measure"]] % (v, by), float(ck.get("half_done_at") or b["from"])))
        elif not ck:
            bits.append("A hold: nobody moves far; they breathe and settle.")
        out.append(" ".join(bits))
    return out


def gaps(d):
    """Our beats' moves the reference does not show (the motion read's `missing`), once the read is of this
    reference. Empty when the reference shows everything our beats do."""
    read = _load(Path(d) / "motion-read.json") or {}
    return [str(x).strip() for x in read.get("missing") or [] if str(x).strip()]


def split(n, k):
    """n items into k runs as even as can be, in order: [[0, 1], [2], ...]."""
    out, at = [], 0
    for i in range(k):
        size = n // k + (1 if i < n % k else 0)
        out.append(list(range(at, at + size)))
        at += size
    return out


def ref_timing(take, read, seconds=None):
    """Each of our lines' window on the reference's own beat timing: our lines laid over the reference's beats in
    order (several beats to a line, or one beat's window shared by several lines). Returns (rows, seconds) in
    motion_program's timeline shape, or (None, None) when the reference has no beats."""
    lines = take.get("script") or []
    beats = sorted(read.get("beats") or [], key=lambda b: float(b["from"]))
    if not lines or not beats:
        return None, None
    rows = []
    if len(lines) <= len(beats):
        for k, g in enumerate(split(len(beats), len(lines))):
            rows.append((k, float(beats[g[0]]["from"]), float(beats[g[-1]]["to"])))
    else:
        for i, g in enumerate(split(len(lines), len(beats))):
            a, b = float(beats[i]["from"]), float(beats[i]["to"])
            step = (b - a) / max(1, len(g))
            rows += [(k, a + step * j, a + step * (j + 1)) for j, k in enumerate(g)]
    end = float(seconds or 0) or max(r[2] for r in rows) + 0.3
    return [{"line": k + 1, "speaker": lines[k].get("speaker"), "from": round(a, 2), "to": round(b, 2)} for k, a, b in rows], round(end, 2)


def ours(scene_dir, take=None, model=None):
    """The rehearsal programmed from OUR beats (motion_program.py), timed to the reference's beats, our figures starting
    where its people stood and filmed by its tracked camera (retarget.build's camera path). For a reference that does not show our moves (`gaps`): the swipe gives the skeleton of the moment
    (timing, cuts, camera), our beats give every body move. The reference's own rehearsal moves to
    rehearsal-reference/. The motion passes as programmed motion does (decide); the board says why it was made."""
    import motion_program as MP
    scene_dir = Path(scene_dir)
    d = scene_dir / "motion"
    take = take or _load(scene_dir / "take.json") or {}
    if not take.get("script") and not take.get("staging"):
        raise SystemExit("this scene's take has no beats to program (%s)" % (scene_dir / "take.json"))
    read = ME.read_of(d) or {}
    ref = _load(d / "ref.json") or {}
    rows, seconds = ref_timing(take, read, ref.get("seconds"))
    reh, kept = d / "rehearsal", d / "rehearsal-reference"
    if reh.exists() and not (_load(d / "motion.json") or {}).get("ours_because"):
        shutil.rmtree(kept, ignore_errors=True)
        shutil.move(str(reh), str(kept))
    frame = None
    if (d / "pose.json").exists() and read.get("people"):
        try:                                          # the reference's own staging: where its people stood, its camera
            import retarget as RT
            frame = RT.build(d)
        except (OSError, ValueError, KeyError, IndexError, ZeroDivisionError):
            frame = None
    if frame and frame.get("cuts"):
        # a reference with cuts re-frames its people shot by shot: its first shot sets where ours start, and the camera
        # is programmed to follow them (its cuts and framings stay in the take's camera words, from the track)
        first = next((i for i, _ in enumerate(frame["camera"]["track"])), 0)
        frame = {"people": [p for p in frame["people"] if (p.get("track") or [None])[first]], "fps": frame["fps"],
                 "seconds": frame["seconds"], "cuts": frame["cuts"]}
    m = MP.program(take, reh, model or MP.MODEL, rows=rows, seconds=(frame or {}).get("seconds") or seconds, frame=frame)
    words = camera_words(d) if (d / "camera.json").exists() else None
    rec = _load(d / "motion.json") or {}
    for k in ("override", "decided", "approved_by", "approved_at"):
        rec.pop(k, None)
    because = gaps(d)
    rec.update({"kind": "programmed", "status": "ready", "ours_because": because or ["programmed from our beats"],
                "timing_from": "the reference's beats" if rows else "our lines' reads", "dropped": m.get("dropped"),
                "notes": m.get("notes") or []})
    rec["take_motion"] = {"source": str(reh / "blocking.mp4"), "from": 0.0, "to": m["take_motion"].get("to") or seconds,
                          "approved": True, "pose": str(reh / "skeleton.mp4"),
                          "camera": {"from_track": True, "words": words} if words else (m["take_motion"].get("camera") or {})}
    (d / "motion.json").write_text(json.dumps(rec, indent=1))
    _say(d, "rehearse", True, "our beats, on the reference's timing",
         "The reference does not show: %s. The stand-ins act our beats instead; the reference gives the timing and the "
         "camera only.%s" % ("; ".join(because) or "(asked by hand)",
                              (" Moves the figures could not carry: " + " · ".join(m.get("notes"))) if m.get("notes") else ""),
         file="rehearsal/blocking.mp4", ours=True, dropped=m.get("dropped") or 0)
    return rec


PALETTE = ([0.85, 0.75, 0.6], [0.15, 0.15, 0.17], [0.55, 0.2, 0.2], [0.2, 0.35, 0.55], [0.75, 0.75, 0.75], [0.35, 0.5, 0.3])


def direct(scene_dir, direction, seconds=None, render=True):
    """The scene's motion from OUR direction (production injection: our movement and camera instructions, generated
    for our scene): where everyone starts, every move on its timing, every camera shot. Rendered as the rehearsal the
    take moves to; any reference's own rehearsal moves to rehearsal-reference/. Passes as made (nothing real to
    measure our own direction against); the take's camera words are our shots'."""
    import motion as MO
    import motion_program as MP
    scene_dir = Path(scene_dir)
    d = scene_dir / "motion"
    d.mkdir(parents=True, exist_ok=True)
    people = [{"name": p["name"], "at": list(p.get("at") or [0, 2])[:2], "face": p.get("face", 0),
               "color": p.get("color") or PALETTE[k % len(PALETTE)]} for k, p in enumerate(direction.get("people") or [])]
    # nobody on screen (a product or a place): the direction is the camera alone
    shots = (direction.get("camera") or {}).get("shots") or []
    end = max([float(b.get("to") or 0) for b in direction.get("beats") or []] + [float(seconds or 0), 1.0])
    # whoever is seated when the scene opens sits from the first frame
    opening = [{"from": 0.0, "to": 0.2, "who": p["name"], "sit": True} for p in direction.get("people") or [] if p.get("sit") or p.get("seated")]
    raw = {"people": people, "beats": opening + list(direction.get("beats") or [])}
    spec = MP.clean(raw, end)
    spec.update({"seconds": round(end, 2), "fps": 16, "size": [480, 854], "render": render,
                 "camera": {"shots": shots} if shots else (direction.get("camera") or {}),
                 "sky": [0.55, 0.72, 0.92], "floor": [0.82, 0.74, 0.58]})
    reh, kept = d / "rehearsal", d / "rehearsal-reference"
    rec = _load(d / "motion.json") or {}
    if reh.exists() and rec.get("kind") not in ("directed", "programmed"):
        shutil.rmtree(kept, ignore_errors=True)
        shutil.move(str(reh), str(kept))
    reh.mkdir(parents=True, exist_ok=True)
    (reh / "spec.json").write_text(json.dumps(spec, indent=1))
    MO.blocking(reh / "spec.json", reh / "blocking.mp4", exact=True, motion_dir=reh)
    for k in ("override", "decided", "approved_by", "approved_at", "ours_because", "people_max", "frames", "frames_with_people",
              "hands_seen", "faces_seen", "files", "tracked_at"):           # the reference's own measures and files
        rec.pop(k, None)
    rec.update({"kind": "directed", "status": "ready", "dropped": len(spec["dropped"]), "from": 0.0, "to": spec["seconds"],
                "camera_shots": [{"from": x.get("from"), "words": x.get("words")} for x in shots]})
    rec["take_motion"] = {"source": str(reh / "blocking.mp4"), "from": 0.0, "to": spec["seconds"], "approved": True,
                          "pose": str(reh / "skeleton.mp4"), "camera": {}}
    (d / "motion.json").write_text(json.dumps(rec, indent=1))
    _say(d, "rehearse", True, "our direction: %d moves, %d shots" % (len(spec["beats"]), len(shots)),
         "Our own movement and camera, generated for our scene; the source gave what each moment must do, not the moves."
         + ((" Moves the figures could not carry: %d." % len(spec["dropped"])) if spec["dropped"] else ""),
         file="rehearsal/blocking.mp4", directed=True)
    _say(d, "camera", True, "our shots", " · ".join("%.1f s %s" % (float(x.get("from") or 0), x.get("words") or "") for x in shots))
    return rec


def preview(d):
    """reference | its skeleton | the 3D rehearsal, side by side: what is watched before paying."""
    d = Path(d)
    out = d / "preview.mp4"
    ins = [d / "read.mp4", d / "skeleton.mp4", d / "rehearsal" / "blocking.mp4"]
    ins = [p for p in ins if p.exists()]
    fl = ";".join("[%d:v]scale=-2:640,setsar=1[v%d]" % (i, i) for i in range(len(ins)))
    fl += ";" + "".join("[v%d]" % i for i in range(len(ins))) + "hstack=inputs=%d:shortest=1[o]" % len(ins)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for p in ins:
        cmd += ["-i", str(p)]
    subprocess.run(cmd + ["-filter_complex", fl, "-map", "[o]", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p",
                          "-movflags", "+faststart", str(out)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vf", "fps=1.5,scale=-2:300,tile=6x1", "-frames:v", "1",
                    str(d / "preview.jpg")], check=False)
    return str(out)


def who(scene_dir, pairs, by=None):
    """A person's correction of who is who: {"A1": "<one of our people>" or "extra"} written to who.json (it wins over
    the model's read), then the 3D rehearsal and the preview are made again from it and decided afresh (an earlier
    pass or override does not carry over: the motion changed)."""
    d = Path(scene_dir) / "motion"
    old = _load(d / "who.json") or {}
    old.update({str(k).upper(): v for k, v in pairs.items()})
    old["_by"], old["_at"] = by or old.get("_by"), time.strftime("%Y-%m-%dT%H:%M:%S")
    (d / "who.json").write_text(json.dumps(old, indent=1))
    rec = _load(d / "motion.json") or {}
    if any(rec.pop(k, None) for k in ("override", "approved_by", "approved_at")):
        (d / "motion.json").write_text(json.dumps(rec, indent=1))
    return prepare(scene_dir, only=["rehearse", "preview"], retry=False)


def _stamp(d):
    """What a check was made against: the reference's track and the rehearsal (each one's file time). A check stamped
    with another reference or another rehearsal is stale and does not count."""
    d = Path(d)
    parts = [d / "pose.json", d / "rehearsal" / "pose.json"]
    if not parts[1].exists():
        return None
    return "|".join("%.3f" % p.stat().st_mtime if p.exists() else "-" for p in parts)


def _stamped(f, d):
    """Stamp a check file with the reference and the rehearsal it was made against."""
    rec = _load(f)
    if rec is not None:
        rec["rehearsal_stamp"] = _stamp(d)
        Path(f).write_text(json.dumps(rec, indent=1, ensure_ascii=False))


def _current(rec, d):
    """A check counts when it was made against this reference and rehearsal (or carries no stamp: made before stamps)."""
    return rec is not None and (rec.get("rehearsal_stamp") is None or rec.get("rehearsal_stamp") == _stamp(d))


# what each kind of motion is held to. A rehearsal from real footage (real-skeleton) is checked against that footage; a
# shot with nobody in it is its reference's own camera path; programmed and hand-built 3D motion (the verbs, no real
# footage to measure against) is the fallback and passes as made; any other motion (a clip tracked but never rehearsed)
# has not been through the checks.
CHECKED_KINDS = ("real-skeleton",)
PASS_KINDS = {"camera-only": "nobody in the shot: the reference's own camera path is the motion",
              "programmed": "programmed motion (the fallback, no real footage to measure it against)",
              "3d": "a hand-built 3D blocking (no real footage to measure it against)",
              "directed": "our own direction: movement and camera generated for our scene (production injection)"}


def decide(scene_dir):
    """The chain's own decision on a scene's motion: passed, or held with the reasons. Nobody is asked.

    For a rehearsal made from real footage it reads what the checks wrote, made against this reference and this
    rehearsal: the rehearsal's rows against the reference (the failed rows that hold: the move itself, the stand-in on
    its footage, its framing, a lead nobody followed), the stand-ins' bodies against the cast, and the watcher's shots
    (a move that does not happen, people misplaced or the wrong size). A preview the watcher could not look at (no
    account answered) is decided on the measured rows alone, and `checked` says so. Camera-only, programmed and hand-
    built 3D motion pass as made; a clip tracked but never rehearsed is held until the chain runs on it.

    The start picture is judged apart from the motion: its rows go to `decided.picture` (and the board), never into
    `take_motion.held`, because a take is checked against its own picture when it is made (picture_held).

    Writes motion.json `status` ("approved" or "held"), `take_motion.approved` / `.held`, and `decided` = {"ok" (the
    checks alone), "passed" (the checks, or a recorded override that still stands), "held", "checked", "picture"}."""
    d = Path(scene_dir) / "motion"
    f = d / "motion.json"
    rec = _load(f)
    if not rec:
        raise SystemExit("no motion here yet (%s): run the motion chain on the scene first" % f)
    tm = rec.get("take_motion") or {}
    kind = "camera-only" if rec.get("camera_only") else rec.get("kind")
    held, checked, ours_held = [], [], []
    if kind in PASS_KINDS:
        checked.append(PASS_KINDS[kind])
    elif kind not in CHECKED_KINDS or Path(tm.get("source") or "").parts[-3:] != ("motion", "rehearsal", "blocking.mp4"):
        # the take moves to the rehearsal (wherever the scene folder sits), never to a clip read in after it
        held.append("this motion has not been rehearsed and checked (it was read from a clip since): run the motion chain on the scene")
    else:
        rows = _load(d / "match-rehearsal.json")
        if rows is not None and rows.get("held_by") is None and (d / "rehearsal" / "pose.json").exists():
            # rows written before the chain decided for itself carry no word on which fails hold: measured again here
            # (free and local: the rehearsal's own exact joints against the reference's track)
            import match as MA
            try:
                MA.compare(d, d / "rehearsal", "rehearsal", (_load(d / "ref.json") or {}).get("cuts"))
                _stamped(d / "match-rehearsal.json", d)
                rows = _load(d / "match-rehearsal.json")
            except (OSError, ValueError, KeyError, SystemExit):
                pass
        if not _current(rows, d):
            held.append("the rehearsal was never checked against its reference" if rows is None else
                        "the reference or the rehearsal changed since they were last checked")
        else:
            checked.append("the rehearsal against its reference: %d pass, %d fail" % (rows.get("passed", 0), rows.get("failed", 0)))
            held += list(rows.get("held_by") if rows.get("held_by") is not None else
                         ["%s: %s" % (r["name"], r["short"]) for r in rows.get("rows") or [] if r["ok"] is False])
        for g in gaps(d):
            ours_held.append("the reference does not show our beat's move (%s): its skeletons would act another moment. "
                             "Run motion_chain.py ours on the scene (our beats on the reference's timing and camera), or "
                             "give real footage of our move" % g)
        held += ours_held
        bc = _load(d / "match-build.json")
        if bc and _current(bc, d):
            checked.append("the stand-ins' bodies against the cast: %d of %d" % (bc.get("passed", 0), len(bc.get("rows") or [])))
            held += list(bc.get("held_by") or [])
        v = _load(d / "verdict.json")
        if v and _current(v, d):
            checked.append("the watcher: %s" % v.get("verdict"))
            held += ["the watcher, %s" % h for h in (v.get("holds") if v.get("holds") is not None else
                                                     ([x.get("what") for x in v.get("faults") or [] if x.get("matters") == "a lot"] if v.get("verdict") == "not yet" else []))]
        else:
            checked.append("not watched (no account could look at the preview): decided on the measured rows alone")
    picture = []
    sp = _load(d / "match-start-picture.json")
    if sp and _current(sp, d):
        picture = ["%s: %s" % (r["name"], r["short"]) for r in sp.get("rows") or [] if r["ok"] is False]
        checked.append("the start picture (%s) against the rehearsal's first frame: %d pass, %d fail" % (
            Path(sp.get("picture") or "first-frame.png").name, sp.get("passed", 0), sp.get("failed", 0)))
    ok = not held
    if "own checks" in str(rec.get("approved_by") or ""):      # written by a stopgap that meant the checks: no override
        rec.pop("approved_by", None)
        rec.pop("approved_at", None)
    if not rec.get("override") and rec.get("approved_by") and kind not in PASS_KINDS:
        # an approval given by hand before the chain decided for itself: kept, as the override it now is
        rec["override"] = {"by": rec["approved_by"], "at": rec.get("approved_at"), "over": [], "from_before": True}
    # a recorded override stands until the motion changes, except over our own beats: a rehearsal acting the
    # reference's moves where ours are written is never passed by hand (2026-11-15)
    over = rec.get("override") if not ok and not ours_held else None
    passed = bool(ok or over)
    rec.update({"status": "approved" if passed else "held",
                "decided": {"ok": ok, "passed": passed, "held": held, "checked": checked, "picture": picture,
                            "by": "the chain's own checks" if ok else ("an override by %s" % over.get("by")) if over else "the chain's own checks",
                            "at": time.strftime("%Y-%m-%dT%H:%M:%S")}})
    rec.setdefault("take_motion", {}).update({"approved": passed, "held": [] if passed else held})
    f.write_text(json.dumps(rec, indent=1))
    _say(d, "approve", passed, "passed" if ok else ("held, overridden by %s" % over.get("by")) if over else "held: " + held[0][:90],
         ("Passed by its own checks: " + "; ".join(checked) + ".") if ok else
         ("Held by its own checks (%s), overridden by %s." % (" · ".join(held), over.get("by"))) if over else ("Held by its own checks. " + " · ".join(held)),
         held=held, checked=checked)
    if sp and _current(sp, d):
        _say(d, "picture", not picture, "matches the first frame" if not picture else "does not match: " + picture[0][:80],
             "The start picture %s laid over the rehearsal's first frame. %s" % (Path(sp.get("picture") or "").name,
                                                                                  " · ".join(picture) or "Everyone there, in place, the right size."),
             file="first-frame.png")
    return rec["decided"]


def approve(scene_dir, by):
    """An override, recorded: a named person passes motion the chain's own checks held (or motion that never went
    through them: a phone act-out dropped on a scene). The chain itself never waits for this; it decides (`decide`)."""
    import motion as MO
    if not by:
        raise SystemExit("an override needs the name of who gave it (--by)")
    d = Path(scene_dir) / "motion"
    was = (_load(d / "motion.json") or {}).get("decided") or {}
    rec = MO.approve(scene_dir, by)
    rec["override"] = {"by": by, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "over": was.get("held") or []}
    rec["take_motion"]["held"] = []
    if rec.get("decided"):
        rec["decided"]["passed"] = True
    (d / "motion.json").write_text(json.dumps(rec, indent=1))
    _say(d, "approve", True, "passed by override (%s)" % by, "Overridden by %s%s." % (by, (", over: " + " · ".join(was["held"])) if was.get("held") else ""), by=by, override=True)
    return rec


def picture_held(scene_dir, picture):
    """Why a take may not start from this picture, or "" when it may: the picture must pass start_check against the
    scene's rehearsal (a record for this same picture, newer than it, is reused; otherwise the check runs now)."""
    pic = Path(picture)
    d = Path(scene_dir) / "motion"
    if not pic.exists() or not (d / "rehearsal" / "pose.json").exists():
        return ""
    f = d / "match-start-picture.json"
    rec = _load(f) or {}
    if not (rec.get("picture") == str(pic) and f.stat().st_mtime >= pic.stat().st_mtime and _current(rec, d)):
        rec = start_check(scene_dir, pic)
    if rec.get("failed"):
        bad = "; ".join("%s %s" % (r["name"], r["short"]) for r in rec.get("rows") or [] if r.get("ok") is False)
        return ("this take's start picture does not match its motion's first frame (%s): remake it "
                "(motion_program.py first-frame) before the take is paid for" % bad)
    return ""


def for_take(take, dry_run=False):
    """The take as it may be made: its scene's motion in once that motion has passed its own checks, and, when it
    carries a tracked camera, the written shot sizes out. Motion its checks held, or that never went through them, stops
    the take before any paid call, with the reason. Nobody is waited on."""
    m = dict(take.get("motion") or {})
    if m.get("scene"):
        f = Path(m["scene"]) / "motion" / "motion.json"
        if not f.exists():
            raise SystemExit("no motion read for this scene yet (%s): run the motion chain on it first (components/motion/motion_chain.py run)" % f)
        tm = json.loads(f.read_text())["take_motion"]
        m.update({k: tm[k] for k in ("source", "from", "to", "approved", "held", "pose", "camera") if k in tm})
    if not dry_run and m.get("held"):
        raise SystemExit("this scene's motion is held by its own checks (%s). Give it a better reference or correct who is who, and run the "
                         "motion chain again (motion_chain.py run); no take is made from held motion." % " · ".join(m["held"]))
    if m.get("approved") is False and not dry_run:
        raise SystemExit("this scene's motion has not been through its checks: run the motion chain on the scene (motion_chain.py run "
                         "<scene dir>); it passes or holds on its own")
    if not m:
        return take
    md = Path(m["scene"]) / "motion" if m.get("scene") else None
    if md is not None and not dry_run and m.get("segment") in (None, 0) and take.get("picture"):
        held = picture_held(m["scene"], take["picture"])
        if held:
            raise SystemExit(held)
    seg = None
    if m.get("segment") is not None and md is not None:
        parts = _load(md / "segments.json") or []
        seg = next((p for p in parts if p["k"] == int(m["segment"])), None)
        if seg is None:
            raise SystemExit("this scene's motion has no part %s (it has %d)" % (m["segment"], len(parts)))
        m.update({"from": seg["from"], "to": seg["to"]})           # that part of the rehearsal only
        if (m.get("camera") or {}).get("from_track"):
            m["camera"] = dict(m["camera"], words=camera_words(md, seg["from"], seg["to"]))
    out = dict(take, motion=m)
    mrec = _load(md / "motion.json") or {} if md is not None else {}
    # programmed from our beats because the reference acts another moment: its read describes that moment, so none of
    # it rides into the take's words (the reference gave the timing and the camera only)
    read = ME.read_of(md) if md is not None and not mrec.get("ours_because") and mrec.get("kind") != "directed" else None
    if read and read.get("beats"):                   # how real people do this moment, beat by beat, for the take's words
        if seg:                                      # the beats inside this part, on the part's own clock
            read = dict(read, beats=[dict(b, **{"from": max(0.0, b["from"] - seg["from"]), "to": min(seg["to"], b["to"]) - seg["from"]})
                                     for b in read["beats"] if b["to"] > seg["from"] + 0.1 and b["from"] < seg["to"] - 0.1])
        out["mechanics"] = mechanics(read)
    cam = m.get("camera") or {}
    if cam.get("from_track") and not (take.get("camera") or {}).get("directed"):   # our own shots are never replaced
        was = take.get("camera") or {}
        dropped = {k: was[k] for k in ("shots", "framing", "move", "style", "angle") if was.get(k)}
        # views (multi-cam) and anything else stay; sizes and moves come from the track alone
        kept = {k: v for k, v in was.items() if k not in ("shots", "framing", "move", "style", "angle", "focus")}
        out["camera"] = dict(kept, move=cam.get("words") or "the camera moves only as in the motion reference", from_track=True)
        if dropped:
            out["camera_dropped"] = dropped
        out["script"] = [{k: v for k, v in ln.items() if k != "camera"} for ln in take.get("script") or []]
    return out


def check(scene_dir, clip=None, name="take"):
    """A finished take against the reference; the rows go to <scene>/motion/match-<name>.json."""
    import match as MA
    scene_dir = Path(scene_dir)
    d = scene_dir / "motion"
    take = _load(scene_dir / "take.json") or {}
    clip = Path(clip or take.get("out") or scene_dir / "take.mp4")
    if not clip.exists():
        raise SystemExit("no finished clip to check (%s)" % clip)
    return MA.match(d, clip, name)


def print_words(scene_dir, place=None):
    """The 3D set print's words for a scene's start picture, all from the scene itself: the place (`place`, else the
    take's `look`), the rehearsal's first frame person by person (frame_words: where each head sits, how big, how much
    body, facing, hands), and each cast member's look, numbered in face-board order (the take's `lineup`, then the rest
    of the cast). Written by hand these drifted from the shot every time (2026-11-15)."""
    sd = Path(scene_dir)
    take = json.loads((sd / "take.json").read_text())
    cast = take.get("cast") or {}
    order = [n for n in (take.get("lineup") or []) if n in cast] + [n for n in cast if n not in (take.get("lineup") or [])]
    fw = frame_words(sd) or ""
    for k, n in enumerate(order, 1):
        fw = fw.replace(n + ":", "person %d (%s):" % (k, n))
    looks = " ".join("Person %d (%s): %s." % (k, n, (cast[n] or {}).get("look", "").rstrip("."))
                     for k, n in enumerate(order, 1) if isinstance(cast.get(n), dict))
    where = place or (take.get("look") or "").split(";")[0]
    return ("A real photograph shot on a phone, %s. The 3D render is the layout: keep its camera, framing and every "
            "person's place, size and facing exactly; do not move, enlarge, add or remove anyone. %s Nobody else stands "
            "in the shot. The large faces at the top of the reference picture are each person's REAL face, numbered in "
            "this order; their outfits are under them. Copy each face and outfit exactly: same face shape and width, same "
            "skin tone (never lighter), same features, same mask; never slimmer, younger, lighter or prettier. %s No text, "
            "no logos." % (where.strip().rstrip("."), fw.strip(), looks)).replace("  ", " ")


def frame_words(scene_dir, frame=0):
    """The rehearsal's first frame said in words, for whoever makes the start picture: per person, where the head sits
    in the frame, how much of the body the frame shows, which way they face, and where each hand is. Measured off the
    stand-ins' own joints (an image model does not read a grey stand-in's camera; it reads words)."""
    d = Path(scene_dir) / "motion"
    reh = _load(d / "rehearsal" / "pose.json")
    if not reh or not reh.get("frames"):
        raise SystemExit("no rehearsal here yet (%s)" % (d / "rehearsal"))
    people = next((f["people"] for f in reh["frames"][frame:] if f["people"]), [])
    return framing_words(people)


def framing_words(people):
    """`people`: one frame's people with `body33` (fractions of the frame, with a seen flag) and `world`."""
    def inside(q):
        return q[2] > 0.5 and 0.0 <= q[0] <= 1.0 and 0.0 <= q[1] <= 1.0
    lines = []
    for p in sorted(people, key=lambda p: p["body33"][0][0]):
        b, w = p["body33"], p.get("world") or []
        name = p.get("name") or "the person"
        across = "left" if b[0][0] < 0.36 else "right" if b[0][0] > 0.64 else "centre"
        up = "upper" if b[0][1] < 0.36 else "lower" if b[0][1] > 0.64 else "middle"
        hips, knees, ankles = inside(b[23]) or inside(b[24]), inside(b[25]) or inside(b[26]), inside(b[27]) or inside(b[28])
        shows = ("the whole body, feet in frame" if ankles else "head to knees" if knees else "head to hips, no legs in frame" if hips
                 else "head and chest only, no hips or legs in frame")
        face = ""
        if len(w) >= 13:
            # which way the face points: the nose from between the ears (x along the picture, z toward or away from the lens)
            fx, fz = w[0][0] - (w[7][0] + w[8][0]) / 2, w[0][2] - (w[7][2] + w[8][2]) / 2
            side = math.degrees(math.atan2(abs(fx), abs(fz) or 1e-6))
            to = "left" if fx < 0 else "right"
            face = ("in profile, facing the picture's %s" % to) if side > 60 else ("three-quarter, turned to the picture's %s" % to) if side > 25 else \
                   ("facing the camera" if fz < 0 else "facing away from the camera")
        hands = []
        for label, wr, sh, hp in (("left", 15, 11, 23), ("right", 16, 12, 24)):
            if not inside(b[wr]):
                continue
            h = ("raised to the face" if b[wr][1] < b[sh][1] - 0.02 else "at chest height" if b[wr][1] < (b[sh][1] + b[hp][1]) / 2 else
                 "at the waist" if b[wr][1] < b[hp][1] + 0.03 else "down by the thigh")
            reach = b[wr][0] - b[sh][0]
            out = (", reaching to the picture's %s" % ("left" if reach < 0 else "right")) if abs(reach) > 0.15 else ""
            hands.append("their %s hand %s%s" % (label, h, out))
        # how big the head reads, said only when the shoulders are in the frame to measure it by
        size = (", about %.0f%% of the frame's height" % (100 * abs(b[0][1] - (b[11][1] + b[12][1]) / 2) * 2.2)) if inside(b[11]) and inside(b[12]) else \
               ", large in the frame (the shoulders run out of it)"
        lines.append("%s: head in the %s %s of the frame%s; the frame shows %s; %s%s." % (
            name, up, across, size, shows, face or "facing as the layout shows", ("; " + "; ".join(hands)) if hands else "; no hands in frame"))
    return "Framing, exactly as the layout frame: " + " ".join(lines) + " Keep this framing: do not pull back, do not show more of any body than this, do not change the side the camera is on."


def rehearsal_hidden(d, first, aspect=0.5625):
    """Who the rehearsal's own first frame hides: its render read with the same reader a start picture is read with,
    and every stand-in the reader cannot find there (no head read within a head of theirs) stands behind someone, as
    the picture's people will. Returns {name: the nearer person in front of them}, or None when there is no render to
    read (the check then reads the joints)."""
    import subprocess
    import match as MA
    import motion as MO
    blk = Path(d) / "rehearsal" / "blocking.mp4"
    if not blk.exists():
        return None
    work = Path(d) / "rehearsal" / "frame-0-read"
    if not (work / "pose.json").exists() or (work / "pose.json").stat().st_mtime < blk.stat().st_mtime:
        work.mkdir(parents=True, exist_ok=True)
        clip = work / "frame.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(blk), "-frames:v", "1", "-vf", "fps=16", str(work / "frame.png")], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "0.3", "-i", str(work / "frame.png"), "-vf",
                        "fps=16,scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(clip)], check=True)
        MO.track(clip, work, kind="picture")
    pose = _load(work / "pose.json") or {"frames": []}
    seen = max((f["people"] for f in pose["frames"]), key=len, default=[])
    read = [m for m in (ME.frame_measures(p, aspect) for p in seen) if "x" in m]
    exact = [(p.get("name"), ME.frame_measures(p, aspect)) for p in first]
    exact = [(n, m) for n, m in exact if n and "x" in m]
    out = {}
    for n, m in exact:
        if any(math.hypot((r["x"] - m["x"]) * aspect, r["y"] - m["y"]) <= m["head_size"] for r in read):
            continue
        nearer = [(n2, m2) for n2, m2 in exact if n2 != n and m2["head_size"] > m["head_size"]]
        if nearer:
            out[n] = min(nearer, key=lambda v: math.hypot((v[1]["x"] - m["x"]) * aspect, v[1]["y"] - m["y"]))[0]
    return out


def start_check(scene_dir, picture=None):
    """The start picture set against the rehearsal's first frame before any take is paid for: the picture's people
    are read with the tracker's own reader and laid over the stand-ins (everyone there, in place, the same size in the
    frame). A picture framed wider, tighter or from another side than the motion it must start fails here. Writes
    <scene>/motion/match-start-picture.json (the board shows it) and returns it."""
    import match as MA
    import motion as MO
    scene_dir = Path(scene_dir)
    d = scene_dir / "motion"
    picture = Path(picture or d / "first-frame.png")
    reh = _load(d / "rehearsal" / "pose.json")
    if not picture.exists() or not reh or not reh.get("frames"):
        raise SystemExit("needs the start picture (%s) and the scene's rehearsal (%s)" % (picture, d / "rehearsal"))
    work = d / "match-start-picture"
    work.mkdir(parents=True, exist_ok=True)
    clip = work / "picture.mp4"                         # the picture as a quarter second of video, so the same reader reads it
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "0.3", "-i", str(picture), "-vf",
                    "fps=16,scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(clip)], check=True)
    MO.track(clip, work, kind="picture")
    pose = _load(work / "pose.json") or {"frames": []}
    seen = max((f["people"] for f in pose["frames"]), key=len, default=[])
    first = next((f["people"] for f in reh["frames"] if f["people"]), [])
    aspect = pose["width"] / float(pose["height"]) if pose.get("height") else 0.5625
    rows = MA.start_rows(first, seen, aspect, hidden=rehearsal_hidden(d, first))
    rec = {"clip": "start picture", "picture": str(picture), "rows": rows, "passed": sum(1 for r in rows if r["ok"] is True),
           "failed": sum(1 for r in rows if r["ok"] is False), "open": 0, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    rec["rehearsal_stamp"] = _stamp(d)
    (d / "match-start-picture.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    if (_load(d / "motion.json") or {}).get("decided"):      # the start picture is one of the checks the motion passes or is held on
        decide(scene_dir)
    return rec


def _print_as_start(scene_dir, pic):
    """The take's filed 3D set print (take.json `set_print`) becomes the start picture as it is, when it passes
    start_check against this rehearsal: the set was staged from the rehearsal's own positions, facing and camera, so the
    print already is the first frame and redrawing it (a second model reading two layouts) only moves people. Returns
    True when it was used. (2026-11-15: three redraws of a matching print each drifted people and were refused.)"""
    import shutil
    try:
        take = json.loads((Path(scene_dir) / "take.json").read_text())
    except (OSError, ValueError):
        return False
    sp = take.get("set_print")
    if not sp or not Path(sp).exists():
        return False
    d = Path(scene_dir) / "motion"
    if (_load(d / "motion.json") or {}).get("camera_only"):
        # nobody's body is in the shot (a close-up of skin, hands, an object): there is no rehearsal to lay people on,
        # so the filed print is the first frame as it is; faces are still checked inside the take (take_faces)
        shutil.copyfile(sp, pic)
        rec = {"picture": str(pic), "failed": 0, "passed": 0, "rows": [], "camera_only": True,
               "why": "camera-only motion: the filed print is the start picture as printed, no people to place"}
        (d / "match-start-picture.json").write_text(json.dumps(rec, indent=1))
        _stamped(d / "match-start-picture.json", d)
        return True
    if start_check(scene_dir, Path(sp)).get("failed"):
        return False
    shutil.copyfile(sp, pic)
    start_check(scene_dir, pic)                          # the record names the start picture itself
    return True


def ready(scene_dir, picture=True, tries=2, looks=None):
    """Everything a take needs from the chain, made and checked by the chain itself, with nobody asked: the scene's
    motion decided (passed, by its checks or a recorded override, or held), and the start picture made from the
    rehearsal's first frame (motion_program `first_frame`: framing in words, our cast and set) and laid over that frame;
    a picture that does not match is made again, up to `tries`. Returns {"ok", "picture", "held": [...], "tries"}.
    Making a picture is a paid call: this is for the moment a take is about to be made, never for looking."""
    scene_dir = Path(scene_dir)
    d = scene_dir / "motion"
    if not _load(d / "motion.json"):
        raise SystemExit("no motion here yet (%s): run the motion chain on the scene first (motion_chain.py run)" % (d / "motion.json"))
    won = decide(scene_dir)
    if not won["passed"]:                               # the motion itself is held: no picture is paid for on top of it
        return {"ok": False, "picture": None, "held": won["held"], "tries": 0}
    if not picture:
        return {"ok": True, "picture": None, "held": [], "tries": 0}
    pic, why, n = d / "first-frame.png", None, 0
    sp = _load(d / "match-start-picture.json") or {}
    good = pic.exists() and sp.get("picture") == str(pic) and sp.get("failed") == 0 and _current(sp, d)
    if pic.exists() and not good and not (sp.get("picture") == str(pic) and _current(sp, d)):
        good = not start_check(scene_dir, pic)["failed"]  # a picture there already, never checked against this rehearsal: checked (free)
    if not good and (_load(Path(scene_dir) / "take.json") or {}).get("compose"):
        # composed before the image model (compose_start.py): the plate and each person's piece, placed in code on the
        # rehearsal's own points, then one light pass; the picture model never lays anyone out
        import compose_start as CS
        try:
            good = CS.run(scene_dir)["ok"]
        except SystemExit as e:
            why = str(e)
    if not good:                                         # the scene's own filed print, staged from this rehearsal's
        good = _print_as_start(scene_dir, pic)           # layout and camera: the start picture as printed, no redraw
    while not good and n < tries:
        n += 1
        try:
            import motion_program as MP
            MP.first_frame(scene_dir, looks)             # makes it, then lays it over the rehearsal's first frame itself
            good = True
        except SystemExit as e:
            why = str(e)
    return {"ok": good, "picture": str(pic) if good else None,
            "held": [] if good else [why or "the start picture could not be made to match the rehearsal's first frame"], "tries": n}


def status(scene_dir):
    d = Path(scene_dir) / "motion"
    return {"stages": (_load(d / "chain.json") or {}).get("stages") or {},
            "matches": {f.stem.replace("match-", ""): {k: v for k, v in (_load(f) or {}).items() if k in ("passed", "failed", "open", "checked_at")}
                        for f in sorted(d.glob("match-*.json"))}}


def rows(production):
    """Every scene's chain as check rows, the shape a board draws (board.py, which a board may load on its own)."""
    import board as BD
    return BD.rows(production)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)

    def opts(k):
        return [a[i + 1] for i, x in enumerate(a) if x == k and i + 1 < len(a)]

    def opt(k, d=None):
        return (opts(k) or [d])[0]
    if a[0] == "run":
        spans = [tuple(float(x) for x in s.split("-")) for s in opts("--span")] or None
        take = _load(opt("--take")) if opt("--take") else None
        st = prepare(a[1], take, opt("--brand"), opt("--framemap"), opt("--source"), spans, opt("--clip"),
                     opt("--only").split(",") if opt("--only") else None)
        for k, s in st.items():
            print("%s  %-36s %s" % ({True: "✓", False: "✗", None: "…"}[s["ok"]], s["name"], s["short"]))
    elif a[0] == "who":
        st = who(a[1], dict(x.split("=", 1) for x in a[2:] if "=" in x and not x.startswith("--")), opt("--by"))
        for k, s in st.items():
            print("%s  %-36s %s" % ({True: "✓", False: "✗", None: "…"}[s["ok"]], s["name"], s["short"]))
    elif a[0] == "decide":
        won = decide(a[1])
        print(("passed" if won["ok"] else "passed by override (%s)" % won["by"]) if won["passed"] else "held: " + " · ".join(won["held"]))
        if won.get("picture"):
            print("start picture does not match: " + " · ".join(won["picture"]))
        sys.exit(0 if won["passed"] else 1)
    elif a[0] == "ours":
        rec = ours(a[1], model=opt("--model"))
        print(json.dumps({k: rec.get(k) for k in ("kind", "ours_because", "timing_from", "dropped", "notes")}, indent=1, ensure_ascii=False))
        won = decide(a[1])
        print("passed" if won["passed"] else "held: " + " · ".join(won["held"]))
    elif a[0] == "approve":
        print(json.dumps(approve(a[1], opt("--by"))["take_motion"], indent=1))
    elif a[0] == "check":
        rec = check(a[1], a[2] if len(a) > 2 and not a[2].startswith("--") else None, opt("--name", "take"))
        for r in rec["rows"]:
            print("%s  %-64s %s" % ({True: "✓", False: "✗", None: "–"}[r["ok"]], r["name"][:64], r["short"]))
        print("%d ✓  %d ✗" % (rec["passed"], rec["failed"]))
    elif a[0] == "frame-words":
        print(frame_words(a[1]))
    elif a[0] == "print-words":
        print(print_words(a[1]))
    elif a[0] == "start-check":
        rec = start_check(a[1], a[2] if len(a) > 2 and not a[2].startswith("--") else None)
        for r in rec["rows"]:
            print("%s  %-44s %s" % ({True: "✓", False: "✗", None: "–"}[r["ok"]], r["name"][:44], r["short"]))
        sys.exit(1 if rec["failed"] else 0)
    elif a[0] == "status":
        print(json.dumps(status(a[1]), indent=1, ensure_ascii=False))
    elif a[0] == "rows":
        print(json.dumps(rows(a[1]), indent=1, ensure_ascii=False))
    else:
        sys.exit(__doc__)
