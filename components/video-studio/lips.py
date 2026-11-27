#!/usr/bin/env python3
"""What the picture does with the voice, measured on every swipe shot (BRIEF-SPEC rule 9, ruled 2026-11-12).

    python3 lips.py <writing or teardown run>          writes <run>/lips.json (computed once, kept)
    python3 lips.py <run> --print                      prints every shot's picture type
    python3 lips.py setup                              makes the face reader ready on this machine (any machine, once)

It runs in the teardown, before any writing (video-teardown run.py, where the frame map is handed to the writing): every
swipe that is torn down is measured, its table is added to the frame map the writing reads, and lips.json is shared with
every piece written from that teardown. The Video Studio and the shot list read the same file.

Every face on screen is read about 8 times a second (MediaPipe Face Landmarker, jaw opening) and set against the run's
word timings. Each frame-map shot (K01 …) gets one picture type:
  talking   the voice's owner is on screen and speaking it: lips open and close with the words (lip-synced take)
  mime      someone else on screen mouths a line the voice says (a retold line acted out): mouth moves, no voice in it
  reaction  one opening of the mouth under the voice: a gasp, a laugh, a smile; not speech
  present   the voice's owner is on screen, mouth still, the voice runs over them (voice-over on the speaker)
  away      the picture has left the speaker (hands, product, another place) while the voice runs on
  silent    no voice under this shot: music or room sound only
The teardown's own Roll column is not used for this: measured on 12 Nov it called 80 shots lips-on where 3 were.

Who owns the voice: the names before "Name:" in the teardown's Transcript column. A face counts as theirs when the frame
map's `who` for that shot names them first. The reader needs mediapipe, opencv and numpy; when this Python lacks them it
runs itself under VISION_PYTHON, else ~/.cache/take-layers/venv/bin/python (the same models take_layers.py uses).
No brand, product or person is named here.
"""
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

CACHE = Path.home() / ".cache" / "take-layers"
FACE_MIN = 0.06      # a face smaller than this share of the frame height is too small to read lips on
MOVE = 0.035         # mean frame-to-frame jaw change that is any mouth movement at all
TALK_MOVE = 0.08     # ... and that, with repeated openings, is speech
TALK_RATE = 1.0      # mouth openings a second that read as talking (a gasp opens once)
GAP = 0.6            # words closer than this are one stretch of speech
OWNER_MARGIN = 0.15  # how far below the owner's own likeness a face may fall and still be the owner
OWNER_LIKE = 0.36    # SFace cosine at which a face is the voice's owner (OpenCV's own match threshold is 0.363)
TYPES = ("talking", "mime", "reaction", "present", "away", "silent")
LIPS = {"talking": "on", "mime": "mime", "reaction": "off", "present": "off", "away": "off", "silent": "off"}


MODELS = {           # the same models take_layers.py uses, fetched once into CACHE
    "face.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
    "yunet.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "sface.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}
PACKAGES = ["mediapipe", "opencv-python-headless", "numpy"]


def vision_python():
    for p in (os.environ.get("VISION_PYTHON"), str(CACHE / "venv" / "bin" / "python")):
        if p and Path(p).exists():
            return p
    return None


def setup():
    """Make the reader ready on this machine: its models in CACHE and a Python with mediapipe at CACHE/venv. Safe to
    repeat; does nothing that is already there. Returns the Python to run under."""
    import urllib.request
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, url in MODELS.items():
        if not (CACHE / name).exists():
            urllib.request.urlretrieve(url, CACHE / name)
    py = vision_python()
    if py and subprocess.run([py, "-c", "import mediapipe, cv2, numpy"], capture_output=True).returncode == 0:
        return py
    base = os.environ.get("VISION_BASE_PYTHON") or next(
        (c for c in ("python3.12", "python3.11", "python3.10", sys.executable)
         if subprocess.run(["sh", "-c", "command -v " + c], capture_output=True).returncode == 0), sys.executable)
    venv = CACHE / "venv"
    subprocess.run([base, "-m", "venv", str(venv)], check=True)
    py = str(venv / "bin" / "python")
    subprocess.run([py, "-m", "pip", "install", "-q"] + PACKAGES, check=True)
    return py


