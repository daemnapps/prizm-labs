"""THE EDIT STAGE (2026-11-13): after a production's versions are rendered and before its covers, the swipe's edit moves
are read off the swipe, set on our clock and laid as their own layers; the covers wait until every move is laid or has
a reason: the edit moves are part of the chain, not a hand pass (decision 2026-11-12 "A video is finished only after
the edit pass").

    python3 edit_stage.py run <production>      read the moves, lay what the stage lays itself, write edit/stage.json
    python3 edit_stage.py state <production>    every move, its second in the swipe and in ours, laid or why not

The steps (each a step on the Next step screen, STEPS below):
  read   every edit move the swipe's teardown names: the frame map's per-shot `edit` (a punch-in, a flash or red
         vignette, a graphic pop, any move that is not a plain cut) and `camera.move` (a push-in), the sound sheet's
         effects (each sound and its job) and its music changes (drops out, builds / hits). Read from the writing run
         the brief names (framemap/framemap.json, sound-sheet.json).
  clock  each move's second in our cut: the swipe shot it sits in (K..) is the shot-list row that copies it; its place
         inside that shot is kept in proportion (studio-build/layout.json for the scene times, the rows' shares).
  lay    what the stage lays itself: each sound effect goes into music/bed.json "effects" at its second, from the sound
         bank (components/video-production/banks/sfx) by name, and is then its own row in the edit (to_studio
         sound_layers). A sound the bank has no take of is not laid: its reason says so (the edit line's sfx_make makes
         banked sounds). A music change is laid when the bed has a stop or a cue within `music_window` seconds of it.
         Every other move (a punch-in, a flash, a graphic pop) is laid by whoever lays it, in the production's own
         layers, and recorded in brief.json "edit": {"<move id>": {"landed": "<where>"} | {"reason": "<why not>"}}.
  check  every move laid or with a reason. A move with neither holds the production before the covers (`hold`).
         Props a graphic pop floats in are pictures from image production (a cut-out with a run record), never drawn
         shapes: a pop whose record names no image-production picture is not counted as laid (`props_from_tool`).

Files, in briefs/<production>/edit/: stage.json (every move, the board's source). The Checks panel shows them as the
"Edit moves" group (checks_board.py).

  music  (2026-11-13) a production whose bed is not made from the swipe gets one (make_music: the swipe's sound sheet,
         its sections on our cuts, ElevenLabs Music); a bed that goes silent inside, and captions not set from the
         swipe's look (brief.json captions.look `from_swipe`), hold like an open move until fixed or reasoned.

  reads  (2026-11-13) every spoken shot against its own line (edit_notes.line_check: the vision_judge door on the
         rendered cut; a miss names the shot and the line), the props laid through the layers template (layers.py,
         brief.json "layers": centred, waist height, never in a close-up, image-production cut-outs), and every edit
         note in the brief (edit_notes.brief_notes: 5-brief.md B-ROLL, CARDS, END CARD, LAYERS AND SOUND, and
         brief.json "edit_notes"). Each is a row; one neither laid nor reasoned holds like an open move.

  moves  (2026-11-17) the moves director (edit_moves.py, video-edit moves/machine/director.py): one edit move per
         scene, pitched safe / bold / wild and kept by a stated machine rule, written to edit/moves-picks.json and laid
         by to_studio.py on the next render; a move the edit cannot lay for free is a gap row with its reason.

SWITCH: edit-stage.json beside this file (`on`, and the parts `lay_sfx`, `hold`, `props_from_tool`, `music_from_swipe`,
`line_check`, `props_template`, `brief_notes`, `director`), or
VIDEO_STUDIO_EDIT_OFF=1 / =<part>[,<part>] on one machine. Row EDIT-STAGE in team/rollbacks.md.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")  # the Studio's production side (settings, takes, voices) until each seam is cut
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))  # this folder first, then the Studio it serves

CONF = HERE / "edit-stage.json"
STEPS = [("read", "Every edit move read off the swipe"), ("clock", "Each move set on our clock"),
         ("lay", "Sound effects and music laid as their own layers"), ("check", "Every move laid or with a reason")]
PARTS = ("lay_sfx", "hold", "props_from_tool", "music_from_swipe", "line_check", "props_template", "brief_notes",
         "listen", "reactions", "director")
ALIAS = {"woosh": "whoosh", "swoosh": "whoosh", "swish": "swoosh-soft", "typing": "typewriter", "tick": "click"}


def _load(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def conf():
    return _load(CONF, {}) or {}


def _env_off():
    return {x.strip() for x in os.environ.get("VIDEO_STUDIO_EDIT_OFF", "").split(",") if x.strip()}


def on() -> bool:
    """Is the edit stage on? No switch file: on."""
    return not (_env_off() & {"1", "all", "on"}) and conf().get("on", True) is not False


def part_on(name) -> bool:
    return name not in _env_off() and conf().get(name, True) is not False


# ---------------------------------------------------------------- read: the swipe's moves
def _kind(text):
    t = (text or "").lower()
    if re.search(r"\b(zoom|punch)", t):
        return "punch-in"
    if re.search(r"\b(red|flash|vignette|glitch|whip)", t):
        return "flash"
    if re.search(r"\b(graphic|overlay|pop|sticker|bottle|logo)", t):
        return "graphic-pop"
    return "edit"


def read_moves(framemap, sound):
    """Every edit move: [{"id", "kind", "k", "swipe_at", "what"}], from the frame map and the sound sheet (dicts)."""
    moves = []
    for s in (framemap or {}).get("shots") or []:
        m = s.get("map") or {}
        e = str(m.get("edit") or "").strip()
        kind = _kind(e)
        if kind != "edit":               # a plain cut (however it is worded) is the cut itself, not a move to lay
            at = float(s["end"]) - 0.3 if kind in ("punch-in", "flash") and "end" in e.lower() else float(s["start"])
            moves.append({"kind": kind, "k": s["id"], "swipe_at": round(at, 2), "what": e[:160]})
        cam = str((m.get("camera") or {}).get("move") or "")
        if re.search(r"push", cam, re.I):
            moves.append({"kind": "push-in", "k": s["id"], "swipe_at": float(s["start"]), "what": "camera: " + cam[:120]})
    for fx in ((sound or {}).get("effects") or {}).get("effects") or []:
        moves.append({"kind": "sfx", "k": None, "swipe_at": float(fx["at"]), "sound": fx.get("name"),
                      "what": "%s (%s)" % (fx.get("name"), fx.get("job") or "effect")})
    mus = (sound or {}).get("music") or {}
    for c in (mus.get("measured") or {}).get("changes") or (mus.get("heard") or {}).get("changes") or []:
        what = str(c.get("what") or "")
        moves.append({"kind": "music-drop" if "drop" in what else "music-hit", "k": None, "swipe_at": float(c["at"]),
                      "what": "music " + what})
    moves.sort(key=lambda m: m["swipe_at"])
    for i, m in enumerate(moves, 1):
        m["id"] = "%s-%d" % (m["kind"], i)
    return moves


# ---------------------------------------------------------------- clock: the swipe's second → ours
def shot_of(framemap, t):
    for s in (framemap or {}).get("shots") or []:
        if float(s["start"]) <= t < float(s["end"]) + 1e-6:
            return s
    return None


def clock(framemap, rows, layout):
    """A function: the swipe's second → our second (None where no row of ours copies that swipe shot). rows: the shot
    list's rows (scene, copies, share), layout: {"scenes": [{"scene", "start", "end"}]}."""
    sc = {s["scene"]: s for s in (layout or {}).get("scenes") or []}
    at, k_at = {}, {}
    for r in rows:
        s = sc.get(r["scene"])
        if not s:
            continue
        d = float(s["end"]) - float(s["start"])
        a = at.get(r["scene"], float(s["start"]))
        span = float(r.get("share") or 0) * d
        if r.get("copies"):
            k_at[r["copies"]] = (a, span)
        at[r["scene"]] = a + span

    def ours(t):
        s = shot_of(framemap, t)
        if not s or s["id"] not in k_at:
            return None
        a, span = k_at[s["id"]]
        frac = (t - float(s["start"])) / max(1e-6, float(s["end"]) - float(s["start"]))
        return round(a + max(0.0, min(1.0, frac)) * span, 2)
    return ours


