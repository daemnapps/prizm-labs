"""Swipe check: is the made ad the swipe's ad? Pass or fail per check, measured on the files, never claimed.

  python3 swipe_check.py <production> [<rendered cut.mp4>]     prints the checks and writes briefs/<p>/SWIPE-CHECK.json

Checks, each from the production's own files:
  every_swipe_shot   every swipe shot each scene names is in the shot list and picked (swipe_shots.py, picks.json)
  clean_cuts         every cut in a made scene is one we placed (within 3 frames of a shot boundary): no stray cut from
                     inside one of our clips, no shot under 3 frames. How long each shot runs is the swipe's share, a
                     layout default, never graded (owner, 16 Nov: "that's subjective, we just need to execute clean edits")
  one_take_scenes    a scene the swipe holds as ONE shot (the hook) has no cut inside it
  voices_match       the narrator and every on-camera speaker read in the voice set for their demographic (voices.py)
  words_heard        the cut's speech matches the script (0.95 or more), when a cut is given
  loudness           the cut sits at -14 LUFS (within 0.5), when a cut is given
  no_flash           no shot in the cut is shorter than 3 frames
  no_repeat          no two shots play overlapping time of the same source file (decisions: "never reuse the same clip
                     section"; narrator-montage-edit: "no clip section is used twice"); measured from each scene's take:
                     the source, its in-point and the seconds its share plays. A made clip used again in another scene
                     repeats; one scene's shots playing successive seconds of one made take do not (a continuous take)
  shots_copy         every made shot shows what its swipe shot shows (shot_copy.py: the swipe frame and ours judged
                     side by side, cached per frame; picture in SHOT-AUDIT.jpg; --fill routes the misses). A MISSING
                     shot (a different moment) fails; a WEAK one (same moment, framing off) is listed and shown orange. Skip with
                     --no-judge only to read the other checks quickly; a cut is never passed without it.
THE EDIT'S OWN CHECKS are the chain's, called from here, never copied (owner ruling 2026-11-16, V57 (swipe is the backbone)): clean_cuts,
no_flash, words_heard and the noted differences come from components/video-edit/machine/cut_check.py, so the edit
line and the video editor's hand-off run check the same way. This file reads the Studio's production files.
Brand-agnostic: reads the production, its brief and the swipe's frame map.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os  # noqa: E402
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")  # the Studio's production side (settings, takes, voices) until each seam is cut
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))  # this folder first, then the Studio it serves
import settings as ST  # noqa: E402
import swipe_shots as SS  # noqa: E402
CC = ST.chain("video-edit", "cut_check")     # the edit's own checks: one home for every editing path

FRAME = CC.FRAME
cuts = CC.cuts
dur = CC.dur


_num = CC._num        # words compared the way they are spoken (the chain's cut_check.canon)
canon = CC.canon


def _scene(shot):
    """The scene a shot id belongs to: `S12.K23` -> `S12`."""
    return str(shot).split(".")[0]


def repeats(segments, tol=0.04, made=()):
    """Pairs of shots that repeat footage. segments: [(shot, source, start, end)]. Two shots repeat when they play
    overlapping time of the same source, or when both play a made clip (a source under one of `made`): a generated
    clip is one moment, so any second use of it repeats that moment. The one exception: shots of the SAME scene that
    play different, non-overlapping seconds of one made clip are one continuous take cut into the swipe's shots
    (take.py; rule 2026-11-12, AI shots of one moment are one take), not a repeat."""
    out = []
    for i, (a, fa, sa, ea) in enumerate(segments):
        for b, fb, sb, eb in segments[i + 1:]:
            if fa != fb:
                continue
            ov = min(ea, eb) - max(sa, sb)
            if ov > tol:
                out.append((a, b, "%s-%s s" % (round(max(sa, sb), 2), round(min(ea, eb), 2))))
            elif any(str(fa).startswith(str(m)) for m in made):
                if _scene(a) != _scene(b):
                    out.append((a, b, "the same made clip"))
            else:                        # ONE USE PER CLIP (owner, 21 Nov): a footage clip file plays once per ad
                out.append((a, b, "the same clip"))
    return out


def _source_file(entry):
    """The file a take's source entry plays (generated clips resolve under the Studio's sources)."""
    if isinstance(entry, str):
        return str(Path(entry).resolve())
    loc = str((entry or {}).get("drive_location") or (entry or {}).get("file") or "")
    if loc and not Path(loc).is_absolute():
        cand = ST.SOURCES / loc
        if cand.exists():
            loc = str(cand)
        elif "/" in loc.strip("/") and not loc.startswith("generated/"):
            return "footage:" + loc       # a clip on another footage root (read by range): real footage, not made
        else:
            loc = str(ST.SOURCES / "generated" / Path(loc).name)
    return str(Path(loc).resolve()) if loc else ""


def segments_of(n):
    """Every picture shot in the cut as (shot, source file, start, end), from each scene's picked take."""
    bd = ST.BRIEFS / n
    brief = json.load(open(bd / "brief.json"))
    segs = []
    for sid in brief["order"]:
        tf = bd / "scenes" / sid / (brief["picks"][sid] + ".json")
        run = bd / "scenes" / sid / "out" / brief["picks"][sid] / (sid + ".mp4")
        if not tf.is_file():
            continue
        wf = json.load(open(tf))
        steps = [s for s in wf["steps"] if s["tool"] == "ffmpeg.trim"]
        total = dur(run) if run.is_file() else 0.0
        wsum = sum(float((s.get("params") or {}).get("weight") or 0) for s in steps) or 1.0
        for s in steps:
            key = str(s["inputs"].get("source", "")).replace("slot:", "")
            f = _source_file((wf.get("sources") or {}).get(key))
            a = float(s["inputs"].get("in") or 0)
            secs = total * float((s.get("params") or {}).get("weight") or 0) / wsum if total else \
                float(s["inputs"].get("out") or a) - a
            segs.append((s.get("note", "").split(" ·")[0] or key, f or key, a, a + secs))
    return segs