def table(run):
    """The measured picture types as text for the writing (added to the frame map it reads)."""
    f = Path(run) / "lips.json"
    if not f.is_file():
        return "[UNFILLED: picture types not measured — lips.py <run> measures them]"
    d = json.loads(f.read_text())
    rows = ["PICTURE TYPES, MEASURED (lips.py; trust these over any written Roll label). The voice owner: %s. Counts: %s."
            % (", ".join(d.get("owners") or ["unknown"]), ", ".join("%s %d" % kv for kv in sorted(d["counts"].items()))),
            "talking = the owner speaks on screen, lips synced · mime = someone else mouths a line the voice says · "
            "reaction = one gasp or laugh · present = the owner on screen, mouth still, voice over them · away = the "
            "picture has left the speaker · silent = no voice under it.", "",
            "| Shot | Time | Picture | Who is on screen |", "|---|---|---|---|"]
    for k, r in d["shots"].items():
        rows.append("| %s | %.1f-%.1f s | %s | %s |" % (k, r["start"], r["end"], r["picture"], ", ".join(r.get("who") or [])[:60]))
    return "\n".join(rows)


def ensure(run):
    """Measure a run if it has no lips.json yet, setting the reader up on this machine first if needed. Returns a line
    saying what happened; never raises (the writing then reads [UNFILLED] and says so)."""
    run = Path(run)
    if (run / "lips.json").is_file():
        return "picture types: already measured"
    try:
        py = setup()
        r = subprocess.run([py, "-I", str(Path(__file__).resolve()), str(run)], capture_output=True, text=True)
        if r.returncode or not (run / "lips.json").is_file():
            return "picture types: could not measure (%s)" % (r.stderr.strip().splitlines() or ["no output"])[-1][:160]
        return "picture types: " + r.stdout.strip().splitlines()[-1]
    except Exception as e:  # noqa: BLE001
        return "picture types: could not measure (%s: %s)" % (type(e).__name__, str(e)[:120])


def speech_spans(audio_dir):
    """Speech as spans from the transcriber's word timings (audio/speakers.json); line timings only as a fallback."""
    d = Path(audio_dir)
    for name in ("speakers.json", "words.json"):
        f = d / name
        if not f.is_file():
            continue
        doc = json.loads(f.read_text())
        if doc.get("words"):
            spans = []
            for w in doc["words"]:
                if w.get("type", "word") != "word":
                    continue
                a, b = float(w["start"]), float(w["end"])
                if spans and a - spans[-1][1] < GAP:
                    spans[-1][1] = b
                else:
                    spans.append([a, b])
            return [tuple(s) for s in spans]
        if doc.get("lines"):
            return [(float(l["start"]), float(l["end"])) for l in doc["lines"]]
    return []


def voice_owners(run):
    """Who owns the voice, from the teardown's cast: each person whose block says they speak ("Speaks: 0:00-5:28", a
    voice in their screen time, or a Voice line), never one marked "Speaks: none". Transcript "Name:" labels otherwise."""
    f = Path(run) / "stages" / "1-teardown.md"
    text = f.read_text() if f.is_file() else ""
    owners = []
    blocks = re.split(r"(?m)^(?:###\s+(.+)|\*\*([^*]{1,40})\*\*\s*)$", text)
    for i in range(1, len(blocks) - 2, 3):
        name = (blocks[i] or blocks[i + 1] or "").strip()
        body = blocks[i + 2][:1500]
        if not name or name.isupper() or not re.search(r"Role and screen time", body):
            continue
        if re.search(r"Speaks:\s*none|\bVoice:\**\s*(none|n/a|silent)\b", body, re.I):
            continue
        if re.search(r"Speaks:\s*\S|Voice \(\d|\bVoice:\**\s*\w", body):
            owners.append(re.sub(r"\s*\(.*\)$", "", name).lower())
    if owners:
        return owners
    names = Counter()
    for line in text.splitlines():
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 6 and re.match(r"\d+:\d+", cols[0]):
            m = re.match(r"([A-Z][\w .'-]{0,30}?):\s", cols[5])
            if m:
                names[m.group(1).strip().lower()] += 1
    return [n for n, _ in names.most_common()]


