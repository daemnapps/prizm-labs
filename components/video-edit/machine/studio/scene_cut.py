"""Cut one Studio scene: a take's ready pictures, its read and its cards laid into the scene's clip, its captions and
its layers. Moved here from video_studio.py (2026-11-21): assembling what production made is the edit's job. The take
print itself (gen.take) is production's and stays in the Studio, which hands this the ready workflow.

The helpers (ff, loudness, exact_level, probe_dur, the caption lines on the read's own word times) are the Studio's
names too: video_studio.py points at these, so there is one copy."""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))


def _vs():
    """The Studio's production side (where a production lives, its footage, its take records), loaded when first used."""
    import video_studio as VS
    return VS


def load(p):
    return _vs().load(p)


def save(p, obj):
    return _vs().save(p, obj)


def bdir(n):
    return _vs().bdir(n)


def read_words(n, s, vfile):
    try:
        SPELL.update(load(os.path.join(bdir(n), "brief.json")).get("spell") or {})
    except (OSError, ValueError):
        pass
    return _read_words(n, s, vfile)


def _read_words(n, s, vfile):
    """Word times for a read: the tightened read's own list when the scene uses one, else the kept read's."""
    side = os.path.splitext(vfile)[0] + ".words.json"
    if os.path.exists(side):
        return load(side)["words"]
    return load(os.path.join(bdir(n), "voice", "reads.json"))["lines"][s]["words"]


def ff(args):
    # a scene's own ffmpeg (a few seconds of video) skips the machine's queue that long jobs elsewhere hold (17 Nov);
    # the full render (hyperframes) still queues
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, capture_output=True, text=True,
                       env=dict(os.environ, DAEMN_FFMPEG_DIRECT="1"))
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[-600:])


