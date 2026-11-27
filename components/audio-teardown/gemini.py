"""One door to Gemini for every "heard" read: an audio file and an instruction
in, parsed JSON out. Low thinking — listening needs none, and the default
stalled for four minutes on 3 of 10 swipes (2026-09-25). A model that fails
hands over to the next; the caller learns which one answered and why the
others did not."""
import base64
import json
import os
import re
import subprocess
from pathlib import Path

import house_models
from keys import key

URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
# the Model House's judge, then its first busy-model fallback (V2; verify row 17, 2026-10-21); seconds each
JUDGE = house_models.model_id("behind.judge")
BUSY = [m for m in house_models.model_ids("behind.judge_busy") if m != JUDGE]
MODELS = [(JUDGE, 240), (BUSY[0], 180)]
# the company key, then the standing backup (decision 2026-11-12: a key out of credit never stops a read)
KEYS = ("GEMINI_API_KEY", "GEMINI_API_KEY_PERSONAL")
SPENT = ("402", "RESOURCE_EXHAUSTED", "credits are depleted", "quota", "429")


def _one(model, audio, text, timeout, key_name="GEMINI_API_KEY"):
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(Path(audio).read_bytes()).decode()}},
        {"text": text}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0,
                             "thinkingConfig": {"thinkingLevel": "low"}}}
    # the body goes to curl on stdin — no copy of the audio is left in system temp;
    # stdin is taken, so the key header comes from a pipe — never on curl's command line
    header = f"x-goog-api-key: {key(key_name)}\n"
    rfd, wfd = os.pipe()
    try:
        with os.fdopen(wfd, "w") as w:
            w.write(header)
        r = subprocess.run(["curl", "-sS", "--max-time", str(timeout), "-H", "Content-Type: application/json",
                            "-H", f"@/dev/fd/{rfd}", "--data-binary", "@-", URL.format(m=model)],
                           input=json.dumps(body), capture_output=True, text=True, pass_fds=(rfd,))
    finally:
        os.close(rfd)
    try:
        raw = json.loads(r.stdout)["candidates"][0]["content"]["parts"][-1]["text"]
    except (ValueError, KeyError, IndexError):
        raise RuntimeError((r.stdout or r.stderr or "no answer")[:200])
    return json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip()))


def one(answer):
    """An answer that should be one JSON object: a one-item list around it is unwrapped (2026-11-15: the music
    read came back as [ {...} ] and every caller that wanted a dict dropped it silently, leaving the sheet blank)."""
    if isinstance(answer, list) and len(answer) == 1 and isinstance(answer[0], dict):
        return answer[0]
    return answer if isinstance(answer, dict) else {}


def ask(audio, text, models=MODELS):
    """(parsed JSON, model that answered, [(model, why) for the ones that failed])"""
    tried = []
    for model, cap in models:
        for name in KEYS:
            try:
                k = key(name)
            except Exception:  # noqa: BLE001 — a key this machine does not hold is skipped
                k = None
            if not k:
                continue
            try:
                return _one(model, audio, text, cap, name), model, tried
            except Exception as e:  # noqa: BLE001
                tried.append((model if name == KEYS[0] else f"{model} ({name})", str(e)[:160]))
                if not any(w in str(e) for w in SPENT):
                    break                                  # not a spent key: the next key would fail the same way
    raise RuntimeError("no Gemini model answered: " + "; ".join(f"{m}: {w}" for m, w in tried))


def prompt(stem, here):
    """(path, text) of the newest prompts/<stem>-v<N>-owner.md, its version note stripped."""
    files = sorted((Path(here) / "prompts").glob(f"{stem}-v*-owner.md"),
                   key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    p = files[-1]
    return p, re.sub(r"^\*v\d+[^\n]*\*\n+", "", p.read_text())
