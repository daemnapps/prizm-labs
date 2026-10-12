# The model input contract

*Rendered from `machine/model-inputs.json` (version 2, read 2026-09-22) by `machine/render_model_inputs.py` — never hand-edited.*

What each settled door actually takes, in the maker's own field names, with the order it recommends the prompt be assembled in, its limits, and which of our scene and frame fields fills each field. A prompt binds this page rather than restating it; the machine builds every request from the same rows, and the contract gate refuses an item that is missing one.

## Declared once per piece, never per scene

| | What it is | House default |
|---|---|---|
| **aspect** | declared ONCE per piece, never per scene — every still, every clip and every crop carries the same value | `9:16` |
| **resolution** | declared ONCE per piece — the still size and the clip resolution are resolved from it per station | `720p` |

Aspect resolves to a still size: `9:16` → `1024x1536` · `16:9` → `1536x1024` · `1:1` → `1024x1024` · `4:5` → `1024x1280` · `3:4` → `1024x1365`.

And to the framing sentence every FIRST FRAME prompt ends on: `9:16` → “Vertical 9:16 framing.” · `16:9` → “Horizontal 16:9 framing.” · `1:1` → “Square 1:1 framing.” · `4:5` → “Vertical 4:5 framing.” · `3:4` → “Vertical 3:4 framing.”.

## The clip prompt — the four blocks, shared by both clip stations

