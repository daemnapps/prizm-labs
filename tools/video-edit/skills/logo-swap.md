---
name: logo-swap
description: Logo swap on a finished video clip. Put the brand's real logo where a wrong, made-up or competitor logo sits, on every frame, everything else untouched. Use when someone says "swap the logo in this video", "logo swap", "wrong logo on the clip", "put our logo on this video".
---

# Logo swap (video)

## Model check, before every run

This skill runs on **Higgsfield Genjutsu, replace object (`hf_mult_replace_object`)**. First search Higgsfield's models (`models_explore`
search "genjutsu replace") for a NEWER version of that same model: the same maker and job
with a higher number or a newer release. If there is one, use it, and tell the
person which one you used so this file gets updated. Never switch to a
different maker or a different kind of tool on your own.

**Price it first.** Video costs real credits: run the same call with
`get_cost: true`, say the number, then run it.

## Steps

1. You need the clip and the brand's logo file (from the brand's folder on the Drive). Never let the model draw one.
2. `generate_video` with `model: hf_mult_replace_object`, `resolution: "1080p"`,
   `medias`: the clip with role `video`, the reference picture with role `image`.
3. Prompt, filled in:

   > Replace {which logo, where} with the logo in the reference image, on every frame, same position, same size, following the surface it is on as it moves. Keep everything else exactly as it is: {list what is in the clip: the other people, the product, any words on screen, the background, the camera move}. Nothing new added.

4. Check the whole clip, not one frame: the swap holds on every frame, nothing
   else changed, words on screen are untouched, no flicker at the edges.
5. Name it like the original with `-logo` on the end.

## Never

- Regenerate the whole clip from a prompt. An edit is the approved clip plus ONE change.
- Change two things in one run. Two changes = two runs.
- Crop, stretch or add bars to fix a size. That is `reframe-9x16`.

Not yet tested live (written 29 Sep from the Higgsfield tool definitions).
