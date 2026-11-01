#!/usr/bin/env python3
"""v2.py — the video edit, second version, BESIDE run.py (v1 stays the default).

    python3 machine/v2.py ad --control <kit> --hook <kit> [--hook <kit> ...] --brand <b> --label <l> [--runs-root R]
            # 1st call: everything is cut and a ROUGH PREVIEW is made, then it stops for a yes
    python3 machine/v2.py ad ... --yes
            # after the yes: the control renders ONCE in full; each hook renders only its new opening
            # and is joined onto the finished control
    python3 machine/v2.py share <v2-run> <version>   # ONE share copy, only for the picked version, never bigger than its master
    python3 machine/v2.py clean <v2-run>             # once the ad ships: this run's own work files go

What changed from v1 (the 2026-10-18 audit, deep-edit.json):
  1. A hook is the control with a new opening. v1 rendered every hook in full (97% of every
     hook render repeated the control). v2 finds where the hook's cut sheet becomes the
     control's (shifted by the hook's length), renders only the part before that, and joins
     it onto the control's own frames with a stream copy. Every joined hook is then checked
     frame by frame against the control after the opening; a mismatch falls back to a
     full render, never ships a wrong join.
  2. Whatever depends only on the clips is done once and kept on disk (.cache/v2, gitignored):
     face tracks (faces.py's cache was in-memory), the scene read, voice/song levelling,
     transcription, the keyframe fix. A hook run finds them already there.
  3. One render at a time (a lock across processes: 35.6 fps alone vs 14.6 fps side by side);
     every clip is re-cut with a keyframe each second, once (the engine warned on 57 of 60
     clips); --crf is pinned, so the same sheet gives the same file.
  4. Rough preview (draft, 15 fps) before any full render; renders are keyed by what is in
     them, so a song swap re-renders only what changed; one share copy, picked version only.
  5. The reviewer gets the brief, the hook text, the end card and only the sheet lines it
     checks; frames are taken at caption times with the words expected on each; a BLOCKER
     or FIX holds the version (it is not marked ready). Prompt caching is off on every
     claude -p it starts.
  6. `clean` removes only this run's own work folders.

It reuses v1's cut, assembly, helpers, gate, compose and master exactly as they are —
only the order of work, the caches and the render change. Output:
runs/video-edit/<brand>/<label>/ with v2.json, REPORT.md and deliverable/.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
sys.path.insert(0, str(HERE))
os.environ["DISABLE_PROMPT_CACHING"] = "1"   # every claude -p this process starts (5)

import run as R  # noqa: E402  — v1, used as it is
import assemble as A  # noqa: E402
import compose as C  # noqa: E402
import cutsheet as CS  # noqa: E402

CACHE = TOOL / ".cache" / "v2"
FPS_PREVIEW = 15
CRF_FINAL = 18        # pinned: same sheet, same file (v1 drifted crf15 → crf18 under one quality word)
CRF_PREVIEW = 30
KEYINT_S = 1.0        # a keyframe every second in every source clip
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".webm")
TIMES: list = []      # (step, seconds) for the report


# ---------------------------------------------------------------- small helpers
def log(msg: str) -> None:
    print(msg, flush=True)


@contextlib.contextmanager
def timed(step: str):
    t0 = time.time()
    yield
    TIMES.append((step, round(time.time() - t0, 1)))
    log(f"  · {step}: {time.time() - t0:.1f}s")


def sh(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


_MD5 = None


def md5(p: Path) -> str:
    """md5 of a file, remembered by (real path, size, mtime) so big clips are read once."""
    global _MD5
    p = Path(p).resolve()
    f = CACHE / "md5.json"
    if _MD5 is None:
        _MD5 = json.loads(f.read_text()) if f.exists() else {}
    st = p.stat()
    k = f"{p}|{st.st_size}|{int(st.st_mtime)}"
    if k not in _MD5:
        h = hashlib.md5()
        with open(p, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""):
                h.update(b)
        _MD5[k] = h.hexdigest()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(_MD5))
    return _MD5[k]


def key_of(*parts) -> str:
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:20]


def link_or_copy(src, dst, *a, **kw):
    """compose's asset copy, as a hard link: v1 copied 19 GB of byte-identical kit clips."""
    dst = Path(dst)
    if dst.exists():
        dst.unlink()
    try:
        os.link(Path(src).resolve(), dst)
    except OSError:
        shutil.copy2(src, dst)
    return str(dst)


class _ShutilLinks:
    copy2 = staticmethod(link_or_copy)

    def __getattr__(self, name):
        return getattr(shutil, name)


C.shutil = _ShutilLinks()


def probe_frames_fps(video: Path) -> tuple[int, float]:
    out = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
              "stream=nb_read_packets,r_frame_rate", "-of", "json", video]).stdout
    s = json.loads(out)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return int(s["nb_read_packets"]), float(n) / float(d)


