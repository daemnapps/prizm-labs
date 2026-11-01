# Seedream 5.0 Pro — what it takes, and what works

*Rendered from `components/model-inputs/inputs/seedream-5-pro-edit.json` (read 2026-10-26, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- max images: 10
- max images note: Higgsfield's own rule (`higgsfield model get seedream_v5_pro`): at most 10 image_references; more are refused
- output max: 2048x2048 (2K)
- output pixels: between 1024x1024 and 2048x2048 in total; aspect ratio from 1/16 to 16
- default size: auto_2K
- formats: JPEG by default, PNG available
- safety checker: on by default; can only be turned off through the API
- pixel exact edits: not guaranteed: ByteDance notes finer text rendering and pixel-level editing consistency can still improve
- price note: Higgsfield: 2.5 credits per picture at 9:16, 2k (quoted free by `higgsfield generate cost`, 26 Oct). fal's dollar figures were for fal's door, which is retired.

## The prompt structure that works

- **Order a photographic prompt like a photographer's brief: subject first, then where the camera stands, then the light and the finish; name lens, aperture and grain.**
- **For layouts (posters, graphics), describe the arrangement like a handoff: name the grid, the regions and what goes in each; put copy in double quotes with its placement.**
- **State composition, off-centre framing and palette: anything unstated falls back to the safe average (dead-centre symmetry).**
- **State each light's direction, hardness and colour. 'Well lit' gives a flat sourceless glow.**
- **Name textures (wool fibre, leather grain, skin scattering) rather than 'detailed'.**
- **For an edit, name the single thing that changes and say the rest stays.**
- **Refer to references by number ('from image 2', 'from image 1'). fal does not formally document the indexing rule: verify on a test.**
- **To composite, feed separate plates (product, surface, logo, props) and give one composite instruction; keep plates in sequence.**
- **Shoot or choose each reference from about the angle it will take in the final frame.**
- **Wrap exact words in double quotes and say where they belong; check each line at full size, long body copy is the weak area.**
- **Refine one strong base with targeted edits instead of rerolling.**

## Avoid

- Vague quality words like 'well lit' and 'detailed'.
- Leaving composition open: it comes back generic and centred.
- Too many elements in one pass: instructions get dropped.
- Plates shot at different angles: the composite does not read as one scene.
- An edit with no 'keep everything else the same' line: changes spread beyond the intended area.
- Studio, cinematic or staged wording when you want a real photo.
- A person's name, a date or a quote from our own rulings inside the prompt: the model draws it as picture content.

## Through Higgsfield (differs from the maker's own door)

- resolutions: 1k, 1.5k, 2k
- aspect ratios: 1:1, 4:3, 3:4, 16:9, 9:16, 3:2, 2:3, 21:9
- references: role image_references; at most 10 (Higgsfield's own rule)
- differs: extra fields: is_inpaint (treat as an edit of the references) and remove_bg. Reachable through the Higgsfield command line only (the keyed API does not sell it).
- default resolution: 2k
- Not available: custom WxH other than the optional width and height fields; mask (an is_inpaint flag treats the request as an edit of the reference, no mask).
