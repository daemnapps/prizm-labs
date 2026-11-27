# Faceless Video

What it makes: one finished narrator-led channel video (no on-camera person), motion clips or narrated stills, in a locked non-photoreal look with one voice and optional burned subtitles. Five types: Explainer, History, Kids, Picture Story, Fairy Tale & Myth.
Sources: `faceless-video/SKILL.md`, `commands/faceless-video.md` (the slash command only says "unknown token, use ordinary generation"; the real instructions are the workflow), `faceless-video/references/*.md`, `faceless-video/scripts/*`

## Inputs it needs
- An explicit faceless-channel request (a topic alone is never enough). Channel type; motion mode (animated clips or still pictures); for Kids: who carries the sound (narrator / talking characters / sung music video).
- Style from a preset-card gallery (cards resolved with `resolve_explainer_preset`; style image is the look anchor), or user uploads (up to 3, authoritative).
- One combined screen: duration, aspect (16:9 or 9:16), subtitles yes/no, thumbnail yes/no; the topic (their idea, their script, or five researched topics); the narrator voice (picker; default pinned preset if none picked). Anything the user already said is locked and not asked again.

## Steps in order
0. **Intake**, fixed order, one take: type, motion mode, (Kids sound), style, duration/aspect/subtitles/thumbnail, topic, voice. After the last answer production runs straight to delivery; gates post and proceed.
1. **Style anchor.** One `seedream_5_5` 1k style key built on donor images (card style image + style file's canonical refs + uploads), never prose alone.
2. **Asset roster.** Characters (2:3), several locations plus coverage angles (chosen aspect), props (1:1), the through-line prop, optional variety inserts; all 1k, the style formula byte-identical in every prompt; ASSET LOCK posted.
3. **Script and block plan.** Through-line, arc (hook, build, turn, payoff), N blocks of 10 s each = five hard-cut shots; `script_manifest.json`; SCRIPT LOCK posted; `validate_motion_script.py` must print `valid:true` (stills: `validate_picture_story.py`).
4. **Generate blocks.** One `minimax_h3` clip per block, 10 s, 2K, at most 7 image refs; cut count measured with ffprobe; block 1 compared to the asset sheets.
5. **Voiceover** (`narration` workflow): `text2speech_v2` / `elevenlabs` per block line, locked voice pair, measured with `measure_narration_takes.py`.
6. **Assemble** the immutable clean master (`finish_video.sh` / `assemble_slides.sh`); 7. **Caption** it (`video-montage` scripts) when subtitles are on; 8. no automatic upscale; 8b. thumbnail when asked; 9. deliver one `final.mp4`.

## Prompt blocks, word for word

**1. Block prompt, the core template (one 10 s, five-shot `minimax_h3` request)** — `faceless-video/references/prompts.md` section 3
```text
Style: {STYLE}; {MOTION} — the visual style is EXACTLY as in the reference images, same rendering, same surface treatment.
PALETTE LOCK: use ONLY the colors and the background treatment of the reference images ({e.g. flat off-white/clean webcomic background}). Do NOT introduce any new or foreign colors, no colored/gradient/painted backgrounds that aren't in the references, no recoloring of characters or objects.
A single 10-second scene of FIVE hard-cut shots. Do NOT open the video on any reference image or show a sheet/swatch — stage everything fresh, matching characters, room, colors and background to their references. Characters only emote and gesture, they do NOT talk. Motion starts on frame 1 (no opening freeze).
REFERENCES (look, identity, palette): @Image1 = LOCATION ({desc}). @Image2 = {CHARACTER A} ({desc}). @Image3 = {CHARACTER B}. @Image4 = {PROP}.
SHOT 1 — 0.0s to 2.0s — {SIZE+ANGLE}: {beat}.
HARD CUT.
SHOT 2 — 2.0s to 4.0s — {DIFFERENT SIZE+ANGLE}: {beat}.
HARD CUT.
SHOT 3 — 4.0s to 6.0s — {DIFFERENT SIZE+ANGLE}: {beat}.
HARD CUT.
SHOT 4 — 6.0s to 8.0s — {DIFFERENT SIZE+ANGLE}: {beat}.
HARD CUT.
SHOT 5 — 8.0s to 10.0s — {DIFFERENT SIZE+ANGLE}: {payoff}.
Five hard-cut shots at 2.0s, 4.0s, 6.0s and 8.0s, no dissolves, no fades. {MOTION}, continuous motion within each shot, never freezes.
```

**2. Audio and negative lines of every block** — same file
```text
AUDIO: {diegetic SFX only} — no voice, no narration, no music.
NEGATIVE: opening on a reference image, a sheet/swatch or a static first frame, leading freeze, dissolves or fades, NEW or foreign colors, colored/gradient/painted background not in the references, recolored characters, style drift, extra people, cloned characters, characters talking, lip-sync, on-screen text, captions, photorealism{2D-ONLY: , 3D render}, watermark.
```

**3. Action grammar** (what shot beats must be) — same file
```text
**Action grammar (all styles):** write SHOT beats as pure CHOREOGRAPHY — the {STYLE}
formula owns the look, so no style/color/material words inside beats; elements enter
STAGGERED ("A, then B, then C" — never simultaneously) with landing verbs (snaps into
place, stamps down, drops with a bounce, settles); exactly ONE camera behavior per
shot, stated once (slow push-in / static / gentle drift / whip) — two moves in one cut
reads as AI soup; the FINAL shot eases into a stable, still micro-moving final frame
(settled ≠ frozen — rule 21 holds).
```

**4. Style key prompt (one `seedream_5_5` 1k call)** — same file, section 1
```text
"A clean {STYLE} STYLE SAMPLE: one simple recognizable subject
(a small friendly object or mini-scene) rendered in the style so its line weight,
shading and colours read at a glance. Balanced, attractive, easy to read. No palette
strip, no colour chips, no swatch bar, no colour squares, no labels, no text, no
watermark, no reference-sheet layout."
```

```text
From uploads (style only), verbatim prefix: "Take only the visual render style and
color grading of the input image(s)… never use the characters, inscriptions, etc."
```

**5. Asset prompts (characters 2:3, locations in the chosen aspect, props 1:1; all 1k)** — same file, section 2
```text
- **Character (2:3, 1k):** "Full-body character centered on a plain flat solid-color
  background, in THIS EXACT style: {STYLE}. Character: {desc — distinctive, readable
  silhouette}. No text, no watermark."
- **Location (CHOSEN aspect, 1k):** "{interior/exterior} … in THIS EXACT style: {STYLE}.
  {key furnishings + ONE named anchor object with a position}. Empty room — no people, no
  characters, no figures. Wide establishing. No text, no watermark."
- **Prop (1:1, 1k):** "A single isolated prop centered on a plain flat solid-color
  background, in THIS EXACT style: {STYLE}. Object: {desc}. No hands, no scene, no
  other objects. No watermark."
```

**6. Style formula, Stickman Cartoon (the generic one)** — same file, section 0
```text
flat 2D webcomic cartoon, extremely minimal — uniform thin even-weight black
outlines, egg-shaped heads with tiny dot eyes and a single line mouth, plain
noodle limbs, solid flat color fills with NO shading, NO gradients, NO texture,
deadpan minimalist design, plain flat solid-color backgrounds.
```

**7. Style formula, Editorial Motion Graphics ({ACCENT} locked once per video)** — `faceless-video/references/style-editorial-collage.md`
```text
flat editorial documentary collage on a warm cream paper stage with subtle
fiber grain: monochrome halftone archival photo cutouts with rough white
keylines and a slightly offset {ACCENT} stroke behind each cutout, one
single {ACCENT} accent color per video — a large flat {ACCENT} disc behind
the main subject and exactly one color-popped hero element among the
monochrome — torn paper edges and tape strips, soft paper drop shadows,
hand-drawn {ACCENT} marker circles, arrows and underline strokes (abstract
strokes only, never letters), abstract unlabeled data shapes and flat
stylized maps, subtle print misregistration on inked elements, snappy
staggered spring motion with slight overshoot, non-photorealistic
illustrated collage, never live-action.
```

**8. Editorial block audio line** — same file
```text
Every motion verb gets at most ONE sound cue; nothing sounds that didn't
move. 2–4 cues per block + one bed: paper pops and thwips on entrances, a
stamp hit on the impact beat, soft tick-tick on data steps, low newsroom-air
bed underneath. Percussive, never musical; still "no voice, no narration, no
music" (the bed is room tone, not a track).
```

**9. Voiceover line format** — `faceless-video/references/vo_and_captions.md`
```text
- **Line prompt format — delivery direction, not pacing:** send every line as
  `[ {DELIVERY}, {optional block mood}, starts speaking immediately] [00:00-00:09] {text}`.
  {DELIVERY} is ONE direction phrase composed once for the whole video to fit the channel
  type + topic (e.g. `wry conversational explainer, neutral accent, bright dry timbre,
  lively pace`) and repeated VERBATIM on every line — that keeps the timbre consistent
  across blocks. {optional block mood} is 2–4 words for this block's beat (`a bright
  knowing reveal`, `hushed conspiratorial`). `starts speaking immediately` kills the
  leading pause. ElevenLabs ignores the `[00:00-00:09]` window for pacing.
```

**10. Kids song mode: the song prompt skeleton (at most 2048 characters)** — `faceless-video/references/kids-song.md`
```text
A full {1|2}-minute children's {song|dance-along song}, SUNG by a warm
bright {gentle|cheerful, energetic} female singer with a smile in her voice
- a real melodic song with verses and a repeating chorus on a clear singable
tune, not narration. THE BEAT IS STEADY AND CONSTANT from the first second
to the last: {100|112} BPM, simple 4/4, NO tempo changes, NO slowdowns, NO
pauses between sections. Every lyric line has 8 syllables in steady trochaic
meter (stress on 1,3,5,7), sung one syllable per beat, and EVERY line starts
exactly on beat one of its bar; each line is one 4-bar phrase. Melody:
simple {sweet|bouncy} nursery tune in {C|G} major, small steps within one
octave, verse lower and playful, chorus a little higher and brighter.
Instruments: {mood set from above}; clean warm mix, voice clearly in front,
everything locked to the same steady beat. Structure with NO gaps: 4s
instrumental intro, Verse 1, Chorus, Verse 2, Chorus, Verse 3, Chorus
(final, fuller, extra claps and bells), 4s outro on {bells + a happy
character sound}.
Verse 1: "{4 lines, 8 syllables each}" · Chorus: "{4 lines, catchy, action
words, repeats verbatim}" · Verse 2 · Chorus: (repeat) · Verse 3 · Chorus:
(repeat, final, fuller)
Delivery: {soft and melodic | energetic but sweet}, perfectly in tune, every
syllable landing right on the steady beat; innocent and age-appropriate for
toddlers. Total length approximately {1|2} minutes.
```

**11. Gates, commands run word for word** — `faceless-video/SKILL.md`
```text
python3 ${HF_WORKFLOWS}/faceless-video/scripts/validate_motion_script.py \
  --script script_manifest.json --duration-seconds {requested_seconds}
```

```text
python3 ${HF_WORKFLOWS}/faceless-video/scripts/validate_picture_story.py \
  --script script_manifest.json --duration-seconds {requested_seconds}
```

**12. The shot rule (rule 2)** — same file
```text
2. **Every clip is ONE 10s shot-group of FIVE hard-cut shots (~2s each)** written into a
   single prompt (Phase 4) — **no shot longer than 2.5s**: a frame that hangs 3–5s reads as
   a slideshow. **Kids blocks use the FOUR-cut interplay pattern** (2.5s,
   `references/kids-styles.md`). One `minimax_h3` call = one 10s block; never separate
   clips per cut.
   **COUNT THE CUTS THAT CAME BACK — the model under-delivers.** Dev 2026-07-29: 8 blocks
   × 5 cuts came back with 29 visible cuts, i.e. ~4s per frame.
   ```
   ffprobe -v error -select_streams v:0 -show_entries frame=pkt_pts_time \
     -of csv=p=0 -f lavfi "movie=blockNN.mp4,select=gt(scene\,0.3)" | wc -l
   ```
   A block with fewer cuts than asked, or any shot ≥3s, is regenerated ONCE with the cuts
   spelled out shot by shot ("SHOT 1 (0.0–2.0s): …" … "SHOT 5 (8.0–10.0s): …"). If the
   second attempt still under-delivers, keep it and say which blocks are slow.
   **The count under-reports on FLAT looks** (Editorial, Paper Diorama, Pastel Flat 2D,
   Poster Vector, Stickman): pixel change between similar compositions never crosses the
   threshold — dev read 3/1/3 on blocks that visually had more. There: re-measure with
   `scene,0.15` and treat a low count as a SUSPICION, not a verdict — look at the block
   before spending a regeneration, and never wait on a regeneration that hangs when a
   `completed` version already exists.
   **DEGRADATION IS AUTOMATIC, AND NEVER ASKED.** A block that failed twice at its cut
   count drops one cut on the next attempt (5→4, Kids 4→3), silently. "Shall I simplify the
   choreography?" is a stop this flow does not have.
```

Style files with their own formula, palette lock and motion token: `style-editorial-collage.md`, `style-paper-diorama.md`, `style-mannequin.md`, `style-cinematic-storybook.md`, `kids-styles.md` (Studio 3D and others), `history-longform.md`; picture mode `picture-flow.md`; Kids talking characters `kids-talking-characters.md`; preset ids `preset-catalog.md`. The script writer rules are in `scriptwriter.md`.

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Style key, every asset, stills frames | `seedream_5_5` | always `resolution:"1k"`; style key 16:9; character 2:3, location chosen aspect, prop 1:1; a still variation is an edit with only the previous frame as reference |
| Clips (motion mode) | `minimax_h3` | 10 s, `2K`, 16:9 or 9:16, `image_references` location → characters → props, at most 7 per call, native audio, one block per call |
| Narration | `text2speech_v2` | `variant:"elevenlabs"`, locked voice pair, 20-23 words (Kids 17-21) per 10 s block |
| Kids song / stills continuous read | `seed_audio` | song prompt only (kids song); stills: one continuous read |
| Music bed (Kids, Fairy Tale default or asked) | `sonilo_music` | instrumental only, under the narration |
| Thumbnail | via `thumbnail-generation` | only when the cover answer was yes |
| Upscale | `upscale_video` | only after delivery, on the user's request |
| Transcription, captions, assembly | none | Whisper, ffmpeg via the bundled scripts |
Models are locked: no substitutions.

## Checks and gates
- GATE 0 intake locked; GATE 1a the style key names the card title and donor media ids (zero donors on a style with a card = a bug); GATE 2 every asset exists; GATE 3 `valid:true` pasted verbatim; GATE 4 all N blocks completed, shown, block 1 compared with the sheets.
- The validator enforces block count, 20-23 words per 10 s line (Kids 17-21), no filler words, no five-word phrase shared by two blocks, adjacent shots differing in size, at most 2 consecutive blocks per location, cold open at most 8 words.
- Cut count: five visible cuts per block via ffprobe scene detection; a block with fewer is regenerated once with the cuts spelled out, then one cut is dropped silently; flat styles re-measured at 0.15 before spending.
- Retry ladder for `nsfw` / `failed`: reword (drop child/kid words, calm the pose), never drop a block. A `completed` block is final unless a named gate fails.
- Final QC: exactly one `final.mp4` from `final_clean.mp4`; style consistent; no talking or lip-sync (except declared Kids dialogue blocks); VO at -16 LUFS; subtitles burned by the montage scripts; no brand/IP/studio names.
- Not for: ideas only, single clips, silent animation, image-to-video, footage edits, ads, product demos, any on-camera presenter, UGC, thumbnails alone.

## Price pattern
Never written: it posts the roster and blocks but quotes through the generation tools' own estimates; there is no stop for money. `_prices.md` has no quote for `seedream_5_5` (1k), `minimax_h3` (sells only 2K), `text2speech_v2`, `seed_audio` or `sonilo_music`: not quoted. Count: a 2 min motion video is 12 blocks = 12 `minimax_h3` calls plus about 12-20 asset images and 12 voice takes.

## Cheap swap
- Clips: `wan3_0` 480p at 7.5 credits/10 s (up to 10 image refs, so the 7-ref packing still fits) instead of `minimax_h3` 2K (not quoted): 12 blocks cost about 90 credits. The five-shot hard-cut prompt must be re-tested on Wan; the cut-count gate stays. `gemini_omni_flash_1_2` 360p 7.5/10 s (max 7 image refs, 3-10 s with refs) is the other option.
- Cheapest of all: Still pictures mode (no clips at all): one `seedream_5_0_flash` 2k at 0.5 per beat, about 0.5 × 60 frames = 30 credits for a 5 min story plus voice.
- Pictures: `seedream_5_0_flash` 2k at 0.5 or `gpt_image_2_6_flare` 1k low at 0.75 instead of `seedream_5_5` (not quoted).
- Narration: Kokoro tts, local and free (components/local-studio/README.md), instead of `text2speech_v2` (not quoted); the workflow locks ElevenLabs for its word-band validator, so expect a re-measure.
- Music bed: skip (the workflow ships without one if the model is refused) or a local track; `sonilo_music` not quoted.
- Local free: Whisper (captions timing), Demucs, Real-ESRGAN (instead of `upscale_video`), RIFE, ffmpeg assembly.
- Script, through-line, shot plan, validation fixes: Claude on the plan, free to us.
