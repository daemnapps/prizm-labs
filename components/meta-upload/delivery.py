"""delivery — the one size every ad video is filed and sent at.

The Studio keeps its masters at full quality (crf 16-18, ~20 Mbps). That is right for editing and wrong for Meta:
a 45 s master is ~110 MB, which took ~35 min per video to go up (11 Nov 2026). Meta re-encodes every upload, so
the extra bits never reach a viewer. Every video that lands on an approval card is made to SPEC here, once.

    python3 delivery.py <master.mp4> <out.mp4>     # make one delivery file
    python3 delivery.py --check <file.mp4>         # does a file already meet SPEC
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

SPEC = {
    "width": 1080,          # never upscaled; 9:16 masters come out 1080x1920
    "fps_max": 30,          # a 24/25/30 master keeps its rate; anything faster is brought down to 30
    "video_kbps": 4000,     # 11 Nov 2026: 4 Mbps halves every upload; tested on 0324 V1: SSIM 0.988, PSNR 45 dB vs 8 Mbps, no visible change (was 8000, 1 Nov). Meta re-encodes every upload. Rollback: 8000
    "audio_kbps": 128,
    "codec": "h264",
    "pix_fmt": "yuv420p",
}
SLACK = 1.25                # a file within 25% of the rate is already delivery size


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=bit_rate,duration:stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate",
                        "-of", "json", str(p)], capture_output=True, text=True, timeout=120)
    return json.loads(r.stdout or "{}")


def meets(p):
    """True when the file is already at SPEC (or lighter): nothing to do."""
    d = probe(p)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    try:
        rate = int((d.get("format") or {}).get("bit_rate") or 0)
        n, _, den = (v.get("avg_frame_rate") or "0/1").partition("/")
        fps = float(n) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return False
    return (v.get("codec_name") == SPEC["codec"] and v.get("pix_fmt") == SPEC["pix_fmt"]
            and int(v.get("width") or 0) <= SPEC["width"] and fps <= SPEC["fps_max"] + 0.5
            and 0 < rate <= (SPEC["video_kbps"] + SPEC["audio_kbps"]) * 1000 * SLACK)


def make(src, dst):
    """src -> dst at SPEC. Returns dst. A file already at SPEC is copied as it is."""
    src, dst = Path(src), Path(dst)
    if meets(src):
        shutil.copy2(src, dst)
        return dst
    k = SPEC["video_kbps"]
    tmp = Path(tempfile.mkdtemp(prefix="delivery-")) / dst.name
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
                        "-vf", f"scale='min({SPEC['width']},iw)':-2:flags=lanczos", "-fpsmax", str(SPEC["fps_max"]),
                        "-c:v", "libx264", "-preset", "medium", "-profile:v", "high",
                        "-b:v", f"{k}k", "-maxrate", f"{k * 5 // 4}k", "-bufsize", f"{k * 2}k",
                        "-pix_fmt", SPEC["pix_fmt"], "-c:a", "aac", "-b:a", f"{SPEC['audio_kbps']}k", "-ar", "48000",
                        "-movflags", "+faststart", str(tmp)], check=True, capture_output=True, timeout=3600)
        shutil.move(str(tmp), dst)
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)
    return dst


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        print("meets delivery spec" if meets(sys.argv[2]) else "needs a delivery copy")
    elif len(sys.argv) == 3:
        out = make(sys.argv[1], sys.argv[2])
        print(f"{out}: {out.stat().st_size // 1_000_000} MB")
    else:
        sys.exit(__doc__)
