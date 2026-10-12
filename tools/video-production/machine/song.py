#!/usr/bin/env python3
"""
song.py — the song for a sung piece, printed from the brief's song block and
nothing else. SONG-CHAIN.md is the chain, step by step.

the owner, 2026-09-23: "if we trigger a song to be made, we have a specific
protocol / chain to do that as well, so we remove all hallucination and
variables and can just print." And, the same day, after the blind test:
"Eleven Labs won for me for sure." So the song is ElevenLabs Music
(`music_v2_5`), and every input to it is pinned:

  the words    the brief's `song.sections[].lines` — and every one of them must
               already be a line of the script (the scenes' `lyrics`). song.py
               never writes, fixes or pads a lyric; a line that is not in the
               script is refused by name, and a script line no section sings is
               refused by name too.
  the sound    ONE row of banks/music-styles/index.json, by `song.style_id`. No
               free-text style in a brief. A draft row, an unknown id, a vocal
               that disagrees with the row, or a section name the row has no
               line for is refused by name.
  the request  built mechanically: one chunk per section, text = its lines
               joined by newlines, duration_ms = seconds × 1000, positive styles
               = the row's + "<bpm> BPM" + the row's line for that section,
               negative styles = the row's. Model id, url, output format, seed,
               context adherence and the limits come from providers.json
               (direct.elevenlabs_song) — never a literal here.
  the saying   each line is SENT with the brand's protected words swapped for
               how they are said (brands/<brand>/brand-identity/voice/pronunciation.json) and
               every figure in words (spoken-rules.json), by lexicon.for_model —
               the same step the voice takes. The brief's lines are untouched;
               request.json and song.json record what was swapped.

    python3 machine/song.py <run> [--dry-run]

Writes, under `<run>/song/`:
  request.json   exactly what is (or would be) sent — written on --dry-run too
  song.mp3       the song as it came back; NEVER overwritten (a remake moves the
                 old take to versions/song-vN.mp3 first) and never levelled
  song-14lufs.mp3  a copy, levelled to −14 LUFS (one linear gain)
  transcript.json  what speech-to-text heard, with word times
  timing.json    every line and every section on the song's clock, from the
                 transcript's word times — for captions and cuts
  song.json      the record: model, seed, takes, the gate's verdicts, cost

THE SONG GATE: the song is transcribed (ElevenLabs speech-to-text, the same
door lineparity.py uses); every section's lines must be heard, in order, each
at or above providers.json gates.song_lines.threshold, and the last line must
finish (lineparity.ending_heard); every protected word in the lyrics must be
heard (matched on its real spelling) and every figure heard as its words. A
word nobody has confirmed by ear is a warning. A failing take is made ONCE more — the same
request with the next seed — and heard again; still failing, the run STOPS,
naming the line that is missing.

`transport(method, url, headers, body_bytes) -> (status, headers, bytes)` is
the one seam every real call goes through (music and speech-to-text), the
same shape as lineparity.py's. Tests pass fakes; nothing here calls the
network on --dry-run.

Exit 0 pass · 2 stopped (a refusal, or the gate failed twice) · 3 bad input.
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STYLE_BANK = HERE.parent / "banks" / "music-styles" / "index.json"
TARGET_LUFS = -14.0


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lp = _load("lineparity")
platform = lp.platform


class Refused(SystemExit):
    """The brief's song block cannot be printed as it stands. The message
    names exactly what is wrong and where."""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(p: Path, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def door() -> dict:
    """providers.json direct.elevenlabs_song — url, model, query, seed, limits."""
    d = (platform.registry().get("direct") or {}).get("elevenlabs_song")
    if not d:
        raise Refused("providers.json has no direct.elevenlabs_song row — the song door is not configured")
    return d


def door_closed() -> str:
    """'' when providers.json doors.audio is this door (direct:<the song
    model's provider>); otherwise the reason, named — song.py prints on its
    own door only, and never quietly on another."""
    reg = platform.registry()
    primary = str(((reg.get("doors") or {}).get("audio") or {}).get("primary", ""))
    model = (reg.get("models") or {}).get(door()["model_id"]) or {}
    mine = f"direct:{model.get('provider', '?')}"
    if primary != mine:
        return (f"the brief's song block has sections, but the song door is {primary!r} — "
                f"song.py prints on {mine} only")
    return ""


def threshold() -> float:
    g = (platform.registry().get("gates") or {}).get("song_lines") or {}
    return float(g.get("threshold", 0.75))


def usd_per_second(model_id: str) -> float | None:
    m = (platform.registry().get("models") or {}).get(model_id) or {}
    for r in m.get("rates") or []:
        if "usd_per_second" in r:
            return float(r["usd_per_second"])
    return None


# --------------------------------------------------------------- the words

def _key(line: str) -> str:
    """A line's identity for matching: its words, lower case, no punctuation."""
    return " ".join(lp.normalize(line))


def script_lines(plan: dict) -> list[tuple[str, str]]:
    """(scene id, line) for every line of the script — the scenes' `lyrics`,
    in play order. That list IS the script of a sung piece (brief v16)."""
    out = []
    for s in plan.get("scenes") or []:
        for ln in s.get("lyrics") or []:
            if str(ln).strip():
                out.append((str(s.get("id")), str(ln).strip()))
    return out


def check_words(block: dict, plan: dict) -> None:
    """Every sung line is a script line, and every script line is sung."""
    script = script_lines(plan)
    if not script:
        raise Refused("the brief carries no script to sing — a sung piece puts its lines in each "
                      "scene's `lyrics` (brief v16); song.py never writes a lyric")
    known = {_key(l) for _, l in script}
    sung = set()
    for i, sec in enumerate(block.get("sections") or [], 1):
        for ln in sec.get("lines") or []:
            if _key(ln) not in known:
                raise Refused(f"song section {i} ({sec.get('name')}) sings {ln!r}, which is not a line "
                              f"of the script — a lyric comes only from the scenes' `lyrics`, word for word")
            sung.add(_key(ln))
    missing = [(sid, l) for sid, l in script if _key(l) not in sung]
    if missing:
        sid, l = missing[0]
        raise Refused(f"scene {sid}'s line {l!r} is in no section of the song — every line of the "
                      f"script is sung, or the picture shows words nobody hears")


# --------------------------------------------------------------- the sound

def load_styles(path: Path | None = None) -> dict:
    doc = read_json(Path(path or STYLE_BANK))
    if not doc or not isinstance(doc.get("rows"), list):
        raise Refused(f"the music style bank cannot be read at {path or STYLE_BANK}")
    return {r["id"]: r for r in doc["rows"] if r.get("id")}


def style_row(block: dict, styles: dict) -> dict:
    sid = block.get("style_id")
    if not sid:
        raise Refused("the song block names no style_id — the sound is one row of "
                      "banks/music-styles/index.json, never words in the brief")
    row = styles.get(sid)
    if row is None:
        raise Refused(f"style_id {sid!r} is not a row of the music style bank — the rows are: "
                      f"{' · '.join(sorted(styles))}")
    if row.get("status") != "approved":
        raise Refused(f"style {sid!r} is a {row.get('status') or 'unmarked'} row, not approved — the owner "
                      f"hears and approves a style before a run sings in it")
    vocal = block.get("vocal")
    if vocal and str(vocal).lower() != str(row.get("vocal", "")).lower():
        raise Refused(f"the brief asks for a {vocal} vocal but style {sid!r} is sung by a "
                      f"{row.get('vocal')} vocal — pick the row that is, or add one")
    for sec in block.get("sections") or []:
        name = section_kind(sec.get("name"))
        if name not in (row.get("section_styles") or {}):
            raise Refused(f"style {sid!r} has no line for a {sec.get('name')!r} section — it has: "
                          f"{' · '.join(row.get('section_styles') or {})}. Add it to the row, never the brief")
    return row


# ------------------------------------------------------------- the request

# THE FLOW (the owner, 2026-10-10: "there's awkward space in the song … I don't
# think you're actually listening to the track … the songs need to flow. That's
# what keeps people captivated"). Measured on 13 songs: 35–90 s of dead air each,
# single gaps up to 22 s, two that sang their first word 12 s in — because every
# section was given more time than its lines need and the music model filled the
# rest with instrumental. Two fixes, both mechanical: a section's length comes
# from its lines and the tempo ("seconds": "fit" or left out), and every take is
# LISTENED to — first word, longest gap, share of dead air — before it is kept.
FLOW_DEFAULTS = {"first_word_s": 1.0, "max_gap_s": 2.0, "dead_air_ratio": 0.05, "ignore_tail_s": 4.0,
                 "beats_per_line": 4, "tail_beats": 1, "shrink": 0.85}


def flow_gates(format_id: str = "song-ad") -> dict:
    """The flow thresholds: the defaults, then providers.json gates.song_flow, then the
    format's PLAYBOOK (formats/playbooks/<format>.json stages.song.flow — the owner
    2026-10-10, one specialised workflow per kind of ad). No playbook → unchanged."""
    try:
        g = (json.loads((HERE / "providers.json").read_text()).get("gates") or {}).get("song_flow") or {}
    except Exception:
        g = {}
    try:
        pbk = _load("playbook").own_setting(format_id, "stages.song.flow") or {}
    except Exception:
        pbk = {}
    return {**FLOW_DEFAULTS, **g, **{k: v for k, v in pbk.items() if k in FLOW_DEFAULTS and v is not None}}


def _playbook_bpl(style_id, format_id: str = "song-ad"):
    """The playbook's pace for a music style row that carries none of its own
    (stages.song.beats_per_line_by_style) — None when there is no playbook or no entry."""
    try:
        return (_load("playbook").own_setting(format_id, "stages.song.beats_per_line_by_style") or {}).get(style_id)
    except Exception:
        return None


def section_kind(name) -> str:
    """'verse 2' and 'Chorus' read as the row's 'verse' and 'chorus' — a numbered
    section is the same kind of section."""
    import re as _re
    return _re.sub(r"\s*\d+$", "", str(name or "").strip().lower())


def fit_seconds(lines: list, bpm, row: dict, name=None) -> float:
    """A section's length from its lines and the tempo: beats_per_line beats a line
    (the style row's own, else the default — a rapped line is about one bar) plus a
    short tail. Never padded; never under the door's 3 s floor."""
    g = flow_gates()
    b = float(bpm or row.get("bpm") or 90)
    bpl = float(row.get("beats_per_line") or _playbook_bpl(row.get("id")) or g["beats_per_line"])
    n = max(1, len([l for l in lines if str(l).strip()]))
    return max(3.0, round((n * bpl + float(g["tail_beats"])) * 60.0 / b, 1))


def flow(transcript: dict, g: dict | None = None) -> dict:
    """Listen to the take: when the first word lands, every gap between words, the
    share of the song that is dead air. {pass, first_word, gaps:[{at, s}], dead_air_s, ratio, problems}."""
    g = {**flow_gates(), **(g or {})}
    W = [w for w in (transcript.get("words") or []) if w.get("type", "word") == "word"
         and w.get("start") is not None and not str(w.get("text", "")).strip().startswith("[")]
    if not W:
        return {"pass": False, "problems": ["no words heard — cannot check the flow"], "gaps": []}
    end = W[-1]["end"]
    gaps = [{"at": round(W[i - 1]["end"], 1), "s": round(W[i]["start"] - W[i - 1]["end"], 1)}
            for i in range(1, len(W)) if W[i]["start"] - W[i - 1]["end"] > g["max_gap_s"]
            and W[i - 1]["end"] < end - g["ignore_tail_s"]]
    dead = round(sum(x["s"] for x in gaps) + max(0.0, W[0]["start"]), 1)
    ratio = round(dead / end, 3) if end else 1.0
    probs = []
    if W[0]["start"] > g["first_word_s"]:
        probs.append(f"the first word lands at {W[0]['start']:.1f} s — open on the punch line (≤ {g['first_word_s']:g} s)")
    if gaps:
        worst = max(gaps, key=lambda x: x["s"])
        probs.append(f"{len(gaps)} gap(s) over {g['max_gap_s']:g} s — worst {worst['s']:g} s at {worst['at']:g} s")
    if ratio > g["dead_air_ratio"]:
        probs.append(f"dead air is {ratio:.0%} of the song (≤ {g['dead_air_ratio']:.0%})")
    return {"pass": not probs, "first_word": round(W[0]["start"], 2), "gaps": gaps, "dead_air_s": dead,
            "ratio": ratio, "problems": probs}


def resolved(block: dict, request: dict) -> dict:
    """The block with every section's seconds as sent ("fit" resolved), so the
    timing and the gate read the same windows the music door was asked for."""
    out = json.loads(json.dumps(block))
    for sec, ch in zip(out.get("sections") or [], request["body"]["composition_plan"]["chunks"]):
        sec["seconds"] = ch["duration_ms"] / 1000
    return out


def shrink_block(block: dict, row: dict, factor: float) -> dict:
    """The same song, every section tighter — for the remake after a take with dead air."""
    out = json.loads(json.dumps(block))
    bpm = block.get("bpm") or row.get("bpm")
    for sec in out.get("sections") or []:
        lines = [l for l in sec.get("lines") or [] if str(l).strip()]
        cur = sec.get("seconds")
        cur = fit_seconds(lines, bpm, row, sec.get("name")) if cur in (None, "", "fit") else float(cur)
        sec["seconds"] = max(3.0, round(cur * factor, 1))
    return out


def build_plan(block: dict, row: dict, limits: dict) -> dict:
    """The composition_plan, mechanically. Nothing in it is chosen here."""
    bpm = block.get("bpm") or row.get("bpm")
    if bpm is not None and not isinstance(bpm, (int, float)):
        raise Refused(f"song.bpm is {bpm!r} — a number, or left out for the style row's own")
    chunks, total = [], 0
    for i, sec in enumerate(block.get("sections") or [], 1):
        lines = [str(l).strip() for l in sec.get("lines") or [] if str(l).strip()]
        sec_s = sec.get("seconds")
        if sec_s in (None, "", "fit"):
            sec_s = fit_seconds(lines, bpm, row, sec.get("name"))
        ms = int(round(float(sec_s) * 1000))
        if not (limits["chunk_ms_min"] <= ms <= limits["chunk_ms_max"]):
            raise Refused(f"song section {i} ({sec.get('name')}) is {ms / 1000:g} s — a section is "
                          f"{limits['chunk_ms_min'] / 1000:g}–{limits['chunk_ms_max'] / 1000:g} s")
        if len(lines) > limits["lines_per_chunk"]:
            raise Refused(f"song section {i} has {len(lines)} lines — at most {limits['lines_per_chunk']}")
        long = next((l for l in lines if len(l) > limits["chars_per_line"]), None)
        if long:
            raise Refused(f"song section {i}'s line {long!r} is over {limits['chars_per_line']} characters")
        styles = list(row.get("positive_styles") or [])
        if bpm is not None:
            styles.append(f"{bpm:g} BPM")
        styles.append(row["section_styles"][section_kind(sec.get("name"))])
        chunks.append({"text": "\n".join(lines), "duration_ms": ms,
                       "positive_styles": styles,
                       "negative_styles": list(row.get("negative_styles") or [])})
        total += ms
    if not chunks:
        raise Refused("the song block has no sections")
    if total > limits["total_ms_max"]:
        raise Refused(f"the song runs {total / 1000:g} s — at most {limits['total_ms_max'] / 1000:g} s")
    return {"chunks": chunks}


def sent_block(block: dict, rows: list | None) -> tuple[dict, list[dict]]:
    """The block with every line as it is SENT: protected words swapped for
    their say_as, figures in words (lexicon.for_model). Returns it and the
    record of what changed, line by line."""
    lx = _load("lexicon")
    out, log = dict(block), []
    secs = []
    for sec in block.get("sections") or []:
        lines = []
        for ln in sec.get("lines") or []:
            sent, said = lx.for_model(str(ln), rows or [])
            lines.append(sent)
            if sent != str(ln):
                log.append({"line": str(ln), "sent": sent, **said})
        secs.append({**sec, "lines": lines})
    out["sections"] = secs
    return out, log


def build_request(block: dict, plan: dict, styles: dict | None = None, seed: int | None = None,
                  rows: list | None = None) -> dict:
    """{method, url, body} — exactly what goes to the music door. `said` (not
    sent) records what the saying step changed."""
    if not isinstance(block, dict) or not block.get("sections"):
        raise Refused("the plan carries no song block with sections — a sung brief (v16) writes "
                      "`song: {style_id, vocal, bpm, sections: [{name, seconds, lines}]}`")
    d = door()
    row = style_row(block, styles if styles is not None else load_styles())
    check_words(block, plan)
    sending, said = sent_block(block, rows)
    comp = build_plan(sending, row, d["limits"])
    if d.get("context_adherence"):
        for c in comp["chunks"]:
            c["context_adherence"] = d["context_adherence"]
    query = "&".join(f"{k}={v}" for k, v in (d.get("query") or {}).items())
    body = {"composition_plan": comp, "model_id": d["model_id"],
            "seed": int(d["seed"] if seed is None else seed)}
    return {"method": d.get("method", "POST"), "url": d["url"] + (f"?{query}" if query else ""), "body": body,
            "said": said}


def seconds_of(request: dict) -> float:
    return sum(c["duration_ms"] for c in request["body"]["composition_plan"]["chunks"]) / 1000


def http_transport(method: str, url: str, headers: dict, body: bytes | None):
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def call_music(request: dict, key: str, transport) -> bytes:
    status, _h, data = transport(request["method"], request["url"],
                                 {"xi-api-key": key, "Content-Type": "application/json"},
                                 json.dumps(request["body"]).encode())   # "said" is the record, never sent
    if status is not None and status >= 400:
        raise RuntimeError(f"ElevenLabs music error {status}: {data[:400]!r}")
    return data


# ------------------------------------------------------------- the gate

def tokens_of(text: str) -> list[str]:
    """A transcriber's words as the script spells them: `[tags]` dropped
    (lineparity.normalize), and every figure said in words by the one number
    table (spoken_numbers) — on the lyric and on what was heard alike, so
    "$29" and "twenty-nine dollars" are the same words."""
    return lp.normalize(lp.say_numbers(re.sub(r"\[[^\]]*\]", " ", text or "")))


def transcribe(song: Path, key: str, transport) -> dict:
    """ElevenLabs speech-to-text on the song — the text AND the word times."""
    boundary = lp._boundary()
    body = lp._multipart_body({"model_id": lp.STT_MODEL_ID, "timestamps_granularity": "word"},
                              [("file", Path(song))], boundary)
    status, _h, data = transport("POST", lp.ELEVEN_STT,
                                 {"xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"},
                                 body)
    doc = json.loads(data.decode()) if data else {}
    if status is not None and status >= 400:
        raise RuntimeError(f"ElevenLabs speech-to-text error {status}: {json.dumps(doc)[:400]}")
    return doc


def timed_tokens(transcript: dict) -> list[dict]:
    """[{w, start, end}] — every heard word as script tokens, each with its time."""
    out = []
    words = [w for w in transcript.get("words") or [] if w.get("type", "word") == "word"]
    if not words:   # a transcript with text and no word list: untimed tokens
        return [{"w": t, "start": None, "end": None} for t in tokens_of(transcript.get("text", ""))]
    for w in words:
        for t in tokens_of(w.get("text", "")):
            out.append({"w": t, "start": w.get("start"), "end": w.get("end")})
    return out


def gate(block: dict, transcript: dict, lex: list | None = None) -> dict:
    """Every section's lines heard, in order; the last line finished; every
    protected word and every figure in the lyrics heard. Returns
    {pass, missing, lines:[{section, line, match, start, end}], sections:[...]}."""
    heard = timed_tokens(transcript)
    got = [t["w"] for t in heard]
    th = threshold()
    cursor, rows, missing = 0, [], None
    for si, sec in enumerate(block.get("sections") or [], 1):
        for ln in sec.get("lines") or []:
            want = tokens_of(ln)
            n = len(want)
            best, at = 0.0, None
            for i in range(cursor, max(cursor, len(got) - max(n - 2, 1)) + 1):
                for m in (n - 1, n, n + 1):
                    if m <= 0:
                        continue
                    r = difflib.SequenceMatcher(None, got[i:i + m], want).ratio()
                    if r > best + 1e-9:
                        best, at = r, (i, m)
                if best >= 0.999:
                    break
            row = {"section": si, "name": sec.get("name"), "line": ln, "match": round(best, 3)}
            if at and best >= th:
                i, m = at
                span = heard[i:i + m]
                row.update({"start": span[0]["start"], "end": span[-1]["end"],
                            "words": [{"w": t["w"], "start": t["start"], "end": t["end"]} for t in span]})
                cursor = i + m
            elif missing is None:
                missing = row
            rows.append(row)
    lines = [l for s in block.get("sections") or [] for l in s.get("lines") or []]
    finished = lp.ending_heard(" ".join(got), lp.say_numbers(lines[-1])) if lines else True
    sections, planned = [], 0.0
    for si, sec in enumerate(block.get("sections") or [], 1):
        mine = [r for r in rows if r["section"] == si and r.get("start") is not None]
        secs = float(sec.get("seconds") or 0)
        sections.append({"section": si, "name": sec.get("name"), "scene": sec.get("scene"),
                         "planned_seconds": sec.get("seconds"),
                         # where the plan put it on the song's clock — the only
                         # time an instrumental section has
                         "planned_start": round(planned, 3), "planned_end": round(planned + secs, 3),
                         "start": mine[0]["start"] if mine else None,
                         "end": mine[-1]["end"] if mine else None})
        planned += secs
    problems = []
    if missing:
        problems.append(f"section {missing['section']} ({missing['name']}): the line {missing['line']!r} "
                        f"is not heard (best match {missing['match']})")
    if not finished:
        problems.append(f"the last line does not finish: {lines[-1]!r}")
    lx = _load("lexicon")
    heard_text = transcript.get("text", "") or " ".join(w.get("text", "") for w in transcript.get("words") or [])
    lyric = "\n".join(str(l) for l in lines)
    protected = lx.heard_check(lyric, heard_text, lex or [], lx.threshold_of())
    for p in protected:
        if not p["heard_ok"]:
            problems.append(f"protected word not heard: {p['term']!r} (sent as {p['say_as']!r}, best match {p['match']})")
    figures = _load("spoken_numbers").figures_heard(lyric, heard_text)
    for f in figures:
        if not f["heard_ok"]:
            problems.append(f"number not heard as said: {f['figure']!r} should be {f['said']!r}")
    return {"pass": not problems, "problems": problems, "finished": finished,
            "heard": transcript.get("text", ""), "lines": rows, "sections": sections,
            "protected": protected, "numbers": figures,
            "unconfirmed": lx.unconfirmed_in(lyric, lex or []), "at": now()}


# ----------------------------------------------------------------- level

def level_copy(song: Path, target: float = TARGET_LUFS) -> Path | None:
    """A levelled COPY at −14 LUFS; the original is never touched."""
    dest = song.with_name("song-14lufs.mp3")
    shutil.copyfile(song, dest)
    ok = _load("voice").level_slice(dest, target)
    return dest if ok else None


# ------------------------------------------------------------------ the run

def plan_of(run: Path) -> dict:
    plan = read_json(run / "plan.json")
    if plan is None:
        raise Refused(f"no plan.json in {run}")
    return plan


def make(run: Path, plan: dict | None = None, dry_run: bool = False, transport=None,
         stt_transport=None, key: str | None = None, styles: dict | None = None,
         level: bool = True) -> dict:
    """The whole chain. Returns the song record (also written to song/song.json).
    A refusal is a `Refused` (SystemExit) naming what is wrong."""
    plan = plan if plan is not None else plan_of(run)
    block = plan.get("song") or {}
    d = door()
    lx = _load("lexicon")
    lex = lx.load(plan.get("brand")) if plan.get("brand") else lx.for_run(run)
    request = build_request(block, plan, styles=styles, rows=lex)
    block = resolved(block, request)
    sd = run / "song"
    write_json(sd / "request.json", request)
    secs = seconds_of(request)
    rate = usd_per_second(request["body"]["model_id"])
    est = round(secs * rate, 4) if rate else None
    record = {"model_id": request["body"]["model_id"], "style_id": block.get("style_id"),
              "seconds": secs, "usd_estimate_per_take": est, "request": "song/request.json",
              "said": request.get("said") or [], "takes": []}
    if dry_run:
        print(f"song (dry run): {len(request['body']['composition_plan']['chunks'])} section(s), "
              f"{secs:g} s on {record['model_id']}, seed {request['body']['seed']} — "
              f"≈ ${est} a take; request written to {sd / 'request.json'}, nothing spent")
        record["dry_run"] = True
        return {**record, "pass": True}

    k = key if key is not None else lp.key_of()
    if not k:
        raise Refused("no ELEVENLABS_API_KEY — in the environment or the Keychain vault")
    transport = transport or http_transport
    stt_transport = stt_transport or http_transport
    pre = _load("preflight")
    song = sd / "song.mp3"
    seed0 = int(d["seed"])
    result = None
    for attempt in (1, 2):
        if attempt == 2 and result and result.get("flow_failed"):
            block = shrink_block(block, style_row(block, styles if styles is not None else load_styles()),
                                 float(flow_gates()["shrink"]))
            req = build_request(block, plan, styles=styles, seed=seed0, rows=lex)
            block = resolved(block, req)
        else:
            req = request if attempt == 1 else build_request(block, plan, styles=styles, seed=seed0 + 1, rows=lex)
        if attempt == 2:
            write_json(sd / "request-remake.json", req)
        if song.exists():
            arch = sd / "versions"
            arch.mkdir(parents=True, exist_ok=True)
            n = 1
            while (arch / f"song-v{n}.mp3").exists():
                n += 1
            song.rename(arch / f"song-v{n}.mp3")
        song.write_bytes(call_music(req, k, transport))
        try:
            pre.ledger(run, req["body"]["model_id"], f"SONG-take{attempt}", secs, "done",
                       brand=plan.get("brand"), shot="SONG")
        except SystemExit:
            pass
        transcript = transcribe(song, k, stt_transport)
        write_json(sd / "transcript.json", transcript)
        result = gate(block, transcript, lex)
        fl = flow(transcript)
        if not fl["pass"]:
            result["pass"] = False
            result["problems"] = list(result["problems"]) + fl["problems"]
            result["flow_failed"] = result.get("problems") and not any(
                p for p in result["problems"] if p not in fl["problems"])
        result["flow"] = fl
        record["takes"].append({"take": attempt, "seed": req["body"]["seed"], "at": now(), "flow": fl,
                                "pass": result["pass"], "problems": result["problems"],
                                "heard": result["heard"]})
        if result["pass"]:
            break
    record["pass"] = result["pass"]
    record["problems"] = result["problems"]
    if result.get("unconfirmed"):
        record["warnings"] = [f"not yet confirmed by ear: {', '.join(result['unconfirmed'])}"]
    timing = {"song": "song/song.mp3", "model_id": record["model_id"],
              "seconds_planned": secs, "sections": result["sections"], "lines": result["lines"],
              "at": now()}
    write_json(sd / "timing.json", timing)
    if result["pass"] and level:
        lv = level_copy(song)
        record["levelled"] = str(lv.relative_to(run)) if lv else None
    pre.verdict(run, "SONG", "song", {"verdict": "PASS" if result["pass"] else "FAIL",
                                      "problems": result["problems"], "takes": len(record["takes"])})
    write_json(sd / "song.json", {**record, "at": now()})
    return record


def report(rec: dict) -> None:
    if rec.get("dry_run"):
        return
    tag = "PASS" if rec["pass"] else "STOP"
    extra = " (made twice)" if len(rec.get("takes") or []) > 1 else ""
    print(f"{tag}  song{extra} · {rec['seconds']:g} s on {rec['model_id']}"
          + ("" if rec["pass"] else f" — {'; '.join(rec['problems'])}"))
    for w in rec.get("warnings") or []:
        print(f"WARN  {w}")


def plan_from_spec(spec: dict) -> dict:
    """A song ad written as a song spec (title, brand, style_id, bpm, sections of
    lines; SONG-WRITING.md) as the plan make() takes: one scene per line, sung."""
    sections = [{"name": x["name"], "seconds": x.get("seconds", "fit"), "lines": list(x["lines"])}
                for x in spec["sections"]]
    scenes = [{"id": f"L{i}", "kind": "broll", "to_camera": False, "voice": "", "lyrics": [ln]}
              for i, ln in enumerate((l for x in sections for l in x["lines"]), 1)]
    return {"brand": spec.get("brand"), "song": {"style_id": spec["style_id"], "vocal": spec.get("vocal"),
            "bpm": spec.get("bpm"), "sections": sections}, "scenes": scenes}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--spec", help="a song spec (SONG-WRITING.md); its plan is written into the run first")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    run = Path(a.run).resolve()
    if a.spec:
        run.mkdir(parents=True, exist_ok=True)
        pl = run / "plan.json"
        if not pl.exists():
            write_json(pl, plan_from_spec(json.loads(Path(a.spec).read_text())))
    if not run.is_dir():
        print(f"no such run: {run}", file=sys.stderr)
        return 3
    try:
        rec = make(run, dry_run=a.dry_run)
    except SystemExit as e:
        print(f"REFUSED {e}", file=sys.stderr)
        return 2
    report(rec)
    return 0 if rec["pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
