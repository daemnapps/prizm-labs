#!/usr/bin/env python3
"""
voice.py — the piece's voice, generated once, on the direct ElevenLabs
account, before anything else in a run generates a single frame.

ONE CONTINUOUS VOICE (2026-09-18, the owner: "there is no clean voice-over —
shooting line by line comes out choppy"). The default is no longer one call
per line. The script is built from the brief's voice paragraphs in order,
one chunk per SCENE, and each chunk is sent to
`text-to-speech/{voice}/with-timestamps` carrying `previous_request_ids` —
the ids read off the previous responses' `request-id` header — so every
chunk is conditioned on the audio actually spoken before it and the read
never restarts. The chunks concatenate into ONE track, `vo/track.mp3`, and
`vo/timing.json` says where every scene and every sentence sits on it. The
talking door gets the scene's own slice, `vo/<scene>.mp3`, cut from that one
track with ffmpeg — so what a clip lip-syncs to is a piece of the continuous
read, not a separate take.

Request stitching runs on `eleven_multilingual_v2`; it is not on v3. That,
the endpoint and every field name come from `model-inputs.json` — the model
input contract — never from a literal here.

The old per-line path is kept as `--per-line`, for the old brief shape and
for a run that only wants one line re-made.

the owner's 2026-09-17 ruling: voice is the direct ElevenLabs account, one
custom voice per character. Custom voices (cloned/designed) live on his
ElevenLabs account; fal's ElevenLabs endpoints only see library voices and
cannot use an account-private voice id — no key passthrough, no
clone/design endpoint on fal. So the line is generated FIRST, from here,
via the direct ElevenLabs API, and the audio is piped into whichever
provider needs it: uploaded to Higgsfield as the media a talking beat
lip-syncs to (role `audio`), or attached on fal as the item's own `audio`
media. Same recipe on both providers.

    python3 machine/voice.py <run-dir> [--character <name>] [--dry-run]
                                        [--cast-root <dir>]
                                        [--continuous | --per-line]

Reads `<run>/lines.json` (line id -> text) and `<run>/run.json` (brand).
Finds the character's `voice.json` under `brands/<brand>/ai-elements/characters/<name>/`
(the old `ai-cast/<name>/` still works)
(or `--cast-root/<name>/`, so a test never has to read `brands/`). The
character defaults to the plan's own `cast.name` (`<run>/plan.json`),
slugified into the same lowercase folder name every ai-cast entry already
uses.

`voice.json` must carry a `voice_id` — an ElevenLabs voice id on the
account. A file that only carries a fal library preset name (`voice`) is
refused: the voice has to be bound to the direct account, never a preset.

Writes `<run>/voice/<line id>.mp3` and `<run>/voice/manifest.json`
(`{line id: {file, voice_id, model_id, chars, at}}`). `--dry-run` prints
every request this would make and writes nothing — but a missing or
preset-only voice is still a hard stop even on a dry run, because nothing
downstream should ever plan around a voice that cannot actually speak.

A run with no scene carrying a line has nothing to voice — this module
does nothing, cleanly, without asking a run for a character it does not
need.

No brand, model or person name lives in this file. A character's identity
comes from the run's own plan and brand; `--cast-root` exists only so a
test can point this at a fixture instead of the real `brands/` tree.

Exit 0 done (or nothing to voice) · 2 no bindable voice · 3 bad input.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import shutil
import tempfile
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def _workspace(start=__file__):
    """The workspace root, FOUND by walking up — never counted with parents[N].

    The count here was right only while this file sat in the team notes The move
    to components/ on 2026-09-22 made it resolve to ~/Projects, one level too
    high — outside the repo entirely. A marker cannot go quietly wrong the next
    time something moves. AI_WORKSPACE still wins when it names a workspace.
    """
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError(f"no workspace found upward of {here}")



HERE = Path(__file__).resolve().parent
# machine/voice.py -> ai-video-production -> damon -> lab -> the workspace
# root — the same count run.py and prompt.py use for the same reason.
WORKSPACE = _workspace()

ELEVEN_TTS = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
VOICE_SETTINGS_KEYS = ("stability", "similarity_boost", "style", "use_speaker_boost", "speed")
FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vp_keys = _load("vp_keys")


def contract() -> dict:
    """The voice station's own row in the model input contract — the
    endpoint, the model id that stitching needs, and the cap on how many
    request ids may be carried. Nothing about this door is written here."""
    return _load("model_inputs").station("voice")


def default_model_id() -> str:
    for f in contract().get("fields", []):
        if f.get("name") == "model_id":
            return f.get("house_default") or ""
    return ""


def timestamps_url(voice_id: str) -> str:
    url = (contract().get("endpoints") or {}).get("with_timestamps") or ""
    return url.replace("{voice_id}", voice_id)


def stitch_depth() -> int:
    return int((contract().get("limits") or {}).get("previous_request_ids") or 3)


def pins() -> dict:
    """The fields every voice call sends pinned (model-inputs.json voice.pins,
    2026-09-23): `apply_text_normalization: off` — our own number rules have
    already said every figure, so ElevenLabs does not guess — and `seed`, so a
    line asked for twice is asked for the same way."""
    p = contract().get("pins") or {}
    return {k: v for k, v in p.items() if not k.startswith("_")}


def lexicon_mod():
    return _load("lexicon")


def prepared(text: str, rows: list | None) -> tuple[str, dict]:
    """The paragraph exactly as the model is sent it: the brand's protected
    words swapped for how they are said, then every figure in words
    (lexicon.for_model), THEN the punctuation map (for_reading) — in that
    order, because the map turns a dash into a comma and would make "28–40"
    "28, 40" and "(209) 444-2316" a list. The script is never changed —
    this is only what is sent, and it is recorded."""
    sent, said = lexicon_mod().for_model(text or "", rows or [])
    return for_reading(sent), said


def body_for(text: str, model_id: str, rows: list | None, seed_offset: int = 0) -> tuple[dict, dict]:
    sent, said = prepared(text, rows)
    body = {"text": sent, "model_id": model_id}
    p = pins()
    if "apply_text_normalization" in p:
        body["apply_text_normalization"] = p["apply_text_normalization"]
    if p.get("seed") is not None:
        body["seed"] = int(p["seed"]) + int(seed_offset)
    return body, said


def for_model(model_id: str, settings: dict) -> dict:
    """v3 (the house voice model since 2026-10-01) takes stability only as 0.0,
    0.5 or 1.0 — a ruled 0.45 is sent as the nearest of those."""
    st = dict(settings or {})
    if "v3" in (model_id or "") and isinstance(st.get("stability"), (int, float)):
        st["stability"] = min((0.0, 0.5, 1.0), key=lambda x: abs(x - st["stability"]))
    return st


def stitches(model_id: str) -> bool:
    """Request stitching (previous_request_ids) is a v2 feature; v3 reads each
    line on its own and holds the voice without it."""
    return "v3" not in (model_id or "")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text())


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1) + "\n")


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def cast_name_of(run: Path) -> str:
    plan = read_json(run / "plan.json", {}) or {}
    return (plan.get("cast") or {}).get("name") or ""


def cast_root_of(brand: str | None) -> Path:
    """The brand's characters folder: ai-elements/characters/ (the v6 name),
    else the old ai-cast/ while a brand has not moved yet."""
    b = WORKSPACE / "brands" / (brand or "")
    for rel in ("ai-elements/characters", "ai-cast"):
        if (b / rel).is_dir():
            return b / rel
    return b / "ai-elements" / "characters"


def character_home(brand: str | None, character: str, cast_root: Path | None) -> Path:
    """A person's folder: runs/ai-elements/<brand>/casting/<name>/ (element_paths.py),
    falling back to the pre-2026-09-23 brands/<brand>/ai-cast/<name>/."""
    if cast_root:
        return cast_root / character
    return _load("element_paths").casting_home(brand or "", character, WORKSPACE)


def _doc_of(run: Path) -> dict:
    """The brief's own json block, when the run was started from a brief."""
    b = run / "brief.md"
    if not b.is_file():
        return {}
    try:
        doc, _ = _load("scenes").json_block(b.read_text())
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def speakers(run: Path) -> dict:
    """EVERY SPEAKER HAS THEIR OWN VOICE (the owner, 2026-09-23: "we need to
    create a voice just for our person … not June's"). Scene id -> the bank
    folder name of the person whose voice reads it: the scene's `speaker`
    when the brief names one (brief v17), else the first cast id its `who`
    names, else the plan's lead. A cast id maps to its folder through the
    brief's `bank_id`, else its slug."""
    plan = read_json(run / "plan.json", {}) or {}
    doc = _doc_of(run)
    lead = cast_name_of(run)
    cast = doc.get("cast") or []
    ids = [c.get("id") or c.get("name") for c in cast if (c.get("id") or c.get("name"))] \
        or list((plan.get("cast") or {}).get("names") or [])
    # a cast id's folder: its bank_id, else the slug of its NAME (what the
    # single-voice read always used), else the slug of the id
    folder = {(c.get("id") or c.get("name")): (c.get("bank_id") or slugify(c.get("name") or "")) for c in cast}
    scenes = {s.get("id"): s for s in (doc.get("scenes") or [])}
    for s in plan.get("scenes") or []:
        scenes.setdefault(s.get("id"), s)
    out = {}
    for sid, s in scenes.items():
        who = s.get("speaker") or ""
        if not who:
            w = (s.get("who") or "").upper()
            hits = [(w.find(c.upper()), c) for c in ids if c and c.upper() in w]
            who = min(hits)[1] if hits else lead
        b = folder.get(who) or ""
        out[sid] = b if b and b.upper() != "NEW" else slugify(who)
    return out


