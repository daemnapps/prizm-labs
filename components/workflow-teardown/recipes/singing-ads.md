# Singing Ads

A 9:16 cartoon story ad cut phrase by phrase to our own song or narration; the song is the soundtrack, unchanged.

Higgsfield original: `/singing-ads` · built from `sources/higgsfield/commands/singing-ads.md`, `sources/higgsfield/drama-ads/scripts/styles/feature-3d.md`, `sources/higgsfield/drama-ads/catalog/_cards.md`

## Price

| | |
|---|---|
| higgsfield | ≈560 credits draft (500 clips + ~60 sheets); ≈2,670 more for the 1080p final |
| house | ≈500 credits draft with banked sheets; upscale free |
| cheap | ≈125 credits (Wan 3.0 480p, banked sheets, free local upscale): about a quarter of the draft, a twentieth of the final |
| basis | 167 s song, prices quoted 2026-11-21 |

## Inputs

- **song**: the hand-off's song (assets/kit/song/*.mp3)
- **timed lyrics** (optional): assets/kit/song/lyrics-timed.json in the hand-off, else made free on this Mac (local-studio stt)
- **cast**: runs/ai-elements/<brand>/casting/<role>/full/master.png + sheets/look-*.png
- **places** (optional): runs/ai-elements/<brand>/sets/<set>/ first picture
- **product** (optional): runs/ai-elements/<brand>/products/<product>/model/product-sheet.png
- **house rules**: brands/<brand>/CLAUDE.md + the owner's hard rules (no disclaimers, no men kissing, clothed cast)

## Steps

### 0. The ad's record — `none`

Higgsfield opens a Drama Ads record so every clip is filed under one ad. Ours: the run folder and lane.json are the record.

| | model | credits |
|---|---|---|
| Higgsfield | ads_studio_story_recipe | 0 |
| our house | runs/higgsfield/<brand>/<label>/ + lane.json | 0 |

**Higgsfield, word for word**

```
## 0. THE AD'S RECORD

- If your tools include `ads_studio_story_recipe`, call it once before anything else: `preset_id` is the example card's id when the message names one, else `"/singing-ads"`. Skip this when you already hold a `story_id` it answered for this ad.
- Pass that `story_id` as `drama_ads_id` in `params` of every generation and batch item, and in `meta` of the final `show_result`. Without one, go on without it.
```

Check: lane.json carries the owner's go and a credit cap before any paid step.

### 1. Settings and the price — `plan.quote`

Measure the song, fix 9:16, pick the clip quality, quote the whole film before the first paid call.

| | model | credits |
|---|---|---|
| Higgsfield | estimate_image_cost / estimate_video_cost | 0 |
| our house | same quotes (they submit nothing) | 0 |

On this Mac: `ffprobe for the length`

**Higgsfield, word for word**

```
## 1. SETTINGS

- The audio: get the user's file into the sandbox the way the server's rule for attached media says (mp3, m4a, wav and ogg are accepted). Everything below works on that one file.
- Length: the audio's exact length, measured with ffprobe. Shape: 9:16. Look: feature-3d (smooth 3D feature-animation cartoon) with true-to-life everyday actions.
- Images: `seedream_5_5`, 2k, 16:9. Do not send a "label" parameter: the backend rejects it.
- Clips: `seedance_2_5` with mode `omni_reference`, aspect_ratio 9:16, generate_audio false, and duration = the clip window rounded up to the next whole second.
- Clip quality, asked once, each option with the film's total price beside it:
  - a draft cut: every clip sent with `draft: true` (480p), cheaper now, finalized later at 1080p (step 8);
  - or the finished resolution straight away: 480p, 720p or 1080p.
  - If the server answers that drafts are not available for this account, say so and offer the three resolutions.
- Prices are never written here and never remembered: get each one from `estimate_image_cost` or `estimate_video_cost` with the same `params` you will send (a price lookup submits nothing) — one lookup per distinct image request and per distinct clip length — and add them up for the film. Quote that total once, in the quality question, before the first paid call. When the plan grows, say the new total before the next paid call.
- Clip sound is never used. The final audio is the user's file only.
```

**Ours**

```
Song {song} is {seconds} s. Shape 9:16. Look: {style}. Clip model {clip_model} at {resolution}. Quote every distinct picture and clip length, add them up, write the total and the cap into lane.json, stop for the go.
```

Check: Total under the cap in lane.json.

