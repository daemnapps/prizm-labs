# Colour Grades (/<grade>-grade-hf)

Regrades a user's clip with one of 34 ShotDeck-board colour grades, each a Seedance 2.5 video edit with a colour-only prompt; location, people, motion and audio stay.

Source files: `grade-hf/SKILL.md`, `commands/teal-orange-grade-hf.md`

## Inputs it needs

- One video, 4-30 s, with its media id and URL.
- A grade (one of 34 commands such as /teal-orange-grade-hf, /bleach-bypass-grade-hf).
- Resolution 720p default, 1080p or 480p on request; optional colour-only user note.

## Steps in order

1. **Source** - Confirmed media id and URL.
2. **Probe** - Duration and audio stream.
3. **Cost line** - One line.
4. **Generate** - `generate_video` mode `video_edit`, the grade's prompt verbatim, clip as @Video1.
5. **Restore audio** - Remux original audio.
6. **Deliver** - One line: grade, resolution, duration, audio kept.

## Prompt blocks, word for word

**The grade prompt (Teal & Orange, verbatim)** (`commands/teal-orange-grade-hf.md`)

```text
COLOUR GRADE ONLY - TEAL & ORANGE.

KEEP MY SHOT: @Video1 is my original video. Keep it exactly as it is: the same location, architecture, walls,
windows, floor, background, every object, every person, their faces, hair and clothes, their positions,
movements, gestures, expressions and lip movement, the light sources and shadows, and the camera movement,
framing and timing. Never add, remove, replace or redecorate anything. Only the colours of the existing frame
change.

NEW GRADE:
Regrade as the blockbuster teal and orange look: skin and warm highlights pushed to a rich golden orange,
while shadows, walls and background shift to a deep cool teal-cyan. Strong separation between the warm people
and the teal surroundings, punchy contrast.

The location of @Video1 stays fully recognisable in every frame and every edge and texture stays sharp.
Photorealistic, natural skin texture, original lens perspective. No added text, no music.
```

**'Softer' note wording** (`grade-hf/SKILL.md`)

```text
Apply this grade at about half strength; keep more
of the original colour.
```

**Sentence added when the clip has on-screen text** (`grade-hf/SKILL.md`)

```text
Keep every caption, subtitle, title, logo and other on-screen text exactly as in
@Video1: same words, styling, position and timing; only the colours of the scene change.
```

**Generation request** (`grade-hf/SKILL.md`)

```text
{"params":{"model":"seedance_2_5","mode":"video_edit","prompt":"<the grade's prompt>","count":1,"duration":<ceil(D)>,"resolution":"720p","aspect_ratio":"auto","generate_audio":false,"medias":[{"value":"<clip media id>","role":"video"}]}}
```

**Grade list (commands)** (`grade-hf/SKILL.md`)

```text
| Command                           | Grade                 |
| --------------------------------- | --------------------- |
| `/high-key-airy-grade-hf`         | High-Key Airy         |
| `/teal-orange-grade-hf`           | Teal & Orange         |
| `/bleach-bypass-grade-hf`         | Bleach Bypass         |
| `/cross-processed-grade-hf`       | Cross-Processed       |
| `/desaturated-grade-hf`           | Desaturated           |
| `/technicolor-grade-hf`           | Technicolor           |
| `/duotone-grade-hf`               | Duotone               |
| `/red-wash-grade-hf`              | Red Wash              |
| `/hyper-saturated-grade-hf`       | Hyper-Saturated       |
| `/colour-negative-grade-hf`       | Colour Negative       |
| `/pastel-grade-hf`                | Pastel                |
| `/warm-amber-grade-hf`            | Warm Amber            |
| `/cool-blue-grade-hf`             | Cool Blue             |
| `/matrix-green-grade-hf`          | Matrix Green          |
| `/yellow-tint-grade-hf`           | Yellow Tint           |
| `/magenta-wash-grade-hf`          | Magenta Wash          |
| `/complementary-palette-grade-hf` | Complementary Palette |
| `/analogous-palette-grade-hf`     | Analogous Palette     |
| `/monochromatic-grade-hf`         | Monochromatic Palette |
| `/split-toning-grade-hf`          | Split Toning          |
| `/crushed-blacks-grade-hf`        | Crushed Blacks        |
| `/lifted-blacks-grade-hf`         | Lifted Blacks         |
| `/print-film-grade-hf`            | Print Film Emulation  |
| `/kodachrome-grade-hf`            | Kodachrome            |
| `/fuji-greens-grade-hf`           | Fuji Greens           |
| `/day-for-night-grade-hf`         | Day-for-Night         |
| `/infrared-grade-hf`              | Infrared              |
| `/neon-noir-grade-hf`             | Neon Noir             |
| `/1970s-vintage-grade-hf`         | 1970s Vintage         |
| `/night-vision-grade-hf`          | Night Vision          |
| `/sickly-green-yellow-grade-hf`   | Sickly Green-Yellow   |
| `/thermal-grade-hf`               | Thermal               |
| `/earth-tones-grade-hf`           | Earth Tones           |
| `/blown-out-grade-hf`             | Blown-Out Highlights  |
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Regrade | `seedance_2_5` | mode `video_edit`, duration ceil(D), resolution 720p, aspect_ratio auto, generate_audio false, clip as role `video` |

## Checks and gates

- Never writes a grade of its own, swaps in other colours (brand colours included), or grades with ffmpeg, LUTs or filters: ffmpeg only probes and restores audio.
- Duotone, red-wash and colour-negative come out as a strongly tinted scene with near-natural skin: the user is told in one line.
- A user note becomes one colour-and-tone sentence at the end of NEW GRADE; never removes KEEP MY SHOT.
- Matching a film or reference stills is `/color-grade`, not this workflow.
- Library note: only `/teal-orange-grade-hf` is saved with its prompt; the other 33 grade prompts are not in the library.

## Price pattern

Quotes by length at the resolution; one paid generation per clip per grade. `seedance_2_5` video_edit is not quoted in `_prices.md`: not quoted, re-quote first.

## Cheap swap

- Free local grading: the `color-grade` engine (below) or ffmpeg curves/colorbalance/LUT does a grade for 0 credits, but it is a colour transform, not Seedance's re-render, so a strong creative grade will look different.
- Gemini edit: `gemini_omni_flash_1_2` mode `edit`, 360p (source 3-15 s, up to 7 image refs): the same 7.5 credits per 10 s tier as its quoted reference-to-video; the edit price itself is not quoted, re-quote first.
