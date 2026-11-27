"""THE MEASURES — numbers a tool takes from a track, the same every time.

Runs INSIDE the audio venv (~/.daemn/venvs/audio: librosa ISC, PANNs MIT with
CC-BY weights, torch BSD) — music.py and effects.py call it as its own process,
so nothing here is imported by the chain.

    python measure.py music <track>          tempo, beats, key, energy curve, changes, ending
    python measure.py events <track> [beats] [bank files]   every added sound, sharp or soft, timed (PANNs),
                                             grouped by sameness, each with its nearest bank sound

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


def loop_beats(env, fps, beat):
    """How many beats the music's loop repeats over: of 2, 4, 8 and 16 beats, the shortest whose onset pattern
    matches itself one loop later almost as well as the best one does (a snare is compared with a snare, never with
    the kick two beats away)."""
    best = {}
    for nb in (2, 4, 8, 16):
        k = int(round(nb * beat * fps))
        if k <= 0 or k >= len(env) // 2:
            continue
        a, b = env[:-k], env[k:]
        best[nb] = float(np.corrcoef(a, b)[0, 1]) if a.std() and b.std() else 0.0
    if not best:
        return 4
    top = max(best.values())
    return min(nb for nb, c in best.items() if c >= 0.9 * top)


def loop_residual(S, fps, beats, rank=1, loop=None):
    """How much each frame of a mel spectrogram (dB) holds that the music's own loop does not: the frame against the
    same place 2, 4, 8 and 16 beats away, keeping only sound that is HERE and not THERE, and the second-smallest of
    those (an effect laid twice a bar apart still stands out against the other places). A frame of the loop itself
    scores near 0; an added hit, a riser or a swell scores high. Without a beat grid: zeros (nothing to compare)."""
    T = S.shape[1]
    beats = sorted(beats or [])
    if len(beats) < 8:
        return np.zeros(T)
    beat = float(np.median(np.diff(beats)))
    D = []
    for nb in ([loop, 2 * loop, 3 * loop] if loop else (2, 4, 8, 16)):
        k = int(round(nb * beat * fps))
        if k <= 0 or k >= T:
            continue
        for sgn in (1, -1):
            idx = np.arange(T) + sgn * k
            ok = (idx >= 0) & (idx < T)
            d = np.full(T, np.nan)
            d[ok] = np.mean(np.maximum(S[:, ok] - S[:, idx[ok]], 0), axis=0)
            D.append(d)
    if not D:
        return np.zeros(T)
    D = np.sort(np.array(D), axis=0)                    # NaN (no partner that far away) sorts last
    n_ok = (~np.isnan(D)).sum(axis=0)
    pick = np.clip(np.minimum(rank, n_ok - 1), 0, None)
    res = D[pick, np.arange(T)]
    return np.nan_to_num(res)


def spans(curve, fps, k=6.0, min_s=0.03):
    """Stretches where a curve rises above its own median by k median-deviations: [(start s, end s, peak)]."""
    sm = np.convolve(curve, np.ones(5) / 5, "same")
    med = float(np.median(sm))
    thr = med + k * float(np.median(np.abs(sm - med)) or 1e-6)
    out, a = [], None
    for i, v in enumerate(list(sm) + [-np.inf]):
        if v > thr and a is None:
            a = i
        elif v <= thr and a is not None:
            if (i - a) / fps >= min_s:
                out.append((a / fps, i / fps, float(sm[a:i].max()) / (thr or 1)))
            a = None
    return out


def groups(fps_, mags, kinds=None, same=0.93, floor=2.0):
    """Moments that are the same added sound: cosine >= same between their fingerprints (what rose over the music at
    that moment, fingerprint()). Walked in time order, each joins the first earlier group it matches, so the same input
    always gives the same groups. A moment with almost nothing added (mag < floor) is its own group; a soft rise
    only ever joins another soft rise."""
    out, heads = [], []
    kinds = kinds or ["hit"] * len(mags)
    for f, m, kd in zip(fps_, mags, kinds):
        g = None
        if m >= floor:
            for gi, h, hk in heads:
                if hk == kd and float(f @ h / (np.linalg.norm(f) * np.linalg.norm(h) + 1e-9)) >= same:
                    g = gi
                    break
        if g is None:
            g = max(out) + 1 if out else 1
            if m >= floor:
                heads.append((g, f, kd))
        out.append(g)
    return out


def fingerprint(P, f, scale):
    """What rose over the music at frame f: the mel power just after minus just before, positive part, log-scaled."""
    post = P[:, f:f + 6].mean(axis=1)
    pre = P[:, max(0, f - 8):max(1, f - 2)].mean(axis=1)
    return np.log1p(np.maximum(post - pre, 0) / scale)


def events(path, beats=None, top=60, bank=None):
    """Every added sound in the voices-removed track, timed, with the loop's own version of that moment beside it.
    Run on the track WITHOUT voices: on the full mix, speech drowns every effect (24 swipes, 2026-09-30).

    v2 (2026-11-15): the same swipe gave different effects on different runs (a snare heard as "camera shutter",
    then "typewriter"; a click found once and missed the next time). The old pass kept the top 15% of onsets and
    threw away every one the tagger heard as music, and in a song the tagger hears music everywhere. Now:
    1. a hit: every onset, against the same place in the loop one, two and three loops away (loop_beats) (`stands_out`: how much louder
       it is than the loop's own version of that place; a kick or snare of the loop scores about 1); `ref_at` is
       the quietest of those places, so the ear can hear the loop alone first and then this moment
    2. a soft sound: every stretch of 0.25 s or more that the loop does not hold (loop_residual): a riser, a swell,
       a whoosh, a drone
    3. kept: every onset in the top 30% of the track's own and every soft sound, one per 0.15 s, the `top` that
       stand out most; the ear (effects.py) hears each against its `ref_at` and decides
    4. each fingerprinted by what rose over the music; the same fingerprint is the same sound (`group`), and the
       nearest bank sound by that fingerprint (`bank_match`) is a fixed, repeatable match
    5. the room: the quietest second of the track and its level
    Without a beat grid (no music) every onset is its own reference-free hit and `stands_out` is its strength over
    the track's median."""
    import librosa
    from panns_inference import AudioTagging
    labels = [r[2] for r in list(csv.reader(open(Path.home() / "panns_data/class_labels_indices.csv")))[1:]]
    y, sr = load(path, 32000)
    dur = len(y) / sr
    hop = 512
    fps = sr / hop
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    frames = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=hop, backtrack=False)
    P = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=hop, n_mels=64)
    scale = float(P.mean()) + 1e-9
    S = np.maximum(librosa.power_to_db(P, ref=np.max), -60)
    beats = sorted(beats or [])
    beat = float(np.median(np.diff(beats))) if len(beats) >= 8 else None
    T = len(env)
    loop = loop_beats(env, fps, beat) if beat else None
    med = float(np.median(env[frames])) if len(frames) else 1.0
    floor = float(np.percentile(env[frames], 70)) if len(frames) else np.inf
    level = \
        np.sqrt(P.mean(axis=0))
    cands = []
    for f in frames:
        v = float(env[f])
        if v < floor:
            continue
        ratio, ref = v / (med or 1.0), None
        if beat:
            before = float(level[max(0, f - 8):max(1, f - 2)].mean()) or 1e-9
            others = []
            for nb in (loop, 2 * loop, 3 * loop):
                for sgn in (-1, 1):
                    g = int(round(f + sgn * nb * beat * fps))
                    if 8 <= g < T - 2:
                        lv = float(level[g - 8:g - 2].mean())
                        if 0.5 <= lv / before <= 2.0:          # the music is playing there as it is here
                            others.append((float(env[g - 2:g + 3].max()), g))
            if others:
                ratio = v / (float(np.median([o[0] for o in others])) or 1e-6)
                ref = min(others)[1] / fps
        cands.append({"at": f / fps, "until": None, "kind": "hit", "strength": v / (med or 1.0),
                      "stands_out": ratio, "ref_at": ref, "f": int(f)})
    res = loop_residual(S, fps, beats, loop=loop)
    for a, b, peak in spans(res, fps, min_s=0.25):
        f = int(a * fps)
        cands.append({"at": a, "until": b, "kind": "soft", "strength": float(env[f]) / (med or 1.0),
                      "stands_out": peak, "ref_at": (a - loop * beat) if beat and a - loop * beat >= 0 else
                      ((a + loop * beat) if beat and b + loop * beat <= dur else None), "f": f})
    cands.sort(key=lambda c: (-(c["kind"] == "soft"), -c["stands_out"], -c["strength"]))
    kept = []
    for c in cands:
        end = c["until"] or c["at"]
        if any(k["at"] - 0.15 <= c["at"] <= (k["until"] or k["at"]) + 0.15 or c["at"] - 0.15 <= k["at"] <= end + 0.15
               for k in kept):
            continue
        kept.append(c)
    kept.sort(key=lambda c: -(min(c["stands_out"], 4.0) + min(c["strength"], 4.0)))
    kept = sorted(kept[:top], key=lambda c: c["at"])
    out = {"onsets": int(len(frames)), "seconds": round(dur, 2), "beat_seconds": round(beat, 3) if beat else None,
           "loop_beats": loop}
    fps_ = [fingerprint(P, c["f"], scale) for c in kept]
    mags = [float(x.sum()) for x in fps_]
    grp = groups(fps_, mags, [c["kind"] for c in kept])
    bank_fp = []
    for bf in bank or []:
        if "room-tone" in Path(bf).name:
            continue
        try:
            yb, _ = load(bf, 32000)
            Pb = librosa.feature.melspectrogram(y=yb[:sr * 2], sr=sr, hop_length=hop, n_mels=64)
            e = Pb.sum(axis=0)
            k = int(np.argmax(e > e.max() * 0.1))
            bank_fp.append((bf, np.log1p(Pb[:, k:k + 6].mean(axis=1) / scale)))
        except Exception:  # noqa: BLE001 — a bank file that will not decode is left out, never fatal
            continue
    tagger = AudioTagging(checkpoint_path=str(Path.home() / "panns_data/Cnn14_mAP=0.431.pth"), device="cpu") if kept else None
    ev = []
    for c, fp, mag, gi in zip(kept, fps_, mags, grp):
        a = max(0, int((c["at"] - 0.1) * sr))
        n = int(sr * max(1.0, min(4.0, (c["until"] or c["at"]) - c["at"] + 0.4)))
        seg = y[a:a + n]
        seg = np.pad(seg, (0, max(0, sr - len(seg)))).astype("float32")
        p = tagger.inference(seg[None, :])[0][0]
        ranked = [(labels[k], float(p[k])) for k in np.argsort(-p) if k not in SPEECH and k not in MUSIC][:3]
        row = {"at": round(c["at"], 2), "until": round(c["until"], 2) if c["until"] else None, "kind": c["kind"],
               "strength": round(c["strength"], 2), "stands_out": round(c["stands_out"], 2),
               "ref_at": round(c["ref_at"], 2) if c["ref_at"] is not None else None,
               "added_mag": round(mag, 1), "group": gi,
               "sounds": [{"sound": nm, "p": round(q, 3)} for nm, q in ranked],
               "music_likelihood": round(float(p[137]) if len(p) > 137 else 0.0, 2),
               "on_beat": any(abs(c["at"] - b) <= 0.06 for b in beats)}
        if bank_fp and mag >= 2.0:
            sims = sorted(((float(fp @ v / (np.linalg.norm(fp) * np.linalg.norm(v) + 1e-9)), bf) for bf, v in bank_fp),
                          reverse=True)
            row["bank_match"] = {"file": sims[0][1], "similarity": round(sims[0][0], 3)}
        ev.append(row)
    out["events"] = ev
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    per = int(fps)
    if len(rms) > per:
        roll = np.convolve(rms, np.ones(per) / per, "valid")
        i = int(np.argmin(roll))
        out["room"] = {"at": round(i / fps, 2), "until": round(i / fps + 1, 2),
                       "db": round(float(20 * np.log10(roll[i] + 1e-9)), 1)}
    return out


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
    elif what == "music":
        print(json.dumps(music(track)))
    else:
        bank = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None
        print(json.dumps(events(track, beats, bank=bank)))
