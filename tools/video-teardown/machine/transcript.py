"""THE VERBATIM TRANSCRIPT — every word of the swipe, every speaker (2026-09-24).

the owner, after a rewrite kept a handful of fragments of a swipe whose whole
power was its back-and-forth: "All that dialogue and back-and-forth with the
creator and the doctor, that's literally what makes this thing real and work,
and we're missing all of it."

The teardown model writes a shot table with one fragment of speech per row
("So fat grafting...") — every stage after it only ever saw the fragments.
This is not a model's reading: it is the audio transcribed word for word
(ElevenLabs speech-to-text, speakers separated), cut into LINES — one line per
speaker turn — numbered T1, T2, … with their start time. It is appended to the
teardown record, so every later stage gets the whole script, and the stage-3
line check holds the injection to one line of ours per line of theirs.

Speaker separation is audio-only: two people with similar voices can share a
label. The transcript says so; the teardown's shot table says who is on screen.

    python3 transcript.py <run dir>        writes stages/1-transcript.md and
                                           appends it to stages/1-teardown.md
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

STT = "https://api.elevenlabs.io/v1/speech-to-text"
MARK = "### VERBATIM TRANSCRIPT"



def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod


def _key():
    return _shared_keys().lookup("ELEVENLABS_API_KEY")


# THE AUDIO TEARDOWN (2026-09-25). Scribe alone dropped a Korean mother's lines
# as "[laughs]" and, on a second run, translated her into English without a
# word. The words now come from components/audio-teardown: the voices split off
# the music, Gemini writing every word in the language it was said, Scribe v2
# saying who spoke when, and one voice card per person. It runs as its own
# process (its module names would collide with this folder's), into a cache
# keyed by the video's content, so the transcript before the read and the one
# attached after it are the same run. If it fails, the old Scribe-only path
# runs and says so. Off: VT_NO_AUDIO_TEARDOWN=1.
AUDIO_TEARDOWN = Path(__file__).resolve().parents[3] / "components" / "audio-teardown" / "run.py"
AUDIO_CACHE = Path(__file__).resolve().parent / ".tmp" / "audio-teardown"


def _fingerprint(video):
    v = Path(video)
    with open(v, "rb") as f:
        head = f.read(1 << 20)
    return hashlib.sha1(head + str(v.stat().st_size).encode()).hexdigest()[:16]


def audio_teardown(video):
    """The audio teardown's folder for this video (run once, then reused), or None."""
    if os.environ.get("VT_NO_AUDIO_TEARDOWN") or not AUDIO_TEARDOWN.exists():
        return None
    out = AUDIO_CACHE / _fingerprint(video)
    reuse = False
    if (out / "transcript.json").exists() and (out / "sound-sheet.json").exists():
        if "mix" in json.loads((out / "sound-sheet.json").read_text()):
            return out
        reuse = True        # made before music, effects and the mix existed — add only those
    r = subprocess.run([sys.executable, str(AUDIO_TEARDOWN), str(video), "--out", str(out)] + (["--reuse"] if reuse else []),
                       capture_output=True, text=True, timeout=1800)
    if r.returncode or not (out / "transcript.json").exists():
        print(f"      audio teardown could not run — Scribe only: {(r.stderr or r.stdout)[-200:]}", flush=True)
        return None
    print(f"      audio teardown: {r.stdout.strip().splitlines()[0][:200]}", flush=True)
    return out


def transcribe(video):
    at = audio_teardown(video)
    if at:
        return {"_lines": json.loads((at / "transcript.json").read_text()), "_audio": str(at)}
    return scribe_only(video)


def scribe_only(video):
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "a.mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vn", "-ac", "1",
                        "-ar", "16000", "-b:a", "64k", str(a)], check=True)
        r = subprocess.run(["curl", "-sS", "--max-time", "300", "-H", f"xi-api-key: {_key()}",
                            "-F", "model_id=scribe_v1", "-F", "diarize=true",
                            "-F", "timestamps_granularity=word", "-F", f"file=@{a}", STT],
                           capture_output=True, text=True)
    d = json.loads(r.stdout)
    if "words" not in d:
        raise RuntimeError(f"speech-to-text failed: {r.stdout[:300]}")
    return d


