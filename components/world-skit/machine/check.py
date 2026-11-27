#!/usr/bin/env python3
"""check.py: the standing check that made the first skit work.

    python3 check.py listen <run>                 every scripted word heard, loudness, first-frame black, effects inside their sections
    python3 check.py compare <run> <swipe video>  the swipe and the cut side by side, one frame a second, for a person to read

Writes into the run. Listening by a person is still required: this proves the words landed, not that it's funny."""
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def listen(run):
    run = Path(run)
    sys.path.insert(0, str(ROOT / "components/video-teardown/machine"))
    import transcript as tr
    heard = re.findall(r"[a-z0-9']+", " ".join(w["text"] for w in tr.scribe_only(run / "final.mp4")["words"] if w.get("type", "word") == "word").lower())
    lines = json.loads((run / "lines.json").read_text())
    ad = json.loads((run / "ad.json").read_text())
    want = re.findall(r"[a-z0-9']+", " ".join(lines[r["id"]] for r in ad["timeline"] if r["id"] in lines).lower())
    match = round(difflib.SequenceMatcher(None, want, heard).ratio(), 3)
    log = subprocess.run(["ffmpeg", "-nostats", "-i", str(run / "final.mp4"), "-af", "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    report = {"words_match": match, "lufs": float(lufs[-1]) if lufs else None, "person_listened": False}
    (run / "listen.json").write_text(json.dumps(report, indent=1))
    print(report)


def compare(run, swipe):
    from PIL import Image
    run = Path(run)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(swipe)]))
    frames = []
    for t in range(int(min(dur, 60))):
        row = []
        for v in (swipe, run / "final.mp4"):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t + .01), "-i", str(v), "-frames:v", "1", "-vf", "scale=120:-1", str(run / "_c.png")], check=True)
            row.append(Image.open(run / "_c.png").convert("RGB").copy())
        frames.append(row)
    w, h = frames[0][1].size
    sheet = Image.new("RGB", (w * len(frames), h * 2))
    for i, (a, b) in enumerate(frames):
        sheet.paste(a.resize((w, h)), (i * w, 0))
        sheet.paste(b, (i * w, h))
    sheet.save(run / "compare.jpg", quality=80)
    (run / "_c.png").unlink()
    print(run / "compare.jpg")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "listen":
        listen(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "compare":
        compare(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
