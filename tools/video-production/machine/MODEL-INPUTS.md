# The model input contract

*Rendered from `machine/model-inputs.json` (version 1, read 2026-09-18) by `machine/render_model_inputs.py` — never hand-edited.*

What each settled door actually takes, in the maker's own field names, with the order it recommends the prompt be assembled in, its limits, and which of our scene and frame fields fills each field. A prompt binds this page rather than restating it; the machine builds every request from the same rows, and the contract gate refuses an item that is missing one.

## Declared once per piece, never per scene

| | What it is | House default |
|---|---|---|
| **aspect** | declared ONCE per piece, never per scene — every still, every clip and every crop carries the same value | `9:16` |
| **resolution** | declared ONCE per piece — the still size and the clip resolution are resolved from it per station | `720p` |

Aspect resolves to a still size: `9:16` → `1024x1536` · `16:9` → `1536x1024` · `1:1` → `1024x1024` · `4:5` → `1024x1280` · `3:4` → `1024x1365`.

And to the framing sentence every FIRST FRAME prompt ends on: `9:16` → “Vertical 9:16 framing.” · `16:9` → “Horizontal 16:9 framing.” · `1:1` → “Square 1:1 framing.” · `4:5` → “Vertical 4:5 framing.” · `3:4` → “Vertical 3:4 framing.”.

## The clip prompt — the four blocks, shared by both clip stations

THE FOUR BLOCKS, in the exact shape of the call that worked live on 2026-09-18 evening — Seedance 2.5 on the settled door, first frame + last frame + the scene's voice slice, 9 s, line check 100%.

Every block is built from LABELLED fields. A slot that resolves to nothing is a refusal by name, never a fragment: nothing submits red, so a prompt that cannot be built is not written at all.

Both clip stations (motion and talking) use this one shape; the only differences are the audio line, the words in the timeline and the lip line, each of which names the condition it appears under.

| Block | How it is written |
|---|---|
| 1 · assets | `@Image1 is the first frame: {first}.` `@Image2 is the last frame: {last}.` `@Audio1 is {who}'s voice; they speak the words in @Audio1 exactly, their lips moving with every word, nothing else is said.` (a to-camera scene only — the slice is attached as audio_references) |
| 2 · summary | `{who} at {setting} {does}, {style}, {camera}.` — ONE clean sentence, assembled from labelled slots and never by gluing raw fields end to end. A missing slot is a refusal. |
| 3 · timeline | `{start}-{end}s: {do}`, first `, the frame at @Image1`, last `, settling on the framing of @Image2`, performance ` [{beat}]` |
| 4 · consistency | `One continuous take, no cuts, {camera_sentence}.` `Same {setting}, same {lighting}, same wardrobe throughout.` `The speaker is talking for the whole clip: their lips, jaw and face move naturally with the voice throughout.` (a to-camera scene only) No subtitles. No background music. |

Every slot comes from a LABELLED field, and a slot that resolves to nothing is refused by name — a block built from a gap is a fragment, and a fragment is how a clip ends up being about something else.

The summary's slots, and where each is read from:

| Slot | Read from | What it is |
|---|---|---|
| `who` | scene.who | who is in it, as the brief describes them |
| `setting` | scene.setting | the one world block the scene plays in |
| `does` | scene.happens → first_frame.action | what they do — the scene's own outcome/section line, never a paraphrase of the paragraph |
| `style` | piece.style → first_frame.style | the style words, declared once for the piece by the format profile |
| `camera` | camera_phrases | the camera in one phrase, built from the LAST FRAME's Camera word and the FIRST FRAME's Composition |

The camera, in one phrase and in one sentence, from the LAST FRAME's own Camera word:

| Camera word | In the summary | In what holds |
|---|---|---|
| `same` | a locked frame | the camera does not move |
| `push-in` | one slow push-in from {first_framing} to {target} | the only camera movement is the slow push in |
| `new angle` | one move to a new angle, {target} | the only camera movement is the one move onto the new angle |
| `pull-out` | one slow pull-out from {first_framing} to {target} | the only camera movement is the slow pull out |

the words after 'to' on the LAST FRAME's Camera line — `push-in to close`. A move that names no framing to land on is a refusal, never a guess.

**The LAST FRAME's Camera is one of exactly these:** `same` · `push-in to <framing>` · `pull-out to <framing>` · `new angle to <framing>`.

