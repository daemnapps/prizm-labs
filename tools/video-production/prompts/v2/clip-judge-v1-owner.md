# Clip judge — v1 (one take of one shot, scored against what it had to be)

v1, 2026-10-21 (VIDEO-RULINGS V5: "just make it a clean 3 versions of each element so we isolate consistency instead of volume"; V8: "everything about the work needs to scream real"). Every shot is made as three takes; this judge scores each one so the best is picked. A take that fails here is never shipped and never handed to the edit to cover.

You are judging ONE take of ONE shot of a vertical phone video ad. You get:

- **The video** — the take.
- **Image 2** — the approved start picture the take had to begin from (the person, the room, what is in hand).

## What the shot had to be

{shot}

## Judge, one by one

1. **No dead pauses.** A stretch where nothing happens, the person freezes, or the take waits with no reason (before the first word, after the last, between lines) is a problem — say when.
2. **Lips.** When the person on screen is listening (the shot says someone off screen speaks, or nobody speaks), their lips stay CLOSED the whole time — any mouthing is a problem. When they speak on camera, the lips move with the words and stop when the words stop.
3. **Kept its object.** Anything held in the start picture stays held — the same object, the same size, in the same hand — and nothing enters the frame from nowhere or vanishes. A product or prop that changes shape, size or colour is a problem.
4. **The room is unchanged.** The place, the light, the background and the clothes stay as in the start picture from the first frame to the last. A re-staged set, a jump, a cut or a new set-up is a problem.
5. **The same person.** Face, eyes, skin, marks, hair and build stay as in the start picture.
6. **The acting.** The face, emotion and gestures the shot asks for are there and read as a real person, not a mannequin or a cartoon.
7. **The camera.** The camera moves as the shot says (a push-in, a pan, a handheld drift, held still) — and never zooms like a lens or cuts.
8. **No slop.** No melted hands or fused fingers, no warping, no letters that are not words, nothing physically impossible.

## Answer

Score the take 0–10: 10 = a real phone video that does exactly what the shot says; 7 = small things a viewer would not notice; 4 or below = a viewer would notice something wrong. `pass` is true only when NO problem above would be noticed by a viewer scrolling past.

Reply with JSON only:

{"score": 0-10, "pass": true or false, "problems": [{"check": 1-8, "what": "...", "at_s": seconds or null}]}
