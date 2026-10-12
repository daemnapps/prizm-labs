"""Stage 0 — measure the source file. No model, no spend.

The teardown record is a model's reading of the video; the recipe stage cuts
the ORIGINAL footage by the second, so it needs the file's own clock:

  - hard cuts (ffmpeg scene detection, score kept)
  - loudness every 0.5 s (RMS of the mix, dB)
  - duration and frame rate

Written to the run as measure.json and measure.md. The source is found by
the path in the teardown's run.json, else the same Shared Assets path on this
machine's Drive mount, else by the Drive file id in run.json's video_url
(gdrive-creator, into a temp folder deleted after measuring); measure.json's
video_from says which. When none reaches it (or there is no ffmpeg), the stage
records why and the chain carries on with the record's own timestamps.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEMUCS = Path.home() / ".daemn" / "venvs" / "demucs" / "bin" / "python"   # the shared local Demucs venv, when present
SCENE = 0.06          # scan threshold; a HARD cut is a local peak scoring ≥ 25, a SOFT change 14–24
HARD, SOFT, NEAR = 25, 14, 0.1


def _ff(args, timeout=300):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr


def probe(video):
    out = _ff(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=r_frame_rate,width,height:format=duration", "-of", "json", str(video)])
    d = json.loads(out[out.find("{"):]) if "{" in out else {}
    st = (d.get("streams") or [{}])[0]
    num, _, den = (st.get("r_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else None
    return {"duration": float((d.get("format") or {}).get("duration") or 0), "fps": round(fps, 3) if fps else None,
            "width": st.get("width"), "height": st.get("height")}


def cuts(video):
    out = _ff(["ffmpeg", "-hide_banner", "-i", str(video), "-filter:v",
               f"select='gt(scene,{SCENE})',metadata=print", "-an", "-f", "null", "-"])
    times = [float(x) for x in re.findall(r"pts_time:([\d.]+)", out)]
    scores = [float(x) for x in re.findall(r"lavfi\.scene_score=([\d.]+)", out)]
    raw = [{"t": round(t, 2), "score": round(s * 100)} for t, s in zip(times, scores)]
    peaks = []
    for x in raw:
        near = [y["score"] for y in raw if y is not x and abs(y["t"] - x["t"]) <= NEAR]
        if x["score"] >= SOFT and all(x["score"] > n for n in near):
            peaks.append({**x, "kind": "hard" if x["score"] >= HARD else "soft"})
    return peaks


def loudness(video, step=0.5):
    n = int(48000 * step)
    out = _ff(["ffmpeg", "-hide_banner", "-i", str(video), "-vn", "-af",
               f"aresample=48000,asetnsamples=n={n}:p=0,astats=metadata=1:reset=1,"
               "ametadata=print:key=lavfi.astats.Overall.RMS_level", "-f", "null", "-"])
    vals = []
    for v in re.findall(r"lavfi\.astats\.Overall\.RMS_level=(-?[\d.]+|-inf)", out):
        vals.append(-90.0 if v == "-inf" else max(-90.0, round(float(v))))
    return vals


def music_stem(video, work):
    """Loudness of everything that is not voice (Demucs two-stem), every 0.5 s — or None, with why.
    The mix alone cannot tell a quiet bed from room tone under speech; the stem can."""
    if not DEMUCS.exists():
        return None, "the local Demucs venv is not installed on this machine"
    work.mkdir(parents=True, exist_ok=True)
    wav = work / "stereo.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vn", "-ac", "2", "-ar", "44100", str(wav)], check=True)
    r = subprocess.run([str(DEMUCS), "-m", "demucs", "--two-stems", "vocals", "-o", str(work / "sep"), str(wav)],
                       capture_output=True, text=True, timeout=900)
    nw = next((work / "sep").rglob("no_vocals.wav"), None)
    if r.returncode or not nw:
        return None, "Demucs failed: " + (r.stderr or "")[-160:]
    vals = loudness(nw)
    shutil.rmtree(work, ignore_errors=True)
    return vals, None


MARKER = "Shared drives/" + os.environ.get("SHARED_DRIVE_NAME", "Shared Assets") + "/"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "run-kit"))
from run_kit import paths  # noqa: E402
REPO = paths.repo(Path(__file__).resolve().parent)


def file_id(url):
    """The Drive file id in a `…/file/d/<id>…` or `…?id=<id>` link, else None."""
    m = re.search(r"/file/d/([A-Za-z0-9_-]{10,})", url or "") or re.search(r"[?&]id=([A-Za-z0-9_-]{10,})", url or "")
    return m.group(1) if m else None


def locate(tj, work, fetch=None):
    """The source video for a teardown's run.json, and how it was reached: (path, how) or (None, why).
    Tries the path as written, then the same Shared Assets path on this machine's Drive mount, then the
    Drive file id in video_url fetched into `work` (a folder the caller owns and cleans up)."""
    video = tj.get("video") or ""
    if video and Path(video).is_file():
        return Path(video), "the path in run.json"
    missing = ["not on this machine"]
    if MARKER in video:
        sys.path.append(str(REPO / "components" / "brandpath"))
        import drive_index
        m = drive_index.mount()
        if m and (m / video.split(MARKER, 1)[1]).is_file():
            return m / video.split(MARKER, 1)[1], "this machine's Drive mount"
    missing.append("no Drive mount has it")
    fid = file_id(tj.get("video_url"))
    if not fid:
        missing.append("run.json records no Drive file id (video_url)")
    elif fetch is None and not os.environ.get("GDRIVE_SA_KEY"):
        missing.append("no GDRIVE_SA_KEY in the environment")
    else:
        if fetch is None:
            sys.path.append(str(REPO / "components" / "gdrive-creator"))
            from gdrive_creator import engine
            fetch = engine.get_media
        dest = Path(work) / ("source" + (Path(video).suffix or ".mp4"))
        try:
            fetch(fid, dest)
        except Exception as e:
            return None, "Drive by file id " + fid + " failed: " + (type(e).__name__ + ": " + str(e))[:160]
        return dest, "Drive by file id " + fid
    return None, "; ".join(missing)


def run(run_dir, teardown_run, echo=print, fetch=None):
    """Measure the source named in the teardown's run.json; write measure.json/.md."""
    run_dir = Path(run_dir)
    tj = json.loads((Path(teardown_run) / "run.json").read_text()) if (Path(teardown_run) / "run.json").is_file() else {}
    res = {"video": str(Path(tj["video"])) if tj.get("video") else None}
    if not shutil.which("ffmpeg"):
        res["skipped"] = "ffmpeg is not installed on this machine"
    else:
        with tempfile.TemporaryDirectory() as tmp:
            video, how = locate(tj, tmp, fetch)
            if video is None:
                res["skipped"] = ("the source video named in the teardown's run.json is not reachable from this machine — "
                                  + how)
            else:
                _measure(res, video, run_dir)
                res["video_from"] = how
    (run_dir / "measure.json").write_text(json.dumps(res, indent=1) + "\n")
    (run_dir / "measure.md").write_text(markdown(res))
    echo("  -> stage0  Measure (ffmpeg, no model): " + (res.get("skipped") or
         f"{len(res.get('shots', []))} shots, avg {res.get('avg_shot')} s, {res.get('fps')} fps"))
    return res