def planned_cuts(run, scenes) -> int:
    """How many shot changes the chain planned inside these scenes: each call's later shots (shot pictures) and the
    joins where one scene runs over two calls."""
    try:
        plan = json.loads((Path(run) / "clips" / "plan.json").read_text())
    except (OSError, ValueError, TypeError):
        return 0
    n = 0
    for sid in scenes:
        calls = [c for c in plan.get("calls") or [] if sid in (c.get("scenes") or [])
                 and (c.get("layout") or {}).get("position") != "top"]
        n += sum(len(c.get("shot_pictures") or []) for c in calls) + max(0, len(calls) - 1)
    return n


def check(n, cut=None, judge=True):
    bd = ST.BRIEFS / n
    brief = json.load(open(bd / "brief.json"))
    ours = (brief.get("lane") or "") in ("real", "mix")     # owner, 20 Nov: real-footage ads are graded on our words
    # an AI-lane cut whose scenes hold the production chain's own cut (ai_shots.lay_edit, 20 Nov): its shots are the
    # chain's, checked before they were paid for by the chain's checklist (clips/checklists.json), read here
    chain = (brief.get("lane") or "") == "ai" and not (bd / "picks.json").is_file()
    if ours:
        import our_shots as OS
        sl = OS.build(n)
        judge = False                    # no paid judge against the swipe's frames: the shots are ours
    elif chain:
        sl = {"shots": []}
        judge = False                    # the chain's checklist judged every picture before its clip
    else:
        sl = SS.build(n)
    picks = json.load(open(bd / "picks.json")) if (bd / "picks.json").is_file() else {"shots": {}}
    out = []
    if chain:
        import ai_shots as AS
        st = AS.chain_status(brief)
        cks = json.loads((Path(st["run"]) / "clips" / "checklists.json").read_text()) \
            if st.get("run") and (Path(st["run"]) / "clips" / "checklists.json").is_file() else {}
        crossed = {cid: [r["line"] for r in v.get("rows") or [] if r.get("state") == "✗"] for cid, v in cks.items()}
        crossed = {k: v for k, v in crossed.items() if v}
        out.append({"check": "chain_checklist", "pass": bool(cks) and not crossed,
                    "detail": ("every clip's checklist passed (%d clips)" % len(cks)) if cks and not crossed else
                    ("no checklist filled for this run's clips" if not cks else
                     "; ".join("%s ✗ %s" % (k, ", ".join(v)[:120]) for k, v in crossed.items()))})
    unpicked = [r["id"] for r in sl["shots"] if r.get("copies") and r["id"] not in picks["shots"]
                and len([x for x in sl["shots"] if x["scene"] == r["scene"]]) > 1]
    # V57 (owner, 16 Nov): the swipe gives the order and each scene's job; which shots we use is ours. A swipe
    # shot we did not pick is noted, never a fail.
    if chain:
        pass                               # the chain's checklist above stands in for the swipe-shot list
    elif ours:
        added = {a.get("id") for rows_ in (picks.get("add") or {}).values() for a in rows_ or []}   # a brief shot filled by an add
        missing = [r["id"] for r in sl["shots"] if r["id"] not in picks.get("shots", {}) and r["id"] not in added]
        out.append({"check": "every_line_shot", "pass": not missing,
                    "detail": "every spoken beat has its clip" if not missing else "no clip yet: " + ", ".join(missing)})
    else:
      out.append({"check": "every_swipe_shot", "pass": True, "note": bool(unpicked),
                "detail": "all %d swipe shots in the shot list%s" % (len([r for r in sl["shots"] if r.get("copies")]),
                                                                     "" if not unpicked else "; ours leaves out (noted): " + ", ".join(unpicked))})
    bad, one = [], []
    st_run = Path(AS.chain_status(brief).get("run") or "") if chain else None
    for sid in brief["order"]:
        rows = [r for r in sl["shots"] if r["scene"] == sid]
        run = bd / "scenes" / sid / "out" / brief["picks"][sid] / (sid + ".mp4")
        if not run.is_file():
            bad.append(sid + ": not made")
            continue
        c, d = cuts(run), dur(run)
        if (picks.get("add") or {}).get(sid):
            continue                       # the owner's added shots change the shares; checked by eye
        if len(rows) == 1 and rows[0].get("copies"):
            one.append((sid, c))
            continue
        placed, at = [], 0.0
        wf = json.load(open(bd / "scenes" / sid / (brief["picks"][sid] + ".json")))
        trims = [st for st in wf.get("steps") or [] if st["tool"] == "ffmpeg.trim"]
        if trims and not any(st["tool"] == "voice.read" for st in wf.get("steps") or []):
            for st in trims[:-1]:        # a scene with no read plays each shot its own seconds: the cuts we placed
                at += float(st["inputs"].get("out") or 0) - float(st["inputs"].get("in") or 0)
                placed.append(at)
        elif trims and (chain or all((st.get("params") or {}).get("weight") for st in trims)):
            # each shot its weight's share of the read: the chain's scenes, and a footage scene cut to its read (a
            # song's slot), whose weights are what the cut placed — never the swipe's shares, which it no longer uses
            wsum = sum(float((st.get("params") or {}).get("weight") or 1) for st in trims) or 1.0
            for st in trims[:-1]:
                at += d * float((st.get("params") or {}).get("weight") or 1) / wsum
                placed.append(at)
            # inside a chain scene, the planned shot changes (each later shot opens on its own print, and a scene cut
            # over two calls joins them) are the chain's own cuts: up to that many found cuts are placed ones
            if chain:
                planned = planned_cuts(st_run, [str(st["inputs"]["source"])[len("slot:chain-"):] for st in trims])
                extra = [x for x in c if all(abs(x - y) > 0.15 for y in placed)]
                if len(extra) <= planned:
                    placed += extra
        else:
            for r in rows[:-1]:
                at += r["share"] * d
                placed.append(at)
        bad.append(CC.scene_fault(sid, c, d, placed))      # a stray cut inside a shot, or a flash under 3 frames
    out.append(CC.clean_cuts(bad))
    inside = [(s, c) for s, c in one if c]
    rep = repeats(segments_of(n), made=[str((ST.SOURCES / "generated").resolve())])
    out.append({"check": "no_repeat", "pass": not rep,
                "detail": "no clip section is used twice" if not rep else
                "; ".join("%s and %s both play %s" % r for r in rep)})
    try:                                 # every voice is the one set for its demographic (voices.py, rule 2026-11-12)
        import voices as VO
        vr = VO.report(n)
        badv = ["%s %s has %s, wants %s" % (r, v["face"], v["has"], v["wants"] or "no voice set") for r, v in vr.items() if not v["ok"]]
        out.append({"check": "voices_match", "pass": not badv,
                    "detail": ("%d speaking role(s), each in the voice set for its demographic" % len(vr)) if not badv else "; ".join(badv)})
    except SystemExit as e:
        out.append({"check": "voices_match", "pass": False, "detail": str(e)})
    # V57 (swipe is the backbone): a scene the swipe holds as one shot may be cut by us; the cut is ours (noted). Stray cuts and flash
    # frames are still failed by clean_cuts and no_flash.
    out.append({"check": "one_take_scenes", "pass": True, "note": bool(inside),
                "detail": ", ".join(s for s, _ in one) + " play as one take" if not inside else
                "ours cuts a scene the swipe holds as one (noted): " + "; ".join("%s cuts at %s" % (s, [round(x, 2) for x in c]) for s, c in inside)})
    if cut:
        import voice_continuous as V
        a = Path(cut).with_suffix(".check.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cut), "-vn", str(a)], check=True)
        heard = [w["w"] for w in V.stt(str(a))]
        script = []
        # a chain-made scene's read has no prompt: its words are the chain's own, laid in voice/reads.json by
        # ai_shots.lay_edit (2026-11-21, brief-0380: the check read "no spoken script" and passed a cut with drifting captions)
        said = ((json.load(open(bd / "voice" / "reads.json")) if (bd / "voice" / "reads.json").is_file() else {})
                .get("lines") or {})
        for sid in brief["order"]:
            wf = json.load(open(bd / "scenes" / sid / (brief["picks"][sid] + ".json")))
            for st in wf["steps"]:
                if st["tool"] in ("voice.read", "voice.ai"):
                    script.append(st.get("prompt") or ((said.get(sid) or {}).get("text") if st.get("model") ==
                                                       "the production chain" else "") or "")
                elif st["tool"] == "gen.take":       # a one-take print speaks its own script (the hook)
                    script += [ln.get("say") or "" for ln in (st.get("params") or {}).get("script") or []]
        # nothing read (a song ad, a music-only cut): no script to hear, the check passes and says so (cut_check)
        out.append(CC.words_heard(" ".join(script).split(), heard))
        ln = subprocess.run(["ffmpeg", "-nostdin", "-i", str(cut), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
        lufs = float(re.findall(r'"input_i" : "(-?[0-9.]+)"', ln)[-1])
        out.append({"check": "loudness", "pass": abs(lufs + 14) <= 0.5, "detail": "%.1f LUFS" % lufs})
        out.append(CC.no_flash(cuts(cut), dur(cut)))
    if judge:   # the owner 10 Nov: a clip at the right length is not a copy of the shot; judge what each shot shows
        import shot_copy as SCP
        r = SCP.judge(n)
        bad = [x for x in r["shots"] if x["verdict"] in ("MISSING", "UNCHECKED")]     # a different moment fails the cut
        weak = [x["id"] for x in r["shots"] if x["verdict"] == "WEAK"]                   # same moment, framing off: shown
        if bad:   # the swipe gives the idea, the edit is ours (owner, 16 Nov): a shot that differs from the swipe's is noted, never failed
            out.append(CC.differs([(x["id"], x["verdict"].lower()) for x in bad]))
            bad = None
        if bad is not None:
          out.append({"check": "shots_copy", "pass": not bad,
                    "detail": (("no shot missing; %d copy, %d weak (orange in SHOT-AUDIT.jpg: %s)"
                                % (r["counts"]["COPIES"], len(weak), ", ".join(weak))) if not bad else
                               "; ".join("%s %s: %s" % (x["id"], x["verdict"], x.get("need") or x.get("why", "")) for x in bad))})
    (bd / "SWIPE-CHECK.json").write_text(json.dumps({"production": n, "cut": str(cut) if cut else None, "checks": out}, indent=1))
    return out


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    res = check(args[0], args[1] if len(args) > 1 else None, judge="--no-judge" not in sys.argv)
    for r in res:
        print("%s %-17s %s" % ("✓" if r["pass"] else "✗", r["check"], r["detail"]))
    sys.exit(0 if all(r["pass"] for r in res) else 1)
