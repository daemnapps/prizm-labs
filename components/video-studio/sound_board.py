"""THE SOUND BOARD (2026-11-15): every sound in a scene gets its own card, the swipe's next to ours, with the same
control pictures have. Sound used to be one music bed (music/bed.json: a cue sheet, duck points, an effects list) laid
as timeline rows, with nothing per sound to compare or check.

    python3 sound_board.py build <production> [--scene S1] [--make] [--no-ear] [--fresh]
    python3 sound_board.py show <production> [--scene S1]

One card per sound in the scene:
  music    each section of the swipe's music (build, break, hit, drop, out), from its sound sheet's measured changes
  effect   each added sound the swipe's effects read heard (audio-teardown effects.py, run on the swipe here)
  vocal    each non-word sound a person makes (sniffs, "Ew", "Mm", moans, sighs): the speech-to-text's sound events,
           the sheet's vocal sounds and a lone interjection
  room     the room tone: the quietest second of the scene

Each card holds:
  swipe    the swipe's own clip of that sound, cut out (from its no-voice track for music and effects, its voice
           track for vocal sounds, the full mix for the room)
  ours     the same moment cut from our latest cut (the same track), on our clock (edit_stage.clock), and what it is
           made from: the bank file, the music take and its cue, or the prompt of a take we made
  take     with --make, a new take of the effect (or room) made for this card through ElevenLabs sound generation
           (the door the buzzer was made through), its prompt kept on the card; never laid into the bed by this tool
  checks   lands  ours starts on the swipe's frame (within one frame of our cut)
           level  it sits over or under the music by the swipe's amount (within 3 dB; the room within 6 dB)
           ear    the swipe's and ours heard back to back: same, close or different, and what differs

Files, all in briefs/<production>/sound/ (nothing else in the brief is written):
  swipe/audio/{voices,music,mix}.mp3   the swipe split once (audio-teardown split.py)
  swipe/effects.json                   the swipe's effects read, run here so every card has one
  cut/<cut name>/{voices,music,mix}.mp3  our cut split the same way
  <scene>/board.json                   the cards; <scene>/clips/*.mp3 the cut-out sounds; <scene>/takes/*.mp3 made takes
  index.json                           which scenes have a board (the Studio's Sound button reads it)

The Studio shows it on Production: the Sound button opens the board for the open scene (canvas.html), served by the
existing /files/<production>/sound/... route, so a running Studio needs no restart.
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PY = Path.home() / ".daemn" / "venvs" / "audio" / "bin" / "python"
LEVEL_DB = 3.0          # a sound sits right when it is within this many dB of the swipe's over/under
ROOM_DB = 6.0
SILENT_DB = -60.0       # a track this quiet over a sound's seconds has nothing there
INTERJECTION = re.compile(r"^(e+w+|m+h*m+|h+m+|o+h+|a+h+|u+g+h+|wow|whoa|yu+m+|hu+h|o+o+h+|a+w+|ouch|eh+|hmph)[.!?]*$", re.I)


def _load(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def _teardown(name):
    """A module of the audio teardown (split, effects, gemini), loaded from its own folder."""
    import settings as ST
    root = ST.part("audio-teardown")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("at_" + name, root / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *map(str, args)], check=True)


def cut(src, a, b, out):
    """One clip of src from a to b seconds (never before 0), with 20 ms fades so a cut-out never clicks."""
    a = max(0.0, float(a))
    n = max(0.1, float(b) - a)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    ff("-ss", "%.3f" % a, "-t", "%.3f" % n, "-i", src, "-af",
       "afade=t=in:d=0.02,afade=t=out:st=%.3f:d=0.02" % max(0.0, n - 0.02), "-ac", "1", "-b:a", "160k", out)
    return out


def measure(tracks, asks):
    """Every number the cards need in one run of sound_measure.py (the audio venv)."""
    if not asks:
        return {}
    r = subprocess.run([str(PY), str(HERE / "sound_measure.py")], input=json.dumps({"tracks": tracks, "asks": asks}),
                       capture_output=True, text=True, timeout=900)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {"_error": (r.stderr or r.stdout)[-300:]}


# ---------------------------------------------------------------- where things are
def latest_cut(B):
    """Our newest full cut: rough-cut-v<N>-sdr.mp4 with the highest N (the raw one when no sdr copy exists)."""
    best = None
    for f in glob.glob(str(Path(B) / "rough-cut-v*-*.mp4")):
        m = re.search(r"rough-cut-v(\d+)-(sdr|raw)\.mp4$", f)
        if m:
            k = (int(m.group(1)), m.group(2) == "sdr")
            if best is None or k > best[0]:
                best = (k, f)
    return best[1] if best else None


def split_once(video, out):
    """voices / music / mix of a video, split once (audio-teardown split.py, Demucs) and kept."""
    out = Path(out)
    if (out / "mix.mp3").exists() and (out / "voices.mp3").exists():
        return {k: str(out / (k + ".mp3")) for k in ("voices", "music", "mix") if (out / (k + ".mp3")).exists()}
    tr = _teardown("split").split(Path(video), out)
    return {k: str(v) for k, v in tr.items() if k in ("voices", "music", "mix") and v}


def swipe_window(B, scene, framemap):
    """The swipe seconds a scene copies: the span of the swipe shots its shot-list rows copy."""
    rows = [r for r in (_load(Path(B) / "shot-list.json", {}) or {}).get("shots") or [] if r.get("scene") == scene]
    ks = {r.get("copies") for r in rows if r.get("copies")}
    spans = [(float(s["start"]), float(s["end"])) for s in (framemap or {}).get("shots") or [] if s.get("id") in ks]
    spans += [tuple(map(float, r["swipe_span"])) for r in rows if r.get("swipe_span")]
    if not spans:
        return None
    return min(a for a, _ in spans), max(b for _, b in spans)


def scene_span(B, scene):
    for s in (_load(Path(B) / "studio-build" / "layout.json", {}) or {}).get("scenes") or []:
        if s.get("scene") == scene:
            return float(s["start"]), float(s["end"])
    return None


def fps_of(video):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=r_frame_rate",
                            "-of", "csv=p=0", str(video)], capture_output=True, text=True, timeout=30)
        a, _, b = r.stdout.strip().partition("/")
        return float(a) / float(b or 1)
    except Exception:  # noqa: BLE001
        return 30.0


# ---------------------------------------------------------------- the swipe's sounds
def picture_moments(framemap):
    """The swipe's own edit moments, for its effects read: every cut (with what the frame map says the edit does) and
    every move the edit stage reads (punch-in, flash, graphic pop, push-in)."""
    import edit_stage as ES
    out = []
    for s in (framemap or {}).get("shots") or []:
        e = str((s.get("map") or {}).get("edit") or "").strip()
        if float(s.get("start") or 0) > 0.05:
            out.append({"at": float(s["start"]), "what": "cut to %s%s" % (s.get("id"), (": " + e[:90]) if e else "")})
    for m in ES.read_moves(framemap, {}):
        if m["kind"] not in ("sfx", "music-drop", "music-hit"):
            out.append({"at": float(m["swipe_at"]), "what": "%s: %s" % (m["kind"], m["what"][:90])})
    return sorted(out, key=lambda m: m["at"])


def music_sections(sound, w0, w1):
    """The swipe's music as sections between its measured changes, named: build (the first), break (after a drop
    that the music comes back from), hit (the instant it comes back), drop (the groove after the hit), out (after the
    last drop-out). Only the ones inside [w0, w1] (a hit right at the scene's end is kept)."""
    m = (sound or {}).get("music") or {}
    me = m.get("measured") or {}
    if not m.get("present") and not me.get("present"):
        return []
    start, end = float(me.get("starts") or 0.0), float(me.get("ends") or me.get("seconds") or w1)
    ch = sorted(((float(c["at"]), "drop" if "drop" in str(c.get("what")) else "hit") for c in me.get("changes") or []))
    edges = [(start, "start")] + ch + [(end, "end")]
    out = []
    for i, ((a, why), (b, _)) in enumerate(zip(edges, edges[1:])):
        if why == "start":
            name = "build"
        elif why == "drop":
            name = "break" if any(k == "hit" for t, k in edges[i + 1:]) else "out"
        else:
            name = "drop"
            out.append({"name": "hit", "at": a, "until": None})
        out.append({"name": name, "at": a, "until": b})
    def inside(s):
        if s["until"] is None:                           # the hit: an instant, kept when it falls on the scene
            return w0 - 1e-6 <= s["at"] <= w1 + 0.3
        return min(s["until"], w1) - max(s["at"], w0) > 0.2
    return [s for s in out if inside(s)]


def vocal_sounds(speakers, sound, w0, w1):
    """Every non-word sound a person makes in [w0, w1]: the speech-to-text's sound events ([sniffs], [sighs]), the
    sheet's vocal sounds, and a word said alone that is only a sound ("Ew.", "Mm.")."""
    out = []
    words = (speakers or {}).get("words") or []
    for i, w in enumerate(words):
        a, b, text = float(w.get("start") or 0), float(w.get("end") or 0), str(w.get("text") or "").strip()
        if b < w0 or a > w1:
            continue
        if w.get("type") == "audio_event":
            out.append({"name": text.strip("[]() ").lower(), "at": a, "until": b, "speaker": w.get("speaker")})
        elif w.get("type") == "word" and INTERJECTION.match(text):
            prev = words[i - 1] if i else None
            nxt = words[i + 1] if i + 1 < len(words) else None
            alone = all(not x or x.get("type") != "word" or abs(float(x.get("start", 0)) - a) > 0.6 for x in (prev, nxt))
            if alone:
                out.append({"name": '"%s"' % text, "at": a, "until": b, "speaker": w.get("speaker")})
    for v in (sound or {}).get("vocal_sounds") or []:
        a, b = float(v.get("at") or 0), float(v.get("end") or v.get("until") or v.get("at") or 0)
        if b < w0 or a > w1 or any(o["name"].startswith(str(v.get("sound"))[:4]) and abs(o["until"] - b) < 1.5 for o in out):
            continue
        out.append({"name": str(v.get("sound")), "at": a, "until": b, "speaker": v.get("speaker")})
    return sorted(out, key=lambda x: x["at"])


def tight(span_a, span_b, most=2.5):
    """A long sound-event span (Scribe marks [sniffs] 0-2.98 s) cut to the last `most` seconds before it ends: the
    sound itself, not the silence before it."""
    return max(span_a, span_b - most), span_b


# ---------------------------------------------------------------- ours
def bed_of(B):
    return _load(Path(B) / "music" / "bed.json", {}) or {}


def made_from_effect(e):
    f = str(e.get("file") or "")
    if "/banks/" in f:
        return {"kind": "bank", "file": f, "label": "Bank: " + Path(f).name}
    if e.get("prompt"):
        return {"kind": "prompt", "file": f, "prompt": e["prompt"], "label": "Made: " + e["prompt"][:120]}
    return {"kind": "file", "file": f, "label": Path(f).name + (" (" + e["what"] + ")" if e.get("what") else "")}


def music_made_from(bed, a, b):
    cue = next((c for c in bed.get("cue_sheet") or [] if float(c["at"]) <= a + 0.3 < float(c.get("until", 1e9))), None)
    edit = bed.get("edit") or {}
    line = next((v for k, v in edit.items() if cue and k in str(cue.get("what", "")).lower()), None)
    take = bed.get("take")
    return {"kind": "music take", "file": take, "cue": (cue or {}).get("what"), "edit": line,
            "label": "%s · %s" % (bed.get("source") or "music", take or "bed.mp3") +
                     (" · cue %.2f-%.2f s: %s" % (float(cue["at"]), float(cue["until"]), cue["what"]) if cue else "")}


# ---------------------------------------------------------------- the ear
EAR = """You will hear two sounds with half a second of silence between them. A (first, {a:.1f} s) is a {what} cut from
a short video ad we are copying. B (second, {b:.1f} s) is ours, cut from the same moment of our version. Judge only that
sound, not the picture or the words around it.

Does B sound like A: the same kind of sound, the same weight and length, the same feel? Answer "same" when a listener
would not notice the swap, "close" when it is the same kind of sound but noticeably different, "different" when it is
another sound or missing.

JSON only: {{"match": "same|close|different", "differs": "<one short line: what is different, or empty>"}}"""


def ear(a, b, what):
    """The swipe's clip and ours back to back, judged by the audio teardown's Gemini door (keys fall through)."""
    for clip, who in ((a, "the swipe"), (b, "ours")):
        lv = mean_db(clip)
        if lv is not None and lv < SILENT_DB:          # the ear calls silence "same" (2026-11-15): never ask it
            return {"match": "different", "differs": "nothing to hear: %s is silent here (%.0f dB)" % (who, lv),
                    "model": None}
    G = _teardown("gemini")
    with tempfile.TemporaryDirectory() as td:
        ab = Path(td) / "ab.mp3"
        ff("-i", a, "-i", b, "-f", "lavfi", "-t", "0.5", "-i", "anullsrc=r=44100:cl=mono", "-filter_complex",
           "[0:a]aresample=44100,aformat=channel_layouts=mono[x];[1:a]aresample=44100,aformat=channel_layouts=mono[y];"
           "[x][2:a][y]concat=n=3:v=0:a=1[o]", "-map", "[o]", ab)
        da, db_ = _dur(a), _dur(b)
        got, model, _ = G.ask(ab, EAR.format(a=da, b=db_, what=what))
        got = G.one(got)
        return {"match": got.get("match"), "differs": got.get("differs"), "model": model}


def mean_db(p):
    """The mean level of a clip in dB (ffmpeg volumedetect), or None."""
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(p), "-af", "volumedetect", "-f", "null",
                            os.devnull], capture_output=True, text=True, timeout=60)
        m = re.search(r"mean_volume:\s*(-?[0-9.]+|-inf) dB", r.stderr)
        return None if not m else (-120.0 if m.group(1) == "-inf" else float(m.group(1)))
    except Exception:  # noqa: BLE001
        return None