def keyframes(video: Path) -> list[float]:
    out = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-skip_frame", "nokey", "-show_entries",
              "frame=pts_time", "-of", "csv=p=0", video]).stdout
    vals = [x.strip().strip(",") for x in out.split()]
    return sorted(float(x) for x in vals if x and x != "N/A")


# ---------------------------------------------------------------- 2. disk caches over v1's helpers
def install_caches() -> None:
    import faces as FC
    import thumbs as TH

    track0 = FC.track

    def track(video, t0, seconds, fps=5.0):
        f = CACHE / "faces" / f"{key_of(md5(video), round(float(t0), 3), round(float(seconds), 3), fps)}.json"
        if f.exists():
            STATS["faces_hit"] += 1
            return json.loads(f.read_text())
        got = track0(video, t0, seconds, fps)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(got))
        STATS["faces_miss"] += 1
        return got
    FC.track = track

    scene0 = TH.scene

    def scene(frame):
        f = CACHE / "scenes" / f"{md5(frame)}.json"
        if f.exists():
            STATS["scene_hit"] += 1
            return json.loads(f.read_text())
        got = scene0(frame)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(got))
        STATS["scene_miss"] += 1
        return got
    TH.scene = scene

    lv0, lc0 = R.level_voice, R.level_clip

    def level_voice(src, work, target=-16.0):
        work = Path(work); work.mkdir(parents=True, exist_ok=True)
        c = CACHE / "level" / f"{md5(src)}_{target}.wav"
        if not c.exists():
            got = lv0(src, CACHE / "level" / "tmp", target)
            c.parent.mkdir(parents=True, exist_ok=True); Path(got).replace(c)
            STATS["level_miss"] += 1
        else:
            STATS["level_hit"] += 1
        out = work / "voice.level.wav"
        link_or_copy(c, out)
        return out
    R.level_voice = level_voice

    def level_clip(src, work, target=-16.0):
        c = CACHE / "level" / f"{md5(src)}_{target}{Path(src).suffix}"
        if not c.exists():
            got = lc0(src, CACHE / "level", target)
            Path(got).replace(c)
        out = Path(work) / f"{Path(src).stem}.level.mp4"
        link_or_copy(c, out)
        return out
    R.level_clip = level_clip

    wf0 = R.words_for

    def words_for(kit, kit_dir, work):
        v = kit.get("voice") or {}
        if v.get("words"):
            return wf0(kit, kit_dir, work)
        c = CACHE / "words" / f"{md5(Path(kit_dir) / v['src'])}.json"
        if c.exists():
            return json.loads(c.read_text())
        got = wf0(kit, kit_dir, work)
        c.parent.mkdir(parents=True, exist_ok=True); c.write_text(json.dumps(got))
        return got
    R.words_for = words_for


STATS = {k: 0 for k in ("faces_hit", "faces_miss", "scene_hit", "scene_miss", "level_hit", "level_miss",
                        "gop_fixed", "gop_reused", "renders", "renders_reused")}


# ---------------------------------------------------------------- 3. keyframes fixed once, renders one at a time
def fixed_clip(src: Path) -> Path:
    """The same clip with a keyframe every second — once per clip, shared by every hook and song swap."""
    if src.suffix.lower() not in VIDEO_EXT:
        return src
    out = CACHE / "gop" / f"{md5(src)}{src.suffix.lower()}"
    if out.exists():
        STATS["gop_reused"] += 1
        return out
    ks = keyframes(src)
    dur = R.CS.probe_seconds(src) or 0
    gaps = [b - a for a, b in zip(ks, ks[1:] + [dur])] if ks else [dur]
    if max(gaps or [0]) <= KEYINT_S * 1.5:
        return src
    _, fps = probe_frames_fps(src)
    g = max(1, round(fps * KEYINT_S))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part" + out.suffix)
    r = sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0", "-c:v", "libx264", "-crf", "14", "-preset", "fast",
            "-g", g, "-keyint_min", g, "-sc_threshold", "0", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", tmp])
    if r.returncode:
        return src
    tmp.replace(out)
    STATS["gop_fixed"] += 1
    return out


