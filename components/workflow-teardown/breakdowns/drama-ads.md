# Drama Ads

What it makes: a finished short story ad film (default 9:16, length the story needs, e.g. ~55 s) whose characters act and talk on screen, from a catalog card or the user's own idea, directed and joined entirely in the sandbox.
Sources: `drama-ads/SKILL.md`, `commands/drama-ads.md`, `drama-ads/references/{models,styles,style-master,sheet-stylized,location,clips,formats,story-rules,script-format,characters}.md`, `drama-ads/scripts/styles/*.md`, `drama-ads/catalog/_cards.md` + `catalog/<card>.md`

## Inputs it needs
- The user's words, OR a catalog card (id or title; the card's "Recreate Ad" button sends one line: `card <id> «title» (style); mode: ask|hands-off; product <id>; characters avatar:<id>,…; idea: <words>`). Bare `/drama-ads` only lists cards and waits.
- Optional: product (Ads Studio product id, its photo is imported), characters (Marketing Studio avatar ids, used as face photos), the user's own script / photos / reference video / audio.
- One intake question only: resolution (480p / 720p / 1080p, each with the whole-film total) and mode (stop after each stage, or hands-off). A card line that already says both asks nothing.
- Sandbox (`ffmpeg ffprobe python3 curl jq faster_whisper`), `get_drama_ads_config` for every price. `drama_ads_id` rides on every generation.

## Steps in order
1. **Intake (step 0).** `ads_studio_story_recipe` reads the card (its `prompt` is the film brief, `script.text` an optional screenplay, `settings` length/shape). Ask resolution + mode. `balance` once. State the plan and total; ask-mode ends the turn on "Approve references".
2. **Availability.** `models_explore` on `seedance_2_5`: needs `omni_reference` and `video_extension` and the film's resolution, else stop.
3. **Script (step 1).** Write `script.json` by `story-rules.md` + `script-format.md`; pick a style (11 in `styles.md`), read only its style file; `checks.py script` until PASS.
4. **Viewer plan and effects (step 2).** `plan.json` (the film as a chain of ~15 s clips) and `effects.json`.
5. **Reference images (step 3), live action: no master; 3D/2D: the style master first, alone, then everything else with the master attached.** Character sheets (nine views in 2D), prop sheets, two-panel location sheets (3D) or background plates (2D). Looked at one by one; failed ones remade.
6. **Clips (step 4).** Round 1 = clips needing nothing from each other; round 2 = clips built on round 1 (extensions, frame plates); voice samples bound to characters. First clip of each model/mode goes alone and is checked (shape, size, length) before the rest.
7. **Assembly (step 5)** in the sandbox: join, mix score/narration (`assemble.py`, `song_times.py`, `stems.py`).
8. **Look before hand-over (step 6)**: contact sheets, every line heard, broken clips found (a paid remake is its own approval).
9. **Captions (step 7)** when asked; **deliver (step 8)**: one gallery (`show_generation_by_ids` / `show_result`) and "spent X of ≈ Y credits".

## Prompt blocks, word for word

Catalog has 47 cards in 9 styles (see below). Style files exist for 11 templates; the text below is one example (`feature-3d`) plus the fixed templates every style uses.