def _dur(p):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                           capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except Exception:  # noqa: BLE001
        return 0.0


# ---------------------------------------------------------------- making a take (ElevenLabs sound generation)
def take_prompt(card):
    s = card["swipe"]
    name = card["name"]
    if card["kind"] == "room":
        word = str(card.get("room_word") or "").strip()
        place = word if word and word.lower() not in ("silence", "none", "-") else "a quiet small indoor room"
        return "room tone: the quiet sound of %s, steady, no music, no voices, no single sounds" % place
    dur = max(0.5, (s.get("until") or s["at"] + 0.6) - s["at"])
    shape = "a soft sound that rises and swells" if card.get("soft") else "one short, sharp"
    job = ("for a %s" % s["job"].replace("-", " ")) if s.get("job") else ""
    return ("%s %s sound effect %s in a fast social video edit, %.1f seconds, clean and close, no music, no voice"
            % (shape, name, job, dur)).replace("  ", " ")


def make_take(card, out, key=None, transport=None):
    """One take of an effect or the room, through ElevenLabs sound generation (providers.json direct.elevenlabs_banks,
    the door the bank and the buzzer were made through). Returns {"file", "prompt", "seconds", "made_at"}."""
    import urllib.request
    prov = _load(HERE.parent / "video-production" / "machine" / "providers.json", {}) or {}
    door = (prov.get("direct") or {}).get("elevenlabs_banks", {}).get("sound_generation") or {}
    url = (door.get("url") or "https://api.elevenlabs.io/v1/sound-generation") + "?output_format=" + \
        (door.get("query") or {}).get("output_format", "mp3_44100_128")
    s = card["swipe"]
    secs = 10.0 if card["kind"] == "room" else round(max(0.5, min(30.0, (s.get("until") or s["at"] + 0.6) - s["at"])), 2)
    prompt = take_prompt(card)
    body = {"text": prompt, "duration_seconds": secs, "prompt_influence": 0.6,
            "model_id": door.get("model_id") or "eleven_text_to_sound_v2"}
    if card["kind"] == "room":
        body["loop"] = True
    if key is None:
        import settings as ST
        key = ST.key("ELEVENLABS_API_KEY")
    data = json.dumps(body).encode()
    if transport:
        audio = transport(url, data, key)
    else:
        req = urllib.request.Request(url, data=data, headers={"xi-api-key": key, "Content-Type": "application/json"})
        audio = urllib.request.urlopen(req, timeout=300).read()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(audio)
    return {"file": str(out), "prompt": prompt, "seconds": secs, "made_at": time.strftime("%Y-%m-%d %H:%M"),
            "door": "elevenlabs sound-generation " + body["model_id"]}