def kit_view(kit_dir: Path, dest: Path) -> Path:
    """The kit as the edit sees it: every file a link to the original, every video clip a link
    to its keyframe-fixed copy. The kit itself is never written to."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    def walk(src: Path, out: Path):
        for p in sorted(src.iterdir()):
            q = out / p.name
            if p.is_dir():
                q.mkdir(); walk(p, q)
            else:
                real = p.resolve()
                q.symlink_to(fixed_clip(real) if real.suffix.lower() in VIDEO_EXT else real)
    walk(kit_dir, dest)
    return dest


@contextlib.contextmanager
def one_render_at_a_time():
    CACHE.mkdir(parents=True, exist_ok=True)
    with open(CACHE / "render.lock", "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def compose(sheet: dict, kit_dir: Path, project: Path, captions: bool, duration: float | None = None) -> Path:
    C.compose(sheet, kit_dir, project, captions=captions)
    if duration is not None:   # only the opening: the page ends where the hook meets the control
        html = (project / "index.html").read_text()
        html = re.sub(r'(data-composition-id="[^"]*"[^>]*?data-duration=")[^"]*(")', rf"\g<1>{duration:.6f}\g<2>", html, count=1)
        (project / "index.html").write_text(html)
    return project


def render(project: Path, out: Path, quality: str, crf: int, fps: int | None, store: Path) -> tuple[Path, bool]:
    """Render a composed page. Keyed by what is in it (page + assets + settings): the same
    page is never rendered twice — a song swap re-renders only the pages it changed."""
    assets = sorted((str(p.relative_to(project)), p.stat().st_size) for p in (project / "assets").rglob("*") if p.is_file())
    k = key_of((project / "index.html").read_text(), assets, quality, crf, fps)
    hit = store / f"{k}.mp4"
    if hit.exists():
        STATS["renders_reused"] += 1
        link_or_copy(hit, out)
        return out, True
    store.mkdir(parents=True, exist_ok=True)
    part = store / f"{k}.part.mp4"   # a killed render never leaves a file that looks finished
    cmd = ["hyperframes", "render", project, "--output", part, "--quality", quality, "--crf", crf, "--quiet"] + (["--fps", fps] if fps else [])
    with one_render_at_a_time():
        for c in (["hyperframes", "lint", project], cmd):
            r = sh(c)
            (project.parent / f"{project.name}.{c[1]}.log").write_text(r.stdout + r.stderr)
            if r.returncode:
                raise SystemExit(f"{c[1]} failed — see {project.parent / (project.name + '.' + c[1] + '.log')}")
    part.replace(hit)
    STATS["renders"] += 1
    out.parent.mkdir(parents=True, exist_ok=True)
    link_or_copy(hit, out)
    return out, False


# ---------------------------------------------------------------- the cut (v1's, cached)
def cut(kit_dir: Path, brand: str, label: str, work: Path) -> dict:
    controls = R.controls_for(None)
    kit, red = R.gather(kit_dir)
    if red:
        raise SystemExit("\n".join("RED   " + r for r in red))
    work.mkdir(parents=True, exist_ok=True)
    sheet = R.auto_cut(kit, kit_dir, work, controls, brand, label)
    A.assemble(sheet, kit, controls, brand)
    R.helpers_pass(sheet, kit_dir, controls)
    red = CS.check(sheet, kit_dir)
    if red:
        raise SystemExit("\n".join("RED   " + r for r in red) + "\nnothing renders red")
    sheet["_kit"] = kit
    return sheet


# ---------------------------------------------------------------- 1. where a hook becomes the control
_SKIP = {"id", "face_track", "face_track_frames", "face_track_fps", "face_track_by", "face_track_space", "scene_read",
         "placed", "placement", "moved", "why", "start", "end", "at", "t", "with"}


def _timed_items(sheet: dict) -> list[tuple[str, dict]]:
    out = [("picture", c) for c in sheet.get("picture") or []]
    out += [("word", w) for w in (sheet.get("captions") or {}).get("words") or []]
    out += [("overlay", o) for o in sheet.get("overlays") or []]
    out += [("sfx", s) for s in sheet.get("sfx") or []]
    for k, rows in (sheet.get("layers") or {}).items():
        out += [(f"layer.{k}", r) for r in rows or [] if isinstance(r, dict)]
    for e in _element_rows(sheet):
        if isinstance(e, dict) and "start" in e:
            out.append(("element", e))
    return out


def _start(d: dict) -> float:
    return _num(d.get("start", d.get("at", 0)))


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _end(d: dict) -> float:
    if "end" in d:
        return _num(d["end"])
    return _start(d) + _num(d.get("duration", d.get("for", 0)))


def _sig(kind: str, d: dict, shift: float) -> str:
    body = {k: (Path(v).name if isinstance(v, str) and ("/" in v) else v) for k, v in d.items() if k not in _SKIP}
    return json.dumps([kind, round(_start(d) - shift, 2), round(_end(d) - shift, 2), body], sort_keys=True, default=str)


def split_point(hook: dict, control: dict) -> tuple[float, float, list[str]]:
    """(shift, D, what differs): the hook is the control shifted by `shift` seconds from hook
    time D on. D is the end of the last thing in the hook that the control does not have."""
    shift = round(CS.end_of(hook) - CS.end_of(control), 3)
    have = {_sig(k, d, 0.0) for k, d in _timed_items(control)}
    D, diff = 0.0, []
    for k, d in _timed_items(hook):
        if _sig(k, d, shift) not in have:
            D = max(D, _end(d))
            diff.append(f"{k} {d.get('id') or d.get('text') or ''} {_start(d):.2f}-{_end(d):.2f}s")
    return shift, round(D, 3), diff


# ---------------------------------------------------------------- the joins
def audio_wav(video: Path, out: Path, t0: float = 0.0, t1: float | None = None) -> Path:
    cmd = ["ffmpeg", "-v", "error", "-y"] + (["-ss", f"{t0:.6f}"] if t0 else []) + ["-i", video] + \
          (["-t", f"{t1 - t0:.6f}"] if t1 is not None else []) + ["-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", out]
    r = sh(cmd)
    if r.returncode:
        raise SystemExit(r.stderr)
    return out


def master_audio(wav: Path, out: Path, mix: dict) -> Path:
    """v1's master (−14 LUFS, −1 dBTP, two passes) on the sound alone — seconds, not a 500 MB rewrite."""
    lufs, tp = mix.get("lufs", -14), mix.get("true_peak_db", -1)
    af = f"loudnorm=I={lufs}:TP={tp - 0.5}:LRA=11"
    err = sh(["ffmpeg", "-nostats", "-v", "info", "-i", wav, "-af", af + ":print_format=json", "-f", "null", "-"]).stderr
    m = json.loads(err[err.rindex("{"): err.rindex("}") + 1])
    af2 = (af + f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
           f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
           f",alimiter=limit={10 ** ((tp - 0.3) / 20):.4f}:level=false")
    r = sh(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", af2, "-ar", "48000", "-c:a", "aac", "-b:a", R.AAC_MASTER, out])
    if r.returncode:
        raise SystemExit(r.stderr)
    return out


def mux(video: Path, audio: Path, out: Path) -> Path:
    r = sh(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c", "copy",
            "-shortest", "-movflags", "+faststart", out])
    if r.returncode:
        raise SystemExit(r.stderr)
    return out


