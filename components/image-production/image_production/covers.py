"""THE COVER JOB: one cover per version of a video ad, made start to finish by this tool (2026-11-12).

A cover (thumbnail) is its own purpose, `cover` (purposes.json, `job: "cover"`), not a generic ad picture. One request
makes one version's cover:

    the frame     the strongest frame of that version's own video (`cover.frame`, from `cover.video` at `cover.t`
                  seconds), checked against that video with ffmpeg; a picture this tool made is refused. IMAGE 1,
                  the composition.
    the set       the filed 3D set (`set`) is still required: its kept print rides beside the frame as IMAGE 2 and
                  decides the people and the room. No people picture is made without a filed set (GATE-4).
    the product   a named `product` comes from its 3D kit, rendered and placed by the tool, even though a set is named.
                  A cover that names no product is told to show none.
    the words     the picture model paints no words. The version's headline is set by the tool's own words step
                  (words.set_headline) inside this job, before the picture is delivered, so the words are exact.
                  Nothing is added after the tool delivers. The faces under the words are read on the plate
                  (face_read.py); a cover whose faces were not read is not `ok`.
    the type      one per ad: the job's, or on a single request the ad's filed cover-type.json beside its folder.
    the concept   the swipe is a real cover's id; with no direction, its rated move in the cover index is the concept.
    the record    run.json, the picture's .recipe.json and `<picture>.cover.json` carry `cover`: the version id, the
                  swipe id it follows, the source frame (its file, the video it is from, the second, its sha256), the
                  set and its print, the type the words were set in, and the delivered file's sha256. The approval
                  filer's cover rule (components/meta-upload/cover_rule.py) reads it from there.

One ad's versions are made together (`make_ad`, `make.py covers --job <job.json>`): one type record sets every
version's headline in the same face, weight, size and band (`ad_type`), every version starts from a different frame,
and the ad's record (`covers.json`) says which covers are fit to file (`ok`).

ROLLBACK (models.json `gate.cover`, or IMAGE_COVER_OFF=all or a comma list on one machine; row in team/rollbacks.md):
    "on": false                  purpose `cover` is refused; covers are made as purpose `ad`, as before
    "source_frame": false        the set's kept print is the base again; the frame rides after it as a reference
    "product_with_set": false    with a set named the product is not brought in from its 3D kit, as before
    "words_step": false          the picture model paints the words from the prompt, as before
    "own_video": false           `video` and `t` are optional and the frame is not checked against its video
    "frame_not_made": false      only a frame with a .recipe.json beside it counts as a picture we made
    "one_type": false            a single request with no `type` is fitted to its own headline alone
    "faces": false               a cover whose faces were not read can be fit to file
    "swipe_concept": false       any swipe id is taken, and a cover with no direction may carry no concept
    "video_stream": false        `video` need not be a real video stream with a duration (a still picture is read
                                 as a one-frame video, as before)
    "made_look": false           a frame is refused as a picture we made only by its bytes and records, not by how it
                                 looks (a re-saved or re-encoded copy of a cover or its plate is taken, as before)
    "unfit_exit": false          `make.py` with one cover request exits 0 on a delivered cover that is not `ok`
    "face_keep": false           the model's redrawn faces stay on the cover, as before 2026-11-13 (face_keep.py: the
                                 frame's own faces and lips are laid back over the made picture, pixel for pixel, the
                                 headline is set clear of them, and a kept face that changed or no longer lines up
                                 makes the cover unfit)

Nothing here names a brand, a product or a person.
"""
import base64
import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from . import paths as P, prompting, route as R, set_gate as SG, words as W

BLOCK = ("ad", "version", "headline", "frame", "video", "t", "swipe", "type")
NEEDED = ("version", "headline", "frame", "swipe")
PARTS = ("source_frame", "product_with_set", "words_step", "own_video", "frame_not_made", "one_type", "faces",
         "swipe_concept", "video_stream", "made_look", "unfit_exit", "face_keep")
JOB_FIELDS = ("brand", "ad", "out", "versions", "set", "product", "product_place", "people", "references", "type",
              "label", "model", "checks", "rules")
VERSION_FIELDS = ("version", "headline", "frame", "video", "t", "swipe", "direction", "set", "product",
                  "product_place", "people", "references", "checks", "rules")
VERSION_NEEDED = ("version", "headline", "frame", "video", "swipe")
PICTURE = (".png", ".jpg", ".jpeg", ".webp")
STILL_FORMATS = ("image2", "gif", "apng", "webp", "png", "jpeg", "bmp", "tiff")   # ffprobe formats that hold pictures
NOTHING = "Nothing was sent and nothing was spent."


class CoverRefused(ValueError):
    """A cover request that cannot be made as asked. Raised before any door, so nothing was sent or spent."""


# ── the switches ─────────────────────────────────────────────────────────────────────────────────────────────────────
def config(t=None):
    return ((t or R.table()).get("gate") or {}).get("cover") or {}


def _off():
    return {x.strip() for x in os.environ.get("IMAGE_COVER_OFF", "").split(",") if x.strip()}


def job_on(t=None):
    """Whether purpose `cover` is taken at all. A table with no `gate.cover` block keeps the job on."""
    return "all" not in _off() and config(t).get("on", True) is not False


def on(part, t=None):
    """Whether one part of the cover job is on (one of PARTS)."""
    off = _off()
    return job_on(t) and part not in off and config(t).get(part, True) is not False


def is_cover(purpose_row):
    return (purpose_row or {}).get("job") == "cover"


