#!/usr/bin/env python3
"""One continuous take: a whole scene made as ONE clip (components/video-production/BRIEF-SPEC.md, "Continuous takes
and motion", ruled 2026-11-09).

Where the swipe holds one take, the scene is one call carrying:
  - the start picture (made by image production from the swipe's frame),
  - one short voice sample per speaker (the model speaks every line itself, in that voice),
  - the motion reference (camera, staging, body language): real footage of the same action, rehearsed in 3D by the
    motion chain (components/motion) and passed by its own checks before this call,
  - the whole script in order, each line with its speaker, and the camera, staging and body language in words.

    python3 take.py <take.json> [--dry-run]          make the take (every view, then the multi-cam cut)
    python3 take.py scene <scene dir> [--dry-run]     the scene in one go, nobody asked: motion (our beats on the
                                                      reference's timing and camera when the reference acts another
                                                      moment), the start picture from the 3D set print, the scene input
                                                      review page, the take, then its checks (faces, every beat on
                                                      screen, the real footage)
    python3 take.py variant <main scene dir> <name> <opening.json | "the new opening, in words"> [--picture <changed start>] [--seconds N] [--whole] [--keep-motion] [--look NAME="look with the change"] [--dry-run]
                                                      a variation: the main scene's start picture, motion, camera and
                                                      cast reused as made, only its opening element swapped (the start
                                                      picture with that one element changed through image production)
    python3 take.py voices [word]                     the voices we own (made from real speakers), by name
    python3 take.py hear "<voice name>" "a line" [out.mp3]   hear a voice say a line before it goes in a take
    python3 take.py check <take.json>                 read the finished take back (take_layers.py) and mark each beat
    python3 take.py lipsync <clip> <voice.mp3> [--model latentsync|sync|musetalk] [--out f.mp4]
                                                      the clip's face made to speak our read (a tracked take has no voices)

take.json:
  {"out": "take.mp4", "model": "<route to try first; none = the house order>", "backups": ["<route>", ...],  "seconds": 20,
   "picture": "start.png",
   "cast": {"HOST": "sheets/host.png", "RATER": "sheets/rater.png"},     every person's character sheet (keeps them ours)
   "speakers": {"HOST": ["reads/1.mp3", "reads/3.mp3"], "RATER": ["reads/2.mp3"]},
   "script": [{"speaker": "HOST", "say": "...", "do": "what the body does on this line", "read": "reads/1.mp3"}, ...],
   "staging": "who stands where and who moves where, in order",
   "motion": {"source": "swipe.mp4", "from": 0, "to": 10, "blur": [[x, y, w, h], ...]},
             or {"scene": "<scene folder>", "blur": [...]}: that scene's motion from the motion chain (real footage
             tracked, read, rehearsed in 3D), sent once it has passed the chain's own checks; held motion is never sent
   "look": "place, light and sound in one line"}

Controls (ruled 2026-11-09, BRIEF-SPEC rules 6-8):
  cast NAME: {"sheet": "sheets/x.png", "voice": "<a voice we own, by name>", "look": "what they wear and look like",
              "seen": [t, x, y]}
      voice  - every line of that character is read again in that voice (ElevenLabs, our own voices only); swap the
               name to swap the voice; `hear` plays it first
      body   - written per beat (`moves`, every route); or the whole scene acted out on a phone by people standing
               where the characters stand, tracked by motion.py and given as `motion`: the pose route copies it 1:1
  script line: {"moves": {"NAME": "what that body does on this beat"}, "faces": {"NAME": "<a face below>"},
                "camera": "what the camera does on this beat", "focus": "<a focus below, for this beat>"}
      faces  - one of FACES (smile, grin, laugh, disgust, unsure, surprise, bite-lip, flirty, deadpan, neutral); written
               into the prompt in the model's words and checked back off the take's face mesh (`check`)
  camera: {"move": "<a move below>", "angle": "<an angle>", "framing": "<a framing>", "focus": "<a focus>",
           "style": "<a style below; a handheld scene gets operator unless none>",
           "shots": [{"seconds": 5, "framing": "wide", "angle": "eye", "on": "the line-up"}, ...],      one take, cut inside
           "views": [{"name": "A", "framing": "wide"}, {"name": "B", "framing": "close", "on": "RATER"}],  multi-cam
           "cut": ["A", "B", "A", ...]}                                                              view per line
      move   - handheld-follow, push-in, pull-out, pan-left, pan-right, orbit, static, whip-pan
      focus  - rack (a phone lens: sharp on the speaker or the hands, background soft, focus moving), shallow, deep
      style  - operator (open wide, push in to the action, close on the speaker, wide for the laugh, in on the reaction)
      shots  - cuts inside one call, from a shot list in the prompt (Seedance 2.5, Wan 3.0)
      views  - the same moment made once per view, then cut together line by line on the take's own speech

Swipe words (2026-11-15): a take with its own beats takes only the swipe shots' camera and timing (shot_list), and
the prompt is read for the swipe's own words before every paid call (swipe_leaks): a person, action, face or on-screen
thing the swipe's shot map names that is not in our take stops the take with the words listed; `allow_words` on the
take lets one through on purpose.

Faces (2026-11-13, take_faces.py): the start picture must pass the face gate against the sheets of the people in it
(`in_picture`, default the whole cast) before anything is sent, and every beat of the made take is checked against the
people it names; a drifted take is kept as <out>.drift.mp4 and never used.

Routes, in the house order (components/generative-model-house, clips.take*): wan-start@higgsfield (the exact first frame;
the model speaks the lines and our reads are laid after), seedance@higgsfield (first frame + a voice sample per speaker
+ motion video), wan-ref@fal (reference mode), and vace-pose@fal (the motion clip's tracked poses drive our first frame).
A refusal or a failure moves the take to the next route; sent.json records every route tried and the one that made it.
Keys by name through the key loader. No brand, product or person is named here. Python 3.9.
"""
import json
import re
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

CAMERA = ("One continuous take shot on a phone held by a person on location: real handheld movement the whole time; the "
          "camera drifts, bobs and re-frames as the operator follows the action. No cuts, no tripod, no smooth glide.")
MOTION = ("Copy the camera movement, handheld shake, pacing and body language of the reference video; take nothing else "
          "from it (not its people, clothes, place or words). Its figures are stand-ins: take only how they move, never "
          "their build, proportions or shape; every person's body, height and weight are exactly their character sheet's.")
# A face per character per beat: the words the model is given, and what the face mesh must show for the beat to pass
# (take_layers.py values, 0-1). One list, so a brief's faces are always ones the take can be checked against.
FACES = {
    "neutral": ("a relaxed, neutral face", {}),
    "smile": ("a warm closed smile", {"smile": 0.35}),
    "grin": ("a wide toothy grin", {"smile": 0.5}),
    "laugh": ("laughing out loud, mouth open, eyes creased", {"smile": 0.45, "jaw_open": 0.2}),
    "disgust": ("wrinkles the nose and pulls a disgusted face", {"frown": 0.15}),
    "unsure": ("an unsure face, head tilted, lips pressed, brows up", {"brow_raise": 0.15}),
    "surprise": ("surprised, brows up and mouth open", {"brow_raise": 0.25, "jaw_open": 0.2}),
    "bite-lip": ("bites the lower lip, pleased", {"lip_bite": 0.2}),
    "flirty": ("a flirty half smile", {"smile": 0.3}),
    "deadpan": ("a flat deadpan face", {}),
}
MOVES = {
    "handheld-follow": "a phone held by an operator walking with the action: real handheld bob and drift, re-framing as it follows",
    "push-in": "the camera pushes in slowly toward the subject",
    "pull-out": "the camera pulls back slowly to reveal more of the scene",
    "pan-left": "the camera pans left to follow the action",
    "pan-right": "the camera pans right to follow the action",
    "orbit": "the camera arcs around the subjects",
    "static": "a locked-off camera on a tripod, no movement",
    "whip-pan": "a fast whip pan to the next subject",
}
ANGLES = {"eye": "at eye level", "low": "from a low angle looking up", "high": "from a high angle looking down",
          "over-shoulder": "over the shoulder of the person facing them", "pov": "from the point of view of a person in the scene"}
FRAMINGS = {"wide": "a wide shot of everyone", "medium": "a medium shot, waist up", "close": "a close-up",
            "two-shot": "a two-shot"}
# Focus (ruled 2026-11-09, from the camera look of a reference-mode print the house kept as its standard): a real phone
# lens, the subject sharp and the background soft, the focus moving with the action. Set for the scene (`camera.focus`) or on one line (`focus`); a handheld scene gets `rack` unless set.
FOCUS = {"rack": "a shallow depth of field like a real phone lens: whoever speaks or is touched is sharp and the "
                 "background falls soft; the focus moves to each new speaker and to the hands as they land",
         "shallow": "a shallow depth of field: the subject sharp, the background soft",
         "deep": "everything in focus, near and far"}
# How the operator shoots the whole scene. `operator` is the default for a handheld scene: open wide, push in to the
# action, close on the speaker, pull back wide for the laugh or reveal, push in on the reaction. `camera.style: "none"` leaves it out.
STYLES = {"operator": "Shot by a skilled phone operator: it opens wide on everyone, then pushes in fast to the action; "
                      "whoever speaks gets a close-up; it pulls back wide for the big laugh or reveal, then pushes in "
                      "close on the reaction. Real handheld energy, never static."}