EXACTLY these four, and a move always names the framing it lands on, in the same words the FIRST FRAME's Composition uses. 'new angle' alone is a move with nowhere to go, and the gate refuses it by name rather than guessing.

### The beat grammar

A beat is ONE visible action, one verb, present tense, something a camera can see. How a line is delivered is not an action: it belongs in the bracket at the end of the beat, never in Do.

Two actions joined by 'and', 'then' or a comma are two beats. A pause is a beat whose action is `holds`, with the pause in Over.

Words a beat never opens on — they name the read, not the picture: `says`, `say`, `speaks`, `speak`, `tells`, `states`, `delivers`, `quotes`, `narrates`, `repeats`, `stops`, `stop`, `slows`, `speeds`, `settles`, `pauses`, `pause`, `emphasises`, `emphasizes`, `continues`, `begins`, `starts`, `finishes`. the verb a beat opens on is what the camera sees happen. These name how the line is performed, not what moves — they belong in the bracket.

The pause: `holds`. a pause IS a beat: `Do: holds`, with the silence named in Over. It is the one beat whose action is stillness, and it is never a delivery note.

B-ROLL IS A SCENE, NOT AN INSERT (2026-09-19). Where the argument shows something, the brief writes a scene of its own — `to_camera: false`, its own setting, frames, beats and the paragraph that plays over it. An insert wedged inside another scene's beat is a second picture inside one clip, and one clip cannot cut.

## The brief — the json block, which IS the brief

THE BRIEF IS THE PROMPT (Damon, 2026-09-19: "this brief is for the AI system to interpret, not for me as the human to read — format these briefs in a way that AI is able to directly build what it needs to build").

So the truth of a brief is the LAST fenced json block in it, in this shape. The Markdown above the block is the readable view for a person, rendered from these same fields; nothing downstream parses it.

Every key below is present on every object — a string stays a string, a list stays a list, and a key with nothing to say carries an empty string rather than being dropped. A dropped key is a gap the gate cannot tell from an omission.

| Object | Every key it carries |
|---|---|
| the block itself | `lane` · `piece` · `cast` · `world` · `product_lock` · `scenes` |
| `piece` | `title` · `aspect_ratio` · `resolution` · `format` · `brand` · `avatar` · `sub` · `awareness` · `sophistication` · `framework` |
| each `cast[]` | `id` · `name` · `identity_block` · `voice` |
| a cast member's `voice` | `cast_voice_id` |
| each `world[]` | `id` · `description` |
| each `scenes[]` | `id` · `section` · `technique` · `delivery` · `emotion` · `outcome` · `setting_id` · `who` · `to_camera` · `voice` · `first_frame` · `beats` · `last_frame` |
| a scene's `delivery` | `humor` · `style` · `register` · `pacing` |
| a scene's `first_frame` | `subject` · `composition` · `action` · `location` · `style` · `camera` · `lighting` · `refs` |
| each `beats[]` | `id` · `do` · `camera` · `over` · `bracket` |
| a scene's `last_frame` | `camera` · `change` |

