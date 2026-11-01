"""Measure every voice option before a person hears it (the owner, 2026-09-23:
"the audio is muffled… option 2 and 3 are literally men… sounds too deep").

    <helpers-venv>/python voice_qc.py <person-folder>

Writes <person>/voice/check.json: per option, the median pitch (Hz), who it
sounds like (man under 160 Hz, woman above), how much of its energy sits above
4 kHz (a muffled take loses its highs), and `fails` naming what is wrong
against the spec's `voice.gender` and `voice.pitch` ("not deep" → a man must
sit at 100 Hz or above). Needs librosa (the video-edit helpers venv).
"""
import json, os, sys
from pathlib import Path
# this folder has a platform.py; Python puts a script's own folder first on the
# path, which hides the standard library's `platform` from librosa — drop it
_here = os.path.dirname(os.path.abspath(__file__))
sys.path = [p for p in sys.path if os.path.abspath(p or ".") != _here]
import numpy as np, librosa

LOW_MAN, MIN_HIGHS = 160, 0.08


def check(person: Path) -> dict:
    spec = json.loads((person / "spec.json").read_text())
    v = spec.get("voice") or {}
    want = v.get("gender", "")
    # an elderly woman sits lower than a young one — 130 Hz, not 160, is the line
    # (Yai, 2026-09-23: 135–141 Hz is an old woman, not a man)
    text = " ".join([v.get("persona", ""), *(v.get("adjustments") or [])]).lower()
    low = 125 if any(w in text for w in ("eighty", "elderly", "grandmother", "85", "88")) else LOW_MAN
    not_deep = any("not deep" in a.lower() for a in v.get("adjustments") or [])
    rows = []
    for o in sorted((person / "voice").glob("option-*.mp3")):
        y, sr = librosa.load(o, sr=22050, mono=True)
        f0, vf, _ = librosa.pyin(y, fmin=60, fmax=400, sr=sr)
        hz = float(np.nanmedian(f0)) if np.any(vf) else 0.0
        S = np.abs(librosa.stft(y)); fr = librosa.fft_frequencies(sr=sr)
        highs = float(S[fr > 4000].sum() / S.sum())
        sounds = "man" if hz and hz < low else ("woman" if hz else "unknown")
        fails = []
        if want and sounds != want:
            fails.append(f"sounds like a {sounds}")
        if want == "man" and not_deep and hz and hz < 100:
            fails.append("too deep")
        if highs < MIN_HIGHS:
            fails.append("muffled")
        rows.append({"option": int(o.stem.split("-")[1]), "hz": round(hz), "sounds": sounds, "highs_pct": round(highs * 100, 1), "fails": fails})
    out = {"person": person.name, "want": want, "options": rows}
    (person / "voice" / "check.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    r = check(Path(sys.argv[1]).resolve())
    for o in r["options"]:
        print(f"option {o['option']}: {o['hz']} Hz {o['sounds']}, highs {o['highs_pct']}% {'— FAILS: ' + ', '.join(o['fails']) if o['fails'] else '— ok'}")
