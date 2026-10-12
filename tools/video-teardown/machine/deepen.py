"""DEEPEN THE RECORD — focused passes over the same video (2026-09-24).

the owner, reading a teardown record with one-line visuals, "Music: none" and two
doctors where there were three: "the more detail that we can extract from all
of these assets, the better our reference-to-generation quality comes out …
the teardown record should be that in all of its glory."

One call asked to write the whole record goes shallow somewhere — measured on
the Mara swipe: a median of 20–30 words a shot on the strongest model, twice.
So the record is written first (stage 1, the structure), then each part that
generation depends on is re-read from the video in a pass of its own, and
written back into the record:

    VISUALS  every shot of the shot table, as a scene prompt (who, doing, face,
             frame, camera, light, place, props) — 50–120 words each
    PEOPLE   the CAST, PLACES and PROPS sections at casting-sheet / set-sheet
             depth — every person who speaks or appears, even as a hand
    MUSIC    the music, described as a composer would be briefed

Every pass is handed the machine transcript (who speaks, when, every word) and
watches the video at 2 frames a second. Brand-agnostic: it reads only the run's
own video, transcript and record.

    python3 deepen.py <run dir>
"""
import importlib.util, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = os.environ.get("DEEPEN_MODEL", "gemini-3.1-pro-preview")


def _tools():
    sp = importlib.util.spec_from_file_location("gemini_breakdown", HERE.parent / "tools" / "gemini_breakdown.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def ask(video, prompt, want_json=False):
    g = _tools()
    k = g.key()
    uri, mime = g.upload_cached(k, Path(video))
    gen = {"temperature": 0.2, "maxOutputTokens": 65536}
    if want_json:
        gen["responseMimeType"] = "application/json"
    part = {"file_data": {"file_uri": uri, "mime_type": mime}}
    if mime.startswith("video"):  # an audio file (the isolated music) takes no frame rate
        part["video_metadata"] = {"fps": float(os.environ.get("GEMINI_VIDEO_FPS", "2"))}
    body = {"contents": [{"parts": [part, {"text": prompt}]}], "generationConfig": gen}
    last = ""
    for _ in range(3):
        try:
            r = g.req(f"{g.BASE}/v1beta/models/{MODEL}:generateContent?key={k}",
                      data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
            return json.loads(re.search(r"[\[{].*[\]}]", text, re.S).group(0)) if want_json else text.strip()
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:200]}"
    raise RuntimeError(f"deepen pass failed — {last}")


def _table(record):
    lines = record.split("\n")
    hi = next(i for i, l in enumerate(lines) if l.startswith("|") and "Visuals" in l and "Timestamp" in l)
    cols = [c.strip() for c in lines[hi].strip().strip("|").split("|")]
    rows = []
    j = hi + 1
    while j < len(lines) and lines[j].startswith("|"):
        c = [x.strip() for x in lines[j].strip().strip("|").split("|")]
        if len(c) >= len(cols) and re.match(r"\d+:\d+", c[0]):
            rows.append((j, c))
        j += 1
    return lines, cols, rows


_TS_KEYS = ("timestamp", "time", "ts", "shot")


def _shot_text(v):
    """The visuals for one shot, however the model shaped it: a string, or the
    labeled clauses (Who / Doing / Face …) returned as their own fields."""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        for want in ("visuals", "visual", "description", "scene", "prompt", "text"):
            for k, x in v.items():
                if str(k).strip().lower() == want and isinstance(x, str):
                    return x.strip()
        return " / ".join(f"{k}: {x.strip()}" for k, x in v.items()
                          if isinstance(x, str) and str(k).strip().lower() not in _TS_KEYS).strip()
    return ""


