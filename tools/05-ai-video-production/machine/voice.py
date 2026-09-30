#!/usr/bin/env python3
"""
voice.py — the piece's voice, generated once, on the direct ElevenLabs
account, before anything else in a run generates a single frame.

ONE CONTINUOUS VOICE (2026-09-18, Damon: "there is no clean voice-over —
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

Damon's 2026-09-17 ruling: voice is the direct ElevenLabs account, one
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

HERE = Path(__file__).resolve().parent
# machine/voice.py -> ai-video-production -> damon -> lab -> the workspace
# root — the same count run.py and prompt.py use for the same reason.
WORKSPACE = Path(__file__).resolve().parents[4]

ELEVEN_TTS = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
VOICE_SETTINGS_KEYS = ("stability", "similarity_boost", "style", "use_speaker_boost", "speed")
FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    root = cast_root if cast_root else cast_root_of(brand)
    return root / character


def key_of() -> str | None:
    """ELEVENLABS_API_KEY: env first, then the Keychain vault — never a
    crash, only ever a None when neither has it. A teammate's clone with
    no vault module and no key is simply "not found", the same as every
    other key lookup in this machine."""
    k = os.environ.get("ELEVENLABS_API_KEY")
    if k:
        return k
    try:
        import daemn_keys
        return daemn_keys.key("ELEVENLABS_API_KEY") or None
    except Exception:
        return None


def http_transport(method: str, url: str, body: dict | None, headers: dict) -> bytes:
    """The real network call — the default `transport`. Returns the raw
    audio bytes fal/Higgsfield's own submit paths never touch; this is the
    only station whose provider is always ElevenLabs, direct."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def http_json_transport(method: str, url: str, body: dict | None, headers: dict):
    """The real network call for the timestamps endpoint. Returns
    `(body_bytes, response_headers)` — the headers matter, because
    `request-id` is what the NEXT chunk is stitched onto."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read(), {k.lower(): v for k, v in dict(r.headers).items()}


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
            f"Damon's ruling 2026-09-17")
    rec = json.loads(record.read_text())
    voice_id = rec.get("voice_id")
    if not voice_id:
        raise SystemExit(
            "this character's voice is a fal library preset; bind a custom "
            "ElevenLabs voice id in voice.json (voice_id) — Damon's ruling "
            "2026-09-17")
    return voice_id, rec.get("model_id") or default_model_id(), voice_settings_of(rec)


def make_lines(run: Path, home: Path, dry_run: bool, transport, key: str | None) -> dict:
    """The LEGACY path — one call per line in `<run>/lines.json`, kept for the
    old brief shape and for re-making a single line. Returns the manifest
    written (or that would be written, on --dry-run)."""
    lines = read_json(run / "lines.json", {}) or {}
    lines = {lid: text for lid, text in lines.items() if text}
    if not lines:
        return {}

    voice_id, model_id, settings = binding(home)
    voice_dir = run / "voice"
    manifest: dict = {}

    for lid, text in lines.items():
        url = ELEVEN_TTS.format(voice_id=voice_id)
        body = {"text": text, "model_id": model_id}
        if settings:
            body["voice_settings"] = settings
        headers = {"xi-api-key": key or "", "Content-Type": "application/json",
                   "Accept": "audio/mpeg"}
        dest = voice_dir / f"{lid}.mp3"
        row = {"file": str(dest.relative_to(run)), "voice_id": voice_id,
               "model_id": model_id, "chars": len(text), "at": now()}
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
    # the ellipsis is the breath (Damon, 2026-09-19) — the one-character
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


def line_windows(text: str, alignment: dict, offset: float) -> list[dict]:
    """Every sentence of a paragraph with its start and end on the ONE
    timeline, read off the chunk's own character alignment: find the
    sentence's offset in the chunk text, then take the first character's
    start time and the last character's end time, plus everything that has
    already played."""
    starts = (alignment or {}).get("character_start_times_seconds") or []
    ends = (alignment or {}).get("character_end_times_seconds") or []
    out = []
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
    det = subprocess.run([FFMPEG, "-i", str(path), "-af",
                          f"silencedetect=noise=-30dB:d={floor}", "-f", "null", "-"],
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


def make_track(run: Path, home: Path, dry_run: bool, transport, key: str | None) -> dict:
    """THE ONE READ. One chunk per scene paragraph, stitched chunk to chunk
    on `previous_request_ids`, concatenated into `vo/track.mp3`, timed in
    `vo/timing.json`, and sliced per scene into `vo/<scene>.mp3` for the
    talking door. Returns the manifest: scene id -> its slice."""
    script = read_json(run / "lines.json", {}) or {}
    script = {sid: text for sid, text in script.items() if text}
    if not script:
        return {}

    voice_id, model_id, settings = binding(home)
    per_scene = scene_settings(run)
    vo = run / "vo"
    cap = stitch_depth()
    ids: list[str] = []
    manifest: dict = {}
    timing = {"track": "vo/track.mp3", "voice_id": voice_id, "model_id": model_id,
              "scenes": {}, "at": now()}
    played = 0.0
    chunks: list[tuple[str, bytes]] = []

    for sid, text in script.items():
        url = timestamps_url(voice_id)
        body = {"text": for_reading(text), "model_id": model_id}
        # the cast voice's own record, then this scene's settings over it —
        # the spice pass writes them per scene from the register recipe
        chunk_settings = {**settings, **voice_settings_of(per_scene.get(sid) or {})}
        if chunk_settings:
            body["voice_settings"] = chunk_settings
        if ids:
            body["previous_request_ids"] = ids[-cap:]
        headers = {"xi-api-key": key or "", "Content-Type": "application/json",
                   "Accept": "application/json"}
        if dry_run:
            print(json.dumps({"scene": sid, "url": url, "body": body}, indent=1))
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
            "lines": line_windows(text, alignment, played),
        }
        chunks.append((sid, audio))
        played += seconds

    if dry_run:
        return {sid: {"file": f"vo/{sid}.mp3", "voice_id": voice_id,
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

    track = vo / "track.mp3"
    listing = parts_dir / "concat.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in paths))
    if not run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                       "-c", "copy", str(track)]):
        # no ffmpeg (or it refused): the chunks still make one file in order
        track.write_bytes(b"".join(p.read_bytes() for p in paths))

    for sid, row in timing["scenes"].items():
        dest = vo / f"{sid}.mp3"
        cut = run_ffmpeg(["-y", "-i", str(track), "-ss", f"{row['start']:.3f}",
                          "-to", f"{row['end']:.3f}", "-c", "copy", str(dest)])
        if not cut:
            # the slice is the chunk that made it — same audio, same words
            src = next((p for p in paths if p.name.endswith(f"-{sid}.mp3")), None)
            if src:
                dest.write_bytes(src.read_bytes())
        manifest[sid] = {"file": f"vo/{sid}.mp3", "voice_id": voice_id,
                         "model_id": model_id, "chars": row["chars"],
                         "start": row["start"], "end": row["end"], "at": now()}

    timing["total"] = round(played, 3)
    write_json(vo / "timing.json", timing)
    write_json(vo / "manifest.json", manifest)
    return manifest


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
    return make_track(run, home, dry_run, transport or http_json_transport, the_key)


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
