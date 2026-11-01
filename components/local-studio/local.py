#!/usr/bin/env python3
"""local.py — the local studio. One door to every model that runs on this Mac.

    python3 tools/local/local.py <job> <input> [options]

Jobs (each runs in its own environment; this file only needs the system python):

    interp   <video>  -o out.mp4 [--factor 2]            RIFE v4.6 (ncnn/Metal) frame interpolation
    upscale  <image|video> -o out [--scale 2] [--engine esrgan|seedvr2] [--esrgan-model realesrgan-x4plus]
    matte    <image|video> -o out [--model full|lite]     BiRefNet cut-out (PyTorch MPS): RGBA png / ProRes 4444 + WebM with alpha
    segment  <video>  -o outdir --point X,Y [--point ...] SAM 2.1 video tracking (PyTorch MPS): mask video + overlay
    stt      <audio|video> -o out(.json/.srt)             Whisper large-v3-turbo (MLX), word timestamps
    stems    <audio>  -o outdir [--model htdemucs_ft]     Demucs (PyTorch MPS)
    tts      "text"   -o out.wav [--voice am_michael]     Kokoro-82M (MLX), stock voices only
    image    "prompt" -o out.png [-W 1024 -H 1536 --steps 4 --seed 1]   FLUX.2 klein 4B, 4-bit (MLX via mflux)
    edit     "prompt" --ref a.jpg [--ref b.jpg] -o out.png             FLUX.2 klein 4B edit, 4-bit (MLX via mflux)
    3d       <image>  -o out.glb                         TRELLIS.2 image-to-3D (components/3d/make3d), textured GLB
    i2v      <image>  "prompt" -o out.mp4 [--seconds 4 -W 704 -H 1280] LTX-2.5 distilled, 4-bit (MLX), video + audio
    runs                                                 print the timing log

Every run is timed and its peak memory recorded (macOS `time -l`), appended to
runs/local-studio/_system/runs.jsonl (the repo's runs plane). Weights live in tools/local/models/ (never committed).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
MODELS = ROOT / "models"
AV_BIN = REPO / "tools" / "av" / "bin"
RIFE = AV_BIN / "rife-ncnn-vulkan-20221029-macos"
ESRGAN_BIN = "realesrgan-ncnn-vulkan"
AV_PY = (ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv" / "bin" / "python").exists() else REPO / "tools" / "av" / ".venv" / "bin" / "python"      # torch 2.x + MPS, demucs, SAM-2, transformers
MLX_BIN = ROOT / ".venv-mlx" / "bin"                                # mflux, mlx-whisper, mlx-audio
LTX_BIN = ROOT / "src" / "ltx-2-mlx" / ".venv" / "bin" / "ltx-2-mlx"
LTX_PACK = MODELS / "ltx-2.5-mlx-q4"
SAM2_CKPT = (ROOT / "models" / "sam2" / "sam2.1_hiera_small.pt") if (ROOT / "models" / "sam2" / "sam2.1_hiera_small.pt").exists() else REPO / "tools" / "av" / "models" / "sam2" / "sam2.1_hiera_small.pt"
RUNS = REPO / "runs" / "local-studio" / "_system" / "runs.jsonl"

FLUX2_Q4 = "mflux-community/flux2-klein-4b-mflux-q4"
SEEDVR2 = str(MODELS / "seedvr2-3b")                                   # numz/SeedVR2_comfyUI fp16 3B + VAE
WHISPER = "mlx-community/whisper-large-v3-turbo"
KOKORO = "mlx-community/Kokoro-82M-bf16"

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}


def esrgan_places() -> list:
    """Where Real-ESRGAN (ncnn) may live, in the order looked: the folder named by REALESRGAN_DIR,
    this component's models/realesrgan, the workspace's tools/av/bin/realesrgan, then the
    realesrgan-ncnn-vulkan on PATH. Found, never hard-coded (2026-10-10: the job pointed at a
    tools/av path this repo does not have, so the first song ad was upscaled from another checkout)."""
    out = []
    if os.environ.get("REALESRGAN_DIR"):
        out.append(Path(os.environ["REALESRGAN_DIR"]).expanduser())
    out += [MODELS / "realesrgan", AV_BIN / "realesrgan"]
    on_path = shutil.which(ESRGAN_BIN)
    if on_path:
        out.append(Path(on_path).resolve().parent)
    return out


def esrgan_dir() -> Path:
    """The Real-ESRGAN folder: the binary and its models/ side by side. None found: stop, naming every place looked."""
    places = esrgan_places()
    for d in places:
        if (d / ESRGAN_BIN).is_file() and (d / "models").is_dir():
            return d
    raise SystemExit("upscale: Real-ESRGAN not found — looked in " + ", ".join(str(d) for d in places)
                     + f" (each needs {ESRGAN_BIN} and models/ side by side). Put it in {MODELS / 'realesrgan'}, "
                       "or name its folder in REALESRGAN_DIR.")


def env(shared_hf_cache: bool = False, offline: bool = True) -> dict:
    e = dict(os.environ)
    if offline:                             # weights already here: never wait on the network
        e["HF_HUB_OFFLINE"] = "1"
    if not shared_hf_cache:                 # new weights land in tools/local/models, one folder to delete
        e["HF_HOME"] = str(MODELS / "hf")
    e["TORCH_HOME"] = str(MODELS / "torch")
    e["HF_HUB_DISABLE_TELEMETRY"] = "1"
    e["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    e["PATH"] = f"{MLX_BIN}:{e.get('PATH', '')}"
    return e


def run(cmd, job: str, meta: dict | None = None, cwd=None, shared_hf_cache=False) -> dict:
    """Run one step under `time -l`; log wall time + peak memory footprint."""
    cmd = [str(c) for c in cmd]
    t = time.time()
    p = subprocess.run(["/usr/bin/time", "-l", *cmd], cwd=cwd, env=env(shared_hf_cache), stderr=subprocess.PIPE, text=True)
    err = p.stderr
    if p.returncode != 0 and re.search(r"offline|LocalEntryNotFound|OfflineModeIsEnabled|not.*cached", err, re.I):
        print(f"[{job}] weights not on this Mac yet, downloading once…", file=sys.stderr)
        t = time.time()                     # first run: fetch weights, then time the real run
        p = subprocess.run(["/usr/bin/time", "-l", *cmd], cwd=cwd, env=env(shared_hf_cache, offline=False), stderr=subprocess.PIPE, text=True)
        err = p.stderr
    wall = time.time() - t
    m = re.search(r"(\d+)\s+peak memory footprint", err)
    peak = int(m.group(1)) / 1e9 if m else None
    if p.returncode != 0:
        sys.stderr.write(err[-4000:])
        raise SystemExit(f"[{job}] failed (exit {p.returncode})")
    rec = {"job": job, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(wall, 2),
           "peak_gb": round(peak, 2) if peak else None, **(meta or {})}
    RUNS.parent.mkdir(parents=True, exist_ok=True)
    with RUNS.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))
    return rec


def probe(path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True).stdout
    d = json.loads(out or "{}")
    s = (d.get("streams") or [{}])[0]
    num, den = (s.get("r_frame_rate") or "30/1").split("/")
    return {"w": s.get("width"), "h": s.get("height"), "fps": float(num) / float(den),
            "fps_str": s.get("r_frame_rate") or "30/1", "duration": float(d.get("format", {}).get("duration") or 0)}


def frames_out(video, d: Path, fmt="png"):
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), str(d / f"%08d.{fmt}")], check=True)
    return sorted(d.glob(f"*.{fmt}"))


def frames_in(d: Path, fps: str, out, audio_from=None, fmt="png"):
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", fps, "-i", str(d / f"%08d.{fmt}")]
    if audio_from:
        cmd += ["-i", str(audio_from), "-map", "0:v", "-map", "1:a?", "-c:a", "copy", "-shortest"]
    cmd += ["-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)


# ------------------------------------------------------------------ jobs
def job_interp(a):
    p = probe(a.input)
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        src = frames_out(a.input, t / "in")
        n = len(src) * a.factor
        (t / "out").mkdir()
        rec = run([RIFE / "rife-ncnn-vulkan", "-i", t / "in", "-o", t / "out", "-m", RIFE / a.model, "-n", n],
                  "interp", {"tool": f"RIFE {a.model} (ncnn/Metal)", "input": str(a.input), "in_frames": len(src),
                             "out_frames": n, "in_res": f"{p['w']}x{p['h']}", "video_seconds": round(p["duration"], 2)})
        fps = f"{p['fps'] * a.factor:g}"
        frames_in(t / "out", fps, a.output, audio_from=a.input)
    print(a.output)


def job_upscale(a):
    is_video = Path(a.input).suffix.lower() in VIDEO_EXT
    if a.engine == "seedvr2":
        target = f"{a.scale}x"
        if is_video:
            p = probe(a.input)
            with tempfile.TemporaryDirectory() as t:
                t = Path(t)
                src = frames_out(a.input, t / "in")
                rec = run([MLX_BIN / "python", ROOT / "jobs" / "seedvr2_frames.py", t / "in", t / "out", SEEDVR2, a.scale],
                          "upscale", {"tool": "SeedVR2 3B 8-bit (MLX, per frame)", "input": str(a.input), "frames": len(src),
                                      "in_res": f"{p['w']}x{p['h']}", "scale": a.scale, "video_seconds": round(p["duration"], 2)})
                frames_in(t / "out", p["fps_str"], a.output, audio_from=a.input)
        else:
            run([MLX_BIN / "mflux-upscale-seedvr2", "--model", SEEDVR2, "--base-model", "seedvr2-3b", "-q", "8", "--image-path", a.input, "--resolution", target,
                 "--softness", a.softness, "--seed", "42", "--output", Path(a.output).resolve()],
                "upscale", {"tool": "SeedVR2 3B 8-bit (MLX)", "input": str(a.input), "scale": a.scale, "images": 1})
        print(a.output)
        return
    # Real-ESRGAN ncnn. Single-thread load/proc/save: multi-thread scrambled frames in Carousel.
    ESRGAN = esrgan_dir()
    model = a.esrgan_model
    scale = a.scale if model.startswith("realesr-animevideov3") else 4
    if is_video:
        p = probe(a.input)
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            src = frames_out(a.input, t / "in")
            (t / "out").mkdir()
            run([ESRGAN / "realesrgan-ncnn-vulkan", "-i", t / "in", "-o", t / "out", "-m", ESRGAN / "models", "-n", model,
                 "-s", scale, "-f", "png", "-j", "1:1:1", "-t", "256"], "upscale",
                {"tool": f"Real-ESRGAN {model} x{scale} (ncnn/Metal)", "input": str(a.input), "frames": len(src),
                 "in_res": f"{p['w']}x{p['h']}", "scale": scale, "video_seconds": round(p["duration"], 2)}, cwd=ESRGAN)
            if scale != a.scale:  # x4 models: bring down to the asked scale with lanczos
                (t / "sc").mkdir()
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", p["fps_str"], "-i", t / "out" / "%08d.png", "-vf",
                                f"scale={p['w'] * a.scale}:{p['h'] * a.scale}:flags=lanczos", t / "sc" / "%08d.png"], check=True)
                shutil.rmtree(t / "out"); (t / "sc").rename(t / "out")
            frames_in(t / "out", p["fps_str"], a.output, audio_from=a.input)
    else:
        run([ESRGAN / "realesrgan-ncnn-vulkan", "-i", Path(a.input).resolve(), "-o", Path(a.output).resolve(), "-m",
             ESRGAN / "models", "-n", model, "-s", scale, "-t", "256"], "upscale",
            {"tool": f"Real-ESRGAN {model} x{scale} (ncnn/Metal)", "input": str(a.input), "images": 1}, cwd=ESRGAN)
        if scale != a.scale:  # x4 model: bring down to the asked scale
            o = Path(a.output).resolve(); tmp = o.with_name(o.stem + ".tmp" + o.suffix)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", o, "-vf", f"scale=iw*{a.scale}/{scale}:ih*{a.scale}/{scale}:flags=lanczos", tmp], check=True)
            tmp.replace(o)
    print(a.output)


def job_matte(a):
    run([AV_PY, ROOT / "jobs" / "matte.py", a.input, a.output, "--model", a.model], "matte",
        {"tool": f"BiRefNet {a.model} (PyTorch MPS)", "input": str(a.input)}, shared_hf_cache=True)


def job_segment(a):
    cmd = [AV_PY, ROOT / "jobs" / "segment.py", a.input, a.output, "--ckpt", SAM2_CKPT]
    for pt in a.point or []:
        cmd += ["--point", pt]
    if a.box:
        cmd += ["--box", a.box]
    if a.seconds:
        cmd += ["--seconds", a.seconds]
    p = probe(a.input)
    run(cmd, "segment", {"tool": "SAM 2.1 hiera-small (PyTorch MPS)", "input": str(a.input), "in_res": f"{p['w']}x{p['h']}",
                         "video_seconds": min(p["duration"], a.seconds or 1e9)})


def job_stt(a):
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(a.input)],
                               capture_output=True, text=True).stdout.strip() or 0)
    run([MLX_BIN / "mlx_whisper", a.input, "--model", WHISPER, "--word-timestamps", "True", "--output-format", "all",
         "--output-dir", out.parent, "--output-name", out.stem,
         "--condition-on-previous-text", "True" if a.context else "False",
         "--hallucination-silence-threshold", "2", *(["--language", a.language] if a.language else [])],
        "stt", {"tool": "Whisper large-v3-turbo (mlx-whisper)", "input": str(a.input), "audio_seconds": round(dur, 2)})


def job_stems(a):
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(a.input)],
                               capture_output=True, text=True).stdout.strip() or 0)
    run([AV_PY, "-m", "demucs", "-n", a.model, "-d", "mps", "-o", a.output, a.input], "stems",
        {"tool": f"Demucs {a.model} (PyTorch MPS)", "input": str(a.input), "audio_seconds": round(dur, 2)})


def job_tts(a):
    out = Path(a.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    run([MLX_BIN / "python", ROOT / "jobs" / "tts.py", a.input, out, "--voice", a.voice, "--model", KOKORO,
         "--speed", a.speed], "tts", {"tool": "Kokoro-82M bf16 (MLX)", "voice": a.voice, "chars": len(a.input)})


def job_image(a):
    run([MLX_BIN / "mflux-generate-flux2", "--model", FLUX2_Q4, "--base-model", "flux2-klein-4b", "--prompt", a.input,
         "--width", a.W, "--height", a.H, "--steps", a.steps, "--seed", a.seed, "--output", a.output],
        "image", {"tool": "FLUX.2 klein 4B q4 (mflux/MLX)", "res": f"{a.W}x{a.H}", "steps": a.steps, "images": 1})


def job_edit(a):
    run([MLX_BIN / "mflux-generate-flux2-edit", "--model", FLUX2_Q4, "--base-model", "flux2-klein-4b", "--prompt", a.input,
         "--image-paths", *a.ref, "--steps", a.steps, "--seed", a.seed, "--output", a.output,
         *(["--width", a.W, "--height", a.H] if a.W else [])],
        "edit", {"tool": "FLUX.2 klein 4B q4 edit (mflux/MLX)", "refs": a.ref, "steps": a.steps, "images": 1})


def job_i2v(a):
    if not (LTX_PACK / "transformer-distilled.safetensors").exists():
        raise SystemExit("i2v is not installed: the LTX-2.5 distilled 4-bit pack (~29 GB) is not on this Mac. "
                         "Image-to-video runs on Seedance (Higgsfield). See README.md, 'Not local'.")
    frames = int(round(a.seconds * 24 / 8)) * 8 + 1          # LTX frame grid: 8n+1
    run([LTX_BIN, "generate", "--distilled", "--model", LTX_PACK, "--image", a.input, "--prompt", a.prompt,
         "-H", a.H, "-W", a.W, "-f", frames, "--frame-rate", "24", "--seed", a.seed, "-o", a.output],
        "i2v", {"tool": "LTX-2.5 distilled q4 (MLX)", "input": str(a.input), "res": f"{a.W}x{a.H}", "frames": frames,
                "video_seconds": round(frames / 24, 2)})


def job_object3d(a):
    run([REPO / "components" / "3d" / "make3d", a.input, a.output, *(["--seed", a.seed] if a.seed else [])], "3d",
        {"tool": "TRELLIS.2-4B (trellis-mac, PyTorch MPS) + Blender finish", "input": str(a.input), "objects": 1}, shared_hf_cache=True)


def job_runs(a):
    if not RUNS.exists():
        print("no runs yet")
        return
    for line in RUNS.read_text().splitlines():
        r = json.loads(line)
        print(f"{r['when']}  {r['job']:<8} {r['seconds']:>8.1f}s  peak {r.get('peak_gb')} GB  {r.get('tool', '')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="job", required=True)

    s = sub.add_parser("interp"); s.add_argument("input"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--factor", type=int, default=2); s.add_argument("--model", default="rife-v4.6")

    s = sub.add_parser("upscale"); s.add_argument("input"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--scale", type=int, default=2); s.add_argument("--engine", choices=["esrgan", "seedvr2"], default="esrgan")
    s.add_argument("--esrgan-model", default="realesrgan-x4plus"); s.add_argument("--softness", default="0.0")

    s = sub.add_parser("matte"); s.add_argument("input"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--model", choices=["full", "lite"], default="full")

    s = sub.add_parser("segment"); s.add_argument("input"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--point", action="append"); s.add_argument("--box"); s.add_argument("--seconds", type=float)

    s = sub.add_parser("stt"); s.add_argument("input"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--language")
    s.add_argument("--context", action="store_true", help="feed the last line into the next (off by default: it caused repeat loops on the song)")

    s = sub.add_parser("stems"); s.add_argument("input"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--model", default="htdemucs_ft")

    s = sub.add_parser("tts"); s.add_argument("input"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--voice", default="am_michael"); s.add_argument("--speed", default="1.0")

    s = sub.add_parser("image"); s.add_argument("input"); s.add_argument("-o", "--output", required=True)
    s.add_argument("-W", default="1024"); s.add_argument("-H", default="1536")
    s.add_argument("--steps", default="4"); s.add_argument("--seed", default="1")

    s = sub.add_parser("edit"); s.add_argument("input"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--ref", action="append", required=True); s.add_argument("-W"); s.add_argument("-H")
    s.add_argument("--steps", default="4"); s.add_argument("--seed", default="1")

    s = sub.add_parser("i2v"); s.add_argument("input"); s.add_argument("prompt"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--seconds", type=float, default=4); s.add_argument("-W", default="704"); s.add_argument("-H", default="1280")
    s.add_argument("--seed", default="42")

    s = sub.add_parser("3d"); s.add_argument("input"); s.add_argument("-o", "--output", required=True); s.add_argument("--seed")

    sub.add_parser("runs")
    a = ap.parse_args()
    globals()["job_object3d" if a.job == "3d" else f"job_{a.job}"](a)


if __name__ == "__main__":
    main()
