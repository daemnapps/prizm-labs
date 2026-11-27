# Short Drama

What it makes: one short-drama episode (30 s to 3 min; 9:16, 16:9 or 1:1) with characters talking on screen, from a script or an idea, in one of 15 looks; optional edited cut and music score.
Sources: `commands/short-drama.md`, `short-drama/SKILL.md`, `commands/short-drama-references-{script,pictures,clips,styles,pacing,editing,edl,auto-edit,music,sound,qc}.md`, `short-drama/scripts/{check,assemble,edit_input,frames}.py.md`

## Inputs it needs
- A script (pasted, attached or a file path), OR an idea in a sentence or two, OR "show me story ideas".
- Quality: 480p draft (recommended) / 720p / 1080p. Mode: step by step (asks at plan, pictures, film) or full auto. Edit kinds: `montage`, `screen_text`, `subtitles`, `music`.
- Format (9:16 default, 16:9, 1:1) and the look (picked from a gallery after the script is read). Optional credit limit.
- Ages come only from the script or the user's own words, never from the model. Limits: at most 8 character pictures, 4 locations, 4 props, film at most 180 s, one clip per started 15 s.

## Steps in order
0. **Onboarding.** Welcome lines, then up to 4 questions (what they have, quality, mode, edit). Quotes before any spend.
1. **Plan (stop 1).** Load the script reference: read people, places, props, cut to one episode by screen time, stage every scene, write `plan.json` (characters with voice cards, locations, props, scenes). `check.py plan` refuses any line not in the user's script. Shows plan and total; yes pays for pictures.
2. **Pictures (stop 2).** Per character: face (`soul_2`), outfit flat-lay (`soul_2`), then a three-view sheet (`seedream_v5_pro`) made from both; per location an empty general view; per prop that matters one picture. Drawn looks make the sheet from text only. Every picture shown; safety look for protected people. Yes pays for draft clips.
3. **Clips.** Group scenes into clips, design shots, time speech, write each prompt in a fixed order, `check.py lines/clips` until OK; send non-extending clips in batches of 12; extensions only after the parent completes.
4. **The film.** `check.py stage … clips` downloads takes, `check.py film`, then `assemble.py` joins (scales to the first clip, 24 fps, levels sound, hard cuts, no music or titles).
5. **Changes and the final (stop 3).** User-asked remakes only; 1080p final = the exact draft request with `draft:false`, `draft_job_id`, `resolution:"1080p"`. `register_result` saves to history; `check.py close` prints what may be said.
6. **The edited film.** Montage, name cards, subtitles (free) and an optional instrumental score (credits), using an EDL, `edl_check.py`, render, `qc_check.py`.

## Prompt blocks, word for word

**1. Face prompt (fill only the bracketed slots)** — `commands/short-drama-references-pictures.md`
```text
front-view shot, face close up of a [ADJECTIVE] [AGE] [ORIGIN], with [FACE], [IDENTITY DETAILS, ]natural skin texture, and [HAIR]. [PRONOUN] [has/have] [LOOK], wearing a simple neckline outfit (a protected person: a plain crew-neck top, shoulders covered). Head-and-shoulders, whole head and hair visible, seamless bright white studio backdrop, soft even light on both sides of [POSSESSIVE] face, neutral colour, true-to-life realism, gaze locked on the lens.
```

**2. Outfit flat-lay prompt** — same file
```text
A top-down flat-lay photograph of one complete [men's / women's] outfit[ for a BUILD man / woman], laid out as a single dressed figure on a plain light stone-grey linen background, in a vertical 3:4 frame, like a wardrobe department continuity photograph. The outfit is [COUNT], each appearing once. The garments are laid flat and empty, layered into one standing silhouette in the centre of the frame from collar to footwear, the whole outfit inside the frame at full length with even empty space around it. [CHARACTER SENTENCE] [GARMENTS] [PALETTE]. Soft, even, neutral daylight from directly above, neutral white balance, gentle natural shadows under each item, true-to-life colour and texture: [TEXTURES], with plain inner collars, linings and insoles. Clean, crisp, high-resolution photograph.
```

