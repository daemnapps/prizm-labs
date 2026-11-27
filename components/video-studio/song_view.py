"""The song of a sung ad, read for the pages: the brief's song block joined to the song file and its clock.

A sung brief carries a `song` block (style_id, vocal, bpm, sections[{name, scene, seconds, lines}]) and its scenes
carry `lyrics` (components/video-writing/prompts/stage-5-brief/ai-lane, the "song" field). song.py makes the song
into the production run: `<run>/song/song.mp3`, `timing.json` (every section and line on the song's clock) and
`song.json` (the gate's verdict). This file reads those and nothing else; it never writes a lyric or a time.

    view(brief, run_dir)  -> the song card and each scene's place on the song, or {"sung": False}
    scene_times(order, v) -> each scene's window on the song; unsung scenes between two sung ones share the gap

The idea decides it is a song ad: its song run is `runs/video-production/<brand>/<writing run>` (run.json
`brief_from` names the writing run) or, for a song written from the idea's spoken brief (SONG-WRITING.md, song.py
--spec), `runs/video-production/<brand>/<writing run>-song`. Either run's plan.json `song` block is the song; a
writing brief that is itself sung counts too. Every other ad is not a song ad and shows nothing.
"""
import json
import re
from pathlib import Path

KINDS = (("pre-chorus", "pre"), ("prechorus", "pre"), ("chorus", "chorus"), ("hook", "chorus"), ("refrain", "chorus"),
         ("verse", "verse"), ("bridge", "bridge"), ("turn", "bridge"), ("break", "break"), ("intro", "intro"),
         ("punch", "intro"), ("outro", "outro"), ("end", "outro"))


SUNG_WORDS_PER_SECOND = 2.0   # a page's planned length for a "fit" section, shown as planned; the song's clock replaces it


def kind(name):
    """A section's family by its name: 'chorus 2' and 'final hook' are choruses, 'the turn' is a bridge."""
    low = str(name or "").lower()
    return next((k for word, k in KINDS if word in low), "other")


def _key(line):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", str(line or "").lower())).strip()


def _json(p):
    try:
        d = json.loads(Path(p).read_text())
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def sung(brief):
    """True when the brief is sung: a song block with sections."""
    return bool(isinstance(brief, dict) and isinstance(brief.get("song"), dict) and (brief["song"].get("sections") or []))


def brief_of(writing_run):
    """The writing run's structured brief (the one json block with scenes in its stage-5 file), or None."""
    run = Path(writing_run)
    rec = _json(run / "run.json") or {}
    out = ((rec.get("stages") or {}).get("stage5") or {}).get("out") or "stages/5-brief.md"
    p = (run / out).resolve()
    if not p.is_relative_to(run.resolve()) or not p.is_file():
        return None
    found = []
    for block in re.findall(r"^```(?:json)?[ \t]*\r?\n(.*?)^```[ \t]*$", p.read_text(), re.M | re.S):
        try:
            d = json.loads(block)
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("scenes"), list):
            found.append(d)
    return found[0] if len(found) == 1 else None


def production_run(runs_root, brand, writing_slug):
    """Where song.py makes this idea's song: the run named after the writing run, or its `-song` run when only that
    one carries a song (the plan song.py prints from, or a song folder)."""
    if not brand or not writing_slug or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", str(writing_slug)) \
            or not re.fullmatch(r"[a-z0-9-]+", str(brand)):
        return None
    base = Path(runs_root) / "video-production" / brand
    for run in (base / writing_slug, base / (writing_slug + "-song")):
        if sung(_json(run / "plan.json")) or (run / "song" / "song.mp3").is_file():
            return run
    return base / writing_slug


def song_block(brief, run_dir=None):
    """The idea's song: the song run's plan (what song.py sings) first, else the writing brief's own song block."""
    plan = _json(Path(run_dir) / "plan.json") if run_dir else None
    if sung(plan):
        return plan["song"]
    return brief["song"] if sung(brief) else None