# ---------------------------------------------------------------- lay
def _bank():
    """The sound bank: {id: local file} for every banked effect that is on this machine."""
    idx = _load(HERE.parents[2] / "video-production" / "banks" / "sfx" / "index.json", {}) or {}
    roots = [Path(os.environ["VIDEO_STUDIO_DRIVE"])] if os.environ.get("VIDEO_STUDIO_DRIVE") else []
    roots += sorted(Path.home().glob("Library/CloudStorage/GoogleDrive-*/Shared drives"))
    out = {}
    for r in idx.get("rows") or []:
        for root in roots:
            f = root / str(r.get("file") or "")
            if r.get("id") and f.is_file():
                out[r["id"]] = str(f)
                break
    return out


def lay_sfx(moves, bed, bank, start=0.0, skip=()):
    """Each sfx move with our second goes into the bed plan's "effects" (on the bed's clock: our second - start) unless
    an effect already sits within `sfx_window` (1 s) of it, or the move has its own record in brief.json "edit" (skip:
    an effect placed on purpose, e.g. moved onto the frame of change, is never laid twice). Returns the ids laid now."""
    effects = bed.setdefault("effects", [])
    laid = []
    for m in moves:
        if m["kind"] != "sfx" or m.get("ours") is None or m["id"] in skip:
            continue
        t = round(m["ours"] - start, 3)
        if any(abs(float(e.get("at", -99)) - t) <= float(conf().get("sfx_window", 1.0)) for e in effects):
            m["landed"] = "already in the bed's effects at %.2f s" % (m["ours"])
            continue
        name = ALIAS.get(m.get("sound"), m.get("sound"))
        f = bank.get(name)
        if not f:
            m["reason"] = "the sound bank has no '%s': make it (video-edit sfx_make.py) and run the stage again" % name
            continue
        effects.append({"at": t, "sound": name, "what": "swipe %s at %.2f s" % (m["what"], m["swipe_at"]), "file": f,
                        "volume_db": -6})
        m["landed"] = "laid: Effect · %s at %.2f s" % (name, m["ours"])
        laid.append(m["id"])
    effects.sort(key=lambda e: float(e.get("at", 0)))
    return laid


