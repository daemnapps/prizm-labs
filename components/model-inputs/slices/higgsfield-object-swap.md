# Genjutsu object swap — what it takes, and what works

*Rendered from `components/model-inputs/inputs/higgsfield-object-swap.json` (read 2026-10-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- duration seconds: 4 to 30
- max images: 8
- max videos: 1
- resolutions: 480p to 720p to 1080p
- min shot seconds: a clean shot of at least about 2 s with no cut inside (ours); the model's minimum is 4 s, a shorter shot is played forward-back-forward to reach it and trimmed (ours, 18 Oct)
- price per second usd: from 0.159 (list 0.318) at Genjutsu; about 8.3 credits a second measured at 1080p (ours)
- maker documentation: Higgsfield publishes no step-by-step page for Object Swap; its blog describes the mode and a third-party guide tested it. Limits above the vendor's list are OURS, measured.
- never send stems: master
- min video seconds: 4
- image formats: jpg to jpeg to png to webp
- House: resolution 480p, upscaled locally (the house size); per_shot one swap per shot, never one pass over a clip with cuts; person a cast member's BASELINE (headshot, look, details, expressions), never the master (the owner, 2026-10-27; replaces the earlier 'send the whole sheet' line)

## The prompt structure that works

- **A swap replaces something that is already in the shot and never adds. Whatever must be on a counter, in a hand or on a wall has to be in the SOURCE shot already, or come from a scene still made first; the swap will not put it there.**
- **The cast member goes in from the BASELINE pictures, never the master. A swap given the master alone is a face swap; the baseline gives the face, the look, the details and the expressions the shot needs.**
- **Split at the cuts and swap one shot at a time; a whole-clip pass missed people in 4 of 16 shots and put the wrong subject on the wrong person.**
- **State the before and the after state from the brief; everything else, body included, stays identical.**
- **Name every accessory of the original that must go, not only a colour; a headwrap's tails survived when only its colour was removed.**
- **A recast subject is built inside the shot's own light and look, not laid in from a studio sheet.**
- **Every swap is checked against the baseline before it is kept; when the swap kept the original person's face, send the same shot to motion control instead (9 of 9 kept it).**
- **A shot under the 4 s minimum is played forward-back-forward and trimmed; trim the loop seam off.**
- **Before a batch, find a clip and object pair that works reliably: try a different prop in the same source clip, hold the action fixed and compare at the same moment.**

## Avoid

- Expecting our line from a swap: it keeps the original mouth, so it carries no line of ours.
- Expecting it to add things: it replaces, never adds; the product goes only where the swipe already has something in hand.
- One swap pass over a clip with several cuts.
- Sending the master as the person: it is a face swap, and the baseline is the rule.
- A shot shorter than the model's minimum without playing it forward-back-forward.
- Removing an accessory by naming only its colour.
- A studio-backdrop sheet as the only reference: it reads pasted on.
- Keeping a swap without checking the face: 9 of 9 kept the original person.
