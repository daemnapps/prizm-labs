#!/usr/bin/env python3
"""THE TRANSCRIPT BAKE-OFF — the same swipes through every speech-to-text model
we hold a key for, side by side (2026-09-25).

the owner: "we need the best accuracy at this tear down level so i don't want to go
cheap … do a test for all of them." The verbatim transcript is what every later
stage is held to (transcript.py), so the model that writes it is chosen on
evidence, not on a leaderboard.

    python3 transcript_bakeoff.py <video> [<video> …] [--models a,b] [--out DIR]

Per video, the audio is cut once (mono 16 kHz) and sent to every model AT THE
SAME TIME. Each answer is folded into one shape — lines of {speaker, start,
text} — and saved as <out>/<video>/<model>.json. Then every model's words are
lined up against every other model's: a word most other models did not hear is
DISPUTED. A model with few disputed words agrees with the field; the page shows
each disputed word so a person can hear who was right.

No ground truth exists for a swipe, so agreement is the measure — and the page
is where a person settles it.
"""
import argparse, base64, difflib, json, re, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path



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


HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]

# $ per audio-hour, from each vendor's price page on 2026-09-25.
MODELS = {
    "scribe-v1":        {"who": "ElevenLabs", "name": "Scribe v1 (what the chain uses today)", "per_hour": 0.22},
    "scribe-v2":        {"who": "ElevenLabs", "name": "Scribe v2", "per_hour": 0.22},
    "gpt-transcribe":   {"who": "OpenAI", "name": "GPT Transcribe", "per_hour": 0.36},
    "gpt-4o-diarize":   {"who": "OpenAI", "name": "GPT-4o Transcribe (speakers)", "per_hour": 0.36},
    "whisper-1":        {"who": "OpenAI", "name": "Whisper", "per_hour": 0.36},
    "gemini-3.1-pro":   {"who": "Google", "name": "Gemini 3.1 Pro", "per_hour": 0.35},
    "gemini-3.5-flash": {"who": "Google", "name": "Gemini 3.5 Flash", "per_hour": 0.10},
}


def curl(args, timeout=600):
    r = subprocess.run(["curl", "-sS", "--max-time", str(timeout)] + args, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise RuntimeError((r.stdout or r.stderr)[:300])


def audio_of(video, td):
    a = Path(td) / "a.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vn", "-ac", "1",
                    "-ar", "16000", "-b:a", "64k", str(a)], check=True)
    return a


def dur_of(a):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "default=nw=1:nk=1", str(a)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


# ---------------------------------------------------------------- the models

def scribe(a, model):
    import transcript as T
    d = curl(["-H", f"xi-api-key: {_shared_keys().lookup('ELEVENLABS_API_KEY')}",
              "-F", f"model_id={model}", "-F", "diarize=true", "-F", "timestamps_granularity=word",
              "-F", f"file=@{a}", "https://api.elevenlabs.io/v1/speech-to-text"])
    if "words" not in d:
        raise RuntimeError(str(d)[:300])
    return [{"speaker": l["speaker"], "start": l["start"], "text": l["text"]} for l in T.lines_of(d)]


def openai(a, model):
    k = _shared_keys().lookup("OPENAI_API_KEY")
    fmt = "diarized_json" if "diarize" in model else ("verbose_json" if model == "whisper-1" else "json")
    args = ["https://api.openai.com/v1/audio/transcriptions", "-H", f"Authorization: Bearer {k}",
            "-F", f"model={model}", "-F", f"file=@{a}", "-F", f"response_format={fmt}"]
    if "diarize" in model:
        args += ["-F", "chunking_strategy=auto"]
    d = curl(args)
    if "error" in d:
        raise RuntimeError(d["error"].get("message", str(d))[:300])
    if d.get("segments") and "speaker" in d["segments"][0]:
        return [{"speaker": f"Speaker {s['speaker']}", "start": s.get("start", 0), "text": s["text"].strip()}
                for s in d["segments"]]
    if d.get("segments"):
        return [{"speaker": "—", "start": s.get("start", 0), "text": s["text"].strip()} for s in d["segments"]]
    return [{"speaker": "—", "start": 0, "text": s.strip()}
            for s in re.split(r"(?<=[.?!])\s+", d.get("text", "")) if s.strip()]


GEMINI_ASK = (
    "Transcribe this audio word for word. Every word exactly as spoken, including fillers, "
    "false starts and repeats; do not tidy, summarise or translate. Separate speakers "
    "(Speaker 1, Speaker 2 … in order of first appearance). One entry per speaker turn. "
    "Mark non-speech only as [music], [laughs] etc. Return JSON only: "
    '[{"speaker": "Speaker 1", "start": <seconds>, "text": "..."}]')


