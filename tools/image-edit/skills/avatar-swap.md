---
name: avatar-swap
description: Avatar swap on a finished image. Same ad, a different person from the brand's banked cast; pose, framing, product, words and background all held. Use when someone says "avatar swap", "swap the person", "same ad, different person", "put <cast name> in this", "different model on this one".
---

# Avatar swap (image)

One finished picture in, the same picture out with ONE change: who the person is.

## Model check, before every run

This skill runs on **GPT Image 2.5 (`gpt_image_2_5`, variant `sunburst`)**. First search Higgsfield's models (`models_explore`
search "gpt image") for a NEWER version of that same model: the same maker and job
with a higher number or a newer release (GPT Image 3 after GPT Image 2.5). If
there is one, use it, and tell the person which one you used so this file gets
updated. Never switch to a different maker or a different kind of tool on your
own.

## Steps

1. You need the finished picture and the new person's banked cast photo (the
   brand's cast master, from the cast folder on the Drive). The new person always
   comes from the brand's cast. Never invent a new face from words.
2. `generate_image` with `model: gpt_image_2_5`, `variant: sunburst`,
   `quality: high`, `resolution: 2k`, `aspect_ratio` = the picture's own shape,
   `medias`: the picture first, the cast photo second, both `image_references`.
3. Prompt, filled in:

   > Image 1 is a finished ad. Image 2 is the person who should be in it. Change ONE thing in image 1: replace the person with the person in image 2 (her face, hair and build), in exactly the same pose, framing, expression and wardrobe register. Keep everything else in image 1 exactly as it is: {the product and where it is held, every word, the background, the light}. Nothing new added.

   If the picture shows the same person twice (a before and after), say so and
   swap both, keeping the difference between them (e.g. the spots in "before").
4. Check before handing over: it is visibly the image 2 person, same pose and
   framing, and the product, every word and the background are unchanged.
5. Name it like the original with `-<person>` on the end.

## Never

- Re-roll the whole picture from a prompt. An edit is the approved picture plus ONE change.
- Change two things in one run. Two changes = two runs, one after the other.
- Crop, stretch or add bars to fix a size. That is `resize-9x16`.

Not yet tested live (29 Sep: uploads of real faces need the owner's ok first).
