"""SAM 2.1 on ONE picture, prompted by a box: the object inside the box, cut
out — not the hand holding it (a hand is its own object). Writes a white-on-black
mask PNG the size of the picture. Runs in this component's .venv (PyTorch MPS).
    python jobs/segment_image.py <image> <out-mask.png> --box x0,y0,x1,y1 (pixels)"""
import argparse
from pathlib import Path
import numpy as np, torch
from PIL import Image
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(); ap.add_argument("image"); ap.add_argument("out"); ap.add_argument("--box", required=True)
ap.add_argument("--ckpt", default=str(ROOT / "models" / "sam2" / "sam2.1_hiera_small.pt"))
ap.add_argument("--cfg", default="configs/sam2.1/sam2.1_hiera_s.yaml")
a = ap.parse_args()
dev = "mps" if torch.backends.mps.is_available() else "cpu"
pred = SAM2ImagePredictor(build_sam2(a.cfg, a.ckpt, device=dev))
img = np.array(Image.open(a.image).convert("RGB"))
pred.set_image(img)
box = np.array([float(v) for v in a.box.split(",")])
masks, scores, _ = pred.predict(box=box[None, :], multimask_output=True)
m = masks[int(np.argmax(scores))]
Image.fromarray((m > 0).astype(np.uint8) * 255).save(a.out)
print(f"score {float(scores.max()):.3f}")
