"""ALIGN THE APPROVED TAKE TO THE LIPS — the clip model performs the line (so its lips
move), our APPROVED recording is what you hear: each stretch of the approved take is
sped up or slowed down so every word starts exactly when the model's mouth says it.
Keeps the voice we approved (the owner 2026-10-03: the speech-to-speech voices "look like
shit"), keeps the lips. Brand-agnostic.

    python3 align_take.py <clip.mp4> <approved.mp3> --out <clip-with-take.mp4> [--from S --to S]
"""
from __future__ import annotations

import argparse, difflib, json, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lineparity  # noqa: E402

MIN_CHUNK = 0.22      # seconds — shorter stretches merge into the next (fewer cuts, cleaner sound)
MAX_SQUEEZE = 1.6     # never speed a stretch up or slow it down past this; a bigger gap is left as a pause


def words(audio: Path) -> list[dict]:
    k = lineparity.key_of(); b = lineparity._boundary()
    body = lineparity._multipart_body({"model_id": lineparity.STT_MODEL_ID, "timestamps_granularity": "word"}, [("file", Path(audio))], b)
    st, _h, raw = lineparity.http_transport("POST", lineparity.ELEVEN_STT, {"xi-api-key": k, "Content-Type": f"multipart/form-data; boundary={b}"}, body)
    return [w for w in json.loads(raw.decode()).get("words", []) if w.get("type") == "word"]


def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower())


def anchors(take: list[dict], lips: list[dict]) -> list[tuple[float, float]]:
    """(time in the take, time on the lips) for every word both say, in order."""
    sm = difflib.SequenceMatcher(a=[norm(w["text"]) for w in take], b=[norm(w["text"]) for w in lips], autojunk=False)
    out = []
    for blk in sm.get_matching_blocks():
        for i in range(blk.size):
            out.append((take[blk.a + i]["start"], lips[blk.b + i]["start"]))
    return out


def _tempo(f):
    parts = []
    while f > 2.0:
        parts.append("atempo=2.0"); f /= 2.0
    while f < 0.5:
        parts.append("atempo=0.5"); f /= 0.5
    parts.append(f"atempo={f:.4f}")
    return ",".join(parts)


def align(clip: Path, take: Path, out: Path, a_from: float = 0.0, a_to: float | None = None) -> dict:
    ff = "ffmpeg"
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        src = t / "take.wav"
        cut = ["-ss", f"{a_from}"] + (["-to", f"{a_to}"] if a_to else [])
        subprocess.run([ff, "-v", "error", "-y", *cut, "-i", str(take), "-ac", "1", "-ar", "44100", str(src)], check=True)
        lip_audio = t / "lips.wav"
        subprocess.run([ff, "-v", "error", "-y", "-i", str(clip), "-vn", "-ac", "1", "-ar", "44100", str(lip_audio)], check=True)
        tw, lw = words(src), words(lip_audio)
        an = anchors(tw, lw)
        if len(an) < 2:
            raise SystemExit(f"too few shared words to align ({len(an)}): take heard {len(tw)}, lips heard {len(lw)}")
        take_end = tw[-1]["end"] + 0.15
        lip_end = lw[-1]["end"] + (take_end - tw[-1]["end"])
        pts = [(0.0, max(0.0, an[0][1] - an[0][0]))] + an + [(take_end, lip_end)]
        # merge stretches that are too short to stretch cleanly
        keep = [pts[0]]
        for p in pts[1:]:
            if p[0] - keep[-1][0] >= MIN_CHUNK and p[1] - keep[-1][1] >= MIN_CHUNK:
                keep.append(p)
        if keep[-1] != pts[-1]:
            keep[-1] = pts[-1]
        pieces, lead, factors = [], keep[0][1], []
        for n, ((a0, b0), (a1, b1)) in enumerate(zip(keep, keep[1:])):
            f = (a1 - a0) / max(1e-3, b1 - b0)            # >1 speeds up, <1 slows down
            f = max(1 / MAX_SQUEEZE, min(MAX_SQUEEZE, f)); factors.append(round(f, 2))
            pc = t / f"p{n}.wav"
            subprocess.run([ff, "-v", "error", "-y", "-ss", f"{a0:.3f}", "-to", f"{a1:.3f}", "-i", str(src),
                            "-af", _tempo(f), str(pc)], check=True)
            pieces.append((b0, pc))
        ins, flt = [], []
        for n, (b0, pc) in enumerate(pieces):
            ins += ["-i", str(pc)]
            ms = int(max(0.0, b0) * 1000)
            flt.append(f"[{n}:a]adelay={ms}|{ms}[d{n}]")
        mixed = t / "aligned.wav"
        fc = ";".join(flt) + ";" + "".join(f"[d{n}]" for n in range(len(pieces))) + f"amix=inputs={len(pieces)}:normalize=0[o]"
        subprocess.run([ff, "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[o]", str(mixed)], check=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([ff, "-v", "error", "-y", "-i", str(clip), "-i", str(mixed), "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
        return {"file": str(out), "anchors": len(an), "stretches": len(pieces), "take_words": len(tw), "lip_words": len(lw), "speed_changes": factors}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("clip"); ap.add_argument("take"); ap.add_argument("--out", required=True)
    ap.add_argument("--from", dest="a_from", type=float, default=0.0); ap.add_argument("--to", dest="a_to", type=float)
    a = ap.parse_args()
    print(json.dumps(align(Path(a.clip), Path(a.take), Path(a.out), a.a_from, a.a_to), indent=1))
