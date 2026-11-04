#!/usr/bin/env python3
"""
voice.py — the piece's voice, generated once, on the direct ElevenLabs
account, before anything else in a run generates a single frame.

EACH LINE ITS OWN READ (VIDEO-RULINGS V4/V5, 2026-10-21; replaces the 2026-09-18 "one continuous voice"). The
voice model is the Generative Model House's (`sound.voice`, ElevenLabs v3): every scene's line is sent on its own
to `text-to-speech/{voice}/with-timestamps` with that line's delivery as its v3 audio tag ("[softly, a pause
before the price] …", the brief's `delivery_tag`). v3 takes no request stitching, so nothing is carried from one
line to the next — the 2026-09-18 stitched read was a v2 feature and is not used. With `READS` above 1 (run_v2
sets 3) every line is read three times, each read heard back word for word (audiocheck), and the best one is
LOCKED (`vo/locks.json`, every read kept under `vo/reads/`). The locked reads are laid end to end on
`vo/track.mp3` only so `vo/timing.json` can say where every line sits; the talking door gets each scene's own
locked read, `vo/<scene>.mp3`, exactly as it was read.

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
Finds the character's `voice.json` under `brands/<brand>/ai-cast/<name>/`
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
import concurrent.futures as cf
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

    The count here was right only while this file sat in lab/owner/. The move
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
# machine/voice.py -> ai-video-production -> owner -> lab -> the workspace
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
    """The house voice model (components/generative-model-house `sound.voice`, P23). A house that cannot be read is
    a STOP naming it — never a model written anywhere else (verify 2026-10-21 row 17, VIDEO-RULINGS V2)."""
    try:
        return _load("house").voice_model()
    except (Exception, SystemExit) as e:                # noqa: BLE001
        raise SystemExit(f"the voice model comes from the Generative Model House (sound.voice) and it could not be "
                         f"read: {e}") from None


OUTPUT_FORMAT = "mp3_44100_192"   # ElevenLabs' best mp3 (P47: the 128 kbps default added to the muffled sound)


def timestamps_url(voice_id: str) -> str:
    url = (contract().get("endpoints") or {}).get("with_timestamps") or ""
    url = url.replace("{voice_id}", voice_id)
    return url + ("&" if "?" in url else "?") + f"output_format={OUTPUT_FORMAT}" if url else url


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


def body_for(text: str, model_id: str, rows: list | None, seed_offset: int = 0,
             tag: str | None = None) -> tuple[dict, dict]:
    sent, said = prepared(text, rows)
    sg = _load("sheet_gates")                   # the Eleven v3 sheet, before the line is sent
    sg.raise_on_errors(sg.voice_text("eleven-v3", sent), "voice")
    # THE DELIVERY IS SENT (P12, VIDEO-RULINGS V4): on v3 the line's own delivery goes in as its audio tag,
    # "[softly, a pause before the price] …" — the voice model reads the tag, the captions never see it
    t = " ".join(str(tag or "").strip().strip("[]").split())
    if t and "v3" in (model_id or "") and not re.match(r"^\s*\[", sent):
        sent = f"[{t}] {sent}"
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
    create a voice just for our person … not Susan's"). Scene id -> the bank
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
    """ELEVENLABS_API_KEY through the shared key loader (vp_keys) — never a
    crash, only ever a None when it is not found, the same as every
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
    # went out on the account's defaults, and a long read drifted: Creator-A came back
    # British on one line and Australian on another (2026-10-01). Nested first,
    # top-level keys (older records) over them.
    # THE MODEL IS THE HOUSE'S (verify 2026-10-21 row 7, VIDEO-RULINGS V2/V4): a voice.json's own `model_id`
    # (eleven_multilingual_v2 on older casts) is history — every read, the rescue re-read and the audio gate's remake
    # included, is on the house voice (ElevenLabs v3), whichever module loaded this file
    return voice_id, default_model_id(), \
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

    tags = delivery_tags(run)
    for lid, text in lines.items():
        url = ELEVEN_TTS.format(voice_id=voice_id)
        body, said = body_for(text, model_id, rows, tag=tags.get(lid))
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