# ---------------------------------------------------------------- checks
def check_lands(sw_ours_t, ours_t, frame):
    """Ours starts on the swipe's frame: within one frame of our cut."""
    if sw_ours_t is None or ours_t is None:
        return {"id": "lands", "ok": None, "short": "not measured", "detail": "no onset found to compare"}
    d = ours_t - sw_ours_t
    frames = d / frame
    ok = abs(d) <= frame + 0.005
    # V57: our sound is ours; a difference from the swipe's timing, level or feel is a note (None), never red
    return {"id": "lands", "ok": True if ok else None, "short": "on the frame" if ok else "%+.0f frames %s" % (
        frames, "late" if d > 0 else "early"), "detail": "swipe at %.3f s on our clock, ours at %.3f s (%+.3f s, one "
                                                          "frame = %.3f s)" % (sw_ours_t, ours_t, d, frame)}


def check_level(sw, ours, what, tol=LEVEL_DB):
    if sw is None or ours is None:
        return {"id": "level", "ok": None, "short": "not measured", "detail": "no level to compare"}
    d = ours - sw
    ok = abs(d) <= tol
    return {"id": "level", "ok": True if ok else None, "short": "%s %+.0f dB (swipe %+.0f)" % (what, ours, sw) if ok else
            "%.0f dB too %s" % (abs(d), "loud" if d > 0 else "quiet"),
            "detail": "%s: swipe %+.1f dB, ours %+.1f dB (%+.1f, within %.0f dB passes)" % (what, sw, ours, d, tol)}


