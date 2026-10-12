"""THE MEASURES — numbers a tool takes from a track, the same every time.

Runs INSIDE the audio venv (the venv named by AUDIO_PYTHON: librosa ISC, PANNs MIT with
CC-BY weights, torch BSD) — music.py and effects.py call it as its own process,
so nothing here is imported by the chain.

    python measure.py music <track>          tempo, beats, key, energy curve, changes, ending
    python measure.py events <track>         every non-speech, non-music sound, timed (PANNs)

Prints one JSON object.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import subprocess
import tempfile

SR = 22050
# Krumhansl–Kessler key profiles — the standard way to read a key from pitch content.
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def load(path, sr):
    """Any audio file → mono samples, decoded by ffmpeg (mp3 support varies by machine)."""
    import soundfile as sf
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-ac", "1", "-ar", str(sr), str(wav)],
                       check=True)
        y, _ = sf.read(str(wav), dtype="float32")
    return y, sr


def music(path):
    import librosa
    y, sr = load(path, SR)
    dur = len(y) / sr
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
    floor = max(1e-4, float(np.percentile(rms, 95)) * 0.08)
    present = rms > floor
    out = {"seconds": round(dur, 1), "music_share_percent": round(100 * float(present.mean()))}
    if present.mean() < 0.1:
        out["present"] = False
        return out
    out["present"] = True
    on = t[present]
    out["starts"], out["ends"] = round(float(on[0]), 1), round(float(on[-1]), 1)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    out["tempo_bpm"] = round(float(np.atleast_1d(tempo)[0]), 1)
    out["beats"] = [round(float(b), 2) for b in beats]
    out["downbeats_guess"] = out["beats"][::4]
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    best = max(((np.corrcoef(np.roll(prof, k), chroma)[0, 1], NOTES[k], mode)
                for prof, mode in ((MAJOR, "major"), (MINOR, "minor")) for k in range(12)))
    out["key"], out["key_confidence"] = f"{best[1]} {best[2]}", round(float(best[0]), 2)
    # energy curve, one value a second, 0–100 of this track's own loudest second
    per = [float(rms[(t >= s) & (t < s + 1)].mean()) if ((t >= s) & (t < s + 1)).any() else 0.0
           for s in range(int(np.ceil(dur)))]
    top = max(per) or 1.0
    curve = [round(100 * v / top) for v in per]
    out["energy_curve"] = curve
    changes = []
    for s in range(2, len(curve) - 1):
        before, after = np.mean(curve[max(0, s - 3):s]), np.mean(curve[s:s + 3])
        if after - before >= 30:
            changes.append({"at": s, "what": "builds / hits", "from": round(before), "to": round(after)})
        elif before - after >= 30:
            changes.append({"at": s, "what": "drops out", "from": round(before), "to": round(after)})
    kept = []
    for c in changes:                                  # one change per three seconds
        if not kept or c["at"] - kept[-1]["at"] >= 3:
            kept.append(c)
    out["changes"] = kept
    tail = curve[-3:] if len(curve) >= 3 else curve
    out["ending"] = ("fades" if len(tail) == 3 and tail[0] > tail[1] > tail[2] and tail[2] < 40
                     else "stops dead" if tail and tail[-1] >= 50 else "ends quietly")
    return out


SPEECH = set(range(0, 41)) | {70}              # AudioSet: human voice, speech, singing, rapping, whistling
MUSIC = set(range(137, 283))                   # AudioSet: music, instruments, genres, music moods


def events(path, beats=None, top=40):
    """Every sharp non-speech sound in the voices-removed track, timed, with what
    it most likely is. Run on the track WITHOUT voices: on the full mix, speech
    drowns every effect (a first pass over 24 swipes found five, 2026-09-30).

    1. every onset (a sudden rise in sound), with its strength
    2. the strongest ones — sharper than 85% of the track's own onsets — kept
    3. each named by the AudioSet tagger (PANNs) from one second around it,
       speech and music labels set aside; the beat grid says if it sits on a beat
    """
    import librosa
    from panns_inference import AudioTagging
    labels = [r[2] for r in list(csv.reader(open(Path.home() / "panns_data/class_labels_indices.csv")))[1:]]
    y, sr = load(path, 32000)
    env = librosa.onset.onset_strength(y=y, sr=sr)
    frames = librosa.onset.onset_detect(onset_envelope=env, sr=sr, backtrack=False)
    if not len(frames):
        return {"events": [], "onsets": 0}
    strength = env[frames]
    cut = float(np.percentile(strength, 85))
    keep = [(float(librosa.frames_to_time(f, sr=sr)), float(v)) for f, v in zip(frames, strength) if v >= cut]
    keep = sorted(keep, key=lambda x: -x[1])[:top]
    keep.sort()
    tagger = AudioTagging(checkpoint_path=str(Path.home() / "panns_data/Cnn14_mAP=0.431.pth"), device="cpu")
    windows = []
    for t, _ in keep:
        a = max(0, int((t - 0.25) * sr))
        seg = y[a:a + sr]
        windows.append(np.pad(seg, (0, sr - len(seg))))
    windows = np.stack(windows).astype("float32")
    probs, _ = tagger.inference(windows)
    beats = beats or []
    out = []
    for (t, v), p in zip(keep, probs):
        ranked = [(labels[k], float(p[k])) for k in np.argsort(-p) if k not in SPEECH and k not in MUSIC][:3]
        musical = float(p[137]) if len(p) > 137 else 0.0
        out.append({"at": round(t, 2), "strength": round(v / (cut or 1), 2),
                    "sounds": [{"sound": n, "p": round(q, 3)} for n, q in ranked],
                    "music_likelihood": round(musical, 2),
                    "on_beat": any(abs(t - b) <= 0.06 for b in beats)})
    return {"events": out, "onsets": int(len(frames))}


def duck(path, intervals):
    """How loud the music is while someone speaks vs when nobody does (dB).
    A big gap means the music was pulled down under the voice."""
    y, sr = load(path, 16000)
    inside = np.zeros(len(y), dtype=bool)
    for a, b in intervals:
        inside[int(a * sr):int(b * sr)] = True
    def db(x):
        return round(float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)), 1) if len(x) else None
    return {"music_db_while_speaking": db(y[inside]), "music_db_otherwise": db(y[~inside])}


if __name__ == "__main__":
    what, track = sys.argv[1], sys.argv[2]
    beats = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    if what == "duck":
        print(json.dumps(duck(track, json.loads(sys.argv[3]))))
    else:
        print(json.dumps(music(track) if what == "music" else events(track, beats)))
