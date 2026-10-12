"""Does a voice actually sound OLDER than a baseline? Measured, not guessed
(the owner, 2026-09-23: "<the elder> still sounds like a young woman… actually listen").

    <helpers-venv>/python voice_age.py <baseline.mp3> <candidate.mp3> [...]

Both read the SAME line. Older voices read slower, sit lower, and waver more.
Per candidate, against the baseline: duration ratio (slower = older), median
pitch ratio (lower = older), pitch waver (median frame-to-frame pitch change in
semitones — tremble), breathiness (share of unvoiced energy). An option counts
as older only if it is at least 15 % slower AND lower or more wavery.
"""
import json, os, sys
_here = os.path.dirname(os.path.abspath(__file__))
sys.path = [p for p in sys.path if os.path.abspath(p or ".") != _here]
import numpy as np, librosa


def feats(f):
    y, sr = librosa.load(f, sr=22050, mono=True)
    yt, _ = librosa.effects.trim(y, top_db=35)
    f0, vf, _ = librosa.pyin(yt, fmin=60, fmax=450, sr=sr)
    v = f0[vf] if np.any(vf) else np.array([np.nan])
    st = 12 * np.log2(v / np.nanmedian(v))
    waver = float(np.nanmedian(np.abs(np.diff(st)))) if len(st) > 2 else 0.0
    rms = librosa.feature.rms(y=yt)[0]; vmask = np.resize(vf, rms.shape)
    breath = float(rms[~vmask].sum() / max(rms.sum(), 1e-9))
    return {"dur": len(yt) / sr, "hz": float(np.nanmedian(v)), "waver": waver, "breath": breath}


base = feats(sys.argv[1]); rows = []
for c in sys.argv[2:]:
    f = feats(c)
    r = {"file": os.path.basename(c), "slower": round(f["dur"] / base["dur"], 2), "pitch": round(f["hz"] / base["hz"], 2),
         "waver": round(f["waver"] / max(base["waver"], 1e-6), 2), "breath": round(f["breath"] / max(base["breath"], 1e-6), 2), "hz": round(f["hz"])}
    r["older"] = r["slower"] >= 1.15 and (r["pitch"] <= 0.95 or r["waver"] >= 1.2)
    r["score"] = round((r["slower"] - 1) + (1 - r["pitch"]) + (r["waver"] - 1) * 0.5 + (r["breath"] - 1) * 0.3, 2)
    rows.append(r)
print(json.dumps({"baseline": {k: round(v, 2) for k, v in base.items()}, "candidates": sorted(rows, key=lambda r: -r["score"])}, indent=1))
