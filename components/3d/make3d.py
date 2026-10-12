"""
make3d — image -> textured GLB, locally and free, with TRELLIS.2
(Apple Silicon port: https://github.com/shivampkumar/trellis-mac).

Usage: make3d <image> <out.glb> [--seed N] [--pipeline-type 512|1024|1024_cascade]
              [--faces N] [--texture-size 1024|2048|4096] [--keep-raw]

Background removal is built in (BiRefNet), so a plain photo/render works.

Differences from trellis-mac's own generate.py:
  * the two gated Hugging Face models are swapped for ungated equivalents,
    so no Hugging Face login is needed:
      facebook/dinov3-vitl16-pretrain-lvd1689m -> camenduru mirror (same sha256)
      briaai/RMBG-2.0 (background removal)     -> ZhengPeng7/BiRefNet (MIT)
  * its texture step is replaced by finish.py + bake_blender.py (clean
    texture, correct colour, upright; see finish.py for why)
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TRELLIS = os.path.join(HERE, "trellis-mac")

REMAP = {
    "facebook/dinov3-vitl16-pretrain-lvd1689m": "camenduru/dinov3-vitl16-pretrain-lvd1689m",
    "briaai/RMBG-2.0": "ZhengPeng7/BiRefNet",
}


def raw_path(out):
    """--keep-raw's file: <name>_raw.npz beside the output .glb (run output never lands in the component)."""
    return os.path.join(os.path.dirname(out), os.path.basename(out)[:-4] + "_raw.npz")


ap =argparse.ArgumentParser(prog="make3d", description="image -> textured GLB (local TRELLIS.2)")
ap.add_argument("image")
ap.add_argument("out")
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--pipeline-type", default="512", choices=["512", "1024", "1024_cascade"])
ap.add_argument("--faces", type=int, default=300_000, help="triangle budget of the output (default 300000)")
ap.add_argument("--texture-size", type=int, default=2048, choices=[1024, 2048, 4096])
ap.add_argument("--keep-raw", action="store_true",
                help="also save the raw decoder mesh + voxel colours beside the output .glb")
a = ap.parse_args()

image, out = os.path.abspath(a.image), os.path.abspath(a.out)
if not os.path.exists(image):
    sys.exit(f"make3d: image not found: {image}")
if not out.lower().endswith(".glb"):
    sys.exit("make3d: output must end in .glb")
os.makedirs(os.path.dirname(out), exist_ok=True)

# Same backend setup as trellis-mac/generate.py (must precede torch import)
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
os.environ.setdefault("ATTN_BACKEND", "sdpa")
os.environ.setdefault("SPARSE_ATTN_BACKEND", "sdpa")
try:
    import flex_gemm  # noqa: F401
    os.environ.setdefault("SPARSE_CONV_BACKEND", "flex_gemm")
except (ImportError, RuntimeError):
    os.environ.setdefault("SPARSE_CONV_BACKEND", "none")
os.chdir(TRELLIS)
sys.path.insert(0, os.path.join(TRELLIS, "TRELLIS.2"))
sys.path.append(os.path.join(TRELLIS, "stubs"))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402
from PIL import Image  # noqa: E402


def _remap(cls):
    orig = cls.from_pretrained.__func__

    def from_pretrained(klass, name, *args, **kw):
        name = REMAP.get(name, name)
        if "BiRefNet" in name:
            # BiRefNet's remote code defaults to fp16 weights; the pipeline
            # feeds it fp32 images on MPS, so load it in fp32.
            kw.setdefault("torch_dtype", torch.float32)
        return orig(klass, name, *args, **kw)
    cls.from_pretrained = classmethod(from_pretrained)


_remap(transformers.AutoModelForImageSegmentation)
_remap(transformers.DINOv3ViTModel)

from finish import finish  # noqa: E402

T0 = time.time()
print("make3d: loading TRELLIS.2 ...", flush=True)
from trellis2.pipelines.trellis2_image_to_3d import Trellis2ImageTo3DPipeline  # noqa: E402

pipe = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B")
pipe.to(torch.device("mps"))
t_load = time.time() - T0
print(f"make3d: loaded in {t_load:.0f}s", flush=True)

t = time.time()
res = pipe.run(Image.open(image), seed=a.seed, pipeline_type=a.pipeline_type)
mesh = res[0] if isinstance(res, list) else res
V = mesh.vertices.cpu().numpy()
F = mesh.faces.cpu().numpy()
if len(V) == 0 or len(F) == 0:
    sys.exit("make3d: the model produced an empty mesh (macOS GPU watchdog). "
             "Retry; if it repeats, close other GPU-heavy apps.")
t_gen = time.time() - t
print(f"make3d: generated {len(F):,} triangles in {t_gen:.0f}s", flush=True)

coords = mesh.coords.cpu().numpy()
coords = coords[:, -3:] if coords.shape[1] == 4 else coords
attrs = mesh.attrs.cpu().float().numpy()
origin = mesh.origin.cpu().numpy()
vsz = float(mesh.voxel_size)
if a.keep_raw:
    np.savez_compressed(raw_path(out),
                        verts=V, faces=F, coords=coords, attrs=attrs, origin=origin, voxel_size=vsz)
del pipe, res
torch.mps.empty_cache()

t = time.time()
n = finish(V, F, coords, attrs, origin, vsz, out, target_faces=a.faces, texture_size=a.texture_size)
t_fin = time.time() - t
print(f"make3d: finished ({n:,} triangles, {a.texture_size}px texture) in {t_fin:.0f}s", flush=True)
print(f"make3d: wrote {out}")
print(f"make3d: total {time.time() - T0:.0f}s  (load {t_load:.0f}s, generate {t_gen:.0f}s, finish {t_fin:.0f}s)")