# ── the request's cover block ────────────────────────────────────────────────────────────────────────────────────────
def block(req, t=None):
    """The request's `cover` block, checked. Raises CoverRefused naming what is wrong."""
    if not job_on(t):
        raise CoverRefused("components/image-production refuses this cover: the cover job is switched off (models.json "
                           "`gate.cover.on`, or IMAGE_COVER_OFF). Make it as purpose `ad`, as before. " + NOTHING)
    c = req.get("cover")
    if not isinstance(c, dict):
        raise CoverRefused("components/image-production refuses this cover: purpose `cover` needs a `cover` block naming "
                           f"{', '.join(NEEDED)}. " + NOTHING)
    unknown = sorted(set(c) - set(BLOCK))
    missing = [k for k in NEEDED if not str(c.get(k) or "").strip()]
    if unknown or missing:
        raise CoverRefused("components/image-production refuses this cover: "
                           + ("; ".join(x for x in (
                               f"the `cover` block is missing {', '.join(missing)}" if missing else "",
                               f"it carries keys nothing reads: {', '.join(unknown)}" if unknown else "") if x))
                           + f". The block is: {', '.join(BLOCK)}. " + NOTHING)
    try:
        count = int(req.get("count") or 1)
    except (TypeError, ValueError):
        raise CoverRefused(f"components/image-production refuses this cover: `count` is a number, and a cover's is 1 "
                           f"({req.get('count')!r}). " + NOTHING)
    if count != 1:
        raise CoverRefused("components/image-production refuses this cover: a cover is one request per version and one "
                           "picture per request (`count` is 1). " + NOTHING)
    frame = Path(str(c["frame"])).expanduser()
    if not frame.is_file() or frame.suffix.lower() not in PICTURE:
        raise CoverRefused(f"components/image-production refuses this cover: its source frame is not a picture on this "
                           f"machine ({c['frame']}). `cover.frame` is a frame of the version's own video. " + NOTHING)
    if frame.with_suffix(".recipe.json").is_file():
        raise CoverRefused(f"components/image-production refuses this cover: its source frame is a picture we made "
                           f"({frame}). A cover starts from a frame of the version's own video, never from another "
                           f"generated picture. " + NOTHING)
    try:
        frame_at = float(c["t"]) if c.get("t") is not None else None
    except (TypeError, ValueError):
        frame_at = None                                   # refused below, with its own reason
    made = (made_here(frame, t, video=str(c.get("video") or "").strip() or None, at=frame_at)
            if on("frame_not_made", t) else None)
    if made:
        raise CoverRefused(f"components/image-production refuses this cover: its source frame is a picture we made "
                           f"({frame}: {made}). A cover starts from a frame of the version's own video, never from a "
                           f"cover, its plate or any other picture this tool delivered. " + NOTHING)
    if req.get("from_image") and on("source_frame", t):
        raise CoverRefused(f"components/image-production refuses this cover: a cover takes no `from_image` "
                           f"({req['from_image']}). Its base is the frame of its own video (`cover.frame`), with the "
                           f"filed set's kept print beside it. " + NOTHING)
    at = c.get("t")
    if at is not None:
        try:
            at = float(at)
        except (TypeError, ValueError):
            raise CoverRefused(f"components/image-production refuses this cover: `cover.t` is the frame's second in "
                               f"its video, a number ({c.get('t')}). " + NOTHING)
    video = str(c.get("video") or "").strip() or None
    video_sha = None
    if on("own_video", t):
        lost = [k for k, v in (("video", video), ("t", at)) if v is None]
        if lost:
            raise CoverRefused(f"components/image-production refuses this cover: the `cover` block is missing "
                               f"{' and '.join(lost)}. A cover starts from the strongest frame of the version's own "
                               f"video, so the request names that video (`cover.video`, --video) and the frame's second "
                               f"in it (`cover.t`, --frame-at), and the frame is checked against it. " + NOTHING)
        said = frame_of_video(frame, video, at)
        if said:
            raise CoverRefused(f"components/image-production refuses this cover: its source frame ({frame}) is not a "
                               f"frame of the version's own video: {said}. Grab the frame from that video at that "
                               f"second. " + NOTHING)
        video = str(Path(video).expanduser().resolve())
        video_sha = SG.sha(video)
    swipe = str(c["swipe"]).strip()
    if on("swipe_concept", t):
        if placeholder(swipe):
            raise CoverRefused(f"components/image-production refuses this cover: its swipe id is a placeholder "
                               f"({swipe!r}). A cover follows a real cover its audience sees: name that cover's id in "
                               f"the cover swipe index (runs/asset-index/swipes/covers). " + NOTHING)
        if req.get("_direction_from") and swipe_move(swipe) is None:
            raise CoverRefused(f"components/image-production refuses this cover: it brings no direction and the cover "
                               f"swipe index has no move for its swipe ({swipe}): no row with that id, or the row "
                               f"names no move. With no concept from a real cover there is nothing to blend. Name a "
                               f"swipe whose move is rated in the index, or bring a direction that carries the "
                               f"concept. " + NOTHING)
    return {"ad": str(c.get("ad") or "").strip() or None, "version": str(c["version"]).strip(),
            "headline": str(c["headline"]).strip(), "frame": frame, "video": video, "video_sha256": video_sha,
            "t": at, "swipe": swipe, "type": c.get("type")}


# ── the frame: a frame of the version's own video, never a picture this tool made ───────────────────────────────────
MATCH = 0.08            # mean grey difference (0..1) at 36x64 under which a frame is the video's picture at that second
NUDGE = (0.0, -0.04, 0.04, -0.1, 0.1, -0.25, 0.25)       # seconds tried around `t`: a grab lands on the nearest frame
_SEEN = {}
_LEDGER = {"key": None, "set": set(), "looks": [], "vectors": {}}