def music_laid(m, bed, start=0.0, window=0.75):
    """A music change is laid when the bed has a stop (silent duck stretch) or a cue within `window` of it."""
    if m.get("ours") is None:
        return None
    t = m["ours"] - start
    drop = bed.get("dropout")
    if drop and abs(float(drop[0]) - t) <= window and m["kind"] == "music-drop":
        return "the bed drops out at %.2f s" % (float(drop[0]) + start)
    if drop and abs(float(drop[1]) - t) <= window and m["kind"] == "music-hit":
        return "the bed hits at %.2f s" % (float(drop[1]) + start)
    for c in bed.get("cue_sheet") or []:
        if abs(float(c.get("at", -99)) - t) <= window:
            return "a cue of the bed at %.2f s: %s" % (float(c["at"]) + start, c.get("what", ""))
    for p in bed.get("duck_points") or []:
        if m["kind"] == "music-drop" and float(p.get("v", 1)) == 0 and abs(float(p["t"]) - t) <= window:
            return "the bed goes silent at %.2f s" % (float(p["t"]) + start)
    return None


def _from_tool(rec):
    """A graphic pop's record names an image-production picture (a file with a run record beside it)."""
    for f in re.findall(r"(/[^ ,;]+\.(?:png|webp|jpg))", json.dumps(rec)):
        p = Path(f)
        if p.is_file() and any((d / "run.json").is_file() for d in (p.parent, p.parent.parent)):
            return True
    return False


def check(moves, records):
    """Every move laid or with a reason; records: brief.json "edit". Returns the moves still open (ids)."""
    open_ = []
    for m in moves:
        r = (records or {}).get(m["id"]) or {}
        if r.get("landed") and not m.get("landed"):
            m["landed"] = r["landed"]
            if m["kind"] == "graphic-pop" and part_on("props_from_tool") and not _from_tool(r):
                m.pop("landed")
                m["reason_open"] = "the pop's props are not named as image-production pictures"
        if r.get("reason") and not m.get("landed"):
            m["reason"] = r["reason"]
        if not m.get("landed") and not m.get("reason"):
            open_.append(m["id"])
    return open_


# ---------------------------------------------------------------- music: the swipe's own sound, on our cuts
def music_plan(sound, ours, length):
    """An ElevenLabs Music composition plan from the swipe's sound sheet: its genre, tempo, key, instruments and mood,
    instrumental (it sits under our voice), its sections cut where the swipe's music drops out and hits, set on our
    clock (`ours`, the swipe's second -> ours). Returns (plan, cues)."""
    m = (sound or {}).get("music") or {}
    me, he = m.get("measured") or {}, m.get("heard") or {}
    ck = m.get("checked") or {}
    if ck.get("agreed"):                  # 2026-11-13: the music as two listens of the isolated track agree, not a name
        he = dict(he, genre=ck.get("genre"), subgenre=ck.get("subgenre"), instruments=ck.get("instruments") or [],
                  mood_words=ck.get("mood_words") or [])
        tempo = ("%s BPM, %s" % (ck["bpm"], ck.get("felt_tempo") or "")) if ck.get("bpm") else ""
    else:
        tempo = ("%d BPM" % round(me["tempo_bpm"])) if me.get("tempo_bpm") else ""
    styles = [x for x in [" ".join(x for x in (he.get("subgenre"), he.get("genre")) if x), tempo,
                          me.get("key") or ""] if x]
    styles += list(he.get("instruments") or []) + list(he.get("mood_words") or []) + ["instrumental"]
    marks = []
    for c in me.get("changes") or he.get("changes") or []:
        t = ours(float(c["at"]))
        if t is not None and 0.5 < t < length - 0.5:
            marks.append((round(t, 3), "drop" if "drop" in str(c.get("what")) else "hit"))
    edges = [0.0] + [t for t, _ in marks] + [length]
    kinds = ["start"] + [k for _, k in marks]
    secs, cues = [], []
    for i, k in enumerate(kinds):
        a, b = edges[i], edges[i + 1]
        if b - a < 0.5:
            continue
        pos = {"start": ["the track's opening groove, full energy, building"],
               "drop": ["drops out: almost empty, a soft pad and a riser only, no drums, no bass"],
               "hit": ["the hit: full energy on the first beat, the main groove"]}[k]
        if i == len(kinds) - 1:
            pos = pos + ["ends with a short final hit and a quick fade"]
        secs.append({"section_name": "%s %d" % (k, i + 1), "positive_local_styles": pos,
                     "negative_local_styles": ["drums", "bass"] if k == "drop" else [],
                     "duration_ms": int(round((b - a) * 1000)), "lines": []})
        cues.append({"at": round(a, 3), "until": round(b, 3), "what": {"start": "the swipe's groove from the top",
                     "drop": "the swipe's drop-out: low, never silent", "hit": "the swipe's hit"}[k]})
    neg = ["vocals", "singing", "rap", "spoken word"]
    if ck.get("agreed") and ck.get("family") != "pop":
        neg += ["pop", "synth-pop", "EDM", "four-on-the-floor"]
    plan = {"positive_global_styles": styles, "negative_global_styles": neg,
            "sections": secs}
    return plan, cues