**1. A card's film prompt (the "recipe prompt"; example card "Bear proof", Cartoon story style)** — `drama-ads/catalog/bear-proof.md`, field `prompt`
```text
/drama-ads
Make a roughly 55-second deadpan storytime ad in `feature-3d`: an absurd problem the narrator quietly ends with the user's
product.

## The user's inputs
The user's message (their own text outside this prompt, and what they attach) may change any part of this film: the story, cast,
structure, look, sound, length or anything else. What it changes follows the user; every part it leaves alone follows this prompt.
Use all they give as "The user's own material" says, over this prompt, language and length included: photos keep its label exact,
their claims only, their idea or script fitted. Invent a missing product or name (never a real brand) and report it. Their
tagline, offer or call to action follows the punchline as one line over the product; a logo stays on it.

## Settings
This prompt is the brief for the film, not a reference video (none comes with it): make the film it describes. Its settings,
structure, pacing and sound replace the skill's defaults and base numbers, never its rules or checks. `feature-3d`, `storytime`,
9:16, 50-60 seconds, narration at 160-175 words a minute; nobody speaks on screen. Captions: the style's own line.

## The product in the film
It enters at 50% as the narrator's secret switch, named once in that line; the next says what it does. A morning-lit hero close-up
shows its label; it stays in the payoff. A physical product replaces the old thing, a used-up one joins a routine, an app or
service is set up quietly or sends its person or result. No end card, tagline or hard sell follows.

## Structure
0-7%: Before the hero appears, one wide shows the problem's most absurd consequence, as line one flatly states: someone near its
source in outsized gear against it. 7-22%: The hero appears beside the cause; the exaggeration plays out, then becomes the hero's
problem. 22-50%: Two or three everyday fixes fail, each a sight gag with a count, until the hero breaks at an exact hour. 50-65%:
The switch. 65-74%: It works so well it raises a new comic worry. 74-94%: A chimed time phrase jumps months on to the hook's
place; that gear, now idle or repurposed, flips the opening exaggeration. The last line, the callback punchline, claims only the
user's words. 94-100%: The hero's satisfied face.

## Cast
The hero: of the buyers' age and sex, exhausted then smug, acting with the face. The cause: someone close, oblivious, one habit
feeding the exaggeration.

## Tone, sound and look
Dry lines of three to ten words, some fragments. A soft score runs throughout; the problem's sound, the chime and a payoff thud
are the clips' own. Navy nights with warm amber pools of light, one honey-lit morning with floating dust.

## Details you invent
Where the user's message gives none, invent the details that fill the parts above: names, places, props, looks, lines and jokes.
Make each from the product, its buyers, where it is used and what goes wrong without it, not the first stock choice that comes to
mind. The parts themselves stay as this prompt writes them unless the user's message changes them.

```

**2. Style line, `feature-3d`** — `drama-ads/scripts/styles/feature-3d.md` (script.json `style`, first words of every clip prompt)
```text
3D animated feature-film look: smooth, rounded stylised characters with large expressive eyes, warm golden light, rich warm
colours with one or two strong accents, richly dressed real-scale sets with gently rounded forms.
```

**3. Style block, `feature-3d`** — same file (pasted word for word into the master and every image made from it)
```text
3D animated feature-film look: smooth, rounded, stylised 3D characters with slightly oversized heads, large expressive eyes with
big irises and bright catchlights, full expressive brows, small soft noses, soft rounded jaws, smooth skin with a gentle warm glow
and rosy cheeks, hair sculpted in soft flowing clumps with fine strands, rounded hands with five fingers; age shows in soft
sculpted wrinkles and grey hair. Clothes in real fabrics with soft folds: fine knit, cotton, corduroy, wool. Sets at real scale
with slightly simplified, rounded forms and clean, finished surfaces: painted plaster, wood, tile, enamel, fabric. Rich, warm
colour: one or two strong, saturated colours from the film's facts in the clothes and the set, against warm neutrals.
```

**4. Light words, `feature-3d`** — same file
```text
Warm golden sunlight from one side with soft shadows, a gentle warm rim on hair and shoulders, soft bounce light filling the
shadows; a soft glow around bright windows and highlights; a shallow depth of field, the background blurred into warm round
highlights.
```

**5. Video words, `feature-3d`** — same file (every clip prompt, after the style line)
```text
Smooth, fluid feature-animation motion with clear, readable poses; broad, expressive facial acting: eyes and brows move a lot,
natural blinks, clear mouth shapes synced to every word; hair and cloth follow through softly; soft warm light with a gentle rim
and a soft glow around bright windows, shallow depth of field with warm round highlights in the blur; a smooth, motivated camera.
Clear, close character voices over quiet room tone, no music.
```

