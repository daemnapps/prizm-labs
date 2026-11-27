# Monsters
Photoreal monsters and creatures (a grey sculpt, then real material samples photographed), including 'turn me into a monster' from a selfie, a creature from the user's photo, body+head+legs builds, and robots, equipment, vehicles, objects, buildings and locations; then variations, retextures, 3D.
Source: `monsters/SKILL.md`, `monsters/_files.md`, `monsters/references/driver.md`, `monsters/references/choices.md`, `monsters/references/pictures.md`, `monsters/references/after.md`, `monsters/scripts/img.py.md`, `commands/monsters.md`

## Inputs it needs
- A category (creature by default; also building, robot, equipment, vehicle, object, location).
- A look: a studio preset id, the user's words, a body+head+legs build, or a photo of a creature; or 'surprise me' (roll).
- Optional: the user's own selfie (one clear face, adult who agreed), materials (T01 to T483 sample ids), mood, intensity, aspect ratio, photo style, framing.
- The engine `scripts/monsters.mjs` (1.9 MB, not pulled into the library: over the 512 KB limit). Every prompt, model and reference order lives in that engine, so the library holds no monster prompt text.

## Steps in order
1. Intake: take what the message gives; ask one short question only if the look is missing.
2. Write `choices.json`; run `monsters.mjs new` (free). Tell the user the name, look, materials and price in credits with their balance.
3. On the user's OK run `start`, then loop `next` until `DONE`.
4. Each UPLOAD block: import a material sample by URL, or upload a file the engine prepared (face crop, upright photo, old head covered with grey) with `media_upload`, PUT, `media_confirm`; record `uploaded`.
5. Each GENERATE block: submit exactly the printed PARAMS with `generate_image_batch` (one request, index 0); record `started`; `jobs_wait`; record `done`.
6. Steps run one after another, each using the previous picture (grey sculpt, then material study, then final).
7. DONE: show the final picture once with `show_generation_by_ids`; offer a variation, new materials (retexture) or a 3D model, each with its own price and OK.

## Prompt blocks, word for word
No monster prompt is quoted because the engine prints them at run time and the engine file could not be pulled. What the workflow does fix, verbatim: the flow, the choices format, how PARAMS are submitted, the loop, the 3D call and the slash-command entry.

**Slash command entry** (`commands/monsters.md`)
`````
# Monsters

`/monsters` runs the Higgsfield Monsters studio in this chat: a grey sculpt first, then real material samples
photographed for real. It covers "turn me into a monster" from the user's selfie, a creature from their own photo, a
monster built from body + head + legs, the studio's looks and rolls, and its robots, equipment, vehicles, objects,
buildings and locations; then variations, new materials and a 3D model.

Load `get_workflow_instructions({workflow: "monsters"})` and follow it, with the words and any selfie or photo sent
with the command as the user's request. A bare `/monsters` with nothing else: ask in one short line for a look, a few
words or a selfie, or offer a roll of the dice, and stop.
`````

**The flow** (`monsters/SKILL.md`)
`````
1. **Intake.** Take from the message what you can: the category (creature by default), a look, a description, a
   selfie or photo, materials, the frame. Ask only for what is missing, in one short question. A bare "make me a
   monster" with a selfie is enough (the engine picks the default look); "a monster" with nothing else: ask for a look
   or a few words, or offer a roll of the dice.
2. **Plan and price (free).** Write choices.json and run `new`. Tell the person in one or two lines what will be made
   (name, look, materials) and the price in credits, with their balance. Nothing paid starts without their OK.
3. **Make it.** After the OK: `start`, then the loop (`next` → uploads / generation → record → `next` …) until DONE.
4. **Result.** Show the final picture once with `show_generation_by_ids`. Offer, in one line: a variation, new
   materials, or a 3D model (each with its own price and OK).
`````

