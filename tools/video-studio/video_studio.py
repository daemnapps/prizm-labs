"""Video Studio: every scene of a brief is a node with its own saved workflow.

  python3 video_studio.py serve [--port 8921]   the canvas page
  python3 video_studio.py run <brief> S1           rerun one scene alone (what the scheduled agent calls)
  python3 video_studio.py package <brief>          write the production package for HyperFrames

A workflow (briefs/<n>/scenes/<S>/take-N.json) holds every step: tool, model,
prompt, seed, inputs, params. A run writes the scene file, a thumbnail, its
caption layer and a run record next to it, so one scene remakes alone and the
assembly picks up whatever take is picked.
"""
import datetime
import glob
import hashlib
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as ST  # noqa: E402
BRIEFS = str(ST.BRIEFS)
SOURCES = str(ST.SOURCES)
DRIVE_ROOTS = ST.DRIVE_ROOTS
LOCK = threading.Lock()
RUNNING = {}
MAKING = {}   # AI shots with a take being made right now (Production view: pick a clip model, make a take)
RUNNABLE = {"ffmpeg.trim", "voice.read", "layer.photo", "layer.offer", "hyperframes.card"}  # tools this canvas can run today; others show what they wait on
WAITS = {"voice.ai": "AI voice", "gen.shot": "shot generation", "gen.take": "continuous take", "human.read": "voice read", "capture.page": "page capture", "layer.photo": "edit layer",
         "layer.offer": "edit layer"}


# Phone look for generated shots: a lower-resolution sensor, softer and flatter colour, grain, a small handheld drift.
PHONE_LOOK = ("noise=alls=6:allf=t+u,"
              "crop=1040:1850:20+14*sin(t*1.7)+6*sin(t*4.1):35+10*sin(t*1.3)+5*sin(t*3.7),scale=1080:1920,setsar=1")


def phone_copy(src):
    """A generated clip re-shot as a phone would: lower resolution, phone sharpening halo, sensor grain, heavy compression."""
    out = os.path.join(SOURCES, "generated", "phone", os.path.basename(src))
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        ff(["-i", src, "-an", "-vf", "scale=432:768:flags=bilinear,eq=contrast=0.9:saturation=0.84:gamma=1.05,"
            "gblur=sigma=0.7,unsharp=5:5:0.6:5:5:0,noise=alls=14:allf=t+u,fps=30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "31", "-pix_fmt", "yuv420p", out])
    return out


def bdir(n):
    return os.path.join(BRIEFS, n)


def sdir(n, s):
    return os.path.join(bdir(n), "scenes", s)


def load(p):
    with open(p) as f:
        return json.load(f)


def save(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


def wf_hash(wf):
    keep = {k: wf[k] for k in ("steps", "clock", "sources") if k in wf}
    return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:12]


def resolve(src):
    loc = src["drive_location"]
    if os.path.isabs(loc) and os.path.exists(loc):          # a library clip, by its synced Drive path
        return loc
    if os.path.exists(os.path.join(SOURCES, loc)):  # a generated shot, kept beside the pulled sources
        return os.path.join(SOURCES, loc)
    rel = loc[len("Shared Assets/"):] if loc.startswith("Shared Assets/") else loc
    for root in DRIVE_ROOTS:
        p = os.path.join(root, rel)
        if os.path.exists(p):
            return p
    p = os.path.join(SOURCES, os.path.basename(loc))   # pulled from Drive by its link when no synced folder has it
    if os.path.exists(p):
        return p
    raise FileNotFoundError("source not found (set VIDEO_STUDIO_DRIVE or pull it by link): " + loc)


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
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[-600:])


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
        cur.append((text, w["start"], w["end"]))
        if text[-1:] in ",.?!…" or len(cur) == 4 or i == len(words) - 1:
            out.append({"start": cur[0][1], "end": cur[-1][2], "text": " ".join(t for t, _, _ in cur)})
            cur = []
    for i in range(len(out) - 1):          # each line stays up until the next one starts
        out[i]["end"] = out[i + 1]["start"]
    return out


def run_scene(n, s, take=None):
    brief = load(os.path.join(bdir(n), "brief.json"))
    take = take or brief["picks"][s]
    d = sdir(n, s)
    wf = load(os.path.join(d, take + ".json"))
    steps = wf["steps"]
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
        wts = [(float(st["inputs"]["out"]) - float(st["inputs"]["in"])) if st["tool"] == "ffmpeg.trim" else float(st["params"].get("weight", 2.0)) for st in pics]
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
            src = resolve(wf["sources"][st["inputs"]["source"][5:]])
            if st["params"].get("look") == "phone":
                src = phone_copy(src)
            if st["tool"] == "layer.photo":   # the whole photo, never cropped, on a dark ground
                ins += ["-loop", "1", "-t", str(dur + 0.5), "-i", src]
                v = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x111111,setsar=1,fps=24000/1001,trim=end_frame={frames},setpts=PTS-STARTPTS"
            else:
                ins += ["-ss", str(st["inputs"]["in"]), "-t", str(dur + 0.5), "-i", src]
                c = st["params"].get("crop")
                v = (f"crop={c['w']}:{c['h']}:{c['x']}:{c['y']}," if c else "") + \
                    f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=24000/1001,trim=end_frame={frames},setpts=PTS-STARTPTS"
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


def scene_state(n, s, brief):
    d = sdir(n, s)
    takes = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(d, "take-*.json")))
    pick = brief["picks"].get(s, takes[0] if takes else None)
    wf = load(os.path.join(d, pick + ".json"))
    rp = os.path.join(d, "out", pick, "run.json")
    run = load(rp) if os.path.exists(rp) else None
    fresh = bool(run and run["workflow_hash"] == wf_hash(wf))
    waits = sorted({WAITS.get(st["tool"], st["tool"]) for st in wf["steps"] if st["tool"] not in RUNNABLE})
    status = "running" if RUNNING.get((n, s)) else ("made" if fresh else ("changed" if run else ("waiting" if waits else "ready")))
    return {"scene": s, "takes": takes, "pick": pick, "workflow": wf, "run": run, "status": status, "waits": waits}