def camera_words(cam, on=None, shot=False):
    """A camera setting in words: move, angle, framing and who it is on. A shot inside a cut names only what changes."""
    if not cam:
        return CAMERA
    if cam.get("directed"):
        # our own camera direction (production injection), shot by shot, hard cuts between
        at, out = 0.0, []
        for k, sh in enumerate(cam.get("shots") or [], 1):
            out.append("Shot %d (%g-%g s): %s" % (k, at, at + float(sh.get("seconds") or 0), str(sh.get("words") or "").rstrip(".")))
            at += float(sh.get("seconds") or 0)
        return "The camera, shot by shot, cut hard between shots:\n" + ".\n".join(out) + "."
    if cam.get("from_track"):
        # the camera was tracked off real footage (components/motion): it is said only as measured. No shot sizes, no
        # operator style, no focus pulls: written sizes made models invent push-ins (owner's review, 2026-11-12)
        return str(cam.get("move") or CAMERA)
    bits = [] if shot and not cam.get("move") else [MOVES.get(cam.get("move", "handheld-follow"), cam.get("move", ""))]
    if cam.get("framing"):
        bits.append(FRAMINGS.get(cam["framing"], cam["framing"]) + (f" on {cam.get('on') or on}" if (cam.get("on") or on) else ""))
    if cam.get("angle"):
        bits.append(ANGLES.get(cam["angle"], cam["angle"]))
    handheld = cam.get("move", "handheld-follow") == "handheld-follow"
    focus = cam.get("focus") or ("rack" if handheld and not shot else "")
    if focus:
        bits.append(FOCUS.get(focus, focus))
    words = ", ".join(b for b in bits if b)
    if shot:
        return words[:1].upper() + words[1:] + "."
    style = STYLES.get(cam.get("style") or ("operator" if handheld else ""), "")
    return ("Camera: " + words + (". One continuous take, no cuts." if not cam.get("shots") else ".")
            + (" " + style if style else ""))


# What each door takes (components/model-inputs/inputs/<model>.json): voice samples in total, the motion clip, and
# whether the motion clip counts against the output length.
DOORS = {
    # wan-vace-pose: an open model on fal driven by the motion clip's tracked poses (bodies, hands, faces), from our first
    # frame; it carries no voices (sound is laid after) and copies the clip's action exactly. fal's checker stays on unless
    # the fal account is authorised to turn it off. 16 fps, 4n+1 frames, at most 241.
    "wan-vace-pose": {"voice_total": 0, "voice_each": (0, 0), "motion_max": 15, "shared_30": False},
    "seedance-2.5": {"voice_total": 30, "voice_each": (2, 15), "motion_max": 15, "shared_30": False},
    "wan-3.0": {"voice_total": 15, "voice_each": (1, 15), "motion_max": 15, "shared_30": True},
}


def seconds_of(f) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def samples(speakers, work, door):
    """One voice sample per speaker, in speaker order: that speaker's reads joined, cut to fit the door's limits.
    The sample only teaches the voice; the model speaks every line itself."""
    lim = DOORS[door]
    each_cap = min(lim["voice_each"][1], lim["voice_total"] / max(1, len(speakers)))
    out = []
    for name, reads in speakers.items():
        f = Path(work) / f"voice-{name.lower().replace(' ', '-')}.mp3"
        ins = sum((["-i", str(r)] for r in reads), [])
        flt = "".join(f"[{i}]" for i in range(len(reads))) + f"concat=n={len(reads)}:v=0:a=1,atrim=0:{each_cap:.2f},apad=whole_dur={lim['voice_each'][0]}"
        subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", flt, "-b:a", "192k", str(f)], check=True)
        out.append((name, f))
    return out


def motion_clip(motion, seconds, work, door):
    """The swipe's seconds as the motion reference, its on-screen words and stickers blurred (`blur`: boxes as
    fractions of the frame), cut to what the door takes."""
    lim = DOORS[door]
    span = float(motion["to"]) - float(motion.get("from", 0))
    span = min(span, lim["motion_max"], (29 - seconds) if lim["shared_30"] else span)   # a second of margin: a clip measures a hair long
    if span < 2:
        return None
    f = Path(work) / "motion.mp4"
    boxes = motion.get("blur") or []
    if boxes:
        parts = [f"[0]split={len(boxes) + 1}[base]" + "".join(f"[b{i}]" for i in range(len(boxes)))]
        last = "base"
        for i, (x, y, w, h) in enumerate(boxes):
            parts.append(f"[b{i}]crop=iw*{w}:ih*{h}:iw*{x}:ih*{y},boxblur=25[c{i}]")
            parts.append(f"[{last}][c{i}]overlay=W*{x}:H*{y}[o{i}]")
            last = f"o{i}"
        vf = ["-filter_complex", ";".join(parts), "-map", f"[{last}]"]
    else:
        vf = []
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(motion.get("from", 0)), "-t", f"{span:.2f}",
                    "-i", str(motion["source"])] + vf + ["-an", "-c:v", "libx264", "-crf", "22", str(f)], check=True)
    return f


PRODUCT_WORDS = r"(?i)\b(?:the |a |an )?(?:evora |amber |yellow |brown |unbranded )*(?:body[- ]oil |oil |pump )*(?:pump )?bottle\b|\bbody oil\b"


def swipe_shots(take):
    """The swipe's own shots (video-teardown framemap) inside this take's motion window, with the window's start on the
    swipe's clock: ([shots], a0, a1), or ([], 0, 0) when the take's motion has no swipe behind it."""
    m = take.get("motion") or {}
    src, a0, a1 = m.get("source"), float(m.get("from") or 0), float(m.get("to") or 0)
    ref = Path(m["scene"]) / "motion" / "ref.json" if m.get("scene") else None
    if ref and ref.exists():
        r = json.loads(ref.read_text())
        span = (r.get("spans") or [{}])[0]
        base = float(span.get("from") or 0)
        src = r.get("source") or src
        a0, a1 = base + (a0 if m.get("segment") is not None else 0.0), base + (a1 if m.get("segment") is not None else float(r.get("seconds") or a1))
    if not src or not a1:
        return [], 0.0, 0.0
    fm = Path(os.path.realpath(src)).parent / "framemap" / "framemap.json"
    if not fm.exists():
        return [], 0.0, 0.0
    shots = [s for s in json.loads(fm.read_text()).get("shots") or [] if min(s["end"], a1) - max(s["start"], a0) > 0.25]
    return shots, a0, a1


LEAK_MIN = 4          # words shorter than this are never judged (articles, "her", "man")


def _words(text):
    import re
    return {w for w in re.findall(r"[a-z]+", str(text).lower()) if len(w) >= LEAK_MIN}


def swipe_leaks(take, text):
    """Words of the swipe that reached the prompt without being ours (2026-11-15: 'Blonde Woman ... sniffing', its
    product graphics and its men reached a hook take and the clip copied them). A word leaks when the swipe's shot map
    uses it for a person, an action, a face or what is on screen, the prompt carries it, and neither our take (its
    script, staging, cast, look; never the motion's own read of the swipe) nor this file's own fixed words nor the swipe's camera notes say it. Returns the
    sorted leaks; empty when the take has no swipe behind it."""
    shots, _, _ = swipe_shots(take)
    if not shots:
        return []
    theirs, camera = set(), set()
    for s in shots:
        mp = s.get("map") or {}
        camera |= _words(json.dumps(mp.get("camera") or {}))
        theirs |= _words(mp.get("start_frame")) | _words(mp.get("end_frame"))
        for mo in mp.get("moments") or []:
            theirs |= _words(mo.get("who")) | _words(mo.get("does")) | _words(mo.get("face"))
    ours = _words(json.dumps({k: take.get(k) for k in ("script", "staging", "cast", "look", "camera", "allow_words")}))
    return sorted((_words(text) & theirs) - ours - _fixed_words() - camera)


_FIXED = {}


def _fixed_words():
    """The words every prompt carries whatever the take (this file's own sentences): the prompt of a blank take."""
    if "w" not in _FIXED:
        blank = {"script": [{"speaker": "A", "say": "x", "do": "x", "faces": {"A": f}} for f in FACES] +
                 [{"speaker": "A", "say": "x", "who": "A", "action": "moves", "prop": "cup", "target": "B", "where": "here"}],
                 "cast": {"A": {"sheet": "a.png", "look": "x"}}, "doctrine": {"show": "x"}}
        got = set()
        for motion in (True, False):
            try:
                got |= _words(prompt(blank, [("A", "a.mp3")], motion))
            except Exception:     # noqa: BLE001 - a blank take the prompt cannot read just adds nothing
                pass
        _FIXED["w"] = got
    return _FIXED["w"]