def _measure(res, video, run_dir):
    """Probe, cuts, shots, loudness and the music stem of one file, into res."""
    res.update(probe(video))
    c = cuts(video)
    res["cuts"] = c
    bounds = [0.0] + [x["t"] for x in c if x["kind"] == "hard"] + [res["duration"]]
    res["soft_changes"] = [x for x in c if x["kind"] == "soft"]
    res["shots"] = [{"n": i + 1, "start": round(a, 2), "end": round(b, 2), "len": round(b - a, 2)}
                    for i, (a, b) in enumerate(zip(bounds, bounds[1:])) if b - a > 0.04]
    res["avg_shot"] = round(res["duration"] / max(1, len(res["shots"])), 2)
    lv = loudness(video)
    res["loudness_db_every_0_5s"] = lv
    if lv:
        top = sorted(range(len(lv)), key=lambda i: -lv[i])[:3]
        res["loudest"] = [{"t": i * 0.5, "db": lv[i]} for i in sorted(top)]
        quiet = [i * 0.5 for i, x in enumerate(lv) if x <= -48]
        res["quiet_windows_s"] = quiet
    stem, why = music_stem(video, run_dir / ".stems")
    if stem:
        res["music_stem_db_every_0_5s"] = stem
        res["music_present_s"] = [i * 0.5 for i, x in enumerate(stem) if x >= -45]
    else:
        res["music_stem_skipped"] = why


def markdown(m):
    if m.get("skipped"):
        return f"# Measurement\n\nNot measured — {m['skipped']}. The chain uses the teardown record's own timestamps.\n"
    L = ["# Measurement — the file's own clock", "",
         f"Duration {m['duration']:.2f} s · {m.get('fps')} fps · {m.get('width')}×{m.get('height')} · "
         f"{len(m['shots'])} shots · average shot {m['avg_shot']} s. Hard cuts = ffmpeg scene-score peaks ≥ {HARD}; "
         f"soft changes (a dissolve, a fast move, a partial cut) = peaks {SOFT}–{HARD - 1}: "
         + (", ".join(f"{x['t']:.2f} s ({x['score']})" for x in m.get("soft_changes", [])) or "none") + ".", "",
         "| Shot | Start (s) | End (s) | Length (s) | Cut score |", "|---|---|---|---|---|"]
    scores = {round(c["t"], 2): c["score"] for c in m.get("cuts", [])}
    for s in m["shots"]:
        L.append(f"| {s['n']} | {s['start']:.2f} | {s['end']:.2f} | {s['len']:.2f} | {scores.get(s['start'], '—')} |")
    lv = m.get("loudness_db_every_0_5s") or []
    L += ["", "**Loudness, mix (RMS dB, every 0.5 s from 0.0):** " + " ".join(str(x) for x in lv), "",
          "**Loudest windows:** " + ", ".join(f"{x['t']:.1f} s ({x['db']} dB)" for x in m.get("loudest", [])),
          "", "**Near-silent windows (≤ −48 dB):** " + (", ".join(f"{t:.1f}" for t in m.get("quiet_windows_s", [])) or "none")]
    if m.get("music_stem_db_every_0_5s"):
        L += ["", "**Loudness, music stem (everything that is not voice — Demucs):** " + " ".join(str(x) for x in m["music_stem_db_every_0_5s"]),
              "", "**Music or effects present (stem ≥ −45 dB) at:** " + (", ".join(f"{t:.1f}" for t in m.get("music_present_s", [])) or "nowhere")]
    else:
        L += ["", f"Music stem not measured — {m.get('music_stem_skipped')}."]
    return "\n".join(L) + "\n"