def brief_state(n):
    brief = load(os.path.join(bdir(n), "brief.json"))
    return {"brief": brief, "scenes": [scene_state(n, s, brief) for s in brief["order"]]}


def new_take(n, s):
    brief = load(os.path.join(bdir(n), "brief.json"))
    d = sdir(n, s)
    cur = load(os.path.join(d, brief["picks"][s] + ".json"))
    k = 1 + max(int(os.path.basename(p)[5:-5]) for p in glob.glob(os.path.join(d, "take-*.json")))
    cur["take"] = f"take-{k}"
    cur["from_take"] = brief["picks"][s]
    save(os.path.join(d, f"take-{k}.json"), cur)
    # the cut keeps the take it has until someone picks the copy (the owner 8 Nov: "New take" emptied a finished scene)
    return cur["take"]


def shot_frame(n, s, step_id):
    """A still of one shot in a scene (its source at the shot's in point), cached beside the scene's run."""
    brief = load(os.path.join(bdir(n), "brief.json"))
    pick = brief["picks"][s]
    wf = load(os.path.join(sdir(n, s), pick + ".json"))
    st = next(x for x in wf["steps"] if x.get("id") == step_id)
    src = (wf.get("sources") or {}).get(((st.get("inputs") or {}).get("source") or "")[5:])
    out = os.path.join(sdir(n, s), "out", "shots", pick + "-" + step_id + ".jpg")
    if os.path.exists(out):
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    path = resolve(src) if src else None
    if not path or not os.path.exists(path):
        raise FileNotFoundError("no source for " + step_id)
    t = float((st.get("inputs") or {}).get("in") or 0) + 0.3
    args = ["ffmpeg", "-v", "error", "-y"] + ([] if path.lower().endswith((".jpg", ".jpeg", ".png")) else ["-ss", str(t)])
    subprocess.run(args + ["-i", path, "-frames:v", "1", "-vf", "scale=270:-2", out], check=True, timeout=60)
    return out


def open_in_hyperframes(n, version=None):
    """The edit (or one version's edit) in HyperFrames' own studio, running locally, to show inside the Video Studio
    (the owner 8 Nov: in the Claude browser, local, not Chrome or the desktop app). Reuses a studio already running for
    that project; otherwise starts one in the background."""
    d = os.path.join(bdir(n), "versions", version, "studio") if version and version != "control" else os.path.join(bdir(n), "studio")
    if not os.path.isdir(d):
        raise FileNotFoundError("no HyperFrames project for " + (version or "the cut") + " yet")
    def running():
        r = subprocess.run(["hyperframes", "preview", "--list"], capture_output=True, text=True, timeout=30)
        for line in r.stdout.splitlines():
            m = re.search(r"Port (\d+)\s+studio\s+(.+?) \(PID", line)
            if m and os.path.realpath(m.group(2).strip()) == os.path.realpath(d):
                return int(m.group(1))
        return None
    port = running()
    if not port:
        import socket
        port = 3400
        while True:
            with socket.socket() as sk:
                if sk.connect_ex(("127.0.0.1", port)):
                    break
            port += 1
        subprocess.run(["hyperframes", "preview", d, "--background", "--port", str(port), "--open=false"],
                       capture_output=True, text=True, timeout=90)
        port = running() or port
    return {"project": os.path.relpath(d, HERE), "url": f"http://127.0.0.1:{port}/"}