def stitch(head: Path, control_raw: Path, k_ctrl: float, out: Path, mix: dict, tmp: Path) -> Path:
    """head (hook time 0 → its end) + the control's own frames from keyframe k_ctrl on, video
    stream-copied; the sound joined at the same sample and mastered once."""
    tmp.mkdir(parents=True, exist_ok=True)
    body = tmp / "body.mp4"
    r = sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{k_ctrl:.6f}", "-i", control_raw, "-map", "0:v:0", "-c", "copy",
            "-avoid_negative_ts", "make_zero", body])
    if r.returncode:
        raise SystemExit(r.stderr)
    lst = tmp / "list.txt"   # the concat demuxer keeps clean timestamps (a joined .ts did not: frames read wrong)
    lst.write_text(f"file '{Path(head).resolve()}'\nfile '{body.resolve()}'\n")
    vid = tmp / "video.mp4"
    r = sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-map", "0:v:0", "-c", "copy", "-movflags", "+faststart", vid])
    if r.returncode:
        raise SystemExit(r.stderr)
    hw, bw = audio_wav(head, tmp / "head.wav"), audio_wav(control_raw, tmp / "body.wav", t0=k_ctrl)
    joined = tmp / "sound.wav"
    sh(["ffmpeg", "-v", "error", "-y", "-i", hw, "-i", bw, "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", "-c:a", "pcm_s16le", joined])
    return mux(vid, master_audio(joined, tmp / "sound.m4a", mix), out)


def psnr_at(a: Path, ta: float, b: Path, tb: float) -> float | None:
    err = sh(["ffmpeg", "-v", "info", "-ss", f"{ta:.3f}", "-i", a, "-ss", f"{tb:.3f}", "-i", b, "-frames:v", "1",
              "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-"]).stderr
    m = re.search(r"average:(\S+)", err)
    if not m:
        return None
    return float("inf") if m.group(1) == "inf" else float(m.group(1))


def same_after_opening(hook_mp4: Path, control_mp4: Path, shift: float, from_s: float, n: int = 12) -> dict:
    """The proof: the hook's frames after its opening, against the control's at the same moment."""
    dur = R.CS.probe_seconds(control_mp4) or 0
    start = from_s - shift + 0.2
    ts = [start + (dur - 0.5 - start) * i / (n - 1) for i in range(n)]
    rows = []
    for t in ts:
        v = psnr_at(hook_mp4, t + shift, control_mp4, t)
        if v is None or v < 60:   # one read can fail under load: read it again before calling it different
            v = psnr_at(hook_mp4, t + shift, control_mp4, t)
        rows.append({"control_s": round(t, 2), "hook_s": round(t + shift, 2), "psnr": v})
    ok = all(r["psnr"] is not None and r["psnr"] >= 60 for r in rows)
    return {"identical": ok, "samples": rows}