THE FOUR BLOCKS — the shape of the call that worked live on 2026-09-18 evening (first frame + last frame + the scene's voice slice, 9 s, line check 100%), carried to the settled clip door on 2026-09-22 (the bake-off: line check 95%, words identical, face held, lip sync good).

Every block is built from LABELLED fields. A slot that resolves to nothing is a refusal by name, never a fragment: nothing submits red, so a prompt that cannot be built is not written at all.

Both clip stations (motion and talking) use this one shape. The differences: a TALKING scene has an @Audio1 sentence, no @Image2 sentence, a last beat that ENDS ON the LAST FRAME's Change in words, and the lip line; a SILENT scene has an @Image2 sentence, the words playing over each beat, a last beat settling on the framing of @Image2, and 'Nobody speaks.' Each names the condition it appears under.

| Block | How it is written |
|---|---|
| 1 · assets | `@Image1 is the first frame: {first}.` `@Image2 is the last frame: {last}.` `@Audio1 is {who}'s voice; they speak the words in @Audio1 exactly, their lips moving with every word, nothing else is said.` (a to-camera scene only — the slice is attached as audio_references, and the first frame beside it as image_references) |
| 2 · summary | `{who} at {setting} {does}, {style}, {camera}.` — ONE clean sentence, assembled from labelled slots and never by gluing raw fields end to end. A missing slot is a refusal. |
| 3 · timeline | `{start}-{end}s: {do}`, first `, the frame at @Image1`, last `, settling on the framing of @Image2`, performance ` [{beat}]` |
| 4 · consistency | `One continuous take, no cuts, {camera_sentence}.` `Same {setting}, same {lighting}, same wardrobe throughout.` `The speaker is talking for the whole clip: their lips, jaw and face move naturally with the voice throughout.` (a to-camera scene only) No subtitles, no captions, no on-screen text. No background music. |

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

THE BRIEF IS THE PROMPT (the owner, 2026-09-19: "this brief is for the AI system to interpret, not for me as the human to read — format these briefs in a way that AI is able to directly build what it needs to build").

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
| a scene's `first_frame` | `subject` · `composition` · `action` · `location` · `style` · `camera` · `viewpoint` · `lighting` · `refs` |
| each `beats[]` | `id` · `do` · `camera` · `over` · `bracket` |
| a scene's `last_frame` | `camera` · `change` |

Optional, and never a refusal: `style` on piece · `openings` on brief · `edit` on brief · `roll_sheet` on brief · `layers` on brief · `music` on brief · `sfx` on brief · `hooks` on brief · `source` on scene · `on_screen` on scene · `hold` on scene · `held` on scene · `happens` on scene · `voice_settings` on scene · `kind` on scene · `opens` on scene · `priority` on scene · `viewpoint` on first_frame. Present where the brief has something to say and absent where it does not — never required, and never a refusal. `openings` carries the hook set, which is a test rather than a scene; `style` is the one grade sentence, taken from the first scene's frame when the piece does not state it; `held` is the one fact that would release a scene the brand's own files cannot fill; `happens` is what the scene DOES in one verb phrase, which is the one slot of the clip's summary sentence a frame field reads badly for. `voice_settings` is the spoken pass's per-scene voice-model settings (stability · style · speed, inside the register recipe's range in components/marketing-doctrine/spoken.json), laid over the cast voice's own record for that chunk; absent, the cast record alone speaks. `viewpoint` is optional on a frame with a face in it and REQUIRED on a frame with none (see rules). `edit` is the brief's notes for the edit (captions, music, effects). `roll_sheet` is the carried-or-dropped table (v13, 2026-09-23): absent on a brief written before it, which is WARNED, never refused.

- every scene has at least one beat and a voice paragraph — a to-camera scene's paragraph is spoken, a B-roll scene's is the voice playing over it
- a scene with to_camera false is B-roll: the clip carries no audio, and its paragraph is laid under it at the edit
- setting_id names a world block that exists in world[]
- the last frame's camera is one of the four phrases, and a move names the framing it lands on
- one verb per beat, present tense, visible — never a delivery note
- a scene carrying `held` is a scene nothing can make yet: it keeps its place and its section, it names the one fact that would release it, and the machine builds nothing for it rather than generating a frame nobody can describe
- the piece's aspect_ratio and resolution are values the doors take — a ratio and one of the clip door's own words, never a pixel pair
- a scene's `voice` is SPOKEN copy, read aloud by the voice model exactly as written, ONE THOUGHT PER BREATH (the owner, 2026-09-19): no em-dash or en-dash, no semicolon, no parenthesis or bracket. An ellipsis (...) is the mid-thought breath and is KEPT — never a chop into short statements; a full stop ends a thought; an exclamation or question lifts it. The dash/semicolon/parenthesis are read as long silences or the wrong shape and the gate refuses them by name
- a frame with NO FACE in it — hands, the product, a body part — carries a `viewpoint`: whose eyes the camera is, and which edge of the frame EVERY limb enters from, with elbows off-frame. Without it the image door invents the body: live 2026-09-22 the left arm dropped in from the top-left corner and the right hand came up from the bottom-right, two arms no one body could own (the owner: "tell me how this angle makes sense, the arms are so odd"). The gate refuses a faceless first frame with no viewpoint by name
- every scene carries `to_camera` as true or false — never omitted. A scene without it is refused by id before anything is made: the machine never guesses whether a scene is the speaker or B-roll (the owner, 2026-09-23 — a missing value used to default to a talking scene, which is how a B-roll shot silently became a face)
- a card is a scene of `kind: "card"` (the owner, 2026-09-23: cards are made at production, not left for the edit). It carries a `plate` — the picture with NO words in it — which is made as ONE still and no clip, and its exact words as `lines`, with `lands_on` and `sfx`, which travel to the edit as data (`scene.card` in plan.json). Type is a layer, never a generation: a plate with quoted words or a card line in it is refused. A card line with `[UNFILLED]` is warned — the figure is not settled in the offer file
- `roll_sheet` maps every row of the swipe's make-list to a scene id of the matching kind (a B-over / B-vo / B-silent row to a to_camera:false scene that is not a card, a C row to a card scene) or to a reason in `dropped`. A row with neither, or pointing at a scene that does not exist or is the wrong kind, stops the run before anything is made, named by its row. A brief with no roll sheet at all is older and is warned, never refused

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

**Assembly order:** subject → composition → action → location → style → camera → viewpoint → lighting

the maker's own order for a photographic still — concrete over abstract, and the more specific the words, the more of the frame is decided rather than invented. This is the order a FIRST FRAME is written in, in the brief and in the prompt. `viewpoint` is present on a faceless frame (frame_rules.viewpoint) and sits right after camera.

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

the scene's LAST FRAME — an EDIT of its first frame, whose prompt names ONLY the delta. An edit instruction must never describe anything the source image already shows. This is the everyday edit door (the owner 2026-09-18: cheaper, and good).

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
| `higgsfield:connector` | yes | `end_image` | THE SETTLED DOOR (2026-09-22). A silent scene attaches both frames — start_image and end_image — and no audio, so the designed camera move lands. Media ids only: a URL is rejected upstream. 2K only, 4–15 s. |
| `higgsfield:connector:seedance_2_5` | yes | `end_image` | THE CLIP DOOR since 2026-09-22 (the owner: "let's just run with seedance for now, the output is just way better and takes less tweaking"). Takes the first frame (start_image), the last frame (end_image) and, on a talking scene, the voice slice (audio_references) TOGETHER on one call, up to 30 s — so a talking scene keeps its last frame, which the MiniMax door could not. 1080p at bitrate high: 12 cr/s live. |
| `higgsfield:api` | yes | `end_image_url` | the same house through its own API key pair — separate wallet |
| `byteplus:direct` | yes | `content[].role = last_frame` | the alternate. Explicit first_frame / last_frame roles; on this door the first/last-frame roles and omni_reference are mutually exclusive, so a talking beat there lands its last frame in the timeline's final beat instead. |

a scene has exactly two generated stills — the FIRST FRAME and the LAST FRAME. On a SILENT scene both are attached: start_image and end_image. On a TALKING scene the first frame is attached as image_references beside the audio and the last frame is NOT attached (the 422 of 2026-09-22) — its Change is the last beat's 'ending on …' words, and the submit sheet says so.

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `model` | **required** | the slug in providers.json providers.higgsfield-mcp.stations.motion | `None` | — |
| `prompt` | **required** | the assembled paragraph — asset line (@Image1 + @Image2), one-sentence summary, the timeline of beats settling on @Image2, the consistency notes | `None` | the scene's first frame, its beats and its last frame, in that order |
| `start_image` | **required** | an uploaded media id — a URL is rejected upstream (422 uuid_parsing) | `None` | the scene's FIRST FRAME |
| `end_image` | **required** | the scene's last frame — a real input on the settled door (role end_image) for a SILENT scene; never beside audio (the 422 of 2026-09-22) | `None` | the scene's LAST FRAME |
| `duration` | optional | 4–15 | `the scene's own length, read from vo/timing.json — ceil(the slice), floored at 4; past 15 the scene is refused (split at a beat, or the alternate door)` | the scene's slice of the one voice track |
| `aspect_ratio` | optional | auto · 21:9 · 16:9 · 4:3 · 1:1 · 3:4 · 9:16 | `the piece's Aspect` | the piece's Aspect |
| `resolution` | **required** | 2K only (1440×2560 at 9:16) | `2K` | fixed by the door — the piece's Resolution sizes the stills, not this clip |
| `batch_size` | optional | 1–4 | `None` | how many takes of the same call — not sent unless a run asks; a batch of 4 costs 4× |

**Assembly order:** assets → summary → timeline → consistency

the maker's own four blocks, in this order, assembled from the shared `clip_prompt` shape at the top of this file. (1) the asset line: what @Image1 and @Image2 are; (2) ONE clean summary sentence from labelled slots; (3) the timeline of beats, one verb each, spans off the one voice track, the first anchored on @Image1 and the last settling on @Image2; (4) what holds — the take, the setting, the light, the wardrobe, Nobody speaks, the negatives.

- **assets** — @Image1 is the first frame: <the first frame in one line>. @Image2 is the last frame: <the delta as a description>.
- **summary** — one sentence — who, where, what they do, the style, the camera
- **timeline** — 0-2.54s: … · 3.18-4.55s: … — one verb per beat, the spans read off the one voice track, the first beat naming the frame at @Image1 and the last settling on the framing of @Image2; a silent beat may carry the words playing over it
- **consistency** — One continuous take, no cuts, <the camera sentence>. Same <setting>, same <light>, same wardrobe throughout. No subtitles. No background music.

**The maker's limits.**

- `max_beats`: 15
- `max_beats_why`: the maker's own warning: a storyboard is better suited to 15 panels or fewer; past that the order drifts and frames go still
- `duration_seconds`: [4, 15]
- `duration_note`: the owner 2026-09-22: most scenes should be 4–6 seconds with a few frames/movements. A scene longer than 15 s is refused by rule 12: split at a beat, or route to the alternate door (seedance_2_5, up to 30 s)
- `one_verb_per_beat`: True
- `one_verb_why`: two short actions are stable, three or more drift — a beat that names two actions is two beats
- `no_high_frequency_action`: timestamps do not control repeated fast motion
- `refs`: {'images': 30, 'videos': 10, 'audio': 10, 'best': '1–5 subjects; stability decreases from 6'}
- `ceilings_from`: providers.json models[...].ceilings — text and labels garble, hands near a product merge, a product label must be reference-locked
- `frames_per_scene`: 2
- `frames_per_scene_why`: first and last only — the beats between them are written into the timeline, never generated as stills
- `min_beats`: 1
- `clip_media_roles`: ['start_image', 'end_image']
- `clip_media_roles_why`: EXACTLY these roles on a silent clip, and nothing else — the first frame as start_image, the last as end_image, no audio. A cast sheet or a style frame beside them is a second opinion about the same face, and the dry run that found this bug had sent both instead of the first frame (2026-09-18).
- `duration_from`: ceil(the scene's slice of the voice track), floored at the door's minimum (4). The ceiling (15) is NOT clamped — a paragraph past it is refused by name so the scene is split at a beat boundary or routed to the alternate door, never quietly shortened.
- `no_end_image_with_audio`: True
- `no_end_image_with_audio_why`: the backend's 422, verbatim: "start_image/end_image cannot be mixed with reference media; audio_references require at least one image or video reference."
- `resolution`: 2K only

**Our field → its field.**

| Ours | Where it lands |
|---|---|
| first_frame | start_image (the still made for it) and @Image1 in the asset line |
| last_frame | end_image (the still made as an edit of the first) and its own @Image2 asset line |
| camera | named in the beat only when it moves; otherwise once, in the summary |
| over | the words playing over that beat — {dialogue} where the door performs it, otherwise carried by the voice track at the edit |
| beat_emotion | the attitude word in the beat — never a pacing instruction |
| hold | the consistency block |
| beats | the timeline — one line per beat, its span from vo/timing.json, one verb, the camera only where it moves |

Read from: the Higgsfield connector's own model listing for the settled clip slug (models_explore), read live 2026-09-22

## talking — higgsfield

Model: `seedance_2_5` (read from providers.json, never written twice).

ONE clip per to-camera scene — the scene's whole paragraph, performed, from its first frame to its last, with the scene's slice of the one voice track attached as the audio it dubs.

| Door | Takes the last frame? | As | Note |
|---|---|---|---|
| `higgsfield:connector` | no | `—` | THE SETTLED DOOR (2026-09-22). A talking scene = image_references [the first frame] + audio_references [the voice slice], NO end_image — first/last frame and reference media cannot mix on this slug. The LAST FRAME is still made (the next scene opens from it) but travels as words: the last beat ends on its Change. Known cost: with no frame to land on the model may hold the final gesture longer (the bake-off's scene 1 held the hand up). |
| `higgsfield:connector:seedance_2_5` | yes | `end_image` | THE CLIP DOOR since 2026-09-22 (the owner: "let's just run with seedance for now, the output is just way better and takes less tweaking"). Takes the first frame (start_image), the last frame (end_image) and, on a talking scene, the voice slice (audio_references) TOGETHER on one call, up to 30 s — so a talking scene keeps its last frame, which the MiniMax door could not. 1080p at bitrate high: 12 cr/s live. |
| `higgsfield:api` | yes | `end_image_url` | the same house through its own API key pair — separate wallet |
| `byteplus:direct` | yes | `content[].role = last_frame` | the alternate. Explicit first_frame / last_frame roles; on this door the first/last-frame roles and omni_reference are mutually exclusive, so a talking beat there lands its last frame in the timeline's final beat instead. |

a scene has exactly two generated stills — the FIRST FRAME and the LAST FRAME. On a SILENT scene both are attached: start_image and end_image. On a TALKING scene the first frame is attached as image_references beside the audio and the last frame is NOT attached (the 422 of 2026-09-22) — its Change is the last beat's 'ending on …' words, and the submit sheet says so.

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `model` | **required** | the slug in providers.json providers.higgsfield-mcp.stations.talking | `None` | — |
| `prompt` | **required** | the assembled paragraph — asset line (@Image1 + @Audio1 only), one-sentence summary, the timeline of beats ending on the LAST FRAME's change in words, the consistency notes | `None` | the scene's first frame, its beats and its last frame, in that order |
| `image_references` | **required** | the FIRST FRAME's media id, and ONLY that — a cast sheet or a style frame beside it is a second opinion about the same face | `None` | the scene's FIRST FRAME |
| `audio_references` | **required** | one clip — the scene's slice, 2–15 s | `None` | the scene's slice of the one voice track — vo/<scene>.mp3 |
| `duration` | optional | 4–15 | `the scene's own length, read from vo/timing.json — ceil(the slice), floored at 4; past 15 the scene is refused (split at a beat, or the alternate door)` | the scene's slice of the one voice track |
| `aspect_ratio` | optional | auto · 21:9 · 16:9 · 4:3 · 1:1 · 3:4 · 9:16 | `the piece's Aspect` | the piece's Aspect |
| `resolution` | **required** | 2K only (1440×2560 at 9:16) | `2K` | fixed by the door — the piece's Resolution sizes the stills, not this clip |
| `batch_size` | optional | 1–4 | `None` | how many takes of the same call — not sent unless a run asks; a batch of 4 costs 4× |

**Assembly order:** assets → summary → timeline → consistency

the maker's own four blocks, in this order, assembled from the shared `clip_prompt` shape at the top of this file. (1) the asset line: what @Image1 and @Audio1 are — NO @Image2 on a talking scene, because this door takes no end_image beside audio; (2) ONE clean summary sentence from labelled slots; (3) the timeline of beats, one verb each, spans off the one voice track, the first anchored on @Image1 and the last ENDING ON the LAST FRAME's Change, in words; (4) what holds — the take, the setting, the light, the wardrobe, the lip line, the negatives.

- **assets** — @Image1 is the first frame: <the first frame in one line>. @Audio1 is <who>'s voice; they speak the words in @Audio1 exactly, their lips moving with every word, nothing else is said.
- **summary** — one sentence — who, where, what they do, the style, the camera
- **timeline** — 0-2.54s: … · 3.18-4.55s: … — one verb per beat, the spans read off the one voice track, the first beat naming the frame at @Image1 and the last ending on <the LAST FRAME's Change, in words>; no beat restates the words, because they arrive as attached audio
- **consistency** — One continuous take, no cuts, <the camera sentence>. Same <setting>, same <light>, same wardrobe throughout. Natural lip movement matching the voice. No subtitles. No background music.

**The maker's limits.**

- `max_beats`: 15
- `duration_seconds`: [4, 15]
- `audio_clip_seconds`: [2, 15]
- `audio_clip_mb`: 15
- `one_verb_per_beat`: True
- `line_parity`: every talking clip is transcribed and compared to its paragraph before it ships — lip-sync to the wrong words is a FLAG
- `ceilings_from`: providers.json models[...].ceilings
- `frames_per_scene`: 2
- `frames_per_scene_why`: first and last only — the beats between them are written into the timeline, never generated as stills
- `min_beats`: 1
- `clip_media_roles`: ['image_references', 'audio_references']
- `clip_media_roles_why`: EXACTLY these roles on a talking clip, and nothing else. The first frame rides as image_references (it cannot be start_image beside audio — the 422); the slice as audio_references; NO end_image. A cast sheet or a style frame beside the first frame is a second opinion about the same face.
- `duration_from`: ceil(the scene's slice of the voice track), floored at the door's minimum (4). The ceiling (15) is NOT clamped — a paragraph past it is refused by name so the scene is split at a beat boundary or routed to the alternate door, never quietly shortened.
- `duration_note`: the owner 2026-09-22: most scenes should be 4–6 seconds with a few frames/movements. A scene longer than 15 s is refused by rule 12: split at a beat, or route to the alternate door (seedance_2_5, up to 30 s)
- `no_end_image_with_audio`: True
- `no_end_image_with_audio_why`: the backend's 422, verbatim: "start_image/end_image cannot be mixed with reference media; audio_references require at least one image or video reference."
- `resolution`: 2K only
- `last_frame_lands_in_words`: True
- `last_frame_lands_in_words_why`: no end_image on a talking call, so the timeline's last beat ends on the LAST FRAME's Change, said in words; the model decides where it lands — the awkward hold (scene 1 of the bake-off) is the cost, and a scene that must land an exact frame goes silent or to the alternate

**Our field → its field.**

| Ours | Where it lands |
|---|---|
| first_frame | image_references (the still made for it) and @Image1 in the asset line |
| voice_paragraph | audio_references — the scene's slice, never the whole track |
| last_frame | still MADE (the next scene opens from it) but NOT attached — this door takes no end_image beside audio; its Change becomes the last beat's 'ending on …' words |
| beat_emotion | the attitude word in the beat |
| to_camera | the shape — image_references + audio_references, no end_image |
| beats | the timeline — one line per beat, its span from vo/timing.json, one verb, the camera only where it moves |

Read from: the Higgsfield connector's own model listing for the settled clip slug (models_explore), read live 2026-09-22

## voice — direct:elevenlabs

ONE continuous track for the whole piece — every scene's paragraph spoken in order, stitched request to request so the read never restarts, then sliced per scene for the talking door

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `text` | **required** | one chunk — one scene's paragraph | `None` | the scene's Voice paragraph, byte-identical to the script |
| `model_id` | optional | eleven_v3 · eleven_multilingual_v2 | `eleven_v3` | — |
| `previous_request_ids` | optional | the request ids of the up-to-3 most recent chunks, read from each response's `request-id` header | `carried automatically, chunk to chunk` | the scene order — this is what makes one read instead of many |
| `previous_text / next_text` | optional | the adjacent text | `None` | — |
| `voice_settings` | optional | stability · similarity_boost · style · use_speaker_boost · speed | `whatever the character's voice.json carries` | the character's own voice record |
| `apply_text_normalization` | optional | auto · on · off (API default auto) | `off` | pinned — machine/spoken_numbers.py has already said every figure in words (spoken-rules.json), so ElevenLabs' own guess is switched off |
| `seed` | optional | any | `1` | pinned — every chunk of a read sends the same seed; a remake of a scene sends seed + the remake number, recorded in timing.json |
| `language_code` | optional | ISO 639-1 | `None` | — |
| `pronunciation_dictionary_locators` | optional | dictionary id + version on the ElevenLabs account | `None` | — not used: the brand's protected words are swapped into the text before the call (machine/lexicon.py, brands/<brand>/brand-identity/voice/pronunciation.json) |

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

Read from: https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps · https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries · https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/request-stitching

## sfx-generate — direct:elevenlabs

ONE row of the SFX bank (tools/video-production/banks/sfx) — a cue or a room-tone bed, made once and reused forever. machine/make_bank.py builds the call from the row; --dry-run only until a spend is approved (2026-09-23).

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `text` | **required** | a description of the sound | `None` | the bank row's `prompt` |
| `duration_seconds` | optional | 0.5–30 | `None` | the bank row's `seconds` |
| `prompt_influence` | optional | 0–1 | `0.3` | — |
| `loop` | optional | true · false (eleven_text_to_sound_v2 only) | `False` | the bank row's `loop` — true on every room-tone bed |
| `model_id` | optional | eleven_text_to_sound_v2 | `eleven_text_to_sound_v2` | — |
| `output_format (query)` | optional | mp3_44100_128 · pcm_* · opus_* … | `mp3_44100_128` | — |

**Assembly order:** text

The row's prompt, verbatim. Nothing else is written into it.

Read from: https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert

## music-compose — direct:elevenlabs

ONE row of the music bank (tools/video-production/banks/music) — an instrumental bed tagged energy · tempo · mood, made once and reused forever. machine/make_bank.py builds the call from the row; --dry-run only until a spend is approved (2026-09-23).

| Field | Req? | Values | House default | What fills it |
|---|---|---|---|---|
| `prompt` | **required** | a description of the track | `None` | the bank row's `prompt` (energy, mood and BPM written into it) |
| `music_length_ms` | optional | 3000–600000 | `None` | the bank row's `seconds` × 1000 |
| `force_instrumental` | optional | true · false | `True` | — a bed sits under a voice; it never sings |
| `model_id` | optional | music_v1 · music_v2 · music_v2_5 | `music_v1` | — |
| `output_format (query)` | optional | mp3_44100_128 · pcm_* · opus_* … | `mp3_44100_128` | — |

**Assembly order:** prompt

The row's prompt, verbatim. Never a named commercial track.

Read from: https://elevenlabs.io/docs/api-reference/music/compose

## The picture rules — said in every still that qualifies

| Rule | Applies to | The words sent | Why |
|---|---|---|---|
| viewpoint | the scene's `to_camera` is false AND the first frame shows no face (its `who` names hands / the product, or its subject says no face) | whose eyes the camera is + which frame edge every limb enters from + elbows off-frame | the body geometry is the one thing a still description leaves to chance when there is no face to anchor it; said in words it is decided, not invented (live 2026-09-22) |
| first_instant | every FIRST FRAME still | This picture is the first instant only: anything the scene does later, such as a hand that comes in on a later line, is not in it yet. | the three-doctors run QC, 2026-10-02: the opening still read the scene's later movement ('her right hand entering … on the second line') as already done, so the hand was up at her collar in the first frame. |
| wardrobe_in_words | every still with a person who wears a named look | {who} wears {outfit} ({continuity}), exactly as in the outfit reference — their face reference is for the face only, not the clothes. | the three-doctors run QC, 2026-10-02: with only the look sheet attached, 8 of 22 pictures put Nova in her master photo's plain T-shirt instead of the scene's look. |
| product_label | every still that carries the real packshot | The product's label reads exactly as the packshot, letter for letter: {label_lock}. | the three-doctors run QC, 2026-10-02: a tube came back labelled 'PASHIDA'. |
| endcard | an endcard showing more than one person | Equal panels, one person per panel, each exactly the same width; each person in their own place from the ad, never one shared room; the top fifth of the picture left as calm plain background for the words set in the edit; every face inside the middle 4:5 area. | the three-doctors run QC, 2026-10-02: the three-doctor endcard came back with a wider middle panel, all three in one generic room, and its word band outside the 4:5 zone. |
| swipe_camera | every first frame, card plate or own picture that copies a swipe shot | The FIRST reference image is the swipe shot this picture copies, blurred on purpose. Copy from it exactly: where the camera is, its height and angle, how close it is, the framing and crop, where each person and hand sits in the frame, where the light comes from, how hard or soft it is and its colour, the shading and shadows it throws on faces, necks, hands and clothes, how bright the picture is, and its camera look. Where any position written above disagrees with it, the swipe shot wins. Take nothing else from it: the people, faces, clothes, words and room details come from the other references and the words above. | the owner, 2026-10-02: 'literally look like the swipe … this is what makes it indistinguishable from AI'. THE RECIPE he confirmed the same day ('literally everything looks perfect now. Even the dark spots are on the right side of her face'): GPT Image 2.5 — the ruled still model — with this blurred shot first and the written framing dropped. A switch to Nano Banana Pro with a sharp guide and a face pass, made by a session without his ruling, came out wider, posed and pasted-in; it is withdrawn. Shadows added the same day — the owner: 'we're now missing some of the shading and shadows that are present in the actual swipe shot … we need to account for all these little things'. 'Camera look', not 'phone-camera look': the look is the swipe's own, real or stylised. |
| face_check | every still with one of our people in it — a CHECK only, it changes nothing | Image 1 is the REFERENCE photo of one person. Image 2 is a picture we made. Find the person in image 2 who is meant to be this person (same gender, the role they play). Is it the SAME individual as image 1? Compare feature by feature: face shape and length, eye shape and colour, nose bridge and tip, lips, jawline and chin, hairline, hair colour, length and parting, and age. Clothes, light, angle and expression do not matter. Be strict: her own family must be certain it is her. If ANY feature is noticeably different, or it only looks like the same type of person, the answer is DIFFERENT. If this person is not in image 2 at all, answer ABSENT. Answer JSON only: {"verdict": "SAME" | "DIFFERENT" | "ABSENT", "why": "one short sentence"} | the same ruling: nothing reaches the owner with a made-up person in it. |
| product_scale | every still that carries the real packshot | The product is its real size and shape: exactly the packshot's proportions, and as big against the hand and face as a real one is — a hand-held product sits inside one hand and is never larger than the hand holding it, the same size as in the ad's other pictures. In a close-up the camera moves closer; the product does not grow. | the owner, 2026-10-02, Round 1: Section 21's tube came out wider than her palm and nearly hand-length — 'that bottle size is not correct … compare against all the other face scrub bottles used in the generation, and also look at the actual pack shot'. Only the label was ruled; nothing ruled the size. |
| first_frame_kept | every clip that starts from an approved picture | @Image1 is the first frame. Keep it exactly as it is: the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing in it is re-staged, re-framed or zoomed. | 2026-10-02, Nova Section 1: the clip prompt restated the brief's framing ('close-up', 'a blank lettering band') over the approved picture; Seedance followed the words and zoomed in. The picture carries the composition; the words carry only what changes (the same rule as pictures, where the swipe shot carries the camera and the written composition is dropped). |
| swipe_motion | a clip of a section the storyboard makes by motion transfer (the swipe's own movement). On the ruled route (Omni on fal, providers.json direct.omni_route, 2026-10-03) only a clip with NOBODY OF OURS ON SCREEN gets the blurred footage: a person on screen is image-to-video from the approved picture, the movement said in words, and every clip of the section starts from the approved picture, never a clip's last frame (ruling_2026_10_03_no_handoffs). The @Video1 wording below is the legacy door's (clips_plan.py, --legacy-clips) | @Video1 is a blurred clip used ONLY for movement: copy how the camera moves (a handheld phone drifting and bobbing with the arm that holds it, or a held tripod frame, exactly as it moves there), how every person and hand moves, where each touch lands, and the timing and rhythm of each movement. Take nothing else from @Video1: no person, face, hair, clothes, sign, words, captions or place from it; everything you see comes from @Image1 and the words above. | the storyboard's motion-transfer sections (storyboard_plan.MAKERS 'B-over'): 'the swipe's own clip drives the movement, rebuilt with our people, look and place from the locked elements and our start frame'. The same recipe as swipe_camera for pictures: the swipe carries the material, our references carry the people. |
| card_plate | every card plate | No added text anywhere in the picture: no words, letters, numbers, prices or captions laid over it, and clear empty space left where the words will be set later. Any printed label on a real product stays exactly as its reference shows it. The plate's surface (a receipt, a screen, a page) is framed exactly as the swipe's own card is, and nothing holds it — no hand, no fingers, no person — unless the brief's plate sentence says so. Natural colour, never posterised. | the three-doctors run QC, 2026-10-02: both receipt cards came back as a small receipt held in a hand, one posterised into psychedelic colour; the swipe's receipt fills the frame. Framing follows the swipe's card (2026-10-02 QC: the swipe's receipt is a strip across the middle with black above and below). |
