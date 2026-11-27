"""A question about one or more pictures, answered by a vision model on this Mac
(MLX via mlx-vlm, free, no network once the weights are here). Runs in this
component's .venv-vlm. Prints ONE JSON line: {"answer", "model", "load_seconds",
"gen_seconds", "images"}. The picture checks of video-production ask through it
(video-production/machine/vision_judge.py, the "local" judge).
    python jobs/vision_ask.py --model mlx-community/Qwen3-VL-8B-Instruct-4bit \
        (--prompt "..." | --prompt-file p.md) [--max-tokens 1200] img1.png [img2.png ...]"""
import argparse, json, time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("images", nargs="*")
ap.add_argument("--model", required=True)
ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
ap.add_argument("--max-tokens", type=int, default=1200)
ap.add_argument("--max-side", type=int, default=1024)       # pixels the model reads; more is slower, not wiser
a = ap.parse_args()
prompt = a.prompt if a.prompt is not None else Path(a.prompt_file).read_text()

from PIL import Image
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template

imgs = []
for p in a.images:
    im = Image.open(p).convert("RGB")
    im.thumbnail((a.max_side, a.max_side))
    imgs.append(im)

t = time.time()
model, processor = load(a.model)
load_s = time.time() - t
text = apply_chat_template(processor, model.config, prompt, num_images=len(imgs))
t = time.time()
out = generate(model, processor, text, imgs or None, max_tokens=a.max_tokens, temperature=0.0, verbose=False)
gen_s = time.time() - t
answer = getattr(out, "text", out)
print(json.dumps({"answer": answer, "model": a.model, "load_seconds": round(load_s, 1),
                  "gen_seconds": round(gen_s, 1), "images": len(imgs)}))
