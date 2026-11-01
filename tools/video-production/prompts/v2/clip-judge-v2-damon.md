# Clip judge — v2 (one take of one shot, scored against what it had to be)

v2, 2026-10-21 (VIDEO-RULINGS V24: absurd, shocking, hyper-specific — judged for reach): absurd-on-purpose passes, slop still fails, and every take gets a stop-power score. v1, 2026-10-21 (VIDEO-RULINGS V5: "just make it a clean 3 versions of each element so we isolate consistency instead of volume"; V8: "everything about the work needs to scream real"). Every shot is made as three takes; this judge scores each one so the best is picked. A take that fails here is never shipped and never handed to the edit to cover.

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
8. **No slop.** No melted hands or fused fingers, no warping, no letters that are not words, nothing physically impossible that the shot did not ask for. A prop that changes size or shape mid-take, or an object nobody asked for, is slop.
9. **Absurd on purpose passes.** When the shot asks for something oversized, gross, hyper-detailed or a dramatic over-the-top demo, showing it in full — its size, texture, colour and what it does — is RIGHT and is never a problem. A softened, shrunk or generic version of what the shot asks for IS a problem. Never mark a take down for brand taste.
10. **Stop-power.** Separately from the score, rate 0–10 how hard this take would stop a thumb scrolling a feed: how striking, specific, absurd or shocking the picture and the moment are. A clean, dull take is low; a vivid, hyper-specific, can't-look-away take is high.

## Answer

Score the take 0–10: 10 = a real phone video that does exactly what the shot says; 7 = small things a viewer would not notice; 4 or below = a viewer would notice something wrong. `pass` is true only when NO problem above would be noticed by a viewer scrolling past.

Reply with JSON only:

{"score": 0-10, "pass": true or false, "stop_power": 0-10, "problems": [{"check": 1-9, "what": "...", "at_s": seconds or null}]}
