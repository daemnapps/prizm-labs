---
name: resize-9x16
description: Aspect ratio resize. Turn any image (4:5, 1:1, 16:9, 2:3, odd sizes) into a 9:16 asset with the picture untouched and inside the centred 4:5 safe zone, the background continued around it. Use when someone says "these aren't 9:16", "this isn't 9:16", "resize to 9:16", "make this 9:16", "aspect ratio resize", "fix the ratio", or hands over an image or video in the wrong shape.
---

# Aspect ratio resize → 9:16

Every ad asset is 9:16. Everything that matters (faces, product, headline,
badges, price) sits inside the centred 4:5 window of that frame, because feed
placements crop a 9:16 down to that window. So a wrong-shaped picture is never
cropped, never stretched, never padded with bars and never regenerated. The
whole picture is kept exactly where the numbers below put it, and only the
background around it is painted.

## Model check, before every run

This skill runs on **FLUX.2 Pro Outpaint**. First search Higgsfield's models
(`models_explore` search "outpaint") for a NEWER version of the same model:
the same maker and job with a higher number (FLUX.3 Pro Outpaint, FLUX.2 Max
Outpaint). If there is one, use it, and tell the person which one you used so
this file gets updated. Never switch to a different maker or a different kind
of tool on your own.

## Image: the one model to use

**FLUX.2 Pro Outpaint** (`flux_2_pro_outpaint`), because it takes the number of
pixels to add on each side, so the picture lands exactly inside the safe zone.
Do NOT use the plain "Outpaint" tool (`outpaint_image`) for this: tested
29 Sep, it zooms out and redraws the whole scene smaller, and the headline ends
up on the edge of the safe zone.

### Steps

1. **Read the image's width W and height H.**
   - Already 9:16 (H ÷ W is 1.77 or 1.78) → leave it alone and say so.
   - Taller than 9:16 → say so and stop. That is not a resize case.
2. **Make it 1080 wide if it is wider.** FLUX refuses big files. If W is more
   than 1080, shrink it to 1080 wide (keep the shape), for example in the
   sandbox: `magick in.png -resize 1080x out.png`, then upload `out.png` and
   use its new W and H.
3. **Work out the four numbers.**
   - If H ÷ W is 1.25 or less (4:5, 1:1, 3:2, 16:9, anything wider):
     `total = round(W × 16 ÷ 9)` · `top = floor((total − H) ÷ 2)` ·
     `bottom = total − H − top` · `left = right = 0`
   - If H ÷ W is more than 1.25 (2:3, 3:4 portrait, 5:7…):
     `frame = round(H × 4 ÷ 5)` · `left = floor((frame − W) ÷ 2)` ·
     `right = frame − W − left` · `total = round(frame × 16 ÷ 9)` ·
     `top = floor((total − H) ÷ 2)` · `bottom = total − H − top`

   Ready-made for the usual sizes:

   | In (W × H) | top | bottom | left | right | Out |
   |---|---|---|---|---|---|
   | 1080 × 1350 (4:5) | 285 | 285 | 0 | 0 | 1080 × 1920 |
   | 1080 × 1080 (1:1) | 420 | 420 | 0 | 0 | 1080 × 1920 |
   | 1080 × 608 (16:9) | 656 | 656 | 0 | 0 | 1080 × 1920 |
   | 720 × 1080 (2:3) | 228 | 228 | 72 | 72 | 864 × 1536 |

4. **Run it.** `generate_image` with `model: flux_2_pro_outpaint`, the image
   as `image_references`, `input_width: W`, `input_height: H`, the four
   `expand_*` numbers, and this prompt word for word (no dashes in it, the
   model rejects them):

   > Extend this picture outward on every side. The visible picture is finished and must not change in any way. Continue the same backdrop, the same surface, the same light, the same colour and grain, seamlessly, with no edge, no band and no change of tone where it meets the picture. Put nothing new there: no object, no word, no logo, no shape, no person. Background only.

5. **Check it before handing it over.** The original sits in the middle,
   unchanged. Nothing new was added around it: no words, objects, people or
   logos. The seam where the new background meets the picture doesn't show.
   If any of that fails, run step 4 again. Never fix it by cropping.
6. Name the result like the original with `-9x16` on the end.

## Video

`reframe` with `aspect_ratio: "9:16"` on the source video.

## Never

- "Crop to 9:16". It cuts off the headline, the product or the face.
- "Fit with bars" or a solid colour band. It reads as a mistake in feed.
- Regenerating the picture at 9:16 from its prompt. It changes the picture.
- The plain Outpaint tool for a static. It shrinks the picture.

This is the Higgsfield copy of the team's `resize-9x16` skill. The finishing step
in image production is `tools/image-production/tools/finish.py`.
