#!/usr/bin/env python3
"""One continuous take: a whole scene made as ONE clip (tools/video-production/BRIEF-SPEC.md, "Continuous takes
and motion", ruled 2026-11-09).

Where the swipe holds one take, the scene is one call carrying:
  - the start picture (made by image production from the swipe's frame),
  - one short voice sample per speaker (the model speaks every line itself, in that voice),
  - the swipe's seconds as the motion reference (camera, staging, body language),
  - the whole script in order, each line with its speaker, and the camera, staging and body language in words.

    python3 take.py <take.json> [--dry-run]          make the take (every view, then the multi-cam cut)
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
             or {"scene": "<scene folder>", "blur": [...]}: the motion authored and approved on that scene (motion.py:
             a swipe's seconds, a phone act-out or a 3D blocking); a motion marked "approved": false is never sent
   "look": "place, light and sound in one line"}

Controls (ruled 2026-11-09, BRIEF-SPEC rules 6-8):
  cast NAME: {"sheet": "sheets/x.png", "voice": "<a voice we own, by name>", "look": "what they wear and look like",
              "seen": [t, x, y]}
      voice  - every line of that character is read again in that voice (ElevenLabs, our own voices only); swap the
               name to swap the voice; `hear` plays it first
      body   - written per beat (`moves`, every route); or the whole scene acted out on a phone by people standing
               where the characters stand, tracked by motion.py and given as `motion`: the pose route copies it 1:1
  script line: {"moves": {"NAME": "what that body does on this beat"}, "faces": {"NAME": "<a face below>"},
                "camera": "what the camera does on this beat"}
      faces  - one of FACES (smile, grin, laugh, disgust, unsure, surprise, bite-lip, flirty, deadpan, neutral); written
               into the prompt in the model's words and checked back off the take's face mesh (`check`)
  camera: {"move": "<a move below>", "angle": "<an angle>", "framing": "<a framing>",
           "shots": [{"seconds": 5, "framing": "wide", "angle": "eye", "on": "the line-up"}, ...],      one take, cut inside
           "views": [{"name": "A", "framing": "wide"}, {"name": "B", "framing": "close", "on": "RATER"}],  multi-cam
           "cut": ["A", "B", "A", ...]}                                                              view per line
      move   - handheld-follow, push-in, pull-out, pan-left, pan-right, orbit, static, whip-pan
      shots  - cuts inside one call, from a shot list in the prompt (Seedance 2.5, Wan 3.0)
      views  - the same moment made once per view, then cut together line by line on the take's own speech

Routes, in the house order (tools/generative-model-house, clips.take*): wan-start@higgsfield (the exact first frame;
the model speaks the lines and our reads are laid after), seedance@higgsfield (first frame + a voice sample per speaker
+ motion video), wan-ref@fal (reference mode), and vace-pose@fal (the motion clip's tracked poses drive our first frame).
A refusal or a failure moves the take to the next route; sent.json records every route tried and the one that made it.
Keys by name through the key loader. No brand, product or person is named here. Python 3.9.
"""
import json
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
          "from it (not its people, clothes, place or words).")
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


def camera_words(cam, on=None, shot=False):
    """A camera setting in words: move, angle, framing and who it is on. A shot inside a cut names only what changes."""
    if not cam:
        return CAMERA
    bits = [] if shot and not cam.get("move") else [MOVES.get(cam.get("move", "handheld-follow"), cam.get("move", ""))]
    if cam.get("framing"):
        bits.append(FRAMINGS.get(cam["framing"], cam["framing"]) + (f" on {cam.get('on') or on}" if (cam.get("on") or on) else ""))
    if cam.get("angle"):
        bits.append(ANGLES.get(cam["angle"], cam["angle"]))
    words = ", ".join(b for b in bits if b)
    if shot:
        return words[:1].upper() + words[1:] + "."
    return "Camera: " + words + (". One continuous take, no cuts." if not cam.get("shots") else ".")


# What each door takes (tools/model-inputs/inputs/<model>.json): voice samples in total, the motion clip, and
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