def lines_of(d, gap=1.2, long=6.0):
    """One line per speaker turn: a new line whenever the speaker changes or
    they pause longer than `gap` seconds — and, inside a turn that has run
    `long` seconds or more, at the next sentence end, so a one-person
    monologue becomes lines, not one block. Short dialogue turns stay whole.
    Sound tags ([laughs], [music]) stay."""
    if "_lines" in d:                      # the audio teardown already made the lines
        return d["_lines"]
    out, cur = [], None
    for w in d["words"]:
        if w.get("type") not in ("word", "audio_event"):
            if cur:
                cur["text"] += w.get("text", "")
            continue
        sp = w.get("speaker_id") or "speaker_0"
        ended = bool(cur) and re.search(r"(?<!\bDr)(?<!\bMr)(?<!\bMrs)(?<!\bMs)[.?!]\W*$", cur["text"].strip()) \
            and (cur["end"] - cur["start"]) >= long
        if not cur or sp != cur["speaker"] or w["start"] - cur["end"] > gap or ended:
            cur = {"speaker": sp, "start": w["start"], "end": w["end"], "text": w.get("text", "")}
            out.append(cur)
        else:
            cur["text"] += w.get("text", "")
            cur["end"] = w["end"]
    for i, l in enumerate(out, 1):
        l["id"] = f"T{i}"
        l["text"] = re.sub(r"\s+", " ", l["text"]).strip()
        l["speaker"] = "Speaker " + str(int(re.sub(r"\D", "", l["speaker"]) or 0) + 1)
    return out



def split_row(line, ncols, fold_into=None):
    """A table row as `ncols` cells. A pipe inside a cell (older records wrote
    ` | ` between the parts of Sound or On-Screen Text) makes too many cells;
    the extras are folded back into `fold_into` (default: the last column)."""
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(c) <= ncols:
        return c
    k = ncols - 1 if fold_into is None else fold_into
    extra = len(c) - ncols
    return c[:k] + [" / ".join(c[k:k + extra + 1])] + c[k + extra + 1:]


