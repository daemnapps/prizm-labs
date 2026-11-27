# Shorts Studio (/shorts)

Makes one finished reel (vertical 9:16 by default, up to about two minutes) carried by one consistent AI presenter: script, cast, presenter takes, captions, motion design, sound and music, composed in HTML and rendered by a bundled engine.

Source files: `commands/shorts.md`, `shorts-studio/SKILL.md`, `shorts-studio/scripts/reels.py.md`, `shorts-studio/scripts/engine/render.py.md`, `commands/shorts-references-takes.md`, `commands/shorts-references-avatar.md`, `commands/shorts-references-media.md`, `commands/shorts-references-script.md`, `commands/shorts-references-motion.md`, `commands/shorts-references-composition.md`, `commands/shorts-references-reference.md`, `commands/shorts-references-art-direction.md`

## Inputs it needs

- A topic, source, script, preset (`/shorts/<slug>`) or brief; a bare /shorts only opens the preset gallery.
- Optional: presenter photo or video, a voice, a style reference reel, language, length, aspect ratio, a budget cap.
- Own-recording mode: the user's own recording(s) of 20 s or more become the footage instead of generated takes.
- Everything missing is decided by the workflow and said in one line; it never asks (except script approval if the user asked for that).

## Steps in order

1. **Resolve the brief** - Script, host source, supplied files, style reference; one tool check (`reels.py --help`, ffmpeg, faster-whisper, engine doctor).
2. **Host and location** - Four cast sheets (two-panel face + full length) and four rooms; the workflow picks one of each.
3. **Script and plan** - script.md, reel.json takes (dialogue, pronunciations, one shot each), edit-plan.md with Beat/Cue/Captions lines.
4. **Cost line** - One estimate line before the first paid call, then it continues without waiting.
5. **Generate takes** - Every presenter take at once in `generate_video_batch` calls of at most 12; materials, footage and music alongside.
6. **Draft build while jobs run** - reels.py measure --draft + scaffold; placeholders replaced as takes land.
7. **Measure, music, mattes** - reels.py measure (trims picture and speech to the located line), music, cutout.
8. **Compose and render** - Motion design, captions and sound effects in `composition/`; engine render.py renders final.mp4 (size xl), then reels.py check.
9. **Review and deliver** - Frame sequences, compare with style reference, pack composition.zip, upload, register_result, show_result.

## Prompt blocks, word for word

**Presenter take request** (`commands/shorts-references-takes.md`)

```text
generate_video_batch({"requests": [{"index": 2, "params": {
  "model": "seedance_2_5", "prompt": "<authored prompt>",
  "duration": 6, "aspect_ratio": "<reel.json aspect_ratio; 3:4 for 4:5>", "resolution": "<reel.json resolution>",
  "medias": [{"value": "<identity id>", "role": "image_references"},
             {"value": "<location id>", "role": "image_references"}],
  "mode": "omni_reference", "generate_audio": true, "bitrate_mode": "high"
}}]})
```

**Reference roles, cast/photo take** (`commands/shorts-references-takes.md`)

```text
@Image1 defines the presenter's identity and wardrobe only. Its background and
pose are not the scene. @Image2 defines the location: its space, furniture,
materials and light. It is a place, not a fixed camera position; the shot below
sets the camera and the presenter's position in it.
```

**Reference roles, supplied-video take** (`commands/shorts-references-takes.md`)

```text
@Video1 is the reference of the character, voice and location. Preserve the wardrobe,
the location and its light. It is not a fixed camera position; the shot below sets the
camera and the presenter's position in that location.
```

**Audio block (native speech)** (`commands/shorts-references-takes.md`)

```text
Audio: Generate only the presenter's clean, close-miked speaking voice. Use reference
audio for voice identity only. Keep the background silent. No music, score, instrumental
bed, ambient sounds, sound effects or other voices. Do not carry over background audio
from the references.
```

**Shot template** (`commands/shorts-references-takes.md`)

```text
SHOT — <size>: the frame runs from <its top edge> to <where its bottom edge cuts the body>; <frontal or three-quarter>, the lens <level with, above or below> <the presenter's> eyes, <with a style reference: its lens and depth of field,> <locked off, or one move with its speed>: the presenter <posture at the spot>, <action>; behind <the presenter>, <what of the location the frame holds>.
Character says:
"<the take's dialogue>"
```

**Light block form** (`commands/shorts-references-takes.md`)

```text
Light: <the setup's own light>
```

**Cast sheet prompt (4 candidates)** (`commands/shorts-references-avatar.md`)

```text
A natural studio character sheet photograph of one beautiful <ADULT AGE BAND, ETHNICITY
AND GENDER>, <THE ROLE, SUCH AS A BAKERY OWNER, OR A VIDEO PRESENTER WITHOUT ONE>, shown
twice side by side in two equal vertical
panels on one seamless pure-white background. <SHORT HAIRSTYLE; THE TOP, LOWER GARMENT
AND FOOTWEAR>.
Left panel: a frontal, eye-level close-up of the face, from just above the top of the
head down to the collarbones; the face fills most of the panel, sharp and evenly lit.
Right panel: the same person full length, standing upright and facing the camera, the
whole body from head to toe with both feet flat on the floor and fully visible, arms
resting naturally by the sides, a little space above the head and below the feet.
The same face, hair and outfit in both panels, a calm, neutral expression and relaxed
posture. Subtle everyday makeup and natural skin texture. Soft, even frontal lighting.
Only this one presenter and the white background: no other people, no props, no
furniture, no text or labels. Horizontal 4:3 photograph.
```