# ---------------------------------------------------------------- checks + 5. the reviewer
def checks(video: Path, sheet: dict, head_s: float | None = None) -> list[dict]:
    want, have = CS.end_of(sheet), CS.probe_seconds(video) or 0
    res = [{"check": "length matches the sheet", "pass": abs(have - want) < 0.25, "detail": f"{have:.2f}s rendered, {want:.2f}s on the sheet"}]
    span = ["-t", f"{head_s + 1:.2f}"] if head_s else []   # a joined hook: only its new opening is new picture
    black = sh(["ffmpeg", "-v", "info"] + span + ["-i", video, "-vf", "blackdetect=d=0.2:pix_th=0.05", "-an", "-f", "null", "-"]).stderr
    res.append({"check": "picture never goes black" + (" (new opening)" if head_s else ""), "pass": "black_start" not in black,
                "detail": "no black frames" if "black_start" not in black else "black frames found"})
    lufs, tp = R.loudness(video)
    mix = sheet.get("mix") or {"lufs": -14, "true_peak_db": -1}
    res.append({"check": "mix mastered", "pass": lufs is not None and abs(lufs - mix.get("lufs", -14)) <= 1.0 and tp is not None and tp <= mix.get("true_peak_db", -1) + 0.1,
                "detail": f"{lufs} LUFS, {tp} dBTP"})
    return res


def caption_lines(sheet: dict) -> list[dict]:
    """The caption pieces exactly as compose puts them on screen (2-4 words each), not whole sung lines."""
    caps = sheet.get("captions") or {}
    L = C.look_of(sheet)
    quiet = [(c["start"], c["start"] + c["duration"]) for c in sheet.get("picture") or [] if c.get("kind") in C.TEXT_KINDS]
    quiet += [(o["start"], o["start"] + o["duration"]) for o in sheet.get("overlays") or [] if o.get("kind") == "hook"]
    return [{"start": l[0]["start"], "end": l[-1]["end"], "words": " ".join(x["text"] for x in l)}
            for l in C.caption_lines(caps.get("words") or [], L.get("max_words", 4))
            if not any(a <= (l[0]["start"] + l[-1]["end"]) / 2 < b for a, b in quiet)]   # compose shows no caption under the hook or a text plate


def _element_rows(sheet: dict) -> list:
    """`elements` is a list of rows on some sheets and a plain true/false on others (the cut sheet
    reads it as a flag) — only a list has rows. A true here used to crash the review step."""
    e = sheet.get("elements")
    return e if isinstance(e, list) else []


def end_card(sheet: dict) -> dict | None:
    for e in _element_rows(sheet) + (sheet.get("overlays") or []):
        if isinstance(e, dict) and "end" in str(e.get("kind", "")).lower():
            return {k: e.get(k) for k in ("kind", "text", "words", "rows", "cta", "start", "duration") if e.get(k) is not None}
    pic = sheet.get("picture") or []
    if pic:   # no drawn end card: the last clip IS the close, made by production with its own words in it
        c = pic[-1]
        return {"kind": "last clip (made by production — any title or button in it is part of the clip, not the edit)",
                "clip": c["id"], "start": c["start"], "duration": c["duration"], "under_words": c.get("why")}
    return None


def brief_of(sheet: dict, kit_dir: Path) -> Path | None:
    kit = sheet.get("_kit") or {}
    for cand in [kit.get("brief")] + ([str(Path(kit["from_run"]) / "brief.md")] if kit.get("from_run") else []):
        if not cand:
            continue
        for base in (kit_dir, R.repo_root()):
            p = (base / cand) if not Path(cand).is_absolute() else Path(cand)
            if p.is_file():
                return p
    return None