def _grey(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size, im.convert("L").resize((36, 64), Image.BOX).tobytes()


def _twins(video):
    """The video, then its clean twin (<name>.clean.<ext>, the same cut with no captions) when one sits beside it."""
    v = Path(video)
    other = (v.with_name(v.name.replace(".clean.", ".", 1)) if ".clean." in v.name
             else v.with_name(v.stem + ".clean" + v.suffix))
    return [v] + ([other] if other.is_file() else [])


def frame_of_video(frame, video, at):
    """Why `frame` is not the picture at `at` seconds of `video` (or of its clean twin), None when it is. The frame and
    a grab at that second (and a few nearby, a grab lands on the nearest frame) are compared small and grey: the same
    picture shape and under MATCH apart. Local only (ffmpeg)."""
    video = Path(str(video)).expanduser()
    if not video.is_file():
        return f"its video is not a file on this machine ({video})"
    ff = shutil.which("ffmpeg")
    if not ff:
        return "ffmpeg is not on this machine, so the frame cannot be checked against its video"
    stream = on("video_stream")
    key = (str(frame), SG.sha(frame), str(video.resolve()), video.stat().st_mtime_ns, round(float(at), 3), stream)
    if key in _SEEN:
        return _SEEN[key]
    twins = _twins(video)
    if stream:
        why = not_a_video(video, at)
        if why:
            _SEEN[key] = why
            return why
        twins = [v for v in twins if v == video or not not_a_video(v, at)]
    fsize, fg = _grey(frame)
    best, said = None, None
    with tempfile.TemporaryDirectory(prefix="cover-frame-") as d:
        n = 0
        for v in twins:
            for dt in NUDGE:
                s = float(at) + dt
                if s < 0:
                    continue
                n += 1
                out = Path(d) / f"grab-{n}.png"
                r = subprocess.run([ff, "-v", "error", "-nostdin", "-y", "-ss", f"{s:.3f}", "-i", str(v), "-frames:v",
                                    "1", str(out)], capture_output=True)
                if r.returncode or not out.is_file():
                    continue
                vsize, vg = _grey(out)
                shape = vsize[0] / vsize[1]
                if abs(fsize[0] / fsize[1] - shape) > 0.03 * shape:
                    said = (f"the frame is {fsize[0]}x{fsize[1]} and the video is {vsize[0]}x{vsize[1]}, not the same "
                            f"picture shape")
                    break
                diff = sum(abs(a - b) for a, b in zip(fg, vg)) / (255.0 * len(fg))
                best = diff if best is None else min(best, diff)
                if diff <= MATCH:
                    _SEEN[key] = None
                    return None
            if said:
                break
    if not said:
        said = (f"{video.name} has no frame at {float(at):g} s" if best is None else
                f"it is not the picture at {float(at):g} s of {video.name} ({best:.0%} apart; a frame of the video is "
                f"under {MATCH:.0%})")
    _SEEN[key] = said
    return said


def not_a_video(video, at=None):
    """Why `video` is not a real video (a video stream with a duration, `at` inside it), None when it is. A still
    picture is not a video, whatever its name: ffmpeg reads a picture as a one-frame input. Local only (ffprobe)."""
    video = Path(str(video)).expanduser()
    if video.suffix.lower() in PICTURE:
        return f"its video is a picture file, not a video ({video.name})"
    fp = shutil.which("ffprobe")
    if not fp:
        return "ffprobe is not on this machine, so its video cannot be checked to be a video"
    r = subprocess.run([fp, "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=codec_type,duration:format=format_name,duration", "-of", "json", str(video)],
                       capture_output=True, text=True)
    try:
        got = json.loads(r.stdout or "{}")
    except ValueError:
        got = {}
    streams = [s for s in got.get("streams") or [] if s.get("codec_type") == "video"]
    if r.returncode or not streams:
        return f"its video has no video stream ({video.name})"
    fmt = str((got.get("format") or {}).get("format_name") or "")
    if fmt.endswith("_pipe") or any(x in STILL_FORMATS for x in fmt.split(",")):
        return f"its video is a still picture, not a video ({video.name} reads as {fmt})"
    durations = []
    for x in ((got.get("format") or {}).get("duration"), streams[0].get("duration")):
        try:
            durations.append(float(x))
        except (TypeError, ValueError):
            pass
    length = max(durations) if durations else 0.0
    if length <= 0:
        return f"its video has no duration ({video.name})"
    if at is not None and float(at) > length:
        return f"{video.name} is {length:g} s long, so it has no frame at {float(at):g} s"
    return None


# ── how a picture looks: a re-saved or re-encoded copy of a cover or its plate is still a picture we made ───────────
LOOK = (27, 48)         # grey cells a picture is read at (9:16)
LOOK_FLOOR = 8.0        # the least grey spread a picture needs to be told by its look; a flatter one is told by bytes
LOOK_SAME = 0.15        # under this far apart (see apart) a frame is a copy of the made picture, re-saved or regraded


def look(path):
    """How a picture looks, small and grey: "<w>x<h>:<base64 of LOOK grey cells>". Stored in the cover's record and its
    ledger line, so a copy of the cover or its plate is known after it is re-saved, re-encoded or regraded."""
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
        g = im.convert("L").resize(LOOK, Image.BOX).tobytes()
    return f"{w}x{h}:" + base64.b64encode(g).decode()


def _vector(seen):
    """A stored look as (shape, mean, cells scaled to their own spread, spread), None when it cannot be read."""
    try:
        size, data = str(seen).split(":", 1)
        w, h = (int(x) for x in size.split("x"))
        g = base64.b64decode(data)
    except (ValueError, TypeError):
        return None
    if not g or not h:
        return None
    mean = sum(g) / len(g)
    spread = (sum((x - mean) ** 2 for x in g) / len(g)) ** 0.5
    return (w / h, mean, [(x - mean) / max(spread, LOOK_FLOOR) for x in g], spread)


def apart(a, b):
    """How far apart two looks are (0 the same picture; two unrelated pictures are around 1), None when they are not the
    same picture shape or one has too little detail to be told by its look (a flat picture). The cells are each scaled to
    their own picture's spread, so a regrade moves them little; the mean grey counts a little."""
    if a is None or b is None or len(a[2]) != len(b[2]) or abs(a[0] - b[0]) > 0.03 * b[0]:
        return None
    if min(a[3], b[3]) < LOOK_FLOOR:
        return None
    return sum(abs(x - y) for x, y in zip(a[2], b[2])) / len(a[2]) + abs(a[1] - b[1]) / 255.0


def _pairs_of(looks):
    """(made, its source frame) from a record's `looks`: the cover and its plate, each against the frame it came from."""
    if not isinstance(looks, dict):
        return []
    src = looks.get("source")
    return [(looks[k], src) for k in ("cover", "plate") if isinstance(looks.get(k), str)]


def _ledger_shas():
    """Every sha256 the tool's ledger names: the pictures it made, and the pictures they were made from (a cover's
    plate is the `from` of its cover). Empty when there is no ledger here."""
    return _read_ledger()["set"]


def _ledger_looks():
    """(made look, source look) for every cover and plate the tool's ledger records a look for."""
    return _read_ledger()["looks"]


def _read_ledger():
    try:
        from . import provenance as PV
    except ImportError:
        return {"set": set(), "looks": []}
    led = PV.ledger_path()
    try:
        st = led.stat()
    except OSError:
        return {"set": set(), "looks": []}
    key = (str(led), st.st_mtime_ns, st.st_size)
    if _LEDGER["key"] != key:
        got, looks = set(), []
        for line in led.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict):
                continue
            got.update(row[k] for k in ("sha256", "from") if isinstance(row.get(k), str))
            looks.extend(_pairs_of(row.get("looks")))
        _LEDGER.update(key=key, set=got, looks=looks, vectors={})
    return _LEDGER


def _made_shas(rec):
    """The sha256s a run record gives for pictures the tool made (a cover, its plate), never for what it was made from."""
    if isinstance(rec, dict):
        for k, v in rec.items():
            if k in ("source_frame", "frame", "set", "request", "references"):
                continue
            if k in ("sha256", "plate_sha256") and isinstance(v, str):
                yield v
            else:
                yield from _made_shas(v)
    elif isinstance(rec, list):
        for x in rec:
            yield from _made_shas(x)


def _record_looks(rec):
    """(made look, source look) pairs from a run record's `looks` blocks, at any depth."""
    if isinstance(rec, dict):
        for k, v in rec.items():
            if k == "looks":
                yield from _pairs_of(v)
            elif k not in ("source_frame", "request", "references"):
                yield from _record_looks(v)
    elif isinstance(rec, list):
        for x in rec:
            yield from _record_looks(x)


_GRABBED = {}


def _video_looks(video, at, t=None):
    """The looks of the real frames of `video` (and its clean twin) at `at` seconds and a few nearby (NUDGE), grabbed
    with ffmpeg. [] when there is no video, no second, no ffmpeg, or (switch video_stream) it is not a real video."""
    if not video or at is None:
        return []
    video = Path(str(video)).expanduser()
    ff = shutil.which("ffmpeg")
    if not ff or not video.is_file():
        return []
    key = (str(video.resolve()), video.stat().st_mtime_ns, round(float(at), 3))
    if key in _GRABBED:
        return _GRABBED[key]
    if on("video_stream", t) and not_a_video(video, at):
        _GRABBED[key] = []
        return []
    got = []
    with tempfile.TemporaryDirectory(prefix="cover-look-") as d:
        n = 0
        for v in _twins(video):
            for dt in NUDGE:
                s = float(at) + dt
                if s < 0:
                    continue
                n += 1
                out = Path(d) / f"grab-{n}.png"
                r = subprocess.run([ff, "-v", "error", "-nostdin", "-y", "-ss", f"{s:.3f}", "-i", str(v), "-frames:v",
                                    "1", str(out)], capture_output=True)
                if not r.returncode and out.is_file():
                    got.append(_vector(look(out)))
    _GRABBED[key] = got
    return got


