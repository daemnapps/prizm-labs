# The local studio

## How to use it → (team dashboard)

Every editing job that runs on this Mac (M3 Max, 64 GB), behind one launcher.
the owner never runs this. Claude sessions and the pipeline call it. Brought into
the workspace 2026-09-29 nested inside `video-edit/`; moved out 2026-09-30 to
its own component, `components/local-studio/` — a general compute runner any
tool can call, not specific to video editing. Internal paths below (`tools/
local`, `tools/av`) still point at where this lived in the owner's own sandbox;
not yet fixed — first real run here updates them.

```
python3 components/local-studio/local.py --help   # the jobs and every flag
python3 components/local-studio/local.py runs     # every run so far: time + peak memory
```

| Job | Command | Model (build) | Measured on this Mac, 2026-09-27 |
|---|---|---|---|
| Frame interpolation | `interp clip.mp4 -o out.mp4 [--factor 2]` | RIFE v4.6 (ncnn, Metal) | 4.0 s Seedance clip, 720×1280, 24→48 fps: **12.3 s** (≈3 s per video-second), 0.9 GB |
| Upscale (video) | `upscale clip.mp4 -o out.mp4 --esrgan-model realesr-animevideov3` | Real-ESRGAN animevideov3 (ncnn) | same clip to 1440×2560: **42.9 s** (≈10.6 s per video-second), 0.6 GB |
| Upscale (video, heavier model) | `upscale clip.mp4 -o out.mp4` | Real-ESRGAN x4plus (ncnn), 4× then down to 2× | same clip: **500 s** (≈124 s per video-second), 2.4 GB |
| Upscale (stills) | `upscale still.jpg -o out.png --engine seedvr2` | SeedVR2 3B, 8-bit (MLX, mflux) | 683×1024 → 1360×2038: **50.9 s** incl. load, 15.6 GB MLX peak |
| Upscale (video, SeedVR2) | `upscale clip.mp4 -o out.mp4 --engine seedvr2` | same, frame by frame | 1 s (24 frames) 720×1280 → 1440×2560: **1,073 s** (≈44 s per frame, ≈18 min per video-second). Frames are upscaled independently |
| Cut-out / matte | `matte still.jpg -o out.png` · `matte clip.mp4 -o out.mov [--model lite]` | BiRefNet (PyTorch MPS) | 0.50 s/frame full · 0.19 s/frame lite. 3 s 1080×1920 clip: 166 s full / 130 s lite incl. load + encode. Video out = ProRes 4444 with alpha + WebM with alpha + matte mp4 |
| Segment + track | `segment clip.mp4 -o dir --box x0,y0,x1,y1 --point x,y` | SAM 2.1 hiera-small (PyTorch MPS) | 90 frames 1080×1920, 2 objects: **50 s** tracking (0.56 s/frame), 4.6 GB. Held both objects across hard cuts |
| Captions / STT | `stt audio.mp3 -o out.json [--language en]` | Whisper large-v3-turbo (mlx-whisper) | 3:46 song: **7.3 s** (≈31× real time), 3.6 GB. Writes json/srt/vtt/txt with word timestamps |
| Stems | `stems song.mp3 -o dir` | Demucs htdemucs_ft (PyTorch MPS) | 3:46 song: **29.4 s** (≈7.8 s per audio-minute), 3.3 GB. 38.7 s loop: 7.5 s |
| Voice (stock only) | `tts "text" -o out.wav [--voice am_michael]` | Kokoro-82M (MLX, mlx-audio) | 11.9 s of speech in **3.8 s** incl. load. Stock voices only — no cloning |
| Image edit / outfit swap | `edit "prompt" --ref a.jpg [--ref b.jpg] -o out.png` | FLUX.2 klein 4B, 4-bit (mflux) | 1 ref, 688×1024: **33.9 s**. 3 refs, 864×1536: **95.5 s**, 15.1 GB MLX peak |
| Still | `image "prompt" -o out.png [-W 864 -H 1536]` | FLUX.2 klein 4B, 4-bit (mflux) | 864×1536, 4 steps: **32.4 s** |
| 3D object | `3d ref.png -o out.glb` | TRELLIS.2-4B (components/3d/make3d) | carousel: **399 s** (load 101, generate 272, finish 20), 22.8 GB |
| Image → video | `i2v still.jpg "prompt" -o out.mp4` | LTX-2.5 distilled 4-bit (MLX) | **Not installed.** Needs ~29 GB of weights; see "Not local" |

