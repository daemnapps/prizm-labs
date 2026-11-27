# Ad Multiplier

N versions of one proven 4-30 s ad: Edit keeps the footage, motion and sound and swaps the person, product, clothes, background or one text element; Recreate re-shoots the same ad for another audience, language or cast; Hook or CTA only swaps the open or the close.

Higgsfield original: `ad-multiplier` · built from `sources/higgsfield/ad-multiplier/SKILL.md`, `sources/higgsfield/ad-multiplier/references/media-pipeline.md`, `sources/higgsfield/ad-multiplier/references/prompt-writer.md`, `sources/higgsfield/ad-multiplier/references/recreate.md`, `sources/higgsfield/ad-multiplier/ui.yaml.md`

## Price

| | |
|---|---|
| higgsfield | Edit: ≈420 credits (4 outputs × 105 at 720p) + Soul pictures for any missing person (not quoted). Recreate: ≈180 at 480p or ≈960 at 1080p for 4 outputs (720p not quoted) |
| house | Genjutsu object swap with banked cast and product (0 for pictures); swap not quotable without a source video |
| cheap | ≈90 credits (Kling 4.0 Flash video-edit, 720p, 4 × 22.5), banked cast, free local masks and sound: about a fifth of Ad Multiplier. Recreate on Wan 3.0 480p ≈45 for 4 |
| basis | one 15 s source, 4 outputs, prices quoted 2026-11-21 |

## Inputs