def _looks_like_made(frame, pairs, video=None, at=None, t=None):
    """Why `frame` is a copy of one of the made pictures in `pairs` by how it looks, None when it is not. A frame near a
    made picture is still the video's frame when it is at least as near that picture's own source frame, or at least
    as near a real frame of its own video at its second (`video`, `at`: grabbed and compared). The second test settles
    a model that kept the moment, whose plate is almost its source frame, so the first is a near-tie."""
    mine = _vector(look(frame))
    cache = _LEDGER.setdefault("vectors", {})
    real = None
    for made, source in pairs:
        m = cache.get(made) or cache.setdefault(made, _vector(made))
        d = apart(mine, m)
        if d is None or d > LOOK_SAME:
            continue
        if source is not None:
            s = cache.get(source) or cache.setdefault(source, _vector(source))
            ds = apart(mine, s)
            if ds is not None and ds <= d:
                continue
        if real is None:
            near = [x for x in (apart(mine, g) for g in _video_looks(video, at, t)) if x is not None]
            real = min(near) if near else False
        if real is not False and real <= d:
            continue
        return (f"it looks like a cover or plate the tool made, re-saved or re-encoded ({d:.0%} apart; a copy is under "
                f"{LOOK_SAME:.0%})")
    return None


def made_here(frame, t=None, video=None, at=None):
    """Why `frame` is a picture this tool made (a cover, a plate, any delivered picture), None when nothing says so.
    `video` and `at` are the video the frame is said to come from and its second in it: a frame nearer a real frame of
    that video at that second than to a made picture is the video's frame."""
    frame = Path(frame)
    if any(p.name == "generated" for p in frame.resolve().parents):
        return "it sits in a run's generated/ folder"
    if frame.with_suffix(".cover.json").is_file():
        return "a cover record sits beside it"
    digest = SG.sha(frame)
    if digest in _ledger_shas():
        return "its bytes are in the tool's ledger of made pictures"
    pairs = []
    for d in dict.fromkeys((frame.parent, frame.parent.parent)):
        recs = [d / "run.json", d / "covers.json"] + sorted(d.glob("*.cover.json"))[:200] + sorted(d.glob("*.recipe.json"))[:200]
        for f in recs:
            try:
                rec = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            if digest in set(_made_shas(rec)):
                return f"its bytes are recorded as a made picture in {f.name}"
            pairs.extend(_record_looks(rec))
    if on("made_look", t):
        said = _looks_like_made(frame, _ledger_looks() + pairs, video=video, at=at, t=t)
        if said:
            return said
    return None


PLACEHOLDER = {"none", "null", "nil", "tbd", "todo", "swipe", "unknown", "placeholder", "na", "test", "example",
               "sample", "xxx", "id", "any", "default"}


def placeholder(swipe):
    """A swipe id that names no real cover: empty, under three letters or digits, or a stand-in word."""
    s = re.sub(r"[^a-z0-9]+", "", str(swipe or "").lower())
    return len(s) < 3 or s in PLACEHOLDER


# ── the direction, when the request brings none ──────────────────────────────────────────────────────────────────────
NO_MOVE = ("", "none", "as-shot", "unrated")


def swipe_move(swipe):
    """The move the followed swipe makes, in plain words, from the cover swipe index in this workspace
    (runs/asset-index/swipes/covers/covers.json, a row's `move`). None when there is no index here, no such row, or
    the row names no move. The picture is never read: the move is taken, not the swipe."""
    try:
        rows = json.loads((P.repo() / "runs" / "asset-index" / "swipes" / "covers" / "covers.json").read_text())
    except (OSError, ValueError):
        return None
    rows = rows if isinstance(rows, list) else (rows.get("covers") or rows.get("rows") or []) if isinstance(rows, dict) else []
    for row in rows:
        if isinstance(row, dict) and str(row.get("id")) == str(swipe):
            move = str(row.get("move") or "").strip().lower()
            return None if move in NO_MOVE else move.replace("-", " ")
    return None


def default_direction(req):
    """The standing direction for a cover request that carries none (prompts/cover-direction): the moment in the frame,
    the version's line shown literally, one thing pushed, and the followed swipe's move when the index names it. None
    when the request is not a whole cover request (the block's own check then says what is missing)."""
    c = req.get("cover")
    if not isinstance(c, dict) or not str(c.get("headline") or "").strip():
        return None
    move = swipe_move(c.get("swipe"))
    concept = f" The move to make, taken from a real cover this audience already sees: {move}." if move else ""
    said = " ".join(str(c["headline"]).split()).replace('"', "'")
    body = " ".join(prompting.body(prompting.latest("cover-direction")).split())
    return body.replace("{headline}", said).replace("{concept}", concept)


# ── the type: one record for every version of an ad ──────────────────────────────────────────────────────────────────
def _definitions():
    return json.loads((P.home() / "cover-type.json").read_text())


def default_type():
    return dict(_definitions()["default"])


def type_of(given=None):
    """A whole type record: the given one (a mapping, or a JSON file holding one, alone or under `type`) over the
    default. Raises CoverRefused naming every problem."""
    if isinstance(given, (str, Path)):
        f = Path(str(given)).expanduser()
        if not f.is_file():
            raise CoverRefused(f"components/image-production refuses this cover: the type file is not on this machine "
                               f"({given}). " + NOTHING)
        given = json.loads(f.read_text())
        given = given.get("type", given) if isinstance(given, dict) else given
    if given is not None and not isinstance(given, dict):
        raise CoverRefused("components/image-production refuses this cover: `type` is a mapping or a JSON file. " + NOTHING)
    style = default_type()
    style.update({k: v for k, v in (given or {}).items() if not k.startswith("_")})
    bad = W.check_type(style)
    if bad:
        raise CoverRefused("components/image-production refuses this cover: " + "; ".join(bad) + ". " + NOTHING)
    return style


def _given_zone(given):
    if isinstance(given, (str, Path)):
        try:
            given = json.loads(Path(str(given)).expanduser().read_text())
            given = given.get("type", given)
        except (OSError, ValueError, AttributeError):
            return False
    return isinstance(given, dict) and bool(given.get("zone"))


def ad_type(headlines, given=None, clear_of=None):
    """The one type record for every version of an ad: the given type over the default, at the one size every headline
    fits its band at. Every version set by it carries the same face, weight, size and band.

    `clear_of` lists, headline for headline, where that version's product will sit (`product_box`, or None). When the
    given type names no band, the bands in cover-type.json are tried in order and the first one where no headline lands
    on its own version's product is the ad's band."""
    headlines = [str(h) for h in headlines]
    bands = [None] if _given_zone(given) else (list(_definitions().get("bands") or []) or [None])
    first = None
    for band in bands:
        style = type_of(given)
        if band is not None:
            style["zone"] = dict(band)
        try:
            style["size_px"] = W.fit(headlines, style)
        except W.WordsRefused as ex:
            if first is None and band is bands[-1]:
                raise CoverRefused(f"components/image-production refuses these covers: {ex} " + NOTHING)
            continue
        style["min_size_px"] = min(float(style.get("min_size_px") or style["size_px"]), style["size_px"])
        first = first or style
        hits = False
        for text, box in zip(headlines, clear_of or []):
            lay = W.layout(text, style) if box else None
            if lay and _overlap(_fractions(lay), box):
                hits = True
        if not hits:
            return style
    return first                                             # none is clear: the engine's refusal names the two boxes


