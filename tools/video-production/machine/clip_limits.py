"""The clip model's limits, read from the rulebook (components/model-inputs/inputs/<model>.json) and checked in code before
anything is sent. One source: the video chain's field list (model-inputs.json) reads its numbers from the same file.

    findings = check("seedance-2.5", duration=6, resolution="480p", images=[png], videos=[mp4], audios=[mp3])
    raise_on_errors(findings)            # a SystemExit that names every error; warnings never stop a call

A finding is {id, level: "error"|"warn", say}. An error means the model would refuse the call or the call breaks a rule we
hold; the door stops. No network, no spend (it opens only local files to measure them). Python 3.9.
"""
import importlib.util
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
_IR = []


def rules():
    if not _IR:
        sp = importlib.util.spec_from_file_location("clip_limits_input_rules", HERE.parents[1] / "model-inputs" / "input_rules.py")
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _IR.append(m)
    return _IR[0]


def limits(model):
    return rules().limits(model)


def seconds_of(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def check(model, duration, resolution, images=(), videos=(), audios=(), aspect=9 / 16, measure=True):
    """The call's inputs against the rulebook. `images`, `videos`, `audios` are file paths; `measure` reads their lengths."""
    L = limits(model)
    out = []

    def add(id_, level, say):
        out.append({"id": id_, "level": level, "say": say})

    lo, hi = L.get("duration_seconds", [0, 10 ** 6])
    if not lo <= float(duration) <= hi:
        add("duration", "error", f"{duration} s is outside what {model} makes ({lo} to {hi} s).")
    if L.get("resolutions") and resolution not in L["resolutions"]:
        add("resolution", "error", f"resolution {resolution!r} is not one of {', '.join(L['resolutions'])}.")
    ar = L.get("aspect_ratio_range")
    if ar and not ar[0] <= float(aspect) <= ar[1]:
        add("aspect", "error", f"aspect {aspect:.2f} is outside {ar[0]} to {ar[1]}.")
    if len(images) > L.get("max_images", 10 ** 6):
        add("max-images", "error", f"{len(images)} pictures is more than {model} takes ({L['max_images']}).")
    for i, im in enumerate(images, 1):
        ext = Path(str(im)).suffix.lower().lstrip(".")
        if ext and L.get("image_formats") and ext not in L["image_formats"]:
            add("image-format", "error", f"picture {i} is .{ext}; {model} takes {', '.join(L['image_formats'])}.")
    sub = L.get("stable_image_subjects")
    if sub and len(images) > sub[1]:
        add("stable-images", "warn", f"{len(images)} pictures is past the stable range ({sub[0]} to {sub[1]} subjects).")
    for i, im in enumerate(images, 1):             # the person is the BASELINE, never the master (the owner, 2026-10-27; the sheet's never_send_stems)
        stem = Path(str(im)).stem.lower()
        if any(stem.startswith(x) for x in L.get("never_send_stems", [])):
            add("never-send", "error", f"picture {i} ({Path(str(im)).name}) is on {model}'s never-send list ({', '.join(L['never_send_stems'])}): "
                "the person goes in from the baseline (headshot, look, details, expressions).")
    for i, v in enumerate(videos, 1):
        ext = Path(str(v)).suffix.lower().lstrip(".")
        if ext and L.get("video_formats") and ext not in L["video_formats"]:
            add("video-format", "error", f"reference video {i} is .{ext}; {model} takes {', '.join(L['video_formats'])}.")
        if Path(str(v)).is_file() and L.get("max_video_mb") and Path(str(v)).stat().st_size > L["max_video_mb"] * 1024 * 1024:
            add("video-size", "error", f"reference video {i} is over {L['max_video_mb']} MB.")
        if measure and Path(str(v)).is_file():
            sec = seconds_of(v)
            lo_v, hi_v = L.get("video_seconds_range") or [L.get("min_video_seconds", 0), 10 ** 6]
            if not lo_v <= sec <= hi_v:
                add("video-clip-range", "error", f"reference video {i} is {sec:.1f} s; {model} takes {lo_v} to {hi_v if hi_v < 10 ** 6 else 'any'} s.")
    if len(videos) > L.get("max_videos", 10 ** 6):
        add("max-videos", "error", f"{len(videos)} videos is more than {model} takes ({L['max_videos']}).")
    if measure and videos:
        total = sum(seconds_of(v) for v in videos if Path(v).is_file())
        if total > L.get("max_video_seconds_total", 10 ** 6):
            add("video-seconds", "error", f"the reference videos run {total:.1f} s together; the limit is {L['max_video_seconds_total']} s.")
        best = L.get("best_reference_video_seconds")
        for i, v in enumerate(videos, 1):
            s = seconds_of(v) if Path(v).is_file() else 0.0
            if best and s and not (2 <= s <= max(best[1], 15)):
                add("video-clip-seconds", "warn", f"reference video {i} is {s:.1f} s; 2 to 15 s is accepted, {best[0]} to {best[1]} s works best.")
    if len(audios) > L.get("max_audio_clips", 10 ** 6):
        add("max-audio", "error", f"{len(audios)} audio clips is more than {model} takes ({L['max_audio_clips']}).")
    if measure and audios:
        secs = [seconds_of(a) if Path(a).is_file() else 0.0 for a in audios]
        if sum(secs) > L.get("max_audio_seconds_total", 10 ** 6):
            add("audio-seconds", "error", f"the audio runs {sum(secs):.1f} s together; the limit is {L['max_audio_seconds_total']} s.")
        rng = L.get("audio_clip_seconds")
        for i, s in enumerate(secs, 1):
            if rng and s and not rng[0] <= s <= rng[1]:
                add("audio-clip-seconds", "error", f"audio clip {i} is {s:.1f} s; {model} takes {rng[0]} to {rng[1]} s a clip.")
        mb = L.get("audio_clip_mb")
        for i, a in enumerate(audios, 1):
            if mb and Path(a).is_file() and Path(a).stat().st_size > mb * 1024 * 1024:
                add("audio-size", "error", f"audio clip {i} is over {mb} MB.")
    return out


def raise_on_errors(findings, who=""):
    errs = [f for f in findings if f["level"] == "error"]
    if errs:
        raise SystemExit((who + ": " if who else "") + "stopped before sending — " + " ".join(f"[{f['id']}] {f['say']}" for f in errs))
    return findings