READS = 1          # reads made of every line at once; V33/V34 (2026-10-21): one — the first read is meant to land
TRIES = 1          # V34 (the owner 2026-10-21: "3 tries max if there is failure"): a read that fails its words check is read
                   # again, one at a time, up to this many in all; the first that passes is locked (run_v2 sets 3)
VOICE_PARALLEL = 4  # reads in flight at once (P52) — under ElevenLabs' concurrency limit; a 429 backs off (_retry)


def delivery_tags(run: Path) -> dict:
    """{scene id: the scene's v3 delivery tag} — the brief's `delivery_tag` (shot contract, CHANGES.md 2026-10-21) on
    the scene, else its only `lines[]` row's; the plan's when the brief has none. {} for an older brief. A scene of
    several lines is read line by line, each with its own tag (scene_lines) — this is only the scene's fallback."""
    out = {}
    scenes = list(_doc_of(run).get("scenes") or []) + list((read_json(run / "plan.json", {}) or {}).get("scenes") or [])
    for s in scenes:
        if not isinstance(s, dict) or str(s.get("id")) in out:
            continue
        tag = s.get("delivery_tag")
        rows = s.get("lines") if isinstance(s.get("lines"), list) else []
        if not tag and len(rows) == 1 and isinstance(rows[0], dict):
            tag = rows[0].get("delivery_tag")
        if tag:
            out[str(s.get("id"))] = str(tag)
    return out


def scene_lines(run: Path, sid: str, text: str, tag: str | None) -> list:
    """[(line id, words, delivery tag)] for one scene (P55): its shots' lines (shots[].lines[].say, each with its own
    `delivery_tag`, else its shot's, else the scene's) — or, with no shots, the scene's own `lines[]` rows — when they
    make up the scene's words, in order; else the scene as ONE line, id = the scene id (every older brief). Every line
    is read with ITS OWN tag (verify 2026-10-21 row 4): a scene that is one line takes that line's tag, never the
    first row's for the whole scene."""
    doc = _doc_of(run)
    sc = next((x for x in doc.get("scenes") or [] if str(x.get("id")) == str(sid)), None) or {}
    words = lambda l: str(l.get("say") or l.get("text") or "").strip()
    rows_ = []
    for sh in sc.get("shots") or []:
        if not isinstance(sh, dict):
            continue
        for l in sh.get("lines") or []:
            if isinstance(l, dict) and words(l):
                rows_.append((words(l), l.get("delivery_tag") or sh.get("delivery_tag") or sc.get("delivery_tag") or tag))
    if not rows_:
        for l in sc.get("lines") if isinstance(sc.get("lines"), list) else []:
            if isinstance(l, dict) and words(l):
                rows_.append((words(l), l.get("delivery_tag") or sc.get("delivery_tag") or tag))
    norm = lambda t: " ".join(re.findall(r"[a-z0-9']+", re.sub(r"\[[^\]]*\]", " ", str(t or "")).lower()))
    if not rows_ or norm(" ".join(r[0] for r in rows_)) != norm(text):
        return [(sid, text, tag)]
    if len(rows_) == 1:
        return [(sid, text, rows_[0][1])]
    return [(f"{sid}.L{n}", say, t) for n, (say, t) in enumerate(rows_, 1)]