def _band_words(zone):
    return (f"the band from {zone['top']:g}% to {zone['bottom']:g}% down the frame, "
            f"{zone['left']:g}% to {zone['right']:g}% across")


def _overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def _fractions(lay):
    w, h = lay["frame"]
    l, t, r, b = lay["box_px"]
    return (l / w, t / h, r / w, b / h)


def planned_box(brand, product, product_place=None):
    """Where a named product will sit on a cover before anything is resolved: the kit's own placement under the
    request's. None when no product is named or its kit has no 3D model (the engine refuses that later)."""
    if not product:
        return None
    from . import product3d
    try:
        decl = product3d.declaration(product3d.find_kit(brand, product))
    except (OSError, ValueError, KeyError):
        decl = None
    if decl is None:
        return None
    return product_box(product3d.plan({"product_place": product_place or {}}, decl))


def product_box(place):
    """Where a placed product will sit, as fractions of the frame (l, t, r, b): the same estimate the scene prompt is
    told to keep clear (product3d.spot_words)."""
    x, y, h = float(place["x"]), float(place["y"]), float(place["height"])
    return (max(0.0, x - h * 0.6), max(0.0, y - h * 1.1), min(1.0, x + h * 0.6), y)


def clear_of_product(cov, place):
    """Refuse, before anything is spent, a cover whose headline and product would land on each other."""
    lay = (cov.get("words") or {}).get("layout")
    if not lay or not place:
        return
    words_box = _fractions(lay)
    box = product_box(place)
    if _overlap(words_box, box):
        raise CoverRefused(
            "components/image-production refuses this cover: the headline and the product would land on each other "
            f"(the words from {words_box[1] * 100:.0f}% to {words_box[3] * 100:.0f}% down, the product from "
            f"{box[1] * 100:.0f}% to {box[3] * 100:.0f}% down). Move the product (`product_place`: x, y, height) or the "
            "band (`cover.type.zone`). " + NOTHING)


# ── the request, turned into the cover's request ─────────────────────────────────────────────────────────────────────
def apply(req, blk, printed, t=None):
    """The request as the engine makes it: the frame and the set print in their places, the product from its kit, the
    word band kept clear, and `_cover`, what the record will say. Raises CoverRefused."""
    req = dict(req)
    refs = [str(x) for x in req.get("references") or []]
    frame = str(blk["frame"])
    if printed is not None and SG.sha(frame) == SG.sha(printed):
        raise CoverRefused("components/image-production refuses this cover: its source frame is the set's kept print. A "
                           "cover starts from the strongest frame of the version's own video; a redraw of the set print "
                           "is not a cover. " + NOTHING)
    if on("source_frame", t):
        req["from_image"] = frame                           # the composition; the set print rides beside it
        req["references"] = ([str(printed)] if printed is not None else []) + refs
        base = "frame"
    else:                                                   # rolled back: the kept print is the base, as before
        if printed is not None:
            req["from_image"] = str(printed)
        req["references"] = [frame] + refs
        base = "print" if printed is not None else "references"
    rules = list(req.get("rules") or [])

    if on("words_step", t):
        # the ad's type, exactly as given; a request that carries none takes its ad's filed type (cover-type.json beside
        # its folder) or, the ad's first, fits the default to its headline and files it for the ad's other versions
        clear = [planned_box(req["brand"], req.get("product"), req.get("product_place"))
                 if on("product_with_set", t) else None]
        type_file = None
        if blk.get("type"):
            style = type_of(blk["type"])
        elif on("one_type", t):
            style, type_file = single_type(req, blk, clear)
        else:
            style = ad_type([blk["headline"]], clear_of=clear)
        try:
            lay = W.layout(blk["headline"], style)
        except W.WordsRefused as ex:
            raise CoverRefused(f"components/image-production refuses this cover: {ex}. " + NOTHING)
        if lay is None and (type_file or {}).get("from") == "filed":
            raise CoverRefused(
                f"components/image-production refuses this cover: the headline does not fit the ad's type "
                f"({style['size_px']:g} px in {style.get('max_lines', 3)} lines, filed in {type_file['file']}): "
                f"\"{blk['headline']}\". Every version of one ad is set in one type: make the ad's versions again "
                f"together (make.py covers --job), which fits one size to every headline. " + NOTHING)
        if lay is None:
            raise CoverRefused(
                f"components/image-production refuses this cover: the headline does not fit its band at "
                f"{style['size_px']:g} px in {style.get('max_lines', 3)} lines: \"{blk['headline']}\". The cover job "
                f"(make.py covers) fits one size to every version of the ad; or shorten it, or give the band more room "
                f"(`cover.type.zone`). " + NOTHING)
        rules.append(prompting.body(prompting.latest("cover-word-space")).replace("{band}", _band_words(style["zone"])))
        words = {"by": "the tool's words step (image_production.words.set_headline)", "type": style,
                 "face_file": P.portable(str(W.face_file(style["face"]))), "lines": lay["lines"], "layout": lay}
        if type_file:
            words["type_file"] = type_file
    else:
        rules.append(f'The words on the picture are exactly these, spelled letter for letter: "{blk["headline"]}". '
                     f'No other words anywhere.')
        words = {"by": "the picture model (gate.cover.words_step is off)", "type": None}

    product = None
    if req.get("product"):
        if on("product_with_set", t):
            if req.get("product_3d") is False:
                raise CoverRefused("components/image-production refuses this cover: a cover's product comes from its 3D "
                                   "kit and is never drawn by the picture model (`product_3d` cannot be false). Leave "
                                   "`product` out for a cover with no product in frame. " + NOTHING)
            req["product_3d"] = True
            req["_product_with_base"] = True
            product = {"key": req["product"], "from": "its 3D kit, rendered and placed by the tool"}
        else:
            product = {"key": req["product"], "from": "the picture model (gate.cover.product_with_set is off)"}
    elif on("product_with_set", t):
        rules.append(prompting.body(prompting.latest("cover-no-product")))
    if on("face_keep", t) and base == "frame":     # the video's people are kept, not redrawn
        rules.append("Every person in picture 1 stays exactly where they stand, at the same size, pose and angle: their "
                     "faces and lips are taken from picture 1 as they are and laid back over your picture, so do not "
                     "move, resize or turn any person. Change everything around them: the room, the light, the pushed "
                     "concept, the product.")
    req["rules"] = rules

    from PIL import Image
    with Image.open(frame) as im:
        frame_size = list(im.size)
    req["_cover"] = {
        "ad": blk["ad"], "version": blk["version"], "headline": blk["headline"], "swipe": blk["swipe"], "base": base,
        "source_frame": {k: v for k, v in (("file", frame), ("video", blk["video"]),
                                           ("video_sha256", blk.get("video_sha256")), ("t", blk["t"]),
                                           ("sha256", SG.sha(frame)), ("size", frame_size)) if v is not None},
        "set": ({"name": SG.set_name(req.get("set")), "print": str(printed), "sha256": SG.sha(printed)}
                if printed is not None else None),
        "words": words, "product": product}
    if req.get("_direction_from"):
        req["_cover"]["direction_from"] = req["_direction_from"]
    return req