def gemini(a, model):
    k = _shared_keys().lookup("GEMINI_API_KEY")
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(a.read_bytes()).decode()}},
        {"text": GEMINI_ASK}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(body, f)
    d = curl([f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={k}",
              "-H", "Content-Type: application/json", "--data-binary", f"@{f.name}"])
    Path(f.name).unlink()
    try:
        txt = d["candidates"][0]["content"]["parts"][-1]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(str(d)[:300])
    rows = json.loads(re.sub(r"^```(json)?|```$", "", txt.strip()))
    return [{"speaker": r.get("speaker", "—"), "start": float(r.get("start") or 0), "text": r.get("text", "").strip()}
            for r in rows]


RUN = {
    "scribe-v1": lambda a: scribe(a, "scribe_v1"),
    "scribe-v2": lambda a: scribe(a, "scribe_v2"),
    "gpt-transcribe": lambda a: openai(a, "gpt-transcribe"),
    "gpt-4o-diarize": lambda a: openai(a, "gpt-4o-transcribe-diarize"),
    "whisper-1": lambda a: openai(a, "whisper-1"),
    "gemini-3.1-pro": lambda a: gemini(a, "gemini-3.1-pro-preview"),
    "gemini-3.5-flash": lambda a: gemini(a, "gemini-3.5-flash"),
}


# ------------------------------------------------------------- the compare

def words(lines):
    return re.findall(r"[a-z0-9']+", " ".join(l["text"] for l in lines).lower().replace("’", "'"))


def matched(a, b):
    """Which words of `a` line up with a word of `b`."""
    out = set()
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        out.update(range(blk.a, blk.a + blk.size))
    return out


def disputed(mine, others):
    """Index of each of my words that most other models did not have — words
    this model may have INVENTED or misheard."""
    hits = [0] * len(mine)
    for o in others:
        for i in matched(mine, o):
            hits[i] += 1
    need = len(others) / 2
    return {i for i, h in enumerate(hits) if h < need}


def missed(mine, others_by_model):
    """Words the field agrees were said (most models heard them) that this
    model left OUT — the half of accuracy that agreement alone rewards. A
    model that drops a second speaker entirely agrees with everyone on what
    little it kept; this is what catches it."""
    lost = total = 0
    for k, o in others_by_model.items():
        rest = [w for kk, w in others_by_model.items() if kk != k] + [mine]
        solid = set(range(len(o))) - disputed(o, rest)
        have = matched(o, mine)
        lost += len(solid - have)
        total += len(solid)
    return round(100 * lost / max(1, total), 1)


def one_video(video, models, out):
    name = re.sub(r"[^a-z0-9]+", "-", (Path(video).parent.name + "-" + Path(video).stem).lower()).strip("-")[:60]
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        a = audio_of(video, td)
        secs = dur_of(a)

        def go(m):
            t0 = time.time()
            try:
                lines = RUN[m](a)
                err = None
            except Exception as e:                                  # one model failing never stops the rest
                lines, err = [], f"{type(e).__name__}: {str(e)[:240]}"
            rec = {"model": m, "seconds": round(time.time() - t0, 1), "lines": lines, "error": err,
                   "cost": round(MODELS[m]["per_hour"] * secs / 3600, 5)}
            (d / f"{m}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
            return m, rec

        with ThreadPoolExecutor(max_workers=len(models)) as ex:
            got = dict(ex.map(go, models))
    ws = {m: words(r["lines"]) for m, r in got.items() if not r["error"]}
    for m, r in got.items():
        if r["error"]:
            continue
        others = [w for k, w in ws.items() if k != m]
        dis = disputed(ws[m], others) if others else set()
        r.update({"words": len(ws[m]), "disputed": sorted(dis),
                  "agree": round(100 * (1 - len(dis) / max(1, len(ws[m]))), 1),
                  "missed": missed(ws[m], {k: w for k, w in ws.items() if k != m}),
                  "speakers": len({l["speaker"] for l in r["lines"] if l["speaker"] != "—"})})
    summary = {"video": str(video), "name": name, "audio_seconds": round(secs, 1), "models": got}
    (d / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    return summary


def main():
    ap = argparse.ArgumentParser(description="Every speech-to-text model on the same swipes.")
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--out", default=str(WS / "runs" / "transcript-bakeoff" / "_system" / time.strftime("%Y-%m-%d")))
    a = ap.parse_args()
    sys.path.insert(0, str(HERE))
    models = [m.strip() for m in a.models.split(",") if m.strip()]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # The videos run together too — nothing here waits on another swipe.
    with ThreadPoolExecutor(max_workers=len(a.videos)) as ex:
        res = list(ex.map(lambda v: one_video(v, models, out), a.videos))
    (out / "bakeoff.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    for s in res:
        print(f"\n{s['name']}  ({s['audio_seconds']}s)")
        for m, r in s["models"].items():
            print(f"  {m:<17} " + (f"ERROR {r['error']}" if r["error"] else
                                   f"{r['agree']:5.1f}% agree · {r['missed']:4.1f}% missed · {r['words']} words · {r['speakers']} voices · {r['seconds']}s · ${r['cost']:.4f}"))
    print(f"\n{out / 'bakeoff.json'}")


if __name__ == "__main__":
    main()
