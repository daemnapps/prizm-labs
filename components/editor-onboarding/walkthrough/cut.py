#!/usr/bin/env python3
"""Cut a long screen recording down to the parts that teach — from a cut list.

    python3 cut.py cut-list.json <source.mp4> [--out folder]

The cut list is JSON: chapters, each with a title card and the time ranges to
keep ("MM:SS" or "H:MM:SS"). Every kept range is re-encoded to one common shape
(size, fps, audio), a title card is put in front of each chapter, and the
pieces are joined. Needs ffmpeg and Pillow, both of which this Mac already has.

The source recording never goes in the repo — it is too big and it is a call.
The cut list does, so the edit can be redone or changed by editing text.
"""
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path

FONT = "/System/Library/Fonts/HelveticaNeue.ttc"


def secs(t: str) -> float:
    parts = [float(p) for p in t.split(":")]
    return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def card(text: str, out: Path, size: str, fps: int, seconds: int, small: str = ""):
    """A black title card. Drawn with Pillow, because Homebrew's ffmpeg ships
    without the text filter; ffmpeg then holds the picture for `seconds`."""
    from PIL import Image, ImageDraw, ImageFont
    w, h = (int(v) for v in size.split("x"))
    img = Image.new("RGB", (w, h), "black")
    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(FONT, int(h * 0.061))
    tiny = ImageFont.truetype(FONT, int(h * 0.028))
    lines = text.split("\n")
    y = h // 2 - int(h * 0.047) * len(lines)
    for line in lines:
        tw = d.textlength(line, font=big)
        d.text(((w - tw) / 2, y), line, fill="white", font=big)
        y += int(h * 0.094)
    if small:
        tw = d.textlength(small, font=tiny)
        d.text(((w - tw) / 2, h - int(h * 0.167)), small, fill="#EBFF00", font=tiny)
    png = out.with_suffix(".png")
    img.save(png)
    run(["ffmpeg", "-v", "error", "-y",
         "-loop", "1", "-framerate", str(fps), "-i", str(png),
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", str(seconds), "-vf", f"fade=t=in:st=0:d=0.4,fade=t=out:st={seconds - 0.4}:d=0.4,format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-shortest", str(out)])


def shares_screen(src: Path, t: float, probe: list[int]) -> bool:
    """True when the Meet layout has a shared screen up: the probe box (above
    the webcam tile, right column) is black only in that layout."""
    from PIL import Image, ImageStat
    png = Path(tempfile.gettempdir()) / "probe.png"
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", str(png)])
    x0, y0, x1, y1 = probe
    box = Image.open(png).convert("L").crop((x0, y0, x1, y1))
    return ImageStat.Stat(box).mean[0] < 20


def piece(src: Path, a: float, b: float, out: Path, size: str, fps: int, crf: int = 18, screen: dict | None = None):
    w, h = size.split("x")
    vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={fps}"
    if screen and shares_screen(src, (a + b) / 2, screen["probe"]):
        vf = f"crop={screen['w']}:{screen['h']}:{screen['x']}:{screen['y']},{vf}"
        print("    (shared screen — cropped to it)", flush=True)
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src),
         "-vf", vf,
         "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-af", "afade=t=in:d=0.2",
         str(out)])


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    spec = json.loads(Path(sys.argv[1]).read_text())
    src = Path(sys.argv[2]).expanduser()
    out_dir = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    size, fps, cs = spec.get("size", "1920x1080"), int(spec.get("fps", 24)), int(spec.get("card_seconds", 3))
    crf = int(spec.get("quality", 18))   # x264 crf: 18 is visually lossless for a screen recording
    tmp = Path(tempfile.mkdtemp(prefix="cut-"))
    parts: list[Path] = []
    total = 0.0
    opener = tmp / "00-title.mp4"
    card(spec["title"], opener, size, fps, cs + 1, spec.get("subtitle", ""))
    parts.append(opener)
    for i, ch in enumerate(spec["chapters"], 1):
        c = tmp / f"{i:02d}-card.mp4"
        card(ch["card"], c, size, fps, cs)
        parts.append(c)
        for j, (a, b) in enumerate(ch["keep"]):
            p = tmp / f"{i:02d}-{j}.mp4"
            piece(src, secs(a), secs(b), p, size, fps, crf, spec.get("screen"))
            parts.append(p)
            total += secs(b) - secs(a)
            print(f"  chapter {i} · {a}–{b}", flush=True)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    final = out_dir / spec["output"]
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
         "-movflags", "+faststart", str(final)])
    print(f"done — {final}  ({total/60:.1f} min of footage + cards)")


if __name__ == "__main__":
    main()