def single_type(req, blk, clear):
    """(type, {"file", "from"}) for a single cover request that names its ad but no type: the ad's filed type
    (`cover-type.json` beside the request's folder, the same file `make_ad` writes), or, the ad's first cover, the default
    fitted to this headline, filed when the cover is delivered. Raises CoverRefused."""
    if not blk["ad"]:
        raise CoverRefused("components/image-production refuses this cover: it names no ad (`cover.ad`, --ad) and no "
                           "type (`cover.type`, --type). Every version of one ad is set in one type, so a single cover "
                           "request says which ad it belongs to; or make the ad's versions together with make.py "
                           "covers --job. " + NOTHING)
    f = Path(str(req["out"])).expanduser().parent / "cover-type.json"
    if f.is_file():
        try:
            filed = json.loads(f.read_text())
        except ValueError:
            filed = {}
        if not isinstance(filed, dict) or str(filed.get("ad") or "") != blk["ad"]:
            raise CoverRefused(f"components/image-production refuses this cover: the type file beside its folder ({f}) "
                               f"is for another ad ({(filed or {}).get('ad') if isinstance(filed, dict) else None}). "
                               f"One folder of covers per ad. " + NOTHING)
        return type_of(filed.get("type")), {"file": str(f), "from": "filed"}
    return ad_type([blk["headline"]], clear_of=clear), {"file": str(f), "from": "new"}


def face_reader():
    """The local face reader (image_production/face_read.py: macOS Vision, the scene tool the video edit line already
    uses). None when this machine has none."""
    from . import face_read
    return face_read.reader()


def faces_on_words(picture, box, read):
    """Whether the headline's box touches a face or lips on `picture` (the plate, before the words hide anything)."""
    if not box:
        return {"checked": False, "why": "the tool set no words box, so where the words sit is not known"}
    if read is None:
        return {"checked": False, "why": "no face reader on this machine (macOS Vision, "
                                         "components/video-edit/machine/vision/scene.swift)"}
    try:
        found = [tuple(float(x) for x in f) for f in (read(str(picture)) or [])]
    except Exception as ex:                              # noqa: BLE001  a reader that cannot run says so
        return {"checked": False, "why": f"the face reader stopped ({type(ex).__name__}: {str(ex)[:160]})"}
    hits = [f for f in found if _overlap(box, f)]
    return {"checked": True, "found": len(found), "on_words": bool(hits), "read": str(picture)}


def reference_clause(cov):
    """The cover's reference clause, in place of the edit clause. None when the frame is not the base (rolled back)."""
    if (cov or {}).get("base") != "frame":
        return None
    line = prompting.body(prompting.latest("cover-set-print")) if cov.get("set") else ""
    return re.sub(r"[ \t]{2,}", " ", prompting.body(prompting.latest("cover-frame")).replace("{print_line}", line)).strip()


def order(references, cov):
    """The frame first and the set print second, whatever else rides along."""
    if (cov or {}).get("base") != "frame":
        return list(references)
    first = [cov["source_frame"]["file"]] + ([cov["set"]["print"]] if cov.get("set") else [])
    return first + [r for r in references if r not in first]


def clear_of_kept(picture, plate, c, words):
    """The headline moves to the first band (cover-type.json `bands`) where it covers no kept face, set again from the
    plate; when none is clear it stays where it was and the face check says so."""
    from . import face_keep as FK
    kept = FK.boxes_of(c.get("kept_faces"))
    if not kept or not any(_overlap(words["box_px"], k) for k in kept):
        return
    for band in list(_definitions().get("bands") or []):
        style = dict(words["type"], zone=dict(band))
        try:
            got = W.set_headline(plate, c["headline"], style, out=picture, plate=plate)
        except W.WordsRefused:
            continue
        if not any(_overlap(got["box_px"], k) for k in kept):
            words.update(type=style, lines=got["lines"], box_px=got["box_px"], band_moved="clear of the kept faces")
            return
    W.set_headline(plate, c["headline"], words["type"], out=picture, plate=plate)    # none clear: as first set


def finish(picture, cov, raw_dir, placed=None, faces=None):
    """After the picture is delivered to `out` and before it is recorded: set the headline over it (the tool's words
    step), read the faces under the words, and say what the cover is. Returns the cover's record, with `ok`.
    `faces(picture) -> [(l, t, r, b) px]` replaces the local face reader (a test seam)."""
    c = copy.deepcopy(cov)
    picture = Path(picture)
    words = c.get("words") or {}
    words.pop("layout", None)
    frame = (c.get("source_frame") or {}).get("file")
    keeping = on("face_keep") and c.get("base") == "frame" and frame and Path(frame).is_file()
    if keeping:                                                  # the frame's own faces back over the made picture
        from . import face_keep as FK
        read = faces if faces is not None else face_reader()
        if read is None:                                         # no reader: nothing kept, the face check says so
            keeping = False
            c["kept_faces"] = None
        else:
            c["kept_faces"] = FK.keep(picture, frame, read)
    if words.get("type"):
        plate = Path(raw_dir) / f"{picture.stem}-plate{picture.suffix}"
        try:
            got = W.set_headline(picture, c["headline"], words["type"], plate=plate)
            words.update(lines=got["lines"], box_px=got["box_px"], plate=str(plate), plate_sha256=SG.sha(plate))
            if keeping:
                clear_of_kept(picture, plate, c, words)
        except W.WordsRefused as ex:
            words["error"] = str(ex)
    if keeping:
        c["kept_faces"] = FK.verify(picture, c["kept_faces"])
    tf = words.get("type_file")
    if tf and tf.get("from") == "new" and words.get("type") and not words.get("error"):
        f = Path(tf["file"])
        if not f.is_file():                                     # the ad's first cover files the ad's type
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps({"ad": c.get("ad"), "type": words["type"]}, indent=1, ensure_ascii=False) + "\n")
    if on("faces"):
        pic = Path(words["plate"]) if words.get("plate") else picture
        c["faces"] = faces_on_words(pic, words.get("box_px"), faces if faces is not None else face_reader())
    else:
        c["faces"] = {"checked": False, "why": "the face check is switched off (gate.cover.faces)"}
    c["faces_checked"] = c["faces"].get("checked") is True
    c["panels"] = panels(Path(words["plate"]) if words.get("plate") else picture)
    c["plate_words"] = plate_words(Path(words["plate"]) if words.get("plate") else picture, c.get("headline"))
    if c.get("product") and (c["product"].get("from") or "").startswith("its 3D kit"):
        p = placed or {}
        c["product"].update({k: p[k] for k in ("source", "box", "render", "error") if p.get(k) is not None})
        if not p:
            c["product"]["error"] = "the 3D product was not placed"
    c["file"] = str(picture)
    c["sha256"] = SG.sha(picture)
    if on("made_look"):                                          # how the cover, its plate and its frame look
        c["looks"] = _looks_of(picture, words.get("plate"), (c.get("source_frame") or {}).get("file"))
    c["problems"] = problems(c)
    c["ok"] = not c["problems"]
    picture.with_suffix(".cover.json").write_text(                # the cover's own record, beside it wherever it goes
        P.portable(json.dumps(c, indent=1, ensure_ascii=False, default=str)) + "\n")
    try:                                                         # and its line in the tool's ledger, where there is one
        from . import provenance
        provenance.stamp(picture, "cover", base=words.get("plate_sha256"), purpose="cover", version=c["version"],
                         swipe=c["swipe"], headline=c["headline"], ad=c.get("ad"),
                         source_frame={k: c["source_frame"].get(k) for k in ("file", "video", "t")},
                         looks=c.get("looks"))
    except ImportError:
        pass
    return c