def beat_words(ln, k):
    """One beat in words: what each body does, each face, the camera, then the line."""
    bits = [ln["do"].rstrip(".") + "." if ln.get("do") else ""]
    for who, mv in (ln.get("moves") or {}).items():
        bits.append(f"{who} {mv.rstrip('.')}.")
    for who, fc in (ln.get("faces") or {}).items():
        bits.append(f"{who}'s face: {FACES.get(fc, (fc, {}))[0]}.")
    if ln.get("camera"):
        bits.append(f"Camera: {ln['camera'].rstrip('.')}.")
    say = f" {ln['speaker']}: \"{ln['say']}\"" if ln.get("say") else ""
    return f"{k}. " + " ".join(b for b in bits if b) + say


def prompt(take, voices, with_motion, view=None, own_voices=False):
    audio = {name: i for i, (name, _) in enumerate(voices, 1)}
    who = ", ".join(f"Audio {i} is the voice of {name}" for name, i in audio.items())
    cast = {n: (c if isinstance(c, dict) else {"sheet": c}) for n, c in (take.get("cast") or {}).items()}
    cam = dict(take.get("camera") or {})
    if view:
        cam.update({k: v for k, v in view.items() if k != "name"})
    lines = [beat_words(ln, k) for k, ln in enumerate(take["script"], 1)]
    shots = ""
    if cam.get("shots"):
        at, out = 0.0, []
        for k, sh in enumerate(cam["shots"], 1):
            out.append(f"Shot {k} ({at:g}-{at + sh['seconds']:g} s): {camera_words(sh, sh.get('on'), shot=True)}")
            at += sh["seconds"]
        shots = "The take cuts between these shots of the same moment:\n" + "\n".join(out)
    return "\n".join(x for x in [
        camera_words(cam) if (cam or view) else CAMERA,
        shots,
        MOTION if with_motion else "",
        "The people, clothes, place and light are exactly those of the reference picture.",
        ("Each person looks exactly like their character sheet: " + ", ".join(f"{n} is the sheet named {n}" for n, c in cast.items() if c.get("sheet")) + ".") if any(c.get("sheet") for c in cast.values()) else "",
        " ".join(f"{n}: {c['look'].rstrip('.')}." for n, c in cast.items() if c.get("look")),
        take.get("staging", ""),
        (f"{who}; each speaks only their own lines, lips matching every word." if who else
         "Each person speaks only their own lines, lips matching every word." if own_voices else "") + " Real body language on every line.",
        "In order:\n" + "\n".join(lines),
        (take.get("look") or "") + " No music, no text on screen.",
    ] if x)


# --- voices: only the ones we own, picked by name (tools/video-production/machine/make_voice.py makes them) ---
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
    """A voice by name: exact first, then the one name that contains it. Refuses a name that is no one's or several."""
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
    take's speakers and reads point at the new files."""
    import hashlib
    cast = {n: c for n, c in (take.get("cast") or {}).items() if isinstance(c, dict) and c.get("voice")}
    if not cast:
        return take
    d = Path(work) / "reads"
    d.mkdir(parents=True, exist_ok=True)
    ids = {n: voice_id(c["voice"]) for n, c in cast.items()}
    take = json.loads(json.dumps(take))
    for k, ln in enumerate(take["script"], 1):
        n = ln["speaker"]
        if n in ids and ln.get("say"):
            h = hashlib.sha1(f"{ids[n]}|{ln['say']}".encode()).hexdigest()[:10]
            f = d / f"{n.lower().replace(' ', '-')}-{k}-{h}.mp3"
            if not f.exists():
                say(ids[n], ln["say"], f, cast[n].get("settings"))
            ln["read"] = str(f)
    speakers = {}
    for ln in take["script"]:
        if ln.get("read"):
            speakers.setdefault(ln["speaker"], []).append(ln["read"])
    take["speakers"] = {n: speakers.get(n, v) for n, v in (take.get("speakers") or speakers).items()}
    for n in speakers:
        take["speakers"].setdefault(n, speakers[n])
    take["voices"] = {n: {"name": cast[n]["voice"], "voice_id": ids[n]} for n in cast}
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
# The route order lives in the Generative Model House (tools/generative-model-house/models.json, clips.take*):
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
        return out or ["wan-start@higgsfield", "seedance@higgsfield", "wan-ref@fal"]
    except Exception:  # noqa: BLE001  a copy of the tools without the house still has the ruled order
        return ["wan-start@higgsfield", "seedance@higgsfield", "wan-ref@fal"]