def check_ear(got):
    if not got or not got.get("match"):
        return {"id": "ear", "ok": None, "short": "not heard", "detail": (got or {}).get("error") or "the ear was not asked"}
    m = got["match"]
    return {"id": "ear", "ok": True if m in ("same", "close") else None, "short": m, "detail": (got.get("differs") or "") +
            (" (heard by %s)" % got.get("model") if got.get("model") else "")}


# ---------------------------------------------------------------- build
def build(n, scene="S1", make=False, use_ear=True, fresh=False, B=None):
    import edit_stage as ES
    import settings as ST
    B = Path(B) if B else ST.BRIEFS / n
    R = ES._writing_run(B)
    sheet = _load(R / "sound-sheet.json", {}) or {}
    fm = _load(R / "framemap" / "framemap.json", {}) or {}
    speakers = _load(R / "audio" / "speakers.json", {}) or {}
    src = R / "source.mp4"
    if not src.exists():
        raise SystemExit("no swipe video in the writing run: %s" % src)
    S = B / "sound"
    sw = split_once(src, S / "swipe" / "audio")
    cutf = latest_cut(B)
    if not cutf:
        raise SystemExit("no cut of ours yet (rough-cut-v*.mp4)")
    ours = split_once(cutf, S / "cut" / Path(cutf).stem)
    frame = 1.0 / fps_of(cutf)
    span = scene_span(B, scene)
    win = swipe_window(B, scene, fm)
    if not span or not win:
        raise SystemExit("scene %s has no place on our clock or in the swipe" % scene)
    rows = (_load(B / "shot-list.json", {}) or {}).get("shots") or []
    lay = _load(B / "studio-build" / "layout.json", {}) or {}
    clock = ES.clock(fm, rows, lay)

    def on_ours(t):
        v = clock(t) if fm.get("shots") else None
        if v is None:                                   # outside a copied shot: in proportion inside the scene
            v = span[0] + (t - win[0]) * (span[1] - span[0]) / max(1e-6, win[1] - win[0])
        return round(v, 3)

    # the swipe's effects, read with the teardown's own effects step (kept; --fresh reads again)
    fxf = S / "swipe" / "effects.json"
    fx = _load(fxf) if fxf.exists() and not fresh else None
    if fx is None and sw.get("music"):
        beats = ((sheet.get("music") or {}).get("measured") or {}).get("beats")
        fx = _teardown("effects").read(sw["music"], beats, picture=picture_moments(fm))
        _save(fxf, fx)
    fx = fx or {"effects": []}
    bed = bed_of(B)
    D = S / scene
    clips = D / "clips"
    cards, asks = [], []
    stem = {"music": "music", "effect": "music", "vocal": "voices", "room": "mix"}

    def add(card):
        cards.append(card)
        return card

    # music sections
    for sec in music_sections(sheet, *win):
        a = max(sec["at"], win[0])
        b = min(sec["until"], win[1]) if sec["until"] else None
        cid = "music-%s-%d" % (sec["name"], int(round(a * 10)))
        add({"id": cid, "kind": "music", "name": sec["name"], "swipe": {"at": round(a, 3), "until": b,
             "what": "the swipe's music: %s" % sec["name"]}, "ours": {"at": on_ours(a), "until": on_ours(b) if b else None}})
    # effects
    for e in fx.get("effects") or []:
        if not (win[0] - 0.05 <= e["at"] <= win[1] + 0.05):
            continue
        cid = "effect-%s-%d" % (re.sub(r"[^a-z]+", "-", str(e.get("name") or "sound")), int(round(e["at"] * 100)))
        add({"id": cid, "kind": "effect", "name": e.get("name") or "sound", "soft": e.get("kind") == "soft",
             "swipe": {"at": e["at"], "until": e.get("until"), "job": e.get("job"), "sure": e.get("sure"),
                       "bank": e.get("bank"), "found": e.get("found"),
                       "what": "%s (%s)" % (e.get("name"), e.get("job") or "effect")},
             "ours": {"at": on_ours(e["at"]), "until": on_ours(e["until"]) if e.get("until") else None}})
    # the people's sounds
    for v in vocal_sounds(speakers, sheet, *win):
        a, b = tight(v["at"], v["until"]) if v["until"] - v["at"] > 2.5 else (v["at"], v["until"])
        cid = "vocal-%s-%d" % (re.sub(r"[^a-z]+", "-", v["name"].lower()).strip("-"), int(round(a * 100)))
        add({"id": cid, "kind": "vocal", "name": v["name"], "swipe": {"at": round(a, 3), "until": round(b, 3),
             "speaker": v.get("speaker"), "what": "a person: %s" % v["name"]},
             "ours": {"at": on_ours(a), "until": on_ours(b)}})
    # the room
    asks.append({"id": "room-swipe", "op": "quiet", "track": "swipe-mix", "a": win[0], "b": win[1]})
    asks.append({"id": "room-ours", "op": "quiet", "track": "ours-mix", "a": span[0], "b": span[1]})
    tracks = {"swipe-" + k: v for k, v in sw.items()}
    tracks.update({"ours-" + k: v for k, v in ours.items()})

    # every number in one pass
    for c in cards:
        k = stem[c["kind"]]
        s, o = c["swipe"], c["ours"]
        if c["kind"] == "music":
            if c["name"] != "build" or s["at"] > win[0] + 0.2:
                asks += [{"id": c["id"] + "|sw-t", "op": "change", "track": "swipe-music", "t": s["at"], "win": 1.0},
                         {"id": c["id"] + "|o-t", "op": "change", "track": "ours-music", "t": o["at"], "win": 1.0}]
            if s.get("until"):
                asks += [{"id": c["id"] + "|sw-m", "op": "level", "track": "swipe-music", "a": s["at"], "b": s["until"]},
                         {"id": c["id"] + "|sw-x", "op": "level", "track": "swipe-mix", "a": win[0], "b": win[1]},
                         {"id": c["id"] + "|o-m", "op": "level", "track": "ours-music", "a": o["at"], "b": o["until"]},
                         {"id": c["id"] + "|o-x", "op": "level", "track": "ours-mix", "a": span[0], "b": span[1]}]
        elif c["kind"] == "vocal":
            a2, b2 = s["at"], s["until"]
            oa2, ob2 = o["at"], o["until"]
            asks += [{"id": c["id"] + "|sw-t", "op": "onset", "track": "swipe-voices", "t": a2, "win": 0.5},
                     {"id": c["id"] + "|o-t", "op": "onset", "track": "ours-voices", "t": oa2, "win": 0.5},
                     {"id": c["id"] + "|sw-v", "op": "level", "track": "swipe-voices", "a": a2, "b": b2},
                     {"id": c["id"] + "|sw-m", "op": "level", "track": "swipe-music", "a": a2, "b": b2},
                     {"id": c["id"] + "|o-v", "op": "level", "track": "ours-voices", "a": oa2, "b": ob2},
                     {"id": c["id"] + "|o-m", "op": "level", "track": "ours-music", "a": oa2, "b": ob2}]
        else:
            asks += [{"id": c["id"] + "|sw-t", "op": "onset", "track": "swipe-" + k, "t": s["at"], "win": 0.25},
                     {"id": c["id"] + "|sw-over", "op": "over", "track": "swipe-mix", "t": s["at"], "until": s.get("until")}]
    got = measure(tracks, asks)

    # the room card, now that its seconds are known
    rs, ro = got.get("room-swipe"), got.get("room-ours")
    if rs and ro:
        add({"id": "room", "kind": "room", "name": "room tone", "room_word": fx.get("room"),
             "swipe": {"at": rs["at"], "until": rs["at"] + 1.0, "what": "the room: %s" % (fx.get("room") or "quietest second")},
             "ours": {"at": ro["at"], "until": ro["at"] + 1.0}})

    # ours: what each card is made from
    fx_ours = [e for e in bed.get("effects") or [] if span[0] - 0.3 <= float(e.get("at", -1)) <= span[1] + 0.3]
    used = set()
    for c in cards:
        o = c["ours"]
        if c["kind"] == "effect":
            near = sorted((abs(float(e["at"]) - o["at"]), i) for i, e in enumerate(fx_ours) if i not in used)
            if near and near[0][0] <= 0.6:
                e = fx_ours[near[0][1]]
                used.add(near[0][1])
                o["made_from"] = made_from_effect(e)
                o["bed_at"] = float(e["at"])
            else:
                o["made_from"] = {"kind": "none", "label": "Nothing of ours here yet"}
        elif c["kind"] == "music":
            o["made_from"] = music_made_from(bed, o["at"], o.get("until") or o["at"])
        elif c["kind"] == "vocal":
            near = next((e for e in fx_ours if e.get("sound") == "reaction" and abs(float(e["at"]) - o["at"]) <= 1.0), None)
            o["made_from"] = made_from_effect(near) if near else {
                "kind": "scene take", "label": "The scene's own take (%s): her sound as filmed" % scene}
        else:
            o["made_from"] = {"kind": "cut", "label": "The cut's own quietest second"}
    for i, e in enumerate(fx_ours):                       # ours with no swipe sound beside it
        if i in used or e.get("sound") == "reaction":
            continue
        t = float(e["at"])
        add({"id": "effect-ours-%d" % int(t * 100), "kind": "effect", "name": e.get("sound") or "sound", "ours_only": True,
             "swipe": {"at": None, "until": None, "what": "nothing in the swipe here"},
             "ours": {"at": t, "until": None, "made_from": made_from_effect(e)}})

    # ours effects: measured where our effect sits in the cut (the bed's second), not at the swipe's
    asks2 = []
    for c in cards:
        if c["kind"] == "effect":
            t = c["ours"].get("bed_at", c["ours"]["at"])
            asks2 += [{"id": c["id"] + "|o-t", "op": "onset", "track": "ours-music", "t": t, "win": 0.25},
                      {"id": c["id"] + "|o-over", "op": "over", "track": "ours-mix", "t": t, "until": None}]
            if c["ours"].get("bed_at") is not None:
                c["ours"]["at"] = round(float(c["ours"]["bed_at"]), 3)
    got.update(measure(tracks, asks2))

    # clips
    for c in cards:
        k = stem[c["kind"]]
        s, o = c["swipe"], c["ours"]
        pad = (0.4, 0.9) if c["kind"] in ("effect", "vocal") and not s.get("until") else (0.25, 0.25)
        if c["kind"] == "music" and not s.get("until"):
            pad = (1.0, 1.5)                             # the hit: a second either side
        if s.get("at") is not None:
            sa, sb = s["at"] - pad[0], (s.get("until") or s["at"]) + pad[1]
            if c["kind"] == "music" and s.get("until"):
                sb = min(sb, sa + 8.0)
            s["clip"] = str(cut(sw[k], sa, sb, clips / (c["id"] + "-swipe.mp3")).relative_to(B))
            s["clip_from"] = round(max(0.0, sa), 3)
        oa, ob = o["at"] - pad[0], (o.get("until") or o["at"]) + pad[1]
        if c["kind"] == "music" and o.get("until"):
            ob = min(ob, oa + 8.0)
        o["clip"] = str(cut(ours[k], oa, ob, clips / (c["id"] + "-ours.mp3")).relative_to(B))
        o["clip_from"] = round(max(0.0, oa), 3)
        mf = o.get("made_from") or {}
        if mf.get("file") and Path(str(mf["file"])).is_file() and str(mf["file"]).endswith(".mp3"):
            dst = clips / (c["id"] + "-source.mp3")
            dst.parent.mkdir(parents=True, exist_ok=True)
            ff("-i", mf["file"], "-t", "8", "-ac", "1", "-b:a", "160k", dst)
            mf["clip"] = str(dst.relative_to(B))

    # checks
    for c in cards:
        s, o, cid = c["swipe"], c["ours"], c["id"]
        checks = []
        if c.get("ours_only"):
            checks.append({"id": "lands", "ok": None, "short": "no swipe sound here", "detail": "ours only"})
        elif c["kind"] == "room":
            checks.append({"id": "lands", "ok": None, "short": "a bed, no frame", "detail": "room tone runs under the scene"})
            checks.append(check_level(rs["db"], ro["db"], "room", ROOM_DB))
        elif c["kind"] == "music":
            sw_t, o_t = got.get(cid + "|sw-t"), got.get(cid + "|o-t")
            if c["name"] == "build" and s["at"] <= win[0] + 0.2:
                sw_t, o_t = on_ours(s["at"]), o["at"]
            else:
                sw_t = on_ours(sw_t) if sw_t is not None else None
            checks.append(check_lands(sw_t, o_t, frame))
            sm, sx, om, ox = (got.get(cid + x) for x in ("|sw-m", "|sw-x", "|o-m", "|o-x"))
            if None not in (sm, sx, om, ox):
                checks.append(check_level(sm - sx, om - ox, "music against the scene"))
            else:
                checks.append({"id": "level", "ok": None, "short": "an instant", "detail": "the hit is checked by its frame"})
        elif c["kind"] == "vocal" and (got.get(cid + "|o-v") is None or got[cid + "|o-v"] < SILENT_DB):
            checks.append({"id": "lands", "ok": False, "short": "missing in our cut",
                           "detail": "our cut's voice track is silent here (%s dB)" % got.get(cid + "|o-v")})
            checks.append({"id": "level", "ok": False, "short": "missing", "detail": "swipe voice %s dB, ours silent"
                           % got.get(cid + "|sw-v")})
        else:
            sw_t, o_t = got.get(cid + "|sw-t"), got.get(cid + "|o-t")
            if o.get("made_from", {}).get("kind") == "none":
                checks.append({"id": "lands", "ok": None, "short": "nothing of ours (noted)", "detail": "no effect of ours "
                               "within 0.6 s of this moment (music/bed.json effects)"})
            else:
                checks.append(check_lands(on_ours(sw_t) if sw_t is not None else None, o_t, frame))
            if c["kind"] == "vocal":
                sv, sm, ov, om = (got.get(cid + x) for x in ("|sw-v", "|sw-m", "|o-v", "|o-m"))
                checks.append(check_level(sv - sm if None not in (sv, sm) else None,
                                          ov - om if None not in (ov, om) else None, "voice over the music"))
            else:
                checks.append(check_level(got.get(cid + "|sw-over"), got.get(cid + "|o-over"), "over the music"))
        c["checks"] = checks

    # takes (ElevenLabs), only when asked: a spend
    if make:
        for c in cards:
            if c["kind"] not in ("effect", "room") or c.get("ours_only"):
                continue
            n_take = len(glob.glob(str(D / "takes" / (c["id"] + "-take-*.mp3")))) + 1
            try:
                c["take"] = make_take(c, D / "takes" / ("%s-take-%d.mp3" % (c["id"], n_take)))
                c["take"]["file"] = str(Path(c["take"]["file"]).relative_to(B))
            except Exception as e:  # noqa: BLE001 — one take that fails is said on its card, never fatal
                c["take"] = {"error": str(e)[:200], "prompt": take_prompt(c)}
    else:
        old = {c["id"]: c for c in (_load(D / "board.json", {}) or {}).get("cards") or []}
        for c in cards:
            if old.get(c["id"], {}).get("take"):
                c["take"] = old[c["id"]]["take"]

    # the ear: the swipe's clip and ours, and the swipe's and the new take
    if use_ear:
        from concurrent.futures import ThreadPoolExecutor

        def hear(c):
            s, o = c["swipe"], c["ours"]
            if not s.get("clip"):
                return
            what = {"music": "piece of music", "effect": "sound effect", "vocal": "sound a person makes",
                    "room": "room tone"}[c["kind"]]
            try:
                c["checks"].append(check_ear(ear(B / s["clip"], B / o["clip"], what)))
            except Exception as e:  # noqa: BLE001
                c["checks"].append(check_ear({"error": str(e)[:160]}))
            t = c.get("take") or {}
            if t.get("file") and not t.get("ear"):
                try:
                    t["ear"] = check_ear(ear(B / s["clip"], B / t["file"], what))
                except Exception as e:  # noqa: BLE001
                    t["ear"] = check_ear({"error": str(e)[:160]})
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(hear, cards))
    else:
        for c in cards:
            c["checks"].append({"id": "ear", "ok": None, "short": "not heard", "detail": "built with --no-ear"})

    order = {"music": 0, "effect": 1, "vocal": 2, "room": 3}
    cards.sort(key=lambda c: (order[c["kind"]], c["ours"]["at"]))
    board = {"production": n, "scene": scene, "built": time.strftime("%Y-%m-%d %H:%M"),
             "cut": Path(cutf).name, "frame_seconds": round(frame, 4),
             "swipe_window": [round(win[0], 3), round(win[1], 3)], "ours_window": [round(span[0], 3), round(span[1], 3)],
             "effects_read": {"prompt": fx.get("prompt"), "heard_by": fx.get("heard_by"),
                              "moments_found": fx.get("moments_found"), "room": fx.get("room")},
             "counts": {k: sum(1 for c in cards if c["kind"] == k) for k in order},
             "fails": sum(1 for c in cards for k in c["checks"] if k["ok"] is False),
             "cards": cards}
    _save(D / "board.json", board)
    idx = _load(S / "index.json", {}) or {}
    idx.setdefault("scenes", {})[scene] = {"board": "sound/%s/board.json" % scene, "built": board["built"],
                                           "cards": len(cards), "fails": board["fails"]}
    _save(S / "index.json", idx)
    return board


