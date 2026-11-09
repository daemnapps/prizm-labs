#!/usr/bin/env python3
"""One continuous take: a whole scene made as ONE clip (tools/video-production/BRIEF-SPEC.md, "Continuous takes
and motion", ruled 2026-11-09).

Where the swipe holds one take, the scene is one call carrying:
  - the start picture (made by image production from the swipe's frame),
  - one short voice sample per speaker (the model speaks every line itself, in that voice),
  - the swipe's seconds as the motion reference (camera, staging, body language),
  - the whole script in order, each line with its speaker, and the camera, staging and body language in words.

    python3 take.py <take.json> [--dry-run]

take.json:
  {"out": "take.mp4", "model": "<route to try first; none = the house order>", "backups": ["<route>", ...],  "seconds": 20,
   "picture": "start.png",
   "cast": {"HOST": "sheets/host.png", "RATER": "sheets/rater.png"},     every person's character sheet (keeps them ours)
   "speakers": {"HOST": ["reads/1.mp3", "reads/3.mp3"], "RATER": ["reads/2.mp3"]},
   "script": [{"speaker": "HOST", "say": "...", "do": "what the body does on this line", "read": "reads/1.mp3"}, ...],
   "staging": "who stands where and who moves where, in order",
   "motion": {"source": "swipe.mp4", "from": 0, "to": 10, "blur": [[x, y, w, h], ...]},
   "look": "place, light and sound in one line"}

Routes, in the house order (tools/generative-model-house, clips.take*): wan-start@higgsfield (the exact first frame;
the model speaks the lines and our reads are laid after), seedance@higgsfield (first frame + a voice sample per speaker
+ motion video), wan-ref@fal (reference mode), and vace-pose@fal (the motion clip's tracked poses drive our first frame).
A refusal or a failure moves the take to the next route; sent.json records every route tried and the one that made it.
Keys by name through the key loader. No brand, product or person is named here. Python 3.9.
"""
import json
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


def prompt(take, voices, with_motion):
    audio = {name: i for i, (name, _) in enumerate(voices, 1)}
    who = ", ".join(f"Audio {i} is the voice of {name}" for name, i in audio.items())
    lines = []
    for k, ln in enumerate(take["script"], 1):
        do = f" {ln['do'].rstrip('.')}." if ln.get("do") else ""
        lines.append(f"{k}.{do} {ln['speaker']}: \"{ln['say']}\"")
    return "\n".join(x for x in [
        CAMERA,
        MOTION if with_motion else "",
        "The people, clothes, place and light are exactly those of the reference picture.",
        ("Each person looks exactly like their character sheet: " + ", ".join(f"{n} is the sheet named {n}" for n in take.get("cast") or {}) + ".") if take.get("cast") else "",
        take.get("staging", ""),
        f"{who}; each speaks only their own lines, lips matching every word. Real body language on every line.",
        "In order:\n" + "\n".join(lines),
        (take.get("look") or "") + " No music, no text on screen.",
    ] if x)


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
    pic, cast = take["picture"], list((take.get("cast") or {}).values())
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


def make(take, dry_run=False):
    first = ALIASES.get(take.get("model"), take.get("model"))
    routes = ([first] if first else []) + [r for r in (take.get("backups") or house_routes()) if r != first]
    out = Path(take["out"])
    work = out.with_suffix("")
    work.mkdir(parents=True, exist_ok=True)
    secs = int(take.get("seconds") or 20)
    tried = []
    for route in routes:
        door = {"wan-start@higgsfield": "wan-3.0", "wan-ref@fal": "wan-3.0", "seedance@higgsfield": "seedance-2.5",
                "vace-pose@fal": "wan-vace-pose"}.get(route, "wan-3.0")
        voices = samples(take["speakers"], work, door) if DOORS[door]["voice_total"] and take.get("speakers") and route != "wan-start@higgsfield" else []
        wants_motion = route in ("seedance@higgsfield", "wan-ref@fal", "vace-pose@fal")
        mclip = motion_clip(take["motion"], secs, work, door) if take.get("motion") and take["motion"].get("source") and wants_motion else None
        text = prompt(take, voices, mclip is not None)
        sent = {"route": route, "seconds": secs, "picture": str(take["picture"]), "voices": [str(v) for _, v in voices],
                "motion": str(mclip) if mclip else None, "prompt": text, "tried": tried}
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
        print(json.dumps({"take": str(out), "route": route, "request_id": rid, "refused_first": [x["route"] for x in tried]}))
        return sent
    raise SystemExit(f"every route refused this take: {json.dumps(tried)[:800]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    make(json.loads(Path(sys.argv[1]).read_text()), dry_run="--dry-run" in sys.argv)