Optional, and never a refusal: `style` on piece · `openings` on brief · `source` on scene · `on_screen` on scene · `hold` on scene · `held` on scene · `happens` on scene · `voice_settings` on scene. Present where the brief has something to say and absent where it does not — never required, and never a refusal. `openings` carries the hook set, which is a test rather than a scene; `style` is the one grade sentence, taken from the first scene's frame when the piece does not state it; `held` is the one fact that would release a scene the brand's own files cannot fill; `happens` is what the scene DOES in one verb phrase, which is the one slot of the clip's summary sentence a frame field reads badly for. `voice_settings` is the spoken pass's per-scene voice-model settings (stability · style · speed, inside the register recipe's range in components/marketing-doctrine/spoken.json), laid over the cast voice's own record for that chunk; absent, the cast record alone speaks.

- every scene has at least one beat and a voice paragraph — a to-camera scene's paragraph is spoken, a B-roll scene's is the voice playing over it
- a scene with to_camera false is B-roll: the clip carries no audio, and its paragraph is laid under it at the edit
- setting_id names a world block that exists in world[]
- the last frame's camera is one of the four phrases, and a move names the framing it lands on
- one verb per beat, present tense, visible — never a delivery note
- a scene carrying `held` is a scene nothing can make yet: it keeps its place and its section, it names the one fact that would release it, and the machine builds nothing for it rather than generating a frame nobody can describe
- the piece's aspect_ratio and resolution are values the doors take — a ratio and one of the clip door's own words, never a pixel pair
- a scene's `voice` is SPOKEN copy, read aloud by the voice model exactly as written, ONE THOUGHT PER BREATH (Damon, 2026-09-19): no em-dash or en-dash, no semicolon, no parenthesis or bracket. An ellipsis (...) is the mid-thought breath and is KEPT — never a chop into short statements; a full stop ends a thought; an exclamation or question lifts it. The dash/semicolon/parenthesis are read as long silences or the wrong shape and the gate refuses them by name

## still-generate — direct:openai

Model: `gpt-image-2.5-sunburst` (read from providers.json, never written twice).

the FIRST FRAME of a scene — a generation, because no source image exists yet. It carries its references (cast sheet, packshot, style frame) in the order the maker preserves detail in.

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `model` | **required** | the slug in providers.json direct.openai.model | `None` | — |
| `prompt` | **required** | the whole first-frame description, assembled in the order below | `None` | the frame's subject · composition · action · location · style · camera · lighting |
| `image[]` | when references exist | the references, in order — FIRST item is the one whose detail is preserved | `None` | the frame's Refs: cast sheet first, packshot second, style frame last |
| `size` | optional | 1024x1024 · 1536x1024 · 1024x1536 · custom WxH (multiple of 16, ratio 1:3–3:1, max edge 3840) | `resolved from the piece's aspect through aspect_to_size` | the piece's Aspect |
| `quality` | optional | low · medium · high · xhigh · max · auto | `direct.openai.params.quality` | the piece's Resolution |
| `moderation` | optional | auto · low | `direct.openai.params.moderation` | — |
| `output_format` | optional | png · jpeg · webp | `direct.openai.params.output_format` | — |
| `background` | optional | transparent · opaque · auto (transparent needs png/webp) | `None` | — |
| `output_compression` | optional | 0–100, jpeg/webp only | `None` | — |
| `n` | optional | generations only | `1` | — |

**Assembly order:** subject → composition → action → location → style → camera → lighting

the maker's own order for a photographic still — concrete over abstract, and the more specific the words, the more of the frame is decided rather than invented. This is the order a FIRST FRAME is written in, in the brief and in the prompt.

**The maker's limits.**

- `references`: cast sheet first (finest detail preserved), packshot second, style frame last
- `one_person_per_call`: keep one described person per call — an edit that does not name who drifts wardrobe onto everyone
- `text_in_frame`: generate the plate clean; words go on as a layer afterwards (frames-by-edit.md)
- `input_fidelity`: REJECTED on 2.5 — invalid_input_fidelity_model, live 2026-09-18 (providers.json direct.openai.proven). It belongs to the 2.x models; do not send it on the settled slug.

**Our field → its field.**

| Ours | Where it lands |
|---|---|
| subject | who is in it — by the cast name the brief already fixed, never a re-description of the face |
| composition | how it is framed and how much of the frame each thing occupies |
| action | what the person or the object is doing at this instant |
| location | the world block this scene plays in, by its name |
| style | the piece's one grade sentence |
| camera | the result — how high, how close, how much depth — never a named device |
| lighting | where the light comes from and how flat it is |
| refs | image[] — in the order listed |

Read from: https://developers.openai.com/api/docs/guides/image-generation · https://developers.openai.com/api/docs/models/gpt-image-2 · https://developers.openai.com/cookbook/examples/generate_images_with_high_input_fidelity

## still-edit — direct:google

Model: `gemini-3-pro-image` (read from providers.json, never written twice).

the scene's LAST FRAME — an EDIT of its first frame, whose prompt names ONLY the delta. An edit instruction must never describe anything the source image already shows. This is the everyday edit door (Damon 2026-09-18: cheaper, and good).

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `model` | **required** | the slug in providers.json direct.google.image_model | `None` | — |
| `contents[0].parts[].inline_data` | **required** | image refs, in order — the previous frame first, the cast sheet second; up to 6 object refs / 5 character refs on Pro | `None` | the previous frame, then the character's cast sheet |
| `contents[0].parts[].text` | **required** | the instruction — the delta only, stated as a verb | `None` | the frame's Do / Change line |
| `generationConfig.imageConfig.aspectRatio` | optional | 1:1 · 3:2 · 2:3 · 3:4 · 4:3 · 4:5 · 5:4 · 9:16 · 16:9 · 21:9 | `the piece's Aspect` | the piece's Aspect |
| `generationConfig.imageConfig.imageSize` | optional | 1K · 2K · 4K | `direct.google.image_config.imageSize` | the piece's Resolution |
| `safetySettings[].category` | optional | HARASSMENT · HATE_SPEECH · SEXUALLY_EXPLICIT · DANGEROUS_CONTENT · CIVIC_INTEGRITY | `direct.google.safety_categories` | — |
| `safetySettings[].threshold` | optional | BLOCK_NONE · BLOCK_ONLY_HIGH · BLOCK_MEDIUM_AND_ABOVE · BLOCK_LOW_AND_ABOVE | `direct.google.safety` | — |

**Assembly order:** delta

the whole prompt is the change, stated as a verb — add, remove, move, turn, change the grade. Nothing already visible in the source frame is mentioned. Measured: full re-description ran 4,262 characters and blended two identities; delta-only ran 204–386 and held the scene (frames-by-edit.md).

**The maker's limits.**

- `character_refs`: 5
- `object_refs`: 6
- `watermark`: every image carries a non-removable SynthID mark
- `delta_only`: a frame whose prompt describes the room, the wardrobe or the face is re-generating, not editing — the defect this station exists to prevent
- `references`: ALWAYS TWO references, in this order: the previous frame FIRST, the character's cast sheet SECOND. Measured live 2026-09-18 — with the frame alone as the only reference the face drifted.

**Our field → its field.**

| Ours | Where it lands |
|---|---|
| delta | contents[0].parts[].text — the only thing said |
| camera | named only when the camera itself moves on this frame |
| refs | inline_data — the previous frame first, then the packshot where a product reappears |

Read from: https://ai.google.dev/gemini-api/docs/image-generation · https://ai.google.dev/gemini-api/docs/safety-settings

## still-edit-fidelity — direct:openai

Model: `gpt-image-2.5-sunburst` (read from providers.json, never written twice).

THE FACE-RESCALE EDIT — the same delta edit at the stills door, for a last frame whose camera moves in on the face or takes a new angle on it. Measured live 2026-09-18: the edit door held the face but under-delivered the camera move; the fidelity door delivered both.

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `model` | **required** | the slug in providers.json direct.openai.model | `None` | — |
| `prompt` | **required** | the instruction only — the delta, never the scene around it | `None` | the frame's Do / Change line |
| `image[]` | **required** | the previous frame FIRST, the character's cast sheet SECOND | `None` | the previous frame, then the cast sheet |
| `mask` | optional | same size and format as the image, alpha channel, under 50MB | `None` | — |
| `size` | optional | as still-generate | `resolved from the piece's aspect through aspect_to_size` | the piece's Aspect |
| `quality` | optional | low · medium · high · xhigh · max · auto | `direct.openai.params.quality` | the piece's Resolution |
| `input_fidelity` | optional | high — preserves faces, logos and labels | `high` | — |

**Assembly order:** delta

identical to still-edit — focused changes referencing existing content, never the scene around them

**The maker's limits.**

- `references`: ALWAYS TWO references, in this order: the previous frame FIRST, the character's cast sheet SECOND. Measured live 2026-09-18 — with the frame alone as the only reference the face drifted.
- `delta_only`: as still-edit

**Our field → its field.**

| Ours | Where it lands |
|---|---|
| delta | prompt |
| refs | image[] — the previous frame first |

Read from: https://developers.openai.com/api/docs/guides/image-generation · https://developers.openai.com/api/docs/models/gpt-image-2 · https://developers.openai.com/cookbook/examples/generate_images_with_high_input_fidelity

## motion — higgsfield

Model: `seedance_2_5` (read from providers.json, never written twice).

ONE clip per scene — the whole scene, from its FIRST FRAME to its LAST FRAME, with what happens between them written as timed beats on the prompt's own timeline. Two stills per scene, never one per beat; never one clip per line.

| Door | Takes the last frame? | As | Note |
|---|---|---|---|
| `higgsfield:connector` | yes | `end_image` | THE SETTLED DOOR. Its media roles were read off models_explore on 2026-09-18: the last frame IS a real input here, attached as end_image beside the first. start_image must be a media uuid — a URL is rejected upstream. |
| `higgsfield:api` | yes | `end_image_url` | the same house through its own API key pair — separate wallet |
| `byteplus:direct` | yes | `content[].role = last_frame` | the alternate. Explicit first_frame / last_frame roles; on this door the first/last-frame roles and omni_reference are mutually exclusive, so a talking beat there lands its last frame in the timeline's final beat instead. |

a scene has exactly two generated stills — the FIRST FRAME and the LAST FRAME — and both are attached: start_image and end_image. Only a door with no end-frame field falls back to describing the last frame as the timeline's final beat, and the submit sheet says so.

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `model` | **required** | the slug in providers.json providers.higgsfield-mcp.stations.motion | `None` | — |
| `mode` | **required** | t2v · omni_reference · video_edit · video_extension | `omni_reference` | the settled door's one mode — the first frame, the last frame and (on a to-camera scene) the voice slice travel on one call |
| `prompt` | **required** | the assembled paragraph — asset line, one-sentence summary, the timeline of beats, the consistency notes | `None` | the scene's first frame, its beats and its last frame, in that order |
| `start_image` | **required** | an uploaded media id — a URL is rejected upstream (422 uuid_parsing) | `None` | the scene's FIRST FRAME |
| `end_image` | **required** | the scene's last frame — a real input on the settled door (role end_image) and on BytePlus direct (role last_frame) | `None` | the scene's LAST FRAME |
| `duration` | optional | 4–30 | `the scene's own length, read from vo/timing.json — never a number a format sets` | the scene's slice of the one voice track |
| `aspect_ratio` | optional | 21:9 · 16:9 · 4:3 · 1:1 · 3:4 · 9:16 · adaptive | `the piece's Aspect` | the piece's Aspect |
| `resolution` | optional | 480p · 720p (no 1080p native on this door) | `the piece's Resolution` | the piece's Resolution |
| `generate_audio` | optional | true · false | `False` | silent motion carries no sound of its own — the one voice track is laid under it at the edit |

**Assembly order:** assets → summary → timeline → consistency

the maker's own four blocks, in this order, assembled from the shared `clip_prompt` shape at the top of this file — the exact shape of the call that worked live 2026-09-18 evening. (1) the asset line: what @Image1, @Image2 and @Audio1 are; (2) ONE clean summary sentence from labelled slots; (3) the timeline of beats, one verb each, spans off the one voice track, the first anchored on @Image1 and the last settling on @Image2; (4) what holds — the take, the setting, the light, the wardrobe, the negatives.

- **assets** — @Image1 is the first frame: <the first frame in one line>. @Image2 is the last frame: <the delta as a description>.
- **summary** — one sentence — who, where, what they do, the style, the camera
- **timeline** — 0-2.54s: … · 3.18-4.55s: … — one verb per beat, the spans read off the one voice track, the first beat naming the frame at @Image1 and the last settling on the framing of @Image2; a silent beat may carry the words playing over it
- **consistency** — One continuous take, no cuts, <the camera sentence>. Same <setting>, same <light>, same wardrobe throughout. No subtitles. No background music.

**The maker's limits.**

- `max_beats`: 15
- `max_beats_why`: the maker's own warning: a storyboard is better suited to 15 panels or fewer; past that the order drifts and frames go still
- `duration_seconds`: [4, 30]
- `duration_note`: clips within 20 seconds generally produce better results; a scene longer than the ceiling splits at a beat boundary, never mid-paragraph
- `one_verb_per_beat`: True
- `one_verb_why`: two short actions are stable, three or more drift — a beat that names two actions is two beats
- `no_high_frequency_action`: timestamps do not control repeated fast motion
- `refs`: {'images': 30, 'videos': 10, 'audio': 10, 'best': '1–5 subjects; stability decreases from 6'}
- `ceilings_from`: providers.json models[...].ceilings — text and labels garble, hands near a product merge, a product label must be reference-locked
- `frames_per_scene`: 2
- `frames_per_scene_why`: first and last only — the beats between them are written into the timeline, never generated as stills
- `min_beats`: 1
- `clip_media_roles`: ['start_image', 'end_image']
- `clip_media_roles_why`: EXACTLY these roles on the clip, and nothing else. The first frame carries the identity, the wardrobe, the room and the light — a cast sheet or a style frame attached beside it is a second opinion about the same face, and the dry run that found this bug had sent both instead of the first frame (2026-09-18).
- `duration_from`: ceil(the scene's slice of the voice track), floored at the door's minimum. The ceiling is NOT clamped — a paragraph past it is refused by name so the scene is split at a beat boundary, never quietly shortened.

**Our field → its field.**

| Ours | Where it lands |
|---|---|
| first_frame | start_image (the still made for it) and @Image1 in the asset line |
| last_frame | end_image (the still made as an edit of the first) and its own asset line; on a door with no end-frame field, the timeline's final beat plus a consistency note |
| camera | named in the beat only when it moves; otherwise once, in the summary |
| over | the words playing over that beat — {dialogue} where the door performs it, otherwise carried by the voice track at the edit |
| beat_emotion | the attitude word in the beat — never a pacing instruction |
| hold | the consistency block |
| beats | the timeline — one line per beat, its span from vo/timing.json, one verb, the camera only where it moves |

Read from: https://docs.byteplus.com/en/docs/ModelArk/1520757 · https://docs.byteplus.com/en/docs/ModelArk/2607689 · https://higgsfield.ai/seedance/2.5

## talking — higgsfield

Model: `seedance_2_5` (read from providers.json, never written twice).

ONE clip per to-camera scene — the scene's whole paragraph, performed, from its first frame to its last, with the scene's slice of the one voice track attached as the audio it dubs.

| Door | Takes the last frame? | As | Note |
|---|---|---|---|
| `higgsfield:connector` | yes | `end_image` | THE SETTLED DOOR. Its media roles were read off models_explore on 2026-09-18: the last frame IS a real input here, attached as end_image beside the first. start_image must be a media uuid — a URL is rejected upstream. |
| `higgsfield:api` | yes | `end_image_url` | the same house through its own API key pair — separate wallet |
| `byteplus:direct` | yes | `content[].role = last_frame` | the alternate. Explicit first_frame / last_frame roles; on this door the first/last-frame roles and omni_reference are mutually exclusive, so a talking beat there lands its last frame in the timeline's final beat instead. |

a scene has exactly two generated stills — the FIRST FRAME and the LAST FRAME — and both are attached: start_image and end_image. Only a door with no end-frame field falls back to describing the last frame as the timeline's final beat, and the submit sheet says so.

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `model` | **required** | the slug in providers.json providers.higgsfield-mcp.stations.talking | `None` | — |
| `mode` | **required** | t2v · omni_reference · video_edit · video_extension | `omni_reference` | a to-camera scene |
| `prompt` | **required** | the same four assembled blocks as motion, with the spoken paragraph carried by the attached audio rather than written twice | `None` | the scene's first frame, its beats and its last frame, in that order |
| `start_image` | **required** | an uploaded media id — a URL is rejected upstream | `None` | the scene's FIRST FRAME |
| `audio_references` | **required** | up to 10 clips, under 15MB each, 2–30s each | `None` | the scene's slice of the one voice track — vo/<scene>.mp3 |
| `end_image` | **required** | the scene's last frame — a real input on the settled door (role end_image) and on BytePlus direct (role last_frame) | `None` | the scene's LAST FRAME |
| `omni_reference` | optional | the identity references this scene holds to | `None` | the cast sheet for whoever speaks |
| `duration` | optional | 4–30 | `the scene's own length, read from vo/timing.json` | the scene's slice of the one voice track |
| `aspect_ratio` | optional | as motion | `the piece's Aspect` | the piece's Aspect |
| `resolution` | optional | 480p · 720p | `the piece's Resolution` | the piece's Resolution |
| `generate_audio` | optional | true · false | `True` | true on this door — the attached line is what comes back spoken |

**Assembly order:** assets → summary → timeline → consistency

the maker's own four blocks, in this order, assembled from the shared `clip_prompt` shape at the top of this file — the exact shape of the call that worked live 2026-09-18 evening. (1) the asset line: what @Image1, @Image2 and @Audio1 are; (2) ONE clean summary sentence from labelled slots; (3) the timeline of beats, one verb each, spans off the one voice track, the first anchored on @Image1 and the last settling on @Image2; (4) what holds — the take, the setting, the light, the wardrobe, the negatives.

- **assets** — @Image1 is the first frame: <the first frame in one line>. @Image2 is the last frame: <the delta as a description>. @Audio1 is <who>'s voice; they speak the words in @Audio1 exactly, nothing else is said.
- **summary** — one sentence — who, where, what they do, the style, the camera
- **timeline** — 0-2.54s: … · 3.18-4.55s: … — one verb per beat, the spans read off the one voice track, the first beat naming the frame at @Image1 and the last settling on the framing of @Image2; no beat restates the words, because they arrive as attached audio
- **consistency** — One continuous take, no cuts, <the camera sentence>. Same <setting>, same <light>, same wardrobe throughout. Natural lip movement matching the voice. No subtitles. No background music.

**The maker's limits.**

- `max_beats`: 15
- `duration_seconds`: [4, 30]
- `audio_clip_seconds`: [2, 30]
- `audio_clip_mb`: 15
- `one_verb_per_beat`: True
- `line_parity`: every talking clip is transcribed and compared to its paragraph before it ships — lip-sync to the wrong words is a FLAG
- `ceilings_from`: providers.json models[...].ceilings
- `frames_per_scene`: 2
- `frames_per_scene_why`: first and last only — the beats between them are written into the timeline, never generated as stills
- `min_beats`: 1
- `clip_media_roles`: ['start_image', 'end_image', 'audio_references']
- `clip_media_roles_why`: EXACTLY these roles on the clip, and nothing else. The first frame carries the identity, the wardrobe, the room and the light — a cast sheet or a style frame attached beside it is a second opinion about the same face, and the dry run that found this bug had sent both instead of the first frame (2026-09-18).
- `duration_from`: ceil(the scene's slice of the voice track), floored at the door's minimum. The ceiling is NOT clamped — a paragraph past it is refused by name so the scene is split at a beat boundary, never quietly shortened.

**Our field → its field.**

| Ours | Where it lands |
|---|---|
| first_frame | start_image (the still made for it) and @Image1 in the asset line |
| voice_paragraph | audio_references — the scene's slice, never the whole track |
| last_frame | end_image (the still made as an edit of the first) and its own asset line; on a door with no end-frame field, the timeline's final beat plus a consistency note |
| beat_emotion | the attitude word in the beat |
| to_camera | the mode — omni_reference and the audio attached |
| beats | the timeline — one line per beat, its span from vo/timing.json, one verb, the camera only where it moves |

Read from: https://docs.byteplus.com/en/docs/ModelArk/1520757 · https://docs.byteplus.com/en/docs/ModelArk/2607689 · https://higgsfield.ai/seedance/2.5

## voice — direct:elevenlabs

ONE continuous track for the whole piece — every scene's paragraph spoken in order, stitched request to request so the read never restarts, then sliced per scene for the talking door

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `text` | **required** | one chunk — one scene's paragraph | `None` | the scene's Voice paragraph, byte-identical to the script |
| `model_id` | optional | eleven_multilingual_v2 · eleven_v3 | `eleven_multilingual_v2` | — |
| `previous_request_ids` | optional | the request ids of the up-to-3 most recent chunks, read from each response's `request-id` header | `carried automatically, chunk to chunk` | the scene order — this is what makes one read instead of many |
| `previous_text / next_text` | optional | the adjacent text | `None` | — |
| `voice_settings` | optional | stability · similarity_boost · style · use_speaker_boost · speed | `whatever the character's voice.json carries` | the character's own voice record |
| `seed / language_code / apply_text_normalization` | optional | — | `None` | — |

**Assembly order:** scene paragraphs, in brief order

one chunk per scene paragraph — never per sentence. Shooting line by line is what made the read choppy; the paragraph is the unit, and the stitch carries the read across scene boundaries.

**The maker's limits.**

- `previous_request_ids`: 3
- `request_id_age_hours`: 2
- `stitching_model`: eleven_multilingual_v2 only
- `chunking`: the API does not chunk — the machine picks the boundaries, and the boundary is the scene

**Our field → its field.**

| Ours | Where it lands |
|---|---|
| voice_paragraph | text — one chunk per scene |
| scene_order | previous_request_ids — the stitch |
| scene_slice | vo/<scene>.mp3, cut from the one track at the scene's own start and end |

Read from: https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps · https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/request-stitching
