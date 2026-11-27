# Lighting Looks (/<look>-hf)

Relights a user's clip with one of 62 lighting looks through Seedance 2.5 video edit, changing only light and colour, then restores the original audio.

Source files: `lighting-hf/SKILL.md`, `commands/high-key-hf.md`

## Inputs it needs

- One video, 4-30 s, with its media id and URL.
- A look (one of 62 commands such as /high-key-hf, /neon-hf, /golden-hour-hf); several looks run as one generation each on the same clip.
- Resolution 720p by default, 1080p or 480p on request.
- Optional short user note, added as light-only wording.

## Steps in order

1. **Clip** - Confirmed media id and URL; upload an attachment if it has none.
2. **Probe** - Duration D and whether there is audio; one frame via ffmpeg if on-screen text must be checked.
3. **Cost line** - One line: billed by length at the resolution.
4. **Generate** - `generate_video`, mode `video_edit`, the look's prompt sent verbatim, clip as @Video1 only.
5. **Restore audio** - Same remux as the other edit workflows.
6. **Deliver** - One line: look, resolution, duration, audio kept; tell the user if the result is shorter than the clip.

## Prompt blocks, word for word

**The look prompt (High-key example, verbatim)** (`commands/high-key-hf.md`)

```text
LIGHTING & COLOUR CHANGE ONLY - HIGH-KEY.

KEEP MY SHOT: @Video1 is my original video. Keep it exactly as it is: the same location, architecture, walls,
windows, floor, background, every object, every person, their faces, hair and clothes, their positions,
movements, gestures, expressions and lip movement, and the camera movement, framing and timing. Nobody gets a
hat, cap or any new accessory. Never add, remove, replace or redecorate anything. Only the light falling on
the existing scene and the colour grade change.

NEW LIGHT:
- Exposure raised by about 2 stops: the whole image is very bright, airy and luminous, much lighter than the
original in every frame.
- Huge soft white light from in front and from both sides, out of frame, floods the people: faces bright and
glowing, almost no shadows under the chins or noses.
- The existing walls, floor and objects turn bright and pale; the lightest parts of the background bloom to
near pure white while their shapes stay visible.
- Shadows lifted to light grey, never dark; very low contrast, soft white bloom around highlights, clean
bright skin, gentle saturation, crisp commercial look.
- The change from the original light is obvious at first glance in every frame.

The location of @Video1 stays fully recognisable in every frame. Light is physically real: it wraps faces and
bodies and moves correctly as people and camera move, never a flat filter. Photorealistic, natural skin
texture, original lens perspective. No added text, no music.
```

**Sentence added when the clip has on-screen text** (`lighting-hf/SKILL.md`)

```text
Keep every
caption, subtitle, title, logo and other on-screen text exactly as in @Video1: same words, styling, position
and timing; only the light on the scene changes.
```

**Generation request** (`lighting-hf/SKILL.md`)

```text
{"params":{"model":"seedance_2_5","mode":"video_edit","prompt":"<the look's prompt>","count":1,"duration":<ceil(D)>,"resolution":"720p","aspect_ratio":"auto","generate_audio":false,"medias":[{"value":"<clip media id>","role":"video"}]}}
```

**Look list (commands)** (`lighting-hf/SKILL.md`)

