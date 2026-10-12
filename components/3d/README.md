# make3d — free, local image-to-3D

## How to use it → (team dashboard)

One picture in, one textured `.glb` out, on this Mac. No credits, no login, no upload.
Brought into the workspace 2026-09-29 nested inside `video-edit/`; moved out
2026-09-30 to its own component, `components/3d/` — a general tool, not
specific to video editing. `components/objects/` calls it as a sibling.

```
components/3d/make3d <image.png> <out.glb>
```

Options: `--seed N` (try another variation), `--faces 300000` (triangle budget),
`--texture-size 2048` (1024 / 2048 / 4096), `--pipeline-type 512` (1024 is sharper but slower, untested here),
`--keep-raw` (save the raw model to `raw/` for debugging).

Background removal is built in (BiRefNet). A plain product shot or render on a flat background works best.

## What's installed (2026-09-26)

| Piece | Where | Size |
|---|---|---|
| TRELLIS.2-4B (Microsoft, MIT) via the Apple-Silicon port [trellis-mac](https://github.com/shivampkumar/trellis-mac) | `trellis-mac/` + its own Python 3.11 venv `trellis-mac/.venv` | 1.1 GB |
| Model weights: TRELLIS.2-4B, TRELLIS-image-large decoder, DINOv3 (ungated mirror `camenduru/…`, same sha256 as Meta's), BiRefNet | `~/.cache/huggingface/hub` | ~16 GB |
| Our wrapper: `make3d` → `make3d.py` → `finish.py` → `bake_blender.py` (uses the Blender already on this Mac) | this folder | tiny |

Its own venv (see `make3d.py` for the path it uses). No Hugging Face account needed: the two gated models trellis-mac asks for
(Meta DINOv3, BRIA RMBG-2.0) are swapped for ungated equivalents inside `make3d.py`.
The wrapper runs offline (`HF_HUB_OFFLINE=1`); to re-download weights run with `HF_HUB_OFFLINE=0`.

**Installing on another Apple-Silicon Mac (3d#2, documented steps; no setup script yet):** (1) clone [trellis-mac](https://github.com/shivampkumar/trellis-mac) into `components/3d/trellis-mac/` (gitignored) — the commit the owner's install runs is not recorded in this repo yet, so record it when you install; (2) build its Python 3.11 venv at `trellis-mac/.venv` by trellis-mac's own README; (3) run `make3d` once with `HF_HUB_OFFLINE=0` to fetch the weights into `~/.cache/huggingface/hub` (~16 GB); (4) Blender on PATH (`blender --version`), which `finish.py` shells out to. `make3d` execs `trellis-mac/.venv/bin/python`, so a clone without step 2 fails at the exec.

## Time per object (M3 Max, 64 GB)

| Test | Load | Generate | Finish (clean + texture) | Total |
|---|---|---|---|---|
| monk | 160 s | 299 s | 29 s | **~8 min** |
| turntable | 130 s | 240 s | 17 s | **~6.5 min** |

Load is paid once per run (weights from disk). Earlier runs generated the monk in 199 s, so expect 6–9 min.
Peak memory ~18–20 GB.

## What didn't work, and what we changed

- **Metal acceleration not available.** trellis-mac's fast Metal pieces (`mtlbvh`, `mtldiffrast`, `mtlmesh`, `mtlgemm`, `o_voxel`) all failed to build:
  `xcrun: error: unable to find utility "metal"` — this Mac has Command Line Tools only, not full Xcode, and
  `xcodebuild -downloadComponent MetalToolchain` needs Xcode. (`o_voxel` also failed on `'Eigen/Dense' file not found`.)
  `mtlgemm`'s shaders also need macOS 26; this Mac is on 15.7. So it runs the slower pure-PyTorch fallback — still works.
- **trellis-mac's fallback texture baker was unusable:** camouflage-patch texture, washed-out colour (extra gamma), and the
  model came out lying on its back (Z-up). Replaced with `finish.py` + `bake_blender.py`: decimate to 300K triangles,
  orient faces outward, colour from the model's own voxel colour field, UV-unwrap + bake a 2048 texture in Blender, export an upright GLB.
- The GLB ships **flat-shaded with no normal data** on purpose: the decoder's triangle winding is inconsistent, and smooth
  normals turned that into dark cracks. At 300K triangles flat shading reads as smooth.
- Hugging Face gating, `einops` missing, BiRefNet fp16/fp32 mismatch — all fixed inside the wrapper.

## Quality vs the paid version (Meshy via Higgsfield)

Side-by-sides: made in the owner's private repo before the move and not in this one (media stays out of git, rule 3); the findings below stand on their own.

**Monk**
- Geometry: pose, proportions and the robe folds are close to the paid one. Some small holes/specks in the surface (the port skips hole-filling).
- Texture: robe colour right and clean; skin tone fine. Lower detail than paid (no fine cloth weave).
- Face: clearly worse. Features are puffy and distorted and it doesn't look like the reference person. The paid face is recognisable.

**Turntable**
- Geometry: clean, square body, feet, platter, tonearm all there; body edges are crisper than the paid one's warped box.
  Small parts (strobe-dot ring, headshell, pitch slider, buttons) are mushy or missing.
- Texture: reads as white/black plastic, not brushed silver metal (no metallic map); record grooves and label absent.
  Paid has the metal look and more small detail.

Short version: good enough for mid/background props and silhouettes; not good enough for close-ups of faces or small
hard-surface detail. Paid still wins on hero objects.