def read_faces(video, fps=8.0):
    import cv2
    import mediapipe as mp
    base = mp.tasks.BaseOptions(model_asset_path=str(CACHE / "face.task"))
    opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, running_mode=mp.tasks.vision.RunningMode.VIDEO,
                                                 num_faces=3, output_face_blendshapes=True)
    lm = mp.tasks.vision.FaceLandmarker.create_from_options(opts)
    rec = cv2.FaceRecognizerSF.create(str(CACHE / "sface.onnx"), "")
    det = None
    cap = cv2.VideoCapture(str(video))
    src = cap.get(cv2.CAP_PROP_FPS) or 30
    step, out, i = max(1, round(src / fps)), [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step == 0:
            t = i / src
            res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)),
                                      int(t * 1000))
            h, w = frame.shape[:2]
            if det is None:
                det = cv2.FaceDetectorYN.create(str(CACHE / "yunet.onnx"), "", (w, h), 0.6)
            _, found = det.detect(frame)
            feats = []                                   # who each face is: an SFace likeness vector, by where it sits
            for row in (found if found is not None else []):
                try:
                    feats.append(((row[0] + row[2] / 2) / w, rec.feature(rec.alignCrop(frame, row)).flatten()))
                except cv2.error:
                    pass
            faces = []
            for pts, bs in zip(res.face_landmarks or [], res.face_blendshapes or []):
                ys, xs = [p.y for p in pts], [p.x for p in pts]
                jaw = next((b.score for b in bs if b.category_name == "jawOpen"), 0.0)
                cx = sum(xs) / len(xs)
                near = min(feats, key=lambda f: abs(f[0] - cx), default=None)
                feat = [round(float(v), 4) for v in near[1]] if near is not None and abs(near[0] - cx) < 0.12 else None
                faces.append({"x": round(cx, 3), "size": round(max(ys) - min(ys), 3), "jaw": round(jaw, 3), "feat": feat})
            out.append({"t": round(t, 3), "faces": faces})
        i += 1
    return out


def _openings(v):
    """Mouth openings: each rise past the mouth's own middle (a still or barely moving mouth has none)."""
    if max(v) - min(v) < 0.08:
        return 0
    mid, n, up = (max(v) + min(v)) / 2, 0, False
    for x in v:
        if x > mid and not up:
            n, up = n + 1, True
        elif x < mid - 0.02:
            up = False
    return n


def _cos(x, y):
    nx, ny = sum(v * v for v in x) ** 0.5, sum(v * v for v in y) ** 0.5
    return sum(p * q for p, q in zip(x, y)) / (nx * ny) if nx and ny else 0.0


def _mean(vs):
    vs = [v for v in vs if v]
    return [sum(c) / len(vs) for c in zip(*vs)] if vs else None


def judge(samples, a, b, spans, owner_on_screen, owner_face=None, bar=None, all_known=True):
    """One shot's picture type from its frames, the speech under it, and whether the frame map names the voice's owner."""
    win = [s for s in samples if a <= s["t"] < b]
    if not win:
        return {"picture": "away", "why": "no frames read"}
    tracks, feats = {}, {}                            # each face, followed by where it sits across the frame
    for s in win:
        for f in s["faces"]:
            if f["size"] < FACE_MIN:
                continue
            key = min(tracks, key=lambda k: abs(k - f["x"]), default=None)
            if key is None or abs(key - f["x"]) > 0.15:
                key = f["x"]
                tracks[key] = []
            tracks[key].append(f["jaw"])
            feats.setdefault(key, []).append(f.get("feat"))
    secs = max(0.01, b - a)
    talk = sum(max(0.0, min(b, e) - max(a, s)) for s, e in spans) / secs
    seen = {k: v for k, v in tracks.items() if len(v) >= 0.5 * len(win)}
    face = max((len(v) / len(win) for v in tracks.values()), default=0.0)
    moves = {k: sum(abs(x - y) for x, y in zip(v, v[1:])) / (len(v) - 1) for k, v in seen.items() if len(v) > 2}
    move = max(moves.values(), default=0.0)
    rate = max((_openings(v) / secs for v in seen.values() if len(v) > 2), default=0.0)
    likeness, owner_here = None, owner_on_screen
    if owner_face and isinstance(owner_face[0], tuple):
        refs = owner_face                            # [(face, bar)], one per speaker
    else:
        refs = [(owner_face, bar or OWNER_LIKE)] if owner_face else []
    if refs and seen:                                # by face: is each face on screen one of the voice's owners?
        # a face's margin over the nearest owner's bar (each speaker has their own face and their own bar)
        like = {k: max(_cos(m, f) - b_ for f, b_ in refs) for k in seen for m in [_mean(feats.get(k) or [])] if m}
        if like:
            owner_here = max(like.values()) >= 0
            mover = max(moves, key=moves.get) if moves else None
            if mover in like:
                likeness = round(like[mover], 3)
                # a mouth that matches no known speaker is a mime only when every speaker's face is known
                owner_on_screen = like[mover] >= 0 or not all_known
            else:
                owner_on_screen = owner_here
    if owner_on_screen is None:
        owner_on_screen = True
    if owner_here is None:
        owner_here = owner_on_screen
    if talk < 0.25:
        kind = "silent"
    elif face >= 0.5 and move >= TALK_MOVE and rate >= TALK_RATE:
        kind = "talking" if owner_on_screen else "mime"
    elif face >= 0.5 and move >= MOVE:
        kind = "reaction"
    elif face >= 0.5 and owner_here:
        kind = "present"
    else:
        kind = "away"
    return {"picture": kind, "lips": LIPS[kind], "faces": len(seen), "face_share": round(face, 2), "speech_share": round(talk, 2),
            "mouth_move": round(move, 3), "openings_per_s": round(rate, 2), "owner_likeness": likeness,
            "why": "faces %d · face %d%% · speech %d%% · mouth %.3f · %.1f openings/s" % (len(seen), face * 100, talk * 100, move, rate)}