- **the ad**: runs/winners/<brand>/bank.json (a row by ad_ids; its video from Meta or Drive), or a swipe from runs/intake/<brand>/<date>/swipes.jsonl (asset.file / asset.drive, route video-teardown); 4.0-30.0 s
- **the ad's teardown** (optional): runs/video-teardown/<brand>/<run>/ (transcript.json, framemap, stages/1-teardown.md); stands in for Higgsfield's video analysis
- **what changes**: runs/ad-variations/<brand>/<run>/ (stage2--locks-levers.md: locks kept, levers moved), else the owner's ordered list in lane.json
- **cast** (optional): brands/<brand>/ai-cast/ masters (not every brand has one), else runs/ai-elements/<brand>/casting/<role>/full/master.png + sheets/
- **product** (optional): brands/<brand>/products/<product>/images/ (not every brand has one), else runs/ai-elements/<brand>/products/<product>/model/product-sheet.png
- **market words** (optional): brands/<brand>/core-avatars/<avatar>/language/
- **house rules**: brands/<brand>/CLAUDE.md + the owner's hard rules (no disclaimers, no men kissing, clothed cast, adults only)
- **the run record**: runs/higgsfield/<brand>/<label>/lane.json (mode, outputs, resolution, credit cap, the owner's go)

## Steps

### 0. Pick the mode — `none`

Edit keeps the source footage, motion and sound and changes named targets (a person, the product, clothes, the background, one text element). Recreate re-shoots the same ad as new footage for another audience, language, cast or product. Hook or CTA only swaps the opening or the close and keeps the rest.

| | model | credits |
|---|---|---|
| Higgsfield | the directing chat model | 0 |
| our house | the run's lane.json names the mode; a proven winner with a kept performance = Edit, a swipe from another market = Recreate | 0 |

**Higgsfield, word for word**

```
## Choose the mode first

- **Edit** (default): targeted changes to the source footage — replace, add,
  remove, or modify people, products, objects, clothing, backgrounds,
  attributes, or targeted text — while its motion, timing, and audio survive.
  One output may contain several simultaneous edits. Follow Stages 1-7 below.
- **Recreate**: the same ad re-shot as new footage for another market,
  audience, spoken language, cast, product, or setting. Load
  [recreate.md](references/recreate.md) once with `get_workflow_bundle_file`
  and follow it instead of Stages 1-7 and their output contract. The runtime
  contract below still applies: submit each output with `generate_video`, one
  at a time, and let its original widget show the final result.
- **Hook or CTA only**: a new opening hook, closing call to action, or both,
  with the rest of the ad kept. Follow the "Hook or CTA only" section of
  [recreate.md](references/recreate.md), under the same runtime contract.
- If the request fits both, ask one question: keep the original footage and
  change named targets, or re-shoot the ad as new footage?
```

Check: One mode per run, written in lane.json before anything is quoted.

### 1. Intake and the price — `plan.quote`

The ordered output list (N = finished videos), which replacements have a picture, 720p or 1080p; quote every output before the first paid call.

| | model | credits |
|---|---|---|
| Higgsfield | estimate_video_cost (submits nothing) | 0 |
| our house | same quotes; the cap and the owner's go in lane.json | 0 |

**Higgsfield, word for word**

```
## Stage 1 — resolve intake once

As soon as a source is supplied, collect all still-missing fields in one turn:

1. the requested edit and ordered output list or explicit `N`;
2. whether replacement reference images exist: all, some, or none;
3. final resolution: `720p` (recommended/faster) or `1080p`.

Do not ask again for information already explicit. If references are promised,
wait for them before paid generation. If the target, time range, reference
mapping, or list-to-output assignment is ambiguous, ask one bundled mapping
question rather than guessing.
```

**Ours**

```
Source: {ad}. Outputs, in order: {outputs} (N = {n}). Each output changes only: {changes}. References on hand: {cast} / {product}; missing: {missing}. Resolution {resolution}. Quote ceil({seconds}) s per output with {clip_model}, add them up, write the total and the cap into lane.json, stop for the go.
```

Check: Total under the lane.json cap; ordered lists zipped by position, never multiplied out.

### 2. Probe the source — `edit.probe`

Measure the source: exact length (4.0-30.0 s or stop), display shape after rotation, fps, the default sound stream and its offset.

| | model | credits |
|---|---|---|
| Higgsfield | ffprobe in the Higgsfield sandbox | 0 |
| our house | ffprobe on this Mac | 0 |

On this Mac: `ffprobe -v error -show_streams -show_format -of json -- source.mp4`

**Higgsfield, word for word**

```
## Source probe normalization

Download only the trusted hosted source URL, following HTTPS redirects only and
limiting it to 500 MiB. Probe with:

```bash
curl --fail --location --proto '=https' --proto-redir '=https' --retry 2 --max-filesize 524288000 --output source.mp4 "$SOURCE_URL"
ffprobe -v error -show_streams -show_format -of json -- source.mp4
```

Normalize the JSON deterministically:

1. Select the primary non-cover-art video stream: prefer
   `disposition.default=1`, otherwise the first video stream whose
   `disposition.attached_pic` is not `1`.
2. Parse finite positive duration from `format.duration`, falling back to the
   primary video stream's duration. Reject missing/non-finite duration and any
   result outside 4.0-30.0 seconds.
3. Require positive coded width/height. Parse positive sample-aspect ratio,
   default `1:1`. Display aspect is `(coded_width * SAR) / coded_height`; invert
   it after normalized 90° or 270° rotation from side data or `tags.rotate`.
4. Parse positive `avg_frame_rate`, then `r_frame_rate`, falling back to 24 fps
   only for duration tolerance.
5. Select the audio stream marked `disposition.default=1`, otherwise the first
   audio stream. Retain its absolute ffprobe stream index. A missing audio stream
   means the source is silent.
6. Parse finite primary-video and selected-audio `start_time`. Set
   `AUDIO_OFFSET = audio_start_time - video_start_time` only when both are
   finite; otherwise use `0.0`.

Retain exact `SOURCE_DURATION`, `ceil(SOURCE_DURATION)`, display aspect, fps,
rotation-aware display geometry, audio stream index, and audio offset.
```

Check: Length inside 4.0-30.0 s; never trim, loop or freeze to fit.

### 3. Read the source — `read.source`

Timed scenes, every target the edit names, and for each person to be replaced: visible casting presentation and hairstyle (two axes).

| | model | credits |
|---|---|---|
| Higgsfield | video_analysis_create / video_analysis_status | not quoted |
| our house | our video teardown of that ad (runs/video-teardown/<brand>/<run>/: transcript.json, framemap, stages/1-teardown.md); a gap is read by the Gemini 3.1 Pro judge (gemini-3.1-pro-preview) | 0 when the teardown exists; cents otherwise |
| cheapest | Gemini 3 Flash fast read (gemini-3-flash-preview) | cents |

Cheap swap: House rule: reads inside a run are the judge; Flash is a person's pick. A swipe we already tore down needs no read at all. Registry: gemini-3-flash-preview.

On this Mac: `python3 components/local-studio/local.py stt source.mp4 -o words.json (the spoken words on the clock, free)`

**Higgsfield, word for word**

```
## Stage 2 — register, probe, and analyze the source once

1. Resolve one confirmed source `media_id` plus its hosted HTTPS URL. Reuse an
   existing confirmed upload from `show_medias` when the user identifies it.
2. In one `sandbox_exec` call, download that trusted hosted URL and run:

   ```bash
   ffprobe -v error -show_streams -show_format -of json -- source.mp4
   ```

   Apply the exact normalization and range checks in
   [media-pipeline.md](references/media-pipeline.md). Retain only the returned
   measurements; the downloaded sandbox file is not durable.
3. Call `video_analysis_create` once with `video_input_id:<source media_id>`,
   then poll its id with `video_analysis_status` every 30-60 seconds until
   `completed` or `failed`. Use the returned scenes as the timed source caption.
   Do not start a second analysis while the first is pending.
4. Retry analysis once only if it fails, returns no usable scenes/timing, omits
   a requested target, or lacks observable evidence for either required
   casting-presentation or hairstyle axis. Stop before generation if the second
   result is unusable. Missing stature/build never triggers this retry.

For every source person that will be replaced, derive a required two-axis
`source_visual_casting_profile` only from observable evidence in the analysis:
apparent racial/ethnic casting presentation plus hairstyle length, texture, and
shape. These are fictional visual casting descriptors, not claims about real
identity. The video-analysis contract does not guarantee a stature/build field.
Stature and build are optional, non-gating appearance context: carry either only
when the user supplies it or the analysis states it unambiguously; otherwise
omit it without asking. Never ask the user, block generation, reject an image,
or regenerate solely because stature or build is unavailable or unchanged. If
either side of a required two-axis contrast is unclear after the one retry, ask
for a clearer source or for both the visible source trait and desired replacement
trait; do not guess.
```

**Ours**

```
From the teardown of {ad}: list each scene with start-end seconds; for every target in {changes} give a plain anchor ("the man in the grey tee") and the seconds it is visible; for every person to be replaced, the visible casting presentation and hairstyle (length, texture, shape). Visible evidence only.
```

Check: Every target named in the plan is found with its seconds; stop before spend if not.

### 4. Plan the outputs — `write.plan`

One line per output: each edit mapped to a target anchor and its seconds; a person swap covers every appearance; captions and untargeted text kept.

| | model | credits |
|---|---|---|
| Higgsfield | the directing chat model | 0 |
| our house | Claude on the signed-in plan | 0 |
| cheapest | Claude on the plan (writing costs don't count) | 0 |

Cheap swap: Writing is free to us. Registry: claude-sonnet-5.

**Higgsfield, word for word**

```
## Stage 3 — plan ordered outputs

- Preserve explicit `N`; otherwise infer it from the ordered output list, or use
  one for a single edit request.
- Map edits on existing content to analysis target descriptions plus a unique
  plain-language anchor and natural visible ranges. An `add` instead uses a
  caption-grounded placement and timing.
- A person identity replacement is global across that person's appearances. If
  the user asks for a partial person replacement, ask them to choose either a
  full identity replacement or a non-identity attribute edit.
- Resolve each person reference's appearance authority before prompt writing.
  Default to `complete_look`; record a `clothing_override` only for a separately
  mapped garment/full-outfit image or an explicit user clothing instruction.
  Source wardrobe inferred from the video is never an override. A clothing
  override inside an identity replacement does not cancel global exclusion of
  the original person.
- `remove` needs no asset and describes the revealed background. `add` states
  placement, scale, motion, and interaction. Attribute edits change only the
  named property. Preserve captions, subtitles, UI, motion design, labels,
  branding, and every other source text element exactly as shown unless the
  user explicitly requests a specific text or graphic edit or that text is
  physically attached to a replaced target. A targeted text edit preserves
  source typography, placement, animation, and timing unless the user changes
  them. Do not introduce blanket text cleanup or caption generation.
- Resolve every user-dependent choice during planning. A final Ad Multiplier
  prompt states only the resolved edit and contains no branches, alternatives,
  or meta-conditions. A targeted text edit becomes one explicit operation while
  all untargeted text receives an unconditional preservation instruction.
- Shared assets/instructions may repeat across outputs. Ordered replacement
  lists pair by output position only.
```

**Ours**

```
For output {i} of {n}: change {changes_i} using the locks and levers of {variation_run} (keep every lock). Map each change to its anchor and seconds from the read. A person swap = {source_person} -> {cast_i}, every appearance. A product swap = {source_product} -> {product}. Keep every caption, label and on-screen line unless {text_edit} names it. No branches: every choice resolved here.
```

Check: Every output resolved, nothing conditional left; lists zipped, never crossed.

### 5. Replacement people — `pictures.people`

Only for a person swap with no picture: Higgsfield invents an adult on a white studio backdrop and asks for approval. Ours: the banked cast master, already signed off.

| | model | credits |
|---|---|---|
| Higgsfield | soul_2, 3:4, 2k, count 1 per missing person | not quoted |
| our house | our banked cast master (0); a missing person goes through casting and GPT Image 2.5 (gpt-image-2.5), never invented here | 0 for banked, ~2 per new master |
| cheapest | Seedream 5.0 Flash, 2k (seedream_5_0_flash) | 0.5 |

Cheap swap: Only a stand-in for a person we have no master for; breaks the rule that every person starts from the cast, so it is a test-only pick. GPT Image 2.6 flare 1k low (0.75, registry missing) is the other. Registry: missing.

On this Mac: `python3 components/local-studio/local.py matte master.png -o cutout.png (BiRefNet: the master on a clean white backdrop, free)`

**Higgsfield, word for word**

```
## Stage 4 — acquire replacement references

### User-supplied images

Resolve each image to a confirmed media id and hosted HTTPS URL. Keep one fixed
order. The URL is for visual inspection; the media id is the downstream
generation input. Never substitute one for the other.

### Missing adult human references — Soul 2.0

Use Soul 2.0 (`soul_2`) only for a requested human replacement that lacks a
user image. It is not a fallback for animals, creatures, robots, products,
objects, backgrounds, removals, attributes, text edits, children, or teens.

1. Load the live contract once with
   `models_explore({action:"get",model_id:"soul_2"})`.
2. Submit one distinct `generate_image` call per missing adult slot, one
   position at a time. Use no `medias` and no `soul_id`; use `count:1`,
   `aspect_ratio:"3:4"`, and `quality:"2k"`. Soul 2.0 is prompt-driven: put the
   adult age band, presentation, period-appropriate wardrobe, and visual genre
   directly in the positive prompt. Use only the live Soul 2.0 fields shown
   below; do not add structured demographic or cinematic controls. If either
   required axis cannot map after the one permitted analysis retry, ask; never
   ask for stature/build. For a source under 20, require a user reference or
   explicit consent to recast the role as an adult.
3. Before each request, build a positive two-axis contrast plan against that
   slot's source person. Every generated replacement must have both: a clearly
   different apparent racial/ethnic casting presentation and a different
   hairstyle, including length, texture, and shape. Stature/build never gates
   this plan. Do not force a different body type, body proportions, face shape,
   or facial geometry. Those traits come naturally from the generated image.
   Generated people in the same request set must also remain visibly distinct
   from one another.

   Write each Soul prompt as one cohesive **140-190 word natural-language
   paragraph**, not a tag list, fragment stack, or compressed semicolon
   checklist. Resolve every field before writing; never submit bracketed
   placeholders or slash-separated alternatives. The replacement must be
   strikingly beautiful, handsome, or otherwise conventionally attractive. Use
   the matching concrete phrase for the requested presentation: `strikingly
   beautiful`, `strikingly handsome`, or `conventionally attractive`. Include these four
   anchors or close positive paraphrases in fluent prose: `with high model
   facial features`, `symmetrical features`, `well-proportioned figure`, and
   `natural skin texture`. Never default an unspecified presentation to the
   worked example's woman; resolve it from the request/source mapping or ask.
   Beauty and realism are quality floors, not additional contrast axes.

   Build the paragraph in this order:

   1. **Subject and pose:** open with a straight-on, eye-level, full-body portrait
      of exactly one adult age 20+. State the positive replacement casting traits,
      skin tone, hairstyle length/texture/shape, facial quality, posture,
      expression, and direct camera gaze. Add stature/build only when it is
      user-specified or unambiguously available; never invent it as a contrast.
      Describe the selected casting presentation through concrete visible traits;
      never write only "different" or "contrasting," and never mention the source
      person's traits in the Soul prompt.
   2. **Wardrobe:** name a complete stylish, period-appropriate outfit from top
      through footwear, using opaque, well-structured fabrics plus at most two
      restrained accessories. Keep the entire outfit and both feet visible.
   3. **Studio and composition:** place the subject alone against a seamless
      matte-white studio backdrop whose white floor blends cleanly into the wall.
      Center the figure in balanced vertical framing with generous negative space
      and no props, furniture, text, logos, or visual clutter.
   4. **Lighting and palette:** use soft, evenly diffused high-key natural studio
      lighting, gentle grounded shadows, controlled highlights, and no harsh
      contrast or overexposure. State a restrained outfit-led color palette.
   5. **Capture and finish:** specify a professional high-resolution digital
      camera, deep depth of field, ample dynamic range, minimal noise, and
      razor-sharp head-to-toe focus. Close with authentic skin detail, realistic
      human anatomy, natural hands and limbs, and no plastic retouching,
      distortion, or exaggerated traits, plus a crisp modern editorial mood.

   For multiple missing people, vary the concrete pose, outfit silhouette,
   accessories, palette accents, and both casting axes while preserving this
   studio/camera quality standard. The worked request below demonstrates prose
   form only. Rebuild every subject detail from the slot's approved contrast plan;
   do not copy its woman, age, casting presentation, hair, skin tone, or wardrobe.
   Submit the completed paragraph as-is; Soul 2.0 has no model-side prompt
   enhancer in this connector.

   ```json
   {"params":{"model":"soul_2","prompt":"A straight-on, eye-level full-body portrait features a strikingly beautiful 24-year-old Afro-Caribbean woman with supermodel facial features, symmetrical features, a well-proportioned figure, warm deep-brown skin with natural texture, and long dark softly waved hair. She stands poised with shoulders back, one foot angled outward, arms relaxed, and a direct camera gaze. She wears a structured matte-black blazer, opaque high-neck top, tailored wide-leg trousers, pointed-toe heels, thin gold chain, and small stud earrings. Her complete outfit and both feet are visible. A seamless matte-white studio backdrop and matching floor contain no props, furniture, text, logos, or clutter, leaving generous negative space around her centered figure. Soft, evenly diffused high-key natural studio lighting creates gentle grounded shadows, authentic skin detail, and controlled highlights without harsh contrast or overexposure. A crisp black, white, and subtle gold palette supports the modern fashion-editorial mood. Captured on a professional high-resolution digital camera with balanced vertical framing, deep depth of field, ample dynamic range, minimal noise, and razor-sharp focus from face to footwear, the image preserves realistic anatomy, natural hands and limbs, and a photogenic unretouched editorial finish without distortion or exaggerated traits.","count":1,"aspect_ratio":"3:4","quality":"2k"}}
   ```

   This text-only Soul 2.0 request receives neither `@Video1` nor media inputs.
   Words such as "different" or "contrasting" without explicit positive
   replacement traits do not satisfy the gate.
4. Retain the returned job id and let its original `generate_image` widget poll
   and display that position automatically. Do not invoke another display or
   polling tool. Retry only a terminal-failed position once. Inspect each
   completed result against its mapped source profile, contrast plan, and
   quality gate.
   Regenerate a named position once if either required axis is unchanged, vague,
   or missing, or if the person is not attractive, photogenic, natural-looking,
   and anatomically realistic. Never offer a failed-contrast or failed-quality
   candidate for approval.
5. Ask for approval of the candidate shown in its original generation widget.
   Continue only after approval; regenerate named people or stop as requested.
6. After approval, retain its `result_url` for visual inspection, completed
   generated-person image `job_id` for direct Ad Multiplier image media, and
   approved positive two-axis profile. Use the approved image directly without
   re-uploading it. It is a normal positional image reference in both the prompt
   contract and Ad Multiplier; the Full MCP generation resolver turns the
   completed job id into `image_job` media.
```

**Ours**

```
Use {cast} (full/master.png, complete look: face, hair, skin, build, outfit, shoes, accessories). If {cast} is missing: stop and run casting for {role}, adult 20+, from real references; never a generated stranger.
```

Check: Every swapped person has a signed-off master; adults only; clothed.

### 6. Edit prompt — `write.edit_prompt`

One prompt per output from the plan: COMPACT for object, product, background or attribute edits; DETAILED for any person swap. The text-preservation block once; the original person excluded from every frame.

| | model | credits |
|---|---|---|
| Higgsfield | the directing chat model, by prompt-writer.md | 0 |
| our house | Claude on the signed-in plan | 0 |
| cheapest | Claude on the plan | 0 |

Cheap swap: Free; the prompt contract is the value, keep it whole. Registry: claude-sonnet-5.

**Higgsfield, word for word**

```
## Choose one template

Use **DETAILED** when any source-person identity replacement is requested, when
there are multiple identity swaps, when the swapped subject spans multiple
shots or interacts with props, reflections, or shadows, when changes span at
least three categories, or when the user asks for a detailed brief. Otherwise
use **COMPACT**. Never announce the selected mode.

### COMPACT

```text
TASK - VIDEO EDIT:
Preserve every caption, subtitle, and other untargeted on-screen text element from @Video1 exactly as it appears, including its wording, styling, placement, animation, and timing. Text physically attached to a replaced target follows that replacement.
<start>-<end>s: keep everything exactly the same
<start>-<end>s: <one operation sentence>. Keep every unrequested element, camera motion, lighting treatment, and overall color grading from @Video1 exactly the same.
```

Rules:

- Tile the full measured duration with no gaps or overlaps. Merge consecutive
  identical segments. A whole-clip edit has one change line and no keep line.
- Use one operation sentence per changed segment. Merge simultaneous clauses
  with semicolons and a final `and`.
- Reference-backed replace: `Replace only [target] in @Video1 with
  [replacement] from [@ImageN]`.
- Text-only replace: `Replace only [target] in @Video1 with [description]`.
- Modify: `Modify only [target] in @Video1 so that [change]`.
- Remove: `Remove only [target] from @Video1 and reconstruct the revealed area
  consistently with its immediate surroundings`.
- Add: `Add only [element] at [caption-grounded placement] in @Video1`.
- Every attached reference is cited only by its canonical `@ImageN` tag.
- COMPACT is forbidden for a person identity replacement.

### DETAILED

Write these blocks in order. The numbered edit blocks are the only list:

```text
[@ImageN] — [ALIAS], the complete replacement look for [TARGET]: [complete visible identity, optional visible build/stature when discernible, hair, outfit, footwear, headwear, eyewear, jewelry, and accessories]. Transfer this entire look from @ImageN, including the full outfit and all worn accessories.
Preserve every caption, subtitle, and other untargeted on-screen text element from @Video1 exactly as it appears, including its wording, styling, placement, animation, and timing. Text physically attached to a replaced target follows that replacement.
Video edit. Keep this @Video1 clip exactly as it is — the same shots and cuts, camera moves, framing, composition, unmapped performers, setting, untargeted held and environmental props, lighting, pacing, and timing. Change only [complete scope], keeping source blocking, poses, motion, position, screen placement, and timing while rendering each replacement person's complete image-defined look.
1. [REPLACE | MODIFY | REMOVE | ADD] — [mapped target and operation, complete-look @ImageN binding when present, resolved clothing override when present, temporal scope, source-person exclusion when required, and interaction/reflection handling].
[IDENTITY | REFERENCE | EDIT] lock: [every mapping, untouched-content protection, anti-bleed rules, and generated two-axis profile when present].
Render [one imperative summary transferring each replacement's complete reference-defined look, including clothing and accessories, while inheriting only source performance and timing].
Everything else — [untouched people, objects, untargeted wardrobe, text, environment, lighting, the camera moves and all timing] — stays exactly the same.
```

Reference declarations precede the preservation sentence, one per distinct
asset. Describe the complete visible look relevant to the edit; never rename or
restyle a reference. For a person, declare the full outfit and all worn items as
part of that complete look. For a character sheet, declare one alias and one
reference.

Each numbered edit names exactly one operation and one target. Several
operations may share a time window but remain separately numbered. For a full
creative recast, map every source target to its replacement explicitly. Do not
create a numbered block for default source-text preservation; only an explicitly
requested text or graphic edit receives an operation block.

The lock must name important untouched content and state that no other person,
object, **untargeted** wardrobe, text, environment, action, cut, camera move,
lighting treatment, or timing changes. Never protect the mapped source person's
wardrobe when the person reference owns the complete look. Every person
replacement includes its specific source-person exclusion. Multiple
replacements also forbid identities from crossing, merging, exchanging, or
duplicating onto another figure.

In every reference-backed person replacement, write the alias as coming from its
canonical `@ImageN`. `@Video1` is only the source performance/scene; it is never
the replacement identity or look. Use the exact tag casing `@Video1` and
`@ImageN`.

## Person replacement exclusion

Every source-person identity replacement must contain this target-specific
meaning once:

> The original source person identified as [target] in @Video1 must never appear in any frame of the output. Replace that person completely with [ALIAS] from [@ImageN] in every appearance, transferring the complete reference-defined look and retaining only the original performance, pose, blocking, interactions, and timing.

Extend the exclusion through cuts, entrances, exits, occlusions, motion blur,
transitions, reflections, and shadows. Name each mapping separately; never use
"replace everyone". Attribute, hair, or clothing changes do not trigger global
identity exclusion because they preserve the source person.

A resolved clothing override within a person identity replacement does not
cancel the global identity exclusion. Worn headwear, eyewear, jewelry, watches,
bags, and other worn accessories belong to the complete look. Preserve only
held or environmental interaction props from the source unless they are
separately targeted.

For a generated person, copy both positive values from
`replacement_casting_profile` into both the reference declaration and render
instruction. Preserve the complete attractive, photogenic, natural-looking
identity and complete outfit/accessories visible in the approved image. Do not
invent or force a body type, body-proportion, face-shape, or facial-geometry
contrast with the source. Never ask for or validate a stature/build contrast.

## Final validation

Reject and rewrite once if any check fails:

- the plain prompt is non-empty and at most 3900 characters;
- all requested operations and real timeline ranges are covered;
- every required attached image tag appears at least once;
- no undeclared image tag, media UUID, upload id, job id, URL, or other transport
  identifier appears;
- each supplied reference maps to exactly one edit unless explicitly excluded
  or complementary;
- every generated person's two-axis profile and complete visible likeness are
  preserved positively and consistently without invented body or face contrast;
- every mapped person reference transfers its complete visible look, including
  clothing and accessories, except for a resolved separate clothing reference
  or explicit user wardrobe instruction;
- no mapped source wardrobe is retained by default, called "unchanged," or
  protected as untargeted content;
- each replaced source person has a target-specific global exclusion;
- the exact two-sentence source-text preservation block appears once;
- every untargeted source text or graphic is preserved, every explicit text edit
  is scoped only to its named target, and no automatic text-removal or caption-
  generation operation appears;
- no unresolved user/request conditional appears in the rendered prompt;
- every replacement alias comes from its declared `@ImageN`, never `@Video1`,
  and all media tags use canonical case with no `@video1`, `@image1`, or other
  lowercase/mixed-case variant;
- no unmapped source content changes and no shot, camera move, identity,
  semantic label, or timing is invented.
```

**Ours**

```
TASK - VIDEO EDIT:
Preserve every caption, subtitle, and other untargeted on-screen text element from @Video1 exactly as it appears, including its wording, styling, placement, animation, and timing. Text physically attached to a replaced target follows that replacement.
0-{t1}s: keep everything exactly the same
{t1}-{t2}s: Replace only {product_anchor} in @Video1 with {product_name} from @Image1. Keep every unrequested element, camera motion, lighting treatment, and overall color grading from @Video1 exactly the same.

(person swap, DETAILED)
@Image{k} — {ALIAS}, the complete replacement look for {person_anchor}: {master_description}. Transfer this entire look from @Image{k}, including the full outfit and all worn accessories.
Preserve every caption, subtitle, and other untargeted on-screen text element from @Video1 exactly as it appears, including its wording, styling, placement, animation, and timing. Text physically attached to a replaced target follows that replacement.
Video edit. Keep this @Video1 clip exactly as it is — the same shots and cuts, camera moves, framing, composition, unmapped performers, setting, untargeted held and environmental props, lighting, pacing, and timing. Change only {scope}, keeping source blocking, poses, motion, position, screen placement, and timing while rendering each replacement person's complete image-defined look.
1. REPLACE — The original source person identified as {person_anchor} in @Video1 must never appear in any frame of the output. Replace that person completely with {ALIAS} from @Image{k} in every appearance, transferring the complete reference-defined look and retaining only the original performance, pose, blocking, interactions, and timing.
IDENTITY lock: {locks}.
Render {ALIAS} with the complete look of @Image{k} while inheriting only source performance and timing.
Everything else — {untouched} — stays exactly the same.
```

Check: At most 3900 characters; every @ImageN used; the preservation block exactly once; no ids, URLs or open conditions.

### 7. Edit clips — `clips.edit`

One silent edit per output, one at a time: the source video first, then each reference picture in @Image order; duration = ceil(source seconds).

| | model | credits |
|---|---|---|
| Higgsfield | ad_multiplier, mode video_edit, 720p, generate_audio false, duration_policy strict | 70 per 10 s at 720p (105 for a 15 s source) |
| our house | Genjutsu object swap (higgsfield-object-swap): our cast or product into the shot, motion kept; Genjutsu motion transfer (higgsfield-motion-control) when the swap keeps the old face | not quotable without a source video |
| cheapest | Kling 4.0 Flash, video-edit mode, 720p (kling_4_0_flash) | 15 per 10 s (22.5 for a 15 s source) |

Cheap swap: About a fifth of Ad Multiplier at the same 720p; loses its tuned whole-look person swap and text guard, so check every frame. Others: Gemini Omni Flash 1.2 edit at 360p, 7.5 per 10 s, sources 3-15 s only, edit price not quoted (missing); Genjutsu Lite (hf_mult_replace_object_flash, Kling 4.0, missing, not quotable without a video); Seedance 2.5 video_edit 30 per 10 s at 480p (seedance-2.5); Wan 3.0 480p with the source as a video reference, 7.5 per 10 s (wan-3.0) has no edit mode, it re-makes the shot and loses the exact motion. Registry: missing.

On this Mac: `python3 components/local-studio/local.py segment source.mp4 -o masks --box x0,y0,x1,y1 (SAM 2.1 tracks the target); matte for a clean edge (BiRefNet); then ffmpeg overlays only the masked region of the edit onto the source, so nothing untargeted can drift`

**Higgsfield, word for word**

```
## Stage 6 — submit silent Ad Multiplier edits

For each output, send the source video first, then every image reference in the
same order used by the manifest and prompt. A user image uses its confirmed
media id; a generated-person image uses its completed generation job id. The
prompt refers to both only by their canonical `@ImageN` tags.

```json
{"params":{"model":"ad_multiplier","prompt":"<validated prompt verbatim>","count":1,"duration":8,"duration_policy":"strict","aspect_ratio":"auto","resolution":"720p","mode":"video_edit","generate_audio":false,"medias":[{"value":"<source media id>","role":"video"},{"value":"<@Image1 confirmed user media id>","role":"image"},{"value":"<@Image2 approved generated-person job id>","role":"image"}]}}
```

Use `model:"ad_multiplier"` for every edit request; never call
`model:"seedance_2_5"` directly in this workflow. The numeric duration is
illustrative: always use `ceil(SOURCE_DURATION)`. Use
the chosen resolution. Submit outputs one at a time in order with
`generate_video`. Retain each accepted job id under its output index. Retry only
a rejected or terminal-failed position once with the same approved identity and
scope; never retry a pending position.

After each submission, rely on its original `generate_video` widget to poll and
render that Ad Multiplier position. Do not invoke another display or polling
tool. State that the widget preview is silent and still requires final audio
restoration and QC, then continue to the next output only after the current
position is terminal.

Do not extract audio in a separate early sandbox call: it would not survive the
remote render. Finalization re-downloads the immutable source and extracts its
default audio in the same producing sandbox call.
```

**Ours**

```
{edit_prompt}  (medias: {ad} as video, then {image_refs} in @Image order; duration ceil({seconds}); {resolution}; sound off)
```

Check: Send output 1 alone and look at it before the rest; retry a failed position once, never a pending one.

### 8. Put the sound back — `edit.finish`

Drop any generated sound, keep only the edited picture, trim to the exact source length, lay the source's own sound back with its measured offset.

| | model | credits |
|---|---|---|
| Higgsfield | ffmpeg in the Higgsfield sandbox | 0 |
| our house | Video Edit (components/video-edit), the Studio's edit line | 0 |

On this Mac: `ffmpeg -nostdin -y -i raw.mp4 -i source-audio.mka -filter_complex "[1:a:0]$AUDIO_FILTER[a]" -map 0:v:0 -map "[a]" -t $SOURCE_DURATION -c:v copy -c:a aac -b:a 192k -movflags +faststart final.mp4`

**Higgsfield, word for word**

```
## One-call finalization

Before the call, reserve one `media_upload` MP4 slot per output and retain each
exact `upload_url`. Process at most four completed outputs in one call.

Inside the call:

1. Download the immutable source once with the HTTPS-only command above.
2. Extract its selected default audio once. First try stream copy to MKA; if it
   fails, decode once to PCM WAV. Use the absolute stream index, `-nostdin`, and
   safely quoted paths:

   ```bash
   ffmpeg -nostdin -y -i source.mp4 -map "0:$AUDIO_STREAM_INDEX" -vn -c:a copy source-audio.mka
   # fallback only after copy failure
   ffmpeg -nostdin -y -i source.mp4 -map "0:$AUDIO_STREAM_INDEX" -vn -c:a pcm_s24le source-audio.wav
   ```

   If an audible source fails both commands, fail the group; never deliver a
   silent substitute. Skip extraction for a silent source.
3. Download each trusted completed generation HTTPS result URL with the same
   protocol and size restrictions. Reject an unplayable or video-less raw result.
4. Build `AUDIO_FILTER` from the measured offset:

   - positive: `adelay=<offset_ms>:all=1,asetpts=PTS-STARTPTS,apad=whole_dur=<duration>,atrim=duration=<duration>`;
   - negative: `atrim=start=<absolute_offset>,asetpts=PTS-STARTPTS,apad=whole_dur=<duration>,atrim=duration=<duration>`;
   - zero: `asetpts=PTS-STARTPTS,apad=whole_dur=<duration>,atrim=duration=<duration>`.

5. Discard accidental generated audio, retain only the generated video stream,
   trim to exact source duration, and restore only extracted source audio:

   ```bash
   # Audible source
   ffmpeg -nostdin -y -i raw.mp4 -i "$AUDIO_ABS" \
     -filter_complex "[1:a:0]$AUDIO_FILTER[source_audio]" \
     -map 0:v:0 -map '[source_audio]' -t "$SOURCE_DURATION" \
     -c:v copy -c:a aac -b:a 192k -movflags +faststart final.mp4

   # Silent source
   ffmpeg -nostdin -y -i raw.mp4 -map 0:v:0 -t "$SOURCE_DURATION" \
     -c:v copy -an -movflags +faststart final.mp4
   ```

   Do not use `-itsoffset`, `-shortest`, or `-avoid_negative_ts make_zero`:
   those may shift or truncate the inherited video timeline. If the generated
   video is too short, fail it rather than looping or freezing frames.
6. Probe each final and require all gates:

   - playable and contains a video stream;
   - duration within `max(1/fps, 0.10)` seconds of exact source duration;
   - rotation/SAR-aware display aspect within 1.5% relative error of source;
   - displayed short edge within 8 pixels of selected 720 or 1080;
   - audible source → AAC audio exists; silent source → no audio stream.

7. PUT only passing finals to their reserved slots in the same command:

   ```bash
   code=$(curl -sS -o /dev/null -w '%{http_code}' -X PUT --upload-file final.mp4 "$UPLOAD_URL")
   test "$code" = 200
   ```

Emit one concise machine-readable receipt per output containing only its workflow
index, QC measurements, PUT status, and failure reason. After the call, invoke
`media_confirm` only for HTTP-200 outputs. A provider download failure may retry
once; never create a second Ad Multiplier job for a download, remux, QC, or upload
failure.
```

Check: Length within max(1/fps, 0.10) s of the source; shape within 1.5%; short edge within 8 px of 720/1080; source sound present (or silent if the source was).

### 9. Check and deliver — `behind.judge`

Contact sheet per output: the replaced person never shows (cuts, reflections, shadows), untargeted captions and labels unchanged, the product label exact; deliver in output order.

| | model | credits |
|---|---|---|
| Higgsfield | ffprobe gates; media_upload / media_confirm; the chat model reports | 0 |
| our house | Gemini 3.1 Pro judge (gemini-3.1-pro-preview) on 2 fps contact sheets | metered, cents |
| cheapest | Gemini 3 Flash fast read (gemini-3-flash-preview) | cents |

Cheap swap: House rule: every read inside a run is the judge; Flash is a person's pick only. Registry: gemini-3-flash-preview.

On this Mac: `ffprobe + ffmpeg contact sheets (fps=2,tile)`

**Higgsfield, word for word**

```
## Stage 7 — finalize, upload, and verify

For each completed Ad Multiplier job, retain its trusted HTTPS `result_url` for
processing; never deliver the raw silent widget preview as the final result.
Process at most 4 completed outputs per sandbox call.

1. Load [media-pipeline.md](references/media-pipeline.md).
2. Reserve one final MP4 slot per output with `media_upload` before the sandbox
   call.
3. In one self-contained `sandbox_exec` command, download the trusted source
   and raw results, extract the source's default audio once, trim/remux each
   result, run all duration/aspect/resolution/audio gates, and PUT each passing
   final to its own reserved `upload_url`. Do not reuse or reconstruct an upload
   URL.
4. Call `media_confirm` only for outputs whose PUT returned HTTP 200.

Deliver only confirmed final upload URLs, in original output order, labeled
`Output 1`, `Output 2`, and so on. State `completed/total`, concise failure and
pending counts, selected resolution, exact source duration, and whether source
audio was restored or the source was silent. Never expose raw Ad Multiplier URLs,
silent generation artifacts, generated-person references, prompts, manifests,
local paths, or job/element ids as deliverables.

## Failure boundaries

| Failure | Required response |
| --- | --- |
| Source outside 4-30s | Stop; report measured duration and accepted range |
| Source upload/probe fails | Retry once when safe; otherwise stop before spend |
| Analysis invalid twice | Stop before generation |
| Ambiguous mapping | Ask one bundled mapping question |
| Generated-person image position fails twice | Fail each dependent whole output or stop |
| User rejects generated people | Regenerate named people or stop |
| Approved generated-person direct reference unavailable | Fail every dependent output before Ad Multiplier |
| Prompt validation fails twice | Fail only that output before Ad Multiplier |
| Ad Multiplier position fails | Retry only that position once |
| Source is silent | Produce a silent verified final |
| Audible source extraction fails | Do not deliver a silent substitute |
| Download/remux/QC/upload fails | Isolate that output; keep verified successes |
| Some outputs remain pending | Report pending; never duplicate them |
```

**Ours**

```
For output {i}: is {person_anchor} visible in any frame (including reflections and shadows)? Does every caption and on-screen line match {ad} word for word and in place? Is {product_name}'s label exact? Is anything changed that the plan did not name? Answer pass or fail per question with the second it happens.
```

Check: Delivered to the Studio and Drive in output order, never to Meta from here; failures reported by position.

### 10. Recreate — `clips.recreate`

Recreate mode only: the same ad re-shot as new footage for another audience, language, cast or product. Higgsfield's backend reads the source, casts, voices and renders ceil(source seconds) at the source shape; the render is the deliverable.

| | model | credits |
|---|---|---|
| Higgsfield | ad_multiplier_v2, prompt + medias + resolution + count only, 720p default | not quotable without a source video; ceil(seconds) at the Seedance 2.5 per-second rate (480p 3/s = 45 for 15 s; 1080p 16/s = 240; 720p not quoted) |
| our house | our own chain: the ad workflow (teardown, writing, Seedance 2.5 takes from our cast, ElevenLabs v3 voices, Video Edit) | ≈45 per 15 s at 480p, upscaled free |
| cheapest | Wan 3.0, 480p, the source as a video reference + up to 10 cast/product pictures + voice refs (wan3_0) | 7.5 per 10 s (11.25 for 15 s) |

Cheap swap: A sixth of the Seedance rate; loses the backend's own read, casting and voice; our teardown and our own reads (eleven-v3) fill those, and the swipe stays the idea, our words and shots the ad. Registry: wan-3.0.

On this Mac: `RIFE interp and Real-ESRGAN upscale afterwards (local-studio interp / upscale), free`

**Higgsfield, word for word**

```
## Intake — ask only for what is missing

The backend never asks, so the prompt must carry the request. Ask once, in one
question, only when the user has not given:

1. the source video (4.0-30.0 seconds);
2. what changes: the target market or audience, the spoken language, a new
   product, or new people.

Without other instructions, make 1 output at `720p`. Ask nothing the user already
stated, and never ask about audio, setting, image roles, or the product mode:
the backend decides them. Never invent product facts, prices, offers, or claims.
Ordered lists pair by output position; never build a Cartesian product.

Do not generate people for this mode. When the user wants a different person
and gives no photo, describe that person in the prompt: the backend generates
one adult likeness itself, at no extra charge, and casts it; describe any
further person in words. With a photo, pass it as an `image` media
and say in the prompt whom it replaces. A new performer or a new spoken
language gets a new voice; the source voice and music stay only when nobody
who speaks changes, unless the prompt asks otherwise.

## Map each output to one request

| Field        | Value                                                                                                                                                                                                                                    |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `model`      | `"ad_multiplier_v2"`, with `count:1` per output                                                                                                                                                                                          |
| `prompt`     | That output's whole request in the user's words, at most 4000 characters: the market or audience, the spoken language, a replacement product's name and the facts the user gave, who each image is, lines to say exactly in quotes, and any explicit audio or setting wish. Add no invented facts. |
| `medias`     | The source as `role:"video"`, then up to 20 images as `role:"image"`. Images need no role: the backend classifies them as product, person, wardrobe, location, prop, logo, or style, and the prompt's words about an image win. |
| `resolution` | `720p` unless the user asked for `1080p` or `480p`.                                                                                                                                                                                      |

```json
{"params":{"model":"ad_multiplier_v2","prompt":"Recreate this ad for the German market in German, with the presenter in the image replacing the main presenter.","count":1,"resolution":"720p","medias":[{"value":"<source media id>","role":"video"},{"value":"<presenter image media id>","role":"image"}]}}
```

Every output is an independent backend analysis and render, so two outputs
with the same inputs still differ. Each output costs `ceil(source seconds)` at
the Seedance 2.5 per-second rate for the chosen resolution.
```

**Ours**

```
Recreate this ad for {audience} in {language}, same beats, order, timing and capture style. The person in @Image1 ({cast}) replaces the main presenter. The product is {product_name} (@Image2); facts: {product_facts}. Lines to say exactly: "{lines}". Words from {market_words}. No invented facts, prices or offers; no disclaimers on screen.
```

Check: Same beats and length as the source; our cast and product exact; every line heard; no claim we did not supply.

### 11. Hook or CTA only — `clips.sections`

New opening hook (4-15 s), new closing CTA (4-5 s) or both, stitched in with hard cuts; the rest of the ad untouched.

| | model | credits |
|---|---|---|
| Higgsfield | ad_multiplier_v2, mode sections, section hook | cta | both | reserves 15 / 5 / 20 s at the Seedance 2.5 rate, charged for seconds rendered (480p: 45 / 15 / 60 reserved) |
| our house | a new hook as a Seedance 2.5 take (clips.take) from our cast, cut in by Video Edit | ≈15-45 per hook at 480p |
| cheapest | Wan 3.0, 480p, start frame from the source's first shot (wan3_0) | 7.5 per 10 s (≈3.75-11 per hook) |

Cheap swap: We find the cut point ourselves (scene list from the read) and splice with ffmpeg; loses the backend's own cut-at-the-word and setting match. Registry: wan-3.0.

On this Mac: `ffmpeg concat with hard cuts at the shot boundary from the read; stt to keep the cut off a spoken word`

**Higgsfield, word for word**

```
## Hook or CTA only

When the user wants a new opening hook, a new closing call to action, or both,
and the rest of their ad kept as it is, send the same request with
`mode:"sections"` and `section:"hook"`, `section:"cta"`, or `section:"both"`.
One output with `section:"both"` replaces the hook and the CTA together.

The backend finds each section in the source (the first hook, the last CTA),
cuts at the end of the shot that finishes it, never inside a spoken word, renders each new section in the source's
setting at a length it picks (a hook 4-15 seconds, a CTA 4-5), and stitches them
in with hard cuts. The rest of the source is untouched, so the result is
`source length - removed sections + new sections` seconds long. When the source
has no clear hook or CTA, the new one is added before (hook) or after (CTA) the
whole ad and nothing is removed. The prompt says what the new hook or CTA should
do or say; leave out changes to the rest of the ad, which a sections run cannot
make.

A sections output reserves its longest length (hook 15 seconds, CTA 5, both 20)
at the Seedance 2.5 per-second rate and is charged only for the seconds it
renders; the rest comes back. With `section:"both"`, if one part fails the
output still completes with the source kept in place of that part, only the
rendered part is charged, and the job's `failed_sections` names the part that
failed; if both fail, the job fails and nothing is charged.

```json
{"params":{"model":"ad_multiplier_v2","mode":"sections","section":"hook","prompt":"New hook: open on a close-up of the product with the question \"Still tired at 3 pm?\"","count":1,"resolution":"720p","medias":[{"value":"<source media id>","role":"video"}]}}
```
```

**Ours**

```
New hook: {hook_line}, opening on {hook_picture} in the source's setting, {seconds_hook} s. Keep everything after the first hook exactly as it is.
```

Check: Cut lands at a shot end, never inside a word; the rest of the ad unchanged frame for frame.

## Checks

- Mode, ordered outputs, resolution, price and cap in lane.json before the first paid call
- Source measured inside 4.0-30.0 s; never trimmed to fit
- Output 1 sent and checked alone before the rest
- The replaced person never appears in any frame, reflection or shadow
- Every untargeted caption, label and on-screen line unchanged; the product label exact
- Length within 0.10 s of the source; the source's own sound back on (Edit)
- No disclaimers, invented claims, prices or offers on screen

## Rules

- One source, N ordered outputs; lists zipped by position, never multiplied out
- Source motion, cuts, timing and sound kept in Edit; only named targets change
- A person swap covers every appearance; the original never survives a frame
- Every person from our signed-off cast; adults only; clothed; men never kiss or hug men
- Captions and untargeted on-screen text kept exactly; no disclaimers, offer, price or call to action added