def package(n):
    """Production package: each made scene's file at its place on the timeline, for HyperFrames."""
    st = brief_state(n)
    at, items = 0.0, []
    for sc in st["scenes"]:
        if sc["status"] != "made":
            items.append({"scene": sc["scene"], "status": sc["status"], "waits": sc["waits"]})
            continue
        r = sc["run"]
        base = os.path.join("scenes", sc["scene"])
        items.append({"scene": sc["scene"], "take": sc["pick"], "status": "made", "start": round(at, 3),
                      "end": round(at + r["duration"], 3),
                      "video": os.path.join(base, r["files"]["video"]),
                      "layers": {"captions": os.path.join(base, r["files"]["captions"])},
                      "recipe": os.path.join(base, sc["pick"] + ".json"), "workflow_hash": r["workflow_hash"]})
        at += r["duration"]
    pkg = {"schema": "production-package/v1", "brief": st["brief"]["brief"], "deliver": st["brief"]["deliver"],
           "made_seconds": round(at, 3), "scenes": items,
           "written": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    save(os.path.join(bdir(n), "production-package.json"), pkg)
    return pkg


# ---------------------------------------------------------------- the studio (one front door for video work)
# the owner 8 Nov: one centralized menu, one look, always clear which brief and stage; full reference for AI shots.
GEN = os.path.join(SOURCES, "generated")
BOARD = ST.BOARD
APPROVE = ST.APPROVE
_cache = {}


def _get(url, timeout=4, ttl=20):
    import time as _t
    import urllib.request as _u
    hit = _cache.get(url)
    if hit and _t.time() - hit[0] < ttl:
        return hit[1]
    try:
        v = json.load(_u.urlopen(url, timeout=timeout))
    except Exception:  # noqa: BLE001 — a tool that is down just shows as empty
        v = None
    _cache[url] = (_t.time(), v)
    return v


def productions():
    out = []
    for bp in sorted(glob.glob(os.path.join(BRIEFS, "*", "brief.json"))):
        try:
            b = load(bp)
        except (OSError, ValueError):
            continue
        n = os.path.basename(os.path.dirname(bp))
        key = str(b.get("brief") or "")
        brand = key.split("_", 1)[0] if key.split("_", 1)[0] in dict(brands_here()) else None
        out.append({"n": n, "title": b.get("title") or n, "idea": b.get("idea"), "brand": brand, "key": key,
                    "scenes": len(b.get("order") or []),
                    "versions": len(versions(n))})
    return out


def ledger_stages(prods):
    """key -> {"id", "name", "flag"} for every production, read from the ledger (the Queue). A piece the ledger has
    closed (sent to Meta and completed) is live. Names are the ledger's own stage names (components/naming/stages.json)."""
    d = _get(ST.LEDGER + "/api/queue", timeout=20, ttl=60) or {}
    names = {}
    try:
        names = {s["id"]: s["name"] for s in json.loads((ST.part("naming") / "stages.json").read_text())["stages"]}
    except (OSError, ValueError, KeyError):
        pass
    by_id = {}
    for e in d.get("items") or []:
        by_id[e.get("id")] = e
    for e in d.get("removed") or []:
        if str(e.get("note") or "").startswith("Completed") or e.get("stage") == "live":
            by_id.setdefault(e.get("id"), dict(e, stage="live"))
    out = {}
    for p in prods:
        key = p.get("key") or ""
        e = by_id.get(key)
        if e is None and p.get("run"):                           # a piece named by its writing run
            e = by_id.get(f"{key.split('_', 1)[0]}_idea_{p['run']}")
        if e is None and "_brief-" in key:                       # the same brief under another product spelling
            brand, num = key.split("_", 1)[0], key.rsplit("_brief-", 1)[1]
            e = next((x for k, x in by_id.items() if str(k).startswith(brand + "_") and str(k).endswith("_brief-" + num)), None)
        if e:
            sid = e.get("stage")
            out[key] = {"id": sid, "name": names.get(sid, sid), "flag": e.get("flag")}
    return out


def idea_runs():
    """storyboard idea -> its writing run, from the board's matrix (the board's own data)."""
    try:
        board = Path(os.environ.get("VIDEO_STUDIO_BOARD_DATA") or ST.REPO / "runs" / "storyboard")
        return {f"brief{a['n']}": a.get("line") for a in json.loads((board / "matrix.json").read_text()).get("ads", []) if a.get("line")}
    except (OSError, ValueError):
        return {}


def link_productions(prods, ideas=None):
    """A production made from an idea's writing run is that idea's production, even when its brief.json never said so:
    its key ends with the run's name. Fills `idea` and `run` on each production."""
    runs = idea_runs()
    for p in prods:
        key = str(p.get("key") or p.get("n") or "")
        if not p.get("idea"):
            p["idea"] = next((i for i, r in runs.items() if r and key.endswith(r)), None)
        p["run"] = runs.get(p.get("idea")) if p.get("idea") else None
    return prods


def ledger_idea_stages(ideas):
    """idea -> its ledger stage, for storyboard ideas not yet in production: the board's matrix names each idea's
    writing run, and the ledger files a run as <brand>_idea_<run>."""
    d = _get(ST.LEDGER + "/api/queue", timeout=20, ttl=60) or {}
    try:
        names = {s["id"]: s["name"] for s in json.loads((ST.part("naming") / "stages.json").read_text())["stages"]}
    except (OSError, ValueError, KeyError):
        names = {}
    runs = idea_runs()
    items = list(d.get("items") or [])
    out = {}
    for i in ideas:
        run = runs.get(i.get("id"))
        if not run:
            continue
        e = next((x for x in items if str(x.get("id")) == f"{i.get('brand')}_idea_{run}"
                  or any(str(s).endswith(":" + run) for s in x.get("sources") or [])), None)
        if e:
            out[i["id"]] = {"id": e.get("stage"), "name": names.get(e.get("stage"), e.get("stage")), "flag": e.get("flag")}
    return out


def brands_here():
    """(brand, label) for every brand folder in this workspace; the label from the brand's own account file."""
    out = []
    root = ST.REPO / "brands"
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        if not d.is_dir() or d.name.startswith(("_", ".")):
            continue
        label = d.name
        acc = d / "meta" / "account.json"
        try:
            a = json.loads(acc.read_text())
            label = a.get("label") or (a.get("spelling") or {}).get(d.name) or d.name.capitalize()
        except (OSError, ValueError):
            continue                       # a brand with no account file runs no ads, so it has no video work here
        out.append((d.name, label))
    return out


def menu():
    ideas = _get(BOARD + "/api/ideas") or []
    prods = link_productions(productions())
    by_idea = {p["idea"]: p for p in prods if p.get("idea")}
    for p in prods:
        if not p["brand"] and p.get("idea"):
            p["brand"] = next((i.get("brand") for i in ideas if i.get("id") == p["idea"]), None)
    cards = (_get(APPROVE + "/api/cards?view=check", timeout=6, ttl=30) or {}).get("cards") or []
    waiting = {}
    for c in cards:
        waiting.setdefault(c.get("brand"), []).append(c.get("ad_name") or c.get("id"))
    # every ad's stage comes from the ledger (the Queue), the same record the board and every tool read (the owner,
    # 8 Nov: "studio needs to function on the same ledger as the board because it's all one integrated system")
    stage_of = ledger_stages(prods)
    idea_stage = ledger_idea_stages(ideas)
    brands = []
    for b, label in brands_here():
        items = []
        for i in ideas:
            if i.get("brand") != b:
                continue
            p = by_idea.get(i["id"])
            stage = stage_of.get(p["key"]) if p else idea_stage.get(i["id"])
            stage = stage or ({"id": "making", "name": "Handed off · making"} if p else {"id": "idea", "name": "Storyboard"})
            items.append({"idea": i["id"], "name": i.get("name"), "swipe": i.get("swipe"), "production": p and p["n"],
                          "key": p and p["key"], "versions": p and p["versions"], "stage": stage})
        loose = [p for p in prods if p["brand"] == b and not p.get("idea")]
        brands.append({"id": b, "label": label, "ideas": items,
                       "productions": [{"production": p["n"], "name": p["title"], "key": p["key"],
                                        "stage": stage_of.get(p["key"]) or {"id": "making", "name": "Handed off · making"}} for p in loose],
                       "waiting": len(waiting.get(b, []))})
    return {"brands": brands, "board": bool(ideas), "approve": cards is not None}


def _recipes():
    """name -> (recipe dict, recipe file) over every recipe file the generator wrote."""
    out = {}
    for f in sorted(glob.glob(os.path.join(GEN, "recipes*.json"))):
        try:
            d = load(f)
        except (OSError, ValueError):
            continue
        rel = os.path.relpath(f, GEN)
        if isinstance(d, list):
            for r in d:
                out[r.get("name")] = (dict(r, kind="from a real frame"), rel)
        elif isinstance(d, dict):
            shots = d.get("shots") or {}
            for name, prompt in (shots.items() if isinstance(shots, dict) else []):
                out[name] = ({"name": name, "kind": "from a text prompt only", "action": prompt, "style": d.get("style"),
                              "model": d.get("model"), "seed": d.get("seed"), "job": (d.get("jobs") or {}).get(name)}, rel)
    return out


def _gen_file(rel):
    return rel if rel and os.path.isfile(os.path.join(GEN, rel)) else None


def clip_reference(n, s):
    """Everything behind each AI shot a scene uses: the real frame, every prompt, the models and settings, every take
    made (kept and rejected, with the reason), and where the shot sits in the scene."""
    import gen_ref as GR
    brief = load(os.path.join(bdir(n), "brief.json"))
    take = brief["picks"][s]
    wf = load(os.path.join(sdir(n, s), take + ".json"))
    rec = _recipes()
    out = []
    for slot, src in (wf.get("sources") or {}).items():
        if not src.get("generated"):
            continue
        name = os.path.splitext(os.path.basename(src.get("file") or src.get("drive_location") or ""))[0]
        r, rf = rec.get(name, ({}, None))
        made = r.get("made") or {}
        steps = []
        on_house = str(made.get("process") or "").startswith("house")
        OLD_EDIT, OLD_I2V = "fal-ai/nano-banana/edit", "fal-ai/bytedance/seedance/v1/lite/image-to-video"
        if r.get("kind") == "from a real frame":
            exact = {x.get("what"): x for x in made.get("steps") or []}
            ref = _gen_file(os.path.join("refs", r.get("ref") or ""))
            if r.get("still"):
                st = exact.get("still")
                steps.append({"what": "Still from the reference", "model": (st or {}).get("model") or (GR.EDIT if on_house else OLD_EDIT), "input": ref,
                              "prompt": (st or {}).get("sent", {}).get("prompt") or (r["still"] + GR.MATCH),
                              "prompt_note": "exactly as sent" if st else "rebuilt: the recipe's words plus the tool's camera-match clause",
                              "out": _gen_file(os.path.join("refs", name + "-still.jpg")),
                              "request_id": (st or {}).get("request_id"), "at": (st or {}).get("at")})
            cl = exact.get("clip")
            steps.append({"what": "Clip from the still" if r.get("still") else "Clip from the reference", "model": (cl or {}).get("model") or (GR.I2V if on_house else OLD_I2V),
                          "input": _gen_file(made.get("frame")) or (steps[-1]["out"] if steps else ref),
                          "prompt": (cl or {}).get("sent", {}).get("prompt") or (r.get("action", "") + GR.LOOK),
                          "prompt_note": "exactly as sent" if cl else "rebuilt: the recipe's action plus the tool's phone-look clause",
                          "settings": (cl or {}).get("sent") and {k: v for k, v in cl["sent"].items() if k not in ("prompt", "image_url")}
                          or {"resolution": "720p", "duration": "5 s", "seed": r.get("seed", 322)},
                          "out": _gen_file(name + ".mp4"), "request_id": (cl or {}).get("request_id"), "at": (cl or {}).get("at")})
        elif r:
            ref = None
            steps.append({"what": "Clip from a text prompt (no reference frame)", "model": r.get("model"), "input": None,
                          "prompt": (r.get("action") or "") + " " + (r.get("style") or ""), "prompt_note": "as written in the recipe",
                          "settings": {"seed": r.get("seed")}, "out": _gen_file(name + ".mp4"), "request_id": r.get("job")})
        else:
            ref = None
        phone = _gen_file(os.path.join("phone", name + ".mp4"))
        if phone:
            steps.append({"what": "Phone pass", "model": "ffmpeg (no AI)", "input": name + ".mp4",
                          "prompt": "Re-shot through a phone look: 432 px, grain, compression, handheld drift (video_studio.phone_copy)",
                          "prompt_note": "a fixed recipe, not a prompt", "out": phone})
        rejected = sorted(os.path.relpath(f, GEN) for f in glob.glob(os.path.join(GEN, "rejected", name + "*")))
        used = [{"step": st.get("id"), "in": (st.get("inputs") or {}).get("in"), "out": (st.get("inputs") or {}).get("out")}
                for st in wf.get("steps") or [] if (st.get("inputs") or {}).get("source") == "slot:" + slot]
        out.append({"slot": slot, "name": name, "kind": r.get("kind") or "no recipe found", "recipe_file": rf,
                    "process": made.get("process") if on_house else "made OFF the house process (fal: Nano Banana edit, Seedance lite 720p) — before 8 Nov",
                    "on_house": on_house, "house": GR.PROCESS,
                    "ref": ref, "steps": steps, "rejected_notes": r.get("rejected") or [], "rejected_files": rejected,
                    "error": r.get("error"), "used": used,
                    "clip_model": (r.get("clip_model") or GR.DEFAULT) if r.get("kind") == "from a real frame" else None,
                    "making": bool(MAKING.get(name))})
    return {"brief": n, "scene": s, "take": take, "shots": out}


# ---------------------------------------------------------------- motion: author a scene's motion, watch it, approve it
MOTION_READING = {}   # (brief, scene) -> what is being read right now


def _beats(wf):
    """The scene's lines in order, each with its speaker: what the motion has to carry."""
    lines = [st for st in wf.get("steps") or [] if st.get("tool") in ("voice.ai", "human.read") and st.get("prompt")]
    lines.sort(key=lambda st: (st.get("params") or {}).get("order") or 0)
    if lines:
        return [{"speaker": (st.get("params") or {}).get("speaker") or "", "say": st["prompt"]} for st in lines]
    return [{"speaker": "", "say": w} for w in [wf.get("words")] if w]


def _swipe_of(brief):
    """The swipe this brief was written from, when its writing run holds it."""
    run = os.path.join(str(ST.WRITING), str(brief.get("brief") or ""))
    found = sorted(glob.glob(os.path.join(run, "*swipe*.mp4")))
    return found[0] if found else None


def motion_state(n, s):
    brief = load(os.path.join(bdir(n), "brief.json"))
    d = os.path.join(sdir(n, s), "motion")
    f = os.path.join(d, "motion.json")
    rec = load(f) if os.path.exists(f) else None
    wf = load(os.path.join(sdir(n, s), brief["picks"][s] + ".json"))
    swipe = _swipe_of(brief)
    base = "/files/" + n + "/scenes/" + s + "/motion/"
    reading = MOTION_READING.get((n, s))
    return {"brief": n, "scene": s, "status": "reading" if reading and not reading.get("error") else (rec or {}).get("status") or "none",
            "error": (reading or {}).get("error"), "reading": reading, "motion": rec, "beats": _beats(wf),
            "swipe": {"file": os.path.basename(swipe), "seconds": round(probe_dur(swipe), 1)} if swipe else None,
            "urls": {k: base + v + ("?t=" + rec.get("tracked_at", "")) for k, v in (rec.get("files") or {}).items()} if rec else {},
            "camera": (load(os.path.join(d, "camera.json")).get("summary") if os.path.exists(os.path.join(d, "camera.json")) else None),
            "has_take": os.path.exists(os.path.join(sdir(n, s), "take.json"))}


def _read_motion(n, s, clip, start, end, kind, name=None):
    key = (n, s)
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "motion.py"), "scene", sdir(n, s), clip, "--from", str(start)]
                           + (["--to", str(end)] if end else []) + ["--kind", kind] + (["--name", name] if name else []),
                           capture_output=True, text=True, timeout=1800)
        if r.returncode:
            MOTION_READING[key] = {"error": (r.stderr or r.stdout).strip()[-400:] or "the motion reader failed"}
            return
        MOTION_READING.pop(key, None)
    except Exception as e:  # noqa: BLE001  shown on the page
        MOTION_READING[key] = {"error": str(e)}