def make_music(B, sound, ours, length, transport=None, key=None):
    """The bed made from the swipe's sound sheet (ElevenLabs Music, its sections on our cuts): music/swipe-music.mp3,
    music/bed.mp3 and bed.json ("from_swipe": true; the drop-out ducked low, never silent; effects kept)."""
    import subprocess
    import urllib.request
    plan, cues = music_plan(sound, ours, length)
    if not plan["sections"]:
        return None
    m = Path(B) / "music"
    m.mkdir(exist_ok=True)
    (m / "swipe-music-plan.json").write_text(json.dumps(plan, indent=1))
    if key is None:
        import settings as ST
        key = ST.key("ELEVENLABS_API_KEY")
    body = json.dumps({"composition_plan": plan, "model_id": "music_v1"}).encode()
    url = "https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192"
    if transport:
        audio = transport(url, body, key)
    else:
        req = urllib.request.Request(url, data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
        audio = urllib.request.urlopen(req, timeout=900).read()
    (m / "swipe-music.mp3").write_bytes(audio)
    if not transport:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(m / "swipe-music.mp3"), "-af",
                        "highshelf=f=3000:g=-4,equalizer=f=1800:t=q:w=1.2:g=-3,lowshelf=f=90:g=2,volume=-2dB,alimiter=limit=0.89",
                        "-ar", "44100", "-c:a", "libmp3lame", "-q:a", "2", str(m / "bed.mp3")], check=True)
    old = _load(m / "bed.json", {}) or {}
    v = lambda db: round(10 ** (db / 20), 4)
    pts = [{"t": 0, "v": 0}, {"t": 0.05, "v": v(-6)}]
    drops = [c for c in cues if "drop-out" in c["what"]]
    first_voice = next((c["at"] for c in cues if "hit" in c["what"]), None)
    for c in drops:
        pts += [{"t": round(c["at"] - 0.05, 3), "v": v(-6)}, {"t": round(c["at"] + 0.1, 3), "v": v(-14)},
                {"t": round(c["until"] - 0.05, 3), "v": v(-14)}]
    if first_voice is not None:
        pts += [{"t": round(first_voice + 0.05, 3), "v": v(-15)}]
    pts += [{"t": round(length - 0.1, 3), "v": v(-15)}, {"t": round(length, 3), "v": 0}]
    bed = {"source": "elevenlabs", "lane": "the swipe's own sound", "take": "swipe-music.mp3", "from_swipe": True,
           "music_checked": bool(((sound or {}).get("music") or {}).get("checked", {}).get("agreed")),
           "why": "made from the swipe's sound sheet, its sections on this ad's cuts (edit_stage make_music, decision 2026-11-13)",
           "starts_at": 0.0, "cue_sheet": cues, "effects": old.get("effects") or [], "duck_points": sorted(pts, key=lambda p: p["t"]),
           "dropout": [drops[0]["at"], drops[0]["until"]] if drops else None}
    (m / "bed.json").write_text(json.dumps(bed, indent=1, ensure_ascii=False))
    return bed


# ---------------------------------------------------------------- the people's own sounds (2026-11-13)
REACT_TEXT = {"ew": "[disgusted] Ew.", "ugh": "[disgusted] Ugh.", "sniff": "[sniffs]", "inhale": "[inhales slowly]",
              "sigh": "[sighs]", "hmm": "[unimpressed] Hmm.", "mmm": "[pleased] Mmm.", "moan": "[moans softly] Mmmh...",
              "gasp": "[gasps]", "laugh": "[laughs]", "kiss": "[kisses]"}


