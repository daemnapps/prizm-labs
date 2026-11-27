# Recipe · drama camera and performance (v1)

The camera and acting rule every micro-drama clip carries (format `micro-drama`, station "Script, plan and clip prompts").
It replaces the Drama Ads defaults of a locked-off frame, a slow push and small acting. The Drama Ads skill's own
rules stay as they are; this is our override on top of them, applied to every clip prompt before checks.py runs.

Proven on the first micro-drama that went through cleanly (the two-film Drama Ads test of 2026-11-26 and the part 1
it was restored onto, 2026-11-27): the owner's correction was "restore the successful drama ad process, including
emotion and camera movement".

## Every story shot

1. **A physical camera move.** Name it as a move with a start and an end: handheld follow, whip pan to the speaker,
   push from the doorway to a close-up, orbit half way round the table, crash zoom on the reaction. Never "locked-off",
   "static camera" or "slow push" (the check refuses those words unless the setup marks the shot `static_ok` with
   its reason, e.g. a black end card).
2. **A cut or reframe every 2 to 3 seconds**, inside the clip's shot list. Keep enough screen time for the product
   proof and for any physical action to finish on screen.
3. **A visible reaction to what came before.** Each beat opens on the listener answering the last line or action:
   the face changes, the gaze moves, the body shifts. Direct the face, the gesture, the gaze and the delivery of
   the line, never an emotion adjective alone ("she is hurt" is not direction; "her jaw sets, she looks at the
   floor, then back up before the line" is).
4. **The camera reference is movement only.** When a silent camera reference clip goes in, it directs how the
   camera moves and nothing else: the cast, room and product come from this film's own sheets.

## What stays fixed

The approved dialogue word for word, the cast as cast (identity, skin, the visible problem the story turns on),
wardrobe, the product from its own approved casting sheet, and the production voices.

## Accepting a take

A PASS from checks.py validates the prompt only. A take is accepted after looking at the returned clip for five
things, each written into `film/takes.json` (`looked`): the camera movement, the acting and reactions, identity,
the dialogue as heard, and continuity with the clips before and after.
