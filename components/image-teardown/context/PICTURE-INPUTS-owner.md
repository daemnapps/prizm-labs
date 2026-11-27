# Picture Inputs — what we hand the GPT image model, and what it should get

Mirror of the artifact page (link in `artifacts.md`). 2026-10-26. Republish over it.

## The finding (product slop)

Every product has three real photographs on file: front, three-quarter, back
(`runs/ai-elements/<brand>/products/<product>/model/reference-front|34|back.png`).
Only FLEX (face brush) had them wired into `kit.json` (`shown.refs`). The other ten
products sent ONE photo, the front, as a transparent PNG. Any ad that shows the
tube lying down, turned, or in a hand asked the model to invent the sides it was
never shown. That is the "generic product" look.

**Changed (live, `components/image-production/image_production/plain.py`):** when a kit
has no `shown.refs`, the call now sends front + three-quarter + back, on the opaque
white-background photos, each labelled with its side, followed by one line:
"Preserve its geometry, colour and label legibility exactly, whichever side faces the
camera; do not restyle it, relabel it or invent any side that is not shown."

## What each call sends today

| Call | Door | Sends | Settings |
|---|---|---|---|
| `plain.make` (statics, carousels, scene stills) | edits, `image[]` | swipe/plate, real pieces, product refs, one prompt | `gpt-image-2.5-sunburst`, quality high, moderation low, 4:5 = 1024x1280 |
| `gpt_drafts.py` (older draft path) | edits | swipe + product photos; 3D render pasted AFTER | same |
| `image-production` engine / `route.py` | edits if a source picture, else generations | prompt + references | same table `models.json` |
| `casting/generate.py` | edits, 1 reference, 1:1 | baseline frame + prompt | same |
| video stills (`runs/video-production/.../pictures`) | edits | 2-4 unlabelled refs | finished still measures 1024x1536 (2:3), prompt says 9:16 |

## What OpenAI says (sources)

- Image prompting guide (developers.openai.com/api/docs/guides/image-prompting): order the
  prompt scene, subject, details, constraints; label every input by number and role; for
  products say "preserve product geometry and label legibility exactly" and "do not restyle
  the product"; list what must not change on an edit; for gpt-image-2 omit `input_fidelity`
  (inputs are always processed at high fidelity); quality low/medium/high/auto, 2.5 adds
  xhigh and max; sizes: multiples of 16, ratio at most 3:1, 655,360 to 8,294,400 pixels.
- GPT Image prompting cookbook (developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide):
  "Image 1: ... Image 2: ..." labels; match lighting, perspective, scale and shadows so a
  composite reads as one capture; "photorealistic", "real photograph", real texture; avoid
  studio, staged and cinematic wording; use high quality for small or dense text; "do not
  change anything else"; long unfocused prompts are hard to debug.
- Image generation guide (developers.openai.com/api/docs/guides/image-generation): edit endpoint
  takes several images; mask is guidance, not exact.
- Third-party (weaker evidence, not relied on): scenario.com and atlabs.ai guides repeat the same
  structure and claim more reference images are accepted; unverified.

## Where we waste an input or fight the model

1. Ten products send one angle (fixed above).
2. Transparent PNG sent raw (fixed above, opaque photo now).
3. Video stills: references are listed as paths with no "Image 1/2/3" roles, and the prompt says
   "the man in the reference sheet" without saying which image.
4. Video stills: boilerplate "the LED wall only glows colour" rides on every scene, including a park.
5. Video stills: finished size is 2:3, not 9:16.
6. Planned product laid in afterwards (`product-space-v1`): an empty spot plus a pasted render
   breaks "match lighting, perspective, shadows". It is how cut-out looks happen (the owner, 2026-10-25).
7. Author quotes ("the owner, 2026-10-25: ...") were sent to the model in the people line (removed above).
8. Casting anchor sheet uses studio and VFX wording ("professional modeling digitization session",
   "VFX, AAA game studios", "Ultra high realism"), which the guide says pushes polish, not photos.
9. Size and quality never vary: label-bearing shots stay at 1.3 megapixels.

## Prompts, old next to new

### Product line (live)

OLD: The other attached images are the real {names}: show each exactly as it looks in its photos (shape, colour, size, label), as the lines say.
Labels: IMAGE 2 is the real {NAME}: its real photo.

