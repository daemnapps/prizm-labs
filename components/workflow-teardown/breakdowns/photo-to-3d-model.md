# Photo to 3D Model
One clean, optimized textured GLB per object from a photo, sized for game, web/AR, 3D print or render, optionally rigged.
Source: `photo-to-3d-model/SKILL.md`, `photo-to-3d-model/_files.md`

## Inputs it needs
- One photo (better 2 to 4 of the same object from different sides) of an object, product, character, creature or prop.
- The use: game / real-time, web / AR (default), 3D print or render; sets polygon budget and topology.
- Characters: whether to rig or animate.

## Steps in order
1. Intake: one object per model; ask which if several. Default use is web/AR, said aloud.
2. Prepare: busy background, other objects or hands -> `remove_background` first. Warn if the object is cut off, blurred or tiny; say the back is invented when only one side shows.
3. Pick the model by the table; a creature that trips Meshy's safety check goes to Hunyuan.
4. Set the fields with the provider's own field names (a foreign field is silently dropped and the job runs with no polygon limit).
5. Call `generate_3d` once per object, with the photo as a media; wait with `jobs_wait`.
6. Characters: rig via Meshy flags or `3d_rigging` on the GLB; look up clip ids with `animation_actions`.
7. Fix: far over budget (over 3x) means a wrong field name, regenerate; wrong polygon count or quads -> remesh; bad texture -> retexture; wrong shape -> next model once.
8. Answer with the GLB, the model, budget and topology applied, rigged or not, and what was invented; offer one next step.

## Prompt blocks, word for word
This workflow sends no text prompt: its fixed content is the model choice, the provider field names, the budgets and the call shape. Those are quoted.

**Model pick table** (`photo-to-3d-model/SKILL.md`)
`````
| Need                                  | Model                      | Notes                                                                                 |
| ------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------- |
| Default (props, products, characters) | `meshy_v7_image_to_3d`     | rig: `pose_mode: "a-pose"`, `enable_rigging: true`; stylized: `model_type: "lowpoly"` |
| 2–4 photos of the same object         | `hunyuan3d_v3_image_to_3d` | pass all photos in `medias`                                                           |
| Max detail for print or render        | `hunyuan3d_v3_image_to_3d` | `generate_type: "Normal"`, high `face_count`                                          |
`````

**Model notes** (`photo-to-3d-model/SKILL.md`)
`````
- A creature or monster can trip Meshy's safety check (`nsfw` status on a
  non-human beast). Use Hunyuan for it instead.
- Hunyuan files are heavy (about 40 MB at 50 000 triangles, from large
  textures). For web, AR or games prefer Meshy.
- Tripo (`tripo_*`) failed in both test runs (about 10 minutes, then
  `failed`). Use it only if the user asks for it.
`````

**Provider field names** (`photo-to-3d-model/SKILL.md`)
`````
| Provider                | Polygon budget            | Texture                                            | PBR          | Quads                                                           |
| ----------------------- | ------------------------- | -------------------------------------------------- | ------------ | --------------------------------------------------------------- |
| Tripo (`tripo_*`)       | `face_limit`              | `texture: true`                                    | `pbr`        | `quad: true`                                                    |
| Meshy (`meshy_*`)       | `target_polycount`        | `should_texture: true`                             | `enable_pbr` | `topology: "quad"`                                              |
| Hunyuan (`hunyuan3d_*`) | `face_count` (min 40 000) | always textured unless `generate_type: "Geometry"` | `enable_pbr` | `polygon_type: "quadrilateral"` with `generate_type: "LowPoly"` |

Budgets:

| Use                           | Triangles                  | PBR               | Topology                      |
| ----------------------------- | -------------------------- | ----------------- | ----------------------------- |
| Game / real-time hero         | 10 000–30 000              | yes               | triangle                      |
| Game prop / mobile / playable | 2 000–8 000                | no                | triangle                      |
| Web / AR viewer (default)     | 30 000–50 000              | yes               | triangle                      |
| 3D print                      | 200 000+ (Hunyuan 500 000) | no texture needed | triangle                      |
| Render / archviz              | 100 000–500 000            | yes               | quad if the user will edit it |
`````

