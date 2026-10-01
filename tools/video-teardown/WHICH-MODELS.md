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

## Making the frames — Soul v2

Every still starts here: `text2image_soul_v2`.

| Setting | Value | Why |
|---|---|---|
| Size | 1536 × 2048 | portrait, enough resolution to crop |
| Style | General | anything else fights your prompt |
| `enhance_prompt` | **off** | on, it rewrites you and drifts off the brief |
| Seed | fixed, one per character | the same number gives you the same face |

**The character-sheet trick.** Before you generate any scene, make one image
per person as a split-screen sheet: full body on the left, chest-up close-up
on the right, both the same character. Then feed that sheet in as the
reference for every scene they appear in. That is what stops them being a
different human in every shot — it is the single biggest difference between
work that looks made and work that looks broken.

---

## Making the shots — Seedance 2.0

Frames become video with `seedance_2_0`.

| Setting | Value |
|---|---|
| Ratio / size | 9:16, 1080 × 1920 |
| `mode` | `std` |
| `generate_audio` | `true` — it invents its own ambience and dialogue |
| `multi_shots` | `false` — one shot per generation, always |
| `speedramp` | `auto` |
| Length | **4s per scene beat**, 6s for silent b-roll |

Longer single takes (8–15s) work when one continuous moment carries the beat,
but cutting 4-second shots is what holds attention.

Feed each generation the character sheet plus a full cinematic description of
the moment — not a shot label. "Cinematic drama, golden morning market stall.
The elderly woman from the reference image reaches across the counter…" beats
"scene 3, woman at stall" every time.

---

## Voice, if you need it — Seed Audio

`seed_audio`, wav, 24000 Hz.

| Setting | Value |
|---|---|
| `speech_rate` | −5 to −15 (slower reads as more serious) |
| `loudness_rate` · `pitch_rate` | 0 |
| `expression_intensity` | 5 |

No voice presets. Describe the person in words, and clone from an uploaded
reference file when you want a specific voice.

Note: if Seedance is already generating audio for a shot, you do not need a
separate voice track for it. Use Seed Audio for narration over the cut.

---

## The order you do it in

1. Character sheets — one per person, fixed seed. **Do this first, always.**
2. Frames — the brief's image prompt plus the character sheet as reference.
3. Shots — Seedance, 4 seconds, one shot per generation.
4. Voice — only if the cut needs narration.

## When something looks wrong

**A different face every shot** — you skipped the character sheet, or changed
the seed. Go back to step 1.

**It ignored half your prompt** — `enhance_prompt` is on. Turn it off.

**Everything feels stiff** — your prompts are shot labels, not descriptions.
Write what a person watching would see.

**The product looks wrong** — nothing in the prompt told it what the product
looks like. That comes from your brand folder; fill that part in.