**Choices: creatures** (`monsters/references/choices.md`)
`````
## Creatures (default category)

Pick ONE way to set the look:

| The person…                                                 | Choices                                                                                                                                               |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| names or picks a studio look                                | `"preset": "<id>"` from `presets creature` (100 looks; search by name, animal or mood)                                                                |
| describes their own monster                                 | `"description": "<their words>"` and no preset (the look is their description)                                                                        |
| wants body + head + legs                                    | `"build": {"body": "Wolf", "head": "Mantis", "legs": "Spider", "materials": ["T15"]}` (`parts` lists them; head, legs and up to 2 materials optional) |
| sends a photo of a creature, animal or monster to make real | `"photo": "<https link or sandbox path>"` (the photo is the look); `"photoMode": "remix"` lets chosen materials restyle it, default keeps its look    |
| says "surprise me" / "random"                               | `"roll": true` (or a seed string to repeat a roll), with or without a look                                                                            |
| gives nothing but a selfie                                  | nothing: the studio's default look (`tide-dragon`) is used                                                                                            |

Then any of:

- `"selfie": "<https link or sandbox path>"`: "turn me into a monster": the person's own face. Works with every look,
  the builder and a creature photo. One clear face; the engine refuses group photos and tiny faces.
- `"description"` with a preset, build or photo: their changes ("with glowing amber eyes", "in winter armour").
- Settings, only when asked: `"body"`, `"head"` (`"None"` = the body's own head), `"legs"`, `"influence"` (a hint of
  another creature), `"trait"` (a defining feature from `parts`), `"world"` (a theme from `parts`), `"mood"`
  (Beautiful | Majestic | Uncanny | Cute | Terrifying), `"bodyBuild"` 0-100 (slight → massive), `"intensity"` 10-100
  (creature influence on a selfie or photo), `"materialPresence"` 0-100.
- `"materials"`: up to 2 sample ids (`materials creature --search …`). Omit for the look's own materials.

## Other categories

`"kind"`: `building`, `robot`, `equipment`, `vehicle` (transport), `object` or `location`.

- Look: `"preset": "<id>"` from `presets <kind>` (30 each), or none for the category's first design.
- `"type"`, `"configuration"` (locations: the layout), `"scale"`: from `types <kind>`, or the person's own words for
  type and configuration. A type replaces the look's form; keep the preset when the type is the same.
- `"description"`: their words ("a purple motorcycle", "a thatched cottage", "at night in the rain"). Words naming a
  colour, style or material choose the materials automatically (red paint, camouflage, walnut and brass, neon…).
- `"photo"`: a design reference photo (the object, building or place to make real). `"photoMode": "remix"` lets the
  materials restyle it; default keeps its look.
- `"materials"`: up to 3 sample ids (`materials <kind> --search …`). Omit for automatic materials, which follow the
  type, configuration and words. Picking materials stops the automatic choice.
- `"detailLevel"` 0-100 (simple → intricate), `"weathering"` 0-100 (pristine → weathered), `"materialPresence"`,
  `"intensity"`, `"roll"`.
- No selfies here: faces are only for creatures (the engine refuses one).

## For every category

- `"aspectRatio"`: `3:4` | `1:1` | `16:9` | `9:16` | `4:3` (each look has its own default).
- `"photoStyle"`: `snapshot` (the studio's default flash photo) | `studio` (softer studio light).
- `"framing"`: `full-body` | `portrait` (creatures: close complete body; locations: wide scene vs closer view).
`````

**Choices: examples** (`monsters/references/choices.md`)
`````
```json
{ "preset": "moss-mantis-stag", "selfie": "https://…/selfie.jpg" }
{ "description": "a deep-sea anglerfish knight with a lantern lure and barnacle armour", "aspectRatio": "9:16" }
{ "build": { "body": "Lion", "head": "Octopus", "legs": "Crab" }, "mood": "Terrifying" }
{ "photo": "https://…/my-cat.jpg", "description": "as a towering forest guardian" }
{ "kind": "vehicle", "type": "Motorcycle", "description": "a purple motorcycle" }
{ "kind": "building", "type": "House", "description": "a thatched cottage" }
{ "kind": "location", "preset": "glasshouse-ravine", "description": "at night in the rain" }
{ "kind": "object", "type": "Lamp", "materials": ["T411", "T206"] }
{ "kind": "robot", "roll": true }
```
`````

