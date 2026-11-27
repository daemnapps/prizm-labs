# Singing Ads

What it makes: a 9:16 3D cartoon drama ad that tells the story of the user's own song or first-person narration phrase by phrase; the final film's audio is the user's file, unchanged, first frame to last.
Sources: `commands/singing-ads.md`; its style block comes from `drama-ads/scripts/styles/feature-3d.md`. The catalog has 3 singing-ads cards (`drama-ads/catalog/_cards.md`, style "Singing ads"); the command asks `ads_studio_story_recipe` for an example card or `"/singing-ads"` and carries its `story_id` as `drama_ads_id`.

## Inputs it needs
- The user's audio file (mp3, m4a, wav, ogg): a first-person story told over music or narration. Its length is the film's length (ffprobe).
- The user's instructions; the product if the audio does not name it (shown in the last picture, asked in the same round); optionally the product photo.
- One question round before any paid step: clip quality with total price, plus the product question. Nothing else is asked.

## Steps in order
0. **The ad's record:** `ads_studio_story_recipe` once; `story_id` becomes `drama_ads_id` on every generation.
1. **Settings:** length from ffprobe, 9:16, look `feature-3d`; price every distinct image and clip request with `estimate_*_cost`; ask the quality (draft 480p to be finalized, or 480p/720p/1080p).
2. **Transcribe** the whole file with faster-whisper (word timestamps, no VAD on a song), write `lines.tsv` of 2-4 word phrases split at punctuation or gaps over 0.4 s.
3. **Story map:** one picture per phrase; cast and story only from what the audio says; fixed outfit and one signature colour per character; 5-8 recurring locations; pacing about 1.9 s a shot; time-jump words become title cards.
4. **Reference images** (look at each, remake wrong ones): master, character sheets, later-look sheets, two-panel location sheets, product sheet.
5. **Clips** (5-14 s windows at phrase boundaries, 3-11 timed shots each): first clip alone and checked, rest in batches of up to 12, at most 16 running; 2 fps contact-sheet check; remake only wrong identity, missing beat, stray text/brands.
6. **Assembly:** frame-exact cuts at 24 fps, scale 1080x1920, join with the concat demuxer, add the user's audio (AAC 192k), burn ASS captions.
7. **Check and deliver:** ffprobe both files, 0.5 fps contact sheets, upload both, `show_result` (`singing_ad`), report with links, credits, inventions, Meta risks.
8. **Final version** (only if made as drafts and the user approves): finalize each clip from its `draft_job_id`, reassemble identically.

## Prompt blocks, word for word

**1. Style block, `feature-3d` (the master image carries it word for word)** — `drama-ads/scripts/styles/feature-3d.md`
```text
3D animated feature-film look: smooth, rounded, stylised 3D characters with slightly oversized heads, large expressive eyes with
big irises and bright catchlights, full expressive brows, small soft noses, soft rounded jaws, smooth skin with a gentle warm glow
and rosy cheeks, hair sculpted in soft flowing clumps with fine strands, rounded hands with five fingers; age shows in soft
sculpted wrinkles and grey hair. Clothes in real fabrics with soft folds: fine knit, cotton, corduroy, wool. Sets at real scale
with slightly simplified, rounded forms and clean, finished surfaces: painted plaster, wood, tile, enamel, fabric. Rich, warm
colour: one or two strong, saturated colours from the film's facts in the clothes and the set, against warm neutrals.
```

**2. Style line (line 1 of every clip prompt)** — same file
```text
3D animated feature-film look: smooth, rounded stylised characters with large expressive eyes, warm golden light, rich warm
colours with one or two strong accents, richly dressed real-scale sets with gently rounded forms.
```

**3. Pace paragraph (line 2 of every clip prompt, word for word)** — `commands/singing-ads.md` step 5
```text
Brisk, energetic real-time pace: every character moves with purpose, about one and a fifth times the speed of a calm everyday pace, snappy and decisive, never slow motion, never drifting or lingering. Every shot opens mid-action and contains one clear story action with a visible cause and result. Fast, punchy feature-animation acting: quick head turns, sharp reactions, big readable poses, eyes and brows snap; hair and cloth whip and settle. Energetic camera: quick push-ins, short whip pans, handheld energy in tense moments, tracking shots that keep up with fast walkers. Warm light with a gentle rim, shallow depth of field. Hard cuts between shots.
```

**4. Closing paragraph of every clip prompt, word for word** — same
```text
The characters act and react without speaking; no voice-over, no narration. No music and no score. No captions, no subtitles, no on-screen text. No slow motion. Every character keeps the exact face, hair, body and clothes of their sheet in every shot; every place matches its location sheet; the <PRODUCT> keeps its exact label.
```

**5. Clip prompt structure** — same
```text
- Prompt structure:
  - Line 1: the style line.
  - Line 2, word for word:
    "Brisk, energetic real-time pace: every character moves with purpose, about one and a fifth times the speed of a calm everyday pace, snappy and decisive, never slow motion, never drifting or lingering. Every shot opens mid-action and contains one clear story action with a visible cause and result. Fast, punchy feature-animation acting: quick head turns, sharp reactions, big readable poses, eyes and brows snap; hair and cloth whip and settle. Energetic camera: quick push-ins, short whip pans, handheld energy in tense moments, tracking shots that keep up with fast walkers. Warm light with a gentle rim, shallow depth of field. Hard cuts between shots."
  - Then the @Image bindings.
  - Then the timed shots: "0-3 s: <framing>: <who> <posture> <action with its result>."
  - End with, word for word:
    "The characters act and react without speaking; no voice-over, no narration. No music and no score. No captions, no subtitles, no on-screen text. No slow motion. Every character keeps the exact face, hair, body and clothes of their sheet in every shot; every place matches its location sheet; the <PRODUCT> keeps its exact label."
  - Leave the product clause out of that line in a clip that does not show the product.
```