def shot_list(take):
    """The swipe's own shots inside this take, each as a window: its framing and camera, what it opens and ends on, and
    every move and face the shot map read (video-teardown framemap). Swipe people become ours, the swipe's product
    becomes ours. This is the scene's shot-by-shot direction (SEEDANCE-INPUTS: one visible action per window, face and
    hands said per shot)."""
    import re
    shots, a0, a1 = swipe_shots(take)
    if not shots:
        return ""
    cast = [n for n in (take.get("cast") or {})]
    lead = next((n for n in cast if n not in ("HUSBAND", "HOTEL MANAGER", "MANAGER", "HOUSEKEEPER")), cast[0] if cast else "she")
    names = {"creator": lead.title(), "hotel manager": "the hotel manager", "manager": "the hotel manager",
             "husband": "her husband", "housekeeper": "the housekeeper"}
    product = (product_of(take) or {}).get("name") or "the product"

    def ours(t):
        t = re.sub(PRODUCT_WORDS, "the " + product + " tube", str(t or ""))
        for k, v in names.items():
            t = re.sub(r"(?i)\b" + k + r"\b(?: in outfit \d+)?", v, t)
        # what people wear and what the product looks like come from our pictures, never from the swipe's words
        t = re.sub(r"(?i)\s*\b(?:in|wearing) (?:a |an |her )?(?:[a-z-]+ ){0,4}(?:dress|shirt|blouse|cardigan|robe|suit|outfit|top|trousers|pants|sandals|jacket)(?: and (?:[a-z-]+ ){0,3}(?:sandals|shoes|earrings|trousers|pants))?\b", "", t)
        t = re.sub(r"(?i)\s*\b(?:of|with) (?:yellow|amber|golden|clear) (?:liquid|oil)\b", "", t).replace("clear the ", "the ")
        return re.sub(r"\s*\([^)]*\)", "", t).strip()
    # A take with its own beats (`do`) says what happens in our words; the swipe's shots then give only their timing
    # and camera. Their people, actions and on-screen graphics never reach the prompt (2026-11-15: a hook take sent
    # the swipe's "Blonde Woman ... sniffing", its product graphics and a different man per shot; the clip copied all
    # three over the take's own beats).
    if (take.get("camera") or {}).get("directed"):
        return ""                                   # our own camera direction replaces the swipe's shots entirely
    own_beats = any((ln or {}).get("do") or (ln or {}).get("action") for ln in take.get("script") or []) or \
        any(isinstance(b, dict) and (b.get("action") or b.get("do")) for b in take.get("beats") or [])
    out = []
    for k, s in enumerate(shots, 1):
        mp, cam = s.get("map") or {}, (s.get("map") or {}).get("camera") or {}
        a, b = max(0.0, s["start"] - a0), min(a1, s["end"]) - a0
        frame = ", ".join(x for x in (cam.get("distance"), cam.get("height"), cam.get("held"), cam.get("move")) if x and x != "none")
        if own_beats:
            out.append(f"Shot {k} ({a:.1f}-{b:.1f} s): camera {frame or 'as in the motion reference'}.")
            continue
        line = f"Shot {k} ({a:.1f}-{b:.1f} s), {frame}: opens on {ours(mp.get('start_frame')).rstrip('.')}; ends on {ours(mp.get('end_frame')).rstrip('.')}."
        for mo in mp.get("moments") or []:
            line += f" At {max(0.0, float(mo.get('t') or 0) + s['start'] - a0):.1f} s {ours(mo.get('who'))} {ours(mo.get('does')).rstrip('.')}" + (f"; face and hands: {ours(mo.get('face')).rstrip('.')}" if mo.get("face") else "") + "."
        out.append(line)
    head = ("The camera, shot by shot (what happens is in the beats below):\n" if own_beats else
            "The take, shot by shot, cut exactly at these times:\n")
    return (head + "\n".join(out)) if out else ""


def _mc():
    home = str(ST.part("motion"))
    if home not in sys.path:
        sys.path.insert(0, home)
    import motion_chain as MC
    return MC


def beat_words(ln, k):
    """One beat in words: who does what (its fields: who, action, prop, target, where; else its `do`), each body's
    move, each face, the camera, then the line."""
    act = _mc().beat_action(ln)
    bits = [act.rstrip(".") + "." if act else ""]
    for who, mv in (ln.get("moves") or {}).items():
        bits.append(f"{who} {mv.rstrip('.')}.")
    for who, fc in (ln.get("faces") or {}).items():
        bits.append(f"{who}'s face: {FACES.get(fc, (fc, {}))[0]}.")
    if ln.get("camera"):
        bits.append(f"Camera: {ln['camera'].rstrip('.')}.")
    if ln.get("focus"):
        bits.append(f"Focus: {FOCUS.get(ln['focus'], ln['focus']).rstrip('.')}.")
    lips = ln.get("lips", "on")                       # BRIEF-SPEC rule 9: the picture's own relation to the voice
    if not ln.get("say"):
        say = ""
    elif lips == "mime":
        say = f" {ln.get('mouthed_by') or 'The person on screen'} mouths these words with no sound: \"{ln['say']}\""
    elif lips == "off":
        say = " (her words here are voice-over, laid on afterwards: lips stay closed)"   # never typed: typed lines burn in subtitles
    else:
        say = f" {ln['speaker']}: \"{ln['say']}\""
    return f"{k}. " + " ".join(b for b in bits if b) + say


def speaking(take):
    """The speakers who say a line on screen (lips on). Voice-over and mimed lines put no voice into the take."""
    on = {ln.get("speaker") for ln in take.get("script") or [] if ln.get("say") and ln.get("lips", "on") == "on"}
    return {n: v for n, v in (take.get("speakers") or {}).items() if n in on}


def prompt(take, voices, with_motion, view=None, own_voices=False):
    audio = {name: i for i, (name, _) in enumerate(voices, 1)}
    who = ", ".join(f"Audio {i} is the voice of {name}" for name, i in audio.items())
    cast = {n: (c if isinstance(c, dict) else {"sheet": c}) for n, c in (take.get("cast") or {}).items()}
    cam = dict(take.get("camera") or {})
    if view and not cam.get("from_track"):
        cam.update({k: v for k, v in view.items() if k != "name"})
    import take_beats as TB
    script = take["script"]
    if not any(ln.get("action") or ln.get("do") for ln in script) and TB.beats_of(take):
        # the brief's discrete beats carry the action; the script carries only the speech, laid on afterwards in order
        lines = [beat_words(dict(b, say=""), k) for k, b in enumerate(TB.beats_of(take), 1)]
        spoken = [f'{ln["speaker"]}: "{ln["say"]}"' for ln in script if ln.get("say") and ln.get("lips", "on") == "on"]
        if spoken:
            lines.append("Spoken, in this order, over those beats: " + " ".join(spoken))
    else:
        lines = [beat_words(ln, k) for k, ln in enumerate(script, 1)]
    shots = ""
    if cam.get("shots") and not cam.get("directed"):
        at, out = 0.0, []
        for k, sh in enumerate(cam["shots"], 1):
            out.append(f"Shot {k} ({at:g}-{at + sh['seconds']:g} s): {camera_words(sh, sh.get('on'), shot=True)}")
            at += sh["seconds"]
        shots = "The take cuts between these shots of the same moment:\n" + "\n".join(out)
    return "\n".join(x for x in [
        camera_words(cam) if (cam or view) else CAMERA,
        shots,
        shot_list(take),
        MOTION if with_motion else "",
        "The people, clothes, place and light are exactly those of the reference picture.",
        sheet_words(cast),
        (lambda pr, k: (f"Then picture {k} is the product, {pr['name']}: wherever it appears it looks exactly like that "
                        "picture, same shape, colour, cap and label, the same size in a hand; never another tube, bottle "
                        "or label.") if pr else "")(product_of(take), 2 + sum(1 for c in cast.values() if c.get("sheet"))),
        " ".join(f"{n}: {c['look'].rstrip('.')}." for n, c in cast.items() if c.get("look")),
        take.get("staging", ""),
        # the marketing doctrine's moment (video-writing doctrine_tags.py): the feeling this scene exists to create, turned up
        # the doctrine's moment as faces and hands only (an emotion word makes Seedance overact: SEEDANCE-INPUTS)
        (("Faces and hands, turned up but real: " + take["doctrine"]["show"].rstrip(".") + ".")
         if (take.get("doctrine") or {}).get("show") else ""),
        ((f"{who}; each speaks only their own lines, lips matching every word." if who else
          "Each person speaks only their own lines, lips matching every word." if own_voices else "")
         if any(ln.get("lips", "on") == "on" for ln in take["script"] if ln.get("say")) else
         "No one on screen speaks: the voice is laid over afterwards. Mouths stay closed, except where a line says "
         "someone mouths words.") + " Real body language on every line.",
        "In order:\n" + "\n".join(lines),
        # the motion read (components/motion): how real people do this moment, measured off real footage
        ("How the bodies move, as real people do it, by the second:\n" + "\n".join(take["mechanics"])) if take.get("mechanics") else "",
        (take.get("look") or "") + " No music, no text on screen.",
    ] if x)


def product_of(take):
    """The product picture the clip must show, or None: the take's own `product` ({"picture", "name"}), else the one its
    scene's start picture was made with (motion/first-frame.json). The video model gets it as a reference after the
    character sheets, so the product looks the same in every frame and every take (the start picture alone drifts)."""
    pr = take.get("product")
    if isinstance(pr, dict) and pr.get("picture") and Path(pr["picture"]).exists():
        return {"picture": str(pr["picture"]), "name": pr.get("name") or Path(pr["picture"]).parent.name}
    scene = (take.get("motion") or {}).get("scene")
    if not scene:
        return None
    try:
        ff = json.loads((Path(scene) / "motion" / "first-frame.json").read_text())
    except (OSError, ValueError):
        return None
    pid = ff.get("product")
    pic = next((r for r in ff.get("references") or [] if pid and f"/products/{pid}/" in r and Path(r).exists()), None)
    return {"picture": pic, "name": pid.replace("-", " ")} if pic else None


def sheet_words(cast):
    """Which reference picture is whose sheet: the pictures go in as the start picture, then each sheet in cast order."""
    named = [n for n, c in cast.items() if c.get("sheet")]
    if not named:
        return ""
    return ("After the first reference picture come the character sheets, one per person, in this order: "
            + ", ".join(f"picture {k} is {n}" for k, n in enumerate(named, 2))
            + ". Each person looks exactly like their own sheet in every frame: same face, hair, skin and build.")