def _looks_of(picture, plate, source):
    out = {}
    for k, f in (("cover", picture), ("plate", plate), ("source", source)):
        try:
            if f and Path(f).is_file():
                out[k] = look(f)
        except (OSError, ValueError):
            continue
    return out


def panels(picture):
    """A strip or grid of other frames inside the picture, or None (2026-11-21, brief-0380: the backup picture model
    copied its reference board's layout and laid three small video frames along the cover's bottom). Read the way a
    board is built: a full-width line of one colour across the outer part of the frame, and past it, between that line
    and the edge, at least one full-height line of one colour inside the frame (the gap between two panels)."""
    try:
        from PIL import Image
        import statistics as _st
        g = Image.open(picture).convert("L")
        w, h = 270, max(2, round(270 * g.size[1] / g.size[0]))
        px = g.resize((w, h)).load()
    except Exception:                                   # noqa: BLE001 -- an unreadable picture is said by other checks
        return None
    row = lambda y: _st.pstdev([px[x, y] for x in range(w)])
    col = lambda x, band: _st.pstdev([px[x, yy] for yy in band])
    for y in [y for y in range(3, h - 3) if y < 0.42 * h or y > 0.58 * h]:
        # a thin even line with picture on both sides (a flat dark shirt or a white wall is not a divider)
        if row(y) >= 8 or row(y - 3) < 20 or row(y + 3) < 20:
            continue
        band = range(y + 2, h) if y > h / 2 else range(0, y - 1)
        if len(band) < 0.08 * h:
            continue
        cuts = [x for x in range(int(0.15 * w), int(0.85 * w))
                if col(x, band) < 10 and col(x - 3, band) >= 20 and col(x + 3, band) >= 20]
        if cuts:
            return ("the picture holds a strip of other frames: a full-width divider at %d%% of its height with a "
                    "panel gap past it" % round(100 * y / h))
    return None


def plate_words(picture, headline=None):
    """Words the picture model drew into the picture before the tool set the headline (2026-11-21, brief-0380 H6: the
    headline was painted at the top and then set again, so it showed twice): every line Vision reads that is headline
    sized (3% of the frame's height or more) or carries the headline's own words. A product's small label is not one.
    None when the reader cannot run."""
    from . import text_read as TR
    got = TR.lines(picture)
    if got is None:
        return None
    hw = {w for w in re.findall(r"[a-z]{3,}", str(headline or "").lower())}
    out = []
    for h, t in got:
        tw = set(re.findall(r"[a-z]{3,}", t.lower()))
        if h >= 0.03 or (hw and len(tw & hw) >= 2):
            out.append(t)
    return out


def problems(cov):
    """Why a made cover is not fit to file, [] when it is."""
    out = []
    if cov.get("plate_words"):
        out.append("words drawn in the picture under the headline: " + " / ".join(cov["plate_words"])[:160])
    if cov.get("below_criteria") and cov.get("judge_fails"):
        out.append("the picture judge failed it: " + "; ".join(cov["judge_fails"])[:240])
    if cov.get("panels"):
        out.append(str(cov["panels"]) + " — one single photograph, never a board of frames")
    if (cov.get("words") or {}).get("error"):
        out.append("the headline was not set: " + cov["words"]["error"])
    if (cov.get("product") or {}).get("error"):
        out.append("the product is not on the cover: " + str(cov["product"]["error"]))
    k = cov.get("kept_faces")
    if k is not None and not k.get("pass"):
        out.append("the video's faces were not kept: " + str(k.get("why") or "a kept face changed"))
    f = cov.get("faces") or {}
    if f.get("on_words"):
        out.append("the headline sits on a face")
    elif on("faces") and f.get("checked") is not True:
        out.append("faces not checked: " + str(f.get("why") or "no face reader ran"))
    return out


# ── one ad: every version, one type ──────────────────────────────────────────────────────────────────────────────────
def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "version"


def check_job(job):
    """The job's shape, checked. Raises CoverRefused naming every problem."""
    bad = []
    if not isinstance(job, dict):
        raise CoverRefused("components/image-production refuses these covers: the job is not a mapping. " + NOTHING)
    unknown = sorted(set(job) - set(JOB_FIELDS))
    if unknown:
        bad.append(f"the job carries fields nothing reads: {', '.join(unknown)} (have: {', '.join(JOB_FIELDS)})")
    bad += [f"the job is missing `{k}`" for k in ("brand", "ad", "out", "versions") if not job.get(k)]
    seen, frames = set(), {}
    for i, v in enumerate(job.get("versions") or [], 1):
        name = str((v or {}).get("version") or f"version {i}")
        if not isinstance(v, dict):
            bad.append(f"{name}: not a mapping")
            continue
        extra = sorted(set(v) - set(VERSION_FIELDS))
        if extra:
            bad.append(f"{name}: carries fields nothing reads: {', '.join(extra)}")
        lost = [k for k in VERSION_NEEDED if not str(v.get(k) or "").strip()]
        if lost:
            bad.append(f"{name}: missing {', '.join(lost)}")
            continue
        if _slug(name) in seen:
            bad.append(f"{name}: named twice (one cover per version)")
        seen.add(_slug(name))
        digest = SG.sha(Path(str(v["frame"])).expanduser())
        if digest is None:
            bad.append(f"{name}: its source frame is not a file on this machine ({v['frame']})")
        elif digest in frames:
            bad.append(f"{name}: the same source frame as {frames[digest]}. Each version's cover starts from the "
                       f"strongest moment of its own video")
        else:
            frames[digest] = name
    if bad:
        raise CoverRefused("components/image-production refuses these covers: " + "; ".join(bad) + ". " + NOTHING)


def requests(job, style):
    """One engine request per version, each carrying the ad's one type."""
    out = []
    root = Path(str(job["out"])).expanduser()
    label = str(job.get("label") or f"cover-{_slug(job['ad'])}")
    for v in job["versions"]:
        req = {"brand": job["brand"], "purpose": "cover", "direction": v.get("direction"),
               "out": str(root / _slug(v["version"])), "label": f"{label}-{_slug(v['version'])}",
               "cover": {"ad": job["ad"], "version": v["version"], "headline": v["headline"], "frame": str(v["frame"]),
                         "video": str(v["video"]), "swipe": v["swipe"], "type": style}}
        if v.get("t") is not None:
            req["cover"]["t"] = v["t"]
        if not str(req["direction"] or "").strip():           # none given: the engine writes the standing one
            req.pop("direction")
        for k in ("set", "product", "product_place", "people", "model"):
            val = v[k] if k in v else job.get(k)
            if val is None or (val is False and k != "people"):     # `"product": false` leaves the product off
                continue
            req[k] = val
        for k in ("references", "checks", "rules"):
            both = list(job.get(k) or []) + list(v.get(k) or [])
            if both:
                req[k] = both
        out.append(req)
    return out