**6. Style master prompt, first paragraph** — `drama-ads/references/style-master.md` (The master)
```text
1. "A single wide film still from a <the style's medium>." Then the style block, word for word. It holds no light and no place:
   the film's own place and light follow.
```

**7. Character sheet (character the master shows)** — `drama-ads/references/sheet-stylized.md`
```text
"A character reference sheet of the <character as the master shows it> from the attached reference image. <He | She | It> looks
exactly as <he | she | it> does in the attached reference image: <the character's facts, as the master drew them>. Copy the style
of the attached reference image completely, <the style's copy words>, and draw <him | her | it> in it: <the style block>."
```

**8. Prop sheet** — `drama-ads/references/style-master.md` (Prop sheets)
```text
"A prop reference sheet of the <prop> from the attached reference image, as a prop of a <the style's medium>. It looks exactly
like the <prop> in the attached reference image: <the prop from its facts, every visible part named>. Copy the style of the attached
reference image completely, <the style's copy words>, and draw it in it: <the style block>. The finish of the film rather than a
product photograph. Two views side by side on a plain light-grey background: a front view at eye level and a three-quarter view from
above. Soft, even studio light from the front, the same in both views. One object only: take only this <prop> from the attached
reference image, nothing of its room, its light or anything else in it. No text, labels, logos or watermarks."
```

**9. Two-panel location sheet opening, 3D styles** — `drama-ads/references/location.md` (OTHER STYLES)
```text
- The opening sentence names the place as built in the look when it is a miniature, in the words of its style file's Image words: "A two-panel location reference sheet of one and the same <place>, built as a <the style's miniature words> miniature set: <where, time, weather>."
```