NEW: The other attached images are photographs of the real {names}, each marked with the side it shows. Preserve its geometry, colour and label legibility exactly, whichever side faces the camera; do not restyle it, relabel it or invent any side that is not shown.
Labels: IMAGE 2 is the real {NAME}: the FRONT view. IMAGE 3 is the real {NAME}: the THREE-QUARTER view. IMAGE 4 is the real {NAME}: the BACK view.

### People line (live)

OLD ends: ...A celebrity or known influencer stays recognisable as a nod (the owner, 2026-10-25: "always try to use celebrity / known influencer lookalikes and other cultural references") with a slightly different face, never the real person.
NEW ends: ...A celebrity or known influencer stays recognisable as a nod, with a slightly different face, never the real person.

### Video still (PROPOSED, not wired; example: pastor-barber still A)

OLD: Keep this exact park scene, camera angle and the two men tumbling on the paving stones below. Add THE PASTOR BARBER (the man in the reference sheet, exactly his face, beard, glasses and heavyset build): a light blue-and-white Christian Dior Oblique monogram print blazer, white shirt, thin dark tie, white trousers, black loafers with red soles, gold cross lapel pin, clear rectangular glasses, hanging in the air above them on two thin black wires from a hidden harness, legs out in a wide mid-air split, red soles showing, his left hand pointing down at the two men, his right hand raised high and closed around nothing (the real product is laid in later), mouth open mid-shout. Daylight, same park light. Raw phone footage look, 9:16 vertical: true skin with visible pores and a little sweat sheen, slight handheld softness, no grade, no retouching. No words, letters, logos or graphics anywhere in the frame; the LED wall only glows colour. Keep every face and hand inside the centre 4:5 of the frame; leave the bottom quarter free of faces.

NEW:
Image 1: the scene plate. Keep this exact park, camera angle, daylight and the two men tumbling on the paving stones.
Image 2: THE PASTOR BARBER, the cast master. Exact face, beard, glasses and heavyset build.
Image 3: his flying look. Use it for the wardrobe only.

Add the Pastor Barber to Image 1, hanging in the air above the two men on two thin black wires from a hidden harness. He wears the outfit from Image 3. Legs out in a wide mid-air split, red soles showing, left hand pointing down at the two men, right hand raised high with the fist closed and empty, mouth open mid-shout.

A real vertical phone photo in the same daylight as Image 1. Natural skin texture with visible pores and a little sweat sheen, no retouching.
Keep every face and hand inside the centre 4:5; leave the bottom quarter free of faces.
Do not change anything else in Image 1. No text, no logos.

### Casting anchor sheet (PROPOSED, not wired)

OLD: (components/casting/prompts/anchor-v1-owner.md) ...similar to a professional modeling digitization session... Ultra high realism. Extremely accurate identity preservation. No artistic interpretation. No beauty filters... used by professional VFX, AAA game studios, or film character departments.

NEW:
Image 1 is the only source of identity. Make a 3x3 sheet of nine photographs of this exact same person on a plain light gray background: front, left profile, right profile, left three-quarter, right three-quarter, slight downward gaze, slight upward gaze, serious, neutral.
Keep identical in all nine: facial structure, eye shape and spacing, nose, lips, jawline, hairstyle and hairline, skin tone, age, proportions, asymmetries and marks, clothing and accessories. Do not beautify, stylize or smooth.
Real photographs: natural skin texture with pores, soft even light, the same camera distance and framing in all nine. No text, no added accessories, no background variation.

## Settings to try (one test each, not changed yet)

- Label-bearing shots: quality xhigh and a larger frame (4:5 at 1280x1600 = 2.0 megapixels; limit 8.3).
- Video stills: DONE 2026-10-26, true 9:16 at 1152x2048 (`video-production/machine/providers.json`, `model-inputs.json`); they were 2:3, and were already quality xhigh (the table above says high for statics only).
- `input_fidelity`: leave out (correct already).

## Not yet tested

No new picture has been generated with these changes. the owner stopped the paid test on 2026-10-26.
Only the product line and the people line are live.

## The Picture Bench (added 2026-10-26)

`components/image-production/bench/` (`serve.py`, `page.html`): a page at http://localhost:8895 (phone: the owner-mac:8895).
Pick brand and product, pick a swipe or upload one, write THE PICTURE, press Make. It shows the numbered images and the
five prompt sections as the model receives them, makes ONE picture through `plain.make` (quality high or xhigh, 4:5),
files it under `runs/image-production/<brand>/picture-bench/` and copies it, with its prompt, to the same path on the
Shared Assets drive. It is running now from a background process; it is not yet a login-time job.