def _signature(style):
    return json.dumps(style, sort_keys=True, ensure_ascii=False)


def check_ad(rows, faces=None):
    """The ad-level checks over the made covers; each row gets `ok` and `problems`. Returns the ad's problems.
    `faces(picture) -> [(l, t, r, b) px]` replaces the local face reader. A row whose faces were not read is not ok
    (gate.cover.faces); a headline on a face is a problem."""
    ad_bad = []
    made = [r for r in rows if r.get("file")]
    moved = any((r.get("words") or {}).get("band_moved") for r in made)

    def _type(r):                       # a band moved to clear the video's kept faces is still the ad's one type
        t = dict((r.get("words") or {}).get("type") or {})
        if moved:
            t.pop("zone", None)
        return t
    types = {_signature(_type(r)) for r in made}
    if len(types) > 1:
        ad_bad.append("the versions are not set in one type (face, weight, size and band differ)")
    by_sha = {}
    for r in made:
        if on("faces") and (faces is not None or "faces" not in r):    # a reader given, or a row never read
            w = r.get("words") or {}
            pic = w.get("plate") if w.get("plate") and Path(str(w["plate"])).is_file() else r["file"]
            r["faces"] = faces_on_words(pic, w.get("box_px"), faces if faces is not None else face_reader())
        r["faces_checked"] = (r.get("faces") or {}).get("checked") is True
        r["problems"] = problems(r)
        twin = by_sha.setdefault(r.get("sha256"), r["version"])
        if twin != r["version"]:
            r["problems"].append(f"the same picture as {twin}")
        r["ok"] = not r["problems"] and not ad_bad
    return ad_bad


def make_ad(job, only=None, dry_run=False, faces=None, **engine_kw):
    """Every version's cover for one ad, in one type. `job`:

        {"brand", "ad", "out", "set", "product"?, "product_place"?, "people"?, "references"?, "type"?, "label"?,
         "versions": [{"version", "headline", "frame", "video", "t"?, "swipe", "direction",
                       "set"?, "product"?, "product_place"?, "people"?, "references"?}, ...]}

    `frame` is a frame of `video`, that version's own video, at `t` seconds; the record names all three.
    A version with no `direction` gets the job's standing one (prompts/cover-direction).

    A version's own field wins over the job's; `"product": false` on a version leaves the product off that cover.
    `only` makes just the named versions again, in the ad's filed type. `dry_run` resolves every request and spends
    and writes nothing. `engine_kw` goes to the engine (mirror=, mode=, and the test seams).

    Returns {"ok", "brand", "ad", "out", "type", "covers": [...], "failed": [...], "problems": [...], "record"}.
    A cover is fit to file only when its row says `ok`."""
    from . import engine as E
    check_job(job)
    t = engine_kw.get("table")
    style = None
    if on("words_step", t):
        spots = [planned_box(job["brand"], v["product"] if "product" in v else job.get("product"),
                             v["product_place"] if "product_place" in v else job.get("product_place"))
                 if on("product_with_set", t) else None for v in job["versions"]]
        style = ad_type([v["headline"] for v in job["versions"]], job.get("type"), clear_of=spots)
    root = Path(str(job["out"])).expanduser()
    type_file, record_file = root / "cover-type.json", root / "covers.json"
    wanted = {_slug(x) for x in ([only] if isinstance(only, str) else (only or []))}
    known = {_slug(v["version"]) for v in job["versions"]}
    if wanted - known:
        raise CoverRefused(f"components/image-production refuses these covers: `only` names versions the job does not "
                           f"have ({', '.join(sorted(wanted - known))}). " + NOTHING)
    if wanted and style is not None and type_file.is_file():
        filed = json.loads(type_file.read_text()).get("type")
        if _signature(filed) != _signature(style):
            raise CoverRefused("components/image-production refuses these covers: this job's type is not the type the "
                               f"ad's other versions were set in ({P.rel(type_file)}). Make every version again "
                               "(leave `only` out) so the ad stays in one type. " + NOTHING)
    reqs = [r for r in requests(job, style) if not wanted or _slug(r["cover"]["version"]) in wanted]

    resolve_kw = {k: engine_kw[k] for k in ("library", "purposes_map", "table") if k in engine_kw}
    refused = []
    for r in reqs:                                           # everything free first: one refusal stops the whole ad
        try:
            E.resolve(E.with_learnings(r), **resolve_kw)
        except E.BadRequest as ex:
            why = str(ex)
            if getattr(ex, "set_refused", False) and not dry_run:
                why += SG.queue_refusal(r["brand"], r.get("direction") or r["cover"]["headline"], name=r["label"],
                                        products=[r.get("product")],
                                        resume={"tool": "make.py covers", "request": r},
                                        source="image-production cover job")
            refused.append(f"{r['cover']['version']}: {why}")
    if refused:
        raise CoverRefused("components/image-production refuses these covers, and made none of them:\n  "
                           + "\n  ".join(refused))
    if dry_run:
        return {"ok": True, "dry_run": True, "brand": job["brand"], "ad": job["ad"], "out": str(root), "type": style,
                "requests": reqs, "covers": [], "failed": [], "problems": []}

    root.mkdir(parents=True, exist_ok=True)
    rows, failed = [], []
    for r in reqs:
        version = r["cover"]["version"]
        try:
            got = E.make(r, **engine_kw)
        except (Exception, SystemExit) as ex:                # noqa: BLE001  one version failing never stops its siblings
            failed.append({"version": version, "why": f"{type(ex).__name__}: {str(ex)[:400]}"})
            continue
        cov = dict(got.get("cover") or {})
        pic0 = (got.get("pictures") or [{}])[0] or {}
        cov.update(version=version, run=str(Path(got["out"]) / "run.json"),
                   below_criteria=bool(got.get("below_criteria")),
                   judge_fails=[str(x) for x in (pic0.get("fails") or pic0.get("failed_checks") or [])][:4])
        rows.append(cov)

    if wanted and record_file.is_file():                     # a remake keeps its siblings' rows
        old = P.local(json.loads(record_file.read_text())).get("covers") or []
        done = {_slug(r["version"]) for r in rows} | {_slug(f["version"]) for f in failed}
        rows = [o for o in old if _slug(o.get("version")) not in done] + rows
    order_of = {_slug(v["version"]): i for i, v in enumerate(job["versions"])}
    rows.sort(key=lambda r: order_of.get(_slug(r.get("version")), 999))
    ad_bad = check_ad(rows, faces)
    result = {"ok": bool(rows) and not failed and not ad_bad and all(r.get("ok") for r in rows)
              and len(rows) == len(job["versions"]),
              "machine": P.TOOL, "job": "cover", "brand": job["brand"], "ad": job["ad"], "out": str(root),
              "type": style, "covers": rows, "failed": failed, "problems": ad_bad,
              "made": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if style is not None:
        type_file.write_text(json.dumps({"ad": job["ad"], "type": style}, indent=1, ensure_ascii=False) + "\n")
    record_file.write_text(P.portable(json.dumps(result, indent=1, ensure_ascii=False, default=str)) + "\n")
    result["record"] = str(record_file)
    return result