def _shots(got, stamps):
    """ONE ANSWER SHAPE MUST NOT COST THE SHOTS (2026-09-25): the pass asks for
    {timestamp: visuals}, but a JSON-mode model also answers with a bare array,
    an array of {timestamp, visuals} objects, or either wrapped in a single key
    — and `dict.update()` on a list of strings raised "dictionary update
    sequence element #0 has length 1; 2 is required", which killed the whole
    visuals leg and left every shot with its stage-1 one-liner.

    Whatever came back, return {timestamp: visuals}. An array carries no keys,
    so it is paired back to the timestamps of the chunk that was asked for, in
    the order they were asked for."""
    if isinstance(got, dict):
        if len(got) == 1:                          # {"shots": [...]} / {"visuals": "…"}
            k, inner = next(iter(got.items()))
            if not re.match(r"\d+:\d+", str(k).strip()) and (
                    isinstance(inner, (list, dict)) or (isinstance(inner, str) and len(stamps) == 1)):
                return _shots(inner, stamps)
        out = {}
        for k, v in got.items():
            t = _shot_text(v)
            if t:
                out[str(k).strip()] = t
        return out
    if isinstance(got, list):
        out = {}
        for i, item in enumerate(got):
            ts = ""
            if isinstance(item, dict):
                for k, v in item.items():
                    if str(k).strip().lower() in _TS_KEYS and isinstance(v, str):
                        ts = v.strip()
                        break
            t = _shot_text(item)
            if not t:
                continue
            if ts not in stamps:                   # unnamed, or named in its own words
                ts = stamps[i] if i < len(stamps) else ts
            if ts:
                out[str(ts)] = t
        return out
    if isinstance(got, str) and len(stamps) == 1:  # one shot asked for, one answer back
        return {stamps[0]: got.strip()}
    return {}


def visuals_pass(video, record, transcript_md):
    lines, cols, rows = _table(record)
    vi, ti = cols.index("Visuals"), cols.index("Timestamp")
    shots = [c[ti] for _, c in rows]
    cast = re.search(r"\*\*CAST\*\*(.*?)(?=\*\*PROPS\*\*|\*\*2\.)", record, re.S)
    prompt = f"""Watch this video closely. For EACH of these shots (timestamps), write what is on screen as a
scene-generation prompt, 50–120 words, as short labeled clauses in this order:
Who: (the person by the name below, and the outfit they wear in this shot) · Doing: the action, hands included ·
Face: expression, and where they look · Frame: shot size, and where each person sits in the frame (left/centre/right,
how much of the height) · Camera: who holds it (handheld selfie / propped / another person / mirror), front or rear
camera, height and angle, distance, movement, phone-grade or high-res · Light: source, direction, quality, colour ·
Place: the location and what of it is visible behind them · Props: what is in frame.
Only what you can see; write [UNCLEAR] rather than guess. A person who is only a hand or an arm in frame is still named.

The people and places, as named in the record (use these names):
{cast.group(1)[:6000] if cast else '(none named)'}

The machine transcript (who speaks, when):
{transcript_md}

The shots: {json.dumps(shots)}

Answer with ONE JSON object: {{"<timestamp exactly as given>": "<the visuals for that shot>", ...}} — every shot."""
    got, failed = {}, []
    for i in range(0, len(shots), 4):       # four shots a call: a long answer gets cut off
        chunk = shots[i:i + 4]
        part = prompt.replace(f"The shots: {json.dumps(shots)}", f"The shots: {json.dumps(chunk)}")
        try:
            got.update(_shots(ask(video, part, want_json=True), chunk))
        except Exception as e:
            # one chunk the model answers unusably costs its four shots, never the rest
            failed.append(f"{chunk[0]}: {type(e).__name__}: {str(e)[:80]}")
    # the timestamp may come back spaced or trimmed differently than the table writes it
    loose = {}
    for k, v in got.items():
        loose.setdefault(re.sub(r"\s+", "", k), v)
        m = re.match(r"\d+:\d+", k)
        if m:
            loose.setdefault(m.group(0), v)
    done = 0
    for j, c in rows:
        m = re.match(r"\d+:\d+", c[ti])
        v = got.get(c[ti]) or loose.get(re.sub(r"\s+", "", c[ti])) or (loose.get(m.group(0)) if m else None)
        if v and len(v.split()) > len(c[vi].split()):
            c[vi] = v.replace("|", "/").replace("\n", " ")
            lines[j] = "| " + " | ".join(c) + " |"
            done += 1
    return "\n".join(lines), done, len(rows), failed


