---
name: logo-swap
description: Logo swap on a finished image. Put the brand's real logo where a wrong, made-up or competitor logo sits, same place and size, everything else untouched. Use when someone says "swap the logo", "logo swap", "fix the logo", "that's the wrong logo", "put our logo on this".
---

# Logo swap (image)

One finished picture in, the same picture out with ONE change: the logo.

## Model check, before every run

This skill runs on **GPT Image 2.5 (`gpt_image_2_5`, variant `sunburst`)**. First search Higgsfield's models (`models_explore`
search "gpt image") for a NEWER version of that same model: the same maker and job
with a higher number or a newer release (GPT Image 3 after GPT Image 2.5). If
there is one, use it, and tell the person which one you used so this file gets
updated. Never switch to a different maker or a different kind of tool on your
own.

## Steps

1. You need two things: the finished picture, and the brand's logo file
   (from the brand's folder on the Drive, or the one the person hands over).
   No logo file, no run. Never let the model draw a logo from memory.
2. `generate_image` with `model: gpt_image_2_5`, `variant: sunburst`,
   `quality: high`, `resolution: 2k`, `aspect_ratio` = the picture's own shape,
   `medias`: the picture first, the logo second, both `image_references`.
3. Prompt, filled in:

   > Image 1 is a finished ad. Image 2 is the brand's logo. Change ONE thing in image 1: replace {which logo, where: e.g. the round mark in the middle of the tube's label} with the logo in image 2, same position, same size, same orientation, printed on the surface like the rest of it. Keep everything else in image 1 exactly as it is, to the pixel: {list what is in the picture: the headline, the product and every other word on it, the background, the light, the framing}. Nothing new added.

4. Check before handing over: the logo matches image 2 exactly (same letters,
   same proportions) and sits where the old one sat. Every word and every other
   object is unchanged. If anything else moved, run it again. Never keep a
   version where the words changed.
5. Name it like the original with `-logo` on the end.

## Never

- Re-roll the whole picture from a prompt. An edit is the approved picture plus ONE change.
- Change two things in one run. Two changes = two runs, one after the other.
- Crop, stretch or add bars to fix a size. That is `resize-9x16`.

Not yet tested live with a wrong logo (29 Sep: run on a picture that already had the right mark, and everything else held).
