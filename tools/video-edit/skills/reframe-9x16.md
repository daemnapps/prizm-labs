---
name: reframe-9x16
description: Video aspect ratio resize. Turn a clip in any shape (16:9, 1:1, 4:5) into 9:16 with the footage kept whole and the edges filled, never cropped or barred. Use when someone says "this video isn't 9:16", "make this vertical", "reframe to 9:16", "resize the video", "aspect ratio resize" on a video.
---

# Reframe to 9:16 (video)

## Model check, before every run

This skill runs on **Higgsfield Reframe (`reframe`)**. First search Higgsfield's models (`models_explore`
search "reframe") for a NEWER version of that same model: the same maker and job
with a higher number or a newer release. If there is one, use it, and tell the
person which one you used so this file gets updated. Never switch to a
different maker or a different kind of tool on your own.

**Price it first.** Video costs real credits: run the same call with
`get_cost: true`, say the number, then run it.

## Steps

1. Already 9:16 → leave it alone and say so.
2. `reframe` with `aspect_ratio: "9:16"` and the clip as the one `video` media.
   Over 15 seconds: also pass `duration_seconds` and `resolution: "1080p"`
   (max 60 seconds; longer clips are cut into parts first).
3. Optional: a still of the scene as an `image` media guides how the edges are filled.
4. Check: the original footage sits in the middle, whole and unchanged;
   faces, product and any words sit inside the middle 4:5 of the frame; the
   filled edges don't flicker or add anything new.
5. Name it like the original with `-9x16` on the end.

A picture, not a clip? Use the image skill `resize-9x16`.

## Never

- Regenerate the whole clip from a prompt. An edit is the approved clip plus ONE change.
- Change two things in one run. Two changes = two runs.
- Crop, stretch or add bars to fix a size. That is `reframe-9x16`.

Not yet tested live (written 29 Sep from the Higgsfield tool definitions).