### 2. Transcribe — `sound.words`

Words on the song's clock, 2-4 word phrases, written to lines.tsv. Drives the cuts and the captions.

| | model | credits |
|---|---|---|
| Higgsfield | faster-whisper small (sandbox) | 0 |
| our house | ElevenLabs Scribe (scribe_v1) | metered |
| cheapest | whisper-large-v3-turbo (local-studio stt) | 0 |

Cheap swap: A 3:46 song in 7 s on this Mac. Better still: the hand-off's lyrics-timed.json, no transcription at all. Registry: whisper-large-v3-turbo.

On this Mac: `python3 components/local-studio/local.py stt song.mp3 -o words.json`

**Higgsfield, word for word**

```
## 2. TRANSCRIBE

- Transcribe the whole file in one pass with faster-whisper with word timestamps, as a background job. The `small` model is already in `/opt/whisper-models` (pass it as `download_root`). Do not use vad_filter on a song.
- Write lines.tsv (start, end, phrase). A phrase is 2–4 words, split at punctuation or at gaps over 0.4 s.
- This file drives both the captions and the shot timeline.
- If transcription is impossible, ask the user for the lyrics and place the lines by the audio's energy gaps.
```

**Ours**

```
Phrases of 2-4 words, split at punctuation or at gaps over 0.4 s; columns start, end, phrase.
```

Check: Every sung line present, in order (the only song gate we hold).

### 3. Story map — `write.story_map`

One picture per phrase: cast only from the words, 5-8 recurring places, ~1.9 s shots, a cause and a result in every shot, the hook readable by second 1-2.