def key_of() -> str | None:
    """ELEVENLABS_API_KEY: env first, then the Keychain vault — never a
    crash, only ever a None when neither has it. A teammate's clone with
    no vault module and no key is simply "not found", the same as every
    other key lookup in this machine."""
    return vp_keys.key("ELEVENLABS_API_KEY")


def http_transport(method: str, url: str, body: dict | None, headers: dict) -> bytes:
    """The real network call — the default `transport`. Returns the raw
    audio bytes fal/Higgsfield's own submit paths never touch; this is the
    only station whose provider is always ElevenLabs, direct."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _retry(fn, tries: int = 4, wait: float = 6.0):
    """A dropped connection is the network, not the read — try again (found
    2026-09-23: a remake died on one timeout)."""
    import time as _t, urllib.error as _ue, socket as _so
    for n in range(tries):
        try:
            return fn()
        except (_ue.URLError, TimeoutError, _so.timeout, ConnectionError) as e:
            if isinstance(e, _ue.HTTPError) and e.code < 500 and e.code != 429:
                raise
            if n == tries - 1:
                raise
            _t.sleep(wait * (n + 1))


def http_json_transport(method: str, url: str, body: dict | None, headers: dict):
    """The real network call for the timestamps endpoint. Returns
    `(body_bytes, response_headers)` — the headers matter, because
    `request-id` is what the NEXT chunk is stitched onto."""
    data = json.dumps(body).encode() if body is not None else None
    def once():
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.read(), {k.lower(): v for k, v in dict(r.headers).items()}
    return _retry(once)


def voice_settings_of(rec: dict) -> dict:
    return {k: rec[k] for k in VOICE_SETTINGS_KEYS if k in rec}


def binding(home: Path) -> tuple[str, str, dict]:
    """The character's own voice record: (voice_id, model_id, settings). A
    missing record, or one that only names a library preset, is a hard stop
    — nothing downstream should plan around a voice that cannot speak."""
    record = home / "voice.json"
    if not record.is_file():
        raise SystemExit(
            f"no voice.json for this character at {record} — bind a custom "
            f"ElevenLabs voice id there (voice_id) before this run can speak, "
            f"the owner's ruling 2026-09-17")
    rec = json.loads(record.read_text())
    voice_id = rec.get("voice_id")
    if not voice_id:
        raise SystemExit(
            "this character's voice is a fal library preset; bind a custom "
            "ElevenLabs voice id in voice.json (voice_id) — the owner's ruling "
            "2026-09-17")
    # The character's ruled settings live under "settings" in voice.json (make_voice
    # writes them there). They were never read — every line without brief settings
    # went out on the account's defaults, and a long read drifted: Nova came back
    # British on one line and Australian on another (2026-10-01). Nested first,
    # top-level keys (older records) over them.
    return voice_id, rec.get("model_id") or default_model_id(), \
        {**voice_settings_of(rec.get("settings") or {}), **voice_settings_of(rec)}


def make_lines(run: Path, home: Path, dry_run: bool, transport, key: str | None) -> dict:
    """The LEGACY path — one call per line in `<run>/lines.json`, kept for the
    old brief shape and for re-making a single line. Returns the manifest
    written (or that would be written, on --dry-run)."""
    lines = read_json(run / "lines.json", {}) or {}
    lines = {lid: text for lid, text in lines.items() if text}
    if not lines:
        return {}

    voice_id, model_id, settings = binding(home)
    rows = lexicon_mod().for_run(run)
    voice_dir = run / "voice"
    manifest: dict = {}

    for lid, text in lines.items():
        url = ELEVEN_TTS.format(voice_id=voice_id)
        body, said = body_for(text, model_id, rows)
        if settings:
            body["voice_settings"] = settings
        headers = {"xi-api-key": key or "", "Content-Type": "application/json",
                   "Accept": "audio/mpeg"}
        dest = voice_dir / f"{lid}.mp3"
        row = {"file": str(dest.relative_to(run)), "voice_id": voice_id,
               "model_id": model_id, "chars": len(text), "at": now(),
               "sent_text": body["text"], **said}
        if dry_run:
            print(json.dumps({"line": lid, "url": url, "body": body}, indent=1))
            manifest[lid] = row
            continue
        audio = transport("POST", url, body, headers)
        voice_dir.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(audio)
        manifest[lid] = row

    if not dry_run:
        write_json(voice_dir / "manifest.json", manifest)
    return manifest


# ------------------------------------------------ one continuous voice

SENTENCE = re.compile(r"[^.!?]+[.!?]*")


def run_ffmpeg(args: list[str]) -> bool:
    """One ffmpeg call. Returns False when ffmpeg is not on this machine or
    the call failed — the caller then falls back rather than dying, because
    a missing binary must never lose a track that was already generated."""
    if not Path(FFMPEG).exists():
        return False
    try:
        p = subprocess.run([FFMPEG, *args], capture_output=True)
        return p.returncode == 0
    except Exception:
        return False


SPOKEN_JSON = WORKSPACE / "components" / "marketing-doctrine" / "spoken.json"

# The safety net for a brief written before the spoken pass existed, and for
# a machine with no doctrine folder beside it: a dash becomes a comma and an
# the ellipsis is KEPT — it is the breath (2026-09-19). The same two rows the doctrine's map carries, so the
# take reads the same either way.
FALLBACK_TAKE = [
    {"pattern": r"\s*[\u2014\u2013]\s*", "with": ", "},
    # the ellipsis is the breath (the owner, 2026-09-19) — the one-character
    # form is normalised to three dots and otherwise KEPT
    {"pattern": r"\u2026", "with": "..."},
]


def punctuation_map() -> dict:
    """The doctrine's punctuation map for the voice model
    (components/marketing-doctrine/spoken.json -> punctuation_map): what each
    mark does on the model the track is made on, and what the take does with
    it. {} when the doctrine is not beside this machine — the fallback rows
    then carry the take."""
    try:
        return (json.loads(SPOKEN_JSON.read_text()) or {}).get("punctuation_map") or {}
    except Exception:
        return {}


def take_rules(pm: dict | None = None) -> list[dict]:
    """The rewrite rows for the take, read off the map: every mark whose
    `take.action` is `replace` becomes a {pattern, with} row, in map order.
    A mark the map says to `keep` is left alone. Falls back to FALLBACK_TAKE
    when the map carries nothing."""
    pm = punctuation_map() if pm is None else pm
    rows = []
    for m in pm.get("marks") or []:
        take = m.get("take") or {}
        if take.get("action") != "replace":
            continue
        pat = take.get("pattern") or (r"\s*" + re.escape(m.get("mark") or "") + r"\s*")
        rows.append({"pattern": pat, "with": take.get("with", ", ")})
    return rows or list(FALLBACK_TAKE)


def for_reading(text: str, rules: list[dict] | None = None) -> str:
    """The paragraph as the voice model should READ it. The brief keeps its
    punctuation for the record, but an em-dash is read as a
    long pause (measured 2026-09-19: 1.3\u20131.7 s of silence at every dash,
    a 7 s paragraph taking 11 s). Since the spoken pass (2026-09-19) the
    brief's paragraph is written for the mouth and the gate refuses those
    marks, so this is the safety net for older briefs: each mark is handled
    the way the doctrine's punctuation map says (`take` per mark), and the
    words never change, so the line check and the timing sheet still match
    the brief."""
    t = text or ""
    for row in (take_rules() if rules is None else rules):
        t = re.sub(row["pattern"], row["with"], t)
    # two marks that met at a seam collapse to one: a full stop outranks a
    # comma, and nothing doubles
    t = re.sub(r"\s+([,.])", r"\1", t)
    # the ellipsis is the breath and survives the seam clean-up: protect it,
    # collapse the rest, put it back
    t = t.replace("\u2026", "...").replace("...", "\x00")
    t = re.sub(r",\s*\.", ".", t)
    t = re.sub(r"\.\s*,", ".", t)
    t = re.sub(r",\s*,", ",", t)
    t = re.sub(r"\.\s*\.", ".", t)
    t = re.sub(r"^[,.\s]+", "", t)
    t = t.replace("\x00", "...")
    return re.sub(r"\s{2,}", " ", t).strip()


def scene_settings(run: Path) -> dict:
    """{scene id: voice_settings} for every scene in the run's plan that
    carries them (the brief block's per-scene `voice_settings`, written by
    the spoken pass from the register recipe). Empty for an older plan."""
    plan = read_json(run / "plan.json", {}) or {}
    out = {}
    for s in plan.get("scenes") or []:
        vs = s.get("voice_settings") if isinstance(s, dict) else None
        if isinstance(vs, dict) and vs:
            out[str(s.get("id"))] = vs
    return out


def chunk_duration(alignment: dict) -> float:
    ends = (alignment or {}).get("character_end_times_seconds") or [0.0]
    return float(ends[-1]) if ends else 0.0


SAID_SENTENCE = re.compile(r".+?(?:[.!?]+(?=\s|$)|$)", re.S)


def line_windows(text: str, alignment: dict, offset: float, said: str | None = None) -> list[dict]:
    """Every sentence of a paragraph with its start and end on the ONE
    timeline, read off the chunk's own character alignment: find the
    sentence's offset in the chunk text, then take the first character's
    start time and the last character's end time, plus everything that has
    already played.

    `said` is the text the model was actually SENT (figures and protected
    words said out). The alignment is against that text, so the windows are
    found in it, and each carries the script's own sentence as `text` (for
    the captions) and the sent one as `said`."""
    starts = (alignment or {}).get("character_start_times_seconds") or []
    ends = (alignment or {}).get("character_end_times_seconds") or []
    out = []
    if said is not None and said != text:
        orig = [m.group(0).strip() for m in SAID_SENTENCE.finditer(text) if m.group(0).strip()]
        found = [m for m in SAID_SENTENCE.finditer(said) if m.group(0).strip()]
        for i, m in enumerate(found):
            s = m.group(0).strip()
            a = m.start() + (len(m.group(0)) - len(m.group(0).lstrip()))
            z = a + len(s) - 1
            if a >= len(starts) or z >= len(ends):
                continue
            out.append({"text": orig[i] if len(orig) == len(found) else s, "said": s,
                        "start": round(offset + float(starts[a]), 3),
                        "end": round(offset + float(ends[z]), 3)})
        return out
    for m in SENTENCE.finditer(text):
        s = m.group(0).strip()
        if not s:
            continue
        a, z = m.start(), m.end() - 1
        if a >= len(starts) or z >= len(ends):
            continue
        out.append({"text": s, "start": round(offset + float(starts[a]), 3),
                    "end": round(offset + float(ends[z]), 3)})
    return out


def breath_of(run: Path) -> float | None:
    """The pause length the take is cut to: the matched creators' mean pause
    from the brand's voiceprint roll-up (brief block -> piece.voiceprint or
    the run's own voiceprint.json), else the spoken slice's default breath,
    else None (no tightening)."""
    for cand in (run / "voiceprint.json",):
        if cand.is_file():
            try:
                v = json.loads(cand.read_text())
                mean = (v.get("pauses") or {}).get("mean_s")
                if mean:
                    return round(min(max(float(mean), 0.3), 0.9), 2)
            except Exception:
                pass
    try:
        sp = json.loads((WORKSPACE / "components" / "marketing-doctrine" / "spoken.json").read_text())
        b = (sp.get("breath") or {}).get("default_s")
        if b:
            return float(b)
    except Exception:
        pass
    return 0.45


def audio_seconds(path: Path) -> float | None:
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def tighten_pauses(path: Path, breath: float, floor: float = 0.3) -> bool:
    """Cut every silence longer than `breath` in one audio file down to
    `breath`, in place. Leading silence is dropped. Returns True when the
    file changed. Pure ffmpeg: silencedetect to find the gaps, then the
    kept spans concatenated."""
    # SILENCE IS RELATIVE TO THE VOICE (2026-10-07): a fixed -30 dB floor read a
    # quiet voice's words as silence and cut them out (the the athlete moderator, ~25 dB
    # under the rest, came back as 3 s of a 7 s line and 0.1 s of "Vic Lawson").
    # The floor sits 14 dB under the take's own mean level, never above -30 dB.
    vol = subprocess.run([FFMPEG, "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    mv = re.search(r"mean_volume: (-?[\d.]+) dB", vol)
    noise = min(-30.0, float(mv.group(1)) - 14.0) if mv else -30.0
    det = subprocess.run([FFMPEG, "-i", str(path), "-af",
                          f"silencedetect=noise={noise:.1f}dB:d={floor}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", det)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", det)]
    total = audio_seconds(path)
    if not starts or total is None:
        return False
    keep, t, changed = [], 0.0, False
    for s0, e0 in zip(starts, ends):
        if s0 <= 0.05:
            t = max(e0 - 0.1, 0.0); changed = True
            continue
        if e0 - s0 <= breath:
            continue
        keep.append((t, s0 + breath / 2)); t = e0 - breath / 2; changed = True
    keep.append((t, total))
    if not changed:
        return False
    tmpdir = Path(tempfile.mkdtemp(prefix="breath-"))
    parts = []
    for i, (a, b) in enumerate(keep):
        if b - a <= 0.02:
            continue
        seg = tmpdir / f"seg{i}.mp3"
        subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                        "-i", str(path), "-c:a", "libmp3lame", "-b:a", "128k", str(seg)], check=True)
        parts.append(seg)
    lst = tmpdir / "segs.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    out = tmpdir / "tight.mp3"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:a", "libmp3lame", "-b:a", "128k", str(out)], check=True)
    shutil.copy(out, path)
    shutil.rmtree(tmpdir, ignore_errors=True)
    return True


def make_track(run: Path, home: Path, dry_run: bool, transport, key: str | None,
               homes: dict | None = None) -> dict:
    """THE ONE READ. One chunk per scene paragraph, stitched chunk to chunk
    on `previous_request_ids`, concatenated into `vo/track.mp3`, timed in
    `vo/timing.json`, and sliced per scene into `vo/<scene>.mp3` for the
    talking door. Returns the manifest: scene id -> its slice."""
    script = read_json(run / "lines.json", {}) or {}
    script = {sid: text for sid, text in script.items() if text}
    if not script:
        return {}

    homes = homes or {}
    # one binding per speaker; a scene whose speaker has no voice stops the
    # run here, named — never read in somebody else's voice
    bound = {}
    for sid in script:
        h = homes.get(sid) or home
        if h not in bound:
            bound[h] = binding(h)
    voice_id, model_id, settings = bound[home] if home in bound else next(iter(bound.values()))
    rows = lexicon_mod().for_run(run)
    per_scene = scene_settings(run)
    vo = run / "vo"
    cap = stitch_depth()
    ids_by_voice: dict = {}
    manifest: dict = {}
    timing = {"track": "vo/track.mp3", "voice_id": voice_id, "model_id": model_id,
              "voices": {}, "pins": pins(), "scenes": {}, "at": now()}
    played = 0.0
    chunks: list[tuple[str, bytes]] = []

    for sid, text in script.items():
        voice_id, model_id, settings = bound[homes.get(sid) or home]
        ids = ids_by_voice.setdefault(voice_id, [])   # stitched within one voice only
        timing["voices"][sid] = {"voice_id": voice_id, "speaker": (homes.get(sid) or home).name}
        url = timestamps_url(voice_id)
        body, said = body_for(text, model_id, rows)
        # the cast voice's own record, then this scene's settings over it —
        # the spice pass writes them per scene from the register recipe
        chunk_settings = for_model(model_id, {**settings, **voice_settings_of(per_scene.get(sid) or {})})
        if chunk_settings:
            body["voice_settings"] = chunk_settings
        if ids and stitches(model_id):
            body["previous_request_ids"] = ids[-cap:]
        headers = {"xi-api-key": key or "", "Content-Type": "application/json",
                   "Accept": "application/json"}
        if dry_run:
            print(json.dumps({"scene": sid, "speaker": (homes.get(sid) or home).name,
                              "url": url, "body": body}, indent=1))
            continue

        got = transport("POST", url, body, headers)
        payload, res_headers = got if isinstance(got, tuple) else (got, {})
        data = json.loads(payload.decode() if isinstance(payload, bytes) else payload)
        audio = base64.b64decode(data.get("audio_base64") or "")
        alignment = data.get("alignment") or data.get("normalized_alignment") or {}
        rid = {str(k).lower(): v for k, v in (res_headers or {}).items()}.get("request-id")
        if rid:
            ids.append(rid)

        seconds = chunk_duration(alignment)
        timing["scenes"][sid] = {
            "start": round(played, 3), "end": round(played + seconds, 3),
            "seconds": round(seconds, 3), "file": f"vo/{sid}.mp3",
            "request_id": rid, "chars": len(text),
            "voice_settings": chunk_settings or None,
            # what the model was SENT (protected words and figures said out),
            # and what was swapped — the captions keep the script's spelling
            "sent_text": body["text"], "said_as": said["said_as"], "numbers": said["numbers"],
            "seed": body.get("seed"),
            "lines": line_windows(text, alignment, played, said=body["text"]),
        }
        chunks.append((sid, audio))
        played += seconds

    if dry_run:
        return {sid: {"file": f"vo/{sid}.mp3", "voice_id": timing["voices"][sid]["voice_id"],
                      "speaker": timing["voices"][sid]["speaker"],
                      "model_id": model_id, "chars": len(t), "at": now()}
                for sid, t in script.items()}

    vo.mkdir(parents=True, exist_ok=True)
    parts_dir = vo / "chunks"
    parts_dir.mkdir(exist_ok=True)
    paths = []
    breath = breath_of(run)
    for i, (sid, audio) in enumerate(chunks, 1):
        p = parts_dir / f"{i:02d}-{sid}.mp3"
        p.write_bytes(audio)
        # THE BREATH (2026-09-19): the voice model leaves ~1 s of silence at
        # a full stop; the brand's own creators measured 0.4–0.8 s. Every
        # pause in the take is cut down to the matched creators' breath, and
        # the timing sheet is re-read off the trimmed audio so every slice
        # and beat still lands on the words.
        if breath and not dry_run:
            trimmed = tighten_pauses(p, breath)
            if trimmed:
                secs = audio_seconds(p)
                sc = timing["scenes"].get(sid)
                if sc and secs:
                    delta = sc["seconds"] - secs
                    sc["seconds"], sc["end"] = round(secs, 3), round(sc["start"] + secs, 3)
                    sc["breath_s"] = breath
                    sc["tightened_by_s"] = round(delta, 3)
                    # later scenes start earlier by what this one lost
                    for other in timing["scenes"].values():
                        if other["start"] > sc["start"]:
                            other["start"] = round(other["start"] - delta, 3)
                            other["end"] = round(other["end"] - delta, 3)
                    for ln in sc.get("lines") or []:
                        ln["end"] = min(ln["end"], sc["end"])
        paths.append(p)

    # THE TIMELINE IS THE AUDIO (2026-10-01). Each scene's start used to be the
    # sum of the words' alignment ends, but a chunk's file runs longer than its
    # last word (trailing silence + the mp3's own padding), so every slice cut
    # from the joined track drifted later — by the close, "Tap the button below"
    # was cut as the end of the line before it. Starts are now the running sum
    # of each chunk's REAL length, every line window moves with its scene, and
    # the slice is the scene's own chunk.
    t = 0.0
    for sid, p in zip([c[0] for c in chunks], paths):
        sc = timing["scenes"].get(sid)
        secs = audio_seconds(p)
        if sc and not secs:          # length unreadable (no ffprobe, a stub): keep the words' timing
            t = sc["end"]
            continue
        if sc and secs:
            shift = round(t - sc["start"], 3)
            sc["start"], sc["seconds"], sc["end"] = round(t, 3), round(secs, 3), round(t + secs, 3)
            for ln in sc.get("lines") or []:
                for k in ("start", "end"):
                    if isinstance(ln.get(k), (int, float)):
                        ln[k] = round(min(ln[k] + shift, sc["end"]), 3)
        t += secs or 0.0
    played = t or played

    track = vo / "track.mp3"
    listing = parts_dir / "concat.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in paths))
    if not run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                       "-c", "copy", str(track)]):
        # no ffmpeg (or it refused): the chunks still make one file in order
        track.write_bytes(b"".join(p.read_bytes() for p in paths))

    for sid, row in timing["scenes"].items():
        dest = vo / f"{sid}.mp3"
        src = next((p for p in paths if p.name.endswith(f"-{sid}.mp3")), None)
        cut = False
        if src:
            dest.write_bytes(src.read_bytes()); cut = True   # the scene's own audio, exactly
        else:
            cut = run_ffmpeg(["-y", "-i", str(track), "-ss", f"{row['start']:.3f}",
                              "-to", f"{row['end']:.3f}", "-c", "copy", str(dest)])
        if not cut:
            # the slice is the chunk that made it — same audio, same words
            src = next((p for p in paths if p.name.endswith(f"-{sid}.mp3")), None)
            if src:
                dest.write_bytes(src.read_bytes())
        level_slice(dest)
        manifest[sid] = {"file": f"vo/{sid}.mp3",
                         "voice_id": timing["voices"][sid]["voice_id"],
                         "speaker": timing["voices"][sid]["speaker"],
                         "model_id": model_id, "chars": row["chars"],
                         "start": row["start"], "end": row["end"], "at": now()}

    timing["total"] = round(played, 3)
    write_json(vo / "timing.json", timing)
    write_json(vo / "manifest.json", manifest)
    return manifest


LEVEL_LUFS = -16.0   # every slice at the same loudness (the owner, 2026-09-23: "take care of volume")
LEVEL_TP = -1.5


def level_slice(path: Path, target: float = LEVEL_LUFS) -> bool:
    """One scene's slice brought to the same loudness as every other — volume
    only. Two passes: measure, then one LINEAR gain (no compression, so the
    delivery is untouched). The first pilot run drifted 17 LU between scenes."""
    import re as _re
    probe = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", str(path), "-af",
                            f"loudnorm=I={target}:TP={LEVEL_TP}:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True)
    m = _re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", probe.stderr)
    if not m:
        return False
    meas = json.loads(m.group(0))
    tmp = path.with_suffix(".level.mp3")
    af = (f"loudnorm=I={target}:TP={LEVEL_TP}:LRA=11:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:"
          f"measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true")
    ok = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-af", af, "-ar", "44100", "-b:a", "192k", str(tmp)]).returncode == 0
    if ok and tmp.exists():
        tmp.replace(path)
    # A QUIET VOICE STILL LANDS ON TARGET (2026-10-07): a linear gain stops short
    # when the take's peaks would clip, so a soft voice came out 13 LU under the
    # rest (the the athlete moderator; the owner heard it). What is left is closed with
    # the same gain plus a peak limiter — only the peaks are touched.
    if ok:
        again = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", str(path), "-af",
                                f"loudnorm=I={target}:TP={LEVEL_TP}:LRA=11:print_format=json", "-f", "null", "-"],
                               capture_output=True, text=True)
        m2 = _re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", again.stderr)
        if m2:
            have = float(json.loads(m2.group(0))["input_i"])
            if have > -70 and abs(have - target) > 1.5:
                lim = 10 ** (LEVEL_TP / 20)
                af2 = f"volume={target - have:.2f}dB,alimiter=limit={lim:.3f}:level=disabled"
                if subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-af", af2,
                                   "-ar", "44100", "-b:a", "192k", str(tmp)]).returncode == 0 and tmp.exists():
                    tmp.replace(path)
    return ok


def remake_scene(run: Path, sid: str, character: str | None = None, dry_run: bool = False,
                 cast_root: str | None = None, transport=None, key: str | None = None) -> dict:
    """ONE scene's slice of the read, made again — nothing else touched
    (the owner, 2026-09-23: regenerate only the element that is wrong). Same
    text, same voice, same model, same per-scene settings, and stitched on
    the SAME previous_request_ids the first read used (timing.json keeps
    each scene's request id), so it still sounds like the same continuous
    read. The old slice is archived to vo/versions/, the pause tightening
    runs as before, and timing.json records the remake. Other scenes'
    slices do not move."""
    run_json = read_json(run / "run.json", {}) or {}
    char = character or speakers(run).get(sid) or slugify(cast_name_of(run))
    home = character_home(run_json.get("brand"), char, Path(cast_root) if cast_root else None)
    script = read_json(run / "lines.json", {}) or {}
    text = script.get(sid)
    if not text:
        raise SystemExit(f"{sid}: no words for this scene in lines.json — nothing to voice")
    timing = read_json(run / "vo" / "timing.json", {}) or {}
    order = [k for k, v in script.items() if v]
    same = {k for k, v in (timing.get("voices") or {}).items()
            if v.get("speaker") == home.name} or set(order)
    before = [(timing.get("scenes") or {}).get(k, {}).get("request_id")
              for k in order[:order.index(sid)] if k in same]
    ids = [r for r in before if r][-stitch_depth():]
    voice_id, model_id, settings = binding(home)
    chunk_settings = for_model(model_id, {**settings, **voice_settings_of(scene_settings(run).get(sid) or {})})
    # a remake asks with the next seed: the same seed would ask for the same
    # take that just failed (remake n sends seed + n, recorded below)
    n_remake = len(((timing.get("scenes") or {}).get(sid) or {}).get("remakes") or []) + 1
    body, said = body_for(text, model_id, lexicon_mod().for_run(run), seed_offset=n_remake)
    if chunk_settings:
        body["voice_settings"] = chunk_settings
    if ids and stitches(model_id):
        body["previous_request_ids"] = ids
    url = timestamps_url(voice_id)
    if dry_run:
        print(json.dumps({"scene": sid, "url": url, "body": body}, indent=1))
        return {"scene": sid, "dry_run": True}
    the_key = key if key is not None else key_of()
    if not the_key:
        raise SystemExit("no ELEVENLABS_API_KEY — set it in the environment or the Keychain vault")
    headers = {"xi-api-key": the_key, "Content-Type": "application/json", "Accept": "application/json"}
    got = (transport or http_json_transport)("POST", url, body, headers)
    payload, res_headers = got if isinstance(got, tuple) else (got, {})
    data = json.loads(payload.decode() if isinstance(payload, bytes) else payload)
    audio = base64.b64decode(data.get("audio_base64") or "")
    vo = run / "vo"
    dest = vo / f"{sid}.mp3"
    if dest.exists():
        arch = vo / "versions"
        arch.mkdir(parents=True, exist_ok=True)
        n = 1
        while (arch / f"{sid}-v{n}.mp3").exists():
            n += 1
        dest.rename(arch / f"{sid}-v{n}.mp3")
    vo.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(audio)
    breath = breath_of(run)
    if breath:
        tighten_pauses(dest, breath)
    level_slice(dest)
    rid = {str(k).lower(): v for k, v in (res_headers or {}).items()}.get("request-id")
    sc = (timing.setdefault("scenes", {})).setdefault(sid, {})
    sc.setdefault("remakes", []).append({"at": now(), "request_id": rid, "seconds": audio_seconds(dest),
                                         "stitched_on": ids, "seed": body.get("seed"),
                                         "sent_text": body["text"], "said_as": said["said_as"]})
    write_json(vo / "timing.json", timing)
    return {"scene": sid, "file": str(dest), "seconds": audio_seconds(dest), "request_id": rid}


def is_scene_shape(run: Path) -> bool:
    """A run built from a scene-shape brief speaks in paragraphs; an old-shape
    run speaks line by line. The run's own plan says which, so nobody has to
    pass a flag for the normal case."""
    plan = read_json(run / "plan.json", {}) or {}
    if plan.get("shape") == "scene":
        return True
    return any(s.get("frames") for s in plan.get("scenes", []) or [])


def run_for(run: Path, character: str | None = None, dry_run: bool = False,
            cast_root: str | None = None, transport=None, key: str | None = None,
            per_line: bool | None = None) -> dict:
    """The whole module, as one call — what `run.py`'s `cmd_start` uses.
    Continuous by default on a scene-shape run, per line on the old shape;
    `per_line=True/False` forces it either way."""
    run_json = read_json(run / "run.json", {}) or {}
    brand = run_json.get("brand")
    char = character or slugify(cast_name_of(run))
    lines = read_json(run / "lines.json", {}) or {}
    if not any((lines or {}).values()):
        return {}
    if not char:
        raise SystemExit("no character named — pass --character, or give the "
                          "plan a cast.name")
    home = character_home(brand, char, Path(cast_root) if cast_root else None)
    the_key = key if key is not None else key_of()
    if per_line is None:
        per_line = not is_scene_shape(run)
    if per_line:
        return make_lines(run, home, dry_run, transport or http_transport, the_key)
    homes = {}
    if not character:
        root = Path(cast_root) if cast_root else None
        homes = {sid: character_home(brand, who, root) for sid, who in speakers(run).items()
                 if sid in lines and lines[sid]}
    return make_track(run, home, dry_run, transport or http_json_transport, the_key, homes=homes)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--character")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cast-root")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--continuous", action="store_true",
                      help="one stitched track for the whole piece (the default "
                           "on a scene-shape run)")
    mode.add_argument("--per-line", action="store_true",
                      help="the legacy path: one call, one file, per line")
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    run = Path(a.run).resolve()
    if not run.is_dir():
        print(f"no such run: {run}", file=sys.stderr)
        return 3
    per_line = True if a.per_line else (False if a.continuous else None)
    try:
        manifest = run_for(run, character=a.character, dry_run=a.dry_run,
                           cast_root=a.cast_root, per_line=per_line)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    if not a.dry_run:
        if per_line is True or (per_line is None and not is_scene_shape(run)):
            print(f"{len(manifest)} line(s) voiced into {run / 'voice'}")
        else:
            print(f"{len(manifest)} scene(s) on one track in {run / 'vo'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
