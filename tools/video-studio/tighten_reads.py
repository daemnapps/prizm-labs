"""Tighten a brief's kept reads: every pause between words longer than GAP is cut down to GAP.

  python3 tighten_reads.py <brief>         writes voice/tight/S*.mp3 and S*.words.json; the kept reads are untouched
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAP, LEAD, TAIL = 0.18, 0.06, 0.12


def tighten(n):
    sys.path.insert(0, HERE)
    import video_studio as SC
    vdir = os.path.join(SC.bdir(n), "voice")
    reads = json.load(open(os.path.join(vdir, "reads.json")))["lines"]
    os.makedirs(os.path.join(vdir, "tight"), exist_ok=True)
    for s, line in reads.items():
        ws = line["words"]
        keep, a = [], max(0.0, ws[0]["start"] - LEAD)
        for i in range(len(ws) - 1):
            gap = ws[i + 1]["start"] - ws[i]["end"]
            if gap > GAP:
                keep.append((a, ws[i]["end"] + GAP / 2))
                a = ws[i + 1]["start"] - GAP / 2
        keep.append((a, ws[-1]["end"] + TAIL))
        src = os.path.join(vdir, f"{s}.mp3")
        parts = "".join(f"[0:a]atrim={x:.3f}:{y:.3f},asetpts=PTS-STARTPTS[p{k}];" for k, (x, y) in enumerate(keep))
        fc = parts + "".join(f"[p{k}]" for k in range(len(keep))) + f"concat=n={len(keep)}:v=0:a=1[a]"
        out = os.path.join(vdir, "tight", f"{s}.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[a]", "-c:a", "libmp3lame", "-q:a", "2", out], check=True)
        def shift(t):  # where a time in the kept read lands in the tightened one
            off = 0.0
            for x, y in keep:
                if t <= y:
                    return round(off + max(0.0, t - x), 3)
                off += y - x
            return round(off, 3)
        new = [dict(w, start=shift(w["start"]), end=shift(w["end"])) for w in ws]
        json.dump({"scene": s, "from": f"voice/{s}.mp3", "max_gap": GAP, "words": new}, open(os.path.join(vdir, "tight", f"{s}.words.json"), "w"), indent=1)
        print(s, f"{ws[-1]['end']:.2f}s → {new[-1]['end']:.2f}s")


if __name__ == "__main__":
    tighten((sys.argv[1] if len(sys.argv) > 1 else sys.exit("name the brief, e.g. " + os.path.basename(__file__) + " 0001")))