| | model | credits |
|---|---|---|
| Higgsfield | the chat model directing the run | 0 |
| our house | Claude on the signed-in plan | 0 |
| cheapest | Claude on the plan (writing costs don't count) | 0 |

Cheap swap: Writing is free to us; spend nothing here. Registry: claude-sonnet-5.

**Higgsfield, word for word**

```
## 3. STORY MAP (one picture per phrase)

- Cast and story: only what the audio tells. The narrator is the hero; every other character and a change in the hero's look appear only when the words say so. Never add a before-and-after change, an antagonist, or a friend who brings the product, that the audio does not have.
- The product, by where it is named:
  - in the audio: it enters the story the way the words say.
  - only in the user's message or attachment, never in the audio: ask, in the same round as the quality question, whether to show it; with no answer, show it. Shown, it is in the picture of the last phrase, in the hero's hand or standing in frame, with no effect the audio does not claim.
  - nowhere: the film has no product. Never invent one, and say so in the report.
- Give each character a fixed outfit and one signature colour; a hero whose look changes in the audio gets one colour per look.
- Places: 5–8 recurring locations, one location sheet each. One-off places (car, store, gym, doctor, billboard street) are written straight into the clip prompts.
- Every phrase gets its own picture, cut on the word; every noun in the narration gets its own shot.
- Pacing:
  - Average shot about 1.9 s, about 30 cuts a minute.
  - Many 0.5–1.2 s close-ups of hands and props (keys, ring, zip, earring, pouch).
  - Show a shock at 2–3 sizes in a row: wide, medium, extreme close-up.
- Every shot contains one visible story action with a cause and a result, for example: she drops her lunch tote and the salad spills; she slams the laptop shut; the elevator doors close in his face. Never a character just standing and looking.
- Quoted speech ("She said, get on a plane") is shown as that person acting it, with no lip-sync.
- Time jumps the audio names ("Week one…") become title cards added at assembly. Leave those seconds out of the clips.
- Hook: the opening situation of the audio must be readable by second 1–2; when it is a conflict, both sides are in frame.
- Meta rules:
  - No brands except the user's product, no celebrities, and a clothed cast. A child in the cast is an ordinary character in an everyday scene: never in a romantic, sexual, violent or dangerous situation.
- Product photo: when the film has a product, ask for its photo together with the quality question. When the answer brings none, say that you will design the product's look yourself from what the user and the audio say, and go on; say it again in the report.
```

**Ours**

```
From lines.tsv, give every phrase its own shot, cut on the word. Cast = only who the words name: {cast}. A change of look only where the words change it: {looks}. Places = {places} (5-8 recurring). The product {product} enters where the words name it; otherwise in the last phrase, in hand. Average shot 1.9 s; many 0.5-1.2 s close-ups of hands and props; a shock at three sizes (wide, medium, extreme close-up). Every shot: one visible action with a cause and a result. Quoted speech is acted, never lip-synced. Hook readable by second 1-2; a conflict shows both sides. {house_rules}
```

Check: Every phrase has a shot; nothing the words don't say.

### 4. Reference pictures — `pictures.sheets`

Style master, a sheet per character, a sheet per later look, a two-panel sheet per place, a product sheet.

| | model | credits |
|---|---|---|
| Higgsfield | seedream_5_5 (now seedream_v5_pro), 2k, 16:9 | 2.5 each, ~20-25 sheets = 50-60 |
| our house | our banked cast, looks, sets and product sheet (0); a missing sheet only: GPT Image 2.5 (gpt-image-2.5) | 0 for banked, ~2 per gap |
| cheapest | Seedream 5.0 Flash, 2k (seedream_5_0_flash) | 0.5 |

Cheap swap: Only for a sheet we have no bank for. Banked sheets cost nothing and keep the cast the same across ads. Registry: missing.

**Higgsfield, word for word**

```
## 4. REFERENCE IMAGES (Seedream 5.5; look at every one and remake any that's wrong)

1. A style-setting master image: the feature-3d style block word for word, plus the main location with the hero and up to two other characters of the story. Write the ages explicitly (e.g. "looks a youthful 51, mostly jet-black hair").
2. A character sheet per character, with the master attached: front, three-quarter and profile full body, plus a head-and-shoulders close-up, on light grey.
3. Only when the audio changes a character's look: a sheet of the later look, with the earlier sheet attached first, then the master. Prompt: "the same person, same face, eyes, skin and age", then list only the changes.
4. A two-panel location sheet per place, master attached: the camera view and the reverse view, with no people.
5. Only when the film has a product: the product sheet, with the master and the product photo (when there is one) attached: front and three-quarter views, "keep the label text and layout exactly".
```

**Ours**

```
Master: {style_block} + {main_place} with {hero} and up to two others; ages written out. Sheet per character (master attached): front, three-quarter, profile full body + head-and-shoulders close-up on light grey. Later look: the same person, same face, eyes, skin and age; then only the changes: {look_changes}. Place: two panels, camera view and reverse, no people. Product: front and three-quarter, keep the label text and layout exactly.
```

Check: Look at every sheet; remake any that's wrong. Banked sheets are already signed off.

### 5. Clips — `clips.scene`

5-14 s windows on phrase boundaries, 3-11 timed shots each, up to 9 reference pictures bound by name, no sound, no text.

| | model | credits |
|---|---|---|
| Higgsfield | seedance_2_5 omni_reference, 9:16, sound off, draft 480p | 30 per 10 s (≈500 for a 167 s song) |
| our house | Seedance 2.5 (seedance-2.5@higgsfield); song-ad clips are MiniMax H3 2K by house ruling | 30 per 10 s at draft |
| cheapest | Wan 3.0, 480p, image references (wan-3.0@higgsfield) | 7.5 per 10 s (≈125 for a 167 s song) |

Cheap swap: Takes up to 10 reference pictures, the same @Image binding and the same timed shot list. Second cheap pick: Gemini Omni Flash 1.2 at 360p, 7.5 per 10 s, max 7 pictures and 10 s per clip (registry: missing). Registry: wan-3.0.

On this Mac: `RIFE frame interpolation and Real-ESRGAN upscale afterwards (local-studio interp / upscale), free`

**Higgsfield, word for word**

```
Line 1: the style line.
Line 2: Brisk, energetic real-time pace: every character moves with purpose, about one and a fifth times the speed of a calm everyday pace, snappy and decisive, never slow motion, never drifting or lingering. Every shot opens mid-action and contains one clear story action with a visible cause and result. Fast, punchy feature-animation acting: quick head turns, sharp reactions, big readable poses, eyes and brows snap; hair and cloth whip and settle. Energetic camera: quick push-ins, short whip pans, handheld energy in tense moments, tracking shots that keep up with fast walkers. Warm light with a gentle rim, shallow depth of field. Hard cuts between shots.
Then the @Image bindings.
Then the timed shots: "0-3 s: <framing>: <who> <posture> <action with its result>."
End: The characters act and react without speaking; no voice-over, no narration. No music and no score. No captions, no subtitles, no on-screen text. No slow motion. Every character keeps the exact face, hair, body and clothes of their sheet in every shot; every place matches its location sheet; the <PRODUCT> keeps its exact label.
```

**Ours**

```
{style_line}
Brisk, energetic real-time pace: every character moves with purpose, about one and a fifth times the speed of a calm everyday pace, snappy and decisive, never slow motion, never drifting or lingering. Every shot opens mid-action and contains one clear story action with a visible cause and result. Fast, punchy feature-animation acting: quick head turns, sharp reactions, big readable poses, eyes and brows snap; hair and cloth whip and settle. Energetic camera: quick push-ins, short whip pans, handheld energy in tense moments, tracking shots that keep up with fast walkers. Warm light with a gentle rim, shallow depth of field. Hard cuts between shots.
@Image1 is {place}. @Image2 is {NAME}, {race}, looks {age}, {hair}, {marks}. @Image3 is {NAME}'s {look} outfit. ...
{before_state}
0-{t1} s: {framing}: {who} {posture} {action and its result}. {t1}-{t2} s: ...
The characters act and react without speaking; no voice-over, no narration. No music and no score. No captions, no subtitles, no on-screen text. No slow motion. Every character keeps the exact face, hair, body and clothes of their sheet in every shot; every place matches its location sheet; the {product} keeps its exact label.
```

Check: Send the first clip alone and check it (quality, 9:16, length). Then 2 fps contact sheet per clip; remake only a wrong identity, a missing beat, stray text or brands.

### 6. Assembly — `edit.assemble`

Cut each clip to its window frame-exact at 24 fps, 1080x1920, title cards if any, join, lay the song, burn captions.

| | model | credits |
|---|---|---|
| Higgsfield | ffmpeg in the sandbox | 0 |
| our house | Video Edit (components/video-edit), the Studio's edit line | 0 |

On this Mac: `ffmpeg; captions as ASS from lines.tsv`

**Higgsfield, word for word**

```
## 6. ASSEMBLY

- Cut each clip and each card gap to its exact timeline window, frame-exact at 24 fps: frames = round(end×24) − round(start×24).
  - Scale to 1080×1920 with lanczos. Encode with libx264 veryfast crf 17, no audio.
  - Why 1080×1920 when the clips are draft or 720p: only so the burned-in text (captions, title cards, any overlay the user asked for) is drawn sharp, and because 1080×1920 is the standard Reels/Stories upload size. It adds no detail to the picture. Tell the user this in the report.
- Fonts: the sandbox has Montserrat ExtraBold and Metropolis for captions and overlays; check the serif with `fc-list | grep -i "DejaVu Serif"` and use Liberation Serif when it is missing. Inter is not installed.
- Title cards (only when the story map has them): cut from the satin clip, with the words the audio says for that jump in cream, DejaVu Serif: the label (e.g. "WEEK") at size 150, at 36% height, and its number, when it has one, at size 330, at 45% height.
- Join the segments with the concat demuxer. The result must match the audio's length to within 0.05 s.
- Overlays other than captions and title cards: none by default. Never add, and never suggest, an offer, a price, a discount, a guarantee badge or a call-to-action button such as "ORDER NOW". Burn one in only when the user's own message asks for that text on screen, in their wording: Montserrat ExtraBold, in a box, large enough to read on a phone, clear of the captions and of the Reels buttons; any text with "%" needs expansion=none. Words the audio says are captions, not overlays.
- Add the user's audio (AAC 192k, -t = the audio's length, faststart). That gives \*\_clean.mp4.
- Captions: build an ASS file from lines.tsv.
  - Montserrat ExtraBold 76, white, outline 3.5, shadow 3, bottom-centre, MarginV 700, so they sit clear of the Reels buttons.
  - Burn them in to make \*\_captioned.mp4.
  - When the user asked for an end overlay, end the last caption before it appears.
- Run the encodes as background jobs. A 6-minute 1080p film takes about 10 minutes: encode a long film in parts that each fit the 15-minute limit, then join them with the concat demuxer.
```

**Ours**

```
Windows from the story map; frames = round(end*24) - round(start*24); scale 1080x1920 lanczos; x264 crf 17; song as AAC 192k; captions Montserrat ExtraBold 76, white, outline 3.5, shadow 3, bottom-centre, MarginV 700. No offer, price or call to action on screen.
```

Check: Length matches the song within 0.05 s.

### 7. Check and deliver — `behind.judge`

ffprobe both files, 0.5 fps contact sheets, check the hook, cards, seams, change of look, last picture, captions against words.

| | model | credits |
|---|---|---|
| Higgsfield | the directing chat model looks at contact sheets | 0 |
| our house | Gemini 3.1 Pro judge | metered, cents |
| cheapest | Gemini 3 Flash fast read (gemini-3-flash-preview) | cents |

Cheap swap: House rule: every read inside a run is the judge; Flash is a person's pick only. Registry: gemini-3-flash-preview.

On this Mac: `ffprobe + contact sheets`

**Higgsfield, word for word**

```
## 7. CHECK AND DELIVER

- Run ffprobe on both outputs: 1080×1920, audio present, the audio's length.
- Make 0.5 fps contact sheets in a NEW folder.
- Check:
  - the hook;
  - every title card;
  - every seam (no flash of the old shot, no repeated move);
  - the change of look, when the audio has one;
  - the last picture (the product, when the film has one, and any overlay the user asked for, legible);
  - captions against the words.
- Upload both files to Higgsfield, one at a time: `media_upload` for the upload URL, a PUT of the file from the sandbox with its `Content-Type: video/mp4` header, then `media_confirm`. Show the captioned film with `show_result({ action: "singing_ad", media_id, meta: { drama_ads_id } })` (`meta` only when you hold the id) and give the user the link `media_confirm` returned for each file. A link alone is not a delivery: the widget comes first.
- Report:
  - the links;
  - the credits spent;
  - what was invented (product look, characters);
  - shots that drift from their words;
  - Meta risks (before/after rules, and health or weight-loss claims in the audio itself);
  - if the clips are drafts: that this is a draft cut, its picture upscaled to 1080×1920 only for sharp text, and the finalize offer with its price (step 8).
```

**Ours**

```
Check: the hook; every title card; every seam; the change of look; the last picture (product legible); captions against the words. Report what was invented and any shot that drifts from its words.
```

Check: Delivered to the Studio and Drive, never to Meta from here.

### 8. Final version — `clips.finish`

After the owner likes the draft: re-render every clip at 1080p from its draft (same motion), reassemble.

| | model | credits |
|---|---|---|
| Higgsfield | seedance_2_5 draft_job_id → 1080p | 160 per 10 s (≈2,670 for a 167 s song) |
| our house | Real-ESRGAN upscale on this Mac (house: 480p made, upscaled locally) | 0 |
| cheapest | Real-ESRGAN animevideov3, local (real-esrgan) | 0 |

Cheap swap: ~11 s of compute per video-second. Pay for the Seedance final only on a proven winner. Registry: real-esrgan.

On this Mac: `python3 components/local-studio/local.py upscale clip.mp4 -o out.mp4 --esrgan-model realesr-animevideov3`

**Higgsfield, word for word**

```
## 8. FINAL VERSION (only when the clips were made as drafts, and only after the user approves the draft cut)

- Finalize every clip within 7 days of its draft: call `seedance_2_5` with `draft_job_id` = the clip's draft job id from jobs.json. A final made from a draft is always 1080p.
  - The final renders the draft's full length. Its duration parameter is ignored.
  - The final keeps the draft's motion and framing, so no prompts change.
  - Finalize the satin title-card clip too, when there is one.
- Quote the cost before sending and wait for the go-ahead: look the price up with `estimate_video_cost` on one finalize request per distinct clip length and add them up.
- Send in batches as large as the batch tool accepts, up to 12, with at most 16 jobs running at once. Save the final job ids in jobs.json next to the drafts.
- Check each final against its draft (same shots, same length, 1080×1920) before using it.
- Reassemble exactly as in step 6 with the same windows, overlays, captions and audio, from the final clips.
  - Name the files \*\_final_clean.mp4 and \*\_final_captioned.mp4.
- Run step 7 again on the final files and deliver them the same way.
```

Check: Same shots, same length, 1080x1920.

## Checks

- Price quoted and under the lane.json cap before the first paid call
- First clip checked alone before the batch
- Every sung line heard in order
- Contact sheet per clip: identity, beat, no stray text or brands
- Length = song length within 0.05 s
- No disclaimers, offer, price or call to action on screen

## Rules

- Song unchanged first frame to last
- Cast and story only from the words
- Clothed cast, no brands but ours, men never kiss or hug men
- No offer, price, disclaimer or call to action on screen
