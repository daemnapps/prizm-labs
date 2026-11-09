# The Generative Model House — what each model does (the only rule, 2026-10-20)

the owner, 2026-10-20: *"any of these generative tools that we build should just reference model house.
There's no reason to write it into anything specific … Model house should be a component. That way we can
adjust our model house and keep that separate from the actual workflow and just reference it directly."*
And: *"for image editing, we're still gonna use GPT."*

**This component is the only place that says which model does which job.** Every tool that makes a
picture, a clip, a voice or a sound reads it: people read this page, code reads `models.json` through
`model_house.py`. No tool writes a model choice of its own. To add or change a model, change it here and
every tool follows. `tools/video-production/SHOT-ROUTES.md` decides HOW a shot is made (REAL footage
we own, a SWAP of the swipe's own shot, or AI); when it is AI, the model comes from here. Which model each
ad FORMAT uses is ruled per format and recorded here too.

## The house default, and a person's pick (MDL-8 (registry-linked house), 2026-10-22)

the team, 2026-10-22: *"link the model house to the registry, although the model house should also be able to pull
from the model component as well. the owner's point with model house was not to limit to just limited models."*

**The rule: a TOOL calls `model(job)` and gets the house default, only. A tool never picks a non-default model on
its own** — not for cost, not because a key is missing. **Only a person's explicit pick goes through `pick()`.**

- **Every job names its model by REGISTRY ID.** `models.json` here stores, per job, `registry` (an id in
  `components/models/models.json`), the `door` it is sold through and the `capability` the job needs — no
  vendor name, price or key of its own. The registry holds those: one entry per model, with `doors` when one
  model is sold at more than one door (GPT Image 2.5 at OpenAI and at fal is ONE entry, two doors).
- **`model(job)` answers what it always did**: the vendor's name for the row's door under `model` (pictures,
  sound, behind) or `id` (clips, swipe footage); a bare string for `behind.judge`, `behind.upscale`,
  `behind.3d`; a list under `models` for `behind.judge_busy`. Its dict answers also carry `registry_id`,
  `key_env`, `transport` and `cost`. A registry id the registry lacks, a deprecated one, a door it does not
  sell, or a capability it does not list is refused by name — never a guess.
- **`choices(job)` is the open pool**: the house default first, then every registry model that is not
  deprecated and lists the job's capability, one line per door, in a fixed order (registry id, then door). Draft
  models are offered; a person sees each one's `status`.
- **`pick(job, model)` is a person's pick**: a registry id, or `<id>@<door>` when it is sold at more than one
  door (`gpt-image-2.5@fal`); nothing named = the house default. A model not in `choices(job)` is refused by
  name, and so is a pick whose key this machine does not have ("seedream-5-pro-edit@fal needs FAL_KEY, which
  this machine does not have") — never silently swapped for another.
- **`purpose`** (`choices(job, purpose=…)`) is accepted and ignored today. It is where a later card ranks the
  pool by what is logged about each model and what proved good for which purpose, fed back to
  `components/models`.

    python3 components/generative-model-house/model_house.py --choices pictures.edit

## Door ruling, 2026-10-26: all generative access through Higgsfield (being wired, NOT switched)

the owner: the whole team works out of Higgsfield, costs and incentives are good, it has an API and an MCP, so fal is a waste of
time. The registry now has a `higgsfield` door on GPT Image 2.5 (`gpt_image_2_5`), Seedream 5 Pro (`seedream_v5_pro`) and
Nano Banana Pro (`nano_banana_pro`), vendor ids read from Higgsfield's own model list. **The picture jobs have NOT been moved to the Higgsfield door**, because Higgsfield's keyed API does not sell these
three models: its picture catalog (open.higgsfield.ai, read 26 Oct) is Soul, Grok Imagine, Marketing Studio, Ideogram,
Recraft, Qwen Image and Z-Image. GPT Image 2.5, Seedream 5 Pro and Nano Banana Pro are only in the Higgsfield app, MCP and
CLI (`@higgsfield/cli`, browser login, no keys). The engine's Higgsfield picture door is built and tested offline
(`image_production/providers.py` `_higgsfield`, row `gpt-image-higgsfield`, not routed). the owner decides the route: keep
OpenAI direct for chains, ask Higgsfield to enable API access, or use their CLI. What Higgsfield's GPT Image door cannot do that OpenAI direct can: a mask (region edits), a custom size, `n`, the
moderation flag. Its defaults are the cheapest picture (flare, low, 1k), so every call must name its variant, quality and
resolution. **Stays off Higgsfield:** ElevenLabs v3 voice, music and Scribe (Higgsfield has only Eleven v4 and no Scribe),
the Gemini judge and fast read (no vision judge there), real-esrgan and trellis (local).

## What each model takes, and what works (2026-10-26)

`components/model-inputs` holds, per model, every input with its limits, the prompt structure the maker says works and
what to avoid. The house names the model for a job; that component answers its inputs, by the same registry id
(`input_rules.for_job("pictures.edit")`, `for_job("clips.seedance")`). A new model enters the house with its registry
row AND an inputs file there; `input_rules.coverage()` lists the jobs that do not have one yet.

## Pictures

| Job | Model | Notes |
|---|---|---|
| every picture: cast sheets, stills, plates, first and last frames | **GPT Image 2.5** (`gpt-image-2.5-sunburst`, OpenAI direct) | from the cast sheets and real references; quality high; the same model on fal takes over when OpenAI is busy |
| every image edit (change one thing in an approved picture, region edits, the 9:16 finish) | **GPT Image 2.5**, edits | ruled again 2026-10-20. Nano Banana Pro is not used for edits or anything else |
| backup when GPT refuses a picture we're allowed to make | **Seedream** (fal) | the owner 2026-10-21. Same prompt and references; Seedream's own rules still apply; the run record says which model made it |

### Motion, read before any take (2026-11-09)

A scene's motion is read and approved before a take is paid for (BRIEF-SPEC.md rule 7, "Motion sources").

| Job | Tool | Gives | Cost and time, as measured 2026-11-09 |
|---|---|---|---|
| read a clip's motion (the default) | **MediaPipe on this machine** (`components/video-studio/motion.py`): a person finder, then pose, hands and face per person; the camera solved from the background | points for every person, hand and face; a skeleton video; the camera's path | free; 4 s of clip read in 18 s, 14 s of a crowded swipe in 57 s |
| a swipe the local reader misses | **fal DWPose**, one call per frame (`motion.py --engine fal`) | a skeleton picture per frame, no points, no camera | 2 s of clip: 32 calls, about 0.02 USD, 4 minutes |
| block a scene in 3D | **Blender**, headless (`motion.py blocking`) | a blocking clip from stand-in people, a `.glb` set, beats and a moving camera | free; 5 s rendered in about 25 s |

## Clips — Seedance 2.5, every clip (the owner, 2026-10-23)

| Job | Model | How |
|---|---|---|
| every clip | **Seedance 2.5**, made at **480p and upscaled on this Mac** (the owner, 2026-10-26; was 720p), Higgsfield API (`tools/video-production/machine/seedance.py`) | a talking clip sends the start picture AND the line's voice read in one call (`reference-to-video`); a silent clip goes from the picture (`image-to-video`). Nothing is re-voiced after. Cost never decides. |
| backup clip | **Kling 4.0**, 720p (no 480p), Higgsfield API (`machine/kling.py`, `clips.backup`) | only when Seedance fails its three takes, is refused or is down. It takes the start picture and NO audio, so its clip is silent: a talking clip is laid over its own locked read, not lip-synced. The run ledger says which model made each clip. Rulebook: `components/model-inputs/inputs/kling-4.0.json` |

## Using the swipe's own footage

| Job | Model | Notes |
|---|---|---|
| put our cast (or our product) into the swipe's shot, keeping its motion | **Genjutsu object swap** (`hf_mult_replace_object`) | the full cast sheet goes in; it keeps the original mouth, so it carries no line of ours |
| the swap kept the original person's face | **Genjutsu motion transfer** (`hf_mult_motion_control`) | our cast master is the person, the swipe shot only drives the movement |

## Sound

| Job | Model | Notes |
|---|---|---|
| every voice line | **ElevenLabs v3**, one custom voice per character | **each line is its own read**, with that shot's delivery as an audio tag; never one long take for the whole piece |
| the song in a song ad | **Suno**, by hand in its own app (ruled 2026-10-28: "for all song ads, we're just using Suno. It's the best.") | the chain writes its inputs (`song.py --suno`, by `model-inputs/inputs/suno.json`) and gates the take (`song.py --from-file`); ElevenLabs Music stays the music bed |
| the clips of a song ad (the singer on camera) | **Seedance 2.0** (`seedance-2.0`, on Higgsfield; ruled 2026-10-29: better movement and lip-sync than 2.5 in the song-ad tests) | every other clip stays Seedance 2.5; the singer's slice of the Suno song is the read; the clip's own sound is not kept |
| music beds and sound effects | **ElevenLabs** Music and Sound Effects | |
| word timings for captions and the line check | **ElevenLabs Scribe** | |
| who speaks when on a swipe (speaker labels) | **ElevenLabs Scribe v2** (`scribe_v2`) | the audio teardown's speaker pass; its words are merged with the judge's heard lines, never trusted alone outside English |

## Behind the scenes

| Job | Model |
|---|---|
| judging a picture or clip (does it match, is it slop) | **Gemini 3.1 Pro** |
| when the judge is busy ("high demand") | **Gemini 3.5 Flash**, then **Gemini 3 Flash** — a fallback, never a cost choice |
| a hand tool's quick test read of one prompt on one video | **Gemini 3 Flash** (every read inside a run is the judge) |
| upscaling a low-resolution clip | local **Real-ESRGAN**; the fal ByteDance upscaler as the alternate |
| a 3D object from one picture | local **TRELLIS.2** |

## Also read by code (listed 2026-10-21 so this page and models.json agree)

Each job's registry id (`components/models/models.json`) since MDL-8 (registry-linked house): pictures
`gpt-image-2.5` (openai; overflow at fal), backup `seedream-5-pro-edit`; clips `seedance-2.5` (Higgsfield); swipe footage `higgsfield-object-swap`,
`higgsfield-motion-control`; sound `eleven-v3`, `eleven-ttv-v3`, `eleven-music-v2.5` (the music bed), `suno` (the song, by hand),
`scribe_v1` (words), `scribe_v2` (speakers); behind `gemini-3.1-pro-preview` (judge), `gemini-3.5-flash` then
`gemini-3-flash-preview` (busy), `gemini-3-flash-preview` (fast read), `real-esrgan` and
`bytedance-upscaler-video` (upscale), `trellis.2-4b` (3D). The registry entries filed by that card are drafts.

| Job in `models.json` | Model | When |
|---|---|---|
| `pictures.overflow` | GPT Image 2.5 (the same model) on fal | OpenAI answers busy (429): the same model, sold by fal, makes the picture at once (ruled 2026-10-10) |
| `pictures.backup` | Seedream (fal) | GPT Image refuses a picture we're allowed to make (V21) |
| `sound.music_bed` | ElevenLabs Music `music_v2_5` | a music bed, when the swipe or brief calls for one (no separate bed model is ruled) |
| `behind.upscale_alternate` | fal ByteDance upscaler | the alternate to the free local Real-ESRGAN upscale of a picked take |
| `behind.fast_read` | Gemini 3 Flash | a hand tool's quick test read only; every read inside a run is `behind.judge` |