def show(board):
    lines = ["%s · %s · %d cards, %d checks off (cut %s)" % (board["production"], board["scene"], len(board["cards"]),
                                                           board["fails"], board["cut"])]
    for c in board["cards"]:
        marks = " ".join("%s %s" % ({True: "✓", False: "✗", None: "–"}[k["ok"]], k["short"]) for k in c["checks"])
        at = c["swipe"]["at"]
        lines.append("  %-7s %-16s swipe %-7s ours %-7.2f  %s" % (c["kind"], c["name"][:16],
                                                                   "%.2f" % at if at is not None else "—", c["ours"]["at"], marks))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Every sound in a scene, the swipe's next to ours, with its checks.")
    ap.add_argument("what", choices=["build", "show"])
    ap.add_argument("production")
    ap.add_argument("--scene", default="S1")
    ap.add_argument("--make", action="store_true", help="make a new take of every effect and the room (ElevenLabs, a spend)")
    ap.add_argument("--no-ear", action="store_true", help="skip the by-ear checks (no Gemini calls)")
    ap.add_argument("--fresh", action="store_true", help="read the swipe's effects again")
    a = ap.parse_args(argv)
    if a.what == "build":
        b = build(a.production, a.scene, make=a.make, use_ear=not a.no_ear, fresh=a.fresh)
    else:
        import settings as ST
        b = _load(ST.BRIEFS / a.production / "sound" / a.scene / "board.json")
        if not b:
            print("no sound board for %s %s yet" % (a.production, a.scene))
            return 1
    print(show(b))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
