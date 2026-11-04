# Model Input Sheets (the owner)

Mirror of the artifact page *Model Input Sheets* (27 Oct 2026). Generated from `components/model-inputs/inputs/*.json` by the same script as the page; every sheet is **draft**, nothing is approved. Each rule carries its source beside it.

Maker sources are the makers' own pages where they exist; where the maker publishes nothing (Genjutsu object swap, Suno's limits) the sheet says so and the rule rests on our own 18 Oct findings or on community-tested figures.

## Genjutsu motion control — The clip maker

**For the sale ad.** Makes the sale-ad clip: her scene still moves the way the money reel moves. Her face and look come from her baseline, the room and the real tube are already in the still, and the reel gives only the movement. Check the tube in every clip, because the maker says props can be dropped.

*14 inputs · 11 structure rules · 10 avoid · 5 qualities · registry id `higgsfield-motion-control` · medium video · status draft · read 2026-10-27*

### Limits

- duration seconds: 3, 30
- max images: 1
- max videos: 1
- image formats: jpg, jpeg, png, webp
- max image mb: 10
- min image edge px: 340 (Kling guide, video: short edge at least 340, long edge up to 3850); 720 on the ComfyUI door; 300 short edge on Kling's own character-image rule
- video formats: mp4, mov, webm, m4v
- max video mb: 100
- reference video seconds: 3 to 30 (Kling); 30 only when the character follows the VIDEO, 10 when it follows the IMAGE (ComfyUI, Runway)
- output length: equals the reference video's length; if the motion is fast or complex it can come back shorter, never under 3 s of continuous motion extracted, and the credits are not refunded (Kling)
- resolutions: 480p, 720p, 1080p
- kling motion control: {"mode": ["std", "pro"], "background_source": ["input_image", "input_video"], "character_orientation": ["video", "image"]}
- output shape: comes back at the stills' own shape (834x1112, 3:4, from a 4:5 still): scale it back, never crop (a crop left the original caption peeking out) (ours, 18 Oct)
- price credits per second: Kling 3.0 Standard 9, Professional 12; Kling 2.6 Standard 5, Professional 8 (Kling's own door; Higgsfield bills in its credits)
- house: resolution: 480p, upscaled locally
- house: aspect: 9:16 from the jump (the scene still is made 9:16, the swipe is 9:16)
- house: person: the cast member's BASELINE built into a scene still (headshot, look, details, expressions); never the master (the owner, 2026-10-27)
- house: orientation: video (follow the swipe's movement and camera)

### Qualities

std, pro, 480p, 720p, 1080p

### Inputs

| Input | Use | What it is | Allowed | What we send | Source |
|---|---|---|---|---|---|
| image_references | yes | The ONE scene still: the person from her baseline, standing in her room, the real product in the frame. It is both the character and the world. | one picture (jpg, png or webp, under 10 MB); whole body and head visible; arms and hands visible; room to move | the approved scene still made 9:16 on GPT Image 2.5 from the BASELINE (headshot, look, details, expressions) + her room + the real product photo; never the master, never a studio sheet | <https://kling.ai/quickstart/motion-control-user-guide>; <https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-kling>; `components/model-inputs/VIDEO-PATH-owner.md` |
| video_references | yes | The swipe video whose movement is copied: timing, gesture, expression and (in video orientation) camera move. | one video, 3 to 30 s, mp4/mov/webm/m4v under 100 MB, short edge at least 340 px, one continuous shot, one person | the swipe's one clean shot cut on the frame map's boundaries, 9:16 | <https://kling.ai/quickstart/motion-control-user-guide>; <https://docs.comfy.org/tutorials/partner-nodes/kling/kling-motion-control/workflow> |
| character_orientation | yes | Whether the output follows the video's orientation and camera or the still's. | video (up to 30 s; best for whole-body action) or image (up to 10 s; best for portraits with camera moves set in words) | video: the swipe's movement and camera are the point | <https://docs.comfy.org/tutorials/partner-nodes/kling/kling-motion-control/workflow>; <https://kling.ai/quickstart/motion-control-user-guide> |
| mode / tier | yes | Standard (about 720p) for tests, Professional (1080p) for fast hands and finer detail. | std or pro | std for the first take; pro only for a shot with fast hands that failed on std | <https://docs.comfy.org/tutorials/partner-nodes/kling/kling-motion-control/workflow>; <https://kling.ai/quickstart/motion-control-user-guide> |
| resolution | yes | Output size tier on the Higgsfield door. | 480p, 720p, 1080p | 480p, upscaled locally | <https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-kling>; `components/generative-model-house/MODEL-HOUSE.md` |
| background_source | yes | Which input gives the background: the still or the swipe video. | input_image or input_video | input_image: the room is already in our scene still, so the swipe's place never shows | <https://kling.ai/quickstart/motion-control-user-guide>; `tools/video-production/SHOT-ROUTES.md` |
| prompt | maybe | Words for the background and details not covered by the motion or the still (an outfit, an added thing, the environment). | free text; the maker gives no length limit | short: keep the still's room and product, no new objects; or empty | <https://kling.ai/quickstart/motion-control-user-guide>; <https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-kling> |
| keep_original_sound | no | Keep the reference video's own sound in the output. | boolean | false: the swipe's sound is not ours; voice and music are laid in at the edit | <https://docs.comfy.org/tutorials/partner-nodes/kling/kling-motion-control/workflow> |
| face reference / Element Library (Kling 3.0) | no | A separate face binding from clear close-ups (front plus side views). | facial information only; it does NOT carry clothing, hairstyle, makeup or props; binds only when the character's orientation matches the video's | not used: the face comes from the scene still | <https://kling.ai/quickstart/motion-control-user-guide> |
| duration | no | Length of the clip. | not set by you: it follows the reference video, 3 to 30 s | the swipe shot's own length (about 2 to 5 s per shot), cut to the frame map | <https://kling.ai/quickstart/motion-control-user-guide> |
| seed | no | Repeat a result. | not documented by the maker for this model | not sent | <https://kling.ai/quickstart/motion-control-user-guide> |
| mask / region | no | Mark an area to change. | none on this model | not available: a fix is a new still or a new run | <https://kling.ai/quickstart/motion-control-user-guide> |
| audio / voice reference | no | A voice for lip-sync. | none: motion control copies the swipe's mouth movement, it does not take our line | not available: our line is laid under the clip at the edit | <https://kling.ai/quickstart/motion-control-user-guide>; `tools/video-production/SHOT-ROUTES.md` |
| aspect ratio | yes | The picture shape. | not chosen: it follows the still; match the still's and the video's aspect (both 9:16) | 9:16 both | <https://docs.comfy.org/tutorials/partner-nodes/kling/kling-motion-control/workflow> |

### Rules that work

- Make the whole scene as ONE still first: the person, her room and the product in the frame. The motion model only moves what the still shows. — `components/model-inputs/VIDEO-PATH-owner.md`
- The person in the still is built from the cast BASELINE (headshot, look, details, expressions), never the master. — `components/model-inputs/VIDEO-PATH-owner.md (the owner 2026-10-27); machine/swipe_swap_job.py`
- The swipe video drives only the movement: timing, gesture, expression and camera. The person, the room and the product do not come from it. — <https://kling.ai/quickstart/motion-control-user-guide>
- Build the person inside the shot's own look (same pose, light, contact shadows, depth of field, grain); a studio sheet laid in reads as pasted on. The photo look is the swipe's, never cleaner. — `tools/video-production/VIDEO-RULINGS.md V38, V52`
- Match the still's framing to the video's: whole body with whole body, half body with half body, close-up with close-up. Same aspect on both. — <https://kling.ai/quickstart/motion-control-user-guide>; <https://docs.comfy.org/tutorials/partner-nodes/kling/kling-motion-control/workflow>
- The still must show every limb the motion needs, arms and hands included, with clear space around the body for large movement. — <https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-kling>; <https://kling.ai/quickstart/motion-control-user-guide>
- One continuous shot, one person, no cuts, camera movement or obstructions in the reference; if two people are present the larger is used. Cut the swipe at its cuts and run one shot at a time. — <https://kling.ai/quickstart/motion-control-user-guide>; `tools/video-production/VIDEO-RULINGS.md V39`
- Steady, moderate movement works best. Fast gestures smear in the source and again in the model: blur the source first and check fast hands in QC; use pro for a fast-hands shot. — <https://kling.ai/quickstart/motion-control-user-guide>; `tools/video-production/VIDEO-RULINGS.md V38 to V41 (18 Oct)`
- A prop is carried only if it is in the scene still, and the maker says face binding drops props, so check the product in every clip: whole, same size, not melted. If it did not survive, the product is laid in from the real photo at the edit. — <https://kling.ai/quickstart/motion-control-user-guide>; `tools/video-production/SHOT-ROUTES.md`
- The result comes back at the still's own shape; scale it back to 9:16, never crop it. — `tools/video-production/VIDEO-RULINGS.md (18 Oct)`
- Check the face against the baseline before a clip is kept; motion control exists because object swaps kept the original face (9 of 9 swaps kept it, 9 of 9 transfers carried ours). — `tools/video-production/SHOT-ROUTES.md`

### Avoid

- Building the still from the master instead of the baseline. — `components/model-inputs/VIDEO-PATH-owner.md`
- A person built on a grey studio backdrop: it reads pasted on. — `tools/video-production/VIDEO-RULINGS.md V38`
- Cropping the stretched output: the original caption shows at the edge. — `tools/video-production/VIDEO-RULINGS.md (18 Oct)`
- A reference video with cuts, shot changes or camera moves: it can be truncated. — <https://kling.ai/quickstart/motion-control-user-guide>; <https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-kling>
- Overly fast motion or a subject whose body or head is blocked. — <https://kling.ai/quickstart/motion-control-user-guide>
- More than one person in the reference: the largest in frame is used, not the one you meant. — <https://kling.ai/quickstart/motion-control-user-guide>
- Expecting our spoken line from motion control: it copies the swipe's mouth and carries no audio of ours. — `tools/video-production/SHOT-ROUTES.md`
- Assuming a prop in the still survives the motion: the maker says face binding drops props; the product is checked in every clip and never drawn. — <https://kling.ai/quickstart/motion-control-user-guide>; `tools/video-production/SHOT-ROUTES.md`
- Under 3 s of continuous motion in the reference: the run fails and the credits are not refunded. — <https://kling.ai/quickstart/motion-control-user-guide>
- A close-up still with a full-body video (or the reverse), or mismatched aspect ratios. — <https://kling.ai/quickstart/motion-control-user-guide>; <https://docs.comfy.org/tutorials/partner-nodes/kling/kling-motion-control/workflow>

## Genjutsu object swap — The fallback clip maker

**For the sale ad.** Used only if motion control fails: puts her into the reel's own shot. It replaces and never adds, so the tube on the counter must come from the scene still, not from this. She goes in from her baseline, never the master.

*10 inputs · 9 structure rules · 8 avoid · 5 qualities · registry id `higgsfield-object-swap` · medium video · status draft · read 2026-10-27*

### Limits

- duration seconds: 4, 30
- max images: 8
- max videos: 1
- resolutions: 480p, 720p, 1080p
- min shot seconds: a clean shot of at least about 2 s with no cut inside (ours); the model's minimum is 4 s, a shorter shot is played forward-back-forward to reach it and trimmed (ours, 18 Oct)
- price per second usd: from 0.159 (list 0.318) at Genjutsu; about 8.3 credits a second measured at 1080p (ours)
- maker documentation: Higgsfield publishes no step-by-step page for Object Swap; its blog describes the mode and a third-party guide tested it. Limits above the vendor's list are OURS, measured.
- house: resolution: 480p, upscaled locally (the house size)
- house: per_shot: one swap per shot, never one pass over a clip with cuts
- house: person: a cast member's BASELINE (headshot, look, details, expressions), never the master (the owner, 2026-10-27; replaces the earlier 'send the whole sheet' line)

### Qualities

480p, 720p, 1080p, lite 720p, lite 1080p

### Inputs

| Input | Use | What it is | Allowed | What we send | Source |
|---|---|---|---|---|---|
| video_references | yes | The swipe's own shot to take the motion and the scene from. | one video, a clean single shot, model minimum 4 s | one shot cut on the frame map's boundaries | <https://higgsfield.ai/blog/higgsfield-genjutsu>; `tools/video-production/SHOT-ROUTES.md` |
| image_references | yes | What goes in: the cast member's BASELINE pictures (headshot, look, details, expressions), or the product photo. | several pictures | the baseline pictures that fit the shot (headshot and look at least); never the master alone and never the master as the person | `components/model-inputs/VIDEO-PATH-owner.md`; `tools/video-production/machine/cast_swap.py` |
| prompt | yes | The standard swap words: who is replaced by whom, the before or after state, every accessory to remove. | text; the maker says presets can do the job with no prompt | the standard prompt (cast_swap.py prompt --state before/after) | <https://higgsfield.ai/blog/higgsfield-genjutsu>; `tools/video-production/CLAUDE.md` |
| resolution | yes | Output size. | 480p, 720p, 1080p | 480p | `vendor list: Higgsfield connector model list` |
| preset | no | A ready swap recipe (person, outfit, product). | Higgsfield presets | not used: the standard prompt is ours | <https://higgsfield.ai/blog/higgsfield-genjutsu> |
| target element | yes | Which single thing is replaced. | named in the prompt: one subject, outfit or product | one subject per run | <https://higgsfield.ai/blog/higgsfield-genjutsu>; <https://app.therundown.ai/guides/swap-the-product-and-keep-the-performance-with-higgsfield> |
| lite variant | no | Genjutsu Lite, a Kling 4.0 based swap. | 720p or 1080p | not used (only the v1.0 path is proven on our door) | `vendor list: Higgsfield connector model list` |
| audio | no | Our voice line. | none: the swap keeps the original mouth and sound | not available: a line of ours is laid under at the edit | `tools/video-production/SHOT-ROUTES.md` |
| mask | no | Mark the area to change. | none on this model | not available | `vendor list: Higgsfield connector model list` |
| duration | no | Length of the output. | follows the source shot; model minimum 4 s | the swipe shot's length, looped forward-back-forward when under 4 s | `tools/video-production/VIDEO-RULINGS.md V39` |

### Rules that work

- A swap replaces something that is already in the shot and never adds. Whatever must be on a counter, in a hand or on a wall has to be in the SOURCE shot already, or come from a scene still made first; the swap will not put it there. — `tools/video-production/SHOT-ROUTES.md`; <https://app.therundown.ai/guides/swap-the-product-and-keep-the-performance-with-higgsfield (the swapped prop did not land and the original stayed)>
- The cast member goes in from the BASELINE pictures, never the master. A swap given the master alone is a face swap; the baseline gives the face, the look, the details and the expressions the shot needs. — `components/model-inputs/VIDEO-PATH-owner.md (the owner 2026-10-27)`
- Split at the cuts and swap one shot at a time; a whole-clip pass missed people in 4 of 16 shots and put the wrong subject on the wrong person. — `tools/video-production/VIDEO-RULINGS.md V39`
- State the before and the after state from the brief; everything else, body included, stays identical. — `tools/video-production/CLAUDE.md`
- Name every accessory of the original that must go, not only a colour; a headwrap's tails survived when only its colour was removed. — `tools/video-production/VIDEO-RULINGS.md V38`
- A recast subject is built inside the shot's own light and look, not laid in from a studio sheet. — `tools/video-production/VIDEO-RULINGS.md V38`
- Every swap is checked against the baseline before it is kept; when the swap kept the original person's face, send the same shot to motion control instead (9 of 9 kept it). — `tools/video-production/SHOT-ROUTES.md`
- A shot under the 4 s minimum is played forward-back-forward and trimmed; trim the loop seam off. — `tools/video-production/VIDEO-RULINGS.md V39`
- Before a batch, find a clip and object pair that works reliably: try a different prop in the same source clip, hold the action fixed and compare at the same moment. — <https://app.therundown.ai/guides/swap-the-product-and-keep-the-performance-with-higgsfield>

### Avoid

- Expecting our line from a swap: it keeps the original mouth, so it carries no line of ours. — `tools/video-production/SHOT-ROUTES.md`
- Expecting it to add things: it replaces, never adds; the product goes only where the swipe already has something in hand. — `tools/video-production/SHOT-ROUTES.md`; <https://app.therundown.ai/guides/swap-the-product-and-keep-the-performance-with-higgsfield>
- One swap pass over a clip with several cuts. — `tools/video-production/VIDEO-RULINGS.md V39`
- Sending the master as the person: it is a face swap, and the baseline is the rule. — `components/model-inputs/VIDEO-PATH-owner.md`
- A shot shorter than the model's minimum without playing it forward-back-forward. — `tools/video-production/VIDEO-RULINGS.md V39`
- Removing an accessory by naming only its colour. — `tools/video-production/VIDEO-RULINGS.md V38`
- A studio-backdrop sheet as the only reference: it reads pasted on. — `tools/video-production/VIDEO-RULINGS.md V38`
- Keeping a swap without checking the face: 9 of 9 kept the original person. — `tools/video-production/SHOT-ROUTES.md`

## ElevenLabs Eleven v3 (speech) — Voice

**For the sale ad.** Speaks any line of hers, one line per read with a delivery tag. Pick the voice first, the tags only work if the voice can do them.

*11 inputs · 8 structure rules · 6 avoid · 3 qualities · registry id `eleven-v3` · medium voice · status draft · read 2026-10-27*

### Limits

- max prompt chars: 5000
- max prompt chars note: 5,000 comes from a third-party review only; ElevenLabs' own prompting page gives no number. Confirm before relying on it.
- min prompt chars advised: 250
- output formats: mp3 and pcm tiers (set by output_format)
- languages: 70+ (third-party review)
- house: reads: each line is its own read with that shot's delivery as an audio tag; never one long take for the whole piece
- house: voice: one custom voice per character (V4)

### Qualities

creative, natural, robust

### Inputs

| Input | Use | What it is | Allowed | What we send | Source |
|---|---|---|---|---|---|
| text | yes | The words to speak plus audio tags and punctuation for delivery. | text; very short prompts give inconsistent output, over 250 characters is encouraged | one line per read with its delivery tag | <https://elevenlabs.io/docs/best-practices/prompting> |
| voice_id | yes | Which voice. The maker calls this the most important parameter. | a voice from the library or our designed voice | the character's own voice | <https://elevenlabs.io/docs/best-practices/prompting>; `tools/video-production/VOICE-CHAIN.md` |
| model_id | yes | Which speech model. | eleven_v3 | eleven_v3 | <https://elevenlabs.io/docs/best-practices/prompting> |
| stability | yes | How much the read follows direction. Creative and Natural respond to tags; Robust reduces responsiveness. | creative, natural, robust | natural | <https://elevenlabs.io/docs/best-practices/prompting> |
| audio tags | yes | Bracketed delivery: emotions, [whispers], [sighs], [laughs], sound effects like [applause]. | short, clear tags matched to the voice | one tag per shot's delivery | <https://elevenlabs.io/docs/best-practices/prompting> |
| punctuation | yes | Ellipses add pauses and weight, capitals add emphasis, standard marks set rhythm. | plain text | used for pace | <https://elevenlabs.io/docs/best-practices/prompting> |
| language_code | no | Force a language. | ISO code | not sent: the text sets it | <https://elevenlabs.io/docs/best-practices/prompting> |
| seed | maybe | Repeat a read. | integer | not pinned: a bad read is remade | <https://elevenlabs.io/docs/best-practices/prompting> |
| output_format | yes | File type and rate. | mp3_44100_128 and others | mp3 | <https://elevenlabs.io/docs/best-practices/prompting> |
| text-to-dialogue | no | Several speakers in one call. | multi-speaker script | not used: each line is its own read | <https://elevenlabs.io/docs/overview/capabilities/text-to-dialogue> |
| SSML break tags | no | Timed pauses. | NOT supported on v3 | never sent | <https://elevenlabs.io/docs/best-practices/prompting> |

### Rules that work

- Each line is its own read with that shot's delivery as a tag; never one long take for the whole piece. — `tools/video-production/VOICE-CHAIN.md`
- Choose the voice first; a tag only works if the delivery already exists in the voice. A whisper tag fails on a loud voice. — <https://elevenlabs.io/docs/best-practices/prompting>
- Match tags to the voice's character: a serious voice does not respond well to playful tags. — <https://elevenlabs.io/docs/best-practices/prompting>
- Keep tags short, clear and about emotion, tone, pace or action; describe voice quality so it cannot be read as a sound cue. — <https://elevenlabs.io/docs/best-practices/prompting>
- Give it enough text; very short inputs are inconsistent. — <https://elevenlabs.io/docs/best-practices/prompting>
- Use ellipses for weight, capitals for emphasis and normal punctuation for rhythm instead of break tags. — <https://elevenlabs.io/docs/best-practices/prompting>
- For the most expressive read use Creative or Natural stability. — <https://elevenlabs.io/docs/best-practices/prompting>
- Write brand words and figures the way they are spoken; the text is the only lever. — `tools/video-production/SONG-CHAIN.md`

### Avoid

- SSML break tags: v3 ignores them. — <https://elevenlabs.io/docs/best-practices/prompting>
- Playful tags on a serious voice. — <https://elevenlabs.io/docs/best-practices/prompting>
- A Professional Voice Clone on v3 when clone quality matters: not fully optimised. — <https://elevenlabs.io/docs/best-practices/prompting>
- One long take for the whole piece. — `tools/video-production/VOICE-CHAIN.md`
- A one-word or very short prompt. — <https://elevenlabs.io/docs/best-practices/prompting>
- Tags the voice reads aloud because they read like speech. — <https://elevenlabs.io/docs/best-practices/prompting>

## ElevenLabs Voice Design (eleven_ttv_v3) — Voice design

**For the sale ad.** Builds her own voice once from her description and a real recording, then every line uses that voice.

*11 inputs · 6 structure rules · 4 avoid · 3 qualities · registry id `eleven-ttv-v3` · medium voice · status draft · read 2026-10-27*

### Limits

- voice description: required; the maker states no maximum
- text chars: 100, 1000
- reference audio: base64, eleven_ttv_v3 only; size limit not stated
- previews: returned as a list; maximum not stated
- house: rule: one custom voice per character, designed from the cast member's description and a real reference recording

### Qualities

quality (higher = better, less variety), guidance_scale 5 default, loudness 0.5 default

### Inputs

| Input | Use | What it is | Allowed | What we send | Source |
|---|---|---|---|---|---|
| voice_description | yes | The voice in words. | text, required; longer and more detailed at a low guidance scale | the cast member's age, tone, accent, pace, warmth | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |
| model_id | yes | Design model. | eleven_multilingual_ttv_v2 (default) or eleven_ttv_v3 | eleven_ttv_v3: the only one that takes a reference recording | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |
| reference_audio_base64 | yes | A real recording to steer the voice. | base64 audio, v3 only | the real reference recording | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |
| prompt_strength | maybe | Balance between the description and the reference: 0 almost no prompt, 1 almost no reference. | 0 to 1, v3 only | tuned per voice | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |
| text | yes | Sample text the preview speaks. | 100 to 1000 characters, or auto_generate_text true | a line in her register | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |
| guidance_scale | maybe | How closely to follow the description. | default 5; high values sound artificial or robotic | default | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |
| loudness | no | Output level. | -1 to 1, default 0.5, 0 is about -24 LUFS | default | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |
| seed | maybe | Repeat a voice. | integer; same seed and inputs give the same voice | pinned once a voice is chosen | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |
| quality | no | Better output, less variety. | number | default | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |
| should_enhance | no | AI expands the description. | boolean, default false | false: the words are ours | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |
| stream_previews | no | Return ids to stream. | boolean | false | <https://elevenlabs.io/docs/api-reference/text-to-voice/design> |

### Rules that work

- Design from a real reference recording on v3 so the voice has a human base. — <https://elevenlabs.io/docs/api-reference/text-to-voice/design>
- Prefer a longer, more detailed description at a low guidance scale over a short one at a high scale. — <https://elevenlabs.io/docs/api-reference/text-to-voice/design>
- Design the voice once and bank it; every later read uses that voice id. — `tools/video-production/VIDEO-RULINGS.md V4`
- Pin the seed once a preview is chosen so the voice can be rebuilt. — <https://elevenlabs.io/docs/api-reference/text-to-voice/design>
- Keep the sample text between 100 and 1000 characters. — <https://elevenlabs.io/docs/api-reference/text-to-voice/design>
- Listen to every preview and pick by ear; a 409 means a preview is still generating, retry. — <https://elevenlabs.io/docs/api-reference/text-to-voice/design>

### Avoid

- A high guidance scale: the voice turns artificial or robotic. — <https://elevenlabs.io/docs/api-reference/text-to-voice/design>
- A reference recording on the v2 design model: only v3 takes it. — <https://elevenlabs.io/docs/api-reference/text-to-voice/design>
- Sample text under 100 or over 1000 characters. — <https://elevenlabs.io/docs/api-reference/text-to-voice/design>
- Designing a new voice each run: the character changes. — `tools/video-production/VIDEO-RULINGS.md V4`

## ElevenLabs Music v2.5 — Music (connected)

**For the sale ad.** Makes the song for a sung ad from a section-by-section plan. The first section sets the sound for the whole song.

*12 inputs · 8 structure rules · 6 avoid · 3 qualities · registry id `eleven-music-v2.5` · medium music · status draft · read 2026-10-27*

### Limits

- duration seconds: 3, 600
- sections max: 30
- section seconds: 3, 120
- styles per section max: 50
- negative styles per section max: 50
- lines max house: 30
- chars per line max house: 200
- music length ms: 3000, 600000
- style language: styles must be English; lyrics may be any language
- house: context_adherence: high
- house: seed: 1
- house: format: mp3_44100_192
- house: level: -14 LUFS copy
- house: remake: once, seed + 1
- house: style: one ruled row from banks/music-styles/index.json, no free text

### Qualities

context_adherence low, context_adherence medium, context_adherence high

### Inputs

| Input | Use | What it is | Allowed | What we send | Source |
|---|---|---|---|---|---|
| composition_plan | yes | An ordered list of sections, each with its own length, styles and lyrics. | up to 30 sections of 3 to 120 s, 3 s to 10 min total; music_v2 or music_v2_5 | one section per song part, built mechanically from the brief | <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>; `tools/video-production/SONG-CHAIN.md` |
| prompt | no | A plain text brief for the whole piece. | text; mutually exclusive with a composition plan | not used: the plan is | <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans> |
| music_length_ms | no | Total length for a prompt call. | 3,000 to 600,000 | from the plan's sections | <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans> |
| model_id | yes | Which music model. | music_v2_5 (also music_v2) | music_v2_5 | <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans> |
| section text (lyrics) | yes | The words sung in a section. | text; curly braces for directions like {instrumental break}, never parentheses | the section's lines as sung, brand words swapped for say_as, figures in words | <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>; `tools/video-production/SONG-CHAIN.md` |
| positive_styles | yes | What the section should sound like. | up to 50, English; the first section sets genre and tone for the whole song, so 6 to 7 or more early | the ruled style row + BPM + the row's line for that section | <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>; `tools/video-production/SONG-CHAIN.md` |
| negative_styles | yes | What to keep out. | up to 50 per section, English | the style row's list | <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>; `tools/video-production/SONG-CHAIN.md` |
| duration_ms per section | yes | Length of each section. | 3,000 to 120,000 | seconds x 1000 from the brief | <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans> |
| respect_sections_durations | maybe | Follow section times strictly (true) or let quality win (false). | boolean; default strict | default | <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans> |
| context_adherence | yes | How closely to follow the plan. | low, medium, high (default high) | high | <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>; `tools/video-production/SONG-CHAIN.md` |
| seed | yes | Repeat a result. | integer | 1, then seed + 1 for the one remake | `tools/video-production/SONG-CHAIN.md` |
| output_format | yes | File type. | mp3_44100_192 and others | mp3_44100_192 | `tools/video-production/SONG-CHAIN.md` |

### Rules that work

- Use a composition plan for control; a plan and a text prompt cannot be mixed. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>
- The first section's styles set genre and tone for the whole piece: load it with 6 to 7 or more specific styles. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>
- Name what you hear ('warm acoustic guitar with light fingerpicking', '80 BPM'), not moods alone. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>
- Use negative styles liberally to keep unwanted sounds out. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>
- Put inline directions in curly braces inside the text, never parentheses. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>
- Every section 3 to 120 s, at most 30 sections, 10 minutes total; the house caps lines at 200 characters and 30 lines. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>; `tools/video-production/SONG-CHAIN.md`
- Every sung line must be a script line and every script line sung; the song is transcribed and each line must be heard at 0.75 or better. — `tools/video-production/SONG-CHAIN.md`
- A failed gate remakes ONCE with seed + 1, then stops naming the missing line. — `tools/video-production/SONG-CHAIN.md`

### Avoid

- Copyrighted names or content in styles: the plan is rejected as bad_composition_plan. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>
- Parentheses for inline directions. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>
- A plan and a prompt in one call. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>
- A thin first section: the whole song comes out generic. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>
- A free-text style instead of the ruled row. — `tools/video-production/SONG-CHAIN.md`
- Styles in another language. — <https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans>

## Suno (v5 / v5.5, by hand, no API) — Music (by hand)

**For the sale ad.** Not connected, so a person types it in. Style box is 4 to 7 descriptors, lyrics carry section tags, weirdness stays low for commercial work. The finished file still goes through the same words-heard check as any song ad.

*15 inputs · 12 structure rules · 11 avoid · 6 qualities · registry id `suno` · medium music · status draft · read 2026-10-27*

### Limits

- style box chars: about 1,000 on v5 / v5.5 (community-tested; Suno publishes no limits table); older v4 about 200; text past the limit is cut silently
- lyrics box chars: sources conflict: about 3,000 or up to 5,000; stay near 2,500
- title chars: about 100 (one third-party source)
- style descriptors: 3 to 5 simple, 8 to 15 detailed, about 20 maximum; sweet spot 4 to 7
- genres max: 3
- exclusions max: about 2 to 3
- syllables per line: 6, 10
- lines per section: 4 standard, 8 longer
- pipe stack max: 7
- voices upload seconds: 15, 240
- voices kept seconds: 120
- custom models: 6 tracks minimum, 3 per account (Pro or Premier)
- numbers are: community figures except the sliders, which are Suno's own help page; confirm in the app before a batch
- house: how: a person writes or approves the style and lyrics by hand; the finished file then goes through the same song gate as any song ad (words heard in order, last line finished)
- house: door: none: manual until an API door is ruled

### Qualities

weirdness 10-30 (safe), weirdness 50 (default), weirdness 70-100 (experimental), style influence 70-100 (strict), style influence 40-60 (specific tags), style influence 10-30 (loose)

### Inputs

| Input | Use | What it is | Allowed | What we send | Source |
|---|---|---|---|---|---|
| style of music | yes | The sound of the song: genre, tempo, mood, instruments, vocal, era. | comma-separated tags, about 1,000 characters; earlier tags weigh more | genre + BPM + mood + 2-3 instruments + vocal + era, 4 to 7 descriptors, front-loaded | <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>; <https://github.com/mttkllr/suno-field-guide>; <https://roo.beehiiv.com/p/suno-prompting> |
| lyrics | yes | The words sung, with section tags. | text with [Verse] [Chorus] style tags; never empty | the brief's song lines word for word, 6 to 10 syllables a line, 4 lines a section | <https://github.com/mttkllr/suno-field-guide>; <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>; `tools/video-production/formats/song-ad.md` |
| title | no | Song name. | about 100 characters | a plain working name | <https://roo.beehiiv.com/p/suno-prompting> |
| exclude styles | yes | What to keep out. | short list; more reliable than 'no X' in the style box; do not overload | 2 to 3 named recurring faults | <https://github.com/mttkllr/suno-field-guide>; <https://jackrighteous.com/en-us/blogs/guides-using-suno-ai-music-creation/advanced-suno-prompt-engineering-guide> |
| weirdness | yes | Safe to chaotic; 50 is the normal result. | 0 to 100 slider | 20 to 30 for a song ad (commercial, safe) | <https://help.suno.com/en/articles/6141377>; <https://github.com/mttkllr/suno-field-guide> |
| style influence | yes | How strictly the style box is followed. | 0 to 100 slider, loose to strong | 70 to 90 for vague tags, 40 to 60 for specific ones | <https://help.suno.com/en/articles/6141377>; <https://github.com/mttkllr/suno-field-guide> |
| audio influence | maybe | How much an uploaded audio steers the result (appears with an upload). | slider | only when a reference is uploaded | <https://help.suno.com/en/articles/6141377> |
| vocal gender | yes | Male or female voice. | set explicitly | set to the song's vocal | <https://github.com/mttkllr/suno-field-guide> |
| instrumental | no | No singing. | toggle, or [Instrumental] in the style box | off for a song ad | <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026> |
| model version | yes | Which engine. | v5, v5.5, earlier | v5 for steadiness; v5.5 is more expressive but can drift to generic pop mid-track | <https://github.com/mttkllr/suno-field-guide>; <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026> |
| Voices / Personas | no | A cloned or saved voice. | upload 15 s to 4 min (best 2 min kept); paid tier | not used unless a voice is ruled for the brand | <https://github.com/mttkllr/suno-field-guide> |
| Extend / Cover | maybe | Lengthen a song or re-sing it on another model. | tools in the app | generate on v5, then Cover on v5.5 if more expression is wanted | <https://github.com/mttkllr/suno-field-guide> |
| structure tags | yes | Section labels: Intro, Verse, Pre-Chorus, Chorus, Bridge, Break, Solo, Build, Outro, End. | in the lyrics box; [Instrumental Break] is more reliable than [Bridge] | one per section; Bridge and Outro once each | <https://github.com/mttkllr/suno-field-guide>; <https://roo.beehiiv.com/p/suno-prompting> |
| vocal tags | yes | [Male Vocal] [Female Vocal] [Whisper] [Falsetto] [Choir] [Harmonies]. | either box; a mid-song change goes in the lyrics just before that section | style box for the main vocal, lyrics for a change | <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026> |
| BPM | yes | A numeric tempo anchor. | number, always with a mood word | from the ruled style row | <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026> |

### Rules that work

- Style box order: genre, tempo, mood, instruments, vocal style, era, reference. Put what matters most first. — <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>
- Use 4 to 7 descriptors; cut any two that say the same thing; stacking 15 or more dilutes it. — <https://roo.beehiiv.com/p/suno-prompting>; <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>
- One primary genre plus one modifier, three at most; strong genres (pop, rock, electronic) override weak ones (grunge, math rock, swing). — <https://github.com/mttkllr/suno-field-guide>
- Name specific instruments, two or three core textures only. — <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>
- Give BPM as a number and always pair it with a mood word. — <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>
- Put a section tag over every part of the lyrics; without them the whole song sits at one energy. — <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>; <https://github.com/mttkllr/suno-field-guide>
- Set the main vocal in the style box and the gender explicitly; use the lyrics box for a change within the song. — <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>; <https://github.com/mttkllr/suno-field-guide>
- Use the Exclude field for unwanted traits rather than 'no X' in the style box, and keep it to two or three. — <https://github.com/mttkllr/suno-field-guide>
- Move one slider at a time; weirdness low for commercial work; style influence high when the tags are vague. — <https://github.com/mttkllr/suno-field-guide>; <https://help.suno.com/en/articles/6141377>
- Write 6 to 10 syllable lines and 4-line sections; shorter lyrics make shorter songs, use Extend for length. — <https://github.com/mttkllr/suno-field-guide>
- When a take misses, change one thing before regenerating; the same prompt again gives the same result. — <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>
- Whatever Suno makes goes through the same song gate as any song ad: every script line heard in order, last line finished. Suno may sing words the lyrics do not hold. — `tools/video-production/SONG-CHAIN.md`

### Avoid

- Short poetic lines, ALL CAPS phrases or quotes in the style box: they get sung. — <https://github.com/mttkllr/suno-field-guide>
- An empty lyrics box. — <https://github.com/mttkllr/suno-field-guide>
- 'Don't' or 'no X' phrasing inside the style box. — <https://github.com/mttkllr/suno-field-guide>
- Contradictory tags such as calm with aggressive, or more than three genres. — <https://roo.beehiiv.com/p/suno-prompting>; <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>
- A BPM with no mood word. — <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>
- Putting the vocal style only in the lyrics box. — <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>
- More than three or four instruments. — <https://roo.beehiiv.com/p/suno-ai-prompts-that-actually-work-in-v5-5-2026>
- Relying on 'ethereal', 'crescendo' or 'realistic', and on chorus modifiers: they are often ignored or overridden. — <https://github.com/mttkllr/suno-field-guide>
- More than about seven elements in one pipe-stacked tag, or Bridge/Outro/Build used more than once. — <https://github.com/mttkllr/suno-field-guide>
- Trusting v5.5 to hold the style the whole way: it can drift to generic pop or change when extended. — <https://github.com/mttkllr/suno-field-guide>; <https://roo.beehiiv.com/p/suno-prompting>
- Naming a living artist as the style: the song-ad style is a ruled row, no free text. — `tools/video-production/SONG-CHAIN.md`

## Real-ESRGAN (local video upscale) — Upscale (first choice)

**For the sale ad.** Makes the 480p clip sharp for 1080x1920 on this Mac. Leave face enhancement off so her face stays the approved one.

*9 inputs · 5 structure rules · 4 avoid · 4 qualities · registry id `real-esrgan` · medium upscale · status draft · read 2026-10-27*

### Limits

- native scale: 4
- outscale: any final factor; the model runs x4 and resizes
- tile default: 0
- precision default: fp16
- formats: png, jpg, webp
- house: use: the first upscaler: a 480p clip is made, then upscaled locally to 1080x1920
- house: alternate: bytedance-upscaler-video

### Qualities

x4plus, animevideov3, fp16, fp32

### Inputs

| Input | Use | What it is | Allowed | What we send | Source |
|---|---|---|---|---|---|
| input frames/video | yes | What is upscaled. | frames (jpg, png, webp) or a video through inference_realesrgan_video.py | the kept 480p take | <https://github.com/xinntao/Real-ESRGAN> |
| model_name | yes | Which weights. | RealESRGAN_x4plus (general), realesr-animevideov3 (animation video) | RealESRGAN_x4plus for live-action looking clips | <https://github.com/xinntao/Real-ESRGAN> |
| outscale | yes | Final factor. | number; model runs x4 then resizes | to 1080x1920 from 480p | <https://github.com/xinntao/Real-ESRGAN> |
| tile | maybe | Split a frame to save memory. | 0 = off; tiling can leave block seams | 0 unless memory fails | <https://github.com/xinntao/Real-ESRGAN> |
| face_enhance | no | GFPGAN face restoration. | boolean, off by default | off: it changes the cast member's face | <https://github.com/xinntao/Real-ESRGAN> |
| fp32 | no | Full precision. | boolean, default fp16 | off | <https://github.com/xinntao/Real-ESRGAN> |
| ext | yes | Output type. | auto, jpg, png | png frames then encode | <https://github.com/xinntao/Real-ESRGAN> |
| frame rate | yes | Keep the clip's rate. | set at encode | unchanged (V40: probed, chosen) | `tools/video-production/VIDEO-RULINGS.md V40` |
| denoise strength | no | Blend of the general model. | listed for the general-wdn model in the repo docs | not used | <https://github.com/xinntao/Real-ESRGAN> |

### Rules that work

- Generate at 480p and upscale locally; the upscaler adds pixels, not new content. — `components/generative-model-house/MODEL-HOUSE.md (generate at 480p, upscale locally)`
- Use realesr-animevideov3 for animated footage; x4plus for general. — <https://github.com/xinntao/Real-ESRGAN>
- Tile only when memory fails, knowing seams can appear. — <https://github.com/xinntao/Real-ESRGAN>
- Leave face enhancement off: it changes a face the face gate already approved. — <https://github.com/xinntao/Real-ESRGAN>; `face gate`
- Check the upscaled clip for smoothing of grain and text; the swipe's grain is part of the look. — `tools/video-production/VIDEO-RULINGS.md V38`

### Avoid

- GFPGAN on a cast member. — <https://github.com/xinntao/Real-ESRGAN>
- Upscaling a take that is not yet kept. — `MODEL-HOUSE.md`
- Assuming the NCNN build supports every Python option such as outscale. — <https://github.com/xinntao/Real-ESRGAN>
- Adding grain or a filter after upscaling to fix a smooth look. — `tools/video-production/VIDEO-RULINGS.md V38`

## ByteDance video upscaler (Higgsfield) — Upscale (alternate)

**For the sale ad.** The backup upscaler on Higgsfield. Treat 4K as the ceiling; the 8K claim is unconfirmed.

*8 inputs · 5 structure rules · 4 avoid · 3 qualities · registry id `bytedance-upscaler-video` · medium upscale · status draft · read 2026-10-27*

### Limits

- target resolutions: 1080p, 2k, 4k
- higgsfield claims up to: 8K for video (Higgsfield help page); the upstream API stops at 4K and errors above it: the two disagree, so 4K is the safe ceiling
- input resolutions: 480p, 720p, 1080p
- frame rate max: 60
- formats: mp4, mov, webm, m4v, gif
- typical time: 1 to 5 minutes
- max duration: not stated by any source
- house: use: the alternate when local Real-ESRGAN is not good enough

### Qualities

1080p, 2k, 4k

### Inputs

| Input | Use | What it is | Allowed | What we send | Source |
|---|---|---|---|---|---|
| video | yes | The clip to upscale. | mp4, mov, webm, m4v, gif | the kept take | <https://replicate.com/bytedance/video-upscaler>; <https://fal.ai/models/fal-ai/bytedance-upscaler/upscale/video/llms.txt> |
| target_resolution | yes | Output size. | 1080p, 2k, 4k (Higgsfield also lists 8K, unconfirmed upstream) | 1080p for a 9:16 ad | <https://fal.ai/models/fal-ai/bytedance-upscaler/upscale/video/llms.txt>; <https://higgsfield.ai/creator-hub/help-center/troubleshooting/my-video-upscale-is-stuck-or-failed-what-should-i-do> |
| frame rate | maybe | Output rate (up to 60 fps). | up to 60 fps | keep the clip's own rate | <https://replicate.com/bytedance/video-upscaler> |
| preset / detail tuning | maybe | Preset-tuned detail for video. | Higgsfield presets | default | <https://higgsfield.ai/creator-hub/help-center/troubleshooting/my-video-upscale-is-stuck-or-failed-what-should-i-do> |
| scale factor | maybe | Options depend on the selected model. | set on the door | the one that reaches 1080p | <https://higgsfield.ai/creator-hub/help-center/troubleshooting/my-video-upscale-is-stuck-or-failed-what-should-i-do> |
| duration | no | Clip length. | no cap found | the whole kept take (4 to 10 s) | <https://higgsfield.ai/creator-hub/help-center/troubleshooting/my-video-upscale-is-stuck-or-failed-what-should-i-do> |
| aspect | yes | Shape. | kept from the input | 9:16 | <https://replicate.com/bytedance/video-upscaler> |
| audio | maybe | Sound track. | not documented | re-attach the original audio at the edit | `tools/video-edit` |

### Rules that work

- The local Real-ESRGAN is first; use this only as the alternate. — `MODEL-HOUSE.md`
- Treat 4K as the ceiling: the upstream API errors above it. — <https://fal.ai/models/fal-ai/bytedance-upscaler/upscale/video/llms.txt>
- Feed 480p to 1080p sources. — <https://replicate.com/bytedance/video-upscaler>
- A video upscale takes 1 to 5 minutes; a stuck job is a retry, not a new spend. — <https://higgsfield.ai/creator-hub/help-center/troubleshooting/my-video-upscale-is-stuck-or-failed-what-should-i-do>
- Check the result keeps the swipe's grain and the face. — `tools/video-production/VIDEO-RULINGS.md V38`

### Avoid

- Upscaling before the take is kept. — `MODEL-HOUSE.md`
- Trusting the 8K claim without testing. — <https://higgsfield.ai/creator-hub/help-center/troubleshooting/my-video-upscale-is-stuck-or-failed-what-should-i-do>; <https://fal.ai/models/fal-ai/bytedance-upscaler/upscale/video/llms.txt>
- A target above 4K on the API: it errors. — <https://fal.ai/models/fal-ai/bytedance-upscaler/upscale/video/llms.txt>
- Assuming the sound track survives the upscale. — `no source states it`

## TRELLIS.2 4B (image to 3D) — 3D for the product

**For the sale ad.** Builds the tube turntable from one clean, whole photo, so the tube is rendered and never drawn. Compare the label to the real photo.

*9 inputs · 6 structure rules · 5 avoid · 3 qualities · registry id `trellis.2-4b` · medium 3d · status draft · read 2026-10-27*

### Limits

- input images: 1
- output: PBR GLB plus a preview video
- grid resolutions: 512, 1024, 1536
- time h100 seconds: {"512": 3, "1024": 17, "1536": 60}
- gpu: NVIDIA, at least 24 GB; tested on A100 and H100
- platform: Linux only tested
- decimation target faces example: 1000000
- texture px example: 4096
- house: use: builds the product turntable from one real photo
- house: product_rule: the product is never drawn: a render of the 3D model is the picture (product-from-3D-model rule)

### Qualities

512, 1024, 1536

### Inputs

| Input | Use | What it is | Allowed | What we send | Source |
|---|---|---|---|---|---|
| image | yes | The one picture the model is built from. | a single image | the cleanest whole-product photo, nothing cut off, plain background | <https://github.com/microsoft/TRELLIS.2> |
| resolution | yes | Grid size of the shape. | 512, 1024, 1536 | 1024 | <https://github.com/microsoft/TRELLIS.2> |
| seed | maybe | Repeat a build. | integer | pinned and recorded | <https://github.com/microsoft/TRELLIS.2> |
| decimation target | no | Simplify the mesh for export. | faces; the example uses 1,000,000 | default | <https://github.com/microsoft/TRELLIS.2> |
| texture size | yes | Baked texture. | pixels; the example uses 4096 | 4096 for a label | <https://github.com/microsoft/TRELLIS.2> |
| alpha | no | Transparency in the texture. | stored but inactive until connected in the 3D tool | not used | <https://github.com/microsoft/TRELLIS.2> |
| attention backend | no | Which attention kernel. | flash-attn, or xformers via ATTN_BACKEND | default | <https://github.com/microsoft/TRELLIS.2> |
| memory setting | no | Reduce GPU memory. | PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True | set when memory fails | <https://github.com/microsoft/TRELLIS.2> |
| view/camera for preview | yes | Preview video. | rendered with environment lighting | turntable orbit | <https://github.com/microsoft/TRELLIS.2> |

### Rules that work

- Give it one clean, whole picture of the product; the model builds everything else from it. — <https://github.com/microsoft/TRELLIS.2>
- Read the label on the turntable: a build can warp text; compare against the real photo before the model is used. — `PRODUCT-KITS.md`
- 1024 builds in about 17 s on an H100; use 1536 only when the label is unreadable at 1024. — <https://github.com/microsoft/TRELLIS.2>
- The export is opaque; if the cut-out matters, connect the alpha in the 3D tool. — <https://github.com/microsoft/TRELLIS.2>
- Pictures of the product come from renders of this model or the real photo, never drawn. — `PRODUCT-KITS.md`
- It needs a 24 GB NVIDIA GPU on Linux; on the Mac it runs through the door that has one. — <https://github.com/microsoft/TRELLIS.2>

### Avoid

- Expecting it to merge several photos: it takes one. — <https://github.com/microsoft/TRELLIS.2>
- A photo with the product cut off: the missing part is invented. — `components/model-inputs/VIDEO-PATH-owner.md`
- A photo with a smear or reflection on or behind the product. — `components/model-inputs/VIDEO-PATH-owner.md`
- Using the turntable without comparing the label to the real photo. — `PRODUCT-KITS.md`
- Running it on a laptop without the GPU. — <https://github.com/microsoft/TRELLIS.2>

## Gemini 3.1 Pro (the judge) — The judge

**For the sale ad.** Reads every clip for face, whole tube, leftover people and slop. Video goes first, question after, and every verdict names a timestamp. It checks; the owner approves.

*9 inputs · 6 structure rules · 5 avoid · 2 qualities · registry id `gemini-3.1-pro-preview` · medium judge · status draft · read 2026-10-27*

### Limits

- file api gb paid: 20
- file api gb free: 2
- inline mb: 100
- request total mb inline: 20
- videos per request: 10
- default fps: 1
- tokens per second: {"low_media_resolution": 100, "high_media_resolution": 300}
- context video hours: {"low": 3, "high": 1}
- formats: mp4, mpeg, mov, avi, x-flv, mpg, webm, wmv, 3gpp
- house: busy_fallback: ['gemini-3.5-flash', 'gemini-3-flash-preview']
- house: fallback_rule: when the judge answers 'high demand' (V17), never a cost choice

### Qualities

low media resolution, high media resolution

### Inputs

| Input | Use | What it is | Allowed | What we send | Source |
|---|---|---|---|---|---|
| video | yes | The clip or swipe to read. | File API for over 100 MB or reused files; inline under about 20 MB request total | File API upload | <https://ai.google.dev/gemini-api/docs/video-understanding> |
| text prompt | yes | The question or rubric. | text, placed AFTER the video part | the judge's check list for this stage | <https://ai.google.dev/gemini-api/docs/video-understanding> |
| fps | maybe | Sampling rate. | default 1 fps; custom fps and clipping only in static mode | raise only for fast action | <https://ai.google.dev/gemini-api/docs/video-understanding> |
| start_offset / end_offset | maybe | Read only a span. | static mode | a shot's span | <https://ai.google.dev/gemini-api/docs/video-understanding> |
| media_resolution | maybe | Detail per frame. | low about 100 tokens/s, high about 300 | high for text on screen and faces | <https://ai.google.dev/gemini-api/docs/video-understanding> |
| timestamps | yes | Refer to moments. | MM:SS | used in the rubric and answers | <https://ai.google.dev/gemini-api/docs/video-understanding> |
| YouTube URL | no | Read a public video by link. | public only, preview | not used: files are local | <https://ai.google.dev/gemini-api/docs/video-understanding> |
| multiple videos | maybe | Compare clips. | up to 10 on 2.5 and later | the take vs the swipe | <https://ai.google.dev/gemini-api/docs/video-understanding> |
| response schema | yes | Structured answer. | JSON schema | the verdict shape each gate reads | `tools/video-production/machine/clip_judge.py` |

### Rules that work

- Put the video part first and the text prompt after it. — <https://ai.google.dev/gemini-api/docs/video-understanding>
- Refer to moments with MM:SS so the answer points at a place. — <https://ai.google.dev/gemini-api/docs/video-understanding>
- One check per read (face, product, leftover person, slop); a verdict that names the timestamp. — `tools/video-production/VIDEO-RULINGS.md V41`
- Use the File API above 100 MB or for reuse. — <https://ai.google.dev/gemini-api/docs/video-understanding>
- On 'high demand' fall back in order to the next model that can read video. — `tools/video-production/VIDEO-RULINGS.md V17`
- Raise fps or clip the span for fast action; 1 fps misses it. — <https://ai.google.dev/gemini-api/docs/video-understanding>

### Avoid

- Putting the prompt before the video. — <https://ai.google.dev/gemini-api/docs/video-understanding>
- Judging fast hands at the default 1 fps. — <https://ai.google.dev/gemini-api/docs/video-understanding>
- Accepting a pass with no timestamp. — `tools/video-production/VIDEO-RULINGS.md V41`
- Letting the judge approve: the owner approves status, the judge only checks. — `components/model-inputs/VIDEO-PATH-owner.md`
- Custom fps or clipping in agentic mode: not supported. — <https://ai.google.dev/gemini-api/docs/video-understanding>