def people_pass(video, record, transcript_md):
    m = re.search(r"(\*\*CAST\*\*.*?)(?=\n\|\s*Timestamp|\nThen give me|\n`?Timestamp)", record, re.S)
    if not m:
        return record, False
    # held out of the f-string below: a backslash inside one is a syntax error
    # before Python 3.12, and this machine has to parse on the stock 3.9 too
    named = ", ".join(re.findall(r"^\*\*([^*]+)\*\*\s*$", m.group(1), re.M))
    prompt = f"""Watch this video closely and write three sections, at the depth of a film production's
casting sheet and set sheet — every person and place here will be rebuilt from your words.

**CAST** — one sheet per person who appears or speaks. The transcript below says how many voices there are and
when each speaks; every speaking voice is a person in the CAST, even if on screen they are only a hand or an arm.
For each, labeled lines: Role and screen time (on-screen and speaking timestamps) · Age (one bracket) · Face (shape;
eyes — colour, shape, lids; brows; nose; lips; jaw and chin; skin tone and undertone; skin texture — pores, lines,
spots, freckles, where; marks; glasses) · Hair (colour and greys, length, texture, style, parting) · Body (build,
height relative to others or the room, posture) · Makeup · Wardrobe, per outfit with timestamps (every garment:
colour, material, pattern, fit, neckline; shoes if seen; every piece of jewellery with metal and style) · Hands
(skin, nails, rings — hands are often all we see) · Voice (pitch, accent, pace, timbre, volume, laugh, tics — from the
audio) · Movement and manner (gestures, expressions, eyeline, how they relate to the camera) · Relation to others.

**PLACES** — one sheet per location: What it is (as it really appears) · Layout relative to camera · Surfaces
(walls, floor, ceiling — colour, material, pattern) · Fixtures and furniture (each, with colour and material) ·
Light (every source, direction, hardness, colour temperature; time of day outside) · Dressing (everything on
shelves, counters, walls; signage verbatim) · Room sound · Timestamps.

**PROPS** — every object handled or featured: what it is, colour, material, size against a hand, brand if shown,
who holds it and when.

Only what you can see and hear; mark [UNCLEAR] rather than guess, and (inferred) where you infer.
Keep the names the record already uses where they fit: {named}

The machine transcript:
{transcript_md}

Start with **CAST**. Nothing before it, nothing after PROPS."""
    got = ask(video, prompt)
    if "**CAST**" not in got:
        return record, False
    return record.replace(m.group(1), got.strip() + "\n\n"), True


def music_pass(video, record, desc=None):
    prompt = """Listen to this video's audio. Describe the music under it as someone briefing a composer:
genre and sub-genre; the instruments you can hear; vocals or none; the feel (bright/dark, key feel); the era or
reference; how it is built (intro, loop, drop); how it sits under the voice (ducked, loud, gone during speech);
where it starts, stops or changes (timestamps). Name the track only if you can identify it; otherwise name two real
tracks it sounds like, marked (sounds like). If there is truly no music, say so and describe any other sound bed.
One paragraph, no heading."""
    got = desc if desc is not None else ask(video, prompt)
    desc = got.replace("\\", "").replace("\n", " ")
    # the label may come back plain, **bold** or `code`
    new, n = re.subn(r"^[`*]*Music, described:?[`*]*:?.*$", lambda m: "**Music, described:** " + desc, record, count=1, flags=re.M)
    if not n:
        new, n = re.subn(r"^([`*]*Music:?[`*]*:?.*)$", lambda m: m.group(1) + "\n\n**Music, described:** " + desc, record, count=1, flags=re.M)
    if not n:
        raise RuntimeError("no Music line in the record to describe")
    return new