def wan_words(text, take, with_motion):
    """The house prompt in Wan 3.0 reference mode's own terms: it addresses its media by position ("Image 1",
    "Video 1", fal's schema), so every "reference picture", "picture N" and "motion reference" is named that way, and
    each cut is listed as a shot that starts on its own framing. Image 1 is never called the first or opening frame: in
    reference mode no frame travels with the references and the opening is rebuilt from them, so calling it a frame
    lets the model paste it in as the opening (Wan 3.0 rulebook, components/model-inputs/inputs/wan-3.0.json, avoid list,
    2026-11-27). It is named for what it gives: the place, the people and where they stand, and the framing."""
    import re
    t = text.replace("After the first reference picture come the character sheets, one per person, in this order: ",
                     "Then come the character sheets, one per person: ")
    t = re.sub(r"\bpicture (\d+) is ", r"Image \1 is ", t)
    t = t.replace("the reference picture", "Image 1").replace("the reference video", "Video 1")
    t = t.replace("the motion reference", "Video 1").replace("the reference's own framings", "Video 1's own framings")
    head = ["Image 1 is the scene's start picture: use it only for the place, the people and where each one stands, and "
            "the camera's framing; it is a reference, not a frame of the video."]
    if with_motion:
        head.append("Video 1 is a motion guide acted by plain wooden stand-ins: follow its camera, its cuts, its timing "
                    "and how each body moves; take nothing else from it.")
        m = take.get("motion") or {}
        try:
            ref = json.loads((Path(m["scene"]) / "motion" / "ref.json").read_text()) if m.get("scene") else {}
        except (OSError, ValueError):
            ref = {}
        a0, a1 = float(m.get("from") or 0.0), float(m.get("to") or 1e9)   # this part's own clock on a long scene
        cuts = [round(float(c) - a0, 2) for c in ref.get("cuts") or [] if a0 + 0.2 < float(c) < a1 - 0.2]
        if cuts:
            at = [0.0] + cuts
            head.append("It is cut as Video 1 is cut: " + "; ".join(
                f"shot {k} from {a:g} s" for k, a in enumerate(at, 1)) + ".")
    return "\n".join(head) + "\n" + t


# --- voices: only the ones we own, picked by name (components/video-production/machine/make_voice.py makes them) ---
def _eleven(path, body=None):
    sys.path.insert(0, str(ST.part("keys")))
    import loader
    h = {"xi-api-key": loader.key("ELEVENLABS_API_KEY"), "Content-Type": "application/json"}
    r = urllib.request.Request("https://api.elevenlabs.io" + path, data=json.dumps(body).encode() if body is not None else None,
                               headers=h, method="POST" if body is not None else "GET")
    return urllib.request.urlopen(r, timeout=300)


def voices(word=None):
    """The voices on our account that were made from real speakers (designed from a recording, or cloned), by name."""
    out, token = [], None
    while True:
        q = "/v2/voices?page_size=100&voice_type=personal" + (f"&next_page_token={token}" if token else "")
        d = json.load(_eleven(q))
        for v in d.get("voices", []):
            if v.get("category") in ("generated", "cloned", "professional"):
                out.append({"name": v["name"], "voice_id": v["voice_id"], "kind": v.get("category"),
                            "about": (v.get("description") or "")[:140]})
        token = d.get("next_page_token")
        if not d.get("has_more") or not token:
            break
    return [v for v in out if not word or word.lower() in v["name"].lower()]


def voice_id(name):
    """A voice by name: exact first, then the one name that contains it. Refuses a name that is no one's or several.
    A voice id itself (20 letters and digits) is returned as it is."""
    if re.fullmatch(r"[A-Za-z0-9]{20}", str(name or "")):
        return name
    vs = voices()
    hit = [v for v in vs if v["name"].lower() == name.lower()] or [v for v in vs if name.lower() in v["name"].lower()]
    if len(hit) != 1:
        raise SystemExit(f"voice {name!r}: {'no voice we own has that name' if not hit else 'several match: ' + ', '.join(v['name'] for v in hit)}")
    return hit[0]["voice_id"]


def say(vid, text, out, settings=None):
    body = {"text": text, "model_id": "eleven_v3", "apply_text_normalization": "off"}
    if settings:
        body["voice_settings"] = settings
    Path(out).write_bytes(_eleven(f"/v1/text-to-speech/{vid}?output_format=mp3_44100_192", body).read())
    return out


def reread(take, work):
    """Every line of a character with a `voice` is read again in that voice (cached per voice and words), and the
    take's speakers and reads point at the new files. With `mic` on the take or the cast member
    ({"place": "beach", "kind": "handheld"}), each read is then placed on that mic in that place (mic_place.py)."""
    import hashlib
    # a cast member's voice: `voice_id` (set from the brand's voice list by voices.py, rule 2026-11-12: every voice
    # matches the demographic on screen) or `voice` (a voice we made, by name)
    cast = {n: c for n, c in (take.get("cast") or {}).items() if isinstance(c, dict) and (c.get("voice_id") or c.get("voice"))}
    if not cast:
        return take
    d = Path(work) / "reads"
    d.mkdir(parents=True, exist_ok=True)
    ids = {n: c.get("voice_id") or voice_id(c["voice"]) for n, c in cast.items()}
    take = json.loads(json.dumps(take))
    for k, ln in enumerate(take["script"], 1):
        n = ln["speaker"]
        if n in ids and ln.get("say"):
            # mic: the read placed on a clean mic in the scene's place (mic_place.py); the clean read stays in reads/clean/
            mic = cast[n].get("mic") or take.get("mic")
            stem = f"{n.lower().replace(' ', '-')}-{k}-" + hashlib.sha1(f"{ids[n]}|{ln['say']}".encode()).hexdigest()[:10]
            clean = (d / "clean" / f"{stem}.mp3") if mic else (d / f"{stem}.mp3")
            if not clean.exists():
                clean.parent.mkdir(parents=True, exist_ok=True)
                say(ids[n], ln["say"], clean, cast[n].get("settings"))
            f = clean
            if mic:
                import mic_place
                f = d / f"{stem}-{mic.get('place', 'beach')}-{mic.get('kind', 'handheld')}.mp3"
                if not f.exists():
                    mic_place.place(clean, f, **{x: mic[x] for x in ("place", "kind", "bed", "bed_db") if x in mic})
            ln["read"] = str(f)
    speakers = {}
    for ln in take["script"]:
        if ln.get("read"):
            speakers.setdefault(ln["speaker"], []).append(ln["read"])
    take["speakers"] = {n: speakers.get(n, v) for n, v in (take.get("speakers") or speakers).items()}
    for n in speakers:
        take["speakers"].setdefault(n, speakers[n])
    take["voices"] = {n: {"name": cast[n].get("voice_name") or cast[n].get("voice") or ids[n], "voice_id": ids[n]} for n in cast}
    return take


def _fal(endpoint, body):
    sys.path.insert(0, str(ST.part("keys")))
    import loader
    h = {"Authorization": "Key " + loader.key("FAL_KEY"), "Content-Type": "application/json"}

    def call(url, data=None):
        r = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=h,
                                   method="POST" if data is not None else "GET")
        try:
            return json.load(urllib.request.urlopen(r, timeout=120))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"fal {e.code}: {e.read().decode()[:400]}")

    def up(path):
        ctype = {".png": "image/png", ".jpg": "image/jpeg", ".mp3": "audio/mpeg", ".mp4": "video/mp4"}[Path(path).suffix]
        i = call("https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3",
                 {"content_type": ctype, "file_name": Path(path).name})
        urllib.request.urlopen(urllib.request.Request(i["upload_url"], data=Path(path).read_bytes(),
                                                      headers={"Content-Type": ctype}, method="PUT"), timeout=300)
        return i["file_url"]

    body = {k: ([up(x) for x in v] if k.endswith("_urls") else v) for k, v in body.items()}
    body = {k: (up(v[0]) if k.endswith("_url") and isinstance(v, list) else v) for k, v in body.items()}
    job = call(f"https://queue.fal.run/{endpoint}", body)
    while True:
        st = call(job["status_url"])
        if st.get("status") == "COMPLETED":
            return job, call(job["response_url"])
        if st.get("status") not in ("IN_QUEUE", "IN_PROGRESS"):
            raise RuntimeError(f"fal ended {st}")
        time.sleep(15)


HF = "/opt/homebrew/bin/higgsfield"
REFUSED = ("nsfw", "moderat", "content_policy", "content checker", "flagged", "safety", "not allowed")
# The route order lives in the Generative Model House (components/generative-model-house/models.json, clips.take*):
# the first route makes the take; a refusal or failure moves to the next one, and the take records which route made it.
HOUSE_ROUTES = ["clips.take", "clips.take_backup", "clips.take_backup_open"]
ROUTE_OF = {("wan-3.0", "higgsfield"): "wan-start@higgsfield", ("seedance-2.5", "higgsfield"): "seedance@higgsfield",
            ("wan-3.0", "fal"): "wan-ref@fal", ("wan-2.2-vace-fun-pose", "fal"): "vace-pose@fal"}
ALIASES = {"seedance-2.5": "seedance@higgsfield", "wan-3.0": "wan-ref@fal", "wan-vace-pose": "vace-pose@fal"}
DOOR = {"wan-start@higgsfield": "wan-3.0", "wan-ref@fal": "wan-3.0", "seedance@higgsfield": "seedance-2.5",
        "vace-pose@fal": "wan-vace-pose"}
