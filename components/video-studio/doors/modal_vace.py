# PARKED 2026-11-09, not used: wired into nothing (no take route, no house job), kept so the own-GPU route can return without being rebuilt; parked to keep the take routes simple. Never rendered: it waits on a Modal token.
"""Wan 2.2 VACE Fun (pose) on our own Modal GPU: a backup for when a hosted provider's checker blocks an ordinary shot.

Same inputs as fal's `fal-ai/wan-22-vace-fun-a14b/pose`: a first frame, a motion clip and a prompt. The motion clip's
poses (bodies, hands, faces) are tracked inside the app, then drive the first frame frame for frame. 16 fps, 4n+1 frames
(at most 241), 480p. No checker: the open weights run as published.

    modal run modal_vace.py --picture start.png --motion clip.mp4 --prompt "..." --out take.mp4 [--seconds 14]

Writes take.mp4, take.pose.mp4 (the tracked poses) and take.modal.json (timings, GPU, measured cost). Nothing stays
running: the app lives only for the call. The weights (about 81 GB) are cached once on the Modal volume `vace-weights`.
Keys: MODAL_TOKEN_ID / MODAL_TOKEN_SECRET in the environment.
"""
import io
import json
import time
from pathlib import Path

import modal

MODEL = "linoyts/Wan2.2-VACE-Fun-14B-diffusers"     # Wan 2.2 VACE Fun A14B in diffusers form (two experts, boundary 0.875)
WEIGHTS = "/weights"
MAX_FRAMES = 241
FPS = 16
SIZES = {"9:16": (480, 832), "16:9": (832, 480), "1:1": (624, 624)}       # width, height; multiples of 16
# Modal list prices (modal.com/pricing, read 2026-11-09), USD a second, for the measured cost in the receipt.
GPU_USD_S = {"B200": 0.001736, "H200": 0.001261, "H100": 0.001097, "L4": 0.000222}
NEGATIVE = ("text, captions, logos, watermark, flash, still camera, extra people, changed clothes, blurry, low quality, "
            "deformed hands, extra fingers, distorted faces")

app = modal.App("vace-pose")
weights = modal.Volume.from_name("vace-weights", create_if_missing=True)

render_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install("torch==2.8.0", "diffusers==0.42.1", "transformers>=4.55,<5", "accelerate>=1.10", "sentencepiece",
                 "ftfy", "imageio[ffmpeg]", "huggingface_hub>=0.34", "numpy<3", "pillow")
    .env({"HF_HOME": f"{WEIGHTS}/hf"})
)
pose_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install("torch==2.8.0", "torchvision==0.23.0", "controlnet_aux==0.0.10", "timm==0.9.16", "opencv-python-headless",
                 "huggingface_hub>=0.34", "numpy<2", "pillow", "scipy", "scikit-image", "einops")
)


def _cover(img, w, h):
    """Crop to the target shape from the centre, then resize: nothing stretched."""
    from PIL import Image
    sw, sh = img.size
    s = max(w / sw, h / sh)
    img = img.resize((round(sw * s), round(sh * s)), Image.LANCZOS)
    l, t = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((l, t, l + w, t + h))


@app.function(image=render_image, volumes={WEIGHTS: weights}, timeout=7200, cpu=4, memory=16384)
def fetch():
    """Once: the weights onto the volume (CPU only, no GPU time)."""
    from huggingface_hub import snapshot_download
    t = time.time()
    snapshot_download(MODEL, local_dir=f"{WEIGHTS}/model", max_workers=16)
    Path(f"{WEIGHTS}/model/.complete").write_text(MODEL)
    weights.commit()
    return round(time.time() - t, 1)


@app.function(image=pose_image, gpu="L4", timeout=1800)
def poses(motion: bytes, frames: int, width: int, height: int) -> bytes:
    """The motion clip at 16 fps, cropped to the take's shape, every frame's body, hands and face tracked and drawn as
    a pose picture; returned as a lossless-enough mp4."""
    import subprocess
    import tempfile
    from PIL import Image
    from controlnet_aux.open_pose import OpenposeDetector
    t0 = time.time()
    det = OpenposeDetector.from_pretrained("lllyasviel/Annotators").to("cuda")
    d = Path(tempfile.mkdtemp())
    (d / "in.mp4").write_bytes(motion)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(d / "in.mp4"), "-vf", f"fps={FPS}", "-frames:v", str(frames),
                    str(d / "f%04d.png")], check=True)
    for i, f in enumerate(sorted(d.glob("f*.png"))):
        img = _cover(Image.open(f).convert("RGB"), width, height)
        p = det(img, detect_resolution=max(width, height), image_resolution=max(width, height), include_body=True,
                include_hand=True, include_face=True, output_type="pil")
        p.resize((width, height)).save(d / f"p{i:04d}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(d / "p%04d.png"), "-c:v", "libx264",
                    "-crf", "10", "-pix_fmt", "yuv420p", str(d / "pose.mp4")], check=True)
    print(f"poses: {len(list(d.glob('p*.png')))} frames in {time.time() - t0:.0f} s", flush=True)
    return (d / "pose.mp4").read_bytes()