def join_line_reads(vo: Path, sid: str, parts: list, gap: float) -> tuple:
    """A scene's slice from its lines' locked reads, one after another with `gap` seconds of quiet between
    (P55): (audio bytes, the joined character alignment, the joined sent text). Without ffmpeg the reads are
    joined end to end and the alignment carries no gap."""
    d = vo / "lines"
    d.mkdir(parents=True, exist_ok=True)
    files = []
    for n, (audio, _al, _t) in enumerate(parts, 1):
        f = d / f"{sid}.L{n}.mp3"
        f.write_bytes(audio)
        files.append(f)
    quiet = d / f"{sid}-gap.mp3"
    out = d / f"{sid}-joined.mp3"
    listing = d / f"{sid}-joined.txt"
    ok = run_ffmpeg(["-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{gap:.3f}", "-c:a", "libmp3lame",
                     "-b:a", "192k", str(quiet)])
    seq = [x for f in files for x in (f, quiet)][:-1] if ok else files
    listing.write_text("".join(f"file '{x.name}'\n" for x in seq))
    joined = (run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c:a", "libmp3lame", "-b:a", "192k",
                          str(out)]) and out.is_file())
    audio = out.read_bytes() if joined else b"".join(a for a, _al, _t in parts)
    gap_s = gap if (ok and joined) else 0.0
    chars, starts, ends, t0 = [], [], [], 0.0
    for n, (_a, al, txt) in enumerate(parts):
        if n:
            chars.append(" "); starts.append(round(t0 - gap_s, 3)); ends.append(round(t0, 3))
        cs = list(al.get("characters") or list(txt))
        st = al.get("character_start_times_seconds") or [0.0] * len(cs)
        en = al.get("character_end_times_seconds") or [0.0] * len(cs)
        chars += cs
        starts += [round(t0 + float(x), 3) for x in st]
        ends += [round(t0 + float(x), 3) for x in en]
        t0 = t0 + chunk_duration(al) + gap_s
    return audio, {"characters": chars, "character_start_times_seconds": starts,
                   "character_end_times_seconds": ends}, " ".join(t for _a, _al, t in parts)


def score_read(path: Path, line: str, rows: list | None, check=None) -> dict:
    """One read of a line, heard back: its words (audiocheck.check_slice — every word, the line finished,
    protected words and figures), its length. The best read is the one that passes with the closest words."""
    try:
        got = (check or _load("audiocheck").check_slice)(path, line, rows=rows)
    except Exception as e:                              # noqa: BLE001 — a read nobody heard is never locked first
        got = {"pass": False, "match": 0.0, "problems": [f"not heard: {e}"[:200]]}
    return {"pass": bool(got.get("pass")), "match": float(got.get("match") or 0.0),
            "seconds": audio_seconds(path), "problems": got.get("problems") or []}


