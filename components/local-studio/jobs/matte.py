"""BiRefNet cut-out on PyTorch MPS. Image -> RGBA PNG. Video -> ProRes 4444 .mov with alpha
(+ a VP9 .webm with alpha beside it, + a black/white matte .mp4). Runs in tools/av/.venv."""
import argparse, subprocess, tempfile, time, json
from pathlib import Path
import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

MODELS = {"lite": "ZhengPeng7/BiRefNet_lite", "full": "ZhengPeng7/BiRefNet"}
ap = argparse.ArgumentParser()
ap.add_argument("input"); ap.add_argument("output"); ap.add_argument("--model", default="full"); ap.add_argument("--size", type=int, default=1024)
a = ap.parse_args()
dev = "mps" if torch.backends.mps.is_available() else "cpu"
torch.set_float32_matmul_precision("high")
net = AutoModelForImageSegmentation.from_pretrained(MODELS[a.model], trust_remote_code=True).float().to(dev).eval()
tf = transforms.Compose([transforms.Resize((a.size, a.size)), transforms.ToTensor(),
                         transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

def matte(img):
    with torch.no_grad():
        pred = net(tf(img).unsqueeze(0).to(dev))[-1].sigmoid().cpu()[0].squeeze()
    return transforms.ToPILImage()(pred).resize(img.size, Image.LANCZOS)

inp, out = Path(a.input), Path(a.output)
out.parent.mkdir(parents=True, exist_ok=True)
per = []
if inp.suffix.lower() not in {".mp4", ".mov", ".m4v", ".mkv", ".webm"}:
    img = Image.open(inp).convert("RGB")
    matte(img)  # warm-up (first MPS call compiles kernels)
    t = time.time(); m = matte(img); per.append(time.time() - t)
    img.putalpha(m); img.save(out.with_suffix(".png"))
else:
    fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(inp)],
                         capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td); (td / "in").mkdir(); (td / "rgba").mkdir(); (td / "m").mkdir()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(inp), str(td / "in" / "%08d.png")], check=True)
        for f in sorted((td / "in").glob("*.png")):
            img = Image.open(f).convert("RGB")
            t = time.time(); m = matte(img); per.append(time.time() - t)
            m.save(td / "m" / f.name); img.putalpha(m); img.save(td / "rgba" / f.name)
        base = out.with_suffix("")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", fps, "-i", str(td / "rgba" / "%08d.png"), "-c:v", "prores_ks",
                        "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(base) + ".mov"], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", fps, "-i", str(td / "rgba" / "%08d.png"), "-c:v", "libvpx-vp9",
                        "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30", "-auto-alt-ref", "0", str(base) + ".webm"], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", fps, "-i", str(td / "m" / "%08d.png"), "-c:v", "libx264",
                        "-crf", "16", "-pix_fmt", "yuv420p", str(base) + "-matte.mp4"], check=True)
print(json.dumps({"device": dev, "model": MODELS[a.model], "frames": len(per), "per_frame_s": round(sum(per) / len(per), 3)}))
