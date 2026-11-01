# Real-ESRGAN (local video upscale) — what it takes, and what works

*Rendered from `components/model-inputs/inputs/real-esrgan.json` (read 2026-10-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- native scale: 4
- outscale: any final factor; the model runs x4 and resizes
- tile default: 0
- precision default: fp16
- formats: png to jpg to webp
- House: use the first upscaler: a 480p clip is made, then upscaled locally to 1080x1920; alternate bytedance-upscaler-video

## The prompt structure that works

- **Generate at 480p and upscale locally; the upscaler adds pixels, not new content.**
- **Use realesr-animevideov3 for animated footage; x4plus for general.**
- **Tile only when memory fails, knowing seams can appear.**
- **Leave face enhancement off: it changes a face the face gate already approved.**
- **Check the upscaled clip for smoothing of grain and text; the swipe's grain is part of the look.**

## Avoid

- GFPGAN on a cast member.
- Upscaling a take that is not yet kept.
- Assuming the NCNN build supports every Python option such as outscale.
- Adding grain or a filter after upscaling to fix a smooth look.