def view(brief, run_dir=None):
    """The song card for the pages. Times are the song's own (timing.json); before a song exists, the plan's
    `seconds` laid end to end, marked planned."""
    brief = brief if isinstance(brief, dict) else {}
    block = song_block(brief, run_dir)
    if not block:
        return {"sung": False}
    sd = Path(run_dir) / "song" if run_dir else None
    timing = (_json(sd / "timing.json") if sd else None) or {}
    record = (_json(sd / "song.json") if sd else None) or {}
    has_song = bool(sd and (sd / "song.mp3").is_file())
    heard = {int(s.get("section") or 0): s for s in timing.get("sections") or [] if isinstance(s, dict)}
    lines_of = {}
    for ln in timing.get("lines") or []:
        lines_of.setdefault(int(ln.get("section") or 0), []).append(ln)
    sections, clock = [], 0.0
    for i, sec in enumerate(block.get("sections") or [], 1):
        planned = float(sec.get("seconds")) if isinstance(sec.get("seconds"), (int, float)) else None
        if planned is None:                       # "fit": the song sets it; until then, its words at a sung pace
            words = sum(len(str(x).split()) for x in sec.get("lines") or [])
            planned = round(max(3.0, words / SUNG_WORDS_PER_SECOND), 1)
        h = heard.get(i) if has_song else None
        start = h.get("start") if h else None
        end = h.get("end") if h else None
        timed = start is not None and end is not None
        if not timed:
            start, end = clock, clock + (planned or 0.0)
        clock = max(clock, end)
        sections.append({"n": i, "name": sec.get("name") or "", "kind": kind(sec.get("name")), "scene": sec.get("scene"),
                         "seconds": planned, "lines": list(sec.get("lines") or []), "start": round(start, 2),
                         "end": round(end, 2), "timed": timed,
                         "line_times": [{"line": ln.get("line"), "start": ln.get("start"), "end": ln.get("end")}
                                        for ln in (lines_of.get(i) or []) if has_song]})
    scenes = {}
    for sc in brief.get("scenes") or []:
        sid = sc.get("id")
        lyr = [str(x) for x in (sc.get("lyrics") or []) if str(x).strip()]
        own = [s for s in sections if s["scene"] == sid]
        if not own and lyr:                       # a section with no scene id: the one that sings this scene's lines
            want = {_key(x) for x in lyr}
            own = [s for s in sections if want & {_key(x) for x in s["lines"]}][:1]
        if not sid or not (own or lyr):
            continue
        scenes[sid] = {"lyrics": lyr, "section": own[0]["name"] if own else None,
                       "kind": own[0]["kind"] if own else None,
                       "start": min(s["start"] for s in own) if own else None,
                       "end": max(s["end"] for s in own) if own else None,
                       "timed": bool(own) and all(s["timed"] for s in own)}
    gate = record.get("pass") if has_song else None
    return {"sung": True, "style_id": block.get("style_id"), "vocal": block.get("vocal"), "bpm": block.get("bpm"),
            "sections": sections, "scenes": scenes, "seconds": round(max([s["end"] for s in sections] or [0]), 2),
            "song": {"made": has_song, "timed": bool(timing.get("sections")) and has_song, "heard": gate,
                     "problems": list(record.get("problems") or []) if has_song else [],
                     "file": "song/song.mp3" if has_song else None}}


def scene_times(order, v):
    """Each scene in `order` placed on the song: a sung scene takes its section's window; unsung scenes before or
    between sung ones share that gap evenly; scenes after the last sung one have no place (None)."""
    out = {s: None for s in order}
    if not v.get("sung"):
        return out
    anchors = [(i, v["scenes"][s]) for i, s in enumerate(order) if (v["scenes"].get(s) or {}).get("start") is not None]
    for i, a in anchors:
        out[order[i]] = {"start": a["start"], "end": a["end"], "section": a["section"], "kind": a["kind"], "sung": True}
    prev_i, prev_end = -1, 0.0
    for i, a in anchors:
        gap = list(range(prev_i + 1, i))
        if gap and a["start"] > prev_end:
            step = (a["start"] - prev_end) / len(gap)
            for k, j in enumerate(gap):
                out[order[j]] = {"start": round(prev_end + k * step, 2), "end": round(prev_end + (k + 1) * step, 2),
                                 "section": None, "kind": None, "sung": False}
        prev_i, prev_end = i, max(prev_end, a["end"])
    return out