def best_read(scored: list[dict]) -> int:
    """The index of the locked read: a passing read first, then the closest words, then the read whose length
    is nearest the others' middle (consistency over a lucky outlier — V5), then the earliest."""
    lens = sorted(x["seconds"] for x in scored if x.get("seconds"))
    mid = lens[len(lens) // 2] if lens else 0.0
    return max(range(len(scored)), key=lambda i: (scored[i]["pass"], round(scored[i]["match"], 3),
                                                  -abs((scored[i].get("seconds") or mid) - mid), -i))


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


# the owner, 19 Oct 2026: "knowing the general voice pacing in the swipe … will determine the same pacing for the
# audio we create." The swipe's own transcript (teardown's transcript.json, one row per speaker turn with start
# and end) gives its words per second and its pause between lines. The voice is asked for at that speed
# (ElevenLabs `speed`, 0.7–1.2) and the take's pauses are cut to the swipe's, so our read breathes like the swipe.
NATURAL_WPS = 2.6        # what a voice reads at speed 1.0, near enough; the speed asked for is swipe ÷ this


def swipe_pace(run: Path) -> dict | None:
    rj = read_json(run / "run.json", {}) or {}
    bf = rj.get("brief_from")
    cands = []
    if bf:
        b = Path(bf)
        cands += [b.parent.parent / "transcript.json", b.parent / "transcript.json"]
    cands.append(run / "transcript.json")
    rows = next((read_json(c, None) for c in cands if c.is_file()), None)
    if not isinstance(rows, list) or not rows:
        return None
    words = spoken = 0.0
    gaps = []
    prev_end = None
    for r in rows:
        try:
            a, b = float(r["start"]), float(r["end"])
        except Exception:
            continue
        n = len(str(r.get("text") or "").split())
        if b > a and n:
            words += n
            spoken += b - a
        if prev_end is not None and a > prev_end:
            gaps.append(a - prev_end)
        prev_end = b
    if words < 5 or spoken <= 0:
        return None
    wps = words / spoken
    gaps.sort()
    pause = gaps[len(gaps) // 2] if gaps else None
    return {"words_per_second": round(wps, 2),
            "pause_s": round(min(max(pause, 0.15), 1.2), 2) if pause is not None else None,
            "speed": round(min(max(wps / NATURAL_WPS, 0.7), 1.2), 2), "lines": len(rows)}


def breath_of(run: Path) -> float | None:
    """The pause length the take is cut to: the matched creators' mean pause
    from the brand's voiceprint roll-up (brief block -> piece.voiceprint or
    the run's own voiceprint.json), else the spoken slice's default breath,
    else None (no tightening)."""
    sp = swipe_pace(run)                       # the swipe's own pause wins: it is the ad we are remaking
    if sp and sp.get("pause_s"):
        return sp["pause_s"]
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
    # quiet voice's words as silence and cut them out (the LeBron moderator, ~25 dB
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
        # aresample re-frames the cut: a segment ending at the take's last frame broke libmp3lame
        # ("inadequate AVFrame plane padding", exit 234) and stopped the baddie barber's voice (2026-10-21)
        subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                        "-i", str(path), "-af", "aresample=44100", "-c:a", "libmp3lame", "-b:a", "128k",
                        str(seg)], check=True)
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
    pace = swipe_pace(run)
    vo = run / "vo"
    cap = stitch_depth()
    ids_by_voice: dict = {}
    manifest: dict = {}
    timing = {"track": "vo/track.mp3", "voice_id": voice_id, "model_id": model_id,
              "voices": {}, "pins": pins(), "scenes": {}, "at": now(), "swipe_pace": pace}
    played = 0.0
    chunks: list[tuple[str, bytes]] = []
    tags = delivery_tags(run)
    locks = read_json(vo / "locks.json", {}) or {}

    n_reads = max(1, int(READS))
    # EVERY READ AT ONCE (P52, 2026-10-21, the owner: "figure out ways to make this more efficient"): v3 takes no
    # stitching, so no read waits on another — every line's reads (and each read's words check) run side by side,
    # VOICE_PARALLEL at a time; a 429 backs off and asks again (_retry). A stitched (v2) voice still reads in order.
    stitched = any(stitches(m) for _v, m, _s in bound.values())
    pool = cf.ThreadPoolExecutor(max_workers=VOICE_PARALLEL) if (not dry_run and not stitched) else None
    jobs: dict = {}

    def request(sid, text, tag):
        voice_id, model_id, settings = bound[homes.get(sid) or home]
        ids = ids_by_voice.setdefault(voice_id, [])   # stitched within one voice only
        url = timestamps_url(voice_id)
        body, said = body_for(text, model_id, rows, tag=tag)
        # the cast voice's own record, then this scene's settings over it —
        # the spice pass writes them per scene from the register recipe
        chunk_settings = for_model(model_id, {**settings, **({"speed": pace["speed"]} if pace else {}),
                                              **voice_settings_of(per_scene.get(sid) or {})})
        if chunk_settings:
            body["voice_settings"] = chunk_settings
        if ids and stitches(model_id):
            body["previous_request_ids"] = ids[-cap:]
        headers = {"xi-api-key": key or "", "Content-Type": "application/json",
                   "Accept": "application/json"}
        return voice_id, url, body, said, chunk_settings, headers

    def one_read(url, body, headers, k: int):
        b_ = dict(body, **({"seed": body["seed"] + k} if k and body.get("seed") is not None else {}))
        got = transport("POST", url, b_, headers)
        payload, res_headers = got if isinstance(got, tuple) else (got, {})
        data = json.loads(payload.decode() if isinstance(payload, bytes) else payload)
        return (base64.b64decode(data.get("audio_base64") or ""),
                data.get("alignment") or data.get("normalized_alignment") or {},
                {str(k_).lower(): v for k_, v in (res_headers or {}).items()}.get("request-id"), b_)

    def read_and_hear(lid, text, url, body, headers, k):
        r_ = one_read(url, body, headers, k)
        if n_reads == 1 and TRIES <= 1:
            return r_, None
        reads_dir = vo / "reads"
        reads_dir.mkdir(parents=True, exist_ok=True)
        f_ = reads_dir / f"{lid}-r{k + 1}.mp3"
        f_.write_bytes(r_[0])
        return r_, {"read": k + 1, "file": str(f_.relative_to(run)), "seed": r_[3].get("seed"),
                    **score_read(f_, text, rows)}

    def tries_of(lid, text, url, body, headers):
        """ONE READ, AGAIN ONLY ON FAILURE (V34): read, hear it; read again only when the words check fails, up to TRIES
        reads in all. Returns every read made, in order."""
        out = []
        for k in range(max(1, int(TRIES))):
            got_ = read_and_hear(lid, text, url, body, headers, k)
            out.append(got_)
            if (got_[1] or {}).get("pass"):
                break
        return out
    retrying = n_reads == 1 and int(TRIES) > 1

    # EACH LINE ITS OWN READ (P55, VIDEO-RULINGS V4): a scene whose shots carry lines (shots[].lines[].say) is read
    # line by line, each with its own delivery tag, three reads a line, one locked a line; a scene without them is
    # one line, as before. The scene's slice is its lines' locked reads, one after another, a breath between.
    units = {sid: scene_lines(run, sid, text, tags.get(sid)) for sid, text in script.items()}
    if pool is not None:
        for sid, text in script.items():
            for lid, say, tag in units[sid]:
                _vid, url, body, _said, _cs, headers = request(sid, say, tag)
                jobs[lid] = ([pool.submit(tries_of, lid, say, url, body, headers)] if retrying else
                             [pool.submit(read_and_hear, lid, say, url, body, headers, k) for k in range(n_reads)])

    for sid, text in script.items():
        timing["voices"][sid] = {"voice_id": bound[homes.get(sid) or home][0], "speaker": (homes.get(sid) or home).name}
        got_lines = []
        for lid, say, tag in units[sid]:
            voice_id, url, body, said, chunk_settings, headers = request(sid, say, tag)
            ids = ids_by_voice.setdefault(voice_id, [])
            if dry_run:
                for k in range(n_reads):
                    b_ = dict(body, **({"seed": body["seed"] + k} if k and body.get("seed") is not None else {}))
                    print(json.dumps({"scene": sid, **({"line": lid} if lid != sid else {}),
                                      "speaker": (homes.get(sid) or home).name,
                                      **({"read": f"{k + 1} of {n_reads}"} if n_reads > 1 else {}),
                                      "url": url, "body": b_}, indent=1))
                continue
            if retrying:
                got_reads = jobs[lid][0].result() if lid in jobs else tries_of(lid, say, url, body, headers)
            else:
                got_reads = ([f.result() for f in jobs[lid]] if lid in jobs
                             else [read_and_hear(lid, say, url, body, headers, k) for k in range(n_reads)])
            if got_reads[0][1] is None:
                r_ = got_reads[0][0]
            else:
                # THREE CLEAN READS, SCORED, ONE LOCKED (P13, VIDEO-RULINGS V5): every read kept under vo/reads/,
                # each heard back word for word; the locked one is the line's voice from here on (vo/locks.json)
                made = [x for x, _sc in got_reads]
                scored = [sc for _x, sc in got_reads]
                pick_i = best_read(scored)
                r_ = made[pick_i]
                locks[lid] = {"locked": pick_i + 1, "reads": scored, "tag": tag, "scene": sid, "say": say, "at": now()}
                write_json(vo / "locks.json", locks)
                print(f"  {lid}: {len(made)} read(s) — read {pick_i + 1} locked "
                      f"({'passes' if scored[pick_i]['pass'] else 'BEST OF NONE PASSING'}, match {scored[pick_i]['match']})")
            if r_[2]:
                ids.append(r_[2])
            got_lines.append((lid, say, tag, r_, said, chunk_settings))
        if dry_run:
            continue
        if len(got_lines) == 1:
            _lid, _say, tag0, (audio, alignment, rid, _sent), said, chunk_settings = got_lines[0]
            sent_text = _sent["text"]
        else:
            audio, alignment, sent_text = join_line_reads(vo, sid, [(x[3][0], x[3][1], x[3][3]["text"]) for x in got_lines],
                                                          breath_of(run) or 0.4)
            rid, _sent = got_lines[-1][3][2], got_lines[0][3][3]
            said = {"said_as": [w for x in got_lines for w in x[4]["said_as"]],
                    "numbers": [w for x in got_lines for w in x[4]["numbers"]]}
            chunk_settings, tag0 = got_lines[0][5], got_lines[0][2]

        seconds = chunk_duration(alignment)
        timing["scenes"][sid] = {
            "start": round(played, 3), "end": round(played + seconds, 3),
            "seconds": round(seconds, 3), "file": f"vo/{sid}.mp3",
            "request_id": rid, "chars": len(text),
            "voice_settings": chunk_settings or None,
            # what the model was SENT (protected words and figures said out),
            # and what was swapped — the captions keep the script's spelling
            "sent_text": sent_text, "said_as": said["said_as"], "numbers": said["numbers"],
            "seed": _sent.get("seed"), "delivery_tag": tag0,
            **({"locked_read": locks[sid]["locked"]} if sid in locks and (n_reads > 1 or retrying) else {}),
            **({"line_reads": [{"line": x[0], "tag": x[2], **({"locked_read": locks[x[0]]["locked"]}
                                                               if x[0] in locks and (n_reads > 1 or retrying) else {})}
                               for x in got_lines]} if len(got_lines) > 1 else {}),
            "lines": line_windows(text, alignment, played, said=sent_text),
        }
        chunks.append((sid, audio))
        played += seconds
    if pool is not None:
        pool.shutdown(wait=True)

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
    repace(run)
    return read_json(vo / "manifest.json", manifest) or manifest