def _program_motion(n, s):
    key = (n, s)
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "motion_program.py"), "scene", sdir(n, s)],
                           capture_output=True, text=True, timeout=1800)
        if r.returncode:
            MOTION_READING[key] = {"error": (r.stderr or r.stdout).strip()[-400:] or "the motion programmer failed"}
            return
        MOTION_READING.pop(key, None)
    except Exception as e:  # noqa: BLE001  shown on the page
        MOTION_READING[key] = {"error": str(e)}


def motion_program(n, s):
    """Our own motion, programmed from the scene's take: Claude writes the blocking, the figures act it out."""
    if MOTION_READING.get((n, s)) and not MOTION_READING[(n, s)].get("error"):
        raise RuntimeError("this scene's motion is already being made")
    if not os.path.exists(os.path.join(sdir(n, s), "take.json")):
        raise RuntimeError("this scene has no take written yet")
    MOTION_READING[(n, s)] = {"kind": "programmed", "file": "the take", "since": datetime.datetime.now().strftime("%H:%M:%S")}
    threading.Thread(target=_program_motion, args=(n, s), daemon=True).start()
    return motion_state(n, s)


def motion_start(n, s, clip, start=0.0, end=None, kind="phone", name=None):
    if MOTION_READING.get((n, s)) and not MOTION_READING[(n, s)].get("error"):
        raise RuntimeError("this scene's motion is already being read")
    MOTION_READING[(n, s)] = {"kind": kind, "file": name or os.path.basename(clip), "since": datetime.datetime.now().strftime("%H:%M:%S")}
    threading.Thread(target=_read_motion, args=(n, s, clip, start, end, kind, name), daemon=True).start()
    return motion_state(n, s)


