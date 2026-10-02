---
name: element-swap
description: Element swap on a finished image. Change ONE thing in the picture (a product, a prop, a badge, the background, or take something out) and hold everything else. Use when someone says "element swap", "swap the product", "change the background", "swap the prop", "take the watermark out", "replace the soap with leaves".
---

# Element swap (image)

One finished picture in, the same picture out with ONE thing changed.

## Model check, before every run

This skill runs on **GPT Image 2.5 (`gpt_image_2_5`, variant `sunburst`)**. First search Higgsfield's models (`models_explore`
search "gpt image") for a NEWER version of that same model: the same maker and job
with a higher number or a newer release (GPT Image 3 after GPT Image 2.5). If
there is one, use it, and tell the person which one you used so this file gets
updated. Never switch to a different maker or a different kind of tool on your
own.

## Which swap

| The ask | The change line | Reference picture |
|---|---|---|
| product | replace the product with the product in image 2, same angle, same size, same spot, same hand | the brand's real product photo (always, never drawn) |
| prop / object | replace {the thing} with {the new thing}, the same size and in the same spot, lit by the same light | optional |
| badge / sticker | replace {the badge} with {the new badge}, same position and size | the badge file, if there is one |
| background | replace the background with {the new setting}, keeping every foreground element exactly where it is | optional |
| remove | remove {the thing} and fill the space with what is behind it | none |

The person is `avatar-swap`. The logo is `logo-swap`. Words in the picture are
not swapped here: type is set by the designer, not redrawn by a model.

## Steps

1. `generate_image` with `model: gpt_image_2_5`, `variant: sunburst`,
   `quality: high`, `resolution: 2k`, `aspect_ratio` = the picture's own shape,
   `medias`: the picture first, then the reference picture if the row has one.
2. Prompt, filled in:

   > This is a finished ad. Change ONE thing: {the change line}. Keep everything else exactly as it is, to the pixel: {list what is in the picture: the headline, the product and every word on it, the people, the background, the framing}. Nothing else added or moved.

3. Check before handing over: the one thing changed, and nothing else did.
   Words are the first thing to check. If anything else moved, run it again.
4. Name it like the original with `-<what changed>` on the end.

Tested 29 Sep in Higgsfield: a soap bar → a sprig of green leaves on a finished ad. The
leaves landed on the same dish; headline, tube and every word held.

## Never

- Re-roll the whole picture from a prompt. An edit is the approved picture plus ONE change.
- Change two things in one run. Two changes = two runs, one after the other.
- Crop, stretch or add bars to fix a size. That is `resize-9x16`.
