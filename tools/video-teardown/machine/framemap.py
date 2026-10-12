"""THE FRAME MAP — the swipe, shot by shot and moment by moment (2026-10-01).

the owner: "in the source video, actually map out every single frame so when we
describe what happens in our version it's as close as possible to the swipe so
it becomes indistinguishable. the movement of the characters and everything
needs to be mimiced." The teardown record says what each stretch of the video
IS; this says what HAPPENS in it, with timings, so the storyboard can copy the
movement, the cuts and the layers rather than re-invent them.

    cuts      every hard cut, found in the pixels (ffmpeg scene change) — no model
    shots     the stretch between two cuts: a clip, its first / middle / last
              frame and a contact sheet, kept beside the run (media, never git)
    moments   one judge per shot (the strongest Gemini we hold, watching the clip
              at 8 fps) answers the frame-map prompt: who is in frame, the start
              and end frame as stills, the camera, every visible action with its
              time and body geometry, on-screen text, sound, and the edit

Writes `framemap/framemap.json` and `framemap/FRAME-MAP.md` in the run. A shot's
answer is cached by its span and the prompt version, so a re-run never re-asks.
Brand-agnostic: it reads only the run's own video and teardown record.

FRAME BY FRAME (the owner, 2026-10-08: "it needs to be frame by frame, by frame …
when we get to the frame generation … we can actually work with the real
frames … use those as the references"). Beside the shots:

    frames/   EVERY frame the judge watched — 8 a second, original resolution,
              `frames/<K##>/<K##>-<index>-<t seconds>.jpg` — and
              `frames/index.json` (shot, index, t, file per frame). A shot
              already extracted is skipped (its `.complete` marker).
    elements/ every person, place and prop the frame map names, cut out of
              those frames (frame_elements.py): `elements/<kind>-<slug>/` with
              the crops (the recorded position, padded 8%; no position = the
              full frame), `element.json` (shots, times, frames used, crops,
              the best frame) and `elements/index.json`.

THE DRIVE: frames/, shots/, elements/ and the two framemap text files are
copied to the run's library folder on the Drive, beside the teardown stages —
`the shared drive/swipes/<run>/teardown/framemap/` (run.json `library`).
Copy only, never a delete; a file already there at the same size is left alone.
Only a run in this machine's real working folder (runs/video-teardown/_work/,
workdir.py) reaches the Drive (tests and scratch runs never do). Media never
goes in git (_work/ is ignored; file_run.py files text only).

HOW PRODUCTION USES THEM: the elements step (3.2, elements_check.py `sheet`)
attaches each to-make person/set/prop's element folder as `swipe_frames`, so
the make step starts from the real frames; the first frames (4.4,
element_refs.py) carry the swipe frame they recreate as a COMPOSITION
reference.

    python3 framemap.py <teardown run dir> [--threshold 0.25] [--no-model] [--no-drive]
    python3 framemap.py <teardown run dir> --frames-only   frames + elements + Drive
                                                           from the framemap.json on file
"""
import argparse, concurrent.futures as cf, hashlib, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPTS = HERE.parent / "prompts" / "stage-1f-frame-map"
FPS = "8"


def prompt_file():
    files = sorted(PROMPTS.glob("stage1f-frame-map-v*-damon.md"),
                   key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    return files[-1]


def _sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def duration(video):
    r = _sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)])
    return float(r.stdout.strip())


def capture(video):
    """How the swipe was captured, measured — the look our pictures are finished
    to (the owner, 2026-10-01: "mara literally shot this video on iphone and the
    quality isn't good, that's perfect for what we want")."""
    r = _sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate,bit_rate,codec_name,pix_fmt:format=bit_rate",
             "-of", "json", str(video)])
    try:
        j = json.loads(r.stdout)
    except ValueError:
        return {}
    st = (j.get("streams") or [{}])[0]
    num, _, den = str(st.get("r_frame_rate") or "0/1").partition("/")
    br = st.get("bit_rate") or (j.get("format") or {}).get("bit_rate")
    return {"width": st.get("width"), "height": st.get("height"),
            "fps": round(float(num) / float(den or 1), 2) if num else None,
            "video_kbps": round(int(br) / 1000) if br else None,
            "codec": st.get("codec_name"), "pix_fmt": st.get("pix_fmt")}