# THE READ MOVES AT THE SWIPE'S PACE (2026-10-27). ElevenLabs' `speed`
# tops out at 1.2 and v3 honours it only loosely, so a slow-voiced cast member still read at about half the swipe's
# words per second (a 36 s swipe became an 85 s read). After the reads are locked, every line slower than the swipe is
# sped up to the swipe's words per second — pitch kept (ffmpeg atempo), never past PACE_MAX — and the timing sheet,
# the slices and the track are rebuilt off the new audio. The read as made is kept as vo/versions/<id>-before-pace.mp3.
PACE_MAX = 2.0
PACE_SLACK = 0.92        # a line already at 92% of the swipe's pace is left alone


def _spoken_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", re.sub(r"\[[^\]]*\]", " ", text or "")))


def repace(run: Path) -> dict:
    """Every scene's slice brought up to the swipe's words per second (see above). {scene: factor} for those changed."""
    vo = Path(run) / "vo"
    timing = read_json(vo / "timing.json", {}) or {}
    wps = float(((timing.get("swipe_pace") or {}).get("words_per_second")) or 0)
    if not wps or not timing.get("scenes"):
        return {}
    done = {}
    for sid, sc in timing["scenes"].items():
        f = vo / f"{sid}.mp3"
        keep = vo / "versions" / f"{sid}-before-pace.mp3"
        src = keep if keep.is_file() else f            # always paced from the read as made, so a re-pace never compounds
        secs = audio_seconds(src) if src.is_file() else None
        words = _spoken_words(sc.get("sent_text") or "")
        if not secs or not words:
            continue
        cur = words / secs
        if cur >= wps * PACE_SLACK:
            continue
        factor = round(min(PACE_MAX, wps / cur), 3)
        if (sc.get("paced") or {}).get("factor") == factor:
            continue
        keep.parent.mkdir(parents=True, exist_ok=True)
        if not keep.exists():
            keep.write_bytes(f.read_bytes())
        tmp = f.with_suffix(".paced.mp3")
        if not run_ffmpeg(["-y", "-i", str(keep), "-filter:a", f"atempo={factor}", str(tmp)]):
            continue
        tmp.replace(f)
        level_slice(f)
        sc["paced"] = {"factor": factor, "from_seconds": round(secs, 3), "swipe_wps": wps, "before": f"vo/versions/{keep.name}"}
        done[sid] = factor
    if not done:
        return {}
    t, order = 0.0, sorted(timing["scenes"].items(), key=lambda kv: kv[1].get("start") or 0)
    for sid, sc in order:
        secs = audio_seconds(vo / f"{sid}.mp3") or sc.get("seconds") or 0.0
        old_start, old_len = sc.get("start") or 0.0, sc.get("seconds") or secs or 1.0
        k = secs / old_len if old_len else 1.0
        for ln in sc.get("lines") or []:
            for key in ("start", "end"):
                if isinstance(ln.get(key), (int, float)):
                    ln[key] = round(t + (ln[key] - old_start) * k, 3)
        sc["start"], sc["seconds"], sc["end"] = round(t, 3), round(secs, 3), round(t + secs, 3)
        t += secs
    timing["total"] = round(t, 3)
    listing = vo / "pace-concat.txt"
    listing.write_text("".join(f"file '{sid}.mp3'\n" for sid, _ in order))
    run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(vo / "track.mp3")])
    listing.unlink()
    write_json(vo / "timing.json", timing)
    man = read_json(vo / "manifest.json", {}) or {}
    for sid, row in man.items():
        sc = timing["scenes"].get(sid)
        if sc:
            row["start"], row["end"] = sc["start"], sc["end"]
    write_json(vo / "manifest.json", man)
    return done


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
    # rest (the LeBron moderator; the owner heard it). What is left is closed with
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
    rows = lexicon_mod().for_run(run)
    url = timestamps_url(voice_id)
    vo = run / "vo"
    # PER LINE, AS THE MAIN READ IS (P61): each of the scene's lines its own read with its own tag, READS reads a
    # line heard back and one locked a line (vo/locks.json), joined with a breath — never the scene as ONE read
    units = scene_lines(run, sid, text, delivery_tags(run).get(sid))
    n_reads = max(1, int(READS))
    the_key = None
    if not dry_run:
        the_key = key if key is not None else key_of()
        if not the_key:
            raise SystemExit("no ELEVENLABS_API_KEY — set it in the environment or the Keychain vault")
    headers = {"xi-api-key": the_key or "", "Content-Type": "application/json", "Accept": "application/json"}
    locks = read_json(vo / "locks.json", {}) or {}
    got_lines, body, said = [], None, {"said_as": [], "numbers": []}
    for lid, say, tag in units:
        body, said_ = body_for(say, model_id, rows, seed_offset=n_remake * n_reads, tag=tag)
        said = {"said_as": said["said_as"] + said_["said_as"], "numbers": said["numbers"] + said_["numbers"]}
        if chunk_settings:
            body["voice_settings"] = chunk_settings
        if ids and stitches(model_id) and len(units) == 1:
            body["previous_request_ids"] = ids
        if dry_run:
            for k in range(n_reads):
                print(json.dumps({"scene": sid, **({"line": lid} if lid != sid else {}), "url": url,
                                  "body": dict(body, **({"seed": body["seed"] + k} if k and body.get("seed") is not None else {}))},
                                 indent=1))
            continue
        made, scored = [], []
        for k in range(n_reads):
            b_ = dict(body, **({"seed": body["seed"] + k} if k and body.get("seed") is not None else {}))
            got = (transport or http_json_transport)("POST", url, b_, headers)
            payload, res_headers = got if isinstance(got, tuple) else (got, {})
            data = json.loads(payload.decode() if isinstance(payload, bytes) else payload)
            r_ = (base64.b64decode(data.get("audio_base64") or ""),
                  data.get("alignment") or data.get("normalized_alignment") or {},
                  {str(k_).lower(): v for k_, v in (res_headers or {}).items()}.get("request-id"), b_)
            made.append(r_)
            if n_reads > 1:
                (vo / "reads").mkdir(parents=True, exist_ok=True)
                f_ = vo / "reads" / f"{lid}-remake{n_remake}-r{k + 1}.mp3"
                f_.write_bytes(r_[0])
                scored.append({"read": k + 1, "file": str(f_.relative_to(run)), "seed": b_.get("seed"),
                               **score_read(f_, say, rows)})
        pick_i = best_read(scored) if scored else 0
        if scored:
            locks[lid] = {"locked": pick_i + 1, "reads": scored, "tag": tag, "scene": sid, "say": say,
                          "remake": n_remake, "at": now()}
        got_lines.append(made[pick_i])
    if dry_run:
        return {"scene": sid, "dry_run": True}
    if len(locks):
        write_json(vo / "locks.json", locks)
    if len(got_lines) == 1:
        audio, _al, rid, body = got_lines[0]
    else:
        audio, _al, _txt = join_line_reads(vo, sid, [(r[0], r[1], r[3]["text"]) for r in got_lines], breath_of(run) or 0.4)
        rid, body = got_lines[-1][2], {**got_lines[0][3], "text": _txt}
        res_headers = {}
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
    sc = (timing.setdefault("scenes", {})).setdefault(sid, {})
    sc.setdefault("remakes", []).append({"at": now(), "request_id": rid, "seconds": audio_seconds(dest),
                                         "stitched_on": ids, "seed": body.get("seed"), "lines": len(got_lines),
                                         "sent_text": body["text"], "said_as": said["said_as"]})
    write_json(vo / "timing.json", timing)
    return {"scene": sid, "file": str(dest), "seconds": audio_seconds(dest), "request_id": rid}


