# Image teardown — the static-ad twin of the video chain

**Keys this tool needs:** GEMINI_API_KEY, APIFY_TOKEN, GDRIVE_SA_KEY (optional). Put your own in `.env` at the top of the repo — see [`.env.example`](../../.env.example).

**Image teardown** takes a picture ad (one still, or a carousel) and gives back
its structure — what it is, element by element — and a brief to remake it for
one of our brands. It does not make the picture; the draft standard and
image production do that from its brief. Owner: the owner. A component since
2026-10-01 (moved out of `the team notes/image-teardown/`). Spoken name: "image
teardown". The one-page definition is `CLAUDE.md`; how to run it is `RUN.md`.

    python3 tools/image-teardown/chain.py start --brand <brand> --product <product> --avatar <avatar> --swipe <swipe> --dry-run

Runs file at `runs/image-teardown/<brand>/<label>/`; every brief gets one id in
`briefs.json` (`python3 tools/briefs.py check`).

## How to use it → (team dashboard)


Same chain, one frame. Built 2026-08-19 from `stage1-teardown-v6-damon.md`
after the owner's call to start the teardown process on image ads.

**Current shape (2026-09-20):** `CLAUDE.md` is the one-page definition — steps,
the element labels, the two gates, where runs file. `RUN.md` is how to run it
for a brand, including `--dry-run`. Tests: `python3 tests/test_image_teardown.py`.
What follows is the history.

The 2026-08-19 lane took one image per run, with no set pass and no carousel
lane. Since 2026-09-22 `chain.py start --form sequence` runs a carousel or a
slideshow (`CLAUDE.md`, "The branch"). The set-map prompt is still parked in
`prompts/parked/` and is not part of the chain.

## What is here

| Path | What it is |
|---|---|
| **`DRAFT-STANDARD.md`** | **The ruling on how a swipe becomes our draft (the owner, 2026-09-17: "do not deviate"). One command: `tools/draft.py --brand <brand>`. Prompts: `prompts/stage7-*`, `prompts/stage8-*`** |
| `prompts/stage1-image-teardown-v1-damon.md` | One static in, one reproduction spec out |
| `prompts/video-doctrine-extract-v1.md` | A teaching video in, its operating doctrine out |
| `tools/gemini_image.py` | Image-in / text-out runner — the twin of `tools/gemini_breakdown.py` |
| `tools/compose.py` | Sets the type layer over a generated plate (ImageMagick) |
| `tools/iterate.py` | **Retired 2026-09-13** — ran stage 5's job list against fal.ai. Pictures are made on Higgsfield; see `../image-production/PIPELINE.md` |
| `build_artifact.py` | Renders one run folder into `artifact.html` |
| `build_prompt_library.py` | Renders every prompt into `prompt-library.html` |
| `runs/<date>-<slug>/` | One folder per run: `assets/`, `out/`, `artifact.html` |

## Why a separate runner

`tools/gemini_breakdown.py` runs an ffprobe audio pre-flight before every
call — the fix for the creator-g-01 fabrication, where the model invented speech
for a silent file. Pointed at a PNG it finds no audio stream and injects
"this video file contains NO audio track" into an image prompt. So images go
through `gemini_image.py` instead: inline base64, no Files API, no pre-flight.
Multiple `--image` flags go in one call, labelled IMAGE 1..n, which is what
stage 1B reads.

## Running it

```bash
cd content-machine/image-teardown
R=runs/2026-08-19-brand-a-thai-secret

# one teardown per ad
python3 tools/gemini_image.py \
  --prompt-file prompts/stage1-image-teardown-v1-damon.md \
  --image $R/assets/ad-01_thai-secret-editorial-1x1.png \
  --model gemini-3.1-pro-preview \
  --out $R/out/01-teardown-ad-01.md

# then the chain, one stage at a time
./run-chain.sh $R 2      # replication spec
./run-chain.sh $R 3      # injection
./run-chain.sh $R 4a     # placement
./run-chain.sh $R 4b     # headlines
./run-chain.sh $R 4c     # support copy
./run-chain.sh $R 4d     # offer block
./run-chain.sh $R 5      # build sheet

# rebuild the read-through
python3 build_artifact.py $R
```

Screenshots dropped straight from the ad account are fine as input. Downscale
copies into `assets/web/` before building the artifact — the page embeds them
as data URIs and full-size PNGs blow the size budget:

```bash
sips -Z 720 -s format jpeg -s formatOptions 72 in.png --out assets/web/in.jpg
```

## Chain QC for stage 1 (image)

Read against `prompts/reference/CHAIN-QC.md`; these replace its stage-1 block.

- [ ] All four sections present: Objective Record, Frame Mechanics, Psychology, Index
- [ ] Frame Spec covers ratio / palette with hex / treatment / generation tells
- [ ] Subject & Setting profile covers who / wardrobe / setting / props / light and camera
- [ ] Zone table has all five columns, one row per element, no merged zones
- [ ] Every position is a percentage of frame — no "upper area"
- [ ] Type & Treatment gives class, weight, case, size as % of height, color
- [ ] Reading path numbered, with what the viewer understands after stop 1 alone
- [ ] Scroll-stop mechanism names one element and what survives without it
- [ ] `Breaks if cut:` present per block; `Belief shift:` present per play
- [ ] `(inferred)` on every specific typeface name
- [ ] `[UNCLEAR: …]` used where the frame is unresolvable — or its absence plausible
- [ ] `[ARTIFACT: …]` used for platform chrome or watermarks if any exist
- [ ] Observation only — no evaluation of brand or product
- [ ] Element registry sized as % of frame, usable as a template spec

## Producing the ad

There is no designer and no design tool. The chain ends in two JSON blocks:

```bash
# 1. the plates — image models paint the picture, no words in it
python3 tools/iterate.py --jobs $R/out/jobs.json \
  --out-dir $R/iterations --ref $R/assets/character-ref.png

# 2. the type layer — set deterministically, so exact wording survives
python3 tools/compose.py --plate $R/iterations/<plate>.png \
  --layer $R/out/type-layer.json --file 01 --out $R/finals/ad-01.png
```

Stage 5 decides which text the model renders and which the compositor sets.
Short and huge goes to the model; long, small, or character-exact goes to the
compositor. The guarantee always goes to the compositor.

## Open

- Calibration testing across all stages — the owner's call, scheduled after the
  prompts existed rather than before.
- A per-brand character reference, so the same face holds across a whole set
  without re-describing it.
