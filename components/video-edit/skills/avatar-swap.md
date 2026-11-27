---
name: avatar-swap
description: Avatar swap on a finished video clip. Same clip, a different person from the brand's banked cast; motion, framing, product and background held. Use when someone says "avatar swap", "swap the person in this video", "same clip, different person", "put <cast name> in this clip", "recast this".
---

# Avatar swap (video)

## Model check, before every run

This skill runs on **Higgsfield Genjutsu, replace object (`hf_mult_replace_object`)**. First search Higgsfield's models (`models_explore`
search "genjutsu replace") for a NEWER version of that same model: the same maker and job
with a higher number or a newer release. If there is one, use it, and tell the
person which one you used so this file gets updated. Never switch to a
different maker or a different kind of tool on your own.

**Price it first.** Video costs real credits: run the same call with
`get_cost: true`, say the number, then run it.

## Steps

1. You need the clip and the new person's banked cast photo (the brand's cast master). The new person always comes from the brand's cast.
2. `generate_video` with `model: hf_mult_replace_object`, `resolution: "1080p"`,
   `medias`: the clip with role `video`, the reference picture with role `image`.
3. Prompt, filled in:

   > Replace the person with the person in the reference image (face, hair and build), doing exactly the same movements, in the same framing, with the same expression and timing. Keep everything else exactly as it is: {list what is in the clip: the other people, the product, any words on screen, the background, the camera move}. Nothing new added.

4. Check the whole clip, not one frame: the swap holds on every frame, nothing
   else changed, words on screen are untouched, no flicker at the edges.
5. Name it like the original with `-avatar` on the end.

**The other way to recast:** if the new person should perform the clip's
motion in THEIR OWN scene (their room, their outfit), use
`hf_mult_motion_control` instead: the cast photo as `image`, the clip as
`video`. That is a new scene with the same moves, not a swap inside the old one.

## Never

- Regenerate the whole clip from a prompt. An edit is the approved clip plus ONE change.
- Change two things in one run. Two changes = two runs.
- Crop, stretch or add bars to fix a size. That is `reframe-9x16`.

Not yet tested live (written 29 Sep from the Higgsfield tool definitions).
