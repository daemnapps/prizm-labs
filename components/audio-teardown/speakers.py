"""WHO SPEAKS WHEN — ElevenLabs Scribe v2, word timings and speaker labels.

Scribe is used for what it is good at and nothing else. Its WORDS are not
trusted outside English: in the test (2026-09-25) it turned a Korean speaker
into "[laughs]", and on a second run translated her into English without
saying so. Its speaker labels and timings are what the merge uses.
"""
import json
import subprocess

from keys import key

STT = "https://api.elevenlabs.io/v1/speech-to-text"
MODEL = "scribe_v2"


def listen(audio, timeout=300):
    r = subprocess.run(["curl", "-sS", "--max-time", str(timeout), "-H", f"xi-api-key: {key('ELEVENLABS_API_KEY')}",
                        "-F", f"model_id={MODEL}", "-F", "diarize=true", "-F", "timestamps_granularity=word",
                        "-F", f"file=@{audio}", STT], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        raise RuntimeError(f"Scribe: {(r.stdout or r.stderr)[:200]}")
    if "words" not in d:
        raise RuntimeError(f"Scribe: {str(d)[:200]}")
    words = [{"start": w["start"], "end": w["end"], "text": w.get("text", ""), "type": w.get("type"),
              "speaker": w.get("speaker_id") or "speaker_0"}
             for w in d["words"] if w.get("type") in ("word", "audio_event")]
    return {"model": MODEL, "language": d.get("language_code"), "language_probability": d.get("language_probability"),
            "words": words}