def loudness(p):
    """The file's integrated loudness (LUFS), as the swipe check measures it."""
    m = subprocess.run(["ffmpeg", "-nostdin", "-i", str(p), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(json.loads(m[m.rindex("{"):m.rindex("}") + 1])["input_i"])


def exact_level(p, target=-14.0, within=0.3):
    """After loudnorm: when the file still sits off the target (loudnorm falls back short of it when the true peak
    blocks a linear gain), one plain gain puts it on (17 Nov: every version landed at -13.2). Turning down only lowers
    the peak; a turn up is limited at -1 dBTP."""
    got = loudness(p)
    if abs(got - target) <= within:
        return got
    tmp = str(p) + ".lvl.mp4"
    gain = target - got
    af = "volume=%.2fdB" % gain + (",alimiter=limit=0.891:level=false" if gain > 0 else "")
    ff(["-i", str(p), "-c:v", "copy", "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp])
    os.replace(tmp, str(p))
    return loudness(p)


def probe_dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                       capture_output=True, text=True)
    return round(float(r.stdout.strip()), 3)


SPELL = {}      # the brief's own spellings for captions (brief.json "spell", e.g. a product name in capitals)


def spelled(w):
    for a, b in SPELL.items():
        w = w.replace(a, b)
    return w


def _caption_chunks(words, script):
    """Caption lines on the read's own word times, in the script's spelling, broken at punctuation or every 4 words."""
    toks = script.split()
    use_script = len(toks) == len(words)
    out, cur = [], []
    for i, w in enumerate(words):
        text = toks[i] if use_script else spelled(w["w"])
        # a spoken word the script writes as nothing (a zero-width filler: "two hundred thousand" written "200,000")
        # stretches the word before it and never counts as a word of its own, so no empty word lights up or breaks a line
        if not text.strip("​‌‍﻿") and (cur or out):
            if cur:
                cur[-1] = (cur[-1][0], cur[-1][1], w["end"])
            else:
                out[-1]["end"] = out[-1]["words"][-1]["end"] = w["end"]
            if i < len(words) - 1 or not cur:
                continue
        else:
            cur.append((text, w["start"], w["end"]))
        sung = "line" in w                   # a song's read: one caption per lyric line, read whole (owner, 20 Nov)
        if (words[i + 1].get("line") != w.get("line") if sung and i < len(words) - 1 else
                (not sung and (text[-1:] in ",.?!…" or len(cur) == 4))) or i == len(words) - 1:
            # each word keeps its own time, for word-by-word captions (a word box riding the spoken word)
            ws = [{"text": t, "start": a, "end": b} for t, a, b in cur]
            out.append({"start": cur[0][1], "end": cur[-1][2], "text": " ".join(t for t, _, _ in cur), "words": ws})
            cur = []
    for i in range(len(out) - 1):          # each line stays up until the next one starts
        out[i]["end"] = out[i + 1]["start"]
    return out



def cut(n, s, take, wf, steps, brief):
    """The scene's clip from its workflow (every step runnable), its captions, its layers and its run record."""
    VS = _vs()
    d = VS.sdir(n, s)
    WAITS, RUNNABLE, PHONE_LOOK = VS.WAITS, VS.RUNNABLE, VS.PHONE_LOOK
    ranged, resolve, phone_copy, wf_hash = VS.ranged, VS.resolve, VS.phone_copy, VS.wf_hash
    blocked = [WAITS.get(st["tool"], st["tool"]) for st in steps if st["tool"] not in RUNNABLE]
    if blocked:
        return {"ok": False, "waits": sorted(set(blocked))}
    out = os.path.join(d, "out", take)
    os.makedirs(out, exist_ok=True)
    t0 = datetime.datetime.now(datetime.timezone.utc)
    tmp = tempfile.mkdtemp(prefix="scene-")
    caps, layers, at = [], [], 0.0
    deliver = brief["deliver"]
    W, H = deliver["width"], deliver["height"]
    FPS = 24000 / 1001
    voice = next((st for st in steps if st["tool"] == "voice.read"), None)
    pics = [st for st in steps if st["tool"] in ("ffmpeg.trim", "layer.photo")]
    # how long each picture step runs: its own in/out, or, with a read, its share of the read
    if voice:
        vfile = os.path.join(bdir(n), voice["inputs"]["file"])
        vlen = probe_dur(vfile)
        total = max(vlen + float(voice["params"].get("tail", 0.2)), float(wf.get("min_seconds") or 0))
        # a step's own weight wins (swipe_cut.py: its swipe shot's share of the scene); else a trim's in/out span
        wts = [float(st["params"]["weight"]) if "weight" in st["params"] else
               (float(st["inputs"]["out"]) - float(st["inputs"]["in"])) if st["tool"] == "ffmpeg.trim" else 2.0 for st in pics]
        frames_total = round(total * FPS)
        rdw = read_words(n, s, vfile)
        if all("from_word" in st["params"] for st in pics):   # cut on the word: each shot starts as its word is spoken
            cuts = [0] + [round(rdw[int(st["params"]["from_word"])]["start"] * FPS) for st in pics[1:]] + [frames_total]
            fr = [max(1, cuts[i + 1] - cuts[i]) for i in range(len(pics))]
        else:
            fr = [max(1, round(frames_total * w / sum(wts))) for w in wts]
            fr[-1] = max(1, frames_total - sum(fr[:-1]))
    else:
        fr = [max(1, round((float(st["inputs"]["out"]) - float(st["inputs"]["in"])) * FPS)) for st in pics]
    try:
        ins, chains, labels = [], [], []
        for i, st in enumerate(pics):
            frames = fr[i]
            dur = frames / FPS
            entry = wf["sources"][st["inputs"]["source"][5:]]
            rg = None if st["tool"] != "ffmpeg.trim" or st["params"].get("look") == "phone" else \
                ranged(entry, (brief.get("shot_fill") or {}).get("brand") or "")
            src = rg[0] if rg else resolve(entry)
            if st["params"].get("look") == "phone":
                src = phone_copy(src, (brief.get("deliver") or {}).get("upscale"))
            if st["tool"] == "layer.photo":   # the whole photo, never cropped, on a dark ground
                ins += ["-loop", "1", "-t", str(dur + 0.5), "-i", src]
                fit = f"scale={W}:{H}:force_original_aspect_ratio=decrease"
                if st["params"].get("fill") == "blur":   # the photo over a blurred, darkened copy of itself filling the frame (feed-native, no bars)
                    v = (f"split=2[pb{i}][pf{i}];[pb{i}]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:3,"
                         f"eq=brightness=-0.12[pbg{i}];[pf{i}]{fit}[pfg{i}];[pbg{i}][pfg{i}]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=24000/1001")
                else:
                    v = f"{fit},pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x111111,setsar=1,fps=24000/1001"
                mv = st["params"].get("move")
                if mv:   # a held still reads as a slideshow: the frame keeps moving, a steady push in by `move` (0.12 = 12%) over the shot
                    amt = 0.12 if mv in (True, "push") else float(mv)
                    v += (f",scale={W * 2}:{H * 2}:flags=lanczos,zoompan=z='1+{amt}*on/{max(1, frames)}':x='iw/2-(iw/zoom/2)':"
                          f"y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=24000/1001,setsar=1")
                v += f",trim=end_frame={frames},setpts=PTS-STARTPTS"
            else:
                ins += (["-headers", rg[1]] if rg else []) + ["-ss", str(st["inputs"]["in"]), "-t", str(dur + 0.5), "-i", src]
                c = st["params"].get("crop")
                v = (f"crop={c['w']}:{c['h']}:{c['x']}:{c['y']}," if c else "") + \
                    f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=24000/1001"
                mv = st["params"].get("move")       # the swipe's camera move laid on our clip (edit_stage.lay_camera)
                if mv == "push":                    # a slow push in over the shot, 10%
                    v += (f",scale={W * 2}:{H * 2}:flags=lanczos,zoompan=z='1+0.10*on/{max(1, frames)}':"
                          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=24000/1001,setsar=1")
                elif mv == "punch":                 # a punch in: the shot held 15% closer from its first frame
                    v += f",scale={round(W * 1.15)}:{round(H * 1.15)}:flags=lanczos,crop={W}:{H},setsar=1"
                v += f",trim=end_frame={frames},setpts=PTS-STARTPTS"
                if st["params"].get("look") == "phone":   # a generated shot made to read like the phone footage around it
                    v += "," + PHONE_LOOK
            if voice or st["params"].get("sound") == "mute" or st["tool"] == "layer.photo":
                chains.append(f"[{i}:v:0]{v}[v{i}];anullsrc=r=48000:cl=stereo,atrim=duration={dur:.6f}[a{i}]")
            else:
                au = f"aresample=48000,atrim=duration={dur:.6f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={max(0, dur - 0.012):.6f}:d=0.012"
                chains.append(f"[{i}:v:0]{v}[v{i}];[{i}:a:0]{au}[a{i}]")
            labels.append(f"[v{i}][a{i}]")
            if st.get("caption") and not voice:
                caps.append({"start": round(at, 3), "end": round(at + dur, 3), "text": st["caption"], "step": st["id"]})
            at += dur
        fc = ";".join(chains) + ";" + "".join(labels) + f"concat=n={len(pics)}:v=1:a=1[v][a0]"
        maps = ["-map", "[v]", "-map", "[a0]"]
        if voice:                          # the read is the scene's sound; the footage stays silent under it
            k = len(pics)
            ins += ["-i", vfile]
            fc += f";[{k}:a:0]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={at:.6f},atrim=duration={at:.6f}[vo];[a0][vo]amix=inputs=2:normalize=0[a]"
            maps = ["-map", "[v]", "-map", "[a]"]
            rd = dict(load(os.path.join(bdir(n), "voice", "reads.json"))["lines"][s], words=read_words(n, s, vfile))
            caps = [dict(c, step="voice") for c in _caption_chunks(rd["words"], rd["text"])]
            caps[-1]["end"] = round(at, 3)
            offers = [st for st in steps if st["tool"] == "layer.offer"]
            for j, st in enumerate(offers):   # each offer card holds while its own line is spoken
                fw = st["params"].get("from_word")
                idx = next((q for q, w in enumerate(rd["words"]) if fw and w["w"].strip(",.?!").lower() == fw.lower()), 0)
                st_t = rd["words"][idx]["start"] if j else 0.0
                layers.append({"id": st["id"], "kind": "offer", "text": st["prompt"], "start": round(st_t, 3)})
            for j in range(len(layers)):
                layers[j]["end"] = layers[j + 1]["start"] if j + 1 < len(layers) else round(at, 3)
        video = os.path.join(out, f"{s}.mp4")
        ff(ins + ["-filter_complex", fc] + maps + ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
                  "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", video])
        card = next((st for st in steps if st["tool"] == "hyperframes.card"), None)
        if card:                           # an edited card: the cut footage plays under a HyperFrames design, rendered here
            proj = os.path.join(d, card["inputs"]["project"])
            os.makedirs(os.path.join(proj, "assets"), exist_ok=True)
            shutil.copy(video, os.path.join(proj, "assets", "bg.mp4"))
            tpl = os.path.join(proj, "index.template.html")
            if os.path.exists(tpl):          # a design laid over a narrated scene: timed to the read's own words
                cw = read_words(n, s, vfile) if voice else []
                p = card["params"]
                t_in = cw[int(p["from_word"])]["start"] if "from_word" in p else float(p.get("in", 0))
                t_out = cw[int(p["to_word"])]["start"] if "to_word" in p else float(p.get("out", at))
                rows = []
                if p.get("track"):            # follow a box from the first frame of the cut, for a graphic that rides on it
                    import track as TR
                    rows = TR.track(os.path.join(proj, "assets", "bg.mp4"), p["track"]["box"], float(p["track"].get("from", 0)))
                html = open(tpl).read().replace("{{DUR}}", f"{at:.3f}").replace("{{IN}}", f"{t_in:.3f}").replace("{{OUT}}", f"{t_out:.3f}")
                html = html.replace("{{TRACK}}", json.dumps(rows))
                open(os.path.join(proj, "index.html"), "w").write(html)
            r = subprocess.run(["hyperframes", "render", "--quality", "draft", "--sdr", "--fps", "24000/1001", "-o", video, proj],
                               capture_output=True, text=True, cwd=proj)
            if r.returncode or not os.path.exists(video):
                raise RuntimeError("card render failed: " + (r.stderr or r.stdout)[-600:])
            withsound = video[:-4] + ".snd.mp4"   # the scene's own sound (the read, or silence) goes back under the design
            ff(["-i", video, "-i", os.path.join(proj, "assets", "bg.mp4"), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", withsound])
            os.replace(withsound, video)
            planned = probe_dur(video)
            at = planned
        thumb = os.path.join(out, f"{s}.jpg")
        ff(["-ss", str(min(1.0, at / 2)), "-i", video, "-frames:v", "1", "-vf", "scale=270:-1", thumb])
        dur = probe_dur(video)
        planned = round(at, 3)
        save(os.path.join(out, f"{s}.captions.json"), {"scene": s, "layer": "captions", "style": "verbatim", "lines": caps})
        files = {"video": os.path.relpath(video, d), "thumb": os.path.relpath(thumb, d),
                 "captions": os.path.relpath(os.path.join(out, f"{s}.captions.json"), d)}
        if layers:
            save(os.path.join(out, f"{s}.layers.json"), {"scene": s, "layers": layers})
            files["layers"] = os.path.relpath(os.path.join(out, f"{s}.layers.json"), d)
        rec = {"scene": s, "take": take, "workflow_hash": wf_hash(wf), "ran_at": t0.isoformat(timespec="seconds"),
               "seconds_to_make": round((datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds(), 1),
               "duration": dur, "cost_usd": 0.0, "files": files, "clock_check": None,
               "voice": ({"file": voice["inputs"]["file"], "seconds": vlen} if voice else None)}
        if wf.get("clock", {}).get("locked"):
            want = round(wf["clock"]["end"] - wf["clock"]["start"], 3)
            rec["clock_check"] = {"want": want, "got": planned, "ok": abs(want - planned) <= 1 / FPS}
        save(os.path.join(out, "run.json"), rec)
        hist = os.path.join(d, "runs.jsonl")
        with open(hist, "a") as f:
            f.write(json.dumps(rec) + "\n")
        return {"ok": True, "run": rec}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