**3. Character sheet prompt (references named only as "first/second attached reference image")** — same file
```text
the first attached reference image is the single source of truth for this [woman's / man's] face: the same facial structure, brows, eyes, nose, lips and skin tone, a full likeness match to the first attached reference image. the second attached reference image is the single source of truth for [her / his] clothes: the same garments, footwear and accessories as in the second attached reference image, with their cut, construction, materials and hardware, now worn on [her / his] body. With this exact [woman / man] in this exact outfit, create a horizontal three-panel photographic character appearance sheet on a plain neutral light-grey studio backdrop with thin white vertical separators, lit from the front by soft, even, diffused studio light, the same in all three panels and equal on both sides of the face and body: a wardrobe fitting of a real [actress / actor] in real clothes, cinematic live-action realism, natural skin texture with visible pores, subtle photographic grain. [Age and build.] [The hair sentence.] [She / He] wears [the outfit, garment by garment]. Every material reads as real [materials] with visible stitching and [its finish]. [The palette sentence.] [She / He] stands straight in a relaxed, neutral pose with natural adult proportions, the waist at the middle of the figure, arms loose at the sides; every hand is empty and relaxed. Left panel: the front of the outfit from the neck down to the footwear, natural proportions, the head above the crop, showing [the front: fit, closures, textures, wear]. Centre panel: a full-length rear view from head to footwear, showing [the back of the hair and of every garment]. Right panel: one large head-and-shoulders portrait with the whole head inside the frame and clear space above it, the same face as the first attached reference image, [the hair as styled], [what shows at the neck and shoulders], calm and neutral, eyes to the camera. Exactly one visible face across the sheet, in the right panel only. The garments, materials, colours, hardware and footwear stay identical across all three views.
```

**4. Location prompt: how it is written (Chinese prose, fixed opener and closer)** — same file, section 6
```text
Write the prompt as one paragraph of Chinese prose, 350 to 600 Chinese characters, never over 650:

1. Open with `电影剧照，`, then the genre's film, then the film look: how dark the frame is, how much lies in shadow, the key source and its colour.
2. The place: kind, era, size; every `map` item with its material, colour and position; every door; the open floor.
3. The camera: a wide establishing view at standing eye height, from where, looking which way.
4. The place's own lights that are on.
5. End word for word with `画面中没有任何人，没有人影。`
```

**5. Reverse-view edit** — same file
```text
- Reverse view: "Show this same place from its opposite side: the camera now stands at the far side of what this picture shows, at the same height, facing back toward where this camera stood." Save its job id in `reverse`. 
```

```text
- End word for word with: "Everything else stays exactly as in the attached reference image; no people anywhere, the place stands empty."
```

**6. Prop prompt opener and closer** — same file, section 7
```text
- One English paragraph of about 100 to 160 words. Open with "a cinematic live-action photograph".
```

```text
- End with: "no people, no other objects, no brand logos".
```

