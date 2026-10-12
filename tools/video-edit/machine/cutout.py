#!/usr/bin/env python3
"""cutout.py — a true cut-out of the presenter for a greenscreen `cutout` scene:
BiRefNet (MIT) mattes every frame, and the result is an alpha PNG sequence plus an
alpha WebM (VP9, yuva420p) the edit can stand in front of the plate.

    python3 machine/cutout.py <clip> [--from s] [--seconds 2] [--out <dir>] [--model lite|full]
    python3 machine/cutout.py <clip> --dry-run      what it would do, the model, the download — nothing run
    attach(sheet, root, make_missing=True)          the edit's door: every greenscreen `cutout` scene gets its
                                                    presenter's alpha WebM, made once and cached by picture hash
                                                    (.cache/cutout/, gitignored) — compose stands it on the plate

Runs in the helpers venv (torch + transformers; the weights come from the author's own
Hugging Face repo, ZhengPeng7/BiRefNet_lite — MIT — on first use, cached by Hugging Face).
It never touches the source clip. Speed on this Mac is printed per frame; the lite model
at 1024² on Apple-silicon MPS is the default, CPU is the fallback.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
sys.path.insert(0, str(HERE))
MODELS = {"lite": "ZhengPeng7/BiRefNet_lite", "full": "ZhengPeng7/BiRefNet"}


def matte_here(clip: str, out: str, t0: float, seconds: float, model: str, size: int = 1024, keep_frames: bool = True) -> dict:
    import numpy as np
    import torch
    from PIL import Image
    from torchvision import transforms
    from transformers import AutoModelForImageSegmentation
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    t_load = time.time()
    net = AutoModelForImageSegmentation.from_pretrained(MODELS[model], trust_remote_code=True).to(dev).eval()
    t_load = time.time() - t_load
    o = Path(out); (o / "frames").mkdir(parents=True, exist_ok=True)
    src = o / "src"; src.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-i", clip, "-t", str(seconds), str(src / "%04d.png")], check=True)
    fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", clip],
                         capture_output=True, text=True).stdout.strip() or "30"
    tf = transforms.Compose([transforms.Resize((size, size)), transforms.ToTensor(),
                             transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    per = []
    frames = sorted(src.glob("*.png"))
    for f in frames:
        img = Image.open(f).convert("RGB")
        t = time.time()
        with torch.no_grad():
            pred = net(tf(img).unsqueeze(0).to(dev))[-1].sigmoid().cpu()[0].squeeze()
        per.append(time.time() - t)
        mask = transforms.ToPILImage()(pred).resize(img.size)
        img.putalpha(mask)
        img.save(o / "frames" / f.name)
    webm = o / "cutout.webm"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", fps, "-i", str(o / "frames" / "%04d.png"), "-c:v", "libvpx-vp9",
                    "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30", "-auto-alt-ref", "0", str(webm)], check=True)
    for f in frames:
        f.unlink()
    src.rmdir()
    if not keep_frames:  # the edit draws the WebM; the RGBA frames are ~1 MB each and are not kept in the cache
        for f in (o / "frames").glob("*.png"):
            f.unlink()
        (o / "frames").rmdir()
    return {"frames": len(frames), "device": dev, "model": MODELS[model], "load_s": round(t_load, 1), "fps": fps,
            "per_frame_s": round(sum(per) / len(per), 3) if per else None, "png_sequence": str(o / "frames") if keep_frames else None, "webm": str(webm),
            "torch": torch.__version__}


CACHE = TOOL / ".cache" / "cutout"   # gitignored; one folder per picture hash + model


def picture_hash(path: Path) -> str:
    """The hash of the PICTURE only (the video stream's packets, copied, not decoded) — so a
    levelled copy of a clip (same picture, new sound) finds the cut-out already made."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, text=True)
    if r.returncode == 0 and "MD5=" in r.stdout:
        return r.stdout.strip().split("MD5=")[1][:32]
    import hashlib
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def seconds_of(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def cached(src: Path, model: str = "lite", h: str | None = None) -> dict | None:
    d = CACHE / f"{(h or picture_hash(src))[:16]}-{model}"
    meta = d / "cutout.json"
    if meta.is_file():
        m = json.loads(meta.read_text())
        if Path(m.get("webm", "")).is_file():
            return {**m, "cached": True}
    return None


def make(src: Path, model: str = "lite") -> dict:
    """The whole clip cut out once (every part of the cut then reads its own stretch of it by
    data-media-start), cached by the picture's hash. Returns the cache record."""
    h = picture_hash(src)
    got = cached(src, model, h)
    if got:
        return got
    import helpers
    d = CACHE / f"{h[:16]}-{model}"
    d.mkdir(parents=True, exist_ok=True)
    (CACHE / ".gitignore").write_text("*\n") if not (CACHE / ".gitignore").exists() else None
    secs = seconds_of(src)
    t = time.time()
    r = helpers.call("cutout.py", str(src), "--from", "0", "--seconds", str(secs), "--out", str(d), "--model", model, "--here", "--drop-frames", timeout=7200)
    made = time.time() - t
    webm = d / f"{h[:16]}.webm"  # a unique name: compose copies it into the page's assets by name
    Path(r["webm"]).replace(webm)
    rec = {"hash": h, "source": str(src), "seconds": round(secs, 3), "frames": r["frames"], "fps": r.get("fps"), "device": r["device"],
           "model": r["model"], "per_frame_s": r["per_frame_s"], "load_s": r["load_s"], "made_s": round(made, 1),
           "per_video_second_s": round(made / secs, 2) if secs else None, "webm": str(webm), "licence": "BiRefNet — MIT (code and weights)"}
    (d / "cutout.json").write_text(json.dumps(rec, indent=1))
    return {**rec, "cached": False}


def attach(sheet: dict, root: Path, make_missing: bool = True, maker=None) -> list[str]:
    """Every greenscreen `cutout` scene gets `cutout: {webm, hash, cached, ...}` — made (or found
    in the cache) from its presenter clip. No venv, a failure, or a dry run: nothing is set,
    compose shows the presenter whole and the gate WARNS."""
    notes, done = [], {}
    for c in sheet.get("picture") or []:
        if c.get("kind") != "greenscreen" or (c.get("greenscreen") or {}).get("layout") != "cutout":
            continue
        src = Path(c["src"]) if Path(c["src"]).is_absolute() else Path(root) / c["src"]
        key = str(src)
        try:
            if key not in done:
                done[key] = (maker or make)(src) if make_missing else cached(src)
            rec = done[key]
        except Exception as e:
            notes.append(f"cut-out not made for {c['id']} ({type(e).__name__}: {str(e)[:160]}) — the presenter shows whole")
            continue
        if not rec:
            notes.append(f"cut-out for {c['id']}: not in the cache — a dry run makes none; the real run cuts it out")
            continue
        c["cutout"] = {k: rec.get(k) for k in ("webm", "hash", "cached", "per_video_second_s", "per_frame_s", "device", "model")}
        notes.append(f"cut-out: {c['id']} — " + ("from the cache" if rec.get("cached") else
                     f"made in {rec['made_s']}s ({rec['per_video_second_s']}s per second of video, {rec['per_frame_s']}s a frame on {rec['device']})"))
    return notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip"); ap.add_argument("--from", dest="t0", type=float, default=0.0); ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--out"); ap.add_argument("--model", choices=list(MODELS), default="lite"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--here", action="store_true", help=argparse.SUPPRESS); ap.add_argument("--drop-frames", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    out = a.out or str(Path.cwd() / (Path(a.clip).stem + ".cutout"))  # never beside the source: a production run is read-only
    if a.here:
        print(json.dumps(matte_here(a.clip, out, a.t0, a.seconds, a.model, keep_frames=not a.drop_frames))); return 0
    if a.dry_run:
        import helpers
        print(json.dumps({"dry_run": True, "clip": a.clip, "from": a.t0, "seconds": a.seconds, "model": MODELS[a.model],
                          "licence": "MIT (code and weights)", "download": "weights from huggingface.co on first use (lite ≈ 180 MB, full ≈ 900 MB)",
                          "writes": [f"{out}/frames/0001.png … (RGBA)", f"{out}/cutout.webm (VP9 + alpha)"],
                          "venv": str(helpers.python() or "not built")}, indent=1)); return 0
    import helpers
    got = helpers.call("cutout.py", a.clip, "--from", str(a.t0), "--seconds", str(a.seconds), "--out", out, "--model", a.model, "--here", timeout=3600)
    print(json.dumps(got, indent=1)); return 0


if __name__ == "__main__":
    sys.exit(main())