# the cost of a take per second at 480p: plan credits on the Higgsfield CLI, dollars elsewhere (model-inputs, 2026-11-09)
COST = {"wan-start@higgsfield": (1, "credits"), "seedance@higgsfield": (3, "credits"),
        "wan-ref@fal": (0.05, "usd"), "vace-pose@fal": (0.15, "usd")}
OWN_VOICES = {"wan-start@higgsfield", "vace-pose@fal"}      # these speak with the model's own voices (or none): our reads are laid after


class Refused(RuntimeError):
    """A route said no (a content filter, a moderation flag) or failed: the next route takes the work."""


def house_routes():
    try:
        sys.path.insert(0, str(ST.part("generative-model-house")))
        import model_house as MH
        out = []
        for job in HOUSE_ROUTES:
            row = MH._row(job)
            rid = row["registry"] if isinstance(row["registry"], str) else row["registry"][0]
            r = ROUTE_OF.get((rid, row.get("door")))
            if r and r not in out:
                out.append(r)
        return out or ["seedance@higgsfield", "wan-start@higgsfield", "wan-ref@fal"]
    except Exception:  # noqa: BLE001  a copy of the tools without the house still has the ruled order
        return ["seedance@higgsfield", "wan-start@higgsfield", "wan-ref@fal"]


def guard(job_type, args):
    """The house's spend guard before a paid take (generative-model-house/spend.py, 2026-11-25): its size, every file
    there, the words, and never the same request twice. Returns (spend, fingerprint); a copy of the tools without the
    house has no guard to ask: (None, None)."""
    import importlib.util as iu
    f = Path(str(ST.part("generative-model-house"))) / "spend.py"
    if not f.is_file():
        return None, None
    spec = iu.spec_from_file_location("gmh_spend", str(f))
    sp = iu.module_from_spec(spec)
    spec.loader.exec_module(sp)
    flags = list(zip(args[::2], args[1::2]))
    files = [v for k, v in flags if k in ("--start-image", "--end-image", "--image-references", "--audio-references", "--video-references")]
    said = {k.lstrip("-"): v for k, v in flags if v not in files}
    sp.check(job_type, said)
    sp.inputs(said.get("prompt"), files)
    return sp, sp.once(job_type, said, files)