@app.cls(image=render_image, volumes={WEIGHTS: weights}, gpu=["B200", "H200", "H100"], memory=131072, timeout=5400)
class Vace:
    @modal.enter()
    def load(self):
        import torch
        from diffusers import AutoencoderKLWan, WanVACEPipeline
        t = time.time()
        src = f"{WEIGHTS}/model"
        vae = AutoencoderKLWan.from_pretrained(src, subfolder="vae", torch_dtype=torch.float32)
        self.pipe = WanVACEPipeline.from_pretrained(src, vae=vae, torch_dtype=torch.bfloat16)
        self.gpu = torch.cuda.get_device_name(0)
        mem = torch.cuda.get_device_properties(0).total_memory / 2**30
        if mem > 120:                                   # B200 / H200: both experts and the text encoder stay on the card
            self.pipe.to("cuda")
            self.offload = False
        else:                                           # H100: the idle expert waits in memory
            self.pipe.enable_model_cpu_offload()
            self.offload = True
        self.load_s = round(time.time() - t, 1)

    @modal.method()
    def render(self, picture: bytes, pose: bytes, prompt: str, negative: str, refs: list, width: int, height: int,
               steps: int, guidance: float, seed: int) -> dict:
        import tempfile
        import imageio.v3 as iio
        import torch
        from PIL import Image
        from diffusers.utils import export_to_video
        t = time.time()
        first = _cover(Image.open(io.BytesIO(picture)).convert("RGB"), width, height)
        frames = [Image.fromarray(a).convert("RGB").resize((width, height)) for a in iio.imiter(pose, extension=".mp4")]
        n = min(MAX_FRAMES, (len(frames) - 1) // 4 * 4 + 1)
        # VACE: black mask = keep (our exact first frame), white mask = make (every later frame, driven by its pose)
        video = [first] + frames[1:n]
        mask = [Image.new("L", (width, height), 0)] + [Image.new("L", (width, height), 255)] * (n - 1)
        ref = [first] + [_cover(Image.open(io.BytesIO(r)).convert("RGB"), width, height) for r in refs]
        out = self.pipe(video=video, mask=mask, reference_images=ref, prompt=prompt, negative_prompt=negative,
                        height=height, width=width, num_frames=n, num_inference_steps=steps, guidance_scale=guidance,
                        generator=torch.Generator("cuda").manual_seed(seed)).frames[0]
        if ref:                                         # the reference frames lead the output: drop them
            out = out[len(out) - n:]
        f = Path(tempfile.mkdtemp()) / "take.mp4"
        export_to_video(out, str(f), fps=FPS)
        return {"video": f.read_bytes(), "frames": n, "seconds": round(n / FPS, 2), "gpu": self.gpu,
                "offload": self.offload, "load_s": self.load_s, "render_s": round(time.time() - t, 1)}


def _gpu_rate(name):
    return next((v for k, v in GPU_USD_S.items() if k in (name or "").upper()), GPU_USD_S["H100"])


@app.local_entrypoint()
def main(picture: str, motion: str, prompt: str, out: str, seconds: float = 15.0, negative: str = NEGATIVE,
         refs: str = "", aspect: str = "9:16", steps: int = 30, guidance: float = 5.0, seed: int = 42):
    w, h = SIZES[aspect]
    frames = min(MAX_FRAMES, int(seconds * FPS) // 4 * 4 + 1)
    t0 = time.time()
    if _cached():
        fetch_s = 0
    else:
        print(json.dumps({"stage": "fetch", "note": "first run: caching the weights on the volume"}), flush=True)
        fetch_s = fetch.remote()
    t1 = time.time()
    pose = poses.remote(Path(motion).read_bytes(), frames, w, h)
    t2 = time.time()
    res = Vace().render.remote(Path(picture).read_bytes(), pose, prompt, negative,
                               [Path(r).read_bytes() for r in refs.split(",") if r], w, h, steps, guidance, seed)
    t3 = time.time()
    o = Path(out)
    o.parent.mkdir(parents=True, exist_ok=True)
    o.write_bytes(res.pop("video"))
    o.with_suffix(".pose.mp4").write_bytes(pose)
    gpu_s = t3 - t2                                     # billed GPU time for the render container (load + render)
    cost = round(gpu_s * _gpu_rate(res["gpu"]) + (t2 - t1) * GPU_USD_S["L4"], 3)
    receipt = dict(res, take=str(o), pose=str(o.with_suffix(".pose.mp4")), fetch_s=fetch_s,
                   pose_s=round(t2 - t1, 1), render_call_s=round(gpu_s, 1),
                   cold_start_s=round(gpu_s - res["render_s"], 1), total_s=round(t3 - t0, 1),
                   cost_usd=cost, cost_usd_per_s=round(cost / res["seconds"], 4), steps=steps, guidance=guidance,
                   seed=seed, size=[w, h], model=MODEL, at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    o.with_suffix(".modal.json").write_text(json.dumps(receipt, indent=1))
    print(json.dumps(receipt), flush=True)


def _cached():
    """True once fetch() has finished (it writes model/.complete last)."""
    try:
        return any(Path(e.path).name == ".complete" for e in weights.listdir("model"))
    except Exception:  # noqa: BLE001  no folder yet: first run
        return False