def measure(run):
    run = Path(run)
    fm = json.loads((run / "framemap" / "framemap.json").read_text())
    owners = voice_owners(run)
    spans = speech_spans(run / "audio")
    samples = read_faces(run / "source.mp4")
    rows = {}
    firsts = [str(((s.get("map") or {}).get("who") or [""])[0]).lower() for s in fm["shots"]]
    named = any(f.startswith(o) for f in firsts for o in owners)   # the frame map names the voice's owner somewhere
    # the owner's face, learned from shots where the frame map names only them: the one face there is theirs
    # each owner's face, learned from shots where the frame map names only them; each with its own bar, set from how
    # alike that person is to their own face (a drawn style scores every face higher)
    refs, alone = [], []
    for o in owners:
        mine = [s for s in fm["shots"] if len((s.get("map") or {}).get("who") or []) == 1
                and str(s["map"]["who"][0]).lower().startswith(o)]
        faces = [f.get("feat") for s in mine for x in samples if s["start"] <= x["t"] < s["end"] and len(x["faces"]) == 1
                 for f in x["faces"] if f.get("feat")]
        ref = _mean(faces)
        if not ref:
            continue
        selfs = sorted(_cos(f, ref) for f in faces)
        refs.append((ref, max(OWNER_LIKE, selfs[len(selfs) // 2] - OWNER_MARGIN)))
        alone += [s["id"] for s in mine]
    ref = refs or None
    bar = min((b_ for _, b_ in refs), default=OWNER_LIKE)
    for s in fm["shots"]:
        who = [str(w).lower() for w in (s.get("map") or {}).get("who") or []]
        first = who[0] if who else ""
        # by face when the owner's face is known; by the frame map's names otherwise; unknown counts as theirs
        owner = None if ref else (any(first.startswith(o) for o in owners) if named else True)
        rows[s["id"]] = {"start": s["start"], "end": s["end"], "who": who, **judge(samples, s["start"], s["end"], spans, owner, ref, bar, len(refs) == len(owners))}
    return {"schema": "lips/v1", "owners": owners, "owner_face_from": alone[:40], "owner_faces": len(refs), "owner_bar": round(bar, 3), "thresholds": {"face_min": FACE_MIN, "move": MOVE, "talk_move": TALK_MOVE,
            "talk_rate": TALK_RATE}, "counts": dict(Counter(r["picture"] for r in rows.values())), "shots": rows}


def labels(run, compute=True):
    """{K: row} for a run, from <run>/lips.json; measured once (setting the reader up if needed) when missing."""
    f = Path(run) / "lips.json"
    if not f.is_file() and compute:
        ensure(run)
    return json.loads(f.read_text())["shots"] if f.is_file() else {}


def main(argv):
    if not argv:
        sys.exit(__doc__)
    if argv[0] == "setup":
        print(setup())
        return 0
    run = Path(argv[0])
    if not (run / "lips.json").is_file():
        (run / "lips.json").write_text(json.dumps(measure(run), indent=1))
    d = json.loads((run / "lips.json").read_text())
    print(json.dumps(d["counts"]))
    if "--print" in argv:
        for k, r in d["shots"].items():
            print(k, r["picture"], r["why"], "|", ", ".join(r["who"])[:60])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