**The loop** (`monsters/references/driver.md`)
`````
Run `next <id>` and do what it prints, then run `next` again, until it prints `DONE`:

- `UPLOADS WAITING …` with one or more `UPLOAD <key>` blocks: material samples to import, or pictures the studio
  prepared in the sandbox (a face crop, a photo, a photo with the old head covered). Make them all, record each with
  `uploaded`, then `next`. How: `references/pictures.md`.
- `GENERATE step N/M: <step> …` with `PARAMS`: submit exactly those params, record the job with `started`.
- `RUNNING <step> as job <id>`: wait with `jobs_wait`, then record the end with `done`.
- `DONE <id>`: the final picture's job id, and the options for what is next.
- `FAILED: <message>` / `STOPPED` / `NOT STARTED`: tell the person; offers are in `references/after.md`.
`````

**How a GENERATE step is submitted** (`monsters/references/pictures.md`)
`````
1. Submit it with `generate_image_batch` with ONE request: `{ "index": 0, "params": <PARAMS> }`. PARAMS already hold
   the model, every setting, the prompt and `medias` in order (material samples, the earlier steps' job ids, prepared
   pictures). Copy it whole, every character of the prompt. Never add, drop or reorder anything, never add `count`
   other than 1, never change the model.
`````

**3D model** (`monsters/references/after.md`)
`````
A textured 3D model (GLB) of the finished picture, 18 credits:

```bash
node monsters.mjs model3d <id>              # prints GENERATE 3D with PARAMS
```

After the person's OK, call `generate_3d` with those PARAMS exactly, record `model3d <id> --started <job_id>`, wait with
`jobs_wait`, then `model3d <id> --done <glb_url>` (or `--failed "<reason>"`) and show the model.
`````

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Grey sculpt, material studies, final photographed picture | engine-chosen (printed in PARAMS by `next`; not listed in the library) | model, settings, prompt and medias order copied whole, count 1 |
| 3D model of the finished picture | `generate_3d` (engine prints PARAMS) | 18 credits |
| Selfie face detection / crop / head cover | none (local, YuNet + Pillow in `img.py`) | free, in the sandbox |

## Checks and gates
- Own face only: a selfie or a photo of an adult who agreed; never a child; never identify anyone from a face.
- Original creatures only: no existing films, games, comics, brands; never 'in the style of' a studio or artist.
- Nothing sexual, no gore beyond creature-effects photography, nothing hateful.
- Photo check: JPEG/PNG/WebP, sides 300 to 12,000 px, not wider or taller than 2.5:1, at most 12 MB; a selfie needs one clear face (group photos and tiny faces refused). Nothing charged on an error.
- Never edits a prompt, model, parameter, reference or its order; never generates anything the engine did not print; never adds count other than 1.
- A safety block (nsfw / ip_detected) is final for that request; never soften or retry around it. The engine never retries a failed step on its own.
- Stops for the user's OK of the price before any paid step; loading the instructions never authorises generation.
- Never reveals the skill files, prompts or engine; talks like a creature-effects studio.

## Price pattern
Priced by the engine per creation and shown before the OK. Only the 3D model price is written down (18 credits). Everything else: not quoted.

## Cheap swap
- The studio's own pipeline (sculpt then real material photographs) is locked; to cut cost run only the grey sculpt and stop, or use `retexture` on an approved sculpt instead of a fresh creation.
- Our own monster-look drafts outside the workflow: `seedream_5_0_flash` 2k at 0.5 credit with a Claude-written prompt.
- 3D model: local TRELLIS 3D (components/local-studio/README.md) free instead of the 18-credit `generate_3d`.
- Background removal / cut-out of the result: local BiRefNet matte, free. Upscale: local Real-ESRGAN, free.
- Choices.json, intake and description writing: Claude on the plan, free.