def motion_upload(n, s, name, kind, data):
    """A phone video (or a 3D render) dropped on the scene: kept in the scene's motion folder and read."""
    d = os.path.join(sdir(n, s), "motion")
    os.makedirs(d, exist_ok=True)
    ext = os.path.splitext(name or "")[1].lower() or ".mp4"
    if ext not in (".mp4", ".mov", ".m4v", ".webm"):
        raise RuntimeError("a video please: .mp4, .mov, .m4v or .webm")
    f = os.path.join(d, "source" + ext)                  # the scene's motion clip (the one before it is replaced)
    with open(f, "wb") as out:
        out.write(data)
    return motion_start(n, s, f, 0.0, None, kind if kind in ("phone", "3d", "swipe") else "phone", os.path.basename(name or ""))


def motion_approve(n, s, by=None):
    import motion as MO
    MO.approve(sdir(n, s), by)
    return motion_state(n, s)


def versions(n):
    """The finished cut and each opening's version, newest render of each."""
    b = bdir(n)
    out = []
    cuts = sorted(glob.glob(os.path.join(b, "rough-cut-v*-sdr.mp4")),
                  key=lambda f: int(re.search(r"-v(\d+)-", f).group(1)) if re.search(r"-v(\d+)-", f) else 0)
    if cuts:
        out.append({"id": "control", "label": "Control", "file": os.path.relpath(cuts[-1], BRIEFS)})
    for d in sorted(glob.glob(os.path.join(b, "versions", "*"))):
        h = os.path.basename(d)
        f = sorted(glob.glob(os.path.join(d, "*-" + h + ".mp4")))
        if not f:
            continue
        title = h
        try:
            hb = load(os.path.join(b, "brief.json")).get("picks", {}).get(h)
            title = load(os.path.join(sdir(n, h), hb + ".json")).get("title") or h
        except Exception:  # noqa: BLE001
            pass
        out.append({"id": h, "label": title if title[:1] == "V" else h.replace("H", "V") + " · " + title,
                    "file": os.path.relpath(f[0], BRIEFS)})
    return out


