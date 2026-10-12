# An elder-presenter ad for a body scrub — full Higgsfield production run
Reconstructed from generation history 2026-08-30. Companion data file: `evidence-run.json`
(328 generations, full verbatim params, chronological).

## The three production waves

| Wave | Dates (UTC) | What happened |
|---|---|---|
| 1 | 2026-07-28 18:50 → 07-29 07:41 | All original character + scene stills (gpt_image_2), elder voice cloned from an uploaded WAV, first 4–10s video tests (seedance_2_0), incl. first lip-syncs |
| 2 | 2026-08-10 11:46 → 08-11 07:17 | Full 4-character voice cast built (seed_audio), scene stills composed from character stills (seedream_v5_pro), full silent b-roll + lip-sync scene production |
| 3 | 2026-08-18 01:53 → 02:13 | Evolved recipe: fresh soul_v2 character sheets, then PROMPTED seedance shots (still + full text direction + generate_audio on), longer takes up to 15s, product hero shots, 3 closing VO lines |

## Counts per stage (total 328)

| Stage | Total | Wave 1 (Jul 28-29) | Wave 2 (Aug 10-11) | Wave 3 (Aug 18) |
|---|---|---|---|---|
| character-still | 47 | 23 | 20 | 4 |
| scene-still | 68 | 22 | 46 | — |
| still-upscale | 0 | — | — | — |
| voiceover | 99 | 65 | 31 | 3 |
| scene-video-silent | 33 | 18 | 15 | — |
| scene-video-lipsync | 54 | 14 | 40 | — |
| scene-video-prompted | 24 | — | — | 24 |
| product-video | 3 | — | — | 3 |

**still-upscale: none exist.** No upscale-model jobs appear anywhere in the account history for
these windows; resolution was handled in-generation (stills at 2K, video at 1080p).

## Models and settings per stage

**character-still / scene-still (July):** `gpt_image_2` (inner param `"model": "videotape-alpha"`),
9:16, 1520x2688, `resolution: "2k"`, `quality: "high"`. Some from scratch (no medias), some from
1–2 uploaded reference photos (`media_input`).

**character-still (Aug):** `gpt_image_2` for the two American character portraits (e3af5922 = 62yo
Arizona woman, 0dbd36ad = 64yo man, both 9:16 2K from 2 reference photos), then `seedream_v5_pro`
for character boards: 3:2 studio turnarounds of the 45yo Thai woman (942424a3, f741400e, built from
3 uploads) and a 16-image 16:9 2K board cluster (2720x1536, seeded, batch_size 1) — headshot grids,
full-body wardrobe lineups, pose sheets, all feeding later scene composition.

**scene-still (Aug):** `seedream_v5_pro`, 9:16, 2K (1536x2720), random `seed` per job,
`is_inpaint: false`. Every scene is composed by stacking `role:"image"` references: character
still image_jobs + uploaded product/reference photos. Two July image_jobs (33e6a8a4 product shot,
245c2efa) are re-referenced 13 days later in Aug scene jobs — stills are durable, reusable assets.

**voiceover:** `seed_audio`, wav, 24000 Hz, batch_size 1. July elder: `speech_rate: 15` (two at
20), no expression params. Aug cast: `speech_rate` -5 to -15 per character (man -10, Arizona woman
-8/-10, Thai woman -5, elder-in-Thai -15), `loudness_rate: 0`, `pitch_rate: 0`,
`expression_intensity: 5`, `mood: 0`. **No voice presets/voice ids anywhere** — every voice is
defined by a prose persona description in the prompt, plus @Audio reference cloning (below).

**scene-video (silent + lip-sync):** `seedance_2_0`, 9:16, 1080p (1080x1920), `mode: "std"`,
`generate_audio: true` (always, even on lip-sync jobs that get a driving track),
`multi_shots: false`, `speedramp: "auto"`, `bitrate_mode: "standard"`, `prompt_language: "en"`.
Durations: 4s x57, 5s x14, 6s x9, 8s x1, 10s x6 (July tests ran longer; the Aug production
standardized on 4s per scene beat, 6s for silent b-roll).

## CAVEAT: prompts for Wave 1/2 image and video jobs are empty — Wave 3's are fully persisted

The history API returns `"prompt": ""` for every Wave 1 and Wave 2 image job (gpt_image_2
/videotape-alpha and seedream_v5_pro) and video job — verified via show_generations,
show_generation_by_ids, and job_display. But Wave 3 (Aug 18) jobs come back with FULL verbatim
prompts on both its soul_v2 stills and its seedance videos. So the platform DOES persist prompts;
the empty Wave 1/2 fields reflect how those jobs were submitted — video jobs driven purely by
start frame + audio track with the prompt omitted, and stills created through a surface that did
not pass prompt text through. Audio jobs retain full prompts in every wave. Wave 1/2 image/video
creative intent is therefore reconstructed from reference chains + visual inspection; Wave 3 is
documented verbatim.

## Wave 3 (Aug 18): the evolved recipe

Twenty minutes, 34 jobs, a fundamentally different method:

1. **01:53** — four `text2image_soul_v2` character sheets (1536x2048, style "General",
   `enhance_prompt: false`, fixed seeds): "Split-screen character sheet composition, left side a
   full-body shot ... right side a tight close-up chest-up portrait of the same character" — one
   per cast member (very elderly female = elder 7b337cc1, elderly male 1f971a98, elderly
   female 8f78dd50, middle-aged female 712ada05). Characters regenerated fresh rather than reusing
   Wave 2 stills.
