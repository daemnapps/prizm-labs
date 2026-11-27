---
name: cast-deslop
description: Make a generated character look real before it goes into any video. Two steps for every character, from the first casting: de-slop the master with real skin and hair texture photos, then build the character's video element (a talking, moving reference clip with its voice). Use when someone says "de-slop this character", "deslop <name>", "make <name> look real", "skin texture pass", "build the video element for <name>", "video cast <name>", "get <name> ready for video", after any new master is generated, or before any scene that puts a cast character in video.
---

# Cast de-slop + video element

External dependencies: `brands/_TEMPLATE/ai-cast/CHARACTER-SPEC.md` (steps 3b and 5b are this skill), `runs/ai-elements/_texture-refs/` (the shared texture photo bank and its `index.json`), `runs/ai-elements/<brand>/casting/<id>/` (the character's folder), `components/generative-model-house/` (`MODEL-HOUSE.md` + `models.json`: the only place a model is chosen), the Higgsfield tools (`media_upload`, `generate_image`, `generate_video`, `jobs_wait`).

**Models come from the Model House, never from this file.** Today the house says: picture edits use GPT Image 2.5, with Seedream as the backup (`pictures.edit` / `pictures.backup`), and a talking take follows the `clips.take` route order (ruled 2026-11-09): Wan 3.0 start-frame first (`clips.take`), Seedance 2.5 omni-reference as the backup (`clips.take_backup`). A model the house does not list is never used, except as a labelled test the owner asked for.

Every character runs both steps before it is castable in video. No scene uses a raw master.

## Step 1 · De-slop the master (picture)

From 2026-11-10 this step runs INSIDE the casting sheet tool (`components/video-production/machine/make_character.py`, step 2 after the master): name the two bank rows in the spec's `texture` (`{"skin": {file, shows}, "hair": {file, shows, on}, "keep"}`), run `--only deslop`, check the takes at 100% crop, `--pick-deslop a|b`, then run the sheets. Use the steps below by hand only for a master made before that date; the bank rules (1) apply either way.

1. **Pick texture references** from `runs/ai-elements/_texture-refs/index.json`. Use two kinds together (owner ruling, 2026-11-26): a **customer** row (a crop of a real customer's before photo, the closest match in tone, age and condition: acne, razor bumps, dark marks) and a **macro** row (a close macro shot of that skin type's pores). Pick one hair row too. If no row matches, fill the gap first:
   - Customer rows: crop the brand's before/after photos (`Shared Assets/brands/<brand>/intake/before-after/`) to skin only: the "before" side, no eyes, no full face, no words.
   - Macro rows: a free stock macro photo (Pexels or Unsplash), or a texture crop of owned creator footage.
   - Save it in the bank with its source, its `kind` (customer or macro) and its `condition`, and add the row.
   - The reference gives texture only: never copy a customer's or creator's face, and never show their photo itself in an ad.
2. **Upload** the references (or reuse the `higgsfield_media_id` in the row) and the character's `master.jpg`.
3. **Generate** with the house's `pictures.edit` model (GPT Image 2.5 on Higgsfield, `gpt_image_2_5`), image edit: 9:16, count 2. If it refuses, use the house backup (`seedream_v5_pro`). Order the references as master, then skin, then hair. Prompt template:

   > Image 1 is the character: keep this exact person, same face, bone structure, eyes, expression, hair shape, hairline, wardrobe, framing and background. Change only the surface texture. Take the skin texture from Image 2 (<what it shows>) and apply it to the face, forehead, nose and neck, keeping the character's own skin tone and redness. Remove any over-etched or plastic AI skin. Take the hair texture from Image 3 (<what it shows>) and apply it to the <hair/beard>, keeping its shape and color. Real fabric weave on the clothes. Unretouched phone photo, soft window light, slight grain. Do not copy any face or person from Images 2 or 3.

4. **Check** a 100% crop of nose, cheeks, mouth and beard: raw master beside each take.
   - Pass: real pore and freckle pattern, single hairs with skin showing between them, same face.
   - Fail: smoothed, plastic, a different face, or the reference person showing through. Redo.
5. **Save** to `deslop/`: both takes, the references used in `deslop/refs/`, and which take passed. The passing take is the master every board and video uses from now on.

## Step 2 · Video element (video casting)

1. **Line:** one short, natural line in the character's lane, taken from the brand's language bank. Not ad copy.
2. **Generate** on the house's `clips.take` route: Wan 3.0 (`wan3_0`), with the de-slopped master as `start_image`, 8 s, 9:16, sound on, 3 takes. On a refusal or failure, fall back to `clips.take_backup`: Seedance 2.5 (`seedance_2_5`, omni_reference), sending the voice sample as `audio_references` once the character has one.

   Prompt: handheld phone selfie, same person, same wardrobe and room, talks straight to camera, says the line, one small hand-to-face move, natural blinks, voice described by age, register and delivery, skin keeps its pores and redness, no music.
3. **Check** frames at one per second:
   - Face stays the same person.
   - The mouth moves with the words.
   - Hands never cover the face for long.
   - Skin stays real in motion.
4. **Show the takes side by side with sound** on the character's page. The owner picks one. Never pick for them: the take sets the character's voice for every ad after.
5. **Save** the pick as `video-element/@char_<id>_video_v1.mp4`. Write the voice and the element name into the character's records. Every scene prompt then names `@char_<id>_video_v1` for face, hair, wardrobe and voice. Pose, props and light come from the scene.

## Cost
- 2 picture edits and 3 Wan takes per character (Seedance only as the backup), on credits, never unlimited without a yes.
- A rerun replaces only the step that failed.

## Tested
- 2026-11-09, Brand A `wes`: round 2 with references passed the zoom check. Made on Seedream (picture) and Seedance / Wan / Kling (clips) before this skill read the Model House. Kling is out. Wan 3.0 is the house's first route for takes, with Seedance as the backup.