def paced_read(run: Path, sid: str, speed: float, dest: Path, character: str | None = None,
               cast_root: str | None = None, transport=None, key: str | None = None, text: str | None = None) -> dict:
    """ONE MORE READ OF A LINE, AT THE PACE OF ITS BEST TAKE (P49, 2026-10-21): same words, voice, model, tag and
    settings as the locked read, its `speed` multiplied by `speed` (ElevenLabs takes 0.7–1.2), written to `dest` —
    a candidate beside the other reads, never over vo/<scene>.mp3. Recorded in vo/locks.json under the line."""
    run_json = read_json(run / "run.json", {}) or {}
    char = character or speakers(run).get(sid) or slugify(cast_name_of(run))
    home = character_home(run_json.get("brand"), char, Path(cast_root) if cast_root else None)
    text = text or (read_json(run / "lines.json", {}) or {}).get(sid)   # one line of the scene (P55), else all of it
    if not text:
        raise SystemExit(f"{sid}: no words for this scene in lines.json — nothing to read")
    voice_id, model_id, settings = binding(home)
    base = {**settings, **voice_settings_of(scene_settings(run).get(sid) or {})}
    pace = round(max(0.7, min(1.2, float(base.get("speed") or 1.0) * float(speed))), 3)
    body, _said = body_for(text, model_id, lexicon_mod().for_run(run), seed_offset=READS + 1,
                           tag=delivery_tags(run).get(sid))
    body["voice_settings"] = for_model(model_id, {**base, "speed": pace})
    the_key = key if key is not None else key_of()
    if not the_key:
        raise SystemExit("no ELEVENLABS_API_KEY — set it in the environment")
    got = (transport or http_json_transport)("POST", timestamps_url(voice_id), body,
                                             {"xi-api-key": the_key, "Content-Type": "application/json",
                                              "Accept": "application/json"})
    payload = got[0] if isinstance(got, tuple) else got
    data = json.loads(payload.decode() if isinstance(payload, bytes) else payload)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(base64.b64decode(data.get("audio_base64") or ""))
    locks = read_json(run / "vo" / "locks.json", {}) or {}
    locks.setdefault(sid, {}).setdefault("paced", []).append({"file": str(dest.relative_to(run)) if run in dest.parents
                                                              else str(dest), "speed": pace, "at": now()})
    write_json(run / "vo" / "locks.json", locks)
    return {"file": str(dest), "speed": pace}


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
    # The plan's cast name is the first scene's `who` ("BRAND-B, seen and not speaking", 2026-10-09) —
    # the lead's folder is the brief's cast row that name points at, by its bank_id.
    if not character:
        _nm = cast_name_of(run).upper()
        for _c in _doc_of(run).get("cast") or []:
            _id, _b = (_c.get("id") or _c.get("name") or ""), _c.get("bank_id") or ""
            if _id and _id.upper() in _nm and _b and _b.upper() != "NEW":
                char = _b
                break
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
