# The image models we use (2026-09-22)

The route is `models.json` in this folder, read by `image_production/route.py`.
**Nothing chooses a model in its own code** — a caller asks the table.

| Row | Model | Provider | When it is picked |
|---|---|---|---|
| `gpt-image-person` | `gpt-image-2.5-sunburst` | OpenAI | **every picture**, unless a rule above it matches. the owner, 2026-09-22: *"everything image needs to just be gpt now, literally that's it."* Makes 9:16 natively (1152x2048) |
| `gpt-image-edit` | `gpt-image-2.5-sunburst` | OpenAI | an edit of an existing picture — the approved frame back in, one thing moves. The only door that takes a mask, so region edits and the 9:16 finish live here |
| `gemini-image-object` | `gemini-3-pro-image` | Google | only when a caller forces it by name |

Sizes are exact ratios: any size whose sides both divide by 16 (9:16 = 1152x2048,
4:5 = 1024x1280). 1080x1920 is refused by the model for that reason.

## Video frames came onto this table (2026-09-22)

the owner, the same evening: *"brief frames need to run on gpt, not nano banana."*
`tools/video-teardown/machine/frames.py` now asks this route like every
other caller and names no model of its own. Proven live that day: one frame
back at **1152x2048**, true 9:16, from a seed still as the reference.

Two things about the move, because they change how a frame is asked for:

- **The reference legend.** Gemini's door let a sentence sit beside each
  reference picture (this is the face, this is the location, this is the real
  product). GPT Image takes one prompt and a LIST of pictures, so those same
  sentences are written into the prompt as a numbered legend in the order the
  pictures are attached — `frames.legend()`. The words are unchanged.
- **No second model.** Nano Banana Pro had a per-frame fallback to Nano Banana
  2 when its 250/day cap ran out. There is one door now, so `FALLBACK` equals
  `MODEL` and those branches are inert.

**The QC inspector is still Gemini** (`FRAMES_QC_MODEL`, `gemini-3.5-flash`).
That is a vision READ of a finished frame, not generation — a different job,
and cheap. Say the word if it should move too.

## fal is gone (2026-09-22)

Ruled three times — 2026-09-11, restated 09-13, and again 2026-09-22
(*"remove anything with fal or flux lora, we decided to not use these tools"*).
Removed that day:

| Where | What went |
|---|---|
| `video-teardown/machine/frames.py` | the nano-banana/edit call, the flux-lora trained-identity path, the packshot composite, `fal_call`. The seed still, the face and the product now go to Gemini as reference images — the same edit-first operation in that model's own door |
| `video-teardown/machine/cast_voice.py` | fal's ElevenLabs endpoint → **ElevenLabs direct**, and it now writes a real `voice_id`, which the video machine has required since 2026-09-17 |
| `casting/casting/generate.py` | the fal client subprocess → this component's `gpt-image-edit` row |
| `email-production/fal_generate.py`, `gen_placeholders.py` | retired (their caller was already history; the live path makes pictures on GPT Image) |
| `image-teardown/tools/fal_drafts.py` | renamed `gpt_drafts.py`, the `--door fal` escape hatch removed |
| `the team notes/avatar-builder/build.py` | retired — its job is `components/casting` now |
| `video-teardown/machine/doctor.py`, Control Room registry | stopped asking for `FAL_KEY` |

**Still on fal, and NOT touched** — each is somebody else's call:

- `tools/video-production/machine/omni.py` + `providers_fal.py` + `sound.py`
  — the fal clip/song route. The house table already moved motion and talking to
  **MiniMax H3 through Higgsfield** (the owner, 2026-09-22, after the bake-off), so
  this looks superseded rather than live, but proving it is not a five-minute job.
- `components/identity-training/` — trains LoRAs on fal. **the developer's component**, and
  the LoRA consumer inside the owner's frames.py is already gone.
- `components/chain-runner/` — names `FAL_KEY` in its grant docs only. the developer's.
- `platform/workers/mini-worker/` — passes `FAL_KEY` through to jobs.