def _hf(job_type, args, out):
    """One take through the Higgsfield command line (the signed-in plan's credits): create, wait, download."""
    sp, fp = guard(job_type, args)
    r = subprocess.run([HF, "--json", "generate", "create", job_type] + args, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        msg = (r.stderr or r.stdout).strip()[:400]
        raise (Refused if any(w in msg.lower() for w in REFUSED) else RuntimeError)(f"higgsfield {job_type}: {msg}")
    ids = json.loads(r.stdout or "null")
    job = ids[0] if isinstance(ids, list) else (ids or {}).get("id")
    if sp:
        sp.record(job_type, fp, str(job), out)
    w = subprocess.run([HF, "--json", "generate", "wait", str(job)], capture_output=True, text=True, timeout=3600)
    body = json.loads(w.stdout or "{}")
    state = str(body.get("status", "")).lower()
    if state != "completed" or not body.get("result_url"):
        raise Refused(f"higgsfield {job_type} ended '{state}' (job {job})")
    urllib.request.urlretrieve(body["result_url"], out)
    return job, body["result_url"]


def lay(take_file, script, out):
    """Our reads laid where the take speaks each line (a route that speaks in its own voices): each line's first words
    are found in the take's own speech, the read is placed there (sped up at most 1.35x to fit before the next line),
    and the take's own sound stays low underneath."""
    import re
    import voice_continuous as V

    def norm(w):
        w = re.sub(r"[^a-z]", "", w.lower())
        return "mm" if re.fullmatch(r"m+h?m*", w or "x") else w
    a = Path(take_file).with_suffix(".heard.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(take_file), "-vn", str(a)], check=True)
    words = V.stt(str(a))
    ws = [norm(w["w"]) for w in words]
    starts, k = [], 0
    for ln in script:
        first = [norm(x) for x in ln["say"].split()][:2]
        j = next((i for i in range(k, len(ws) - 1) if ws[i] == first[0] and (len(first) < 2 or ws[i + 1] == first[1])), None)
        if j is None:
            j = next((i for i in range(k, len(ws)) if ws[i] == first[0]), None)
        starts.append(words[j]["start"] if j is not None else None)
        k = j + 1 if j is not None else k
    total = seconds_of(take_file)
    ins, filt, mix, n, placed = ["-i", str(take_file)], ["[0:a]volume=0.12[bed]"], ["[bed]"], 1, []
    for i, (ln, st) in enumerate(zip(script, starts)):
        if st is None or not ln.get("read"):
            placed.append(None)
            continue
        nxt = next((x for x in starts[i + 1:] if x is not None), total)
        tempo = min(1.35, max(1.0, seconds_of(ln["read"]) / max(0.4, nxt - st - 0.05)))
        ms = int(st * 1000)
        ins += ["-i", str(ln["read"])]
        filt.append(f"[{n}:a]atempo={tempo:.2f},adelay={ms}|{ms}[v{n}]")
        mix.append(f"[v{n}]")
        n += 1
        placed.append({"say": ln["say"], "at": round(st, 2), "tempo": round(tempo, 2)})
    filt.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0,loudnorm=I=-16:TP=-1.5[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    return placed


def _route(route, take, work, secs, text, voices, mclip, raw):
    pic = take["picture"]
    cast = [c.get("sheet") if isinstance(c, dict) else c for c in (take.get("cast") or {}).values()]
    cast = [c for c in cast if c]                 # character sheets only: a cast entry may carry just a voice and a look
    pr = product_of(take)
    if pr and route != "wan-start@higgsfield":
        cast = cast + [pr["picture"]]             # the product picture rides after the sheets, as the prompt numbers it
    if route == "wan-start@higgsfield":
        # the exact first frame; a start picture cannot ride with references on this model, so it speaks the lines in
        # its own voices and ours are laid after
        args = ["--prompt", text, "--start-image", str(pic), "--duration", str(secs), "--resolution", "480p",
                "--aspect_ratio", "9:16", "--generate_audio", "true", "--enable_thinking", "true"]
        return _hf("wan3_0", args, raw)
    if route == "seedance@higgsfield":
        # the default print (2026-11-09): the picture rides as an image reference, first, so Seedance rebuilds the first
        # frame from it; `start_exact` asks for it as the exact start frame instead (Seedance refuses a swimwear start frame)
        first = ["--start-image", str(pic)] if take.get("start_exact") else ["--image-references", str(pic)]
        # which Seedance: 2.5 (omni_reference, the default), 2.0 (`seedance_mode` std or fast) or 2.0 mini (no mode)
        job = take.get("seedance_job") or "seedance_2_5"
        mode = (["--mode", "omni_reference"] if job == "seedance_2_5" else
                ["--mode", take.get("seedance_mode") or "fast"] if job == "seedance_2_0" else [])
        args = ["--prompt", text] + mode + first + ["--duration", str(secs),
                "--resolution", "480p", "--aspect_ratio", "9:16", "--generate_audio", "true"]
        for c in cast:
            args += ["--image-references", str(c)]
        for _, v in voices:
            args += ["--audio-references", str(v)]
        if mclip:
            args += ["--video-references", str(mclip)]
        return _hf(job, args, raw)
    if route == "wan-ref@fal":
        body = {"prompt": text, "reference_image_urls": [pic] + cast[:9], "reference_audio_urls": [str(v) for _, v in voices],
                "resolution": "480p", "aspect_ratio": "9:16", "duration": secs, "enable_safety_checker": False,
                "enable_thinking": True, "audio": bool(voices)}   # voice-over takes come back silent: no invented mouths or sound
        if mclip:
            body["reference_video_urls"] = [str(mclip)]
        try:
            job, res = _fal("alibaba/wan-3.0/reference-to-video", body)
        except RuntimeError as e:
            raise Refused(str(e))
        url = (res.get("video") or {}).get("url")
        if not url:
            raise Refused(f"fal answered with no video: {str(res)[:200]}")
        urllib.request.urlretrieve(url, raw)
        return job.get("request_id"), url
    if route == "vace-pose@fal":
        # programmed motion (components/motion/motion_program.py) carries its exact skeleton video as `motion.pose`: it goes in as the
        # poses themselves (OpenPose colours, preprocess off), so the model never re-detects people from stand-ins
        skel = (take.get("motion") or {}).get("pose")
        src = Path(skel) if skel and Path(skel).exists() else mclip
        if not src:
            raise Refused("the pose route needs `motion`: the clip (or the skeleton video) whose poses drive the take")
        pose = work / "pose-16fps.mp4"
        n = int(min(241, seconds_of(src) * 16, secs * 16)) // 4 * 4 + 1
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "fps=16", "-frames:v", str(n), "-an",
                        "-c:v", "libx264", "-crf", "20", str(pose)], check=True)
        body = {"prompt": text, "video_url": [str(pose)], "first_frame_url": [pic], "ref_image_urls": [pic] + cast[:9],
                "preprocess": not (skel and src == Path(skel)), "match_input_num_frames": True, "match_input_frames_per_second": True,
                "resolution": "480p", "aspect_ratio": "9:16", "enable_safety_checker": False, "enable_prompt_expansion": False,
                "negative_prompt": "text, captions, logos, flash, still camera, extra people, changed clothes"}
        try:
            job, res = _fal("fal-ai/wan-22-vace-fun-a14b/pose", body)
        except RuntimeError as e:
            raise Refused(str(e))
        url = (res.get("video") or {}).get("url")
        if not url:
            raise Refused(f"fal answered with no video: {str(res)[:200]}")
        urllib.request.urlretrieve(url, raw)
        return job.get("request_id"), url
    raise SystemExit(f"no take route {route!r}: {', '.join(sorted(set(ROUTE_OF.values())))}")


def cost(route, secs):
    per, unit = COST.get(route, (0, "?"))
    return {"amount": round(per * secs, 2), "unit": unit}


def one(take, routes, out, secs, dry_run=False, view=None):
    """One take of the scene (one camera view): the first route that does not refuse makes it."""
    work = out.with_suffix("")
    work.mkdir(parents=True, exist_ok=True)
    tried = []
    import take_beats as TB                        # every beat says who does what, as fields, before anything is bought
    beat_gaps = TB.gaps(take)
    stops = [g for g in beat_gaps if g["stop"]]
    if stops and not dry_run and TB.on("fields"):
        raise SystemExit("no take made: beats are not written out: %s. Give every beat its who and action (and its prop, "
                         "target and where when it has them); nothing was sent or spent." % "; ".join(
                             "beat %d: %s" % (g["beat"], g["why"]) for g in stops))
    if not dry_run:
        import take_faces as TF                    # the start picture's people are their sheets, before anything is bought
        TF.gate_picture(take)
        _mc()
        import compose_start as CS                 # and the video model's content filter would take it (2026-11-15: a
        safe = CS.safe_for_video(take["picture"])  # take refused as nsfw from its start picture)
        if safe.get("safe") is False:
            raise SystemExit("no take made: the video model would refuse this start picture (%s); remake it covered. "
                             "Nothing was sent or spent." % (safe.get("why") or "content filter"))
    for route in routes:
        door = DOOR.get(route, "wan-3.0")
        talkers = speaking(take)                     # only lips-on speakers send a voice sample
        voices = samples(talkers, work, door) if DOORS[door]["voice_total"] and talkers and route != "wan-start@higgsfield" else []
        wants_motion = route in ("seedance@higgsfield", "wan-ref@fal", "vace-pose@fal")
        mclip = motion_clip(take["motion"], secs, work, door) if take.get("motion") and take["motion"].get("source") and wants_motion else None
        text = prompt(take, voices, mclip is not None, view=view, own_voices=route in OWN_VOICES)
        leaks = swipe_leaks(take, text)       # the last stop before a paid call: nothing of the swipe's but its camera
        if leaks and not dry_run:
            raise SystemExit("no take made: the prompt carries the swipe's own words, not ours: %s. Say what happens in "
                             "the take's beats (or list a word the take means on purpose in `allow_words`); nothing "
                             "was sent or spent." % ", ".join(leaks))
        if route == "wan-ref@fal":
            text = wan_words(text, take, mclip is not None)
        sent = {"route": route, "seconds": secs, "picture": str(take["picture"]), "voices": [str(v) for _, v in voices],
                "cast_voices": take.get("voices"), "motion": str(mclip) if mclip else None, "view": view, "prompt": text,
                "cost": cost(route, secs), "tried": tried, "swipe_leaks": leaks, "beat_gaps": beat_gaps}
        (work / "sent.json").write_text(json.dumps(sent, indent=1))
        if dry_run:
            print(json.dumps(sent, indent=1))
            return sent
        raw = work / f"take-{route.split('@')[0]}.mp4"
        try:
            rid, url = _route(route, take, work, secs, text, voices, mclip, raw)
        except Refused as e:
            tried.append({"route": route, "refused": str(e)[:300]})
            print(f"{route} refused: {str(e)[:200]} -> next route", flush=True)
            continue
        placed = None
        if route in OWN_VOICES and any(ln.get("read") for ln in take["script"]):
            placed = lay(raw, take["script"], out)
        else:
            out.write_bytes(raw.read_bytes())
        import take_faces as TF                    # every beat's people still their sheets; a drifted take is never used
        sent["faces"] = TF.hold_drift(take, out)
        sent["beats"] = TB.hold_misses(take, out)  # and every beat we wrote is on screen: who, action, prop, target, line-up
        sent.update({"request_id": rid, "url": url, "file": str(out), "laid": placed, "tried": tried,
                     "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        (work / "sent.json").write_text(json.dumps(sent, indent=1))
        print(json.dumps({"take": str(out), "route": route, "request_id": rid, "cost": sent["cost"],
                          "refused_first": [x["route"] for x in tried]}), flush=True)
        return sent
    raise SystemExit(f"every route refused this take: {json.dumps(tried)[:800]}")


def line_starts(clip, script):
    """Where each line starts in a take, from the take's own speech (each line's first two words)."""
    import re
    import voice_continuous as V

    def norm(w):
        w = re.sub(r"[^a-z]", "", w.lower())
        return "mm" if re.fullmatch(r"m+h?m*", w or "x") else w
    a = Path(clip).with_suffix(".heard.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-vn", str(a)], check=True)
    words = V.stt(str(a))
    ws = [norm(w["w"]) for w in words]
    out, k = [], 0
    for ln in script:
        first = [norm(x) for x in ln["say"].split()][:2]
        j = next((i for i in range(k, len(ws) - 1) if ws[i] == first[0] and (len(first) < 2 or ws[i + 1] == first[1])), None)
        if j is None:
            j = next((i for i in range(k, len(ws)) if ws[i] == first[0]), None)
        out.append(words[j]["start"] if j is not None else None)
        k = j + 1 if j is not None else k
    return out


def cut_views(made, take, out):
    """Multi-cam: the views of the same moment cut together line by line. Each line comes from the view the `cut`
    names (default: views in turn), from that view's own start of the line to its start of the next line, so the
    words run on unbroken across every cut."""
    names = [v["name"] for v in take["camera"]["views"]]
    plan = take["camera"].get("cut") or [names[k % len(names)] for k in range(len(take["script"]))]
    starts = {n: line_starts(made[n]["file"], take["script"]) for n in names}
    groups, k = [], 0
    while k < len(plan):
        j = k
        while j + 1 < len(plan) and plan[j + 1] == plan[k]:
            j += 1
        groups.append((plan[k], k, j))
        k = j + 1
    work = out.with_suffix("")
    work.mkdir(parents=True, exist_ok=True)
    files, used = [], []
    for i, (n, k, j) in enumerate(groups):
        def span(v):
            a = 0.0 if k == 0 else starts[v][k]
            b = None if j + 1 >= len(plan) else starts[v][j + 1]
            return (a, b) if a is not None and (b is None or b > a) else None
        sp = span(n)
        if sp is None:                      # the view never said these lines: another view carries them
            n = next((v for v in names if span(v)), None)
            if n is None:
                continue
            sp = span(n)
        a, b = sp
        f = work / f"cut-{i:02d}-{n}.mp4"
        a0 = max(0.0, a - 0.05)
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{a0:.3f}", "-i", made[n]["file"]]
        if b is not None:
            cmd += ["-t", f"{b - a0:.3f}"]
        subprocess.run(cmd + ["-vf", "scale=480:854:force_original_aspect_ratio=increase,crop=480:854,fps=24,setsar=1",
                              "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-ar", "48000", "-ac", "2", str(f)], check=True)
        files.append(f)
        used.append({"lines": [k + 1, j + 1], "view": n, "from": round(a, 2), "to": round(b, 2) if b else None})
    lst = work / "cut.txt"
    lst.write_text("".join(f"file '{f}'\n" for f in files))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "libx264", "-crf", "18",
                    "-c:a", "aac", "-movflags", "+faststart", str(out)], check=True)
    return used


def motion_in(take, dry_run=False):
    """The take's motion, through the motion chain's one door (components/motion/motion_chain.py `for_take`): a
    scene's motion when `motion.scene` names one, once it has passed the chain's own checks; motion they held, or that
    never went through them, stops the take before any paid call, with the reason; and when the motion carries a camera tracked off real footage, the take's written shot sizes come out
    (the camera is then said only as the track measured it)."""
    home = str(ST.part("motion"))
    if home not in sys.path:
        sys.path.insert(0, home)
    import motion_chain as MC
    return MC.for_take(take, dry_run)