**6. Reference binding and limits** — same
```text
- References: at most 9 images, in this order: location sheet(s), then character sheets, then the product sheet in a clip that shows the product. Bind each one in the prompt ("@Image1 is <NAME>, <age, look, outfit>").
```

**7. Master image instruction** — step 4
```text
1. A style-setting master image: the feature-3d style block word for word, plus the main location with the hero and up to two other characters of the story. Write the ages explicitly (e.g. "looks a youthful 51, mostly jet-black hair").
```

**8. Character sheet** — step 4
```text
2. A character sheet per character, with the master attached: front, three-quarter and profile full body, plus a head-and-shoulders close-up, on light grey.
```

**9. Later-look sheet, location sheet, product sheet** — step 4
```text
3. Only when the audio changes a character's look: a sheet of the later look, with the earlier sheet attached first, then the master. Prompt: "the same person, same face, eyes, skin and age", then list only the changes.
```

```text
4. A two-panel location sheet per place, master attached: the camera view and the reverse view, with no people.
```

```text
5. Only when the film has a product: the product sheet, with the master and the product photo (when there is one) attached: front and three-quarter views, "keep the label text and layout exactly".
```

**10. Flashbacks and props** — step 5
```text
- Write flashbacks as "Flashback, cooler colours: …".
```

**11. Video words, `feature-3d`** (the style file's own, for reference; this command's own pace paragraph replaces them) — `drama-ads/scripts/styles/feature-3d.md`
```text
Smooth, fluid feature-animation motion with clear, readable poses; broad, expressive facial acting: eyes and brows move a lot,
natural blinks, clear mouth shapes synced to every word; hair and cloth follow through softly; soft warm light with a gentle rim
and a soft glow around bright windows, shallow depth of field with warm round highlights in the blur; a smooth, motivated camera.
Clear, close character voices over quiet room tone, no music.
```

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Master, character, location, product sheets | `seedream_5_5` | 2k, 16:9, no "label" parameter |
| Clips | `seedance_2_5` | mode `omni_reference`, 9:16, `generate_audio:false`, duration = window rounded up; `draft:true` (480p) or 480p/720p/1080p; up to 9 image refs |
| Title-card background (only if the audio has time jumps) | `seedance_2_5` text-to-video | 6 s burgundy satin rippling, no text, same quality as the clips |
| Finalize | `seedance_2_5` | `draft_job_id` = the clip's draft; always 1080p; keeps motion and framing, no prompt changes |
| Transcription, captions, assembly | none | faster-whisper `small`, ASS captions, ffmpeg |
No song or voice model: the audio is the user's own.

## Checks and gates
- One question round only (quality with price, product). The quality answer is the go-ahead; loading the command authorises nothing.
- Clips: the first clip is sent alone and checked (quality, 9:16, right length). Clip sound is never used. Windows plus card gaps must cover the audio exactly; the film must match the audio length within 0.05 s.
- Story rules: only what the audio tells (no invented antagonist, before/after, or friend who brings the product); every shot has a visible action with cause and result; quoted speech is acted, no lip-sync; hook readable by second 1-2.
- Meta rules: no brands except the user's product, no celebrities, clothed cast; a child is an ordinary character in an everyday scene, never in a romantic, sexual, violent or dangerous one. Props that could carry a brand are "plain, unlabeled".
- Never adds, nor suggests, an offer, price, discount, guarantee badge or "ORDER NOW" button; burns text only when the user's message asks for it, in their wording.
- Final check: ffprobe 1080x1920 with audio and the audio's length; contact sheets for hook, title cards, seams, look change, last picture, captions against words. Report shots that drift from words and Meta risks.
- Drafts: finalize within 7 days of the draft; the final is checked against its draft.

## Price pattern
Never written down: each price from `estimate_image_cost` / `estimate_video_cost` with the exact params, one lookup per distinct image request and clip length, added up and said once before the first paid call; the finalize cost quoted again and waited for. Rough, from `_prices.md`, for a 60 s song (about 7 clips of ~9 s, 10 pictures): draft clips about 200 credits, finalized 1080p about 960 on top; pictures not quoted for `seedream_5_5`.

## Cheap swap
- Clips: `wan3_0` 480p at 7.5/10 s (takes `generate_audio` off, up to 10 image refs, so the workflow's 9) instead of `seedance_2_5` at 30/10 s draft or 160/10 s 1080p: a 60 s film about 45 credits (saves ~155 vs draft, ~915 vs 1080p). It has no `draft_job_id` finalise path; upscale locally instead. `gemini_omni_flash_1_2` 360p 7.5/10 s (max 7 image refs, ≤10 s with refs) also works.
- Pictures: `seedream_5_0_flash` 2k at 0.5 (or `gpt_image_2_6_flare` 1k low 0.75) in place of `seedream_5_5` (not quoted).
- Local free: faster-whisper transcription (already in the sandbox), ffmpeg cuts/concat/captions, Real-ESRGAN upscale of 480p clips to 1080x1920 instead of a paid 1080p finalize.
- Writing (story map, phrase-per-picture list, prompts): Claude on the plan, free to us.
