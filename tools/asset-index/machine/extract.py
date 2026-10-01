#!/usr/bin/env python3
"""
Pull everything a clip record needs, locally and for free:
frames, transcript, and the measurements. Nothing here calls a model.

  python3 extract.py "<folder>" <out_dir> [--limit N]

Writes runs/asset-index/<brand>/<label>/<clip-id>/ containing frames + clip.json.
"""
import json, os, subprocess, sys, glob, hashlib
from pathlib import Path

VIDEO_EXT = {".mp4", ".mov", ".m4v"}
FRAME_W = 384
MAX_FRAMES = 6
SEC_PER_FRAME = 8


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(path)])
    if r.returncode != 0:
        return None
    try:
        d = json.loads(r.stdout)
    except Exception:
        return None
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    dur = float(d.get("format", {}).get("duration", 0) or 0)
    return {
        "duration_s": round(dur, 2),
        "width": v.get("width"),
        "height": v.get("height"),
        "has_audio": a is not None,
        "size_mb": round(os.path.getsize(path) / 1048576, 1),
    }


def extract(path, outdir, meta):
    outdir.mkdir(parents=True, exist_ok=True)
    dur = meta["duration_s"] or 1
    n = max(1, min(MAX_FRAMES, int(dur // SEC_PER_FRAME) + 1))
    interval = max(1.0, dur / n)
    run(["ffmpeg", "-v", "error", "-i", str(path),
         "-vf", f"fps=1/{interval:.3f},scale={FRAME_W}:-1",
         "-frames:v", str(n), str(outdir / "f_%02d.jpg"), "-y"])
    frames = sorted(p.name for p in outdir.glob("f_*.jpg"))
    stamps = [round(i * interval, 1) for i in range(len(frames))]
    return [{"file": f, "t": t} for f, t in zip(frames, stamps)]


def transcribe(path, outdir, model):
    wav = outdir / "audio.wav"
    run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1",
         "-ar", "16000", "-c:a", "pcm_s16le", str(wav), "-y"])
    if not wav.exists():
        return []
    try:
        segs, _ = model.transcribe(str(wav), beam_size=1)
        out = [{"start": round(s.start, 1), "end": round(s.end, 1),
                "text": s.text.strip()} for s in segs]
    except Exception as e:
        out = [{"error": str(e)}]
    wav.unlink(missing_ok=True)
    return out


def runs_root() -> Path:
    """runs/asset-index/<brand>/<label>/ in the repo, per runs/README.md."""
    here = Path(__file__).resolve()
    for d in here.parents:
        if (d / "runs" / "README.md").exists():
            return d / "runs" / "asset-index"
    return here.parent.parent / "runs"


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("footage", help="a folder of video, read recursively")
    ap.add_argument("--brand", required=True, help="the brand this footage belongs to — names where the records land")
    ap.add_argument("--label", help="a name for this pull (default: the footage folder's own name)")
    ap.add_argument("--out", help="override the output folder entirely")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    src = Path(a.footage)
    label = a.label or src.name
    out = Path(a.out) if a.out else runs_root() / a.brand / label
    limit = a.limit

    files = [p for p in sorted(src.rglob("*")) if p.suffix.lower() in VIDEO_EXT]
    if limit:
        files = files[:limit]
    out.mkdir(parents=True, exist_ok=True)

    from faster_whisper import WhisperModel
    model = WhisperModel("base.en", device="cpu", compute_type="int8")

    done = 0
    for p in files:
        cid = hashlib.sha1(str(p).encode()).hexdigest()[:10]
        d = out / cid
        if (d / "clip.json").exists():
            done += 1
            continue
        meta = probe(p)
        if not meta:
            print(f"SKIP (unreadable) {p.name}", flush=True)
            continue
        frames = extract(p, d, meta)
        tr = transcribe(p, d, model) if meta["has_audio"] else []
        rec = {
            "clip_id": cid,
            "path": str(p),
            "filename": p.name,
            "folder": str(p.parent.relative_to(src)) if p.parent != src else ".",
            "meta": meta,
            "frames": frames,
            "transcript": tr,
        }
        (d / "clip.json").write_text(json.dumps(rec, indent=1))
        done += 1
        words = sum(len(s.get("text", "").split()) for s in tr)
        print(f"[{done}/{len(files)}] {p.name}  {meta['duration_s']}s  "
              f"{len(frames)} frames  {words} words", flush=True)

    print(f"\nDONE — {done} clips prepared in {out}")


if __name__ == "__main__":
    main()