def cuts(video, threshold=0.25):
    """Hard cuts, in seconds — where the picture changes more than `threshold`."""
    r = _sh(["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
             f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"])
    return [round(float(t), 3) for t in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def shots(video, threshold=0.25, min_len=0.2):
    end = duration(video)
    marks = [0.0] + [c for c in cuts(video, threshold) if 0 < c < end] + [end]
    out = []
    for a, b in zip(marks, marks[1:]):
        if b - a < min_len and out:          # a flash shorter than a few frames joins the shot before
            out[-1]["end"] = round(b, 3); continue
        out.append({"start": round(a, 3), "end": round(b, 3)})
    for i, s in enumerate(out, 1):
        s["id"] = f"K{i:02d}"
        s["seconds"] = round(s["end"] - s["start"], 3)
    return out


def cut_media(video, shot, folder):
    """The shot's clip, its first / middle / last frame and a contact sheet (4 per second)."""
    folder.mkdir(parents=True, exist_ok=True)
    sid, a, b = shot["id"], shot["start"], shot["end"]
    clip = folder / f"{sid}.mp4"
    if not clip.exists():
        _sh(["ffmpeg", "-y", "-v", "error", "-ss", str(a), "-to", str(b), "-i", str(video),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", str(clip)])
    stills = {}
    for name, t in (("first", a + 0.03), ("mid", (a + b) / 2), ("last", max(a, b - 0.06))):
        f = folder / f"{sid}-{name}.jpg"
        if not f.exists():
            _sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
                 "-frames:v", "1", "-vf", "scale=360:-2", str(f)])
        stills[name] = f.name
    sheet = folder / f"{sid}-sheet.jpg"
    if not sheet.exists():
        n = max(1, int(round(shot["seconds"] * 4)))
        cols = min(n, 8)
        rows = (n + cols - 1) // cols
        _sh(["ffmpeg", "-y", "-v", "error", "-ss", str(a), "-to", str(b), "-i", str(video),
             "-vf", f"fps=4,scale=180:-2,tile={cols}x{rows}", "-frames:v", "1", str(sheet)])
    return {"clip": clip.name, "stills": stills, "sheet": sheet.name}


REPEAT = 15.0     # mean pixel difference (0–255) under which two shots are one clip used twice


def _sig(path):
    from PIL import Image
    return Image.open(path).convert("L").resize((48, 85))


def repeats(shots_, folder):
    """Shots the swipe uses more than once — the same clip cut in again (a stock
    insert, a reused reaction). Measured on the middle stills; never two shots in
    a row (that is a jump cut, not a reuse). Each repeat points at the first use.
    2026-10-02: an earlier run's three phone inserts were one stock clip, made once."""
    try:
        from PIL import ImageChops, ImageStat
    except ImportError:
        return {}
    sig = {k["id"]: _sig(folder / k["stills"]["mid"]) for k in shots_ if (folder / k["stills"]["mid"]).exists()}
    out = {}
    ids = [k["id"] for k in shots_]
    for i, a in enumerate(ids):
        if a in out or a not in sig:
            continue
        for b in ids[i + 2:]:
            if b in out or b not in sig:
                continue
            if ImageStat.Stat(ImageChops.difference(sig[a], sig[b])).mean[0] < REPEAT:
                out[b] = a
    return out


def people_names(run_dir):
    try:
        import importlib.util as u
        sp = u.spec_from_file_location("cast_match", HERE / "cast_match.py")
        cm = u.module_from_spec(sp); sp.loader.exec_module(cm)
        tear = (Path(run_dir) / "stages" / "1-teardown.md").read_text()
        return list(cm.swipe_people(tear))
    except Exception:
        return []


def ask_shot(clip, shot, people, ask=None):
    if ask is None:
        os.environ["GEMINI_VIDEO_FPS"] = FPS
        import deepen
        ask = deepen.ask
    text = (prompt_file().read_text()
            .replace("{seconds}", f"{shot['seconds']:.2f}")
            .replace("{start}", f"{shot['start']:.2f}").replace("{end}", f"{shot['end']:.2f}")
            .replace("{people}", ", ".join(people) or "(none named — describe them plainly)"))
    return _one(ask(clip, text, want_json=True))


def _one(ans):
    """The judge sometimes wraps its one answer in a list — unwrap it."""
    if isinstance(ans, list) and len(ans) == 1 and isinstance(ans[0], dict):
        return ans[0]
    return ans


LONG_SHOT = 10.0   # seconds: a shot longer than this is watched in windows
WINDOW = 8.0       # seconds per window


def merge_windows(parts, shot_start):
    """One shot's answer from its windows' answers. The prompt gives every time from the start of what the judge
    watched — here a window — so each moment, text and sound is shifted by where its window sits in the shot, then
    laid in time order. People, camera and look from the first window that answered; the start frame from the first
    and the end frame from the last."""
    ok = [(w, a) for w, a in parts if a and "error" not in a]
    if not ok:
        return parts[0][1] if parts else None
    first, last = ok[0][1], ok[-1][1]

    def shifted(key):
        rows = []
        for w, a in ok:
            off = round(w["start"] - shot_start, 3)
            for r in a.get(key) or []:
                if not isinstance(r, dict):
                    continue
                r = {**r, "window": w["id"]}
                for k in ("t", "until"):
                    if isinstance(r.get(k), (int, float)):
                        r[k] = round(r[k] + off, 2)
                rows.append(r)
        return sorted(rows, key=lambda r: r.get("t") if isinstance(r.get("t"), (int, float)) else 0)

    edits = [a.get("edit") for _, a in ok if a.get("edit")]
    return {"who": first.get("who"), "start_frame": first.get("start_frame"), "end_frame": last.get("end_frame"),
            "camera": first.get("camera"), "moments": shifted("moments"), "on_screen": shifted("on_screen"),
            "sound": shifted("sound"), "edit": edits[0] if len(edits) == 1 else edits, "windows": len(ok)}


def build(run_dir, threshold=0.25, model=True, ask=None, workers=5, frames=True, drive=True):
    d = Path(run_dir)
    video = d / "source.mp4"
    out = d / "framemap"
    media = out / "shots"
    cache_p = out / "answers.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    pname = prompt_file().name
    people = people_names(d)
    sh = shots(video, threshold)
    for s in sh:
        s.update(cut_media(video, s, media))

    def one(s):
        key = hashlib.md5(f"{pname}|{s['start']}|{s['end']}".encode()).hexdigest()[:12]
        if key in cache:
            return s["id"], key, _one(cache[key])
        if not model:
            return s["id"], key, None
        try:
            return s["id"], key, ask_shot(media / s["clip"], s, people, ask)
        except Exception as e:
            return s["id"], key, {"error": f"{type(e).__name__}: {str(e)[:200]}"}

    # A LONG SHOT IS WATCHED IN WINDOWS (2026-10-08). One judge per shot gave a 90 s single-camera press
    # conference twelve moments with 40 s gaps — nothing to copy — and production improvised (the owner: "the whole
    # point … is to go frame by frame … so that we're not overcomplicating and doing all this adjustment").
    # A shot past LONG_SHOT seconds is asked in WINDOW-second windows and the moments merged on the swipe clock.
    jobs = []
    for s in sh:
        if s["seconds"] <= LONG_SHOT:
            jobs.append((s, None)); continue
        a = s["start"]
        while a < s["end"] - 0.5:
            b = min(s["end"], a + WINDOW)
            w = {"id": f"{s['id']}w{len([j for j in jobs if j[0] is s]) + 1:02d}", "start": round(a, 3),
                 "end": round(b, 3), "seconds": round(b - a, 3)}
            wclip = media / f"{w['id']}.mp4"
            if not wclip.exists():
                _sh(["ffmpeg", "-y", "-v", "error", "-ss", str(w["start"]), "-to", str(w["end"]), "-i", str(video),
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", str(wclip)])
            w["clip"] = wclip.name
            jobs.append((s, w)); a = b

    def one_job(job):
        s, w = job
        return (s, w) + one(w or s)[1:]

    got = {}
    with cf.ThreadPoolExecutor(workers) as ex:
        for s, w, key, ans in ex.map(one_job, jobs):
            if ans and "error" not in ans:
                cache[key] = ans
            got.setdefault(s["id"], []).append((w, ans))
    for s in sh:
        parts = got.get(s["id"]) or []
        if len(parts) == 1 and parts[0][0] is None:
            s["map"] = parts[0][1]; continue
        s["map"] = merge_windows([(w, a) for w, a in parts], s["start"])
        s["windows"] = [{"id": w["id"], "start": w["start"], "end": w["end"],
                         "ok": bool(a) and "error" not in a} for w, a in parts]
    rep = repeats(sh, media)
    for s_ in sh:
        if s_["id"] in rep:
            s_["same_as"] = rep[s_["id"]]
    out.mkdir(parents=True, exist_ok=True)
    cache_p.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    doc = {"video": video.name, "seconds": round(duration(video), 3), "threshold": threshold,
           "prompt": pname, "model": "gemini (deepen.ask) at " + FPS + " fps", "people": people,
           "capture": capture(video),
           "cuts": [s["start"] for s in sh[1:]], "repeats": rep, "shots": sh}
    (out / "framemap.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    (out / "FRAME-MAP.md").write_text(markdown(doc))
    if frames:
        frames_and_elements(d, doc, drive=drive, workers=workers)
    return doc


# ---------------------------------------------------------------- frame by frame

FRAME_NAME = re.compile(r"^(K\d+)-(\d+)-([0-9.]+)\.jpg$")


def frame_name(sid, i, t):
    """K03-0012-20.400.jpg — the shot, the frame's index inside it, its time in the swipe."""
    return f"{sid}-{i:04d}-{t:.3f}.jpg"


def extract_frames(video, shots_, out, workers=4):
    """EVERY frame of every shot at the analysis rate (FPS a second), original
    resolution, JPEG ~85 — `frames/<K>/<K>-<index>-<t>.jpg` — and
    `frames/index.json`. A shot already extracted (its `.complete` marker) is
    skipped. -> the index rows."""
    fdir = Path(out) / "frames"
    fdir.mkdir(parents=True, exist_ok=True)

    def one(s):
        sid, a, b = s["id"], float(s["start"]), float(s["end"])
        d = fdir / sid
        done = d / ".complete"
        if not done.exists():
            tmp = d / "_tmp"
            tmp.mkdir(parents=True, exist_ok=True)
            for f in tmp.glob("*.jpg"):          # a half-finished extraction of our own
                f.unlink()
            _sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(video),
                 "-vf", f"fps={FPS}", "-q:v", "3", str(tmp / "%05d.jpg")])
            got = sorted(tmp.glob("*.jpg"))
            for i, f in enumerate(got):
                f.replace(d / frame_name(sid, i, a + i / float(FPS)))
            tmp.rmdir()
            if got:
                done.write_text(str(len(got)))
        rows = []
        for f in sorted(d.glob(f"{sid}-*.jpg")):
            m = FRAME_NAME.match(f.name)
            if m:
                rows.append({"shot": sid, "index": int(m.group(2)), "t": float(m.group(3)),
                             "file": f"frames/{sid}/{f.name}"})
        return sorted(rows, key=lambda r: r["index"])

    rows = []
    with cf.ThreadPoolExecutor(max(1, workers)) as ex:
        for r in ex.map(one, shots_):
            rows += r
    (fdir / "index.json").write_text(json.dumps(
        {"fps": float(FPS), "count": len(rows), "frames": rows}, indent=0))
    return rows


def drive_home(run_dir):
    """The run's framemap folder on the Drive — beside the teardown stages in the
    run's library folder (run.json `library`, else where run.py's library_home
    puts it): `the shared drive/swipes/<run>/teardown/framemap/`."""
    d = Path(run_dir)
    st = {}
    try:
        st = json.loads((d / "run.json").read_text())
    except (OSError, ValueError):
        pass
    if st.get("library"):
        return Path(st["library"]) / "teardown" / "framemap"
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import library as L
    v = Path(st.get("video") or "")
    if "creators" in v.parts and "posts" in v.parts:
        return v.parent / "teardown" / "framemap"
    return L.root() / "swipes" / L.slug(st.get("label") or st.get("slug") or d.name) / "teardown" / "framemap"


MIRROR_FILES = ("framemap.json", "FRAME-MAP.md")
MIRROR_DIRS = ("frames", "shots", "elements")


def mirror(run_dir, dest=None):
    """Copy the frame map's text, frames, shots and elements to the Drive.
    COPY ONLY — nothing on the mount is ever deleted or renamed (a trashed
    folder comes back with a new id and kills every link). Same name, same
    size: left alone. Only a run in this machine's working folder
    (runs/video-teardown/_work/) reaches the Drive unless `dest` is given.
    -> (dest, copied, kept) or None."""
    import shutil
    import workdir
    d = Path(run_dir)
    if dest is None:
        if d.resolve().parent != workdir.root().resolve():
            return None
        dest = drive_home(d)
    dest = Path(dest)
    src = d / "framemap"
    wanted = [src / n for n in MIRROR_FILES if (src / n).is_file()]
    for sub in MIRROR_DIRS:
        if (src / sub).is_dir():
            wanted += [f for f in sorted((src / sub).rglob("*")) if f.is_file()]
    copied = kept = 0
    for f in wanted:
        rel = f.relative_to(src)
        if any(p.startswith(".") or p == "_tmp" for p in rel.parts) or f.name.endswith(".gemini-uri.json"):
            continue
        out = dest / rel
        if out.is_file() and out.stat().st_size == f.stat().st_size:
            kept += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
        copied += 1
    return dest, copied, kept


def frames_and_elements(run_dir, doc=None, drive=True, workers=4):
    """frames/ → elements/ → the Drive, from the frame map on file. Never asks
    the model. -> a one-line note."""
    d = Path(run_dir)
    doc = doc or json.loads((d / "framemap" / "framemap.json").read_text())
    rows = extract_frames(d / "source.mp4", doc["shots"], d / "framemap", workers)
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import frame_elements as FE
    idx = FE.build(d)
    note = f"{len(rows)} frames · {len(idx['elements'])} elements"
    if drive:
        try:
            got = mirror(d)
            note += (f" · Drive: {got[1]} copied, {got[2]} already there → {got[0]}" if got
                     else " · Drive: not a machine run, not mirrored")
        except Exception as e:                   # the Drive is never fatal to the map
            note += f" · Drive: NOT mirrored — {type(e).__name__}: {e}"
    return note


def markdown(doc):
    L = [f"# Frame map — {doc['video']} ({doc['seconds']} s, {len(doc['shots'])} shots)", "",
         f"Cuts found in the pixels (scene change > {doc['threshold']}); each shot watched at "
         f"{FPS} fps with `{doc['prompt']}`.", "",
         "**Captured as:** " + ", ".join(f"{k} {v}" for k, v in (doc.get("capture") or {}).items() if v), ""]
    for s in doc["shots"]:
        m = s.get("map") or {}
        L += [f"## {s['id']} · {s['start']:.2f}–{s['end']:.2f} s ({s['seconds']:.2f} s)"
              + (f" · the same clip as {s['same_as']}" if s.get("same_as") else ""), ""]
        if "error" in m:
            L += [f"_not mapped: {m['error']}_", ""]; continue
        if not m:
            L += ["_not mapped yet_", ""]; continue
        cam = m.get("camera") or {}
        L += [f"**Who:** {', '.join(m.get('who') or [])}",
              f"**Camera:** {cam.get('height','')} · {cam.get('distance','')} · {cam.get('held','')} · move: {cam.get('move','')}",
              f"**Start frame:** {m.get('start_frame','')}", f"**End frame:** {m.get('end_frame','')}", "",
              "| t | who | does | face |", "|---|---|---|---|"]
        L += [f"| {x.get('t')} | {x.get('who','')} | {str(x.get('does','')).replace('|','/')} | {str(x.get('face','')).replace('|','/')} |"
              for x in m.get("moments") or []]
        if m.get("on_screen"):
            L += ["", "**On screen:** " + "; ".join(f"{x.get('t')}–{x.get('until')} s \"{x.get('text')}\" ({x.get('where')}, {x.get('look')})" for x in m["on_screen"])]
        if m.get("sound"):
            L += ["", "**Sound:** " + "; ".join(f"{x.get('t')} s {x.get('what')}" for x in m["sound"])]
        L += ["", f"**Edit:** {m.get('edit','')}", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--threshold", type=float, default=0.25)
    ap.add_argument("--no-model", action="store_true", help="cuts and stills only")
    ap.add_argument("--no-drive", action="store_true", help="do not copy to the Drive")
    ap.add_argument("--frames-only", action="store_true",
                    help="frames + elements + Drive from the framemap.json on file (no model, no re-map)")
    a = ap.parse_args()
    if a.frames_only:
        print(frames_and_elements(a.run_dir, drive=not a.no_drive))
        sys.exit(0)
    doc = build(a.run_dir, a.threshold, model=not a.no_model, frames=False)
    print(frames_and_elements(a.run_dir, doc, drive=not a.no_drive))
    bad = [s["id"] for s in doc["shots"] if not s.get("map") or "error" in (s.get("map") or {})]
    print(f"{len(doc['shots'])} shots · {len(doc['cuts'])} cuts · mapped {len(doc['shots']) - len(bad)}"
          + (f" · NOT mapped: {', '.join(bad)}" if bad else ""))
