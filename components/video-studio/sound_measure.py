"""The Sound board's numbers: every measure one card needs, taken from the tracks by a tool, the same every time.

Runs INSIDE the audio venv (~/.daemn/venvs/audio: numpy, soundfile, librosa); sound_board.py calls it as its own
process with one JSON request on stdin and reads one JSON answer on stdout.

    {"tracks": {"<name>": "<audio file>"},
     "asks": [{"id": "...", "op": "onset", "track": "<name>", "t": 2.26, "win": 0.3},
              {"id": "...", "op": "over", "track": "<name>", "t": 2.26, "until": null},
              {"id": "...", "op": "level", "track": "<name>", "a": 0.0, "b": 12.0},
              {"id": "...", "op": "change", "track": "<name>", "t": 12.0, "win": 1.0},
              {"id": "...", "op": "quiet", "track": "<name>", "a": 0.0, "b": 15.0}]}

    onset   the sharpest onset within `win` seconds of t (seconds), or null
    over    how far a sound at t stands over what was playing just before it: the loudest 50 ms in [t, t+0.3]
            (or [t, until]) minus the median 50 ms in [t-0.6, t-0.1], in dB
    level   the RMS level of [a, b] in dB (full scale)
    change  the biggest change of level (0.2 s before against 0.2 s after) within `win` seconds of t: the second
            a section starts or drops out
    quiet   the quietest second inside [a, b]: {"at", "db"} (the room)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

SR = 22050
HOP = 256


def load(path):
    import soundfile as sf
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-ac", "1", "-ar", str(SR), str(wav)],
                       check=True)
        y, _ = sf.read(str(wav), dtype="float32")
    return y


def rms50(y):
    """RMS in 50 ms windows, one value per HOP samples."""
    n = int(0.05 * SR)
    sq = np.convolve(y.astype("float64") ** 2, np.ones(n) / n, "same")[::HOP]
    return np.sqrt(np.maximum(sq, 1e-12))


def db(x):
    return round(float(20 * np.log10(max(float(x), 1e-9))), 1)


def answer(ask, y, r, fps):
    op, t = ask["op"], float(ask.get("t") or 0)
    i = lambda s: max(0, min(len(r) - 1, int(round(s * fps))))  # noqa: E731
    if op == "onset":
        import librosa
        env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
        w = float(ask.get("win") or 0.3)
        a, b = i(t - w), i(t + w) + 1
        fr = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP)
        fr = [f for f in fr if a <= f < b]
        if not fr:
            return None
        f = max(fr, key=lambda f: env[f])
        return round(f / fps, 3)
    if op == "over":
        until = ask.get("until")
        hit = r[i(t):i(float(until) if until else t + 0.3) + 1]
        before = r[i(t - 0.6):i(t - 0.1) + 1]
        if not len(hit) or not len(before):
            return None
        return round(db(hit.max()) - db(np.median(before)), 1)
    if op == "level":
        seg = y[int(float(ask["a"]) * SR):int(float(ask["b"]) * SR)]
        return db(np.sqrt(np.mean(seg.astype("float64") ** 2))) if len(seg) else None
    if op == "change":
        w = float(ask.get("win") or 1.0)
        n = max(2, int(0.2 * fps))                     # level over 0.2 s, compared 0.2 s apart: a section, not a beat
        L = 20 * np.log10(np.convolve(r, np.ones(n) / n, "same"))
        a, b = max(n, i(t - w)), min(len(L) - n, i(t + w) + 1)
        if b - a < 3:
            return None
        d = L[a + n:b + n] - L[a - n:b - n]
        k = a + int(np.argmax(np.abs(d)))
        return round(k / fps, 3)
    if op == "quiet":
        a, b = i(float(ask["a"])), i(float(ask["b"]))
        per = int(fps)
        if b - a <= per:
            return None
        roll = np.convolve(r[a:b], np.ones(per) / per, "valid")
        k = int(np.argmin(roll))
        return {"at": round((a + k) / fps, 2), "db": db(roll[k])}
    return None


def run(req):
    fps = SR / HOP
    tracks = {}
    out = {}
    for ask in req.get("asks") or []:
        name = ask["track"]
        if name not in tracks:
            try:
                y = load(req["tracks"][name])
                tracks[name] = (y, rms50(y))
            except Exception as e:  # noqa: BLE001 — a track that will not decode answers null, never fatal
                tracks[name] = (None, str(e)[:120])
        y, r = tracks[name]
        out[ask["id"]] = None if y is None else answer(ask, y, r, fps)
    return out


if __name__ == "__main__":
    print(json.dumps(run(json.loads(sys.stdin.read()))))
