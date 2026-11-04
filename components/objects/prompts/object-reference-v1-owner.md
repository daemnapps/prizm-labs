# Object reference image, v1 (the owner)

The one image a 3D object is built from. Fill the braces; send the real photo
of the thing as a reference image whenever one exists. Model: GPT Image 2.5
(`gpt_image_2_5`) on the Higgsfield connector, aspect 4:3 (or 3:4 for tall
things).

---

A single {what}, {detail}. Shown whole, in a three-quarter view that shows its
shape clearly, centred with margin all round. Isolated on a plain light-grey
studio background, soft even lighting, no props, no hands, no text unless the
object itself carries it ({text_rule}). Photoreal, crisp modern iPhone-quality
detail; true colours and materials as they are in real life{match_rule}.

---

- `{what}`: the thing, plainly ("koi fish", "DJ turntable with a record on it").
- `{detail}`: the facts that make it *this* one (colours, material, era, size cue).
- `{text_rule}`: "no readable text" by default; or the exact word it carries ("the neon reads GOJA").
- `{match_rule}`: when a real photo is attached: ", matching the reference photo exactly".