def _hf(job_type, args, out):
    """One take through the Higgsfield command line (the signed-in plan's credits): create, wait, download."""
    r = subprocess.run([HF, "--json", "generate", "create", job_type] + args, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        msg = (r.stderr or r.stdout).strip()[:400]
        raise (Refused if any(w in msg.lower() for w in REFUSED) else RuntimeError)(f"higgsfield {job_type}: {msg}")
    ids = json.loads(r.stdout or "null")
    job = ids[0] if isinstance(ids, list) else (ids or {}).get("id")
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
    if route == "wan-start@higgsfield":
        # the exact first frame; a start picture cannot ride with references on this model, so it speaks the lines in
        # its own voices and ours are laid after
        args = ["--prompt", text, "--start-image", str(pic), "--duration", str(secs), "--resolution", "480p",
                "--aspect_ratio", "9:16", "--generate_audio", "true", "--enable_thinking", "true"]
        return _hf("wan3_0", args, raw)
    if route == "seedance@higgsfield":
        args = ["--prompt", text, "--mode", "omni_reference", "--start-image", str(pic), "--duration", str(secs),
                "--resolution", "480p", "--aspect_ratio", "9:16", "--generate_audio", "true"]
        for c in cast:
            args += ["--image-references", str(c)]
        for _, v in voices:
            args += ["--audio-references", str(v)]
        if mclip:
            args += ["--video-references", str(mclip)]
        return _hf("seedance_2_5", args, raw)
    if route == "wan-ref@fal":
        body = {"prompt": text, "reference_image_urls": [pic] + cast[:9], "reference_audio_urls": [str(v) for _, v in voices],
                "resolution": "480p", "aspect_ratio": "9:16", "duration": secs, "enable_safety_checker": False,
                "enable_thinking": True, "audio": True}
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
        if not mclip:
            raise Refused("the pose route needs `motion`: the clip whose poses drive the take")
        pose = work / "pose-16fps.mp4"
        n = int(min(241, seconds_of(mclip) * 16)) // 4 * 4 + 1
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mclip), "-vf", "fps=16", "-frames:v", str(n), "-an",
                        "-c:v", "libx264", "-crf", "20", str(pose)], check=True)
        body = {"prompt": text, "video_url": [str(pose)], "first_frame_url": [pic], "ref_image_urls": [pic] + cast[:9],
                "preprocess": True, "match_input_num_frames": True, "match_input_frames_per_second": True,
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
    for route in routes:
        door = DOOR.get(route, "wan-3.0")
        voices = samples(take["speakers"], work, door) if DOORS[door]["voice_total"] and take.get("speakers") and route != "wan-start@higgsfield" else []
        wants_motion = route in ("seedance@higgsfield", "wan-ref@fal", "vace-pose@fal")
        mclip = motion_clip(take["motion"], secs, work, door) if take.get("motion") and take["motion"].get("source") and wants_motion else None
        text = prompt(take, voices, mclip is not None, view=view, own_voices=route in OWN_VOICES)
        sent = {"route": route, "seconds": secs, "picture": str(take["picture"]), "voices": [str(v) for _, v in voices],
                "cast_voices": take.get("voices"), "motion": str(mclip) if mclip else None, "view": view, "prompt": text,
                "cost": cost(route, secs), "tried": tried}
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
    """The take's motion: a scene's approved motion (motion.py) when `motion.scene` names one. Motion that is waiting
    for approval stops the take before any paid call."""
    m = dict(take.get("motion") or {})
    if m.get("scene"):
        f = Path(m["scene"]) / "motion" / "motion.json"
        if not f.exists():
            raise SystemExit(f"no motion read for this scene yet ({f})")
        tm = json.loads(f.read_text())["take_motion"]
        m.update({k: tm[k] for k in ("source", "from", "to", "approved", "pose") if k in tm})   # pose: the exact skeleton video of programmed motion
    if m.get("approved") is False and not dry_run:
        raise SystemExit("this scene's motion waits for approval: approve it on the scene page, then make the take")
    return dict(take, motion=m) if m else take


def make(take, dry_run=False):
    take = motion_in(take, dry_run)
    first = ALIASES.get(take.get("model"), take.get("model"))
    routes = ([first] if first else []) + [r for r in (take.get("backups") or house_routes()) if r != first]
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
# on a 2.5 s close-up (tools/model-inputs/inputs/wan-2.2-vace-fun-pose.json `lip_sync`): LatentSync followed the
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
    else:
        make(json.loads(Path(a[0]).read_text()), dry_run="--dry-run" in a)
