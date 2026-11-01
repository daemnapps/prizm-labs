# TRELLIS.2 4B (image to 3D) — what it takes, and what works

*Rendered from `components/model-inputs/inputs/trellis.2-4b.json` (read 2026-10-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- input images: 1
- output: PBR GLB plus a preview video
- grid resolutions: 512 to 1024 to 1536
- time h100 seconds: {'512': 3, '1024': 17, '1536': 60}
- gpu: NVIDIA, at least 24 GB; tested on A100 and H100
- platform: Linux only tested
- decimation target faces example: 1000000
- texture px example: 4096
- House: use builds the product turntable from one real photo; product_rule the product is never drawn: a render of the 3D model is the picture (product-from-3D-model rule)

## The prompt structure that works

- **Give it one clean, whole picture of the product; the model builds everything else from it.**
- **Read the label on the turntable: a build can warp text; compare against the real photo before the model is used.**
- **1024 builds in about 17 s on an H100; use 1536 only when the label is unreadable at 1024.**
- **The export is opaque; if the cut-out matters, connect the alpha in the 3D tool.**
- **Pictures of the product come from renders of this model or the real photo, never drawn.**
- **It needs a 24 GB NVIDIA GPU on Linux; on the Mac it runs through the door that has one.**

## Avoid

- Expecting it to merge several photos: it takes one.
- A photo with the product cut off: the missing part is invented.
- A photo with a smear or reflection on or behind the product.
- Using the turntable without comparing the label to the real photo.
- Running it on a laptop without the GPU.