## 9:16 from the jump (2026-10-26)

the owner: making 4:5 and painting space around it "comes out like shit and inconsistent"; 9:16 from the start with the safe zone
assumed is easier to crop. Now, for every photo and video chain (not email): pictures are generated at 9:16 (1152x2048) with a
THE FRAME section in the prompt (centre 4:5 = safe zone, top and bottom 15% bleed); the judge measures the zone; nothing is
outpainted. Changed: `image_production/engine.py` (native for safe-zone purposes, edits excepted), `plain.py`, `pictures.py`,
`slides.py`, the bench, `image-teardown/chain.py` (the 4:5 "pad" route for ads with words is gone), video stills 1152x2048.
Not changed: email; edits of existing pictures (`image-edit`, region edits) keep their frame and are finished the old way;
`gpt_drafts.py` (oldest draft path). Five engine tests that asserted the old 4:5-then-finish rule were rewritten to the new rule.

## Which model, how many inputs (2026-10-26)

Model: **GPT Image 2.5** (`gpt-image-2.5-sunburst`), OpenAI direct today and moving to the Higgsfield command line (the owner, 26 Oct; OpenAI stays as a transitional net), for every picture (fresh or edit, people or not). The bench shows it,
read off `models.json`. Inputs: the edits endpoint takes **up to 16 images**, each png/webp/jpg under 50 MB
(developers.openai.com/api/reference/cli/resources/images/methods/edit). `plain.MAX_IMAGES = 16` refuses more. The bench takes extra
pictures, each with a role line that becomes "IMAGE n is ...".

## Every input, and the prompt structure that works (2026-10-26)

Sources: OpenAI image edit and generate references (developers.openai.com/api/reference/cli/resources/images/methods/edit|generate),
GPT Image 2.5 prompting guide (developers.openai.com/api/docs/guides/image-prompting).

| Input | Allowed | We send |
|---|---|---|
| model | gpt-image-2.5-sunburst (quality), gpt-image-2.5-flare (fast, about GPT Image 2 quality) | sunburst; flare is not in the model house |
| prompt | up to 32,000 characters | 1,500 to 5,000 |
| image | up to 16, png/webp/jpg under 50 MB | 3 to 6 |
| mask | png under 4 MB, same size as image 1, transparent = edit; guidance only | region edits only |
| size | WxH multiples of 16, edge up to 3840, ratio up to 3:1, 655,360 to 8,294,400 px, above 3,686,400 experimental | 1152x2048; bench also 1440x2560, 1008x1792 |
| quality | low, medium, high, xhigh, max, auto (xhigh, max: 2.5 only) | high statics, xhigh video stills |
| n | 1 to 10 | 1 |
| output_format / output_compression | png, jpeg, webp / 0 to 100 | png |
| background | auto, opaque, transparent | auto |
| moderation | low, auto | low |
| input_fidelity | 1 and 1.5 only; omit on 2.x | left out |
| stream, partial_images, safety_identifier | optional | not used |
| style, response_format, user | retired / deprecated | not used |

Prompt structure (the guide): define the result first; labelled sections (scene, subject, details, constraints); number every
input with a role; name what must not change and change one thing; exact words in quotes with position, typography, "exactly
once" and no extra text; plain photo wording (no cinematic or studio); concrete people (framing, gaze, hands); explicit frame
and zone; one change per iteration; do not rely on the prompt for pixel-exact parts. Our five sections (INPUTS, THE PICTURE,
THE PRODUCT, THE PEOPLE, THE FRAME, RULES) map onto these; gaps: "exactly once" for text, and plain photo wording is not forced.
The bench now exposes quality (low to max) and size (1152x2048, 1440x2560, 1008x1792); `plain.valid_size` enforces OpenAI's rule.

## Installed as a component (2026-10-26)

`components/model-inputs/` holds the definitions (`inputs/gpt-image-2.5.json`, `inputs/seedance-2.5.json`, both filled; Seedream 5 Pro and Nano Banana Pro follow, same shape), the checker
(`input_rules.py`) and the rendered slices. `plain.make` calls `check()` before every picture (errors stop it, warnings are
recorded on the record's `checks`); the bench shows the findings. Not done: no chain prompt binds the slice yet; the video
contract does not yet read its limits from here.