**7. Clip prompt: the twelve parts in order** — `commands/short-drama-references-clips.md` section 5
```text
Write it in English, spoken lines as the script has them, each part on its own line, in this order. Paste the fixed lines word for word from the example. Hard limit: 20,000 characters; aim for 13,300 or fewer. A shot line has at most 55 words, a reference line 35, the cast line with its geography 170. Never write `@tag`, `<<<`, `[[` or ids: point to a picture only as "image reference N", numbered in the order attached.

1. **Sound line**, fixed. With no line in the clip: `STRICT RULE: Absolutely no music, only diegetic sounds; no one speaks.` With narration it ends `…only diegetic sounds and the narrator's voice-over.`
2. **Style line**, fixed for live action up to the colon, then the scene's light in one sentence: the one key source the location picture shows, where it is, how it falls and what it leaves dark; the grade; the air. Copy that sentence word for word into every clip of the scene. A night scene names no colour. With a `style_id`, the whole line up to the colon is that look's style line from `/short-drama/references/styles`. For a drawn style in the user's own words, replace the words before "people and set" with the plan's style.
3. **Look line**, fixed, live action only.
4. **Reference lines**, one per attached picture, in order, and then the `Continuity:` line: paste what `check.py lines plan.json <n>` prints, word for word (section 6).
5. **Cast line** `In frame only: …`, then the geography by side and depth, ending `Eyelines never at the camera.`
6. **Opening state**: everyone present at the first frame, each stance in one word, and their distances.
7. **Speech budgets**, one sentence per speaker, then who never speaks: `Anna and the guards never speak in this clip.`
8. **Intention sentences**, one per acting character, at most 30 words: what they want and the one drive they act with once they decide, from excitement, perseverance, inspiration, willpower, grit, zeal, tenacity, persistence, resilience. No other emotion.
9. **Pace line**. Never ask for stillness, holds or pauses.
10. **Shot lines**: `S1 0.0-2.5s · size, camera, height, movement · action`, sound events timed.
11. **Audio**: the fixed language line with the script's own language in place of "English", then `S3 (2.1-4.0s) Boris to Anna, dry and clipped: "..."` per line, then `No speech in S1, S5.`
12. **Restrictions**, fixed, last. When the clip shows background people, add before its last line: `- Background people never copy the face or hair of any image reference; each referenced character appears once, as themselves.`
```

**8. A complete 13 s clip (all fixed lines word for word)** — same file
```text
STRICT RULE: Absolutely no music, only diegetic sounds.
Realism cinematic, real skin with pores and small marks, natural eyes, people and set lit only by this place's named sources: the tall window behind the sink, daylight falling across the counter onto the faces from one side, the hallway dark; soft contrast, muted warm palette; still, clear air.
Framed on the rule of thirds, with a light anamorphic lens character: softly oval out-of-focus highlights in the background, and a fine 35mm film grain.
Image reference 1 (location Kitchen): the Kitchen 100% as in the reference.
Image reference 2 (character Mira): Mira, face, hair, body and clothes 100% as in the reference.
Image reference 3 (character Daniel): Daniel, face, hair, body and clothes 100% as in the reference.
Image reference 4 (prop Letter): the Letter 100% as in the reference.
Continuity: Mira is clean and unchanged from the reference, with no stain, mark or damage; Daniel is clean and unchanged from the reference, with no stain, mark or damage.
In frame only: Mira and Daniel. The counter near, the window behind it. Mira at the counter's near side, screen left; Daniel at its far side, screen right, an arm's length across it. Eyelines never at the camera.
Opening: Mira mid-stride toward the counter, the letter in her hand; Daniel standing at the sink, three steps from her.
Mira speaks aloud 2 times between 1.6s and 10.3s and never again; silent before 1.6s and from 10.3s to the end.
Daniel speaks aloud 1 time between 3.7s and 6.0s and never again; silent before 3.7s and from 6.0s to the end.
Mira is out to make Daniel own the signature; once he admits it she presses for the whole truth, with grit.
Daniel is out to slow her down; once the letter lands he decides to face it, with resilience.
Pace: tight and pressing; every shot opens in motion, a beat only where a line lands.
S1 0.0-1.5s · medium_wide, from the near end of the counter looking along it, eye level, slow push-in · Mira, full length near left, strides to the counter, the letter in her hand; Daniel, middle right, turns from the sink to face her; the window behind him.
S2 1.5-3.6s · close, cut at the collarbones, three-quarter from across the counter, slightly low, handheld · Mira plants her free hand on the counter and lifts the letter into frame; her voice begins at 1.6s; her look passing right of the lens, level; only the dark hallway behind her.
S3 3.6-6.1s · close, cut at the collarbones, three-quarter from Mira's side, slightly high, handheld · Daniel steps in to the counter's far edge, both hands closing on it; his voice begins at 3.7s; his look passing left of the lens, level; only the window behind him.
S4 6.1-7.6s · insert, from above the counter, high, static · Mira's hand comes in from the left and drops the letter on the counter; it lands at 6.9s and slides a hand's width right; her fingers open and lift away.
S5 7.6-10.4s · extreme_close, brows to lips, profile from the window side, slightly low, slow push-in · Mira leans in over the counter; her voice begins at 7.7s and ends at 10.3s; her look going off the right edge, level; the dark hallway soft behind her.
S6 10.4-13.0s · close, cut at the collarbones, from the front, slightly high, slow push-in · Daniel's eyes go down to the letter on the counter and stay there, his jaw sets, his hands flatten either side of it; only the window behind him.
All speech is in English. Only the words inside double quotation marks are ever spoken aloud; every voice direction and every other word of this text stays silent.
S2 (1.6-3.5s) Mira to Daniel, a woman's voice of about 30, a low clear alto, tight and quiet: "You signed it. Without me."
S3 (3.7-6.0s) Daniel to Mira, a man's voice of about 35, a warm baritone, careful and low: "I was going to tell you tonight."
S5 (7.7-10.3s) Mira to Daniel, hard and close: "Then tell me. Who gets the house?"
No speech in S1, S4, S6.
Restrictions:
- No music of any kind: no score, no soundtrack, no background music, no melody, no drone, no pad, no sting, no swell.
- No added sound effects: no whoosh, no boom, no impact hit, no riser.
- Only diegetic sound: the characters' voices and the natural sounds of this place.
- No words but the quoted lines, each only inside its own Audio window; outside them no one on screen speaks, whispers or mouths a word.
```

**9. Look style line, `realism_cinematic` (the default look)** — `commands/short-drama-references-styles.md`
```text
### `realism_cinematic` Higgsfield Cinematic

- Picture words: Cinematic live action, natural skin and motivated lighting. Restrained warm practical lights and cool shadows.
- Style line: `Realism cinematic, real skin with pores and small marks, natural eyes, people and set lit only by this place's named sources:`
```

The other 14 looks, each with a Picture words line and a Style line, are in that same file: `kdrama` Coming of Age, `k_drama` K-Drama, `romcom` Romantic comedy, `nineties` 90's, `dark_academia` Dark Academia, `anime` Anime, `painted_25d` 2.5D, `classic_2d` Classic 2D, `painterly_2d` Painterly 2D, `furry` Furry, `classic_3d` Classic 3D, `painterly_3d` Painterly 3D, `cgi` CGI, `noir_3d` Noir 3D.

**10. Score cue prompt: its order** — `commands/short-drama-references-music.md`
```text
One prompt per cue: `elevenlabs_music_v2` through `generate_audio_batch` (read the model first, as auto-edit.md says),
`duration` the cue's span plus 2 seconds (rounded up; 3 to 300 seconds), `force_instrumental: true`. The prompt runs a few hundred to
a thousand characters, in this order:

1. "Instrumental film score cue, no lyrics.";
2. **the scene**: the event from the spotting, with its people, its place and what is done, as concretely as the script
   and frames give it;
3. **the key and the tempo**;
4. **the instruments** this cue takes from the palette, and the motif by its description;
5. **the moves in seconds of the cue**, from its hit points: what plays from when to when, "a full hit at about N
   seconds", "at N seconds everything stops";
6. **how it ends**: cut off dead, a hit ringing out, a held chord left unresolved, a fade to silence;
7. three to five words of mood.
```

**11. Score price quote request** — `commands/short-drama-references-auto-edit.md`
```text
`{"params": {"model": "elevenlabs_music_v2", "prompt": "Instrumental film score cue, no lyrics.", "duration": <the film's seconds, at most 300>, "force_instrumental": true}}`
```

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Character face, outfit flat-lay | `soul_2` | 3:4, 2k, no references |
| Character sheet, location, reverse view, prop | `seedream_v5_pro` | 16:9, 2k, `is_inpaint:false`, `remove_bg:false`; sheet takes face then outfit as `image_references` |
| Clips | `seedance_2_5` | `omni_reference`, `generate_audio:true`, `bitrate_mode:"high"`, plan aspect, 4-30 s; 480p `draft:true`, 720p `draft:false`, final 1080p from `draft_job_id` |
| Extension clip | `seedance_2_5` | `video_extension`, forward, parent job last media |
| Score (optional) | `elevenlabs_music_v2` | `force_instrumental:true`, duration = cue span + 2 s, via `generate_audio_batch` |
| Speech check, cuts, subtitles, QC | none | faster-whisper, ffmpeg, numpy/Pillow in sandbox |

## Checks and gates
- `check.py` must print OK at each stop: `script-save`, `plan` (every line from the script, voice cards, protected-person fields), `pictures` (prompt rules, refuses revealing words for protected people and gives a rewrite), `clips` / `finals` (a line quoted more often than played, delivery notes sharing a word with a line, windows too long), `film`, `edited`, `close`.
- Protected characters (no stated age, under 18, creature, kind left open): plain fully dressed, no romance; their face/outfit/sheet get the kids' safety look; a failed one is not used.
- Stops: plan (pays for pictures), pictures (pays for draft clips), film (1080p final and fixes). Full auto: no stops, final only when chosen quality is 1080p. A remake is paid and made only on the user's request. Never reword a refused prompt to slip the same content through.
- Refuses: Seedance without `omni_reference` (film cannot be made); no draft support makes clips 720p with a note.
- Says only what was checked: length and shape measured, frames seen; never claims it heard the audio.

## Price pattern
Quotes every paid step with `estimate_image_cost`, `estimate_video_cost`, `estimate_audio_cost` before spending; the yes to each stop pays only for that stage. Its own welcome lines say about 400 credits for 2 min at 480p, 900 at 720p, 2,300 at 1080p; the score about 8 credits for 2 min. Check against `_prices.md`: 2 min of draft clips = 12 × 30 = 360 credits, plus a 1080p final 12 × 160 = 1,920 on top of the draft.

## Cheap swap
- Clips: `wan3_0` 480p at 7.5/10 s instead of `seedance_2_5` at 30 (draft) / 160 (1080p): 2 min goes from about 360 to about 90 credits (saves ~270), and from ~2,280 to ~90 with a free local upscale. Wan has no `draft_job_id` finalise path or `video_extension` mode; extensions become fresh clips. `gemini_omni_flash_1_2` 360p at 7.5/10 s is the other cheap route (max 7 image refs, 3-10 s with refs).
- Sheets, locations, props: `seedream_v5_pro` (2.5 per picture on `_prices.md`) to `seedream_5_0_flash` 2k at 0.5 or `gpt_image_2_6_flare` 1k low at 0.75 (saves 1.75-2 each; about 10-15 for a cast of 6, 3 places, 2 props).
- Face and outfit on `soul_2` (not quoted): same cheap picture models if the likeness holds.
- Score: `elevenlabs_music_v2` is already about 8 credits per 2 min; skip or keep.
- Local free: Whisper for the speech checks (already in sandbox), ffmpeg join/cuts/subtitles, Real-ESRGAN upscale, Demucs stems if a take needs cleaning, RIFE interpolation.
- Writing (script reading, staging, plan, clip prompts, EDL decisions): Claude on the plan, free.
