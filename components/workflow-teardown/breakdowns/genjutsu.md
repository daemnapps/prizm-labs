# Genjutsu

Browse and apply Higgsfield's Genjutsu presets: restyle a video in a named Style, transfer a driving video's motion onto subjects in your images, or replace an object, product, garment or character in a clip. A bare `/genjutsu` only opens the gallery.
Source: `commands/genjutsu.md`, `katana/references/genjutsu-routing.md` (short-prompt rule), `_models-video.md`, `katana/references/budget.md` section 4.5 (billing)

## Inputs it needs
- Pick one path: gallery (nothing needed), a named Style, a selected preset, or a direct custom request.
- Style: one video of 4-30 s, up to 5 optional reference images, optional prompt, resolution (720p in the quote call).
- Motion transfer: reference images of the subjects (1-49 for `hf_mult_motion_control`) plus exactly one driving video.
- Object replacement: 1-30 reference images plus one source video of 4-30 s.
- Existing AI Influencer sheet: its image job id, to carry it into the gallery.

## Steps in order
1. Resolve the path: bare command or "browse" opens `get_presets({source:"genjutsu",category:"genjutsu"})` and stops; trending/new use their own category; a selected preset opens its settings and stops.
2. Style: find it by name with `category:"genjutsu-styles"` (never invent an id); ask if several match.
3. Collect missing media; import or upload once and reuse the media id; never use the catalog example as the user's input.
4. Price: `get_presets` with the style id and inputs returns `execution.cost_credits` and readiness; report it.
5. Generate only on the user's go: `execute_preset` for a style or catalog preset (execute once), or `generate_video` with the model chosen by intent for a custom request.
6. Wait with `jobs_wait` (15 s timeout); the widget updates itself; do not claim success on a failed submit.

## Prompt blocks, word for word
Genjutsu keeps the prompt almost empty: references carry appearance and motion.

**Motion-transfer prompt (the only fixed prompt line; 40 words max)**  
`katana/references/genjutsu-routing.md`

```
A motion-transfer prompt can be: "Apply the source video's motion to the character in the reference image, keeping their clothing, the framing and the timing." For a fully specified preset, omit the prompt or use an empty string only when its actual contract permits it. An extra phrase is justified only to resolve a concrete ambiguity, such as which of two subjects' motion transfers. This rule does not limit the image-editing prompt or Seedance shot instructions.
```

**Short-prompt rule**  
`katana/references/genjutsu-routing.md`

```
For direct Genjutsu calls and preset text fields, default to one sentence and allow at most two sentences / 40 words. State the transformation and a minimal preservation rule. Appearance, clothing, source action, camera and composition already come from the media. Do not itemize visual traits, scene beats, textures, effects or garments; a short clause keeping the clothing from the reference image is enough. Preserve the full analysis and compositing plan outside the generation prompt.
```

**Style catalog lookup call**  
`commands/genjutsu.md`

```
1. Find the style: `get_presets({source:"genjutsu",category:"genjutsu-styles",query:"<style name>"})`. Match the user's wording to a returned name; if several match, ask which one. If none match, browse `category:"genjutsu-styles"` without query and let the user choose. Never substitute a motion preset or invent a style ID. A bare request to browse styles stops after the gallery opens.
```

**Style price call**  
`commands/genjutsu.md`

```
3. Price: call `get_presets` with `source:"genjutsu"`, the returned `genjutsu-style:` `preset_id` and `initial_inputs:{video:["<video UUID>"],references:[...],resolution:"720p"}`. Report `execution.cost_credits` and readiness. If no price is returned, say the price is unavailable and that credits may still be used.
```

**Style generate call**  
`commands/genjutsu.md`

```
4. Generate only when the user asks: `execute_preset({source:"genjutsu",preset_id:"genjutsu-style:<id>",inputs:{video:[...],references:[...],resolution,prompt}})`, then follow its job instructions. Do not execute twice; a refused style returns no job.
```

**Model choice by intent**  
`commands/genjutsu.md`

```
- Copy, repeat, reproduce, mimic, or transfer motion, actions, gestures, dance, or camera motion from a driving video to reference-image subjects: `hf_mult_motion_control`.
- Replace, change, or swap an object, product, garment, or character in a source video using reference images: `hf_mult_replace_object`.
```

**Direct-call parameter rule**  
`commands/genjutsu.md`

```
Read `models_explore` with `action:"get"` with the selected `model_id` for current supported parameters. Put arguments inside `params`: `model` is the selected ID, `prompt` is the user's brief, and `medias` contains reference images with role `image` and exactly one source/driving video with role `video`. Use supplied media and context. If a custom-video request is missing intent or required media, ask for those inputs. A bare `/genjutsu` follows the preset-gallery entry path above. Do not submit until required inputs are available.
```

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Transfer motion from a driving video to your subject | `hf_mult_motion_control` | 480p/720p/1080p (default 720p), images 1-49, one video |
| Replace an object or person in a source clip | `hf_mult_replace_object` | 480p/720p/1080p, images 1-30, one video 4-30 s |
| Lite motion transfer (Wan 3.0, up to 15 s) | `hf_mult_motion_control_flash` | 480p/720p/1080p, images 1-10 |
| Lite object replacement (Kling 4.0) | `hf_mult_replace_object_flash` | 720p/1080p/4k |
| Restyle a clip in a Style | preset `genjutsu-style:<id>` through `execute_preset` (not a model id; never pass `genjutsu` as a model) | video 4-30 s, 720p |

## Checks and gates
- Browsing never authorizes generation; the gallery widget collects references and shows price; Generate is the user's click.
- Style is not a motion preset; never substitute one for the other or invent a style id.
- Never uses the example's characters or images as the user's references; asks only for missing media or intent.
- Free Genjutsu attempts (`use_free_gens`) are unavailable on this connector; a refused style returns no job; no duplicate submit after the widget has generated; `use_unlim` is preserved, never removed on rejection.
- User intent wins over the catalog example's model (copy actions = motion transfer even if the example was a replacement).
- Prompt capped at one sentence, two at most, 40 words.

## Price pattern
Quotes first (`get_presets` returns the style cost; `estimate_video_cost` for direct calls). Motion transfer is billed by the probed driving-video seconds, rounded: 11 / 7 / 3 credits per second at 1080p / 720p / 480p (Katana budget notes; a 11.08 s take at 1080p cost 121). Style cost: returned by the call, not in `_prices.md`. `hf_mult_replace_object_flash` cannot be quoted without a source video: not quoted. Typical 5 s transfer at 720p: about 35 credits.

## Cheap swap
- Motion transfer `hf_mult_motion_control` (7 per second at 720p): `hf_mult_motion_control_flash` (Wan 3.0, 15 s max; not quoted here) or `wan3_0` 480p 7.5 per 10 s with the driving clip as a video ref (about a 6 to 10 times saving; not the same transfer quality).
- Object replacement: `hf_mult_replace_object_flash` (Kling 4.0, not quoted) as the cheaper door, or a local route: SAM2 segment plus BiRefNet matte plus a still edit (`seedream_5_0_flash` 2k, 0.5) composited with ffmpeg.
- Restyle: a single styled key picture (`seedream_5_0_flash` 0.5) plus ffmpeg camera moves instead of restyling every frame.
- Resolution: 480p (3 per second) then Real-ESRGAN upscale locally, instead of 1080p (11 per second).
- Prompt, gallery choice, media prep and probing: Claude and ffmpeg, free.