**10. Clip prompt: order, then the fixed language and no-music sentences** — `drama-ads/references/clips.md` (The clip's prompt)
```text
- **The order:**
  1. the film's `style` line;
  2. its style file's video words (`scripts/styles/<template>.md`);
  3. the clip's action beat by beat, in literal camera terms, each beat its own paragraph opening with its seconds
     ("<from>-<to> s: <framing> …"): `checks.py clip` reads only those, and a prompt without them is refused;
  4. its dialogue (speaker, words, delivery);
  5. its effects (`effects.json`, `plan-and-effects.md`), each named only on its owner.

  In a clip where nobody speaks on screen, leave out the video words' sentences about mouths and voices.
```

```text
- The language, word for word, in every clip with speech: "Every spoken line is in American English, exactly the words in quotes;
  nobody speaks any other language." Without it a whole clip came back spoken in Mandarin.
- No music, word for word, in every clip's prompt: "No music and no score." The video model sometimes adds a score of its own,
  and music belongs over the joined film (Assembly). A clip that lip-syncs its part of the song has its own sound sentence instead
  (`formats.md`).
```

Other 10 style files, same sections (Style line, Style block, Light words, Image words, Video words, Acting, Motion and physics, Light and camera, Captions, Pitfalls): `drama-ads/scripts/styles/{live-action,phone,hyperreal-3d,doll-3d,crochet,claymation,paper-diorama,pixel-art,paper-collage,ink-cartoon}.md`.

## The catalog: 47 cards, 9 styles
`drama-ads/catalog/_cards.md` is a JSON of `styles` (9, each with a cover and subtitle), `cards` (47: id, style_id, title, preview video/poster, product, presenter, location) and `director`. Each card's full recipe sits in `drama-ads/catalog/<card-title>.md`.

| Style | Cards |
|---|---|
| Micro drama (live action) | 18 |
| Cartoon story (3D, told by its hero) | 7 |
| Claymation story | 4 |
| Singing ads (`/singing-ads`, no recipe) | 3 |
| Cinematic story | 3 |
| Talking object | 3 |
| Inside the body | 3 |
| Doll story | 3 |
| Crochet story | 3 |

A card recipe holds: `id`, `title`, `style {id,title}`, `prompt` (the film brief, quoted in full above: opens with `/drama-ads`, length/format/tone line, then fixed sections "The user's inputs", "Settings" (style id, 9:16, seconds, words per minute, captions), "The product in the film" (when it enters, how), "Structure" (percent-of-runtime beats, e.g. 0-7%, 7-22% ...), "Cast", "Tone, sound and look", "Details you invent"), `script` (a ready screenplay on some cards, else null), `settings {duration_seconds, aspect_ratio}`, `product`, `presenter`, `location` (a card's own slots, may be null), `preview.poster_url`, `drama_ads_id`, `instructions` (pass the id everywhere).

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Style master (3D/2D) | `gpt_image_2_6_flare` | 2k, high, 16:9, nothing attached |
| Sheets, prop sheets, location sheets, plates (3D/2D) | `gpt_image_2_6_flare` | 2k, medium, sheets 16:9, plates the film's ratio, master attached |
| All stills, live action | `seedream_5_5` or `seedream_v5_pro` (film quote says which) | 16:9, 2k, face photo attached |
| Clips | `seedance_2_5` | `omni_reference`, `generate_audio:true`, film resolution + aspect, duration 4-30 whole seconds, refs order images → videos → audio |
| Extension clip | `seedance_2_5` | `video_extension`, forward/backward, source first |
| Narration / a-cappella song | `seed_audio` | via `generate_audio_batch` |
| Score | (score role in the quote; model chosen by the tool) | length = film + 5 s |
| Voice pick | `list_voices` | narrated film only |
| Speech check, joins | none (faster-whisper small, ffmpeg in sandbox) | |

## Checks and gates
- `checks.py` is the last mechanical gate of each step (script, master, sheet, prop, plate, clip, film): run until it prints PASS. It refuses an image prompt whose style block differs from the style file and known IP names in image prompts.
- Ask mode: stops at the plan, references (3D/2D: master, then the rest), clips round 1; round 2 and assembly run on with no question. Hands-off: no stops.
- Every paid result is downloaded and `ffprobe`d against what was asked, then looked at or listened to; a result off its settings is not used.
- Refuses / stops: clip model unavailable; price unavailable (never a remembered rate); sensitive content; the children rule (`characters.md`); IP names; a failed preflight (never another pipeline). Retry ladder for `nsfw` / `ip_detected` / `failed`.
- Never calls `ads_studio_generate`; reads Ads Studio only through `ads_studio_story_recipe` and `ads_studio_list_avatars`.

## Price pattern
Quotes before every paid stage with `get_drama_ads_config` (purpose `film` at intake, `stage` at each approval, `remake` for fixes); never writes a number from memory. Rough figure from `_prices.md`, scaled from the 10 s quote, for a ~55 s film (about 4 clips of ~14 s, 8 pictures): clips at Seedance 480p ≈ 165 credits, at 1080p ≈ 880; pictures ≈ 2.25 + 7 × 1.75 ≈ 15. So about 180 credits at 480p, about 900 at 1080p. The film's own quote is not recorded here.

## Cheap swap
- Clips: `wan3_0` 480p at 7.5 credits/10 s (takes up to 10 image refs + video + audio refs) instead of `seedance_2_5` at 30/10 s draft or 160/10 s 1080p: a 55 s film drops to about 41 credits (saves ~125 vs draft, ~840 vs 1080p). Caveat: no extension mode on Wan; the workflow's round 2 extensions would be fresh clips. `gemini_omni_flash_1_2` 360p at 7.5/10 s has `extend` but max 7 image refs and 3-10 s with refs.
- Pictures: `seedream_5_0_flash` 2k at 0.5 or `gpt_image_2_6_flare` 1k low at 0.75 instead of 1.75-2.25 per picture; about 11 credits saved on a film.
- Local free: Whisper (sandbox already uses it), ffmpeg join and captions, Real-ESRGAN upscale of a 480p film instead of a 1080p render (≈ 840 saved); BiRefNet/SAM2 for plates if needed.
- Writing (script, plan, prompts, checks reading): done by Claude on the plan, free to us.