# ONE ADDRESS (the owner, 8 Nov: "can we not just have this whole thing on one server?"). The Studio serves the storyboard
# board under /board/ and the approval page under /approve/. A request those pages make for their own absolute paths
# (/api/..., /files/...) carries the page as its Referer, so it goes back to the same app; the apps are untouched.
APPS = {"board": ST.BOARD, "approve": ST.APPROVE}
HOP = ("transfer-encoding", "connection", "content-length", "keep-alive", "x-frame-options")


def app_for(handler):
    """(app, path to send it) when this request belongs to the board or the approval page, else None."""
    path = urlparse(handler.path).path
    for name in APPS:
        if path == "/" + name or path.startswith("/" + name + "/"):
            rest = handler.path[len(name) + 1:]
            return name, rest if rest.startswith("/") else "/" + rest
    ref = urlparse(handler.headers.get("Referer") or "")
    if ref.netloc and ref.netloc == (handler.headers.get("Host") or ""):
        for name in APPS:
            if ref.path == "/" + name or ref.path.startswith("/" + name + "/"):
                SERVED[path] = name           # a script or style the app loaded: what it loads goes back to the app too
                return name, handler.path
        if ref.path in SERVED:
            SERVED[path] = SERVED[ref.path]
            return SERVED[ref.path], handler.path
    return None