def scene(scene_dir, dry_run=False):
    """One command for a scene, the whole order, with nobody asked (2026-11-15):

      0 inject   our scene put into the production capabilities of the source shots it re-makes (production_inject:
                 the source's production spec, made once per source, its slots filled with our scene; free)
      1 motion   our own direction rendered as the rehearsal when the injection wrote one (motion_chain `direct`);
                 otherwise the motion chain's decision, where a rehearsal held because its reference does not show our beats' moves is
                 programmed from our beats on the reference's timing and camera (motion_chain `ours`, free) and decided
                 again
      2 picture  the start picture dressed from the scene's filed 3D set print (take.json `set_print`) over the
                 rehearsal's first frame, and laid over that frame (motion_chain `ready`)
      3 review   the scene input review: every input, the beats as fields, the exact prompt and settings, written to
                 <scene>/review/input-review.html (+ .json) before anything is paid for
      4 take     the take
      5 checks   faces against the sheets and every beat on screen (inside the take: take_faces, take_beats), then the
                 take against the real footage (motion_chain `check`)

    Held motion, a start picture that will not match, a beat with no who or action, or the swipe's own words stop it
    before the take is paid for, with the reason. A later part of a long scene (`motion.segment` 2 or more) starts from
    the last frame of the part before: take.json names that frame as its `picture`. `dry_run`: steps 1 and 3 run (both
    free), nothing is made or paid; the plan, the cost and every step's state are printed."""
    MC = _mc()
    sd = Path(scene_dir)
    import production_inject as PI                 # 0 our scene into the source's production capabilities (free)
    sheet = PI.ensure(sd)
    written = json.loads((sd / "take.json").read_text())
    seg = (written.get("motion") or {}).get("segment")
    later = seg is not None and int(seg) > 1
    take = dict(written, motion=dict({k: v for k, v in (written.get("motion") or {}).items() if k in ("segment", "blur")}, scene=str(sd)),
                out=written.get("out") or str(sd / "take.mp4"))
    steps = {"production sheet": str(sheet) if sheet else "none: this scene re-makes no torn-down source"}
    # 1 motion: the chain run first when the scene has none yet (the reference named in take.json `motion`)
    if not (sd / "motion" / "motion.json").exists():
        wm = written.get("motion") or {}
        spans = [(float(wm["from"]), float(wm["to"]))] if wm.get("source") and wm.get("to") is not None else None
        MC.prepare(sd, written, written.get("brand"), written.get("framemap"), wm.get("source"), spans, wm.get("clip"))
    mrec = json.loads((sd / "motion" / "motion.json").read_text()) if (sd / "motion" / "motion.json").exists() else {}
    blk = sd / "motion" / "rehearsal" / "blocking.mp4"
    if mrec.get("ours_because") and blk.exists() and (sd / "take.json").stat().st_mtime > blk.stat().st_mtime:
        MC.ours(sd, written)                         # our beats changed since they were programmed: programmed again
    state = MC.ready(sd, picture=False)
    if not state["ok"] and MC.gaps(sd / "motion"):
        MC.ours(sd, written)
        state = MC.ready(sd, picture=False)
        steps["motion"] = "programmed from our beats on the reference's timing and camera; " + ("passed" if state["ok"] else "held")
    else:
        steps["motion"] = "passed" if state["ok"] else "held"
    if not state["ok"]:
        steps["motion"] += ": " + " · ".join(state["held"])
    # 2 picture
    sp = take.get("set_print")
    steps["set print"] = sp if sp and Path(sp).exists() else "missing: no filed 3D set print named in take.json `set_print` (3d-print)"
    if later:
        steps["picture"] = take.get("picture") or "missing: this part starts from the last frame of the part before"
    elif dry_run:
        take.setdefault("picture", str(sd / "motion" / "first-frame.png"))
        steps["picture"] = ("made from the set print and checked by the chain when the take is made" if sp and Path(sp).exists()
                            else "missing: waits for the set print (3d-print) before it can be made")
    elif state["ok"]:
        got = MC.ready(sd)
        if not got["ok"]:
            steps["picture"] = "held: " + " · ".join(got["held"])
        else:
            take["picture"] = got["picture"] or take.get("picture")
            steps["picture"] = take["picture"]
    # 3 review (from the dry run's own request: what would be sent, exactly)
    planned = make(dict(take, picture=take.get("picture") or str(sd / "motion" / "first-frame.png")), dry_run=True)
    page = review(sd, take, planned, steps, state)
    steps["review"] = str(page)
    print(json.dumps({"steps": steps}, indent=1, ensure_ascii=False))
    if dry_run:
        return {"steps": steps, "planned": planned}
    stop = [k for k in ("motion", "picture") if str(steps.get(k, "")).startswith(("held", "missing"))]
    if stop:
        raise SystemExit("no take made: " + " · ".join("%s %s" % (k, steps[k]) for k in stop))
    # 4 take, with the face and beat doors inside it; 5 the take against the real footage
    res = make(take)
    chk = MC.check(sd, take["out"])
    out = {"take": take["out"], "picture": take["picture"], "beats": (res or {}).get("beats", {}) and {"pass": res["beats"]["pass"]},
           "check": {"passed": chk["passed"], "failed": chk["failed"], "held_by": chk.get("held_by")}}
    print(json.dumps(out, indent=1))
    return dict(out, steps=steps, made=res)


def review(sd, take, planned, steps, state=None):
    """The scene input review (media-production playbook, 2026-11-10), from the dry run's own request: every input in
    the order it is sent, with a preview; each beat's fields; the exact prompt and settings; every step's state.
    Writes <scene>/review/input-review.json and input-review.html, and returns the page."""
    import html
    import take_beats as TB
    out = Path(sd) / "review"
    out.mkdir(parents=True, exist_ok=True)
    sent = planned if isinstance(planned, dict) and "prompt" in planned else next(iter((planned or {}).values()), {})
    inputs = [("start picture", sent.get("picture"))]
    inputs += [("set print", take.get("set_print"))] if take.get("set_print") else []
    for n, c in (take.get("cast") or {}).items():
        c = c if isinstance(c, dict) else {"sheet": c}
        inputs.append(("cast · " + n, c.get("sheet")))
    inputs += [("voice sample", v) for v in sent.get("voices") or []]
    inputs.append(("motion", sent.get("motion") or ((take.get("motion") or {}).get("scene") and str(Path(take["motion"]["scene"]) / "motion" / "rehearsal" / "blocking.mp4"))))
    beats = [{"beat": k, **{f: b.get(f, "") for f in ("who", "action", "prop", "target", "where")}, "says": b.get("say", ""),
              "as one sentence": b.get("do", "") if not b.get("action") else ""} for k, b in enumerate(TB.beats_of(take), 1)]
    rec = {"scene": str(sd), "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "steps": steps, "inputs": [{"role": r, "file": f} for r, f in inputs],
           "beats": beats, "beat_gaps": sent.get("beat_gaps") or TB.gaps(take), "swipe_leaks": sent.get("swipe_leaks"),
           "prompt": sent.get("prompt"), "route": sent.get("route"), "seconds": sent.get("seconds"), "cost": sent.get("cost"),
           "motion_held": (state or {}).get("held")}
    (out / "input-review.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))

    def media(f):
        if not f:
            return '<div class="miss">missing</div>'
        rel = html.escape(os.path.relpath(str(f), str(out)))
        if not Path(f).exists():
            return '<div class="miss">not found: %s</div>' % html.escape(Path(f).name)
        if str(f).endswith((".mp4", ".mov")):
            return '<video src="%s" controls muted playsinline></video>' % rel
        if str(f).endswith((".mp3", ".wav", ".m4a")):
            return '<audio src="%s" controls></audio>' % rel
        return '<img src="%s">' % rel
    e = html.escape
    cards = "".join('<figure>%s<figcaption><b>%d</b> %s</figcaption></figure>' % (media(f), k, e(r)) for k, (r, f) in enumerate(inputs, 1))
    rows = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % e(str(b[c])) for c in ("beat", "who", "action", "prop", "target", "where", "says", "as one sentence"))
                   for b in beats)
    gaps = "".join("<li>beat %d: %s%s</li>" % (g["beat"], e(g["why"]), " <b>(stops the take)</b>" if g["stop"] else "") for g in rec["beat_gaps"])
    st = "".join("<tr><td>%s</td><td>%s</td></tr>" % (e(k), e(str(v))) for k, v in steps.items())
    page = out / "input-review.html"
    page.write_text("""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scene input review</title><style>
:root{--bg:#fafaf7;--fg:#1b1b18;--mute:#6b6b63;--line:#deded6;--bad:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--fg:#ecece6;--mute:#9a9a90;--line:#33332e;--bad:#ff8a80}}
body{background:var(--bg);color:var(--fg);font:15px/1.45 system-ui;margin:0;padding:16px;max-width:1100px}
h1{font-size:20px}h2{font-size:15px;margin:24px 0 8px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
figure{margin:0;border:1px solid var(--line);border-radius:8px;padding:6px}img,video{width:100%%;border-radius:4px}audio{width:100%%}
figcaption{font-size:12px;color:var(--mute)}.miss{color:var(--bad);font-size:13px;padding:20px 0}
table{border-collapse:collapse;width:100%%;font-size:13px;display:block;overflow-x:auto}td{border-bottom:1px solid var(--line);padding:6px;vertical-align:top}
pre{white-space:pre-wrap;font-size:12.5px;border:1px solid var(--line);border-radius:8px;padding:10px}li{color:var(--bad)}
</style><h1>%s · scene input review</h1>
<h2>Steps</h2><table>%s</table>
<h2>Inputs, in the order sent</h2><div class="grid">%s</div>
<h2>Beats, field by field</h2><table><tr><td>#</td><td>who</td><td>action</td><td>prop</td><td>target</td><td>where</td><td>says</td><td>still one sentence</td></tr>%s</table>
%s
<h2>Exact prompt · %s · %s s · %s</h2><pre>%s</pre>""" % (
        e(Path(sd).name), st, cards, rows, ("<h2>Beat gaps</h2><ul>%s</ul>" % gaps) if gaps else "",
        e(str(sent.get("route"))), e(str(sent.get("seconds"))), e(json.dumps(sent.get("cost"))), e(str(sent.get("prompt") or ""))))
    return page