def review(version: str, video: Path, sheet: dict, kit_dir: Path, qc_dir: Path) -> dict:
    """The reviewer, given what it needs: the brief, the hook text, the end card, and only the
    sheet lines it checks; one frame per caption line (with the words that should be on it),
    the opening and the end card. A BLOCKER or FIX holds the version."""
    qc_dir.mkdir(parents=True, exist_ok=True)
    lines = caption_lines(sheet)
    pick = [lines[round(i * (len(lines) - 1) / 5)] for i in range(6)] if len(lines) >= 6 else lines
    hook = [o for o in sheet.get("overlays") or [] if o.get("kind") == "hook"]
    ec = end_card(sheet)
    slim = {"version": version, "length_s": round(CS.end_of(sheet), 2),
            "hook_text": [h.get("text") for h in hook], "end_card": ec,
            "clip_order": [[c["id"], round(c["start"], 2), round(c["duration"], 2)] for c in sheet.get("picture") or []],
            "caption_lines": lines, "overlays": [{k: o.get(k) for k in ("kind", "text", "start", "duration", "zone")} for o in sheet.get("overlays") or []],
            "compliance": sheet.get("compliance")}
    (qc_dir / "sheet-slim.json").write_text(json.dumps(slim, indent=1, ensure_ascii=False))
    frames, items = [], []
    dur = CS.probe_seconds(video) or CS.end_of(sheet)
    shots = [("opening", 0.4, "the hook opening — hook text: " + " / ".join(h.get("text") or "" for h in hook))]
    shots += [(f"line{i + 1}", (l["start"] + l["end"]) / 2, f"caption expected on screen: \"{l['words']}\"") for i, l in enumerate(pick)]
    shots.append(("endcard", max(0, dur - 1.0), "the end card: " + json.dumps(ec, ensure_ascii=False) if ec else "the last second (no end card on the sheet)"))
    for name, t, expect in shots:
        fp = qc_dir / f"{name}.jpg"
        sh(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", "scale=-2:960", fp])
        frames.append(fp)
        items.append({"id": name, "output": [fp], "compare": [f"at {t:.2f}s — {expect}"]})
    src = [qc_dir / "sheet-slim.json"]
    b = brief_of(sheet, kit_dir)
    if b:
        src.append(b)
    try:
        here = Path(__file__).resolve()
        comp = next(p for p in here.parents if (p / "marketing-chain-checks" / "marketing_chain_checks").is_dir())
        if str(comp / "marketing-chain-checks") not in sys.path:
            sys.path.insert(0, str(comp / "marketing-chain-checks"))
        from marketing_chain_checks import review as RV
        door0 = RV._door

        def door():   # the judge builds its own clean environment for claude -p: caching off there too
            m = door0()
            if m is not None and not getattr(m, "_v2_nocache", False):
                ce = m._clean_env
                m._clean_env = lambda: {**ce(), "DISABLE_PROMPT_CACHING": "1"}
                m._v2_nocache = True
            return m
        RV._door = door
        f = RV.after_stage("video-edit", "cut", qc_dir.parent, sources=src, items=items)
    except Exception as e:  # noqa: BLE001
        f = {"_": {"ok": None, "severity": "UNCHECKED", "problems": [f"review not run: {type(e).__name__}: {e}"]}}
    bad = {k: v for k, v in f.items() if isinstance(v, dict) and v.get("severity") in ("BLOCKER", "FIX")}
    unchecked = [k for k, v in f.items() if isinstance(v, dict) and v.get("severity") == "UNCHECKED"]
    return {"held": bool(bad), "findings": bad, "unchecked": unchecked, "brief": str(b) if b else None,
            "frames": [str(x) for x in frames]}


def latest_cutsheet(run: Path) -> Path | None:
    """The newest cutsheet-vN.json in the edit run (the timeline page's saves), or None."""
    vs = []
    for f in Path(run).glob("cutsheet-v*.json"):
        m = re.fullmatch(r"cutsheet-v(\d+)\.json", f.name)
        if m:
            vs.append((int(m.group(1)), f))
    return max(vs)[1] if vs else None


def _tell(kind, title, id_, label=""):
    """Outlier's bell + the owner's phone (run-kit notify: one line in runs/notify/events.jsonl). Never fails the run."""
    try:
        kit = str(HERE.parents[1] / "run-kit")
        if kit not in sys.path:
            sys.path.append(kit)
        from run_kit.notify import safe_notify
        safe_notify(kind, title, id_, label=label)
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------- the command
def ad(a) -> int:
    t_all = time.time()
    install_caches()
    runs_root = Path(a.runs_root).resolve() if a.runs_root else R.repo_root() / "runs" / "video-edit"
    run = runs_root / a.brand / a.label
    work, store, deliv = run / "work", run / "work" / "renders", run / "deliverable"
    state = R.read(run / "v2.json", {"machine": "video-edit-v2", "brand": a.brand, "label": a.label, "started": R.now()})
    kits = [("control", Path(a.control).resolve())] + [(Path(h).resolve().parent.name if Path(h).name == "kit" else Path(h).name, Path(h).resolve()) for h in a.hook]
    names = [("control", kits[0][1])] + [(re.sub(r".*?-(h-[a-z]-.*)$", r"\1", n), p) for n, p in kits[1:]]

    sheets = {}
    with timed("kits: keyframes fixed once, links made"):
        views = {n: kit_view(p, work / "kits" / n) for n, p in names}
    for n, _ in names:
        saved = run / f"cutsheet-{n}.json"
        newest = latest_cutsheet(run) if n == "control" else None   # the timeline page saves cutsheet-vN.json: that is the edit
        if newest and not a.recut:
            sheets[n] = R.read(newest); continue
        if saved.exists() and not a.recut:   # the cut is the edit: after the preview's yes it is not cut again
            sheets[n] = R.read(saved); continue
        with timed(f"cut {n} (faces, scene read, levelling: cached)"):
            sheets[n] = cut(views[n], a.brand, f"{a.label}-{n}", work / "cut" / n)
            R.write(saved, sheets[n])
            if n == "control" and not latest_cutsheet(run):   # the name the timeline page and the Edit list read
                R.write(run / "cutsheet-v1.json", sheets[n])
    ctrl = sheets["control"]
    plan = {}
    for n, _ in names[1:]:
        shift, D, diff = split_point(sheets[n], ctrl)
        plan[n] = {"shift": shift, "opening_ends_s": D, "differs": diff[:40], "differs_count": len(diff)}
        log(f"  {n}: hook adds {shift:.2f}s; new up to {D:.2f}s ({len(diff)} differences)")
    state["plan"] = plan

    # 4. rough preview first
    if not a.yes:
        with timed("rough preview: control (draft, 15 fps)"):
            prev, _ = render(compose(ctrl, views["control"], work / "preview-control", captions=True), deliv / "preview" / "control.mp4",
                             "draft", CRF_PREVIEW, FPS_PREVIEW, store)
        for n, _ in names[1:]:
            with timed(f"rough preview: {n} opening"):
                render(compose(sheets[n], views[n], work / f"preview-{n}", captions=True, duration=plan[n]["opening_ends_s"] + 1.0),
                       deliv / "preview" / f"{n}-opening.mp4", "draft", CRF_PREVIEW, FPS_PREVIEW, store)
        state.update(stage="waiting for a yes on the preview", preview=str(deliv / "preview"))
        state.setdefault("timings", {})["preview"] = {"steps": TIMES[:], "minutes": round((time.time() - t_all) / 60, 2), "stats": dict(STATS)}
        R.write(run / "v2.json", state)
        log(f"PREVIEW ready: {deliv / 'preview'} — run again with --yes to make the finals")
        _tell("timeline", f"Rough cut ready: {a.brand}/{a.label}", f"{a.brand}/{a.label}", a.label)
        return 0

    # the control, once, in full
    versions = {}
    with timed("control: full render (one at a time, crf pinned)"):
        raw, reused = render(compose(ctrl, views["control"], work / "final-control", captions=True), work / "control.raw.mp4",
                             "delivery", CRF_FINAL, None, store)
    with timed("control: master the sound"):
        cm = deliv / f"{a.label}_control.mp4"
        mux(raw, master_audio(audio_wav(raw, work / "control.wav"), work / "control.m4a", ctrl.get("mix") or {}), cm)
    versions["control"] = {"file": str(cm), "checks": checks(cm, ctrl)}
    kf = keyframes(raw)

    for n, _ in names[1:]:
        p = plan[n]
        shift = p["shift"]
        k_ctrl = next((k for k in kf if k >= p["opening_ends_s"] - shift + 0.5), None)
        out = deliv / f"{a.label}_{n}.mp4"
        if k_ctrl is None:
            with timed(f"{n}: full render (no place to join)"):
                hr, _ = render(compose(sheets[n], views[n], work / f"final-{n}", captions=True), work / f"{n}.raw.mp4", "delivery", CRF_FINAL, None, store)
                mux(hr, master_audio(audio_wav(hr, work / f"{n}.wav"), work / f"{n}.m4a", sheets[n].get("mix") or {}), out)
            versions[n] = {"file": str(out), "joined": False, "checks": checks(out, sheets[n])}
            continue
        head_s = k_ctrl + shift
        with timed(f"{n}: render the new opening only ({head_s:.1f}s)"):
            head, _ = render(compose(sheets[n], views[n], work / f"head-{n}", captions=True, duration=head_s), work / f"{n}.head.mp4",
                             "delivery", CRF_FINAL, None, store)
        with timed(f"{n}: join onto the control + master"):
            stitch(head, raw, k_ctrl, out, sheets[n].get("mix") or {}, work / f"join-{n}")
        with timed(f"{n}: proof — frames after the opening vs the control"):
            proof = same_after_opening(out, cm, shift, head_s)
        if not proof["identical"]:   # never ship a wrong join: make it the v1 way
            log(f"  {n}: join did not match the control — full render instead: {[r for r in proof['samples'] if r['psnr'] is None or r['psnr'] < 60]}")
            with timed(f"{n}: full render (join failed the proof)"):
                hr, _ = render(compose(sheets[n], views[n], work / f"final-{n}", captions=True), work / f"{n}.raw.mp4", "delivery", CRF_FINAL, None, store)
                mux(hr, master_audio(audio_wav(hr, work / f"{n}.wav"), work / f"{n}.m4a", sheets[n].get("mix") or {}), out)
        versions[n] = {"file": str(out), "joined": proof["identical"], "opening_s": round(head_s, 2), "proof": proof,
                       "checks": checks(out, sheets[n], head_s=head_s if proof["identical"] else None)}

    # THE AUDIT on every version (E12–E15): words chopped, lips, words on a face or mouth on the finished frames,
    # the swipe's sound — a finding holds the version like a failed check
    import audit as AU
    for n, _ in names:
        with timed(f"{n}: audit"):
            au = AU.audit_sheet(sheets[n], views[n], Path(versions[n]["file"]), sheets[n].get("_kit"))
            R.write(deliv / f"audit-{n}.json", au)
            versions[n]["checks"].append({"check": "audit — every word, shot and caption", "pass": not au["found"],
                                          "detail": "nothing found" if not au["found"] else "; ".join(f["check"] for f in au["found"][:8])})
    if not a.no_review:
        for n, _ in names:
            with timed(f"{n}: reviewer"):
                versions[n]["review"] = review(n, Path(versions[n]["file"]), sheets[n], views[n], run / "qc" / n)
    for n, v in versions.items():
        v["ready"] = all(c["pass"] for c in v["checks"]) and not (v.get("review") or {}).get("held")
        v["bytes"] = Path(v["file"]).stat().st_size
    state.update(stage="made", versions=versions)
    state.setdefault("timings", {})["final"] = {"steps": TIMES[:], "minutes": round((time.time() - t_all) / 60, 2), "stats": dict(STATS)}
    R.write(run / "v2.json", state)
    report(run, state)
    log(f"made: {deliv}")
    return 0


def report(run: Path, state: dict) -> None:
    L = [f"# {state['label']} — video edit v2", ""]
    for phase in ("preview", "final"):
        t = (state.get("timings") or {}).get(phase)
        if t:
            L += [f"## {phase}: {t['minutes']} min", ""] + [f"- {s}: {sec / 60:.1f} min" for s, sec in t["steps"]] + [f"- caches: {t['stats']}", ""]
    for n, v in (state.get("versions") or {}).items():
        L.append(f"## {n} — {'ready' if v.get('ready') else 'HELD'}")
        if "joined" in v:
            pr = v.get("proof") or {}
            L.append(f"- joined onto the control: {v['joined']} (new opening {v.get('opening_s')}s); after the opening "
                     f"{sum(1 for r in pr.get('samples', []) if r['psnr'] == float('inf') or (r['psnr'] or 0) >= 60)}/{len(pr.get('samples', []))} frames match the control")
        L += [f"- {'PASS' if c['pass'] else 'HELD'} {c['check']} — {c['detail']}" for c in v["checks"]]
        rv = v.get("review") or {}
        if rv:
            L.append(f"- reviewer: {'held — ' + '; '.join(k + ': ' + ' / '.join(x.get('problems') or []) for k, x in rv['findings'].items()) if rv['held'] else 'pass'}"
                     + (f" (not checked: {', '.join(rv['unchecked'])})" if rv.get("unchecked") else ""))
        L.append("")
    (run / "REPORT.md").write_text("\n".join(L))


def share(a) -> int:
    """ONE share copy, only for the picked version: the master with its index moved to the
    front (stream copy) — the same pixels, never a bigger file."""
    run = Path(a.run).resolve()
    st = R.read(run / "v2.json")
    v = st["versions"][a.version]
    src = Path(v["file"]); out = src.with_name(src.stem + "_share.mp4")
    r = sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-c", "copy", "-movflags", "+faststart", out])
    if r.returncode or out.stat().st_size > src.stat().st_size * 1.01:
        raise SystemExit("share copy not made: " + (r.stderr or "it came out bigger than its master"))
    v["share"] = str(out); R.write(run / "v2.json", st)
    print(f"share: {out} ({out.stat().st_size / 1e6:.0f} MB, master {src.stat().st_size / 1e6:.0f} MB)")
    return 0


def clean(a) -> int:
    """Once an ad ships: this run's own work folder goes (renders, joins, page copies, kit links).
    Only a folder this tool made (it holds v2.json) and only its work/ — never a kit, never deliverable/."""
    run = Path(a.run).resolve()
    st = R.read(run / "v2.json")
    if not st or st.get("machine") != "video-edit-v2":
        raise SystemExit(f"{run} is not a v2 run — nothing removed")
    w = run / "work"
    seen = {(p.stat().st_dev, p.stat().st_ino): p.stat().st_size for p in w.rglob("*") if p.is_file() and not p.is_symlink()} if w.exists() else {}
    size = sum(seen.values())   # hard links counted once
    shutil.rmtree(w, ignore_errors=True)
    st["cleaned"] = {"at": R.now(), "bytes": size}; R.write(run / "v2.json", st)
    print(f"cleaned {size / 1e9:.2f} GB of work files in {w}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="v2.py"); sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ad"); s.add_argument("--control", required=True); s.add_argument("--hook", action="append", default=[])
    s.add_argument("--brand", required=True); s.add_argument("--label", required=True); s.add_argument("--runs-root")
    s.add_argument("--yes", action="store_true", help="the preview was looked at: make the finals")
    s.add_argument("--no-review", action="store_true")
    s.add_argument("--recut", action="store_true", help="cut again even though this run already has its cut sheets")
    s = sub.add_parser("share"); s.add_argument("run"); s.add_argument("version")
    s = sub.add_parser("clean"); s.add_argument("run")
    a = p.parse_args(argv)
    return {"ad": ad, "share": share, "clean": clean}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