2. **01:54–02:09** — 24 prompted seedance_2_0 drama shots + 3 product shots. The recipe change:
   each video = character-sheet image_job (1–2 refs, or NONE for pure text-to-video) + a FULL
   cinematic text prompt ("Cinematic drama, golden morning Thai market stall. The very elderly
   Thai elder from the first reference image...") + `generate_audio: true` so seedance
   invents ambient sound/dialogue itself — no separate VO track, no lip-sync driving audio.
   Durations stretch to 8/10/12/13/15s single takes. The 3 product hero shots use an uploaded
   product photo (`media_input` 1451ed9c) + motion-photography prompts at 8–9s with
   `generate_audio: false`.
3. **02:13** — three seed_audio closing VO lines (speech_rate 0), cloned from a NEW uploaded MP3
   reference (44c2024a.mp3, the Arizona woman's voice): a grief line, the resolution line that names the product, and the offer line (the record's wording is run output and is not kept here).

Scene coverage repeats the Wave 2 story (Thai market/night market, hospice, airport, airplane,
Arizona cemetery, headstone, forearms comparison) — same film, new production method.

## Asset-chain mechanics (how jobs connect)

1. **Voice cloning via @Audio slots.** An audio job's `medias` array carries `role: "audio"`
   entries; the prompt refers to them positionally as @Audio1, @Audio2. July: every elder VO
   references one uploaded WAV (`a30c1e2a...sfx.wav`, an `audio_input` = her source voice) and
   prompts open with "@Audio1 is the voice reference - match it EXACTLY: an 82 year old Thai
   elder...". Aug: each character got ONE base take generated from a pure prose description
   (no reference), then every subsequent line references that take (`text2speech_job`) as
   @Audio1 — "@Audio1 is the SAME speaker: ... Generate her next recording in the identical
   voice." Late retries stack TWO takes (@Audio1 and @Audio2, e.g. 409abea2) to lock the accent.
2. **Still → video via role "image".** Every video job's `medias` has one `role: "image"` entry of
   type `image_job` (the start frame). Silent b-roll = image only. Lip-sync = image +
   `role: "audio"` entry pointing at a `text2speech_job` (or uploaded `audio_input` in early July
   tests). No text prompt on the video job at all — the scene still + VO track ARE the direction.
3. **Character → scene via stacked image refs.** Aug seedream scene jobs list 1–6 `role: "image"`
   refs mixing `image_job` (character stills, boards, July product shots) and `media_input`
   (uploaded product renders, wardrobe refs). E.g. hospice scene 03f6d704 = [0dbd36ad man
   portrait]; night-market handoff 795440b9 = [Thai-woman upload, 942424a3 turnaround, e3af5922
   Arizona woman, 33e6a8a4 July product shot].
4. **Recurring anchor uploads:** a30c1e2a_sfx.wav (elder voice, 65 uses), a7fbb368.png (Thai
   woman ref, 31), 61a3acde.jpg (elder photo ref, 23), b13bdc54.jpg (20), 2bcf9ea9 (product).

## Iteration patterns

- **Same line, many takes:** the hook line x14 takes;
  the product-name line x13; elder intro line x5.
  Prompt-engineering escalates across retries: "match it EXACTLY" → "The speaker IS the same
  person" → "Voice cloning task... mandatory voice reference" → "CRITICAL: ... EXACT clone" —
  same line, different scaffolding, hunting for accent stability.
- **Same (still, VO) pair re-rendered:** video retries keep the identical image+audio pair and
  just re-roll seedance: (0af2a846 elder-interview + 3de4c921 VO) x3, (d4edefc9 + 9e93126a) x3,
  (4b9a0a1c + 9e93126a) x3, (4c4dc160 + c8727515) x3, eight more pairs x2.
- **July → Aug voice redesign:** July elder VOs ran speech_rate +15 (fast); the Aug session
  rebuilt all voices at negative speech_rate (-5..-15, slower delivery) and added
  expression_intensity 5. The elder herself was re-scoped in Aug to speak one short THAI
  sentence (09769f9c, speech_rate -15); English narration moved to the 45yo Thai woman and the
  Arizona couple.
- **Aspect exploration before production:** Aug 10 19:50-20:10 built 3:2/16:9/3:4 character and
  wardrobe boards, then 20:43+ committed to 9:16 2K scene stills, then 03:49-07:17 (Aug 11) ran
  video production.

## Story/scene coverage (visually verified from outputs)

_(The ad's story and scene list are the brand's creative — run output, not kept in this repo.)_

## Representative FULL verbatim prompts / params

_The verbatim job records (ids, params, prompts) are run output and are not kept in this repo; `evidence-run.json` beside this file carries their shape. The record held these entries:_

- Voiceover — July elder clone (with voice params)
- Voiceover — Aug base voice creation (64yo man, no reference)
- Voiceover — Aug two-reference continuity retry (45yo Thai woman)
- Image and video jobs — verbatim params (prompts empty as stored, see caveat)
- CHAR STILL JULY
- CHAR STILL AUG
- SCENE STILL AUG
- SILENT JULY
- SILENT AUG
- LIPSYNC JULY
- LIPSYNC AUG
- VO JULY ELDER
- VO AUG BASE MAN
- VO AUG CONTINUITY
- Wave 3 — character drama shot (still + prompt + generate_audio)
- Wave 3 — product hero shot (uploaded product photo + prompt, generate_audio false)
- Wave 3 — pure text-to-video (no reference image)