def make(take, dry_run=False):
    take = motion_in(take, dry_run)
    first = ALIASES.get(take.get("model"), take.get("model"))
    # "backups": [] means this route only; no key means the house order
    routes = ([first] if first else []) + [r for r in (take["backups"] if "backups" in take else house_routes()) if r != first]
    out = Path(take["out"])
    secs = int(take.get("seconds") or 20)
    if not dry_run:
        take = reread(take, out.with_suffix(""))
    views = (take.get("camera") or {}).get("views")
    if not views:
        return one(take, routes, out, secs, dry_run)
    made = {}
    for v in views:                         # the same moment, once per camera view
        made[v["name"]] = one(take, routes, out.with_name(f"{out.stem}-view-{v['name']}{out.suffix}"), secs, dry_run, view=v)
    if dry_run:
        return made
    used = cut_views(made, take, out)
    rec = {"take": str(out), "views": {n: {k: m.get(k) for k in ("file", "route", "cost", "request_id")} for n, m in made.items()},
           "cut": used, "cost": {"amount": round(sum(m["cost"]["amount"] for m in made.values()), 2),
                                 "unit": next(iter(made.values()))["cost"]["unit"]}}
    out.with_suffix(".multicam.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps({"take": str(out), "cut": used, "cost": rec["cost"]}))
    return rec


# Lip sync for a take that carries no voices of its own (the pose route): one face, one read, on fal. Tested 2026-11-09
# on a 2.5 s close-up (components/model-inputs/inputs/wan-2.2-vace-fun-pose.json `lip_sync`): LatentSync followed the
# voice best and costs least, so it is the default; Sync makes the sharpest mouth shapes; MuseTalk blurs the mouth.
LIPSYNC = {"latentsync": ("fal-ai/latentsync", "video_url", 0.005), "sync": ("fal-ai/sync-lipsync/v2", "video_url", 0.05),
           "musetalk": ("fal-ai/musetalk", "source_video_url", 0.0125)}


def lipsync(clip, audio, out=None, model="latentsync"):
    """`clip`'s most visible face made to speak `audio`; the audio is the clip's sound afterwards. Cost in USD."""
    ep, vkey, per = LIPSYNC[model]
    body = {vkey: [str(clip)], "audio_url": [str(audio)]}
    if model != "musetalk":
        body["enable_safety_checker"] = False
    if model == "sync":
        body["sync_mode"] = "cut_off"
    job, res = _fal(ep, body)
    out = Path(out or Path(clip).with_suffix(f".{model}.mp4"))
    urllib.request.urlretrieve((res.get("video") or {})["url"], out)
    rec = {"clip": str(clip), "audio": str(audio), "model": model, "file": str(out), "request_id": job.get("request_id"),
           "cost": {"amount": round(per * seconds_of(clip), 3), "unit": "usd"}}
    print(json.dumps(rec))
    return rec


def check(take, clip=None):
    """The finished take read back (take_layers.py, in a Python that has MediaPipe: TAKE_LAYERS_PYTHON) and every
    beat's faces marked: did the face the brief asked for show while that line was spoken."""
    clip = Path(clip or take["out"])
    py = os.environ.get("TAKE_LAYERS_PYTHON", sys.executable)
    lay_json = clip.with_suffix(".layers.json")
    tj = clip.with_suffix(".take.json")
    tj.write_text(json.dumps(take))
    if not lay_json.exists():
        subprocess.run([py, str(HERE / "take_layers.py"), str(tj), "--clip", str(clip), "--out", str(lay_json),
                        "--frames", str(clip.with_suffix(".layers.jpg"))], check=True)
    L = json.loads(lay_json.read_text())
    starts = line_starts(clip, take["script"])
    ends = [next((x for x in starts[i + 1:] if x is not None), L["seconds"]) for i in range(len(starts))]
    marks = []
    for k, (ln, a, b) in enumerate(zip(take["script"], starts, ends), 1):
        for who, fc in (ln.get("faces") or {}).items():
            want = FACES.get(fc, ("", {}))[1]
            if who not in L["tracks"]:
                marks.append({"line": k, "who": who, "face": fc, "at": a, "seen": {}, "pass": None, "why": "not found in the take"})
                continue
            rows = [r for r in L["tracks"].get(who, []) if a is not None and a - 0.3 <= r["t"] <= b + 0.3]
            peak = {m: round(max((r.get(m, 0) for r in rows), default=0), 2) for m in want}
            ok = None if not rows else all(peak[m] >= v for m, v in want.items())
            marks.append({"line": k, "who": who, "face": fc, "at": a, "seen": peak, "pass": ok})
    res = {"take": str(clip), "line_starts": starts, "faces": marks, "found": L["found"]}
    clip.with_suffix(".check.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return res


def variant(main_dir, name, opening, seconds=None, whole=False, dry_run=False, picture=None, keep_motion=False, looks=None):
    """A variation of a made scene: only its opening element swapped, everything else reused as made (owner, 2026-11-16:
    "swaps on variations should be really easy"). The main scene's start picture (already passed its checks), its
    motion, camera, cast, look and line-up are used unchanged; only the beats before the second person in the line-up
    are replaced by `opening`. No new staging, motion run or start picture.

    opening   a .json file with the new opening beats (take.json `script` rows), or one line of words: the action the
              scene's lead does to the first person in the line-up
    seconds   how long the variation take is (default: the opening alone, 5 s; `whole` makes the full scene again)
    picture   the main start picture with the opening's ONE element changed through image production (a prop in a hand,
              wet skin, a different top): needed whenever the new element is already in the first frame. Without it
              the main start picture is used as made (the opening is all action).
    looks     {NAME: "their look with the change"}: the same one element changed in the person's written look (a look
              that still names the old prop wins over the picture: 2026-11-16, the candle version came back with the loupe)
    Writes <main scene>/../<name>/take.json, then makes the take with the usual doors (swipe words, safety, beats)."""
    md = Path(main_dir).resolve()
    main = json.loads((md / "take.json").read_text())
    line = main.get("lineup") or []
    second = line[1] if len(line) > 1 else None
    script = main.get("script") or []
    cut = next((i for i, b in enumerate(script) if second and second in " ".join(str(b.get(k) or "") for k in ("target", "where"))),
               len(script))
    if str(opening).endswith(".json") and Path(opening).exists():
        own = json.loads(Path(opening).read_text())
        own = own.get("script", own) if isinstance(own, dict) else own
    else:
        lead = next((b.get("who") for b in script if b.get("who")), None)
        first = line[0] if line else None
        own = [dict(script[0], action=str(opening), target=first or script[0].get("target"),
                    where=("in front of %s" % first) if first else script[0].get("where"), say="", prop=None)] if script else []
        for b in own:
            b.pop("prop", None) if not b.get("prop") else None
            if lead: b["who"] = lead
    take = dict(main)
    take.pop("production_sheet", None)
    take["script"] = list(own) + ([] if not whole else script[cut:])
    take["seconds"] = int(seconds or (main.get("seconds") if whole else 5))
    take["picture"] = str(Path(picture).resolve()) if picture else (main.get("picture") or str(md / "motion" / "first-frame.png"))
    # the main scene's motion is the main opening's movement (and walks on to the next person): a new opening is a
    # different action, so its own beats drive the body unless --keep-motion (a check, 2026-11-16: with the main motion
    # sent, the mask version copied the loupe move and never lifted the mask)
    if keep_motion or whole:
        take["motion"] = {"scene": str(md)}
    else:
        take.pop("motion", None)
    if looks:
        take["cast"] = {k: (dict(v, look=looks[k]) if isinstance(v, dict) and k in looks else v) for k, v in (main.get("cast") or {}).items()}
    if not whole:
        # an opening alone stays with the first person, and the line is not held for people the start picture hides
        first = line[0] if line else "the first person"
        take["staging"] = (main.get("staging") or "").split(". ")[0] + (". For this whole shot the lead stays in front of %s and "
                                                                      "never moves on to the others." % first)
        take["lineup"] = []
    out_dir = md.parent / name
    out_dir.mkdir(parents=True, exist_ok=True)
    take["out"] = str(out_dir / "take.mp4")
    take["why"] = (main.get("why") or "") + " · variation %s: only the opening element swapped; the rest as %s made it" % (name, md.name)
    (out_dir / "take.json").write_text(json.dumps(take, indent=1, ensure_ascii=False))
    print(json.dumps({"variation": name, "from": str(md), "opening beats": len(own), "kept beats": len(take["script"]) - len(own),
                      "seconds": take["seconds"], "picture": take["picture"], "take": str(out_dir / "take.json")}, indent=1))
    return make(take, dry_run=dry_run)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "voices":
        for v in voices(a[1] if len(a) > 1 else None):
            print(f"{v['name']}  ({v['kind']})  {v['about'][:90]}")
    elif a[0] == "hear":
        print(say(voice_id(a[1]), a[2], a[3] if len(a) > 3 else "hear.mp3"))
    elif a[0] == "lipsync":
        def opt(k, d=None):
            return a[a.index(k) + 1] if k in a else d
        lipsync(a[1], a[2], opt("--out"), opt("--model", "latentsync"))
    elif a[0] == "check":
        check(json.loads(Path(a[1]).read_text()), a[2] if len(a) > 2 else None)
    elif a[0] == "scene":
        scene(a[1], dry_run="--dry-run" in a)
    elif a[0] == "variant":
        variant(a[1], a[2], a[3], seconds=a[a.index("--seconds") + 1] if "--seconds" in a else None,
                whole="--whole" in a, dry_run="--dry-run" in a, picture=a[a.index("--picture") + 1] if "--picture" in a else None,
                keep_motion="--keep-motion" in a,
                looks=dict(x.split("=", 1) for x in [a[i + 1] for i, v in enumerate(a) if v == "--look"]) or None)
    else:
        make(json.loads(Path(a[0]).read_text()), dry_run="--dry-run" in a)