Side-by-sides and sample outputs: `tools/local/samples/cmp-*.jpg` (the media stays
on this Mac), and on The Model Map page, "Local studio" section.

## Where things are

- `setup.sh` — the install: `--check` (default) lists every piece present/missing; `--install` builds `.venv-mlx` and prints each model's fetch command, `--fetch` runs them. `tools/av` is reported, never installed.
- `local.py` — the launcher. Every run is timed with macOS `time -l` and logged to
  `runs/local-studio/_system/runs.jsonl` at the repo root (wall seconds, peak memory footprint, input, model).
- `jobs/` — the per-model scripts the launcher calls (matte, segment, tts, SeedVR2 frames).
- `bench/` — `wer.py` (caption accuracy vs the corrected Carousel lyrics), `sbs.py` and
  `crops.py` (the comparison sheets).
- `models/` — **every weight this studio downloaded, in one folder** (git-ignored).
  Delete the folder to take it all back. `models/hf` (FLUX.2 klein q4 4.6 GB,
  Whisper turbo 1.6 GB, Kokoro 0.4 GB), `models/seedvr2-3b` (7.3 GB), `models/torch`
  (Demucs htdemucs_ft 0.3 GB).
- Environments: `.venv-mlx` (mflux, mlx-whisper, mlx-audio; 1.5 GB). The PyTorch jobs
  (matte, segment, stems) run in the existing `tools/av/.venv`; RIFE and Real-ESRGAN
  are the existing binaries in `tools/av/bin`; 3D is `components/3d/make3d`.
- Reused, not re-downloaded: BiRefNet (0.6 GB, `~/.cache/huggingface`), SAM 2.1 small
  (`tools/av/models/sam2`), TRELLIS.2 (~16 GB, `~/.cache/huggingface`).
- `src/ltx-2-mlx` — the LTX-2 MLX port, installed without weights (0.3 GB).

## Traps found while building it

- **Runs are offline by default** (`HF_HUB_OFFLINE=1`). Hugging Face look-ups hung for
  10+ minutes twice today; the launcher only goes online if the weights are missing.
- **Whisper on music loops.** With "condition on previous text" on, large-v3-turbo
  repeated lines and the song came out at 71% word error; off (now the default) it was
  12.7%. `--context` turns it back on for plain speech.
- **Whisper on the Demucs vocal stem was worse than on the full mix** (25.4% vs 12.7%).
- **`mlx-community/SeedVR2-3B-mlx-int8` is not in mflux's format** (fails on load). The
  working weights are `numz/SeedVR2_comfyUI` (fp16), quantised to 8-bit on load.
- **`mflux-upscale-seedvr2` on a folder writes every frame to one `image.png`** in the
  current directory. The launcher uses `jobs/seedvr2_frames.py` instead.
- **Demucs' own weight download stalled**; the four htdemucs_ft files were fetched
  directly into `models/torch/hub/checkpoints`.
- **BiRefNet full ships fp16 weights**; on MPS they must be cast to fp32.
- **Kokoro needs** `misaki[en]` and spaCy's `en_core_web_sm` (installed).
- Real-ESRGAN runs single-thread (`-j 1:1:1`): multi-thread scrambled frame order in Carousel.

## Not local, and why (facts as of 2026-09-27)

- **Image → video.** The smallest pack that runs on this Mac is LTX-2.5 distilled 4-bit
  (MLX port `dgrauet/ltx-2-mlx`): transformer 11.3 GB + text encoder 10.6 GB + connector
  4.0 GB + VAE/audio/upscaler ≈3 GB ≈ **29 GB**. Free disk was 49–60 GB during this build
  (other sessions were writing too); the floor is 30 GB. Not downloaded. Wan 2.2 TI2V-5B
  8-bit (MLX) is 19.6 GB. Seedance on Higgsfield stays the route (decision 2026-09-27).
- **Motion transfer.** The one Mac port found, SCAIL-2-MLX, is marked work-in-progress
  ("not yet release-quality"): ≈46 GB of weights, ≈51 min per 65-frame 480p clip on an
  M5 Max, ≈47 GB peak memory. No MLX/MPS port of Wan 2.2 Animate found.
- **Stills/edits where identity must hold through a pose change** stay on GPT Image,
  direct through the OpenAI API (decision 2026-09-27) — see the leather-jacket
  side-by-side for what the local model changed.

## Add a model

Put its weights under `models/`, add a `job_<name>` function to `local.py` that calls
`run([...], "<name>", {meta})`, and log a real run on our own assets before listing it.
