# Fixed-subject cast swap — rebuild sheet

One party photo of one man, held unchanged for 15.6 seconds while a different group is pasted in beside him each beat under a label that climbs the alphabet — 5,906,590 views and 36,332 likes (0.6% like rate) for @tsiorasaj.

**Why it works**
The photograph never changes — same pose, same shirt, same bag, same tent and crowd behind — so the only thing the eye has to read each beat is who has appeared next to him, and that reads instantly. The letters do the rest: by the time you're at Plan G you know there are more plans than the video can show, and the alphabet, not the runtime, is what keeps you there.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 1.25s | The plate: subject centre, black open-mesh shirt, small black clutch at his hip, teal-lit tent and party crowd behind, flash on his face. Composited in: a woman in a brown two-piece and two children in white. | Plan A |
| 3.74s | Identical plate, nobody composited in — he's alone. | Plan C |
| 6.24s | Identical plate, three dishevelled men cut in around him — open white shirt and khakis, two in dirty worn workwear, one wrist bandaged. The cut-ins are lit warmer than the plate. | Plan E |
| 8.74s | Identical plate, an older blonde woman in a black lace dress with a chain-strap handbag, arm around him. | Plan G |
| 11.23s | Identical plate, alone again with a pink flamingo pool float beside him. | Plan I |
| 13.73s | Same plate under a cooler, darker grade, two costumed men cut in — a bald bespectacled man in a hat and dark coat, a younger man in plaid. | Plan J |

Read honestly off six stills: the sheet samples every 2.5 seconds and the letters jump A → C → E → G → I, so the video is cutting faster than the sample — roughly one plan per 1.25 seconds, with B, D, F and H landing between the frames I can see. I can't show you those four. The last two samples are only one letter apart, so J looks like it's held longer as the ending. I have no audio and no read on what the pair in Plan J are meant to be — they look like a recognisable TV duo, but stills can't confirm it.

The caption is Greek: "Για plan H και K μαζί είμαι" — my reading is "for plan H and K together, I'm in." It names two plans: H, which falls in a gap between my frames, and K, which is past the last label I can see. So either the video runs beyond J or the caption is joking about a plan that was never shown — the frames don't settle it.

**What carries the value**
The enumeration. One unchanged photograph, the company swapped out under a rising letter — the alphabet implies a longer list of possible lives than the video has time for, and every cut is a one-second gag landing against a constant. Nothing transforms, nothing builds; the joke is the count.

**Shoot it**
- **Camera:** none, in the moving sense. You need one photograph, taken once. Vertical, phone, subject standing flat to camera, whole body in frame with room on both sides — that empty space either side is where every later beat gets pasted. Then it never moves again.
- **Light:** shot as-is with on-camera flash at night — the subject is punched bright and the venue falls off behind him. Any strong single source that separates the subject from a busy background works; the background wants to be visibly a *place* (crowd, lights, structure) so the constant is unmistakable.
- **Wardrobe:** one outfit, held for the entire piece — it's the thing that tells the viewer this is the same photo again. Distinctive enough to recognise at a glance (here: black open-mesh shirt, black trousers, a small black bag held at the hip).
- **The cut-ins:** each beat is a cut-out group dropped beside him, standing at the same ground line and roughly his height. In this video the cut-ins aren't perfectly matched to the plate's light — Plan E's men are warmer, Plan J is graded cooler — and it doesn't hurt it at all. The seams are part of the joke.
- **Editing:** hard cuts, about a second and a quarter each, no transitions. Label in the same place every beat, same size, never moving.

**Or generate it**
Generate the plate once, then reuse that exact image for every beat — regenerating it is what breaks the format.

```
vertical 9:16 phone snapshot, {SUBJECT} standing centre frame at night at an
open-air party venue, holding {PRODUCT} down at one hip, posed flat to camera
with weight on one leg; behind them a large tent lit teal, a lighting rig on a
black pole, a blurred crowd and string lights along the back, a low white couch
at the frame edge, deep blue night sky; hard on-camera flash on {SUBJECT} with
the venue light falling off behind, slight grain, no retouching, no on-screen
text — this exact plate is the constant and every later beat reuses it unchanged
with different people composited in beside {SUBJECT}
```

**Motion:** no camera move of any kind — the plate is a still photograph, and each beat is a hard cut to the identical framing with different company cut in, held roughly a second.

**Text overlay:** `Plan {LETTER}` — white sans-serif, same size and same top-third position every beat, the letter advancing through the alphabet one beat at a time. The caption then picks two letters and takes a side on them.

**Reference:** https://www.instagram.com/p/Dbnj-vtu7Wg/
