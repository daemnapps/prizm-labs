"""Stage 11 — cut the piece from piece.json, then lay the song so the drop lands on the hero shot.

The format: the real clip plays with its own sound until the hit; the hit starts the song (Sus piano); the scratch drops
into meaningful love exactly on the hero shot's first frame; whole-beat shots to the end; hard cut, no fade.
The hero cut is MEASURED on the rendered picture (scene detection), never taken from the plan: frame rounding moved the
goat's planned 15.79 s cut to 15.58 s, and the drop landed late.

Usage (run inside the piece folder):
  cut.py piece.json            -> measures the cuts, prints D (hero cut - hit); writes nothing else
  cut.py piece.json --song S   -> writes piece.json's "out" with song S delayed to the hit
piece.json keys used:
  fps 24 · hit (s) · beat (s, 0.7663 for meaningful love) · src (the original clip, for its sound)
  clip_volume 0.4 · shots: [[file, start_s, beats], ...] (the first shot's length may be given in seconds as
  "hit+1" meaning hit + 1 beat) · hero_shot (index into shots) · out
"""
import json, os, re, subprocess, sys
spec = json.load(open(sys.argv[1])); SONG = sys.argv[sys.argv.index("--song") + 1] if "--song" in sys.argv else None
os.chdir(os.path.dirname(os.path.abspath(sys.argv[1])))
FPS, HIT, BEAT = spec.get("fps", 24), spec["hit"], spec["beat"]
plan = []
for f, ss, ln in spec["shots"]:
    if isinstance(ln, str) and ln.startswith("hit+"): dur = HIT + float(ln[4:]) * BEAT
    else: dur = float(ln) * BEAT
    plan.append((f, ss, dur))
END = sum(p[2] for p in plan)
def ff(*a): subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)
V = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},setsar=1,format=yuv420p"
parts = []
for i, (f, ss, dur) in enumerate(plan):
    ff("-ss", f"{ss}", "-i", f, "-t", f"{dur}", "-vf", V, "-an", "-c:v", "libx264", "-crf", "16", f"_p{i}.mp4"); parts.append(f"_p{i}.mp4")
open("_l.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
ff("-f", "concat", "-safe", "0", "-i", "_l.txt", "-c:v", "libx264", "-crf", "16", "_v.mp4")
out = subprocess.run(["ffmpeg", "-hide_banner", "-i", "_v.mp4", "-vf", "select='gt(scene,0.3)',showinfo", "-f", "null", "-"], capture_output=True, text=True).stderr
cuts = [round(float(x), 3) for x in re.findall(r"pts_time:([0-9.]+)", out)]
planned = sum(p[2] for p in plan[:spec["hero_shot"]])
hero = min(cuts, key=lambda c: abs(c - planned)) if cuts else planned
print("cuts", cuts, "| hero shot planned", round(planned, 3), "measured", hero, "-> song drop D =", round(hero - HIT, 3))
if SONG:
    ms = int(HIT * 1000); vol = spec.get("clip_volume", 0.4)
    ff("-i", "_v.mp4", "-i", spec["src"], "-i", SONG, "-filter_complex",
       f"[1:a]atrim=0:{HIT+0.6},volume={vol},afade=t=out:st={HIT+0.1}:d=0.5,asetpts=PTS-STARTPTS[o];[2:a]adelay={ms}|{ms}[m];"
       f"[o][m]amix=inputs=2:duration=longest:normalize=0,atrim=0:{END},loudnorm=I=-14:TP=-1.5[a]",
       "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{END}", "-movflags", "+faststart", spec["out"])
    print("wrote", spec["out"], round(END, 2), "s")
for p in parts + ["_v.mp4", "_l.txt"]: os.remove(p)
