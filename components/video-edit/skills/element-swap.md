---
name: element-swap
description: Element swap on a finished video clip. Change ONE object (a product, a prop, a garment, a badge) on every frame and hold everything else. Use when someone says "swap the product in this video", "element swap", "change the outfit", "replace the bottle", "swap the prop".
---

# Element swap (video)

## Model check, before every run

This skill runs on **Higgsfield Genjutsu, replace object (`hf_mult_replace_object`)**. First search Higgsfield's models (`models_explore`
search "genjutsu replace") for a NEWER version of that same model: the same maker and job
with a higher number or a newer release. If there is one, use it, and tell the
person which one you used so this file gets updated. Never switch to a
different maker or a different kind of tool on your own.

**Price it first.** Video costs real credits: run the same call with
`get_cost: true`, say the number, then run it.

## Steps

1. You need the clip and a picture of the new thing: the brand's real product photo for a product (always), otherwise a clear picture of the new object or garment.
2. `generate_video` with `model: hf_mult_replace_object`, `resolution: "1080p"`,
   `medias`: the clip with role `video`, the reference picture with role `image`.
3. Prompt, filled in:

   > Replace {the thing} with the {new thing} in the reference image, on every frame, same size, same position, held and moved exactly as the original was. Keep everything else exactly as it is: {list what is in the clip: the other people, the product, any words on screen, the background, the camera move}. Nothing new added.

4. Check the whole clip, not one frame: the swap holds on every frame, nothing
   else changed, words on screen are untouched, no flicker at the edges.
5. Name it like the original with `-element` on the end.

## Never

- Regenerate the whole clip from a prompt. An edit is the approved clip plus ONE change.
- Change two things in one run. Two changes = two runs.
- Crop, stretch or add bars to fix a size. That is `reframe-9x16`.

Not yet tested live (written 29 Sep from the Higgsfield tool definitions).