**Budgets by use** (`photo-to-3d-model/SKILL.md`)
`````
| Use                           | Triangles                  | PBR               | Topology                      |
| ----------------------------- | -------------------------- | ----------------- | ----------------------------- |
| Game / real-time hero         | 10 000–30 000              | yes               | triangle                      |
| Game prop / mobile / playable | 2 000–8 000                | no                | triangle                      |
| Web / AR viewer (default)     | 30 000–50 000              | yes               | triangle                      |
| 3D print                      | 200 000+ (Hunyuan 500 000) | no texture needed | triangle                      |
| Render / archviz              | 100 000–500 000            | yes               | quad if the user will edit it |
`````

**The generate_3d call** (`photo-to-3d-model/SKILL.md`)
`````
Call `generate_3d` once per object with `params: { model, medias: [{ value:
<job_id or media_id>, role: "image_references" }], <the fields above> }`
(Meshy 5 `image_to_3d` / `multi_image_to_3d` take role `image`). A local or
attached photo goes through `media_upload` first; a web URL through
`media_import_url`. Wait with `jobs_wait` before answering.
`````

**Rig and animate** (`photo-to-3d-model/SKILL.md`)
`````
Either set `enable_rigging` (and `enable_animation` + `animation_action_id`)
on the Meshy request, or rig an existing GLB with `3d_rigging`
(`model_url` = the GLB url). Look up clip ids with
`animation_actions`. Rigging works on humanoids; say that
animals and objects may rig poorly.
`````

**Fixes** (`photo-to-3d-model/SKILL.md`)
`````
- Wrong polygon count or the user wants quads → `meshy_v5_remesh` with
  `model_url`, `target_polycount`, `topology`. Far over budget (more than 3×)
  means a wrong field name was sent: regenerate with the right field instead
  of remeshing a huge mesh.
- Texture is off but the shape is right → `meshy_v5_retexture` with
  `model_url` and a `text_style_prompt` or the original photo as
  `image_style_url`.
- Shape is wrong → try the next model from §3 once, then report.
`````

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Default (props, products, characters) | `meshy_v7_image_to_3d` | rig: pose_mode a-pose, enable_rigging true; stylized: model_type lowpoly |
| 2 to 4 photos of one object; max detail for print or render | `hunyuan3d_v3_image_to_3d` | all photos in medias; generate_type Normal, high face_count |
| Background removal | `remove_background` | on the photo first |
| Rigging an existing GLB | `3d_rigging` | model_url = GLB url |
| Remesh / retexture | `meshy_v5_remesh` / `meshy_v5_retexture` | model_url, target_polycount, topology / text_style_prompt or image_style_url |
| Avoid | `tripo_*` | failed in both test runs; only on request |

## Checks and gates
- One object per model.
- Warns when the photo will force the model to guess missing parts; says the back is invented for one-sided photos.
- Hunyuan files are heavy (about 40 MB at 50,000 triangles): prefers Meshy for web, AR and games.
- Budget check after generation: more than 3x over budget means a wrong field name; regenerate, do not remesh a huge mesh.
- Shape wrong: tries the next model once, then reports.
- Rigging works on humanoids; says animals and objects may rig poorly.
- Not for walkable scenes, new camera angles of a location, sketch-to-image, or building something in Blender.

## Price pattern
Not quoted; quotes before paying. One model per object plus optional rig/remesh/retexture calls.

## Cheap swap
- Whole job: local TRELLIS 3D (`3d ref.png -o out.glb`, components/local-studio/README.md) free, about 400 s per object, 22.8 GB, instead of any paid generate_3d.
- Photo prep: local BiRefNet matte instead of the `remove_background` call.
- Remesh / polygon reduction: Blender decimate locally, free, instead of `meshy_v5_remesh`.
- Texture fixes: re-bake in Blender, or regenerate the reference picture on seedream_5_0_flash (0.5) and rerun TRELLIS.
- Model choice, intake, the answer: Claude on the plan, free.