SERVED = {}     # path -> app, for files an app's page loaded (their own requests name them as the Referer)


def proxy(handler, name, path):
    import http.client
    u = urlparse(APPS[name])
    body = handler.rfile.read(int(handler.headers.get("Content-Length") or 0) or 0) or None
    hdr = {k: v for k, v in handler.headers.items() if k.lower() not in ("host", "connection", "referer", "origin")}
    hdr["Host"] = u.netloc                      # the apps answer only their own address and origin
    if handler.headers.get("Origin"):
        hdr["Origin"] = f"{u.scheme}://{u.netloc}"
    if handler.headers.get("Referer"):
        hdr["Referer"] = f"{u.scheme}://{u.netloc}/"
    try:
        c = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=300)
        c.request(handler.command, path, body=body, headers=hdr)
        r = c.getresponse()
    except Exception as e:  # noqa: BLE001
        handler.send_response(502); handler.end_headers(); handler.wfile.write(f"{name} is not running: {e}".encode()); return
    handler.send_response(r.status)
    for k, v in r.getheaders():
        if k.lower() not in HOP:
            if k.lower() == "location" and v.startswith("/"):
                v = "/" + name + v                # a redirect stays inside the app
            handler.send_header(k, v)
    length = r.getheader("Content-Length")
    if length is not None:
        handler.send_header("Content-Length", length)
        handler.end_headers()
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            handler.wfile.write(chunk)
    else:
        data = r.read()
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        got = app_for(self)
        if got:
            return proxy(self, *got)
        u = urlparse(self.path)
        parts = [unquote(p) for p in u.path.strip("/").split("/") if p]
        if not parts or parts == ["studio"]:
            return self.send(200, open(os.path.join(HERE, "studio.html"), "rb").read(), "text/html; charset=utf-8")
        if parts == ["canvas"]:
            return self.send(200, open(os.path.join(HERE, "canvas.html"), "rb").read(), "text/html; charset=utf-8")
        if parts == ["api", "menu"]:
            return self.send(200, menu())
        if parts == ["api", "clipmodels"]:
            import gen_ref as GR
            return self.send(200, {"models": GR.clip_choices()})
        if parts[:2] == ["api", "clip"] and len(parts) == 4:
            return self.send(200, clip_reference(parts[2], parts[3]))
        if parts[:2] == ["api", "shotframe"] and len(parts) == 5:
            try:
                return self.file(shot_frame(parts[2], parts[3], parts[4]))
            except Exception as e:  # noqa: BLE001
                return self.send(404, {"error": str(e)})
        if parts[:2] == ["api", "motion"] and len(parts) == 4:
            return self.send(200, motion_state(parts[2], parts[3]))
        if parts[:2] == ["api", "productions"] and len(parts) == 2:
            return self.send(200, {"productions": link_productions(productions())})
        if parts[:2] == ["api", "versions"] and len(parts) == 3:
            return self.send(200, {"versions": versions(parts[2])})
        if parts[0] == "gen" and len(parts) >= 2:
            p = os.path.realpath(os.path.join(GEN, *parts[1:]))
            if not p.startswith(os.path.realpath(GEN)) or not os.path.isfile(p):
                return self.send(404, {"error": "not found"})
            return self.file(p)
        if parts[:2] == ["api", "brief"] and len(parts) == 3:
            return self.send(200, brief_state(parts[2]))
        if parts[0] == "files" and len(parts) >= 3:
            p = os.path.realpath(os.path.join(BRIEFS, *parts[1:]))
            if not p.startswith(os.path.realpath(BRIEFS)) or not os.path.isfile(p):
                return self.send(404, {"error": "not found"})
            return self.file(p)
        self.send(404, {"error": "not found"})

    def _other(self):
        got = app_for(self)
        if got:
            return proxy(self, *got)
        self.send(405, {"error": "method not allowed"})

    do_PUT = do_DELETE = do_PATCH = _other

    def file(self, p):
        ctype = {"mp4": "video/mp4", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                 "json": "application/json"}.get(p.rsplit(".", 1)[-1].lower(), "application/octet-stream")
        size = os.path.getsize(p)
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else 0
            end = int(b) if b else size - 1
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 16, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

    def do_POST(self):
        got = app_for(self)
        if got:
            return proxy(self, *got)
        u = urlparse(self.path)
        parts = [unquote(p) for p in u.path.strip("/").split("/") if p]
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0) or 0)
        try:
            if len(parts) == 5 and parts[:2] == ["api", "motion"]:
                n, s, act = parts[2], parts[3], parts[4]
                if act == "upload":
                    from urllib.parse import parse_qs
                    q = {k: v[0] for k, v in parse_qs(u.query).items()}
                    return self.send(200, motion_upload(n, s, q.get("name") or "phone.mp4", q.get("kind") or "phone", body))
                q = json.loads(body or b"{}")
                if act == "swipe":
                    swipe = _swipe_of(load(os.path.join(bdir(n), "brief.json")))
                    if not swipe:
                        return self.send(400, {"error": "this brief's swipe is not in its writing run"})
                    return self.send(200, motion_start(n, s, swipe, float(q.get("from") or 0), q.get("to") and float(q["to"]), "swipe"))
                if act == "approve":
                    return self.send(200, motion_approve(n, s, q.get("by")))
                if act == "program":
                    return self.send(200, motion_program(n, s))
            if len(parts) == 5 and parts[:2] == ["api", "scene"]:
                n, s, act = parts[2], parts[3], parts[4]
                if act == "run":
                    with LOCK:
                        if RUNNING.get((n, s)):
                            return self.send(409, {"error": "already running"})
                        RUNNING[(n, s)] = True
                    try:
                        return self.send(200, run_scene(n, s))
                    finally:
                        RUNNING.pop((n, s), None)
                if act == "save":
                    wf = json.loads(body)
                    brief = load(os.path.join(bdir(n), "brief.json"))
                    take = brief["picks"][s]
                    wf["take"] = take
                    save(os.path.join(sdir(n, s), take + ".json"), wf)
                    return self.send(200, scene_state(n, s, brief))
                if act == "take":
                    return self.send(200, {"take": new_take(n, s)})
                if act == "pick":
                    take = json.loads(body)["take"]
                    brief = load(os.path.join(bdir(n), "brief.json"))
                    if not os.path.exists(os.path.join(sdir(n, s), take + ".json")):
                        return self.send(400, {"error": "no such take"})
                    brief["picks"][s] = take
                    save(os.path.join(bdir(n), "brief.json"), brief)
                    return self.send(200, scene_state(n, s, brief))
            if parts[:2] == ["api", "shot"] and len(parts) == 4 and parts[3] in ("pick", "take"):
                import gen_ref as GR                  # a person's clip-model pick for one AI shot, and a new take on it
                name, model = parts[2], json.loads(body or b"{}").get("model")
                if parts[3] == "pick":
                    r = GR.set_pick(name, model)
                    return self.send(200, {"name": name, "clip_model": r.get("clip_model") or GR.DEFAULT})
                with LOCK:
                    if MAKING.get(name):
                        return self.send(409, {"error": "a take of this shot is already being made"})
                    MAKING[name] = True
                try:
                    return self.send(200, GR.remake(name, model))
                except SystemExit as e:
                    return self.send(400, {"error": str(e)})
                finally:
                    MAKING.pop(name, None)
            if parts[:2] == ["api", "package"] and len(parts) == 3:
                return self.send(200, package(parts[2]))
            if parts[:2] == ["api", "hyperframes"] and len(parts) == 3:
                q = json.loads(body or b"{}")
                return self.send(200, open_in_hyperframes(parts[2], q.get("version")))
            if parts[:2] == ["api", "produce"] and len(parts) == 3 and re.fullmatch(r"brief\d+", parts[2]):
                r = subprocess.run([sys.executable, os.path.join(HERE, "seed_from_brief.py"), parts[2]],
                                   capture_output=True, text=True, timeout=120)
                if r.returncode:
                    return self.send(500, {"error": (r.stderr or "could not set up production")[-300:]})
                return self.send(200, json.loads(r.stdout.strip().splitlines()[-1]))
        except Exception as e:  # shown on the canvas, never swallowed
            return self.send(500, {"error": str(e)})
        self.send(404, {"error": "not found"})


def main(argv):
    if not argv or argv[0] == "serve":
        port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8921
        print(f"Video Studio on http://127.0.0.1:{port} — the board at /board/, the approval page at /approve/")
        ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
    elif argv[0] == "run":
        print(json.dumps(run_scene(argv[1], argv[2]), indent=1))
    elif argv[0] == "package":
        print(json.dumps(package(argv[1]), indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
