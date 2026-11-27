# 3D Jutsu
Hosted, revision-controlled 3D scenes built by running Blender Python (bpy) through scene_builder_3d tools: rooms, sets, props, cameras, lights, animation; renders, GLB/blend export, and AI images or video made from a render; plus new camera angles of a supplied location.
Source: `commands/3d-jutsu.md`, `commands/3d-jutsu-references-animation-audit.md`, `commands/3d-jutsu-references-composition-modeling.md`, `commands/3d-jutsu-references-location-new-angles.md`, `commands/3d-jutsu-references-lookdev-lighting.md`, `commands/3d-jutsu-references-scene-building.md`

## Inputs it needs
- A scene brief (room, set, prop layout, camera, lighting, animation) or a supplied location image for new angles.
- The route (hosted scene by default; Blender Studio is a rented GPU billed per second; local Blender via /scene-builder).
- For location angles: the shots the user chooses (a reverse wide, optional side medium and detail), any hidden-layout answers, aspect ratio.
- Hosted tools only: `scene_builder_3d_*`; if absent the workflow says hosted 3D Jutsu is not available.

## Steps in order
1. Settle the route once and keep it for the conversation; one standalone object from an image is not a scene (use image-to-3D).
2. List or create the project (`create_project` once; list before retrying an uncertain create).
3. Loop: `get_project` (revision + sceneSequence), `query_python` to inspect, pick an idempotent `operationId`, `run_python` with the guards; one mutation per project at a time; poll `get_operation`.
4. On a stale-state conflict re-query and regenerate the edit with fresh guards and a new operation ID; read error code and retryAdvice before retrying.
5. First mutation places the delivery camera and a working light rig (ambient, key `LGT_key`, soft fill); Sun, Spot or Point lights only.
6. Work coarse to fine: silhouette, proportion, depth, contact, camera read (small low-sample EEVEE render), detail. Render, retrieve the artifact, look, fix the largest defect.
7. Models only from the curated catalog (`search_assets` then `import_asset` with the result's importArguments).
8. Location mode: build under a saved source-control camera, extend hidden surroundings, prepare clean angle references and per-view prompts, show previews, wait for approval of the paid batch.
9. Deliver files only on request; AI image/video from an inspected render's operationId + artifactId; call `show_scene` once per review boundary.

## Prompt blocks, word for word
The workflow's fixed text is its loop, publish pattern and the per-view generation prompt rule; the five reference files carry the rest (scene-building, composition-modeling, lookdev-lighting, animation-audit, location-new-angles).

**Route choice** (`commands/3d-jutsu.md`)
`````
A 3D scene can be built in three places:

- This hosted scene: free to build. Nothing to rent or install, and building, editing and rendering spend no credits; only an AI image or video made from a render does. The simple default.
- Blender Studio: the prosumer option. A rented GPU box running full Blender that the user opens in the browser, for heavier or professional work, their own files and generated meshes. The GPU is billed in credits by the second for as long as the box runs.
- The Blender on the user's own computer (`/scene-builder`): free, needs a one-time setup.
  Settle the route before creating a project, renting anything or spending credits.

Go without asking only when the user already chose the route:

- They typed `/3d-jutsu`, asked for a hosted 3D Jutsu scene, or are continuing a 3D Jutsu project: continue here.
- They name Blender Studio, or a Blender Studio box is already in use in this conversation: this is not the route. Load `get_preset_instructions` with `{"preset":"/gpu"}` and work in that Blender. Do not create a hosted project for it.
- They selected `/scene-builder` or their own local Blender: that route keeps the work. Offer this one only as an alternative, never silently.

In every other case ask once which route they want, before anything else. This covers a 3D scene with no route named, new views of a supplied location, and "in Blender" without saying which Blender.

- Ask with this client's question tool when it has one, else in one short message.
- Offer only the routes you have tools for: this one needs `scene_builder_3d_*`, Blender Studio needs `gpu_rent` with `kind: blender_studio`. When only one route is left, say which and continue without asking.
- Describe each option by what the user gets and what it costs, and put your recommendation first. For example: "a hosted 3D scene: free to build, nothing to rent or install", "Blender Studio: full Blender in the browser for heavier, pro work, the GPU is billed by the second", "the Blender on your computer: free, needs a one-time setup". Say which is free and which costs credits every time you offer them.
- The answer holds for the rest of the conversation: do not ask again for later 3D requests.

Two more rules, whatever the route:

- One standalone 3D model of an object from an image, with no scene around it, is not a scene: use image-to-3D generation.
- One specific subject from a reference image (a character, a creature, a product) inside a scene: ask once whether to generate it from the image (costs credits, close likeness, harder to edit) or model it from simple shapes (no generation cost, simpler, editable). This version imports catalog assets only, so a generated or uploaded mesh cannot enter a hosted scene: say so, and offer a catalog asset, a build from simple shapes here, or Blender Studio. Never wrap a picture around a mesh as its texture in place of modelling and materials.

If no `scene_builder_3d_*` tools are available on this connector, say that hosted 3D Jutsu is not available here.
`````

**The loop** (`commands/3d-jutsu.md`)
`````
1. `scene_builder_3d_get_project` for the current revision, scene sequence and any active operation.
2. `scene_builder_3d_query_python` to inspect names, dimensions, transforms, materials, cameras, lights and RNA before editing. Queries commit nothing; use them freely. Never guess a name, unit or API.
3. Pick a stable, descriptive `operationId` such as `add-key-light-01`. It is an idempotency key: reuse it only to retry the identical code against identical guards.
4. `scene_builder_3d_run_python` with the query's `revisionBefore` as `revision` and `sceneSequenceAfter` as `expectedSceneSequence`.
5. One mutation at a time per project, imports included. If an operation is still active, poll `scene_builder_3d_get_operation` with the same IDs. Only `succeeded`, `failed`, `timed_out` and `expired` are terminal.
6. On success, `revisionAfter` is the new head.
7. On a stale-state conflict, do not replay the code. Re-query, work out what changed, and regenerate the edit with fresh guards and a new operation ID.
`````

**Publish renders** (`commands/3d-jutsu.md`)
`````
```python
target = artifacts.file(name="preview.png", media_type="image/png")
scene.render.filepath = str(target.path)
scene.render.image_settings.media_type = "IMAGE"  # set before file_format
scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
target.publish()  # unpublished files are discarded
```
`````

**Deliver and paid generation** (`commands/3d-jutsu.md`)
`````
- AI image or video from a render: `scene_builder_3d_generate_angles` (image) and `scene_builder_3d_generate_video` (Seedance 2.5 video with the render as its start frame) spend credits and leave the scene unchanged. Use them only when the user asks for an AI image or video from the scene, with an inspected PNG/JPEG render's `operationId` and `artifactId`, then poll `scene_builder_3d_get_generation`. On an uncertain response, reuse the same `requestId` and arguments; never allocate a new one just to retry.
`````

**Location mode: per-view prompt order** (`commands/3d-jutsu-references-location-new-angles.md`)
`````
Write a concrete per-view prompt in this order: input roles/proxy mapping, verbal
camera lock, layout and visible sides/counts, approved revealed content, identity
and directional patterns, lighting/palette, focus and a short reminder of risky
invariants. Omit inapplicable clauses, replace every placeholder, and trim duplicate
adjectives before spatial constraints. Prompt length is not a quality guarantee.
`````

**Location mode: model and approval** (`commands/3d-jutsu-references-location-new-angles.md`)
`````
Use Seedream 5.5 for appearance reconstruction. Verify the selected model and quote before generation. Inspect current model/tool settings, reference capacity, format
support and cost. Do not hardcode historical prices or claim scene work is free.

Default mode: finish geometry, camera checks, clean previews, reference preparation,
per-view prompts and a current cost estimate before requesting approval. Show the
settled scene and selected camera previews, then end the turn with a direct request
to generate the named shots, image count, model and estimated total cost. A general
request for new angles alone is not approval of that paid batch. This gate applies
to appearance generation, not the scene preview renders needed to prepare it.

An explicit instruction to generate without further confirmation, including casual
wording, authorizes proceeding through generation and bounded correction within
the user's count, settings and budget. Retain that instruction; do not stop for a
redundant plan or generation approval. Service-required payment choices and missing
mandatory authorization remain blockers. Silence never supplies permission.
`````

**Scene proof** (`commands/3d-jutsu-references-scene-building.md`)
`````
## Prove the scene

Execution success is not visual success. A mutation that returned `succeeded` proves the code ran; it proves nothing about what the scene looks like. Before calling a scene complete:

- inspect structural state: expected objects, transforms, parenting, materials, cameras, and frame range;
- render from the delivery camera and **look at the render**: inspect it with this client's image capability after retrieving it with `scene_builder_3d_get_artifact`. Flat magenta is the missing-texture colour, not a material. A cropped subject, a floating object, a light that never reached the frame are all visible in one preview and invisible in `result`;
- for animation, inspect at least rest, departure, peak, settle, final, and the loop seam when present;
- compare against the Scene Passport rather than against what the build script attempted;
- fix the largest concrete failure and repeat only the affected audit.

Do not pass a visual check from numeric state alone. If the evidence cannot be produced — a render that will not finish within the execution deadline, or a client that cannot view images, for example — say so and report that check as blocked rather than declaring the scene done. Keep modifiers, rigs, materials, semantic parts, and source geometry editable unless the requested deliverable requires destructive application.

Budget the proof against the deadline: one render per operation, `BLENDER_WORKBENCH` for pure-form checks (it ignores scene lights), `BLENDER_EEVEE` at modest resolution and low samples whenever the light has to be judged — the camera-read gate and the presentable frame, `CYCLES` only when the user asked for it and the scene is small enough to finish. A render that times out is not evidence either way.
`````

**Structural audit** (`commands/3d-jutsu-references-animation-audit.md`)
`````
## Structural audit

One `scene_builder_3d_query_python` can check all of this against the Scene Passport:

- every expected semantic object exists exactly once;
- dimensions, transforms, origins, parents, collections, and visibility are correct;
- active camera, resolution, render engine, fps, and full frame range match the deliverable;
- the final frame includes the final marker and last key;
- material slots and texture references resolve;
- no stray defaults, duplicate suffixes, orphan proxies, or hidden failures remain;
- hero/export meshes have appropriate normals, closure, and density.

## Motion audit

Inspect at least first/rest, departure, fastest or largest change, settle, final, and the loop seam. At each sample verify framing, collision/intersection, surface contact, visibility, constraints, shading continuity, and motion direction.

Render those frames as stills, retrieve them with `scene_builder_3d_get_artifact`, and look at them with this client's image capability. Numeric evaluation — `matrix_world` at each sampled frame — proves an object is where you keyed it and is in frame; it cannot prove the motion reads. Motion fails when expected properties have no keys, promised motion is imperceptible, objects teleport, rotations flip, the camera loses the subject, constraints jump, or the loop has a visible seam. A single still cannot pass an animation audit; a rest frame plus peak plus final is the minimum.

## Visual audit

View evidence from the delivery camera at delivery scale. Check:

- silhouette and focal hierarchy;
- contact, scale cues, and depth separation;
- texture scale and material/reflection readability;
- highlight and shadow detail without clipping or crushed form;
- coherence between imported and locally built assets;
- framing throughout motion;
- whether any camera-visible asset still reads as an unresolved primitive despite requiring higher fidelity.

Downsampled previews can erase features only a few pixels wide. Inspect critical regions at 1:1 before concluding that detail is absent. Numeric projections can prove that an object is in frame, but cannot prove that it looks like the intended subject.
`````

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Build, edit, render the scene | bpy API 5.2 via `scene_builder_3d_run_python` | engines BLENDER_EEVEE, BLENDER_WORKBENCH, CYCLES only; about 5 min per operation, code at most 256 KiB, no network |
| AI image of a new angle from a render | `seedream_5_5` via `scene_builder_3d_generate_angles` (or `generate_image`) | one optional uploaded reference, enumerated aspectRatio; verify and quote first |
| AI video from a render | `seedance_2_5` via `scene_builder_3d_generate_video` | render as start frame; poll `scene_builder_3d_get_generation` |
| Blender Studio route | `gpu_rent` kind blender_studio | GPU billed in credits per second while it runs |

## Checks and gates
- A succeeded mutation proves the code ran, not that the scene is right: render from the delivery camera, view it, fix before calling it done.
- Revision + sceneSequence guards on every write; never replay stale code.
- At most 8 published files per operation (png, jpeg, mp4); a mismatch fails the whole operation.
- Catalog assets only; never Python downloads or base64 for models; never wrap a picture around a mesh in place of modelling.
- Location mode: image critique alone does not authorize scene work; preparing three options does not authorize three generations; default mode ends the turn asking approval of the named shots, count, model and estimated cost.
- One targeted retry per failing angle within the authorized spend; same major failure after that = stop that angle and say so.
- Never hardcodes historical prices or claims scene work is paid; an explicit 'generate without confirming' authorizes the batch within the user's count and budget.
- Reconciles an uncertain submission with the same requestId and arguments; never a new id to retry.

## Price pattern
Scene building and rendering are free (stated). Paid only for AI image/video from a render: Seedance 2.5 draft 480p 30 credits per 10 s, 1080p 160 per 10 s (from `_prices.md`); Seedream 5.5 angles not quoted (proxy: seedream_v5_pro 2k 2.5). The workflow quotes before generating.

## Cheap swap
- Scene work: already free, nothing to swap.
- AI video from a render: `wan3_0` 480p at 7.5 credits per 10 s (up to 10 image refs) or `gemini_omni_flash_1_2` 360p at 7.5 (max 7 image refs, 10 s or less with refs) instead of `seedance_2_5` 30 draft / 160 at 1080p: saves 75 to 95 percent.
- AI angle images: `seedream_5_0_flash` 2k at 0.5 or `gpt_image_2_6_flare` 1k low at 0.75 instead of 2 to 2.5 per 2k picture.
- Local free: render turntables or camera moves straight from Blender and interpolate with RIFE, upscale with Real-ESRGAN (components/local-studio/README.md); GLB cleanup in local Blender.
- Layout planning, shot specs and per-view prompt writing: Claude on the plan, free.