def stamp(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def render(lines):
    md = [MARK, "",
          "Every word of the swipe, transcribed from its audio (not a model's summary). One line per speaker "
          "turn, numbered. The injection carries every numbered line — one of ours for each of theirs, same "
          "speaker, same order, short replies included. Speakers are separated by voice only: two people with "
          "similar voices can share a label — the shot table above says who is on screen.", "",
          "| # | Time | Speaker | Lang | Line (verbatim) |", "|---|---|---|---|---|"]
    md += [f"| {l['id']} | {stamp(l['start'])} | {l['speaker']} | {l.get('language') or '—'} | "
           f"{l['text'].replace('|', '/')} |" for l in lines]
    return "\n".join(md) + "\n"


def _secs(ts):
    m = re.match(r"\s*(\d+):(\d+(?:\.\d+)?)", ts)
    return int(m.group(1)) * 60 + float(m.group(2)) if m else None


def merge_into_table(record, lines):
    """The shot table's Transcript column, rewritten from the audio: every
    line whose start falls in a row's span, in order, with its speaker. The
    speaker keeps the NAME the record gave (Creator, Doctor 1) when the row
    names exactly one person for exactly one voice; otherwise the voice label."""
    rows = record.split("\n")
    head_i = next((i for i, l in enumerate(rows) if l.startswith("|") and "Transcript" in l and "Timestamp" in l), None)
    if head_i is None:
        return record
    cols = [c.strip() for c in rows[head_i].strip().strip("|").split("|")]
    ti, tsi = cols.index("Transcript"), cols.index("Timestamp")
    body = []
    j = head_i + 1
    while j < len(rows) and rows[j].startswith("|"):
        body.append(j); j += 1
    spans = []
    for k in body:
        c = [x.strip() for x in rows[k].strip().strip("|").split("|")]
        if len(c) != len(cols) or re.match(r"^:?-+", c[0]):
            continue
        a = _secs(c[tsi].split("-")[0]) if c[tsi] else None
        if a is not None:
            spans.append((k, a, c))
    per = []
    for n, (k, a, c) in enumerate(spans):
        b = spans[n + 1][1] if n + 1 < len(spans) else 10 ** 6
        mine = [l for l in lines if a - 0.5 <= l["start"] < b - 0.5] if n else [l for l in lines if l["start"] < b - 0.5]
        said = list(dict.fromkeys(re.findall(r"([A-Z][\w. ']{0,30}?):", c[ti])))
        per.append((k, c, mine, said))
    # A voice alone in a row with one named person gives that voice its name
    # everywhere it is otherwise unnamed (e.g. Speaker 1 = Creator).
    known = {}
    for k, c, mine, said in per:
        voices = list(dict.fromkeys(l["speaker"] for l in mine))
        if len(voices) == 1 and len(said) == 1:
            known.setdefault(voices[0], said[0])
    for k, c, mine, said in per:
        voices = list(dict.fromkeys(l["speaker"] for l in mine))
        local = {}
        if len(voices) == 1 and len(said) == 1:
            local[voices[0]] = said[0]
        for v in voices:
            if v not in local and v in known:
                local[v] = known[v]          # a voice named once keeps its name
        free_names = [x for x in said if x not in local.values()]
        for v in voices:
            if v not in local and free_names:
                local[v] = free_names.pop(0)
        if mine:
            c[ti] = " / ".join(f"{local.get(l['speaker'], l['speaker'])}: {l['text']}" for l in mine).replace("|", "/")
        elif not re.search(r"\[", c[ti] or ""):
            c[ti] = "(no speech)"
        rows[k] = "| " + " | ".join(c) + " |"
    return "\n".join(rows)


def attach(run_dir):
    d = Path(run_dir)
    video = d / "source.mp4"
    if not video.exists():
        raise RuntimeError("no source.mp4 in the run")
    tj = d / "transcript.json"
    # made right before the teardown read (run.py) — reuse it, never transcribe twice
    lines = json.loads(tj.read_text()) if tj.exists() and tj.stat().st_mtime > (d / "stages" / "1-teardown.md").stat().st_mtime - 900 else lines_of(transcribe(video))
    (d / "transcript.json").write_text(json.dumps(lines, indent=1, ensure_ascii=False) + "\n")
    block = render(lines)
    # The audio teardown's own record comes into the run: the Sound Sheet, the
    # voice clips and one voice card per person, appended after the transcript
    # so the deep passes (the cast sheet) and every later stage read them.
    at = audio_teardown(video)
    if at:
        dst = d / "audio"
        dst.mkdir(exist_ok=True)
        for f in ("sound-sheet.json", "sound-sheet.md", "words.json", "speakers.json"):
            if (at / f).exists():
                shutil.copy(at / f, d / f if f.startswith("sound-sheet") else dst / f)
        if (at / "voices").exists():
            shutil.copytree(at / "voices", dst / "voices", dirs_exist_ok=True)
        vc = at / "voices" / "voice-cards.json"
        if vc.exists():
            sheet = (at / "sound-sheet.md").read_text()
            if "### VOICES" in sheet:
                block += "\n" + sheet[sheet.index("### VOICES"):]
    (d / "stages" / "1-transcript.md").write_text(block)
    td = d / "stages" / "1-teardown.md"
    t = td.read_text()
    if MARK in t:
        t = t[:t.index(MARK)].rstrip() + "\n"
    t = merge_into_table(t, lines)
    t = correct_music(t, d)
    td.write_text(t.rstrip() + "\n\n---\n\n" + block)
    return lines


MUSIC_NOTE = "<!-- music corrected from the measured Sound Sheet -->"


def correct_music(t, d):
    """The teardown model GUESSES at the audio; the Sound Sheet MEASURES it.

    On 2026-10-02 a run's teardown said "Music: none. Room tone and voice only."
    while its own sound-sheet.json recorded a lo-fi bed under 99% of the video at
    136 bpm and 17 added effects. The spec then marked zero-distraction audio a
    FIXED element and the brief told the creator not to add music — the one thing
    the swipe actually does. Nothing downstream catches it, because every later
    stage reads the teardown and the teardown is what is wrong. So where the two
    disagree, the measurement wins and says so in the file.
    """
    sj = d / "sound-sheet.json"
    if not sj.is_file() or MUSIC_NOTE in t:
        return t
    try:
        rec = json.loads(sj.read_text())
    except Exception:
        return t
    m = (rec.get("music") or {})
    if not m.get("present"):
        return t
    got = m.get("measured") or {}
    share, bpm = got.get("music_share_percent"), got.get("tempo_bpm")
    fx = rec.get("effects"); n_fx = len((fx.get("effects") or []) if isinstance(fx, dict) else (fx or []))
    said = (f"music under {share}% of the video" if share else "music")
    if bpm:
        said += f", {bpm:g} bpm"
    if n_fx:
        said += f" · {n_fx} effect(s) added in the edit"
    out, fixed = [], False
    for line in t.splitlines():
        s = line.strip()
        low = s.lower()
        if (low.startswith("music:") or low.startswith("**music:**")) and "none" in low:
            out.append(f"Music: {said} — MEASURED off the audio. {MUSIC_NOTE}")
            fixed = True
            continue
        if "music: none" in low and "|" in s:        # a shot-table row
            out.append(line.replace("music: none", f"music: present ({said})")
                           .replace("Music: none", f"music: present ({said})"))
            fixed = True
            continue
        out.append(line)
    t = "\n".join(out)
    if fixed:
        t += (f"\n\n> **The audio was measured, not guessed.** This record originally said the"
              f" swipe had no music. `sound-sheet.json` records {said}. Where the two"
              f" disagree the measurement wins: do not write a 'no music' rule into the"
              f" spec or the brief off this record.\n")
    return t


if __name__ == "__main__":
    ls = attach(sys.argv[1])
    print(f"{len(ls)} lines · {len(set(l['speaker'] for l in ls))} speaker(s) → stages/1-transcript.md, appended to the teardown")