def transcript_check_pass(video, run_dir):
    """THE TRANSCRIPT, CHECKED (2026-09-25): speech-to-text heard "And finally"
    as "Vinyl" and the rewrite carried the nonsense line. The video is watched
    against the machine transcript — its burned-in captions and its audio —
    and every misheard line is corrected in transcript.json, marked with what
    was heard and what the video shows."""
    d = Path(run_dir)
    tj = d / "transcript.json"
    if not tj.exists():
        return []
    lines = json.loads(tj.read_text())
    listing = "\n".join(f"{l['id']} · {l['start']:.1f}s · {l['speaker']}: {l['text']}" for l in lines)
    prompt = f"""Watch and listen to this video. Below is a machine transcript of its audio, one numbered line per
speaker turn. Speech-to-text mishears words — names, quick words, words under music. Check every line against what
is actually said and against any captions burned into the video. List ONLY the lines that are wrong.

{listing}

Answer with ONE JSON object: {{"corrections": [{{"id": "T15", "heard": "<the wrong words>", "correct": "<the right words>",
"evidence": "<the caption text on screen, or what is clearly audible>"}}]}} — an empty list if every line is right."""
    got = ask(video, prompt, want_json=True)
    # the same answer-shape tolerance as the visuals: the corrections may come
    # back bare, or under a key of the model's own choosing
    if isinstance(got, dict):
        corrections = got.get("corrections")
        if corrections is None:
            corrections = next((v for v in got.values() if isinstance(v, list)), [])
    else:
        corrections = got
    fixed = []
    by = {l["id"]: l for l in lines}
    for c in (corrections if isinstance(corrections, list) else []):
        if not isinstance(c, dict):
            continue
        l = by.get(c.get("id"))
        if not l or not c.get("heard") or not c.get("correct") or c["heard"] not in l["text"]:
            continue
        l["text"] = l["text"].replace(c["heard"], c["correct"], 1) + \
            f" (corrected: speech-to-text heard \"{c['heard']}\"; the video: {str(c.get('evidence', ''))[:80]})"
        fixed.append(c)
    if fixed:
        tj.write_text(json.dumps(lines, indent=1, ensure_ascii=False) + "\n")
    return fixed


def deepen(run_dir):
    d = Path(run_dir)
    video = d / "source.mp4"
    td = d / "stages" / "1-teardown.md"
    text = td.read_text()
    mark = "### VERBATIM TRANSCRIPT"
    record, tail = (text.split(mark, 1) + [""])[:2]
    tail = (mark + tail) if tail else ""
    tj = d / "transcript.json"
    tr_md = ""
    if tj.exists():
        sp = importlib.util.spec_from_file_location("transcript", HERE / "transcript.py")
        t = importlib.util.module_from_spec(sp); sp.loader.exec_module(t)
        tr_md = t.render(json.loads(tj.read_text()))
    # The voice cards (audio teardown, 2026-09-25): each person's accent, age by
    # ear, pitch and delivery, heard from their own clip with the music removed —
    # so the cast sheet's Voice line is written from the voice, not the mix.
    ss = d / "sound-sheet.md"
    if ss.exists() and "### VOICES" in ss.read_text():
        sheet = ss.read_text()
        tr_md += "\n" + sheet[sheet.index("### VOICES"):]
    res = {"people": False, "visuals": "0/0", "music": False, "errors": []}
    # Each pass stands alone: one that fails leaves the others' work in place.
    try:
        record, res["people"] = people_pass(video, record, tr_md)
    except Exception as e:
        res["errors"].append(f"people: {str(e)[:120]}")
    try:
        record, done, total, failed = visuals_pass(video, record, tr_md)
        res["visuals"] = f"{done}/{total}"
        if failed:
            res["errors"].append(f"visuals: {len(failed)} chunk(s) skipped — " + "; ".join(failed[:2]))
    except Exception as e:
        res["errors"].append(f"visuals: {str(e)[:120]}")
    try:
        # Split the music from the speech and NAME it (music.py); describe the
        # isolated track. Falls back to reading the full mix if that can't run.
        try:
            sp = importlib.util.spec_from_file_location("music", HERE / "music.py")
            mu = importlib.util.module_from_spec(sp); sp.loader.exec_module(mu)
            m = mu.identify(d)
            song = m.get("song")
            named = (f"IDENTIFIED — \"{song['title']}\" by {song['artist']}" + (f" ({song['link']})" if song.get("link") else "") + ". "
                     if song else f"Not identified ({m.get('how')}). ")
            record = music_pass(video, record, desc=named + "From the music isolated from the speech: " + str(m.get("described") or ""))
            res["music_named"] = bool(song)
        except Exception as e0:
            res["errors"].append(f"music split: {str(e0)[:100]} — described from the full mix instead")
            record = music_pass(video, record)
        res["music"] = True
    except Exception as e:
        res["errors"].append(f"music: {str(e)[:120]}")
    td.write_text(record.rstrip() + "\n\n" + tail if tail else record)
    return res


if __name__ == "__main__":
    print(deepen(sys.argv[1]))