**Location image prompt** (`commands/shorts-references-avatar.md`)

```text
Ultra-realistic editorial photograph of an empty <LOCATION>, in 16:9.
An ordinary <interior or exterior> photograph at <seated or standing> eye height,
with <the chosen seat, or the open floor in front of the anchor> and its surrounding
furnishings visible at natural proportions in one coherent view. This is a flat
rectilinear <interior or exterior> photograph, not an HDRI, not an equirectangular
panorama, not a 360-degree image, not a fisheye. Keep verticals straight and realistic
furniture proportions, with one coherent camera viewpoint.

<SETTING PARAGRAPH WRITTEN FROM THE SELECTED GEOMETRY ABOVE>.

<SCALE ANCHOR. Seated: for filled and empty rooms, a desk in the middle ground with open
floor in front of it and nothing between it and the camera, the surface completely clear,
and behind it a chair whose back rises to the shoulder height of someone seated at that
desk; for a lit studio, its tabletop paragraph with that chair behind it; for a lounge,
one freestanding armchair with the room visible on both sides of it and one low table,
no wider than the chair, in front. Standing: a clear surface at hip height that belongs
to the place, in the middle ground with open floor in front of it and nothing between it
and the camera, and no chair; a lit studio or a bare wall needs only its open floor.
Outdoors: one object of known size that belongs to the place, beside the standing spot,
with open ground in front of it. A style reference: its own furniture>.

<LIGHTING SENTENCE>. <Indoors: Wall, furniture and surface tones sit clearly lighter and
warmer than; outdoors or from a style reference: Surface tones separate clearly from>
<THE HOST'S GARMENT TONE, WRITTEN AS A TONE ALONE SUCH AS "mid-charcoal">, so the
shoulders separate from everything behind them. Plaster, wood, fabric and metal all
render as <mid tones; from a style reference, the tones of its Grade row> with visible
texture and gradation. Shot on a full-frame camera, 35mm rectilinear lens, f/8, a clear
readable environment throughout, <GRADE: professional color grade, high dynamic range,
editorial campaign quality; from a style reference, its Look table's Grade and Texture
rows in words>. No people, no stand-in figures, no
human reflections, no mannequins, no production equipment, no text, no watermark.
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Presenter takes (talking, native speech) | `seedance_2_5` | mode `omni_reference`, `generate_audio` true, `bitrate_mode` high, 1080p, duration per take, identity + location as `image_references` |
| Presenter takes when the user asks for Wan | `wan3_0_prime` | no mode/bitrate_mode/draft, `enable_thinking` true, 30 fps |
| Casting sheets | `soul_cinematic` (fallback `text2image_soul_v2` 2k) | highest quality tier, 4:3, `enhance_prompt` false, 4 requests |
| Photo-route identity sheet | `gpt_image_2_6_flare` | quality high, 2k, 16:9, count 1, the photo as image reference |
| Voice sample | `elevenlabs_v4` | voice_id UUID, batch_size 1, only when the user names a voice (audio-first mode: voices each take) |
| Music bed | `sonilo_music` | duration = runtime + 20 s, one prompt under 1000 characters |
| Presenter matte | `remove_background` | from the accepted take |
| Compose, captions, render, check | none | reels.py and engine/render.py in the sandbox |

## Checks and gates

- Never resends a paid request beyond one allowed replacement; takes and footage are generated once, no paid prototypes or draft finalizing.
- Never describes a face once an image or video carries identity (no age, build, ethnicity words in later prompts); no printed text or logos on garments.
- Casting check: close-up readable, full-length whole, same person in both panels; a failed candidate replaced once. Rooms: no people or reflections, replaced once.
- `reels.py measure` findings (repeated_line, line_not_located, below_resolution, aspect_mismatch, cue_not_found) are fixed or reported; never upscales or stretches a take.
- Render check: loudness and true-peak findings are traced to music or effects (voice is already at target); still_picture, dark_picture and pictures_slower_than_reference are fixed.
- With a style reference, delivery waits until check shows no compare_missing or compare_stale.
- Runs straight through; no questions. Creating a reel does not publish or post anywhere.

## Price pattern

Quotes one estimate line before the first paid call from live pricing and the planned take count. From `_prices.md`: `seedance_2_5` 1080p omni_reference is 160 per 10 s, so a 60 s reel of six 10 s takes is about 960 credits before casting, rooms, mattes, music and materials (those not quoted). 720p or draft takes cost less.

## Cheap swap

- Presenter takes on `wan3_0` 480p: 7.5 credits per 10 s quoted, so six takes are about 45 credits against about 960, then local Real-ESRGAN upscale (free) if 1080p is needed (about 20x cheaper). (The workflow names `wan3_0_prime` for Wan; `wan3_0` is the quoted id.)
- Own-recording mode: the takes cost nothing at all.
- Cast sheets and rooms: `seedream_5_0_flash` 2k: 0.5 credits a picture quoted, against 1.75-2.5 for 2k pictures (8 images = 4 credits) instead of 2.25 each.
- Matte: local BiRefNet; voice: Kokoro tts (stock voices only) or native speech; captions: local Whisper stt; script and plan: Claude on the plan (free).