def _listen():
    import importlib.util
    import settings as ST
    p = ST.part("video-teardown") / "machine" / "listen.py"
    spec = importlib.util.spec_from_file_location("edit_listen", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def reaction_text(sound, feeling):
    """The words a voice model is given for one non-word sound: its audio tag, the feeling turned up."""
    key = next((k for k in REACT_TEXT if k in str(sound).lower()), None)
    if key is None:
        return None
    t = REACT_TEXT[key]
    f = str(feeling or "").lower()
    if key in ("mmm", "moan") and f in ("aroused", "delighted"):
        t = "[moans, delighted] Mmmmh..." if key == "moan" or f == "aroused" else "[delighted] Mmm!"
    if key == "sigh" and f in ("aroused", "delighted"):
        t = "[sighs with pleasure] Ahh..."
    if key == "sigh" and f in ("unimpressed", "disgust"):
        t = "[sighs, unimpressed] Hmph."
    return t


def reaction_moves(sound, ours):
    """Every non-word sound the swipe's people make (sound-sheet `human_sounds`, listen.py) as a move on our clock."""
    out = []
    for i, h in enumerate((sound or {}).get("human_sounds") or [], 1):
        t = ours(float(h["at"]))
        if t is None or not reaction_text(h.get("sound"), h.get("feeling")):
            continue
        out.append({"id": "reaction-%d" % i, "kind": "reaction", "swipe_at": float(h["at"]), "ours": round(t, 3),
                    "sound": h.get("sound"), "feeling": h.get("feeling"),
                    "what": "%s (%s), %.1f s long" % (h.get("sound"), h.get("feeling"), float(h["until"]) - float(h["at"]))})
    return out


def lay_reactions(B, moves, bed, brief, say_fn=None):
    """Each reaction made in the production's reaction voice (brief.json `edit_voices.reactions`, an ElevenLabs voice
    id we own) with eleven_v3 audio tags, trimmed, and laid into the bed's effects at its second. A move already in
    the bed is not made again. Without a voice the moves hold with that reason. Returns the ids laid now."""
    voice = ((brief or {}).get("edit_voices") or {}).get("reactions")
    effects = bed.setdefault("effects", [])
    have = {e.get("move") for e in effects}
    laid = []
    for m in moves:
        if m["id"] in have:
            e = next(e for e in effects if e.get("move") == m["id"])
            m["landed"] = "Effect · her %s at %.2f s (%s)" % (m["sound"], float(e["at"]), Path(e["file"]).name)
            continue
        if not voice:
            m["reason_open"] = "no voice named for the people's sounds (brief.json edit_voices.reactions)"
            continue
        out = Path(B) / "music" / ("react-%s.mp3" % m["id"])
        try:
            make_reaction(reaction_text(m["sound"], m["feeling"]), voice, out)
        except Exception as e:  # noqa: BLE001
            m["reason_open"] = "the sound could not be made: %s" % str(e)[:120]
            continue
        effects.append({"at": round(m["ours"], 3), "sound": "reaction", "move": m["id"], "file": str(out),
                        "volume_db": 0, "what": "her %s (%s), from the swipe at %.2f s" % (m["sound"], m["feeling"],
                                                                                        m["swipe_at"])})
        m["landed"] = "laid: Effect · her %s at %.2f s" % (m["sound"], m["ours"])
        laid.append(m["id"])
    effects.sort(key=lambda e: float(e.get("at", 0)))
    return laid


def make_reaction(text, voice, out, key=None, transport=None):
    """One non-word sound in a voice we own (ElevenLabs eleven_v3, audio tags), silence trimmed off both ends."""
    import subprocess
    import urllib.request
    if key is None:
        import settings as ST
        key = ST.key("ELEVENLABS_API_KEY")
    url = "https://api.elevenlabs.io/v1/text-to-speech/%s?output_format=mp3_44100_128" % voice
    body = json.dumps({"text": text, "model_id": "eleven_v3"}).encode()
    if transport:
        audio = transport(url, body, key)
    else:
        req = urllib.request.Request(url, data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
        audio = urllib.request.urlopen(req, timeout=300).read()
    raw = Path(out).with_suffix(".raw.mp3")
    raw.write_bytes(audio)
    if transport:
        Path(out).write_bytes(audio)
        return out
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse", str(out)], check=True)
    return out


def silent_gap(bed):
    """A stretch inside the bed where the music is ducked to nothing (a drop-out that went silent), or None."""
    pts = sorted((bed or {}).get("duck_points") or [], key=lambda p: float(p["t"]))
    if len(pts) < 3:
        return None
    for a, b in zip(pts[1:-1], pts[2:-1]):
        if float(a.get("v", 1)) == 0 and float(b.get("v", 1)) == 0 and float(b["t"]) - float(a["t"]) > 0.3:
            return (float(a["t"]), float(b["t"]))
    return None


# ---------------------------------------------------------------- the stage
def folder(n, B=None):
    if B:
        return Path(B)
    import settings as ST
    return ST.BRIEFS / n


def _writing_run(B):
    import seed_from_brief as SB
    b = _load(B / "brief.json", {}) or {}
    return SB.WORK / (b.get("run") or b.get("brief") or "")


CAMERA_MOVES = {"push-in": "push", "punch-in": "punch"}


def lay_camera(B, moves, brief):
    """A footage lane (real, mix): the swipe's camera moves are laid on OUR clips by the stage itself, never left for a
    hand pass (owner, 20 Nov 2026: "these edits should not take that long, especially for the real shit"). Each
    push-in / punch-in lands on every shot of ours that copies the swipe shot it sits in, as that pick's
    `params.move` (picks.json: the cut carries a pick's params onto its step, so a re-cut keeps it; the scene runner
    pushes or punches the clip); a move whose swipe shot no shot of ours copies gets that reason. Recorded in
    brief.json "edit" so the check reads it. -> the ids laid now."""
    if (brief.get("lane") or "real") == "ai":
        return []
    pf = B / "picks.json"
    picks = _load(pf, {}) or {}
    shots = picks.get("shots") or {}
    rows = (_load(B / "shot-list.json", {}) or {}).get("shots") or []
    by_k = {}
    for r in rows:
        if r.get("copies") and r["id"] in shots:
            by_k.setdefault(r["copies"], []).append(r["id"])
    rec = brief.setdefault("edit", {})
    laid, changed, target = [], False, {}
    for m in moves:
        mv = CAMERA_MOVES.get(m.get("kind"))
        if not mv or m.get("landed") or (rec.get(m["id"]) or {}).get("reason"):
            continue
        ids = by_k.get(m.get("k")) or []
        if not ids:
            m["reason"] = "the swipe shot %s is not copied by any shot of ours" % m.get("k")
            rec[m["id"]] = {"reason": m["reason"]}
            continue
        for sid in ids:
            target[sid] = mv           # two moves on one shot: the later one stands, as before
        m["landed"] = "%s on %s (picks.json params.move)" % (m["kind"], ", ".join(ids))
        rec[m["id"]] = {"landed": m["landed"]}
        laid.append(m["id"])
    # each shot's final move is compared with what it holds, so a shot two moves land on is not rewritten (and
    # re-cut) on every pass (2026-11-20: three shots flipped push/punch each pass and the cut never settled)
    for sid, mv in target.items():
        prm = shots[sid].setdefault("params", {})
        if prm.get("move") != mv:
            prm["move"], changed = mv, True
    if changed:
        pf.write_text(json.dumps(picks, indent=1, ensure_ascii=False))
    (B / "brief.json").write_text(json.dumps(brief, indent=1, ensure_ascii=False))
    return laid


def run(n, B=None, say=lambda *a, **k: None, run_dir=None):
    B = folder(n, B)
    R = Path(run_dir) if run_dir else _writing_run(B)
    say("read", "doing")
    fm = _load(R / "framemap" / "framemap.json", {}) or {}
    sound = _load(R / "sound-sheet.json", {}) or {}
    if not fm.get("shots"):              # nothing to lay: the stage passes and the covers go on (never due again)
        st = {"production": n, "moves": [], "open": [], "laid_now": [], "note": "no swipe frame map: nothing to lay",
              "counts": {"moves": 0, "laid": 0, "reasoned": 0, "open": 0}}
        (B / "edit").mkdir(exist_ok=True)
        (B / "edit" / "stage.json").write_text(json.dumps(st, indent=1))
        say("read", "done", "no swipe frame map: nothing to lay")
        for sid, _ in STEPS[1:]:
            say(sid, "done", "nothing to lay")
        return st
    moves = read_moves(fm, sound)
    say("read", "done", "%d moves in the swipe" % len(moves))
    say("clock", "doing")
    rows = (_load(B / "shot-list.json", {}) or {}).get("shots") or []
    lay = _load(B / "studio-build" / "layout.json", {}) or {}
    ours = clock(fm, rows, lay)
    for m in moves:
        m["ours"] = ours(m["swipe_at"])
    say("clock", "done", "%d of %d on our clock" % (sum(m["ours"] is not None for m in moves), len(moves)))
    say("lay", "doing")
    bf = B / "music" / "bed.json"
    bed = _load(bf, None)
    made_music = False
    # a sung ad's soundtrack IS its song (owner, 20 Nov): the swipe's music is not re-heard or remade as a bed for it
    sung = (B / "song-cut.json").exists()
    import socket as _so
    _so.setdefaulttimeout(300)            # a network call here never hangs the render (two hung for an hour, 20 Nov)
    if not sung and part_on("listen") and (sound.get("music") or {}).get("present") and (
            "checked" not in (sound.get("music") or {}) or "human_sounds" not in sound):
        try:                                      # the swipe listened to again: its music by ear, its people's sounds
            LI = _listen()
            LI.run(R)
            sound = _load(R / "sound-sheet.json", {}) or sound
        except Exception as e:  # noqa: BLE001
            say("lay", "doing", "the swipe could not be listened to again: %s" % str(e)[:160])
    checked = ((sound.get("music") or {}).get("checked") or {}).get("agreed")
    if not sung and part_on("music_from_swipe") and (sound.get("music") or {}).get("present") and (
            not (bed or {}).get("from_swipe") or (checked and not (bed or {}).get("music_checked"))):
        try:
            length = float((lay or {}).get("length") or 0) + 1.0
            bed = make_music(B, sound, ours, length) or bed
            made_music = bed is not None and bed.get("from_swipe")
        except Exception as e:  # noqa: BLE001 — the stage says why and holds; it never takes the Studio down
            say("lay", "doing", "the swipe's music could not be made: %s" % str(e)[:160])
    laid = []
    if bed is not None and part_on("reactions"):
        reacts = reaction_moves(sound, ours)
        moves += reacts
        made_r = lay_reactions(B, reacts, bed, (_load(B / "brief.json", {}) or {}))
        if made_r:
            bf.write_text(json.dumps(bed, indent=1, ensure_ascii=False))
            laid += made_r
    if bed is not None:
        start = float(bed.get("starts_at") or 0.0)
        if part_on("lay_sfx"):
            recs = (_load(B / "brief.json", {}) or {}).get("edit") or {}
            laid = lay_sfx(moves, bed, _bank(), start,
                           skip={k for k, v in recs.items() if isinstance(v, dict) and (v.get("landed") or v.get("reason"))})
            if laid:
                bf.write_text(json.dumps(bed, indent=1, ensure_ascii=False))
        for m in moves:
            if m["kind"].startswith("music") and not m.get("landed"):
                got = music_laid(m, bed, start, float(conf().get("music_window", 0.75)))
                if got:
                    m["landed"] = got
    else:
        for m in moves:
            if m["kind"] in ("sfx", "music-drop", "music-hit"):
                m["reason"] = m.get("reason") or "this production has no music bed yet (music/bed.json)"
    cam = lay_camera(B, moves, _load(B / "brief.json", {}) or {})
    if cam:
        say("lay", "doing", "%d camera moves laid on our clips" % len(cam))
        laid = list(laid) + cam
    say("lay", "done", "%d effects laid now%s%s" % (len(laid), "; the swipe's music made" if made_music else "",
                                                     "; re-render to hear them" if (laid or made_music) else ""))
    say("check", "doing")
    brief = _load(B / "brief.json", {}) or {}
    open_ = check(moves, brief.get("edit") or {})
    # V57 (owner, 16 Nov): the swipe's moves, music and caption look are suggestions (the "hold" switch, off).
    # HARD rows hold whatever that switch says: a line not heard as written, the bed going silent, our own
    # layers misplaced, the brief's own edit notes not done.
    hard_open = []
    if (sound.get("music") or {}).get("present") and not (B / "song-cut.json").exists():   # a sung ad's sound is its song
        rows = []
        if not (bed or {}).get("from_swipe"):
            rows.append({"id": "music-from-swipe", "kind": "music-source", "swipe_at": 0.0, "ours": 0.0,
                         "what": "the music is the swipe's own sound (its sound sheet), on our cuts"})
        gap = silent_gap(bed)
        if gap:
            rows.append({"id": "music-never-silent", "kind": "music-gap", "swipe_at": gap[0], "ours": gap[0],
                         "what": "the bed goes silent %.2f-%.2f s: a drop-out is low, never silent" % gap})
        for r in rows:
            rec = (brief.get("edit") or {}).get(r["id"]) or {}
            if rec.get("reason"):
                r["reason"] = rec["reason"]
            else:
                open_.append(r["id"])
                if r["id"] == "music-never-silent":
                    hard_open.append(r["id"])
            moves.append(r)
    look = (brief.get("captions") or {}).get("look")
    if fm.get("shots") and not (isinstance(look, dict) and look.get("from_swipe")):
        r = {"id": "captions-from-swipe", "kind": "captions", "swipe_at": 0.0, "ours": 0.0,
             "what": "the captions copy the swipe's caption look (brief.json captions.look, from_swipe: true)"}
        rec = (brief.get("edit") or {}).get(r["id"]) or {}
        if rec.get("reason"):
            r["reason"] = rec["reason"]
        elif isinstance(look, dict) and look.get("id"):    # the brand's own named caption look is the call, not a gap
            r["reason"] = "the brand's own caption look (%s) is used, not the swipe's" % look["id"]
        else:
            open_.append(r["id"])
        moves.append(r)
    records = brief.get("edit") or {}
    import edit_notes as EN
    lines = []
    cut = latest_cut(B)
    if part_on("line_check") and cut:
        say("check", "doing", "reading every spoken shot against its line")
        lines = EN.line_check(B, cut, (_load(B / "shot-list.json", {}) or {}).get("shots") or [], lay)
        _o = EN.resolve(lines, records)
        open_ += _o
        hard_open += _o
        moves += lines
    if part_on("props_template"):
        import layers as LY
        for scene, spec in (brief.get("layers") or {}).items():
            sc = (lay or {}).get("scenes") or []        # a hook version (not in the layout) stands in for the first scene
            x = next((x for x in sc if x["scene"] == scene), sc[0] if sc else {"start": 0, "end": 15.0})
            _, crows = LY.build(B, scene, spec, (_load(B / "shot-list.json", {}) or {}).get("shots") or [],
                                float(x["end"]) - float(x["start"]), rows_scene=x.get("scene"))
            for i, c in enumerate(crows, 1):
                r = {"id": "prop-%s-%d" % (scene, i), "kind": "prop", "swipe_at": 0.0, "ours": None,
                     "what": "%s on %s: %s" % (c["name"], scene, c["short"])}
                if c["ok"]:
                    r["landed"] = "the layers template on %s%s" % (scene, (": " + c["detail"]) if c["detail"] else "")
                else:
                    r["open_why"] = c["detail"]
                moves.append(r)
                if not c["ok"]:
                    open_.append(r["id"])
                    hard_open.append(r["id"])
    if part_on("brief_notes"):
        md_f = R / "stages" / "5-brief.md"
        md = md_f.read_text() if md_f.exists() else ""
        notes = EN.brief_notes(md, brief, B, lines, bed, ALIAS)
        _o = EN.resolve(notes, records)
        open_ += _o
        hard_open += _o
        moves += notes
    if part_on("director"):            # 2026-11-17: one move per scene, chosen by the machine (edit_moves.py)
        say("check", "doing", "the moves director: one move per scene")
        for _try in (1, 2):  # owner ruling 2026-11-20: retry then fail loudly: a crashed director is asked again, then holds the stage
            try:
                import edit_moves as EMV
                moves += EMV.stage(n, B, R, say)
                break
            except Exception as e:  # noqa: BLE001 — an open row, never a "reasoned" one
                if _try == 2:
                    moves.append({"id": "director", "kind": "director", "swipe_at": 0.0, "ours": None,
                                  "what": "the moves director", "open_why": "could not run twice: %s" % str(e)[:160]})
                    open_.append("director")
                    hard_open.append("director")
    st = {"production": n, "moves": moves, "open": open_, "hard_open": hard_open, "laid_now": laid,
          "counts": {"moves": len(moves), "laid": sum(bool(m.get("landed")) for m in moves),
                     "reasoned": sum(bool(m.get("reason")) and not m.get("landed") for m in moves), "open": len(open_)}}
    (B / "edit").mkdir(exist_ok=True)
    (B / "edit" / "stage.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    held = bool(hard_open) or (bool(open_) and part_on("hold"))
    why = [m["open_why"] for m in moves if m["id"] in open_ and m.get("open_why")]
    say("check", "stopped" if held else "done",
        ("%d moves neither laid nor reasoned: %s%s" % (len(open_), ", ".join(open_[:6]),
                                                      (" · " + why[0]) if why else "")) if open_ else
        "%d laid, %d with a reason" % (st["counts"]["laid"], st["counts"]["reasoned"]))
    return st


def latest_cut(B):
    """The newest rendered cut (rough-cut-v<N>-sdr.mp4, by its number), or None."""
    cuts = [(int(m.group(1)), f) for f in Path(B).glob("rough-cut-v*-sdr.mp4")
            for m in [re.match(r"rough-cut-v(\d+)-sdr\.mp4$", f.name)] if m]
    return max(cuts)[1] if cuts else None


def has_frame_map(B) -> bool:
    """Does this production's swipe have a frame map to read moves from? No writing run, or none on this machine: no."""
    try:
        return bool((_load(_writing_run(Path(B)) / "framemap" / "framemap.json", {}) or {}).get("shots"))
    except (Exception, SystemExit):  # noqa: BLE001
        return False


def closed(n, B):
    """Why the edit pass is never offered for this production, or None: the cover stage's own reason (its card is
    approved, live or already carries filed covers, found by the full brief key and the filed-brief lookup)."""
    try:
        import covers_stage as CS
        return CS.closed(n, B)
    except (Exception, SystemExit):  # noqa: BLE001
        return None


def due(n, B=None) -> bool:
    """Is the edit pass due? On, every version rendered, the swipe has a frame map, the production's card is not
    approved, live or covered (closed), and edit/stage.json is missing, older than the last render or the brief, or
    holds a move with neither a layer nor a reason."""
    if not on():
        return False
    B = folder(n, B)
    cuts = sorted(B.glob("rough-cut-v*-sdr.mp4"), key=lambda f: f.stat().st_mtime)
    if not cuts:
        return False
    if not has_frame_map(B) or closed(n, B):
        return False
    f = B / "edit" / "stage.json"
    if not f.exists() or f.stat().st_mtime < cuts[-1].stat().st_mtime:
        return True
    b = B / "brief.json"
    if b.exists() and b.stat().st_mtime > f.stat().st_mtime:
        return True
    st = _load(f, {}) or {}
    return bool(st.get("hard_open")) or (bool(st.get("open")) and part_on("hold"))


def board_rows(B):
    """The Checks panel's "Edit moves" rows (checks_board.py)."""
    st = _load(Path(B) / "edit" / "stage.json", {}) or {}
    rows = []
    for m in st.get("moves") or []:
        rows.append({"group": "Edit moves", "name": ("%s · swipe %.2f s" % (m["kind"], m["swipe_at"])) if m.get("swipe_at")
                     or m["kind"] in ("sfx", "music-drop", "music-hit", "punch-in", "flash", "graphic-pop", "push-in")
                     else "%s · %s" % (m["kind"], m["id"]),
                     "ok": True if m.get("landed") else (None if m.get("reason") else False),
                     "short": ("ours %.2f s" % m["ours"]) if m.get("ours") is not None else "no shot of ours copies it",
                     "detail": "Swipe: %s\n%s" % (m.get("what", ""), ("Laid: " + m["landed"]) if m.get("landed") else
                                                  ("Not laid: " + m["reason"]) if m.get("reason") else
                                                  "%sNeither laid nor reasoned: lay it, or say why in brief.json edit.%s"
                                                  % ((m["open_why"] + ". ") if m.get("open_why") else "", m["id"]))})
    return rows


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("run", "state"):
        sys.exit(__doc__)
    if a[0] == "run":
        st = run(a[1], say=lambda sid, state, said="": print("%-6s %-8s %s" % (sid, state, said)))
    else:
        st = _load(folder(a[1]) / "edit" / "stage.json", {})
    for m in (st or {}).get("moves") or []:
        print("%-14s swipe %6.2f  ours %6s  %s" % (m["kind"], m["swipe_at"], "-" if m.get("ours") is None else "%.2f" % m["ours"],
                                                   ("✓ " + m["landed"]) if m.get("landed") else ("– " + m["reason"]) if m.get("reason") else "✗ open"))
