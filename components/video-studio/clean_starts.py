"""Find hidden cuts inside each shot of a brief's picked takes (a clip's own edit showing for a few frames).

  python3 clean_starts.py <brief>        lists every shot whose source window holds a cut, with where it falls
A cut in the first 0.5 s of a shot means its in point should move past it; one later means the shot jumps mid-way.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import video_studio as SC  # noqa: E402


def cuts(src, a, d):
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{a:.3f}", "-t", f"{d:.3f}", "-i", src, "-an",
                        "-vf", "scale=320:-2,select='gt(scene,0.32)',showinfo", "-f", "null", "-"], capture_output=True, text=True)
    return [round(float(m), 2) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def main(n):
    st = SC.brief_state(n)
    out = []
    for sc in st["scenes"]:
        wf, run = sc["workflow"], sc["run"]
        pics = [x for x in wf["steps"] if x["tool"] == "ffmpeg.trim"]
        if not pics or not run:
            continue
        voice = next((x for x in wf["steps"] if x["tool"] == "voice.read"), None)
        if voice and all("from_word" in x["params"] for x in pics):
            ws = SC.read_words(n, sc["scene"], os.path.join(SC.bdir(n), voice["inputs"]["file"]))
            b = [0] + [ws[int(x["params"]["from_word"])]["start"] for x in pics[1:]] + [run["duration"]]
            durs = [b[i + 1] - b[i] for i in range(len(pics))]
        else:
            durs = [float(x["inputs"]["out"]) - float(x["inputs"]["in"]) for x in pics]
        for x, d in zip(pics, durs):
            src = SC.resolve(wf["sources"][x["inputs"]["source"][5:]])
            c = cuts(src, float(x["inputs"]["in"]), d)
            if c:
                out.append({"scene": sc["scene"], "step": x["id"], "in": x["inputs"]["in"], "seconds": round(d, 2), "cuts_at": c,
                            "note": x.get("note", "")})
                print(f"{sc['scene']:4} {x['id']:7} in {x['inputs']['in']:7}  {d:4.2f}s  cut at +{c}  {x.get('note','')[:50]}")
    return out


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else sys.exit("name the brief, e.g. " + os.path.basename(__file__) + " 0001")))


def suggest(n):
    """For each shot holding a cut: the nearest stretch of the same clip with no cut that is long enough."""
    found = []
    st = SC.brief_state(n)
    for row in main(n):
        sc = next(x for x in st["scenes"] if x["scene"] == row["scene"])
        x = next(s for s in sc["workflow"]["steps"] if s["id"] == row["step"])
        src = SC.resolve(sc["workflow"]["sources"][x["inputs"]["source"][5:]])
        a0, d = float(row["in"]), row["seconds"]
        lo = max(0.0, a0 - 4)
        c = [lo] + [lo + t for t in cuts(src, lo, 14)] + [lo + 14]
        segs = [(c[i] + 0.06, c[i + 1] - 0.06) for i in range(len(c) - 1) if c[i + 1] - c[i] - 0.12 >= d]
        best = min(segs, key=lambda s: abs(max(s[0], min(a0, s[1] - d)) - a0), default=None)
        new = round(max(best[0], min(a0, best[1] - d)), 2) if best else None
        found.append(dict(row, new_in=new))
        print(f"  → {row['scene']} {row['step']}: in {a0} → {new if new is not None else 'no clean stretch long enough'}")
    return found
