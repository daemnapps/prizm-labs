# Which models to use, and the settings that work

Do not leave this on Auto. These are the exact models and settings behind the
videos this system has actually produced — not a guess at what might work.

Everything below runs inside **Higgsfield Supercomputer**.

---

## Reading the video — Gemini

When you upload a swipe video and ask it to describe every scene, that is a
Gemini model doing the watching.

| Use | Model |
|---|---|
| First choice | `gemini-3-flash-preview` |
| If it is busy | `gemini-3.5-flash` |
| For a long or complicated video | `gemini-3.1-pro-preview` |

Flash is the right default — it is fast and it does not miss scenes. Only
reach for Pro when a video is long, dense, or full of overlapping dialogue.

---

## Making the frames — GPT Image 2.5

Every still is GPT Image 2.5, called through the Higgsfield command line (the owner, 2026-10-20 and 2026-10-26; the Soul model is retired).

| Setting | Value | Why |
|---|---|---|
| Size | portrait, 9:16 | the ad's own shape, enough resolution to crop |
| Reference images | the character sheet, plus the real product picture | identity comes from the references, not from words |
| One version | one picture per frame | pick on the judge's review, not by rolling again |

**The character-sheet trick.** Before you generate any scene, make one image
per person as a split-screen sheet: full body on the left, chest-up close-up
on the right, both the same character. Then feed that sheet in as the
reference for every scene they appear in. That is what stops them being a
different human in every shot — it is the single biggest difference between
work that looks made and work that looks broken.

---

## Making the shots — Seedance 2.5, at 480p

Frames become video with Seedance 2.5 on Higgsfield, at 480p only; the clip is upscaled to 1080 × 1920 on this Mac afterwards (the owner, 2026-10-26). How a clip is asked for: `tools/video-production/SEEDANCE-INPUTS.md`.

| Setting | Value |
|---|---|
| Ratio / size | 9:16, 480p (upscaled to 1080 × 1920 later) |
| Image 1 | the approved still, which is also the first frame |
| Audio | the locked read for a talking shot; the line is not typed into the prompt |
| Length | 4 to 10 seconds per call; one shot per call |
| Takes | one take, three tries at most |

Feed each generation the approved still and a description of the moment in
whole-second windows, not a shot label. "Image 1 is the first frame. The
elderly woman at the market stall reaches across the counter at 0–2 s…"
beats "scene 3, woman at stall" every time.

---

## Voice, if you need it — Seed Audio

`seed_audio`, wav, 24000 Hz (narration over the cut only; a talking clip carries the locked ElevenLabs read).

| Setting | Value |
|---|---|
| `speech_rate` | −5 to −15 (slower reads as more serious) |
| `loudness_rate` · `pitch_rate` | 0 |
| `expression_intensity` | 5 |

No voice presets. Describe the person in words, and clone from an uploaded
reference file when you want a specific voice.

Note: a talking shot already carries its voice, so it needs no separate voice track. Use this for narration over the cut.

---

## The order you do it in

1. Character sheets — one per person. **Do this first, always.**
2. Frames — the brief's image prompt plus the character sheet as reference (GPT Image 2.5).
3. Shots — Seedance 2.5 at 480p, one shot per generation.
4. Voice — only if the cut needs narration.

## When something looks wrong

**A different face every shot** — you skipped the character sheet. Go back to step 1.

**Everything feels stiff** — your prompts are shot labels, not descriptions.
Write what a person watching would see.

**The product looks wrong** — nothing in the prompt told it what the product
looks like. That comes from your brand folder; fill that part in.
