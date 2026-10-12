"""One door to Gemini for every "heard" read: an audio file and an instruction
in, parsed JSON out. Low thinking — listening needs none, and the default
stalled for four minutes on 3 of 10 swipes (2026-09-25). A model that fails
hands over to the next; the caller learns which one answered and why the
others did not."""
import base64
import json
import re
import subprocess
from pathlib import Path

from keys import key

URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"
MODELS = [("gemini-3.1-pro-preview", 240), ("gemini-3.5-flash", 180)]


def _one(model, audio, text, timeout):
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(Path(audio).read_bytes()).decode()}},
        {"text": text}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0,
                             "thinkingConfig": {"thinkingLevel": "low"}}}
    # the body goes to curl on stdin — no copy of the audio is left in system temp
    r = subprocess.run(["curl", "-sS", "--max-time", str(timeout), "-H", "Content-Type: application/json",
                        "--data-binary", "@-", URL.format(m=model, k=key("GEMINI_API_KEY"))],
                       input=json.dumps(body), capture_output=True, text=True)
    try:
        raw = json.loads(r.stdout)["candidates"][0]["content"]["parts"][-1]["text"]
    except (ValueError, KeyError, IndexError):
        raise RuntimeError((r.stdout or r.stderr or "no answer")[:200])
    return json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip()))


def ask(audio, text, models=MODELS):
    """(parsed JSON, model that answered, [(model, why) for the ones that failed])"""
    tried = []
    for model, cap in models:
        try:
            return _one(model, audio, text, cap), model, tried
        except Exception as e:
            tried.append((model, str(e)[:160]))
    raise RuntimeError("no Gemini model answered: " + "; ".join(f"{m}: {w}" for m, w in tried))


def prompt(stem, here):
    """(path, text) of the newest prompts/<stem>-v<N>-damon.md, its version note stripped."""
    files = sorted((Path(here) / "prompts").glob(f"{stem}-v*-damon.md"),
                   key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    p = files[-1]
    return p, re.sub(r"^\*v\d+[^\n]*\*\n+", "", p.read_text())