```text
| Command                 | Look                     |
| ----------------------- | ------------------------ |
| `/high-key-hf`          | High-key                 |
| `/low-key-hf`           | Low-key                  |
| `/rembrandt-hf`         | Rembrandt                |
| `/butterfly-hf`         | Butterfly (Paramount)    |
| `/split-hf`             | Split                    |
| `/loop-hf`              | Loop                     |
| `/broad-hf`             | Broad                    |
| `/short-hf`             | Short                    |
| `/chiaroscuro-hf`       | Chiaroscuro              |
| `/silhouette-hf`        | Silhouette               |
| `/rim-light-hf`         | Rim / backlight          |
| `/hard-light-hf`        | Hard light               |
| `/soft-light-hf`        | Soft light               |
| `/bounce-hf`            | Bounce                   |
| `/top-light-hf`         | Top light                |
| `/under-lighting-hf`    | Under lighting           |
| `/golden-hour-hf`       | Golden hour              |
| `/blue-hour-hf`         | Blue hour                |
| `/day-for-night-hf`     | Day-for-night            |
| `/moonlight-hf`         | Moonlight                |
| `/window-light-hf`      | Window light             |
| `/practical-hf`         | Practical                |
| `/firelight-hf`         | Firelight / candlelight  |
| `/venetian-blinds-hf`   | Venetian blinds          |
| `/dappled-hf`           | Dappled / gobo           |
| `/god-rays-hf`          | Volumetric (god rays)    |
| `/overcast-hf`          | Overcast / flat          |
| `/neon-hf`              | Neon                     |
| `/teal-orange-hf`       | Teal & orange            |
| `/monochrome-red-hf`    | Monochrome red           |
| `/screen-glow-hf`       | Screen glow              |
| `/passing-light-hf`     | Passing light            |
| `/strobe-hf`            | Strobe / flicker         |
| `/spotlight-hf`         | Theatrical spotlight     |
| `/clamshell-hf`         | Clamshell                |
| `/three-point-hf`       | Three-point              |
| `/cross-lighting-hf`    | Cross lighting           |
| `/kicker-hf`            | Kicker                   |
| `/eye-light-hf`         | Eye light                |
| `/ring-light-hf`        | Ring light               |
| `/direct-flash-hf`      | Direct flash             |
| `/snow-light-hf`        | Snow light               |
| `/lens-flare-hf`        | Lens flare               |
| `/lightning-hf`         | Lightning                |
| `/atmospheric-fog-hf`   | Atmospheric fog          |
| `/sodium-vapour-hf`     | Sodium vapour            |
| `/fluorescent-hf`       | Fluorescent              |
| `/bare-bulb-hf`         | Bare bulb                |
| `/flashlight-hf`        | Flashlight               |
| `/dashboard-light-hf`   | Dashboard light          |
| `/police-lights-hf`     | Police lights            |
| `/projector-beams-hf`   | Projector beams          |
| `/stained-glass-hf`     | Stained glass            |
| `/searchlight-hf`       | Searchlight              |
| `/explosion-hf`         | Explosion                |
| `/laser-light-hf`       | Laser light              |
| `/blacklight-hf`        | Blacklight               |
| `/bi-colour-hf`         | Bi-colour light          |
| `/mixed-temperature-hf` | Mixed colour temperature |
| `/cast-shadow-hf`       | Cast shadow              |
| `/city-bokeh-hf`        | City bokeh               |
| `/bloom-hf`             | Bloom / halation         |
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Relight | `seedance_2_5` | mode `video_edit`, duration ceil(D), resolution 720p, aspect_ratio auto, generate_audio false, clip as role `video` |

## Checks and gates

- Never writes or rewrites a look's prompt: it is sent verbatim; a user note goes in as one light-only sentence at the end of NEW LIGHT and never removes the KEEP MY SHOT lines.
- Clip outside 4-30 s is reported and stopped.
- Adds the on-screen-text sentence when the clip has captions, titles or logos.
- Review only when asked: faces, movement, lip sync match the original; if drifted, one retry is offered.
- Library note: only `/high-key-hf` is saved here with its prompt; the other 61 look prompts are served by their own commands and were not pulled.

## Price pattern

Quotes by length at the resolution; one paid generation per clip per look. `seedance_2_5` video_edit is not quoted in `_prices.md` (omni_reference draft 480p/10 s is 30 credits): not quoted, re-quote before running.

## Cheap swap

- Gemini edit: `gemini_omni_flash_1_2` mode `edit`, 360p (source 3-15 s, up to 7 image refs): the same 7.5 credits per 10 s tier as its quoted reference-to-video; the edit price itself is not quoted, re-quote first.
- A rough relight for a plain tint or exposure shift can be done free with local ffmpeg (eq, curves, colorbalance, vignette); a true relight (new light direction, shadows) needs a model.
- Look prompts are fixed text, so there is no writing cost.
