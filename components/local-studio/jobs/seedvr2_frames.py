"""SeedVR2 3B over a folder of frames, model loaded once (mflux, MLX). Each frame is upscaled on
its own (no temporal link between frames). Usage: seedvr2_frames.py in_dir out_dir model_dir scale"""
import sys, time, json
from pathlib import Path
from PIL import Image
from mflux.models.seedvr2.variants.upscale.seedvr2 import SeedVR2
src, dst, model_dir, scale = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], int(sys.argv[4])
dst.mkdir(parents=True, exist_ok=True)
m = SeedVR2(quantize=8, model_path=model_dir)
frames = sorted(src.glob("*.png"))
short = min(Image.open(frames[0]).size) * scale
per = []
for f in frames:
    t = time.time()
    m.generate_image(seed=42, image_path=f, resolution=short).save(dst / f.name)
    per.append(time.time() - t)
print(json.dumps({"frames": len(frames), "per_frame_s": round(sum(per) / len(per), 2)}))
