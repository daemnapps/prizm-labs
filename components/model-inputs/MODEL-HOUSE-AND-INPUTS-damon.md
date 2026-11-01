# Model House and Inputs (updated 26 Oct 2026, evening)

A chain asks the Model House for a job, gets one model through Higgsfield, and reads that model's rulebook for what can go
in. Page (what is still open): (private page)

## The setup

Pictures run on **GPT Image 2.5** through Higgsfield's command-line tool (signed in on this Mac); **Seedream 5 Pro** then
**Nano Banana Pro** are backups, used only when GPT fails. Clips run on **Seedance 2.5** through Higgsfield's keyed API at
480p, upscaled on this Mac; **Kling** (Higgsfield API) is the clip backup. No other picture or clip model.

| Job | Model | Door | State |
|---|---|---|---|
| pictures.generate / pictures.edit | GPT Image 2.5 | Higgsfield command line | door built, House switch in progress (OpenAI direct stays as a safety net until the real image ad passes) |
| pictures.backup | Seedream 5 Pro | Higgsfield command line | rulebook filled |
| pictures.object | Nano Banana Pro | Higgsfield command line | rulebook filled |
| clips.seedance | Seedance 2.5 | Higgsfield API | running, rulebook filled |
| clips.backup | Kling | Higgsfield API | building (rulebook, prompt builder, fallback) |
| swipe_footage.swap / motion_transfer | Higgsfield object swap / motion control | Higgsfield API | running, rulebooks to make |

Stays off Higgsfield, on purpose: ElevenLabs voice, music and Scribe (Higgsfield only offers v4, no timing model), the
Gemini judge, and the local upscale (Real-ESRGAN) and 3D.

Higgsfield's keyed API does not list GPT Image 2.5, Seedream 5 Pro or Nano Banana Pro (checked 26 Oct at
open.higgsfield.ai), which is why the three picture models go through the command line. Cost check: GPT Image 2.5 about
0.25 credits a low-quality picture, Seedream 2.5, Nano Banana Pro 2. Account: <brand> workspace, ultra plan.

## How a job is called, and what catches it when it fails

The chain asks for a job by name (`pictures.edit`), never a model. The House answers with the first model and door, which
also picks the rulebook. The chain checks the call against the rulebook, sends it, and on failure the next rung takes the
same prompt, pictures and size. A backup is a House row, not chain code. The run record says which rung made the work.

| Job | First | If it fails or is refused |
|---|---|---|
| pictures.generate, pictures.edit | GPT Image 2.5 | one more try on GPT; then Seedream 5 Pro (refused); then Nano Banana Pro |
| pictures.object | Nano Banana Pro | none yet |
| clips.seedance | Seedance 2.5, one take | another take (three at most), then Kling |
| swipe_footage.swap | object swap | motion control when the swap kept the original face |
| judge | Gemini 3.1 Pro | when busy: Gemini 3.5 Flash, then Gemini 3 Flash Preview |
| upscale | Real-ESRGAN (this Mac) | a Higgsfield upscaler (replacing the fal one) |

Changing one part of a picture (a headline swap) is an ordinary GPT edit that says what must not change; no mask and no
extra model. If the picture drifts, the approved piece is pasted back onto the original.

## How the prompts work

**GPT Image 2.5** (`image_production/plain.py`): six labelled sections in a fixed order, an empty one left out: INPUTS
(which picture is which) · THE PICTURE · THE PRODUCT (keep the real one exact, true size) · THE PEOPLE (lookalikes or
made-up) · THE FRAME (9:16, centre 4:5 safe zone, top and bottom 15% bleed) · RULES (change only what THE PICTURE says; no
other writing). Up to 16 pictures, each numbered with a job. Avoid "cinematic" or "studio" for a real photo.

**Seedance 2.5** (`machine/seedance_prompt.py`): four blocks, about 200 words: ASSETS (Image 1 is the first frame; Audio 1
is the voice) · SUMMARY (the look, one sentence) · TIMELINE (`0-2s:` windows, one visible change each) · CONSTANTS (one
continuous take; same person, clothing, props, room, light; no subtitles; no background music). The spoken line is never
typed in the prompt. No emotion labels, no long lists of "no", no "cinematic". 9:16, 480p upscaled here, length = the read
+ 0.6 s, one take (three at most).

**Seedream 5 Pro, Nano Banana Pro, Kling, object swap, motion control:** each has (or is getting) a rulebook in
`components/model-inputs/inputs/`; the same rule for every model used: no model without its input manifest.

## Still open

- **First:** the prompt generator and preflight (shows the exact prompt, files, settings, rulebook findings and free cost
  for any job, builds from the real brief, never makes anything).
- **To make:** Kling rulebook and prompt builder; object swap and motion control rulebooks; Seedance clip limits checked in
  code; the video chain's field list reading its limits from the rulebook.
- **To wire:** picture backups; Kling clip backup; switch the four picture jobs to Higgsfield; headline swaps as normal GPT
  edits (confirm nothing needs a mask); a Higgsfield upscaler; retire fal and, after the real ad, OpenAI direct.
- **To prove:** no separate tests. Make one real image ad and one real video ad, after the generator has passed the inputs.
