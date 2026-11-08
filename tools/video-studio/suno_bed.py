"""A brief's music bed from a Suno take, cut to the edit: the take's own downbeats land on the scene changes that matter.

  python3 suno_bed.py <brief> [lane]    writes briefs/<brief>/music/bed.mp3 + bed.json, from the brief's music sheet
                                        (briefs/<brief>/music/suno.json: the takes, the lane, the beat grid, the cue sheet, the EQ)
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import video_studio as SC  # noqa: E402

def sheet(n):
    """The brief's music sheet (music/suno.json): the Suno takes, the lane in use, the take's beat grid, the cue sheet
    (scene it starts on, beat of the take, what it does) and the EQ. Data, never code."""
    f = os.path.join(SC.bdir(n), "music", "suno.json")
    if not os.path.isfile(f):
        sys.exit(f"no music sheet for this brief: write {f} (takes, lane, grid, cues, eq)")
    return json.load(open(f))


def _decode(path, sr=44100):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)


def main(n, lane=None):
    import numpy as np
    import tempfile
    d = sheet(n)
    lane = lane or d["lane"]
    TAKES, GRID, CUES, EQ, EQ_NOTE = d["takes"], d["grid"], d["cues"], d["eq"], d.get("eq_note", "")
    T, G = TAKES[lane], GRID[lane]
    m = os.path.join(SC.bdir(n), "music")
    lay = json.load(open(os.path.join(SC.bdir(n), "studio-build", "layout.json")))
    starts = {s["scene"]: s["start"] for s in lay["scenes"]}
    end = lay["length"]
    total = end + 1.0
    beat = G["beat"]
    src = os.path.join(m, T["take"])
    sr = 44100

    cues = [(round(starts[c], 4), b, why) for c, b, why in CUES[lane]]
    pieces, sheet = [], []
    with tempfile.TemporaryDirectory() as td:
        for i, (a0, b, why) in enumerate(cues):
            a1 = cues[i + 1][0] if i + 1 < len(cues) else total
            span = a1 - a0
            s0 = G["origin"] + b * beat
            beats = max(1, round(span / beat))
            sspan = beats * beat if i + 1 < len(cues) else span     # the last stretch runs out at its own speed
            k = sspan / span                    # >1 plays a touch faster, <1 a touch slower
            seg = os.path.join(td, f"{i}.wav")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0:.4f}", "-t", f"{sspan + 0.25:.4f}", "-i", src,
                            "-af", f"atempo={k:.5f}", "-ac", "2", "-ar", str(sr), seg], check=True)
            pieces.append((a0, a1, _decode(seg)))
            sheet.append({"at": round(a0, 3), "until": round(a1, 3), "take_from": round(s0, 3), "beat": b,
                          "beats": beats, "speed": round(k, 4), "what": why})
        out = np.zeros((int(total * sr) + sr, 2), np.float32)
        fade = int(0.012 * sr)
        for i, (a0, a1, x) in enumerate(pieces):
            i0, i1 = int(round(a0 * sr)), int(round(a1 * sr))
            nlen = min(len(x), i1 - i0 + fade)
            y = x[:nlen].copy()
            ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
            if i > 0:
                y[:fade] *= ramp                  # a 12 ms crossfade on each downbeat: no click, no smear
            if nlen > i1 - i0:
                y[i1 - i0:nlen] *= ramp[::-1][: nlen - (i1 - i0)]
            out[i0:i0 + nlen] += y
        out = out[: int(total * sr)]
        fo = int(1.2 * sr)
        out[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]
        raw = os.path.join(td, "raw.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-", raw],
                       input=out.tobytes(), check=True)
        bedp = os.path.join(m, "bed.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", EQ, "-ar", "44100", "-c:a", "libmp3lame", "-q:a", "2", bedp], check=True)
    s2 = starts["S2"]
    v = lambda db: round(10 ** (db / 20), 4)
    pts = [{"t": 0, "v": 0}, {"t": 0.05, "v": v(-23)}, {"t": round(s2 - 0.2, 3), "v": v(-23)}, {"t": round(s2 + 0.3, 3), "v": v(-19)},
           {"t": round(total - 0.1, 3), "v": v(-19)}, {"t": round(total, 3), "v": 0}]
    json.dump({"source": "suno", "lane": lane, "take": T["take"], "suno_song": T["song"], "style": T["style"], "exclude": T["exclude"],
               "lyrics_box": T["lyrics_box"], "why": T["why"], "starts_at": 0.0, "drop_at": round(starts["S3"], 3),
               "hit_at": round(starts[d["hit_scene"]], 3) if d.get("hit_scene") in starts else None, "grid": G, "cue_sheet": sheet, "eq": EQ, "eq_note": EQ_NOTE,
               "duck_points": pts, "duck_db": {"under the interview": -23, "under the narrator": -19},
               "from": "made in Suno, cut to the edit on the take's own downbeats"},
              open(os.path.join(m, "bed.json"), "w"), indent=1)
    for c in sheet:
        print(f"{c['at']:7.3f} beat {c['beat']:3d} speed {c['speed']:.3f}  {c['what']}")
    print("bed", round(SC.probe_dur(bedp), 2), "s")


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else sys.exit("name the brief, e.g. " + os.path.basename(__file__) + " 0001")), sys.argv[2] if len(sys.argv) > 2 else None)
